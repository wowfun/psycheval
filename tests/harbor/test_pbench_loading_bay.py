"""Frozen image identity, count binding, and text-only Judge evidence checks."""

import asyncio
import hashlib
import json
import runpy
import shutil
from collections import Counter
from html import escape
from pathlib import Path

import pytest
from harbor.models.trajectories import Trajectory

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

TASK = Path(__file__).resolve().parents[2] / "datasets/pbench-v1.0/loading-bay-count-01"
IMAGE = TASK / "environment/data/loading-bay.png"
PRIVATE = TASK / "tests/gt/visual-reference.json"
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
COUNTS = {"西侧暂存区": 7, "中央集货区": 5, "东侧月台边": 6}
GOOD = "可装车共18托：西侧暂存区7托，中央集货区5托，东侧月台边6托。排除裸空托盘和红色斜纹待检区中的货物，图例也未计入。"


def test_image_is_only_prepared_input_and_private_reference_matches_it():
    backend = pytest.importorskip("PIL.Image")
    assert [path.name for path in (TASK / "environment/data").iterdir()] == [IMAGE.name]
    with backend.open(IMAGE) as image:
        assert image.size == (1536, 1080) and image.mode == "RGB"
        assert not image.info  # No embedded textual answer or SVG source.
    image = SourceSnapshot.read(IMAGE)
    facts = GRADER["reference_facts"](SourceSnapshot.read(PRIVATE), image)
    assert facts["image_sha256"] == hashlib.sha256(IMAGE.read_bytes()).hexdigest()
    assert Counter(item["category"] for item in facts["objects"]) == {
        "ready": 18,
        "empty": 5,
        "quarantine": 4,
    }
    assert {
        region: sum(
            item["category"] == "ready" and item["region"] == region
            for item in facts["objects"]
        )
        for region in COUNTS
    } == COUNTS
    report = inspect_document(image)
    assert (report.width, report.height) == (1536, 1080)
    assert not hasattr(report, "object_count")


@pytest.mark.parametrize(
    "answer",
    [
        GOOD,
        "总数十八托。西侧暂存区七托；中央集货区五托；东侧月台边六托。",
        "西侧7、中央5、东侧6，合计18。",
        "**总计：18托**\n- 西侧暂存区：7\n- 中央集货区：5\n- 东侧月台边：6",
        "| 分区 | 可装车托数 |\n|---|---|\n| 西侧暂存区 | 7 |\n| 中央集货区 | 5 |\n| 东侧月台边 | 6 |\n| 合计 | 18 |",
        "| 西侧暂存区 | 中央集货区 | 东侧月台边 | 合计 |\n|---|---|---|---|\n|7|5|6|18|",
        "可装车货物18托。\n西侧暂存区：7（另有2托待检和1个空托盘）\n中央集货区：5（有1托待检和2个空托盘）\n东侧月台边：6（有1托待检和2个空托盘）",
        "7托（西侧暂存区），5托（中央集货区），6托（东侧月台边），18托",
        "总托数18托。西侧暂存区7托，中央集货区5托，东侧月台边6托。\n排除内容：\n- 待检货物共4托（西2、中1、东1）\n- 空托盘共5个（西1、中2、东2）\n- 图例不计。",
        "总托数18托。西侧暂存区7托，中央集货区5托，东侧月台边6托。\n排除待检区货物（西2托、中1托、东1托，共4托）；空托盘（西1个、中2个、东2个，共5个）。",
        "排除待检货物和空托盘后共18托。西侧暂存区7托，中央集货区5托，东侧月台边6托。",
    ],
)
def test_correct_counts_allow_prose_chinese_numbers_markdown_and_order(answer):
    assert [row["passed"] for row in GRADER["evaluate"](answer, COUNTS)] == [True, True]


@pytest.mark.parametrize(
    "answer",
    [
        "",
        "我已打开并看过图片。",
        "18,7,5,6",
        "共118托。",
        "共18.5托。",
        "共180托。",
        "不是18，而是19。",
        "总计18；西侧5，中央7，东侧6。",
        "共18，西侧7，西侧8，中央5，东侧6。",
        "共18，西侧7，中央5，东侧6；总计19。",
        "西侧7，中央5，东侧6；总共27托。",
    ],
)
def test_number_stuffing_wrong_binding_and_conflicting_claims_fail(answer):
    assert not any(row["passed"] for row in GRADER["evaluate"](answer, COUNTS))


def test_guessing_total_cannot_earn_region_credit_and_regions_are_distinct_credit():
    assert [row["passed"] for row in GRADER["evaluate"]("18", COUNTS)] == [True, False]
    assert [
        row["passed"] for row in GRADER["evaluate"]("西侧7，中央5，东侧6。", COUNTS)
    ] == [False, True]
    plan = build_scoring_plan(json.loads((TASK / "tests/grader.json").read_text()))
    assert [item.weight for item in plan.items] == [3, 4]


@pytest.mark.parametrize("mutation", ["hash", "category", "duplicate", "bounds"])
def test_broken_private_reference_is_verifier_error(mutation):
    facts = json.loads(PRIVATE.read_text(encoding="utf-8"))
    if mutation == "hash":
        facts["image_sha256"] = "0" * 64
    elif mutation == "category":
        facts["objects"][0]["category"] = "target"
    elif mutation == "duplicate":
        facts["objects"].append(facts["objects"][0])
    else:
        facts["objects"][0]["bbox"] = [0, 0, 10000, 10000]
    with pytest.raises(ValueError):
        GRADER["reference_facts"](
            SourceSnapshot(PRIVATE, json.dumps(facts).encode()),
            SourceSnapshot.read(IMAGE),
        )


@pytest.mark.parametrize(
    "answer,judge_pass,expected", [(GOOD, True, 1), ("18", False, 0.3)]
)
def test_real_verifier_publishes_hash_bound_reference_and_helper_answer_to_text_judge(
    tmp_path, answer, judge_pass, expected
):
    loaded = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert loaded.config.agent.timeout_sec == 900
    judge = load_judge_config(TASK / "tests/judge.yaml")
    assert (judge.rule_weight, judge.llm_weight) == (0.7, 0.3)
    assert judge.rubrics[0].artifact_refs == ("final_answer", "visual_reference")
    roots = {
        name: tmp_path / name
        for name in ("workdir", "inputs", "agent_logs", "verifier_logs", "artifacts")
    }
    for path in roots.values():
        path.mkdir()
    shutil.copyfile(IMAGE, roots["inputs"] / IMAGE.name)
    # Workdir mutation must not replace the retained initial image or reference.
    (roots["workdir"] / IMAGE.name).write_bytes(b"Agent changed its working copy")
    trajectory = Trajectory(
        schema_version="ATIF-v1.7",
        trajectory_id="counting",
        agent={"name": "fixture", "version": "1"},
        steps=[
            {"step_id": 1, "source": "user", "message": "USER_SENTINEL"},
            {"step_id": 2, "source": "agent", "message": "HISTORICAL_SENTINEL"},
            {"step_id": 3, "source": "agent", "message": answer},
            {"step_id": 4, "source": "agent", "message": ""},
        ],
    )
    (roots["agent_logs"] / "trajectory.json").write_text(
        trajectory.model_dump_json(), encoding="utf-8"
    )
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
        server["behavior"] = {"exclusion_explanation": {"passed": judge_pass}}
        result = asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=runtime,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
        )
        assert len(server["requests"]) == 1
        prompt = server["requests"][0]["messages"][-1]["content"]
    assert result["reward"] == pytest.approx(expected)
    assert result["metadata"]["score_merge"]["applied"]
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    records = {row["id"]: row for row in manifest["artifacts"]}
    assert records["visual_reference"]["source_artifact_id"] == "input_image"
    assert records["final_answer"]["source_artifact_id"] == "retained_trajectory"
    assert (
        roots["verifier_logs"] / records["input_image"]["verifier_raw_path"]
    ).read_bytes() == IMAGE.read_bytes()
    source_text = (
        roots["verifier_logs"] / records["visual_reference"]["text_path"]
    ).read_text(encoding="utf-8")
    assert "当前Judge仅支持文本" in source_text
    assert (
        escape(source_text, quote=False) in prompt
        and escape(answer, quote=False) in prompt
    )
    assert "HISTORICAL_SENTINEL" not in prompt and "USER_SENTINEL" not in prompt
    assert not any(
        "image_url" in message for message in server["requests"][0]["messages"]
    )
