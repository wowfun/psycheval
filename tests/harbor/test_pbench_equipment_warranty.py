"""Reconciliation and protected-update invariants for a physical-equipment case."""

import asyncio
import copy
import json
import runpy
import shutil
from datetime import datetime
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

TASK = (
    Path(__file__).resolve().parents[2]
    / "datasets/pbench-v1.0/equipment-warranty-reconcile-01"
)
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))


def reference():
    inputs = TASK / "environment/data"
    return GRADER["reference"](
        inspect_document(inputs / "commissioning-register.xlsx"),
        inspect_document(inputs / "service-register.xlsx"),
    )


def write_output(path, rows, *, reordered=False, formulas=False):
    backend = pytest.importorskip("openpyxl")
    book = backend.Workbook()
    sheet = book.active
    sheet.title = "service_assets"
    fields = list(reversed(GRADER["FIELDS"])) if reordered else list(GRADER["FIELDS"])
    sheet.append(fields)
    for row in reversed(list(rows.values())):
        sheet.append([row[field] for field in fields])
        sheet.cell(
            sheet.max_row, fields.index("commissioned_at") + 1
        ).number_format = "yyyy-mm-dd hh:mm:ss"
    if formulas:
        sheet.cell(2, fields.index("extended_service") + 1).value = "=TRUE()"
    book.create_sheet("处理说明").append(
        ["台账保留现有决定，窗口仅用于本次恢复的设备。"]
    )
    book.save(path)
    book.close()
    return inspect_document(path)


def test_reference_is_union_by_asset_number_and_window_only_for_new_rows():
    current, missing, summary = reference()
    assert summary["initial_commissioning_rows"] == 32
    assert summary["initial_service_rows"] == 24
    assert summary["restored_count"] == 12
    assert summary["restored_extended_count"] == 6
    assert summary["final_asset_count"] == 36
    assert summary["final_extended_count"] == 11
    assert {key for key, row in missing.items() if row["extended_service"]} == {
        "AS-00746",
        "AS-00296",
        "AS-01026",
        "AS-00695",
        "AS-00932",
        "AS-00758",
    }
    assert missing["AS-00746"]["commissioned_at"] == datetime(2026, 4, 6, 6)
    assert missing["AS-01026"]["commissioned_at"] == datetime(2026, 4, 14, 21, 59, 59)
    assert not missing["AS-01057"]["extended_service"]
    assert not missing["AS-00320"]["extended_service"]
    assert current["AS-00902"]["model"] == "PT-420 压力探头"
    assert current["AS-00814"]["service_site"] == "东堤三号闸"
    assert current["AS-00445"]["commissioned_at"] == datetime(2026, 3, 28, 14, 20)
    assert current["AS-00481"]["extended_service"] is True
    assert current["AS-00218"]["extended_service"] is False
    assert "AS-00763" in current


@pytest.mark.parametrize("reordered", [False, True])
def test_exact_result_accepts_column_order_row_order_and_explanatory_sheet(
    tmp_path, reordered
):
    current, missing, _ = reference()
    report = write_output(
        tmp_path / "assets.xlsx", {**current, **missing}, reordered=reordered
    )
    assert all(
        passed for passed, _ in GRADER["assess"](report, current, missing).values()
    )


@pytest.mark.parametrize(
    "change",
    [
        "model",
        "service_site",
        "commissioned_at",
        "extended_service",
        "current_only_missing",
    ],
)
def test_source_cannot_overwrite_protected_current_records(tmp_path, change):
    current, missing, _ = reference()
    rows = copy.deepcopy({**current, **missing})
    if change == "model":
        rows["AS-00902"][change] = "VG-320 阀门执行器"
    elif change == "service_site":
        rows["AS-00814"][change] = "柳岸调蓄站"
    elif change == "commissioned_at":
        rows["AS-00445"][change] = datetime(2026, 4, 7)
    elif change == "extended_service":
        rows["AS-00481"][change] = False
    else:
        rows.pop("AS-00763")
    results = GRADER["assess"](
        write_output(tmp_path / "assets.xlsx", rows), current, missing
    )
    assert not results["existing_preserved"][0]
    assert results["omitted_restored"][0]


@pytest.mark.parametrize(
    "change",
    ["boundary_excluded", "outside_included", "omitted_missing", "wrong_source_field"],
)
def test_each_restored_row_has_its_own_source_fields_and_inclusive_window_flag(
    tmp_path, change
):
    current, missing, _ = reference()
    rows = copy.deepcopy({**current, **missing})
    if change == "boundary_excluded":
        rows["AS-00746"]["extended_service"] = False
    elif change == "outside_included":
        rows["AS-01057"]["extended_service"] = True
    elif change == "omitted_missing":
        rows.pop("AS-00125")
    else:
        rows["AS-00932"]["model"] = "PT-410 压力探头"
    results = GRADER["assess"](
        write_output(tmp_path / "assets.xlsx", rows), current, missing
    )
    assert results["existing_preserved"][0]
    assert not results["omitted_restored"][0]


@pytest.mark.parametrize(
    "change", ["fake_extra", "text_boolean", "text_datetime", "formula", "empty"]
)
def test_import_invalid_or_unrelated_rows_do_not_earn_credit(tmp_path, change):
    current, missing, _ = reference()
    rows = copy.deepcopy({**current, **missing})
    if change == "fake_extra":
        rows["AS-99999"] = {**next(iter(rows.values())), "asset_no": "AS-99999"}
    elif change == "text_boolean":
        rows["AS-00746"]["extended_service"] = "TRUE"
    elif change == "text_datetime":
        rows["AS-00746"]["commissioned_at"] = "2026-04-06 06:00:00"
    elif change == "empty":
        rows = {}
    report = write_output(tmp_path / "assets.xlsx", rows, formulas=change == "formula")
    assert not any(
        passed for passed, _ in GRADER["assess"](report, current, missing).values()
    )


def test_public_verifier_uses_snapshots_and_publishes_count_reference_for_real_judge_protocol(
    tmp_path,
):
    loaded = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert loaded.config.agent.timeout_sec == 900
    assert build_scoring_plan(
        json.loads((TASK / "tests/grader.json").read_text())
    ).custom_ids == ("existing_preserved", "omitted_restored")
    assert len(load_judge_config(TASK / "tests/judge.yaml").rubrics) == 1
    roots = {
        name: tmp_path / name
        for name in ("workdir", "inputs", "agent_logs", "verifier_logs", "artifacts")
    }
    for path in roots.values():
        path.mkdir()
    shutil.copytree(TASK / "environment/data", roots["inputs"], dirs_exist_ok=True)
    (roots["workdir"] / "commissioning-register.xlsx").write_bytes(
        b"changed Agent copy must not define truth"
    )
    current, missing, _ = reference()
    output = roots["workdir"] / "output"
    output.mkdir()
    write_output(output / "ready.xlsx", {**current, **missing})
    answer = "已保存补全台账。本次补回的设备中，有六台符合延长现场服务窗口。"
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
            tests=str(TASK / "tests"), **{key: str(path) for key, path in roots.items()}
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
    assert "restored_extended_count" in prompt and "六台" in prompt
    artifacts = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )["artifacts"]
    by_id = {item["id"]: item for item in artifacts}
    assert by_id["commissioning_xlsx"]["source_path"].startswith(str(roots["inputs"]))
    assert (
        by_id["commissioning_xlsx_text"]["source_artifact_id"] == "commissioning_xlsx"
    )
    assert (roots["verifier_logs"] / "artifact_text/final_answer.md").read_text(
        encoding="utf-8"
    ) == answer
