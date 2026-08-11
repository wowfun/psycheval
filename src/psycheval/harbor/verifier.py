from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from harbor.models.trajectories import Trajectory

_REWARD_DIMENSIONS = (
    "required_tool",
    "required_arguments",
    "required_observation",
    "forbidden_tools",
    "final_answer",
    "required_artifacts",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Grade a Psycheval web trajectory")
    parser.add_argument("config", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = _load_object(args.config)
    agent_logs = Path(os.environ.get("PSYCHEVAL_AGENT_LOGS_DIR", "/logs/agent"))
    verifier_logs = Path(
        os.environ.get("PSYCHEVAL_VERIFIER_LOGS_DIR", "/logs/verifier")
    )
    artifacts_dir = Path(os.environ.get("PSYCHEVAL_ARTIFACTS_DIR", "/logs/artifacts"))
    trajectory_data = _load_object(agent_logs / "trajectory.json")
    trajectory = Trajectory(**trajectory_data)
    checks = grade(trajectory, config, artifacts_dir)
    rewards = reward_dimensions(checks)
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


def grade(
    trajectory: Trajectory, config: dict[str, Any], artifacts_dir: Path
) -> list[dict[str, Any]]:
    allowed_config_fields = {
        "required_calls",
        "forbidden_tool_names",
        "final_terms",
        "required_artifacts",
    }
    unknown_config_fields = sorted(set(config) - allowed_config_fields)
    if unknown_config_fields:
        raise ValueError(
            "verifier config contains unsupported fields: "
            + ", ".join(unknown_config_fields)
        )
    required_calls = config.get("required_calls")
    if not isinstance(required_calls, list) or not required_calls:
        raise ValueError("verifier config requires non-empty 'required_calls'")
    if not all(isinstance(rule, dict) for rule in required_calls):
        raise ValueError("verifier 'required_calls' entries must be objects")

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
        branch_tool_candidates = [
            (branch, candidate)
            for branch in branches
            for candidate in calls
            if candidate[0] > cursor
            and candidate[1].function_name in branch["tool_names"]
        ]
        accepted_names = sorted(
            {name for branch in branches for name in branch["tool_names"]}
        )
        checks.append(
            _check(
                f"required_call_{rule_number}_tool",
                "required_tool",
                bool(branch_tool_candidates),
                f"found {len(branch_tool_candidates)} ordered call branch match(es) "
                f"for exact names: {', '.join(accepted_names)}",
            )
        )
        branch_argument_candidates = [
            (branch, candidate)
            for branch, candidate in branch_tool_candidates
            if _arguments_match(candidate[1].arguments, branch)
        ]
        checks.append(
            _check(
                f"required_call_{rule_number}_arguments",
                "required_arguments",
                bool(branch_argument_candidates),
                "one exact tool branch has the required argument values, terms, "
                "and URL",
            )
        )
        branch_paired_candidates = [
            (branch, candidate)
            for branch, candidate in branch_argument_candidates
            if _has_successful_observation(candidate[2], branch)
        ]
        checks.append(
            _check(
                f"required_call_{rule_number}_observation",
                "required_observation",
                bool(branch_paired_candidates),
                "the same call in one complete branch has a matching non-error "
                "observation",
            )
        )
        if branch_paired_candidates:
            cursor = min(
                candidate[0] for _branch, candidate in branch_paired_candidates
            )

    forbidden_tools = set(
        _string_list(config.get("forbidden_tool_names"), field="forbidden_tool_names")
    )
    if forbidden_tools:
        observed_forbidden = sorted(
            {
                call.function_name
                for step in trajectory.steps
                for call in (step.tool_calls or [])
                if call.function_name in forbidden_tools
            }
        )
        checks.append(
            _check(
                "forbidden_tools",
                "forbidden_tools",
                not observed_forbidden,
                "no forbidden tools were called"
                if not observed_forbidden
                else "called: " + ", ".join(observed_forbidden),
            )
        )
    final_answer = next(
        (
            _content_text(step.message)
            for step in reversed(trajectory.steps)
            if step.source == "agent" and _content_text(step.message).strip()
        ),
        "",
    )
    final_terms = _string_list(config.get("final_terms"))
    checks.append(
        _check(
            "final_answer",
            "final_answer",
            bool(final_answer)
            and all(term.lower() in final_answer.lower() for term in final_terms),
            "final answer contains the required fact and citation evidence",
        )
    )

    required_artifacts = _string_list(config.get("required_artifacts"))
    if required_artifacts:
        invalid = [
            reason
            for relative in required_artifacts
            if (reason := _invalid_artifact(artifacts_dir, relative)) is not None
        ]
        checks.append(
            _check(
                "required_artifacts",
                "required_artifacts",
                not invalid,
                "all required artifacts are rooted, regular, non-empty, and valid"
                if not invalid
                else "invalid: " + "; ".join(invalid),
            )
        )
    return checks


def reward_dimensions(checks: list[dict[str, Any]]) -> dict[str, int]:
    """Aggregate binary check results without hiding per-dimension evidence."""
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
        tool_names = _string_list(
            branch.get("tool_names"), field="tool_names", require_non_empty=True
        )
        if any(not name for name in tool_names):
            raise ValueError("verifier 'tool_names' entries must be non-empty")
        if len(set(tool_names)) != len(tool_names):
            raise ValueError("verifier 'tool_names' entries must be unique")
        argument_values = branch.get("argument_values", {})
        if not isinstance(argument_values, dict) or not all(
            isinstance(key, str) for key in argument_values
        ):
            raise ValueError("verifier 'argument_values' must be an object")
        _string_list(branch.get("argument_terms"), field="argument_terms")
        _string_list(branch.get("observation_terms"), field="observation_terms")
        argument_url = branch.get("argument_url")
        if argument_url is not None and (
            not isinstance(argument_url, str) or not argument_url
        ):
            raise ValueError("verifier 'argument_url' must be a non-empty string")
    return branches


def _arguments_match(arguments: dict[str, Any], rule: dict[str, Any]) -> bool:
    argument_values = rule.get("argument_values", {})
    if not isinstance(argument_values, dict) or not all(
        isinstance(key, str) for key in argument_values
    ):
        raise ValueError("verifier 'argument_values' must be an object")
    if any(arguments.get(key) != value for key, value in argument_values.items()):
        return False
    argument_terms = _string_list(rule.get("argument_terms"), field="argument_terms")
    text = json.dumps(arguments, ensure_ascii=False, sort_keys=True).lower()
    if not all(term.lower() in text for term in argument_terms):
        return False
    argument_url = rule.get("argument_url")
    if argument_url is None:
        return True
    if not isinstance(argument_url, str) or not argument_url:
        raise ValueError("verifier 'argument_url' must be a non-empty string")
    return any(
        _normalize_url(value) == _normalize_url(argument_url)
        for value in _walk_strings(arguments)
    )


def _has_successful_observation(observations: list[Any], rule: dict[str, Any]) -> bool:
    terms = _string_list(rule.get("observation_terms"), field="observation_terms")
    for observation in observations:
        extra = observation.extra or {}
        status = str(extra.get("status") or "").lower()
        if bool(extra.get("is_error")) or status in {
            "error",
            "failed",
            "failure",
            "incomplete",
            "cancelled",
        }:
            continue
        content = _content_text(observation.content).lower()
        if all(term.lower() in content for term in terms):
            return True
    return False


def _invalid_artifact(artifacts_dir: Path, relative: str) -> str | None:
    relative_path = Path(relative)
    if (
        relative_path.is_absolute()
        or relative_path == Path(".")
        or ".." in relative_path.parts
    ):
        raise ValueError(
            f"required artifact {relative!r} must be a relative path below the "
            "artifact root"
        )
    root = artifacts_dir.resolve()
    candidate = artifacts_dir / relative_path
    current = artifacts_dir
    for part in relative_path.parts:
        current = current / part
        if current.is_symlink():
            return f"{relative} is or traverses a symlink"
    try:
        candidate.resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"required artifact {relative!r} must be a relative path below the "
            "artifact root"
        ) from exc
    if not candidate.is_file():
        return f"{relative} is not a regular file"
    if candidate.stat().st_size == 0:
        return f"{relative} is empty"
    if candidate.suffix.lower() == ".png":
        with candidate.open("rb") as artifact:
            if artifact.read(8) != b"\x89PNG\r\n\x1a\n":
                return f"{relative} does not have a PNG signature"
    return None


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def _string_list(
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


def _content_text(value: Any) -> str:
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


def _check(
    check_id: str, dimension: str, passed: bool, evidence: str
) -> dict[str, Any]:
    return {
        "id": check_id,
        "dimension": dimension,
        "passed": bool(passed),
        "evidence": evidence,
    }


if __name__ == "__main__":
    raise SystemExit(main())
