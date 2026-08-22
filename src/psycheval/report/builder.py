from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from psycheval.adapters.base import ConversionResult
from psycheval.analysis import (
    ANALYSIS_REPORT_FIELDS,
    RESERVED_ANALYSIS_METRIC_KEYS,
    cached_analysis_report,
    cached_note_report,
)
from psycheval.atif import (
    _finalize_atif_session_context,
    atif_timestamp_ms,
    step_meta_from_atif_step,
    validate_atif_trajectory,
)
from psycheval.config import ToolConfig
from psycheval.models import NoteInput, ReportSession
from psycheval.redaction import redact_value
from psycheval.report.data_ref import data_ref_for_input
from psycheval.report.metrics import automatic_analysis_metrics
from psycheval.report.timing import step_meta_reports, trial_active_duration_ms

VIEW_SCHEMA_VERSION = 19


def build_report(
    conversion: ConversionResult,
    config: ToolConfig,
    input_label: str,
    input_path: str | None = None,
) -> dict[str, Any]:
    return build_multi_report(
        [ReportSession(conversion, input_label, input_path)],
        config,
        [],
    )


def build_multi_report(
    sessions: list[ReportSession],
    config: ToolConfig,
    notes: list[NoteInput] | None = None,
) -> dict[str, Any]:
    if not sessions:
        raise ValueError("at least one session is required")
    notes = notes or []
    multi = len(sessions) > 1
    prepared: list[dict[str, Any]] = []
    seen_trial_keys: dict[str, int] = {}
    for index, session in enumerate(sessions, start=1):
        prepared.append(
            prepare_session_report(index, session, config, multi, seen_trial_keys)
        )

    trajectories = [item["trajectory"] for item in prepared]
    metas = [item["meta"] for item in prepared]
    includes = ["core"]
    report: dict[str, Any] = {
        "schema_version": VIEW_SCHEMA_VERSION,
        "includes": includes,
        "trajectory": trajectories,
        "trajectory_meta": metas,
    }
    annotations = annotations_report(
        notes,
        metas,
        cell_note_reports(config, prepared),
        analysis_reports(config, prepared),
    )
    if annotations:
        includes.append("annotations")
        report["annotations"] = annotations
    return report


def build_report_from_snapshots(
    trajectories: list[dict[str, Any]],
    metas: list[dict[str, Any]],
    *,
    input_label: str = "serve",
    source_reports: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if len(trajectories) != len(metas):
        raise ValueError("trajectory and meta snapshot counts differ")
    if not trajectories:
        return empty_report(input_label)
    for index, trajectory in enumerate(trajectories):
        validate_atif_trajectory(trajectory, f"report.trajectory[{index}]")
    projected_metas = [
        project_meta_from_atif(trajectory, meta)
        for trajectory, meta in zip(trajectories, metas, strict=True)
    ]
    includes = ["core"]
    report: dict[str, Any] = {
        "schema_version": VIEW_SCHEMA_VERSION,
        "includes": includes,
        "trajectory": trajectories,
        "trajectory_meta": projected_metas,
    }
    notes = note_reports_from_snapshots(source_reports or [], projected_metas)
    analyses = analysis_reports_from_snapshots(
        source_reports or [], trajectories, projected_metas
    )
    if notes or analyses:
        includes.append("annotations")
        report["annotations"] = {"report_notes": [], "notes": notes}
        if analyses:
            report["annotations"]["analysis"] = analyses
    return report


def empty_report(input_label: str = "serve") -> dict[str, Any]:
    return {
        "schema_version": VIEW_SCHEMA_VERSION,
        "includes": ["core"],
        "trajectory": [],
        "trajectory_meta": [],
    }


def prepare_session_report(
    index: int,
    session: ReportSession,
    config: ToolConfig,
    multi: bool,
    seen_trial_keys: dict[str, int],
) -> dict[str, Any]:
    conversion = _finalize_atif_session_context(
        session.conversion,
        session.session_hint if session.adapter_id != "atif" else None,
    )
    trajectory = deepcopy(conversion.trajectory)
    if config.redact:
        trajectory = redact_value(trajectory)
    validate_atif_trajectory(trajectory)
    trial_key = trial_key_for(index, trajectory, config, multi, seen_trial_keys)
    started, finished = canonical_time_bounds(
        trajectory,
        conversion.started_at_ms,
        conversion.finished_at_ms,
    )
    wall_duration = max(0, finished - started)
    steps = step_meta_reports(
        conversion.steps_meta,
        started,
        conversion.timestamp_semantics,
    )
    project_canonical_step_facts(trajectory, steps, started)
    status = "failed" if conversion.warnings or conversion.unmapped_events else "passed"
    data_ref = data_ref_for_input(session.input_label, session.input_path)
    adapter_id = session.adapter_id or config.adapter
    meta = {
        "trial_key": trial_key,
        "adapter": adapter_id,
        **optional("timestamp_semantics", conversion.timestamp_semantics),
        "started_at_ms": started,
        "finished_at_ms": finished,
        "wall_duration_ms": wall_duration,
        "duration_ms": trial_active_duration_ms(conversion.steps_meta, steps),
        "status": status,
        "failure_class": None if status == "passed" else "conversion",
        "score": None,
        "score_message": "offline session conversion",
        "warnings": conversion.warnings,
        "data_ref": data_ref,
        **optional("source_alias", session.source_alias),
        "total_events": conversion.total_events,
        "unmapped_events": conversion.unmapped_events,
        "prompt_unavailable": not any(
            step.get("source") == "user" for step in trajectory.get("steps", [])
        ),
        "steps": steps,
    }
    return {
        "index": index,
        "input_label": session.input_label,
        "input_path": session.input_path,
        "source_alias": session.source_alias,
        "analysis_agent_id": session.analysis_agent_id or adapter_id,
        "trajectory": trajectory,
        "meta": meta,
    }


def canonical_time_bounds(
    trajectory: dict[str, Any],
    fallback_started_at_ms: int | None,
    fallback_finished_at_ms: int | None,
) -> tuple[int, int]:
    timestamps: list[int] = []
    for step in trajectory.get("steps") or []:
        if not isinstance(step, dict):
            continue
        timestamp = atif_timestamp_ms(step)
        if timestamp is not None:
            timestamps.append(timestamp)
            step_extra = (
                step.get("extra") if isinstance(step.get("extra"), dict) else {}
            )
            duration = step_extra.get("duration_ms")
            if isinstance(duration, (int, float)) and not isinstance(duration, bool):
                timestamps.append(timestamp + max(0, int(duration)))
        for call in step.get("tool_calls") or []:
            if not isinstance(call, dict) or not isinstance(call.get("extra"), dict):
                continue
            call_started = iso_timestamp_ms(call["extra"].get("started_at"))
            if call_started is not None:
                timestamps.append(call_started)
                generation = call["extra"].get("generation_duration_ms")
                if isinstance(generation, (int, float)) and not isinstance(
                    generation, bool
                ):
                    timestamps.append(call_started + max(0, int(generation)))
        for result in (step.get("observation") or {}).get("results") or []:
            if not isinstance(result, dict) or not isinstance(
                result.get("extra"), dict
            ):
                continue
            finished = iso_timestamp_ms(result["extra"].get("finished_at"))
            if finished is not None:
                timestamps.append(finished)
    started = int(
        min(timestamps)
        if timestamps
        else (fallback_started_at_ms if fallback_started_at_ms is not None else 0)
    )
    finished = int(
        max(timestamps)
        if timestamps
        else (
            fallback_finished_at_ms if fallback_finished_at_ms is not None else started
        )
    )
    return started, max(started, finished)


def project_meta_from_atif(
    trajectory: dict[str, Any], meta: dict[str, Any]
) -> dict[str, Any]:
    """Return the sidecar shape with portable facts mirrored from ATIF."""

    projected = deepcopy(meta)
    started, finished = canonical_time_bounds(
        trajectory,
        optional_int_value(projected.get("started_at_ms")),
        optional_int_value(projected.get("finished_at_ms")),
    )
    projected["started_at_ms"] = started
    projected["finished_at_ms"] = finished
    projected["wall_duration_ms"] = max(0, finished - started)
    root_extra = trajectory.get("extra")
    if (
        isinstance(root_extra, dict)
        and root_extra.get("timestamp_semantics") is not None
    ):
        projected["timestamp_semantics"] = root_extra["timestamp_semantics"]
    canonical_steps = trajectory.get("steps") or []
    prior_steps = projected.get("steps")
    steps = step_meta_reports(
        [
            step_meta_from_atif_step(index, step)
            for index, step in enumerate(canonical_steps)
        ],
        started,
        projected.get("timestamp_semantics"),
    )
    merge_sidecar_owned_step_fields(steps, prior_steps)
    projected["steps"] = steps
    project_canonical_step_facts(trajectory, steps, started)
    projected["duration_ms"] = active_duration_from_sidecar(
        trajectory,
        steps,
        projected.get("duration_ms") if not isinstance(prior_steps, list) else None,
    )
    import_context = projected.get("import_context")
    source_timing = (
        import_context.get("source_timing")
        if isinstance(import_context, dict)
        and isinstance(import_context.get("source_timing"), dict)
        else {}
    )
    for key in ("duration_ms", "wall_duration_ms"):
        value = optional_int_value(source_timing.get(key))
        if value is not None:
            projected[key] = max(0, value)
    projected["prompt_unavailable"] = not any(
        isinstance(step, dict) and step.get("source") == "user"
        for step in trajectory.get("steps") or []
    )
    return projected


def merge_sidecar_owned_step_fields(
    canonical_steps: list[dict[str, Any]],
    prior_steps: Any,
) -> None:
    """Merge presentation and estimated timing only across matching identities."""

    if not isinstance(prior_steps, list):
        return
    prior_by_step = _unique_reports_by_identity(prior_steps, "step_id")
    for step in canonical_steps:
        prior = prior_by_step.get(str(step.get("step_id")))
        if prior is None:
            continue
        for key in ("duration_ms", "duration_source"):
            if step.get(key) is None and prior.get(key) is not None:
                step[key] = prior[key]

        prior_tools = _unique_reports_by_identity(
            prior.get("tool_calls"), "tool_call_id"
        )
        for tool in step.get("tool_calls") or []:
            if not isinstance(tool, dict):
                continue
            old_tool = prior_tools.get(str(tool.get("tool_call_id")))
            if old_tool is None:
                continue
            if old_tool.get("title") is not None:
                tool["title"] = old_tool["title"]
            for key in (
                "generation_duration_ms",
                "execution_duration_ms",
                "execution_duration_source",
            ):
                if tool.get(key) is None and old_tool.get(key) is not None:
                    tool[key] = old_tool[key]

        prior_observations = _unique_reports_by_identity(
            prior.get("observations"), "source_call_id"
        )
        for observation in step.get("observations") or []:
            if not isinstance(observation, dict):
                continue
            old_observation = prior_observations.get(
                str(observation.get("source_call_id"))
            )
            if old_observation is not None and old_observation.get("title") is not None:
                observation["title"] = old_observation["title"]


def _unique_reports_by_identity(value: Any, key: str) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        return {}
    found: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or item.get(key) is None:
            continue
        identity = str(item[key])
        if identity in found:
            duplicates.add(identity)
        else:
            found[identity] = item
    for identity in duplicates:
        found.pop(identity, None)
    return found


def active_duration_from_sidecar(
    trajectory: dict[str, Any],
    steps: list[dict[str, Any]],
    fallback: Any,
) -> int | None:
    total = 0
    observed = False
    for trajectory_step, step in zip(trajectory.get("steps") or [], steps, strict=True):
        if (
            isinstance(trajectory_step, dict)
            and trajectory_step.get("source") == "agent"
        ):
            duration = optional_int_value(step.get("duration_ms"))
            if duration is not None:
                total += duration
                observed = True
        for tool in step.get("tool_calls") or []:
            if not isinstance(tool, dict):
                continue
            duration = optional_int_value(tool.get("execution_duration_ms"))
            if duration is not None:
                total += duration
                observed = True
    return total if observed else optional_int_value(fallback)


def optional_int_value(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def project_canonical_step_facts(
    trajectory: dict[str, Any],
    step_reports: list[dict[str, Any]],
    started_at_ms: int,
) -> None:
    for step, report in zip(trajectory.get("steps") or [], step_reports, strict=True):
        if not isinstance(step, dict):
            continue
        timestamp = atif_timestamp_ms(step)
        if timestamp is not None:
            report["timestamp_ms"] = timestamp
            report["elapsed_ms"] = timestamp - started_at_ms if started_at_ms else None
        extra = step.get("extra") if isinstance(step.get("extra"), dict) else {}
        for key in ("duration_ms", "duration_source", "truncated"):
            if key in extra:
                report[key] = extra[key]

        calls = {
            str(call.get("tool_call_id")): call
            for call in step.get("tool_calls") or []
            if isinstance(call, dict) and call.get("tool_call_id") is not None
        }
        results = [
            item
            for item in (step.get("observation") or {}).get("results") or []
            if isinstance(item, dict)
        ]
        result_by_call = {
            str(item["source_call_id"]): item
            for item in results
            if item.get("source_call_id") is not None
        }
        for tool_report in report.get("tool_calls") or []:
            call_id = str(tool_report.get("tool_call_id") or "")
            call = calls.get(call_id) or {}
            call_extra = (
                call.get("extra") if isinstance(call.get("extra"), dict) else {}
            )
            started = iso_timestamp_ms(call_extra.get("started_at"))
            if started is not None:
                tool_report["timestamp_ms"] = started
            for key in ("generation_duration_ms", "truncated"):
                if key in call_extra:
                    tool_report[key] = call_extra[key]
            result = result_by_call.get(call_id) or {}
            result_extra = (
                result.get("extra") if isinstance(result.get("extra"), dict) else {}
            )
            if "status" in result_extra:
                tool_report["status"] = result_extra["status"]
            for key in ("execution_duration_ms", "execution_duration_source"):
                if key in result_extra:
                    tool_report[key] = result_extra[key]

        for observation_report, result in zip(
            report.get("observations") or [], results, strict=False
        ):
            result_extra = (
                result.get("extra") if isinstance(result.get("extra"), dict) else {}
            )
            if "status" in result_extra:
                observation_report["status"] = result_extra["status"]
            if "is_error" in result_extra:
                observation_report["tool_error"] = result_extra["is_error"]
            finished = iso_timestamp_ms(result_extra.get("finished_at"))
            if finished is not None:
                observation_report["timestamp_ms"] = finished
            if "truncated" in result_extra:
                observation_report["truncated"] = result_extra["truncated"]
        canonical_errors = [
            item.get("extra", {}).get("is_error")
            for item in results
            if isinstance(item.get("extra"), dict)
            and "is_error" in item.get("extra", {})
        ]
        if canonical_errors:
            report["tool_error"] = any(canonical_errors)


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


def trial_key_for(
    index: int,
    trajectory: dict[str, Any],
    config: ToolConfig,
    multi: bool,
    seen: dict[str, int],
) -> str:
    if not multi:
        base = "session:t001"
    else:
        base = f"session:{safe_key_part(trajectory.get('session_id') or f's{index}')}"
    count = seen.get(base, 0) + 1
    seen[base] = count
    return base if count == 1 else f"{base}:{count}"


def safe_key_part(value: object) -> str:
    text = str(value or "").strip().lower()
    out = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in text)
    return out.strip(".-") or "session"


def annotations_report(
    notes: list[NoteInput],
    metas: list[dict[str, Any]],
    cell_notes: list[dict[str, Any]] | None = None,
    analyses: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    cell_notes = cell_notes or []
    analyses = analyses or []
    if not notes and not cell_notes and not analyses:
        return None
    report_notes: list[dict[str, Any]] = []
    cli_notes_by_trial: dict[str, list[dict[str, Any]]] = {}
    cell_notes_by_trial: dict[str, list[dict[str, Any]]] = {}
    report_count = 0
    trial_counts: dict[str, int] = {}
    for note in cell_notes:
        trial_key = str(note.get("trial_key") or "")
        if not trial_key:
            continue
        cell_notes_by_trial.setdefault(trial_key, []).append(deepcopy(note))
    for note in notes:
        if note.index == 0:
            report_count += 1
            report_notes.append(
                {"label": f"Report note {report_count}", "markdown": note.markdown}
            )
            continue
        meta = metas[note.index - 1]
        trial_key = str(meta["trial_key"])
        trial_counts[trial_key] = trial_counts.get(trial_key, 0) + 1
        cli_notes_by_trial.setdefault(trial_key, []).append(
            {
                "trial_key": trial_key,
                "source": "cli",
                "label": f"CLI note {trial_counts[trial_key]}",
                "markdown": note.markdown,
            }
        )
    trial_notes: list[dict[str, Any]] = []
    for meta in metas:
        trial_key = str(meta["trial_key"])
        trial_notes.extend(cell_notes_by_trial.get(trial_key, []))
        trial_notes.extend(cli_notes_by_trial.get(trial_key, []))
    annotations: dict[str, Any] = {"report_notes": report_notes, "notes": trial_notes}
    if analyses:
        annotations["analysis"] = analyses
    return annotations


def analysis_reports(
    config: ToolConfig,
    prepared: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for item in prepared:
        meta = item["meta"]
        trajectory = item["trajectory"]
        report = computed_analysis_report(trajectory, meta)
        cached = cached_analysis_report(
            workspace_root=config.workspace_root,
            eval_slug=config.analysis_eval_slug,
            agent_id=item.get("analysis_agent_id"),
            session_id=trajectory.get("session_id"),
            trial_key=str(meta.get("trial_key") or ""),
        )
        if cached is not None:
            report = merge_analysis_report(report, cached)
        reports.append(report)
    return reports


def cell_note_reports(
    config: ToolConfig,
    prepared: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for item in prepared:
        meta = item["meta"]
        trajectory = item["trajectory"]
        report = cached_note_report(
            workspace_root=config.workspace_root,
            eval_slug=config.analysis_eval_slug,
            agent_id=item.get("analysis_agent_id"),
            session_id=trajectory.get("session_id"),
            trial_key=str(meta.get("trial_key") or ""),
        )
        if report is not None:
            reports.append(report)
    return reports


def note_reports_from_snapshots(
    source_reports: list[dict[str, Any]],
    metas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for index, source_report in enumerate(source_reports):
        if index >= len(metas) or not isinstance(source_report, dict):
            continue
        annotations = source_report.get("annotations")
        if not isinstance(annotations, dict):
            continue
        for item in annotations.get("notes") or []:
            if not isinstance(item, dict) or not isinstance(item.get("markdown"), str):
                continue
            remapped = {
                key: deepcopy(value)
                for key, value in item.items()
                if key in {"source", "label", "markdown", "source_ref"}
            }
            remapped["trial_key"] = str(metas[index].get("trial_key") or "")
            reports.append(remapped)
    return reports


def analysis_reports_from_snapshots(
    source_reports: list[dict[str, Any]],
    trajectories: list[dict[str, Any]],
    metas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for index, (trajectory, meta) in enumerate(zip(trajectories, metas, strict=True)):
        report = computed_analysis_report(trajectory, meta)
        source_report = source_reports[index] if index < len(source_reports) else None
        if not isinstance(source_report, dict):
            reports.append(report)
            continue
        annotations = source_report.get("annotations")
        if not isinstance(annotations, dict):
            reports.append(report)
            continue
        for item in annotations.get("analysis") or []:
            if not isinstance(item, dict):
                continue
            remapped = {
                key: deepcopy(value)
                for key, value in item.items()
                if key
                in {
                    "status",
                    "relative_path",
                    "md_report",
                    "relative_paths",
                    *ANALYSIS_REPORT_FIELDS,
                }
            }
            if remapped.get("status") != "cached" or not (
                remapped.get("relative_path") or remapped.get("markdown_reports")
            ):
                continue
            remapped["trial_key"] = str(metas[index].get("trial_key") or "")
            report = merge_analysis_report(report, remapped)
        reports.append(report)
    return reports


def computed_analysis_report(
    trajectory: dict[str, Any],
    meta: dict[str, Any],
) -> dict[str, Any]:
    return {
        "trial_key": str(meta.get("trial_key") or ""),
        "status": "computed",
        "analysis_metrics": {
            "auto": automatic_analysis_metrics(trajectory, meta),
        },
    }


def merge_analysis_report(
    base: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overlay.items():
        if key == "trial_key":
            continue
        if key == "analysis_metrics":
            merged["analysis_metrics"] = merge_analysis_metrics(
                merged.get("analysis_metrics"),
                value,
            )
            continue
        merged[key] = deepcopy(value)
    if overlay.get("status") == "cached":
        merged["status"] = "cached"
    return merged


def merge_analysis_metrics(base: Any, overlay: Any) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if isinstance(base, dict):
        for key, value in base.items():
            metrics[str(key)] = deepcopy(value)
    if isinstance(overlay, dict):
        for key, value in overlay.items():
            key_text = str(key)
            if key_text in RESERVED_ANALYSIS_METRIC_KEYS:
                continue
            metrics[key_text] = deepcopy(value)
    return metrics


def optional(key: str, value: Any) -> dict[str, Any]:
    return {} if value is None else {key: value}
