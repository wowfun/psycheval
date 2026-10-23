from __future__ import annotations

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
    RuntimeConfigError,
    optional_effective_runtime_config,
    write_effective_runtime_config,
)
from ._blocking import run_blocking
from ._evaluation import evaluate
from ._judge import JudgeSettings, clear_judge_outputs, merge_scores, run_verifier_judge
from ._judge_config import load_judge_config
from ._score import score_payload
from ._scoring import ScoringPlan, aggregate, build_scoring_plan, normalize_checks


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
                    json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
                    + "\n"
                ).encode("utf-8", errors="backslashreplace")
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
        # Harbor owns process termination when invoked through a Job. Direct API
        # callers must control script completion; cancellation drains this worker.
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


def _builtin_checks(runtime: EffectiveRuntimeConfig, config: dict) -> list[dict]:
    trajectory = Trajectory(
        **_load_object(
            Path(runtime.paths.agent_logs) / "trajectory.json", limit_mib=128
        )
    )
    return evaluate(trajectory, config, Path(runtime.paths.artifacts))


def _prepare_logs(logs: Path) -> None:
    logs.mkdir(parents=True, exist_ok=True)
    for name in (
        "reward.json",
        "reward.txt",
        "checks.json",
        "score.json",
        "custom-stdout.txt",
        "custom-stderr.txt",
        "verifier-error.txt",
    ):
        (logs / name).unlink(missing_ok=True)


async def run_verifier(
    config_path: str | Path,
    *,
    runtime: EffectiveRuntimeConfig | None = None,
    judge_settings: JudgeSettings | None = None,
) -> dict[str, Any]:
    """Run scoring and publish its files, returning the complete score payload.

    Explicit runtime and Judge settings replace their environment-derived values.
    Blocking work runs in threads that settle before cancellation returns.
    Concurrent invocations require separate verifier-log directories.
    """
    config_path = await run_blocking(Path(config_path).resolve)
    if runtime is None:
        runtime = await run_blocking(optional_effective_runtime_config)
    if runtime is None:
        raise RuntimeConfigError("run_verifier requires runtime or PEVAL_CONFIG")
    verifier_logs = Path(runtime.paths.verifier_logs)
    await run_blocking(_prepare_logs, verifier_logs)
    try:
        await run_blocking(clear_judge_outputs, verifier_logs)
        config = await run_blocking(_load_object, config_path)
        plan = await run_blocking(build_scoring_plan, config)
        judge_path = config_path.parent / "judge.yaml"
        judge_config = (
            await run_blocking(load_judge_config, judge_path)
            if await run_blocking(judge_path.exists)
            else None
        )
        settings = judge_settings
        if settings is None:
            settings = JudgeSettings.from_env() if judge_config else JudgeSettings()
        script = config_path.parent / "test_outputs.py"
        if bool(plan.custom_ids) != await run_blocking(script.is_file):
            raise ValueError(
                "custom_checks and test_outputs.py must both be present or absent"
            )
        checks = []
        if plan.requires_trajectory:
            checks.extend(await run_blocking(_builtin_checks, runtime, config))
        if plan.custom_ids:
            checks.extend(await run_blocking(_custom_checks, script, runtime, plan))
        rewards = await run_blocking(aggregate, checks, plan=plan)
        judge = await run_verifier_judge(
            judge_config, runtime, settings, rule_rewards=rewards
        )
        rewards, merge = merge_scores(rewards, judge_config, judge)
        result = score_payload(
            await run_blocking(normalize_checks, checks, plan=plan),
            rewards,
            judge_config,
            judge,
            merge,
        )
        await run_blocking(_write_json, verifier_logs / "score.json", result)
        await run_blocking(_write_json, verifier_logs / "reward.json", rewards)
    except Exception:
        await run_blocking(
            (verifier_logs / "verifier-error.txt").write_text,
            traceback.format_exc(),
            encoding="utf-8",
            errors="backslashreplace",
        )
        raise
    return result
