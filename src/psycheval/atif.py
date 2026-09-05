"""Standalone ATIF-v1.7 recognition and strict, non-mutating validation."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ATIF_VERSION = "ATIF-v1.7"


ATIF_TRAJECTORY_KEYS = {
    "schema_version",
    "session_id",
    "trajectory_id",
    "agent",
    "steps",
    "notes",
    "final_metrics",
    "continued_trajectory_ref",
    "extra",
    "subagent_trajectories",
}


ATIF_AGENT_KEYS = {"name", "version", "model_name", "tool_definitions", "extra"}


ATIF_STEP_KEYS = {
    "step_id",
    "timestamp",
    "source",
    "model_name",
    "reasoning_effort",
    "message",
    "reasoning_content",
    "tool_calls",
    "observation",
    "metrics",
    "is_copied_context",
    "llm_call_count",
    "extra",
}


ATIF_TOOL_CALL_KEYS = {"tool_call_id", "function_name", "arguments", "extra"}


ATIF_OBSERVATION_KEYS = {"results"}


ATIF_OBSERVATION_RESULT_KEYS = {
    "source_call_id",
    "content",
    "subagent_trajectory_ref",
    "extra",
}


ATIF_METRICS_KEYS = {
    "prompt_tokens",
    "completion_tokens",
    "cached_tokens",
    "cost_usd",
    "prompt_token_ids",
    "completion_token_ids",
    "logprobs",
    "extra",
}


ATIF_FINAL_METRICS_KEYS = {
    "total_prompt_tokens",
    "total_completion_tokens",
    "total_cached_tokens",
    "total_cost_usd",
    "total_steps",
    "extra",
}


ATIF_CONTENT_PART_KEYS = {"type", "text", "source"}


ATIF_IMAGE_SOURCE_KEYS = {"media_type", "path"}


ATIF_IMAGE_MEDIA_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


ATIF_SUBAGENT_REF_KEYS = {"trajectory_id", "session_id", "trajectory_path", "extra"}


ATIF_SOURCES = {"system", "user", "agent"}


def is_atif_json_path(path: str) -> bool:
    return read_atif_json_path(path) is not None


def read_atif_json_path(path: str) -> dict[str, Any] | None:
    source = Path(path)
    try:
        parsed = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not is_atif_trajectory(parsed):
        return None
    return parsed


def is_atif_trajectory(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    schema = str(value.get("schema_version") or "")
    return schema.startswith("ATIF-") and isinstance(value.get("agent"), dict)


def validate_atif_trajectory(trajectory: Any, path: str = "trajectory") -> None:
    """Strictly validate an ATIF-v1.7 trajectory without Harbor/Pydantic."""

    _validate_json_value(trajectory, path)
    value = _object(trajectory, path)
    reject_unknown_keys(path, value, ATIF_TRAJECTORY_KEYS)
    _required_literal(value, "schema_version", ATIF_VERSION, path)
    for key in ("session_id", "trajectory_id", "notes", "continued_trajectory_ref"):
        _optional_string(value, key, path)
    _optional_object(value, "extra", path)

    agent = _object(_required(value, "agent", path), f"{path}.agent")
    reject_unknown_keys(f"{path}.agent", agent, ATIF_AGENT_KEYS)
    _required_string(agent, "name", f"{path}.agent")
    _required_string(agent, "version", f"{path}.agent")
    _optional_string(agent, "model_name", f"{path}.agent")
    _optional_object(agent, "extra", f"{path}.agent")
    if agent.get("tool_definitions") is not None:
        definitions = _list(agent["tool_definitions"], f"{path}.agent.tool_definitions")
        for index, definition in enumerate(definitions):
            _object(definition, f"{path}.agent.tool_definitions[{index}]")

    steps = _list(_required(value, "steps", path), f"{path}.steps")
    if not steps:
        raise ValueError(f"{path}.steps must contain at least one step")

    embedded_ids: set[str] = set()
    subagents_value = value.get("subagent_trajectories")
    if subagents_value is not None:
        subagents = _list(subagents_value, f"{path}.subagent_trajectories")
        for index, subagent in enumerate(subagents):
            subpath = f"{path}.subagent_trajectories[{index}]"
            subobject = _object(subagent, subpath)
            identifier = subobject.get("trajectory_id")
            if not isinstance(identifier, str):
                raise ValueError(f"{subpath}.trajectory_id must be a string")
            if identifier in embedded_ids:
                raise ValueError(f"{subpath}.trajectory_id must be unique")
            embedded_ids.add(identifier)
            validate_atif_trajectory(subobject, subpath)

    for index, step in enumerate(steps):
        step_path = f"{path}.steps[{index}]"
        step_value = _object(step, step_path)
        _validate_atif_step(step_value, step_path, index + 1, embedded_ids)

    final_metrics = value.get("final_metrics")
    if final_metrics is not None:
        _validate_final_metrics(
            _object(final_metrics, f"{path}.final_metrics"),
            f"{path}.final_metrics",
        )


def _validate_atif_step(
    step: dict[str, Any],
    path: str,
    expected_step_id: int,
    embedded_ids: set[str],
) -> None:
    reject_unknown_keys(path, step, ATIF_STEP_KEYS)
    step_id = _required_integer(step, "step_id", path, minimum=1)
    if step_id != expected_step_id:
        raise ValueError(
            f"{path}.step_id must be {expected_step_id} (sequential from 1), got {step_id}"
        )
    source = _required_string(step, "source", path)
    if source not in ATIF_SOURCES:
        raise ValueError(f"{path}.source must be one of: agent, system, user")
    _validate_content(_required(step, "message", path), f"{path}.message")
    _optional_iso_timestamp(step, "timestamp", path)
    _optional_string(step, "model_name", path)
    _optional_string(step, "reasoning_content", path)
    _optional_object(step, "extra", path)
    _optional_boolean(step, "is_copied_context", path)
    if step.get("reasoning_effort") is not None and not _is_number_or_string(
        step["reasoning_effort"]
    ):
        raise ValueError(f"{path}.reasoning_effort must be a string or number")
    if step.get("llm_call_count") is not None:
        _integer(step["llm_call_count"], f"{path}.llm_call_count", minimum=0)

    agent_only = (
        "model_name",
        "reasoning_effort",
        "reasoning_content",
        "tool_calls",
        "metrics",
    )
    if source != "agent":
        for key in agent_only:
            if step.get(key) is not None:
                raise ValueError(f"{path}.{key} is only valid when source is agent")
    if source == "agent" and step.get("llm_call_count") == 0:
        for key in ("metrics", "reasoning_content"):
            if step.get(key) is not None:
                raise ValueError(
                    f"{path}.{key} must be absent when llm_call_count is 0"
                )

    tool_ids: set[str] = set()
    if step.get("tool_calls") is not None:
        calls = _list(step["tool_calls"], f"{path}.tool_calls")
        for index, call in enumerate(calls):
            call_path = f"{path}.tool_calls[{index}]"
            call_value = _object(call, call_path)
            reject_unknown_keys(call_path, call_value, ATIF_TOOL_CALL_KEYS)
            call_id = _required_string(call_value, "tool_call_id", call_path)
            if call_id in tool_ids:
                raise ValueError(
                    f"{call_path}.tool_call_id must be unique within the step"
                )
            tool_ids.add(call_id)
            _required_string(call_value, "function_name", call_path)
            _object(
                _required(call_value, "arguments", call_path), f"{call_path}.arguments"
            )
            _optional_object(call_value, "extra", call_path)

    if step.get("observation") is not None:
        observation_path = f"{path}.observation"
        observation = _object(step["observation"], observation_path)
        reject_unknown_keys(observation_path, observation, ATIF_OBSERVATION_KEYS)
        results = _list(
            _required(observation, "results", observation_path),
            f"{observation_path}.results",
        )
        for index, result in enumerate(results):
            result_path = f"{observation_path}.results[{index}]"
            result_value = _object(result, result_path)
            reject_unknown_keys(result_path, result_value, ATIF_OBSERVATION_RESULT_KEYS)
            _optional_string(result_value, "source_call_id", result_path)
            _optional_object(result_value, "extra", result_path)
            if result_value.get("content") is not None:
                _validate_content(result_value["content"], f"{result_path}.content")
            source_call_id = result_value.get("source_call_id")
            if source_call_id is not None and source_call_id not in tool_ids:
                raise ValueError(
                    f"{result_path}.source_call_id does not reference a tool call in the same step"
                )
            refs = result_value.get("subagent_trajectory_ref")
            if refs is not None:
                _validate_subagent_refs(
                    refs, f"{result_path}.subagent_trajectory_ref", embedded_ids
                )

    if step.get("metrics") is not None:
        _validate_metrics(
            _object(step["metrics"], f"{path}.metrics"), f"{path}.metrics"
        )


def _validate_metrics(metrics: dict[str, Any], path: str) -> None:
    reject_unknown_keys(path, metrics, ATIF_METRICS_KEYS)
    for key in ("prompt_tokens", "completion_tokens", "cached_tokens"):
        if metrics.get(key) is not None:
            _integer(metrics[key], f"{path}.{key}", minimum=0)
    if metrics.get("cost_usd") is not None:
        _number(metrics["cost_usd"], f"{path}.cost_usd", minimum=0)
    for key in ("prompt_token_ids", "completion_token_ids"):
        if metrics.get(key) is not None:
            values = _list(metrics[key], f"{path}.{key}")
            for index, value in enumerate(values):
                _integer(value, f"{path}.{key}[{index}]")
    if metrics.get("logprobs") is not None:
        values = _list(metrics["logprobs"], f"{path}.logprobs")
        for index, value in enumerate(values):
            _number(value, f"{path}.logprobs[{index}]")
    _optional_object(metrics, "extra", path)
    prompt = metrics.get("prompt_tokens")
    cached = metrics.get("cached_tokens")
    if cached is not None and prompt is None:
        raise ValueError(f"{path}.prompt_tokens is required when cached_tokens is set")
    if cached is not None and prompt is not None and cached > prompt:
        raise ValueError(f"{path}.cached_tokens must not exceed prompt_tokens")


def _validate_final_metrics(metrics: dict[str, Any], path: str) -> None:
    reject_unknown_keys(path, metrics, ATIF_FINAL_METRICS_KEYS)
    for key in (
        "total_prompt_tokens",
        "total_completion_tokens",
        "total_cached_tokens",
        "total_steps",
    ):
        if metrics.get(key) is not None:
            _integer(metrics[key], f"{path}.{key}", minimum=0)
    if metrics.get("total_cost_usd") is not None:
        _number(metrics["total_cost_usd"], f"{path}.total_cost_usd", minimum=0)
    _optional_object(metrics, "extra", path)
    prompt = metrics.get("total_prompt_tokens")
    cached = metrics.get("total_cached_tokens")
    if cached is not None and prompt is None:
        raise ValueError(
            f"{path}.total_prompt_tokens is required when total_cached_tokens is set"
        )
    if cached is not None and prompt is not None and cached > prompt:
        raise ValueError(
            f"{path}.total_cached_tokens must not exceed total_prompt_tokens"
        )


def _validate_content(value: Any, path: str) -> None:
    if isinstance(value, str):
        return
    parts = _list(value, path)
    for index, part in enumerate(parts):
        part_path = f"{path}[{index}]"
        part_value = _object(part, part_path)
        reject_unknown_keys(part_path, part_value, ATIF_CONTENT_PART_KEYS)
        part_type = _required_string(part_value, "type", part_path)
        if part_type == "text":
            _required_string(part_value, "text", part_path)
            if part_value.get("source") is not None:
                raise ValueError(f"{part_path}.source must be absent for text content")
        elif part_type == "image":
            if part_value.get("text") is not None:
                raise ValueError(f"{part_path}.text must be absent for image content")
            source_path = f"{part_path}.source"
            source = _object(_required(part_value, "source", part_path), source_path)
            reject_unknown_keys(source_path, source, ATIF_IMAGE_SOURCE_KEYS)
            media_type = _required_string(source, "media_type", source_path)
            if media_type not in ATIF_IMAGE_MEDIA_TYPES:
                raise ValueError(
                    f"{source_path}.media_type is not a supported image MIME type"
                )
            _required_string(source, "path", source_path)
        else:
            raise ValueError(f"{part_path}.type must be text or image")


def _validate_subagent_refs(value: Any, path: str, embedded_ids: set[str]) -> None:
    refs = _list(value, path)
    for index, ref in enumerate(refs):
        ref_path = f"{path}[{index}]"
        ref_value = _object(ref, ref_path)
        reject_unknown_keys(ref_path, ref_value, ATIF_SUBAGENT_REF_KEYS)
        for key in ("trajectory_id", "session_id", "trajectory_path"):
            _optional_string(ref_value, key, ref_path)
        _optional_object(ref_value, "extra", ref_path)
        trajectory_id = ref_value.get("trajectory_id")
        trajectory_path = ref_value.get("trajectory_path")
        if trajectory_id is None and trajectory_path is None:
            raise ValueError(
                f"{ref_path} must contain trajectory_id or trajectory_path"
            )
        if trajectory_path is None and trajectory_id not in embedded_ids:
            raise ValueError(
                f"{ref_path}.trajectory_id does not reference an embedded subagent"
            )


def reject_unknown_keys(path: str, value: dict[str, Any], allowed: set[str]) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        keys = ", ".join(extra)
        raise ValueError(f"{path} contains non-ATIF field(s): {keys}")


def is_atif_content(value: Any) -> bool:
    if isinstance(value, str):
        return True
    if not isinstance(value, list):
        return False
    try:
        _validate_content(value, "content")
    except ValueError:
        return False
    return True


def iso_timestamp_ms(value: Any) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def _required(value: dict[str, Any], key: str, path: str) -> Any:
    if key not in value or value[key] is None:
        raise ValueError(f"{path}.{key} is required")
    return value[key]


def _required_string(value: dict[str, Any], key: str, path: str) -> str:
    result = _required(value, key, path)
    if not isinstance(result, str):
        raise ValueError(f"{path}.{key} must be a string")
    return result


def _required_integer(
    value: dict[str, Any], key: str, path: str, minimum: int | None = None
) -> int:
    return _integer(_required(value, key, path), f"{path}.{key}", minimum)


def _required_literal(
    value: dict[str, Any], key: str, expected: str, path: str
) -> None:
    actual = _required_string(value, key, path)
    if actual != expected:
        raise ValueError(f"{path}.{key} must be {expected}")


def _optional_string(value: dict[str, Any], key: str, path: str) -> None:
    if key in value and value[key] is not None and not isinstance(value[key], str):
        raise ValueError(f"{path}.{key} must be a string")


def _optional_boolean(value: dict[str, Any], key: str, path: str) -> None:
    if key in value and value[key] is not None and not isinstance(value[key], bool):
        raise ValueError(f"{path}.{key} must be a boolean")


def _optional_object(value: dict[str, Any], key: str, path: str) -> None:
    if key in value and value[key] is not None:
        _object(value[key], f"{path}.{key}")


def _optional_iso_timestamp(value: dict[str, Any], key: str, path: str) -> None:
    if key not in value or value[key] is None:
        return
    if not isinstance(value[key], str) or iso_timestamp_ms(value[key]) is None:
        raise ValueError(f"{path}.{key} must be an ISO 8601 timestamp")


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list")
    return value


def _integer(value: Any, path: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{path} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{path} must be at least {minimum}")
    return value


def _number(value: Any, path: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{path} must be finite")
    if minimum is not None and number < minimum:
        raise ValueError(f"{path} must be at least {minimum}")
    return number


def _is_number_or_string(value: Any) -> bool:
    if isinstance(value, str):
        return True
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _validate_json_value(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must be finite JSON data")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string JSON key")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise ValueError(f"{path} must contain only JSON-compatible values")
