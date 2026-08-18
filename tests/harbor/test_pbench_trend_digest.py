from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from types import ModuleType

import pytest
from harbor.models.task.config import VerifierEnvironmentMode
from harbor.models.task.task import Task

from tests.fixtures import trend_digest as trend_fixtures

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_TASK_ROOT = _REPOSITORY_ROOT / "datasets" / "pbench-v1.0" / "trend-digest-01"
_NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
_WEIGHTED_DIMENSIONS = ("source_evidence", "freshness", "coverage", "format")


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


@pytest.fixture(scope="module")
def x_fetch() -> Iterator[ModuleType]:
    name = "pbench_trend_x_fetch"
    module = _load_module(
        name,
        _TASK_ROOT / "environment" / "skills" / "x-daily" / "scripts" / "fetch.py",
    )
    yield module
    sys.modules.pop(name, None)


@pytest.fixture(scope="module")
def hn_fetch() -> Iterator[ModuleType]:
    name = "pbench_trend_hn_fetch"
    module = _load_module(
        name,
        _TASK_ROOT
        / "environment"
        / "skills"
        / "hackernews-daily"
        / "scripts"
        / "fetch.py",
    )
    yield module
    sys.modules.pop(name, None)


@pytest.fixture(scope="module")
def verifier() -> Iterator[ModuleType]:
    name = "pbench_trend_verifier"
    module = _load_module(name, _TASK_ROOT / "tests" / "verify.py")
    yield module
    sys.modules.pop(name, None)


def _rss(handle: str, posts: list[tuple[str, datetime, str]]) -> str:
    items = []
    for post_id, published, text in posts:
        items.append(
            "<item>"
            f"<guid>https://nitter.example/{handle}/status/{post_id}</guid>"
            f"<link>https://nitter.example/{handle}/status/{post_id}</link>"
            f"<description><![CDATA[{text}]]></description>"
            f"<pubDate>{format_datetime(published)}</pubDate>"
            "</item>"
        )
    return "<rss><channel>" + "".join(items) + "</channel></rss>"


def test_trend_digest_task_contract_and_workbook(x_fetch: ModuleType) -> None:
    task = Task(_TASK_ROOT)
    assert task.name == "pbench-v1.0/trend-digest-01"
    steps = task.config.steps or []
    assert task.config.multi_step_reward_strategy.value == "mean"
    assert [step.name for step in steps] == [
        "github",
        "x",
        "hacker-news",
    ]
    required_reward = {
        "source_evidence": 1.0,
        "freshness": 1.0,
        "format": 1.0,
        "final_answer": 1.0,
    }
    assert [step.min_reward for step in steps] == [
        required_reward,
        required_reward,
        None,
    ]
    assert [step.verifier.environment_mode for step in steps] == [
        VerifierEnvironmentMode.SHARED,
        VerifierEnvironmentMode.SHARED,
        VerifierEnvironmentMode.SHARED,
    ]
    assert task.config.environment.skills_dir == "/app/skills"
    assert all(
        not task.paths.step_solution_dir(step.name).exists()
        for step in task.config.steps or []
    )
    users = x_fetch.read_users_xlsx(
        _TASK_ROOT / "environment" / "input" / "x-users.xlsx"
    )
    assert [user["handle"] for user in users] == [
        "sama",
        "karpathy",
        "gdb",
        "JeffDean",
        "simonw",
        "_akhaliq",
        "ylecun",
        "kaboroeconomics",
        "fchollet",
        "aidan_mclau",
        "steipete",
    ]
    assert all(user["enabled"] is True for user in users)
    for platform_name, skill_name in (
        ("x", "x-daily"),
        ("hacker-news", "hackernews-daily"),
    ):
        config = json.loads(
            (_TASK_ROOT / "steps" / platform_name / "tests" / "grader.json").read_text(
                encoding="utf-8"
            )
        )
        branch = config["required_calls"][0]["any"][0]
        assert branch == {
            "tool_names": ["*exec*", "*terminal*", "*shell*", "bash"],
            "argument_terms": [skill_name],
        }


def test_trend_digest_instructions_disclose_the_graded_output_contract() -> None:
    expected = {
        "github": (
            "github-YYYYMMDDTHHMMSSZ.md",
            "platform",
            "generated_at",
            "source",
            "window",
        ),
        "x": (
            "x-YYYYMMDDTHHMMSSZ.md",
            "platform",
            "generated_at",
            "source",
            "window_start",
            "window_end",
        ),
        "hacker-news": (
            "hacker-news-YYYYMMDDTHHMMSSZ.md",
            "platform",
            "generated_at",
            "source",
            "snapshot_at",
        ),
    }

    for step, terms in expected.items():
        instruction = (_TASK_ROOT / "steps" / step / "instruction.md").read_text(
            encoding="utf-8"
        )
        assert len(instruction.strip().splitlines()) == 1
        assert all(term in instruction for term in terms)


def test_report_value_matching_accepts_sentence_punctuation_not_longer_urls(
    verifier: ModuleType,
) -> None:
    url = "https://github.com/example/repository"

    assert verifier.contains_value(f"Source: {url}.", url)
    assert verifier.contains_value(f"来源：{url}。", url)
    assert not verifier.contains_value(f"Source: {url}.suffix", url)


def test_x_skill_uses_fallback_and_rolling_window(
    tmp_path: Path, x_fetch: ModuleType
) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "sama-2.xml").write_text(
        _rss(
            "sama",
            [
                ("1", _NOW - timedelta(hours=24), "window start"),
                ("2", _NOW, "now <b>post</b>"),
                ("3", _NOW - timedelta(hours=24, seconds=1), "too old"),
                ("4", _NOW + timedelta(seconds=1), "future"),
            ],
        ),
        encoding="utf-8",
    )
    (fixtures / "karpathy-1.xml").write_text(_rss("karpathy", []), encoding="utf-8")
    output = tmp_path / "x.json"

    result = x_fetch.fetch(
        _TASK_ROOT / "environment" / "input" / "x-users.xlsx",
        output,
        now=_NOW,
        fixture_dir=fixtures,
    )

    accounts = {account["handle"]: account for account in result["accounts"]}
    assert result["successful_fetches"] == 2
    assert accounts["sama"]["status"] == "success"
    assert [post["id"] for post in accounts["sama"]["posts"]] == ["1", "2"]
    assert accounts["sama"]["posts"][1]["text"] == "now post"
    assert accounts["karpathy"]["status"] == "no_updates"
    assert accounts["gdb"]["status"] == "fetch_failed"
    assert json.loads(output.read_text(encoding="utf-8"))["window_start"] == (
        "2026-08-14T12:00:00Z"
    )


def test_x_skill_records_total_source_failure(
    tmp_path: Path, x_fetch: ModuleType
) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    result = x_fetch.fetch(
        _TASK_ROOT / "environment" / "input" / "x-users.xlsx",
        tmp_path / "x.json",
        now=_NOW,
        fixture_dir=fixtures,
    )
    assert result["successful_fetches"] == 0
    assert {account["status"] for account in result["accounts"]} == {"fetch_failed"}


def test_hackernews_skill_preserves_topstories_order(
    tmp_path: Path, hn_fetch: ModuleType
) -> None:
    fixtures = tmp_path / "hn"
    fixtures.mkdir()
    (fixtures / "topstories.json").write_text(
        json.dumps(list(range(1, 15))), encoding="utf-8"
    )
    (fixtures / "item-1.json").write_text(
        json.dumps({"id": 1, "type": "story", "deleted": True}),
        encoding="utf-8",
    )
    for story_id in range(2, 14):
        (fixtures / f"item-{story_id}.json").write_text(
            json.dumps(
                {
                    "id": story_id,
                    "type": "story",
                    "title": f"Story {story_id}",
                    "url": f"https://example.com/{story_id}",
                    "by": "fixture",
                    "score": 100 - story_id,
                    "descendants": story_id,
                    "time": 1_700_000_000 + story_id,
                }
            ),
            encoding="utf-8",
        )

    result = hn_fetch.fetch(
        tmp_path / "hacker-news.json",
        limit=12,
        now=_NOW,
        fixture_dir=fixtures,
    )

    assert [story["id"] for story in result["stories"]] == list(range(2, 14))
    assert [story["rank"] for story in result["stories"]] == list(range(1, 13))


def test_hackernews_skill_fails_without_topstories(
    tmp_path: Path, hn_fetch: ModuleType
) -> None:
    fixtures = tmp_path / "hn"
    fixtures.mkdir()
    with pytest.raises(RuntimeError, match="topstories"):
        hn_fetch.fetch(
            tmp_path / "hacker-news.json",
            limit=12,
            now=_NOW,
            fixture_dir=fixtures,
        )


def _write_trajectory(
    path: Path,
    *,
    arguments: dict,
    observation: str,
    function_name: str,
    final_answer: str,
    observation_extra: dict | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "ATIF-v1.7",
                "trajectory_id": "fixture",
                "agent": {"name": "fixture", "version": "1"},
                "steps": [
                    {"step_id": 1, "source": "user", "message": "collect"},
                    {
                        "step_id": 2,
                        "source": "agent",
                        "message": "",
                        "tool_calls": [
                            {
                                "tool_call_id": "call-1",
                                "function_name": function_name,
                                "arguments": arguments,
                            }
                        ],
                        "observation": {
                            "results": [
                                {
                                    "source_call_id": "call-1",
                                    "content": observation,
                                    "extra": {
                                        "is_error": False,
                                        **(observation_extra or {}),
                                    },
                                }
                            ]
                        },
                    },
                    {"step_id": 3, "source": "agent", "message": final_answer},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
def test_trend_verifier_accepts_complete_current_step(
    platform: str,
    tmp_path: Path,
    verifier: ModuleType,
) -> None:
    workspace = tmp_path / "app"
    shutil.copytree(_TASK_ROOT / "environment", workspace)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    logs = tmp_path / "agent"
    if platform == "github":
        arguments, observation, _ = trend_fixtures.github(artifacts, _NOW)
        function_name = "web_fetch"
    elif platform == "x":
        arguments, observation, _ = trend_fixtures.x(workspace, artifacts, _NOW)
        function_name = "exec_command"
    else:
        arguments, observation, _ = trend_fixtures.hacker_news(
            workspace, artifacts, _NOW
        )
        function_name = "exec_command"
    _write_trajectory(
        logs / "trajectory.json",
        arguments=arguments,
        observation=observation,
        function_name=function_name,
        final_answer=next(artifacts.iterdir()).name,
    )
    config = json.loads(
        (_TASK_ROOT / "steps" / platform / "tests" / "grader.json").read_text(
            encoding="utf-8"
        )
    )

    rewards, _details = verifier.grade(
        config,
        workspace=workspace,
        agent_logs=logs,
        artifacts_dir=artifacts,
        now=_NOW,
    )

    assert set(rewards.values()) == {1.0}


@pytest.mark.parametrize(
    ("platform", "skill_name"),
    [("x", "x-daily"), ("hacker-news", "hackernews-daily")],
)
def test_trend_verifier_requires_skill_name_in_shell_call_arguments(
    platform: str,
    skill_name: str,
    tmp_path: Path,
    verifier: ModuleType,
) -> None:
    workspace = tmp_path / "app"
    shutil.copytree(_TASK_ROOT / "environment", workspace)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    if platform == "x":
        _arguments, observation, _ = trend_fixtures.x(workspace, artifacts, _NOW)
    else:
        _arguments, observation, _ = trend_fixtures.hacker_news(
            workspace, artifacts, _NOW
        )
    logs = tmp_path / "agent"
    _write_trajectory(
        logs / "trajectory.json",
        arguments={"cmd": "python fetch.py"},
        observation=f"{skill_name} completed",
        function_name="agent_terminal",
        final_answer=next(artifacts.iterdir()).name,
    )
    config = json.loads(
        (_TASK_ROOT / "steps" / platform / "tests" / "grader.json").read_text()
    )

    rewards, details = verifier.grade(
        config,
        workspace=workspace,
        agent_logs=logs,
        artifacts_dir=artifacts,
        now=_NOW,
    )

    assert rewards["source_evidence"] == 0
    argument_check = next(
        check
        for check in details["checks"]
        if check["id"] == "required_call_1_arguments"
    )
    assert argument_check["passed"] is False


@pytest.mark.parametrize("platform", ["x", "hacker-news"])
def test_trend_verifier_rejects_nonzero_skill_execution(
    platform: str,
    tmp_path: Path,
    verifier: ModuleType,
) -> None:
    workspace = tmp_path / "app"
    shutil.copytree(_TASK_ROOT / "environment", workspace)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    if platform == "x":
        arguments, observation, _ = trend_fixtures.x(workspace, artifacts, _NOW)
    else:
        arguments, observation, _ = trend_fixtures.hacker_news(
            workspace, artifacts, _NOW
        )
    logs = tmp_path / "agent"
    _write_trajectory(
        logs / "trajectory.json",
        arguments=arguments,
        observation=observation,
        observation_extra={"exit_code": 2},
        function_name="agent_shell",
        final_answer=next(artifacts.iterdir()).name,
    )
    config = json.loads(
        (_TASK_ROOT / "steps" / platform / "tests" / "grader.json").read_text()
    )

    rewards, details = verifier.grade(
        config,
        workspace=workspace,
        agent_logs=logs,
        artifacts_dir=artifacts,
        now=_NOW,
    )

    assert rewards["source_evidence"] == 0
    observation_check = next(
        check
        for check in details["checks"]
        if check["id"] == "required_call_1_observation"
    )
    assert observation_check["passed"] is False


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
def test_trend_verifier_requires_current_artifact_in_final_answer(
    platform: str,
    tmp_path: Path,
    verifier: ModuleType,
) -> None:
    workspace = tmp_path / "app"
    shutil.copytree(_TASK_ROOT / "environment", workspace)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    logs = tmp_path / "agent"
    if platform == "github":
        arguments, observation, _ = trend_fixtures.github(artifacts, _NOW)
        function_name = "web_fetch"
    elif platform == "x":
        arguments, observation, _ = trend_fixtures.x(workspace, artifacts, _NOW)
        function_name = "exec_command"
    else:
        arguments, observation, _ = trend_fixtures.hacker_news(
            workspace, artifacts, _NOW
        )
        function_name = "exec_command"
    _write_trajectory(
        logs / "trajectory.json",
        arguments=arguments,
        observation=observation,
        function_name=function_name,
        final_answer="前一步的报告是 previous-step.md",
    )
    config = json.loads(
        (_TASK_ROOT / "steps" / platform / "tests" / "grader.json").read_text(
            encoding="utf-8"
        )
    )

    rewards, details = verifier.grade(
        config,
        workspace=workspace,
        agent_logs=logs,
        artifacts_dir=artifacts,
        now=_NOW,
    )

    assert all(rewards[name] == 1 for name in _WEIGHTED_DIMENSIONS)
    assert rewards["final_answer"] == 0
    assert rewards["reward"] == 0
    final_check = next(
        check for check in details["checks"] if check["id"] == "final_answer"
    )
    assert final_check["passed"] is False


def test_x_partial_failure_reduces_coverage_without_losing_source_evidence(
    tmp_path: Path, verifier: ModuleType
) -> None:
    workspace = tmp_path / "app"
    shutil.copytree(_TASK_ROOT / "environment", workspace)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    arguments, observation, snapshot = trend_fixtures.x(workspace, artifacts, _NOW)
    snapshot["accounts"][0]["status"] = "fetch_failed"
    (workspace / ".trend-digest" / "x.json").write_text(
        json.dumps(snapshot), encoding="utf-8"
    )
    report = next(artifacts.iterdir())
    report.write_text(
        report.read_text(encoding="utf-8").replace(
            "- 状态：近 24 小时无新推文", "- 状态：抓取失败", 1
        ),
        encoding="utf-8",
    )
    logs = tmp_path / "agent"
    _write_trajectory(
        logs / "trajectory.json",
        arguments=arguments,
        observation=observation,
        function_name="exec_command",
        final_answer=next(artifacts.iterdir()).name,
    )
    config = json.loads(
        (_TASK_ROOT / "steps" / "x" / "tests" / "grader.json").read_text()
    )

    rewards, _details = verifier.grade(
        config,
        workspace=workspace,
        agent_logs=logs,
        artifacts_dir=artifacts,
        now=_NOW,
    )

    assert rewards["source_evidence"] == 1
    assert rewards["freshness"] == 1
    assert rewards["format"] == 1
    assert 0 < rewards["coverage"] < 1


def test_github_previous_step_evidence_is_not_accepted(
    tmp_path: Path, verifier: ModuleType
) -> None:
    workspace = tmp_path / "app"
    workspace.mkdir()
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    trend_fixtures.github(artifacts, _NOW)
    logs = tmp_path / "agent"
    _write_trajectory(
        logs / "trajectory.json",
        arguments={"cmd": "/app/skills/x-daily/scripts/fetch.py"},
        observation="GitHub was fetched in an earlier step",
        function_name="exec_command",
        final_answer=next(artifacts.iterdir()).name,
    )
    config = json.loads(
        (_TASK_ROOT / "steps" / "github" / "tests" / "grader.json").read_text()
    )

    rewards, _details = verifier.grade(
        config,
        workspace=workspace,
        agent_logs=logs,
        artifacts_dir=artifacts,
        now=_NOW,
    )

    assert rewards["source_evidence"] == 0
    assert rewards["coverage"] == 0


def test_github_filename_and_front_matter_must_match(
    tmp_path: Path, verifier: ModuleType
) -> None:
    workspace = tmp_path / "app"
    workspace.mkdir()
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    arguments, observation, _ = trend_fixtures.github(artifacts, _NOW)
    report = next(artifacts.iterdir())
    report.rename(artifacts / "github-wrong.md")
    logs = tmp_path / "agent"
    _write_trajectory(
        logs / "trajectory.json",
        arguments=arguments,
        observation=observation,
        function_name="web_fetch",
        final_answer=next(artifacts.iterdir()).name,
    )
    config = json.loads(
        (_TASK_ROOT / "steps" / "github" / "tests" / "grader.json").read_text()
    )

    rewards, _details = verifier.grade(
        config,
        workspace=workspace,
        agent_logs=logs,
        artifacts_dir=artifacts,
        now=_NOW,
    )

    assert rewards["format"] < 1


def test_github_stale_report_fails_freshness(
    tmp_path: Path, verifier: ModuleType
) -> None:
    workspace = tmp_path / "app"
    workspace.mkdir()
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    arguments, observation, _ = trend_fixtures.github(artifacts, _NOW)
    logs = tmp_path / "agent"
    _write_trajectory(
        logs / "trajectory.json",
        arguments=arguments,
        observation=observation,
        function_name="web_fetch",
        final_answer=next(artifacts.iterdir()).name,
    )
    config = json.loads(
        (_TASK_ROOT / "steps" / "github" / "tests" / "grader.json").read_text()
    )

    rewards, _details = verifier.grade(
        config,
        workspace=workspace,
        agent_logs=logs,
        artifacts_dir=artifacts,
        now=_NOW + timedelta(hours=2),
    )

    assert rewards["source_evidence"] == 1
    assert rewards["freshness"] == 0


def test_x_total_failure_fails_source_evidence(
    tmp_path: Path, verifier: ModuleType
) -> None:
    workspace = tmp_path / "app"
    shutil.copytree(_TASK_ROOT / "environment", workspace)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    arguments, observation, snapshot = trend_fixtures.x(workspace, artifacts, _NOW)
    for account in snapshot["accounts"]:
        account["status"] = "fetch_failed"
    (workspace / ".trend-digest" / "x.json").write_text(
        json.dumps(snapshot), encoding="utf-8"
    )
    report = next(artifacts.iterdir())
    report.write_text(
        report.read_text(encoding="utf-8").replace(
            "状态：近 24 小时无新推文", "状态：抓取失败"
        ),
        encoding="utf-8",
    )
    logs = tmp_path / "agent"
    _write_trajectory(
        logs / "trajectory.json",
        arguments=arguments,
        observation=observation,
        function_name="exec_command",
        final_answer=next(artifacts.iterdir()).name,
    )
    config = json.loads(
        (_TASK_ROOT / "steps" / "x" / "tests" / "grader.json").read_text()
    )

    rewards, _details = verifier.grade(
        config,
        workspace=workspace,
        agent_logs=logs,
        artifacts_dir=artifacts,
        now=_NOW,
    )

    assert rewards["source_evidence"] == 0


def test_hackernews_missing_story_reduces_coverage(
    tmp_path: Path, verifier: ModuleType
) -> None:
    workspace = tmp_path / "app"
    workspace.mkdir()
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    arguments, observation, _ = trend_fixtures.hacker_news(workspace, artifacts, _NOW)
    report = next(artifacts.iterdir())
    report.write_text(
        report.read_text(encoding="utf-8").replace(
            "https://example.com/story-1", "https://example.invalid/missing", 1
        ),
        encoding="utf-8",
    )
    logs = tmp_path / "agent"
    _write_trajectory(
        logs / "trajectory.json",
        arguments=arguments,
        observation=observation,
        function_name="exec_command",
        final_answer=next(artifacts.iterdir()).name,
    )
    config = json.loads(
        (_TASK_ROOT / "steps" / "hacker-news" / "tests" / "grader.json").read_text()
    )

    rewards, _details = verifier.grade(
        config,
        workspace=workspace,
        agent_logs=logs,
        artifacts_dir=artifacts,
        now=_NOW,
    )

    assert rewards["source_evidence"] == 1
    assert rewards["coverage"] == pytest.approx(11 / 12, abs=1e-6)
