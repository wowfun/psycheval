"""Office-shaped score publication, independent of the WorkBuddy runtime."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ._judge_config import JudgeConfig
from ._scoring import REWARD_DIMENSIONS


def _verdict(
    item_id: str,
    status: str,
    reason: str,
    *,
    llm: bool = False,
    evidence_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "status": status,
        "judge_name": "llm_judge" if llm else "rule",
        "judge_type": "llm_judge" if llm else "rule_script",
        "score": None if status == "abstain" else float(status == "pass"),
        "evidence_ids": evidence_ids or [],
        "reason": reason,
        "confidence": None,
        "metadata": metadata or {},
    }


def _group(
    verdicts: list[dict[str, Any]],
    *,
    status: str,
    scores: dict[str, float],
    metadata: dict[str, Any],
    llm: bool = False,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "judge_name": "llm_judge" if llm else "rule",
        "judge_type": "llm_judge" if llm else "rule_script",
        "judge_family": "llm" if llm else "rule",
        "status": status,
        "ok": True,  # Rule failures and optional Judge abstentions are not fatal.
        "verdicts": verdicts,
        "scores": scores,
        "evidence_ids": list(
            dict.fromkeys(
                ref for verdict in verdicts for ref in verdict["evidence_ids"]
            )
        ),
        "errors": errors or [],
        "metadata": metadata,
    }


def score_payload(
    checks: list[dict[str, Any]],
    rewards: dict[str, float],
    judge_config: JudgeConfig | None,
    judge: dict[str, Any],
    merge: dict[str, Any],
) -> dict[str, Any]:
    """Serialize completed scoring without recalculating or rounding rewards."""
    rule_verdicts = [
        _verdict(
            check["id"],
            "pass" if check["passed"] else "fail",
            check["evidence"],
            metadata={key: check[key] for key in ("dimension", "weight", "missing")},
        )
        for check in checks
    ]
    passed = sum(check["passed"] for check in checks)
    pass_rate = passed / len(checks) if checks else 0.0
    judges = [
        _group(
            rule_verdicts,
            status="pass" if passed == len(checks) else "fail",
            scores={
                "pass_rate": pass_rate,
                "overall": rewards["rule_score"],
                **{key: rewards[key] for key in REWARD_DIMENSIONS},
            },
            metadata={"tests_passed": passed, "tests_total": len(checks)},
        )
    ]
    merge_metadata = {
        "method": "weighted_sum" if judge_config else "none",
        **merge,
        "rule_score": rewards["rule_score"],
        "overall": rewards["reward"],
    }
    records = []
    if judge_config is not None:
        config = judge_config.to_dict()
        complete = judge["status"] == "complete"
        outcomes = {check["id"]: check for check in judge["checks"]}
        errors = judge.get("errors", {})
        llm_verdicts = []
        for rubric in config["llm_judge"]["rubrics"]:
            outcome = outcomes.get(rubric["id"])
            llm_verdicts.append(
                _verdict(
                    "llm:" + rubric["id"],
                    ("pass" if outcome["passed"] else "fail") if outcome else "abstain",
                    outcome["reason"]
                    if outcome
                    else errors.get(rubric["id"], judge["reason"]),
                    llm=True,
                    evidence_ids=rubric["artifact_refs"],
                    metadata={
                        "rubric": rubric,
                        **(
                            {"missing": outcome["missing"]}
                            if outcome and "missing" in outcome
                            else {}
                        ),
                    },
                )
            )
        judges.append(
            _group(
                llm_verdicts,
                llm=True,
                status="pass" if complete else "abstain",
                scores={
                    "llm_judge": rewards["llm_score"],
                    "rubric_binary_mean": rewards["llm_score"],
                }
                if complete
                else {},
                errors=[f"{key}: {value}" for key, value in errors.items()],
                metadata={
                    "judge_status": judge["status"],
                    "reason": judge["reason"],
                    "context": judge.get("context"),
                    "settings": judge.get("settings"),
                    **(
                        {"duration_sec": judge["elapsed_sec"]}
                        if "elapsed_sec" in judge
                        else {}
                    ),
                },
            )
        )
        merge_metadata.update(
            rule_weight=judge_config.rule_weight, llm_weight=judge_config.llm_weight
        )
        records = [
            {
                "id": item["id"],
                "type": item["type"],
                "uri": item["path"],
                "metadata": {"required": item["required"]},
            }
            for item in config["artifacts"]
        ]
    # Office's envelope requires both judge-local and flattened verdicts.
    # Keep both views identical; removing either would change that protocol.
    verdicts = [verdict for group in judges for verdict in group["verdicts"]]
    counts = Counter(verdict["status"] for verdict in verdicts)
    if "llm_score" in rewards:
        merge_metadata["llm_score"] = rewards["llm_score"]
    reward = rewards["reward"]
    return {
        "reward": reward,
        "overall": reward,
        "test_status": "full_pass"
        if reward == 1
        else "partial_pass"
        if reward > 0
        else "no_pass",
        "test_pass_rate": pass_rate,
        "tests_passed": passed,
        "tests_total": len(checks),
        **(
            {"llm_judge_component_score": rewards["llm_score"]}
            if "llm_score" in rewards
            else {}
        ),
        "verdicts": verdicts,
        "judges": judges,
        "diagnostics": {
            "status_counts": {
                key: counts[key]
                for key in (
                    "pass",
                    "fail",
                    "review",
                    "abstain",
                    "build_error",
                    "judge_error",
                )
            },
            "evidence": {"records": records, "metadata": {}},
        },
        "metadata": {"scoring_policy": "weighted_mean", "score_merge": merge_metadata},
    }
