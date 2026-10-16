from __future__ import annotations

import asyncio
import gzip
import io
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from harbor.agents.installed.base import NonZeroAgentExitCodeError
from harbor.models.agent.context import AgentContext
from harbor.models.trajectories import Trajectory
from harbor.models.trial.config import MCPServerConfig

from psycheval.harbor.acp_agent import HostACPAgent
from psycheval.harbor.acp_evidence import convert, outcome
from psycheval.harbor.acp_protocol import (
    MAX_FRAME,
    EvidenceBudget,
    ProtocolError,
    StrictTransport,
    decode,
)
from psycheval.harbor.verifier._calls import forbidden_tool_check, required_call_checks
from tests.harbor.environment_support import make_environment

PEER = Path(__file__).resolve().parents[1] / "fixtures/acp_peer.py"
linux = pytest.mark.skipif(sys.platform != "linux", reason="Linux ACP ownership")


@linux
def test_real_psutil_process_identity_survives_linux_boot_time_adjustment(monkeypatch):
    import psutil
    from psutil import _pslinux

    before = psutil.Process(os.getpid())
    wall_birth = before.create_time()
    original = _pslinux.boot_time
    monkeypatch.setattr(_pslinux, "boot_time", lambda: original() + 60)
    after = psutil.Process(os.getpid())
    assert after.create_time() == wall_birth + 60
    assert before == after
    assert hash(before) == hash(after)
    assert {before: "owned"}[after] == "owned"


@pytest.mark.parametrize("metadata", ["x", ["x"], 1, True])
def test_codebuddy_malformed_metadata_is_rejected_categorically(tmp_path, metadata):
    async def scenario():
        reader = asyncio.StreamReader()
        frame = {
            "jsonrpc": "2.0",
            "method": "session/update",
            "params": {
                "sessionId": "fixture",
                "update": {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": "fixture"},
                    "_meta": metadata,
                },
            },
        }
        reader.feed_data((json.dumps(frame) + "\n").encode())
        reader.feed_eof()
        summary = {}
        transport = StrictTransport(
            reader, None, tmp_path, summary, result_format="codebuddy"
        )
        transport.expected_model, transport.phase = "fixture-model", "prompt"
        try:
            with pytest.raises(ProtocolError, match="invalid known ACP payload"):
                await transport.receive()
            assert summary["protocol_complete"] is False
        finally:
            transport.finish()

    asyncio.run(scenario())


@pytest.mark.parametrize("summary_kind", ["missing", "unbound", "malformed"])
def test_harness_bootstrap_failure_retains_bounded_diagnostics(
    tmp_path, monkeypatch, summary_kind
):
    from harbor.environments.base import ExecResult
    from harbor.models.task.config import TaskOS

    from psycheval.harbor import acp_agent

    def unexpected_observer(*args):
        raise AssertionError("no callback must not start an observer")

    monkeypatch.setattr(acp_agent, "_SessionUpdateRelay", unexpected_observer)

    staging, logs = tmp_path / "staging", tmp_path / "logs"
    staging.mkdir()
    diagnostic = "Traceback: fixture bootstrap failure\n"

    class Host:
        work_dir = tmp_path
        os = TaskOS.LINUX

        def runtime_directory(self, name):
            return staging

        async def exec_argv(self, argv, **kwargs):
            if summary_kind != "missing":
                (staging / "acp.summary.json").write_text(
                    "{}" if summary_kind == "unbound" else "{broken",
                    encoding="utf-8",
                )
            return ExecResult(return_code=1, stdout="x" * 1024, stderr=diagnostic)

    host = Host()
    agent = HostACPAgent(logs_dir=logs, argv=[sys.executable], max_evidence_bytes=128)
    agent._setup_host, agent._state, agent._child_env = host, tmp_path, {}
    monkeypatch.setattr(agent, "_host", lambda environment: environment)
    monkeypatch.setattr(agent, "_check_runtime", lambda environment: None)
    with pytest.raises((RuntimeError, ValueError)):
        asyncio.run(agent.run("task", host, AgentContext()))
    assert (logs / "acp.harness.stderr.log").read_text() == diagnostic
    assert sum(path.stat().st_size for path in logs.glob("acp.harness.*.log")) <= 128
    assert not (staging / "request.json").exists()
    assert not (logs / "trajectory.json").exists()


@linux
def test_harness_bootstrap_real_process_traceback_is_retained(tmp_path, monkeypatch):
    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        agent = HostACPAgent(logs_dir=host.trial_paths.agent_dir, argv=[sys.executable])
        original = host.exec_argv

        async def early_crash(argv, **kwargs):
            return await original(
                [
                    sys.executable,
                    "-c",
                    "raise RuntimeError('fixture bootstrap failure')",
                ],
                **kwargs,
            )

        try:
            await agent.setup(host)
            monkeypatch.setattr(host, "exec_argv", early_crash)
            with pytest.raises(RuntimeError, match="setup or cleanup"):
                await agent.run("task", host, AgentContext())
            assert (
                "RuntimeError: fixture bootstrap failure"
                in (agent.logs_dir / "acp.harness.stderr.log").read_text()
            )
            with pytest.raises(RuntimeError, match="unsafe"):
                agent.populate_context_post_run(AgentContext())
        finally:
            await host.stop(True)

    asyncio.run(scenario())


def test_canonical_name_extension_is_validated_before_sdk_projection():
    schema = pytest.importorskip("acp.schema")
    from psycheval.harbor.acp_protocol import sdk_validators, validate_payload

    assert "name" not in schema.ToolCallStart.model_fields
    value = {
        "sessionId": "current",
        "update": {
            "sessionUpdate": "tool_call",
            "toolCallId": "call-1",
            "title": "Human readable title",
        },
    }
    validator = sdk_validators()["session/update"]
    validate_payload(validator, value)
    value["update"]["name"] = "bash"
    validate_payload(validator, value)
    # The SDK ignores this extension; canonical identity comes from raw evidence.
    assert "name" not in schema.ToolCallStart.model_validate(
        value["update"]
    ).model_dump(by_alias=True)
    for invalid in (None, False, 3, "", []):
        value["update"]["name"] = invalid
        with pytest.raises(ProtocolError, match="tool name"):
            validate_payload(validator, value)


@pytest.mark.parametrize(
    "frame",
    [
        b"{}\n",
        b'{"jsonrpc":"2.0","id":true,"result":{}}\n',
        b'{"jsonrpc":"2.0","id":1,"result":{},"result":{}}\n',
        b'{"jsonrpc":"2.0","id":1,"result":NaN}\n',
        b'{"jsonrpc":"2.0","id":1,"result":1e400}\n',
        b'{"jsonrpc":"2.0","id":1,"result":{}}',
    ],
)
def test_wire_rejects_invalid_records(frame):
    with pytest.raises(ProtocolError):
        decode(frame)


def test_summary_metadata_shares_wire_admission_budget():
    summary = {"protocol_complete": True}
    budget = EvidenceBudget(summary, maximum=16)
    budget.write(io.BytesIO(), b"wire")
    with pytest.raises(ProtocolError):
        budget.retain("metadata" * 2)
    assert summary["protocol_complete"] is False
    assert summary["evidence_limit_exceeded"] is True


@pytest.mark.parametrize(
    "maximum,frames",
    [(64 * 1024**2, 65536), (512 * 1024**2, 524288), (4 * 1024**3, 1048576)],
)
def test_frame_admission_scales_with_byte_budget_and_remains_bounded(maximum, frames):
    summary = {"protocol_complete": True}
    budget = EvidenceBudget(summary, maximum=maximum)
    assert budget.maximum_frames == frames == summary["max_evidence_frames"]
    budget.frames = frames - 1
    budget.admit_frame()
    with pytest.raises(ProtocolError):
        budget.admit_frame()
    assert summary["protocol_complete"] is False


def test_inline_image_frame_above_one_mib_is_retained_without_truncation(
    tmp_path,
):
    message = {
        "jsonrpc": "2.0",
        "method": "session/update",
        "params": {
            "sessionId": "s",
            "update": {
                "sessionUpdate": "tool_call_update",
                "toolCallId": "c",
                "content": [
                    {
                        "type": "content",
                        "content": {
                            "type": "image",
                            "data": "A" * (1100 * 1024),
                            "mimeType": "image/png",
                        },
                    }
                ],
            },
        },
    }
    wire = json.dumps(message, separators=(",", ":")).encode() + b"\n"
    assert 1024**2 < len(wire) < MAX_FRAME

    async def run():
        reader = asyncio.StreamReader(limit=MAX_FRAME + 1)
        reader.feed_data(wire)
        reader.feed_eof()
        summary = {"protocol_complete": True}
        transport = StrictTransport(
            reader, None, tmp_path, summary, EvidenceBudget(summary)
        )
        try:
            assert await transport.receive() == message
        finally:
            transport.finish()

    asyncio.run(run())
    assert gzip.decompress((tmp_path / "acp.stdout.ndjson.gz").read_bytes()) == wire


def test_wire_frame_limit_is_still_enforced():
    wire = (
        json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"data": "A" * MAX_FRAME}}
        ).encode()
        + b"\n"
    )
    with pytest.raises(ProtocolError, match="oversized"):
        decode(wire)


def test_long_stream_retention_and_projection_share_the_declared_admission(tmp_path):
    from psycheval.harbor.acp_evidence import _events

    path = tmp_path / "events.ndjson"
    event = (
        json.dumps({"direction": "receive", "phase": "prompt", "message": {}}).encode()
        + b"\n"
    )
    with gzip.open(path, "wb") as stream:
        for _ in range(65537):
            stream.write(event)
    assert sum(1 for _ in _events(path, 512 * 1024**2)) == 65537
    with pytest.raises(ProtocolError, match="limits"):
        sum(1 for _ in _events(path, 64 * 1024**2))


def test_failed_wire_send_rolls_back_correlation_and_phase(tmp_path, monkeypatch):
    from psycheval.harbor import acp_protocol

    monkeypatch.setattr(acp_protocol, "sdk_validators", lambda result_format="acp": {})

    class Writer:
        def write(self, data):
            raise OSError("fixture write failure")

    summary = {"protocol_complete": True}
    transport = StrictTransport(None, Writer(), tmp_path, summary)
    try:
        with pytest.raises(OSError):
            asyncio.run(
                transport.send(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "session/load",
                        "params": {
                            "sessionId": "s",
                            "cwd": "/workspace",
                            "mcpServers": [],
                        },
                    }
                )
            )
        assert transport.pending == {}
        assert transport.phase == "setup" and transport.replay_id is None
        assert summary["protocol_complete"] is False
    finally:
        transport.finish()


def test_legal_control_dense_wire_frame_roundtrips_retained_event(
    tmp_path, monkeypatch
):
    from psycheval.harbor import acp_protocol

    monkeypatch.setattr(acp_protocol, "sdk_validators", lambda result_format="acp": {})
    text = "\x01" * 150000
    message = {
        "jsonrpc": "2.0",
        "method": "session/update",
        "params": {
            "sessionId": "current",
            "update": {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": text},
            },
        },
    }
    wire = (
        json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode()
    assert len(wire) < MAX_FRAME
    summary = {
        "prompt_submitted": True,
        "protocol_complete": True,
        "session_id": "current",
    }
    transport = StrictTransport(None, None, tmp_path, summary)
    try:
        transport.phase = "prompt"
        transport.record("receive", decode(wire))
    finally:
        transport.finish()
    _seal_evidence(tmp_path, summary)
    trajectory = convert(
        tmp_path, summary, "task", {"name": "fixture", "version": "1"}, "acp"
    )
    assert trajectory.steps[-1].message == text


def test_interrupted_publication_cannot_admit_partial_logs(tmp_path, monkeypatch):
    invocation, logs = tmp_path / "invocation", tmp_path / "logs"
    invocation.mkdir()
    logs.mkdir()
    _current_evidence(
        invocation,
        [
            {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "answer"},
            }
        ],
    )
    agent = HostACPAgent(logs_dir=logs, argv=[sys.executable])
    agent._invocation_id = "fixture-invocation"
    original = shutil.move

    def failed_move(source, target):
        if source.name == "acp.events.ndjson.gz":
            raise OSError("fixture publication failure")
        return original(source, target)

    monkeypatch.setattr(shutil, "move", failed_move)
    with pytest.raises(OSError):
        agent._publish_call(invocation)
    with pytest.raises(RuntimeError, match="unsafe"):
        agent.populate_context_post_run(AgentContext())
    assert not (logs / "acp.summary.json").exists()
    assert not (logs / "trajectory.json").exists()


def _seal_evidence(directory, summary):
    from psycheval.harbor.acp_protocol import EVIDENCE_FILES, evidence_manifest

    for name in EVIDENCE_FILES:
        path = directory / name
        data = path.read_bytes() if path.exists() else b""
        if not data.startswith(b"\x1f\x8b"):
            path.write_bytes(gzip.compress(data, mtime=0))
    summary.update(
        invocation_id="fixture-invocation", evidence_files=evidence_manifest(directory)
    )
    (directory / "acp.summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return summary


def _current_evidence(directory, updates):
    (directory / "acp.events.ndjson.gz").write_text(
        "".join(
            json.dumps(
                {
                    "direction": "receive",
                    "phase": "prompt",
                    "message": {
                        "method": "session/update",
                        "params": {"sessionId": "current", "update": update},
                    },
                }
            )
            + "\n"
            for update in updates
        ),
        encoding="utf-8",
    )
    summary = {
        "prompt_submitted": True,
        "session_id": "current",
        "protocol_complete": True,
        "cleanup_complete": True,
    }
    return _seal_evidence(directory, summary)


def test_context_population_preserves_caller_metadata(tmp_path):
    _current_evidence(
        tmp_path,
        [
            {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "answer"},
            }
        ],
    )
    agent = HostACPAgent(logs_dir=tmp_path, argv=[sys.executable])
    agent._invocation_id = "fixture-invocation"
    assert agent.name() == "acp"
    context = AgentContext(metadata={"caller": "retained"})
    agent.populate_context_post_run(context)
    trajectory = json.loads((tmp_path / "trajectory.json").read_text(encoding="utf-8"))
    assert trajectory["agent"]["name"] == "acp"
    assert context.metadata == {
        "caller": "retained",
        "acp_session_id": "current",
        "acp_stop_reason": None,
    }


def test_overlapping_invocation_rejects_and_cancellation_releases_agent(
    tmp_path, monkeypatch
):
    async def run():
        agent = HostACPAgent(logs_dir=tmp_path, argv=[sys.executable])
        entered, release = asyncio.Event(), asyncio.Event()
        instructions = []

        async def invocation(action, instruction, environment):
            instructions.append((action, instruction))
            entered.set()
            await release.wait()

        monkeypatch.setattr(agent, "_run_invocation", invocation)
        first = asyncio.create_task(agent.run("first", None, AgentContext()))
        await entered.wait()
        try:
            with pytest.raises(RuntimeError, match="already active"):
                await agent.resume("overlap", None, AgentContext())
            assert instructions == [("run", "first")]
        finally:
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
        release.set()
        await agent.resume("after cancellation", None, AgentContext())
        assert instructions == [("run", "first"), ("resume", "after cancellation")]

    asyncio.run(run())


def test_evidence_conversion_streams_retained_records(tmp_path, monkeypatch):
    summary = _current_evidence(
        tmp_path,
        [
            {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "answer"},
            }
        ],
    )
    original = Path.read_text

    def bounded_read(path, *args, **kwargs):
        if path.name == "acp.events.ndjson.gz":
            raise AssertionError("retained events must not be read as one string")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", bounded_read)
    trajectory = convert(
        tmp_path, summary, "task", {"name": "fixture", "version": "1"}, "acp"
    )
    assert trajectory.steps[-1].message == "answer"


@pytest.mark.parametrize(
    "event",
    [
        {},
        {"direction": "receive", "phase": "prompt", "message": []},
        {
            "direction": "receive",
            "phase": "prompt",
            "message": {
                "method": "session/update",
                "params": {
                    "sessionId": "current",
                    "update": {"sessionUpdate": "agent_message_chunk", "content": None},
                },
            },
        },
        {
            "direction": "receive",
            "phase": "prompt",
            "message": {"method": "session/update", "params": {}},
        },
        {
            "direction": "receive",
            "phase": "prompt",
            "message": {
                "method": "session/update",
                "params": {
                    "sessionId": "current",
                    "update": {
                        "sessionUpdate": "tool_call",
                        "toolCallId": "one",
                        "rawInput": {},
                    },
                },
            },
        },
    ],
)
def test_malformed_retained_evidence_is_a_protocol_failure(tmp_path, event):
    summary = _current_evidence(tmp_path, [])
    (tmp_path / "acp.events.ndjson.gz").write_text(json.dumps(event) + "\n")
    _seal_evidence(tmp_path, summary)
    with pytest.raises(ProtocolError):
        convert(tmp_path, summary, "task", {"name": "fixture", "version": "1"}, "acp")


@pytest.mark.parametrize("mode", ["stdout-flood", "stderr-flood"])
def test_host_acp_evidence_budget_fails_closed_and_settles(tmp_path, mode):
    async def run():
        host = make_environment(
            tmp_path,
            environment_kwargs={
                "workdir_root": tmp_path / "work",
                "workspace_baseline": "none",
            },
        )
        await host.start(False)
        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir,
            argv=[sys.executable, str(PEER), mode],
            max_evidence_bytes=16 * 1024,
            shutdown_timeout_sec=8,
        )
        try:
            await agent.setup(host)
            with pytest.raises(NonZeroAgentExitCodeError):
                await agent.run("bounded evidence", host, AgentContext())
            summary = json.loads((agent.logs_dir / "acp.summary.json").read_text())
            assert summary["cleanup_complete"]
            assert summary["protocol_complete"] is False
            assert summary["evidence_limit_exceeded"]
            assert (
                sum(
                    (agent.logs_dir / name).stat().st_size
                    for name in (
                        "acp.stdin.ndjson.gz",
                        "acp.stdout.ndjson.gz",
                        "acp.events.ndjson.gz",
                        "acp.stderr.log.gz",
                    )
                )
                <= 16 * 1024
            )
        finally:
            await host.stop(True)

    asyncio.run(run())


@linux
def test_host_acp_handshake_has_one_setup_deadline(tmp_path):
    async def run():
        host = make_environment(
            tmp_path,
            environment_kwargs={
                "workdir_root": tmp_path / "work",
                "workspace_baseline": "none",
            },
        )
        await host.start(False)
        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir,
            argv=[sys.executable, str(PEER), "slow-setup"],
            handshake_timeout_sec=0.45,
            shutdown_timeout_sec=8,
        )
        try:
            await agent.setup(host)
            with pytest.raises(RuntimeError, match="setup or cleanup"):
                await agent.run("one deadline", host, AgentContext())
            summary = json.loads((agent.logs_dir / "acp.summary.json").read_text())
            assert summary["error_type"] == "TimeoutError"
            assert summary["prompt_submitted"] is False
            assert summary["cleanup_complete"]
        finally:
            await host.stop(True)

    asyncio.run(run())


@linux
def test_host_acp_forced_cleanup_signals_each_descendant_once(tmp_path):
    import psutil

    async def run():
        host = make_environment(
            tmp_path,
            environment_kwargs={
                "workdir_root": tmp_path / "work",
                "workspace_baseline": "none",
            },
        )
        await host.start(False)
        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir,
            argv=[sys.executable, str(PEER), "stubborn"],
            shutdown_timeout_sec=7,
        )
        try:
            await agent.setup(host)
            await agent.run("settle descendants", host, AgentContext())
            assert (host.work_dir / "term-count").read_text() == "t"
            assert not psutil.pid_exists(
                int((host.work_dir / "descendant.pid").read_text())
            )
            assert json.loads((agent.logs_dir / "acp.summary.json").read_text())[
                "cleanup_complete"
            ]
        finally:
            await host.stop(True)

    asyncio.run(run())


@pytest.mark.parametrize(
    "value, expected",
    [
        ({"status": "exited", "exit_code": 0, "signal": None}, "completed"),
        ({"status": "exited", "exit_code": 2, "signal": None}, "failed"),
        ({"status": "timed_out", "exit_code": None, "signal": None}, "failed"),
        ({"status": "running", "exit_code": None, "signal": None}, "incomplete"),
        ({"exit_code": 0}, "incomplete"),
    ],
)
def test_rsiversi_bash_requires_terminal_success(value, expected):
    _, result = outcome(
        {
            "name": "bash",
            "status": "completed",
            "rawOutput": {"is_error": False, "content": [], "value": value},
        },
        "rsiversi",
    )
    assert result["status"] == expected
    assert result["is_error"] == (expected != "completed")


@pytest.mark.parametrize("name", ["bash", "Bash", "execute_bash", "custom"])
@pytest.mark.parametrize(
    "value, expected",
    [
        ({"status": "timed_out", "exit_code": None, "signal": None}, "failed"),
        ({"status": "exited", "exit_code": 2, "signal": None}, "failed"),
        ({"status": "running", "job_id": "pending"}, "incomplete"),
        ({"status": "exited", "exit_code": 0, "signal": None}, "completed"),
    ],
)
def test_execution_outcome_is_independent_of_tool_name(name, value, expected):
    _, extra = outcome(
        {
            "name": name,
            "status": "completed",
            "rawOutput": {
                "is_error": False,
                "content": [],
                "value": value,
            },
        },
        "rsiversi",
    )
    assert extra["status"] == expected
    assert extra["is_error"] == (expected != "completed")


@pytest.mark.parametrize("result_format", ["acp", "rsiversi"])
def test_raw_envelope_does_not_supply_observation_terms(tmp_path, result_format):
    updates = [
        {
            "sessionUpdate": "tool_call",
            "toolCallId": "one",
            "name": "bash",
            "title": "Command",
            "status": "completed",
            "rawInput": {},
            "rawOutput": {
                "is_error": False,
                "content": [],
                "value": {"status": "exited", "exit_code": 0, "signal": None},
            },
        }
    ]
    summary = _current_evidence(tmp_path, updates)
    trajectory = convert(
        tmp_path, summary, "task", {"name": "fixture", "version": "1"}, result_format
    )
    for term in ("error", "exit_code", "exited", "signal"):
        checks = required_call_checks(
            trajectory,
            [{"any": [{"tool_names": ["bash"], "observation_terms": [term]}]}],
        )
        assert checks[-1]["passed"] is False
    assert (
        trajectory.steps[-1].observation.results[0].extra["raw_output"]
        == updates[0]["rawOutput"]
    )


def test_native_process_observation_contains_stream_text_only():
    content, extra = outcome(
        {
            "name": "execute_bash",
            "status": "completed",
            "rawOutput": {
                "is_error": False,
                "content": [
                    {"type": "text", "text": "real text [status: exited; signal: none]"}
                ],
                "value": {
                    "status": "exited",
                    "exit_code": 0,
                    "signal": None,
                    "stdout": {"text": "real text"},
                    "stderr": {"text": "warning"},
                },
            },
        },
        "rsiversi",
    )
    assert content == "real text\nwarning"
    assert extra["status"] == "completed"


@pytest.mark.parametrize("damage", ["missing", "empty", "substitution"])
def test_retained_event_integrity_fails_closed(tmp_path, damage):
    summary = _current_evidence(
        tmp_path,
        [
            {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "answer"},
            }
        ],
    )
    path = tmp_path / "acp.events.ndjson.gz"
    if damage == "missing":
        path.unlink()
    elif damage == "empty":
        path.write_bytes(b"")
    else:
        path.write_bytes(
            gzip.compress(
                gzip.decompress(path.read_bytes()).replace(b"answer", b"forged")
            )
        )
    with pytest.raises(ProtocolError):
        convert(tmp_path, summary, "task", {"name": "fixture", "version": "1"}, "acp")


def test_cleanup_failure_does_not_publish_trajectory(tmp_path):
    summary = _current_evidence(
        tmp_path,
        [
            {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "unsafe answer"},
            }
        ],
    )
    summary["cleanup_complete"] = False
    (tmp_path / "acp.summary.json").write_text(json.dumps(summary))
    agent = HostACPAgent(logs_dir=tmp_path, argv=[sys.executable])
    agent._invocation_id = summary["invocation_id"]
    with pytest.raises(RuntimeError, match="unsafe"):
        agent.populate_context_post_run(AgentContext())
    assert not (tmp_path / "trajectory.json").exists()


def test_invalid_host_invocation_cannot_reuse_prior_evidence(tmp_path):
    summary = _current_evidence(
        tmp_path,
        [
            {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "old answer"},
            }
        ],
    )
    agent = HostACPAgent(logs_dir=tmp_path, argv=[sys.executable])
    agent._invocation_id, agent._instruction = summary["invocation_id"], "old task"
    with pytest.raises(TypeError):
        asyncio.run(agent.run("new task", object(), AgentContext()))
    with pytest.raises(RuntimeError):
        agent.populate_context_post_run(AgentContext())
    assert not (tmp_path / "trajectory.json").exists()


@pytest.mark.parametrize(
    "option",
    [
        {},
        None,
        {"id": []},
        {"id": "x", "type": "select"},
        {"id": "x", "type": "select", "currentValue": "a", "options": [None]},
        {"id": "x", "type": "select", "currentValue": "a", "options": [{}]},
        {"id": "x", "type": "select", "currentValue": [], "options": [{"value": []}]},
        {"id": "x", "type": "select", "currentValue": 1, "options": [{"value": 1}]},
    ],
)
def test_extra_config_options_fail_categorically(option):
    pytest.importorskip("acp")
    from psycheval.harbor.acp_protocol import sdk_validators, validate_payload

    with pytest.raises(ProtocolError):
        validate_payload(
            sdk_validators()["initialize"],
            {
                "protocolVersion": 1,
                "agentCapabilities": {},
                "authMethods": [],
                "configOptions": [option],
            },
        )


@linux
def test_deleted_host_runtime_requires_a_new_agent(tmp_path):
    async def run():
        host = make_environment(
            tmp_path,
            environment_kwargs={
                "workdir_root": tmp_path / "work",
                "workspace_baseline": "none",
            },
        )
        await host.start(False)
        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir, argv=[sys.executable, str(PEER)]
        )
        try:
            await agent.setup(host)
            await host.stop(True)
            await host.start(False)
            with pytest.raises(RuntimeError, match="runtime"):
                await agent.setup(host)
            with pytest.raises(RuntimeError, match="runtime"):
                await agent.run("new lifecycle", host, AgentContext())
            assert not (agent.logs_dir / "acp.summary.json").exists()
        finally:
            await host.stop(True)

    asyncio.run(run())


@linux
def test_cleanup_cancel_is_bounded(tmp_path, monkeypatch):
    from psycheval.harbor import acp_harness

    monkeypatch.setattr(acp_harness, "FORCED_CLEANUP_RESERVE_SEC", 0.4)
    monkeypatch.setattr(acp_harness, "KILL_REAP_RESERVE_SEC", 0.15)

    class Connection:
        async def close(self):
            pass

        async def cancel(self, **kwargs):
            await asyncio.Event().wait()

    async def run():
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "import time; time.sleep(120)",
            stdin=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        prompt = asyncio.create_task(asyncio.Event().wait())
        summary = {"session_id": "current"}
        try:
            await asyncio.wait_for(
                acp_harness._settle(
                    process, Connection(), prompt, asyncio.Event(), 0.8, summary
                ),
                1.5,
            )
            assert summary["cleanup_complete"]
        finally:
            if process.returncode is None:
                process.kill()
            await process.wait()
            prompt.cancel()
            await asyncio.gather(prompt, return_exceptions=True)

    asyncio.run(run())


@linux
def test_cleanup_signal_identity_survives_wall_clock_changes(monkeypatch):
    from types import SimpleNamespace

    import psutil

    from psycheval.harbor import acp_harness

    signals = []
    alive = True
    wall_clock = 0

    class Child:
        pid = 4243

        def __hash__(self):
            return hash((self.pid, "kernel-start-time"))

        def __eq__(self, other):
            return isinstance(other, Child)

        def create_time(self):
            nonlocal wall_clock
            wall_clock += 1
            return wall_clock

        def terminate(self):
            signals.append("term")

        def kill(self):
            nonlocal alive
            signals.append("kill")
            alive = False

        def ppid(self):
            return -1

    import threading

    loop_thread = threading.get_ident()

    def children(**kwargs):
        assert threading.get_ident() != loop_thread
        return [Child()] if alive else []

    parent = SimpleNamespace(pid=4242, children=children)
    monkeypatch.setattr(psutil, "Process", lambda: parent)
    monkeypatch.setattr(acp_harness, "FORCED_CLEANUP_RESERVE_SEC", 3)
    monkeypatch.setattr(acp_harness, "KILL_REAP_RESERVE_SEC", 2.8)

    async def run():
        async def exited():
            return 0

        process = SimpleNamespace(pid=4241, stdin=None, returncode=0, wait=exited)
        summary = {}
        await acp_harness._settle(process, None, None, asyncio.Event(), 3, summary)
        assert summary["cleanup_complete"]
        assert signals == ["term", "kill"]

    asyncio.run(asyncio.wait_for(run(), 5))


@linux
def test_cleanup_stop_interrupts_cooperative_wait():
    from psycheval.harbor.acp_harness import _settle

    async def run():
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "import time; time.sleep(120)",
            stdin=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        stopping, summary = asyncio.Event(), {}
        timer = asyncio.get_running_loop().call_later(0.05, stopping.set)
        try:
            await asyncio.wait_for(
                _settle(process, None, None, stopping, 8, summary), 1.5
            )
            assert summary["cleanup_complete"]
        finally:
            timer.cancel()
            if process.returncode is None:
                process.kill()
            await process.wait()

    asyncio.run(run())


@pytest.mark.parametrize("first_stage", ["protocol", "process", "pipes", "tasks"])
def test_cleanup_task_timeout_preserves_first_failure(first_stage):
    from types import SimpleNamespace

    from psycheval.harbor import acp_harness

    async def scenario():
        before = asyncio.all_tasks()
        primary = OSError("earlier cleanup failure")
        process = SimpleNamespace(stdin=None, stdout=None, returncode=0)
        attempted = []

        class Connection:
            async def close(self):
                attempted.append("protocol")
                if first_stage == "protocol":
                    raise primary

        class Adapter:
            async def settle(self, process, timeout):
                attempted.append("process")
                if first_stage == "process":
                    raise primary

        async def stderr():
            if first_stage == "pipes":
                raise primary

        started = asyncio.Event()

        async def delayed_prompt():
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                # Require the task-settlement deadline to cancel the waiter again.
                await asyncio.Event().wait()

        prompt = asyncio.create_task(delayed_prompt())
        draining = asyncio.create_task(stderr())
        await started.wait()
        summary = {"protocol_complete": False}
        try:
            with pytest.raises(
                TimeoutError if first_stage == "tasks" else OSError
            ) as caught:
                await acp_harness._settle(
                    process,
                    Connection(),
                    prompt,
                    asyncio.Event(),
                    0.1,
                    summary,
                    Adapter(),
                    stderr_task=draining,
                )
            if first_stage != "tasks":
                assert caught.value is primary
            assert summary["cleanup_error_stage"] == first_stage
            assert summary["cleanup_complete"] is False
            assert attempted == ["protocol", "process"]
            assert prompt.done() and draining.done()
            assert asyncio.all_tasks() == before
        finally:
            prompt.cancel()
            await asyncio.gather(prompt, draining, return_exceptions=True)

    asyncio.run(scenario())


@linux
def test_handshake_primary_failure_survives_stop_and_close_error(tmp_path, monkeypatch):
    import acp

    from psycheval.harbor import acp_harness

    class Connection:
        def __init__(self, client):
            self.client = client

        async def initialize(self, **kwargs):
            self.client.stopping.set()
            raise ProtocolError("fixture failure")

        async def close(self):
            raise OSError("fixture close failure")

    monkeypatch.setattr(
        acp, "connect_to_agent", lambda client, transport: Connection(client)
    )
    monkeypatch.setattr(acp_harness, "_subreaper", lambda: None)
    config = {
        "invocation_id": "current",
        "argv": [sys.executable, str(PEER)],
        "cwd": str(tmp_path),
        "state": str(tmp_path),
        "child_env": {},
        "permission_mode": "allow",
        "max_evidence_bytes": 65536,
        "handshake_timeout_sec": 1,
        "shutdown_timeout_sec": 6,
    }
    path = tmp_path / "request.json"
    path.write_text(json.dumps(config))
    assert asyncio.run(acp_harness.run(path)) == 1
    summary = json.loads((tmp_path / "acp.summary.json").read_text())
    assert summary["error_type"] == "ProtocolError"
    assert summary["cleanup_error_type"] == "OSError"
    assert summary["cleanup_complete"] is False
    assert summary["cleanup_error_stage"] == "protocol"


@linux
@pytest.mark.parametrize(
    "mode", ["normal", "background", "no-name", "allow", "deny", "http", "resume"]
)
def test_host_acp_resume_and_owned_cleanup(tmp_path, mode):
    async def run():
        host = make_environment(
            tmp_path,
            environment_kwargs={
                "workdir_root": tmp_path / "work",
                "workspace_baseline": "none",
            },
        )
        await host.start(force_build=False)
        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir,
            argv=[sys.executable, str(PEER), mode],
            config_options={"model": "b"},
            permission_mode="deny" if mode == "deny" else "allow",
            tool_result_format="rsiversi",
            shutdown_timeout_sec=8,
            mcp_servers=[
                MCPServerConfig(
                    name="fixture",
                    transport="streamable-http",
                    url="https://mcp.example.test",
                )
            ]
            if mode == "http"
            else [],
        )
        try:
            await agent.setup(host)
            previous_paths = None
            for action in (agent.run, agent.resume):
                context = AgentContext()
                await action("instruction 中文", host, context)
                assert context.is_empty()
                agent.populate_context_post_run(context)
                summary = json.loads((agent.logs_dir / "acp.summary.json").read_text())
                assert (
                    summary["cleanup_complete"]
                    and summary["config_options"][0]["currentValue"] == "b"
                )
                trajectory = json.loads(
                    (agent.logs_dir / "trajectory.json").read_text()
                )
                calls = [
                    c for s in trajectory["steps"] for c in s.get("tool_calls", [])
                ]
                assert [c["tool_call_id"] for c in calls] == ["call-1"]
                if mode == "resume" and action == agent.resume:
                    events = [
                        json.loads(line)
                        for line in gzip.decompress(
                            (agent.logs_dir / "acp.events.ndjson.gz").read_bytes()
                        ).splitlines()
                    ]
                    methods = [
                        event["message"].get("method")
                        for event in events
                        if event["direction"] == "send"
                    ]
                    assert "session/resume" in methods and "session/load" not in methods
                assert calls[0]["extra"]["title"] == "Human readable title"
                assert calls[0]["extra"]["acp_canonical_name"] == (mode != "no-name")
                evidence = Trajectory.model_validate(trajectory)
                check = required_call_checks(
                    evidence, [{"any": [{"tool_names": ["bash"]}]}]
                )[0]
                assert check["passed"] == (mode != "no-name")
                assert forbidden_tool_check(evidence, ["other"])["passed"] == (
                    mode != "no-name"
                )
                assert "中文🙂" in json.dumps(trajectory, ensure_ascii=False)
                paths = json.loads((host.work_dir / "state-paths.json").read_text())
                if previous_paths is not None:
                    assert paths == previous_paths
                previous_paths = paths
                assert len(paths["XDG_RUNTIME_DIR"].encode()) <= 28
                if mode == "background":
                    import psutil

                    assert not psutil.pid_exists(
                        int((host.work_dir / "descendant.pid").read_text())
                    )
                if mode in {"allow", "deny"}:
                    permission = json.loads(
                        (host.work_dir / "permission.json").read_text()
                    )
                    assert permission["outcome"]["optionId"] == (
                        "no" if mode == "deny" else "yes"
                    )
            calls = list(agent._state.parent.glob("acp-call-*"))
            assert len(calls) == 1, "resume must reuse bounded call staging"
            assert not list(calls[0].glob("acp.*")), "published logs leave call staging"
            runtime = Path(paths["XDG_RUNTIME_DIR"])
            other = make_environment(tmp_path / "other")
            with pytest.raises(RuntimeError, match="original configured Host"):
                await agent.resume("foreign Host", other, AgentContext())
        finally:
            await host.stop(delete=True)
        assert not runtime.exists()

    asyncio.run(run())


@linux
@pytest.mark.skipif(
    not os.environ.get("PEVAL_RSIVERSI_ACP"),
    reason="opt-in real RSIversi binary with local provider",
)
def test_rsiversi_binary_local_tools_cold_restore_and_cancel(tmp_path, monkeypatch):
    requests = []

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(body)
            messages = body["messages"]
            user = max(i for i, m in enumerate(messages) if m["role"] == "user")
            instruction = messages[user]["content"]
            if isinstance(instruction, list):
                instruction = " ".join(p.get("text", "") for p in instruction)
            if any(m["role"] == "tool" for m in messages[user + 1 :]):
                delta, reason = (
                    {"role": "assistant", "content": "fixture complete 中文"},
                    "stop",
                )
            else:
                command = (
                    "printf started > cancel-started; sleep 120"
                    if "slow" in instruction
                    else "exit 7"
                    if "failure" in instruction
                    else "printf verified > fixture.txt"
                )
                delta = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "fixture-" + str(len(requests)),
                            "type": "function",
                            "function": {
                                "name": "bash",
                                "arguments": json.dumps({"command": command}),
                            },
                        }
                    ],
                }
                reason = "tool_calls"
            if "exhaust" in instruction or (
                "recover" in instruction
                and "split large files" not in json.dumps(messages)
            ):
                delta = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "discarded-" + str(len(requests)),
                            "type": "function",
                            "function": {
                                "name": "bash",
                                "arguments": json.dumps(
                                    {"command": "printf forbidden > truncated.txt"}
                                ),
                            },
                        }
                    ],
                }
                reason = "length"
            payload = [
                json.dumps({"choices": [{"delta": delta, "finish_reason": None}]}),
                json.dumps(
                    {
                        "choices": [{"delta": {}, "finish_reason": reason}],
                        "usage": {"prompt_tokens": 2, "completion_tokens": 3},
                    }
                ),
            ]
            data = (
                "".join(f"data: {p}\n\n" for p in payload) + "data: [DONE]\n\n"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    seed = tmp_path / "seed"
    (seed / "rsi/host-profiles/fixture").mkdir(parents=True)
    (seed / "rsi/application-profiles/test-acp").mkdir(parents=True)
    (seed / "rsi/settings.json").write_text(
        json.dumps(
            {
                "rsi.agent": {
                    "default_model": {
                        "deployment": "fixture",
                        "model": "fixture-model",
                    },
                    "output_budgets": [
                        {
                            "model": {
                                "deployment": "fixture",
                                "model": "fixture-model",
                            },
                            "max_output_tokens": 12000,
                        }
                    ],
                }
            }
        )
    )
    (seed / "rsi/host-profiles/fixture/host.profile.toml").write_text(
        f'format=1\n[[steps]]\nkind="plugin"\nid="fixture-provider"\nplugin="rsi.ai.provider.openai-compatible"\n[steps.config]\ndeployment="fixture"\nendpoint="http://127.0.0.1:{server.server_port}"\npath="/v1/chat/completions"\nallow_image_input=false\ncredential={{owner="rsi.ai.provider.openai-compatible",slot="default"}}\n[steps.config.language_models.fixture-model]\ncontext_window_tokens=128000\ndefault_output_reserve_tokens=4096\nmax_output_reserve_tokens=16384\n'
    )
    (seed / "rsi/application-profiles/test-acp/application.profile.toml").write_text(
        'format=1\n[[steps]]\nkind="plugin"\nid="service"\nplugin="rsi.application.acp-service"\nconfig={host_profile="fixture"}\n[[steps]]\nkind="plugin"\nid="application"\nplugin="rsi.application.acp"\n'
    )
    for key in (
        "DEEPSEEK_API_KEY",
        "RSI_DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "RSI_OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    async def run():
        host = make_environment(
            tmp_path / "host",
            environment_kwargs={
                "workdir_root": tmp_path / "work",
                "workspace_baseline": "none",
                "persistent_env": {"RSI_OPENAI_COMPATIBLE_API_KEY": "local-fixture"},
            },
        )
        await host.start(False)
        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir,
            argv=[os.environ["PEVAL_RSIVERSI_ACP"], "--profile", "test-acp"],
            config_dir=seed,
            config_options={
                "model": '{"deployment":"fixture","model":"fixture-model"}'
            },
            tool_result_format="rsiversi",
        )
        try:
            await agent.setup(host)
            sessions = []
            for action, instruction in [
                (agent.run, "success"),
                (agent.run, "failure"),
                (agent.resume, "success after restart"),
                (agent.resume, "recover after truncation"),
            ]:
                context = AgentContext()
                await action(instruction, host, context)
                agent.populate_context_post_run(context)
                sessions.append(context.metadata["acp_session_id"])
                evidence = Trajectory.model_validate_json(
                    (agent.logs_dir / "trajectory.json").read_text()
                )
                check = required_call_checks(
                    evidence, [{"any": [{"tool_names": ["bash"]}]}]
                )[-1]
                assert check["passed"] == (instruction != "failure")
                assert json.loads((agent.logs_dir / "acp.summary.json").read_text())[
                    "cleanup_complete"
                ]
            assert sessions[0] != sessions[1] == sessions[2]
            task = asyncio.create_task(
                agent.resume("slow cancellation", host, AgentContext())
            )
            async with asyncio.timeout(30):
                while not (host.work_dir / "cancel-started").exists():
                    await asyncio.sleep(0.02)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert json.loads((agent.logs_dir / "acp.summary.json").read_text())[
                "cleanup_complete"
            ]
            assert (host.work_dir / "fixture.txt").read_text() == "verified"
            with pytest.raises(NonZeroAgentExitCodeError):
                await agent.resume("exhaust token recovery", host, AgentContext())
            summary = json.loads((agent.logs_dir / "acp.summary.json").read_text())
            assert summary["stop_reason"] == "max_tokens"
            assert summary["cleanup_complete"]
            assert not (host.work_dir / "truncated.txt").exists()
        finally:
            await host.stop(True)

    try:
        asyncio.run(run())
        assert requests and all(r["model"] == "fixture-model" for r in requests)
        assert all(r["max_tokens"] == 12000 for r in requests)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@linux
@pytest.mark.parametrize("multi", [False, True])
@pytest.mark.parametrize("mode", ["normal", "unconfirmed"])
def test_actual_harbor_trial_scores_current_acp_evidence(tmp_path, multi, mode):
    task = tmp_path / "task"
    source = PEER.parent / "harbor-single-step"
    shutil.copytree(source, task)
    grader = {
        "required_calls": [
            {
                "any": [
                    {
                        "tool_names": ["bash"],
                        "argument_values": {"command": "echo fixture"},
                        "observation_terms": ["ok"],
                    }
                ]
            }
        ],
        "final_terms": ["中文"],
    }
    (task / "tests/grader.json").write_text(json.dumps(grader))
    if multi:
        (task / "task.toml").write_text(
            'schema_version="1.4"\nmulti_step_reward_strategy="mean"\n[task]\nname="fixture/acp"\n[environment]\nworkdir="/app"\n[agent]\ntimeout_sec=20\n[verifier]\ntimeout_sec=20\n[[steps]]\nname="first"\nmin_reward=1.0\n[[steps]]\nname="second"\n'
        )
        for name in ("first", "second"):
            step = task / "steps" / name
            step.mkdir(parents=True)
            (step / "instruction.md").write_text("fixture step 中文")
    command = [
        sys.executable,
        "-c",
        "from harbor.cli.main import app; app()",
        "run",
        "--path",
        str(task),
        "--agent",
        "psycheval.harbor.acp_agent:HostACPAgent",
        "--agent-kwarg",
        "argv=" + json.dumps([sys.executable, str(PEER), mode]),
        "--agent-kwarg",
        'config_options={"model":"b"}',
        "--agent-kwarg",
        "tool_result_format=rsiversi",
        "--env",
        "psycheval.harbor.environment:HostEnvironment",
        "--environment-kwarg",
        'host_access={"filesystem":true,"process":true}',
        "--environment-kwarg",
        f"workdir_root={tmp_path / 'work'}",
        "--verifier-import-path",
        "psycheval.harbor.verifier.host:HostVerifier",
        "--jobs-dir",
        str(tmp_path / "jobs"),
        "--job-name",
        "acp",
        "--quiet",
        "--yes",
    ]
    if multi:
        command.append("--resume-trajectory")
    completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (result_path,) = (tmp_path / "jobs/acp").glob("*/result.json")
    result = json.loads(result_path.read_text())
    if mode == "unconfirmed":
        assert result["exception_info"] is not None
        assert result["verifier_result"] is None
        assert not list(result_path.parent.rglob("score.json"))
        assert not list(result_path.parent.rglob("trajectory.json"))
        return
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result["exception_info"] is None, result
    assert result["verifier_result"]["rewards"]["reward"] == 1.0
    if multi:
        assert len(result["step_results"]) == 2
        sessions = [
            s["agent_result"]["metadata"]["acp_session_id"]
            for s in result["step_results"]
        ]
        assert sessions[0] == sessions[1]


@linux
@pytest.mark.skipif(not shutil.which("bwrap"), reason="Bubblewrap is unavailable")
def test_workbuddy_namespace_maps_python_literals_and_isolates_app(tmp_path):
    from psycheval.harbor.workbuddy_namespace import NamespaceEnvironment

    async def run():
        host = make_environment(
            tmp_path,
            environment_kwargs={
                "workdir_root": tmp_path / "work",
                "workspace_baseline": "none",
            },
        )
        await host.start(False)
        try:
            private = host.runtime_directory("workbuddy-namespace-fixture")
            wrapped = NamespaceEnvironment(host, host.environment_dir.parent, private)
            result = await wrapped.exec(
                'python -c \'from pathlib import Path; Path("/app/result").write_text("owned"); Path("/workspace/result").write_text(Path("/app/result").read_text())\'',
                env={"PATH": os.environ["PATH"]},
            )
            assert result.return_code == 0, result.stderr
            assert (host.work_dir / "result").read_text() == "owned"
            assert (private / "app/result").read_text() == "owned"
            assert wrapped.native_path("/app/result") == private / "app/result"
            source = tmp_path / "private-tests"
            source.mkdir()
            (source / "gold.txt").write_text("private grader")
            await wrapped.upload_dir(source, "/tests/nested")
            assert (
                wrapped.native_path("/tests/nested") / "gold.txt"
            ).read_text() == "private grader"
            result = await wrapped.exec("cat /tests/nested/gold.txt")
            assert result.return_code == 0 and result.stdout == "private grader"
            assert wrapped.native_path("/workspace/result") == host.work_dir / "result"
            copied = tmp_path / "download.txt"
            await wrapped.download_file("/app/result", copied)
            assert copied.read_text() == "owned"
            await wrapped.upload_file(source / "gold.txt", "/tests/single.txt")
            assert (
                wrapped.native_path("/tests/single.txt").read_text() == "private grader"
            )
            downloaded = tmp_path / "downloaded-tests"
            await wrapped.download_dir("/tests/nested", downloaded)
            assert (downloaded / "gold.txt").read_text() == "private grader"
            with pytest.raises(ValueError, match="unsupported"):
                wrapped.native_path("/tests/../outside")
        finally:
            await host.stop(True)

    asyncio.run(run())


def test_evidence_preserves_nontext_content_and_interleaved_tool_identity(tmp_path):
    updates = [
        {
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "image", "data": "eA==", "mimeType": "image/png"},
        },
        {
            "sessionUpdate": "tool_call",
            "toolCallId": "one",
            "name": "first",
            "title": "First",
            "status": "pending",
            "rawInput": {"x": 1},
        },
        {
            "sessionUpdate": "tool_call",
            "toolCallId": "two",
            "name": "second",
            "title": "Second",
            "status": "pending",
            "rawInput": {"x": 2},
        },
        {
            "sessionUpdate": "tool_call_update",
            "toolCallId": "two",
            "status": "failed",
            "rawOutput": {"reason": "rejected"},
        },
        {
            "sessionUpdate": "tool_call_update",
            "toolCallId": "one",
            "status": "completed",
            "rawOutput": {"value": 3},
        },
    ]
    (tmp_path / "acp.events.ndjson.gz").write_text(
        "\n".join(
            json.dumps(
                {
                    "direction": "receive",
                    "phase": "prompt",
                    "message": {
                        "method": "session/update",
                        "params": {"sessionId": "current", "update": update},
                    },
                }
            )
            for update in updates
        )
        + "\n"
    )
    trajectory = convert(
        tmp_path,
        _seal_evidence(
            tmp_path,
            {
                "prompt_submitted": True,
                "session_id": "current",
                "protocol_complete": True,
            },
        ),
        "instruction",
        {"name": "fixture", "version": "1"},
        "acp",
    ).to_json_dict()
    step = trajectory["steps"][1]
    assert step["extra"]["acp_content"] == [updates[0]]
    assert [call["function_name"] for call in step["tool_calls"]] == ["first", "second"]
    assert [
        (result["source_call_id"], result["extra"]["status"])
        for result in step["observation"]["results"]
    ] == [("one", "completed"), ("two", "failed")]


@linux
@pytest.mark.parametrize("mode", ["unconfirmed", "sse", "malformed", "eof", "cancel"])
def test_host_acp_failures_preserve_prefix_and_settle(tmp_path, mode):
    async def run():
        host = make_environment(
            tmp_path,
            environment_kwargs={
                "workdir_root": tmp_path / "work",
                "workspace_baseline": "none",
            },
        )
        await host.start(force_build=False)
        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir,
            argv=[sys.executable, str(PEER), mode],
            config_options={"model": "b"},
            shutdown_timeout_sec=8,
            mcp_servers=[
                MCPServerConfig(
                    name="fixture", transport="sse", url="https://mcp.example.test"
                )
            ]
            if mode == "sse"
            else [],
        )
        context = AgentContext()
        try:
            await agent.setup(host)
            task = asyncio.create_task(agent.run("test", host, context))
            if mode == "cancel":
                for _ in range(300):
                    if (host.work_dir / "descendant.pid").exists():
                        break
                    await asyncio.sleep(0.02)
                assert (host.work_dir / "descendant.pid").exists()
                task.cancel()
            with pytest.raises(
                (RuntimeError, NonZeroAgentExitCodeError, asyncio.CancelledError)
            ):
                await asyncio.wait_for(task, 20)
            summary = json.loads((agent.logs_dir / "acp.summary.json").read_text())
            assert summary["cleanup_complete"]
            if mode in {"unconfirmed", "sse"}:
                assert not summary["prompt_submitted"]
                with pytest.raises(RuntimeError):
                    agent.populate_context_post_run(context)
                assert not (agent.logs_dir / "trajectory.json").exists()
            else:
                agent.populate_context_post_run(context)
                assert (agent.logs_dir / "trajectory.json").exists()
                if mode in {"malformed", "eof"}:
                    assert not summary["protocol_complete"]
                if mode == "cancel":
                    import psutil

                    assert not psutil.pid_exists(
                        int((host.work_dir / "descendant.pid").read_text())
                    )
        finally:
            await host.stop(delete=True)

    asyncio.run(run())
