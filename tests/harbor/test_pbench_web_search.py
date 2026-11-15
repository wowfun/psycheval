"""Source-bound search scoring and real local Judge evidence wiring."""

import asyncio
import json
import runpy
from html import escape
from pathlib import Path

import pytest
from harbor.models.trajectories import Trajectory

from psycheval.harbor.family import retain
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

TASK = Path(__file__).resolve().parents[2] / "datasets/pbench-v1.0/web-search-01"
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
URL = "https://www.iana.org/help/example-domains"
GOOD = f"IANA lists example.com and example.org as documentation examples. They are unavailable for registration or transfer. Source: {URL}"
ITEM = {
    "title": "Example Domains",
    "url": URL,
    "snippet": "IANA maintains example.com and example.org for documentation; neither is available for registration or transfer.",
}


def trajectory(
    answer=GOOD, *, content=None, tool="web_search", extra=None, forbidden=None
):
    calls = [
        {
            "tool_call_id": "search-1",
            "function_name": tool,
            "arguments": {"query": "IANA documentation names"},
        }
    ]
    if forbidden:
        calls.append(
            {
                "tool_call_id": "other",
                "function_name": forbidden,
                "arguments": {"command": "do something"},
            }
        )
    return Trajectory.model_validate(
        retain(
            {
                "schema_version": "ATIF-v1.7",
                "trajectory_id": "search-case",
                "agent": {"name": "local-fixture", "version": "1"},
                "steps": [
                    {
                        "step_id": 1,
                        "source": "user",
                        "message": "Find the IANA explanation",
                    },
                    {
                        "step_id": 2,
                        "source": "agent",
                        "message": "",
                        "tool_calls": calls,
                        "observation": {
                            "results": [
                                {
                                    "source_call_id": "search-1",
                                    "content": content
                                    if content is not None
                                    else json.dumps({"items": [ITEM]}),
                                    "extra": extra
                                    or {"is_error": False, "status": "completed"},
                                }
                            ]
                        },
                    },
                    {"step_id": 3, "source": "agent", "message": answer},
                ],
                "extra": {"tool_evidence": "complete"},
            }
        )
    )


@pytest.mark.parametrize(
    "tool",
    [
        "web_search",
        "WebSearch",
        "websearch",
        "mcp__exa__web_search_exa",
        "exa_web_search_exa",
    ],
)
def test_successful_real_search_names_and_query_wording_are_not_incidental(
    tmp_path, tool
):
    assert GRADER["assess"](trajectory(tool=tool), tmp_path)[0]


@pytest.mark.parametrize(
    "content",
    [
        json.dumps({"results": [ITEM]}),
        json.dumps(
            {
                "content": [
                    {
                        "type": "text",
                        "text": f"Title: Example Domains\nURL: {URL}\nText: IANA maintains example.com and example.org for documentation.",
                    }
                ]
            }
        ),
        f"Title: Example Domains\nURL: {URL}\nText: IANA maintains example.com and example.org for documentation.\n\nTitle: Another result\nURL: https://iana.org/domains\nText: Other domains",
        f"Title: Example Domains\nURL: {URL}\nPublished: N/A\nAuthor: N/A\nHighlights:\n# Example Domains\n\n1. IANA maintains example.com and example.org for documentation.\n\n## Further reading\nAnother paragraph\n\nTitle: Another hit\nURL: https://other.invalid/page\nHighlights:\nOther text",
        f"## Example Domains\n[{URL}]({URL})\nIANA maintains example.com and example.org for documentation.",
        f"# Search Results\n\n## 1. [Example Domains]({URL})\n\nIANA maintains example.com and example.org for documentation.\n\n**URL:** {URL}\n\n---\n\n## 2. [Other result](https://other.invalid/page)\nOther text",
        f"Example Domains ({URL}) — IANA maintains example.com and example.org for documentation.",
    ],
)
def test_source_binding_accepts_structured_and_standard_text_search_hits(
    tmp_path, content
):
    assert GRADER["assess"](trajectory(content=content), tmp_path)[0]


def test_numbered_markdown_headings_keep_different_hits_separate(tmp_path):
    content = (
        f"## 1. [Example Domains]({URL})\nOnly the page title\n\n"
        "## 2. [Other result](https://other.invalid/page)\n"
        "example.com and example.org are documentation examples."
    )
    assert not GRADER["assess"](trajectory(content=content), tmp_path)[0]


@pytest.mark.parametrize(
    "content",
    [
        json.dumps(
            {
                "items": [
                    {"url": URL, "snippet": "Only the title was returned"},
                    {
                        "url": "https://other.invalid/article",
                        "snippet": "example.com and example.org",
                    },
                ]
            }
        ),
        f"Title: IANA\nURL: {URL}\nText: Only title\n\nTitle: Another article\nURL: https://other.invalid/article\nText: example.com and example.org",
        json.dumps(
            {
                "items": [
                    {
                        "url": "https://www.iana.org.evil.invalid/help/example-domains",
                        "snippet": ITEM["snippet"],
                    }
                ]
            }
        ),
        json.dumps(
            {
                "items": [
                    {
                        "url": "https://www.iana.org/domains/reserved",
                        "snippet": ITEM["snippet"],
                    }
                ]
            }
        ),
    ],
)
def test_domains_from_another_hit_or_spoofed_url_do_not_satisfy_source_binding(
    tmp_path, content
):
    assert not GRADER["assess"](trajectory(content=content), tmp_path)[0]


@pytest.mark.parametrize(
    "answer",
    [
        "",
        "Done",
        f"example.com.evil and foo-example.org — {URL}",
        "example.com and example.org",
        f"example.net — {URL}",
    ],
)
def test_missing_answer_names_or_citation_cannot_earn_rule_credit(tmp_path, answer):
    assert not GRADER["assess"](trajectory(answer), tmp_path)[0]


@pytest.mark.parametrize(
    "tool",
    [
        "web_fetch",
        "bash",
        "exec_command",
        "powershell",
        "browser_navigate",
        "mcp__playwright__browser_evaluate",
        "browser_run_code_unsafe",
    ],
)
def test_forbidden_alternative_channels_gate_the_whole_rule(tmp_path, tool):
    assert not GRADER["assess"](trajectory(forbidden=tool), tmp_path)[0]


@pytest.mark.parametrize(
    "tool,extra",
    [
        ("web_fetch", None),
        ("filesearch", None),
        ("web_search", {"is_error": True, "status": "failed"}),
    ],
)
def test_correct_guesses_failed_search_and_local_search_are_not_search_evidence(
    tmp_path, tool, extra
):
    passed, diagnosis, _, _ = GRADER["assess"](
        trajectory(tool=tool, extra=extra), tmp_path
    )
    assert not passed and diagnosis["matching_successful_search_calls"] == 0
    assert "does not prove" in diagnosis["limit"]


@pytest.mark.parametrize(
    "url",
    [
        "https://iana.org/help/example-domains/",
        "https://www.iana.org/help/example-domains?ref=search#section",
        "http://www.iana.org/help/example-domains",
    ],
)
def test_canonical_iana_help_url_variants_are_acceptable(url):
    assert GRADER["target_url"](url)


def test_noncanonical_tool_claim_cannot_establish_search(tmp_path):
    retained = trajectory()
    retained.steps[1].tool_calls[0].extra = {"acp_canonical_name": False}
    assert not GRADER["assess"](retained, tmp_path)[0]


def test_missing_retained_trajectory_is_an_explicit_unavailable_observation(tmp_path):
    roots = {
        name: tmp_path / name
        for name in ("workdir", "agent_logs", "verifier_logs", "artifacts")
    }
    for path in roots.values():
        path.mkdir()
    runtime = EffectiveRuntimeConfig(
        paths=RuntimePaths(
            tests=str(TASK / "tests"), **{key: str(path) for key, path in roots.items()}
        ),
        verifier=VerifierInvocation("Find IANA"),
    )
    result = asyncio.run(run_verifier(TASK / "tests/grader.json", runtime=runtime))
    assert result["reward"] == 0
    published = (
        roots["verifier_logs"] / "artifact_text/search_observations.md"
    ).read_text(encoding="utf-8")
    assert "missing trajectory" in published


@pytest.mark.parametrize(
    "answer,judge_pass,expected",
    [
        (GOOD, True, 1),
        (f"example.com example.org {URL}", False, 0.4),
        ("I cannot access search", False, 0),
    ],
)
def test_public_verifier_sends_actual_search_and_same_helper_answer_to_judge(
    tmp_path, answer, judge_pass, expected
):
    loaded = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert loaded.config.agent.timeout_sec == 900
    config = json.loads((TASK / "tests/grader.json").read_text())
    assert [item.id for item in build_scoring_plan(config).items] == [
        "custom:search_backed_answer"
    ]
    judge = load_judge_config(TASK / "tests/judge.yaml")
    assert (judge.rule_weight, judge.llm_weight) == (0.4, 0.6)
    roots = {
        name: tmp_path / name
        for name in ("workdir", "agent_logs", "verifier_logs", "artifacts")
    }
    for path in roots.values():
        path.mkdir()
    history = trajectory(answer)
    (roots["agent_logs"] / "trajectory.json").write_text(
        history.model_dump_json(), encoding="utf-8"
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
        server["behavior"] = {"grounded_domain_answer": {"passed": judge_pass}}
        result = asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=runtime,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
        )
    assert result["reward"] == pytest.approx(expected)
    if server["requests"]:
        assert len(server["requests"]) == 1
        prompt = server["requests"][0]["messages"][-1]["content"]
        for filename in ("search_observations", "final_answer"):
            text = (roots["verifier_logs"] / f"artifact_text/{filename}.md").read_text(
                encoding="utf-8"
            )
            assert escape(text, quote=False) in prompt
        assert "search-1" in prompt and "IANA documentation names" in prompt
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text()
    )
    records = {item["id"]: item for item in manifest["artifacts"]}
    assert records["search_observations"]["source_artifact_id"] == "retained_trajectory"
    assert records["final_answer"]["source_artifact_id"] == "retained_trajectory"
