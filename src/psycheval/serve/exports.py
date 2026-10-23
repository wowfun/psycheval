from __future__ import annotations

import io
import json
from dataclasses import dataclass, replace
from typing import Any

import xlsxwriter

from psycheval.config import ToolConfig
from psycheval.i18n import messages_for
from psycheval.metric_contract import BUILTIN_IDS, finite_number, metric_descriptions
from psycheval.report.metrics import tool_success_rate
from psycheval.serve.summary_xlsx import (
    EXCEL_CONTENT_TYPE,
    METRIC_NUMBER_FORMATS,
    SummaryWorksheet,
    metric_heading,
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
            content=xlsx_summary(
                rows,
                catalog.metric_metadata()["metric_descriptions"],
                locale=config.locale,
            ),
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


def xlsx_summary(
    rows: list[dict[str, Any]],
    descriptions: list[dict[str, Any]] | None = None,
    *,
    locale: str = "en",
) -> bytes:
    columns = [
        ("Dataset", lambda row: row.get("dataset_id")),
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
        ("Last Turn End Source", lambda row: row.get("last_turn_finished_at_source")),
        ("TTFT Sum (ms)", lambda row: row.get("ttft_ms_sum")),
        ("TTFT Samples", lambda row: row.get("ttft_sample_count")),
        ("Decode Duration (ms)", lambda row: row.get("decode_duration_ms")),
        ("Decode Tokens", lambda row: row.get("decode_token_count")),
        ("Decode Samples", lambda row: row.get("decode_sample_count")),
        ("Cache-covered Prompt Tokens", lambda row: row.get("cache_prompt_tokens")),
        ("Cache-read Tokens", lambda row: row.get("cache_read_tokens")),
        ("Cache Samples", lambda row: row.get("cache_sample_count")),
        ("#Analysis", lambda row: int(row.get("analysis_count") or 0)),
        ("Source Key", lambda row: row.get("source_key")),
    ]
    definitions = (
        descriptions or metric_descriptions(BUILTIN_IDS)["metric_descriptions"]
    )
    messages = messages_for(locale)

    def measured(row: dict[str, Any], key: str) -> int | float | None:
        if "metric_values" in row:
            return finite_number(row["metric_values"].get(key))
        if key == "tool_success_rate":
            return tool_success_rate(
                row.get("total_tool_calls"), row.get("total_tool_errors")
            )
        return finite_number(row.get(key))

    definitions = [
        item
        for item in definitions
        if any(measured(row, item["key"]) is not None for row in rows)
    ]
    output = io.BytesIO()
    with xlsxwriter.Workbook(
        output,
        {
            "constant_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
        },
    ) as workbook:
        sheet = workbook.add_worksheet("Leaderboard")
        header = workbook.add_format({"bold": True})
        metric_formats = []
        for column, (label, _getter) in enumerate(columns):
            sheet.write_string(0, column, label, header)
        for column, definition in enumerate(definitions, len(columns)):
            sheet.write_string(0, column, metric_heading(definition, messages), header)
            number_format = METRIC_NUMBER_FORMATS[definition["type"]]
            metric_formats.append(workbook.add_format({"num_format": number_format}))
        for index, row in enumerate(rows, 1):
            for column, (_label, getter) in enumerate(columns):
                value = getter(row)
                sheet.write_string(index, column, "" if value is None else str(value))
            for offset, definition in enumerate(definitions):
                value = measured(row, definition["key"])
                column = len(columns) + offset
                if value is not None:
                    sheet.write_number(
                        index,
                        column,
                        value / 86_400_000 if definition.get("unit") == "ms" else value,
                        metric_formats[offset],
                    )
                else:
                    sheet.write_blank(index, column, None, metric_formats[offset])
        sheet.freeze_panes(1, 0)
        sheet.set_column(0, len(columns) + len(definitions) - 1, 20)
    return output.getvalue()
