"""Pure canonical trajectory projections for the rebuildable catalog."""

from __future__ import annotations

from typing import Any

from psycheval._state.annotations import optional_int, optional_str
from psycheval.atif import iso_timestamp_ms
from psycheval.metric_contract import (
    BUILTIN_IDS,
    RESERVED_EXTRA_KEYS,
    custom_metric_id,
    finite_number,
)
from psycheval.report.inference import inference_row_metrics
from psycheval.report.metrics import final_metric, number_metric, tool_success_rate
from psycheval.report.timing import is_model_duration_source, node_duration


def _last_turn_end(meta: dict[str, Any]) -> dict[str, Any]:
    finished = optional_int(meta.get("finished_at_ms"))
    source = "trajectory" if finished is not None else None
    if finished is None and meta.get("adapter") == "harbor":
        evaluation = meta.get("evaluation")
        phases = (
            evaluation.get("phase_timing") if isinstance(evaluation, dict) else None
        )
        if isinstance(phases, dict):
            for phase, origin in (
                ("agent_execution", "harbor_agent_execution"),
                ("overall", "harbor_trial"),
            ):
                timing = phases.get(phase)
                if isinstance(timing, dict):
                    finished = iso_timestamp_ms(timing.get("finished_at"))
                    if finished is not None:
                        source = origin
                        break
    return {
        "last_turn_finished_at_ms": finished,
        "last_turn_finished_at_source": source,
    }


def catalog_summary(
    trajectory: dict[str, Any], meta: dict[str, Any], analysis_count: int
) -> dict[str, Any]:
    metrics = _summary_metrics(trajectory, meta)
    agent = trajectory.get("agent")
    if not isinstance(agent, dict):
        agent = {}
    warnings = meta.get("warnings")
    row = {
        "trial_key": optional_str(
            meta.get("trial_key") or trajectory.get("trajectory_id")
        ),
        "trial_session_id": optional_str(trajectory.get("session_id")),
        "step_outline": step_outline(trajectory, meta),
        **_last_turn_end(meta),
        "status": optional_str(meta.get("status")) or "unknown",
        "score": finite_number(meta.get("score")),
        "score_message": optional_str(meta.get("score_message")),
        "duration_ms": finite_number(meta.get("duration_ms")),
        "wall_duration_ms": _wall_duration_ms(meta),
        "model_duration_ms": model_duration_ms(trajectory, meta),
        "turns": finite_number(final_metric(metrics, "total_turns")),
        "total_tool_calls": number_metric(final_metric(metrics, "total_tool_calls")),
        "total_tool_errors": number_metric(final_metric(metrics, "total_tool_errors")),
        "tokens": _token_total(metrics),
        "cost_usd": finite_number(metrics.get("total_cost_usd")),
        "warnings": len(warnings) if isinstance(warnings, list) else 0,
        "analysis_count": max(0, min(2, int(analysis_count))),
        "model": optional_str(agent.get("model_name")),
        "task_name": optional_str(meta.get("task_name")),
        "job_name": optional_str(meta.get("job_name")),
        "trial_name": optional_str(meta.get("trial_name")),
        "model_provider": optional_str(meta.get("model_provider")),
        "task_keywords": meta.get("task_keywords") or [],
        "rewards": {
            key: value
            for key, value in (meta.get("rewards") or {}).items()
            if finite_number(value) is not None
        },
        "harbor_provenance": meta.get("harbor_provenance") or {},
        "task_metadata": _catalog_task_metadata(meta.get("task_metadata")),
        **inference_row_metrics(metrics),
    }
    row.update(_additional_metrics(trajectory, meta, metrics))
    row["tool_success_rate"] = tool_success_rate(
        row.get("total_tool_calls"), row.get("total_tool_errors")
    )
    values = {
        key: value
        for key in BUILTIN_IDS
        if (value := finite_number(row.get(key))) is not None
    }
    diagnostics = []
    extra = metrics.get("extra") if isinstance(metrics.get("extra"), dict) else {}
    for namespace, source in (("atif.extra", extra), ("reward", row["rewards"])):
        for key, value in source.items():
            if namespace == "atif.extra" and key in RESERVED_EXTRA_KEYS:
                continue
            number = finite_number(value)
            if number is None:
                continue
            try:
                metric_id = custom_metric_id(namespace, key)
            except ValueError as exc:
                diagnostics.append(f"{namespace} metric {key!r}: {exc}")
                continue
            values[metric_id] = number
    row["metric_values"] = values
    row["metric_diagnostics"] = diagnostics
    return row


def _additional_metrics(
    trajectory: dict[str, Any], meta: dict[str, Any], metrics: dict[str, Any]
) -> dict[str, Any]:
    result = {
        key: finite_number(final_metric(metrics, key))
        for key in (
            "total_prompt_tokens",
            "total_completion_tokens",
            "total_cached_tokens",
            "total_steps",
        )
    }
    tools, other = [], []
    for step, step_meta in zip(trajectory.get("steps") or [], meta.get("steps") or []):
        if not isinstance(step, dict) or not isinstance(step_meta, dict):
            continue
        duration = finite_number(step_meta.get("duration_ms"))
        if (
            step.get("source") in {"agent", "assistant"}
            and not is_model_duration_source(step_meta.get("duration_source"))
            and duration is not None
            and duration >= 0
        ):
            other.append(duration)
        for tool in step_meta.get("tool_calls") or []:
            duration = (
                finite_number(tool.get("execution_duration_ms"))
                if isinstance(tool, dict)
                else None
            )
            if duration is not None and duration >= 0:
                tools.append(duration)
    result.update(
        tool_duration_ms=finite_number(sum(tools)) if tools else None,
        other_duration_ms=finite_number(sum(other)) if other else None,
    )
    tests = (meta.get("verifier_evidence") or {}).get("tests") or {}
    passed, total = (
        finite_number(tests.get("passed")),
        finite_number(tests.get("total")),
    )
    if (
        passed is not None
        and total is not None
        and passed == int(passed)
        and total == int(total)
        and 0 <= passed <= total
    ):
        result.update(
            tests_passed=passed,
            tests_total=total,
            test_pass_rate=passed / total if total else None,
        )
    return result


def _catalog_task_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    fields = {
        "description",
        "diagnostic",
        "digest_comparison",
        "digest_matches",
        "keywords",
        "live",
        "live_digest",
        "name",
        "path",
        "requested_name",
        "status",
        "version",
    }
    return {key: item for key, item in value.items() if key in fields}


def _summary_metrics(
    trajectory: dict[str, Any], meta: dict[str, Any]
) -> dict[str, Any]:
    source = meta.get("source_metrics")
    fallback = source if isinstance(source, dict) else {}
    trajectory_metrics = trajectory.get("final_metrics")
    explicit = trajectory_metrics if isinstance(trajectory_metrics, dict) else {}
    metrics = {**fallback, **explicit}
    fallback_extra = (
        fallback.get("extra") if isinstance(fallback.get("extra"), dict) else {}
    )
    explicit_extra = (
        explicit.get("extra") if isinstance(explicit.get("extra"), dict) else {}
    )
    if fallback_extra or explicit_extra:
        metrics["extra"] = {**fallback_extra, **explicit_extra}
    return metrics


def step_outline(
    trajectory: dict[str, Any], meta: dict[str, Any]
) -> list[dict[str, Any]]:
    metadata_by_step_id = {
        str(step.get("step_id")): step
        for step in meta.get("steps", [])
        if isinstance(step, dict) and step.get("step_id") is not None
    }
    outline: list[dict[str, Any]] = []
    steps = trajectory.get("steps", [])
    next_timestamps = {}
    next_timestamp = None
    for step in reversed(steps):
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("step_id"))
        next_timestamps[step_id] = next_timestamp
        timestamp = metadata_by_step_id.get(step_id, {}).get("timestamp_ms")
        if timestamp is not None:
            next_timestamp = timestamp
    for step in steps:
        if not isinstance(step, dict) or step.get("step_id") is None:
            continue
        step_id = step["step_id"]
        source = str(step.get("source") or "").strip().lower()
        normalized_source = "agent" if source == "assistant" else source
        if normalized_source not in {"system", "user", "agent"}:
            normalized_source = "unknown"
        item: dict[str, Any] = {"step_id": step_id, "source": normalized_source}
        step_meta = metadata_by_step_id.get(str(step_id), {})
        duration, duration_source = node_duration(
            step_meta
            if normalized_source == "agent"
            else {"duration_ms": step_meta.get("duration_ms")},
            next_timestamps.get(str(step_id)) if normalized_source == "agent" else None,
            meta.get("timestamp_semantics"),
        )
        if duration is not None:
            item["duration_ms"] = duration
            if duration_source:
                item["duration_source"] = duration_source
        outline.append(item)
    return outline


def model_duration_ms(
    trajectory: dict[str, Any], meta: dict[str, Any]
) -> int | float | None:
    trajectory_steps = trajectory.get("steps")
    meta_steps = meta.get("steps")
    if not isinstance(trajectory_steps, list) or not isinstance(meta_steps, list):
        return None
    total: int | float = 0
    count = 0
    for index, step_meta in enumerate(meta_steps):
        if not isinstance(step_meta, dict) or index >= len(trajectory_steps):
            continue
        step = trajectory_steps[index]
        if not isinstance(step, dict):
            continue
        if str(step.get("source") or "").lower() not in {"agent", "assistant"}:
            continue
        if not is_model_duration_source(step_meta.get("duration_source")):
            continue
        duration = finite_number(step_meta.get("duration_ms"))
        if duration is None or duration < 0:
            continue
        total += duration
        count += 1
    return finite_number(total) if count else None


def _wall_duration_ms(meta: dict[str, Any]) -> int | None:
    explicit = optional_int(meta.get("wall_duration_ms"))
    if explicit is not None:
        return explicit
    started = optional_int(meta.get("started_at_ms"))
    finished = optional_int(meta.get("finished_at_ms"))
    if started is None or finished is None:
        return None
    return max(0, finished - started)


def _token_total(metrics: dict[str, Any]) -> int | float | None:
    values = [
        finite_number(metrics.get(key))
        for key in ("total_prompt_tokens", "total_completion_tokens")
    ]
    present = [value for value in values if value is not None]
    if present:
        return finite_number(sum(present))
    usage = (metrics.get("extra") or {}).get("usage")
    return finite_number(usage.get("total_tokens")) if isinstance(usage, dict) else None
