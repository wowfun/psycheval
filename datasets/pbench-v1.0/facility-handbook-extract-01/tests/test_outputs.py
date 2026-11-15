"""Task-owned range and faithful-table checks over shared document facts."""

import argparse
import json
import re
import unicodedata
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from psycheval.harbor.documents import (
    DocumentParseError,
    inspect_document,
    select_document,
)
from psycheval.harbor.documents.models import Paragraph, Table
from psycheval.harbor.evidence import EvidenceWriter, SourceSnapshot

SECTIONS = ("入场与布展", "开放期间运行", "异常与交接")


def normalized(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(str.maketrans({"–": "-", "—": "-", "−": "-"}))
    text = text.replace("≤", "<=").replace("≥", ">=")
    text = re.sub(r"(?<!\d)0([0-9]):", r"\1:", text)
    return re.sub(r"\s+", "", text)


def cell_text(cell):
    if any(not isinstance(block, Paragraph) for block in cell.blocks):
        raise ValueError("Nested tables are not part of this handbook's table schema")
    return "\n".join(block.text for block in cell.blocks)


def matrix(table):
    if not table.cells:
        return []
    height = max(cell.row + cell.row_span - 1 for cell in table.cells)
    width = max(cell.column + cell.column_span - 1 for cell in table.cells)
    if width * height > 4096:
        raise ValueError("Extracted table exceeds the Task's cell limit")
    grid = [[None] * width for _ in range(height)]
    for cell in table.cells:
        value = normalized(cell_text(cell))
        for row in range(cell.row - 1, cell.row + cell.row_span - 1):
            for column in range(cell.column - 1, cell.column + cell.column_span - 1):
                if grid[row][column] is not None:
                    raise ValueError("Overlapping table cells")
                grid[row][column] = value
    if any(value is None for row in grid for value in row):
        raise ValueError("Incomplete rectangular table")
    return grid


def canonical(table):
    grid = matrix(table)
    if len(grid) < 2 or len(grid[0]) != len(set(grid[0])):
        raise ValueError("Missing data or ambiguous table headers")
    order = sorted(range(len(grid[0])), key=grid[0].__getitem__)
    return tuple(grid[0][column] for column in order), tuple(
        sorted(tuple(row[column] for column in order) for row in grid[1:])
    )


def source_tables(report):
    selected, chapter, found = [], None, set()
    for block in report.blocks:
        if isinstance(block, Paragraph) and block.style == "Heading 1":
            chapter = block.text.strip()
            if chapter in SECTIONS:
                found.add(chapter)
        elif isinstance(block, Table) and chapter in SECTIONS:
            selected.append((chapter, block))
    if found != set(SECTIONS) or len(selected) != 6:
        raise ValueError(
            "Retained handbook does not contain the authored chapter/table set"
        )
    return selected


def evaluate_report(report, source):
    tables = [block for block in report.blocks if block.kind == "table"]
    breaks = [block for block in report.blocks if block.kind == "thematic_break"]
    issues = []
    try:
        expected = Counter(canonical(table) for _, table in source)
        observed = Counter(canonical(block.table) for block in tables)
    except ValueError as error:
        return False, str(error)
    if observed != expected:
        issues.append(
            f"Full table bindings differ: matched={sum((observed & expected).values())}, "
            f"required={sum(expected.values())}, observed={sum(observed.values())}"
        )
    lines = report.text.splitlines()
    exact = all(
        block.end_line == block.start_line + 1
        and lines[block.start_line].strip() == "---"
        for block in breaks
    )
    boundaries = [-1, *(block.start_line for block in breaks), len(lines)]
    groups = [
        sum(left < block.start_line and block.end_line <= right for block in tables)
        for left, right in zip(boundaries, boundaries[1:])
    ]
    if not exact or len(breaks) != len(source) - 1 or groups != [1] * len(source):
        issues.append(f"Expected one table per --- group; observed groups={groups}")
    return not issues, "; ".join(
        issues
    ) or "All scoped table cell/row/header bindings and separators matched"


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
    passed, reason = False, "No single final Markdown document"
    with EvidenceWriter(paths["verifier_logs"]) as evidence:
        snapshot = evidence.capture(
            "handbook_docx", Path(paths["inputs"]) / "venue-operations.docx"
        )
        try:
            source_preserved = (
                SourceSnapshot.read(
                    Path(paths["workdir"]) / "venue-operations.docx"
                ).sha256
                == snapshot.sha256
            )
        except (OSError, ValueError):
            source_preserved = False
        source = source_tables(inspect_document(snapshot))
        reference = [
            {
                "chapter": chapter,
                "body_table_index": table.index,
                "cells": [asdict(cell) for cell in table.cells],
            }
            for chapter, table in source
        ]
        evidence.add_text(
            "source_tables",
            "Source: retained initial venue-operations.docx; chapter and body table/cell references follow.\n\n"
            + json.dumps(reference, ensure_ascii=False, indent=2),
            source_id="handbook_docx",
        )
        selection = select_document([Path(paths["workdir"]) / "output"], format="md")
        if selection.selected is None or len(selection.candidates) != 1:
            evidence.add_text(
                "extracted_tables",
                "No single final Markdown document: " + selection.reason,
            )
        else:
            result = evidence.capture("extracted_md", selection.selected)
            try:
                report = inspect_document(result, format="md")
            except DocumentParseError as error:
                reason = str(error)
                evidence.add_text(
                    "extracted_tables",
                    "No assessable Markdown: " + reason,
                    source_id="extracted_md",
                )
            else:
                passed, reason = evaluate_report(report, source)
                if not source_preserved:
                    passed = False
                    reason += "; the working source document was modified, removed or unavailable"
                evidence.add_text(
                    "extracted_tables", report.to_markdown(), source_id="extracted_md"
                )
    args.output.write_text(
        json.dumps(
            {"checks": [{"id": "scoped_tables", "passed": passed, "evidence": reason}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
