from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from psycheval._harbor_trials import (
    load_direct_harbor_trial_bundle,
    project_harbor_trial_bundle,
)
from psycheval._inspection.validation import validate_inspect_raw_only_args
from psycheval.cli.arguments import CliArgs
from psycheval.config import ToolConfig
from psycheval.inputs import AdapterAssignments, load_inputs
from psycheval.pipeline import build_report_from_loaded_inputs
from psycheval.trial_analysis import TrialAnalysisService


def inspect_report_for_args(
    args: CliArgs,
    adapter_assignments: AdapterAssignments,
    config: object,
) -> dict[str, Any]:
    validate_inspect_raw_only_args(args)
    source_ref_report = inspect_source_ref_report(args, config)
    if source_ref_report is not None:
        return source_ref_report
    path_reports, remaining_paths, remaining_indexes = direct_inspect_reports(
        getattr(args, "path", None) or [],
        adapter_assignments,
        config,
    )
    reports: list[dict[str, Any]] = []
    if remaining_paths or getattr(args, "db", None):
        remapped_assignments = replace(
            adapter_assignments,
            path_adapters={
                compact_index: adapter_assignments.path_adapters[original_index]
                for compact_index, original_index in enumerate(
                    remaining_indexes,
                    start=1,
                )
                if original_index in adapter_assignments.path_adapters
            },
        )
        load_args = replace(
            args,
            path=tuple(remaining_paths),
        )
        loaded_inputs = load_inputs(load_args, remapped_assignments, config=config)
        if loaded_inputs.sessions:
            converted = split_report_sources(
                build_report_from_loaded_inputs(
                    loaded_inputs,
                    config,
                    list(args.note),
                )
            )
            path_chunks = converted[: len(remaining_paths)]
            if len(path_chunks) != len(remaining_paths):
                raise ValueError("path inputs did not produce one source each")
            for original_index, report in zip(
                remaining_indexes,
                path_chunks,
                strict=True,
            ):
                path_reports[original_index - 1] = report
            reports.extend(converted[len(remaining_paths) :])
    reports = [report for report in path_reports if report is not None] + reports
    if not reports:
        raise ValueError("missing input source; pass --path, --db, or --source-ref")
    return merge_reports(reports)


def inspect_source_ref_report(
    args: CliArgs,
    config: object,
) -> dict[str, Any] | None:
    source_refs = list(getattr(args, "source_refs", None) or [])
    if not source_refs:
        return None
    if getattr(args, "path", None) or getattr(args, "db", None):
        raise ValueError("--source-ref cannot be combined with --path or --db")
    if getattr(args, "adapter", None):
        raise ValueError("--source-ref is self-describing; do not assign an adapter")
    if getattr(args, "session_id", None):
        raise ValueError("--session-id is only valid with --db")
    if not isinstance(config, ToolConfig) or not config.workspace_root:
        raise ValueError("--source-ref requires an initialized workspace root")

    service = TrialAnalysisService(config.workspace_root)
    try:
        documents = service.documents(source_refs)
    finally:
        service.close()
    trajectories: list[dict[str, Any]] = []
    metas: list[dict[str, Any]] = []
    for document in documents:
        meta = (
            dict(document.meta)
            if document.meta is not None
            else harbor_diagnostic_meta(document, Path(config.workspace_root))
        )
        if document.last_error:
            meta.setdefault("diagnostic", document.last_error)
        data_ref = meta.get("data_ref")
        path = (
            Path(data_ref["path"])
            if isinstance(data_ref, dict) and isinstance(data_ref.get("path"), str)
            else Path(config.workspace_root)
        )
        trajectories.append(
            document.trajectory or empty_trajectory_for_meta(meta, path)
        )
        metas.append(meta)
    return {
        "schema_version": None,
        "includes": ["core"],
        "trajectory": trajectories,
        "trajectory_meta": metas,
    }


def direct_inspect_reports(
    paths: list[str],
    adapter_assignments: AdapterAssignments,
    config: object,
) -> tuple[list[dict[str, Any] | None], list[str], list[int]]:
    reports: list[dict[str, Any] | None] = []
    remaining: list[str] = []
    remaining_indexes: list[int] = []
    for index, raw_path in enumerate(paths, start=1):
        bundle = (
            load_direct_harbor_trial_bundle(raw_path, config)
            if isinstance(config, ToolConfig)
            else None
        )
        if bundle is not None:
            if index in adapter_assignments.path_adapters:
                raise ValueError(
                    f"path input p{index} is a self-describing Harbor Trial; "
                    "do not assign an adapter"
                )
            documents = project_harbor_trial_bundle(bundle)
            trajectories: list[dict[str, Any]] = []
            metas: list[dict[str, Any]] = []
            for document in documents:
                meta = (
                    dict(document.meta)
                    if document.meta is not None
                    else harbor_diagnostic_meta(document, bundle.trial_dir)
                )
                if document.last_error:
                    meta.setdefault("diagnostic", document.last_error)
                trajectory = document.trajectory or empty_trajectory_for_meta(
                    meta,
                    bundle.trial_dir,
                )
                trajectories.append(trajectory)
                metas.append(meta)
            reports.append(
                {
                    "schema_version": None,
                    "includes": ["core"],
                    "trajectory": trajectories,
                    "trajectory_meta": metas,
                }
            )
            continue
        path = Path(raw_path)
        parsed = read_json_object(path)
        if parsed is None:
            reports.append(None)
            remaining.append(raw_path)
            remaining_indexes.append(index)
            continue
        report = report_from_direct_json(parsed, path)
        if report is None:
            reports.append(None)
            remaining.append(raw_path)
            remaining_indexes.append(index)
        else:
            reports.append(report)
    return reports, remaining, remaining_indexes


def harbor_diagnostic_meta(document: Any, path: Path) -> dict[str, Any]:
    source = document.source if isinstance(document.source, dict) else {}
    return {
        "trial_key": document.source_key,
        "adapter": "harbor",
        "status": document.last_status,
        "failure_class": "harbor-source",
        "warnings": [document.last_error] if document.last_error else [],
        "diagnostic": document.last_error,
        "trajectory_available": False,
        "data_ref": {
            "kind": "harbor-trial",
            "label": source.get("label") or path.name,
            "path": str(path),
        },
        "task_name": source.get("task_name"),
        "job_name": source.get("job_name"),
        "trial_name": source.get("trial_name"),
        "rewards": source.get("rewards") or {},
        "harbor_step": {
            "name": source.get("step_name"),
            "index": source.get("step_index"),
            "count": source.get("step_count"),
        }
        if source.get("step_name")
        else {},
        "harbor_trial_evaluation": source.get("harbor_trial_evaluation") or {},
        "harbor_provenance": source.get("harbor_provenance") or {},
        "total_events": 0,
        "unmapped_events": 0,
        "prompt_unavailable": True,
    }


def read_json_object(path: Path) -> Any:
    if path.suffix.lower() != ".json":
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def report_from_direct_json(parsed: Any, path: Path) -> dict[str, Any] | None:
    if is_report_json(parsed):
        return {
            "schema_version": parsed.get("schema_version"),
            "includes": parsed.get("includes", []),
            "trajectory": list(parsed.get("trajectory") or []),
            "trajectory_meta": list(parsed.get("trajectory_meta") or []),
        }
    if is_atif_trajectory(parsed):
        return {
            "schema_version": None,
            "includes": ["core"],
            "trajectory": [parsed],
            "trajectory_meta": [meta_from_trajectory(parsed, path)],
        }
    metas = meta_list_from_json(parsed)
    if metas is not None:
        return {
            "schema_version": None,
            "includes": ["core"],
            "trajectory": [empty_trajectory_for_meta(meta, path) for meta in metas],
            "trajectory_meta": metas,
        }
    return None


def is_report_json(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("trajectory"), list)
        and isinstance(value.get("trajectory_meta"), list)
    )


def is_atif_trajectory(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and str(value.get("schema_version") or "").startswith("ATIF-")
        and isinstance(value.get("agent"), dict)
    )


def meta_list_from_json(value: Any) -> list[dict[str, Any]] | None:
    if isinstance(value, dict) and looks_like_meta(value):
        return [value]
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        items = [item for item in value if isinstance(item, dict)]
        return items if items and all(looks_like_meta(item) for item in items) else None
    return None


def looks_like_meta(value: dict[str, Any]) -> bool:
    keys = {
        "trial_key",
        "adapter",
        "status",
        "steps",
        "duration_ms",
        "wall_duration_ms",
    }
    return bool(keys & set(value))


def meta_from_trajectory(trajectory: dict[str, Any], path: Path) -> dict[str, Any]:
    steps = trajectory.get("steps") if isinstance(trajectory.get("steps"), list) else []
    return {
        "trial_key": str(
            trajectory.get("trajectory_id") or trajectory.get("session_id") or path.stem
        ),
        "adapter": "atif",
        "status": "passed",
        "warnings": [],
        "data_ref": {"label": path.name, "path": str(path)},
        "steps": [
            {
                "step_id": step.get("step_id", index)
                if isinstance(step, dict)
                else index,
                "tool_calls": [],
                "observations": [],
                "tool_error": False,
                "truncated": False,
            }
            for index, step in enumerate(steps, start=1)
        ],
    }


def empty_trajectory_for_meta(meta: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "schema_version": "ATIF-v1.7",
        "session_id": meta.get("session_id") or meta.get("trial_key") or path.stem,
        "trajectory_id": meta.get("trial_key") or path.stem,
        "agent": {"name": meta.get("adapter") or "metadata-only"},
        "steps": [],
        "final_metrics": {},
    }


def merge_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    trajectories: list[dict[str, Any]] = []
    metas: list[dict[str, Any]] = []
    for report in reports:
        trajectories.extend(
            item for item in report.get("trajectory", []) if isinstance(item, dict)
        )
        metas.extend(
            item for item in report.get("trajectory_meta", []) if isinstance(item, dict)
        )
    while len(metas) < len(trajectories):
        metas.append({})
    while len(trajectories) < len(metas):
        trajectories.append(
            {
                "schema_version": "ATIF-v1.7",
                "agent": {},
                "steps": [],
                "final_metrics": {},
            }
        )
    return {
        "schema_version": None,
        "includes": ["core"],
        "trajectory": trajectories,
        "trajectory_meta": metas,
    }


def split_report_sources(report: dict[str, Any]) -> list[dict[str, Any]]:
    trajectories = [
        item for item in report.get("trajectory", []) if isinstance(item, dict)
    ]
    metas = [
        item for item in report.get("trajectory_meta", []) if isinstance(item, dict)
    ]
    count = max(len(trajectories), len(metas))
    chunks: list[dict[str, Any]] = []
    for index in range(count):
        chunks.append(
            {
                "schema_version": None,
                "includes": ["core"],
                "trajectory": trajectories[index : index + 1],
                "trajectory_meta": metas[index : index + 1],
            }
        )
    return chunks
