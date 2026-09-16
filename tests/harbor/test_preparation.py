from __future__ import annotations

import asyncio
import json
import sys

import pytest

from psycheval.harbor.environment import HostProcessAccessError
from tests.harbor.test_environment import make_environment


def make_host(tmp_path, script=None, **kwargs):
    host = make_environment(
        tmp_path / "host",
        environment_kwargs={
            "workdir_root": tmp_path / "workspaces",
            **kwargs,
        },
    )
    (host.environment_dir / "data/input.txt").write_text("原始数据", encoding="utf-8")
    if script is not None:
        (host.environment_dir / "prepare.py").write_text(script, encoding="utf-8")
    return host


def test_data_only_and_preparation_materials_stay_outside_workspace(tmp_path):
    host = make_host(tmp_path)
    (host.environment_dir / "helper.txt").write_text("not an input")

    async def run():
        await host.start(False)
        try:
            assert (host.work_dir / "input.txt").read_text(
                encoding="utf-8"
            ) == "原始数据"
            assert not (host.work_dir / "data").exists()
            assert not (host.work_dir / "Dockerfile").exists()
            assert not (host.work_dir / "helper.txt").exists()
        finally:
            await host.stop(True)

    asyncio.run(run())


def test_prepare_owns_copy_has_helpers_baseline_and_idempotent_start(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("PYTHONUTF8", "0")
    host = make_host(
        tmp_path / "中文 space",
        """from pathlib import Path
from helper import transform
def prepare(workdir):
    target = Path(workdir)
    assert target.is_absolute()
    assert not (target / 'input.txt').exists()
    assert not (target / '.git').exists()
    source = Path(__file__).parent / 'data/input.txt'
    (target / 'prepared.txt').write_text(transform(source.read_text(encoding='utf-8')), encoding='utf-8')
    print('准备完成')
""",
    )
    (host.environment_dir / "helper.py").write_text(
        "def transform(text): return text + ' converted'\n", encoding="utf-8"
    )
    before = {
        p.relative_to(host.environment_dir): p.read_bytes()
        for p in host.environment_dir.rglob("*")
        if p.is_file()
    }

    async def run():
        await host.start(False)
        try:
            output = host.work_dir / "prepared.txt"
            assert output.read_text(encoding="utf-8") == "原始数据 converted"
            baseline = await host.exec_argv(["git", "status", "--porcelain"])
            assert baseline.return_code == 0 and not baseline.stdout
            assert "准备完成" in (host.trial_paths.trial_dir / "prepare.log").read_text(
                encoding="utf-8"
            )
            output.write_text("agent change")
            await host.stop(False)
            await host.start(False)
            assert output.read_text() == "agent change"
            assert not (host.work_dir / "prepare.py").exists()
            assert before == {
                p.relative_to(host.environment_dir): p.read_bytes()
                for p in host.environment_dir.rglob("*")
                if p.is_file()
            }
        finally:
            await host.stop(True)

    asyncio.run(run())


@pytest.mark.parametrize(
    "script",
    [
        "",
        "def prepare(path): raise ValueError('broken')",
        "async def prepare(path): pass",
        "def prepare(path): return 5",
        "import absent_task_dependency",
    ],
)
def test_prepare_errors_abort_and_preserve_log(tmp_path, script):
    host = make_host(tmp_path, script)

    async def run():
        with pytest.raises(RuntimeError, match="Task preparation failed"):
            await host.start(False)
        assert not list((tmp_path / "workspaces").iterdir())
        assert (host.trial_paths.trial_dir / "prepare.log").read_text(encoding="utf-8")
        with pytest.raises(RuntimeError, match="has not started"):
            await host.exec_argv([sys.executable, "-c", "pass"])

    asyncio.run(run())


def test_preparation_excludes_judge_settings_but_preserves_task_environment(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("PEVAL_JUDGE_API_KEY", "not-for-task-children")
    monkeypatch.setenv("PEVAL_JUDGE_MODEL", "not-for-task-children")
    monkeypatch.setenv("TASK_PREP_VALUE", "available")
    host = make_host(
        tmp_path,
        """import os
def prepare(workdir):
    assert not any(key.upper().startswith('PEVAL_JUDGE_') for key in os.environ)
    assert os.environ['TASK_PREP_VALUE'] == 'available'
""",
        workspace_baseline="none",
    )

    async def run():
        try:
            await host.start(False)
        finally:
            await host.stop(True)

    asyncio.run(run())


def test_preparation_output_limit_cleans_descendants_and_keeps_log(
    tmp_path, monkeypatch
):
    import psutil

    import psycheval.harbor.environment as environment

    monkeypatch.setattr(environment, "_PREPARATION_OUTPUT_LIMIT", 8192)
    marker = tmp_path / "pids.json"
    host = make_host(
        tmp_path,
        f"""import subprocess, sys, json, os
from pathlib import Path
def prepare(workdir):
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    Path({str(marker)!r}).write_text(json.dumps([os.getpid(), child.pid]))
    for _ in range(100):
        print('x' * 1024, flush=True)
""",
        workspace_baseline="none",
    )

    async def run():
        with pytest.raises(RuntimeError, match="output exceeds"):
            await host.start(False)
        assert not list((tmp_path / "workspaces").iterdir())
        for pid in json.loads(marker.read_text()):
            assert (
                not psutil.pid_exists(pid)
                or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
            )
        log = host.trial_paths.trial_dir / "prepare.log"
        assert 0 < log.stat().st_size < 10000
        assert "output exceeds" in log.read_text()

    asyncio.run(run())


@pytest.mark.parametrize("action", ["cancel", "stop", "timeout"])
def test_preparation_cancellation_cleans_child_tree_and_owned_workspace(
    tmp_path, action
):
    marker = tmp_path / "child.json"
    # PID evidence lives outside the workspace so it survives cleanup.
    script = f"""import subprocess, sys, time, json, os
from pathlib import Path
def prepare(workdir):
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    Path({str(marker)!r}).write_text(json.dumps([os.getpid(), child.pid]))
    print('started', flush=True)
    time.sleep(60)
"""
    host = make_host(tmp_path, script, workspace_baseline="none")

    async def run():
        task = asyncio.create_task(host.start(False))
        async with asyncio.timeout(10):
            log_path = host.trial_paths.trial_dir / "prepare.log"
            while not (
                marker.exists()
                and log_path.exists()
                and "started" in log_path.read_text(encoding="utf-8")
            ):
                await asyncio.sleep(0.01)
        with pytest.raises(RuntimeError, match="has not started"):
            await host.exec_argv([sys.executable, "-c", "pass"])
        if action == "cancel":
            task.cancel()
        elif action == "stop":
            await asyncio.wait_for(host.stop(True), timeout=10)
        else:
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(task, timeout=0.01)
        with pytest.raises(asyncio.CancelledError):
            await task
        import psutil

        for pid in json.loads(marker.read_text()):
            assert (
                not psutil.pid_exists(pid)
                or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
            )
        assert not list((tmp_path / "workspaces").iterdir())
        assert "started" in (host.trial_paths.trial_dir / "prepare.log").read_text(
            encoding="utf-8"
        )

    asyncio.run(run())


def test_prepare_failure_does_not_delete_borrowed_workspace(tmp_path):
    workspace = tmp_path / "borrowed"
    workspace.mkdir()
    (workspace / "keep.txt").write_text("keep")
    host = make_environment(
        tmp_path / "host",
        extra_mounts=[
            {
                "type": "bind",
                "source": str(workspace),
                "target": "/app",
            }
        ],
    )
    (host.environment_dir / "prepare.py").write_text(
        "def prepare(workdir): raise RuntimeError('broken')\n"
    )

    async def run():
        with pytest.raises(RuntimeError, match="Task preparation failed"):
            await host.start(False)
        await host.stop(True)
        assert (workspace / "keep.txt").read_text() == "keep"
        assert not (workspace / ".git").exists()

    asyncio.run(run())


def test_filesystem_only_host_copies_data_but_rejects_scripts(tmp_path):
    host = make_environment(
        tmp_path / "host",
        host_access={"filesystem": True, "process": False},
        environment_kwargs={
            "workspace_baseline": "none",
            "workdir_root": tmp_path / "workspaces",
        },
    )
    (host.environment_dir / "data/input.txt").write_text("input")

    async def run():
        await host.start(False)
        try:
            assert (host.work_dir / "input.txt").read_text() == "input"
        finally:
            await host.stop(True)
        (host.environment_dir / "prepare.py").write_text(
            "raise AssertionError('process access denied')"
        )
        with pytest.raises(HostProcessAccessError):
            await host.start(False)
        assert not list((tmp_path / "workspaces").iterdir())

    asyncio.run(run())


def test_preparation_can_modify_project_and_reruns_for_recreated_workspace(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "project.txt").write_text("source")
    host = make_host(
        tmp_path,
        """from pathlib import Path
def prepare(workdir):
    target = Path(workdir) / 'project.txt'
    assert target.read_text() == 'source'
    target.write_text('prepared')
""",
        workspace_source=project,
    )

    async def run():
        for _ in range(2):
            await host.start(False)
            try:
                assert (host.work_dir / "project.txt").read_text() == "prepared"
                assert (project / "project.txt").read_text() == "source"
                baseline = await host.exec_argv(["git", "status", "--porcelain"])
                assert baseline.return_code == 0 and not baseline.stdout
                (host.work_dir / "project.txt").write_text("agent edit")
            finally:
                await host.stop(True)

    asyncio.run(run())


def test_default_copy_rejects_linked_directory_in_borrowed_workspace(tmp_path):
    workspace = tmp_path / "borrowed"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = workspace / "nested"
    if sys.platform == "win32":
        import _winapi

        _winapi.CreateJunction(str(outside), str(link))
    else:
        link.symlink_to(outside, target_is_directory=True)
    host = make_environment(
        tmp_path / "host",
        extra_mounts=[{"type": "bind", "source": str(workspace), "target": "/app"}],
    )
    (host.environment_dir / "data/nested").mkdir()
    (host.environment_dir / "data/nested/input.txt").write_text("input")

    async def run():
        try:
            with pytest.raises(ValueError, match="link or junction"):
                await host.start(False)
        finally:
            await host.stop(True)
        assert not (outside / "input.txt").exists()
        assert workspace.exists()

    asyncio.run(run())
