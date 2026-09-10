from __future__ import annotations

from pathlib import PurePosixPath
from uuid import uuid4

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.task.config import TaskOS
from harbor.models.trial.paths import EnvironmentPaths
from harbor.utils.scripts import quote_shell_arg

from . import __version__, windows
from .environment import HostEnvironment
from .inference_telemetry import populate_context_from_trajectory
from .runtime_config import (
    PEVAL_CONFIG_ENV,
    EffectiveRuntimeConfig,
    HarnessInvocation,
    RuntimePaths,
    write_effective_runtime_config,
)
from .trajectory_validation import load_validated_trajectory


def _normalize_workdir(value: str, task_os: TaskOS) -> str:
    label = "ExternalHarnessAgent workdir"
    if task_os == TaskOS.WINDOWS:
        return "C:" + windows.normalize_environment_path(
            value, label=label, allow_root=True
        )
    if "\x00" in value:
        raise ValueError(f"{label} contains NUL")
    if not value.startswith("/") or value.startswith("//"):
        raise ValueError(f"{label} must be an absolute environment path")
    if ".." in value.split("/"):
        raise ValueError(f"{label} cannot traverse a parent")
    return PurePosixPath(value).as_posix()


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
        prepare_result = await environment.ensure_dirs(
            [workdir],
            chmod=False,
            **(
                {"virtual_workdir": True}
                if isinstance(environment, HostEnvironment)
                else {}
            ),
        )
        if prepare_result is not None and prepare_result.return_code != 0:
            diagnostic = (
                prepare_result.stderr or prepare_result.stdout or "no output"
            ).strip()
            raise RuntimeError(
                "external harness could not prepare workdir "
                f"{workdir!r}: {diagnostic[-2000:]}"
            )
        execution_logs = (
            environment.runtime_directory(f"harness-{uuid4().hex}")
            if isinstance(environment, HostEnvironment)
            else None
        )
        runtime_config_path = self.logs_dir / "peval.json"
        write_effective_runtime_config(
            runtime_config_path,
            EffectiveRuntimeConfig(
                paths=RuntimePaths(
                    workdir=workdir,
                    tests=environment_paths.tests_dir.as_posix(),
                    agent_logs=(
                        str(execution_logs)
                        if execution_logs is not None
                        else environment_paths.agent_dir.as_posix()
                    ),
                    verifier_logs=environment_paths.verifier_dir.as_posix(),
                    artifacts=environment_paths.artifacts_dir.as_posix(),
                ),
                harness=HarnessInvocation(action=action),
            ),
        )
        virtual_instruction = environment_paths.agent_dir / "instruction.txt"
        virtual_runtime_config = environment_paths.agent_dir / "peval.json"
        if execution_logs is not None:
            await environment.upload_dir(self.logs_dir, str(execution_logs))
            (execution_logs / "peval.json").unlink(missing_ok=True)
            virtual_instruction = execution_logs / "instruction.txt"
        invocation_error: BaseException | None = None
        result = None
        try:
            result = await environment.exec(
                f"{self.command} < {quote_shell_arg(virtual_instruction, environment.os)}",
                cwd=workdir,
                env={PEVAL_CONFIG_ENV: virtual_runtime_config.as_posix()},
            )
        except BaseException as exc:
            invocation_error = exc
            raise
        finally:
            try:
                if execution_logs is not None:
                    # Host command cancellation first stops the process tree, then
                    # collects state (including SQLite WAL files) for exact resume.
                    try:
                        await environment.download_dir(
                            str(execution_logs), self.logs_dir
                        )
                    except BaseException as exc:
                        if invocation_error is None:
                            raise
                        invocation_error.add_note(
                            f"harness state collection failed: {exc}"
                        )
            finally:
                if result is not None:
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
        try:
            trajectory = load_validated_trajectory(trajectory_path)
        except ValueError as exc:
            raise RuntimeError(f"external harness wrote invalid ATIF: {exc}") from exc
        populate_context_from_trajectory(context, trajectory)
        context.metadata = {
            "harness_action": action,
            "harness_return_code": result.return_code,
            "trajectory": str(trajectory_path),
            "workdir": workdir,
        }
