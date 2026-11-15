"""Supplier-receiving outcome invariants and evidence delivery."""

import asyncio
import copy
import json
import runpy
import shutil
from pathlib import Path

import pytest
from harbor.models.trajectories import Trajectory

from psycheval.harbor.documents import inspect_document
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

TASK = Path(__file__).resolve().parents[2] / "datasets/pbench-v1.0/receiving-quality-01"
SCORER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
DETAIL = [
    ["SH-1047", 2, "澄野食品", "CT-024", 24, 192, 4],
    ["SH-1061", 1, "澄野食品", "OL-015", 10, 60, 2],
    ["SH-1093", 2, "澄野食品", "CT-024", 24, 72, 6],
    ["SH-1118", 1, "澄野食品", "OT-012", 12, 60, 1],
    ["SH-1038", 1, "青屿乳业", "YG-016", 16, 160, 2],
    ["SH-1074", 2, "青屿乳业", "YG-016", 12, 24, 6],
    ["SH-1106", 1, "青屿乳业", "OT-012", 12, 144, 0],
    ["SH-1129", 1, "青屿乳业", "CT-024", 24, 24, 1],
    ["SH-1056", 1, "禾境饮品", "OT-012", 12, 48, 8],
    ["SH-1082", 1, "禾境饮品", "CT-024", 24, 216, 1],
    ["SH-1101", 1, "禾境饮品", "OL-015", 15, 105, 0],
    ["SH-1137", 1, "禾境饮品", "OL-015", 20, 40, 2],
]
SUMMARY = [
    ["澄野食品", 384, 13, 13 / 384],
    ["青屿乳业", 352, 9, 9 / 352],
    ["禾境饮品", 409, 11, 11 / 409],
]


def expected():
    root = TASK / "environment/data"
    return SCORER["reference"](
        (root / "products.csv").read_bytes(), (root / "receipts.csv").read_bytes()
    )


def workbook(path, details=DETAIL, summary=SUMMARY, percent_header=False):
    backend = pytest.importorskip("openpyxl")
    result = backend.Workbook()
    sheet = result.active
    sheet.title = "可复核明细"
    sheet.append(list(SCORER["DETAIL"]))
    for row in details:
        sheet.append(row)
    sheet = result.create_sheet("采购汇总")
    sheet.append(
        [*SCORER["SUMMARY"][:-1], "不合格率(%)" if percent_header else "不合格率"]
    )
    for row in summary:
        sheet.append(row)
        if not percent_header and isinstance(row[-1], (int, float)):
            sheet.cell(sheet.max_row, 4).number_format = "0.00%"
    result.save(path)
    result.close()
    return inspect_document(path)


def test_reference_selects_latest_before_status_and_has_different_weighted_ranking():
    detail, summary = expected()
    assert detail == {row[0]: dict(zip(SCORER["DETAIL"], row)) for row in DETAIL}
    assert summary == {row[0]: dict(zip(SCORER["SUMMARY"], row)) for row in SUMMARY}
    assert "SH-1142" not in detail
    assert max(summary, key=lambda name: summary[name]["不合格率"]) == "澄野食品"
    unweighted = {
        name: sum(row[6] / row[5] for row in DETAIL if row[2] == name) / 4
        for name in summary
    }
    assert max(unweighted, key=unweighted.get) == "青屿乳业"


@pytest.mark.parametrize("percent_header", [False, True])
def test_materialized_workbook_and_rounded_percentages_are_accepted(
    tmp_path, percent_header
):
    rows = copy.deepcopy(SUMMARY)
    for row in rows:
        row[-1] = round(row[-1] * 100, 2) if percent_header else f"{row[-1] * 100:.2f}%"
    report = workbook(
        tmp_path / "results.xlsx", summary=rows, percent_header=percent_header
    )
    assert SCORER["grade_tables"](report, *expected())[:2] == (True, True)


@pytest.mark.parametrize(
    "mutation",
    [
        "old_revision",
        "cancelled",
        "missing",
        "wrong_override",
        "uncached_formula",
        "duplicate",
    ],
)
def test_incorrect_effective_receipts_cannot_hide_behind_correct_summary(
    tmp_path, mutation
):
    rows = copy.deepcopy(DETAIL)
    if mutation == "old_revision":
        rows[0][1] = 1
    elif mutation == "cancelled":
        rows.append(["SH-1142", 1, "禾境饮品", "CT-024", 24, 480, 1])
    elif mutation == "missing":
        rows.pop()
    elif mutation == "wrong_override":
        rows[1][4:6] = [15, 90]
    elif mutation == "uncached_formula":
        rows[0][5] = "=8*24"
    else:
        rows.append(rows[0])
    report = workbook(tmp_path / "results.xlsx", details=rows)
    assert SCORER["grade_tables"](report, *expected())[:2] == (False, True)


@pytest.mark.parametrize(
    "mutation", ["unweighted", "swapped", "duplicate", "wrong_denominator"]
)
def test_supplier_identity_numerator_denominator_and_ratio_are_bound(
    tmp_path, mutation
):
    rows = copy.deepcopy(SUMMARY)
    if mutation == "unweighted":
        for row in rows:
            row[-1] = sum(r[6] / r[5] for r in DETAIL if r[2] == row[0]) / 4
    elif mutation == "swapped":
        rows[0][2], rows[1][2] = rows[1][2], rows[0][2]
    elif mutation == "duplicate":
        rows.append(rows[0])
    else:
        rows[0][1] += rows[0][2]
    report = workbook(tmp_path / "results.xlsx", summary=rows)
    assert SCORER["grade_tables"](report, *expected())[:2] == (True, False)


def test_empty_tables_do_not_earn_credit(tmp_path):
    report = workbook(tmp_path / "results.xlsx", details=[], summary=[])
    assert SCORER["grade_tables"](report, *expected())[:2] == (False, False)


@pytest.mark.parametrize("correct", [True, False])
def test_optional_annotated_grand_total_is_validated_without_becoming_a_supplier(
    tmp_path, correct
):
    rows = copy.deepcopy(SUMMARY)
    rows.append(["总计（非供应商）", 1145 if correct else 1146, 33, 33 / 1145])
    report = workbook(tmp_path / "results.xlsx", summary=rows)
    assert SCORER["grade_tables"](report, *expected())[:2] == (True, correct)


def test_percentage_header_cannot_hide_a_hundredfold_scale_error(tmp_path):
    report = workbook(tmp_path / "results.xlsx", percent_header=True)
    assert SCORER["grade_tables"](report, *expected())[:2] == (True, False)


def test_two_tables_on_one_worksheet_do_not_meet_the_two_sheet_contract(tmp_path):
    backend = pytest.importorskip("openpyxl")
    book = backend.Workbook()
    sheet = book.active
    for row_index, row in enumerate([list(SCORER["SUMMARY"]), *SUMMARY], 1):
        for column, value in enumerate(row, 10):
            sheet.cell(row_index, column, value)
        if row_index > 1:
            sheet.cell(row_index, 13).number_format = "0.00%"
    for row_index, row in enumerate([list(SCORER["DETAIL"]), *DETAIL], 7):
        for column, value in enumerate(row, 1):
            sheet.cell(row_index, column, value)
    path = tmp_path / "one-sheet.xlsx"
    book.save(path)
    book.close()
    assert SCORER["grade_tables"](inspect_document(path), *expected())[:2] == (
        False,
        False,
    )


def test_verifier_uses_initial_sources_and_delivers_source_bound_evidence(tmp_path):
    assert (
        load_harbor_task(TASK, read_bytes=Path.read_bytes).config.agent.timeout_sec
        == 900
    )
    assert build_scoring_plan(
        json.loads((TASK / "tests/grader.json").read_text())
    ).custom_ids == ("effective_receipts", "supplier_aggregation")
    judge = load_judge_config(TASK / "tests/judge.yaml")
    assert len(judge.rubrics) == 1
    roots = {
        name: tmp_path / name
        for name in ("workdir", "inputs", "agent_logs", "verifier_logs", "artifacts")
    }
    for root in roots.values():
        root.mkdir()
    shutil.copytree(TASK / "environment/data", roots["inputs"], dirs_exist_ok=True)
    (roots["workdir"] / "receipts.csv").write_text("Agent changed this copy")
    output = roots["workdir"] / "output"
    output.mkdir()
    workbook(output / "supplier-review.xlsx")
    answer = "本批优先复盘澄野食品，其不合格率为 13/384，约3.39%。建议逐批复核验收照片与抽样记录，不能据这一次数据断言长期品质或根因。"
    trajectory = Trajectory.model_validate(
        {
            "schema_version": "ATIF-v1.7",
            "agent": {"name": "fixture", "version": "1"},
            "steps": [{"step_id": 1, "source": "agent", "message": answer}],
        }
    )
    (roots["agent_logs"] / "trajectory.json").write_text(
        trajectory.model_dump_json(), encoding="utf-8"
    )
    runtime = EffectiveRuntimeConfig(
        paths=RuntimePaths(
            tests=str(TASK / "tests"),
            **{key: str(value) for key, value in roots.items()},
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
    assert result["reward"] == 1 and result["metadata"]["score_merge"]["applied"]
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    artifacts = {row["id"]: row for row in manifest["artifacts"]}
    for source in ("products", "receipts"):
        assert artifacts[source + "_excerpt"]["source_artifact_id"] == source
        assert artifacts[source]["source_path"].startswith(str(roots["inputs"]))
        assert "L1:" in (
            roots["verifier_logs"] / artifacts[source + "_excerpt"]["text_path"]
        ).read_text(encoding="utf-8")
        assert f"{source}.csv" in prompt
    assert answer in prompt
