from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, replace
from html import escape
from typing import Any

from psycheval.config import ToolConfig
from psycheval.serve.summary_xlsx import (
    EXCEL_CONTENT_TYPE,
    SummaryWorksheet,
    summary_workbook,
)
from psycheval.serve.visibility import project_catalog_rows, project_report
from psycheval.state import CatalogQuery, ServeStateStore, WorkspaceCatalog

MAX_REPORT_EXPORT_CELLS = 100
MAX_REPORT_EXPORT_INPUT_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class ServeExport:
    filename: str
    content_type: str
    content: bytes


def build_summary_serve_export(
    sheets: list[SummaryWorksheet],
    config: ToolConfig,
    *,
    scope: str,
) -> ServeExport:
    if scope == "leaderboard":
        filename = "peval-leaderboard-summary.xlsx"
    elif scope == "saved_views":
        filename = "peval-saved-views.xlsx"
    else:
        raise ValueError("summary scope must be leaderboard or saved_views")
    return ServeExport(
        filename=filename,
        content_type=EXCEL_CONTENT_TYPE,
        content=summary_workbook(sheets, locale=config.locale),
    )


def build_serve_export(
    catalog: WorkspaceCatalog,
    store: ServeStateStore,
    config: ToolConfig,
    *,
    kind: str,
    query: CatalogQuery | None = None,
    view_queries: list[CatalogQuery] | None = None,
    source_keys: list[str] | None = None,
    audience: str = "admin",
) -> ServeExport:
    normalized_kind = str(kind or "").strip().lower()
    if normalized_kind in {"xlsx", "table"}:
        rows = query_all_catalog_rows(
            catalog,
            query or CatalogQuery(),
            view_queries=view_queries,
        )
        rows = project_catalog_rows(rows, audience)
        return ServeExport(
            filename="peval-leaderboard.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=xlsx_summary(rows),
        )
    if normalized_kind != "json":
        raise ValueError("export kind must be xlsx or json")
    keys = list(dict.fromkeys(str(key) for key in source_keys or [] if str(key)))
    if not keys:
        raise ValueError("source_keys must include at least one source")
    if len(keys) > MAX_REPORT_EXPORT_CELLS:
        raise ValueError(f"JSON export is limited to {MAX_REPORT_EXPORT_CELLS} cells")
    resolved = catalog.resolve_keys(keys)
    if resolved != keys:
        missing = next(key for key in keys if key not in set(resolved))
        raise ValueError(f"unknown source: {missing}")
    rows = [catalog.row_for_key(key) for key in keys]
    input_bytes = sum(int(row.get("input_bytes") or 0) for row in rows)
    if input_bytes > MAX_REPORT_EXPORT_INPUT_BYTES:
        raise ValueError("JSON export trajectory/meta input exceeds 50 MiB")
    report = store.report_for_rows(rows, config)
    if audience != "admin":
        report = project_report(report)
    return ServeExport(
        filename="peval-report-v19.json",
        content_type="application/json; charset=utf-8",
        content=(json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode(
            "utf-8"
        ),
    )


def query_all_catalog_rows(
    catalog: WorkspaceCatalog,
    query: CatalogQuery,
    *,
    view_queries: list[CatalogQuery] | None = None,
) -> list[dict[str, Any]]:
    normalized = query.normalized()
    rows: list[dict[str, Any]] = []
    page_number = 1
    while True:
        page = catalog.query(
            replace(normalized, page=page_number, page_size=100),
            include_facets=False,
            any_queries=view_queries or (),
        )
        rows.extend(item.to_dict() for item in page.items)
        if len(rows) >= page.total:
            return rows
        page_number += 1


def xlsx_summary(rows: list[dict[str, Any]]) -> bytes:
    columns = [
        ("Category", lambda row: row.get("source_category")),
        ("Tags", lambda row: ", ".join(row.get("display_tags") or [])),
        ("Custom Tags", lambda row: ", ".join(row.get("source_tags") or [])),
        ("Task Keywords", lambda row: ", ".join(row.get("task_keywords") or [])),
        ("Task", lambda row: row.get("task_name")),
        ("Job", lambda row: row.get("job_name")),
        ("Trial", lambda row: row.get("trial_name")),
        ("Session", lambda row: row.get("trial_session_id") or row.get("session_id")),
        ("Task / Alias", lambda row: row.get("display_alias")),
        ("Custom Alias", lambda row: row.get("source_alias")),
        ("Agent", lambda row: row.get("agent_name") or row.get("adapter")),
        ("Model", lambda row: row.get("model")),
        ("Provider", lambda row: row.get("model_provider")),
        ("Reward", lambda row: row.get("score")),
        (
            "Reward Dimensions",
            lambda row: json.dumps(
                row.get("rewards") or {}, ensure_ascii=False, sort_keys=True
            ),
        ),
        (
            "Harbor Provenance",
            lambda row: json.dumps(
                row.get("harbor_provenance") or {},
                ensure_ascii=False,
                sort_keys=True,
            ),
        ),
        (
            "Live Task Metadata",
            lambda row: json.dumps(
                row.get("task_metadata") or {},
                ensure_ascii=False,
                sort_keys=True,
            ),
        ),
        ("Result", lambda row: row.get("status")),
        ("Last Turn End", lambda row: row.get("last_turn_finished_at_ms")),
        ("Active Duration", lambda row: row.get("duration_ms")),
        ("Avg TTFT (ms)", lambda row: row.get("ttft_ms")),
        ("Decode TPS", lambda row: row.get("tps")),
        ("Turns", lambda row: row.get("turns")),
        ("Tool Calls", lambda row: row.get("total_tool_calls")),
        ("Tool Errors", lambda row: row.get("total_tool_errors")),
        ("Tokens", lambda row: row.get("tokens")),
        ("Cache Hit Rate", lambda row: row.get("cache_hit_rate")),
        ("TTFT Sum (ms)", lambda row: row.get("ttft_ms_sum")),
        ("TTFT Samples", lambda row: row.get("ttft_sample_count")),
        ("Decode Duration (ms)", lambda row: row.get("decode_duration_ms")),
        ("Decode Tokens", lambda row: row.get("decode_token_count")),
        ("Decode Samples", lambda row: row.get("decode_sample_count")),
        ("Cache-covered Prompt Tokens", lambda row: row.get("cache_prompt_tokens")),
        ("Cache-read Tokens", lambda row: row.get("cache_read_tokens")),
        ("Cache Samples", lambda row: row.get("cache_sample_count")),
        ("Cost", lambda row: row.get("cost_usd")),
        ("#Analysis", lambda row: int(row.get("analysis_count") or 0)),
        ("Source Key", lambda row: row.get("source_key")),
    ]
    values = [[label for label, _value in columns]]
    values.extend([[value(row) for _label, value in columns] for row in rows])
    files = {
        "[Content_Types].xml": _xml_declaration()
        + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels": _xml_declaration()
        + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": _xml_declaration()
        + '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Leaderboard" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": _xml_declaration()
        + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": _worksheet_xml(values),
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content.encode("utf-8"))
    return output.getvalue()


def _worksheet_xml(rows: list[list[Any]]) -> str:
    xml_rows: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column_index, value in enumerate(row):
            reference = f"{_column_name(column_index)}{row_index}"
            text = "" if value is None else str(value)
            cells.append(
                f'<c r="{reference}" t="inlineStr"><is><t>{escape(text)}</t></is></c>'
            )
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        _xml_declaration()
        + '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        + "".join(xml_rows)
        + "</sheetData></worksheet>"
    )


def _column_name(index: int) -> str:
    value = index + 1
    output = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        output = chr(65 + remainder) + output
    return output


def _xml_declaration() -> str:
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
