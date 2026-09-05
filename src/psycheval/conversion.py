"""Convert retained sessions and project adapter output into canonical ATIF."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from psycheval.adapters import adapter_for
from psycheval.adapters.base import (
    TIMESTAMP_SEMANTICS_ORDER_ONLY,
    ConversionResult,
    ObservationMeta,
    StepMeta,
    ToolMeta,
)
from psycheval.atif import (
    ATIF_VERSION,
    is_atif_content,
    iso_timestamp_ms,
    read_atif_json_path,
    validate_atif_trajectory,
)
from psycheval.config import ToolConfig
from psycheval.sources import MessageRecord, read_jsonl, read_sqlite_messages


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


def step_meta_from_atif_step(index: int, step: Any) -> StepMeta:
    if not isinstance(step, dict):
        raise ValueError(f"trajectory.steps[{index}] must be an object")
    step_value = step
    tool_calls = [
        ToolMeta(
            tool_call_id=str(call["tool_call_id"]),
            status="pending",
            title=str(call["function_name"]),
            timestamp_ms=iso_timestamp_ms(step_value.get("timestamp")),
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
                timestamp_ms=iso_timestamp_ms(extra.get("finished_at")),
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
        timestamp_ms=iso_timestamp_ms(step_value.get("timestamp")),
        truncated=bool(
            isinstance(step_value.get("extra"), dict)
            and step_value["extra"].get("truncated", False)
        ),
    )


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
        if content is not None and not is_atif_content(content):
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


def _deterministic_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _utc_iso(timestamp_ms: int) -> str:
    value = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    text = value.isoformat(timespec="milliseconds")
    return text.replace("+00:00", "Z")


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
