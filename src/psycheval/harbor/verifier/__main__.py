from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from harbor.models.trajectories import Trajectory

from ..runtime_config import optional_effective_runtime_config
from . import aggregate, evaluate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Grade a Psycheval trajectory")
    parser.add_argument("config", type=Path)
    return parser


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = _load_object(args.config)
    runtime = optional_effective_runtime_config()
    agent_logs = Path(runtime.paths.agent_logs) if runtime else Path("/logs/agent")
    verifier_logs = (
        Path(runtime.paths.verifier_logs) if runtime else Path("/logs/verifier")
    )
    artifacts_dir = (
        Path(runtime.paths.artifacts) if runtime else Path("/logs/artifacts")
    )
    trajectory = Trajectory(**_load_object(agent_logs / "trajectory.json"))
    checks = evaluate(trajectory, config, artifacts_dir)
    rewards = aggregate(checks)
    verifier_logs.mkdir(parents=True, exist_ok=True)
    (verifier_logs / "checks.json").write_text(
        json.dumps({"checks": checks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (verifier_logs / "reward.json").write_text(
        json.dumps(rewards, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
