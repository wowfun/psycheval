"""Verify paired primary totals and publish static HTML and source facts."""

import argparse
import csv
import io
import json
import re
import unicodedata
from decimal import Decimal
from pathlib import Path

from psycheval.harbor.documents import (
    DocumentLimits,
    DocumentParseError,
    inspect_document,
    select_document,
)
from psycheval.harbor.evidence import EvidenceLimitError, EvidenceWriter, SourceSnapshot

METRICS = (
    "attendance_visits",
    "open_days",
    "open_hours",
    "online_reserved_orders",
    "online_checkedin_visits",
    "night_checkedin_visits",
    "response_count",
    "crowded_responses",
)


def normal(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).lower()


def metric(text):
    text = normal(text)
    for field in METRICS:
        if text == field:
            return field
    if any(
        word in text
        for word in (
            "日均",
            "平均",
            "每",
            "增长",
            "下降",
            "同比",
            "环比",
            "占",
            "比例",
            "率",
            "增量",
            "贡献",
            "÷",
            "/",
        )
    ):
        return None
    if re.search(r"(?:选择|认为|感到|回答).*拥挤|拥挤.*(?:人数|人次|\(人\))", text):
        return "crowded_responses"
    if any(
        word in text
        for word in ("答卷数", "问卷数", "答卷人数", "有效答卷", "有效问卷", "回收问卷")
    ):
        return "response_count"
    if "夜场" in text and any(
        word in text for word in ("到馆", "入馆", "人次", "核销")
    ):
        return "night_checkedin_visits"
    if any(word in text for word in ("夜场", "现场", "线下")):
        return None
    if any(word in text for word in ("线上", "在线")):
        if any(word in text for word in ("核销", "到馆", "入馆")):
            return "online_checkedin_visits"
        if any(word in text for word in ("预约", "发出")):
            return "online_reserved_orders"
    if "开放" in text:
        if any(word in text for word in ("小时", "时长")):
            return "open_hours"
        if any(word in text for word in ("天", "日")):
            return "open_days"
    if any(word in text for word in ("到馆", "入馆", "参观", "客流")):
        return "attendance_visits"
    return None


def first_quarter_scope(text):
    text = normal(text)
    if any(
        word in text
        for word in (
            "q2",
            "q3",
            "q4",
            "二季度",
            "三季度",
            "四季度",
            "2季度",
            "3季度",
            "4季度",
            "全年",
            "年度合计",
        )
    ):
        return False
    if any(
        word in text for word in ("q1", "一季度", "第一季度", "1季度", "1-3月", "1—3月")
    ):
        return True
    return None


def table_first_quarter(report, table):
    by_id = {node.id: node for node in report.nodes}

    def ancestors(node_id):
        result = []
        parent = by_id[node_id].parent_id
        while parent is not None:
            result.append(parent)
            parent = by_id[parent].parent_id
        return result

    table_ancestors = set(ancestors(table.node_id))
    captions = [
        report.text_content(node.id)
        for node in report.nodes
        if node.parent_id == table.node_id and node.tag.rsplit("}", 1)[-1] == "caption"
    ]
    if captions:
        scope = first_quarter_scope(" ".join(captions))
        if scope is not None:
            return scope
    active = []
    for heading in report.headings:
        if heading.node_id >= table.node_id:
            break
        enclosing_section = next(
            (
                identity
                for identity in ancestors(heading.node_id)
                if by_id[identity].tag.rsplit("}", 1)[-1] in {"section", "article"}
            ),
            None,
        )
        if enclosing_section is not None and enclosing_section not in table_ancestors:
            continue
        while active and active[-1].level >= heading.level:
            active.pop()
        active.append(heading)
    for heading in reversed(active):
        scope = first_quarter_scope(heading.text)
        if scope is not None:
            return scope
    return False


def quarter(text, *, allow_year=False):
    text = normal(text)
    scope = first_quarter_scope(text)
    if scope is False:
        return None
    matched = re.fullmatch(
        r"(2025|2026)(?:年|-)?(?:q1|第一季度|一季度|1季度|1[-—~～]3月)"
        r"(?:合计|总计)?(?:\([^)]{0,40}\))?(?:合计|总计)?",
        text,
    )
    if matched:
        return matched[1]
    if allow_year and (matched := re.fullmatch(r"(2025|2026)年?", text)):
        return matched[1]
    return None


def number(text):
    text = unicodedata.normalize("NFKC", text).strip()
    matched = re.match(r"^(?:约\s*)?([+-]?[\d,，\s]+(?:\.\d+)?)\s*([万千]?)", text)
    if not matched:
        return None
    if text[matched.end() :].lstrip().startswith("%"):
        return None
    try:
        result = Decimal(re.sub(r"[,，\s]", "", matched[1]))
    except ArithmeticError:
        return None
    return result * {"": 1, "万": 10000, "千": 1000}[matched[2]]


def reference(sources):
    expected = {}
    for year in ("2025", "2026"):
        rows = list(csv.DictReader(io.StringIO(sources[f"stats_{year}"])))
        if [row["month"] for row in rows] != [
            f"{year}-{month:02}" for month in (1, 2, 3)
        ]:
            raise ValueError("Malformed retained monthly primary statistics")
        expected[year] = {
            field: sum(int(row[field]) for row in rows)
            for field in METRICS
            if field not in {"response_count", "crowded_responses"}
        }
        for row in rows:
            if int(row["online_checkedin_visits"]) + int(
                row["onsite_checkedin_visits"]
            ) != int(row["attendance_visits"]):
                raise ValueError("Retained channel counts do not reconcile")
    survey = list(csv.DictReader(io.StringIO(sources["survey"])))
    if {row["quarter"] for row in survey} != {"2025Q1", "2026Q1"} or len(survey) != 2:
        raise ValueError("Malformed retained primary survey")
    for row in survey:
        expected[row["quarter"][:4]].update(
            {
                field: int(row[field])
                for field in ("response_count", "crowded_responses")
            }
        )
    previous, current = expected["2025"], expected["2026"]
    daily = {
        year: values["attendance_visits"] / values["open_days"]
        for year, values in expected.items()
    }
    hourly = {
        year: values["attendance_visits"] / values["open_hours"]
        for year, values in expected.items()
    }
    calculations = {
        "raw_quarter_totals": expected,
        "attendance_growth_percent": 100
        * (current["attendance_visits"] / previous["attendance_visits"] - 1),
        "visits_per_open_day": daily,
        "daily_flow_change_percent": 100 * (daily["2026"] / daily["2025"] - 1),
        "visits_per_open_hour": hourly,
        "hourly_flow_change_percent": 100 * (hourly["2026"] / hourly["2025"] - 1),
        "checkedin_online_share_percent": {
            year: 100 * values["online_checkedin_visits"] / values["attendance_visits"]
            for year, values in expected.items()
        },
        "crowded_among_respondents_percent": {
            year: 100 * values["crowded_responses"] / values["response_count"]
            for year, values in expected.items()
        },
        "night_entries_divided_by_total_increment_percent_not_causal": 100
        * current["night_checkedin_visits"]
        / (current["attendance_visits"] - previous["attendance_visits"]),
    }
    return expected, calculations


def table_grid(table):
    rows = {}
    for cell in table.cells:
        rows.setdefault(cell.row_id, []).append(cell)
    if len(rows) > 200:
        return []
    occupied = {}
    for row, cells in enumerate(rows.values()):
        column = 0
        for cell in cells:
            while (row, column) in occupied:
                column += 1
            height, width = cell.row_span or 1, cell.column_span or 1
            if not 1 <= height <= 200 or not 1 <= width <= 50 or column + width > 50:
                return []
            for vertical in range(height):
                for horizontal in range(width):
                    occupied[row + vertical, column + horizontal] = cell.text
            column += width
    return [
        [occupied.get((row, column), "") for column in range(50)]
        for row in range(len(rows))
    ]


def assess(report, expected):
    observed, conflicts = {}, []

    def record(field, year, value, table_id, row_index):
        if field is None or year is None:
            return
        observed.setdefault(field, set()).add(year)
        if number(value) != expected[year][field]:
            conflicts.append(
                {
                    "field": field,
                    "year": year,
                    "value": value,
                    "table_node": table_id,
                    "row_index": row_index,
                }
            )

    def column(header, labels):
        return next(
            (index for index, text in enumerate(header) if normal(text) in labels), None
        )

    for table in report.tables:
        grid = table_grid(table)
        if not grid:
            continue
        allow_year = table_first_quarter(report, table)
        header = grid[0]
        periods = {
            index: year
            for index, text in enumerate(header)
            if (year := quarter(text, allow_year=allow_year))
        }
        metric_column = column(header, {"指标", "项目", "统计指标"})
        if periods:
            metric_column = 0 if metric_column is None else metric_column
            for row_index, row in enumerate(grid[1:], 1):
                field = metric(row[metric_column])
                for index, year in periods.items():
                    record(field, year, row[index], table.node_id, row_index)
            continue
        period_column = column(header, {"时期", "季度", "统计期", "期间"})
        value_column = column(header, {"数值", "数量", "值"})
        if (
            metric_column is not None
            and period_column is not None
            and value_column is not None
        ):
            for row_index, row in enumerate(grid[1:], 1):
                record(
                    metric(row[metric_column]),
                    quarter(row[period_column], allow_year=allow_year),
                    row[value_column],
                    table.node_id,
                    row_index,
                )
            continue
        fields = {
            index: field for index, text in enumerate(header) if (field := metric(text))
        }
        if fields:
            period_column = 0 if period_column is None else period_column
            for row_index, row in enumerate(grid[1:], 1):
                year = quarter(row[period_column], allow_year=allow_year)
                for index, field in fields.items():
                    record(field, year, row[index], table.node_id, row_index)
    matched = {field for field, years in observed.items() if years == {"2025", "2026"}}
    missing = sorted(set(METRICS) - matched)
    return (
        not missing and not conflicts,
        f"Matched primary comparison fields={sorted(matched)}; missing={missing}; conflicting={sorted({item['field'] for item in conflicts})}; first_mismatches={conflicts[:5]}",
    )


def report_evidence(report):
    facts = [
        "Static HTML extraction only; no browser layout, computed visibility or responsiveness is established.",
        report.to_markdown(),
        "## Authored table cell associations",
    ]
    for table in report.tables:
        for cell in table.cells:
            facts.append(
                f"Table node {table.node_id}, row node {cell.row_id}, cell node {cell.node_id}, spans {cell.row_span}x{cell.column_span}: {cell.text}"
            )
    return "\n\n".join(facts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    if not paths.get("inputs"):
        raise RuntimeError(
            "This task requires ordinary Native Host retained initial inputs"
        )
    passed, reason = False, "No single final HTML report"
    with EvidenceWriter(paths["verifier_logs"]) as evidence:
        texts = {}
        for identity, filename in (
            ("stats_2025", "2025-q1-statistics.csv"),
            ("stats_2026", "2026-q1-statistics.csv"),
            ("survey", "survey-results.csv"),
            ("notices", "institution-notices.md"),
            ("draft", "campaign-draft.md"),
        ):
            source = evidence.capture(identity, Path(paths["inputs"]) / filename)
            text = (
                inspect_document(source).text
                if filename.endswith(".md")
                else source.content.decode("utf-8-sig")
            )
            texts[identity] = text
            evidence.add_text(
                identity + "_text",
                f"Source: {identity} / {filename}; line numbers below are 1-based.\n\n"
                + "\n".join(
                    f"L{index}: {line}"
                    for index, line in enumerate(text.splitlines(), 1)
                ),
                source_id=identity,
            )
        expected, calculations = reference(texts)
        evidence.add_text(
            "calculation_reference",
            "Task reference computed from retained primary CSV snapshots; not evidence that the Agent performed analysis.\n\n"
            + json.dumps(calculations, ensure_ascii=False, indent=2),
        )
        selected = select_document([Path(paths["workdir"]) / "output"], format="html")
        if selected.selected is None or len(selected.candidates) != 1:
            evidence.add_text(
                "report_text", "No single final HTML report: " + selected.reason
            )
        else:
            try:
                source = SourceSnapshot.read(
                    selected.selected, max_bytes=4 * 1024 * 1024
                )
            except EvidenceLimitError as error:
                reason = str(error)
                evidence.add_text("report_text", "Unassessable report: " + reason)
            else:
                evidence.capture("report_html", source)
                try:
                    report = inspect_document(
                        source,
                        limits=DocumentLimits(
                            source_bytes=4 * 1024 * 1024, text_bytes=2 * 1024 * 1024
                        ),
                    )
                except DocumentParseError as error:
                    reason = str(error)
                    evidence.add_text(
                        "report_text",
                        "Unassessable report: " + reason,
                        source_id="report_html",
                    )
                else:
                    passed, reason = assess(report, expected)
                    evidence.add_text(
                        "report_text", report_evidence(report), source_id="report_html"
                    )
    args.output.write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "id": "verified_comparison_data",
                        "passed": passed,
                        "evidence": reason,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
