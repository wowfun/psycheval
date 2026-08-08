from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import pytest
from harbor.models.agent.context import AgentContext
from harbor.models.task.config import EnvironmentConfig
from harbor.models.trial.paths import TrialPaths
from harbor.utils.trajectory_validator import TrajectoryValidator

from psycheval.harbor.agent import ExternalHarnessAgent
from psycheval.harbor.environment import HostEnvironment


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
