"""The shared Trial measurement projection consumed by reports and catalog."""

from __future__ import annotations

from psycheval.harbor.atif import agent_step_count, iso_timestamp_ms
from psycheval.harbor.measurements import (
    METRICS,
    measurement,
    number,
    validate_provenance,
)
from psycheval.report.inference import inference_row_metrics
from psycheval.report.metrics import final_metric, number_metric, tool_success_rate
from psycheval.report.timing import is_model_duration_source


def summary_metrics(trajectory, meta):
    fallback = mapping(meta.get("source_metrics"))
    explicit = mapping(trajectory.get("final_metrics"))
    return {
        **fallback,
        **explicit,
        "extra": {**mapping(fallback.get("extra")), **mapping(explicit.get("extra"))},
    }


def mapping(value):
    return value if isinstance(value, dict) else {}


def model_duration_ms(trajectory, meta):
    if not isinstance(trajectory.get("steps"), list) or not isinstance(
        meta.get("steps"), list
    ):
        return None
    durations = []
    for step, sidecar in zip(trajectory["steps"], meta["steps"]):
        if not isinstance(step, dict) or not isinstance(sidecar, dict):
            continue
        value = number(sidecar.get("duration_ms"))
        if (
            str(step.get("source") or "").lower() in {"agent", "assistant"}
            and is_model_duration_source(sidecar.get("duration_source"))
            and value is not None
            and value >= 0
        ):
            durations.append(value)
    return number(sum(durations)) if durations else None


def construct(trajectory, meta):
    metrics = summary_metrics(trajectory, meta)
    marker = (trajectory.get("extra") or {}).get(
        "measurements", meta.get("measurement_marker")
    )
    new = marker is not None
    version = 1 if new else "legacy"
    results = {}
    agent = trajectory.get("agent") or {}
    producer = {
        "name": agent.get("name", meta.get("adapter", "unknown")),
        "version": agent.get("version", "unknown"),
    }

    def add(key, value, source, method, fields=(), **kwargs):
        results[key] = measurement(
            value,
            source=source,
            method=method,
            basis=method,
            version=version,
            fields=fields,
            producer=producer,
            **kwargs,
        )

    add(
        "score",
        meta.get("score"),
        "evaluation.primary_score",
        "selected_primary_score",
        ("score", "evaluation", "verifier_evidence"),
        grading={
            "source": str(meta.get("score_message") or "")[:128],
            **mapping(mapping(meta.get("verifier_evidence")).get("grading")),
            "harbor_version": (meta.get("harbor_provenance") or {}).get(
                "harbor_version"
            ),
            "task_version": mapping(meta.get("harbor_provenance")).get("task_version"),
            "task_digest": mapping(meta.get("harbor_provenance")).get("task_digest"),
        },
    )
    selected_score = mapping(meta.get("metric_provenance")).get("score")
    if selected_score:
        results["score"]["provenance"] = {
            **selected_score,
            "contract_version": version,
            "grading": results["score"]["provenance"]["grading"],
        }
    active = (meta.get("metric_provenance") or {}).get("duration_ms")
    if active:
        results["duration_ms"] = {
            "value": number(meta.get("duration_ms")),
            "provenance": {**active, "contract_version": version},
        }
    else:
        add(
            "duration_ms",
            meta.get("duration_ms"),
            "retained_sidecar",
            "retained_active_duration",
            ("duration_ms",),
            quality="unknown",
        )
    extra = metrics.get("extra") or {}
    origins = mapping(extra.get("metric_field_origins"))

    def origin(*fields):
        selected = {
            origins.get(
                field,
                "atif.final_metrics"
                if field in mapping(trajectory.get("final_metrics")) or field in extra
                else "harbor.agent_result"
                if field in mapping(meta.get("source_metrics"))
                else "unavailable",
            )
            for field in fields
        }
        return (
            next(iter(selected))
            if len(selected) == 1
            else "mixed:" + ",".join(sorted(selected))
        )

    agent_steps = agent_step_count(trajectory)
    reported_steps = (
        "total_agent_steps" in extra
        and origins.get("total_agent_steps") != "derived.main_trajectory"
    )
    add(
        "agent_steps",
        agent_steps,
        origin("total_agent_steps") if reported_steps else "atif.steps",
        "reported_main_agent_steps" if reported_steps else "count(main_agent_steps)",
        ("final_metrics.extra.total_agent_steps",)
        if reported_steps
        else ("steps.source",),
    )
    calls = number_metric(final_metric(metrics, "total_tool_calls"))
    errors = number_metric(final_metric(metrics, "total_tool_errors"))
    add(
        "total_tool_calls",
        calls,
        origin("total_tool_calls"),
        "main_tool_call_count",
        ("final_metrics.extra.total_tool_calls",),
    )
    add(
        "tool_success_rate",
        tool_success_rate(calls, errors),
        origin("total_tool_calls", "total_tool_errors"),
        "(calls-errors)/calls",
        ("total_tool_calls", "total_tool_errors"),
    )
    present = [
        number(metrics.get(key))
        for key in ("total_prompt_tokens", "total_completion_tokens")
    ]
    available = [value for value in present if value is not None]
    if available:
        add(
            "tokens",
            sum(available),
            origin(
                *(
                    key
                    for key in ("total_prompt_tokens", "total_completion_tokens")
                    if number(metrics.get(key)) is not None
                )
            ),
            "sum(available_prompt_and_completion)",
            ("total_prompt_tokens", "total_completion_tokens"),
            scope="retained_source_scope",
        )
    else:
        add(
            "tokens",
            mapping(extra.get("usage")).get("total_tokens"),
            "atif.extra.usage",
            "reported_total_tokens",
            ("final_metrics.extra.usage.total_tokens",),
            scope="retained_source_scope",
        )
    inference = inference_row_metrics(metrics)
    for key, method in (
        ("ttft_ms", "ttft_ms_sum/ttft_sample_count"),
        ("tps", "decode_token_count/decode_seconds"),
        ("cache_hit_rate", "cache_read_tokens/cache_prompt_tokens"),
    ):
        add(
            key,
            inference.get(key),
            origin("model_inference"),
            method,
            ("final_metrics.extra.model_inference",),
            scope="retained_source_scope",
        )
    add(
        "model_duration_ms",
        model_duration_ms(trajectory, meta),
        "trajectory.duration_sources",
        "sum(eligible_recorded_model_contributions)",
        ("steps.duration_ms", "steps.duration_source"),
        quality="mixed",
    )
    add(
        "cost_usd",
        metrics.get("total_cost_usd"),
        origin("total_cost_usd"),
        "reported_cost",
        ("total_cost_usd",),
        scope="retained_source_scope",
        quality="unknown",
    )
    finish = meta.get("finished_at_ms")
    source = "trajectory"
    if finish is None and meta.get("adapter") == "harbor":
        phases = (meta.get("evaluation") or {}).get("phase_timing")
        phases = phases if isinstance(phases, dict) else {}
        for phase in ("agent_execution", "overall"):
            timing = phases.get(phase)
            candidate = (
                iso_timestamp_ms(timing.get("finished_at"))
                if isinstance(timing, dict)
                else None
            )
            if candidate is not None:
                finish, source = (
                    candidate,
                    "harbor_" + ("trial" if phase == "overall" else phase),
                )
                break
    add(
        "last_turn_finished_at_ms",
        finish,
        source,
        "retained_end_boundary",
        ("finished_at_ms",)
        if source == "trajectory"
        else (
            "evaluation.phase_timing."
            + source.removeprefix("harbor_")
            + ".finished_at",
        ),
        quality="observed"
        if meta.get("timestamp_semantics") == "event_observed"
        else "reported",
    )
    if new:
        native = meta.get("native_measurements") or {}
        if native.get("last_turn_finished_at_ms", {}).get("value") is not None:
            results["last_turn_finished_at_ms"] = native["last_turn_finished_at_ms"]
        for key in (
            "model_duration_ms",
            "ttft_ms",
            "tps",
            "tokens",
            "cache_hit_rate",
            "cost_usd",
            "tool_success_rate",
        ):
            results[key] = native.get(key) or measurement(
                None,
                source="measurement_evidence",
                method="unavailable",
                basis="measurement_contract_1",
                missing=meta.get(
                    "measurement_error", "measurement_evidence_unavailable"
                ),
            )
        trajectory_extra = mapping(trajectory.get("extra"))
        retention = (
            "partial"
            if trajectory_extra.get("incomplete")
            or trajectory_extra.get("diagnostic_only")
            else "complete"
            if isinstance(trajectory.get("steps"), list)
            and not trajectory.get("synthetic")
            else "unknown"
        )
        for key in ("agent_steps", "total_tool_calls"):
            provenance = results[key]["provenance"]
            provenance["retention"] = retention
            if retention == "partial":
                provenance["scope"] = "retained_main_trajectory"
                provenance["basis_id"] += ":retained"
    for item in results.values():
        validate_provenance(item["provenance"])
    return {key: results[key]["value"] for key in METRICS}, {
        key: results[key]["provenance"] for key in METRICS
    }


def project(trajectory, meta):
    values, provenance = construct(trajectory, meta)
    meta["metric_values"], meta["metric_provenance"] = values, provenance
    return meta
