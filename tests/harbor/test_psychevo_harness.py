from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from psycheval.harbor import psychevo_harness
from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    HarnessInvocation,
    RuntimePaths,
    write_effective_runtime_config,
)


def set_runtime_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    logs_dir: Path,
    *,
    action: str = "run",
) -> None:
    path = write_effective_runtime_config(
        tmp_path / "peval.json",
        EffectiveRuntimeConfig(
            paths=RuntimePaths(
                workdir=str(tmp_path),
                tests=str(tmp_path / "tests"),
                agent_logs=str(logs_dir),
                verifier_logs=str(tmp_path / "verifier"),
                artifacts=str(tmp_path / "artifacts"),
            ),
            harness=HarnessInvocation(action=action),
        ),
    )
    monkeypatch.setenv("PEVAL_CONFIG", str(path))


def test_harness_uses_trial_owned_psychevo_database(
    tmp_path: Path, monkeypatch
) -> None:
    logs_dir = tmp_path / "agent"
    pevo = tmp_path / "pevo"
    pevo.write_text("fixture", encoding="utf-8")
    pevo.chmod(0o755)
    set_runtime_config(tmp_path, monkeypatch, logs_dir)
    monkeypatch.delenv("PSYCHEVO_DB", raising=False)
    monkeypatch.setenv("PSYCHEVAL_LEGACY", "must-not-leak")
    monkeypatch.setattr(sys, "stdin", io.StringIO("Fetch the page"))

    def fake_run(command, **kwargs):
        if "run" in command:
            assert kwargs["env"]["PSYCHEVO_DB"] == str(logs_dir / "psychevo-state.db")
            assert "PEVAL_CONFIG" not in kwargs["env"]
            assert "PSYCHEVAL_LEGACY" not in kwargs["env"]
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


def test_harness_resumes_the_exact_trial_owned_session(
    tmp_path: Path, monkeypatch
) -> None:
    logs_dir = tmp_path / "agent"
    pevo = tmp_path / "pevo"
    pevo.write_text("fixture", encoding="utf-8")
    pevo.chmod(0o755)
    set_runtime_config(tmp_path, monkeypatch, logs_dir)
    run_commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        if "run" not in command:
            return subprocess.CompletedProcess(
                command, 0, stdout="pevo 0.1.0\n", stderr=""
            )
        run_commands.append(command)
        Path(kwargs["env"]["PSYCHEVO_DB"]).write_text("fixture", encoding="utf-8")
        turn = len(run_commands)
        events = [
            {"type": "thread.started", "threadId": "thread-1"},
            {
                "type": "item.completed",
                "item": {
                    "id": f"assistant-{turn}",
                    "role": "assistant",
                    "source": "runtime.message",
                    "blocks": [
                        {
                            "kind": "text",
                            "status": "completed",
                            "body": f"Done {turn}.",
                            "metadata": {"model": "fixture-model"},
                        }
                    ],
                },
            },
            {
                "type": "turn.completed",
                "threadId": "thread-1",
                "turnId": f"turn-{turn}",
                "outcome": "completed",
                "toolFailures": 0,
                "finalAnswer": f"Done {turn}.",
            },
        ]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="\n".join(json.dumps(event) for event in events),
            stderr="",
        )

    monkeypatch.setattr(psychevo_harness.subprocess, "run", fake_run)

    monkeypatch.setattr(sys, "stdin", io.StringIO("Start the work"))
    assert psychevo_harness.main(["--pevo", str(pevo), "--dir", str(tmp_path)]) == 0
    set_runtime_config(tmp_path, monkeypatch, logs_dir, action="resume")
    monkeypatch.setattr(sys, "stdin", io.StringIO("Continue the work"))
    assert psychevo_harness.main(["--pevo", str(pevo), "--dir", str(tmp_path)]) == 0

    assert "--session" not in run_commands[0]
    session_flag = run_commands[1].index("--session")
    assert run_commands[1][session_flag + 1] == "thread-1"
    trajectory = json.loads((logs_dir / "trajectory.json").read_text(encoding="utf-8"))
    assert trajectory["session_id"] == "thread-1"
    assert trajectory["steps"][0]["message"] == "Continue the work"
    assert "Start the work" not in json.dumps(trajectory)


def test_harness_resume_requires_trial_owned_state(tmp_path: Path, monkeypatch) -> None:
    logs_dir = tmp_path / "agent"
    logs_dir.mkdir()
    for name in ("trajectory.json", "psychevo.ndjson", "psychevo.stderr.log"):
        (logs_dir / name).write_text("stale\n", encoding="utf-8")
    pevo = tmp_path / "pevo"
    pevo.write_text("fixture", encoding="utf-8")
    pevo.chmod(0o755)
    set_runtime_config(tmp_path, monkeypatch, logs_dir, action="resume")
    monkeypatch.setattr(sys, "stdin", io.StringIO("Continue the work"))

    with pytest.raises(SystemExit, match="state database"):
        psychevo_harness.main(["--pevo", str(pevo), "--dir", str(tmp_path)])
    assert not any(
        (logs_dir / name).exists()
        for name in ("trajectory.json", "psychevo.ndjson", "psychevo.stderr.log")
    )


def test_harness_process_failure_replaces_diagnostics_without_stale_trajectory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    logs_dir = tmp_path / "agent"
    logs_dir.mkdir()
    for name in ("trajectory.json", "psychevo.ndjson", "psychevo.stderr.log"):
        (logs_dir / name).write_text("stale\n", encoding="utf-8")
    session_path = logs_dir / "psychevo-session.json"
    session_path.write_text(
        '{"protocol_version":1,"session_id":"prior-thread"}\n', encoding="utf-8"
    )
    pevo = tmp_path / "pevo"
    pevo.write_text("fixture", encoding="utf-8")
    pevo.chmod(0o755)
    set_runtime_config(tmp_path, monkeypatch, logs_dir)
    monkeypatch.setattr(sys, "stdin", io.StringIO("Start the work"))

    def fake_run(command, **_kwargs):
        return subprocess.CompletedProcess(
            command,
            7,
            stdout="current stdout\n",
            stderr="current stderr\n",
        )

    monkeypatch.setattr(psychevo_harness.subprocess, "run", fake_run)

    with pytest.raises(SystemExit, match="pevo run exited with 7"):
        psychevo_harness.main(["--pevo", str(pevo), "--dir", str(tmp_path)])
    assert not (logs_dir / "trajectory.json").exists()
    assert (logs_dir / "psychevo.ndjson").read_text(encoding="utf-8") == (
        "current stdout\n"
    )
    assert (logs_dir / "psychevo.stderr.log").read_text(encoding="utf-8") == (
        "current stderr\n"
    )
    assert not session_path.exists()


def test_harness_invalid_atif_invalidates_prior_session_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    logs_dir = tmp_path / "agent"
    logs_dir.mkdir()
    session_path = logs_dir / "psychevo-session.json"
    session_path.write_text(
        '{"protocol_version":1,"session_id":"prior-thread"}\n', encoding="utf-8"
    )
    pevo = tmp_path / "pevo"
    pevo.write_text("fixture", encoding="utf-8")
    pevo.chmod(0o755)
    set_runtime_config(tmp_path, monkeypatch, logs_dir)
    monkeypatch.setattr(sys, "stdin", io.StringIO("Start new work"))

    def fake_run(command, **_kwargs):
        if "run" not in command:
            return subprocess.CompletedProcess(
                command, 0, stdout="pevo 0.1.0\n", stderr=""
            )
        events = [
            {"type": "thread.started", "threadId": "new-thread"},
            {
                "type": "item.completed",
                "item": {
                    "id": "assistant-1",
                    "role": "assistant",
                    "source": "runtime.message",
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
                "threadId": "new-thread",
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

    monkeypatch.setattr(psychevo_harness.subprocess, "run", fake_run)
    monkeypatch.setattr(
        psychevo_harness.TrajectoryValidator, "validate", lambda _self, _path: False
    )

    with pytest.raises(SystemExit, match="generated invalid ATIF"):
        psychevo_harness.main(["--pevo", str(pevo), "--dir", str(tmp_path)])

    assert not session_path.exists()
    assert not (logs_dir / "trajectory.json").exists()


def test_harness_rejects_resumed_session_drift(tmp_path: Path, monkeypatch) -> None:
    logs_dir = tmp_path / "agent"
    logs_dir.mkdir()
    (logs_dir / "psychevo-state.db").write_text("fixture", encoding="utf-8")
    (logs_dir / "psychevo-session.json").write_text(
        '{"protocol_version":1,"session_id":"thread-1"}\n', encoding="utf-8"
    )
    (logs_dir / "trajectory.json").write_text("stale\n", encoding="utf-8")
    pevo = tmp_path / "pevo"
    pevo.write_text("fixture", encoding="utf-8")
    pevo.chmod(0o755)
    set_runtime_config(tmp_path, monkeypatch, logs_dir, action="resume")
    monkeypatch.setattr(sys, "stdin", io.StringIO("Continue the work"))

    def fake_run(command, **_kwargs):
        if "run" not in command:
            return subprocess.CompletedProcess(
                command, 0, stdout="pevo 0.1.0\n", stderr=""
            )
        events = [
            {
                "type": "turn.completed",
                "threadId": "thread-2",
                "turnId": "turn-2",
                "outcome": "completed",
                "toolFailures": 0,
                "finalAnswer": "Done.",
            }
        ]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="\n".join(json.dumps(event) for event in events),
            stderr="",
        )

    monkeypatch.setattr(psychevo_harness.subprocess, "run", fake_run)

    with pytest.raises(SystemExit, match="resumed a different session"):
        psychevo_harness.main(["--pevo", str(pevo), "--dir", str(tmp_path)])
    assert not (logs_dir / "trajectory.json").exists()
    assert not (logs_dir / "psychevo-session.json").exists()
