from __future__ import annotations

import ntpath
import re
from pathlib import PurePosixPath
from typing import Any

from peval_py.serve.access import ADMIN_ROLE

CATALOG_PRIVATE_FIELDS = {
    "artifact_dir",
    "db_path",
    "input_path",
    "last_error",
    "path",
    "source_ref",
}
DATA_REF_PRIVATE_FIELDS = {"path", "relative_path", "source_ref"}
ANALYSIS_PRIVATE_FIELDS = {"relative_path", "relative_paths", "source_ref"}
TASK_METADATA_PUBLIC_FIELDS = {
    "description",
    "digest_comparison",
    "digest_matches",
    "keywords",
    "live",
    "live_digest",
    "name",
    "requested_name",
    "status",
    "version",
}
HARBOR_PROVENANCE_PUBLIC_FIELDS = {
    "harbor_version",
    "job_id",
    "mount_id",
    "regrade",
    "result_id",
    "task_checksum",
    "task_digest",
    "task_digest_source",
    "task_source",
    "task_version",
}
REGRADE_PUBLIC_FIELDS = {"action", "task_digest", "trial_id", "type"}
DATA_REF_PUBLIC_FIELDS = {
    "job_name",
    "kind",
    "label",
    "lock_available",
    "source_revision",
    "task_name",
    "trial_name",
    *HARBOR_PROVENANCE_PUBLIC_FIELDS,
}
ABSOLUTE_PATH_IN_ERROR_RE = re.compile(
    r"(?:^|[\s'\"(])"
    r"(?P<path>[A-Za-z]:[\\/][^\s'\"()]+|\\\\[^\\\s]+\\[^\s'\"()]+|/[^\s'\"()]+)"
)


def project_catalog_payload(payload: dict[str, Any], role: str) -> dict[str, Any]:
    if role == ADMIN_ROLE:
        return payload
    projected = dict(payload)
    items = payload.get("items")
    if isinstance(items, list):
        projected["items"] = [project_catalog_row(item) for item in items]
    return projected


def project_catalog_rows(rows: list[dict[str, Any]], role: str) -> list[dict[str, Any]]:
    if role == ADMIN_ROLE:
        return rows
    return [project_catalog_row(row) for row in rows]


def project_catalog_row(row: dict[str, Any]) -> dict[str, Any]:
    projected = dict(row)
    source_path = next(
        (
            projected.get(field)
            for field in ("path", "input_path", "db_path", "artifact_dir", "source_ref")
            if projected.get(field)
        ),
        None,
    )
    for field in CATALOG_PRIVATE_FIELDS:
        projected.pop(field, None)
    if source_path and isinstance(projected.get("label"), str):
        projected["label"] = _safe_source_label(projected["label"])
    task_metadata = row.get("task_metadata")
    if isinstance(task_metadata, dict):
        projected["task_metadata"] = _project_task_metadata(task_metadata)
    harbor_provenance = row.get("harbor_provenance")
    if isinstance(harbor_provenance, dict):
        projected["harbor_provenance"] = _project_harbor_provenance(harbor_provenance)
    return projected


def project_detail_payload(payload: dict[str, Any], role: str) -> dict[str, Any]:
    if role == ADMIN_ROLE:
        return payload
    projected = dict(payload)
    report = payload.get("report")
    if isinstance(report, dict):
        projected["report"] = project_report(report)
    return projected


def project_report(report: dict[str, Any]) -> dict[str, Any]:
    projected = dict(report)
    trajectory_meta = report.get("trajectory_meta")
    if isinstance(trajectory_meta, list):
        projected_meta: list[Any] = []
        for original_meta in trajectory_meta:
            if not isinstance(original_meta, dict):
                projected_meta.append(original_meta)
                continue
            meta = dict(original_meta)
            data_ref = original_meta.get("data_ref")
            if isinstance(data_ref, dict):
                data_ref = dict(data_ref)
                original_path = data_ref.get("path") or data_ref.get("relative_path")
                for field in DATA_REF_PRIVATE_FIELDS:
                    data_ref.pop(field, None)
                if original_path and isinstance(data_ref.get("label"), str):
                    data_ref["label"] = _safe_source_label(data_ref["label"])
                meta["data_ref"] = _project_data_ref(data_ref)
            task_metadata = original_meta.get("task_metadata")
            if isinstance(task_metadata, dict):
                meta["task_metadata"] = _project_task_metadata(task_metadata)
            harbor_provenance = original_meta.get("harbor_provenance")
            if isinstance(harbor_provenance, dict):
                meta["harbor_provenance"] = _project_harbor_provenance(
                    harbor_provenance
                )
            projected_meta.append(meta)
        projected["trajectory_meta"] = projected_meta

    annotations = report.get("annotations")
    if isinstance(annotations, dict):
        projected_annotations = dict(annotations)
        analysis = annotations.get("analysis")
        if isinstance(analysis, list):
            projected_analysis: list[Any] = []
            for original_item in analysis:
                if not isinstance(original_item, dict):
                    projected_analysis.append(original_item)
                    continue
                item = dict(original_item)
                for field in ANALYSIS_PRIVATE_FIELDS:
                    item.pop(field, None)
                markdown_reports = original_item.get("markdown_reports")
                if isinstance(markdown_reports, list):
                    item["markdown_reports"] = [
                        _project_analysis_markdown_report(report)
                        for report in markdown_reports
                    ]
                projected_analysis.append(item)
            projected_annotations["analysis"] = projected_analysis
        notes = annotations.get("notes")
        if isinstance(notes, list):
            projected_notes: list[Any] = []
            for original_item in notes:
                if not isinstance(original_item, dict):
                    projected_notes.append(original_item)
                    continue
                item = dict(original_item)
                item.pop("source_ref", None)
                projected_notes.append(item)
            projected_annotations["notes"] = projected_notes
        projected["annotations"] = projected_annotations
    return projected


def project_guest_error(status: int, message: str, role: str) -> str:
    if role == ADMIN_ROLE:
        return message
    if status < 500 and not _contains_server_path(message):
        return message
    if status < 500:
        return "request could not be completed"
    return "internal server error"


def _contains_server_path(message: str) -> bool:
    for match in ABSOLUTE_PATH_IN_ERROR_RE.finditer(message):
        candidate = match.group("path")
        if candidate == "/api" or candidate.startswith("/api/"):
            continue
        return True
    return False


def _project_harbor_provenance(value: dict[str, Any]) -> dict[str, Any]:
    projected = {
        key: item
        for key, item in value.items()
        if key in HARBOR_PROVENANCE_PUBLIC_FIELDS
    }
    regrade = value.get("regrade")
    if isinstance(regrade, dict):
        projected_regrade = {
            key: item for key, item in regrade.items() if key in REGRADE_PUBLIC_FIELDS
        }
        projected["regrade"] = projected_regrade
    return projected


def _project_task_metadata(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key in TASK_METADATA_PUBLIC_FIELDS}


def _project_data_ref(value: dict[str, Any]) -> dict[str, Any]:
    projected = {key: item for key, item in value.items() if key in DATA_REF_PUBLIC_FIELDS}
    regrade = value.get("regrade")
    if isinstance(regrade, dict):
        projected["regrade"] = {
            key: item for key, item in regrade.items() if key in REGRADE_PUBLIC_FIELDS
        }
    return projected


def _project_analysis_markdown_report(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    projected = dict(value)
    projected.pop("relative_path", None)
    return projected


def _safe_source_label(value: str) -> str:
    text = str(value).strip()
    if not text:
        return text
    windows_name = ntpath.basename(text.replace("/", "\\"))
    posix_name = PurePosixPath(text.replace("\\", "/")).name
    candidates = [item for item in (windows_name, posix_name) if item]
    return min(candidates, key=len) if candidates else "source"
