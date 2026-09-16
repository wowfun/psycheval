"""Declared scoring items and pure weighted aggregation."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from ._calls import _required_branches, _validate_tool_patterns, string_list

BUILTIN_FIELDS = frozenset(
    ("required_calls", "forbidden_tool_names", "final_terms", "required_artifacts")
)
REWARD_DIMENSIONS = (
    "required_tool",
    "required_arguments",
    "required_observation",
    "forbidden_tools",
    "final_answer",
    "required_artifacts",
    "custom_outputs",
)


@dataclass(frozen=True)
class ScoringItem:
    id: str
    dimension: str
    weight: float = 1.0


@dataclass(frozen=True)
class ScoringPlan:
    items: tuple[ScoringItem, ...]

    @property
    def custom_ids(self) -> tuple[str, ...]:
        return tuple(
            item.id.removeprefix("custom:")
            for item in self.items
            if item.dimension == "custom_outputs"
        )

    @property
    def requires_trajectory(self) -> bool:
        return any(item.dimension != "custom_outputs" for item in self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [asdict(item) for item in self.items],
            "total_weight": math.fsum(item.weight for item in self.items),
        }


def build_scoring_plan(config: dict[str, Any]) -> ScoringPlan:
    if not isinstance(config, dict):
        raise ValueError("verifier config must be an object")
    unknown = sorted(set(config) - BUILTIN_FIELDS - {"custom_checks", "scoring"})
    if unknown:
        raise ValueError(
            "verifier config contains unsupported fields: " + ", ".join(unknown)
        )
    calls = config.get("required_calls")
    if calls is None:
        calls = []
    elif not isinstance(calls, list) or not calls:
        raise ValueError("verifier 'required_calls' must be a non-empty array")
    if not all(isinstance(rule, dict) for rule in calls):
        raise ValueError("verifier 'required_calls' entries must be objects")
    items = []
    for index, rule in enumerate(calls, 1):
        _required_branches(rule, index)
        for suffix, dimension in (
            ("tool", "required_tool"),
            ("arguments", "required_arguments"),
            ("observation", "required_observation"),
        ):
            items.append(ScoringItem(f"required_call_{index}_{suffix}", dimension))
    patterns = string_list(
        config.get("forbidden_tool_names"), field="forbidden_tool_names"
    )
    _validate_tool_patterns(patterns, field="forbidden_tool_names")
    if patterns:
        items.append(ScoringItem("forbidden_tools", "forbidden_tools"))
    terms = string_list(config.get("final_terms"), field="final_terms")
    artifacts = string_list(
        config.get("required_artifacts"), field="required_artifacts"
    )
    if calls or patterns or terms or artifacts:
        items.append(ScoringItem("final_answer", "final_answer"))
    if artifacts:
        items.append(ScoringItem("required_artifacts", "required_artifacts"))
    custom = string_list(config.get("custom_checks"), field="custom_checks")
    if any(not name.strip() for name in custom) or len(custom) != len(set(custom)):
        raise ValueError("custom_checks must contain unique nonempty IDs")
    items.extend(ScoringItem(f"custom:{name}", "custom_outputs") for name in custom)
    if not items:
        raise ValueError("verifier config requires at least one non-empty constraint")
    scoring = config.get("scoring", {})
    if not isinstance(scoring, dict) or set(scoring) - {"weights"}:
        raise ValueError("scoring must be an object containing only weights")
    weights = scoring.get("weights", {})
    if not isinstance(weights, dict) or set(weights) - {item.id for item in items}:
        raise ValueError("scoring.weights must map declared check IDs to weights")
    for weight in weights.values():
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(weight)
            or weight < 0
        ):
            raise ValueError("scoring weights must be finite nonnegative numbers")
    items = [
        ScoringItem(item.id, item.dimension, float(weights.get(item.id, 1)))
        for item in items
    ]
    try:
        total = math.fsum(item.weight for item in items)
    except OverflowError as exc:
        raise ValueError("total scoring weight must be finite") from exc
    if not math.isfinite(total) or total <= 0:
        raise ValueError("total scoring weight must be finite and positive")
    return ScoringPlan(tuple(items))


def normalize_checks(
    checks: list[dict[str, Any]], *, plan: ScoringPlan
) -> list[dict[str, Any]]:
    declared = {item.id: item for item in plan.items}
    received = {}
    if not isinstance(checks, list):
        raise ValueError("checks must be an array")
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("each check must be an object")
        check_id = check.get("id")
        if not isinstance(check_id, str) or check_id not in declared:
            raise ValueError(f"unknown check ID: {check_id!r}")
        if check_id in received:
            raise ValueError(f"duplicate check ID: {check_id}")
        if type(check.get("passed")) is not bool:
            raise ValueError(f"check {check_id}: passed must be boolean")
        if not isinstance(check.get("evidence", ""), str):
            raise ValueError(f"check {check_id}: evidence must be text")
        if (
            check.get("dimension", declared[check_id].dimension)
            != declared[check_id].dimension
        ):
            raise ValueError(f"check {check_id}: incorrect dimension")
        received[check_id] = check
    return [
        {
            "id": item.id,
            "dimension": item.dimension,
            "weight": item.weight,
            "passed": received.get(item.id, {}).get("passed", False),
            "evidence": received.get(item.id, {}).get(
                "evidence",
                "Declared check was not reported" if item.id not in received else "",
            ),
            "missing": item.id not in received,
        }
        for item in plan.items
    ]


def aggregate(checks: list[dict[str, Any]], *, plan: ScoringPlan) -> dict[str, float]:
    normalized = normalize_checks(checks, plan=plan)

    def weighted(values):
        total = math.fsum(check["weight"] for check in values)
        return (
            math.fsum(check["weight"] for check in values if check["passed"]) / total
            if total
            else 1.0
        )

    return {
        "reward": weighted(normalized),
        **{
            dimension: weighted(
                [check for check in normalized if check["dimension"] == dimension]
            )
            for dimension in REWARD_DIMENSIONS
        },
    }
