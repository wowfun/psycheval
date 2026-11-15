"""Range, binding and evidence invariants for the venue table-extraction Task."""

import asyncio
import copy
import json
import runpy
import shutil
from html import escape
from pathlib import Path

import pytest

from psycheval.harbor.documents import inspect_document
from psycheval.harbor.evidence import SourceSnapshot
from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    VerifierInvocation,
)
from psycheval.harbor.tasks import load_harbor_task
from psycheval.harbor.verifier import (
    JudgeSettings,
    build_scoring_plan,
    load_judge_config,
    run_verifier,
)
from tests.fixtures.judge_server import judge_server

TASK = (
    Path(__file__).resolve().parents[2]
    / "datasets/pbench-v1.0/facility-handbook-extract-01"
)
SOURCE = TASK / "environment/data/venue-operations.docx"
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))


def source_tables():
    return GRADER["source_tables"](inspect_document(SOURCE))


def source_grids():
    backend = pytest.importorskip("docx")
    doc = backend.Document(SOURCE)
    return [
        [[cell.text for cell in row.cells] for row in table.rows]
        for table in doc.tables[1:7]
    ]


def pipe(grid):
    rows = [
        "| "
        + " | ".join(value.replace("|", "\\|").replace("\n", "<br>") for value in row)
        + " |"
        for row in grid
    ]
    rows.insert(1, "| " + " | ".join("---" for _ in grid[0]) + " |")
    return "\n".join(rows)


def markdown(grids=None):
    return "\n\n---\n\n".join(
        pipe(grid) for grid in (source_grids() if grids is None else grids)
    )


def report(text):
    return inspect_document(SourceSnapshot(Path("tables.md"), text.encode("utf-8")))


def test_source_has_six_scoped_tables_and_two_out_of_scope_tables():
    doc = inspect_document(SOURCE)
    from psycheval.harbor.documents.models import Table

    assert len([block for block in doc.blocks if isinstance(block, Table)]) == 8
    selected = source_tables()
    assert [chapter for chapter, _ in selected] == ["入场与布展"] * 2 + [
        "开放期间运行"
    ] * 2 + ["异常与交接"] * 2
    assert any(cell.row_span == 2 for _, table in selected for cell in table.cells)
    assert GRADER["evaluate_report"](report(markdown()), selected)[0]


def test_row_and_column_order_whitespace_and_equivalent_operators_are_accepted():
    grids = source_grids()[::-1]
    for grid in grids:
        grid[1:] = grid[:0:-1]
        for index, row in enumerate(grid):
            grid[index] = [
                "  " + value.replace("≤", "<=").replace("≥", ">=") + "  "
                for value in row[::-1]
            ]
    assert GRADER["evaluate_report"](report(markdown(grids)), source_tables())[0]


def test_html_rowspan_and_pipe_tables_can_coexist_without_losing_bindings():
    grids = source_grids()
    # The service-response table's two S2 rows share the first-column cell.
    grid = grids[3]
    body = []
    for index, row in enumerate(grid):
        tag = "th" if index == 0 else "td"
        cells = []
        for column, value in enumerate(row):
            if index == 3 and column == 0:
                continue
            span = ' rowspan="2"' if index == 2 and column == 0 else ""
            cells.append(f"<{tag}{span}>{escape(value)}</{tag}>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    tables = [pipe(grid) for grid in grids]
    tables[3] = "<table>\n" + "\n".join(body) + "\n</table>"
    assert GRADER["evaluate_report"](
        report("\n\n---\n\n".join(tables)), source_tables()
    )[0]


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "wrong_number",
        "swapped_cells",
        "outside",
        "placeholder",
        "separator",
        "fenced",
    ],
)
def test_counts_and_keyword_stuffing_cannot_replace_faithful_scoped_tables(mutation):
    grids = copy.deepcopy(source_grids())
    if mutation == "missing":
        grids.pop()
    elif mutation == "duplicate":
        grids[-1] = copy.deepcopy(grids[0])
    elif mutation == "wrong_number":
        grids[0][1][2] = "07:00–10:00"
    elif mutation == "swapped_cells":
        grids[1][1][3], grids[1][2][3] = grids[1][2][3], grids[1][1][3]
    elif mutation == "outside":
        backend = pytest.importorskip("docx")
        outside = backend.Document(SOURCE).tables[-1]
        grids.append([[cell.text for cell in row.cells] for row in outside.rows])
    elif mutation == "placeholder":
        grids = [[grid[0], ["待补充"] * len(grid[0])] for grid in grids]
    text = markdown(grids)
    if mutation == "separator":
        text = text.replace("\n---\n", "\n***\n")
    elif mutation == "fenced":
        text = "```markdown\n" + text + "\n```"
    assert not GRADER["evaluate_report"](report(text), source_tables())[0]


@pytest.mark.parametrize("change_working_source", [False, True])
def test_verifier_captures_initial_source_and_passes_actual_excerpt_to_judge(
    tmp_path, change_working_source
):
    loaded = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert loaded.config.agent.timeout_sec == 900
    assert build_scoring_plan(
        json.loads((TASK / "tests/grader.json").read_text())
    ).custom_ids == ("scoped_tables",)
    judge = load_judge_config(TASK / "tests/judge.yaml")
    assert len(judge.rubrics) == 1 and judge.rubrics[0].artifact_refs == (
        "source_tables",
        "extracted_tables",
    )
    roots = {
        name: tmp_path / name
        for name in ("workdir", "inputs", "agent_logs", "verifier_logs", "artifacts")
    }
    for root in roots.values():
        root.mkdir()
    for root in (roots["workdir"], roots["inputs"]):
        shutil.copyfile(SOURCE, root / SOURCE.name)
    if change_working_source:
        (roots["workdir"] / SOURCE.name).write_bytes(b"changed by Agent")
    output = roots["workdir"] / "output"
    output.mkdir()
    text = markdown()
    (output / "operations.md").write_text(text, encoding="utf-8")
    runtime = EffectiveRuntimeConfig(
        paths=RuntimePaths(
            tests=str(TASK / "tests"),
            **{name: str(path) for name, path in roots.items()},
        ),
        verifier=VerifierInvocation(
            (TASK / "instruction.md").read_text(encoding="utf-8")
        ),
    )
    with judge_server() as server:
        result = asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=runtime,
                judge_settings=JudgeSettings(True, server["url"], "local-fixture"),
            )
        )
        assert len(server["requests"]) == 1
        prompt = server["requests"][0]["messages"][-1]["content"]
    assert result["test_pass_rate"] == (0 if change_working_source else 1)
    assert result["metadata"]["score_merge"]["applied"]
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    records = {row["id"]: row for row in manifest["artifacts"]}
    assert records["source_tables"]["source_artifact_id"] == "handbook_docx"
    assert records["handbook_docx"]["source_path"].startswith(str(roots["inputs"]))
    source_text = (
        roots["verifier_logs"] / records["source_tables"]["text_path"]
    ).read_text(encoding="utf-8")
    assert escape(source_text, quote=False) in prompt
    assert escape(text, quote=False) in prompt
    assert (
        roots["verifier_logs"] / records["handbook_docx"]["verifier_raw_path"]
    ).read_bytes() == SOURCE.read_bytes()
