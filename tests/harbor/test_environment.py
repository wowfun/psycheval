from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import platform
import shlex
import sys
import tarfile
from pathlib import Path

import pytest
from harbor.models.task.config import (
    EnvironmentConfig,
    NetworkMode,
    NetworkPolicy,
    TaskOS,
)
from harbor.models.trial.paths import TrialPaths
from harbor.utils.scripts import quote_windows_shell_arg

from psycheval.harbor.environment import HostEnvironment

_LINUX_ONLY = pytest.mark.skipif(
    platform.system() != "Linux", reason="test exercises the Linux process adapter"
)


def make_environment(
    tmp_path: Path,
    *,
    allow: object = True,
    config: EnvironmentConfig | None = None,
    extra_mounts: list[dict] | None = None,
    trial_name: str = "trial",
    environment_kwargs: dict[str, object] | None = None,
) -> HostEnvironment:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    (environment_dir / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
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
        allow_host_execution=allow,
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
        allow_host_execution=True,
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


def test_rejects_workdir_root_environment_kwarg(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="configured through PEVAL_CONFIG"):
        make_environment(
            tmp_path,
            environment_kwargs={"workdir_root": str(tmp_path / "workspaces")},
        )


@_LINUX_ONLY
def test_automatic_workspace_reuses_trial_short_uuid_and_obeys_delete(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path, trial_name="task__YfQLWrD")
        await environment.start(force_build=False)
        result = await environment.exec('printf "%s|%s" "$PWD" "$PEVAL_CONFIG"')
        cwd, config_path_value = (result.stdout or "").split("|", 1)
        workspace = Path(cwd)
        config_path = Path(config_path_value)
        assert workspace == Path(os.environ["HOME"]) / "workspaces" / "YfQLWrD"
        assert (workspace / "Dockerfile").is_file()
        assert config_path.is_file()

        await environment.stop(delete=False)
        assert workspace.is_dir()
        assert config_path.is_file()
        await environment.stop(delete=True)
        assert not workspace.exists()
        assert not config_path.exists()
        assert workspace.parent.is_dir()

    asyncio.run(scenario())


def test_owned_runtime_cleanup_attempts_every_root_after_one_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = make_environment(tmp_path)
    workspace = tmp_path / "owned-workspace"
    runtime_root = tmp_path / "owned-runtime"
    workspace.mkdir()
    runtime_root.mkdir()
    environment._automatic_workspace = workspace
    environment._runtime_root = runtime_root
    attempted: list[Path] = []

    def fake_rmtree(path: Path, *, ignore_errors: bool) -> None:
        assert ignore_errors is False
        candidate = Path(path)
        attempted.append(candidate)
        if candidate == workspace:
            raise OSError("workspace is busy")

    monkeypatch.setattr("psycheval.harbor.environment.shutil.rmtree", fake_rmtree)

    with pytest.raises(OSError, match="workspace is busy"):
        environment._delete_owned_runtime()

    assert attempted == [workspace, runtime_root]


@_LINUX_ONLY
def test_automatic_workspace_rejects_existing_trial_directory(tmp_path: Path) -> None:
    workspace = Path(os.environ["HOME"]) / "workspaces" / "YfQLWrD"
    workspace.mkdir(parents=True)
    (workspace / "keep.txt").write_text("keep\n", encoding="utf-8")
    environment = make_environment(tmp_path, trial_name="task__YfQLWrD")

    async def scenario() -> None:
        with pytest.raises(FileExistsError, match="refusing to reuse stale state"):
            await environment.start(force_build=False)

    asyncio.run(scenario())
    assert (workspace / "keep.txt").read_text(encoding="utf-8") == "keep\n"


@_LINUX_ONLY
def test_automatic_workspace_generates_short_uuid_for_explicit_trial_name(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path, trial_name="explicit-name")
        await environment.start(force_build=False)
        try:
            result = await environment.exec("pwd")
            workspace = Path((result.stdout or "").strip())
            assert workspace.parent == Path(os.environ["HOME"]) / "workspaces"
            assert len(workspace.name) == 7
            assert workspace.name != "explicit-name"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_start_failure_removes_owned_automatic_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = make_environment(tmp_path, trial_name="task__YfQLWrD")

    def fail_copy(*_args, **_kwargs) -> None:
        raise OSError("fixture copy failed")

    monkeypatch.setattr("psycheval.harbor.environment.shutil.copytree", fail_copy)

    async def scenario() -> None:
        with pytest.raises(OSError, match="fixture copy failed"):
            await environment.start(force_build=False)

    asyncio.run(scenario())
    assert not (Path(os.environ["HOME"]) / "workspaces" / "YfQLWrD").exists()


@_LINUX_ONLY
def test_workbuddy_bootstrap_safely_expands_workspace_and_creates_git_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    environment_dir.joinpath("Dockerfile").write_text("FROM python:3.12-slim\n")
    environment_dir.joinpath("docker-compose.yaml").write_text(
        "services:\n  main:\n    extra_hosts:\n      - host.docker.internal:host-gateway\n"
    )
    source = tmp_path / "source"
    (source / "input" / "workspace").mkdir(parents=True)
    (source / "input" / "workspace" / "brief.txt").write_text("fixture\n")
    with tarfile.open(environment_dir / "workspace.tar.gz", "w:gz") as stream:
        stream.add(source / "input", arcname="input")
    real_open = os.open
    archive_flags: list[int] = []

    def recording_open(
        path: str | bytes | os.PathLike[str],
        flags: int,
        *args: object,
        **kwargs: object,
    ) -> int:
        if Path(path) == environment_dir / "workspace.tar.gz":
            archive_flags.append(flags)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr("psycheval.harbor.environment.os.open", recording_open)
    hook_dir = tmp_path / "inherited-hooks"
    hook_dir.mkdir()
    hook_marker = tmp_path / "hook-ran"
    hook = hook_dir / "post-commit"
    hook.write_text(
        f"#!/bin/sh\ntouch {shlex.quote(str(hook_marker))}\n", encoding="utf-8"
    )
    hook.chmod(0o755)
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.hooksPath")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(hook_dir))
    trial_paths = TrialPaths(tmp_path / "office__YfQLWrD")
    trial_paths.mkdir()
    environment = HostEnvironment(
        environment_dir=environment_dir,
        environment_name="test",
        session_id="test-env",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(workdir=None),
        logger=logging.getLogger("test"),
        mounts=[],
        allow_host_execution=True,
        bootstrap_workbuddy_workspace=True,
    )

    async def scenario() -> None:
        await environment.start(force_build=False)
        try:
            result = await environment.exec(
                "test -f input/workspace/brief.txt && "
                "test -f /workspace/input/workspace/brief.txt && "
                "test ! -e Dockerfile && git status --porcelain && pwd"
            )
            assert result.return_code == 0
            assert (result.stdout or "").strip() == str(
                Path(os.environ["HOME"]) / "workspaces" / "YfQLWrD"
            )
            assert not hook_marker.exists()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())
    if getattr(os, "O_NONBLOCK", 0):
        assert archive_flags
        assert all(flags & os.O_NONBLOCK for flags in archive_flags)


def test_workbuddy_bootstrap_rejects_non_metadata_compose(tmp_path: Path) -> None:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    (environment_dir / "docker-compose.yaml").write_text(
        "services:\n  database:\n    image: postgres\n"
    )
    trial_paths = TrialPaths(tmp_path / "trial")
    trial_paths.mkdir()
    with pytest.raises(ValueError, match="WorkBuddy Compose metadata"):
        HostEnvironment(
            environment_dir=environment_dir,
            environment_name="test",
            session_id="test-env",
            trial_paths=trial_paths,
            task_env_config=EnvironmentConfig(),
            logger=logging.getLogger("test"),
            mounts=[],
            allow_host_execution=True,
            bootstrap_workbuddy_workspace=True,
        )


def test_workbuddy_bootstrap_accepts_semantically_identical_compose(
    tmp_path: Path,
) -> None:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    (environment_dir / "docker-compose.yaml").write_text(
        "# WorkBuddy's inert compatibility metadata.\n"
        "services:\n"
        "  main:\n"
        "    extra_hosts: [host.docker.internal:host-gateway]\n",
        encoding="utf-8",
    )
    with tarfile.open(environment_dir / "workspace.tar.gz", "w:gz"):
        pass
    trial_paths = TrialPaths(tmp_path / "trial")
    trial_paths.mkdir()

    HostEnvironment(
        environment_dir=environment_dir,
        environment_name="test",
        session_id="test-env",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(),
        logger=logging.getLogger("test"),
        mounts=[],
        allow_host_execution=True,
        bootstrap_workbuddy_workspace=True,
    )


def test_workbuddy_bootstrap_rejects_oversized_compose_metadata(
    tmp_path: Path,
) -> None:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    (environment_dir / "docker-compose.yaml").write_bytes(b"#" * (64 * 1024 + 1))
    with tarfile.open(environment_dir / "workspace.tar.gz", "w:gz"):
        pass
    trial_paths = TrialPaths(tmp_path / "trial")
    trial_paths.mkdir()

    with pytest.raises(ValueError, match="Compose metadata is not readable"):
        HostEnvironment(
            environment_dir=environment_dir,
            environment_name="test",
            session_id="test-env",
            trial_paths=trial_paths,
            task_env_config=EnvironmentConfig(),
            logger=logging.getLogger("test"),
            mounts=[],
            allow_host_execution=True,
            bootstrap_workbuddy_workspace=True,
        )


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks are unavailable")
def test_workbuddy_bootstrap_does_not_follow_replaced_archive(
    tmp_path: Path,
) -> None:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    (environment_dir / "docker-compose.yaml").write_text(
        "services:\n  main:\n    extra_hosts:\n"
        "      - host.docker.internal:host-gateway\n"
    )
    archive = environment_dir / "workspace.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        info = tarfile.TarInfo("input/initial.txt")
        info.size = 0
        stream.addfile(info, io.BytesIO())
    trial_paths = TrialPaths(tmp_path / "replaced__YfQLWrD")
    trial_paths.mkdir()
    environment = HostEnvironment(
        environment_dir=environment_dir,
        environment_name="test",
        session_id="test-env",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(workdir=None),
        logger=logging.getLogger("test"),
        mounts=[],
        allow_host_execution=True,
        bootstrap_workbuddy_workspace=True,
    )
    replacement = tmp_path / "replacement.tar.gz"
    with tarfile.open(replacement, "w:gz") as stream:
        info = tarfile.TarInfo("input/replacement.txt")
        info.size = 0
        stream.addfile(info, io.BytesIO())
    archive.unlink()
    archive.symlink_to(replacement)

    async def scenario() -> None:
        with pytest.raises(ValueError, match="archive cannot be extracted"):
            await environment.start(force_build=False)

    asyncio.run(scenario())


@pytest.mark.parametrize("member_name", ("../escape.txt", ".git/config"))
def test_workbuddy_bootstrap_rejects_unsafe_workspace_archive_paths(
    tmp_path: Path, member_name: str
) -> None:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    (environment_dir / "docker-compose.yaml").write_text(
        "services:\n  main:\n    extra_hosts:\n"
        "      - host.docker.internal:host-gateway\n"
    )
    payload = b"private\n"
    info = tarfile.TarInfo(member_name)
    info.size = len(payload)
    with tarfile.open(environment_dir / "workspace.tar.gz", "w:gz") as stream:
        stream.addfile(info, io.BytesIO(payload))
    trial_paths = TrialPaths(tmp_path / "unsafe__YfQLWrD")
    trial_paths.mkdir()
    environment = HostEnvironment(
        environment_dir=environment_dir,
        environment_name="test",
        session_id="test-env",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(workdir=None),
        logger=logging.getLogger("test"),
        mounts=[],
        allow_host_execution=True,
        bootstrap_workbuddy_workspace=True,
    )

    async def scenario() -> None:
        with pytest.raises(ValueError, match="archive path is unsafe"):
            await environment.start(force_build=False)

    asyncio.run(scenario())
    assert not (tmp_path / "escape.txt").exists()


@_LINUX_ONLY
@pytest.mark.parametrize(
    ("payloads", "expected_error"),
    (
        ((b"same\n", b"same\n"), None),
        ((b"first\n", b"second\n"), "conflicting duplicate"),
    ),
)
def test_workbuddy_bootstrap_handles_duplicate_workspace_archive_paths(
    tmp_path: Path,
    payloads: tuple[bytes, bytes],
    expected_error: str | None,
) -> None:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    (environment_dir / "docker-compose.yaml").write_text(
        "services:\n  main:\n    extra_hosts:\n"
        "      - host.docker.internal:host-gateway\n"
    )
    with tarfile.open(environment_dir / "workspace.tar.gz", "w:gz") as stream:
        for payload in payloads:
            info = tarfile.TarInfo("input/workspace/brief.txt")
            info.mode = 0o644
            info.size = len(payload)
            stream.addfile(info, io.BytesIO(payload))
    trial_paths = TrialPaths(tmp_path / "duplicate__YfQLWrD")
    trial_paths.mkdir()
    environment = HostEnvironment(
        environment_dir=environment_dir,
        environment_name="test",
        session_id="test-env",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(workdir=None),
        logger=logging.getLogger("test"),
        mounts=[],
        allow_host_execution=True,
        bootstrap_workbuddy_workspace=True,
    )

    async def scenario() -> None:
        if expected_error is not None:
            with pytest.raises(ValueError, match=expected_error):
                await environment.start(force_build=False)
            return
        await environment.start(force_build=False)
        try:
            result = await environment.exec("cat input/workspace/brief.txt")
            assert result.return_code == 0
            assert result.stdout == "same\n"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_empty_configured_root_restores_trial_temporary_workdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "peval.toml"
    config.write_text('[harbor.host]\nworkdir_root = ""\n', encoding="utf-8")
    original = config.read_bytes()
    monkeypatch.setenv("PEVAL_CONFIG", str(config))

    async def scenario() -> None:
        environment = make_environment(tmp_path / "case")
        await environment.start(force_build=False)
        try:
            result = await environment.exec("pwd")
            assert (result.stdout or "").strip().startswith("/tmp/psycheval-harbor-")
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())
    assert config.read_bytes() == original


@_LINUX_ONLY
def test_separate_verifier_isolates_uploaded_agent_logs_and_artifacts(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_separate_verifier_environment(tmp_path)
        source_agent = tmp_path / "source-agent"
        source_artifacts = tmp_path / "source-artifacts"
        source_agent.mkdir()
        source_artifacts.mkdir()
        (source_agent / "trajectory.json").write_text("{}\n", encoding="utf-8")
        (source_artifacts / "current.txt").write_text("current\n", encoding="utf-8")
        await environment.start(force_build=False)
        try:
            await environment.upload_dir(source_agent, "/logs/agent")
            await environment.upload_dir(source_artifacts, "/logs/artifacts")

            assert (source_agent / "trajectory.json").is_file()
            assert (source_artifacts / "current.txt").is_file()
            result = await environment.exec(
                "test -f /tests/test.sh && "
                "test -f /logs/agent/trajectory.json && "
                "test -f /logs/artifacts/current.txt && pwd"
            )
            assert result.return_code == 0
            assert not Path((result.stdout or "").strip()).is_relative_to(
                Path(os.environ["HOME"]) / "workspaces"
            )
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_exec_translates_paths_and_sets_effective_runtime_config(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path, trial_name="task__YfQLWrD")
        await environment.start(force_build=False)
        try:
            source = tmp_path / "source.txt"
            source.write_text("fixture", encoding="utf-8")
            await environment.upload_file(source, "/tests/source.txt")
            heredoc = await environment.exec(
                "python - <<'PY'\n"
                "from pathlib import Path\n"
                'print(Path("/tests/source.txt").read_text())\n'
                "PY"
            )
            assert heredoc.return_code == 0
            assert heredoc.stdout == "fixture\n"
            result = await environment.exec(
                "printf '%s|' \"$PEVAL_CONFIG\"; cat /tests/source.txt",
                env={"CALL_ENV": "present", "PSYCHEVAL_LEGACY": "hidden"},
            )
            assert result.return_code == 0
            config_path, payload = (result.stdout or "").split("|", 1)
            assert payload == "fixture"
            runtime = json.loads(Path(config_path).read_text(encoding="utf-8"))
            workspace = Path(os.environ["HOME"]) / "workspaces" / "YfQLWrD"
            assert Path(runtime["paths"]["workdir"]) == workspace
            assert Path(runtime["harbor"]["host"]["workspace"]) == workspace
            assert Path(runtime["paths"]["tests"]).name == "tests"
            assert runtime["executables"]["python"] == sys.executable
            assert "harness" not in runtime["harbor"]
            first_config = Path(config_path)
            second, third = await asyncio.gather(
                environment.exec('printf "%s" "$PEVAL_CONFIG"'),
                environment.exec('printf "%s" "$PEVAL_CONFIG"'),
            )
            generated = {
                first_config,
                Path((second.stdout or "").strip()),
                Path((third.stdout or "").strip()),
            }
            assert len(generated) == 3
            assert all(path.is_file() for path in generated)
            env_result = await environment.exec("env")
            assert "PSYCHEVAL_" not in (env_result.stdout or "")
            assert "PEVAL_CONFIG=" in (env_result.stdout or "")
            url_result = await environment.exec("printf '%s' 'https://example.com/app'")
            assert url_result.stdout == "https://example.com/app"
        finally:
            await environment.stop(delete=True)

        assert not workspace.exists()
        assert workspace.parent.is_dir()

    asyncio.run(scenario())


@_LINUX_ONLY
def test_exec_translates_complete_virtual_paths_in_environment_values(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            result = await environment.exec(
                'mkdir -p "$XDG_DATA_HOME"; printf "%s|%s" '
                '"$XDG_DATA_HOME" "$UNCHANGED"',
                env={
                    "XDG_DATA_HOME": "/logs/agent/opencode/xdg-data",
                    "UNCHANGED": "prefix:/logs/agent",
                },
            )
            assert result.return_code == 0
            data_home, unchanged = (result.stdout or "").split("|", 1)
            assert Path(data_home) == (
                environment.trial_paths.agent_dir / "opencode" / "xdg-data"
            )
            assert Path(data_home).is_dir()
            assert unchanged == "prefix:/logs/agent"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_home_override_does_not_inherit_a_stale_host_nvm_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NVM_DIR", str(tmp_path / "host-home" / ".nvm"))

    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            result = await environment.exec(
                'printf "%s|%s" "$HOME" "${NVM_DIR-unset}"',
                env={"HOME": str(tmp_path / "agent-home")},
            )
            assert result.return_code == 0
            assert result.stdout == f"{tmp_path / 'agent-home'}|unset"

            explicit = await environment.exec(
                'printf "%s" "$NVM_DIR"',
                env={
                    "HOME": str(tmp_path / "agent-home"),
                    "NVM_DIR": "/logs/agent/nvm",
                },
            )
            assert explicit.return_code == 0
            assert Path(explicit.stdout or "") == (
                environment.trial_paths.agent_dir / "nvm"
            )
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_linux_command_translation_preserves_composed_home_paths(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            result = await environment.exec("printf '%s|%s' ~/app ${HOME}/app")
            expected = str(Path(os.environ["HOME"]) / "app")
            assert result.return_code == 0
            assert result.stdout == f"{expected}|{expected}"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_linux_paths_preserve_native_relative_c_and_backslash_names(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            sources = []
            for index, payload in enumerate(
                (
                    "virtual",
                    "relative-c",
                    "slash",
                    "backslash",
                    "virtual-leading",
                    "backslash-leading",
                )
            ):
                source = tmp_path / f"source-{index}.txt"
                source.write_text(payload, encoding="utf-8")
                sources.append(source)
            await environment.upload_file(sources[0], "/app/collision.txt")
            await environment.upload_file(sources[1], "C:/app/collision.txt")
            await environment.upload_file(sources[2], "folder/item.txt")
            await environment.upload_file(sources[3], r"folder\item.txt")
            await environment.upload_file(sources[4], "/app/leading.txt")
            await environment.upload_file(sources[5], r"\app\leading.txt")

            result = await environment.exec(
                "cat /app/collision.txt; printf '|'; "
                "cat 'C:/app/collision.txt'; printf '|'; "
                "cat folder/item.txt; printf '|'; "
                "cat 'folder\\item.txt'; printf '|'; "
                "cat /app/leading.txt; printf '|'; cat '\\app\\leading.txt'"
            )
            assert result.return_code == 0
            assert result.stdout == (
                "virtual|relative-c|slash|backslash|virtual-leading|backslash-leading"
            )
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
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


@_LINUX_ONLY
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


@_LINUX_ONLY
def test_workspace_bind_merges_task_context_and_writes_through(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        workspace = tmp_path / "workspace with spaces"
        workspace.mkdir()
        (workspace / "fixture.txt").write_text("old\n", encoding="utf-8")
        (workspace / "unrelated.txt").write_text("keep\n", encoding="utf-8")
        environment = make_environment(
            tmp_path / "case",
            config=EnvironmentConfig(workdir="/workspace"),
            extra_mounts=[
                {
                    "type": "bind",
                    "source": str(workspace),
                    "target": "/workspace",
                }
            ],
        )
        (environment.environment_dir / "fixture.txt").write_text(
            "task\n", encoding="utf-8"
        )

        await environment.start(force_build=False)
        try:
            await environment.ensure_dirs(["/workspace/nested"], chmod=False)
            result = await environment.exec(
                "printf '%s' \"$WORKSPACE_FILE\" > /workspace/nested/marker.txt; pwd",
                cwd="/workspace/nested",
                env={"WORKSPACE_FILE": "/workspace/nested/payload.txt"},
            )
            assert result.return_code == 0
            assert Path((result.stdout or "").strip()) == workspace / "nested"
            assert (workspace / "nested" / "marker.txt").read_text(
                encoding="utf-8"
            ) == str(workspace / "nested" / "payload.txt")
            assert (workspace / "fixture.txt").read_text(encoding="utf-8") == ("task\n")
            assert (workspace / "unrelated.txt").read_text(encoding="utf-8") == (
                "keep\n"
            )
        finally:
            await environment.stop(delete=True)

        assert (workspace / "nested" / "marker.txt").is_file()
        assert (workspace / "unrelated.txt").is_file()
        assert not (Path(os.environ["HOME"]) / "workspaces").exists()

    asyncio.run(scenario())


@_LINUX_ONLY
def test_unmounted_custom_workdir_uses_automatic_workspace(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = make_environment(
            tmp_path, config=EnvironmentConfig(workdir="/custom/nested")
        )
        (environment.environment_dir / "task-input.txt").write_text(
            "input\n", encoding="utf-8"
        )
        await environment.start(force_build=False)
        resolved: Path | None = None
        try:
            await environment.ensure_dirs(["/custom/nested"], chmod=False)
            result = await environment.exec(
                "test -f task-input.txt && pwd", cwd="/custom/nested"
            )
            assert result.return_code == 0
            resolved = Path((result.stdout or "").strip())
            assert len(resolved.name) == 7
        finally:
            await environment.stop(delete=True)

        assert resolved is not None
        assert not resolved.exists()

    asyncio.run(scenario())


@_LINUX_ONLY
def test_unmounted_agent_workdir_override_uses_automatic_workspace(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path, trial_name="task__YfQLWrD")
        await environment.start(force_build=False)
        try:
            await environment.ensure_dirs(["/agent-selected/path"], chmod=False)
            result = await environment.exec("pwd", cwd="/agent-selected/path")
            assert Path((result.stdout or "").strip()) == (
                Path(os.environ["HOME"]) / "workspaces" / "YfQLWrD"
            )
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_workspace_bind_rejects_workdir_outside_target(tmp_path: Path) -> None:
    async def scenario() -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        environment = make_environment(
            tmp_path / "case",
            extra_mounts=[
                {
                    "type": "bind",
                    "source": str(workspace),
                    "target": "/workspace",
                }
            ],
        )
        await environment.start(force_build=False)
        try:
            with pytest.raises(ValueError, match="workspace mount target"):
                await environment.ensure_dirs(["/other"], chmod=False)
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("mount", "message"),
    [
        (
            {"type": "volume", "source": "workspace", "target": "/workspace"},
            "type='bind'",
        ),
        (
            {
                "type": "bind",
                "source": "workspace",
                "target": "/workspace",
                "read_only": True,
            },
            "writable",
        ),
        (
            {"type": "bind", "source": "missing", "target": "/workspace"},
            "existing directory",
        ),
        (
            {"type": "bind", "source": "workspace", "target": "/logs/cache"},
            "reserved path",
        ),
        (
            {"type": "bind", "source": "workspace", "target": "relative"},
            "non-root absolute",
        ),
        (
            {"type": "bind", "source": "workspace", "target": "/"},
            "non-root absolute",
        ),
    ],
)
def test_rejects_invalid_workspace_mount(
    tmp_path: Path, mount: dict, message: str
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    configured = dict(mount)
    if configured["source"] == "workspace":
        configured["source"] = str(workspace)
    with pytest.raises(ValueError, match=message):
        make_environment(tmp_path / "case", extra_mounts=[configured])


def test_rejects_more_than_one_workspace_mount(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    with pytest.raises(ValueError, match="only one workspace mount"):
        make_environment(
            tmp_path / "case",
            extra_mounts=[
                {"type": "bind", "source": str(first), "target": "/first"},
                {"type": "bind", "source": str(second), "target": "/second"},
            ],
        )


@_LINUX_ONLY
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


@_LINUX_ONLY
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


def test_windows_host_reports_native_os_and_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Windows"
    )

    environment = make_environment(tmp_path)

    assert environment.os == TaskOS.WINDOWS
    assert environment.capabilities.windows is True
    assert environment.capabilities.mounted is True


def test_windows_exec_uses_cmd_and_translates_runtime_aliases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Windows"
    )
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def create_process(*args, **kwargs):
        calls.append((args, kwargs))
        return _CompletedProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)

    async def scenario() -> None:
        environment = make_environment(tmp_path / "jobs with spaces")
        await environment.start(force_build=False)
        try:
            source = tmp_path / "source.txt"
            source.write_text("fixture", encoding="utf-8")
            await environment.upload_file(source, "C:/tests/source.txt")
            result = await environment.exec(
                "type C:/tests/source.txt > C:/logs/verifier/result.txt",
                cwd="C:/app",
                env={"XDG_DATA_HOME": "C:/logs/agent/opencode/xdg-data"},
            )
            assert result.return_code == 0
            assert calls
            args, kwargs = calls[0]
            assert args[:4] == (
                r"C:\Windows\System32\cmd.exe",
                "/D",
                "/S",
                "/C",
            )
            translated = str(args[4])
            assert "C:/tests" not in translated
            assert r"C:\tests" not in translated
            assert "C:/logs" not in translated
            assert r"C:\logs" not in translated
            assert "source.txt" in translated
            assert "result.txt" in translated
            assert '"' in translated
            assert len(Path(kwargs["cwd"]).name) == 7
            assert "creationflags" in kwargs
            assert Path(kwargs["env"]["XDG_DATA_HOME"]) == (
                environment.trial_paths.agent_dir / "opencode" / "xdg-data"
            )
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_windows_exec_preserves_a_leading_quoted_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Windows"
    )
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")
    calls: list[tuple[object, ...]] = []

    async def create_process(*args, **kwargs):
        del kwargs
        calls.append(args)
        return _CompletedProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)

    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            result = await environment.exec(
                r'"C:\Program Files\Python312\python.exe" -m fixture'
            )
            assert result.return_code == 0
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())
    assert calls[0][:4] == (
        r"C:\Windows\System32\cmd.exe",
        "/D",
        "/S",
        "/C",
    )
    assert calls[0][4] == (r'""C:\Program Files\Python312\python.exe" -m fixture"')


def test_windows_rejects_every_explicit_user(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Windows"
    )

    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            with pytest.raises(ValueError, match="does not support user switching"):
                await environment.exec("ver", user="root")
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_windows_timeout_terminates_the_process_tree_with_taskkill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Windows"
    )
    target = _HangingProcess()
    invocations: list[tuple[object, ...]] = []

    async def create_process(*args, **kwargs):
        del kwargs
        invocations.append(args)
        if len(invocations) == 1:
            return target
        return _TaskkillProcess(target)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)

    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            with pytest.raises(asyncio.TimeoutError):
                await environment.exec("ping -t localhost", timeout_sec=0.001)
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())
    assert len(invocations) == 2
    assert invocations[1] == (
        "taskkill",
        "/PID",
        str(target.pid),
        "/T",
        "/F",
    )


def test_unsupported_native_host_fails_at_construction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Darwin"
    )

    with pytest.raises(RuntimeError, match="Linux and Windows hosts"):
        make_environment(tmp_path)


@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="native Windows process-tree acceptance runs only on Windows",
)
@pytest.mark.parametrize("termination", ["timeout", "cancel"])
def test_native_windows_termination_removes_child_process_tree(
    tmp_path: Path, termination: str
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path / "native jobs with spaces")
        await environment.start(force_build=False)
        marker = tmp_path / f"late-{termination}.txt"
        source = tmp_path / "spawn-child.py"
        source.write_text(
            "import subprocess, sys, time\n"
            "subprocess.Popen([sys.executable, '-c', "
            f"\"import pathlib, time; time.sleep(1); pathlib.Path({str(marker)!r}).write_text('late')\"])\n"
            "time.sleep(30)\n",
            encoding="utf-8",
        )
        await environment.upload_file(source, "C:/app/spawn-child.py")
        command = f"{quote_windows_shell_arg(sys.executable)} C:/app/spawn-child.py"
        try:
            if termination == "timeout":
                with pytest.raises(asyncio.TimeoutError):
                    await environment.exec(command, timeout_sec=0.3)
            else:
                task = asyncio.create_task(environment.exec(command))
                await asyncio.sleep(0.3)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            await asyncio.sleep(1.2)
            assert not marker.exists()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


class _EmptyStream:
    async def read(self, _size: int) -> bytes:
        return b""


class _CompletedProcess:
    def __init__(self) -> None:
        self.pid = 1001
        self.returncode: int | None = None
        self.stdout = _EmptyStream()
        self.stderr = _EmptyStream()

    async def wait(self) -> int:
        self.returncode = 0
        return 0


class _HangingProcess(_CompletedProcess):
    def __init__(self) -> None:
        super().__init__()
        self.pid = 4242

    async def wait(self) -> int:
        while self.returncode is None:
            await asyncio.sleep(3600)
        return self.returncode


class _TaskkillProcess(_CompletedProcess):
    def __init__(self, target: _HangingProcess) -> None:
        super().__init__()
        self._target = target

    async def wait(self) -> int:
        self._target.returncode = 1
        return await super().wait()

    async def communicate(self) -> tuple[bytes, bytes]:
        await self.wait()
        return b"", b""
