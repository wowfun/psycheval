from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from harbor.utils.trajectory_validator import TrajectoryValidator

from psycheval.harbor.psychevo import (
    parse_ndjson,
    psychevo_events_to_atif,
    terminal_event,
)
from psycheval.harbor.runtime_config import (
    PEVAL_CONFIG_ENV,
    RuntimeConfigError,
    load_effective_runtime_config,
)

_SESSION_STATE_FILENAME = "psychevo-session.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Psychevo and emit ATIF v1.7")
    parser.add_argument("--pevo", default="pevo", help="pevo executable path")
    parser.add_argument("--dir", dest="workdir", help="Psychevo working directory")
    parser.add_argument("--profile")
    parser.add_argument("--model")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    instruction = sys.stdin.read()
    if not instruction.strip():
        raise SystemExit("Psychevo harness received an empty instruction")
    try:
        runtime = load_effective_runtime_config(require_harness=True)
    except RuntimeConfigError as exc:
        raise SystemExit(str(exc)) from exc
    logs_dir = Path(runtime.paths.agent_logs)
    logs_dir.mkdir(parents=True, exist_ok=True)
    trajectory_path = logs_dir / "trajectory.json"
    for output_path in (
        trajectory_path,
        logs_dir / "psychevo.ndjson",
        logs_dir / "psychevo.stderr.log",
    ):
        output_path.unlink(missing_ok=True)
    pevo_path = Path(args.pevo).expanduser()
    pevo = str(pevo_path.resolve()) if pevo_path.is_file() else shutil.which(args.pevo)
    if not pevo:
        raise SystemExit(f"pevo executable not found: {args.pevo}")
    workdir = Path(args.workdir or runtime.paths.workdir).resolve()
    action = runtime.harness.action
    database_path = logs_dir / "psychevo-state.db"
    resumed_session_id = (
        _load_resume_session(logs_dir, database_path) if action == "resume" else None
    )
    (logs_dir / _SESSION_STATE_FILENAME).unlink(missing_ok=True)
    command = [
        str(pevo),
        "run",
        "--format",
        "json",
        "--isolated",
        "--no-agents",
        "--no-skills",
        "--dir",
        str(workdir),
    ]
    if resumed_session_id is not None:
        command.extend(["--session", resumed_session_id])
    if args.profile:
        command.extend(["--profile", args.profile])
    if args.model:
        command.extend(["--model", args.model])
    command.extend(["--", instruction])
    process_env = {
        key: value
        for key, value in os.environ.items()
        if key != PEVAL_CONFIG_ENV and not key.startswith("PSYCHEVAL_")
    }
    process_env["PSYCHEVO_DB"] = str(database_path)
    completed = subprocess.run(
        command,
        cwd=workdir,
        env=process_env,
        text=True,
        capture_output=True,
        check=False,
    )
    (logs_dir / "psychevo.ndjson").write_text(completed.stdout, encoding="utf-8")
    (logs_dir / "psychevo.stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        diagnostic = (completed.stderr or completed.stdout or "no output").strip()
        raise SystemExit(
            f"pevo run exited with {completed.returncode}: {diagnostic[-2000:]}"
        )
    version = _pevo_version(str(pevo))
    try:
        events = parse_ndjson(completed.stdout)
        terminal = terminal_event(events)
        session_id = terminal.get("threadId")
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("Psychevo terminal event has no exact threadId")
        if resumed_session_id is not None and session_id != resumed_session_id:
            raise ValueError(
                "Psychevo resumed a different session: "
                f"expected {resumed_session_id!r}, got {session_id!r}"
            )
        trajectory = psychevo_events_to_atif(
            events,
            instruction=instruction,
            agent_version=version,
        )
    except (TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    trajectory_path.write_text(
        json.dumps(trajectory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validator = TrajectoryValidator()
    if not validator.validate(trajectory_path):
        trajectory_path.unlink(missing_ok=True)
        raise SystemExit("generated invalid ATIF: " + "; ".join(validator.errors))
    _write_session_state(logs_dir, session_id)
    return 0


def _load_resume_session(logs_dir: Path, database_path: Path) -> str:
    if not database_path.is_file():
        raise SystemExit("Psychevo resume requires the Trial-owned state database")
    state_path = logs_dir / _SESSION_STATE_FILENAME
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit("Psychevo resume requires an exact session marker") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit("Psychevo resume session marker is invalid") from exc
    if not isinstance(state, dict) or state.get("protocol_version") != 1:
        raise SystemExit("Psychevo resume session marker is invalid")
    session_id = state.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        raise SystemExit("Psychevo resume session marker has no exact session id")
    return session_id


def _write_session_state(logs_dir: Path, session_id: str) -> None:
    (logs_dir / _SESSION_STATE_FILENAME).write_text(
        json.dumps(
            {"protocol_version": 1, "session_id": session_id},
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )


def _pevo_version(pevo: str) -> str:
    try:
        completed = subprocess.run(
            [pevo, "--version"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    value = completed.stdout.strip()
    return value or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
