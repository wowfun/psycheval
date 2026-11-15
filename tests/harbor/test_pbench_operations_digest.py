"""Date, revision, selection and Judge-evidence invariants for an archive digest."""

import asyncio
import hashlib
import json
import runpy
from datetime import datetime, timedelta
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
    / "datasets/pbench-v1.0/operations-bulletin-digest-01"
)
PREPARE = runpy.run_path(str(TASK / "environment/prepare.py"))
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
REFERENCE = datetime.fromisoformat("2026-12-31T07:22:00+00:00")


def stage(workdir, state, monkeypatch, reference=REFERENCE):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return reference.astimezone(tz)

    monkeypatch.setitem(PREPARE["prepare"].__globals__, "datetime", Clock)
    assert PREPARE["prepare"](workdir, state) == ["materials"]
    return json.loads(
        (workdir / "materials/briefing-context.json").read_text(encoding="utf-8")
    )


def answer(context, *, shuttle="B-8163"):
    return f"""今日运营提醒｜{context["reference_date"]} 上海时间，资料截点15:00。

1. 北门车辆16:30恢复；此前车辆走东门，行人可正常走北门。〔B-7392〕
2. B座2至8层今晚22:00至次日02:00停生活用水，请提前备水；A座及消防供水不受影响。〔B-3915〕
3. 访客自16:00起到南门一层，之前沿用原点，已审核预约无需重办，货运仍走西门。〔B-2639〕
4. 北停车场4至9号充电位升级，17:00前勿占维修位，可用其他车位；并非火警。〔B-9602〕
5. 东食堂晚餐移至西食堂17:00至19:00供应，餐卡照常；午餐不变。〔B-9027〕
6. 环线班车14:10恢复原路线与西厅站，临时站撤销，班距15分钟。〔{shuttle}〕
7. C座3号电梯已通过复检，12:30恢复使用，无需再绕行。〔B-6450〕
"""


@pytest.mark.parametrize(
    "reference, date_value",
    [
        ("2026-12-31T07:22:00+00:00", "2026-12-31"),
        ("2026-12-31T18:22:00+00:00", "2027-01-01"),
        ("2028-02-28T23:50:00+00:00", "2028-02-29"),
        ("2028-02-29T23:50:00+00:00", "2028-03-01"),
    ],
)
def test_one_shanghai_reference_moves_all_source_times_and_cross_day_arrangements(
    tmp_path, reference, date_value
):
    context, text = PREPARE["build_materials"](datetime.fromisoformat(reference))
    assert context["reference_date"] == date_value
    assert context["cutoff"] == date_value + "T15:00:00+08:00"
    path = tmp_path / "bulletins.md"
    path.write_text(text, encoding="utf-8")
    records = GRADER["source_records"](inspect_document(path))
    assert len(records) == 21
    cutoff = datetime.fromisoformat(context["cutoff"])
    assert records["B-2084"]["published_at"] == date_value + "T16:00:00+08:00"
    assert (
        datetime.fromisoformat(records["B-4481"]["published_at"]).date()
        == (cutoff + timedelta(days=1)).date()
    )
    assert (cutoff + timedelta(days=1)).date().isoformat() in records["B-3915"]["body"]
    assert date_value in records["B-4731"]["body"]
    assert (
        datetime.fromisoformat(records["B-4731"]["published_at"]).date()
        == (cutoff - timedelta(days=1)).date()
    )
    assert "B-7392" in GRADER["selection_reference"](context, records)


def test_preparation_retains_hashes_and_no_answer_labels_or_workspace_state(
    tmp_path, monkeypatch
):
    inputs, state = tmp_path / "inputs", tmp_path / "state"
    context = stage(inputs, state, monkeypatch)
    retained = json.loads((state / "reference.json").read_text(encoding="utf-8"))
    assert retained["context"] == context
    assert retained["sha256"] == {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (inputs / "materials").iterdir()
    }
    text = (inputs / "materials/bulletins.md").read_text(encoding="utf-8")
    assert not any(
        value in text
        for value in ("expected", "synthetic", "benchmark", "gold", str(tmp_path))
    )
    assert not (inputs / "reference.json").exists()


@pytest.mark.parametrize("shuttle", ["B-8163", "B-4627"])
def test_current_original_or_faithful_relay_is_valid_without_forcing_a_single_citation(
    shuttle,
):
    context, _ = PREPARE["build_materials"](REFERENCE)
    assert GRADER["assess"](answer(context, shuttle=shuttle), context)[0]


def test_natural_reference_format_and_different_item_order_are_accepted():
    context, _ = PREPARE["build_materials"](REFERENCE)
    text = (
        answer(context).replace("2026-12-31", "2026年12月31日").replace("15:00", "15点")
    )
    prefix, body = text.split("1. ", 1)
    items = ("1. " + body).splitlines()
    assert GRADER["assess"](prefix + "\n".join(reversed(items)), context)[0]


@pytest.mark.parametrize(
    "displayed_date, passed",
    [("2026 年 11 月 15 日", True), ("2026 年 11 月 14 日", False)],
)
def test_date_whitespace_is_accepted_without_accepting_a_different_reference_day(
    displayed_date, passed
):
    context, _ = PREPARE["build_materials"](
        datetime.fromisoformat("2026-11-15T10:22:00+08:00")
    )
    text = answer(context).replace(context["reference_date"], displayed_date)
    assert GRADER["assess"](text, context)[0] is passed


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "duplicate",
        "merged",
        "stale",
        "excluded",
        "unknown",
        "unbound",
        "wrong_date",
        "blank",
        "stuffed",
    ],
)
def test_shortcuts_and_incorrect_source_selection_do_not_earn_rule_credit(change):
    context, _ = PREPARE["build_materials"](REFERENCE)
    text = answer(context)
    if change == "missing":
        text = text[: text.index("7. ")]
    elif change == "duplicate":
        text += "\n8. 环线班车已经恢复。〔B-4627〕\n"
    elif change == "merged":
        text = text.replace("\n2. B座", " B座")
    elif change == "stale":
        text = text.replace("B-7392", "B-5904")
    elif change == "excluded":
        text += "\n8. 东门16:15暂停车辆通行。〔B-2084〕\n"
    elif change == "unknown":
        text = text.replace("B-7392", "B-9999")
    elif change == "unbound":
        text = "〔B-7392〕\n" + text
    elif change == "wrong_date":
        text = text.replace(context["reference_date"], "2025-01-01")
    elif change == "blank":
        text = ""
    else:
        text = (
            text.split("\n1.")[0]
            + "\n1. 北门 班车 B座 电梯 充电 食堂 访客 "
            + " ".join(
                f"〔{sorted(current)[0]}〕"
                for _, current, _ in GRADER["GROUPS"].values()
            )
        )
    assert not GRADER["assess"](text, context)[0]


def test_public_verifier_reads_retained_sources_and_sends_located_slices_to_each_judge(
    tmp_path, monkeypatch
):
    loaded = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert loaded.config.agent.timeout_sec == 900
    assert build_scoring_plan(
        json.loads((TASK / "tests/grader.json").read_text())
    ).custom_ids == ("source_bound_selection",)
    assert len(load_judge_config(TASK / "tests/judge.yaml").rubrics) == 2
    roots = {
        name: tmp_path / name
        for name in (
            "workdir",
            "inputs",
            "preparation_state",
            "agent_logs",
            "verifier_logs",
            "artifacts",
        )
    }
    for path in roots.values():
        path.mkdir()
    context = stage(roots["inputs"], roots["preparation_state"], monkeypatch)
    (roots["workdir"] / "materials").mkdir()
    (roots["workdir"] / "materials/bulletins.md").write_text(
        "Agent changed this copy", encoding="utf-8"
    )
    text = answer(context)
    trajectory = Trajectory.model_validate(
        {
            "schema_version": "ATIF-v1.7",
            "agent": {"name": "fixture", "version": "1"},
            "steps": [
                {
                    "step_id": 1,
                    "source": "agent",
                    "message": "An earlier draft is not the deliverable.",
                },
                {"step_id": 2, "source": "agent", "message": text},
            ],
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
        assert len(server["requests"]) == 2
        for request in server["requests"]:
            prompt = request["messages"][-1]["content"]
            assert (
                "Source slice B-7392" in prompt
                and "Source: bulletin_sources, lines " in prompt
            )
            assert "B-5904" in prompt and "原定18:00提前" in prompt
            assert "2026-12-31T15:00:00+08:00" in prompt and text in prompt
            assert "Agent changed this copy" not in prompt
    assert result["reward"] == 1 and result["metadata"]["score_merge"]["applied"]
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )["artifacts"]
    by_id = {item["id"]: item for item in manifest}
    assert by_id["source_slices"]["source_artifact_id"] == "bulletin_sources"
    assert by_id["bulletin_sources"]["source_path"].startswith(str(roots["inputs"]))
    assert (roots["verifier_logs"] / "artifact_text/final_answer.md").read_text(
        encoding="utf-8"
    ) == text
