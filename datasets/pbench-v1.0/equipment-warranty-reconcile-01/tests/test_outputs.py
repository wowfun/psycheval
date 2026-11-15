"""Equipment-ledger reconciliation over the initial immutable XLSX inputs."""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from harbor.models.trajectories import Trajectory

from psycheval.harbor.documents import (
    DocumentParseError,
    inspect_document,
    select_document,
)
from psycheval.harbor.evidence import EvidenceWriter, SourceSnapshot
from psycheval.harbor.verifier import final_answer_text

BASE_FIELDS = ("asset_no", "model", "commissioned_at", "service_site")
FIELDS = (*BASE_FIELDS, "extended_service")
WINDOW = (datetime(2026, 4, 6, 6), datetime(2026, 4, 14, 21, 59, 59))


class InvalidTable(ValueError):
    """A submitted table does not satisfy the public import contract."""


def records(report, *, extended):
    sheet = next(
        (sheet for sheet in report.sheets if sheet.name == "service_assets"), None
    )
    if sheet is None:
        raise InvalidTable("Missing service_assets worksheet")
    fields = FIELDS if extended else BASE_FIELDS
    grid = {}
    for cell in sheet.cells:
        if cell.value is None and cell.formula is None:
            continue
        address = re.fullmatch(r"([A-Z]+)([1-9]\d*)", cell.address)
        row, column = int(address[2]), address[1]
        if cell.formula is not None:
            raise InvalidTable(f"Formula in required import table: {cell.address}")
        grid.setdefault(row, {})[column] = cell.value
    headers = grid.pop(1, {})
    if len(headers) != len(fields) or set(headers.values()) != set(fields):
        raise InvalidTable("Required header set differs")
    columns = {name: column for column, name in headers.items()}
    expected_types = {
        "asset_no": str,
        "model": str,
        "commissioned_at": datetime,
        "service_site": str,
        "extended_service": bool,
    }
    result = {}
    for number, cells in sorted(grid.items()):
        if set(cells) != set(headers):
            raise InvalidTable(f"Incomplete or extra import fields at row {number}")
        row = {name: cells[column] for name, column in columns.items()}
        for name, value in row.items():
            if type(value) is not expected_types[name]:
                raise InvalidTable(
                    f"Row {number}: {name} must be {expected_types[name].__name__}"
                )
            if name == "commissioned_at" and value.tzinfo is not None:
                raise InvalidTable("Excel date-time must be timezone-naive")
            if isinstance(value, str) and not value.strip():
                raise InvalidTable(f"Row {number}: empty {name}")
        identity = row["asset_no"]
        if identity in result:
            raise InvalidTable(f"Duplicate asset_no: {identity}")
        result[identity] = row
    return result


def reference(source, current):
    source_rows, current_rows = (
        records(source, extended=False),
        records(current, extended=True),
    )
    missing = {
        identity: {
            **row,
            "extended_service": WINDOW[0] <= row["commissioned_at"] <= WINDOW[1],
        }
        for identity, row in source_rows.items()
        if identity not in current_rows
    }
    expected = {**current_rows, **missing}
    summary = {
        "initial_commissioning_rows": len(source_rows),
        "initial_service_rows": len(current_rows),
        "restored_count": len(missing),
        "restored_extended_count": sum(
            row["extended_service"] for row in missing.values()
        ),
        "final_asset_count": len(expected),
        "final_extended_count": sum(
            row["extended_service"] for row in expected.values()
        ),
        "restored_asset_numbers": sorted(missing),
        "window_inclusive": [value.isoformat(sep=" ") for value in WINDOW],
    }
    return current_rows, missing, summary


def assess(report, current, missing):
    try:
        actual = records(report, extended=True)
    except InvalidTable as error:
        return {
            "existing_preserved": (False, str(error)),
            "omitted_restored": (False, str(error)),
        }
    unexpected = sorted(set(actual) - set(current) - set(missing))
    if unexpected:
        reason = f"Unexpected equipment rows: {unexpected}"
        return {
            "existing_preserved": (False, reason),
            "omitted_restored": (False, reason),
        }
    results = {}
    for name, expected in (
        ("existing_preserved", current),
        ("omitted_restored", missing),
    ):
        mismatched = [
            identity
            for identity, row in expected.items()
            if actual.get(identity) != row
        ]
        results[name] = (
            not mismatched,
            f"Matched {len(expected) - len(mismatched)}/{len(expected)} required equipment records; mismatches={mismatched}",
        )
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    if not paths.get("inputs"):
        raise RuntimeError(
            "This Task requires ordinary Native Host retained initial inputs"
        )
    results = {
        name: (False, "No single final workbook")
        for name in ("existing_preserved", "omitted_restored")
    }
    with EvidenceWriter(paths["verifier_logs"]) as evidence:
        reports = []
        for artifact_id, filename in (
            ("commissioning_xlsx", "commissioning-register.xlsx"),
            ("service_xlsx", "service-register.xlsx"),
        ):
            source = evidence.capture(artifact_id, Path(paths["inputs"]) / filename)
            report = inspect_document(source)
            reports.append(report)
            evidence.add_text(
                artifact_id + "_text", report.to_markdown(), source_id=artifact_id
            )
        current, missing, summary = reference(*reports)
        evidence.add_text(
            "reconciliation_reference",
            "Verifier reference derived from the retained commissioning_xlsx and service_xlsx initial inputs, not an Agent achievement.\n\n"
            + json.dumps(summary, ensure_ascii=False, indent=2),
        )
        selected = select_document([Path(paths["workdir"]) / "output"], format="xlsx")
        if selected.selected is not None and len(selected.candidates) == 1:
            source = evidence.capture("completed_xlsx", selected.selected)
            try:
                report = inspect_document(source)
            except DocumentParseError as error:
                evidence.add_text(
                    "workbook_text",
                    "Unassessable workbook: " + str(error),
                    source_id="completed_xlsx",
                )
                results = {name: (False, str(error)) for name in results}
            else:
                results = assess(report, current, missing)
                evidence.add_text(
                    "workbook_text", report.to_markdown(), source_id="completed_xlsx"
                )
        else:
            evidence.add_text(
                "workbook_text", "No single final workbook: " + selected.reason
            )
        try:
            trajectory = SourceSnapshot.read(
                Path(paths["agent_logs"]) / "trajectory.json",
                max_bytes=128 * 1024 * 1024,
            )
        except FileNotFoundError:
            answer = ""
        else:
            answer = final_answer_text(
                Trajectory.model_validate_json(trajectory.content)
            )
        evidence.add_text("final_answer", answer)
    args.output.write_text(
        json.dumps(
            {
                "checks": [
                    {"id": name, "passed": passed, "evidence": reason}
                    for name, (passed, reason) in results.items()
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
