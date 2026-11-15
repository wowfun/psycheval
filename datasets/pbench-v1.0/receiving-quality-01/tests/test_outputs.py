"""Reconcile trusted input snapshots and inspect the submitted workbook facts."""

import argparse
import csv
import io
import json
import math
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from harbor.models.trajectories import Trajectory

from psycheval.harbor.documents import (
    DocumentParseError,
    inspect_document,
    select_document,
)
from psycheval.harbor.evidence import EvidenceWriter, SourceSnapshot
from psycheval.harbor.verifier import final_answer_text

DETAIL = ("到货单号", "修订号", "供应商", "SKU", "采用箱规", "验收件数", "不合格件数")
SUMMARY = ("供应商", "验收件数", "不合格件数", "不合格率")


def read_csv(content):
    return list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))


def reference(products, receipts):
    sizes = {row["SKU"]: int(row["默认箱规"]) for row in read_csv(products)}
    latest = {}
    seen = set()
    for row in read_csv(receipts):
        identity, revision = row["到货单号"], int(row["修订号"])
        if (identity, revision) in seen:
            raise ValueError("Input contains duplicate receipt revisions")
        seen.add((identity, revision))
        if identity not in latest or revision > int(latest[identity]["修订号"]):
            latest[identity] = row
    detail, summary = {}, {}
    for identity, row in latest.items():
        if row["状态"] != "已验收":
            continue
        size = int(row["箱规"]) if row["箱规"].strip() else sizes[row["SKU"]]
        total, defective = int(row["箱数"]) * size, int(row["不合格件数"])
        if size <= 0 or not 0 <= defective <= total:
            raise ValueError("Invalid retained input quantities")
        detail[identity] = dict(
            zip(
                DETAIL,
                (
                    identity,
                    int(row["修订号"]),
                    row["供应商"],
                    row["SKU"],
                    size,
                    total,
                    defective,
                ),
            )
        )
        totals = summary.setdefault(
            row["供应商"], {"供应商": row["供应商"], "验收件数": 0, "不合格件数": 0}
        )
        totals["验收件数"] += total
        totals["不合格件数"] += defective
    for totals in summary.values():
        totals["不合格率"] = totals["不合格件数"] / totals["验收件数"]
    return detail, summary


def label(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value)))


def table(report, columns):
    candidates = []
    for sheet in report.sheets:
        grid = defaultdict(dict)
        for cell in sheet.cells:
            address = re.fullmatch(r"([A-Z]+)(\d+)", cell.address)
            grid[int(address[2])][address[1]] = (
                cell.cached_value if cell.formula is not None else cell.value
            )
        for number, values in sorted(grid.items()):
            headers = {
                name: [
                    column
                    for column, value in values.items()
                    if label(value) == name
                    or (
                        name == "不合格率"
                        and label(value) in {"不合格率(%)", "不合格率%"}
                    )
                ]
                for name in columns
            }
            if not all(len(matches) == 1 for matches in headers.values()):
                continue
            mapping = {name: matches[0] for name, matches in headers.items()}
            data = []
            for row_number, row in sorted(grid.items()):
                if row_number <= number:
                    continue
                record = {name: row.get(column) for name, column in mapping.items()}
                identity = record[columns[0]]
                if identity is None:
                    continue
                is_total = bool(
                    re.fullmatch(r"(?:合计|总计)(?:\([^()]*\))?", label(identity))
                )
                if is_total:
                    if columns == SUMMARY:
                        record["is_total"] = True
                    else:
                        continue
                if str(identity).startswith(("注:", "注：", "说明")) and all(
                    record[name] is None for name in columns[1:]
                ):
                    continue
                if "不合格率" in columns:
                    record["rate_in_percent"] = "%" in label(
                        values[mapping["不合格率"]]
                    )
                    record["rate_address"] = f"{mapping['不合格率']}{row_number}"
                data.append(record)
            candidates.append((sheet.name, data))
    return candidates[0] if len(candidates) == 1 else None


def numeric(value):
    return type(value) in (int, float) and math.isfinite(value)


def rate(value, percent=False, number_format="General"):
    if isinstance(value, str) and value.strip().endswith(("%", "％")):
        try:
            return float(value.strip()[:-1]) / 100
        except ValueError:
            return None
    if numeric(value):
        scaling = re.sub(r'"[^"]*"|\\.', "", number_format)
        if "%" in scaling:
            return value
        if percent or "%" in number_format:
            return value / 100
    return None


def grade_tables(report, expected_detail, expected_summary):
    detail_table, summary_table = table(report, DETAIL), table(report, SUMMARY)
    details = detail_table[1] if detail_table else None
    summaries = summary_table[1] if summary_table else None
    formats = {}
    if summary_table:
        # The shared report owns values/formulas. This Task additionally needs
        # Excel's percent display scale, which XlsxReport does not expose.
        from openpyxl import load_workbook

        book = load_workbook(io.BytesIO(report.source.content), read_only=True)
        try:
            sheet = book[summary_table[0]]
            formats = {
                row["rate_address"]: sheet[row["rate_address"]].number_format
                for row in summaries
            }
        finally:
            book.close()
    reasons = []

    def compare(records, expected, columns):
        if records is None:
            reasons.append(f"No unique table with headers {columns}")
            return False
        if columns == SUMMARY and any(row.get("is_total") for row in records):
            total = {
                key: sum(row[key] for row in expected.values())
                for key in ("验收件数", "不合格件数")
            }
            total["不合格率"] = total["不合格件数"] / total["验收件数"]
            expected = {**expected, "__TOTAL__": total}
        identities = [
            "__TOTAL__" if row.get("is_total") else str(row[columns[0]]).strip()
            for row in records
        ]
        if len(identities) != len(set(identities)) or set(identities) != set(expected):
            reasons.append(f"Unexpected/missing/duplicate rows: observed={identities}")
            return False
        passed = True
        for identity, row in zip(identities, records, strict=True):
            for key in columns[1:]:
                actual, target = row[key], expected[identity][key]
                if key == "不合格率":
                    actual = rate(
                        actual,
                        row.get("rate_in_percent", False),
                        formats.get(row["rate_address"], "General"),
                    )
                    equal = (
                        actual is not None and abs(actual - target) <= 0.00005 + 1e-12
                    )
                elif isinstance(target, str):
                    equal = isinstance(actual, str) and actual.strip() == target
                else:
                    equal = numeric(actual) and actual == target
                if not equal:
                    reasons.append(
                        f"{identity} {key}: observed={actual!r}, required={target!r}"
                    )
                    passed = False
        return passed

    detail_ok = compare(details, expected_detail, DETAIL)
    summary_ok = compare(summaries, expected_summary, SUMMARY)
    if detail_table and summary_table and detail_table[0] == summary_table[0]:
        reasons.append("Detail and supplier summary must be on separate worksheets")
        detail_ok = summary_ok = False
    return (
        detail_ok,
        summary_ok,
        reasons
        or ["Compared exact effective receipt set and supplier-bound quantities/rates"],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    if not paths.get("inputs"):
        raise RuntimeError("This Task requires ordinary Native Host retained inputs")
    checks = {"effective_receipts": False, "supplier_aggregation": False}
    reasons = ["No unambiguous final workbook"]
    with EvidenceWriter(paths["verifier_logs"]) as evidence:
        sources = {}
        for name in ("products", "receipts"):
            source = evidence.capture(name, Path(paths["inputs"]) / f"{name}.csv")
            sources[name] = source.content
            excerpt = f"## Initial {name}.csv\n" + "\n".join(
                f"L{index}: {line}"
                for index, line in enumerate(
                    source.content.decode("utf-8-sig").splitlines(), 1
                )
            )
            evidence.add_text(f"{name}_excerpt", excerpt, source_id=name)
        expected_detail, expected_summary = reference(
            sources["products"], sources["receipts"]
        )
        selection = select_document([Path(paths["workdir"]) / "output"], format="xlsx")
        if selection.selected is not None and len(selection.candidates) == 1:
            snapshot = evidence.capture("workbook_xlsx", selection.selected)
            try:
                report = inspect_document(snapshot)
            except DocumentParseError as error:
                reasons = [str(error)]
                evidence.add_text(
                    "workbook",
                    "No assessable workbook: " + str(error),
                    source_id="workbook_xlsx",
                )
            else:
                detail_ok, summary_ok, reasons = grade_tables(
                    report, expected_detail, expected_summary
                )
                checks.update(
                    effective_receipts=detail_ok, supplier_aggregation=summary_ok
                )
                evidence.add_text(
                    "workbook", report.to_markdown(), source_id="workbook_xlsx"
                )
        else:
            evidence.add_text(
                "workbook", "No single final workbook: " + selection.reason
            )
        trajectory = Path(paths["agent_logs"]) / "trajectory.json"
        try:
            snapshot = SourceSnapshot.read(trajectory, max_bytes=128 * 1024 * 1024)
        except FileNotFoundError:
            answer = ""
        else:
            answer = final_answer_text(Trajectory.model_validate_json(snapshot.content))
        evidence.add_text("final_answer", answer)
    args.output.write_text(
        json.dumps(
            {
                "checks": [
                    {"id": key, "passed": value, "evidence": "; ".join(reasons)}
                    for key, value in checks.items()
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
