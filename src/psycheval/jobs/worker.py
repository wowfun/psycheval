"""Independent execution process; restarting peval serve never restarts a run."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

import psutil

from psycheval.redaction import sanitize_credentials

from .service import JobsService
from .storage import (
    locked,
    process_identity,
    read_json,
    safe_path,
    validate_state,
    write_json,
)


class WorkerControl:
    def __init__(self, service, run_id):
        self.run_id = run_id
        self.workspace = service.workspace
        self.control_dir = safe_path(service.root, run_id)
        self.output_dir = service.workspace / "jobs"
        self.state = validate_state(read_json(self.control_dir / "state.json"), run_id)
        self.state["worker"] = process_identity(os.getpid())
        self._lock = threading.RLock()

    def report(self, **progress):
        if set(progress) - {
            "trials_total",
            "trials_started",
            "trials_completed",
            "current_trial",
        }:
            raise ValueError("harness progress cannot set worker lifecycle or identity")
        for key, value in progress.items():
            if key == "current_trial":
                if not isinstance(value, str) or len(value) > 1000:
                    raise ValueError("current Trial must be a bounded label")
            elif type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(
                    "Trial progress must be a nonnegative integer up to 10000"
                )
        self._report(**progress)

    def _report(self, **progress):
        with self._lock:
            self.state.update(progress, heartbeat=time.time())
            write_json(self.control_dir / "state.json", self.state)

    async def subprocess(self, argv, **options):
        if os.name == "nt":
            options.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
        pending = asyncio.create_task(asyncio.create_subprocess_exec(*argv, **options))
        cancelled = False
        try:
            process = await asyncio.shield(pending)
        except asyncio.CancelledError:
            # Process creation can finish after cancellation on native Windows.
            # Acquire its identity before entering cleanup rather than orphaning it.
            process = await pending
            cancelled = True
        owner = psutil.Process(process.pid)
        owner.create_time()
        descendants = {}
        try:
            if cancelled:
                raise asyncio.CancelledError
            while process.returncode is None:
                try:
                    for child in owner.children(recursive=True):
                        descendants[(child.pid, child.create_time())] = child
                except psutil.Error:
                    pass
                await asyncio.sleep(0.1)
            return await process.wait()
        finally:
            try:
                for child in owner.children(recursive=True):
                    descendants[(child.pid, child.create_time())] = child
            except psutil.Error:
                pass
            for child in [*reversed(list(descendants.values())), owner]:
                try:
                    child.kill()  # psutil verifies creation identity before signaling.
                except psutil.Error:
                    pass
            await asyncio.to_thread(
                psutil.wait_procs, [*descendants.values(), owner], timeout=5
            )
            await process.wait()


async def run(workspace, run_id):
    service = JobsService(workspace)
    control = WorkerControl(service, run_id)
    control.report()
    record = read_json(control.control_dir / "request.json")
    plugin = service.plugin(record["request"]["harness"])

    async def execute():
        jobs = safe_path(workspace, "jobs")
        jobs.mkdir(exist_ok=True)
        while True:
            with locked(service.root):
                now = datetime.now().astimezone()
                output = safe_path(jobs, now.strftime("%Y-%m-%d__%H-%M-%S"))
                try:
                    output.mkdir()
                except FileExistsError:
                    pass
                else:
                    control.output_dir = output
                    control._report(
                        state="running",
                        started_at=now.isoformat(),
                        job_name=output.name,
                    )
                    break
            await asyncio.sleep(0.1)
        await plugin.execute(record["prepared"], control)

    task = asyncio.create_task(execute())
    loop = asyncio.get_running_loop()
    finished = threading.Event()

    def supervise():
        stopped_at = None
        heartbeat_at = time.monotonic()
        while not finished.wait(0.25):
            if (control.control_dir / "stop.json").exists() and stopped_at is None:
                stopped_at = time.monotonic()
                control._report(state="stopping")
                loop.call_soon_threadsafe(task.cancel)
            if stopped_at is not None and time.monotonic() - stopped_at > 30:
                # Only descendants of this worker are eligible for escalation.
                children = psutil.Process().children(recursive=True)
                for child in reversed(children):
                    try:
                        child.kill()
                    except psutil.Error:
                        pass
                psutil.wait_procs(children, timeout=5)
                control._report(
                    state="cancelled",
                    error="Cancellation cleanup exceeded 30 seconds",
                    finished_at=datetime.now().astimezone().isoformat(),
                )
                os._exit(2)
            if time.monotonic() - heartbeat_at >= 2:
                control.report()
                heartbeat_at = time.monotonic()

    # Cancellation remains enforceable even if a plugin blocks the event loop.
    watchdog = threading.Thread(target=supervise, daemon=True)
    watchdog.start()
    outcome = {"state": "completed"}
    try:
        await task
    except asyncio.CancelledError:
        outcome = {"state": "cancelled"}
    except BaseException as exc:
        print(sanitize_credentials(traceback.format_exc()), flush=True)
        outcome = {"state": "failed", "error": sanitize_credentials(str(exc))}
    finally:
        finished.set()
        watchdog.join(timeout=2)
        # Harness libraries may start helpers outside control.subprocess (including
        # native console hosts). They still belong exclusively to this worker.
        children = psutil.Process().children(recursive=True)
        for child in reversed(children):
            try:
                child.kill()
            except psutil.Error:
                pass
        _, alive = await asyncio.to_thread(psutil.wait_procs, children, timeout=5)
        if alive:
            outcome = {
                "state": "failed",
                "error": "Worker descendants did not exit during cleanup",
            }
        control._report(**outcome, finished_at=datetime.now().astimezone().isoformat())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(run(Path(sys.argv[1]), sys.argv[2]))
