"""Bind key table facts; Judge assesses the complete faithful editing task."""

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from psycheval.harbor.documents import (
    DocumentLimits,
    DocumentParseError,
    inspect_document,
    select_document,
)
from psycheval.harbor.evidence import EvidenceLimitError, EvidenceWriter, SourceSnapshot

LIMITS = DocumentLimits(
    source_bytes=2 * 1024 * 1024, text_bytes=2 * 1024 * 1024, facts=30000
)
CATEGORIES = {
    "paper": ["纸本纪念物", "纸质纪念物", "纸本类", "纸本"],
    "wood": ["木作标牌", "木制标牌", "木质标牌", "木作类", "木作"],
    "textile": ["织物纪念品", "纺织纪念品", "织物类", "织物"],
}
TOTAL = ["合计", "总计", "总额", "总数"]
SPECS = {
    "capacity": {
        "columns": {
            "label": ["类别", "品类", "类型", "项目"],
            "days": ["工作日", "参考排期", "常规排期", "排期参考"],
            "limit": [
                "接收上限",
                "单轮容量",
                "每轮上限",
                "单轮上限",
                "单轮接收",
                "接收容量",
            ],
        },
        "labels": CATEGORIES,
        "rows": {
            "paper": {"days": 12, "limit": 20},
            "wood": {"days": 18, "limit": 8},
            "textile": {"days": 15, "limit": 10},
        },
    },
    "registered": {
        "columns": {
            "label": ["类别", "品类", "类型", "项目"],
            "registered": [
                "本轮登记",
                "登记数量",
                "登记件数",
                "登记量",
                "登记",
                "收件数量",
            ],
            "scheduled": [
                "进入排期",
                "已排期",
                "排期件数",
                "本轮排期",
                "排期数量",
                "排期(件)",
            ],
            "pending": ["待确认", "待定"],
        },
        "labels": {**CATEGORIES, "total": TOTAL},
        "rows": {
            "paper": {"registered": 24, "scheduled": 20, "pending": 4},
            "wood": {"registered": 11, "scheduled": 8, "pending": 3},
            "textile": {"registered": 9, "scheduled": 9, "pending": 0},
            "total": {"registered": 44, "scheduled": 37, "pending": 7},
        },
    },
    "budget": {
        "columns": {
            "label": ["用途", "科目", "费用项目", "预算项目", "支持事项", "项目"],
            "amount": ["预算", "金额", "额度"],
        },
        "labels": {
            "intake": ["入库建档", "建档入库", "接收建档", "入库登记"],
            "packaging": ["交接包装", "包装交接", "交接与包装", "包装"],
            "meeting": ["公众说明会", "公开说明会", "说明会"],
            "reserve": ["预备金", "备用金"],
            "total": TOTAL,
        },
        "rows": {
            "intake": {"amount": 680},
            "packaging": {"amount": 940},
            "meeting": {"amount": 360},
            "reserve": {"amount": 420},
            "total": {"amount": 2400},
        },
    },
}


def normalized(text):
    return re.sub(r"[\s`*_]+", "", unicodedata.normalize("NFKC", text)).casefold()


def number(text, header):
    value = normalized(text)
    numbers = re.findall(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", value)
    if len(numbers) != 1:
        return None
    try:
        result = Decimal(numbers[0].replace(",", ""))
    except InvalidOperation:
        return None
    unit = value if "元" in value else normalized(header)
    if "万元" in unit:
        result *= 10000
    elif "千元" in unit:
        result *= 1000
    return result


def table_rows(report):
    tables = []
    for block in report.blocks:
        if block.table is None:
            continue
        rows = defaultdict(dict)
        for cell in block.table.cells:
            if (
                cell.row_span != 1
                or cell.column_span != 1
                or any(not hasattr(part, "text") for part in cell.blocks)
            ):
                break
            rows[cell.row][cell.column] = "\n".join(
                part.text for part in cell.blocks
            ).strip()
        else:
            tables.append(
                (block.start_line + 1, [cells for _, cells in sorted(rows.items())])
            )
    return tables


def column_map(headers, aliases):
    result = {}
    for key, alternatives in aliases.items():
        selected = None
        for alias in alternatives:
            matches = [
                column
                for column, value in headers.items()
                if column not in result.values()
                and normalized(alias) in normalized(value)
            ]
            if len(matches) == 1:
                selected = matches[0]
                break
        if selected is None:
            return None
        result[key] = selected
    return result if len(set(result.values())) == len(result) else None


def validate_table(rows, columns, spec):
    seen, problems = set(), []
    for row in rows[1:]:
        label = row.get(columns["label"], "")
        matches = [
            key
            for key, aliases in spec["labels"].items()
            if any(normalized(alias) in normalized(label) for alias in aliases)
        ]
        if len(matches) != 1:
            # An added arithmetic total is not a new object category.
            if (
                not matches
                and "total" not in spec["rows"]
                and any(normalized(alias) in normalized(label) for alias in TOTAL)
            ):
                continue
            if any(
                number(row.get(column, ""), rows[0].get(column, "")) is not None
                for key, column in columns.items()
                if key != "label"
            ):
                problems.append(f"Unknown or combined numeric row: {label}")
            continue
        key = matches[0]
        if key in seen:
            problems.append(f"Repeated row: {label}")
        seen.add(key)
        for field, expected in spec["rows"][key].items():
            column = columns[field]
            if number(row.get(column, ""), rows[0][column]) != Decimal(expected):
                problems.append(f"Wrong {field} for {label}: {row.get(column, '')}")
    if seen != set(spec["rows"]):
        problems.append(f"Missing rows: {sorted(set(spec['rows']) - seen)}")
    return problems


def evaluate_report(report):
    tables, diagnostics = table_rows(report), {}
    for name, spec in SPECS.items():
        candidates = [
            (line, rows, columns)
            for line, rows in tables
            if rows and (columns := column_map(rows[0], spec["columns"])) is not None
        ]
        if not candidates:
            diagnostics[name] = [
                "No table with distinguishable required column meanings"
            ]
            continue
        issues = []
        for line, rows, columns in candidates:
            issues.extend(
                f"L{line}: {issue}" for issue in validate_table(rows, columns, spec)
            )
        diagnostics[name] = issues
    return all(not issues for issues in diagnostics.values()), diagnostics


def evaluate(paths):
    if not paths.get("inputs"):
        raise RuntimeError("This Task requires retained ordinary Native Host inputs")
    manuscript = SourceSnapshot.read(
        Path(paths["inputs"]) / "workshop-manuscript.txt", max_bytes=1024 * 1024
    )
    source_report = inspect_document(manuscript, format="md", limits=LIMITS)
    selection = select_document([Path(paths["workdir"]) / "output"], format="md")
    passed, detail = False, {"selection": selection.reason}
    with EvidenceWriter(paths["verifier_logs"]) as evidence:
        evidence.capture("source_manuscript", manuscript)
        excerpt = (
            "Source: initial workshop-manuscript.txt, complete lines below.\n\n"
            + "\n".join(
                f"L{number}: {line}"
                for number, line in enumerate(source_report.text.splitlines(), 1)
            )
        )
        evidence.add_text("manuscript", excerpt, source_id="source_manuscript")
        if selection.selected is None:
            evidence.unavailable("handbook", selection.reason)
        else:
            try:
                output = SourceSnapshot.read(
                    selection.selected, max_bytes=LIMITS.source_bytes
                )
            except (EvidenceLimitError, FileNotFoundError) as error:
                detail["reason"] = str(error)
                evidence.unavailable("handbook", str(error))
            else:
                evidence.capture("handbook_file", output)
                try:
                    report = inspect_document(output, format="md", limits=LIMITS)
                except DocumentParseError as error:
                    detail["reason"] = str(error)
                    evidence.unavailable("handbook", str(error))
                else:
                    if report.text.strip():
                        passed, detail["table_bindings"] = evaluate_report(report)
                        evidence.add_text(
                            "handbook", report.to_markdown(), source_id="handbook_file"
                        )
                    else:
                        evidence.unavailable("handbook", "Selected handbook is blank")
    return [
        {
            "id": "key_table_bindings",
            "passed": passed,
            "evidence": json.dumps(detail, ensure_ascii=False),
        }
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    args.output.write_text(
        json.dumps({"checks": evaluate(paths)}, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
