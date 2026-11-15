"""Current maintenance actions preserve time, ownership and record bindings."""

import asyncio
import csv
import hashlib
import io
import json
import runpy
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path

import pytest
from harbor.models.trajectories import Trajectory

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
    Path(__file__).resolve().parents[2] / "datasets/pbench-v1.0/maintenance-handover-01"
)
PREPARATION = runpy.run_path(str(TASK / "environment/prepare.py"))
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
REFERENCE = datetime.fromisoformat("2026-11-15T09:20:00+08:00")
DELIVERIES = [
    (
        "WX-4726",
        "完成P-07冷却泵振动复测，上传复测记录和趋势图",
        4,
        "17:30",
        "JL-7241、JL-7318",
    ),
    ("WX-4726", "核对更换轴承的领用数量，回填领用台账", 3, "12:00", "JL-7932"),
    ("WX-3851", "完成D-03配电柜红外测温并提交异常点照片", 1, "18:00", "JL-7405"),
    ("WX-6184", "复核消防水泵压力曲线并签署复核意见", 6, "22:00", "JL-7584、JL-8286"),
    ("WX-2907", "确认冷库门封条验收并回传签收单", 2, "16:00", "JL-7163"),
]


def materials(reference=REFERENCE):
    return PREPARATION["build_materials"](reference)


def correct_rows(state):
    monday = datetime.fromisoformat(state["week_start"]).date()
    return [
        [order, action, f"{monday + timedelta(days=day):%Y-%m-%d} {clock}", sources]
        for order, action, day, clock, sources in DELIVERIES
    ]


def answer(rows):
    return (
        "| 工单号 | 待办动作 | 截止时间 | 来源记录ID |\n| --- | --- | --- | --- |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
    )


@pytest.mark.parametrize(
    "reference",
    [
        REFERENCE,
        datetime.fromisoformat("2026-12-31T08:15:00+08:00"),
        datetime.fromisoformat("2027-01-04T00:05:00+08:00"),
    ],
)
def test_one_reference_moves_dates_records_and_expected_bindings_together(reference):
    content, state = materials(reference)
    records = list(csv.DictReader(io.StringIO(content.decode("utf-8"))))
    assert len(records) == 16
    assert {row["导出时间"] for row in records} == {reference.isoformat()}
    assert all(datetime.fromisoformat(row["记录时间"]) <= reference for row in records)
    monday = reference.date() - timedelta(days=reference.weekday())
    assert state["week_start"] == monday.isoformat()
    assert state["week_end_exclusive"] == (monday + timedelta(days=7)).isoformat()
    assert state["source_sha256"] == hashlib.sha256(content).hexdigest()
    by_id = {row["记录ID"]: row for row in records}
    for todo, independent_row in zip(state["todos"], correct_rows(state), strict=True):
        assert todo["order"] == independent_row[0]
        assert todo["deadline"] == independent_row[2]
        assert todo["deadline"] in by_id[todo["deadline_source"]]["记录正文"]
    assert GRADER["evaluate_answer"](answer(correct_rows(state)), state)[0]


def test_prepare_writes_only_selected_workspace_input_and_private_state(
    tmp_path, monkeypatch
):
    class Clock:
        @staticmethod
        def now(timezone):
            return REFERENCE.astimezone(timezone)

    monkeypatch.setitem(PREPARATION["prepare"].__globals__, "datetime", Clock)
    workdir, private = tmp_path / "workdir", tmp_path / "state"
    workdir.mkdir()
    private.mkdir()
    assert PREPARATION["prepare"](str(workdir), str(private)) == ["handover.csv"]
    assert {p.name for p in workdir.iterdir()} == {"handover.csv"}
    content, state = materials()
    assert (workdir / "handover.csv").read_bytes() == content
    assert json.loads((private / "reference.json").read_text(encoding="utf-8")) == state


@pytest.mark.parametrize("mode", ["normal", "reversed", "fenced", "without_total"])
def test_one_row_per_delivery_accepts_order_and_harmless_presentation_variation(mode):
    _, state = materials()
    rows = correct_rows(state)
    if mode == "reversed":
        rows.reverse()
    text = answer(rows)
    if mode == "fenced":
        text = "```markdown\n" + text + "\n```"
    if mode == "normal":
        text += "\n\n共5项，本周已逾期但未结事项仍保留。"
    assert GRADER["evaluate_answer"](text, state)[0]


def test_action_binding_accepts_common_equivalent_phrasing():
    _, state = materials()
    rows = correct_rows(state)
    alternatives = [
        "对P-07做振动检测，提交复测记录和趋势曲线",
        "核对轴承领料数量并更新台账",
        "对D-03做温度测量，附异常部位图片",
        "审核消防水泵压力曲线，签名出具意见",
        "核验冷库密封条，回传签收回执",
    ]
    for row, action in zip(rows, alternatives, strict=True):
        row[1] = action
    assert GRADER["evaluate_answer"](answer(rows), state)[0]


@pytest.mark.parametrize(
    "action",
    [
        "复核消防水泵压力曲线，亲笔签认复核结论",
        "复核消防水泵压力曲线，并签署复核意见",
    ],
)
def test_pressure_signoff_equivalence_uses_existing_retained_groups(action):
    _, state = materials()
    pressure = next(todo for todo in state["todos"] if todo["id"] == "pressure")
    assert pressure["groups"][-1] == ["意见", "签署", "签字", "签名"]
    rows = correct_rows(state)
    rows[3][1] = action
    assert GRADER["evaluate_answer"](answer(rows), state)[0]


@pytest.mark.parametrize(
    "action",
    ["复核消防水泵压力曲线并形成复核结论", "亲笔签认复核结论"],
)
def test_signoff_normalization_does_not_supply_missing_action_parts(action):
    _, state = materials()
    rows = correct_rows(state)
    rows[3][1] = action
    assert not GRADER["evaluate_answer"](answer(rows), state)[0]


@pytest.mark.parametrize(
    "mutation",
    [
        "blank",
        "numbers",
        "missing",
        "extra",
        "duplicate",
        "merged",
        "old_deadline",
        "old_source",
        "wrong_source",
        "stuffed_sources",
        "wrong_order",
        "date_only",
    ],
)
def test_unreliable_action_sets_do_not_earn_the_binding_rule(mutation):
    _, state = materials()
    rows = correct_rows(state)
    if mutation == "blank":
        text = ""
    elif mutation == "numbers":
        text = "5项，2026-11-13，17:30，JL-7241，WX-4726"
    else:
        if mutation == "missing":
            rows.pop()
        elif mutation == "extra":
            rows.append(["WX-8421", "补交空压机润滑记录", rows[0][2], "JL-7268"])
        elif mutation == "duplicate":
            rows[1] = rows[0]
        elif mutation == "merged":
            rows[0][1] += "；" + rows[1][1]
        elif mutation == "old_deadline":
            rows[0][2] = rows[4][2]
        elif mutation == "old_source":
            rows[0][3] = "JL-7318"
        elif mutation == "wrong_source":
            rows[3][3] = "JL-8032"
        elif mutation == "stuffed_sources":
            rows[0][3] = "、".join(todo["deadline_source"] for todo in state["todos"])
        elif mutation == "wrong_order":
            rows[2][0] = "WX-6653"
        elif mutation == "date_only":
            rows[0][2] = rows[0][2].split()[0]
        text = answer(rows)
    assert not GRADER["evaluate_answer"](text, state)[0]


def runtime(tmp_path, text):
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
    for root in roots.values():
        root.mkdir()
    content, state = materials()
    (roots["inputs"] / "handover.csv").write_bytes(content)
    (roots["preparation_state"] / "reference.json").write_text(
        json.dumps(state, ensure_ascii=False), encoding="utf-8"
    )
    (roots["workdir"] / "handover.csv").write_text(
        "A changed writable copy is not grading truth"
    )
    trajectory = Trajectory.model_validate(
        {
            "schema_version": "ATIF-v1.7",
            "agent": {"name": "fixture", "version": "1"},
            "steps": [{"step_id": 1, "source": "agent", "message": text}],
        }
    )
    (roots["agent_logs"] / "trajectory.json").write_text(
        trajectory.model_dump_json(), encoding="utf-8"
    )
    config = EffectiveRuntimeConfig(
        paths=RuntimePaths(
            tests=str(TASK / "tests"),
            **{key: str(value) for key, value in roots.items()},
        ),
        verifier=VerifierInvocation(
            (TASK / "instruction.md").read_text(encoding="utf-8")
        ),
    )
    return roots, config


def test_public_verifier_uses_retained_input_and_delivers_bound_evidence(tmp_path):
    loaded = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert loaded.config.agent.timeout_sec == 900
    assert build_scoring_plan(
        json.loads((TASK / "tests/grader.json").read_text())
    ).custom_ids == ("current_action_bindings",)
    judge = load_judge_config(TASK / "tests/judge.yaml")
    assert (judge.rule_weight, judge.llm_weight) == (0.4, 0.6)
    _, state = materials()
    text = answer(correct_rows(state))
    roots, config = runtime(tmp_path, text)
    with judge_server() as server:
        result = asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=config,
                judge_settings=JudgeSettings(True, server["url"], "local-fixture"),
            )
        )
        assert len(server["requests"]) == 2
        prompts = [
            unescape(request["messages"][-1]["content"])
            for request in server["requests"]
        ]
    assert result["reward"] == 1 and result["metadata"]["score_merge"]["applied"]
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    artifacts = {record["id"]: record for record in manifest["artifacts"]}
    assert artifacts["source_handover"]["source_artifact_id"] == "handover_csv"
    assert artifacts["handover_csv"]["source_path"].startswith(str(roots["inputs"]))
    excerpt = (
        roots["verifier_logs"] / artifacts["source_handover"]["text_path"]
    ).read_text(encoding="utf-8")
    assert excerpt in prompts[0] and excerpt in prompts[1]
    assert text in prompts[0] and text in prompts[1]
    assert any(state["week_start"] in prompt for prompt in prompts)


def test_mismatched_retained_state_is_a_verifier_error(tmp_path):
    _, state = materials()
    roots, config = runtime(tmp_path, answer(correct_rows(state)))
    (roots["inputs"] / "handover.csv").write_text("Changed retained source")
    with pytest.raises(RuntimeError, match="custom verifier exited"):
        asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=config,
                judge_settings=JudgeSettings(),
            )
        )
    assert not (roots["verifier_logs"] / "reward.json").exists()
