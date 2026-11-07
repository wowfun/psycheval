import json
from copy import deepcopy

import pytest

from psycheval.harbor import measurements as m
from psycheval.harbor.agents.dsh_measurements import first_output, normalize


def test_large_valid_producer_metadata_does_not_abort_report():
    from psycheval.report.measurements import construct

    trajectory = {"agent": {"name": "a" * 2000, "version": "版本" * 2000}, "steps": []}
    values, provenance = construct(trajectory, {})
    assert values["agent_steps"] == 0
    assert all(
        len(m.encoded(item)) <= m.MAX_PROVENANCE_BYTES for item in provenance.values()
    )


def test_huge_numeric_evidence_is_rejected_without_overflow():
    assert m.number(10**400) is None
    with pytest.raises(ValueError, match="invalid_measurement_record"):
        m._safe_record({"type": "end", "end_ms": 10**400})


def test_failed_publication_removes_temporary_files(tmp_path):
    directory = tmp_path / "agent"
    with pytest.raises(ValueError, match="unapproved_measurement_fields"):
        m.publish(
            directory,
            [{"type": "end", "prompt": "private"}],
            producer={},
            invocation_id="i",
            session_id="s",
            capabilities={},
            complete=True,
        )
    assert list(directory.iterdir()) == []


@pytest.mark.parametrize(
    "bad",
    [
        [],
        123,
        {"events": []},
        {"capabilities": []},
        {"capabilities": {"logical_steps": []}},
    ],
)
def test_malformed_manifest_is_invalid_evidence_not_attribute_error(tmp_path, bad):
    import hashlib

    marker = m.publish(
        tmp_path,
        [],
        producer={"name": "fixture", "version": "1"},
        invocation_id="i",
        session_id="s",
        capabilities={},
        complete=True,
    )
    current = json.loads((tmp_path / m.MANIFEST).read_bytes())
    raw = m.encoded({**current, **bad} if isinstance(bad, dict) else bad)
    (tmp_path / m.MANIFEST).write_bytes(raw)
    marker["sha256"] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError):
        m.read(tmp_path, marker)


def test_corrupt_new_evidence_preserves_trial_and_other_metrics(tmp_path):
    import hashlib
    from types import SimpleNamespace

    from psycheval.report.measurements import construct
    from psycheval.state.workspace_harbor import _load_measurements

    directory = tmp_path / "agent"
    marker = m.publish(
        directory,
        [],
        producer={"name": "fixture", "version": "1"},
        invocation_id="i",
        session_id="s",
        capabilities={},
        complete=True,
    )
    raw = m.encoded({"type": "end", "end_ms": 10**400}) + b"\n"
    (directory / m.EVENTS).write_bytes(raw)
    manifest = json.loads((directory / m.MANIFEST).read_bytes())
    manifest["events"].update(
        bytes=len(raw), records=1, sha256=hashlib.sha256(raw).hexdigest()
    )
    raw_manifest = m.encoded(manifest)
    (directory / m.MANIFEST).write_bytes(raw_manifest)
    marker["sha256"] = hashlib.sha256(raw_manifest).hexdigest()
    trajectory = {
        "session_id": "s",
        "extra": {"measurements": marker},
        "steps": [{"source": "agent"}],
    }
    meta = {}
    _load_measurements(
        SimpleNamespace(path=tmp_path, data_path=None), trajectory, {}, meta
    )
    assert meta["measurement_error"] == "invalid_measurement_evidence"
    values, provenance = construct(trajectory, meta)
    assert values["agent_steps"] == 1
    assert values["tokens"] is None
    assert provenance["tokens"]["contract_version"] == 1


def test_dsh_capture_descendants_offsets_and_tool_hook(tmp_path):
    from psycheval.harbor.agents.dsh_measurements import capture

    def session(identity, parent=None):
        path = tmp_path / "sessions" / "date" / identity / "session.v4.jsonl"
        path.parent.mkdir(parents=True)
        header = {
            "version": 4,
            "id": identity,
            "origin": "subagent" if parent else "user",
            "parentSession": parent,
        }
        events = [
            header,
            {"seq": 1, "type": "tool/call", "time": 10, "data": {"callId": "call"}},
            {"seq": 2, "type": "turn/end", "time": 20, "data": {}},
        ]
        path.write_text("\n".join(map(json.dumps, events)), encoding="utf-8")

    for identity, parent in [
        ("grandchild", "child"),
        ("root", None),
        ("child", "root"),
        ("unrelated", None),
    ]:
        session(identity, parent)
    hook = tmp_path / "hook"
    hook.write_text(
        json.dumps(
            {"session_id": "root", "id": "call", "exit_code": 7, "status": "completed"}
        ),
        encoding="utf-8",
    )
    offsets = {}
    records, complete, diagnostics = capture(tmp_path, "root", offsets, hook)
    assert complete and not diagnostics
    assert {r["session_id"] for r in records} == {"root", "child", "grandchild"}
    assert (
        next(r for r in records if r["session_id"] == "root" and r["type"] == "tool")[
            "exit_code"
        ]
        == 7
    )
    assert set(offsets.values()) == {2}
    assert capture(tmp_path, "root", offsets, hook)[0] == []


def test_dsh_capture_read_and_file_limits(tmp_path, monkeypatch):
    from psycheval.harbor.agents import dsh_measurements as dsh

    path = tmp_path / "sessions" / "date" / "root" / "session.v4.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"version": 4, "id": "root"}) + "\n" + "x" * 100)
    monkeypatch.setattr(dsh, "MAX_NATIVE_RECORD_BYTES", 60)
    records, complete, diagnostics = dsh.capture(
        tmp_path, "root", {}, tmp_path / "missing"
    )
    assert (
        not records and not complete and "native_measurement_read_limit" in diagnostics
    )
    monkeypatch.setattr(dsh.Path, "glob", lambda *_: iter([path] * 1025))
    with pytest.raises(ValueError, match="native_measurement_file_limit"):
        dsh.capture(tmp_path, "root", {}, tmp_path / "missing")


def test_dsh_capture_retains_prefix_on_non_object_or_invalid_json(tmp_path):
    from psycheval.harbor.agents.dsh_measurements import capture

    path = tmp_path / "sessions" / "date" / "root" / "session.v4.jsonl"
    path.parent.mkdir(parents=True)
    header = {"version": 4, "id": "root"}
    end = {"seq": 1, "type": "turn/end", "time": 120, "data": {}}
    for bad in ("123", "{invalid"):
        path.write_text(
            "\n".join([json.dumps(header), json.dumps(end), bad]), encoding="utf-8"
        )
        records, complete, diagnostics = capture(
            tmp_path, "root", {}, tmp_path / "missing-hook"
        )
        assert records[0]["end_ms"] == 120
        assert not complete
        assert diagnostics == ["native_measurement_unreadable"]


def manifest(complete=True):
    return {
        "producer": {"name": "fixture", "version": "1"},
        "complete": complete,
        "events": {"sha256": "0" * 64},
        "capabilities": {
            "logical_steps": {"status": "verified", "basis_id": "fixture"}
        },
    }


def step(**kwargs):
    return {
        "type": "step",
        "id": "1",
        "session_id": "root",
        "scope": "main",
        "clock_id": "clock",
        "start_ms": 100,
        "first_ms": 300,
        "end_ms": 1100,
        "complete": True,
        "output_tokens": 40,
        "token_basis": "final_output_includes_reasoning",
        **kwargs,
    }


def test_matching_samples_retry_wait_and_cancelled_ttft():
    result = m.calculate(
        manifest(False),
        [step(), step(id="2", first_ms=600, complete=False, end_ms=None)],
    )
    assert result["model_duration_ms"]["value"] is None
    assert result["ttft_ms"]["value"] == 350
    assert result["tps"]["value"] == 50
    assert result["tps"]["provenance"]["coverage"]["measured"] == 1
    assert result["ttft_ms"]["provenance"]["coverage"]["total"] is None


def test_unverified_step_capability_does_not_claim_an_empty_target():
    evidence = manifest()
    evidence["capabilities"]["logical_steps"] = {
        "status": "unavailable",
        "reason": "native_first_output_and_retry_identity_unavailable",
    }
    result = m.calculate(
        evidence,
        [
            {
                "type": "request",
                "id": "1",
                "session_id": "root",
                "input_tokens": 100,
                "output_tokens": 10,
            }
        ],
    )
    assert result["tokens"]["value"] == 110
    for key in ("model_duration_ms", "ttft_ms", "tps"):
        assert result[key]["value"] is None
        assert result[key]["provenance"]["coverage"] == {
            "measured": 0,
            "unknown": None,
            "total": None,
            "retained": 0,
        }


@pytest.mark.parametrize(
    "changes",
    [
        dict(clock_id=None),
        dict(first_ms=90),
        dict(end_ms=200),
        dict(output_tokens=None),
        dict(token_basis="unknown"),
    ],
)
def test_no_repaired_clock_or_unknown_token_basis(changes):
    result = m.calculate(manifest(), [step(**changes)])
    assert result["tps"]["value"] is None


def test_duplicate_identity_and_conflicting_identity():
    assert (
        m.calculate(manifest(), [step(), step()])["model_duration_ms"]["value"] == 1000
    )
    result = m.calculate(manifest(), [step(), step(end_ms=1200)])
    assert result["model_duration_ms"]["value"] is None
    assert result["model_duration_ms"]["provenance"]["coverage"]["unknown"] == 1


def test_cache_same_subset_total_requires_all_and_parent_excludes_child():
    rows = [
        {
            "type": "request",
            "session_id": "root",
            "id": "a",
            "input_tokens": 100,
            "output_tokens": 20,
            "cached_tokens": 50,
        },
        {
            "type": "request",
            "session_id": "root",
            "id": "b",
            "input_tokens": 20,
            "output_tokens": None,
        },
    ]
    result = m.calculate(manifest(), rows)
    assert result["tokens"]["value"] is None
    assert result["cache_hit_rate"]["value"] == 0.5
    rows[0]["includes_children"] = True
    rows[1]["parent_request_id"] = "a"
    assert m.calculate(manifest(), rows)["tokens"]["value"] == 120


def test_tool_results_override_completed_and_unknown_excluded():
    rows = [
        {"type": "tool", "session_id": "root", "scope": "main", "id": str(i), **value}
        for i, value in enumerate(
            [
                {"status": "completed", "exit_code": 7},
                {"status": "completed"},
                {"status": "unknown"},
                {"status": "completed", "cancelled": True},
            ]
        )
    ]
    result = m.calculate(manifest(), rows)["tool_success_rate"]
    assert result["value"] == 1 / 3
    assert result["provenance"]["coverage"] == {
        "measured": 3,
        "success": 1,
        "failed": 2,
        "unknown": 1,
        "total": 4,
        "retained": 4,
    }


def test_atomic_generation_digest_whitelist_and_truncated_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "MAX_RECORDS", 1)
    marker = m.publish(
        tmp_path,
        [step(), step(id="2")],
        producer={"name": "fixture", "version": "1"},
        invocation_id="i",
        session_id="root",
        capabilities={},
        complete=True,
    )
    data, rows = m.read(tmp_path, marker)
    assert not data["complete"] and len(rows) == 1
    assert data["diagnostics"] == ["measurement_evidence_truncated"]
    (tmp_path / m.EVENTS).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="digest"):
        m.read(tmp_path, marker)
    with pytest.raises(ValueError, match="unapproved"):
        m.publish(
            tmp_path,
            [step(prompt="secret")],
            producer={},
            invocation_id="i",
            session_id="root",
            capabilities={},
            complete=True,
        )


def test_dsh_native_retry_boundaries_and_no_sensitive_output():
    events = [
        {"type": "step/start", "seq": 0, "time": 100, "data": {"turn": 1, "step": 1}},
        {
            "type": "assistant/attempt",
            "seq": 1,
            "time": 500,
            "data": {
                "turn": 1,
                "step": 1,
                "stream": [
                    {
                        "type": "text-chunks",
                        "time0": 200,
                        "dt": [50],
                        "texts": ["", "private discarded"],
                    }
                ],
            },
        },
        {
            "type": "assistant/message",
            "seq": 2,
            "time": 1100,
            "data": {
                "turn": 1,
                "step": 1,
                "usage": {
                    "inputTokens": 40,
                    "cacheReadTokens": 60,
                    "outputTokens": 5,
                    "totalTokens": 105,
                },
                "stream": [
                    {
                        "type": "text-chunks",
                        "time0": 900,
                        "dt": [],
                        "texts": ["private final"],
                    }
                ],
            },
        },
        {
            "type": "turn/end",
            "seq": 3,
            "time": 1200,
            "data": {"reason": {"kind": "completed"}},
        },
    ]
    before = deepcopy(events)
    rows, seq, complete = normalize(events, "root", main_session="root")
    assert events == before and seq == 3 and complete
    assert rows[0]["first_ms"] == 250 and rows[0]["end_ms"] == 1100
    assert b"private" not in m.encoded(rows)
    result = m.calculate(manifest(), rows)
    assert result["model_duration_ms"]["value"] == 1000
    assert result["ttft_ms"]["value"] == 150
    assert result["tps"]["value"] == pytest.approx(5 / 0.85)
    assert result["tokens"]["value"] is None  # Unreported failed-attempt usage.


def test_first_output_ignores_empty_role_usage_and_counts_tool_name():
    assert (
        first_output(
            [
                {"type": "chunk", "time": 1, "chunk": {"type": "usage"}},
                {"type": "text-chunks", "time0": 2, "dt": [1], "texts": ["", ""]},
                {
                    "type": "tool-call-chunks",
                    "time0": 5,
                    "dt": [],
                    "args": [""],
                    "name": "read",
                },
            ]
        )
        == 5
    )


def test_cancelled_dsh_attempt_intentionally_keeps_ttft_without_decode():
    events = [
        {"type": "step/start", "seq": 0, "time": 100, "data": {"turn": 1, "step": 1}},
        {
            "type": "assistant/attempt",
            "seq": 1,
            "time": 500,
            "data": {
                "turn": 1,
                "step": 1,
                "stream": [
                    {
                        "type": "text-chunks",
                        "time0": 200,
                        "dt": [],
                        "texts": ["partial"],
                    }
                ],
            },
        },
        {"type": "step/end", "seq": 2, "time": 600, "data": {"turn": 1, "step": 1}},
    ]
    rows, _, _ = normalize(events, "root", main_session="root")
    result = m.calculate(manifest(False), rows)
    assert result["ttft_ms"]["value"] == 100
    assert result["tps"]["value"] is None
    assert result["model_duration_ms"]["value"] is None


def test_seeded_child_requests_exclude_inherited_history_and_main_performance():
    events = [
        {"seq": 0, "time": 10, "type": "step/start", "data": {"turn": 1, "step": 1}},
        {
            "seq": 1,
            "time": 20,
            "type": "assistant/message",
            "data": {
                "turn": 1,
                "step": 1,
                "usage": {"outputTokens": 99, "totalTokens": 100},
            },
        },
        {"seq": 2, "time": 21, "type": "session/end-seed", "data": {"inherited": True}},
        {"seq": 3, "time": 30, "type": "step/start", "data": {"turn": 2, "step": 1}},
        {
            "seq": 4,
            "time": 40,
            "type": "assistant/message",
            "data": {
                "turn": 2,
                "step": 1,
                "usage": {"outputTokens": 2, "totalTokens": 12},
            },
        },
        {
            "seq": 5,
            "time": 41,
            "type": "turn/end",
            "data": {"reason": {"kind": "completed"}},
        },
    ]
    rows, _, complete = normalize(events, "child", main_session="root", seeded=True)
    assert complete
    result = m.calculate(manifest(), rows)
    assert result["tokens"]["value"] == 12
    assert result["model_duration_ms"]["value"] is None
    with pytest.raises(ValueError, match="missing_inherited_seed_boundary"):
        normalize(events[:2], "child", main_session="root", seeded=True)


def test_native_identity_and_order_conflicts_are_rejected():
    start = {"seq": 1, "time": 10, "type": "step/start", "data": {"turn": 1, "step": 1}}
    for other, reason in [
        (dict(start, time=20), "conflicting_native_event"),
        (dict(start, seq=0), "out_of_order_native_event"),
        (dict(start, seq=2, data={}), "missing_native_step_identity"),
    ]:
        with pytest.raises(ValueError, match=reason):
            normalize([start, other], "root", main_session="root")


def test_native_read_limit_preserves_prefix(tmp_path):
    from psycheval.harbor.agents.dsh_measurements import bounded_records

    path = tmp_path / "native.jsonl"
    path.write_bytes(b'{"first":1}\n' + b"x" * 200)
    diagnostics = []
    assert list(bounded_records(path, [20], diagnostics)) == [{"first": 1}]
    assert diagnostics == ["native_measurement_read_limit"]


def test_measurement_artifact_validates_digest_and_rejects_unknown_paths(tmp_path):
    from psycheval.state.harbor_verifier_evidence import (
        open_harbor_verifier_artifact_download,
    )

    m.publish(
        tmp_path / "agent",
        [],
        producer={"name": "fixture"},
        invocation_id="i",
        session_id="s",
        capabilities={},
        complete=True,
    )
    artifact = open_harbor_verifier_artifact_download(
        tmp_path, containment_root=tmp_path, artifact_id=m.artifact_id(m.MANIFEST)
    )
    assert json.loads(b"".join(artifact.chunks))["contract_version"] == 1
    with pytest.raises(ValueError):
        open_harbor_verifier_artifact_download(
            tmp_path,
            containment_root=tmp_path / "other",
            artifact_id=m.artifact_id(m.MANIFEST),
        )
    (tmp_path / "agent" / m.EVENTS).write_text("changed")
    with pytest.raises(ValueError, match="measurement_event_digest"):
        m.artifact(tmp_path / "agent", m.artifact_id(m.EVENTS))
