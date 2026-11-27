from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest

from tests.harbor.trend_digest_support import (
    NOW,
    TASK_ROOT,
    grade,
    loaded_task_module,
    make_case,
    score_without,
)


@pytest.fixture(scope="module")
def verifier() -> Iterator[ModuleType]:
    with loaded_task_module(
        "pbench_trend_hn_verifier",
        Path("tests/test_outputs.py"),
    ) as module:
        yield module


@pytest.mark.parametrize("failure", ["missing_link", "wrong_order", "missing_snapshot"])
def test_hn_fixed_twelve_story_checks(tmp_path, verifier, failure):
    runtime, config, report, snapshot = make_case(tmp_path, "hacker-news")
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
    rewards, checks = grade(verifier, runtime, config)
    assert len(checks) == 27
    if failure == "missing_link":
        assert rewards["reward"] == pytest.approx(
            score_without(config, "custom:hn_story_01")
        )
        assert not checks["custom:hn_story_01"]["passed"]
    else:
        assert not checks["custom:hn_snapshot"]["passed"]


def test_hn_metrics_must_match_their_own_story(tmp_path, verifier):
    runtime, config, report, _ = make_case(tmp_path, "hacker-news")
    report.write_text(
        report.read_text(encoding="utf-8").replace(
            "score: 99; comments: 1", "score: 98; comments: 2", 1
        ),
        encoding="utf-8",
    )
    _, checks = grade(verifier, runtime, config)
    assert not checks["custom:hn_story_01"]["passed"]
    assert checks["custom:hn_story_02"]["passed"]


@pytest.mark.parametrize("style", ["bold", "emphasis", "code", "reversed_bilingual"])
def test_hn_metrics_accept_bilingual_labels_and_markdown_emphasis(
    tmp_path, verifier, style
):
    runtime, config, report, snapshot = make_case(tmp_path, "hacker-news")
    content = report.read_text(encoding="utf-8")
    for story in snapshot["stories"]:
        score, comments = story["score"], story["comment_count"]
        old = f"score: {score}; comments: {comments}"
        new = {
            "bold": f"**得分（score）**：{score}; **评论数（comment_count）**：{comments}",
            "emphasis": f"__得分(score)__: {score}; __评论数(comment_count)__: {comments}",
            "code": f"`score`: `{score}`; `comment_count`: `{comments}`",
            "reversed_bilingual": f"**score（得分）**：{score}; **comment_count（评论数）**：{comments}",
        }[style]
        content = content.replace(old, new, 1)
    report.write_text(content, encoding="utf-8")
    assert grade(verifier, runtime, config)[0]["reward"] == 1


@pytest.mark.parametrize("defect", ["wrong_value", "other_story"])
def test_hn_bilingual_metrics_still_require_the_source_value_in_its_story(
    tmp_path, verifier, defect
):
    runtime, config, report, _ = make_case(tmp_path, "hacker-news")
    content = report.read_text(encoding="utf-8")
    content = content.replace(
        "score: 99; comments: 1",
        "**得分（score）**：99; **评论数（comment_count）**：1",
        1,
    )
    if defect == "wrong_value":
        content = content.replace("**得分（score）**：99", "**得分（score）**：98", 1)
    else:
        content = content.replace(
            "- **得分（score）**：99; **评论数（comment_count）**：1\n", "", 1
        )
        content = content.replace(
            "## 2. Fixture Hacker News story 2",
            "## 2. Fixture Hacker News story 2\n\n- **得分（score）**：99; **评论数（comment_count）**：1",
            1,
        )
    report.write_text(content, encoding="utf-8")
    _, checks = grade(verifier, runtime, config)
    assert not checks["custom:hn_story_01"]["passed"]
    assert checks["custom:hn_story_02"]["passed"]


def _hn_supporting_case(tmp_path):
    runtime, config, report, snapshot = make_case(tmp_path, "hacker-news")
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    story = snapshot["stories"][0]

    def step(number, call_id, name, arguments, content):
        return {
            "step_id": number,
            "source": "agent",
            "message": "",
            "tool_calls": [
                {"tool_call_id": call_id, "function_name": name, "arguments": arguments}
            ],
            "observation": {
                "results": [
                    {
                        "source_call_id": call_id,
                        "content": content,
                        "extra": {"exit_code": 0},
                    }
                ]
            },
        }

    data["steps"][-1]["step_id"] = 6
    data["steps"][-1:-1] = [
        step(
            3,
            "story-original",
            "web_fetch",
            {"url": story["url"]},
            "Specific retained original fact.",
        ),
        step(
            4,
            "story-discussion-fetch",
            "pwsh",
            {"command": f'curl "{story["discussion_url"]}" -o "/tmp/discussion.html"'},
            "Saved discussion page",
        ),
        step(
            5,
            "story-discussion-read",
            "pwsh",
            {"command": 'Get-Content "/tmp/discussion.html"'},
            "Specific retained discussion fact.",
        ),
    ]
    path.write_text(json.dumps(data), encoding="utf-8")
    return runtime, config, report, path, data


def test_hn_supporting_sources_bind_original_and_linked_discussion_to_story(
    tmp_path, verifier
):
    runtime, config, _, path, _ = _hn_supporting_case(tmp_path)
    assert grade(verifier, runtime, config)[0]["reward"] == 1
    logs = Path(runtime.paths.verifier_logs)
    text = (logs / "artifact_text/supporting_sources.md").read_text(encoding="utf-8")
    assert (
        "Story rank: 1\nStory ID: 1001\nSource kind: original\nSource URL: https://example.com/story-1"
        in text
    )
    assert "Fetch call: story-original\nEvidence call: story-original" in text
    assert (
        "Fetch call: story-discussion-fetch\nEvidence call: story-discussion-read"
        in text
    )
    assert (
        "Specific retained original fact." in text
        and "Specific retained discussion fact." in text
    )
    assert (
        "Story ID: 1002" in text and "No retained successful source observation" in text
    )
    assert (
        logs / "raw_artifacts/retained_trajectory.json"
    ).read_bytes() == path.read_bytes()


def _hn_repository_case(tmp_path):
    runtime, config, report, path, data = _hn_supporting_case(tmp_path)
    snapshot_path = Path(runtime.paths.workdir) / ".trend-digest/hacker-news.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["stories"][0]["url"] = "https://github.com/fixture/selected"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    report.write_text(
        report.read_text(encoding="utf-8").replace(
            "https://example.com/story-1", "https://github.com/fixture/selected", 1
        ),
        encoding="utf-8",
    )
    data["steps"][2]["tool_calls"][0]["arguments"] = {
        "url": "https://raw.githubusercontent.com/fixture/selected/main/README.md"
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return runtime, config, report, path, data


@pytest.mark.parametrize("source_form", ["direct", "linked_read", "family"])
def test_hn_github_story_includes_same_repository_readme(
    tmp_path, verifier, source_form
):
    runtime, config, _, path, data = _hn_repository_case(tmp_path)
    source = data["steps"][2]
    if source_form == "linked_read":
        source["tool_calls"][0].update(
            function_name="pwsh",
            arguments={
                "command": 'curl "https://raw.githubusercontent.com/fixture/selected/main/README.md" -o /tmp/selected.md'
            },
        )
        source["observation"]["results"][0]["content"] = "Saved README"
        read = data["steps"][4]
        read["tool_calls"][0]["arguments"] = {"command": "cat /tmp/selected.md"}
        read["observation"]["results"][0]["content"] = (
            "Specific retained original fact."
        )
    elif source_form == "family":
        child_source = json.loads(json.dumps(source))
        child_source["step_id"] = 1
        data["subagent_trajectories"] = [
            {
                "schema_version": "ATIF-v1.7",
                "trajectory_id": "readme-child",
                "agent": {"name": "fixture-child", "version": "1"},
                "steps": [child_source],
            }
        ]
        data["steps"].remove(source)
        for number, step in enumerate(data["steps"], 1):
            step["step_id"] = number
    path.write_text(json.dumps(data), encoding="utf-8")
    assert grade(verifier, runtime, config)[0]["reward"] == 1
    text = (
        Path(runtime.paths.verifier_logs) / "artifact_text/supporting_sources.md"
    ).read_text(encoding="utf-8")
    assert "Story rank: 1\nStory ID: 1001\nSource kind: repository_support" in text
    assert "Repository: https://github.com/fixture/selected" in text
    assert "Specific retained original fact." in text


@pytest.mark.parametrize(
    "defect", ["longer_raw", "other_owner", "longer_github", "failed", "copied"]
)
def test_hn_github_story_rejects_invalid_repository_support(tmp_path, verifier, defect):
    runtime, config, _, path, data = _hn_repository_case(tmp_path)
    source = data["steps"][2]
    if defect == "failed":
        source["observation"]["results"][0]["extra"]["exit_code"] = 1
    elif defect == "copied":
        source["is_copied_context"] = True
    else:
        source["tool_calls"][0]["arguments"]["url"] = {
            "longer_raw": "https://raw.githubusercontent.com/fixture/selected-longer/main/README.md",
            "other_owner": "https://raw.githubusercontent.com/other/selected/main/README.md",
            "longer_github": "https://github.com/fixture/selected-other/blob/main/README.md",
        }[defect]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert grade(verifier, runtime, config)[0]["reward"] == 1
    text = (
        Path(runtime.paths.verifier_logs) / "artifact_text/supporting_sources.md"
    ).read_text(encoding="utf-8")
    assert "Specific retained original fact." not in text
    assert "Source kind: repository_support" not in text


@pytest.mark.parametrize(
    "defect", ["failed", "copied", "url_prefix", "unrelated_file", "read_failed"]
)
def test_hn_supporting_sources_reject_unrelated_or_failed_evidence(
    tmp_path, verifier, defect
):
    runtime, config, _, path, data = _hn_supporting_case(tmp_path)
    original, _, read = data["steps"][2:5]
    marker = "Specific retained original fact."
    if defect == "failed":
        original["observation"]["results"][0]["extra"]["exit_code"] = 1
    elif defect == "copied":
        original["is_copied_context"] = True
    elif defect == "url_prefix":
        original["tool_calls"][0]["arguments"]["url"] += "-unrelated"
    elif defect == "unrelated_file":
        original["tool_calls"][0].update(
            function_name="read_file", arguments={"path": "/tmp/unrelated.json"}
        )
    else:
        read["observation"]["results"][0]["extra"]["exit_code"] = 1
        marker = "Specific retained discussion fact."
    path.write_text(json.dumps(data), encoding="utf-8")
    assert grade(verifier, runtime, config)[0]["reward"] == 1
    text = (
        Path(runtime.paths.verifier_logs) / "artifact_text/supporting_sources.md"
    ).read_text(encoding="utf-8")
    assert marker not in text
    assert "No retained successful source observation" in text


@pytest.mark.parametrize("oversized", [False, True])
@pytest.mark.parametrize("repository", [False, True])
def test_hn_supporting_sources_reach_judge_with_one_shared_budget(
    tmp_path, monkeypatch, oversized, repository
):
    import asyncio

    from psycheval.harbor.verifier import JudgeSettings, run_verifier
    from tests.fixtures.judge_server import judge_server

    runtime, config, report, path, data = (
        _hn_repository_case if repository else _hn_supporting_case
    )(tmp_path)
    if oversized:
        data["steps"][2]["observation"]["results"][0]["content"] = "x" * (
            1024 * 1024 - 8000
        )
        path.write_text(json.dumps(data), encoding="utf-8")
    tests = tmp_path / "isolated tests"
    shutil.copytree(TASK_ROOT / "tests", tests)
    shutil.copytree(TASK_ROOT / "steps/hacker-news/tests", tests, dirs_exist_ok=True)
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
        assert reward["rule_score"] == 1
        if oversized:
            assert reward["llm_score"] == 0 and result["reward"] == pytest.approx(0.35)
            assert server["requests"] == []
        else:
            assert result["reward"] == 1 and len(server["requests"]) == 3
            for request in server["requests"]:
                prompt = request["messages"][-1]["content"]
                assert (
                    "Specific retained original fact." in prompt
                    and "Specific retained discussion fact." in prompt
                )
                assert "Story ID: 1001" in prompt and "story-discussion-read" in prompt
                if repository:
                    assert "Source kind: repository_support" in prompt
    logs = Path(runtime.paths.verifier_logs)
    records = {
        item["id"]: item
        for item in json.loads(
            (logs / "artifact_manifest.json").read_text(encoding="utf-8")
        )["artifacts"]
    }
    supporting = records["supporting_sources"]
    assert supporting["extract_status"] == ("error" if oversized else "ok")
    if oversized:
        assert "remaining" in supporting["reason"] and "budget" in supporting["reason"]
        assert (logs / "artifact_text/report.md").read_bytes() == report.read_bytes()
        assert (logs / "artifact_text/sources.md").exists()
    else:
        assert supporting["source_artifact_id"] == "retained_trajectory"
        assert (
            sum(item["bytes"] for item in records.values() if item["type"] == "md")
            <= 1024 * 1024
        )
