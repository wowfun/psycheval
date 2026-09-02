from __future__ import annotations

import json
import sqlite3
from typing import Any

from psycheval.evaluation_report_identity import evaluation_report_ref


def query_evaluation_report_page(
    connection: sqlite3.Connection,
    *,
    generation: int,
    checking: bool,
    valid: bool,
    page: int,
    page_size: int,
    search: str,
) -> dict[str, Any]:
    if not valid:
        return {
            "generation": 0,
            "checking": checking,
            "stale": checking,
            "total": 0,
            "page": page,
            "page_size": page_size,
            "items": [],
        }
    where = "1"
    parameters: list[Any] = []
    if search:
        pattern = f"%{_escape_like(search)}%"
        where = (
            "(title LIKE ? ESCAPE '\\' COLLATE NOCASE "
            "OR source_label LIKE ? ESCAPE '\\' COLLATE NOCASE "
            "OR source_keys_json LIKE ? ESCAPE '\\' COLLATE NOCASE)"
        )
        parameters.extend((pattern, pattern, pattern))
    total = int(
        connection.execute(
            f"SELECT COUNT(*) FROM evaluation_reports WHERE {where}",
            parameters,
        ).fetchone()[0]
    )
    offset = (page - 1) * page_size
    records = connection.execute(
        f"""
        SELECT report_ref, title, source_label, filename, format,
               source_keys_json, primary_source_key
        FROM evaluation_reports
        WHERE {where}
        ORDER BY updated_at_ms DESC, report_ref ASC
        LIMIT ? OFFSET ?
        """,
        [*parameters, page_size, offset],
    ).fetchall()
    return {
        "generation": generation,
        "checking": checking,
        "stale": checking,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "report_ref": str(record["report_ref"]),
                "title": str(record["title"]),
                "filename": str(record["filename"]),
                "format": str(record["format"]),
                "source_keys": json.loads(str(record["source_keys_json"])),
                "primary_source_key": str(record["primary_source_key"]),
                "source_label": str(record["source_label"]),
            }
            for record in records
        ],
    }


def evaluation_report_location(
    connection: sqlite3.Connection,
    report_ref: str,
) -> dict[str, Any]:
    value = str(report_ref or "")
    if not value.startswith("analysis:") or len(value) != len("analysis:") + 64:
        raise ValueError(f"unknown report: {value}")
    record = connection.execute(
        """
        SELECT report_ref, source_ref, title, source_label, filename, format,
               source_keys_json, primary_source_key
        FROM evaluation_reports
        WHERE report_ref = ?
        """,
        (value,),
    ).fetchone()
    if record is None:
        raise ValueError(f"unknown report: {value}")
    return {
        "report_ref": str(record["report_ref"]),
        "source_ref": str(record["source_ref"]),
        "title": str(record["title"]),
        "filename": str(record["filename"]),
        "format": str(record["format"]),
        "source_keys": tuple(json.loads(str(record["source_keys_json"]))),
        "primary_source_key": str(record["primary_source_key"]),
        "source_label": str(record["source_label"]),
    }


def replace_evaluation_report_projection(connection: sqlite3.Connection) -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in connection.execute(
        "SELECT source_key, source_ref, row_json FROM cells ORDER BY source_ref"
    ):
        row = json.loads(str(record["row_json"]))
        if row.get("evaluation_report_present") is not True:
            continue
        source_ref = str(record["source_ref"])
        canonical_ref = _canonical_source_ref(source_ref)
        if canonical_ref is None:
            continue
        grouped.setdefault(canonical_ref, []).append(
            {
                **row,
                "source_key": str(record["source_key"]),
                "source_ref": source_ref,
            }
        )

    connection.execute("DELETE FROM evaluation_reports")
    for source_ref, rows in grouped.items():
        rows.sort(key=_source_sort_key)
        source_keys = list(
            dict.fromkeys(
                str(row["source_key"])
                for row in rows
                if str(row.get("source_key") or "")
            )
        )
        if not source_keys:
            continue
        primary = next((row for row in rows if row.get("readable") is True), rows[0])
        primary_source_key = str(primary["source_key"])
        source_label = _source_label(primary)
        connection.execute(
            """
            INSERT INTO evaluation_reports (
                report_ref, source_ref, title, source_label, filename, format,
                source_keys_json, primary_source_key, updated_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evaluation_report_ref(source_ref),
                source_ref,
                source_label,
                source_label,
                "analysis.md",
                "markdown",
                json.dumps(source_keys, ensure_ascii=False, separators=(",", ":")),
                primary_source_key,
                max(int(row.get("updated_at_ms") or 0) for row in rows),
            ),
        )


def _canonical_source_ref(source_ref: str) -> str | None:
    parts = source_ref.split("/")
    if len(parts) == 5 and parts[0] == "runs" and all(parts):
        return source_ref
    if (
        len(parts) in {4, 6}
        and parts[0] == "harbor"
        and all(parts)
        and (len(parts) == 4 or parts[4] == "steps")
    ):
        return "/".join(parts[:4])
    return None


def _source_sort_key(row: dict[str, Any]) -> tuple[int, str]:
    raw_index = row.get("step_index")
    try:
        step_index = int(raw_index) if raw_index is not None else -1
    except (TypeError, ValueError):
        step_index = 1_000_000
    return step_index, str(row.get("source_ref") or "")


def _source_label(row: dict[str, Any]) -> str:
    for field in (
        "source_alias",
        "display_alias",
        "task_name",
        "trial_name",
        "source_key",
    ):
        value = str(row.get(field) or "").strip()
        if value:
            return value
    return "Evaluation report"


def _escape_like(value: str) -> str:
    return (
        value.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )


__all__ = [
    "evaluation_report_location",
    "query_evaluation_report_page",
    "replace_evaluation_report_projection",
]
