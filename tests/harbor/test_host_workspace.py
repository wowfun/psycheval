from __future__ import annotations

import asyncio
import json
import os
import shutil
import stat
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from harbor.models.task.config import EnvironmentConfig

from psycheval.harbor import environment as host
from tests.harbor.test_environment import (
    make_environment,
    make_separate_verifier_environment,
)


def tree_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_project_copy_does_not_depend_on_python_recursion_depth(tmp_path):
    source, destination = tmp_path / "source", tmp_path / "copy"
    source.mkdir()
    destination.mkdir()
    leaf = source
    for _ in range(120):
        leaf = leaf / "d"
        leaf.mkdir()
    (leaf / "input.txt").write_bytes(b"deep project content")
    # Isolate the reduced recursion limit from pytest and other worker threads.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from pathlib import Path; "
            "from psycheval.harbor.environment import _copy_project_tree; "
            "sys.setrecursionlimit(100); "
            "_copy_project_tree(Path(sys.argv[1]), Path(sys.argv[2]))",
            str(source),
            str(destination),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert (destination / leaf.relative_to(source) / "input.txt").read_bytes() == (
        leaf / "input.txt"
    ).read_bytes()


@pytest.mark.parametrize("restart", [False, True])
def test_missing_owned_runtime_does_not_prevent_cleanup_or_restart(tmp_path, restart):
    environment = make_environment(tmp_path / "host")

    async def scenario():
        await environment.start(False)
        workspace = environment.work_dir
        runtime = environment.native_path("/tests").parent
        await environment.stop(False)
        shutil.rmtree(runtime)
        try:
            await environment.stop(True)
            if restart:
                await environment.start(False)
                assert environment.work_dir.exists()
                assert environment.native_path("/tests").parent != runtime
        finally:
            await environment.stop(True)
        assert not workspace.exists()

    asyncio.run(scenario())


@pytest.mark.parametrize("root_kind", ["default", "explicit"])
def test_workspace_paths_and_lifecycle_ignore_parent_config(
    tmp_path, monkeypatch, root_kind
):
    monkeypatch.setenv("PEVAL_CONFIG", str(tmp_path / "missing.toml"))
    root = tmp_path / "custom workspace"
    kwargs = {} if root_kind == "default" else {"workdir_root": root}
    environment = make_environment(
        tmp_path / "case",
        trial_name="named__YfQLWrD",
        config=EnvironmentConfig(workdir="/custom/project"),
        environment_kwargs=kwargs,
    )

    async def scenario():
        with pytest.raises(RuntimeError, match="has not started"):
            _ = environment.work_dir
        await asyncio.gather(environment.start(False), environment.start(False))
        workspace = environment.work_dir
        assert (
            workspace
            == environment.native_path(".")
            == environment.native_path("/custom/project")
        )
        assert workspace.name == "task_YfQLWrD"
        assert workspace.parent == (
            Path.home() / "workspaces" if root_kind == "default" else root
        )
        result = await environment.exec_argv(
            [
                sys.executable,
                "-c",
                "import json,os; from pathlib import Path; print(json.dumps([os.getcwd(),json.loads(Path(os.environ['PEVAL_CONFIG']).read_text())]))",
            ],
            env=environment.runtime_config_env(),
        )
        assert result.return_code == 0, result.stderr
        cwd, config = json.loads(result.stdout)
        assert Path(cwd) == workspace
        assert Path(config["paths"]["workdir"]) == workspace
        assert Path(config["harbor"]["host"]["workspace"]) == workspace
        await environment.stop(False)
        assert environment.work_dir == workspace
        retained = workspace / "retained.txt"
        retained.write_bytes(b"retained command state")
        tests_dir = environment.native_path("/tests")
        await environment.start(False)
        assert environment.work_dir == workspace
        assert environment.native_path("/tests") == tests_dir
        assert retained.read_bytes() == b"retained command state"
        await environment.stop(True)
        assert not workspace.exists()
        with pytest.raises(RuntimeError, match="has not started"):
            _ = environment.work_dir

    asyncio.run(scenario())


def test_project_copies_are_independent_with_complete_git_baselines(
    tmp_path, monkeypatch
):
    project = tmp_path / "project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "src" / "local.txt").write_text("uncommitted")
    branches = {
        "src/deep/leaf.txt": "nested source",
        "docs/deep/leaf.txt": "sibling source",
        "root.txt": "parent source",
    }
    for relative, content in branches.items():
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    (project / ".gitignore").write_text("ignored.txt\n")
    (project / "ignored.txt").write_text("ignored but included")
    (project / ".git").mkdir()
    (project / ".git" / "config").write_text("original repository")
    (project / "src" / ".git").write_text("gitdir: elsewhere")
    before = tree_files(project)
    monkeypatch.setenv("GIT_DIR", str(project / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(project))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.hooksPath")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(project / "hooks"))
    environments = [
        make_environment(
            tmp_path / f"case-{i}",
            environment_kwargs={
                "workdir_root": tmp_path / "copies",
                "workspace_source": project,
            },
        )
        for i in range(2)
    ]
    for environment in environments:
        (environment.environment_dir / "data/src").mkdir()
        (environment.environment_dir / "data/src" / "task.txt").write_text("task input")
        (environment.environment_dir / "data/.git").mkdir()
        (environment.environment_dir / "data/.git/config").write_text("task repository")
    task_before = [tree_files(env.environment_dir) for env in environments]

    async def scenario():
        try:
            await asyncio.gather(*(env.start(False) for env in environments))
            roots = [env.work_dir for env in environments]
            assert roots[0] != roots[1]
            # Execute Git with an explicitly clean environment, outside inherited test GIT_* state.
            clean_env = {
                k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")
            }
            for root in roots:
                for relative, content in branches.items():
                    assert (root / relative).read_text() == content
                assert (root / "src/local.txt").read_text() == "uncommitted"
                assert (root / "src/task.txt").read_text() == "task input"
                assert not (root / "src/.git").exists()
                status = subprocess.run(
                    ["git", "-C", str(root), "status", "--porcelain"],
                    env=clean_env,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                assert status.stdout == ""
                tracked = subprocess.run(
                    ["git", "-C", str(root), "ls-files"],
                    env=clean_env,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                assert "ignored.txt" in tracked.stdout.splitlines()
            (roots[0] / "src/local.txt").write_text("changed")
            assert (roots[1] / "src/local.txt").read_text() == "uncommitted"
            assert tree_files(project) == before
            assert [
                tree_files(env.environment_dir) for env in environments
            ] == task_before
        finally:
            for env in environments:
                await env.stop(True)
        assert not list((tmp_path / "copies").iterdir())

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "conflict", ["same_file", "source_directory", "task_directory"]
)
def test_project_merge_conflicts_clean_only_the_copy(tmp_path, conflict):
    project = tmp_path / "project"
    project.mkdir()
    environment = make_environment(
        tmp_path / "case",
        environment_kwargs={
            "workdir_root": tmp_path / "copies",
            "workspace_source": project,
        },
    )
    for root, directory in [
        (project, conflict == "source_directory"),
        (environment.environment_dir / "data", conflict == "task_directory"),
    ]:
        if directory:
            (root / "collision").mkdir()
        else:
            (root / "collision").write_text("identical")
    before = tree_files(project)

    async def scenario():
        with pytest.raises(ValueError, match="workspace merge conflict"):
            await environment.start(False)
        with pytest.raises(RuntimeError, match="has not started"):
            _ = environment.work_dir
        assert not list((tmp_path / "copies").iterdir())
        assert tree_files(project) == before

    asyncio.run(scenario())


def test_empty_project_gets_an_initial_commit(tmp_path):
    project = tmp_path / "empty"
    project.mkdir()
    environment = make_environment(
        tmp_path / "case",
        environment_kwargs={
            "workspace_source": project,
            "workdir_root": tmp_path / "copies",
        },
    )
    (environment.environment_dir / "Dockerfile").unlink()

    async def scenario():
        await environment.start(False)
        try:
            result = await environment.exec_argv(["git", "rev-list", "--count", "HEAD"])
            assert result.return_code == 0, result.stderr
            assert result.stdout.strip() == "1"
        finally:
            await environment.stop(True)

    asyncio.run(scenario())


def test_project_start_cancellation_waits_for_copy_then_cleans(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (project / "input").write_text("original")
    root = tmp_path / "copies"
    environment = make_environment(
        tmp_path / "case",
        trial_name="trial__YfQLWrD",
        environment_kwargs={"workspace_source": project, "workdir_root": root},
    )
    entered, release = threading.Event(), threading.Event()
    copy_tree = host._copy_project_tree

    def blocked_copy(source, destination, *, cancel=None):
        if source == project:
            entered.set()
            assert release.wait(10), "test did not release copy worker"
        copy_tree(source, destination, cancel=cancel)

    monkeypatch.setattr(host, "_copy_project_tree", blocked_copy)

    async def scenario():
        task = asyncio.create_task(environment.start(False))
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            with pytest.raises(RuntimeError):
                _ = environment.work_dir
            for _ in range(2):
                task.cancel()
                await asyncio.sleep(0)
                assert not task.done()
            assert (root / "task_YfQLWrD").exists()
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not list(root.iterdir())
        assert (project / "input").read_text() == "original"
        with pytest.raises(RuntimeError):
            _ = environment.work_dir

    asyncio.run(scenario())


def test_source_destination_overlap_fails_without_creating_a_copy(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    root = project / "copies"
    environment = make_environment(
        tmp_path / "case",
        environment_kwargs={"workspace_source": project, "workdir_root": root},
    )
    with pytest.raises(ValueError, match="overlap"):
        asyncio.run(environment.start(False))
    assert not root.exists()


def test_existing_trial_directory_is_never_reused_or_deleted(tmp_path):
    root = tmp_path / "copies"
    workspace = root / "task_YfQLWrD"
    workspace.mkdir(parents=True)
    (workspace / "keep.txt").write_text("keep")
    environment = make_environment(
        tmp_path / "case",
        trial_name="trial__YfQLWrD",
        environment_kwargs={"workdir_root": root},
    )
    with pytest.raises(FileExistsError, match="refusing to reuse stale state"):
        asyncio.run(environment.start(False))
    assert (workspace / "keep.txt").read_text() == "keep"
    with pytest.raises(RuntimeError):
        _ = environment.work_dir


@pytest.mark.parametrize("current_directory", [False, True])
def test_relative_workspace_source_is_resolved_at_construction(
    tmp_path, monkeypatch, current_directory
):
    project = tmp_path / "project"
    project.mkdir()
    (project / "input").write_text("original")
    monkeypatch.chdir(project if current_directory else tmp_path)
    environment = make_environment(
        tmp_path / "case",
        environment_kwargs={
            "workdir_root": tmp_path / "copies",
            "workspace_source": Path("") if current_directory else "project",
        },
    )
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    async def scenario():
        await environment.start(False)
        try:
            assert environment.work_dir.parent == tmp_path / "copies"
            assert (environment.work_dir / "input").read_text() == "original"
        finally:
            await environment.stop(True)
        assert not list(elsewhere.iterdir())

    asyncio.run(scenario())


@pytest.mark.parametrize("condition", ["missing", "file", "inaccessible"])
def test_invalid_project_directory_fails_before_allocation(
    tmp_path, monkeypatch, condition
):
    source = tmp_path / "project"
    root = tmp_path / "copies"
    if condition == "file":
        source.write_text("not a directory")
    elif condition == "inaccessible":
        source.mkdir()
        original_stat = Path.stat

        def denied_stat(path, *, follow_symlinks=True):
            if path == source and not follow_symlinks:
                raise PermissionError("fixture denies directory inspection")
            return original_stat(path, follow_symlinks=follow_symlinks)

        monkeypatch.setattr(Path, "stat", denied_stat)
    with pytest.raises(ValueError, match="workspace source") as raised:
        make_environment(
            tmp_path / "case",
            environment_kwargs={"workspace_source": source, "workdir_root": root},
        )
    if condition != "file":
        assert isinstance(
            raised.value.__cause__,
            FileNotFoundError if condition == "missing" else PermissionError,
        )
    assert not root.exists()


@pytest.mark.parametrize("mode", ["mount"])
def test_project_source_rejects_incompatible_initializers(tmp_path, mode):
    project = tmp_path / "project"
    project.mkdir()
    kwargs = {"workspace_source": project}
    mounts = []
    mounts.append({"type": "bind", "source": str(project), "target": "/workspace"})
    with pytest.raises(ValueError, match="workspace_source"):
        make_environment(
            tmp_path / "case", extra_mounts=mounts, environment_kwargs=kwargs
        )


def test_failed_git_initialization_removes_the_copy(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (project / "input").write_text("keep")
    root = tmp_path / "copies"
    environment = make_environment(
        tmp_path / "case",
        environment_kwargs={"workspace_source": project, "workdir_root": root},
    )

    def missing_git(*args, **kwargs):
        raise FileNotFoundError("git is unavailable")

    monkeypatch.setattr(host.subprocess, "run", missing_git)
    with pytest.raises(ValueError, match="Git baseline"):
        asyncio.run(environment.start(False))
    assert not list(root.iterdir())
    assert (project / "input").read_text() == "keep"


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows junction")
@pytest.mark.parametrize("root_link", [False, True])
def test_project_copy_rejects_windows_junctions(tmp_path, root_link):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("keep")
    junction = (
        tmp_path / "linked-project" if root_link else project / "linked-directory"
    )
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True,
        check=True,
    )
    assert junction.is_junction()
    with pytest.raises(ValueError, match="link or junction"):
        environment = make_environment(
            tmp_path / "case",
            environment_kwargs={
                "workspace_source": junction if root_link else project,
                "workdir_root": tmp_path / "copies",
            },
        )
        asyncio.run(environment.start(False))
    assert (outside / "keep").read_text() == "keep"


@pytest.mark.parametrize("location", ["project", "task"])
def test_project_copy_rejects_links(tmp_path, location):
    project = tmp_path / "project"
    project.mkdir()
    environment = make_environment(
        tmp_path / "case",
        environment_kwargs={
            "workspace_source": project,
            "workdir_root": tmp_path / "copies",
        },
    )
    target = tmp_path / "outside"
    target.write_text("keep")
    directory = (
        project if location == "project" else environment.environment_dir / "data"
    )
    try:
        (directory / "link").symlink_to(target)
    except OSError:
        pytest.skip("host does not permit creating symbolic links")
    with pytest.raises(ValueError, match="link or junction"):
        asyncio.run(environment.start(False))
    assert target.read_text() == "keep"
    assert not list((tmp_path / "copies").iterdir())


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX FIFO")
def test_project_copy_rejects_special_files(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    os.mkfifo(project / "pipe")
    environment = make_environment(
        tmp_path / "case", environment_kwargs={"workspace_source": project}
    )
    with pytest.raises(ValueError, match="special file"):
        asyncio.run(environment.start(False))
    assert stat.S_ISFIFO((project / "pipe").stat().st_mode)


def test_source_is_not_copied_into_separate_verifier(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "private-agent-file").write_text("agent input")
    environment = make_separate_verifier_environment(tmp_path)
    (environment.environment_dir / "prepare.py").write_text(
        "raise AssertionError('Separate verifier must not prepare Task inputs')"
    )
    # Reconstruct through the public constructor, with the same shared Job kwargs.
    environment = host.HostEnvironment(
        environment_dir=environment.environment_dir,
        environment_name="verifier",
        session_id="verifier",
        trial_paths=environment.trial_paths,
        task_env_config=environment.task_env_config,
        host_access={"filesystem": True, "process": True},
        workspace_source=project,
        workdir_root=tmp_path / "copies",
        mounts=[
            {
                "type": "bind",
                "source": str(environment.trial_paths.verifier_dir),
                "target": "/logs/verifier",
            }
        ],
    )

    async def scenario():
        await environment.start(False)
        try:
            assert (environment.native_path("/tests") / "test.sh").exists()
            assert not (environment.native_path("/tests") / ".git").exists()
            assert not (environment.work_dir / "private-agent-file").exists()
            assert not (tmp_path / "copies").exists()
        finally:
            await environment.stop(True)

    asyncio.run(scenario())
