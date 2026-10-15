"""Isolated native Host environment construction for Harbor tests."""

from __future__ import annotations

import logging
from pathlib import Path

from harbor.models.task.config import EnvironmentConfig
from harbor.models.trial.paths import TrialPaths

from psycheval.harbor.environment import HostEnvironment


def make_environment(
    tmp_path: Path,
    *,
    host_access: object | None = None,
    config: EnvironmentConfig | None = None,
    extra_mounts: list[dict] | None = None,
    trial_name: str = "trial",
    environment_kwargs: dict[str, object] | None = None,
) -> HostEnvironment:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    (environment_dir / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (environment_dir / "data").mkdir()
    trial_paths = TrialPaths(tmp_path / trial_name)
    trial_paths.mkdir()
    artifact_mount = trial_paths.artifacts_dir / "logs" / "artifacts"
    artifact_mount.mkdir(parents=True)
    mounts = [
        {"type": "bind", "source": str(trial_paths.agent_dir), "target": "/logs/agent"},
        {
            "type": "bind",
            "source": str(trial_paths.verifier_dir),
            "target": "/logs/verifier",
        },
        {"type": "bind", "source": str(artifact_mount), "target": "/logs/artifacts"},
    ]
    mounts.extend(extra_mounts or [])
    return HostEnvironment(
        environment_dir=environment_dir,
        environment_name="test",
        session_id="test-env",
        trial_paths=trial_paths,
        task_env_config=config or EnvironmentConfig(workdir="/app"),
        logger=logging.getLogger("test"),
        mounts=mounts,
        host_access=(
            host_access
            if host_access is not None
            else {"filesystem": True, "process": True}
        ),
        **(environment_kwargs or {}),
    )


def make_separate_verifier_environment(tmp_path: Path) -> HostEnvironment:
    environment_dir = tmp_path / "task" / "steps" / "continue" / "tests"
    environment_dir.mkdir(parents=True)
    (environment_dir / "test.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    trial_paths = TrialPaths(tmp_path / "trial")
    trial_paths.mkdir()
    return HostEnvironment(
        environment_dir=environment_dir,
        environment_name="test-verifier",
        session_id="test-verifier-env",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(workdir="/app"),
        logger=logging.getLogger("test"),
        mounts=[
            {
                "type": "bind",
                "source": str(trial_paths.verifier_dir),
                "target": "/logs/verifier",
            }
        ],
        host_access={"filesystem": True, "process": True},
    )
