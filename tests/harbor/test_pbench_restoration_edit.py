"""Restoration handbook tables and immutable source evidence boundaries."""

import asyncio
import json
import runpy
from dataclasses import replace
from html import unescape
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
    / "datasets/pbench-v1.0/restoration-handbook-edit-01"
)
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
CAPACITY = """| 类别 | 常规排期参考（工作日） | 单轮接收上限（件） | 必需交接附件 |
| --- | --- | --- | --- |
| 纸本纪念物 | 12 | 20 | 页数清单与登记照片 |
| 木作标牌 | 18 | 8 | 部件清单与登记照片 |
| 织物纪念品 | 15 | 10 | 尺寸记录与登记照片 |"""
REGISTERED = """| 类别 | 本轮登记（件） | 进入排期（件） | 待确认（件） |
| --- | --- | --- | --- |
| 纸本纪念物 | 24 | 20 | 4 |
| 木作标牌 | 11 | 8 | 3 |
| 织物纪念品 | 9 | 9 | 0 |
| 合计 | 44 | 37 | 7 |"""
BUDGET = """| 用途 | 预算金额（元） |
| --- | --- |
| 入库建档 | 680 |
| 交接包装 | 940 |
| 公众说明会 | 360 |
| 预备金 | 420 |
| 合计 | 2400 |"""
TABLES = "\n\n".join([CAPACITY, REGISTERED, BUDGET])


def inspect(text):
    return inspect_document(
        SourceSnapshot(Path("handbook.md"), text.encode("utf-8")), format="md"
    )


@pytest.mark.parametrize(
    "mode",
    [
        "normal",
        "reordered_columns",
        "synonyms",
        "money_units",
        "merged_capacity_registration",
    ],
)
def test_objective_tables_bind_meanings_and_accept_equivalent_presentation(mode):
    text = TABLES
    if mode == "reordered_columns":
        replacement = """| 待确认（件） | 类别 | 进入排期（件） | 本轮登记（件） |
| --- | --- | --- | --- |
| 7 | 合计 | 37 | 44 |
| 0 | 织物纪念品 | 9 | 9 |
| 4 | 纸本纪念物 | 20 | 24 |
| 3 | 木作标牌 | 8 | 11 |"""
        text = text.replace(REGISTERED, replacement)
    elif mode == "synonyms":
        for old, new in [
            ("类别", "品类"),
            ("常规排期参考（工作日）", "参考排期（工作日）"),
            ("单轮接收上限", "单轮容量"),
            ("本轮登记", "登记数量"),
            ("进入排期", "已排期"),
            ("用途", "预算项目"),
            ("预算金额", "额度"),
            ("预备金", "备用金"),
            ("合计", "总计"),
            ("纸本纪念物", "纸质纪念物"),
            ("木作标牌", "木制标牌"),
            ("织物纪念品", "纺织纪念品"),
            ("入库建档", "入库登记"),
            ("交接包装", "交接与包装"),
        ]:
            text = text.replace(old, new)
    elif mode == "money_units":
        converted = BUDGET.replace("预算金额（元）", "预算金额（千元）")
        for old, new in [
            ("680", "0.680"),
            ("940", "0.940"),
            ("360", "0.360"),
            ("420", "0.420"),
            ("2400", "2.400"),
        ]:
            converted = converted.replace(old, new)
        text = text.replace(BUDGET, converted)
    elif mode == "merged_capacity_registration":
        merged = """| 类别 | 常规排期参考（工作日） | 单轮接收上限（件） | 本轮登记（件） | 进入排期（件） | 待确认（件） |
| --- | --- | --- | --- | --- | --- |
| 纸本纪念物 | 12 | 20 | 24 | 20 | 4 |
| 木作标牌 | 18 | 8 | 11 | 8 | 3 |
| 织物纪念品 | 15 | 10 | 9 | 9 | 0 |
| 合计 |  | 38 | 44 | 37 | 7 |"""
        text = merged + "\n\n" + BUDGET
    assert GRADER["evaluate_report"](inspect(text))[0]


@pytest.mark.parametrize(
    "mutation",
    [
        "blank",
        "numbers_in_prose",
        "missing_table",
        "wrong_category",
        "wrong_column",
        "old_total",
        "duplicate",
        "extra_charge",
        "stuffed_cell",
        "missing_pending",
    ],
)
def test_unbound_or_changed_data_cannot_earn_table_credit(mutation):
    text = TABLES
    if mutation == "blank":
        text = ""
    elif mutation == "numbers_in_prose":
        text = text.replace("|", " ").replace("---", "")
    elif mutation == "missing_table":
        text = CAPACITY + "\n\n" + BUDGET
    elif mutation == "wrong_category":
        text = text.replace("| 纸本纪念物 | 12 | 20 |", "| 木作标牌 | 12 | 20 |")
    elif mutation == "wrong_column":
        text = text.replace("| 木作标牌 | 11 | 8 | 3 |", "| 木作标牌 | 3 | 8 | 11 |")
    elif mutation == "old_total":
        text = text.replace("| 合计 | 44 | 37 | 7 |", "| 合计 | 44 | 44 | 0 |")
    elif mutation == "duplicate":
        text = text.replace(
            "| 木作标牌 | 11 | 8 | 3 |",
            "| 木作标牌 | 11 | 8 | 3 |\n| 木作标牌 | 11 | 8 | 3 |",
        )
    elif mutation == "extra_charge":
        text += "\n| 加急费 | 200 |"
    elif mutation == "stuffed_cell":
        text = text.replace(
            "| 木作标牌 | 11 | 8 | 3 |", "| 木作标牌 | 11、8、3 | 11、8、3 | 11、8、3 |"
        )
    elif mutation == "missing_pending":
        text = text.replace("| 织物纪念品 | 9 | 9 | 0 |", "| 织物纪念品 | 9 | 9 |  |")
    assert not GRADER["evaluate_report"](inspect(text))[0]


def test_expected_numeric_facts_are_in_initial_source_with_their_labels():
    source = (TASK / "environment/data/workshop-manuscript.txt").read_text(
        encoding="utf-8"
    )
    for row in [
        "纸本纪念物 | 12 | 20",
        "木作标牌 | 18 | 8",
        "织物纪念品 | 15 | 10",
        "纸本纪念物 | 24 | 20 | 4",
        "木作标牌 | 11 | 8 | 3",
        "织物纪念品 | 9 | 9 | 0",
        "合计 | 44 | 37 | 7",
        "入库建档 | 680",
        "交接包装 | 940",
        "公众说明会 | 360",
        "预备金 | 420",
        "合计 | 2400",
    ]:
        assert row in source
    assert "没有统一的逾期取件收费或处置期限" in source
    assert "暂缓期间不能在统计里继续说" in source


def runtime(tmp_path, text=TABLES):
    roots = {
        name: tmp_path / name
        for name in ("workdir", "inputs", "agent_logs", "verifier_logs", "artifacts")
    }
    for root in roots.values():
        root.mkdir()
    (roots["inputs"] / "workshop-manuscript.txt").write_bytes(
        (TASK / "environment/data/workshop-manuscript.txt").read_bytes()
    )
    (roots["workdir"] / "workshop-manuscript.txt").write_text(
        "Changed writable manuscript", encoding="utf-8"
    )
    output = roots["workdir"] / "output"
    output.mkdir()
    if text is not None:
        (output / "轮值 手册.md").write_text(text, encoding="utf-8")
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


def run(config, settings=JudgeSettings()):
    return asyncio.run(
        run_verifier(
            TASK / "tests/grader.json", runtime=config, judge_settings=settings
        )
    )


def test_public_configuration_and_real_judge_request_artifact_bindings(tmp_path):
    task = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert task.config.agent.timeout_sec == 900
    assert build_scoring_plan(
        json.loads((TASK / "tests/grader.json").read_text())
    ).custom_ids == ("key_table_bindings",)
    judge = load_judge_config(TASK / "tests/judge.yaml")
    assert (judge.rule_weight, judge.llm_weight) == (0.3, 0.7)
    roots, config = runtime(tmp_path)
    with judge_server() as server:
        result = run(config, JudgeSettings(True, server["url"], "local-fixture"))
        prompts = [
            unescape(request["messages"][-1]["content"])
            for request in server["requests"]
        ]
    assert result["reward"] == 1 and len(prompts) == 2
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    artifacts = {record["id"]: record for record in manifest["artifacts"]}
    assert artifacts["manuscript"]["source_artifact_id"] == "source_manuscript"
    assert artifacts["handbook"]["source_artifact_id"] == "handbook_file"
    assert artifacts["source_manuscript"]["source_path"].startswith(
        str(roots["inputs"])
    )
    excerpt = (roots["verifier_logs"] / artifacts["manuscript"]["text_path"]).read_text(
        encoding="utf-8"
    )
    assert "L1: 溪桐街区记忆工坊运营手册" in excerpt
    assert all(excerpt in prompt and TABLES in prompt for prompt in prompts)
    assert all("Changed writable manuscript" not in prompt for prompt in prompts)


def test_tables_without_actual_handbook_only_earn_small_objective_share(tmp_path):
    _, config = runtime(tmp_path)
    with judge_server() as server:
        for rubric in ("faithful_edit", "usable_structure"):
            server["behavior"][rubric] = {"passed": False}
        result = run(config, JudgeSettings(True, server["url"], "local-fixture"))
    assert result["reward"] == pytest.approx(0.3)


@pytest.mark.parametrize("delivery", ["missing", "blank", "corrupt", "ambiguous"])
def test_unavailable_or_ambiguous_document_has_zero_score_and_no_judge_call(
    tmp_path, delivery
):
    roots, config = runtime(
        tmp_path,
        None if delivery == "missing" else "" if delivery == "blank" else TABLES,
    )
    output = roots["workdir"] / "output"
    if delivery == "corrupt":
        (output / "轮值 手册.md").write_bytes(b"\xff")
    elif delivery == "ambiguous":
        (output / "另一版.md").write_text(TABLES + "\n其他内容", encoding="utf-8")
    with judge_server() as server:
        result = run(config, JudgeSettings(True, server["url"], "local-fixture"))
        assert not server["requests"]
    assert result["reward"] == 0


def test_missing_input_snapshot_cannot_use_mutable_source(tmp_path):
    _, config = runtime(tmp_path)
    config = replace(config, paths=replace(config.paths, inputs=None))
    with pytest.raises(RuntimeError, match="custom verifier exited"):
        run(config)


def test_grading_and_published_document_use_the_same_snapshot(tmp_path, monkeypatch):
    roots, config = runtime(tmp_path)
    output = roots["workdir"] / "output/轮值 手册.md"
    original_read = SourceSnapshot.read

    def read_then_change(path, **kwargs):
        snapshot = original_read(path, **kwargs)
        if Path(path) == output:
            output.write_text("Changed after reading", encoding="utf-8")
        return snapshot

    monkeypatch.setattr(SourceSnapshot, "read", read_then_change)
    checks = GRADER["evaluate"]({key: str(value) for key, value in roots.items()})
    assert checks[0]["passed"]
    evidence = (roots["verifier_logs"] / "artifact_text/handbook.md").read_text(
        encoding="utf-8"
    )
    assert evidence == TABLES and "Changed after reading" not in evidence
