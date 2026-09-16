from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any

from harbor.models.trajectories import Trajectory

from ..runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    optional_effective_runtime_config,
    write_effective_runtime_config,
)
from . import aggregate, build_scoring_plan, evaluate
from ._judge import JudgeSettings, clear_judge_outputs, merge_scores, run_judge
from ._judge_config import load_judge_config
from ._scoring import ScoringPlan, normalize_checks


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Grade a Psycheval trajectory")
    parser.add_argument("config", type=Path)
    return parser


def _load_object(path: Path, *, limit_mib: int = 16) -> dict[str, Any]:
    with path.open("rb") as stream:
        raw = stream.read(limit_mib * 1024 * 1024 + 1)
    if len(raw) > limit_mib * 1024 * 1024:
        raise ValueError(f"JSON file exceeds {limit_mib} MiB: {path}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    with tempfile.NamedTemporaryFile(
        dir=path.parent, suffix=".json", delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(
                (
                    json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False)
                    + "\n"
                ).encode("utf-8")
            )
        except BaseException:
            stream.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _custom_checks(
    script: Path, runtime: EffectiveRuntimeConfig, plan: ScoringPlan
) -> list[dict[str, Any]]:
    logs = Path(runtime.paths.verifier_logs)
    with tempfile.TemporaryDirectory(prefix="checks-", dir=logs) as temporary:
        context = write_effective_runtime_config(
            Path(temporary) / "context.json", runtime
        )
        output = Path(temporary) / "result.json"
        # The enclosing Harbor command owns cancellation, timeout and descendants.
        with (
            (logs / "custom-stdout.txt").open("wb") as stdout,
            (logs / "custom-stderr.txt").open("wb") as stderr,
        ):
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(script),
                    "--context",
                    str(context),
                    "--output",
                    str(output),
                ],
                cwd=runtime.paths.workdir,
                env={
                    **{
                        key: value
                        for key, value in os.environ.items()
                        if not key.upper().startswith("PEVAL_JUDGE_")
                    },
                    "PYTHONIOENCODING": "utf-8",
                },
                stdout=stdout,
                stderr=stderr,
                check=False,
            )
        if completed.returncode != 0:
            raise RuntimeError(
                f"custom verifier exited with code {completed.returncode}; see custom-stderr.txt"
            )
        payload = _load_object(output)
        if set(payload) != {"checks"} or not isinstance(payload["checks"], list):
            raise ValueError("custom result must contain a checks array")
        checks = []
        for check in payload["checks"]:
            if not isinstance(check, dict) or set(check) - {"id", "passed", "evidence"}:
                raise ValueError("custom checks accept only id, passed and evidence")
            if (
                not isinstance(check.get("id"), str)
                or check["id"] not in plan.custom_ids
            ):
                raise ValueError(f"unknown custom check ID: {check.get('id')!r}")
            checks.append(
                {**check, "id": "custom:" + check["id"], "dimension": "custom_outputs"}
            )
        return checks


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config_path = args.config.resolve()
    runtime = optional_effective_runtime_config()
    if runtime is None:
        runtime = EffectiveRuntimeConfig(
            paths=RuntimePaths(
                workdir=str(Path.cwd()),
                tests=str(config_path.parent),
                agent_logs="/logs/agent",
                verifier_logs="/logs/verifier",
                artifacts="/logs/artifacts",
            ),
            python=sys.executable,
        )
    verifier_logs = Path(runtime.paths.verifier_logs)
    verifier_logs.mkdir(parents=True, exist_ok=True)
    for name in (
        "reward.json",
        "reward.txt",
        "checks.json",
        "custom-stdout.txt",
        "custom-stderr.txt",
        "verifier-error.txt",
    ):
        (verifier_logs / name).unlink(missing_ok=True)
    try:
        clear_judge_outputs(verifier_logs)
        config = _load_object(config_path)
        plan = build_scoring_plan(config)
        judge_path = config_path.parent / "judge.yaml"
        judge_config = load_judge_config(judge_path) if judge_path.exists() else None
        settings = JudgeSettings.from_env() if judge_config else JudgeSettings()
        script = config_path.parent / "test_outputs.py"
        if bool(plan.custom_ids) != script.is_file():
            raise ValueError(
                "custom_checks and test_outputs.py must both be present or absent"
            )
        checks = []
        if plan.requires_trajectory:
            trajectory = Trajectory(
                **_load_object(
                    Path(runtime.paths.agent_logs) / "trajectory.json", limit_mib=128
                )
            )
            checks.extend(evaluate(trajectory, config, Path(runtime.paths.artifacts)))
        if plan.custom_ids:
            checks.extend(_custom_checks(script, runtime, plan))
        rewards = aggregate(checks, plan=plan)
        judge = asyncio.run(run_judge(judge_config, runtime, settings))
        rewards, merge = merge_scores(rewards, judge_config, judge)
        _write_json(
            verifier_logs / "checks.json",
            {
                "plan": plan.to_dict(),
                "checks": normalize_checks(checks, plan=plan),
                "rewards": rewards,
                "judge": judge,
                "score_merge": merge,
            },
        )
        _write_json(verifier_logs / "reward.json", rewards)
    except Exception:
        (verifier_logs / "verifier-error.txt").write_text(
            traceback.format_exc(), encoding="utf-8", errors="backslashreplace"
        )
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
