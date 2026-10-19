"""Pure canonical trajectory projections for the rebuildable catalog."""

from __future__ import annotations

from typing import Any

from psycheval._state.annotations import optional_int, optional_str
from psycheval.atif import iso_timestamp_ms
from psycheval.report.inference import inference_row_metrics
from psycheval.report.metrics import final_metric, token_total
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
    return {
        "trial_key": optional_str(
            meta.get("trial_key") or trajectory.get("trajectory_id")
        ),
        "trial_session_id": optional_str(trajectory.get("session_id")),
        "step_outline": step_outline(trajectory, meta),
        **_last_turn_end(meta),
        "status": optional_str(meta.get("status")) or "unknown",
        "score": optional_number(meta.get("score")),
        "score_message": optional_str(meta.get("score_message")),
        "duration_ms": optional_int(meta.get("duration_ms")),
        "wall_duration_ms": _wall_duration_ms(meta),
        "model_duration_ms": model_duration_ms(trajectory, meta),
        "turns": optional_number(final_metric(metrics, "total_turns")),
        "total_tool_calls": optional_number(final_metric(metrics, "total_tool_calls")),
        "total_tool_errors": optional_number(
            final_metric(metrics, "total_tool_errors")
        ),
        "tokens": token_total(metrics),
        "cost_usd": optional_number(metrics.get("total_cost_usd")),
        "warnings": len(warnings) if isinstance(warnings, list) else 0,
        "analysis_count": max(0, min(2, int(analysis_count))),
        "model": optional_str(agent.get("model_name")),
        "task_name": optional_str(meta.get("task_name")),
        "job_name": optional_str(meta.get("job_name")),
        "trial_name": optional_str(meta.get("trial_name")),
        "model_provider": optional_str(meta.get("model_provider")),
        "task_keywords": meta.get("task_keywords") or [],
        "rewards": meta.get("rewards") or {},
        "harbor_provenance": meta.get("harbor_provenance") or {},
        "task_metadata": _catalog_task_metadata(meta.get("task_metadata")),
        **inference_row_metrics(metrics),
    }


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
        duration = optional_number(step_meta.get("duration_ms"))
        if duration is None:
            continue
        total += duration
        count += 1
    return total if count else None


def _wall_duration_ms(meta: dict[str, Any]) -> int | None:
    explicit = optional_int(meta.get("wall_duration_ms"))
    if explicit is not None:
        return explicit
    started = optional_int(meta.get("started_at_ms"))
    finished = optional_int(meta.get("finished_at_ms"))
    if started is None or finished is None:
        return None
    return max(0, finished - started)


def optional_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
