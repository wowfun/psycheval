from __future__ import annotations

import re
from pathlib import PurePosixPath

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.task.config import TaskOS
from harbor.models.trial.paths import EnvironmentPaths
from harbor.utils.scripts import quote_shell_arg
from harbor.utils.trajectory_validator import TrajectoryValidator

from psycheval import __version__
from psycheval.harbor.runtime_config import (
    PEVAL_CONFIG_ENV,
    EffectiveRuntimeConfig,
    HarnessInvocation,
    RuntimePaths,
    write_effective_runtime_config,
)

_WINDOWS_ABSOLUTE = re.compile(r"^(?P<drive>[A-Za-z]):[/\\]")


def _normalize_workdir(value: str, task_os: TaskOS) -> str:
    if "\x00" in value:
        raise ValueError("ExternalHarnessAgent workdir contains NUL")
    normalized = value.replace("\\", "/") if task_os == TaskOS.WINDOWS else value
    if task_os == TaskOS.WINDOWS:
        match = _WINDOWS_ABSOLUTE.match(normalized)
        if match is not None:
            drive = match.group("drive").upper()
            if drive != "C":
                raise ValueError(
                    "ExternalHarnessAgent workdir must use the C: environment drive"
                )
            path = normalized[2:]
        elif normalized.startswith("/") and not normalized.startswith("//"):
            drive = "C"
            path = normalized
        else:
            raise ValueError(
                "ExternalHarnessAgent workdir must be an absolute environment path"
            )
    else:
        if not normalized.startswith("/") or normalized.startswith("//"):
            raise ValueError(
                "ExternalHarnessAgent workdir must be an absolute environment path"
            )
        drive = None
        path = normalized
    if ".." in path.split("/"):
        raise ValueError("ExternalHarnessAgent workdir cannot traverse a parent")
    canonical = PurePosixPath(path).as_posix()
    return f"{drive}:{canonical}" if drive is not None else canonical


class ExternalHarnessAgent(BaseAgent):
    """Run a caller-provided harness that writes canonical ATIF output."""

    SUPPORTS_ATIF = True
    SUPPORTS_RESUME = True
    SUPPORTS_LOAD_NATIVE_TRAJECTORY = False
    SUPPORTS_LOAD_ATIF_TRAJECTORY = False
    SUPPORTS_WINDOWS = True

    def __init__(
        self,
        *args,
        command: str | None = None,
        workdir: str | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.command = (command or "").strip()
        if not self.command:
            raise ValueError("ExternalHarnessAgent requires --agent-kwarg command=...")
        if "\x00" in self.command:
            raise ValueError("ExternalHarnessAgent command contains NUL")
        if workdir is not None and not workdir.strip():
            raise ValueError("ExternalHarnessAgent workdir must not be empty")
        self.workdir = workdir.strip() if workdir is not None else None

    @staticmethod
    def name() -> str:
        return "psycheval-external-harness"

    def version(self) -> str:
        return __version__

    async def setup(self, environment: BaseEnvironment) -> None:
        return None

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        await self._invoke("run", instruction, environment, context)

    async def resume(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        await self._invoke("resume", instruction, environment, context)

    async def _invoke(
        self,
        action: str,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        instruction_path = self.logs_dir / "instruction.txt"
        instruction_path.write_text(instruction, encoding="utf-8")
        trajectory_path = self.logs_dir / "trajectory.json"
        trajectory_path.unlink(missing_ok=True)
        environment_paths = EnvironmentPaths.for_os(environment.os)
        configured_workdir = self.workdir or environment.task_env_config.workdir
        default_workdir = environment_paths.logs_dir.parent / "app"
        workdir = _normalize_workdir(
            configured_workdir or default_workdir.as_posix(), environment.os
        )
        prepare_result = await environment.ensure_dirs([workdir], chmod=False)
        if prepare_result is not None and prepare_result.return_code != 0:
            diagnostic = (
                prepare_result.stderr or prepare_result.stdout or "no output"
            ).strip()
            raise RuntimeError(
                "external harness could not prepare workdir "
                f"{workdir!r}: {diagnostic[-2000:]}"
            )
        runtime_config_path = self.logs_dir / "peval.json"
        write_effective_runtime_config(
            runtime_config_path,
            EffectiveRuntimeConfig(
                paths=RuntimePaths(
                    workdir=workdir,
                    tests=environment_paths.tests_dir.as_posix(),
                    agent_logs=environment_paths.agent_dir.as_posix(),
                    verifier_logs=environment_paths.verifier_dir.as_posix(),
                    artifacts=environment_paths.artifacts_dir.as_posix(),
                ),
                harness=HarnessInvocation(action=action),
            ),
        )
        virtual_instruction = environment_paths.agent_dir / "instruction.txt"
        virtual_runtime_config = environment_paths.agent_dir / "peval.json"
        result = await environment.exec(
            f"{self.command} < {quote_shell_arg(virtual_instruction, environment.os)}",
            cwd=workdir,
            env={PEVAL_CONFIG_ENV: virtual_runtime_config.as_posix()},
        )
        (self.logs_dir / "external-harness.stdout.log").write_text(
            result.stdout or "", encoding="utf-8"
        )
        (self.logs_dir / "external-harness.stderr.log").write_text(
            result.stderr or "", encoding="utf-8"
        )
        if result.return_code != 0:
            diagnostic = (result.stderr or result.stdout or "no output").strip()
            raise RuntimeError(
                f"external harness exited with {result.return_code}: {diagnostic[-2000:]}"
            )
        if not trajectory_path.is_file():
            raise RuntimeError(
                "external harness did not write "
                f"{environment_paths.agent_dir.as_posix()}/trajectory.json"
            )
        validator = TrajectoryValidator()
        if not validator.validate(trajectory_path):
            raise RuntimeError(
                "external harness wrote invalid ATIF: " + "; ".join(validator.errors)
            )
        context.metadata = {
            "harness_action": action,
            "harness_return_code": result.return_code,
            "trajectory": str(trajectory_path),
            "workdir": workdir,
        }
