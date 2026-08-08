from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from harbor.utils.trajectory_validator import TrajectoryValidator

from psycheval.harbor.psychevo import parse_ndjson, psychevo_events_to_atif


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
    pevo_path = Path(args.pevo).expanduser()
    pevo = str(pevo_path.resolve()) if pevo_path.is_file() else shutil.which(args.pevo)
    if not pevo:
        raise SystemExit(f"pevo executable not found: {args.pevo}")
    logs_dir = Path(os.environ.get("PSYCHEVAL_AGENT_LOGS_DIR", "/logs/agent"))
    workdir = Path(
        args.workdir or os.environ.get("PSYCHEVAL_WORKDIR", "/app")
    ).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)
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
    if args.profile:
        command.extend(["--profile", args.profile])
    if args.model:
        command.extend(["--model", args.model])
    command.extend(["--", instruction])
    completed = subprocess.run(
        command,
        cwd=workdir,
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
        trajectory = psychevo_events_to_atif(
            parse_ndjson(completed.stdout),
            instruction=instruction,
            agent_version=version,
        )
    except (TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    trajectory_path = logs_dir / "trajectory.json"
    trajectory_path.write_text(
        json.dumps(trajectory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validator = TrajectoryValidator()
    if not validator.validate(trajectory_path):
        trajectory_path.unlink(missing_ok=True)
        raise SystemExit("generated invalid ATIF: " + "; ".join(validator.errors))
    return 0


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
