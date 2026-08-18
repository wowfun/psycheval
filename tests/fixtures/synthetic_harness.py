from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from harbor.utils.trajectory_validator import TrajectoryValidator

from psycheval.harbor.runtime_config import (
    RuntimeConfigError,
    load_effective_runtime_config,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Repository-internal Harbor integration fixture"
    )
    parser.add_argument(
        "--mode",
        choices=("single-step", "multi-step"),
        required=True,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    instruction = sys.stdin.read()
    if not instruction.strip():
        raise SystemExit("synthetic harness received an empty instruction")
    try:
        runtime = load_effective_runtime_config(require_harness=True)
    except RuntimeConfigError as exc:
        raise SystemExit(str(exc)) from exc
    logs_dir = Path(runtime.paths.agent_logs)
    artifacts_dir = Path(runtime.paths.artifacts)
    logs_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "single-step":
        trajectory = _single_step_trajectory(instruction, artifacts_dir)
        session_state = None
    else:
        trajectory, session_state = _multi_step_trajectory(
            instruction,
            logs_dir,
            artifacts_dir,
            action=runtime.harness.action,
            workdir=Path(runtime.paths.workdir),
        )
    trajectory_path = logs_dir / "trajectory.json"
    trajectory_path.write_text(
        json.dumps(trajectory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validator = TrajectoryValidator()
    if not validator.validate(trajectory_path):
        raise SystemExit(
            "fixture generated invalid ATIF: " + "; ".join(validator.errors)
        )
    if session_state is not None:
        (logs_dir / "fixture-session.json").write_text(
            json.dumps(session_state, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    return 0


def _single_step_trajectory(
    instruction: str,
    artifacts_dir: Path,
) -> dict[str, Any]:
    artifact = artifacts_dir / "single.txt"
    artifact.write_text("single-step fixture complete\n", encoding="utf-8")
    return {
        "schema_version": "ATIF-v1.7",
        "trajectory_id": "fixture:single-step",
        "session_id": "fixture-single-step",
        "agent": {"name": "psycheval-test-fixture", "version": "1"},
        "steps": [
            {"step_id": 1, "source": "user", "message": instruction},
            _tool_step(
                2,
                "single-step",
                "fixture_action",
                {"mode": "single-step"},
                {"status": "fixture-complete"},
            ),
            {
                "step_id": 3,
                "source": "agent",
                "message": "single complete: single.txt",
            },
        ],
    }


def _multi_step_trajectory(
    instruction: str,
    logs_dir: Path,
    artifacts_dir: Path,
    *,
    action: str,
    workdir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    step_name = next(
        (
            name
            for name in ("seed", "continue", "finish")
            if name in instruction.lower()
        ),
        None,
    )
    if step_name is None:
        raise SystemExit("multi-step fixture instruction has no recognized step")

    state_path = logs_dir / "fixture-session.json"
    if action == "resume":
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SystemExit(
                "synthetic harness resume requires valid session state"
            ) from exc
        if not isinstance(state, dict) or state.get("protocol_version") != 1:
            raise SystemExit("synthetic harness resume session state is invalid")
        session_id = state.get("session_id")
        sequence = state.get("sequence")
        if not isinstance(session_id, str) or not isinstance(sequence, int):
            raise SystemExit("synthetic harness resume session state is invalid")
        sequence += 1
    else:
        session_id = f"fixture-multi-{step_name}"
        sequence = 1

    workspace_marker = workdir / "multi-step-workspace.txt"
    if step_name == "seed":
        workdir.mkdir(parents=True, exist_ok=True)
        workspace_marker.write_text("workspace-ready\n", encoding="utf-8")
    elif not workspace_marker.is_file():
        raise SystemExit("multi-step fixture workspace state is unavailable")

    artifact_path = artifacts_dir / f"{step_name}.txt"
    artifact_path.write_text(f"{step_name}:{action}:{sequence}\n", encoding="utf-8")
    trajectory = {
        "schema_version": "ATIF-v1.7",
        "trajectory_id": f"{session_id}:{sequence}",
        "session_id": session_id,
        "agent": {"name": "psycheval-test-fixture", "version": "1"},
        "steps": [
            {"step_id": 1, "source": "user", "message": instruction},
            _tool_step(
                2,
                f"{step_name}-{sequence}",
                f"multi_{step_name}",
                {"action": action, "sequence": sequence},
                {"status": "workspace-ready", "step": step_name},
            ),
            {
                "step_id": 3,
                "source": "agent",
                "message": f"{step_name} complete: {artifact_path.name}",
            },
        ],
        "extra": {
            "harness_action": action,
            "session_sequence": sequence,
        },
    }
    state = {
        "protocol_version": 1,
        "session_id": session_id,
        "sequence": sequence,
    }
    return trajectory, state


def _tool_step(
    step_id: int,
    call_id: str,
    function_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "source": "agent",
        "message": "",
        "tool_calls": [
            {
                "tool_call_id": call_id,
                "function_name": function_name,
                "arguments": arguments,
            }
        ],
        "observation": {
            "results": [
                {
                    "source_call_id": call_id,
                    "content": json.dumps(result, ensure_ascii=False, sort_keys=True),
                    "extra": {"is_error": False, "status": "completed"},
                }
            ]
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
