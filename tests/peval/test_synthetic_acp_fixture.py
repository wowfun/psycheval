from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_running_prompt_timer_does_not_keep_fixture_process_alive() -> None:
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "session/prompt",
        "params": {
            "sessionId": "fixture-session",
            "prompt": [{"type": "text", "text": "Hold the running session"}],
        },
    }
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "web/e2e/synthetic_acp.py")],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        process.communicate(json.dumps(message) + "\n", timeout=0.5)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()

    assert process.returncode == 0
