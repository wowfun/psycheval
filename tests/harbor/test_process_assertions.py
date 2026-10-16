from __future__ import annotations

import subprocess
import sys

import psutil
import pytest

from tests.harbor.environment_support import assert_process_exited


def test_exited_process_is_accepted_while_the_parent_still_owns_its_handle():
    with subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    ) as child:
        created = psutil.Process(child.pid).create_time()
        child.terminate()
        child.wait(timeout=5)
        # Popen still owns the Windows process handle until this context exits.
        assert_process_exited(child.pid, created)


def test_active_process_is_not_mistaken_for_a_finished_one():
    with subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    ) as child:
        try:
            created = psutil.Process(child.pid).create_time()
            with pytest.raises(AssertionError, match="remained active"):
                assert_process_exited(child.pid, created, timeout=0.02)
        finally:
            child.terminate()
            child.wait(timeout=5)


def test_reused_pid_does_not_wait_for_an_unrelated_process(monkeypatch):
    class ReusedProcess:
        def create_time(self):
            return 20

        def wait(self, **kwargs):
            raise AssertionError("waited on a reused PID")

    monkeypatch.setattr(psutil, "Process", lambda pid: ReusedProcess())
    assert_process_exited(123, 10)
