from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import pytest
from harbor.models.task.config import EnvironmentConfig, NetworkMode, NetworkPolicy
from harbor.models.trial.paths import TrialPaths

from psycheval.harbor.environment import HostEnvironment


def make_environment(
    tmp_path: Path,
    *,
    allow: object = True,
    config: EnvironmentConfig | None = None,
    extra_mounts: list[dict] | None = None,
) -> HostEnvironment:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    (environment_dir / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    trial_paths = TrialPaths(tmp_path / "trial")
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
        allow_host_execution=allow,
    )


def test_requires_explicit_host_execution_opt_in(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="allow_host_execution=true"):
        make_environment(tmp_path, allow=False)


def test_rejects_resource_requests(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot enforce Task resources: cpus"):
        make_environment(tmp_path, config=EnvironmentConfig(workdir="/app", cpus=2))


def test_rejects_network_policy_it_cannot_enforce(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="network_mode='no-network'"):
        environment_dir = tmp_path / "task" / "environment"
        environment_dir.mkdir(parents=True)
        paths = TrialPaths(tmp_path / "trial")
        paths.mkdir()
        HostEnvironment(
            environment_dir=environment_dir,
            environment_name="test",
            session_id="test-env",
            trial_paths=paths,
            task_env_config=EnvironmentConfig(workdir="/app"),
            logger=logging.getLogger("test"),
            network_policy=NetworkPolicy(network_mode=NetworkMode.NO_NETWORK),
            allow_host_execution=True,
        )


def test_rejects_force_build(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        with pytest.raises(ValueError, match="does not build Docker images"):
            await environment.start(force_build=True)

    asyncio.run(scenario())


def test_exec_translates_paths_and_sets_portable_environment(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            source = tmp_path / "source.txt"
            source.write_text("fixture", encoding="utf-8")
            await environment.upload_file(source, "/tests/source.txt")
            result = await environment.exec(
                "printf '%s|%s|' \"$PSYCHEVAL_WORKDIR\" "
                '"$PSYCHEVAL_TESTS_DIR"; cat /tests/source.txt',
                env={"CALL_ENV": "present"},
            )
            assert result.return_code == 0
            workdir, tests_dir, payload = (result.stdout or "").split("|", 2)
            assert workdir.startswith("/tmp/psycheval-harbor-")
            assert tests_dir.startswith("/tmp/psycheval-harbor-")
            assert payload == "fixture"
            url_result = await environment.exec("printf '%s' 'https://example.com/app'")
            assert url_result.stdout == "https://example.com/app"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_host_subprocess_uses_the_isolated_test_environment(tmp_path: Path) -> None:
    assert os.environ["HARBOR_TELEMETRY"] == "0"
    assert Path(os.environ["HOME"]).is_relative_to(tmp_path)
    assert Path(os.environ["XDG_CONFIG_HOME"]).is_relative_to(tmp_path)
    assert "OPENAI_API_KEY" not in os.environ
    assert "PEVAL_FIXTURE_API_TOKEN" not in os.environ

    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            result = await environment.exec(
                "printf '%s|%s|%s|%s' \"$HARBOR_TELEMETRY\" "
                '"$XDG_CONFIG_HOME" "${OPENAI_API_KEY-unset}" '
                '"${PEVAL_FIXTURE_API_TOKEN-unset}"'
            )
            telemetry, config_home, api_key, api_token = (result.stdout or "").split(
                "|", 3
            )
            assert telemetry == "0"
            assert Path(config_home).is_relative_to(tmp_path)
            assert api_key == "unset"
            assert api_token == "unset"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_exec_preserves_shell_paths_when_trial_path_contains_spaces(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path / "jobs with spaces")
        await environment.start(force_build=False)
        try:
            instruction = environment.trial_paths.agent_dir / "instruction.txt"
            instruction.write_text("exact payload", encoding="utf-8")
            result = await environment.exec(
                "read -r value < '/logs/agent/instruction.txt'; "
                'printf %s "$value" > /logs/verifier/result.txt'
            )
            assert result.return_code == 0
            assert result.stderr == ""
            assert (environment.trial_paths.verifier_dir / "result.txt").read_text(
                encoding="utf-8"
            ) == "exact payload"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_rejects_duplicate_managed_mount_target(tmp_path: Path) -> None:
    substituted = tmp_path / "substituted-agent-logs"
    substituted.mkdir()
    with pytest.raises(ValueError, match="duplicate mount target"):
        make_environment(
            tmp_path,
            extra_mounts=[
                {
                    "type": "bind",
                    "source": str(substituted),
                    "target": "/logs/agent",
                }
            ],
        )


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ({"source": "wrong"}, "source"),
        ({"type": "volume"}, "type"),
        ({"read_only": True}, "writable"),
    ],
)
def test_rejects_mounts_that_do_not_match_harbor_trial_ownership(
    tmp_path: Path, replacement: dict, message: str
) -> None:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    trial_paths = TrialPaths(tmp_path / "trial")
    trial_paths.mkdir()
    mount = {
        "type": "bind",
        "source": str(trial_paths.agent_dir),
        "target": "/logs/agent",
    }
    mount.update(replacement)
    with pytest.raises(ValueError, match=message):
        HostEnvironment(
            environment_dir=environment_dir,
            environment_name="test",
            session_id="test-env",
            trial_paths=trial_paths,
            task_env_config=EnvironmentConfig(workdir="/app"),
            logger=logging.getLogger("test"),
            mounts=[mount],
            allow_host_execution=True,
        )


def test_timeout_terminates_the_process_group(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        marker = tmp_path / "late-marker"
        try:
            with pytest.raises(asyncio.TimeoutError):
                await environment.exec(
                    f"(sleep 0.4; touch {marker}) & wait", timeout_sec=0.05
                )
            await asyncio.sleep(0.5)
            assert not marker.exists()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_rejects_user_switching(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            with pytest.raises(ValueError, match="cannot switch"):
                await environment.exec("true", user=os.getuid() + 10000)
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())
