from __future__ import annotations

import json
import math
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from peval_py.adapters import adapter_for
from peval_py.adapters.base import (
    TIMESTAMP_SEMANTICS_ORDER_ONLY,
    ConversionResult,
    ObservationMeta,
    StepMeta,
    ToolMeta,
)
from peval_py.config import ToolConfig
from peval_py.sources import MessageRecord, read_jsonl, read_sqlite_messages

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


def convert_records(
    records: list[MessageRecord], config: ToolConfig
) -> ConversionResult:
    adapter = adapter_for(config.adapter)
    convert = getattr(adapter, "convert", None)
    if not callable(convert):
        raise ValueError(f"adapter {config.adapter} does not support record input")
    return finalize_atif_conversion(convert(records, config))


def convert_path(path: str, config: ToolConfig) -> ConversionResult:
    atif = convert_atif_json_path(path)
    if atif is not None:
        return atif
    adapter = adapter_for(config.adapter)
    adapter_convert_path = getattr(adapter, "convert_path", None)
    if callable(adapter_convert_path):
        return finalize_atif_conversion(adapter_convert_path(path, config))
    convert = getattr(adapter, "convert", None)
    if not callable(convert):
        raise ValueError(f"adapter {config.adapter} does not support path input")
    return finalize_atif_conversion(convert(read_jsonl(path), config))


def convert_db(
    path: str,
    session_id: str | None,
    config: ToolConfig,
) -> ConversionResult:
    adapter = adapter_for(config.adapter)
    adapter_convert_db = getattr(adapter, "convert_db", None)
    if callable(adapter_convert_db):
        return finalize_atif_conversion(adapter_convert_db(path, session_id, config))
    if not session_id:
        raise ValueError(f"adapter {config.adapter} requires --session-id for DB input")
    convert = getattr(adapter, "convert", None)
    if not callable(convert):
        raise ValueError(f"adapter {config.adapter} does not support DB input")
    return finalize_atif_conversion(
        convert(read_sqlite_messages(path, session_id, config.db), config)
    )


def finalize_atif_conversion(result: ConversionResult) -> ConversionResult:
    """Project adapter output into canonical ATIF-v1.7 and validate it.

    This function is intentionally the only repair boundary. Imported ATIF uses
    :func:`validate_atif_trajectory` directly and is never normalized here.
    """

    trajectory = deepcopy(result.trajectory)
    trajectory["schema_version"] = ATIF_VERSION
    agent = trajectory.get("agent")
    if not isinstance(agent, dict):
        agent = {}
        trajectory["agent"] = agent

    session_id = trajectory.get("session_id")
    agent_name = agent.get("name")
    trajectory.pop("trajectory_id", None)
    if isinstance(session_id, str) and session_id and isinstance(agent_name, str):
        trajectory["trajectory_id"] = f"{agent_name}:{session_id}"

    steps = trajectory.get("steps")
    if not isinstance(steps, list):
        validate_atif_trajectory(trajectory)
        raise AssertionError("unreachable")
    steps_meta = deepcopy(result.steps_meta)
    step_meta = {item.step_id: item for item in steps_meta}
    warnings = list(result.warnings)
    has_portable_timestamp = False
    timestamp_semantics = result.timestamp_semantics
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        meta = step_meta.get(step.get("step_id"))
        if meta is None and index < len(result.steps_meta):
            meta = result.steps_meta[index]
        if meta is not None:
            has_portable_timestamp = (
                _project_step_runtime_facts(step, meta, timestamp_semantics)
                or has_portable_timestamp
            )
        _normalize_converted_step(step, warnings, f"trajectory.steps[{index}]")
        if meta is not None:
            _align_observation_meta(step, meta)

    root_extra = _dict_or_empty(trajectory.get("extra"))
    if timestamp_semantics:
        root_extra["timestamp_semantics"] = timestamp_semantics
    elif has_portable_timestamp:
        root_extra["timestamp_semantics"] = "utc_epoch_milliseconds"
    if root_extra:
        trajectory["extra"] = root_extra
    else:
        trajectory.pop("extra", None)

    trajectory["final_metrics"] = _aggregate_final_metrics(trajectory)
    validate_atif_trajectory(trajectory)
    return replace(
        result,
        trajectory=trajectory,
        steps_meta=steps_meta,
        warnings=warnings,
    )


def _finalize_atif_session_context(
    result: ConversionResult, session_id: str | None
) -> ConversionResult:
    """Attach a source-owned stable session before final canonicalization."""

    if not session_id or result.trajectory.get("session_id") is not None:
        return result
    trajectory = deepcopy(result.trajectory)
    trajectory["session_id"] = str(session_id)
    return finalize_atif_conversion(replace(result, trajectory=trajectory))


def convert_atif_json_path(path: str) -> ConversionResult | None:
    parsed = read_atif_json_path(path)
    if parsed is None:
        return None
    return convert_atif_trajectory(parsed)


def convert_atif_trajectory(parsed: dict[str, Any]) -> ConversionResult:
    validate_atif_trajectory(parsed)
    steps = parsed["steps"]
    meta = [step_meta_from_atif_step(index, step) for index, step in enumerate(steps)]
    timestamps = [step.timestamp_ms for step in meta if step.timestamp_ms is not None]
    root_extra = parsed.get("extra")
    timestamp_semantics = (
        str(root_extra["timestamp_semantics"])
        if isinstance(root_extra, dict)
        and root_extra.get("timestamp_semantics") is not None
        else None
    )
    return ConversionResult(
        trajectory=parsed,
        steps_meta=meta,
        warnings=[],
        total_events=len(steps),
        unmapped_events=0,
        started_at_ms=min(timestamps) if timestamps else None,
        finished_at_ms=max(timestamps) if timestamps else None,
        timestamp_semantics=timestamp_semantics,
    )


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


def step_meta_from_atif_step(index: int, step: Any) -> StepMeta:
    step_value = _object(step, f"trajectory.steps[{index}]")
    tool_calls = [
        ToolMeta(
            tool_call_id=str(call["tool_call_id"]),
            status="pending",
            title=str(call["function_name"]),
            timestamp_ms=atif_timestamp_ms(step_value),
        )
        for call in step_value.get("tool_calls") or []
    ]
    observations = []
    for result in (step_value.get("observation") or {}).get("results") or []:
        extra = result.get("extra") if isinstance(result.get("extra"), dict) else {}
        observations.append(
            ObservationMeta(
                source_call_id=result.get("source_call_id"),
                status=str(extra["status"])
                if extra.get("status") is not None
                else None,
                timestamp_ms=_iso_timestamp_ms(extra.get("finished_at")),
                tool_error=bool(extra.get("is_error", False)),
                truncated=bool(extra.get("truncated", False)),
            )
        )
    return StepMeta(
        step_id=int(step_value["step_id"]),
        source=str(step_value["source"]),
        tool_calls=tool_calls,
        observations=observations,
        tool_error=any(item.tool_error for item in observations),
        timestamp_ms=atif_timestamp_ms(step_value),
        truncated=bool(
            isinstance(step_value.get("extra"), dict)
            and step_value["extra"].get("truncated", False)
        ),
    )


def atif_timestamp_ms(step: dict[str, Any]) -> int | None:
    return _iso_timestamp_ms(step.get("timestamp"))


def _project_step_runtime_facts(
    step: dict[str, Any],
    meta: StepMeta,
    timestamp_semantics: str | None,
) -> bool:
    has_timestamp = False
    portable_time = (
        str(timestamp_semantics or "").lower() != TIMESTAMP_SEMANTICS_ORDER_ONLY
    )
    if meta.timestamp_ms is not None and portable_time:
        step["timestamp"] = _utc_iso(meta.timestamp_ms)
        has_timestamp = True

    step_extra = _dict_or_empty(step.get("extra"))
    if meta.duration_ms is not None and _is_portable_duration_source(
        meta.duration_source
    ):
        step_extra["duration_ms"] = max(0, int(meta.duration_ms))
        if meta.duration_source:
            step_extra["duration_source"] = meta.duration_source
    if meta.truncated:
        step_extra["truncated"] = True
    if step_extra:
        step["extra"] = step_extra

    tool_meta = {item.tool_call_id: item for item in meta.tool_calls}
    for call in step.get("tool_calls") or []:
        if not isinstance(call, dict):
            continue
        item = tool_meta.get(call.get("tool_call_id"))
        if item is None:
            continue
        extra = _dict_or_empty(call.get("extra"))
        if item.timestamp_ms is not None and portable_time:
            extra["started_at"] = _utc_iso(item.timestamp_ms)
        if item.generation_duration_ms is not None:
            extra["generation_duration_ms"] = max(0, int(item.generation_duration_ms))
        if item.truncated:
            extra["arguments_truncated"] = True
        if extra:
            call["extra"] = extra

    observation_meta = list(meta.observations)
    for index, observation in enumerate(
        (step.get("observation") or {}).get("results") or []
    ):
        if not isinstance(observation, dict):
            continue
        item = observation_meta[index] if index < len(observation_meta) else None
        if item is None:
            continue
        extra = _dict_or_empty(observation.get("extra"))
        if item.status is not None:
            extra["status"] = item.status
        extra["is_error"] = bool(item.tool_error)
        if item.timestamp_ms is not None and portable_time:
            extra["finished_at"] = _utc_iso(item.timestamp_ms)
        matching_tool = tool_meta.get(item.source_call_id or "")
        if (
            matching_tool is not None
            and matching_tool.execution_duration_ms is not None
        ):
            extra["execution_duration_ms"] = max(
                0, int(matching_tool.execution_duration_ms)
            )
            if matching_tool.execution_duration_source:
                extra["execution_duration_source"] = (
                    matching_tool.execution_duration_source
                )
        if item.truncated:
            extra["truncated"] = True
        if extra:
            observation["extra"] = extra
    return has_timestamp


def _normalize_converted_step(
    step: dict[str, Any], warnings: list[str], path: str
) -> None:
    if step.get("source") == "agent" and step.get("llm_call_count") is None:
        deterministic = bool(step.get("observation")) and not step.get("tool_calls")
        step["llm_call_count"] = 0 if deterministic else 1
    tool_ids = {
        call.get("tool_call_id")
        for call in step.get("tool_calls") or []
        if isinstance(call, dict)
    }
    for index, result in enumerate(
        (step.get("observation") or {}).get("results") or []
    ):
        if not isinstance(result, dict):
            continue
        content = result.get("content")
        if content is not None and not _is_atif_content(content):
            result["content"] = _deterministic_json(content)
        source_call_id = result.get("source_call_id")
        if source_call_id is not None and source_call_id not in tool_ids:
            extra = _dict_or_empty(result.get("extra"))
            extra["unmatched_source_call_id"] = source_call_id
            result["extra"] = extra
            result.pop("source_call_id", None)
            warning = (
                f"{path}.observation.results[{index}]: unmatched tool result "
                f"{source_call_id}"
            )
            if not any(str(source_call_id) in existing for existing in warnings):
                warnings.append(warning)


def _align_observation_meta(step: dict[str, Any], meta: StepMeta) -> None:
    results = (step.get("observation") or {}).get("results") or []
    for index, item in enumerate(meta.observations):
        if index >= len(results) or not isinstance(results[index], dict):
            continue
        source_call_id = results[index].get("source_call_id")
        item.source_call_id = (
            str(source_call_id) if source_call_id is not None else None
        )


def _aggregate_final_metrics(trajectory: dict[str, Any]) -> dict[str, Any]:
    previous = trajectory.get("final_metrics")
    previous_extra = (
        deepcopy(previous.get("extra"))
        if isinstance(previous, dict) and isinstance(previous.get("extra"), dict)
        else {}
    )
    totals: dict[str, int | float] = {}
    mappings = (
        ("prompt_tokens", "total_prompt_tokens"),
        ("completion_tokens", "total_completion_tokens"),
        ("cached_tokens", "total_cached_tokens"),
        ("cost_usd", "total_cost_usd"),
    )
    for source_key, total_key in mappings:
        values = [
            step["metrics"][source_key]
            for step in trajectory.get("steps") or []
            if isinstance(step, dict)
            and isinstance(step.get("metrics"), dict)
            and step["metrics"].get(source_key) is not None
        ]
        if values:
            total = sum(values)
            totals[total_key] = (
                round(float(total), 12) if source_key == "cost_usd" else int(total)
            )
    totals["total_steps"] = len(trajectory.get("steps") or [])
    if previous_extra:
        totals["extra"] = previous_extra
    return totals


def _is_portable_duration_source(source: str | None) -> bool:
    return source is None or "estimate" not in source.lower()


def _is_atif_content(value: Any) -> bool:
    if isinstance(value, str):
        return True
    if not isinstance(value, list):
        return False
    try:
        _validate_content(value, "content")
    except ValueError:
        return False
    return True


def _deterministic_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _utc_iso(timestamp_ms: int) -> str:
    value = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    text = value.isoformat(timespec="milliseconds")
    return text.replace("+00:00", "Z")


def _iso_timestamp_ms(value: Any) -> int | None:
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
    if not isinstance(value[key], str) or _iso_timestamp_ms(value[key]) is None:
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


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
