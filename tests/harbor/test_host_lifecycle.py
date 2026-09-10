from __future__ import annotations

import asyncio
import json
import sys
import threading
from pathlib import Path

import pytest

from tests.harbor.test_environment import make_environment


def test_stop_waits_for_process_launch_before_deleting_runtime(tmp_path, monkeypatch):
    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        workspace = host.work_dir
        entered, release = asyncio.Event(), asyncio.Event()
        spawn = host._process_adapter.spawn

        async def delayed_spawn(argv, **kwargs):
            entered.set()
            await release.wait()
            assert workspace.is_dir(), "stop deleted cwd while launch was pending"
            return await spawn(argv, **kwargs)

        monkeypatch.setattr(host._process_adapter, "spawn", delayed_spawn)
        command = asyncio.create_task(
            host.exec_argv([sys.executable, "-c", "import time; time.sleep(30)"])
        )
        await entered.wait()
        stopped = asyncio.create_task(host.stop(True))
        try:
            await asyncio.sleep(0.05)
            assert not stopped.done()
            assert workspace.exists()
        finally:
            release.set()
            await asyncio.gather(command, stopped, return_exceptions=True)
            await host.stop(True)
        assert not workspace.exists()
        assert not host._active_processes

    asyncio.run(asyncio.wait_for(scenario(), 10))


@pytest.mark.parametrize("delete", [False, True])
def test_stop_does_not_deadlock_a_callback_command_queued_after_a_launch(
    tmp_path, monkeypatch, delete
):
    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        workspace = host.work_dir
        callback_entered, callback_go, requested = (
            asyncio.Event(),
            asyncio.Event(),
            asyncio.Event(),
        )
        launch_entered, launch_go = asyncio.Event(), asyncio.Event()
        nested_commands = []
        stalled = []
        spawn = host._process_adapter.spawn

        async def delayed_spawn(argv, **kwargs):
            if argv[-1] == "pass":
                launch_entered.set()
                await launch_go.wait()
            return await spawn(argv, **kwargs)

        async def capture(text, stream):
            callback_entered.set()
            await callback_go.wait()
            nested = asyncio.create_task(
                host.exec_argv([sys.executable, "-c", "raise SystemExit(9)"])
            )
            nested_commands.append(nested)
            await asyncio.sleep(0)
            requested.set()
            finished, _ = await asyncio.wait((nested,), timeout=1)
            if not finished:
                stalled.append(True)
                nested.cancel()  # Release the callback even when testing broken code.
                await asyncio.gather(nested, return_exceptions=True)
            else:
                with pytest.raises(RuntimeError, match="stopping|not started"):
                    await nested

        monkeypatch.setattr(host._process_adapter, "spawn", delayed_spawn)
        commands = []
        try:
            with host.scoped_output_callback(capture):
                commands.append(
                    asyncio.create_task(
                        host.exec_argv(
                            [sys.executable, "-c", "print('ready',flush=True)"]
                        )
                    )
                )
            await callback_entered.wait()
            commands.append(
                asyncio.create_task(host.exec_argv([sys.executable, "-c", "pass"]))
            )
            await launch_entered.wait()
            commands.append(asyncio.create_task(host.stop(delete)))
            await asyncio.sleep(0)
            callback_go.set()
            await requested.wait()
            launch_go.set()
            results = await asyncio.gather(*commands, return_exceptions=True)
            assert not stalled, "stop held the launch lock while waiting for a callback"
            assert not any(isinstance(result, BaseException) for result in results), (
                results
            )
            assert not host._active_processes
            assert workspace.exists() is (not delete)
        finally:
            callback_go.set()
            launch_go.set()
            await asyncio.gather(*commands, *nested_commands, return_exceptions=True)
            await host.stop(True)

    asyncio.run(asyncio.wait_for(scenario(), 10))


def test_stop_keeps_runtime_until_output_callback_finishes(tmp_path):
    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        entered, release = asyncio.Event(), asyncio.Event()
        runtime = host.native_path("/tests").parent

        async def capture(text, stream):
            if stream == "stdout":
                entered.set()
                await release.wait()
                assert runtime.is_dir(), (
                    "runtime removed before output callback finished"
                )

        with host.scoped_output_callback(capture):
            command = asyncio.create_task(
                host.exec_argv([sys.executable, "-c", "print('evidence', flush=True)"])
            )
        await entered.wait()
        stopped = asyncio.create_task(host.stop(True))
        try:
            await asyncio.sleep(0.05)
            assert not stopped.done()
            assert runtime.exists()
            with pytest.raises(RuntimeError, match="stopping|not started"):
                await host.exec_argv([sys.executable, "-c", "pass"])
        finally:
            release.set()
            results = await asyncio.gather(command, stopped, return_exceptions=True)
            await host.stop(True)
        assert not any(isinstance(result, BaseException) for result in results), results
        assert not runtime.exists()

    asyncio.run(asyncio.wait_for(scenario(), 10))


def test_commands_are_rejected_while_startup_is_incomplete(tmp_path, monkeypatch):
    async def scenario():
        host = make_environment(tmp_path / "host")
        entered, release = threading.Event(), threading.Event()
        initialize = host._initialize_context

        def slow_initialize():
            initialize()
            entered.set()
            assert release.wait(5)

        monkeypatch.setattr(host, "_initialize_context", slow_initialize)
        start = asyncio.create_task(host.start(False))
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            with pytest.raises(RuntimeError, match="not started"):
                await host.exec_argv([sys.executable, "-c", "pass"])
        finally:
            release.set()
            await start
            await host.stop(True)

    asyncio.run(asyncio.wait_for(scenario(), 10))


def test_concurrent_commands_keep_independent_runtime_configs(tmp_path):
    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        both = asyncio.Event()
        seen = []

        async def capture(text, stream):
            if stream == "stdout":
                seen.append(text)
                if len(seen) == 2:
                    both.set()
                await both.wait()

        try:
            with host.scoped_output_callback(capture):
                results = await asyncio.gather(
                    *(
                        host.exec_argv(
                            [
                                sys.executable,
                                "-c",
                                "import json,os; print(json.dumps([os.getcwd(),os.environ['PEVAL_CONFIG']]),flush=True)",
                            ],
                            cwd=f"/app/{name}",
                            env=host.runtime_config_env(),
                        )
                        for name in ("one", "two")
                    )
                )
            configs = set()
            for result, name in zip(results, ("one", "two"), strict=True):
                cwd, config = json.loads(result.stdout)
                configs.add(config)
                assert Path(cwd) == host.native_path(f"/app/{name}")
                assert Path(
                    json.loads(Path(config).read_text())["paths"]["workdir"]
                ) == Path(cwd)
            assert len(configs) == 2
        finally:
            await host.stop(True)

    asyncio.run(asyncio.wait_for(scenario(), 10))


def test_output_callback_failure_terminates_process_and_releases_command(
    tmp_path, monkeypatch
):
    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        processes = []
        spawn = host._process_adapter.spawn

        async def record(*args, **kwargs):
            process = await spawn(*args, **kwargs)
            processes.append(process)
            return process

        async def failed_capture(text, stream):
            raise ValueError("fixture callback failure")

        monkeypatch.setattr(host._process_adapter, "spawn", record)
        try:
            with host.scoped_output_callback(failed_capture):
                with pytest.raises(ValueError, match="fixture callback failure"):
                    await host.exec_argv(
                        [
                            sys.executable,
                            "-c",
                            "import time; print('ready',flush=True); time.sleep(30)",
                        ]
                    )
            assert processes[0].returncode is not None
            assert not host._active_processes
        finally:
            await host.stop(True)

    asyncio.run(asyncio.wait_for(scenario(), 10))


@pytest.mark.parametrize("operation", ["start", "stop"])
def test_output_callback_cannot_reenter_host_lifecycle(tmp_path, operation):
    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        lifecycle_tasks = []

        async def capture(text, stream):
            lifecycle = asyncio.create_task(getattr(host, operation)(False))
            lifecycle_tasks.append(lifecycle)
            # Let the callback return even if a broken guard makes stop wait on it.
            finished, _ = await asyncio.wait((lifecycle,), timeout=1)
            if finished:
                await lifecycle

        try:
            with host.scoped_output_callback(capture):
                with pytest.raises(RuntimeError, match="active output callback"):
                    await asyncio.wait_for(
                        host.exec_argv([sys.executable, "-c", "print('ready')"]), 2
                    )
            assert not host._active_processes
            assert host.work_dir.is_dir()
        finally:
            await asyncio.gather(*lifecycle_tasks, return_exceptions=True)
            await host.stop(True)

    asyncio.run(asyncio.wait_for(scenario(), 10))


@pytest.mark.parametrize("failure", ["terminate", "communicate", "release"])
@pytest.mark.parametrize("primary", ["callback", "cancel", "timeout"])
def test_command_preserves_primary_error_and_drains_failing_cleanup(
    tmp_path, monkeypatch, failure, primary
):
    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        emitted, communicating, release = (
            asyncio.Event(),
            asyncio.Event(),
            asyncio.Event(),
        )
        spawn = host._process_adapter.spawn
        terminate = host._terminate_process
        release_process = host._process_adapter.release

        async def capture(text, stream):
            emitted.set()
            if primary == "callback":
                raise ValueError("primary callback failure")
            await asyncio.Event().wait()

        async def record_spawn(*args, **kwargs):
            process = await spawn(*args, **kwargs)
            communicate = process.communicate

            async def delayed_communicate():
                result = await communicate()
                communicating.set()
                await release.wait()
                if failure == "communicate":
                    raise OSError("fixture communicate failure")
                return result

            monkeypatch.setattr(process, "communicate", delayed_communicate)
            return process

        async def failed_terminate(process):
            await terminate(process)
            if failure == "terminate":
                raise OSError("fixture terminate failure")

        def failed_release(process):
            release_process(process)
            if failure == "release":
                raise OSError("fixture release failure")

        monkeypatch.setattr(host._process_adapter, "spawn", record_spawn)
        monkeypatch.setattr(host, "_terminate_process", failed_terminate)
        monkeypatch.setattr(host._process_adapter, "release", failed_release)
        with host.scoped_output_callback(capture):
            command = asyncio.create_task(
                host.exec_argv(
                    [sys.executable, "-c", "print('ready',flush=True)"],
                    timeout_sec=1 if primary == "timeout" else None,
                )
            )
        try:
            await emitted.wait()
            if primary == "cancel":
                command.cancel()
            await communicating.wait()
            if primary == "cancel":
                for _ in range(3):
                    command.cancel()
                    await asyncio.sleep(0)
            await asyncio.sleep(0.02)
            assert not command.done(), "command released before cleanup finished"
            assert host._active_processes
            release.set()
            expected = {
                "callback": ValueError,
                "cancel": asyncio.CancelledError,
                "timeout": TimeoutError,
            }[primary]
            with pytest.raises(expected) as caught:
                await command
            assert any(
                f"fixture {failure} failure" in note
                for note in getattr(caught.value, "__notes__", [])
            )
            assert not host._active_processes
        finally:
            release.set()
            await asyncio.gather(command, return_exceptions=True)
            await host.stop(True)

    asyncio.run(asyncio.wait_for(scenario(), 10))


@pytest.mark.parametrize("cancel", [False, True])
def test_runtime_config_write_does_not_block_loop_and_drains_before_stop(
    tmp_path, monkeypatch, cancel
):
    from psycheval.harbor import environment as module

    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        runtime = host.native_path("/tests").parent
        entered, release = threading.Event(), threading.Event()
        forced_release = threading.Event()
        write = module.write_effective_runtime_config
        spawned = []
        spawn = host._process_adapter.spawn

        def delayed_write(*args, **kwargs):
            entered.set()
            if not release.wait(1):
                forced_release.set()
            return write(*args, **kwargs)

        async def record_spawn(*args, **kwargs):
            spawned.append(True)
            return await spawn(*args, **kwargs)

        runtime_env = host.runtime_config_env()
        monkeypatch.setattr(module, "write_effective_runtime_config", delayed_write)
        monkeypatch.setattr(host._process_adapter, "spawn", record_spawn)
        command = asyncio.create_task(
            host.exec_argv([sys.executable, "-c", "print('ready')"], env=runtime_env)
        )
        stopped = None
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            assert not forced_release.is_set(), "runtime JSON write blocked the loop"
            if cancel:
                command.cancel()
                await asyncio.sleep(0)
                command.cancel()
            stopped = asyncio.create_task(host.stop(True))
            await asyncio.sleep(0.05)
            assert not command.done()
            assert not stopped.done()
            assert runtime.exists()
        finally:
            release.set()
            results = await asyncio.gather(
                command, *([stopped] if stopped else []), return_exceptions=True
            )
            await host.stop(True)
        if cancel:
            assert isinstance(results[0], asyncio.CancelledError)
            assert not spawned
        else:
            assert not isinstance(results[0], BaseException), results
            assert spawned == [True]
        assert not runtime.exists()

    asyncio.run(asyncio.wait_for(scenario(), 10))


@pytest.mark.parametrize("cancel", [False, True])
def test_runtime_deletion_does_not_block_loop_and_drains_on_cancel(
    tmp_path, monkeypatch, cancel
):
    import shutil

    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        workspace = host.work_dir
        entered, release = threading.Event(), threading.Event()
        remove = shutil.rmtree
        forced_release = threading.Event()

        def delayed_remove(path, **kwargs):
            if Path(path) == workspace:
                entered.set()
                if not release.wait(1):
                    forced_release.set()
            remove(path, **kwargs)

        monkeypatch.setattr(shutil, "rmtree", delayed_remove)
        stopped = asyncio.create_task(host.stop(True))
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            assert not forced_release.is_set(), (
                "directory deletion blocked the event loop"
            )
            if cancel:
                for _ in range(100):
                    stopped.cancel()
                    await asyncio.sleep(0)
                    assert not stopped.done()
                assert not forced_release.is_set(), (
                    "repeated cancellation starved the event loop"
                )
            assert workspace.exists()
        finally:
            release.set()
            result = await asyncio.gather(stopped, return_exceptions=True)
        if cancel:
            assert isinstance(result[0], asyncio.CancelledError)
        else:
            assert result == [None]
        assert not workspace.exists()
        await host.stop(True)

    asyncio.run(asyncio.wait_for(scenario(), 10))


@pytest.mark.parametrize("cancel_via", ["start", "stop"])
def test_project_copy_cancellation_stops_between_chunks(
    tmp_path, monkeypatch, cancel_via
):
    from psycheval.harbor import environment as module

    project = tmp_path / "project"
    project.mkdir()
    source = project / "large.bin"
    source.write_bytes(b"x" * (3 * 1024 * 1024))
    original_info = source.stat()
    entered, release = threading.Event(), threading.Event()
    reads = []
    git_calls = []
    open_fd = module.os.fdopen

    class Reader:
        def __init__(self, file):
            self.file = file

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.file.close()

        def fileno(self):
            return self.file.fileno()

        def read(self, size=-1):
            chunk = self.file.read(size)
            reads.append(len(chunk))
            if len(reads) == 1:
                entered.set()
                assert release.wait(5)
            return chunk

    def intercepted_open(fd, *args, **kwargs):
        matching = module.os.path.samestat(original_info, module.os.fstat(fd))
        file = open_fd(fd, *args, **kwargs)
        return Reader(file) if matching else file

    monkeypatch.setattr(module.os, "fdopen", intercepted_open)
    monkeypatch.setattr(
        module,
        "_initialize_git_baseline",
        lambda *args, **kwargs: git_calls.append(True),
    )

    async def scenario():
        root = tmp_path / "copies"
        host = make_environment(
            tmp_path / "host",
            environment_kwargs={"workspace_source": project, "workdir_root": root},
        )
        starting = asyncio.create_task(host.start(False))
        stopping = None
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            if cancel_via == "start":
                starting.cancel()
            else:
                stopping = asyncio.create_task(host.stop(True))
            await asyncio.sleep(0)
            assert not starting.done()
        finally:
            release.set()
            results = await asyncio.gather(
                starting, *([stopping] if stopping else []), return_exceptions=True
            )
            await host.stop(True)
        assert isinstance(results[0], asyncio.CancelledError), results
        assert len(reads) == 1, "copy continued reading after cancellation"
        assert not git_calls
        assert list(root.iterdir()) == []
        assert source.read_bytes() == b"x" * (3 * 1024 * 1024)

    asyncio.run(asyncio.wait_for(scenario(), 10))
