from __future__ import annotations

import asyncio
import json
import logging
import platform
import sys
from pathlib import Path

import pytest
from harbor.environments.base import ExecResult
from harbor.models.agent.context import AgentContext
from harbor.models.task.config import EnvironmentConfig, TaskOS
from harbor.models.trial.paths import EnvironmentPaths, TrialPaths
from harbor.utils.scripts import quote_shell_arg
from harbor.utils.trajectory_validator import TrajectoryValidator

from psycheval.harbor.agent import ExternalHarnessAgent
from psycheval.harbor.environment import HostEnvironment
from psycheval.harbor.runtime_config import (
    HARNESS_PROTOCOL_VERSION,
    PEVAL_CONFIG_ENV,
    load_effective_runtime_config,
)
from tests.fixtures import load_pbench_trajectory

_SYNTHETIC_HARNESS = (
    Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_harness.py"
)
_WEB_SEARCH_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "pbench" / "web-search-01"
)

_LINUX_ONLY = pytest.mark.skipif(
    platform.system() != "Linux", reason="test exercises Bash harness commands"
)


@_LINUX_ONLY
def test_external_agent_runs_harness_and_validates_atif(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment_dir = tmp_path / "environment"
        environment_dir.mkdir()
        (environment_dir / "Dockerfile").write_text("FROM scratch\n")
        paths = TrialPaths(tmp_path / "trial with spaces")
        paths.mkdir()
        artifact_mount = paths.artifacts_dir / "logs" / "artifacts"
        artifact_mount.mkdir(parents=True)
        environment = HostEnvironment(
            environment_dir=environment_dir,
            environment_name="agent-test",
            session_id="agent-test-env",
            trial_paths=paths,
            task_env_config=EnvironmentConfig(workdir="/app"),
            logger=logging.getLogger("test"),
            mounts=[
                {
                    "type": "bind",
                    "source": str(paths.agent_dir),
                    "target": "/logs/agent",
                },
                {
                    "type": "bind",
                    "source": str(paths.verifier_dir),
                    "target": "/logs/verifier",
                },
                {
                    "type": "bind",
                    "source": str(artifact_mount),
                    "target": "/logs/artifacts",
                },
            ],
            allow_host_execution=True,
        )
        agent = ExternalHarnessAgent(
            logs_dir=paths.agent_dir,
            command=(
                f"{quote_shell_arg(sys.executable, TaskOS.LINUX)} "
                f"{quote_shell_arg(str(_SYNTHETIC_HARNESS), TaskOS.LINUX)} "
                "--mode single-step"
            ),
        )
        await environment.start(force_build=False)
        try:
            context = AgentContext()
            await agent.run("Find the example domains", environment, context)
            assert TrajectoryValidator().validate(paths.agent_dir / "trajectory.json")
            assert context.metadata is not None
            assert context.metadata["harness_return_code"] == 0
            invalid_agent = ExternalHarnessAgent(
                logs_dir=paths.agent_dir,
                command=("printf '{}' > /logs/agent/trajectory.json"),
            )
            with pytest.raises(RuntimeError, match="invalid ATIF"):
                await invalid_agent.run(
                    "Write invalid ATIF", environment, AgentContext()
                )
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_external_agent_declares_and_uses_windows_paths(tmp_path: Path) -> None:
    async def scenario() -> None:
        logs_dir = tmp_path / "agent logs"
        artifacts_dir = tmp_path / "artifacts"
        environment = _RecordingWindowsEnvironment(logs_dir, artifacts_dir)
        agent = ExternalHarnessAgent(logs_dir=logs_dir, command="fixture-harness")

        await agent.run("Find the example domains", environment, AgentContext())

        paths = EnvironmentPaths.for_os(TaskOS.WINDOWS)
        assert ExternalHarnessAgent.SUPPORTS_WINDOWS is True
        assert environment.cwd == (paths.logs_dir.parent / "app").as_posix()
        assert environment.prepared_dirs == ["C:/app"]
        assert environment.workdirs == ["C:/app"]
        assert environment.command == (
            r"fixture-harness < C:\logs\agent\instruction.txt"
        )

    asyncio.run(scenario())


def test_external_agent_exposes_fresh_and_resume_actions(tmp_path: Path) -> None:
    async def scenario() -> None:
        logs_dir = tmp_path / "agent logs"
        artifacts_dir = tmp_path / "artifacts"
        environment = _RecordingWindowsEnvironment(logs_dir, artifacts_dir)
        agent = ExternalHarnessAgent(logs_dir=logs_dir, command="fixture-harness")

        await agent.run("Start the task", environment, AgentContext())
        await agent.resume("Continue the task", environment, AgentContext())

        assert agent.SUPPORTS_RESUME is True
        assert agent.SUPPORTS_LOAD_NATIVE_TRAJECTORY is False
        assert agent.SUPPORTS_LOAD_ATIF_TRAJECTORY is False
        assert environment.actions == ["run", "resume"]
        assert environment.protocol_versions == [
            HARNESS_PROTOCOL_VERSION,
            HARNESS_PROTOCOL_VERSION,
        ]

    asyncio.run(scenario())


def test_external_agent_workdir_override_precedes_task_config(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = _RecordingWindowsEnvironment(
            tmp_path / "agent logs",
            tmp_path / "artifacts",
            task_workdir="C:/task-workdir",
        )
        agent = ExternalHarnessAgent(
            logs_dir=environment.logs_dir,
            command="fixture-harness",
            workdir="/workspace/nested",
        )
        context = AgentContext()

        await agent.run("Use the workspace", environment, context)

        assert environment.prepared_dirs == ["C:/workspace/nested"]
        assert environment.cwd == "C:/workspace/nested"
        assert environment.workdirs == ["C:/workspace/nested"]
        assert context.metadata is not None
        assert context.metadata["workdir"] == "C:/workspace/nested"

    asyncio.run(scenario())


def test_external_agent_uses_task_workdir_when_not_overridden(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = _RecordingWindowsEnvironment(
            tmp_path / "agent logs",
            tmp_path / "artifacts",
            task_workdir="/task workspace",
        )
        agent = ExternalHarnessAgent(
            logs_dir=environment.logs_dir, command="fixture-harness"
        )

        await agent.run("Use the task workdir", environment, AgentContext())

        assert environment.cwd == "C:/task workspace"
        assert environment.workdirs == ["C:/task workspace"]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "workdir", ["relative", "/workspace/../other", "D:relative", "D:/workspace"]
)
def test_external_agent_rejects_invalid_workdir(tmp_path: Path, workdir: str) -> None:
    async def scenario() -> None:
        environment = _RecordingWindowsEnvironment(
            tmp_path / "agent logs", tmp_path / "artifacts"
        )
        agent = ExternalHarnessAgent(
            logs_dir=environment.logs_dir,
            command="fixture-harness",
            workdir=workdir,
        )

        with pytest.raises(ValueError, match="workdir"):
            await agent.run("Use invalid workdir", environment, AgentContext())

        assert environment.command is None

    asyncio.run(scenario())


@pytest.mark.parametrize("workdir", ["", "   "])
def test_external_agent_rejects_empty_workdir(tmp_path: Path, workdir: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        ExternalHarnessAgent(
            logs_dir=tmp_path / "agent", command="fixture-harness", workdir=workdir
        )


def test_external_agent_fails_when_workdir_cannot_be_prepared(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = _RecordingWindowsEnvironment(
            tmp_path / "agent logs", tmp_path / "artifacts"
        )
        environment.prepare_return_code = 1
        agent = ExternalHarnessAgent(
            logs_dir=environment.logs_dir,
            command="fixture-harness",
            workdir="/workspace",
        )

        with pytest.raises(RuntimeError, match="could not prepare workdir"):
            await agent.run("Use the workspace", environment, AgentContext())

        assert environment.command is None

    asyncio.run(scenario())


def test_external_agent_does_not_reuse_previous_step_trajectory(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        logs_dir = tmp_path / "agent logs"
        environment = _RecordingWindowsEnvironment(logs_dir, tmp_path / "artifacts")
        agent = ExternalHarnessAgent(logs_dir=logs_dir, command="fixture-harness")

        await agent.run("Start the task", environment, AgentContext())
        environment.write_trajectory = False

        with pytest.raises(RuntimeError, match="did not write"):
            await agent.resume("Continue the task", environment, AgentContext())

        assert not (logs_dir / "trajectory.json").exists()

    asyncio.run(scenario())


class _RecordingWindowsEnvironment:
    os = TaskOS.WINDOWS

    def __init__(
        self,
        logs_dir: Path,
        artifacts_dir: Path,
        *,
        task_workdir: str | None = None,
    ) -> None:
        self.logs_dir = logs_dir
        self.artifacts_dir = artifacts_dir
        self.task_env_config = EnvironmentConfig(workdir=task_workdir)
        self.command: str | None = None
        self.cwd: str | None = None
        self.actions: list[str] = []
        self.protocol_versions: list[int] = []
        self.prepared_dirs: list[str] = []
        self.workdirs: list[str] = []
        self.prepare_return_code = 0
        self.write_trajectory = True

    async def ensure_dirs(self, dirs: list[str], *, chmod: bool = True) -> ExecResult:
        self.prepared_dirs.extend(dirs)
        return ExecResult(
            stdout="", stderr="cannot create", return_code=self.prepare_return_code
        )

    async def exec(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        **_kwargs,
    ) -> ExecResult:
        self.command = command
        self.cwd = cwd
        if env is not None:
            assert set(env) == {PEVAL_CONFIG_ENV}
            runtime = load_effective_runtime_config(
                self.logs_dir / "peval.json", require_harness=True
            )
            self.actions.append(runtime.harness.action)
            self.protocol_versions.append(runtime.harness.protocol_version)
            self.workdirs.append(runtime.paths.workdir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        if self.write_trajectory:
            (self.logs_dir / "trajectory.json").write_text(
                json.dumps(
                    load_pbench_trajectory(
                        _WEB_SEARCH_FIXTURE,
                        "Find the example domains",
                        self.artifacts_dir,
                    )
                ),
                encoding="utf-8",
            )
        return ExecResult(stdout="", stderr="", return_code=0)
