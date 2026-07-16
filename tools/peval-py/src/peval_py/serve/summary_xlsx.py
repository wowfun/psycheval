from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import xlsxwriter

from peval_py.i18n import messages_for


EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SUMMARY_STATISTICS = ("mean", "min", "q1", "p50", "q3", "p95", "max")
SUMMARY_METRICS = (
    ("duration_ms", "duration", "Active Duration", "duration"),
    ("tokens", "number", "Tokens", "tokens"),
    ("turns", "number", "Turns", "turns"),
    ("model_duration_ms", "duration", "Model call duration", "model_call_duration"),
    ("total_tool_calls", "number", "Tool Calls", "tool_calls"),
    ("tool_error_rate", "percent", "Tool Error Rate", "tool_error_rate"),
)
_ILLEGAL_SHEET_CHARACTERS = re.compile(r"[\[\]:*?/\\]")


@dataclass(frozen=True)
class SummaryWorksheet:
    name: str
    group_by: str
    matched_count: int
    groups: Sequence[Mapping[str, Any]]
    statistic: str = "mean"
    metadata: Sequence[tuple[str, str | int]] = ()


def summary_workbook(sheets: Sequence[SummaryWorksheet], *, locale: str = "en") -> bytes:
    if not sheets:
        raise ValueError("summary workbook must include at least one worksheet")
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(
        output,
        {
            "in_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
        },
    )
    formats = _workbook_formats(workbook)
    used_names: set[str] = set()
    messages = messages_for(locale)
    try:
        for index, sheet in enumerate(sheets, start=1):
            if sheet.statistic not in SUMMARY_STATISTICS:
                raise ValueError(f"unsupported summary statistic: {sheet.statistic}")
            sheet_name = unique_sheet_name(sheet.name, used_names)
            worksheet = workbook.add_worksheet(sheet_name)
            _write_summary_sheet(
                workbook,
                worksheet,
                sheet,
                index=index,
                formats=formats,
                messages=messages,
            )
    finally:
        workbook.close()
    return output.getvalue()


def unique_sheet_name(value: str, used_names: set[str]) -> str:
    base = _ILLEGAL_SHEET_CHARACTERS.sub("_", str(value or "")).strip().strip("'")
    base = base[:31].strip() or "View"
    candidate = base
    suffix_number = 2
    while candidate.casefold() in used_names:
        suffix = f" ({suffix_number})"
        candidate = f"{base[: 31 - len(suffix)].rstrip()}{suffix}"
        suffix_number += 1
    used_names.add(candidate.casefold())
    return candidate


def _write_summary_sheet(
    workbook: xlsxwriter.Workbook,
    worksheet: Any,
    sheet: SummaryWorksheet,
    *,
    index: int,
    formats: Mapping[str, Any],
    messages: Mapping[str, str],
) -> None:
    worksheet.hide_gridlines(2)
    worksheet.set_tab_color("#C56A3A")
    worksheet.set_column(0, 0, 22)
    worksheet.set_column(1, 1, 24)
    worksheet.set_column(2, 2, 11)
    worksheet.set_column(3, 9, 14)
    worksheet.set_column(10, 10, 3)
    worksheet.set_column(11, 26, 12)

    worksheet.merge_range(0, 0, 0, 9, "", formats["title"])
    worksheet.write_string(0, 0, sheet.name, formats["title"])
    metadata_row = 2
    for label, value in sheet.metadata:
        chunks = _excel_string_chunks(str(value))
        for chunk_index, chunk in enumerate(chunks):
            row_label = str(label) if chunk_index == 0 else f"{label} (cont.)"
            worksheet.write_string(metadata_row, 0, row_label, formats["meta_label"])
            worksheet.merge_range(
                metadata_row,
                1,
                metadata_row,
                9,
                "",
                formats["meta_value"],
            )
            worksheet.write_string(metadata_row, 1, chunk, formats["meta_value"])
            if "\n" in chunk:
                worksheet.set_row(
                    metadata_row,
                    min(72, 18 + chunk.count("\n") * 12),
                )
            metadata_row += 1

    table_header_row = metadata_row + 1
    headers = (
        "Metric",
        "Group",
        "Count",
        "Mean",
        "Min",
        "Q1",
        "P50",
        "Q3",
        "P95",
        "Max",
    )
    rows, metric_ranges = _summary_rows(sheet, messages)
    for column, header in enumerate(headers):
        worksheet.write_string(table_header_row, column, header, formats["table_header"])

    for row_offset, row_values in enumerate(rows, start=1):
        row = table_header_row + row_offset
        metric_type = str(row_values[10])
        worksheet.write_string(row, 0, str(row_values[0]), formats["text"])
        worksheet.write_string(row, 1, str(row_values[1]), formats["text"])
        worksheet.write_number(row, 2, int(row_values[2]), formats["integer"])
        for column, value in enumerate(row_values[3:10], start=3):
            _write_statistic_cell(worksheet, row, column, value, metric_type, formats)

    if rows:
        worksheet.add_table(
            table_header_row,
            0,
            table_header_row + len(rows),
            len(headers) - 1,
            {
                "name": f"SummaryTable{index}",
                "style": "Table Style Medium 2",
                "columns": [{"header": header} for header in headers],
            },
        )
    else:
        worksheet.autofilter(table_header_row, 0, table_header_row, len(headers) - 1)
        worksheet.merge_range(
            table_header_row + 2,
            0,
            table_header_row + 2,
            9,
            messages.get("saved_view_empty", "No matching sessions."),
            formats["empty"],
        )
    worksheet.freeze_panes(table_header_row + 1, 2)

    if not rows:
        return
    statistic_column = 3 + SUMMARY_STATISTICS.index(sheet.statistic)
    chart_positions = ((1, 11), (1, 20), (17, 11), (17, 20), (33, 11), (33, 20))
    metric_labels = {
        key: _metric_label(key, fallback, message_key, messages)
        for key, _kind, fallback, message_key in SUMMARY_METRICS
    }
    for (metric_key, _metric_type, _fallback, _message_key), position in zip(
        SUMMARY_METRICS,
        chart_positions,
    ):
        first_offset, last_offset = metric_ranges[metric_key]
        first_row = table_header_row + 1 + first_offset
        last_row = table_header_row + 1 + last_offset
        chart = workbook.add_chart({"type": "bar", "subtype": "clustered"})
        chart.add_series(
            {
                "name": metric_labels[metric_key],
                "categories": [worksheet.get_name(), first_row, 1, last_row, 1],
                "values": [
                    worksheet.get_name(),
                    first_row,
                    statistic_column,
                    last_row,
                    statistic_column,
                ],
                "fill": {"color": "#C56A3A"},
                "border": {"none": True},
                "data_labels": {"value": True},
            }
        )
        chart.set_title(
            {"name": f"{metric_labels[metric_key]} · {sheet.statistic.upper()}"}
        )
        chart.set_legend({"none": True})
        chart.set_chartarea(
            {"border": {"none": True}, "fill": {"color": "#FFFDF8"}}
        )
        chart.set_plotarea(
            {"border": {"color": "#DED8CC"}, "fill": {"color": "#FFFDF8"}}
        )
        chart.set_x_axis(
            {
                "major_gridlines": {
                    "visible": True,
                    "line": {"color": "#E8E2D7"},
                }
            }
        )
        chart.set_y_axis({"reverse": True})
        chart.set_style(10)
        chart.set_size({"width": 420, "height": 250})
        worksheet.insert_chart(
            position[0],
            position[1],
            chart,
            {"x_offset": 4, "y_offset": 4},
        )


def _excel_string_chunks(value: str) -> list[str]:
    # 16,000 Python code points also fit when every character needs a UTF-16
    # surrogate pair within Excel's 32,767-character cell limit.
    cell_limit = 16_000
    return [
        value[index : index + cell_limit]
        for index in range(0, len(value), cell_limit)
    ] or [""]


def _summary_rows(
    sheet: SummaryWorksheet,
    messages: Mapping[str, str],
) -> tuple[list[tuple[Any, ...]], dict[str, tuple[int, int]]]:
    rows: list[tuple[Any, ...]] = []
    ranges: dict[str, tuple[int, int]] = {}
    if sheet.matched_count < 1:
        return rows, ranges
    for metric_key, metric_type, fallback, message_key in SUMMARY_METRICS:
        first = len(rows)
        for group in sheet.groups:
            metric = next(
                (
                    item
                    for item in group.get("metrics", ())
                    if item.get("key") == metric_key
                ),
                {},
            )
            distribution = metric.get("distribution") or {}
            rows.append(
                (
                    _metric_label(metric_key, fallback, message_key, messages),
                    (
                        messages.get("summary_overall", "Overall")
                        if group.get("key") == "overall"
                        else str(group.get("label") or group.get("key") or "-")
                    ),
                    int(metric.get("count") or 0),
                    metric.get("mean"),
                    distribution.get("min"),
                    distribution.get("q1"),
                    distribution.get("p50"),
                    distribution.get("q3"),
                    distribution.get("p95"),
                    distribution.get("max"),
                    metric.get("type") or metric_type,
                )
            )
        ranges[metric_key] = (first, len(rows) - 1)
    return rows, ranges


def _metric_label(
    _key: str,
    fallback: str,
    message_key: str,
    messages: Mapping[str, str],
) -> str:
    return messages.get(message_key, fallback)


def _write_statistic_cell(
    worksheet: Any,
    row: int,
    column: int,
    value: Any,
    metric_type: str,
    formats: Mapping[str, Any],
) -> None:
    if value is None:
        worksheet.write_blank(
            row,
            column,
            None,
            formats.get(metric_type, formats["number"]),
        )
        return
    number = float(value)
    if metric_type == "duration":
        number /= 86_400_000
    worksheet.write_number(
        row,
        column,
        number,
        formats.get(metric_type, formats["number"]),
    )


def _workbook_formats(workbook: xlsxwriter.Workbook) -> dict[str, Any]:
    return {
        "title": workbook.add_format(
            {
                "bold": True,
                "font_size": 18,
                "font_color": "#322B20",
                "bottom": 2,
                "bottom_color": "#C56A3A",
            }
        ),
        "meta_label": workbook.add_format(
            {"bold": True, "font_color": "#766D60", "valign": "top"}
        ),
        "meta_value": workbook.add_format(
            {"font_color": "#322B20", "text_wrap": True, "valign": "top"}
        ),
        "table_header": workbook.add_format(
            {"bold": True, "font_color": "#FFFFFF", "bg_color": "#70543E", "border": 0}
        ),
        "text": workbook.add_format({"font_color": "#322B20"}),
        "integer": workbook.add_format(
            {"num_format": "#,##0", "font_color": "#322B20"}
        ),
        "number": workbook.add_format(
            {"num_format": "#,##0.00", "font_color": "#322B20"}
        ),
        "duration": workbook.add_format(
            {"num_format": "[h]:mm:ss.000", "font_color": "#322B20"}
        ),
        "percent": workbook.add_format(
            {"num_format": "0.00%", "font_color": "#322B20"}
        ),
        "empty": workbook.add_format(
            {"italic": True, "font_color": "#766D60", "align": "center"}
        ),
    }
