from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from harbor.models.trajectories import Trajectory

from ._artifacts import resolve_required_artifacts
from ._calls import (
    content_text,
    forbidden_tool_check,
    required_call_checks,
    string_list,
)

_CONFIG_FIELDS = {
    "required_calls",
    "forbidden_tool_names",
    "final_terms",
    "required_artifacts",
}
_REWARD_DIMENSIONS = (
    "required_tool",
    "required_arguments",
    "required_observation",
    "forbidden_tools",
    "final_answer",
    "required_artifacts",
)


def evaluate(
    trajectory: Trajectory, config: dict[str, Any], artifacts_dir: Path
) -> list[dict[str, Any]]:
    """Evaluate one step-local trajectory and its current artifacts."""
    unknown_fields = sorted(set(config) - _CONFIG_FIELDS)
    if unknown_fields:
        raise ValueError(
            "verifier config contains unsupported fields: " + ", ".join(unknown_fields)
        )
    if not any(config.get(field) for field in _CONFIG_FIELDS):
        raise ValueError("verifier config requires at least one non-empty constraint")

    required_calls = config.get("required_calls")
    if required_calls is None:
        required_calls = []
    elif not isinstance(required_calls, list) or not required_calls:
        raise ValueError("verifier 'required_calls' must be a non-empty array")
    if not all(isinstance(rule, dict) for rule in required_calls):
        raise ValueError("verifier 'required_calls' entries must be objects")

    checks = required_call_checks(trajectory, required_calls)
    forbidden_patterns = string_list(
        config.get("forbidden_tool_names"), field="forbidden_tool_names"
    )
    if forbidden_patterns:
        checks.append(forbidden_tool_check(trajectory, forbidden_patterns))
    checks.extend(_outcome_checks(trajectory, config, artifacts_dir))
    return checks


def aggregate(checks: list[dict[str, Any]]) -> dict[str, int]:
    """Aggregate binary checks without hiding per-dimension evidence."""
    grouped: dict[str, list[bool]] = {dimension: [] for dimension in _REWARD_DIMENSIONS}
    for check in checks:
        dimension = check.get("dimension")
        if dimension not in grouped:
            raise ValueError(f"unknown verifier check dimension: {dimension!r}")
        grouped[dimension].append(bool(check.get("passed")))
    return {
        "reward": int(all(bool(check.get("passed")) for check in checks)),
        **{dimension: int(all(results)) for dimension, results in grouped.items()},
    }


def _outcome_checks(
    trajectory: Trajectory, config: dict[str, Any], artifacts_dir: Path
) -> list[dict[str, Any]]:
    final_answer = next(
        (
            content_text(step.message)
            for step in reversed(trajectory.steps)
            if step.source == "agent" and content_text(step.message).strip()
        ),
        "",
    )
    final_terms = string_list(config.get("final_terms"))
    required_artifacts = string_list(
        config.get("required_artifacts"), field="required_artifacts"
    )
    resolved_artifacts, invalid_artifacts = resolve_required_artifacts(
        artifacts_dir, required_artifacts
    )
    missing_terms = [
        term for term in final_terms if term.lower() not in final_answer.lower()
    ]
    missing_references = [
        relative
        for relative in resolved_artifacts
        if not _mentions_exact_path(final_answer, relative)
    ]
    failures = []
    if not final_answer.strip():
        failures.append("final answer is empty")
    if missing_terms:
        failures.append("missing terms: " + ", ".join(missing_terms))
    if missing_references:
        failures.append("missing artifact paths: " + ", ".join(missing_references))

    checks = [
        _check(
            "final_answer",
            "final_answer",
            not failures,
            "final answer contains the required terms and artifact paths"
            if not failures
            else "; ".join(failures),
        )
    ]
    if required_artifacts:
        checks.append(
            _check(
                "required_artifacts",
                "required_artifacts",
                not invalid_artifacts,
                "all required artifact patterns matched valid files"
                if not invalid_artifacts
                else "invalid: " + "; ".join(invalid_artifacts),
            )
        )
    return checks


def _mentions_exact_path(content: str, relative: str) -> bool:
    path_character = r"[\w./\\-]"
    return (
        re.search(
            rf"(?<!{path_character}){re.escape(relative)}(?!{path_character})",
            content,
        )
        is not None
    )


def _check(
    check_id: str, dimension: str, passed: bool, evidence: str
) -> dict[str, Any]:
    return {
        "id": check_id,
        "dimension": dimension,
        "passed": bool(passed),
        "evidence": evidence,
    }
