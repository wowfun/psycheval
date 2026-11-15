"""The Web Fetch task grades this attempt's paired source, not a frozen date."""

import asyncio
import json
import runpy
from html import escape
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
from tests.fixtures import load_pbench_trajectory
from tests.fixtures.judge_server import judge_server

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "datasets/pbench-v1.0/web-fetch-01"
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
URL = GRADER["URL"]


def data(tmp_path, *, revision="2042-02-03", tool="web_fetch", answer=None):
    raw = load_pbench_trajectory(
        ROOT / "tests/fixtures/pbench/web-fetch-01",
        "Fetch the page",
        tmp_path / "artifacts",
    )
    raw["steps"][1]["tool_calls"][0]["function_name"] = tool
    raw["steps"][1]["observation"]["results"][0]["content"] = json.dumps(
        {
            "url": URL,
            "status": 200,
            "content": f"# Example Domains\nBody SOURCE_BODY_SENTINEL\nLast revised {revision}.",
        }
    )
    raw["steps"][2]["message"] = (
        answer or f"The page was last revised {revision}. {URL}"
    )
    return raw


def assess(raw):
    return GRADER["assess"](Trajectory.model_validate(raw))


@pytest.mark.parametrize(
    "tool", ["web_fetch", "WebFetch", "WEB-FETCH", "mcp__network__web_fetch"]
)
@pytest.mark.parametrize("revision", ["2017-05-13", "2031-12-31", "2042-02-03"])
def test_date_is_derived_from_the_actual_matched_response(tmp_path, tool, revision):
    passed, facts, source, _ = assess(data(tmp_path, revision=revision, tool=tool))
    assert passed
    assert facts["source_revision_dates"] == [revision]
    assert "SOURCE_BODY_SENTINEL" in source and "tool_call_id=fetch-1" in source


@pytest.mark.parametrize(
    "answer",
    [
        f"2042-02-03 — {URL}",
        f"Last revised: February 3, 2042. {URL}",
        f"修订日期是2042年2月3日，来源：{URL}",
        f"Last revised 3 Feb 2042. {URL}\nAccessed on 2042-02-04.",
        f"HTTP Date is not the Last revised date; Last revised is 2042-02-03. {URL}",
        f"The page was last revised 2042-02-03, not an HTTP response timestamp. {URL}",
    ],
)
def test_answer_allows_equivalent_dates_and_separate_access_dates(tmp_path, answer):
    assert assess(data(tmp_path, answer=answer))[0]


@pytest.mark.parametrize(
    "mutation",
    [
        "no_call",
        "search_instead",
        "shell_instead",
        "wrong_url",
        "unpaired",
        "failed",
        "http_failure",
        "http_string_failure",
        "envelope_error",
        "headers_only",
        "missing_revision",
        "conflicting_source",
        "copied_context",
        "wrong_date",
        "date_stuffing",
        "missing_citation",
        "negated",
        "negated_bare_date",
        "uncertain_date",
        "forbidden_extra",
    ],
)
def test_shortcuts_fail_the_whole_retrieval_check(tmp_path, mutation):
    raw = data(tmp_path)
    step = raw["steps"][1]
    observation = step["observation"]["results"][0]
    if mutation == "no_call":
        step["tool_calls"] = []
        step.pop("observation")
    elif mutation in {"search_instead", "shell_instead"}:
        step["tool_calls"][0]["function_name"] = (
            "web_search" if mutation == "search_instead" else "exec_command"
        )
    elif mutation == "wrong_url":
        step["tool_calls"][0]["arguments"]["url"] = "https://www.iana.org/other"
    elif mutation == "unpaired":
        observation["source_call_id"] = "another-call"
        step["tool_calls"].append(
            {
                "tool_call_id": "another-call",
                "function_name": "read",
                "arguments": {"path": "unrelated.txt"},
            }
        )
    elif mutation == "failed":
        observation["extra"]["is_error"] = True
    elif mutation in {"http_failure", "http_string_failure"}:
        observation["content"] = json.dumps(
            {
                "status": 503 if mutation == "http_failure" else "503",
                "content": "Example Domains Last revised 2042-02-03",
            }
        )
    elif mutation == "envelope_error":
        observation["content"] = json.dumps(
            {
                "error": "Request failed",
                "content": "Example Domains Last revised 2042-02-03",
            }
        )
    elif mutation == "headers_only":
        observation["content"] = json.dumps(
            {"headers": {"Last revised": "2042-02-03"}, "content": "Example Domains"}
        )
    elif mutation == "missing_revision":
        observation["content"] = "Example Domains. HTTP Last-Modified: 2042-02-03"
    elif mutation == "conflicting_source":
        observation["content"] = (
            "Example Domains Last revised 2042-02-03. Last revised 2040-01-01."
        )
    elif mutation == "copied_context":
        step["is_copied_context"] = True
    elif mutation == "wrong_date":
        raw["steps"][2]["message"] = f"Last revised 2017-05-13. {URL}"
    elif mutation == "date_stuffing":
        raw["steps"][2]["message"] = f"Last revised 2042-02-03 or 2017-05-13. {URL}"
    elif mutation == "missing_citation":
        raw["steps"][2]["message"] = "Last revised 2042-02-03."
    elif mutation == "negated":
        raw["steps"][2]["message"] = f"The page was not last revised 2042-02-03. {URL}"
    elif mutation == "negated_bare_date":
        raw["steps"][2]["message"] = f"Not 2042-02-03. {URL}"
    elif mutation == "uncertain_date":
        raw["steps"][2]["message"] = f"Last revised may be 2042-02-03. {URL}"
    else:
        step["tool_calls"].append(
            {
                "tool_call_id": "search-extra",
                "function_name": "web_search",
                "arguments": {"query": "IANA date"},
            }
        )
    assert not assess(raw)[0]


def test_raw_html_uses_shared_static_inspector_without_script_or_network(
    tmp_path, monkeypatch
):
    pytest.importorskip("html5lib")
    pytest.importorskip("tinycss2")
    import socket

    monkeypatch.setattr(
        socket, "socket", lambda *args, **kwargs: pytest.fail("No verifier networking")
    )
    raw = data(tmp_path)
    raw["steps"][1]["observation"]["results"][0]["content"] = (
        "<html><body><h1>Example Domains</h1><script>Last revised 2017-05-13</script><p>Last revised <b>2042-02-03</b>.</p></body></html>"
    )
    assert assess(raw)[0]


@pytest.mark.parametrize("tool", ["web_fetch", "WebFetch", "WEB-FETCH"])
@pytest.mark.parametrize("valid", [True, False], ids=["correct", "wrong-date"])
def test_public_verifier_child_and_actual_judge_request(tmp_path, tool, valid):
    loaded = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert loaded.config.agent.timeout_sec == 900
    config = json.loads((TASK / "tests/grader.json").read_text(encoding="utf-8"))
    assert [item.id for item in build_scoring_plan(config).items] == [
        "custom:verified_fetch"
    ]
    judge = load_judge_config(TASK / "tests/judge.yaml")
    assert judge.rubrics[0].artifact_refs == (
        "execution_facts",
        "fetched_source",
        "final_answer",
    )
    roots = {
        key: tmp_path / key
        for key in ("workdir", "agent_logs", "verifier_logs", "artifacts")
    }
    for path in roots.values():
        path.mkdir(exist_ok=True)
    raw = data(
        tmp_path, tool=tool, answer=None if valid else f"Last revised 2017-05-13. {URL}"
    )
    raw["steps"].insert(
        1, {"step_id": 8, "source": "agent", "message": "HISTORICAL_ANSWER_SENTINEL"}
    )
    for index, step in enumerate(raw["steps"], 1):
        step["step_id"] = index
    trajectory = Trajectory.model_validate(raw)
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
        server["behavior"] = {"faithful_revision_answer": {"passed": valid}}
        result = asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=runtime,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
        )
        assert len(server["requests"]) == 1
        prompt = server["requests"][0]["messages"][-1]["content"]
    assert result["reward"] == int(valid)
    assert result["metadata"]["score_merge"]["applied"]
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    artifacts = {item["id"]: item for item in manifest["artifacts"]}
    assert artifacts["fetched_source"]["source_artifact_id"] == "retained_trajectory"
    assert artifacts["final_answer"]["source_artifact_id"] == "retained_trajectory"
    for identity in ("fetched_source", "execution_facts", "final_answer"):
        content = (roots["verifier_logs"] / artifacts[identity]["text_path"]).read_text(
            encoding="utf-8"
        )
        assert escape(content, quote=False) in prompt
    assert (
        "SOURCE_BODY_SENTINEL" in prompt and "HISTORICAL_ANSWER_SENTINEL" not in prompt
    )
