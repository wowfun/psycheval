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
from harbor.utils.trajectory_validator import TrajectoryValidator

from psycheval.harbor.agent import ExternalHarnessAgent
from psycheval.harbor.canned_harness import _trajectory
from psycheval.harbor.environment import HostEnvironment

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
                f"{sys.executable} -m psycheval.harbor.canned_harness "
                "--scenario web-search"
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
                command=("printf '{}' > \"$PSYCHEVAL_AGENT_LOGS_DIR/trajectory.json\""),
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
        assert environment.command == (
            r"fixture-harness < C:\logs\agent\instruction.txt"
        )

    asyncio.run(scenario())


class _RecordingWindowsEnvironment:
    os = TaskOS.WINDOWS

    def __init__(self, logs_dir: Path, artifacts_dir: Path) -> None:
        self.logs_dir = logs_dir
        self.artifacts_dir = artifacts_dir
        self.command: str | None = None
        self.cwd: str | None = None

    async def exec(self, command: str, cwd: str | None = None, **_kwargs) -> ExecResult:
        self.command = command
        self.cwd = cwd
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        (self.logs_dir / "trajectory.json").write_text(
            json.dumps(
                _trajectory(
                    "web-search", "Find the example domains", self.artifacts_dir
                )
            ),
            encoding="utf-8",
        )
        return ExecResult(stdout="", stderr="", return_code=0)
