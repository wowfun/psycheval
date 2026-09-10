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

from psycheval.harbor.environment import (
    HostAccessPolicy,
    HostEnvironment,
    HostFilesystemAccessError,
    HostProcessAccessError,
)
from psycheval.harbor.workbuddy_environment import WorkBuddyHostEnvironment

_LINUX_ONLY = pytest.mark.skipif(
    platform.system() != "Linux", reason="test exercises the Linux process adapter"
)


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


def test_requires_filesystem_access_policy(tmp_path: Path) -> None:
    with pytest.raises(HostFilesystemAccessError, match="host_access.filesystem=true"):
        make_environment(
            tmp_path,
            host_access={"filesystem": False, "process": False},
            environment_kwargs={"workspace_baseline": "none"},
        )


def test_native_absolute_filesystem_paths_are_not_registered_as_virtual(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(
            tmp_path / "case",
            host_access={"filesystem": True, "process": False},
            environment_kwargs={
                "workspace_baseline": "none",
                "workdir_root": tmp_path / "workspaces",
            },
        )
        native_dir = tmp_path / "native" / "nested"
        await environment.start(force_build=False)
        try:
            await environment.ensure_dirs([str(native_dir)], chmod=False)
            assert native_dir.is_dir()
            assert environment.native_path(native_dir) == native_dir
            source = native_dir / "source.txt"
            source.write_text("native\n", encoding="utf-8")
            assert await environment.is_file(str(source))
            downloaded = tmp_path / "downloaded.txt"
            await environment.download_file(str(source), downloaded)
            assert downloaded.read_text(encoding="utf-8") == "native\n"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_filesystem_operations_reject_stop_in_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        entered = asyncio.Event()
        release = asyncio.Event()

        async def hold_stop(delete: bool) -> None:
            del delete
            entered.set()
            await release.wait()

        monkeypatch.setattr(environment, "_stop_commands", hold_stop)
        stopper = asyncio.create_task(environment.stop(delete=False))
        await entered.wait()
        try:
            with pytest.raises(RuntimeError, match="HostEnvironment is stopping"):
                await environment.is_dir("/app")
        finally:
            release.set()
            await stopper
            await environment.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks are unavailable")
def test_filesystem_checks_and_downloads_do_not_follow_symlinks(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret\n", encoding="utf-8")
    environment = make_environment(
        tmp_path / "case",
        host_access={"filesystem": True, "process": False},
        environment_kwargs={
            "workspace_baseline": "none",
            "workdir_root": tmp_path / "workspaces",
        },
    )

    async def scenario() -> None:
        await environment.start(force_build=False)
        try:
            link = environment.work_dir / "linked-dir"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                if getattr(exc, "winerror", None) == 1314:
                    pytest.skip("host does not grant symbolic-link creation privileges")
                raise
            assert not await environment.is_dir("/app/linked-dir")
            downloaded = tmp_path / "downloaded"
            await environment.download_dir("/app", downloaded)
            assert not (downloaded / "linked-dir").exists()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_rejects_removed_host_execution_flag(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="host_access"):
        make_environment(
            tmp_path,
            environment_kwargs={"allow_host_execution": True},
        )


def test_process_access_requires_filesystem_access() -> None:
    with pytest.raises(ValueError, match="process.*filesystem"):
        HostAccessPolicy(filesystem=False, process=True)


def test_host_access_errors_identify_invalid_field_type() -> None:
    with pytest.raises(ValueError, match=r"process=1.*int"):
        HostAccessPolicy.from_value({"filesystem": True, "process": 1})


def test_bootstrap_workbuddy_flag_requires_bool(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="WorkBuddyHostEnvironment"):
        make_environment(
            tmp_path,
            environment_kwargs={"bootstrap_workbuddy_workspace": "true"},
        )


def test_reset_dirs_retries_readonly_file_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        environment = make_environment(
            tmp_path,
            host_access={"filesystem": True, "process": False},
            environment_kwargs={"workspace_baseline": "none"},
        )
        await environment.start(force_build=False)
        try:
            path = environment.native_path("/app/read-only.txt")
            path.write_text("remove me", encoding="utf-8")
            original_unlink = Path.unlink
            failed = False

            def fail_once(current: Path, *, missing_ok: bool = False) -> None:
                nonlocal failed
                if current == path and not failed:
                    failed = True
                    raise PermissionError("read-only")
                original_unlink(current, missing_ok=missing_ok)

            monkeypatch.setattr(Path, "unlink", fail_once)
            monkeypatch.setattr(
                "psycheval.harbor.environment.windows.retry_readonly_removal",
                lambda operation, current, error: operation(current),
            )
            await environment.reset_dirs(
                remove_dirs=["/app/read-only.txt"],
                create_dirs=[],
                chmod_dirs=[],
            )
            assert not path.exists()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_filesystem_only_host_uses_native_filesystem_without_processes(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(
            tmp_path,
            host_access={"filesystem": True, "process": False},
            environment_kwargs={"workspace_baseline": "none"},
        )

        await environment.start(force_build=False)
        try:
            assert environment.path_mapper.translate(".") == environment.work_dir
            native_absolute = tmp_path / "native.txt"
            assert environment.native_path(native_absolute) == native_absolute
            await environment.ensure_dirs(["/app/input", "/app/download"], chmod=False)
            input_file = environment.native_path("/app/input/value.txt")
            input_file.write_text("value\n", encoding="utf-8")

            assert await environment.is_dir("/app/input")
            assert await environment.is_file("/app/input/value.txt")
            with pytest.raises(
                HostProcessAccessError, match="host_access.process=true"
            ):
                await environment.exec("true")
            with pytest.raises(
                HostProcessAccessError, match="host_access.process=true"
            ):
                await environment.exec_argv([sys.executable, "-c", "pass"])

            await environment.upload_file(input_file, "/app/uploaded.txt")
            upload_dir = tmp_path / "upload"
            upload_dir.mkdir()
            (upload_dir / "nested.txt").write_text("nested\n", encoding="utf-8")
            await environment.upload_dir(upload_dir, "/app/uploaded")

            await environment.empty_dirs(["/app/input"], chmod=False)
            assert await environment.is_dir("/app/input")
            assert not await environment.is_file("/app/input/value.txt")
            await environment.reset_dirs(
                remove_dirs=["/app/download"],
                create_dirs=["/app/download"],
                chmod_dirs=[],
            )
            (environment.native_path("/app/download/keep.txt")).write_text(
                "keep\n", encoding="utf-8"
            )
            (environment.native_path("/app/download/drop.log")).write_text(
                "drop\n", encoding="utf-8"
            )
            nested_download = environment.native_path("/app/download/nested")
            nested_download.mkdir()
            (nested_download / "nested-drop.log").write_text("drop\n", encoding="utf-8")
            download = tmp_path / "download"
            await environment.download_dir_with_exclusions(
                source_dir="/app/download", target_dir=download, exclude=["*.log"]
            )
            assert (download / "keep.txt").read_text(encoding="utf-8") == "keep\n"
            assert not (download / "drop.log").exists()
            assert not (download / "nested" / "nested-drop.log").exists()

            filtered = tmp_path / "filtered"
            await environment.download_dir_filtered(
                source_dir="/app/download",
                target_dir=filtered,
                include=["*.txt"],
            )
            assert (filtered / "keep.txt").is_file()
            assert not (filtered / "drop.log").exists()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_git_baseline_requires_process_access(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="workspace_baseline='git'.*process"):
        make_environment(
            tmp_path,
            host_access={"filesystem": True, "process": False},
        )


def test_workspace_baseline_none_can_be_selected_without_process_access(
    tmp_path: Path,
) -> None:
    environment = make_environment(
        tmp_path,
        host_access={"filesystem": True, "process": False},
        environment_kwargs={"workspace_baseline": "none"},
    )
    with pytest.raises(RuntimeError, match="has not started"):
        _ = environment.path_mapper

    async def scenario() -> None:
        await environment.start(force_build=False)
        try:
            assert not (environment.work_dir / ".git").exists()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_process_output_preserves_split_utf8_characters(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        captured = {"stdout": [], "stderr": []}

        async def capture(text, stream):
            captured[stream].append(text)

        try:
            with environment.scoped_output_callback(capture):
                result = await environment.exec_argv(
                    [
                        sys.executable,
                        "-c",
                        "import os,time; "
                        "os.write(1,b'\\xe4'); os.write(2,b'\\xe6'); "
                        "time.sleep(0.2); "
                        "os.write(1,b'\\xb8\\xad'); os.write(2,b'\\x96\\x87'); "
                        "os.write(1,b'\\xff'); os.write(2,b'\\xe4')",
                    ]
                )
            assert result.stdout == "中\ufffd"
            assert result.stderr == "文\ufffd"
            assert "".join(captured["stdout"]) == result.stdout
            assert "".join(captured["stderr"]) == result.stderr
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_process_enabled_host_accepts_native_absolute_cwd(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            native_cwd = environment.native_path("/app")
            result = await environment.exec_argv(
                [sys.executable, "-c", "import os; print(os.getcwd())"],
                cwd=str(native_cwd),
            )
            assert Path((result.stdout or "").strip()) == native_cwd
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.parametrize("shell", [False, True])
def test_native_process_cwd_remains_caller_owned(tmp_path: Path, shell) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path / "host")
        native_cwd = tmp_path / "caller-owned" / "new-directory"
        await environment.start(force_build=False)
        workspace = environment.work_dir
        try:
            if shell:
                command = "cd" if environment.os == TaskOS.WINDOWS else "pwd"
                result = await environment.exec(command, cwd=str(native_cwd))
            else:
                result = await environment.exec_argv(
                    [sys.executable, "-c", "import os; print(os.getcwd())"],
                    cwd=str(native_cwd),
                )
            assert result.return_code == 0
            assert Path((result.stdout or "").strip()).resolve() == native_cwd.resolve()
            assert environment.work_dir == workspace
            (native_cwd / "keep.txt").write_bytes(b"caller-owned")
        finally:
            await environment.stop(delete=True)
        assert not workspace.exists()
        assert (native_cwd / "keep.txt").read_bytes() == b"caller-owned"

    asyncio.run(scenario())


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
            host_access={"filesystem": True, "process": True},
        )


def test_rejects_force_build(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        with pytest.raises(ValueError, match="does not build Docker images"):
            await environment.start(force_build=True)

    asyncio.run(scenario())


@pytest.mark.parametrize("field", ["workdir_root", "workspace_source"])
@pytest.mark.parametrize("value", ["", "  ", "a\x00b", False, 42])
def test_rejects_invalid_workspace_parameters(tmp_path: Path, field, value) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "absolute native path"
            if field == "workdir_root"
            else "non-empty, NUL-free path"
        ),
    ):
        make_environment(
            tmp_path,
            environment_kwargs={field: value},
        )


@_LINUX_ONLY
def test_automatic_workspace_reuses_trial_short_uuid_and_obeys_delete(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path, trial_name="task__YfQLWrD")
        await environment.start(force_build=False)
        result = await environment.exec(
            'printf "%s|%s" "$PWD" "$PEVAL_CONFIG"',
            env=environment.runtime_config_env(),
        )
        cwd, config_path_value = (result.stdout or "").split("|", 1)
        workspace = Path(cwd)
        config_path = Path(config_path_value)
        assert workspace == Path(os.environ["HOME"]) / "workspaces" / "task_YfQLWrD"
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
    attempted: list[Path] = []
    import shutil

    real_rmtree = shutil.rmtree

    async def scenario():
        await environment.start(force_build=False)
        workspace = environment.work_dir
        runtime_root = environment.native_path("/tests").parent

        def fake_rmtree(path: Path, **kwargs) -> None:
            attempted.append(Path(path))
            if Path(path) == workspace:
                raise OSError("workspace is busy")
            real_rmtree(path, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr("psycheval.harbor.environment.shutil.rmtree", fake_rmtree)
            with pytest.raises(OSError, match="workspace is busy"):
                await environment.stop(delete=True)
        assert attempted == [workspace, runtime_root]
        await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_automatic_workspace_rejects_existing_trial_directory(tmp_path: Path) -> None:
    workspace = Path(os.environ["HOME"]) / "workspaces" / "task_YfQLWrD"
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
            assert workspace.name.startswith("task_") and len(workspace.name) == 12
            assert workspace.name != "explicit-name"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_start_failure_removes_owned_automatic_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = make_environment(tmp_path, trial_name="task__YfQLWrD")

    def fail_copy(*_args, **_kwargs) -> None:
        raise OSError("fixture copy failed")

    monkeypatch.setattr("psycheval.harbor.environment._copy_project_tree", fail_copy)

    async def scenario() -> None:
        with pytest.raises(OSError, match="fixture copy failed"):
            await environment.start(force_build=False)

    asyncio.run(scenario())
    assert not (Path(os.environ["HOME"]) / "workspaces" / "task_YfQLWrD").exists()


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
    environment = WorkBuddyHostEnvironment(
        environment_dir=environment_dir,
        environment_name="test",
        session_id="test-env",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(workdir=None),
        logger=logging.getLogger("test"),
        mounts=[],
        host_access={"filesystem": True, "process": True},
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
                Path(os.environ["HOME"]) / "workspaces" / "task_YfQLWrD"
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
    with pytest.raises(ValueError, match="Docker Compose services"):
        WorkBuddyHostEnvironment(
            environment_dir=environment_dir,
            environment_name="test",
            session_id="test-env",
            trial_paths=trial_paths,
            task_env_config=EnvironmentConfig(),
            logger=logging.getLogger("test"),
            mounts=[],
            host_access={"filesystem": True, "process": True},
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

    WorkBuddyHostEnvironment(
        environment_dir=environment_dir,
        environment_name="test",
        session_id="test-env",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(),
        logger=logging.getLogger("test"),
        mounts=[],
        host_access={"filesystem": True, "process": True},
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

    with pytest.raises(ValueError, match="exceeds 65536"):
        WorkBuddyHostEnvironment(
            environment_dir=environment_dir,
            environment_name="test",
            session_id="test-env",
            trial_paths=trial_paths,
            task_env_config=EnvironmentConfig(),
            logger=logging.getLogger("test"),
            mounts=[],
            host_access={"filesystem": True, "process": True},
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
    environment = WorkBuddyHostEnvironment(
        environment_dir=environment_dir,
        environment_name="test",
        session_id="test-env",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(workdir=None),
        logger=logging.getLogger("test"),
        mounts=[],
        host_access={"filesystem": True, "process": True},
    )
    replacement = tmp_path / "replacement.tar.gz"
    with tarfile.open(replacement, "w:gz") as stream:
        info = tarfile.TarInfo("input/replacement.txt")
        info.size = 0
        stream.addfile(info, io.BytesIO())
    archive.unlink()
    try:
        archive.symlink_to(replacement)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("host does not grant symbolic-link creation privileges")
        raise

    async def scenario() -> None:
        with pytest.raises(ValueError, match="archive cannot be extracted"):
            await environment.start(force_build=False)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "member_name",
    (
        "../escape.txt",
        ".git/config",
        ".GIT/config",
        "nested/.Git/config",
        ".GIT",
        ".git./config",
        "nested/.Git /config",
        "file:stream",
        ".. /escape.txt",
        "ordinary.txt.",
        "ordinary.txt ",
        "ordinary. /file.txt",
    ),
)
def test_workbuddy_bootstrap_rejects_unsafe_workspace_archive_paths(
    tmp_path: Path, member_name: str, monkeypatch
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
    archive_bytes = (environment_dir / "workspace.tar.gz").read_bytes()
    workspaces = tmp_path / "workspaces"
    trial_paths = TrialPaths(tmp_path / "unsafe__YfQLWrD")
    trial_paths.mkdir()
    environment = WorkBuddyHostEnvironment(
        environment_dir=environment_dir,
        environment_name="test",
        session_id="test-env",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(workdir=None),
        logger=logging.getLogger("test"),
        mounts=[],
        host_access={"filesystem": True, "process": True},
        workdir_root=workspaces,
    )

    def forbidden_git(*args, **kwargs):
        pytest.fail("unsafe archive reached Git baseline initialization")

    monkeypatch.setattr(
        "psycheval.harbor.environment._initialize_git_baseline", forbidden_git
    )

    async def scenario() -> None:
        with pytest.raises(ValueError, match="archive path is unsafe"):
            await environment.start(force_build=False)
        with pytest.raises(RuntimeError, match="has not started"):
            _ = environment.work_dir
        await environment.stop(delete=True)

    asyncio.run(scenario())
    assert not (tmp_path / "escape.txt").exists()
    assert list(workspaces.iterdir()) == []
    assert (environment_dir / "workspace.tar.gz").read_bytes() == archive_bytes


@pytest.mark.parametrize("member_name", ["D:/outside/file", "nested/D:outside/file"])
def test_workspace_archive_rejects_drive_paths_before_native_path_join(
    tmp_path, monkeypatch, member_name
):
    from psycheval.harbor.environment import _extract_workspace_archive

    archive = tmp_path / "workspace.tar.gz"
    entry = tarfile.TarInfo(member_name)
    entry.size = 1
    with tarfile.open(archive, "w:gz") as stream:
        stream.addfile(entry, io.BytesIO(b"x"))
    destination = tmp_path / "owned"
    destination.mkdir()
    original_join = Path.joinpath

    def guarded_join(path, *parts):
        if path == destination:
            pytest.fail("archive drive path reached native path mapping")
        return original_join(path, *parts)

    monkeypatch.setattr(Path, "joinpath", guarded_join)
    with pytest.raises(ValueError, match="archive path is unsafe"):
        _extract_workspace_archive(archive, destination)
    assert list(destination.iterdir()) == []


@pytest.mark.parametrize("kind", [tarfile.DIRTYPE, tarfile.REGTYPE, tarfile.SYMTYPE])
def test_workspace_archive_accepts_only_directory_root_entries(tmp_path, kind):
    from psycheval.harbor.environment import _extract_workspace_archive

    archive = tmp_path / "workspace.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        root = tarfile.TarInfo("./")
        root.type, root.mode = kind, 0
        stream.addfile(root)
        entry = tarfile.TarInfo("./input.txt")
        entry.size = 5
        stream.addfile(entry, io.BytesIO(b"input"))
    destination = tmp_path / "owned"
    destination.mkdir()
    mode = destination.stat().st_mode
    if kind == tarfile.DIRTYPE:
        _extract_workspace_archive(archive, destination)
        assert (destination / "input.txt").read_bytes() == b"input"
        assert destination.stat().st_mode == mode
    else:
        with pytest.raises(ValueError, match="unsafe"):
            _extract_workspace_archive(archive, destination)


@pytest.mark.skipif(os.name != "nt", reason="native Windows filename aliases")
def test_workspace_archive_does_not_overwrite_a_native_filename_alias(tmp_path):
    from psycheval.harbor.environment import _extract_workspace_archive

    archive = tmp_path / "workspace.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        for name, content in (("file.txt", b"original"), ("FILE.TXT", b"overwrite")):
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            stream.addfile(entry, io.BytesIO(content))
    destination = tmp_path / "owned"
    destination.mkdir()
    with pytest.raises(ValueError, match="conflicting duplicate paths"):
        _extract_workspace_archive(archive, destination)
    assert (destination / "file.txt").read_bytes() == b"original"


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
    environment = WorkBuddyHostEnvironment(
        environment_dir=environment_dir,
        environment_name="test",
        session_id="test-env",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(workdir=None),
        logger=logging.getLogger("test"),
        mounts=[],
        host_access={"filesystem": True, "process": True},
    )

    async def scenario() -> None:
        if expected_error is not None:
            with pytest.raises(ValueError, match=expected_error):
                await environment.start(force_build=False)
            return
        await environment.start(force_build=False)
        try:
            assert environment.native_path(
                "input/workspace/brief.txt"
            ).read_bytes() == (b"same\n")
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.parametrize("root", [None, "", "relative", "C:relative", "\\root"])
def test_host_rejects_invalid_roots_without_start(tmp_path, root):
    with pytest.raises(ValueError, match="absolute native path"):
        make_environment(tmp_path, environment_kwargs={"workdir_root": root})


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
                env={
                    **environment.runtime_config_env(),
                    "CALL_ENV": "present",
                    "PSYCHEVAL_LEGACY": "hidden",
                },
            )
            assert result.return_code == 0
            config_path, payload = (result.stdout or "").split("|", 1)
            assert payload == "fixture"
            runtime = json.loads(Path(config_path).read_text(encoding="utf-8"))
            workspace = Path(os.environ["HOME"]) / "workspaces" / "task_YfQLWrD"
            assert Path(runtime["paths"]["workdir"]) == workspace
            assert Path(runtime["harbor"]["host"]["workspace"]) == workspace
            assert Path(runtime["paths"]["tests"]).name == "tests"
            assert runtime["executables"]["python"] == sys.executable
            assert "harness" not in runtime["harbor"]
            first_config = Path(config_path)
            second, third = await asyncio.gather(
                environment.exec(
                    'printf "%s" "$PEVAL_CONFIG"', env=environment.runtime_config_env()
                ),
                environment.exec(
                    'printf "%s" "$PEVAL_CONFIG"', env=environment.runtime_config_env()
                ),
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
            assert "PEVAL_CONFIG=" not in (env_result.stdout or "")
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
            host_access={"filesystem": True, "process": True},
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
            assert resolved.name.startswith("task_") and len(resolved.name) == 12
        finally:
            await environment.stop(delete=True)

        assert resolved is not None
        assert not resolved.exists()

    asyncio.run(scenario())


def test_unmounted_agent_workdir_override_uses_automatic_workspace(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path, trial_name="task__YfQLWrD")
        await environment.start(force_build=False)
        try:
            await environment.ensure_dirs(
                ["/agent-selected/path"], chmod=False, virtual_workdir=True
            )
            result = await environment.exec_argv(
                [sys.executable, "-c", "import os; print(os.getcwd())"],
                cwd="/agent-selected/path",
            )
            assert Path((result.stdout or "").strip()) == (
                Path(os.environ["HOME"]) / "workspaces" / "task_YfQLWrD"
            )
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


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
                await environment.ensure_dirs(
                    ["/other"], chmod=False, virtual_workdir=True
                )
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
            "absolute",
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


@pytest.mark.parametrize("mode", ["argv", "shell"])
def test_exec_maps_declared_environment_with_per_call_and_scoped_precedence(
    tmp_path, mode
):
    async def scenario():
        environment = make_environment(
            tmp_path / "space 中文",
            config=EnvironmentConfig(
                workdir="/app",
                env={"TASK_FILE": "/app/task.txt", "OVERRIDE": "/app/task.txt"},
            ),
            environment_kwargs={
                "persistent_env": {
                    "PERSISTENT_FILE": "/app/persistent.txt",
                    "OVERRIDE": "/app/persistent.txt",
                }
            },
        )
        await environment.start(force_build=False)
        try:
            for name in ("task", "persistent", "scoped"):
                environment.native_path(f"/app/{name}.txt").write_text(name)
            script = (
                "import json,os; from pathlib import Path; "
                "print(json.dumps([Path(os.environ['TASK_FILE']).read_text(), "
                "Path(os.environ['PERSISTENT_FILE']).read_text(), os.environ['OVERRIDE']]))"
            )

            async def read(env=None):
                argv = [sys.executable, "-c", script]
                if mode == "argv":
                    result = await environment.exec_argv(argv, env=env)
                else:
                    quote = (
                        quote_windows_shell_arg
                        if environment.os == TaskOS.WINDOWS
                        else shlex.quote
                    )
                    result = await environment.exec(
                        " ".join(quote(arg) for arg in argv), env=env
                    )
                assert result.return_code == 0, result.stderr
                return json.loads(result.stdout)

            assert await read() == [
                "task",
                "persistent",
                str(environment.native_path("/app/persistent.txt")),
            ]
            literal = {"OVERRIDE": "/app/literal"}
            expected = (
                "/app/literal"
                if mode == "argv"
                else str(environment.native_path("/app/literal"))
            )
            assert await read(literal) == ["task", "persistent", expected]
            with environment.scoped_exec_env({"OVERRIDE": "/app/scoped.txt"}):
                assert await read(literal) == [
                    "task",
                    "persistent",
                    str(environment.native_path("/app/scoped.txt")),
                ]
            assert await read(literal) == ["task", "persistent", expected]
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_windows_exec_uses_cmd_and_translates_runtime_aliases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Windows"
    )
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def create_process(adapter, args, **kwargs):
        calls.append((tuple(args), {**kwargs, **adapter.process_kwargs()}))
        return _CompletedProcess()

    monkeypatch.setattr(
        "psycheval.harbor.windows.WindowsProcessAdapter.spawn", create_process
    )

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
                env={
                    "XDG_DATA_HOME": "C:/logs/agent/opencode/xdg-data",
                    "PYTHONPATH": "C:/app;C:/tests/grading;F:/lib",
                    "PATH": "C:/app/bin;F:/tools",
                },
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
            assert Path(kwargs["cwd"]).name.startswith("task_")
            assert len(Path(kwargs["cwd"]).name) == 12
            assert "creationflags" in kwargs
            assert Path(kwargs["env"]["XDG_DATA_HOME"]) == (
                environment.trial_paths.agent_dir / "opencode" / "xdg-data"
            )
            assert kwargs["env"]["PYTHONPATH"] == ";".join(
                (
                    str(environment.native_path("/app")),
                    str(environment.native_path("/tests/grading")),
                    "F:/lib",
                )
            )
            assert kwargs["env"]["PATH"].endswith(
                str(environment.native_path("/app/bin")) + ";F:/tools"
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

    async def create_process(adapter, args, **kwargs):
        del kwargs
        calls.append(tuple(args))
        return _CompletedProcess()

    monkeypatch.setattr(
        "psycheval.harbor.windows.WindowsProcessAdapter.spawn", create_process
    )

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


def test_windows_timeout_closes_the_owned_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Windows"
    )
    target = _HangingProcess()
    closed = []

    class Job:
        def close(self):
            closed.append(True)
            target.returncode = 1

    async def spawn(adapter, argv, **kwargs):
        adapter._jobs[target] = Job()
        return target

    monkeypatch.setattr("psycheval.harbor.windows.WindowsProcessAdapter.spawn", spawn)

    async def scenario():
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            with pytest.raises(asyncio.TimeoutError):
                await environment.exec("ping -t localhost", timeout_sec=0.001)
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())
    assert closed == [True]
    assert target.returncode == 1


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

    async def communicate(self) -> tuple[bytes, bytes]:
        stdout = await self.stdout.read(-1)
        stderr = await self.stderr.read(-1)
        await self.wait()
        return stdout, stderr


class _HangingProcess(_CompletedProcess):
    def __init__(self) -> None:
        super().__init__()
        self.pid = 4242

    async def wait(self) -> int:
        while self.returncode is None:
            await asyncio.sleep(3600)
        return self.returncode


@pytest.mark.parametrize("placement", ["state", "leaf", "upload"])
def test_runtime_storage_and_uploads_do_not_follow_directory_links(
    tmp_path, placement, caplog
):
    import subprocess

    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "private.txt").write_text("private")
        if placement == "upload":
            source = tmp_path / "upload"
            source.mkdir()
            (source / "regular.txt").write_text("regular")
            link = source / "alias"
        else:
            state = host.runtime_directory("first").parent
            if placement == "state":
                (state / "first").rmdir()
                state.rmdir()
                link = state
            else:
                link = state / "second"
        try:
            if os.name == "nt":
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                    check=True,
                    capture_output=True,
                )
            else:
                link.symlink_to(outside, target_is_directory=True)
            if placement == "upload":
                await host.upload_dir(source, "/app/upload")
                assert (host.work_dir / "upload/regular.txt").read_text() == "regular"
                assert not (host.work_dir / "upload/alias").exists()
                assert (
                    sum(
                        "Directory transfer omitted 1 linked entries" in record.message
                        for record in caplog.records
                    )
                    == 1
                )
            else:
                with pytest.raises(ValueError, match="link|junction"):
                    host.runtime_directory("second")
            assert sorted(p.name for p in outside.iterdir()) == ["private.txt"]
        finally:
            if os.path.lexists(link):
                link.rmdir() if os.name == "nt" else link.unlink()
            await host.stop(True)

    asyncio.run(scenario())


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_workspace_archive_strips_special_permission_bits(tmp_path):
    from psycheval.harbor.environment import _extract_workspace_archive

    archive = tmp_path / "workspace.tar.gz"
    entry = tarfile.TarInfo("executable")
    entry.mode = 0o7777
    entry.size = 1
    with tarfile.open(archive, "w:gz") as stream:
        stream.addfile(entry, io.BytesIO(b"x"))
    destination = tmp_path / "project"
    destination.mkdir()
    _extract_workspace_archive(archive, destination)
    assert (destination / "executable").stat().st_mode & 0o7777 == 0o777
