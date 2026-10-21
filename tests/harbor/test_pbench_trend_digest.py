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
from harbor.models.trajectories import Trajectory

from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    VerifierInvocation,
    write_effective_runtime_config,
)
from psycheval.harbor.verifier import aggregate, build_scoring_plan, evaluate
from psycheval.harbor.verifier.__main__ import main as verifier_main
from tests.fixtures import trend_digest as trend_fixtures

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_TASK_ROOT = _REPOSITORY_ROOT / "datasets" / "pbench-v1.0" / "trend-digest-01"
_NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    finally:
        sys.dont_write_bytecode = previous_bytecode
    return module


@pytest.fixture(scope="module")
def x_fetch() -> Iterator[ModuleType]:
    name = "pbench_trend_x_fetch"
    module = _load_module(
        name,
        _TASK_ROOT
        / "environment"
        / "data"
        / "skills"
        / "x-daily"
        / "scripts"
        / "fetch.py",
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
        / "data"
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
    module = _load_module(name, _TASK_ROOT / "tests" / "test_outputs.py")
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
        "required_tool": 1.0,
        "required_arguments": 1.0,
        "required_observation": 1.0,
        "required_artifacts": 1.0,
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
        _TASK_ROOT / "environment" / "data" / "input" / "x-users.xlsx"
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
    x_config = json.loads((_TASK_ROOT / "steps/x/tests/grader.json").read_text())
    for prefix in ("x_fetched_", "x_status_", "x_posts_"):
        assert {
            key.removeprefix(prefix)
            for key in x_config["custom_checks"]
            if key.startswith(prefix)
        } == {user["handle"].casefold() for user in users}
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
            "tool_names": ["*exec*", "*terminal*", "*shell*", "bash", "Bash"],
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
        assert "证据" in instruction and "中文摘要" in instruction
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
        _TASK_ROOT / "environment" / "data" / "input" / "x-users.xlsx",
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
        _TASK_ROOT / "environment" / "data" / "input" / "x-users.xlsx",
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


def _case(tmp_path, platform):
    workspace = tmp_path / "app"
    shutil.copytree(_TASK_ROOT / "environment" / "data", workspace)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    logs = tmp_path / "agent"
    if platform == "github":
        arguments, observation, snapshot = trend_fixtures.github(artifacts, _NOW)
    elif platform == "x":
        arguments, observation, snapshot = trend_fixtures.x(workspace, artifacts, _NOW)
    else:
        arguments, observation, snapshot = trend_fixtures.hacker_news(
            workspace, artifacts, _NOW
        )
    report = next(artifacts.iterdir())
    _write_trajectory(
        logs / "trajectory.json",
        arguments=arguments,
        observation=observation,
        function_name="web_fetch" if platform == "github" else "exec_command",
        final_answer=report.name,
    )
    verifier_logs = tmp_path / "verifier"
    verifier_logs.mkdir()
    runtime = EffectiveRuntimeConfig(
        paths=RuntimePaths(
            str(workspace),
            str(_TASK_ROOT / "steps" / platform / "tests"),
            str(logs),
            str(verifier_logs),
            str(artifacts),
        ),
        verifier=VerifierInvocation("当前步骤中文指令", platform),
    )
    config = json.loads(
        (_TASK_ROOT / "steps" / platform / "tests/grader.json").read_text(
            encoding="utf-8"
        )
    )
    return runtime, config, report, snapshot


def _grade(verifier, runtime, config, *, now=_NOW):
    trajectory = Trajectory(
        **json.loads(
            (Path(runtime.paths.agent_logs) / "trajectory.json").read_text(
                encoding="utf-8"
            )
        )
    )
    checks = evaluate(trajectory, config, Path(runtime.paths.artifacts))
    checks += [
        {**check, "id": "custom:" + check["id"]}
        for check in verifier.check_outputs(runtime.to_dict(), config, now=now)
    ]
    return aggregate(checks, plan=build_scoring_plan(config)), {
        check["id"]: check for check in checks
    }


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
def test_trend_verifier_accepts_complete_current_step(platform, tmp_path, verifier):
    runtime, config, report, _ = _case(tmp_path, platform)
    rewards, checks = _grade(verifier, runtime, config)
    assert set(rewards.values()) == {1.0}
    assert len(checks) == len(config["custom_checks"]) + 5
    evidence = Path(runtime.paths.verifier_logs) / "artifact_text"
    assert (evidence / "report.md").read_bytes() == report.read_bytes()
    assert (evidence / "sources.md").stat().st_size > 0
    manifest = json.loads(
        (evidence.parent / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    assert [
        (item["id"], item["type"], item["extract_status"])
        for item in manifest["artifacts"]
    ] == [
        ("report", "md", "ok"),
        ("sources", "md", "ok"),
    ]


def test_direct_trend_grading_clears_old_evidence(tmp_path, verifier):
    runtime, config, report, _ = _case(tmp_path, "github")
    verifier.check_outputs(runtime.to_dict(), config, now=_NOW)
    logs = Path(runtime.paths.verifier_logs)
    (logs / "keep.log").write_text("preserve")
    report.unlink()
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["steps"][1]["is_copied_context"] = True
    path.write_text(json.dumps(data), encoding="utf-8")
    verifier.check_outputs(runtime.to_dict(), config, now=_NOW)
    assert not (logs / "artifact_text/report.md").exists()
    assert not (logs / "artifact_text/sources.md").exists()
    assert (logs / "keep.log").read_text() == "preserve"
    records = json.loads((logs / "artifact_manifest.json").read_text())["artifacts"]
    assert {item["id"] for item in records} == {"report", "sources"}
    assert all(item["extract_status"] == "missing" for item in records)


@pytest.mark.parametrize("platform", ["github", "hacker-news"])
def test_report_text_is_normalized_once_for_repeated_coverage_checks(
    platform, tmp_path, verifier, monkeypatch
):
    runtime, config, report, _ = _case(tmp_path, platform)
    content = report.read_bytes().decode("utf-8")
    count = 0
    normalize = verifier.normalize

    def tracked(value):
        nonlocal count
        if value == content:
            count += 1
        return normalize(value)

    monkeypatch.setattr(verifier, "normalize", tracked)
    assert _grade(verifier, runtime, config)[0]["reward"] == 1
    assert count == 1


@pytest.mark.parametrize("platform", ["x", "hacker-news"])
@pytest.mark.parametrize("failure", ["arguments", "observation"])
def test_source_call_failures_fail_only_their_builtin_gates(
    platform, failure, tmp_path, verifier
):
    runtime, config, _, _ = _case(tmp_path, platform)
    trajectory_path = Path(runtime.paths.agent_logs) / "trajectory.json"
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    step = trajectory["steps"][1]
    if failure == "arguments":
        step["tool_calls"][0]["arguments"] = {"cmd": "python fetch.py"}
    else:
        step["observation"]["results"][0]["extra"]["exit_code"] = 2
    trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
    rewards, checks = _grade(verifier, runtime, config)
    assert rewards["required_" + failure] == 0
    assert checks["required_call_1_" + failure]["passed"] is False
    assert 0 < rewards["reward"] < 1


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
def test_final_answer_failure_preserves_other_rule_credit(platform, tmp_path, verifier):
    runtime, config, _, _ = _case(tmp_path, platform)
    trajectory_path = Path(runtime.paths.agent_logs) / "trajectory.json"
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    trajectory["steps"][-1]["message"] = "previous-step.md"
    trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
    rewards, checks = _grade(verifier, runtime, config)
    # Intentional contract: one failed item, no global multiplication by zero.
    assert rewards["final_answer"] == 0
    assert rewards["reward"] == (len(checks) - 1) / len(checks)
    assert all(item["passed"] for key, item in checks.items() if key != "final_answer")


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
@pytest.mark.parametrize("tool_name", ["bash", "Bash"])
def test_shell_tool_aliases_preserve_source_gates_and_evidence(
    platform, tool_name, tmp_path, verifier
):
    runtime, config, _, _ = _case(tmp_path, platform)
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    trajectory = json.loads(path.read_text(encoding="utf-8"))
    trajectory["steps"][1]["tool_calls"][0]["function_name"] = tool_name
    path.write_text(json.dumps(trajectory), encoding="utf-8")
    rewards, _ = _grade(verifier, runtime, config)
    assert rewards["reward"] == 1
    assert (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").is_file()


def test_github_previous_step_evidence_is_not_accepted(tmp_path, verifier):
    runtime, config, report, _ = _case(tmp_path, "github")
    _write_trajectory(
        Path(runtime.paths.agent_logs) / "trajectory.json",
        arguments={"cmd": "x-daily"},
        observation="GitHub was fetched in an earlier step",
        function_name="exec_command",
        final_answer=report.name,
    )
    rewards, checks = _grade(verifier, runtime, config)
    assert rewards["required_arguments"] == 0
    assert all(
        not item["passed"] for key, item in checks.items() if "repository_" in key
    )
    assert not (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").exists()


@pytest.mark.parametrize(
    "failure", ["filename", "naive_time", "stale", "missing", "extra"]
)
def test_report_format_and_freshness_have_fixed_partial_credit(
    tmp_path, verifier, failure
):
    runtime, config, report, _ = _case(tmp_path, "github")
    now = _NOW
    if failure == "filename":
        report.rename(report.with_name("github-wrong.md"))
    elif failure == "naive_time":
        report.write_text(
            report.read_text(encoding="utf-8").replace("12:00:00Z", "12:00:00"),
            encoding="utf-8",
        )
    elif failure == "stale":
        now += timedelta(hours=2)
    elif failure == "missing":
        report.unlink()
    else:
        report.with_name("extra.txt").write_text("extra")
    rewards, checks = _grade(verifier, runtime, config, now=now)
    target = {
        "filename": "report_filename",
        "naive_time": "report_timestamp",
        "stale": "report_current",
        "missing": "report_unique",
        "extra": "report_unique",
    }[failure]
    assert not checks["custom:" + target]["passed"]
    assert 0 < rewards["reward"] < 1
    assert len(checks) == 23
    if failure in {"filename", "naive_time", "stale"}:
        assert rewards["required_observation"] == 1


@pytest.mark.parametrize("total", [False, True])
def test_x_failures_preserve_fixed_watchlist_and_honest_status_credit(
    tmp_path, verifier, total
):
    runtime, config, report, snapshot = _case(tmp_path, "x")
    count = 11 if total else 1
    for account in snapshot["accounts"][:count]:
        account["status"] = "fetch_failed"
        account["source_instance"] = None
    (Path(runtime.paths.workdir) / ".trend-digest/x.json").write_text(
        json.dumps(snapshot), encoding="utf-8"
    )
    report.write_text(
        report.read_text(encoding="utf-8").replace(
            "状态：近 24 小时无新推文", "状态：抓取失败", count
        ),
        encoding="utf-8",
    )
    rewards, checks = _grade(verifier, runtime, config)
    assert checks["custom:x_status_sama"]["passed"]
    assert not checks["custom:x_fetched_sama"]["passed"]
    assert checks["custom:x_snapshot"]["passed"]
    assert rewards["reward"] == (len(checks) - count) / len(checks)
    assert len(checks) == 48
    # Actual total fetch outages return nonzero: the builtin observation gate stops the Trial.
    if total:
        trajectory_path = Path(runtime.paths.agent_logs) / "trajectory.json"
        trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
        trajectory["steps"][1]["observation"]["results"][0]["extra"]["exit_code"] = 1
        trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
        assert _grade(verifier, runtime, config)[0]["required_observation"] == 0


@pytest.mark.parametrize(
    "failure",
    [
        "missing_post",
        "outside_window",
        "wrong_window",
        "duplicate_account",
        "bad_status",
        "invalid_json",
    ],
)
def test_x_snapshot_validation_and_fixed_post_checks(tmp_path, verifier, failure):
    runtime, config, report, snapshot = _case(tmp_path, "x")
    account = snapshot["accounts"][0]
    if failure in {"missing_post", "outside_window"}:
        account["status"] = "success"
        account["posts"] = [
            {
                "id": "123",
                "url": "https://x.com/sama/status/123",
                "text": "A concrete source fact",
                "published_at": trend_fixtures.format_utc(
                    _NOW - timedelta(hours=25 if failure == "outside_window" else 1)
                ),
            }
        ]
        report.write_text(
            report.read_text(encoding="utf-8").replace("近 24 小时无新推文", "成功", 1),
            encoding="utf-8",
        )
    elif failure == "wrong_window":
        snapshot["window_start"] = trend_fixtures.format_utc(_NOW - timedelta(hours=12))
    elif failure == "duplicate_account":
        snapshot["accounts"].append(account)
    elif failure == "bad_status":
        account["status"] = {}
    path = Path(runtime.paths.workdir) / ".trend-digest/x.json"
    path.write_text(
        "not JSON" if failure == "invalid_json" else json.dumps(snapshot),
        encoding="utf-8",
    )
    rewards, checks = _grade(verifier, runtime, config)
    assert len(checks) == 48
    assert rewards["reward"] < 1
    if failure == "missing_post":
        assert not checks["custom:x_posts_sama"]["passed"]
        assert checks["custom:x_snapshot"]["passed"]
    elif failure == "wrong_window":
        assert not checks["custom:x_window"]["passed"]
    else:
        assert not checks["custom:x_snapshot"]["passed"]


@pytest.mark.parametrize("failure", ["missing_link", "wrong_order", "missing_snapshot"])
def test_hn_fixed_twelve_story_checks(tmp_path, verifier, failure):
    runtime, config, report, snapshot = _case(tmp_path, "hacker-news")
    snapshot_path = Path(runtime.paths.workdir) / ".trend-digest/hacker-news.json"
    if failure == "missing_link":
        report.write_text(
            report.read_text(encoding="utf-8").replace(
                "https://example.com/story-1", "https://example.invalid/missing", 1
            ),
            encoding="utf-8",
        )
    elif failure == "wrong_order":
        snapshot["stories"].reverse()
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    else:
        snapshot_path.unlink()
    rewards, checks = _grade(verifier, runtime, config)
    assert len(checks) == 27
    if failure == "missing_link":
        assert rewards["reward"] == 26 / 27
        assert not checks["custom:hn_story_01"]["passed"]
    else:
        assert not checks["custom:hn_snapshot"]["passed"]


def test_chinese_summary_does_not_require_a_literal_summary_label(tmp_path, verifier):
    runtime, config, report, _ = _case(tmp_path, "github")
    report.write_text(
        report.read_text(encoding="utf-8").replace("摘要：", "说明："), encoding="utf-8"
    )
    _, checks = _grade(verifier, runtime, config)
    assert checks["custom:report_chinese"]["passed"]


@pytest.mark.parametrize("source_format", ["html", "markdown"])
def test_github_repository_slots_use_relative_heading_links_not_navigation(
    tmp_path, verifier, source_format
):
    runtime, config, _, _ = _case(tmp_path, "github")
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    source = (
        "https://github.com/features/copilot\nhttps://github.com/solutions/use-case\n"
    )
    for index in range(1, 11):
        url = f"/fixture-org-{index}/fixture-repo-{index}"
        source += (
            f'<article><h2><a href="{url}">repository {index}</a></h2></article>\n'
            if source_format == "html"
            else f"## [repository {index}]({url})\n"
        )
    data["steps"][1]["observation"]["results"][0]["content"] = source
    path.write_text(json.dumps(data), encoding="utf-8")
    assert _grade(verifier, runtime, config)[0]["reward"] == 1


def _github_saved_page(tmp_path, *, source_format="jsonl"):
    runtime, config, _, snapshot = _case(tmp_path, "github")
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    fetch = data["steps"][1]
    fetch["tool_calls"][0].update(
        function_name="Bash",
        arguments={
            "command": f'curl -sSL "{trend_fixtures.GITHUB_URL}" -o /tmp/trending.html'
        },
    )
    fetch["observation"]["results"][0]["content"] = "623412 /tmp/trending.html"
    rows = [
        {"rank": rank, "name": name, "desc": f"Source description {rank}"}
        for rank, name in enumerate(snapshot["repositories"], 1)
    ]
    source = (
        json.dumps(rows)
        if source_format == "json"
        else "\n".join(json.dumps(row) for row in rows)
    )
    command = "cd /tmp && python - <<'PY'\nh=open('trending.html').read()\nparse(h)\nPY"
    read = {
        "step_id": 3,
        "source": "agent",
        "message": "",
        "tool_calls": [
            {
                "tool_call_id": "read-page",
                "function_name": "Bash",
                "arguments": {"command": command},
            }
        ],
        "observation": {
            "results": [
                {
                    "source_call_id": "read-page",
                    "content": f"Command: {command}\nStdout: {source}\n\nStderr: (empty)\nExit Code: 0",
                    "extra": {"exit_code": 0},
                }
            ]
        },
    }
    data["steps"].insert(2, read)
    data["steps"][-1]["step_id"] = 4
    return runtime, config, path, data, source


@pytest.mark.parametrize("source_format", ["json", "jsonl"])
def test_github_saved_page_parse_supplies_ranked_source_evidence(
    tmp_path, verifier, source_format
):
    runtime, config, path, data, source = _github_saved_page(
        tmp_path, source_format=source_format
    )
    path.write_text(json.dumps(data), encoding="utf-8")
    assert _grade(verifier, runtime, config)[0]["reward"] == 1
    evidence = (
        Path(runtime.paths.verifier_logs) / "artifact_text/sources.md"
    ).read_text(encoding="utf-8")
    assert source in evidence and "read-page" in evidence and "call-1" in evidence
    assert "parse(h)" not in evidence and "Stdout:" not in evidence


@pytest.mark.parametrize("field", ["name", "repo"])
def test_github_ranked_direct_fetch_accepts_repository_fields_and_later_details(
    tmp_path, verifier, field
):
    runtime, config, path, data, _ = _github_saved_page(tmp_path, source_format="json")
    source = json.dumps(
        [
            {"rank": rank, field: f"fixture-org-{rank}/fixture-repo-{rank}"}
            for rank in range(1, 11)
        ]
    )
    data["steps"][1]["tool_calls"][0]["arguments"] = {
        "code": f"fetch('{trend_fixtures.GITHUB_URL}')"
    }
    data["steps"][1]["tool_calls"][0]["function_name"] = "execute"
    data["steps"][1]["observation"]["results"][0]["content"] = source
    data["steps"][2]["tool_calls"][0].update(
        function_name="execute",
        arguments={"code": f"fetch('{trend_fixtures.GITHUB_URL}')"},
    )
    data["steps"][2]["observation"]["results"][0]["content"] = (
        "Later weekly page descriptions"
    )
    path.write_text(json.dumps(data), encoding="utf-8")
    assert _grade(verifier, runtime, config)[0]["reward"] == 1
    evidence = (
        Path(runtime.paths.verifier_logs) / "artifact_text/sources.md"
    ).read_text(encoding="utf-8")
    assert source in evidence and "Later weekly page descriptions" in evidence
    assert (
        verifier.github_repositories(
            json.dumps([{"rank": 1, "name": "org/first", "repo": "org/conflicting"}])
        )
        == []
    )


@pytest.mark.parametrize(
    "fetch_command,read_name,read_arguments",
    [
        (
            'curl --output="/tmp/trending.html"',
            "Read",
            {"file_path": "/tmp/trending.html"},
        ),
        ("wget -O /tmp/trending.html", "bash", {"command": "cat /tmp/trending.html"}),
        (
            'Invoke-WebRequest -OutFile "C:\\Temp\\trending.html"',
            "exec_command",
            {"command": 'Get-Content -LiteralPath "c:\\temp\\trending.html"'},
        ),
        (
            'cd /tmp && curl -o "trending.html"',
            "Bash",
            {
                "command": "cd /tmp && python -c \"print(Path('trending.html').read_text())\""
            },
        ),
    ],
)
def test_github_saved_page_supports_literal_shell_and_read_paths(
    tmp_path, verifier, fetch_command, read_name, read_arguments
):
    runtime, config, path, data, source = _github_saved_page(tmp_path)
    fetch, read = data["steps"][1:3]
    fetch["tool_calls"][0]["arguments"]["command"] = (
        fetch_command + f' "{trend_fixtures.GITHUB_URL}"'
    )
    read["tool_calls"][0].update(function_name=read_name, arguments=read_arguments)
    read["observation"]["results"][0]["content"] = source
    path.write_text(json.dumps(data), encoding="utf-8")
    assert _grade(verifier, runtime, config)[0]["reward"] == 1


def test_github_source_keeps_later_linked_descriptions(tmp_path, verifier):
    runtime, config, path, data, source = _github_saved_page(tmp_path)
    later = json.loads(json.dumps(data["steps"][2]))
    later["step_id"] = 4
    later["tool_calls"][0]["tool_call_id"] = "read-descriptions"
    result = later["observation"]["results"][0]
    result["source_call_id"] = "read-descriptions"
    result["content"] = "Additional extracted description from the same weekly page"
    data["steps"].insert(3, later)
    data["steps"][-1]["step_id"] = 5
    path.write_text(json.dumps(data), encoding="utf-8")
    assert _grade(verifier, runtime, config)[0]["reward"] == 1
    evidence = (
        Path(runtime.paths.verifier_logs) / "artifact_text/sources.md"
    ).read_text(encoding="utf-8")
    assert source in evidence and result["content"] in evidence
    assert "read-descriptions" in evidence


@pytest.mark.parametrize(
    "failure",
    [
        "fetch_failed",
        "read_failed",
        "unrelated_path",
        "copied_fetch",
        "copied_read",
        "before_fetch",
        "echo_only",
        "bad_rank",
        "duplicate_repo",
        "write_only",
        "wget_log",
    ],
)
def test_github_saved_page_requires_current_successful_linked_evidence(
    tmp_path, verifier, failure
):
    runtime, config, path, data, _ = _github_saved_page(tmp_path)
    fetch, read = data["steps"][1:3]
    observation = read["observation"]["results"][0]
    if failure == "fetch_failed":
        fetch["observation"]["results"][0]["extra"]["exit_code"] = 1
    elif failure == "read_failed":
        observation["extra"]["exit_code"] = 1
    elif failure == "unrelated_path":
        read["tool_calls"][0]["arguments"]["command"] = (
            "cd /other && python -c \"print(open('trending.html').read())\""
        )
    elif failure.startswith("copied_"):
        (fetch if failure == "copied_fetch" else read)["is_copied_context"] = True
    elif failure == "before_fetch":
        data["steps"][1:3] = [read, fetch]
        read["step_id"], fetch["step_id"] = 2, 3
    elif failure == "echo_only":
        observation["content"] = (
            observation["content"]
            .replace("Stdout:", "# command only\n")
            .split("\n\nStderr:")[0]
            + "\nStdout: done\n\nStderr: (empty)"
        )
    elif failure == "bad_rank":
        observation["content"] = observation["content"].replace(
            '"rank": 2', '"rank": 1'
        )
    elif failure == "duplicate_repo":
        observation["content"] = observation["content"].replace(
            "fixture-org-2/fixture-repo-2", "fixture-org-1/fixture-repo-1"
        )
    elif failure == "write_only":
        read["tool_calls"][0]["arguments"]["command"] = (
            "cd /tmp && python -c \"open('trending.html', 'w').write('invented')\""
        )
    elif failure == "wget_log":
        fetch["tool_calls"][0]["arguments"]["command"] = (
            f"wget -o /tmp/trending.html {trend_fixtures.GITHUB_URL}"
        )
    path.write_text(json.dumps(data), encoding="utf-8")
    checks = _grade(verifier, runtime, config)[1]
    assert not any(
        checks[f"custom:github_repository_{rank:02}"]["passed"] for rank in range(1, 11)
    )
    assert not (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").exists()


@pytest.mark.parametrize("same_variable", [True, False])
def test_github_powershell_download_and_node_symbolic_path(
    tmp_path, verifier, monkeypatch, same_variable
):
    runtime, config, path, data, _ = _github_saved_page(tmp_path)
    monkeypatch.setenv("TEMP", "verifier-environment-must-not-be-used")
    fetch, read = data["steps"][1:3]
    fetch["tool_calls"][0]["arguments"] = {
        "command": f'$r = Invoke-WebRequest "{trend_fixtures.GITHUB_URL}"; '
        '$r.Content | Out-File -Encoding utf8 "$env:TEMP\\trending.html"'
    }
    variable = "TEMP" if same_variable else "OTHER_TEMP"
    read["tool_calls"][0]["arguments"] = {
        "command": "const html = fs.readFileSync(process.env."
        + variable
        + "+'\\\\trending.html', 'utf8'); parse(html);"
    }
    rows = [
        {
            "rank": rank,
            "path": f"/fixture-org-{rank}/fixture-repo-{rank}",
            "name": f"fixture-org-{rank} / fixture-repo-{rank}",
            "desc": f"Source description {rank}",
        }
        for rank in range(1, 11)
    ]
    read["observation"]["results"][0]["content"] = (
        "article tags: 10\nBox-row article: 10\n"
        + "\n".join(json.dumps(row) for row in rows)
    )
    path.write_text(json.dumps(data), encoding="utf-8")
    checks = _grade(verifier, runtime, config)[1]
    assert checks["custom:github_repository_10"]["passed"] is same_variable
    if same_variable:
        evidence = (
            Path(runtime.paths.verifier_logs) / "artifact_text/sources.md"
        ).read_text(encoding="utf-8")
        assert "article tags: 10" in evidence and "Source description 10" in evidence


@pytest.mark.parametrize("kind", ["github", "raw", "unrelated", "failed"])
def test_github_sources_include_only_selected_repository_support(
    tmp_path, verifier, kind
):
    runtime, config, path, data, _ = _github_saved_page(tmp_path)
    repo = "fixture-org-1/fixture-repo-1" + (
        "-unrelated" if kind == "unrelated" else ""
    )
    url = (
        f"https://raw.githubusercontent.com/{repo}/main/README.md"
        if kind == "raw"
        else f"https://github.com/{repo}"
    )
    fetch = json.loads(json.dumps(data["steps"][2]))
    fetch["step_id"] = 4
    fetch["tool_calls"][0].update(
        tool_call_id="repo-fetch",
        arguments={"command": f'curl "{url}" -o /tmp/repo.html'},
    )
    fetch["observation"]["results"][0].update(
        source_call_id="repo-fetch",
        content="200 bytes saved",
        extra={"exit_code": 1 if kind == "failed" else 0},
    )
    read = json.loads(json.dumps(fetch))
    read["step_id"] = 5
    read["tool_calls"][0].update(
        tool_call_id="repo-read",
        function_name="Read",
        arguments={"file_path": "/tmp/repo.html"},
    )
    read["observation"]["results"][0].update(
        source_call_id="repo-read",
        content="README supporting facts <&>",
        extra={"exit_code": 0},
    )
    data["steps"][3:3] = [fetch, read]
    data["steps"][-1]["step_id"] = 6
    path.write_text(json.dumps(data), encoding="utf-8")
    assert _grade(verifier, runtime, config)[0]["reward"] == 1
    text = (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").read_text(
        encoding="utf-8"
    )
    assert ("README supporting facts <&>" in text) is (kind in {"github", "raw"})


def test_github_json_wrapped_urls_remain_source_evidence(verifier):
    urls = [f"https://github.com/owner/repo-{rank}" for rank in range(10)]
    assert (
        verifier.github_repositories(json.dumps({"content": "\n".join(urls)})) == urls
    )


def test_github_collection_does_not_copy_trajectory_per_call(
    tmp_path, verifier, monkeypatch
):
    from harbor.models.trajectories import Step, Trajectory

    runtime, config, path, data, _ = _github_saved_page(tmp_path)
    for index in range(200):
        data["steps"].insert(
            -1,
            {
                "step_id": index + 4,
                "source": "agent",
                "message": "",
                "tool_calls": [
                    {
                        "tool_call_id": f"noise-{index}",
                        "function_name": "Bash",
                        "arguments": {"command": "echo diagnostic"},
                    }
                ],
                "observation": {
                    "results": [
                        {
                            "source_call_id": f"noise-{index}",
                            "content": "diagnostic",
                            "extra": {"exit_code": 0},
                        }
                    ]
                },
            },
        )
    data["steps"][-1]["step_id"] = 204
    path.write_text(json.dumps(data), encoding="utf-8")
    counts = {"step": 0, "trajectory": 0}
    original_step, original_trajectory = Step.model_copy, Trajectory.model_copy

    def step_copy(self, **kwargs):
        counts["step"] += 1
        return original_step(self, **kwargs)

    def trajectory_copy(self, **kwargs):
        counts["trajectory"] += 1
        return original_trajectory(self, **kwargs)

    monkeypatch.setattr(Step, "model_copy", step_copy)
    monkeypatch.setattr(Trajectory, "model_copy", trajectory_copy)
    verifier.check_outputs(runtime.to_dict(), config, now=_NOW)
    assert counts["step"] == 0
    assert counts["trajectory"] <= 1


@pytest.mark.parametrize("incomplete", [False, True])
def test_github_linked_source_reaches_xml_judge_and_is_regenerated(
    tmp_path, monkeypatch, incomplete
):
    import asyncio
    from dataclasses import replace
    from html import escape

    from psycheval.harbor.verifier import JudgeSettings, run_verifier
    from tests.fixtures.judge_server import judge_server

    runtime, _, path, data, _ = _github_saved_page(tmp_path)
    path.write_text(json.dumps(data), encoding="utf-8")
    tests = tmp_path / "isolated tests"
    shutil.copytree(_TASK_ROOT / "tests", tests)
    shutil.copytree(_TASK_ROOT / "steps/github/tests", tests, dirs_exist_ok=True)
    runtime = replace(runtime, paths=replace(runtime.paths, tests=str(tests)))
    monkeypatch.setenv("PBENCH_TREND_NOW", _NOW.isoformat())
    with judge_server() as server:
        server["behavior"]["summary_faithfulness"] = (
            {"content": "invalid protocol"} if incomplete else {"passed": False}
        )
        settings = JudgeSettings(True, server["url"], "fixture")
        result = asyncio.run(
            run_verifier(
                tests / "grader.json", runtime=runtime, judge_settings=settings
            )
        )
        assert result["test_pass_rate"] == 1
        assert result["metadata"]["score_merge"]["applied"] is not incomplete
        assert result["reward"] == pytest.approx(1 if incomplete else 0.8 + 0.2 * 2 / 3)
        sources = Path(runtime.paths.verifier_logs) / "artifact_text/sources.md"
        text = sources.read_bytes().decode("utf-8")
        assert len(server["requests"]) == 3
        for request in server["requests"]:
            prompt = request["messages"][-1]["content"]
            assert "<artifact_faithful_text>" in prompt
            assert escape(text, quote=False) in prompt
            assert "read-page" in prompt and "Source description 10" in prompt

        data["steps"][2]["observation"]["results"][0]["extra"]["exit_code"] = 1
        path.write_text(json.dumps(data), encoding="utf-8")
        asyncio.run(
            run_verifier(
                tests / "grader.json", runtime=runtime, judge_settings=settings
            )
        )
        assert not sources.exists()
        assert (
            len(server["requests"]) == 3
        )  # Missing evidence is a local rubric failure.


def test_github_source_bodies_are_deduplicated_with_all_provenance(tmp_path, verifier):
    runtime, config, path, data, _ = _github_saved_page(tmp_path)
    repeated = json.loads(json.dumps(data["steps"][2]))
    repeated["step_id"] = 4
    repeated["tool_calls"][0]["tool_call_id"] = "read-again"
    repeated["observation"]["results"][0]["source_call_id"] = "read-again"
    data["steps"].insert(3, repeated)
    for index, step in enumerate(data["steps"], 1):
        step["step_id"] = index
    path.write_text(json.dumps(data), encoding="utf-8")
    verifier.check_outputs(runtime.to_dict(), config, now=_NOW)
    text = (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").read_text(
        encoding="utf-8"
    )
    assert text.count("Source description 10") == 1
    assert "Evidence call: read-page" in text and "Evidence call: read-again" in text


def test_oversized_github_sources_are_explicit_unavailable_evidence(
    tmp_path, monkeypatch
):
    import asyncio
    from dataclasses import replace

    from psycheval.harbor.verifier import JudgeSettings, run_verifier
    from tests.fixtures.judge_server import judge_server

    runtime, _, path, data, _ = _github_saved_page(tmp_path)
    observation = data["steps"][2]["observation"]["results"][0]
    observation["content"] = observation["content"].replace(
        "\n\nStderr:", "\n" + "x" * (1024 * 1024) + "\n\nStderr:"
    )
    path.write_text(json.dumps(data), encoding="utf-8")
    tests = tmp_path / "isolated tests"
    shutil.copytree(_TASK_ROOT / "tests", tests)
    shutil.copytree(_TASK_ROOT / "steps/github/tests", tests, dirs_exist_ok=True)
    runtime = replace(runtime, paths=replace(runtime.paths, tests=str(tests)))
    monkeypatch.setenv("PBENCH_TREND_NOW", _NOW.isoformat())
    with judge_server() as server:
        result = asyncio.run(
            run_verifier(
                tests / "grader.json",
                runtime=runtime,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
        )
        assert result["test_pass_rate"] == 1
        assert result["metadata"]["score_merge"]["applied"] is True
        assert result["reward"] == pytest.approx(0.8)
        assert server["requests"] == []
    logs = Path(runtime.paths.verifier_logs)
    manifest = json.loads((logs / "artifact_manifest.json").read_text(encoding="utf-8"))
    source = next(item for item in manifest["artifacts"] if item["id"] == "sources")
    assert source["extract_status"] == "error" and "budget" in source["reason"]
    assert not (logs / "artifact_text/sources.md").exists()
    assert (logs / "artifact_text/report.md").exists()


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
def test_trend_cli_publishes_current_step_partial_credit(
    tmp_path, monkeypatch, platform
):
    from dataclasses import replace

    runtime, config, report, _ = _case(tmp_path, platform)
    tests = tmp_path / "isolated tests"
    shutil.copytree(_TASK_ROOT / "tests", tests)
    shutil.copytree(
        _TASK_ROOT / "steps" / platform / "tests", tests, dirs_exist_ok=True
    )
    runtime = replace(runtime, paths=replace(runtime.paths, tests=str(tests)))
    # A delivery naming failure still retains independent rule credit through the real CLI.
    trajectory = Path(runtime.paths.agent_logs) / "trajectory.json"
    data = json.loads(trajectory.read_text(encoding="utf-8"))
    data["steps"][-1]["message"] = "wrong-file.md"
    trajectory.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv(
        "PEVAL_CONFIG",
        str(write_effective_runtime_config(tmp_path / "context.json", runtime)),
    )
    monkeypatch.setenv("PBENCH_TREND_NOW", _NOW.isoformat())
    monkeypatch.setenv("PEVAL_JUDGE_ENABLED", "false")
    assert verifier_main([str(tests / "grader.json")]) == 0
    logs = Path(runtime.paths.verifier_logs)
    reward = json.loads((logs / "reward.json").read_text(encoding="utf-8"))
    checks = json.loads((logs / "score.json").read_text(encoding="utf-8"))
    assert (
        reward["reward"]
        == reward["rule_score"]
        == (checks["tests_total"] - 1) / checks["tests_total"]
    )
    assert reward["final_answer"] == 0
    assert checks["judges"][1]["metadata"]["judge_status"] == "disabled"
    assert (logs / "artifact_text/report.md").read_bytes() == report.read_bytes()


@pytest.mark.parametrize("platform", ["x", "hacker-news"])
def test_fetch_cli_defaults_use_current_workspace(
    tmp_path, monkeypatch, x_fetch, hn_fetch, platform
):
    module = x_fetch if platform == "x" else hn_fetch
    received = []

    def fetch(*args, **kwargs):
        received.extend(args)
        return {"successful_fetches": 1, "stories": list(range(12))}

    monkeypatch.setattr(module, "fetch", fetch)
    monkeypatch.setattr(sys, "argv", ["fetch.py"])
    monkeypatch.chdir(tmp_path)
    assert module.main() == 0
    assert received[-1] == Path(f".trend-digest/{platform}.json")
    if platform == "x":
        assert received[0] == Path("input/x-users.xlsx")


def test_invalid_empty_x_window_is_not_judge_evidence(tmp_path, verifier):
    runtime, config, _, snapshot = _case(tmp_path, "x")
    snapshot["window_start"] = snapshot["window_end"]
    (Path(runtime.paths.workdir) / ".trend-digest/x.json").write_text(
        json.dumps(snapshot)
    )
    _, checks = _grade(verifier, runtime, config)
    assert not checks["custom:x_window"]["passed"]
    assert not (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").exists()


def test_chinese_front_matter_alone_is_not_a_summary(tmp_path, verifier):
    runtime, config, report, _ = _case(tmp_path, "github")
    report.write_text(
        "---\nsource: 这是足够长的中文元数据但没有摘要\n---\nEnglish only",
        encoding="utf-8",
    )
    _, checks = _grade(verifier, runtime, config)
    assert not checks["custom:report_chinese"]["passed"]


def test_utf8_bom_report_from_windows_keeps_front_matter_and_evidence(
    tmp_path, verifier
):
    runtime, config, report, _ = _case(tmp_path, "github")
    report.write_bytes(b"\xef\xbb\xbf" + report.read_bytes())
    assert _grade(verifier, runtime, config)[0]["reward"] == 1
    assert (
        Path(runtime.paths.verifier_logs) / "artifact_text/report.md"
    ).read_bytes() == report.read_bytes()


def test_preparation_excludes_caches_and_records_fixed_input_digest(
    tmp_path, monkeypatch
):
    import hashlib

    staged = tmp_path / "environment"
    shutil.copytree(
        _TASK_ROOT / "environment",
        staged,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    cache = staged / "data/skills/x-daily/scripts/__pycache__"
    cache.mkdir()
    (cache / "local.pyc").write_bytes(b"local interpreter cache")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    monkeypatch.setenv("PBENCH_TREND_NOW", _NOW.isoformat())
    before = {
        p.relative_to(staged): p.read_bytes() for p in staged.rglob("*") if p.is_file()
    }
    module = _load_module("trend_prepare_review", staged / "prepare.py")
    try:
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        module.prepare(str(workdir))
    finally:
        sys.dont_write_bytecode = previous
        sys.modules.pop("trend_prepare_review", None)
    metadata = json.loads(
        (workdir / ".trend-digest/preparation.json").read_text(encoding="utf-8")
    )
    assert datetime.fromisoformat(metadata["prepared_at"]) == _NOW
    assert not list(workdir.rglob("*.pyc"))
    assert not any("__pycache__" in name for name in metadata["sha256"])
    assert (
        metadata["sha256"]["input/x-users.xlsx"]
        == hashlib.sha256((workdir / "input/x-users.xlsx").read_bytes()).hexdigest()
    )
    assert before == {
        p.relative_to(staged): p.read_bytes() for p in staged.rglob("*") if p.is_file()
    }


def test_github_local_read_is_not_a_source_fetch(tmp_path, verifier):
    runtime, config, _, _ = _case(tmp_path, "github")
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["steps"][1]["tool_calls"][0]["function_name"] = "read"
    path.write_text(json.dumps(data), encoding="utf-8")
    rewards, _ = _grade(verifier, runtime, config)
    assert rewards["required_tool"] == 0
    assert rewards["required_observation"] == 0
