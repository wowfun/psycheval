from __future__ import annotations

import ast
import asyncio
import ctypes
import json
import os
import sys
import textwrap
from pathlib import Path, PureWindowsPath

import pytest

from psycheval.harbor import windows
from tests.harbor.test_environment import make_environment


@pytest.mark.parametrize(
    "value",
    [
        "C:/Workspace/a b/中文.txt",
        "c:\\workspace\\a b\\中文.txt",
        "/WORKSPACE/a b/中文.txt",
        "\\WorkSpace\\a b\\中文.txt",
    ],
)
def test_windows_aliases_resolve_to_an_independent_native_drive(value):
    mappings = {"/workspace": PureWindowsPath("D:/Trials/one")}
    assert windows.translate_literal(value, mappings) == r"D:\Trials\one\a b\中文.txt"


@pytest.mark.parametrize(
    "value",
    [
        "D:/workspace",
        "C:workspace",
        "//server/share",
        "\\\\server\\share",
        "/workspace/../gold",
        "/",
    ],
)
def test_windows_environment_paths_reject_ambiguous_or_escaping_paths(value):
    with pytest.raises(ValueError):
        windows.normalize_environment_path(value, label="workdir")


def test_windows_environment_paths_are_not_prefix_replacements():
    mappings = {
        "/workspace": PureWindowsPath("D:/Trial 中文"),
        "/tests": PureWindowsPath("E:/tests"),
    }
    assert windows.translate_literal("/workspace-other/file", mappings) is None
    for path in (
        "C:/workspace/D:/outside",
        "/workspace/C:escape",
        "/workspace/file:stream",
        "/WORKSPACE/../outside",
        "/WORKSPACE/file:stream",
    ):
        with pytest.raises(ValueError):
            windows.translate_literal(path, mappings)
    assert windows.translate_environment(
        {
            "PYTHONPATH": "C:/workspace;C:/tests/grading;F:/lib",
            "VALUE": "literal /workspace",
        },
        mappings,
    ) == {
        "PYTHONPATH": "D:\\Trial 中文;E:\\tests\\grading;F:/lib",
        "VALUE": "literal /workspace",
    }


def test_windows_shell_and_environment_share_case_insensitive_virtual_roots():
    mappings = {
        "/workspace": PureWindowsPath("D:/Trial"),
        "/workspace/out": PureWindowsPath("E:/Output Files"),
    }
    assert windows.translate_command("type /WORKSPACE/OUT/Result.json", mappings) == (
        'type "E:\\Output Files\\Result.json"'
    )
    assert windows.translate_environment(
        {"PATH": "/WORKSPACE/Bin;F:/tools"}, mappings
    ) == {"PATH": "D:\\Trial\\Bin;F:/tools"}


def test_powershell_command_requires_an_executable_and_quotes_literal_arguments():
    assert windows.powershell_command(["C:/Program Files/tool.exe", "a'b; $x"]) == (
        "& 'C:/Program Files/tool.exe' 'a''b; $x'"
    )
    for args in ([], [""], ["tool", "line\nbreak"]):
        with pytest.raises(ValueError):
            windows.powershell_command(args)


def test_python_rewriting_uses_utf8_positions_and_preserves_surrounding_source():
    source = '标题 = "中文"; path = "/workspace/a"  # preserve this comment\n'
    node = next(
        n
        for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.Constant) and n.value == "/workspace/a"
    )
    rewritten = windows.rewrite_python(source, [(node, repr("D:/试验/a"))])
    assert rewritten == "标题 = \"中文\"; path = 'D:/试验/a'  # preserve this comment\n"
    with pytest.raises(ValueError, match="overlapping"):
        windows.rewrite_python(source, [(node, repr("a")), (node, repr("b"))])


def test_exec_argv_preserves_arguments_without_shell_interpretation(tmp_path: Path):
    async def scenario():
        environment = make_environment(tmp_path / "space 中文")
        await environment.start(force_build=False)
        try:
            args = [
                "a b",
                "中文",
                "%PATH%",
                "& echo injected",
                'quote"value',
                "$(touch unwanted)",
                "/workspace/literal",
                "",
            ]
            result = await environment.exec_argv(
                [
                    sys.executable,
                    "-c",
                    "import json,sys; print(json.dumps(sys.argv[1:]))",
                    *args,
                ]
            )
            assert result.return_code == 0
            assert json.loads(result.stdout) == args
            result = await environment.exec_argv(
                [sys.executable, "-c", "import os; print(os.environ['LITERAL'])"],
                env={"LITERAL": "/app/native-looking/value"},
            )
            assert result.stdout.strip() == "/app/native-looking/value"
            assert not environment.native_path("/app/unwanted").exists()
            for invalid in ("echo hello", [], [""], [sys.executable, "\x00"]):
                with pytest.raises(ValueError, match="argv"):
                    await environment.exec_argv(invalid)
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_exec_argv_timeout_cleans_up_the_process(tmp_path: Path):
    async def scenario():
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            with pytest.raises(TimeoutError):
                await environment.exec_argv(
                    [sys.executable, "-c", "import time; time.sleep(60)"],
                    timeout_sec=0.1,
                )
            assert not environment._active_processes
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.parametrize("parent_exits", [False, True])
def test_timeout_terminates_descendants_even_after_the_parent_exits(
    tmp_path, parent_exits
):
    async def scenario():
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        marker = tmp_path / "escaped-child"
        child = f"import time; from pathlib import Path; time.sleep(1); Path({str(marker)!r}).write_text('escaped')"
        parent = (
            f"import subprocess,sys,time; subprocess.Popen([sys.executable, '-c', {child!r}]); "
            + ("" if parent_exits else "time.sleep(60)")
        )
        try:
            with pytest.raises(TimeoutError):
                await environment.exec_argv(
                    [sys.executable, "-c", parent], timeout_sec=0.3
                )
            await asyncio.sleep(1.1)
            assert not marker.exists()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.parametrize("assignment_fails", [False, True])
def test_windows_launch_gate_assigns_ownership_before_starting_target(
    tmp_path, monkeypatch, assignment_fails
):
    marker = tmp_path / "started"
    events = []

    class Job:
        def assign(self, pid):
            assert pid > 0
            assert not marker.exists()
            events.append("assign")
            if assignment_fails:
                raise OSError("fixture assignment failure")

        def close(self):
            events.append("close")

    monkeypatch.setattr(windows, "_ProcessJob", Job)

    async def scenario():
        adapter = windows.WindowsProcessAdapter()
        argv = [
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('started')",
        ]
        if assignment_fails:
            with pytest.raises(OSError, match="assignment"):
                await adapter.spawn(argv)
            assert not marker.exists()
        else:
            process = await adapter.spawn(argv)
            assert await process.wait() == 0
            assert marker.read_text() == "started"
            adapter.release(process)
        assert adapter._jobs == {}

    asyncio.run(scenario())
    assert events == ["assign", "close"]


def test_windows_launch_rejects_caller_stdin_before_allocating_a_job(monkeypatch):
    def unexpected_job():
        pytest.fail("invalid launch allocated a Job")

    monkeypatch.setattr(windows, "_ProcessJob", unexpected_job)

    async def scenario():
        adapter = windows.WindowsProcessAdapter()
        with pytest.raises(ValueError, match="stdin.*reserved"):
            await adapter.spawn(
                [sys.executable, "-c", "pass"], stdin=asyncio.subprocess.PIPE
            )

    asyncio.run(scenario())


@pytest.mark.parametrize("membership", [True, False, None])
def test_job_assignment_failure_reports_membership_and_keeps_the_windows_error(
    monkeypatch, membership
):
    from types import SimpleNamespace

    closed = []
    error = OSError("fixture access denied")
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 5, raising=False)
    monkeypatch.setattr(ctypes, "WinError", lambda code: error, raising=False)
    job = windows._ProcessJob.__new__(windows._ProcessJob)
    job.handle = 11
    job.kernel = SimpleNamespace(
        OpenProcess=lambda *args: 22,
        AssignProcessToJobObject=lambda *args: 0,
        CloseHandle=closed.append,
    )

    def contains(pid, *, any_job=False):
        assert pid == 123 and any_job
        if membership is None:
            raise OSError("membership query denied")
        return membership

    job.contains = contains
    with pytest.raises(RuntimeError, match="WinError 5") as exc:
        job.assign(123)
    assert (
        f"existing Job membership: {membership if membership is not None else 'unknown'}"
        in str(exc.value)
    )
    assert exc.value.__cause__ is error
    assert closed == [22]


@pytest.mark.skipif(sys.platform != "win32", reason="requires native Windows Job APIs")
def test_native_nested_job_owns_launcher_and_descendant():
    source = textwrap.dedent("""\
        import asyncio, json, sys
        from psycheval.harbor.windows import WindowsProcessAdapter

        async def main():
            adapter = WindowsProcessAdapter()
            child = await adapter.spawn(
                [sys.executable, "-c", "import os,time; print(os.getpid(), flush=True); time.sleep(60)"],
                stdout=asyncio.subprocess.PIPE,
            )
            try:
                pid = int(await asyncio.wait_for(child.stdout.readline(), 20))
                job = adapter._jobs[child]
                assert job.contains(child.pid) and job.contains(pid)
                print(json.dumps([child.pid, pid]), flush=True)
                await asyncio.sleep(60)
            finally:
                await adapter.terminate(child)

        asyncio.run(main())
    """)

    async def scenario():
        adapter = windows.WindowsProcessAdapter()
        process = await adapter.spawn(
            [sys.executable, "-c", source],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            line = await asyncio.wait_for(process.stdout.readline(), 30)
            assert line, (await process.stderr.read()).decode()
            inner_launcher, descendant = json.loads(line)
            job = adapter._jobs[process]
            assert job.contains(process.pid)
            assert job.contains(inner_launcher) and job.contains(descendant)
            assert not job.contains(os.getpid())
        finally:
            await adapter.terminate(process)

    asyncio.run(scenario())
