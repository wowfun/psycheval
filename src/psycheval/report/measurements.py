"""The shared Trial measurement projection consumed by reports and catalog."""

from __future__ import annotations

from psycheval.harbor.atif import agent_step_count, iso_timestamp_ms
from psycheval.harbor.family import coverage, scope, selected
from psycheval.harbor.measurements import (
    METRICS,
    measurement,
    number,
    tool_outcome,
    trajectory_tools,
    validate_provenance,
)
from psycheval.report.inference import inference_row_metrics
from psycheval.report.metrics import final_metric, number_metric, tool_success_rate
from psycheval.report.timing import is_model_duration_source


def summary_metrics(trajectory, meta):
    fallback = mapping(meta.get("source_metrics"))
    explicit = mapping(trajectory.get("final_metrics"))
    metrics = {
        **fallback,
        **explicit,
        "extra": {**mapping(fallback.get("extra")), **mapping(explicit.get("extra"))},
    }
    steps = trajectory.get("steps") or []
    if any(step.get("is_copied_context") for step in steps):
        from psycheval.harbor.inference_telemetry import finalize_trajectory_metrics

        execution = [step for step in steps if not step.get("is_copied_context")]
        metrics = finalize_trajectory_metrics({"steps": execution})["final_metrics"]
        costs = [
            number(mapping(step.get("metrics")).get("cost_usd")) for step in execution
        ]
        costs = [value for value in costs if value is not None]
        if costs:
            metrics["total_cost_usd"] = round(sum(costs), 12)
        metrics.setdefault("extra", {}).update(
            total_agent_steps=sum(
                step.get("source") in {"agent", "assistant"} for step in execution
            ),
            total_tool_calls=sum(
                len(step.get("tool_calls") or []) for step in execution
            ),
        )
        metrics["total_steps"] = len(execution)
    return metrics


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
            and not step.get("is_copied_context")
            and is_model_duration_source(sidecar.get("duration_source"))
            and value is not None
            and value >= 0
        ):
            durations.append(value)
    return number(sum(durations)) if durations else None


def _construct_root(trajectory, meta, *, metrics=None):
    copied = any(
        step.get("is_copied_context") for step in trajectory.get("steps") or []
    )
    metrics = summary_metrics(trajectory, meta) if metrics is None else metrics
    marker = (trajectory.get("extra") or {}).get(
        "measurements", meta.get("measurement_marker")
    )
    new = marker is not None
    version = mapping(marker).get("contract_version", 1) if new else "legacy"
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
        if copied:
            return "derived.execution_steps"
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

    agent_steps = agent_step_count({**trajectory, "final_metrics": metrics})
    reported_steps = (
        "total_agent_steps" in extra
        and not copied
        and origins.get("total_agent_steps") != "derived.main_trajectory"
    )
    add(
        "agent_steps",
        agent_steps,
        origin("total_agent_steps") if reported_steps else "atif.steps",
        "reported_main_agent_steps"
        if reported_steps
        else "count(execution_agent_steps)",
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


def construct(trajectory, meta, metric_scope="family"):
    bodies = selected(trajectory, metric_scope)
    inferences = []

    def own(item, sidecar):
        metrics = summary_metrics(item, sidecar)
        inferences.append(inference_row_metrics(metrics))
        values, provenance = _construct_root(item, sidecar, metrics=metrics)
        tools, other = [], []
        for step, step_meta in zip(item.get("steps") or [], sidecar.get("steps") or []):
            if step.get("is_copied_context"):
                continue
            duration = number(step_meta.get("duration_ms"))
            if (
                step.get("source") in {"agent", "assistant"}
                and not is_model_duration_source(step_meta.get("duration_source"))
                and duration is not None
            ):
                other.append(duration)
            tools.extend(
                value
                for tool in step_meta.get("tool_calls") or []
                if (value := number(tool.get("execution_duration_ms"))) is not None
            )
        for key, contributions in (
            ("tool_duration_ms", tools),
            ("other_duration_ms", other),
        ):
            values[key] = sum(contributions) if contributions else None
            provenance[key] = measurement(
                values[key],
                source="trajectory.duration_sources",
                method="sum(eligible_recorded_contributions)",
                basis="retained_duration_components_v2",
                scope="root",
            )["provenance"]
        for key in (
            "total_prompt_tokens",
            "total_completion_tokens",
            "total_cached_tokens",
            "total_steps",
            "total_tool_errors",
        ):
            native_component = (sidecar.get("native_measurements") or {}).get(key)
            values[key] = (
                native_component["value"]
                if native_component
                else number(final_metric(metrics, key))
            )
            provenance[key] = (
                native_component["provenance"]
                if native_component
                else measurement(
                    values[key],
                    source="derived.execution_steps"
                    if any(
                        step.get("is_copied_context")
                        for step in item.get("steps") or []
                    )
                    else "atif.final_metrics",
                    method="retained_component",
                    basis="retained_component",
                    scope="root",
                )["provenance"]
            )
        return values, provenance

    root_meta = dict(meta)
    native_sets = meta.get("native_measurement_sets") or {}
    if native_sets:
        root_meta["native_measurements"] = native_sets.get("root", {})
    values, provenance = own(trajectory, root_meta)
    if metric_scope == "family" and len(bodies) > 1:
        parts = [(values, provenance)]

        def visit(item, sidecar):
            for child in item.get("subagent_trajectories") or []:
                child_meta = (sidecar.get("subagent_meta") or {}).get(
                    child["trajectory_id"], {}
                )
                parts.append(own(child, child_meta))
                visit(child, child_meta)

        visit(trajectory, meta)
        additive = (
            "tokens",
            "cost_usd",
            "agent_steps",
            "total_tool_calls",
            "total_tool_errors",
            "total_steps",
            "total_prompt_tokens",
            "total_completion_tokens",
            "total_cached_tokens",
            "model_duration_ms",
            "tool_duration_ms",
            "other_duration_ms",
        )
        for key in additive:
            known = [v[key] for v, _ in parts if v.get(key) is not None]
            values[key] = sum(known) if known else None
            provenance[key] = measurement(
                values[key],
                source="atif.family",
                method="sum(observed_members)",
                basis="family_components_v2",
                scope="family",
                coverage={
                    "measured": len(known),
                    "unknown": len(parts) - len(known),
                    "total": len(parts),
                },
            )["provenance"]
        # Pool sufficient statistics, never average per-member ratios.
        for key, fields, method in (
            (
                "ttft_ms",
                ("ttft_ms_sum", "ttft_sample_count"),
                "sum(ttft_ms_sum)/sum(ttft_sample_count)",
            ),
            (
                "tps",
                ("decode_token_count", "decode_duration_ms", "decode_sample_count"),
                "1000*sum(decode_token_count)/sum(decode_duration_ms)",
            ),
            (
                "cache_hit_rate",
                ("cache_read_tokens", "cache_prompt_tokens", "cache_sample_count"),
                "sum(cache_read_tokens)/sum(cache_prompt_tokens)",
            ),
        ):
            samples = [item for item in inferences if item[key] is not None]
            pooled = {field: sum(item[field] for item in samples) for field in fields}
            values[key] = inference_row_metrics({"extra": {"model_inference": pooled}})[
                key
            ]
            provenance[key] = measurement(
                values[key],
                source="atif.family",
                method=method,
                basis="family_pooled_samples_v2",
                scope="family",
                coverage={
                    "measured": len(samples),
                    "unknown": len(parts) - len(samples),
                    "total": len(parts),
                },
            )["provenance"]
        outcomes = [
            tool_outcome(tool) for body in bodies for tool in trajectory_tools(body)
        ]
        known = sum(outcome != "unknown" for outcome in outcomes)
        successes = outcomes.count("success")
        values["tool_success_rate"] = successes / known if known else None
        provenance["tool_success_rate"] = measurement(
            values["tool_success_rate"],
            source="atif.family",
            method="successes/known",
            basis="tool_known_outcomes_v1",
            scope="family",
            coverage={
                "measured": known,
                "success": successes,
                "failed": outcomes.count("failed"),
                "unknown": len(outcomes) - known,
                "total": len(outcomes),
            },
            missing="no_known_tool_outcomes",
        )["provenance"]
    native = native_sets.get(metric_scope, {})
    if native:
        for key, measured in native.items():
            if key == "last_turn_finished_at_ms" and metric_scope == "family":
                continue
            values[key], provenance[key] = measured["value"], measured["provenance"]
    for key, item in provenance.items():
        item = dict(item)
        item.pop("family_coverage", None)
        item["scope"] = (
            "evaluation_entry"
            if key
            in (
                "duration_ms",
                "score",
                "last_turn_finished_at_ms",
                "execution_elapsed_ms",
            )
            else metric_scope
        )
        validate_provenance(item)
        provenance[key] = item
    phase = mapping(mapping(meta.get("evaluation")).get("phase_timing")).get(
        "agent_execution", {}
    )
    start, end = (
        iso_timestamp_ms(phase.get("started_at")),
        iso_timestamp_ms(phase.get("finished_at")),
    )
    values["execution_elapsed_ms"] = (
        end - start if start is not None and end is not None and end >= start else None
    )
    provenance["execution_elapsed_ms"] = measurement(
        values["execution_elapsed_ms"],
        source="harbor.agent_execution",
        method="finished-started",
        basis="agent_execution_wall_clock",
        scope="evaluation_entry",
    )["provenance"]
    return values, provenance


def scoped_metrics(meta, metric_scope="family"):
    """Select values, provenance and coverage together without mutating a source."""
    scope(metric_scope)
    return {
        **(meta.get("metric_sets", {}).get(metric_scope) or {}),
        "metric_scope": metric_scope,
    }


def project(trajectory, meta):
    source_limit = 32 * 1024
    meta["metric_sets"] = {}
    for selection in ("root", "family"):
        values, provenance = construct(trajectory, meta, selection)
        meta["metric_sets"][selection] = {
            "metric_values": values,
            "metric_provenance": provenance,
            "family_coverage": coverage(trajectory, selection),
        }
    from psycheval.harbor.measurements import encoded

    if (
        len(
            encoded(
                {
                    selection: measured["metric_provenance"]
                    for selection, measured in meta["metric_sets"].items()
                }
            )
        )
        > source_limit
    ):
        for measured in meta["metric_sets"].values():
            measured["provenance_details_truncated"] = True
            measured["metric_provenance"] = {
                key: {
                    **{
                        field: value
                        for field, value in item.items()
                        if field
                        not in {"producer", "fields", "evidence", "clock", "grading"}
                    },
                    "details_truncated": True,
                }
                for key, item in measured["metric_provenance"].items()
            }
        if (
            len(
                encoded(
                    {
                        key: value["metric_provenance"]
                        for key, value in meta["metric_sets"].items()
                    }
                )
            )
            > source_limit
        ):
            for measured in meta["metric_sets"].values():
                measured["metric_provenance"] = {
                    key: measurement(
                        measured["metric_values"].get(key),
                        source="unknown",
                        method="retained_value_details_truncated",
                        basis="unknown",
                        version=item.get("contract_version", "unknown"),
                        scope=item["scope"],
                        quality="unknown",
                        details_truncated=True,
                        missing="provenance_details_limit",
                        missing_reason="provenance_details_limit",
                    )["provenance"]
                    for key, item in measured["metric_provenance"].items()
                }
    meta.update(meta["metric_sets"]["family"])
    meta["metric_scope"] = "family"
    return meta
