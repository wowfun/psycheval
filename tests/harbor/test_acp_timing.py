import asyncio
import gzip
import json

import pytest

from psycheval.harbor.acp_evidence import convert
from psycheval.harbor.acp_protocol import (
    EVIDENCE_FILES,
    StrictTransport,
    evidence_manifest,
)


def chunk(text="answer"):
    return {
        "sessionUpdate": "agent_message_chunk",
        "content": {"type": "text", "text": text},
    }


def call(status, identity="a", initial=False):
    return {
        "sessionUpdate": "tool_call" if initial else "tool_call_update",
        "toolCallId": identity,
        "status": status,
        "title": "Read",
        "name": "Read",
    }


def trajectory(tmp_path, updates, *, clock=True):
    records = [
        {
            "direction": "receive",
            "phase": "prompt",
            "elapsed_ns": time,
            "message": {
                "method": "session/update",
                "params": {"sessionId": "current", "update": update},
            },
        }
        for time, update in updates
    ]
    summary = {
        "prompt_submitted": True,
        "session_id": "current",
        "invocation_id": "test",
        "protocol_complete": True,
        "cleanup_complete": True,
    }
    if clock:
        summary["client_clock"] = (
            clock
            if isinstance(clock, dict)
            else {
                "version": 1,
                "origin_utc": "2026-10-18T00:00:00+00:00",
                "invocation_id": "test",
            }
        )
    for name in EVIDENCE_FILES:
        data = (
            "".join(json.dumps(r) + "\n" for r in records)
            if name == "acp.events.ndjson.gz"
            else ""
        )
        (tmp_path / name).write_bytes(gzip.compress(data.encode()))
    summary["evidence_files"] = evidence_manifest(tmp_path)
    return convert(
        tmp_path, summary, "task", {"name": "fixture", "version": "1"}, "acp"
    ).model_dump(mode="json")


def test_output_and_parallel_tools_use_client_boundaries(tmp_path):
    updates = [
        (0, chunk("one")),
        (2_000_000, chunk("two")),
        (3_000_000, call("pending", initial=True)),
        (4_000_000, call("in_progress")),
        (5_000_000, call("pending", "b", True)),
        (6_000_000, call("in_progress")),
        (8_000_000, call("completed")),
        (9_000_000, call("completed")),
        (10_000_000, call("failed", "b")),
        (11_000_000, chunk()),
    ]
    for index, (_, update) in enumerate(updates):
        update["_meta"] = {"timestamp": f"2026-10-18T00:00:{59 - index:02d}Z"}
    result = trajectory(tmp_path, updates)
    assert result["extra"]["timestamp_semantics"] == "event_observed"
    step = result["steps"][1]
    assert step["extra"]["duration_ms"] == 2
    assert step["extra"]["duration_source"] == "acp_client_observed_output"
    first, second = step["observation"]["results"]
    assert first["extra"]["execution_duration_ms"] == 4
    assert (
        first["extra"]["execution_duration_source"] == "acp_client_observed_in_progress"
    )
    assert second["extra"]["execution_duration_ms"] == 5
    assert (
        second["extra"]["execution_duration_source"] == "acp_client_observed_lifecycle"
    )
    assert "execution_duration_ms" not in step["tool_calls"][0]["extra"]
    assert result["steps"][2]["extra"]["duration_ms"] is None


@pytest.mark.parametrize(
    "updates,expected",
    [
        ([(0, call("in_progress", initial=True)), (1, call("completed"))], 0),
        ([(0, call(None, initial=True)), (2_000_000, call("completed"))], 2),
        ([(0, call("completed", initial=True))], None),
        ([(0, call("pending", initial=True))], None),
        (
            [
                (0, call("in_progress", initial=True)),
                (2, call("completed")),
                (3, call("in_progress")),
            ],
            None,
        ),
        ([(2, call("in_progress", initial=True)), (1, call("completed"))], None),
        ([(0, call("in_progress", initial=True)), (None, call("completed"))], None),
    ],
)
def test_zero_and_unknown_boundaries(tmp_path, updates, expected):
    step = trajectory(tmp_path, updates)["steps"][1]
    extra = step["observation"]["results"][0]["extra"]
    assert extra["execution_duration_ms"] == expected
    if expected is None:
        assert extra["timing_diagnostic"]


def test_legacy_evidence_does_not_infer_vendor_or_event_times(tmp_path):
    result = trajectory(tmp_path, [(0, chunk()), (1_000_000, chunk())], clock=False)
    assert result["steps"][1]["timestamp"] is None
    assert not (result["steps"][1].get("extra") or {}).get("duration_ms")


def test_invocation_clock_mismatch_is_unknown_without_changing_result(tmp_path):
    result = trajectory(
        tmp_path,
        [(0, call("pending", initial=True)), (5_000_000, call("completed"))],
        clock={
            "version": 1,
            "origin_utc": "2026-10-18T00:00:00Z",
            "invocation_id": "previous",
        },
    )
    assert result["extra"]["timing_diagnostic"] == "invalid_client_clock"
    extra = result["steps"][1]["observation"]["results"][0]["extra"]
    assert extra["status"] == "completed"
    assert extra["execution_duration_ms"] is None


def test_receive_clock_precedes_evidence_processing_and_is_invocation_local(
    tmp_path, monkeypatch
):
    from psycheval.harbor import acp_protocol

    now = [1_000_000]
    monkeypatch.setattr(acp_protocol.time, "monotonic_ns", lambda: now[0])

    async def run():
        for invocation in ("first", "resumed"):
            directory = tmp_path / invocation
            directory.mkdir()
            reader = asyncio.StreamReader()
            message = {
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {"sessionId": "current", "update": chunk()},
            }
            reader.feed_data((json.dumps(message) + "\n").encode())
            summary = {"invocation_id": invocation}
            transport = StrictTransport(reader, None, directory, summary)
            write = transport.raw_in.write

            def slow_write(data):
                now[0] += 10_000_000
                write(data)

            monkeypatch.setattr(transport.raw_in, "write", slow_write)
            now[0] += 100_000
            assert await transport.receive() == message
            transport.finish()
            event = json.loads(
                gzip.decompress((directory / "acp.events.ndjson.gz").read_bytes())
            )
            assert event["elapsed_ns"] == 100_000
            assert event["message"] == message
            assert summary["client_clock"]["invocation_id"] == invocation

    asyncio.run(run())


def test_observed_timing_survives_atif_report_projection(tmp_path):
    from psycheval.conversion import convert_atif_trajectory, finalize_atif_conversion
    from psycheval.report.builder import project_meta_from_atif
    from psycheval.report.metrics import latency_metrics

    original = trajectory(
        tmp_path,
        [
            (0, chunk()),
            (1_000_000, chunk()),
            (2_000_000, call("pending", initial=True)),
            (7_000_000, call("completed")),
            (8_000_000, chunk()),
        ],
    )
    canonical = finalize_atif_conversion(convert_atif_trajectory(original)).trajectory
    meta = project_meta_from_atif(canonical, {})
    step = meta["steps"][1]
    assert step["duration_ms"] == 1
    assert step["duration_source"] == "acp_client_observed_output"
    assert step["tool_calls"][0]["execution_duration_ms"] == 5
    assert (
        step["tool_calls"][0]["execution_duration_source"]
        == "acp_client_observed_lifecycle"
    )
    assert meta["steps"][2]["duration_ms"] is None
    assert "model_duration_ms" not in latency_metrics(canonical, meta)
