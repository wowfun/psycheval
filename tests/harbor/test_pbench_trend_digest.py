from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest
from harbor.models.task.config import VerifierEnvironmentMode
from harbor.models.task.task import Task

from psycheval.harbor.runtime_config import write_effective_runtime_config
from psycheval.harbor.verifier import build_scoring_plan
from psycheval.harbor.verifier.__main__ import main as verifier_main
from tests.fixtures import trend_digest as trend_fixtures
from tests.harbor.trend_digest_support import (
    NOW,
    TASK_ROOT,
    grade,
    load_module,
    loaded_task_module,
    make_case,
    rss,
    score_without,
    write_trajectory,
)


@pytest.fixture(scope="module")
def x_fetch() -> Iterator[ModuleType]:
    with loaded_task_module(
        "pbench_trend_x_fetch",
        Path("environment/data/skills/x-daily/scripts/fetch.py"),
    ) as module:
        yield module


@pytest.fixture(scope="module")
def hn_fetch() -> Iterator[ModuleType]:
    with loaded_task_module(
        "pbench_trend_hn_fetch",
        Path("environment/data/skills/hackernews-daily/scripts/fetch.py"),
    ) as module:
        yield module


@pytest.fixture(scope="module")
def verifier() -> Iterator[ModuleType]:
    with loaded_task_module(
        "pbench_trend_verifier",
        Path("tests/test_outputs.py"),
    ) as module:
        yield module


def test_trend_digest_task_contract_and_workbook(x_fetch: ModuleType) -> None:
    task = Task(TASK_ROOT)
    assert task.name == "pbench-v1.0/trend-digest-01"
    steps = task.config.steps or []
    assert task.config.multi_step_reward_strategy.value == "mean"
    assert [step.name for step in steps] == [
        "github",
        "x",
        "hacker-news",
    ]
    assert [step.min_reward for step in steps] == [
        {"continuation": 1.0},
        {"continuation": 1.0},
        None,
    ]
    for step in steps[:2]:
        config = json.loads(
            (TASK_ROOT / "steps" / step.name / "tests/grader.json").read_text()
        )
        assert set(build_scoring_plan(config).continuation_checks) == {
            "required_call_1_tool",
            "required_call_1_arguments",
            "required_artifacts",
            "final_answer",
        } | ({"required_call_1_observation"} if step.name == "github" else set())
        assert config["scoring"]["weights"]["required_artifacts"] == 0
        assert config["scoring"]["weights"]["final_answer"] == 0
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
        TASK_ROOT / "environment" / "data" / "input" / "x-users.xlsx"
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
    x_config = json.loads((TASK_ROOT / "steps/x/tests/grader.json").read_text())
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
            (TASK_ROOT / "steps" / platform_name / "tests" / "grader.json").read_text(
                encoding="utf-8"
            )
        )
        branch = config["required_calls"][0]["any"][0]
        assert branch == {
            "tool_names": ["*exec*", "*terminal*", "*shell*", "bash", "pwsh"],
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
        instruction = (TASK_ROOT / "steps" / step / "instruction.md").read_text(
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
        rss(
            "sama",
            [
                ("1", NOW - timedelta(hours=24), "window start"),
                ("2", NOW, "now <b>post</b>"),
                ("3", NOW - timedelta(hours=24, seconds=1), "too old"),
                ("4", NOW + timedelta(seconds=1), "future"),
            ],
        ),
        encoding="utf-8",
    )
    (fixtures / "karpathy-1.xml").write_text(rss("karpathy", []), encoding="utf-8")
    output = tmp_path / "x.json"

    result = x_fetch.fetch(
        TASK_ROOT / "environment" / "data" / "input" / "x-users.xlsx",
        output,
        now=NOW,
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
        TASK_ROOT / "environment" / "data" / "input" / "x-users.xlsx",
        tmp_path / "x.json",
        now=NOW,
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
        now=NOW,
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
            now=NOW,
            fixture_dir=fixtures,
        )


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
@pytest.mark.parametrize("available", [False, True], ids=["unavailable", "available"])
def test_trend_schema_v2_optional_input_paths(tmp_path, verifier, platform, available):
    runtime, config, _, _ = make_case(tmp_path, platform)
    if available:
        roots = [tmp_path / name for name in ("inputs", "preparation_state")]
        for root in roots:
            root.mkdir()
        runtime = replace(
            runtime,
            paths=replace(
                runtime.paths, inputs=str(roots[0]), preparation_state=str(roots[1])
            ),
        )
    context = runtime.to_dict()
    assert context["schema_version"] == 2
    assert (context["paths"]["inputs"] is not None) is available
    assert (context["paths"]["preparation_state"] is not None) is available
    checks = verifier.check_outputs(context, config, now=NOW)
    assert checks and all(check["passed"] for check in checks)


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
def test_trend_verifier_accepts_complete_current_step(platform, tmp_path, verifier):
    runtime, config, report, _ = make_case(tmp_path, platform)
    rewards, checks = grade(verifier, runtime, config)
    assert set(rewards.values()) == {1.0}
    assert len(checks) == len(config["custom_checks"]) + 5
    evidence = Path(runtime.paths.verifier_logs) / "artifact_text"
    assert (evidence / "report.md").read_bytes() == report.read_bytes()
    assert (evidence / "sources.md").stat().st_size > 0
    manifest = json.loads(
        (evidence.parent / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    records = {item["id"]: item for item in manifest["artifacts"]}
    source_id = "retained_trajectory" if platform == "github" else "fetch_snapshot"
    expected = {"report_file", source_id, "report", "sources"}
    if platform == "hacker-news":
        expected |= {"retained_trajectory", "supporting_sources"}
    elif platform == "x":
        expected.add("successful_sources")
    assert set(records) == expected
    assert all(item["extract_status"] == "ok" for item in records.values())
    assert records["report"]["source_artifact_id"] == "report_file"
    assert records["sources"]["source_artifact_id"] == source_id
    if platform == "hacker-news":
        assert (
            records["supporting_sources"]["source_artifact_id"] == "retained_trajectory"
        )
        assert "No retained successful source observation" in (
            evidence / "supporting_sources.md"
        ).read_text(encoding="utf-8")
    assert (
        evidence.parent / records["report_file"]["verifier_raw_path"]
    ).read_bytes() == report.read_bytes()
    source = (
        Path(runtime.paths.agent_logs) / "trajectory.json"
        if platform == "github"
        else Path(runtime.paths.workdir) / f".trend-digest/{platform}.json"
    )
    assert (
        evidence.parent / records[source_id]["verifier_raw_path"]
    ).read_bytes() == source.read_bytes()


def test_direct_trend_grading_clears_old_evidence(tmp_path, verifier):
    runtime, config, report, _ = make_case(tmp_path, "github")
    verifier.check_outputs(runtime.to_dict(), config, now=NOW)
    logs = Path(runtime.paths.verifier_logs)
    (logs / "keep.log").write_text("preserve")
    report.unlink()
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["steps"][1]["is_copied_context"] = True
    path.write_text(json.dumps(data), encoding="utf-8")
    verifier.check_outputs(runtime.to_dict(), config, now=NOW)
    assert not (logs / "artifact_text/report.md").exists()
    assert not (logs / "artifact_text/sources.md").exists()
    assert (logs / "keep.log").read_text() == "preserve"
    records = json.loads((logs / "artifact_manifest.json").read_text())["artifacts"]
    assert {item["id"] for item in records} == {
        "retained_trajectory",
        "report",
        "sources",
    }
    assert all(
        item["extract_status"] == "missing" for item in records if item["type"] == "md"
    )


@pytest.mark.parametrize("platform", ["github", "hacker-news"])
def test_report_coverage_does_not_repeat_full_report_normalization(
    platform, tmp_path, verifier, monkeypatch
):
    runtime, config, report, _ = make_case(tmp_path, platform)
    content = report.read_bytes().decode("utf-8")
    count = 0
    normalize = verifier.normalize

    def tracked(value):
        nonlocal count
        if value == content:
            count += 1
        return normalize(value)

    monkeypatch.setattr(verifier, "normalize", tracked)
    assert grade(verifier, runtime, config)[0]["reward"] == 1
    assert count <= 1


@pytest.mark.parametrize("platform", ["x", "hacker-news"])
@pytest.mark.parametrize("failure", ["arguments", "observation"])
def test_source_call_failures_fail_only_their_builtin_gates(
    platform, failure, tmp_path, verifier
):
    runtime, config, _, _ = make_case(tmp_path, platform)
    trajectory_path = Path(runtime.paths.agent_logs) / "trajectory.json"
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    step = trajectory["steps"][1]
    if failure == "arguments":
        step["tool_calls"][0]["arguments"] = {"cmd": "python fetch.py"}
    else:
        step["observation"]["results"][0]["extra"]["exit_code"] = 2
    trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
    rewards, checks = grade(verifier, runtime, config)
    assert rewards["required_" + failure] == 0
    assert checks["required_call_1_" + failure]["passed"] is False
    assert 0 < rewards["reward"] < 1


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
def test_final_answer_failure_preserves_other_rule_credit(platform, tmp_path, verifier):
    runtime, config, _, _ = make_case(tmp_path, platform)
    trajectory_path = Path(runtime.paths.agent_logs) / "trajectory.json"
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    trajectory["steps"][-1]["message"] = "previous-step.md"
    trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
    rewards, checks = grade(verifier, runtime, config)
    assert checks["final_answer"]["passed"] is False
    if platform == "hacker-news":
        assert rewards["final_answer"] == 0
        assert "continuation" not in rewards
    else:
        assert rewards["final_answer"] == 1  # Zero-weight dimension, not a gate.
        assert rewards["continuation"] == 0
        assert rewards["reward"] == 1
    assert rewards["reward"] == pytest.approx(score_without(config, "final_answer"))
    assert all(item["passed"] for key, item in checks.items() if key != "final_answer")


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
@pytest.mark.parametrize("tool_name", ["bash", "Bash", "pwsh"])
def test_shell_tool_aliases_preserve_source_gates_and_evidence(
    platform, tool_name, tmp_path, verifier
):
    runtime, config, _, _ = make_case(tmp_path, platform)
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    trajectory = json.loads(path.read_text(encoding="utf-8"))
    trajectory["steps"][1]["tool_calls"][0]["function_name"] = tool_name
    path.write_text(json.dumps(trajectory), encoding="utf-8")
    rewards, _ = grade(verifier, runtime, config)
    assert rewards["reward"] == 1
    assert (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").is_file()


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
@pytest.mark.parametrize("failure", ["arguments", "observation"])
def test_pwsh_alias_still_requires_successful_source_evidence(
    platform, failure, tmp_path, verifier
):
    runtime, config, _, _ = make_case(tmp_path, platform)
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    trajectory = json.loads(path.read_text(encoding="utf-8"))
    step = trajectory["steps"][1]
    call = step["tool_calls"][0]
    call["function_name"] = "pwsh"
    if failure == "arguments":
        call["arguments"] = {"command": "Write-Output unrelated"}
    else:
        step["observation"]["results"][0]["extra"]["exit_code"] = 2
    path.write_text(json.dumps(trajectory), encoding="utf-8")
    rewards, _ = grade(verifier, runtime, config)
    assert rewards["required_" + failure] == 0
    assert rewards["final_answer"] == 1


def test_github_previous_step_evidence_is_not_accepted(tmp_path, verifier):
    runtime, config, report, _ = make_case(tmp_path, "github")
    write_trajectory(
        Path(runtime.paths.agent_logs) / "trajectory.json",
        arguments={"cmd": "x-daily"},
        observation="GitHub was fetched in an earlier step",
        function_name="exec_command",
        final_answer=report.name,
    )
    rewards, checks = grade(verifier, runtime, config)
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
    runtime, config, report, _ = make_case(tmp_path, "github")
    now = NOW
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
    rewards, checks = grade(verifier, runtime, config, now=now)
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
    runtime, config, report, snapshot = make_case(tmp_path, "x")
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
    rewards, checks = grade(verifier, runtime, config)
    assert checks["custom:x_status_sama"]["passed"]
    assert not checks["custom:x_fetched_sama"]["passed"]
    assert not checks["custom:x_posts_sama"]["passed"]
    assert checks["custom:x_snapshot"]["passed"]
    failures = [
        f"custom:{prefix}_{handle.casefold()}"
        for handle, _ in trend_fixtures.USERS[:count]
        for prefix in ("x_fetched", "x_posts")
    ]
    assert rewards["reward"] == pytest.approx(score_without(config, *failures))
    assert len(checks) == 48
    # Outages lose source credit. X deliberately leaves this check out of its
    # continuation gate so an honest report can proceed to the independent HN step.
    if total:
        trajectory_path = Path(runtime.paths.agent_logs) / "trajectory.json"
        trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
        trajectory["steps"][1]["observation"]["results"][0]["extra"]["exit_code"] = 1
        trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
        failed = grade(verifier, runtime, config)[0]
        assert failed["required_observation"] == 0
        assert failed["continuation"] == 1


@pytest.mark.parametrize("successful_accounts", [0, 1, 11])
def test_x_substantive_judge_requires_validated_successful_source(
    tmp_path, monkeypatch, successful_accounts
):
    import asyncio

    from psycheval.harbor.verifier import JudgeSettings, run_verifier
    from tests.fixtures.judge_server import judge_server

    runtime, config, report, snapshot = make_case(tmp_path, "x")
    failed = 11 - successful_accounts
    for account in snapshot["accounts"][:failed]:
        account.update(status="fetch_failed", source_instance=None)
    (Path(runtime.paths.workdir) / ".trend-digest/x.json").write_text(
        json.dumps(snapshot), encoding="utf-8"
    )
    report.write_text(
        report.read_text(encoding="utf-8").replace(
            "状态：近 24 小时无新推文", "状态：抓取失败", failed
        ),
        encoding="utf-8",
    )
    tests = tmp_path / "isolated tests"
    shutil.copytree(TASK_ROOT / "tests", tests)
    shutil.copytree(TASK_ROOT / "steps/x/tests", tests, dirs_exist_ok=True)
    runtime = replace(runtime, paths=replace(runtime.paths, tests=str(tests)))
    monkeypatch.setenv("PBENCH_TREND_NOW", NOW.isoformat())
    with judge_server() as server:
        result = asyncio.run(
            run_verifier(
                tests / "grader.json",
                runtime=runtime,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
        )
        reward = json.loads(
            (Path(runtime.paths.verifier_logs) / "reward.json").read_text(
                encoding="utf-8"
            )
        )
        assert len(server["requests"]) == (3 if successful_accounts else 1)
        if successful_accounts:
            assert reward["llm_score"] == 1
        else:
            assert reward["llm_score"] == pytest.approx(1 / 3)
            assert reward["reward"] == pytest.approx(
                0.35 * reward["rule_score"] + 0.65 / 3
            )
            assert reward["reward"] <= 0.306971
            verdicts = {
                item["item_id"]: item for item in result["judges"][1]["verdicts"]
            }
            for name in ("summary_faithfulness", "information_value"):
                assert verdicts[f"llm:{name}"]["status"] == "fail"
                assert "successful_sources" in verdicts[f"llm:{name}"]["reason"]
            assert verdicts["llm:clear_chinese"]["status"] == "pass"
            prompt = server["requests"][0]["messages"][-1]["content"]
            assert "fetch_failed" in prompt and "抓取失败" in prompt
    logs = Path(runtime.paths.verifier_logs)
    records = {
        item["id"]: item
        for item in json.loads(
            (logs / "artifact_manifest.json").read_text(encoding="utf-8")
        )["artifacts"]
    }
    record = records["successful_sources"]
    assert record["extract_status"] == ("ok" if successful_accounts else "missing")
    if successful_accounts:
        assert record["source_artifact_id"] == "fetch_snapshot"
        successful = json.loads(
            (logs / "artifact_text/successful_sources.md").read_text(encoding="utf-8")
        )
        assert len(successful["accounts"]) == successful_accounts
        assert {account["status"] for account in successful["accounts"]} == {
            "no_updates"
        }


@pytest.mark.parametrize(
    "failure",
    [
        "missing_post",
        "outside_window",
        "wrong_window",
        "duplicate_account",
        "duplicate_post",
        "bad_status",
        "invalid_json",
    ],
)
def test_x_snapshot_validation_and_fixed_post_checks(tmp_path, verifier, failure):
    runtime, config, report, snapshot = make_case(tmp_path, "x")
    account = snapshot["accounts"][0]
    if failure in {"missing_post", "outside_window", "duplicate_post"}:
        account["status"] = "success"
        account["posts"] = [
            {
                "id": "123",
                "url": "https://x.com/sama/status/123",
                "text": "A concrete source fact",
                "published_at": trend_fixtures.format_utc(
                    NOW - timedelta(hours=25 if failure == "outside_window" else 1)
                ),
            }
        ]
        report.write_text(
            report.read_text(encoding="utf-8").replace("近 24 小时无新推文", "成功", 1),
            encoding="utf-8",
        )
        if failure == "duplicate_post":
            account["posts"] *= 2
    elif failure == "wrong_window":
        snapshot["window_start"] = trend_fixtures.format_utc(NOW - timedelta(hours=12))
    elif failure == "duplicate_account":
        snapshot["accounts"].append(account)
    elif failure == "bad_status":
        account["status"] = {}
    path = Path(runtime.paths.workdir) / ".trend-digest/x.json"
    path.write_text(
        "not JSON" if failure == "invalid_json" else json.dumps(snapshot),
        encoding="utf-8",
    )
    rewards, checks = grade(verifier, runtime, config)
    assert len(checks) == 48
    assert rewards["reward"] < 1
    if failure == "missing_post":
        assert not checks["custom:x_posts_sama"]["passed"]
        assert checks["custom:x_snapshot"]["passed"]
    elif failure == "wrong_window":
        assert not checks["custom:x_window"]["passed"]
    else:
        assert not checks["custom:x_snapshot"]["passed"]


@pytest.mark.parametrize("platform", ["github", "hacker-news"])
@pytest.mark.parametrize("layout", ["table", "ordered_list"])
def test_independent_item_formats_bind_sources_without_heading_templates(
    tmp_path, verifier, platform, layout
):
    runtime, config, report, snapshot = make_case(tmp_path, platform)
    intro = report.read_text(encoding="utf-8").split("## ", 1)[0]
    if platform == "github":
        rows = [
            [
                str(rank),
                repository,
                f"https://github.com/{repository}",
                "当前来源中的仓库。",
            ]
            for rank, repository in enumerate(snapshot["repositories"], 1)
        ]
        headers = ["排名", "仓库", "链接", "摘要"]
    else:
        headers = ["排名", "标题", "原文", "讨论", "score", "comments", "摘要"]
        rows = [
            [
                str(story["rank"]),
                story["title"],
                story["url"],
                story["discussion_url"],
                str(story["score"]),
                str(story["comment_count"]),
                "当前来源中的具体条目。",
            ]
            for story in snapshot["stories"]
        ]
    if layout == "table":
        body = "\n".join(
            [
                "| " + " | ".join(headers) + " |",
                "| " + " | ".join(["---"] * len(headers)) + " |",
            ]
            + ["| " + " | ".join(row) + " |" for row in rows]
        )
    else:
        body = "\n".join(
            f"{rank}. "
            + "; ".join(
                f"{label}: {value}" for label, value in zip(headers, row, strict=True)
            )
            for rank, row in enumerate(rows, 1)
        )
    report.write_text(intro + body + "\n", encoding="utf-8")
    assert grade(verifier, runtime, config)[0]["reward"] == 1


@pytest.mark.parametrize("platform", ["github", "hacker-news"])
@pytest.mark.parametrize("defect", ["merged", "duplicate", "swapped"])
def test_repository_and_story_credit_requires_distinct_ordered_units(
    tmp_path, verifier, platform, defect
):
    runtime, config, report, _ = make_case(tmp_path, platform)
    intro, *sections = report.read_text(encoding="utf-8").split("## ")
    if defect == "merged":
        text = (
            intro
            + "## 所有来源\n"
            + "\n".join(section.split("\n", 1)[1] for section in sections)
        )
    else:
        if defect == "duplicate":
            sections.append(sections[0])
        else:
            sections[0], sections[1] = sections[1], sections[0]
        text = intro + "".join("## " + section for section in sections)
    report.write_text(text, encoding="utf-8")
    _, checks = grade(verifier, runtime, config)
    prefix = "custom:github_repository_" if platform == "github" else "custom:hn_story_"
    slots = [item for key, item in checks.items() if key.startswith(prefix)]
    assert not slots[0]["passed"] and not slots[1]["passed"]
    assert sum(item["passed"] for item in slots) == (
        len(slots) - 2 if defect == "swapped" else 0
    )


@pytest.mark.parametrize("defect", ["duplicate_section", "unsupported_post"])
def test_x_report_cannot_reuse_account_sections_or_invent_posts(
    tmp_path, verifier, defect
):
    runtime, config, report, _ = make_case(tmp_path, "x")
    content = report.read_text(encoding="utf-8")
    if defect == "duplicate_section":
        content += "## Sam Altman (@sama)\n- 状态：近 24 小时无新推文\n"
    else:
        content = content.replace(
            "## Andrej Karpathy",
            "https://x.com/sama/status/123\n\n## Andrej Karpathy",
            1,
        )
    report.write_text(content, encoding="utf-8")
    _, checks = grade(verifier, runtime, config)
    assert not checks["custom:x_posts_sama"]["passed"]
    assert checks["custom:x_fetched_sama"]["passed"]
    assert checks["custom:x_status_sama"]["passed"] is (defect != "duplicate_section")


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
def test_published_evidence_uses_the_bytes_that_were_graded(
    tmp_path, verifier, monkeypatch, platform
):
    runtime, config, report, _ = make_case(tmp_path, platform)
    report_bytes = report.read_bytes()
    source = (
        Path(runtime.paths.agent_logs) / "trajectory.json"
        if platform == "github"
        else Path(runtime.paths.workdir) / f".trend-digest/{platform}.json"
    )
    source_bytes = source.read_bytes()
    enter = verifier.EvidenceWriter.__enter__

    def mutate_after_inspection(writer):
        report.write_text("changed after inspection", encoding="utf-8")
        source.write_text("changed after inspection", encoding="utf-8")
        return enter(writer)

    monkeypatch.setattr(verifier.EvidenceWriter, "__enter__", mutate_after_inspection)
    checks = verifier.check_outputs(runtime.to_dict(), config, now=NOW)
    assert all(check["passed"] for check in checks)
    logs = Path(runtime.paths.verifier_logs)
    assert (logs / "raw_artifacts/report_file.md").read_bytes() == report_bytes
    source_id = "retained_trajectory" if platform == "github" else "fetch_snapshot"
    assert (logs / f"raw_artifacts/{source_id}.json").read_bytes() == source_bytes
    assert (logs / "artifact_text/report.md").read_bytes() == report_bytes


def test_chinese_summary_does_not_require_a_literal_summary_label(tmp_path, verifier):
    runtime, config, report, _ = make_case(tmp_path, "github")
    report.write_text(
        report.read_text(encoding="utf-8").replace("摘要：", "说明："), encoding="utf-8"
    )
    _, checks = grade(verifier, runtime, config)
    assert checks["custom:report_chinese"]["passed"]


@pytest.mark.parametrize("platform", ["github", "x", "hacker-news"])
def test_trend_cli_publishes_current_step_partial_credit(
    tmp_path, monkeypatch, platform
):
    from dataclasses import replace

    runtime, config, report, _ = make_case(tmp_path, platform)
    tests = tmp_path / "isolated tests"
    shutil.copytree(TASK_ROOT / "tests", tests)
    shutil.copytree(TASK_ROOT / "steps" / platform / "tests", tests, dirs_exist_ok=True)
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
    monkeypatch.setenv("PBENCH_TREND_NOW", NOW.isoformat())
    monkeypatch.setenv("PEVAL_JUDGE_ENABLED", "false")
    assert verifier_main([str(tests / "grader.json")]) == 0
    logs = Path(runtime.paths.verifier_logs)
    reward = json.loads((logs / "reward.json").read_text(encoding="utf-8"))
    checks = json.loads((logs / "score.json").read_text(encoding="utf-8"))
    assert reward["reward"] == reward["rule_score"]
    assert reward["rule_score"] == pytest.approx(score_without(config, "final_answer"))
    assert reward["final_answer"] == (0 if platform == "hacker-news" else 1)
    if platform != "hacker-news":
        assert reward["continuation"] == 0
        assert checks["metadata"]["continuation"]["failed_check_ids"] == [
            "final_answer"
        ]
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
    runtime, config, _, snapshot = make_case(tmp_path, "x")
    snapshot["window_start"] = snapshot["window_end"]
    (Path(runtime.paths.workdir) / ".trend-digest/x.json").write_text(
        json.dumps(snapshot)
    )
    _, checks = grade(verifier, runtime, config)
    assert not checks["custom:x_window"]["passed"]
    assert not (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").exists()
    assert not (
        Path(runtime.paths.verifier_logs) / "artifact_text/successful_sources.md"
    ).exists()


def test_chinese_front_matter_alone_is_not_a_summary(tmp_path, verifier):
    runtime, config, report, _ = make_case(tmp_path, "github")
    report.write_text(
        "---\nsource: 这是足够长的中文元数据但没有摘要\n---\nEnglish only",
        encoding="utf-8",
    )
    _, checks = grade(verifier, runtime, config)
    assert not checks["custom:report_chinese"]["passed"]


def test_utf8_bom_report_from_windows_keeps_front_matter_and_evidence(
    tmp_path, verifier
):
    runtime, config, report, _ = make_case(tmp_path, "github")
    report.write_bytes(b"\xef\xbb\xbf" + report.read_bytes())
    assert grade(verifier, runtime, config)[0]["reward"] == 1
    assert (
        Path(runtime.paths.verifier_logs) / "artifact_text/report.md"
    ).read_bytes() == report.read_bytes()


def test_preparation_excludes_caches_and_records_fixed_input_digest(
    tmp_path, monkeypatch
):
    import hashlib

    staged = tmp_path / "environment"
    shutil.copytree(
        TASK_ROOT / "environment",
        staged,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    cache = staged / "data/skills/x-daily/scripts/__pycache__"
    cache.mkdir()
    (cache / "local.pyc").write_bytes(b"local interpreter cache")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    state_dir = tmp_path / "preparation_state"
    state_dir.mkdir()
    monkeypatch.setenv("PBENCH_TREND_NOW", NOW.isoformat())
    before = {
        p.relative_to(staged): p.read_bytes() for p in staged.rglob("*") if p.is_file()
    }
    module = load_module("trend_prepare_review", staged / "prepare.py")
    try:
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        selected = module.prepare(str(workdir), str(state_dir))
    finally:
        sys.dont_write_bytecode = previous
        sys.modules.pop("trend_prepare_review", None)
    metadata = json.loads((state_dir / "preparation.json").read_text(encoding="utf-8"))
    assert selected == ["input", "skills"]
    assert not list((workdir / ".trend-digest").iterdir())
    assert datetime.fromisoformat(metadata["prepared_at"]) == NOW
    assert not list(workdir.rglob("*.pyc"))
    assert not any("__pycache__" in name for name in metadata["sha256"])
    assert (
        metadata["sha256"]["input/x-users.xlsx"]
        == hashlib.sha256((workdir / "input/x-users.xlsx").read_bytes()).hexdigest()
    )
    assert before == {
        p.relative_to(staged): p.read_bytes() for p in staged.rglob("*") if p.is_file()
    }
