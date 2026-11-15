"""Festival map validity and source-grounded Judge request boundaries."""

import asyncio
import json
import runpy
from dataclasses import replace
from html import unescape
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

TASK = (
    Path(__file__).resolve().parents[2]
    / "datasets/pbench-v1.0/festival-contingency-map-01"
)
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
VALID = """# 南梧夜间文化节应变
- 庭院降雨与节目收缩
  - 场地方确认庭院停用后，统筹停户外节目，长廊分批最多60人；未入场观众由信息岗通知等待或退场选择。
  - 动线岗和2名志愿者管理批次，保留故事小组；容量不够就减手作批次，不加借场地。
- 乐队缺席与安静时段
  - 节目岗开场前确认到场，失联则优先保留故事和手作，与带领人确认可承担的批次，不能一人兼所有节目。
  - 20:45前结束扩音；不能补足乐队时由统筹确认缩短节目，21:30结束不顺延。
- 到访与信息中断
  - 集中到访时动线岗先分流到访批次，志愿者保留无台阶路线并给亲子家庭清楚等候安排。
  - 信息岗在网络查询延迟时切纸质名单，更新提示牌；节目岗只把已确认变更交信息岗统一口径。
  - 先用现有提示牌和充电电源，1800元留作必要小额补给；志愿者按批次调配，统筹处理岗位冲突。
"""


def structure(text):
    report = inspect_document(
        SourceSnapshot(Path("answer.md"), text.encode()), format="md"
    )
    return GRADER["hierarchy"](report)


@pytest.mark.parametrize(
    "text",
    [
        VALID,
        "# 应变\n## 场地\n- 转场批次\n## 节目\n- 替代节目\n## 信息\n- 统一通知",
        "应变\n====\n\n场地\n----\n- 转场批次\n\n节目\n----\n- 替代节目\n\n信息\n----\n- 统一通知",
        "**应变**\n- 场地\n  - 转场批次\n- 节目\n  - 替代节目\n- 信息\n  - 统一通知",
        "- 应变\n  - 场地\n    - 转场批次\n  - 节目\n    - 替代节目\n  - 信息\n    - 统一通知",
        "# 应变\n1. 场地\n   1. 转场批次\n2. 节目\n   1. 替代节目\n3. 信息\n   1. 统一通知",
        "```mermaid\nmindmap\n  root((夜间文化节应变))\n    场地\n      转场批次\n    节目\n      替代节目\n    信息\n      统一通知\n```",
        "```mermaid\n%% planning\nmindmap\n\t夜间文化节应变\n\t\t场地\n\t\t\t转场批次\n\t\t节目\n\t\t\t替代节目\n\t\t信息\n\t\t\t统一通知\n```",
    ],
)
def test_real_hierarchy_accepts_natural_formats_without_line_threshold(text):
    assert len(text.splitlines()) < 31
    passed, observed = structure(text)
    assert passed and observed["main_branches"] >= 3


@pytest.mark.parametrize("heading", ["## 假设说明", "# 执行前提", "## 补充边界"])
@pytest.mark.parametrize(
    "outline",
    [VALID, "# 应变\n## 场地\n- 转场批次\n## 节目\n- 替代节目\n## 信息\n- 统一通知\n"],
)
def test_complete_markdown_map_can_have_a_separate_trailing_prose_section(
    heading, outline
):
    text = (
        outline + f"\n{heading}\n这里只做运营分工，专业判断由场地方按既有程序处理。\n"
    )
    passed, observed = structure(text)
    assert passed and observed["main_branches"] == 3


@pytest.mark.parametrize("suffix", ["\n- 假设说明\n", "\n## 补充边界\n"])
def test_unexpanded_outline_nodes_are_not_discarded_as_explanatory_prose(suffix):
    assert not structure(VALID + suffix)[0]


def test_trailing_prose_does_not_complete_an_incomplete_map():
    text = "# 应变\n- 场地\n  - 转场\n- 节目\n  - 替代\n## 信息\n统一现场确认口径。"
    assert not structure(text)[0]


@pytest.mark.parametrize(
    "text",
    [
        "",
        "# 应变\n- 雨天\n- 乐队\n- 排队\n- 网络",
        "# 应变\n- 场地\n  - 转场\n- 节目\n  - 替代",
        "# 应变\n- 场地\n  - 转场\n- 场地\n  - 再转场\n- 节目\n  - 替代",
        "# 应变\n- 场地\n  - 转场\n- 节目\n  - 替代\n- 信息",
        "# 应变一\n## 场地\n- 转场\n# 应变二\n## 节目\n- 替代\n## 信息\n- 通知",
        "雨天要处理，乐队要处理，排队要处理，网络要处理。",
        "```text\n# 应变\n- 场地\n  - 转场\n- 节目\n  - 替代\n- 信息\n  - 通知\n```",
        '{"root":"应变","branches":["场地","节目","信息"]}',
        "```mermaid\nmindmap\n root((应变))\n   场地\n   节目\n   信息\n```",
    ],
)
def test_blank_flat_duplicate_or_unexpanded_content_fails_minimum_structure(text):
    assert not structure(text)[0]


def runtime(tmp_path, text):
    roots = {
        name: tmp_path / name
        for name in ("workdir", "inputs", "agent_logs", "verifier_logs", "artifacts")
    }
    for root in roots.values():
        root.mkdir()
    original = (TASK / "environment/data/event-brief.md").read_bytes()
    (roots["inputs"] / "event-brief.md").write_bytes(original)
    (roots["workdir"] / "event-brief.md").write_text(
        "Wrong mutable workspace source", encoding="utf-8"
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


def run(config, settings=JudgeSettings()):
    return asyncio.run(
        run_verifier(
            TASK / "tests/grader.json", runtime=config, judge_settings=settings
        )
    )


def test_config_and_bound_evidence_reach_actual_judge_requests(tmp_path):
    loaded = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert loaded.config.agent.timeout_sec == 900
    assert build_scoring_plan(
        json.loads((TASK / "tests/grader.json").read_text())
    ).custom_ids == ("minimum_hierarchy",)
    judge = load_judge_config(TASK / "tests/judge.yaml")
    assert (judge.rule_weight, judge.llm_weight) == (0.2, 0.8)
    answer = VALID + "\n## 执行前提\n专业判断由场地方按现有程序处理。\n"
    roots, config = runtime(tmp_path, answer)
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
    assert artifacts["event_brief"]["source_artifact_id"] == "source_brief"
    assert artifacts["source_brief"]["source_path"].startswith(str(roots["inputs"]))
    excerpt = (
        roots["verifier_logs"] / artifacts["event_brief"]["text_path"]
    ).read_text(encoding="utf-8")
    assert "L1: # 南梧造物园" in excerpt
    assert all(excerpt in prompt and answer in prompt for prompt in prompts)
    assert all("Wrong mutable workspace source" not in prompt for prompt in prompts)


def test_keyword_scaffold_can_only_earn_small_structure_share_when_judge_rejects(
    tmp_path,
):
    scaffold = "# 应变\n- 场地\n  - 雨\n- 节目\n  - 缺席\n- 信息\n  - 网络"
    assert structure(scaffold)[0]
    _, config = runtime(tmp_path, scaffold)
    with judge_server() as server:
        for rubric in ("meaningful_branches", "executable_choices"):
            server["behavior"][rubric] = {"passed": False}
        result = run(config, JudgeSettings(True, server["url"], "local-fixture"))
    assert result["reward"] == pytest.approx(0.2)


def test_blank_has_zero_score_without_a_judge_request(tmp_path):
    _, config = runtime(tmp_path, "")
    with judge_server() as server:
        result = run(config, JudgeSettings(True, server["url"], "local-fixture"))
        assert not server["requests"]
    assert result["reward"] == 0


def test_missing_snapshot_does_not_fall_back_to_workspace(tmp_path):
    _, config = runtime(tmp_path, VALID)
    config = replace(config, paths=replace(config.paths, inputs=None))
    with pytest.raises(RuntimeError, match="custom verifier exited"):
        run(config)


def test_oversized_final_content_is_invalid_delivery_not_a_verifier_error(tmp_path):
    _, config = runtime(tmp_path, "超" * (1024 * 1024))
    assert run(config)["reward"] == 0
