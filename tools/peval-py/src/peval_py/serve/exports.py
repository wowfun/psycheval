from __future__ import annotations

import io
import json
import zipfile
from base64 import b64encode
from dataclasses import dataclass, replace
from html import escape
from typing import Any

from peval_py.config import ToolConfig
from peval_py.html import render_workspace_snapshot_html
from peval_py.serve.payloads import WorkspaceSnapshotPresentation
from peval_py.serve.summary_xlsx import EXCEL_CONTENT_TYPE, SummaryWorksheet, summary_workbook
from peval_py.state import CatalogQuery, ServeStateStore, WorkspaceCatalog
from peval_py.workspace_reports import WorkspaceReportLibrary, render_workspace_report_preview
from peval_py.workspace_views import WorkspaceViewLibrary


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
) -> ServeExport:
    normalized_kind = str(kind or "").strip().lower()
    if normalized_kind in {"xlsx", "table"}:
        rows = query_all_catalog_rows(
            catalog,
            query or CatalogQuery(),
            view_queries=view_queries,
        )
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
    return ServeExport(
        filename="peval-report-v19.json",
        content_type="application/json; charset=utf-8",
        content=(json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )


def build_workspace_snapshot_export(
    catalog: WorkspaceCatalog,
    store: ServeStateStore,
    workspace_views: WorkspaceViewLibrary,
    workspace_reports: WorkspaceReportLibrary,
    config: ToolConfig,
    *,
    query: CatalogQuery,
    query_view_names: tuple[str, ...],
    selected_source_keys: tuple[str, ...],
    presentation: WorkspaceSnapshotPresentation,
    echarts_js: bytes,
) -> ServeExport:
    with catalog.read_snapshot_rows(
        query,
        any_queries=lambda: [workspace_views.get(name).filters for name in query_view_names],
        selected_source_keys=selected_source_keys,
    ) as (generation, rows):
        visible_views = [workspace_views.get(name) for name in presentation.visible_view_names]
        if not rows:
            if selected_source_keys:
                raise ValueError("selected sources do not match the current query")
            raise ValueError("workspace snapshot query matched no sources")
        if len(rows) > MAX_REPORT_EXPORT_CELLS:
            raise ValueError(
                f"workspace snapshot is limited to {MAX_REPORT_EXPORT_CELLS} cells"
            )
        report = store.report_for_rows(rows, config)
        metas = list(report.get("trajectory_meta") or [])
        source_trial_keys = {
            str(row.get("source_key")): str(meta.get("trial_key"))
            for row, meta in zip(rows, metas, strict=True)
        }
        catalog_rows = [
            {**row, "report_trial_key": source_trial_keys[str(row.get("source_key"))]}
            for row in rows
        ]

        report_payloads: list[dict[str, Any]] = []
        report_input_bytes = 0
        for metadata in workspace_reports.catalog(source_rows=rows):
            if not metadata.get("source_keys"):
                continue
            attachment = workspace_reports.read(str(metadata["report_id"]))
            report_input_bytes += len(attachment.content)
            report_payloads.append(
                {
                    **metadata,
                    "preview_base64": b64encode(
                        render_workspace_report_preview(attachment)
                    ).decode("ascii"),
                }
            )

        input_bytes = sum(int(row.get("input_bytes") or 0) for row in rows)
        if input_bytes + report_input_bytes > MAX_REPORT_EXPORT_INPUT_BYTES:
            raise ValueError(
                "workspace snapshot trajectory/meta and report input exceeds 50 MiB"
            )

        summary_payload = catalog.summarize_saved_views(
            [(view.name, view.filters, view.group_by) for view in visible_views]
        )
        final_keys = [str(row.get("source_key")) for row in rows]
        selected_source_key = presentation.selected_source_key
        if selected_source_key not in set(final_keys):
            selected_source_key = final_keys[0]
        selected_trial_key = source_trial_keys[selected_source_key]
        selected_index = next(
            index
            for index, meta in enumerate(metas)
            if str(meta.get("trial_key")) == selected_trial_key
        )
        selected_step_id = presentation.selected_step_id
        valid_step_ids = {
            str(step.get("step_id"))
            for step in list(report.get("trajectory") or [])[selected_index].get("steps", [])
            if step.get("step_id") is not None
        }
        if selected_step_id not in valid_step_ids:
            selected_step_id = None
        visible_names = [view.name for view in visible_views]
        snapshot = {
            "generation": generation,
            "catalog_rows": catalog_rows,
            "source_trial_keys": source_trial_keys,
            "presentation": {
                "summary_group_by": presentation.summary_group_by,
                "summary_statistic": presentation.summary_statistic,
                "summary_table_open": presentation.summary_table_open,
                "selected_source_key": selected_source_key,
                "selected_step_id": selected_step_id,
                "visible_view_names": visible_names,
                "workspace_view_filters": {
                    key: list(values)
                    for key, values in presentation.workspace_view_filters.items()
                },
                "open_view_tables": [
                    name for name in presentation.open_view_tables if name in set(visible_names)
                ],
            },
            "views": [view.to_dict() for view in visible_views],
            "view_summaries": summary_payload["views"],
            "reports": report_payloads,
        }
        try:
            echarts_text = echarts_js.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("cached ECharts asset must be UTF-8 JavaScript") from exc
        content = render_workspace_snapshot_html(
            report,
            snapshot,
            config.locale,
            echarts_text,
        ).encode("utf-8")
    return ServeExport(
        filename="peval-workspace-snapshot.html",
        content_type="text/html; charset=utf-8",
        content=content,
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
        ("Tags", lambda row: ", ".join(row.get("source_tags") or [])),
        ("Session", lambda row: row.get("trial_session_id") or row.get("session_id")),
        ("Session Alias", lambda row: row.get("source_alias")),
        ("Agent", lambda row: row.get("agent_name") or row.get("adapter")),
        ("Model", lambda row: row.get("model")),
        ("Result", lambda row: row.get("status")),
        ("Last Turn End", lambda row: row.get("last_turn_finished_at_ms")),
        ("Active Duration", lambda row: row.get("duration_ms")),
        ("Turns", lambda row: row.get("turns")),
        ("Tool Calls", lambda row: row.get("total_tool_calls")),
        ("Tool Errors", lambda row: row.get("total_tool_errors")),
        ("Tokens", lambda row: row.get("tokens")),
        ("Cost", lambda row: row.get("cost_usd")),
        ("Analysised", lambda row: bool(row.get("analysised"))),
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
