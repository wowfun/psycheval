import os
import queue
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from psycheval import file_access
from psycheval.workspace_reports import WorkspaceReportLibrary


def test_catalog_writer_rejects_a_lock_file_replaced_before_open(tmp_path, monkeypatch):
    from tests.peval.test_report_library_associations import library_at

    with library_at(tmp_path) as runtime:
        path = runtime.catalog.path.with_suffix(".sqlite3.writer.lock")
        path.write_bytes(b"original")
        original = file_access._open_lease_descriptor

        def changed(target):
            replacement = tmp_path / "replacement-lock"
            replacement.write_bytes(b"replacement")
            replacement.replace(target)
            return original(target)

        monkeypatch.setattr(file_access, "_open_lease_descriptor", changed)
        with pytest.raises(ValueError, match="changed while opening"):
            runtime.catalog.mutate(lambda: None)


def test_catalog_os_lock_contention_is_immediate_and_does_not_enter_mutation(
    tmp_path, monkeypatch
):
    from psycheval.state.catalog import CatalogBusyError
    from tests.peval.test_report_library_associations import library_at

    with library_at(tmp_path) as runtime:
        path = runtime.catalog.path.with_suffix(".sqlite3.writer.lock")
        path.write_bytes(b"0")
        with path.open("r+b") as handle:
            if os.name == "nt":
                import msvcrt

                def acquire():
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

                def release():
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                def acquire():
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                def release():
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

            acquire()
            try:
                with monkeypatch.context() as patcher:
                    patcher.setattr(
                        file_access.time,
                        "sleep",
                        lambda _: pytest.fail("catalog contention must not poll"),
                    )
                    with pytest.raises(CatalogBusyError):
                        runtime.catalog.mutate(
                            lambda: pytest.fail("contended mutation must not run")
                        )
            finally:
                release()
        _, value = runtime.catalog.mutate(lambda: "retry succeeded")
        assert value == "retry succeeded"


@pytest.mark.parametrize("timeout", [0, -1, True, float("inf"), float("nan"), "1"])
def test_lease_rejects_invalid_deadline_before_creating_file(tmp_path, timeout):
    path = tmp_path / "lease"
    with pytest.raises(ValueError, match="finite and positive"):
        with file_access.blocking_file_lease(
            path, label="Fixture", timeout_sec=timeout
        ):
            pytest.fail("invalid deadline entered the protected operation")
    assert not path.exists()


def test_lease_mutex_and_os_lock_share_one_deadline(tmp_path, monkeypatch):
    now = 0
    released = False

    def acquire_mutex(*, timeout):
        nonlocal now
        assert timeout == 1
        now = 0.75
        return True

    def release_mutex():
        nonlocal released
        released = True

    def sleep(delay):
        nonlocal now
        now += delay

    def busy(*args):
        import errno

        raise OSError(errno.EAGAIN, "fixture contention")

    path = tmp_path / "lease"
    monkeypatch.setattr(
        file_access, "time", SimpleNamespace(monotonic=lambda: now, sleep=sleep)
    )
    monkeypatch.setattr(
        file_access,
        "_LEASE_LOCKS",
        {
            os.path.normcase(os.path.abspath(path)): SimpleNamespace(
                acquire=acquire_mutex, release=release_mutex
            ),
        },
    )
    if os.name == "nt":
        import msvcrt

        monkeypatch.setattr(msvcrt, "locking", busy)
    else:
        import fcntl

        monkeypatch.setattr(fcntl, "flock", busy)
    with pytest.raises(file_access.FileLeaseTimeout):
        with file_access.blocking_file_lease(path, label="Fixture", timeout_sec=1):
            pytest.fail("a contended OS lock cannot enter the body")
    assert now == 1
    assert released


def test_lease_deadline_includes_same_process_contention_and_releases_waiter(tmp_path):
    path = tmp_path / "lease"
    acquired, release = threading.Event(), threading.Event()

    def hold():
        with file_access.blocking_file_lease(path, label="Owner"):
            acquired.set()
            assert release.wait(5)

    owner = threading.Thread(target=hold)
    owner.start()
    try:
        assert acquired.wait(2)
        started = time.monotonic()
        with pytest.raises(TimeoutError, match="Fixture lease.*timed out"):
            with file_access.blocking_file_lease(
                path, label="Fixture lease", timeout_sec=0.05
            ):
                pytest.fail("a waiter cannot enter a held lease")
        assert time.monotonic() - started < 2
    finally:
        release.set()
        owner.join(timeout=2)
    with file_access.blocking_file_lease(path, label="Retry", timeout_sec=0.1):
        pass


@pytest.mark.parametrize("primary_failure", [False, True])
def test_lease_release_failure_preserves_a_primary_mutation_error(
    tmp_path, monkeypatch, primary_failure
):
    if os.name == "nt":
        import msvcrt

        original = msvcrt.locking

        def unlock_failure(fd, operation, count):
            original(fd, operation, count)
            if operation == msvcrt.LK_UNLCK:
                raise OSError("fixture unlock failed")

        monkeypatch.setattr(msvcrt, "locking", unlock_failure)
    else:
        import fcntl

        original = fcntl.flock

        def unlock_failure(fd, operation):
            original(fd, operation)
            if operation == fcntl.LOCK_UN:
                raise OSError("fixture unlock failed")

        monkeypatch.setattr(fcntl, "flock", unlock_failure)
    error = RuntimeError("fixture mutation failed")
    with pytest.raises(RuntimeError if primary_failure else OSError) as failure:
        with file_access.blocking_file_lease(tmp_path / "lease", label="Fixture lease"):
            if primary_failure:
                raise error
    if primary_failure:
        assert failure.value is error
        assert any("unlock failed" in note for note in error.__notes__)


def test_lease_rejects_replaced_file_before_locking(tmp_path, monkeypatch):
    path = tmp_path / "lease"
    path.write_bytes(b"original")
    original = file_access._open_lease_descriptor

    def changed(target):
        replacement = tmp_path / "replacement"
        replacement.write_bytes(b"replacement")
        replacement.replace(target)
        return original(target)

    monkeypatch.setattr(file_access, "_open_lease_descriptor", changed)
    with pytest.raises(ValueError, match="changed while opening"):
        with file_access.blocking_file_lease(path, label="Fixture lease"):
            pytest.fail("a replaced file cannot own the lease")


def test_management_lease_blocks_another_process_and_retains_lock_file(tmp_path):
    ref = "analysis:" + "a" * 64
    source = "from pathlib import Path; import sys; from psycheval.workspace_reports import WorkspaceReportLibrary; "
    source += "library=WorkspaceReportLibrary(Path(sys.argv[1]),lambda:[]); "
    source += "\nwith library._management_state_lease(sys.argv[2]):\n print('locked',flush=True); sys.stdin.readline()\n"
    child = subprocess.Popen(
        [sys.executable, "-c", source, str(tmp_path), ref],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    ready = queue.Queue()
    threading.Thread(
        target=lambda: ready.put(child.stdout.readline()), daemon=True
    ).start()
    try:
        assert ready.get(timeout=15).strip() == "locked"
        path = next((tmp_path / "reports/.management-locks").glob("*.lock"))
        before = path.stat()
        started = time.monotonic()
        with pytest.raises(TimeoutError, match="Fixture lease.*timed out"):
            with file_access.blocking_file_lease(
                path, label="Fixture lease", timeout_sec=0.05
            ):
                pytest.fail("a waiter cannot enter a lease held by another process")
        assert time.monotonic() - started < 2
        with path.open("r+b") as handle:
            if os.name == "nt":
                import msvcrt

                with pytest.raises(OSError):
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                with pytest.raises(OSError):
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        child.stdin.write("release\n")
        child.stdin.flush()
        assert child.wait(timeout=15) == 0
        WorkspaceReportLibrary(tmp_path, lambda: []).clear_management_state(ref)
        assert os.path.samestat(before, path.stat())
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate()
