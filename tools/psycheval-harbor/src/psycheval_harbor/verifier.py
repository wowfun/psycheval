from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from harbor.models.trajectories import Trajectory


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
    reward = int(all(check["passed"] for check in checks))
    verifier_logs.mkdir(parents=True, exist_ok=True)
    (verifier_logs / "checks.json").write_text(
        json.dumps({"checks": checks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (verifier_logs / "reward.json").write_text(
        json.dumps({"reward": reward}, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return 0


def grade(
    trajectory: Trajectory, config: dict[str, Any], artifacts_dir: Path
) -> list[dict[str, Any]]:
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
        tool_name = _required_string(rule, "tool")
        tool_candidates = [
            candidate
            for candidate in calls
            if candidate[0] > cursor and candidate[1].function_name == tool_name
        ]
        checks.append(
            _check(
                f"required_call_{rule_number}_tool",
                bool(tool_candidates),
                f"found {len(tool_candidates)} ordered {tool_name} call(s)",
            )
        )
        argument_candidates = [
            candidate
            for candidate in tool_candidates
            if _arguments_match(candidate[1].arguments, rule)
        ]
        checks.append(
            _check(
                f"required_call_{rule_number}_arguments",
                bool(argument_candidates),
                "a call has the required argument values, terms, and URL",
            )
        )
        paired_candidates = [
            candidate
            for candidate in argument_candidates
            if _has_successful_observation(candidate[2], rule)
        ]
        checks.append(
            _check(
                f"required_call_{rule_number}_observation",
                bool(paired_candidates),
                "the same call has a matching non-error observation",
            )
        )
        if paired_candidates:
            cursor = paired_candidates[0][0]

    forbidden_tools = set(_string_list(config.get("forbidden_tools")))
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
                not invalid,
                "all required artifacts are rooted, regular, non-empty, and valid"
                if not invalid
                else "invalid: " + "; ".join(invalid),
            )
        )
    return checks


def _arguments_match(arguments: dict[str, Any], rule: dict[str, Any]) -> bool:
    argument_values = rule.get("argument_values", {})
    if not isinstance(argument_values, dict) or not all(
        isinstance(key, str) for key in argument_values
    ):
        raise ValueError("verifier 'argument_values' must be an object")
    if any(arguments.get(key) != value for key, value in argument_values.items()):
        return False
    argument_terms = _string_list(rule.get("argument_terms"))
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
    terms = _string_list(rule.get("observation_terms"))
    for observation in observations:
        extra = observation.extra or {}
        status = str(extra.get("status") or "").lower()
        if bool(extra.get("is_error")) or status in {
            "failed",
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


def _required_string(config: dict[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"verifier config requires non-empty {key!r}")
    return value


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("verifier term/artifact fields must be arrays of strings")
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


def _check(check_id: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {"id": check_id, "passed": bool(passed), "evidence": evidence}


if __name__ == "__main__":
    raise SystemExit(main())
