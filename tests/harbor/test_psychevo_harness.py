from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

from psycheval.harbor import psychevo_harness


def test_harness_uses_trial_owned_psychevo_database(
    tmp_path: Path, monkeypatch
) -> None:
    logs_dir = tmp_path / "agent"
    pevo = tmp_path / "pevo"
    pevo.write_text("fixture", encoding="utf-8")
    pevo.chmod(0o755)
    monkeypatch.setenv("PSYCHEVAL_AGENT_LOGS_DIR", str(logs_dir))
    monkeypatch.delenv("PSYCHEVO_DB", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO("Fetch the page"))

    def fake_run(command, **kwargs):
        if "run" in command:
            assert kwargs["env"]["PSYCHEVO_DB"] == str(logs_dir / "psychevo-state.db")
            events = [
                {"type": "thread.started", "threadId": "thread-1"},
                {
                    "type": "item.completed",
                    "item": {
                        "id": "assistant-1",
                        "role": "assistant",
                        "source": "runtime.message",
                        "createdAtMs": 1_000,
                        "blocks": [
                            {
                                "kind": "text",
                                "status": "completed",
                                "body": "Done.",
                                "metadata": {"model": "fixture-model"},
                            }
                        ],
                    },
                },
                {
                    "type": "turn.completed",
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "outcome": "completed",
                    "toolFailures": 0,
                    "finalAnswer": "Done.",
                },
            ]
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="\n".join(json.dumps(event) for event in events),
                stderr="",
            )
        return subprocess.CompletedProcess(command, 0, stdout="pevo 0.1.0\n", stderr="")

    monkeypatch.setattr(psychevo_harness.subprocess, "run", fake_run)

    assert psychevo_harness.main(["--pevo", str(pevo), "--dir", str(tmp_path)]) == 0
    assert (logs_dir / "trajectory.json").is_file()
