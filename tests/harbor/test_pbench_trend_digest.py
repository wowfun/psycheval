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
    evidence = Path(runtime.paths.verifier_logs) / "judge-evidence"
    assert (evidence / "report.md").read_bytes() == report.read_bytes()
    assert (evidence / "sources.md").stat().st_size > 0


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
    assert not (
        Path(runtime.paths.verifier_logs) / "judge-evidence/sources.md"
    ).exists()


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
    reward = json.loads((logs / "reward.json").read_text())
    checks = json.loads((logs / "checks.json").read_text())
    assert (
        reward["reward"]
        == reward["rule_score"]
        == (len(checks["checks"]) - 1) / len(checks["checks"])
    )
    assert reward["final_answer"] == 0
    assert checks["judge"]["status"] == "disabled"
    assert (logs / "judge-evidence/report.md").read_bytes() == report.read_bytes()


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
    assert not (
        Path(runtime.paths.verifier_logs) / "judge-evidence/sources.md"
    ).exists()


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
        Path(runtime.paths.verifier_logs) / "judge-evidence/report.md"
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
