from __future__ import annotations

import pytest
from harbor.models.trajectories import Trajectory

from psycheval.harbor.psychevo import (
    parse_ndjson,
    psychevo_events_to_atif,
)


def completed_events() -> list[dict]:
    return [
        {"type": "thread.started", "threadId": "thread-1"},
        {
            "type": "item.started",
            "item": {
                "id": "assistant-1",
                "role": "assistant",
                "source": "runtime.message",
                "createdAtMs": 1000,
                "blocks": [
                    {
                        "kind": "web",
                        "status": "running",
                        "metadata": {
                            "tool_name": "web_fetch",
                            "tool_call_id": "call-1",
                            "args": {
                                "url": "https://www.iana.org/help/example-domains"
                            },
                        },
                        "result": {
                            "content": "partial",
                            "isError": False,
                            "status": "running",
                        },
                    }
                ],
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "assistant-1",
                "role": "assistant",
                "source": "runtime.stream",
                "createdAtMs": 1000,
                "blocks": [
                    {
                        "kind": "web",
                        "status": "completed",
                        "body": "Example Domains. Last revised 2017-05-13.",
                        "metadata": {"tool_name": "web_fetch", "truncated": False},
                    }
                ],
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "assistant-2",
                "role": "assistant",
                "source": "runtime.message",
                "createdAtMs": 2000,
                "blocks": [
                    {
                        "kind": "text",
                        "status": "completed",
                        "body": "2017-05-13 https://www.iana.org/help/example-domains",
                        "metadata": {"model": "fixture-model"},
                    }
                ],
            },
        },
        {
            "type": "turn.completed",
            "threadId": "thread-1",
            "turnId": "turn-1",
            "outcome": "completed",
            "toolFailures": 0,
            "finalAnswer": "2017-05-13 https://www.iana.org/help/example-domains",
        },
    ]


def test_converts_structured_psychevo_tool_evidence_to_atif() -> None:
    value = psychevo_events_to_atif(
        completed_events(), instruction="Fetch the page", agent_version="pevo 0.1.0"
    )
    trajectory = Trajectory(**value)
    assert trajectory.agent.model_name == "fixture-model"
    call_step = next(step for step in trajectory.steps if step.tool_calls)
    assert call_step.tool_calls is not None
    assert call_step.tool_calls[0].function_name == "web_fetch"
    assert call_step.tool_calls[0].arguments["url"].endswith("example-domains")
    assert call_step.observation is not None
    assert "2017-05-13" in (call_step.observation.results[0].content or "")
    assert call_step.observation.results[0].extra is not None
    assert call_step.observation.results[0].extra["status"] == "completed"


def test_does_not_invent_tool_evidence_from_final_answer() -> None:
    events = [completed_events()[0], *completed_events()[-1:]]
    value = psychevo_events_to_atif(
        events, instruction="Fetch the page", agent_version="pevo 0.1.0"
    )
    assert not any(step.get("tool_calls") for step in value["steps"])


def test_converts_hosted_web_search_action_and_sources_without_reclassifying_text() -> (
    None
):
    events = [
        {
            "type": "item.completed",
            "item": {
                "id": "live:turn-1:assistant",
                "role": "assistant",
                "source": "runtime.message",
                "createdAtMs": 1000,
                "blocks": [
                    {
                        "kind": "web",
                        "status": "completed",
                        "source": "provider.web_search",
                        "body": "Rust release notes",
                        "metadata": {
                            "projection": "provider_tool",
                            "execution_owner": "provider",
                            "tool_name": "web_search",
                            "provider_tool_id": "ws-1",
                            "action": {
                                "type": "search",
                                "query": "Rust release notes",
                            },
                            "status": "completed",
                        },
                    },
                    {
                        "kind": "web",
                        "status": "completed",
                        "source": "provider.source",
                        "body": "[Rust](https://example.com/rust)",
                        "metadata": {
                            "projection": "url_citation",
                            "url": "https://example.com/rust",
                            "title": "Rust",
                        },
                    },
                    {
                        "kind": "text",
                        "status": "completed",
                        "source": "runtime.message",
                        "body": "Final answer from the cited source",
                        "metadata": {"projection": "assistant_text"},
                    },
                ],
            },
        },
        {
            "type": "turn.completed",
            "threadId": "thread-1",
            "turnId": "turn-1",
            "outcome": "completed",
            "toolFailures": 0,
            "finalAnswer": "Final answer from the cited source",
        },
    ]

    trajectory = Trajectory(
        **psychevo_events_to_atif(
            events, instruction="Search the web", agent_version="pevo 0.1.0"
        )
    )
    call_step = next(step for step in trajectory.steps if step.tool_calls)
    assert call_step.tool_calls is not None
    assert call_step.tool_calls[0].arguments == {
        "type": "search",
        "query": "Rust release notes",
    }
    assert call_step.observation is not None
    observation = call_step.observation.results[0].content or ""
    assert "https://example.com/rust" in observation
    assert "Final answer from the cited source" not in observation
    assert any(
        step.message == "Final answer from the cited source"
        for step in trajectory.steps
    )


def test_preserves_completed_assistant_occurrences_when_item_id_is_reused() -> None:
    events = [
        {
            "type": "item.completed",
            "item": {
                "id": "live:turn-1:assistant",
                "role": "assistant",
                "source": "runtime.message",
                "blocks": [
                    {
                        "kind": "text",
                        "status": "completed",
                        "body": "I will inspect the source.",
                    }
                ],
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "live:turn-1:assistant",
                "role": "assistant",
                "source": "runtime.message",
                "blocks": [
                    {
                        "kind": "text",
                        "status": "completed",
                        "body": "The source confirms the answer.",
                    }
                ],
            },
        },
        {
            "type": "turn.completed",
            "threadId": "thread-1",
            "turnId": "turn-1",
            "outcome": "completed",
            "toolFailures": 0,
            "finalAnswer": "The source confirms the answer.",
        },
    ]

    value = psychevo_events_to_atif(
        events, instruction="Inspect it", agent_version="pevo 0.1.0"
    )
    messages = [step.get("message") for step in value["steps"]]
    assert "I will inspect the source." in messages
    assert "The source confirms the answer." in messages


def test_preserves_usage_and_cache_evidence_without_inventing_timing() -> None:
    events = completed_events()
    events[3]["item"]["usage"] = {
        "prompt_tokens": 200,
        "completion_tokens": 25,
        "cached_tokens": 80,
    }

    value = psychevo_events_to_atif(
        events, instruction="Fetch the page", agent_version="pevo 0.1.0"
    )

    inference = value["final_metrics"]["extra"]["model_inference"]
    assert value["final_metrics"]["total_prompt_tokens"] == 200
    assert value["final_metrics"]["total_completion_tokens"] == 25
    assert value["final_metrics"]["total_cached_tokens"] == 80
    assert inference["cache_prompt_tokens"] == 200
    assert inference["cache_read_tokens"] == 80
    assert "ttft_ms_sum" not in inference
    assert "decode_duration_ms" not in inference


def test_rejects_failed_terminal_event() -> None:
    events = completed_events()
    events[-1] = {
        "type": "turn.failed",
        "outcome": "failed",
        "terminalMessage": "provider unavailable",
    }
    with pytest.raises(ValueError, match="provider unavailable"):
        psychevo_events_to_atif(
            events, instruction="Fetch the page", agent_version="unknown"
        )


def test_rejects_malformed_ndjson() -> None:
    with pytest.raises(ValueError, match="line 2"):
        parse_ndjson('{"type":"thread.started"}\nnot-json\n')
