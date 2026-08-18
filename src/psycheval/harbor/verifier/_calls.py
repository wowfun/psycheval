from __future__ import annotations

import json
from fnmatch import fnmatchcase
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from harbor.models.trajectories import Trajectory

_FAILURE_STATUSES = {
    "cancelled",
    "error",
    "failed",
    "failure",
    "incomplete",
    "timed_out",
    "timeout",
}


def required_call_checks(
    trajectory: Trajectory, required_calls: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    observations: dict[str, list[Any]] = {}
    for step in trajectory.steps:
        for result in step.observation.results if step.observation else []:
            if result.source_call_id:
                observations.setdefault(result.source_call_id, []).append(result)
    calls = [
        (position, call, observations.get(call.tool_call_id, []))
        for position, call in enumerate(
            call for step in trajectory.steps for call in (step.tool_calls or [])
        )
    ]

    checks: list[dict[str, Any]] = []
    cursor = -1
    for rule_number, rule in enumerate(required_calls, start=1):
        branches = _required_branches(rule, rule_number)
        tool_candidates = [
            (branch, candidate)
            for branch in branches
            for candidate in calls
            if candidate[0] > cursor
            and _tool_name_matches(candidate[1].function_name, branch["tool_names"])
        ]
        accepted_patterns = sorted(
            {pattern for branch in branches for pattern in branch["tool_names"]}
        )
        checks.append(
            _check(
                f"required_call_{rule_number}_tool",
                "required_tool",
                bool(tool_candidates),
                f"found {len(tool_candidates)} ordered call branch match(es) "
                f"for tool patterns: {', '.join(accepted_patterns)}",
            )
        )
        argument_candidates = [
            (branch, candidate)
            for branch, candidate in tool_candidates
            if _arguments_match(candidate[1].arguments, branch)
        ]
        checks.append(
            _check(
                f"required_call_{rule_number}_arguments",
                "required_arguments",
                bool(argument_candidates),
                "one matched tool branch has the required argument values, terms, "
                "and URL",
            )
        )
        paired_candidates = [
            (branch, candidate)
            for branch, candidate in argument_candidates
            if _has_successful_observation(candidate[2], branch)
        ]
        checks.append(
            _check(
                f"required_call_{rule_number}_observation",
                "required_observation",
                bool(paired_candidates),
                "the same call in one complete branch has a matching successful "
                "observation",
            )
        )
        if paired_candidates:
            cursor = min(candidate[0] for _branch, candidate in paired_candidates)
    return checks


def forbidden_tool_check(trajectory: Trajectory, patterns: list[str]) -> dict[str, Any]:
    _validate_tool_patterns(patterns, field="forbidden_tool_names")
    observed = sorted(
        {
            call.function_name
            for step in trajectory.steps
            for call in (step.tool_calls or [])
            if _tool_name_matches(call.function_name, patterns)
        }
    )
    return _check(
        "forbidden_tools",
        "forbidden_tools",
        not observed,
        "no forbidden tools were called"
        if not observed
        else "called: " + ", ".join(observed),
    )


def string_list(
    value: Any, *, field: str = "term/artifact fields", require_non_empty: bool = False
) -> list[str]:
    if value is None:
        if require_non_empty:
            raise ValueError(f"verifier {field!r} must be a non-empty array of strings")
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"verifier {field!r} must be an array of strings")
    if require_non_empty and not value:
        raise ValueError(f"verifier {field!r} must be a non-empty array of strings")
    return value


def content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            text = getattr(item, "text", None)
            if isinstance(text, str):
                parts.append(text)
        return "\n".join(parts)
    return ""


def _required_branches(rule: dict[str, Any], rule_number: int) -> list[dict[str, Any]]:
    if set(rule) != {"any"}:
        raise ValueError(
            f"verifier required_calls[{rule_number - 1}] must contain only 'any'"
        )
    branches = rule.get("any")
    if not isinstance(branches, list) or not branches:
        raise ValueError(
            f"verifier required_calls[{rule_number - 1}].any must be a non-empty list"
        )
    allowed_fields = {
        "tool_names",
        "argument_values",
        "argument_terms",
        "argument_url",
        "observation_terms",
    }
    for branch_number, branch in enumerate(branches):
        if not isinstance(branch, dict):
            raise ValueError(
                f"verifier required_calls[{rule_number - 1}].any[{branch_number}] "
                "must be an object"
            )
        unknown = sorted(set(branch) - allowed_fields)
        if unknown:
            raise ValueError(
                f"verifier branch contains unsupported fields: {', '.join(unknown)}"
            )
        tool_names = string_list(
            branch.get("tool_names"), field="tool_names", require_non_empty=True
        )
        _validate_tool_patterns(tool_names, field="tool_names")
        argument_values = branch.get("argument_values", {})
        if not isinstance(argument_values, dict) or not all(
            isinstance(key, str) for key in argument_values
        ):
            raise ValueError("verifier 'argument_values' must be an object")
        string_list(branch.get("argument_terms"), field="argument_terms")
        string_list(branch.get("observation_terms"), field="observation_terms")
        argument_url = branch.get("argument_url")
        if argument_url is not None and (
            not isinstance(argument_url, str) or not argument_url
        ):
            raise ValueError("verifier 'argument_url' must be a non-empty string")
    return branches


def _validate_tool_patterns(patterns: list[str], *, field: str) -> None:
    if any(not pattern for pattern in patterns):
        raise ValueError(f"verifier {field!r} entries must be non-empty")
    if len(set(patterns)) != len(patterns):
        raise ValueError(f"verifier {field!r} entries must be unique")


def _tool_name_matches(name: str, patterns: list[str]) -> bool:
    return any(fnmatchcase(name, pattern) for pattern in patterns)


def _arguments_match(arguments: dict[str, Any], rule: dict[str, Any]) -> bool:
    argument_values = rule.get("argument_values", {})
    if any(arguments.get(key) != value for key, value in argument_values.items()):
        return False
    terms = string_list(rule.get("argument_terms"), field="argument_terms")
    text = json.dumps(arguments, ensure_ascii=False, sort_keys=True).lower()
    if not all(term.lower() in text for term in terms):
        return False
    argument_url = rule.get("argument_url")
    if argument_url is None:
        return True
    return any(
        _normalize_url(value) == _normalize_url(argument_url)
        for value in _walk_strings(arguments)
    )


def _has_successful_observation(observations: list[Any], rule: dict[str, Any]) -> bool:
    terms = string_list(rule.get("observation_terms"), field="observation_terms")
    for observation in observations:
        extra = observation.extra or {}
        status = str(extra.get("status") or "").lower()
        exit_code = extra.get("exit_code")
        if (
            bool(extra.get("is_error"))
            or status in _FAILURE_STATUSES
            or exit_code not in {None, 0, "0"}
        ):
            continue
        content = content_text(observation.content).lower()
        if all(term.lower() in content for term in terms):
            return True
    return False


def _walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def _normalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            parsed.query,
            "",
        )
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
