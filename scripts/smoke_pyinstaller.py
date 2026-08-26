from __future__ import annotations

import argparse
import http.client
import json
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    from scripts._smoke_harbor import assert_harbor_inspect, write_harbor_trial
except ModuleNotFoundError:  # Executed directly from scripts/.
    from _smoke_harbor import assert_harbor_inspect, write_harbor_trial

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/peval/fixtures/common_session.jsonl"
SERVE_URL_RE = re.compile(r"^peval serve: (http://[^\s]+/)$")
SERVE_START_TIMEOUT_SECONDS = 30


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed.stdout


def request_json(
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    parsed = urlsplit(base_url)
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {}
    if body is not None:
        headers = {
            "Content-Type": "application/json",
            "Origin": f"{parsed.scheme}://{parsed.netloc}",
        }
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=10)
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    raw = response.read()
    connection.close()
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"frozen peval returned a non-JSON response for {method} {path}"
        ) from exc
    if not isinstance(result, dict):
        raise RuntimeError(f"frozen peval returned a non-object for {method} {path}")
    return response.status, result


def request_bytes(base_url: str, path: str) -> tuple[int, dict[str, str], bytes]:
    parsed = urlsplit(base_url)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=10)
    connection.request("GET", path)
    response = connection.getresponse()
    body = response.read()
    headers = {key.lower(): value for key, value in response.getheaders()}
    connection.close()
    return response.status, headers, body


def expect_status(
    response: tuple[int, dict[str, Any]], expected: int, action: str
) -> dict[str, Any]:
    status, payload = response
    if status != expected:
        detail = payload.get("error", payload)
        raise RuntimeError(f"frozen {action} failed ({status}): {detail}")
    return payload


def wait_operation(base_url: str, payload: dict[str, Any]) -> None:
    operation = payload.get("operation")
    if not isinstance(operation, dict) or not isinstance(
        operation.get("operation_id"), str
    ):
        raise RuntimeError("frozen peval mutation omitted its operation status")
    operation_id = operation["operation_id"]
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        status = expect_status(
            request_json(base_url, "GET", f"/api/operations/{operation_id}"),
            200,
            "operation status",
        )
        state = status.get("state")
        if state == "completed":
            return
        if state not in {"queued", "running"}:
            raise RuntimeError(f"frozen peval operation failed: {status}")
        time.sleep(0.05)
    raise RuntimeError("frozen peval operation did not complete within 10 seconds")


def wait_serve_url(process: subprocess.Popen[str]) -> str:
    assert process.stdout is not None
    output: queue.Queue[str | None] = queue.Queue()

    def read_stdout() -> None:
        try:
            for line in process.stdout:
                output.put(line)
        finally:
            output.put(None)

    reader = threading.Thread(target=read_stdout, daemon=True)
    reader.start()
    deadline = time.monotonic() + SERVE_START_TIMEOUT_SECONDS
    observed: list[str] = []
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            item = output.get(timeout=remaining)
        except queue.Empty:
            break
        if item is None:
            break
        line = item.strip()
        if not line:
            continue
        observed.append(line)
        match = SERVE_URL_RE.fullmatch(line)
        if match is not None:
            return match.group(1)

    stderr = (
        process.stderr.read()
        if process.poll() is not None and process.stderr is not None
        else ""
    )
    stdout = "\n".join(observed[-10:]) or "<no output>"
    raise RuntimeError(
        "frozen peval serve did not publish its URL\n"
        f"stdout:\n{stdout}\nstderr:\n{stderr}"
    )


def smoke_workbench(
    executable: Path, *, cwd: Path, workspace: Path, env: dict[str, str]
) -> None:
    run([str(executable), "init", "-r", str(workspace)], cwd=cwd, env=env)
    process = subprocess.Popen(
        [str(executable), "serve", "-r", str(workspace), "--port", "0"],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        base_url = wait_serve_url(process)
        status, headers, module = request_bytes(base_url, "/assets/peval/main.js")
        if status != 200 or not module.strip():
            raise RuntimeError("frozen peval omitted the browser ESM entrypoint")
        if headers.get("content-type") != "application/javascript; charset=utf-8":
            raise RuntimeError("frozen peval served the browser module with wrong MIME")
        inventory = expect_status(
            request_json(base_url, "GET", "/api/config/harbor"),
            200,
            "Harbor configuration",
        )
        created_dataset = expect_status(
            request_json(
                base_url,
                "POST",
                "/api/config/harbor/datasets",
                {
                    "action": "create",
                    "dataset_id": "smoke",
                    "path": "dataset",
                    "package_name": "smoke/dataset",
                    "expected_revision": inventory["revision"],
                },
            ),
            202,
            "Dataset scaffold",
        )
        wait_operation(base_url, created_dataset)
        task_inventory = expect_status(
            request_json(base_url, "GET", "/api/harbor/datasets"),
            200,
            "Dataset workbench inventory",
        )
        dataset = task_inventory["datasets"][0]
        created_task = expect_status(
            request_json(
                base_url,
                "POST",
                "/api/harbor/tasks",
                {
                    "action": "create",
                    "dataset_id": "smoke",
                    "directory": "task",
                    "package_name": "smoke/task",
                    "steps": 0,
                    "expected_revision": dataset["revision"],
                },
            ),
            202,
            "Workbench Task scaffold",
        )
        wait_operation(base_url, created_task)
        task = created_task.get("result", {}).get("task", {})
        if task.get("status") != "valid":
            raise RuntimeError(f"frozen Workbench created an invalid Task: {task}")
        task_root = workspace / "dataset" / "task"
        required = (
            task_root / "task.toml",
            task_root / "instruction.md",
            task_root / "tests/test_outputs.py",
            task_root / "solution/solve.sh",
        )
        missing = [
            str(path.relative_to(workspace)) for path in required if not path.is_file()
        ]
        if missing:
            raise RuntimeError(
                f"frozen Workbench Task omitted template files: {missing}"
            )
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke the frozen peval CLI and Harbor Dataset Workbench."
    )
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    executable = args.executable.resolve()
    if not executable.is_file():
        raise RuntimeError(f"frozen peval executable not found: {executable}")

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp)
        home = tmp / "home"
        home.mkdir()
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(home),
                "HARBOR_TELEMETRY": "0",
                "SHELL": "/bin/bash",
                "_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION": "1",
            }
        )
        if "Usage: peval" not in run([str(executable), "--help"], cwd=tmp, env=env):
            raise RuntimeError("frozen peval help did not identify the CLI")
        harbor_trial = write_harbor_trial(tmp)
        assert_harbor_inspect(
            run(
                [str(executable), "view", "tr", "-p", str(harbor_trial)],
                cwd=tmp,
                env=env,
            )
        )
        report = tmp / "report.json"
        run(
            [
                str(executable),
                "view",
                "tr",
                "-m",
                "raw",
                "-a",
                "psychevo",
                "-p",
                str(FIXTURE),
                "-o",
                str(report),
            ],
            cwd=tmp,
            env=env,
        )
        if not json.loads(report.read_text(encoding="utf-8"))["trajectory"]:
            raise RuntimeError("frozen peval JSON report omitted trajectories")
        smoke_workbench(executable, cwd=tmp, workspace=tmp / "workspace", env=env)

    print("PyInstaller peval smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
