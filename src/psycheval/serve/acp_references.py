"""Administrator-selected text references; no evidence-content resolution."""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from pathlib import Path, PureWindowsPath
from typing import TYPE_CHECKING, Any, Callable

from psycheval.evaluation_report_identity import evaluation_report_ref
from psycheval.serve.api_support import harbor_workspace
from psycheval.serve.errors import HttpError

if TYPE_CHECKING:
    from psycheval.serve.runtime import ServeRuntime

MAX_ASSOCIATED_REFERENCES = 64


def reference_path(value: str | Path) -> str:
    text = str(value)
    if any(_control(char) for char in text):
        raise ValueError("path contains control characters")
    # Absolute Windows paths also occur in retained metadata on a POSIX host.
    return text.replace("\\", "/") if PureWindowsPath(text).is_absolute() else text


def _control(char: str) -> bool:
    return unicodedata.category(char).startswith("C") or char in "\u2028\u2029"


def reference_value(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return "".join(f"\\u{ord(char):04x}" if _control(char) else char for char in text)


def _lines(values: dict[str, Any]) -> str:
    return "\n".join(
        f"{key}: {reference_value(value)}"
        for key, value in values.items()
        if value is not None
    )


def reference_candidates(
    runtime: ServeRuntime, reference: dict[str, Any]
) -> list[dict[str, Any]]:
    kind = reference.get("kind")
    fields = {
        "source": {"kind", "source_key", "trajectory_id", "step_id"},
        "dataset_task": {"kind", "dataset_id", "task"},
        "report": {"kind", "report_ref"},
    }
    if not isinstance(kind, str) or kind not in fields or set(reference) - fields[kind]:
        raise HttpError(400, "invalid reference identity")
    if any(
        not isinstance(value, str) or not value or len(value) > 512
        for value in reference.values()
    ):
        raise HttpError(
            400, "reference identity fields must be nonempty bounded strings"
        )
    required = {
        "source": {"source_key"},
        "dataset_task": {"dataset_id", "task"},
        "report": {"report_ref"},
    }[kind]
    if not required <= reference.keys() or (
        "step_id" in reference and "trajectory_id" not in reference
    ):
        raise HttpError(400, "reference identity is incomplete")
    candidates: list[dict[str, Any]] = []

    def unavailable(
        id: str, label: str, reason: str, *, label_key: str | None = None
    ) -> None:
        candidates.append(
            {
                "id": id,
                "label": reference_value(label),
                "label_key": label_key or id,
                "text": "",
                "selected": False,
                "reason": reference_value(reason),
            }
        )

    def add(
        id: str,
        label: str,
        selected: bool,
        build: Callable[[], dict[str, Any]],
        *,
        label_key: str | None = None,
    ) -> None:
        candidate = {
            "id": id,
            "label": reference_value(label),
            "label_key": label_key or id,
            "selected": selected,
        }
        try:
            candidate["text"] = _lines(
                {**build(), "workspace": reference_path(runtime.config.workspace_root)}
            )
        except (ValueError, OSError, KeyError, sqlite3.Error) as exc:
            candidate.update(text="", selected=False, reason=reference_value(str(exc)))
        candidates.append(candidate)

    def source_values(row, identity=None, locations=None):
        key = row["source_key"]
        if locations is None:
            locations = runtime.catalog.reference_locations((key,))
        if key not in locations:
            raise ValueError("associated source is unavailable")
        location = runtime.catalog.sources.reference_location(locations[key])
        return {
            "source_ref": row["source_ref"],
            "Read first": "peval view tr -r <workspace> --source-ref <source_ref>",
            **{key: reference_path(path) for key, path in location.items()},
            **(
                {key: identity.get(key) for key in ("trajectory_id", "step_id")}
                if identity
                else {}
            ),
        }

    def task_values(dataset_id, task, row=None):
        paths = harbor_workspace(runtime.store, runtime).task_location(dataset_id, task)
        values = {
            "dataset_id": dataset_id,
            "task": task,
            **{key: reference_path(path) for key, path in paths.items()},
        }
        if row is not None:
            metadata = row.get("task_metadata") or {}
            provenance = row.get("harbor_provenance") or {}
            values.update(
                {
                    "Task observation": "cached catalog observation; not revalidated at insertion or send",
                    "observation_revision": row.get("artifact_revision"),
                    "observation_updated_at_ms": row.get("artifact_updated_at_ms"),
                    "task_status": metadata.get("status"),
                    "recorded_digest": provenance.get("task_digest"),
                    "observed_digest": metadata.get("live_digest"),
                    "digest_matches": metadata.get("digest_matches"),
                    "digest_comparison": metadata.get("digest_comparison"),
                }
            )
        return values

    def report_values(report_ref, location):
        return {
            "report_ref": report_ref,
            "report_path (read-only)": reference_path(location["path"]),
            "source_ref": location.get("source_ref"),
            "Publication": "Canonical reports use peval publish evaluation-report; do not overwrite the referenced file",
        }

    if kind == "source":
        try:
            row = runtime.catalog.row_for_key(reference["source_key"])
        except ValueError as exc:
            unavailable("source", "Source", str(exc))
            return candidates
        add("source", "Source", True, lambda: source_values(row, reference))
        metadata = row.get("task_metadata") or {}
        dataset_id = row.get("dataset_id")
        task = Path(str(metadata.get("path") or "")).name
        if dataset_id and task:
            add(
                "task",
                "Current Task and Dataset",
                False,
                lambda: task_values(dataset_id, task, row),
            )
        elif metadata:
            unavailable(
                "task",
                "Current Task and Dataset",
                metadata.get("diagnostic")
                or metadata.get("status")
                or "Task location is unavailable or ambiguous",
            )
        source_ref = (
            row["source_ref"].split("/steps/", 1)[0]
            if row["source_ref"].startswith("harbor/")
            else row["source_ref"]
        )
        report_ref = evaluation_report_ref(source_ref)
        if row.get("evaluation_report_present"):
            add(
                "report",
                "Canonical report",
                False,
                lambda: report_values(
                    report_ref, runtime.report_library.reference_location(report_ref)
                ),
                label_key="canonical_report",
            )
    elif kind == "dataset_task":
        add(
            "task",
            "Current Task and Dataset",
            True,
            lambda: task_values(reference["dataset_id"], reference["task"]),
        )
    else:
        report_ref = reference["report_ref"]
        try:
            location = runtime.report_library.reference_location(report_ref)
        except (ValueError, OSError, sqlite3.Error) as exc:
            unavailable("report", "Report (read-only)", str(exc))
            return candidates
        add(
            "report",
            "Report (read-only)",
            True,
            lambda: report_values(report_ref, location),
        )
        field = "source_keys" if "source_keys" in location else "source_refs"
        identities = tuple(dict.fromkeys(location.get(field, ())))
        limited = identities[:MAX_ASSOCIATED_REFERENCES]
        try:
            rows = runtime.catalog.binding_rows(**{field: limited})
            # Include missing associations in the same bound as available rows.
            row_field = "source_key" if field == "source_keys" else "source_ref"
            found = {row[row_field] for row in rows}
            missing = [identity for identity in limited if identity not in found]
            selected_rows = rows[:MAX_ASSOCIATED_REFERENCES]
            locations = (
                runtime.catalog.reference_locations(
                    tuple(row["source_key"] for row in selected_rows)
                )
                if selected_rows
                else {}
            )
        except (ValueError, OSError, sqlite3.Error) as exc:
            unavailable("associations", "Associated sources", str(exc))
            return candidates
        for row in selected_rows:
            add(
                f"source:{row['source_key']}",
                row["source_key"],
                False,
                lambda row=row: source_values(row, locations=locations),
                label_key="associated_source",
            )
        for identity in missing[: MAX_ASSOCIATED_REFERENCES - len(selected_rows)]:
            unavailable(
                f"source:{identity}",
                identity,
                "associated source is unavailable",
                label_key="associated_source",
            )
        if (
            len(identities) > len(limited)
            or len(rows) + len(missing) > MAX_ASSOCIATED_REFERENCES
        ):
            unavailable(
                "truncated",
                "More associated sources",
                f"Only the first {MAX_ASSOCIATED_REFERENCES} associated sources are shown; select a source directly for further references.",
            )
    return candidates
