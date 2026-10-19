from __future__ import annotations

import asyncio
import copy
import json
import os
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from harbor.agents.installed.base import NonZeroAgentExitCodeError
from harbor.models.agent.context import AgentContext
from harbor.models.task.config import MCPServerConfig

from psycheval.harbor.opencode import HostOpenCodeAgent
from psycheval.harbor.trajectory_validation import load_validated_trajectory
from psycheval.harbor.verifier import evaluate
from tests.harbor.environment_support import assert_process_exited, make_environment


def _exported_session():
    return {
        "info": {"id": "session-fixture", "outcome": "succeeded"},
        "messages": [
            {
                "id": "assistant-fixture",
                "type": "assistant",
                "model": {"providerID": "fixture", "id": "model"},
                "time": {"created": 1, "completed": 2},
                "content": [{"type": "text", "text": "完成 🎉"}],
                "cost": 0.25,
                "tokens": {"input": 12, "output": 7, "cache": {"read": 3}},
            }
        ],
    }


@pytest.mark.parametrize(
    "field", ["model", "time", "state", "output", "output_item", "error", "part"]
)
def test_malformed_nested_export_fields_have_categorical_errors(tmp_path, field):
    exported = _exported_session()
    message = exported["messages"][0]
    tool = {
        "type": "tool",
        "id": "call",
        "name": "bash",
        "state": {"status": "error", "input": {}, "content": []},
    }
    if field in {"model", "time"}:
        message[field] = None
    elif field == "part":
        message["content"] = [None]
    else:
        message["content"] = [tool]
        if field == "state":
            tool["state"] = None
        elif field == "output":
            tool["state"]["content"] = None
        elif field == "output_item":
            tool["state"]["content"] = [None]
        else:
            tool["state"]["error"] = "invalid"
    path = tmp_path / "opencode-session.json"
    path.write_text(json.dumps(exported), encoding="utf-8")
    before = path.read_bytes()
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    with pytest.raises(ValueError, match="Malformed OpenCode Session"):
        agent.populate_context_post_run(AgentContext())
    assert path.read_bytes() == before
    assert not (tmp_path / "trajectory.json").exists()


def test_epoch_zero_completion_and_null_optional_tool_error_are_valid(tmp_path):
    exported = _exported_session()
    exported["messages"][0].update(
        time={"created": 0, "completed": 0},
        content=[
            {
                "type": "tool",
                "id": "call",
                "name": "bash",
                "state": {
                    "status": "completed",
                    "input": {},
                    "content": [],
                    "error": None,
                },
            }
        ],
    )
    (tmp_path / "opencode-session.json").write_text(
        json.dumps(exported), encoding="utf-8"
    )
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent.populate_context_post_run(AgentContext())
    data = load_validated_trajectory(tmp_path / "trajectory.json")
    assert data["steps"][0]["timestamp"] == "1970-01-01T00:00:00+00:00"
    assert data["steps"][0]["observation"]["results"][0]["extra"]["is_error"] is False


def test_session_export_preserves_tools_and_usage_without_streamed_steps(tmp_path):
    exported = _exported_session()
    tool = {
        "type": "tool",
        "id": "read-source",
        "name": "bash",
        "state": {
            "status": "completed",
            "input": {"command": "python source.py"},
            "content": [{"type": "text", "text": "source data"}],
            "metadata": {"exit": 1},
        },
    }
    exported["messages"][0]["content"].insert(0, tool)
    (tmp_path / "opencode-session.json").write_text(
        json.dumps(exported), encoding="utf-8"
    )
    (tmp_path / "opencode.txt").write_text(
        json.dumps(
            {
                "type": "tool_use",
                "sessionID": "session-fixture",
                "part": {
                    "id": "read-source",
                    "tool": "bash",
                },
            }
        ),
        encoding="utf-8",
    )
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent._instruction = "Read source"
    context = AgentContext()
    agent.populate_context_post_run(context)
    data = load_validated_trajectory(tmp_path / "trajectory.json")
    assert data["steps"][0]["message"] == "Read source"
    assert data["steps"][1]["message"] == "完成 🎉"
    assert data["steps"][1]["tool_calls"][0]["function_name"] == "bash"
    observation = data["steps"][1]["observation"]["results"][0]
    assert observation["content"] == "source data"
    assert observation["extra"]["is_error"] is True
    assert observation["extra"]["exit_code"] == 1
    assert observation["extra"]["raw_output"] == tool["state"]["content"]
    assert context.n_input_tokens == 15
    assert context.n_output_tokens == 7
    assert context.n_cache_tokens == 3
    assert context.cost_usd == 0.25
    assert data["final_metrics"]["extra"]["model_inference"] == {
        "schema_version": 1,
        "cache_prompt_tokens": 15,
        "cache_read_tokens": 3,
        "cache_sample_count": 1,
        "attempt_count": 1,
        "successful_attempt_count": 1,
        "usage_sources": ["opencode-session"],
    }


@pytest.mark.parametrize(
    "tokens,prompt,cached,rate",
    [
        ({"input": 12, "cache": {"read": 3, "write": 5}}, 20, 3, 0.15),
        ({"input": 12, "cache": {"read": 0, "write": 0}}, 12, 0, 0),
        ({"input": 0, "cache": {"read": 3}}, 3, 3, 1),
        ({"input": 0, "cache": {"read": 0, "write": 10}}, 10, 0, 0),
        ({"input": 12}, 12, None, None),
        ({"input": 12, "cache": {}}, 12, None, None),
        ({"input": 12, "cache": {"read": None}}, None, None, None),
        ({"input": 12, "cache": {"read": True}}, None, None, None),
        ({"input": 12, "cache": {"read": -1}}, None, None, None),
        ({"input": 12, "cache": {"read": "3"}}, None, None, None),
        ({"input": 12, "cache": {"read": 3.5}}, None, None, None),
        ({"input": 12, "cache": {"read": 3, "write": None}}, None, None, None),
        ({"input": 12, "cache": {"read": 3, "write": -1}}, None, None, None),
        ({"input": True, "cache": {"read": 3}}, None, None, None),
        ({"input": -1, "cache": {"read": 3}}, None, None, None),
        ({"input": "12", "cache": {"read": 3}}, None, None, None),
        ({"input": 12, "cache": None}, 12, None, None),
        ({"cache": {"read": 3}}, None, None, None),
        ({"input": 0, "cache": {"read": 0}}, 0, None, None),
        ({}, None, None, None),
    ],
)
def test_session_cache_samples_preserve_buckets_and_unknowns(
    tmp_path, tokens, prompt, cached, rate
):
    from psycheval.report.inference import inference_row_metrics

    exported = _exported_session()
    exported["messages"][0]["tokens"] = {**tokens, "output": 7, "reasoning": 2}
    path = tmp_path / "opencode-session.json"
    path.write_text(json.dumps(exported), encoding="utf-8")
    before = path.read_bytes()
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    context = AgentContext(n_input_tokens=999, n_output_tokens=999, n_cache_tokens=999)
    agent.populate_context_post_run(context)
    data = load_validated_trajectory(tmp_path / "trajectory.json")
    metrics = data["steps"][0]["metrics"]
    assert metrics.get("prompt_tokens") == prompt
    assert metrics.get("cached_tokens") == cached
    assert metrics["completion_tokens"] == 7
    assert metrics["cost_usd"] == 0.25
    assert metrics["extra"]["reasoning_tokens"] == 2
    assert context.n_input_tokens == prompt
    assert context.n_output_tokens == 7
    assert context.n_cache_tokens == cached
    assert context.cost_usd == 0.25
    display = inference_row_metrics(data["final_metrics"])
    assert display["cache_hit_rate"] == rate
    assert display["ttft_ms"] is None
    assert display["tps"] is None
    if rate is None:
        assert display["cache_sample_count"] is None
    else:
        assert display["cache_sample_count"] == 1
    cache = tokens.get("cache") or {}
    if type(cache.get("write")) is int and cache["write"] >= 0:
        assert metrics["extra"]["usage"]["cache_write_tokens"] == cache["write"]
    assert path.read_bytes() == before


def test_write_only_usage_preserves_cost_reasoning_and_measured_zero(tmp_path):
    exported = _exported_session()
    exported["messages"][0]["tokens"] = {
        "input": 0,
        "output": 0,
        "reasoning": 2,
        "cache": {"read": 0, "write": 10},
    }
    (tmp_path / "opencode-session.json").write_text(
        json.dumps(exported), encoding="utf-8"
    )
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    context = AgentContext()
    agent.populate_context_post_run(context)
    data = load_validated_trajectory(tmp_path / "trajectory.json")
    metrics = data["steps"][0]["metrics"]
    assert metrics["cost_usd"] == 0.25
    assert metrics["extra"]["reasoning_tokens"] == 2
    assert context.n_input_tokens == 10
    assert context.n_output_tokens == 0
    assert context.n_cache_tokens == 0


def test_cache_rate_uses_paired_message_samples_and_retains_identical_usage(tmp_path):
    from psycheval.report.inference import inference_row_metrics

    exported = _exported_session()
    template = exported["messages"][0]
    for index, tokens in enumerate(
        [
            {"input": 80, "output": 1, "cache": {"read": 20}},
            {"input": 80, "output": 1, "cache": {"read": 20}},
            {"input": 10, "output": 1, "cache": {"read": 0}},
            {"input": 1000, "output": 1},
        ]
    ):
        message = copy.deepcopy(template)
        message.update(id=f"assistant-{index}", tokens=tokens)
        exported["messages"].append(message)
    exported["messages"].pop(0)
    (tmp_path / "opencode-session.json").write_text(
        json.dumps(exported), encoding="utf-8"
    )
    # Streamed usage is not another consumption sample.
    (tmp_path / "opencode.txt").write_text(
        json.dumps(
            {
                "type": "step_finish",
                "sessionID": "session-fixture",
                "part": {"tokens": {"input": 9999, "cache": {"read": 9999}}},
            }
        ),
        encoding="utf-8",
    )
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent.populate_context_post_run(AgentContext())
    data = load_validated_trajectory(tmp_path / "trajectory.json")
    assert data["final_metrics"]["total_prompt_tokens"] == 1210
    assert data["final_metrics"]["total_cached_tokens"] == 40
    inference = inference_row_metrics(data["final_metrics"])
    assert inference["cache_prompt_tokens"] == 210
    assert inference["cache_read_tokens"] == 40
    assert inference["cache_sample_count"] == 3
    assert inference["cache_hit_rate"] == pytest.approx(40 / 210)


def _native_timed_trajectory(tmp_path, model_time, tool_time, status="completed"):
    exported = _exported_session()
    message = exported["messages"][0]
    message["time"] = model_time
    message["content"].extend(
        {
            "type": "tool",
            "id": identity,
            "name": "shell",
            "time": timing,
            "state": {"status": status, "input": {}, "content": []},
        }
        for identity, timing in (
            ("first", tool_time),
            ("parallel", {"ran": 120, "completed": 300}),
        )
    )
    path = tmp_path / "opencode-session.json"
    path.write_text(json.dumps(exported), encoding="utf-8")
    before = path.read_bytes()
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent.populate_context_post_run(AgentContext())
    assert path.read_bytes() == before
    return load_validated_trajectory(tmp_path / "trajectory.json")


def test_native_timing_preserves_model_boundary_parallel_tools_and_projection(tmp_path):
    from psycheval.conversion import convert_atif_trajectory, finalize_atif_conversion
    from psycheval.report.builder import project_meta_from_atif
    from psycheval.report.inference import inference_row_metrics
    from psycheval.state.catalog_projection import model_duration_ms, step_outline

    original = _native_timed_trajectory(
        tmp_path,
        {"created": 0, "streamed": 150, "completed": 600},
        {"created": 90, "ran": 100, "completed": 500},
    )
    step = original["steps"][0]
    assert step["extra"]["duration_ms"] == 150
    assert step["extra"]["duration_source"] == "opencode_native_model_call"
    assert [
        r["extra"]["execution_duration_ms"] for r in step["observation"]["results"]
    ] == [400, 180]
    assert all(
        "execution_duration_ms" not in (c.get("extra") or {})
        for c in step["tool_calls"]
    )
    assert (
        step["tool_calls"][0]["extra"]["started_at"]
        == "1970-01-01T00:00:00.100000+00:00"
    )
    canonical = finalize_atif_conversion(convert_atif_trajectory(original)).trajectory
    meta = project_meta_from_atif(canonical, {})
    assert meta["timestamp_semantics"] == "event_observed"
    assert model_duration_ms(canonical, meta) == 150
    assert (
        step_outline(canonical, meta)[0]["duration_source"]
        == "opencode_native_model_call"
    )
    assert (
        meta["steps"][0]["tool_calls"][0]["execution_duration_source"]
        == "opencode_native_tool_call"
    )
    inference = inference_row_metrics(canonical)
    assert inference["ttft_ms"] is None and inference["tps"] is None


@pytest.mark.parametrize("boundary", [None, True, "150", -1, 1.5, float("inf"), 10**30])
def test_invalid_native_boundaries_stay_unknown_without_fallback(tmp_path, boundary):
    from psycheval.report.builder import project_meta_from_atif
    from psycheval.state.catalog_projection import model_duration_ms

    trajectory = _native_timed_trajectory(
        tmp_path,
        {"created": 0, "streamed": boundary, "completed": 600},
        {"ran": boundary, "completed": 500},
    )
    step = trajectory["steps"][0]
    assert step["extra"]["duration_ms"] is None
    assert step["extra"]["timing_diagnostic"]
    assert step["observation"]["results"][0]["extra"]["execution_duration_ms"] is None
    meta = project_meta_from_atif(trajectory, {})
    assert meta["steps"][0]["duration_ms"] is None
    assert model_duration_ms(trajectory, meta) is None


@pytest.mark.parametrize("status", ["completed", "error", "running"])
def test_native_zero_and_terminal_status(tmp_path, status):
    trajectory = _native_timed_trajectory(
        tmp_path,
        {"created": 0, "streamed": 0, "completed": 600},
        {"ran": 0, "completed": 0},
        status,
    )
    step = trajectory["steps"][0]
    assert step["extra"]["duration_ms"] == 0
    extra = step["observation"]["results"][0]["extra"]
    assert extra["execution_duration_ms"] == (None if status == "running" else 0)
    assert extra["is_error"] is (status != "completed")


@pytest.mark.parametrize(
    "model_time",
    [
        {"created": 200, "streamed": 100, "completed": 600},
        {"created": 0, "streamed": 700, "completed": 600},
        {"created": 0, "completed": 600},
    ],
)
def test_reversed_or_absent_native_boundaries_do_not_use_lifecycle(
    tmp_path, model_time
):
    trajectory = _native_timed_trajectory(
        tmp_path, model_time, {"ran": 500, "completed": 100}
    )
    step = trajectory["steps"][0]
    assert step["extra"]["duration_ms"] is None
    assert step["observation"]["results"][0]["extra"]["execution_duration_ms"] is None


def test_empty_export_clears_context_without_reusing_prior_usage(tmp_path):
    exported = _exported_session()
    exported["messages"] = []
    (tmp_path / "opencode-session.json").write_text(
        json.dumps(exported), encoding="utf-8"
    )
    context = AgentContext(n_input_tokens=999, n_output_tokens=999, n_cache_tokens=999)
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent.populate_context_post_run(context)
    assert (
        context.n_input_tokens
        is context.n_output_tokens
        is context.n_cache_tokens
        is None
    )


def test_usage_alignment_failure_names_opencode(tmp_path, monkeypatch):
    from harbor.agents.installed.opencode import OpenCode
    from harbor.models.trajectories import Trajectory

    converted = Trajectory.model_validate(
        {
            "schema_version": "ATIF-v1.7",
            "session_id": "fixture",
            "agent": {"name": "opencode", "version": "1"},
            "steps": [{"step_id": 1, "source": "user", "message": "task"}],
        }
    )
    monkeypatch.setattr(
        OpenCode, "_convert_events_to_trajectory", lambda *args: converted
    )
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    with pytest.raises(ValueError, match="OpenCode completed message usage"):
        agent._convert_events_to_trajectory(
            [
                {"type": "step_start", "sessionID": "fixture"},
                {"type": "step_finish", "part": {}},
            ]
        )


@pytest.mark.parametrize(
    "failure", ["shape", "session", "model", "incomplete", "tool", "failed"]
)
def test_session_export_rejects_unbound_or_incomplete_evidence(tmp_path, failure):
    exported = _exported_session()
    stream = {"type": "text", "sessionID": "session-fixture"}
    if failure == "shape":
        exported = []
    elif failure == "session":
        exported["info"]["id"] = "another-session"
    elif failure == "model":
        exported["messages"][0]["model"]["id"] = "another-model"
    elif failure == "incomplete":
        exported["messages"][0]["time"].pop("completed")
    elif failure == "failed":
        exported["info"]["outcome"] = "failed"
    else:
        stream = {
            "type": "tool_use",
            "sessionID": "session-fixture",
            "part": {
                "id": "omitted-call",
                "tool": "forbidden_tool",
            },
        }
    (tmp_path / "opencode-session.json").write_text(
        json.dumps(exported), encoding="utf-8"
    )
    (tmp_path / "opencode.txt").write_text(json.dumps(stream), encoding="utf-8")
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    with pytest.raises(ValueError, match="OpenCode"):
        agent.populate_context_post_run(AgentContext())
    assert not (tmp_path / "trajectory.json").exists()


@pytest.mark.parametrize(
    "status,exit_code,passed",
    [
        ("completed", 0, True),
        ("completed", 1, False),
        ("completed", None, True),
        ("error", None, False),
        ("running", None, False),
    ],
)
def test_native_tool_status_and_exit_code_control_observation_gate(
    tmp_path, status, exit_code, passed
):
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent._instruction = "Fetch source"
    events = [
        {"type": "step_start", "sessionID": "fixture"},
        {
            "type": "tool_use",
            "part": {
                "type": "tool",
                "callID": "source",
                "tool": "bash",
                "state": {
                    "status": status,
                    "input": {"command": "python x-daily/fetch.py"},
                    "output": "source fetch result",
                    "metadata": {"exit": exit_code},
                },
            },
        },
        {"type": "step_finish", "part": {}},
        {"type": "step_start", "sessionID": "fixture"},
        {"type": "text", "part": {"type": "text", "text": "done"}},
        {"type": "step_finish", "part": {}},
    ]
    trajectory = agent._convert_events_to_trajectory(events)
    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                {"any": [{"tool_names": ["bash"], "argument_terms": ["x-daily"]}]}
            ]
        },
        tmp_path,
    )
    assert (
        next(check for check in checks if check["id"] == "required_call_1_observation")[
            "passed"
        ]
        is passed
    )
    observation = trajectory.steps[1].observation.results[0]
    assert observation.extra["is_error"] is not passed
    if exit_code is not None:
        assert observation.extra["exit_code"] == exit_code


@pytest.mark.parametrize("field", ["part", "state", "metadata", "status"])
@pytest.mark.parametrize("value", [None, [], "unexpected"])
def test_malformed_tool_data_is_reported_without_mutating_events(
    tmp_path, field, value
):
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent._instruction = "Fetch source"
    part = {
        "type": "tool",
        "callID": "source",
        "tool": "bash",
        "state": {"status": "completed", "input": {}, "output": "source"},
    }
    if field == "part":
        part = value
    elif field == "state":
        part["state"] = value
    else:
        part["state"][field] = value
    events = [
        {"type": "step_start", "sessionID": "fixture"},
        {"type": "tool_use", "part": part},
        {"type": "text", "part": {"type": "text", "text": "retained answer"}},
        {"type": "step_finish", "part": {}},
    ]
    original = copy.deepcopy(events)
    if field in {"part", "state"}:
        with pytest.raises(ValueError, match="Malformed OpenCode tool event"):
            agent._convert_events_to_trajectory(events)
        assert events == original
        return
    trajectory = agent._convert_events_to_trajectory(events)
    assert trajectory.steps[-1].message == "retained answer"
    assert events == original
    if field == "status":
        assert trajectory.steps[-1].observation.results[0].extra["is_error"]


@pytest.mark.parametrize("failure", ["state", "boundary", "unfinished"])
def test_malformed_forbidden_tool_event_cannot_disappear_from_scoring(
    tmp_path, failure
):
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent._instruction = "Do not run forbidden_tool"
    events = [
        {"type": "step_start", "sessionID": "fixture"},
        {
            "type": "tool_use",
            "part": {
                "type": "tool",
                "callID": "forbidden-call",
                "tool": "forbidden_tool",
                "state": None,
            },
        },
        {"type": "text", "part": {"type": "text", "text": "done"}},
        {"type": "step_finish", "part": {}},
    ]
    if failure != "state":
        events[1]["part"]["state"] = {
            "status": "completed",
            "input": {},
            "output": "done",
        }
        if failure == "boundary":
            events[-1]["part"] = None
        else:
            events.pop()
    with pytest.raises(ValueError, match="OpenCode"):
        agent._convert_events_to_trajectory(events)


@pytest.mark.skipif(
    os.environ.get("PEVAL_OPENCODE_CLI_TESTS") != "1",
    reason="opt-in preinstalled OpenCode CLI integration",
)
@pytest.mark.parametrize("variant", [None, "high"])
def test_real_cli_reads_unicode_stdin_and_uses_registered_model(tmp_path, variant):
    executable = shutil.which("opencode")
    assert executable, "Install OpenCode before enabling the CLI integration test"
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, self.headers.get("Authorization"), payload))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for delta, finish in (
                ({"role": "assistant", "content": "完成 🎉"}, None),
                ({}, "stop"),
            ):
                event = {
                    "id": "fixture-completion",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": payload["model"],
                    "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
                }
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
            usage = {
                "id": "fixture-completion",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": payload["model"],
                "choices": [],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 5,
                    "total_tokens": 105,
                    "prompt_tokens_details": {"cached_tokens": 60},
                },
            }
            self.wfile.write(f"data: {json.dumps(usage)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def scenario():
        host = make_environment(tmp_path / "host")
        agent = HostOpenCodeAgent(
            logs_dir=tmp_path / "agent logs",
            executable=executable,
            model_name="fixture/unlisted-model",
            variant=variant,
            extra_env={
                "TEST_API_KEY": "fixture-key",
                "OPENCODE_DISABLE_MODELS_FETCH": "true",
            },
            opencode_config={
                "provider": {
                    "fixture": {
                        "npm": "@ai-sdk/openai-compatible",
                        "models": {
                            "unlisted-model": {"name": "Fixture " + "x" * 40000}
                        },
                        "options": {
                            "baseURL": f"http://127.0.0.1:{server.server_port}/v1",
                            "apiKey": "{env:TEST_API_KEY}",
                        },
                    }
                }
            },
        )
        await host.start(False)
        try:
            await agent.setup(host)
            instruction = '任务 "quoted" & $HOME\n' + "中文" * 18000
            async with asyncio.timeout(60):
                await agent.run(instruction, host, AgentContext())
            context = AgentContext()
            agent.populate_context_post_run(context)
            data = load_validated_trajectory(agent.logs_dir / "trajectory.json")
            assert context.n_input_tokens == 100
            assert context.n_output_tokens == 5
            assert context.n_cache_tokens == 60
            inference = data["final_metrics"]["extra"]["model_inference"]
            assert inference["cache_prompt_tokens"] == 100
            assert inference["cache_read_tokens"] == 60
            assert inference["cache_sample_count"] == 1
            contents = []
            for _, _, payload in requests:
                for message in payload["messages"]:
                    content = message.get("content", "")
                    contents.extend(
                        [content]
                        if isinstance(content, str)
                        else [part.get("text", "") for part in content]
                    )
            assert any(instruction in text for text in contents), [
                (len(text), text[:60]) for text in contents
            ]
            assert requests
            assert all(
                path == "/v1/chat/completions"
                and key == "Bearer fixture-key"
                and payload["model"] == "unlisted-model"
                for path, key, payload in requests
            )
            exported = json.loads(
                (agent.logs_dir / "opencode-session.json").read_text(encoding="utf-8")
            )
            assert exported["info"]["model"]["id"] == "unlisted-model"
            assert exported["info"]["model"]["variant"] == (variant or "default")
        finally:
            await host.stop(True)

    try:
        asyncio.run(scenario())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("provider", ["openai", "anthropic", "fixture"])
@pytest.mark.parametrize("override", [False, True])
def test_opencode_registers_model_and_explicit_connection(tmp_path, provider, override):
    config = (
        {"provider": {provider: {"options": {"baseURL": "http://caller.invalid/v1"}}}}
        if override
        else {}
    )
    before = copy.deepcopy(config)
    agent = HostOpenCodeAgent(
        logs_dir=tmp_path / "logs",
        model_name=f"{provider}/unlisted-model",
        extra_env={f"{provider.upper()}_BASE_URL": "http://connection.invalid/v1"},
        opencode_config=config,
    )

    async def runtime_env():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        try:
            return agent._runtime_env(host)
        finally:
            await host.stop(True)

    env = asyncio.run(runtime_env())
    generated = json.loads(env["OPENCODE_CONFIG_CONTENT"])["provider"][provider]
    assert generated["models"] == {"unlisted-model": {}}
    if override or provider in {"openai", "anthropic"}:
        assert generated["options"]["baseURL"] == (
            "http://caller.invalid/v1" if override else "http://connection.invalid/v1"
        )
    else:
        assert "options" not in generated
    assert config == before


@pytest.mark.parametrize(
    "config",
    [
        [],
        {"skills": None},
        {"skills": []},
        {"skills": {"paths": "path"}},
        {"skills": {"paths": [1]}},
        {"mcp": []},
        {"provider": None},
    ],
)
def test_opencode_rejects_invalid_extended_configuration(tmp_path, config):
    with pytest.raises(ValueError, match="opencode_config"):
        HostOpenCodeAgent(
            logs_dir=tmp_path / "logs",
            model_name="fixture/model",
            opencode_config=config,
        )


@pytest.mark.parametrize("transport", ["stdio", "sse"])
@pytest.mark.parametrize("override_endpoint", [False, True])
def test_task_mcp_defaults_preserve_caller_configuration(
    tmp_path, transport, override_endpoint
):
    if transport == "stdio":
        server = MCPServerConfig(
            name="fixture", transport="stdio", command="python", args=["task-server.py"]
        )
        defaults = {"type": "local", "command": ["python", "task-server.py"]}
        caller = {"environment": {"TOKEN": "{env:TEST_API_KEY}"}}
        if override_endpoint:
            caller["command"] = ["python", "caller-server.py"]
    else:
        server = MCPServerConfig(
            name="fixture", transport="sse", url="https://task.invalid/mcp"
        )
        defaults = {"type": "remote", "url": "https://task.invalid/mcp"}
        caller = {"headers": {"Authorization": "Bearer fixture-token"}}
        if override_endpoint:
            caller["url"] = "https://caller.invalid/mcp"
    caller.update(enabled=False, timeout=4321)
    caller_only = {
        "type": "remote",
        "url": "https://extra.invalid/mcp",
        "enabled": False,
    }
    config = {"mcp": {"fixture": caller, "caller-only": caller_only}}
    before = copy.deepcopy(config)
    server_before = server.model_dump()
    agent = HostOpenCodeAgent(
        logs_dir=tmp_path / "logs",
        model_name="fixture/model",
        mcp_servers=[server],
        opencode_config=config,
    )

    async def runtime_env():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        try:
            return agent._runtime_env(host)
        finally:
            await host.stop(True)

    env = asyncio.run(runtime_env())
    generated = json.loads(env["OPENCODE_CONFIG_CONTENT"])["mcp"]
    assert generated == {"fixture": {**defaults, **caller}, "caller-only": caller_only}
    assert config == before
    assert server.model_dump() == server_before


@pytest.mark.parametrize(
    "outcome",
    [
        "success",
        "error",
        "exit",
        "empty",
        "cancel",
        "export_error",
        "export_timeout",
        "no_session",
        "multiple_sessions",
    ],
)
def test_native_opencode_run_retains_evidence_and_isolates_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    script = tmp_path / "fake opencode.py"
    exported = _exported_session()
    if outcome == "empty":
        exported["messages"] = []
    script.write_text(
        "import json,os,sys,time,psutil\n"
        "from pathlib import Path\n"
        f"outcome={outcome!r}\n"
        "if sys.argv[1:3]==['session','export']:\n"
        " Path('export-process.tmp').write_text(json.dumps({'pid':os.getpid(),'created_at':psutil.Process().create_time()}))\n"
        " Path('export-process.tmp').replace('export.pid')\n"
        " print('export diagnostic',file=sys.stderr,flush=True)\n"
        " if outcome=='export_error': sys.exit(7)\n"
        " if outcome=='export_timeout': time.sleep(60)\n"
        f" print({json.dumps(exported, ensure_ascii=False)!r}); sys.exit()\n"
        "prompt=sys.stdin.buffer.read().decode('utf-8')\n"
        "config=json.loads(os.environ['OPENCODE_CONFIG_CONTENT'])\n"
        "Path('observed.json').write_text(json.dumps({'prompt':prompt,"
        "'config':config,'cwd':os.getcwd(),'argv':sys.argv[1:],"
        "'home':os.environ['HOME'],'data':os.environ['XDG_DATA_HOME'],"
        "'key':os.environ['TEST_API_KEY']}),encoding='utf-8')\n"
        "print(json.dumps({'type':'text',**({} if outcome=='no_session' else {'sessionID':'session-fixture'}),'part':{'type':'text','text':'完成 🎉'}},"
        "ensure_ascii=False),flush=True)\n"
        f"outcome={outcome!r}\n"
        "if outcome=='multiple_sessions': print(json.dumps({'type':'text','sessionID':'other-session'}),flush=True)\n"
        "if outcome=='cancel': time.sleep(60)\n"
        "if outcome=='error': print(json.dumps({'type':'error','error':{'name':'APIError'}}))\n"
        "if outcome=='exit': sys.exit(2)\n",
        encoding="utf-8",
    )

    async def scenario() -> None:
        host = make_environment(tmp_path / "host")
        logs = tmp_path / "agent logs"
        agent = HostOpenCodeAgent(
            logs_dir=logs,
            executable=sys.executable,
            model_name="fixture/model",
            variant="high",
            skills_dir="/harbor/skills",
            mcp_servers=[
                MCPServerConfig(name="fixture", transport="stdio", command="python")
            ],
            extra_env={"TEST_API_KEY": "fixture-key", "PYTHONIOENCODING": "utf-8"},
            opencode_config={"permission": {"webfetch": "deny"}},
        )
        await host.start(force_build=False)
        try:
            await host.ensure_dirs(["/harbor/skills"], chmod=False)
            await agent.setup(host)
            execute = host.exec_argv
            convert = agent._convert_events_to_trajectory
            conversions = []
            parse = agent._parse_stdout
            parses = []

            def counted_parse():
                parses.append(1)
                return parse()

            def counted(events):
                conversions.append(1)
                return convert(events)

            monkeypatch.setattr(agent, "_convert_events_to_trajectory", counted)
            monkeypatch.setattr(agent, "_parse_stdout", counted_parse)
            agent._trajectory = (
                object()
            )  # A previous invocation's cache must be cleared.

            async def fake_cli(argv, **kwargs):
                if argv[1:3] == ["session", "export"]:
                    assert kwargs["timeout_sec"] == 30
                    if outcome == "export_timeout":
                        kwargs["timeout_sec"] = 0.2
                    return await execute([argv[0], str(script), *argv[1:]], **kwargs)
                assert not Path(argv[3]).is_relative_to(agent.logs_dir)
                assert not Path(argv[3]).is_relative_to(host.work_dir)
                return await execute([*argv[:5], str(script), *argv[5:]], **kwargs)

            monkeypatch.setattr(host, "exec_argv", fake_cli)
            instruction = '任务 "quoted" & $HOME\n' + "中文" * 18000
            if outcome == "cancel":
                run = asyncio.create_task(agent.run(instruction, host, AgentContext()))
                async with asyncio.timeout(20):
                    while (
                        not (logs / "opencode.txt").exists()
                        or not (logs / "opencode.txt").stat().st_size
                    ):
                        await asyncio.sleep(0.02)
                run.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await run
            elif outcome in {"error", "exit"}:
                with pytest.raises(NonZeroAgentExitCodeError):
                    await agent.run(instruction, host, AgentContext())
            elif outcome == "empty":
                with pytest.raises(RuntimeError, match="no completed messages"):
                    await agent.run(instruction, host, AgentContext())
            elif outcome == "export_error":
                with pytest.raises(
                    RuntimeError, match="OpenCode Session export failed"
                ):
                    await agent.run(instruction, host, AgentContext())
            elif outcome == "export_timeout":
                with pytest.raises(TimeoutError):
                    await agent.run(instruction, host, AgentContext())
            elif outcome in {"no_session", "multiple_sessions"}:
                with pytest.raises(
                    RuntimeError, match="OpenCode emitted no unique Session"
                ):
                    await agent.run(instruction, host, AgentContext())
            else:
                await agent.run(instruction, host, AgentContext())
                context = AgentContext()
                agent.populate_context_post_run(context)
                agent.populate_context_post_run(AgentContext())
                assert len(conversions) == 1
                assert len(parses) == 1
                assert context.n_output_tokens == 7
                assert context.cost_usd == 0.25
                trajectory = load_validated_trajectory(logs / "trajectory.json")
                raw_trajectory = (logs / "trajectory.json").read_bytes()
                assert not raw_trajectory.startswith(b"\xef\xbb\xbf")
                assert "完成 🎉".encode("utf-8") in raw_trajectory
                assert trajectory["steps"][-1]["message"] == "完成 🎉"
            if outcome != "success":
                assert agent._trajectory is None
            if outcome in {"export_error", "export_timeout"}:
                pid = host.work_dir / "export.pid"
                if pid.exists():
                    assert_process_exited(**json.loads(pid.read_text()))
                diagnostic = logs / "opencode-export.stderr.log"
                if outcome == "export_error":
                    assert "export diagnostic" in diagnostic.read_text(encoding="utf-8")
                diagnostic.rename(diagnostic.with_suffix(".closed"))
            observed = json.loads(
                (host.work_dir / "observed.json").read_text(encoding="utf-8")
            )
            assert observed["prompt"] == instruction
            assert Path(observed["cwd"]) == host.work_dir
            assert not Path(observed["home"]).is_relative_to(logs)
            assert Path(observed["home"]).is_relative_to(
                host.runtime_directory(f"opencode-{agent._runtime_id}")
            )
            assert not Path(observed["data"]).is_relative_to(logs)
            assert observed["config"]["permission"] == {"webfetch": "deny"}
            assert observed["config"]["skills"]["paths"] == [
                str(host.native_path("/harbor/skills"))
            ]
            assert observed["config"]["mcp"]["fixture"]["command"] == ["python"]
            assert "--standalone" in observed["argv"]
            assert (
                observed["argv"][observed["argv"].index("--model") + 1]
                == "fixture/model#high"
            )
            assert observed["key"] == "fixture-key"
            if outcome != "no_session":
                assert "session-fixture" in (logs / "opencode.txt").read_text(
                    encoding="utf-8"
                )
        finally:
            await host.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.parametrize("phase", ["setup", "run"])
@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
def test_generated_opencode_environment_wins_inside_harbor_scope(
    tmp_path, monkeypatch, phase, outcome
):
    path_keys = (
        "HOME",
        "USERPROFILE",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_CACHE_HOME",
        "OPENCODE_CONFIG_DIR",
        "OPENCODE_CONFIG",
    )
    extra = {key: str(tmp_path / "caller" / key) for key in path_keys}
    extra.update(
        OPENCODE_CONFIG_CONTENT='{"permission":"deny"}', TEST_API_KEY="fixture-key"
    )
    keys = (*path_keys, "OPENCODE_CONFIG_CONTENT", "TEST_API_KEY")
    observe = f"json.dumps({{key:os.environ.get(key) for key in {keys!r}}})"
    script = tmp_path / "scoped-opencode.py"
    output = (
        "fixture-version"
        if phase == "setup"
        else '{"type":"text","sessionID":"session-fixture"}'
    )
    script.write_text(
        "import json,os,sys,time\nfrom pathlib import Path\n"
        f"if sys.argv[1:3]==['session','export']: print({json.dumps(_exported_session())!r}); sys.exit()\n"
        f"Path('observed-env.json').write_text({observe},encoding='utf-8')\n"
        f"print({output!r},flush=True)\n"
        f"if {outcome!r}=='cancel': time.sleep(30)\n"
        f"sys.exit(2 if {outcome!r}=='error' else 0)\n",
        encoding="utf-8",
    )

    async def scenario():
        host = make_environment(tmp_path / "host")
        logs = tmp_path / "agent logs"
        agent = HostOpenCodeAgent(
            logs_dir=logs,
            executable=sys.executable,
            model_name="fixture/model",
            extra_env=extra,
            opencode_config={"permission": {"webfetch": "deny"}},
        )
        before = copy.deepcopy(agent.extra_env)
        await host.start(False)
        execute = host.exec_argv

        async def fake_cli(argv, **kwargs):
            actual = (
                [argv[0], str(script)]
                if phase == "setup"
                else [argv[0], str(script), *argv[1:]]
                if argv[1:3] == ["session", "export"]
                else [*argv[:5], str(script), *argv[5:]]
            )
            return await execute(actual, **kwargs)

        async def invoke():
            if phase == "setup":
                await agent.setup(host)
            else:
                await agent.run("fixture instruction", host, AgentContext())

        monkeypatch.setattr(host, "exec_argv", fake_cli)
        try:
            with host.scoped_exec_env(agent.extra_env):
                if outcome == "cancel":
                    task = asyncio.create_task(invoke())
                    log = logs / (
                        "opencode-setup.log" if phase == "setup" else "opencode.txt"
                    )
                    try:
                        async with asyncio.timeout(10):
                            while not log.exists() or not log.stat().st_size:
                                await asyncio.sleep(0.02)
                    finally:
                        task.cancel()
                        with pytest.raises(asyncio.CancelledError):
                            await task
                elif outcome == "error":
                    expected = (
                        RuntimeError if phase == "setup" else NonZeroAgentExitCodeError
                    )
                    with pytest.raises(expected):
                        await invoke()
                else:
                    await invoke()
                observed = json.loads(
                    (host.work_dir / "observed-env.json").read_text(encoding="utf-8")
                )
                for key in path_keys:
                    assert not Path(observed[key]).is_relative_to(logs), key
                config = json.loads(observed["OPENCODE_CONFIG_CONTENT"])
                assert config["provider"]["fixture"]["models"] == {"model": {}}
                assert config["permission"] == {"webfetch": "deny"}
                assert observed["TEST_API_KEY"] == "fixture-key"
                outer = await execute(
                    [sys.executable, "-c", f"import os,json; print({observe})"]
                )
                assert json.loads(outer.stdout) == extra
            assert agent.extra_env == before
        finally:
            await host.stop(True)

    asyncio.run(asyncio.wait_for(scenario(), 20))


def test_opencode_version_mismatch_and_missing_executable(tmp_path: Path) -> None:
    async def scenario() -> None:
        host = make_environment(tmp_path / "host")
        await host.start(force_build=False)
        try:
            for executable, version, error in (
                (sys.executable, "wrong-version", RuntimeError),
                ("missing-opencode-fixture", None, FileNotFoundError),
            ):
                agent = HostOpenCodeAgent(
                    logs_dir=tmp_path / "logs",
                    executable=executable,
                    version=version,
                    model_name="fixture/model",
                )
                with pytest.raises(error):
                    await agent.setup(host)
        finally:
            await host.stop(delete=True)

    asyncio.run(scenario())


def test_agents_with_shared_env_keep_trial_runtime_paths_isolated(tmp_path):
    shared_env = {"TEST_API_KEY": "fixture-key", "HOME": "caller-home"}

    async def scenario():
        host = make_environment(tmp_path / "host")
        agents = [
            HostOpenCodeAgent(
                logs_dir=tmp_path / f"agent-{i}",
                executable=sys.executable,
                model_name="fixture/model",
                extra_env=shared_env,
            )
            for i in range(2)
        ]
        await host.start(force_build=False)
        try:
            # Serial setup catches a previous Trial polluting the next one.
            for agent in agents:
                await agent.setup(host)
                assert agent.extra_env == shared_env
            runtime = [agent._runtime_env(host) for agent in agents]
            for agent, env in zip(agents, runtime, strict=True):
                assert not Path(env["HOME"]).is_relative_to(agent.logs_dir)
                assert env["TEST_API_KEY"] == "fixture-key"
                assert agent.extra_env == shared_env
            assert runtime[0]["HOME"] != runtime[1]["HOME"]
            assert shared_env == {"TEST_API_KEY": "fixture-key", "HOME": "caller-home"}
        finally:
            await host.stop(delete=True)

    asyncio.run(scenario())


def test_opencode_probe_timeout_retains_diagnostic_and_isolated_env(
    tmp_path, monkeypatch
):
    async def scenario():
        host = make_environment(tmp_path / "host")
        logs = tmp_path / "logs"
        agent = HostOpenCodeAgent(
            logs_dir=logs, executable=sys.executable, model_name="fixture/model"
        )
        await host.start(force_build=False)
        try:

            async def timeout(argv, *, env, timeout_sec):
                assert argv[-1] == "--version"
                assert timeout_sec == 30
                assert not Path(env["HOME"]).is_relative_to(logs)
                callback = host._output_callback()
                await callback("startup diagnostic\n", "stderr")
                raise TimeoutError

            monkeypatch.setattr(host, "exec_argv", timeout)
            with pytest.raises(RuntimeError, match="version probe.*30-second"):
                await agent.setup(host)
            assert (logs / "opencode-setup.log").read_text() == "startup diagnostic\n"
        finally:
            await host.stop(delete=True)

    asyncio.run(scenario())


def test_host_options_preflight_matches_constructor(tmp_path):
    import pytest

    from psycheval.harbor.opencode import HostOpenCodeAgent

    options = HostOpenCodeAgent.parse_options(
        {"executable": "custom-opencode", "variant": "high"}
    )
    agent = HostOpenCodeAgent(
        logs_dir=tmp_path,
        model_name="fixture/model",
        executable="custom-opencode",
        variant="high",
    )
    assert options.executable == agent.executable == "custom-opencode"
    assert agent.options.variant == "high"
    assert not agent.capabilities.bridges
    for config in (
        {"skills": []},
        {"mcp": []},
        {"provider": []},
        {"skills": {"paths": [1]}},
    ):
        with pytest.raises(ValueError, match="opencode_config"):
            HostOpenCodeAgent.parse_options({"opencode_config": config})
        with pytest.raises(ValueError, match="opencode_config"):
            HostOpenCodeAgent(
                logs_dir=tmp_path, model_name="fixture/model", opencode_config=config
            )
    with pytest.raises(ValueError, match="disable_web_search"):
        HostOpenCodeAgent.parse_options({"disable_web_search": True})
    with pytest.raises(ValueError, match="disable_web_search"):
        HostOpenCodeAgent(
            logs_dir=tmp_path, model_name="fixture/model", disable_web_search=True
        )
