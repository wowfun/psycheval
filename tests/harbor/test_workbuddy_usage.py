from __future__ import annotations

import gzip
import hashlib
import json

import pytest

from psycheval.harbor import workbuddy_usage as usage


def record(request="r1", conversation="turn", raw=None, normalized=None):
    return {
        "id": "history-" + request,
        "type": "function_call",
        "arguments": "PRIVATE_BODY",
        "providerData": {
            "messageId": request,
            "conversationRequestId": conversation,
            "rawUsage": raw,
            "usage": normalized,
        },
    }


def append(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.name == "acp.events.ndjson.gz":
        old = gzip.decompress(path.read_bytes()) if path.exists() else b""
        path.write_bytes(
            gzip.compress(
                old + (json.dumps(value, ensure_ascii=False) + "\n").encode(), mtime=0
            )
        )
        return
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def setup_evidence(tmp_path, requests=("r1",)):
    root = tmp_path / "config/projects"
    directory = tmp_path / "logs"
    directory.mkdir()
    summary = {
        "session_id": "session",
        "invocation_id": "call",
        "max_evidence_bytes": 1024 * 1024,
    }
    for request in requests:
        append(
            directory / "acp.events.ndjson.gz",
            {
                "direction": "receive",
                "phase": "prompt",
                "message": {
                    "method": "session/update",
                    "params": {
                        "sessionId": "session",
                        "update": {
                            "sessionUpdate": "agent_message_chunk",
                            "_meta": {
                                "codebuddy.ai/modelRequestId": request,
                                "codebuddy.ai/conversationRequestId": "turn",
                            },
                        },
                    },
                },
            },
        )
    return root, directory, summary


def trajectory():
    return {
        "extra": {},
        "steps": [
            {"step_id": 1, "source": "user", "message": "task"},
            {
                "step_id": 2,
                "source": "agent",
                "message": "done",
                "extra": {"workbuddy_model_request_ids": ["r1"]},
            },
        ],
    }


def test_native_ledger_is_bounded_private_and_excludes_resume_history(tmp_path):
    root, directory, summary = setup_evidence(tmp_path)
    path = root / "project/session.jsonl"
    append(path, record("old", raw={"prompt_tokens": 999}))
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    append(
        path,
        record(
            raw={
                "prompt_tokens": 10,
                "completion_tokens": 3,
                "prompt_cache_hit_tokens": 7,
                "api_key": "PRIVATE_KEY",
            }
        ),
    )
    append(path, record("unrelated", conversation="other", raw={"prompt_tokens": 500}))
    evidence = usage.capture_usage(root, directory, summary, baseline, "2.156.0")
    assert [row["model_request_id"] for row in evidence["records"]] == ["r1"]
    assert (
        evidence["sources"][0]["sha256"]
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )
    assert evidence["sources"][0]["baseline_bytes"] > 0
    target = directory / usage.USAGE_FILENAME
    digest = usage.publish_usage(target, evidence)
    assert digest == hashlib.sha256(target.read_bytes()).hexdigest()
    assert "PRIVATE" not in target.read_text(encoding="utf-8")
    data = usage.project_usage(trajectory(), evidence, digest)
    assert data["final_metrics"]["total_prompt_tokens"] == 10
    assert data["final_metrics"]["total_completion_tokens"] == 3
    assert data["final_metrics"]["total_cached_tokens"] == 7
    assert data["extra"]["workbuddy_usage"]["status"] == "complete"


def test_distinct_requests_with_equal_usage_count_both_but_snapshots_count_once(
    tmp_path,
):
    root, directory, summary = setup_evidence(tmp_path, ("r1", "r2"))
    path = root / "project/session.jsonl"
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    raw = {
        "prompt_tokens": 100,
        "completion_tokens": 5,
        "prompt_tokens_details": {"cached_tokens": 60},
    }
    for request in ("r1", "r1", "r2"):
        append(path, {"type": "function_call", "payload": record(request, raw=raw)})
    evidence = usage.capture_usage(root, directory, summary, baseline, "2.156.0")
    evidence["acp_usage"] = [
        {
            "message_id": "provider-response",
            "usage": {"inputTokens": 100, "outputTokens": 5},
        },
        {"message_id": "r1", "usage": raw},
        {
            "message_id": "r1",
            "usage": {
                "inputTokens": 100,
                "outputTokens": 5,
                "inputTokensDetails": {"cached_tokens": 60},
            },
        },
    ]
    data = usage.project_usage(trajectory(), evidence, "digest")
    metrics = data["final_metrics"]
    assert (
        metrics["total_prompt_tokens"],
        metrics["total_completion_tokens"],
        metrics["total_cached_tokens"],
    ) == (200, 10, 120)
    inference = metrics["extra"]["model_inference"]
    assert inference["attempt_count"] == 2
    assert inference["cache_prompt_tokens"] == 200
    assert inference["cache_read_tokens"] == 120
    assert data["steps"][1]["metrics"]["prompt_tokens"] == 100
    assert len(data["steps"]) == 2  # Unaligned r2 belongs only to Trial accounting.


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            {
                "inputTokens": 10,
                "outputTokens": 0,
                "inputTokensDetails": {"cached_tokens": 0},
            },
            (10, 0, 0, None),
        ),
        (
            {
                "prompt_tokens": 10,
                "completion_tokens": 2,
                "prompt_cache_miss_tokens": 8,
                "prompt_cache_hit_tokens": 2,
            },
            (10, 2, 2, None),
        ),
        (
            {
                "input_tokens": 4,
                "output_tokens": 2,
                "cache_read_input_tokens": 5,
                "cache_creation_input_tokens": 1,
            },
            (10, 2, 5, 1),
        ),
        ({"input_tokens": 4, "cache_read_input_tokens": 5}, (None, None, None, None)),
        (
            {
                "prompt_tokens": 10,
                "inputTokensDetails": [{"cached_tokens": 2}, {"cached_tokens": 3}],
                "cache_creation_input_tokens": 4,
            },
            (10, None, 5, 4),
        ),
        (
            {
                "prompt_tokens": 10,
                "prompt_cache_hit_tokens": 0,
                "prompt_tokens_details": {"cached_tokens": 2},
            },
            (10, None, None, None),
        ),
        ({"prompt_tokens": True, "completion_tokens": -1}, (None, None, None, None)),
        ({"prompt_tokens": 3, "cached_tokens": 5}, (3, None, None, None)),
    ],
)
def test_usage_dialects_preserve_known_zero_and_cache_read_semantics(raw, expected):
    assert tuple(usage.normalize_usage(raw).values()) == expected


def test_conflicts_and_missing_requests_do_not_publish_complete_totals(tmp_path):
    root, directory, summary = setup_evidence(tmp_path, ("r1", "missing"))
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    path = root / "project/session.jsonl"
    append(
        path,
        record(raw={"prompt_tokens": 10, "completion_tokens": 2, "cached_tokens": 3}),
    )
    append(
        path,
        record(raw={"prompt_tokens": 11, "completion_tokens": 2, "cached_tokens": 3}),
    )
    evidence = usage.capture_usage(root, directory, summary, baseline, "2.156.0")
    data = usage.project_usage(trajectory(), evidence, "digest")
    assert "total_prompt_tokens" not in data["final_metrics"]
    assert "total_completion_tokens" not in data["final_metrics"]
    assert data["extra"]["workbuddy_usage"]["status"] == "partial"
    assert "conflicting_usage" in data["extra"]["workbuddy_usage"]["diagnostics"]


def test_partial_updates_merge_without_zero_filling_cache(tmp_path):
    root, directory, summary = setup_evidence(tmp_path)
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    path = root / "project/session.jsonl"
    append(path, record(raw={"prompt_tokens": 10}))
    append(path, record(raw={"completion_tokens": 3}))
    evidence = usage.capture_usage(root, directory, summary, baseline, "2.156.0")
    data = usage.project_usage(trajectory(), evidence, "digest")
    assert data["final_metrics"]["total_prompt_tokens"] == 10
    assert data["final_metrics"]["total_completion_tokens"] == 3
    assert "total_cached_tokens" not in data["final_metrics"]
    assert "cache_sample_count" not in data["final_metrics"]["extra"]["model_inference"]


def test_changed_baseline_is_rejected_and_file_handles_close(tmp_path):
    root, directory, summary = setup_evidence(tmp_path)
    path = root / "project/session.jsonl"
    append(path, record(raw={"prompt_tokens": 1}))
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    content = path.read_bytes().replace(b'"prompt_tokens": 1', b'"prompt_tokens": 2')
    path.write_bytes(content)
    with pytest.raises(ValueError, match="changed_baseline"):
        usage.capture_usage(root, directory, summary, baseline, "2.156.0")
    path.rename(path.with_suffix(".closed"))


def test_truncated_tail_does_not_turn_prefix_into_complete_total(tmp_path):
    root, directory, summary = setup_evidence(tmp_path)
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    path = root / "project/session.jsonl"
    append(path, record(raw={"prompt_tokens": 10, "completion_tokens": 2}))
    with path.open("ab") as stream:
        stream.write(b'{"type":')
    evidence = usage.capture_usage(root, directory, summary, baseline, "2.156.0")
    data = usage.project_usage(trajectory(), evidence, "digest")
    assert "total_prompt_tokens" not in data["final_metrics"]
    assert "incomplete_native_tail" in data["extra"]["workbuddy_usage"]["diagnostics"]


def test_usage_file_limit_is_atomic(tmp_path, monkeypatch):
    path = tmp_path / usage.USAGE_FILENAME
    monkeypatch.setattr(usage, "MAX_USAGE_BYTES", 20)
    with pytest.raises(ValueError, match="usage_byte_limit"):
        usage.publish_usage(path, {"records": ["x" * 50]})
    assert not path.exists() and not path.with_suffix(".tmp").exists()


def test_sdk_default_cache_zero_is_not_provider_evidence(tmp_path):
    root, directory, summary = setup_evidence(tmp_path)
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    append(
        root / "project/session.jsonl",
        record(
            raw={"prompt_tokens": 10, "completion_tokens": 2},
            normalized={
                "inputTokens": 10,
                "outputTokens": 2,
                "inputTokensDetails": [{"cached_tokens": 0}],
            },
        ),
    )
    evidence = usage.capture_usage(root, directory, summary, baseline, "2.156.0")
    data = usage.project_usage(trajectory(), evidence, "digest")
    assert "total_cached_tokens" not in data["final_metrics"]
    assert data["extra"]["workbuddy_usage"]["coverage"]["cached_tokens"] == 0


def test_alias_conflict_cannot_be_hidden_by_sdk_fallback(tmp_path):
    root, directory, summary = setup_evidence(tmp_path)
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    append(
        root / "project/session.jsonl",
        record(
            raw={"prompt_tokens": 10, "inputTokens": 11, "completion_tokens": 2},
            normalized={"inputTokens": 10, "outputTokens": 2},
        ),
    )
    evidence = usage.capture_usage(root, directory, summary, baseline, "2.156.0")
    data = usage.project_usage(trajectory(), evidence, "digest")
    assert "total_prompt_tokens" not in data["final_metrics"]
    assert "conflicting_usage" in data["extra"]["workbuddy_usage"]["diagnostics"]


def test_history_byte_limit_blocks_partial_baseline(tmp_path):
    root, directory, summary = setup_evidence(tmp_path)
    append(root / "project/session.jsonl", record(raw={"prompt_tokens": 10}))
    baseline = usage.history_baseline(root, 1)
    assert (
        baseline.files[str((root / "project/session.jsonl").relative_to(root))][3]
        is None
    )
    with pytest.raises(ValueError, match="baseline_byte_limit"):
        usage.capture_usage(root, directory, summary, baseline, "2.156.0")


@pytest.mark.parametrize("axis", ["projects", "entries", "files"])
def test_baseline_enumeration_limit_keeps_reason_and_retries_next_call(
    tmp_path, monkeypatch, axis
):
    root, directory, summary = setup_evidence(tmp_path)
    monkeypatch.setattr(usage, "MAX_HISTORY_FILES", 2)
    if axis == "projects":
        paths = [root / f"project-{index}/note.txt" for index in range(3)]
    elif axis == "entries":
        paths = [root / f"project/note-{index}.txt" for index in range(3)]
    else:
        # The total-file guard matters across projects, independently of child_index.
        paths = [root / f"project-{index // 2}/old-{index}.jsonl" for index in range(3)]
    for path in paths[:2]:
        append(path, {})
    assert not usage.history_baseline(root, 1024).diagnostics
    append(paths[2], {})
    baseline = usage.history_baseline(root, 1024)
    assert baseline.files == {}
    assert baseline.diagnostics == ("history_file_limit",)
    evidence = usage.capture_usage(root, directory, summary, baseline, "fixture")
    assert evidence["diagnostics"] == ["history_file_limit"]
    assert evidence["records"] == []
    projected = usage.project_usage(trajectory(), evidence, "fixture")
    assert projected["extra"]["workbuddy_usage"]["status"] == "partial"
    assert "final_metrics" not in projected
    paths[2].unlink()
    if axis == "projects":
        paths[2].parent.rmdir()
    assert not usage.history_baseline(root, 1024).diagnostics


def test_baseline_untrusted_error_remains_categorical(tmp_path, monkeypatch):
    def fail(root):
        raise ValueError("PRIVATE_HISTORY_PATH_AND_BODY")

    monkeypatch.setattr(usage, "_files", fail)
    baseline = usage.history_baseline(tmp_path, 1024)
    assert baseline.files == {}
    assert baseline.diagnostics == ("baseline_unavailable",)


def test_unchanged_history_reuses_digests_without_spending_the_read_budget(
    tmp_path, monkeypatch
):
    root, directory, summary = setup_evidence(tmp_path)
    path = root / "project/old.jsonl"
    append(path, record("old", raw={"prompt_tokens": 999}))
    cache = {}
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"], cache=cache)
    assert not baseline.diagnostics

    def forbidden(*args):
        raise AssertionError("unchanged history was read again")

    monkeypatch.setattr(usage, "_hash_prefix", forbidden)
    repeated = usage.history_baseline(root, 1, cache=cache)
    assert repeated.files == baseline.files
    assert not repeated.diagnostics
    append(root / "project/session.jsonl", record(raw={"prompt_tokens": 10}))
    evidence = usage.capture_usage(root, directory, summary, repeated, "fixture")
    assert len(evidence["records"]) == 1
    # Capture has already hashed the complete new file, ready for the next call.
    next_call = usage.history_baseline(root, 1, cache=cache)
    assert all(entry[3] is not None for entry in next_call.files.values())


def test_history_cache_invalidates_content_changes_and_does_not_cache_partial_tail(
    tmp_path,
):
    root, directory, summary = setup_evidence(tmp_path)
    path = root / "project/session.jsonl"
    append(path, record(raw={"prompt_tokens": 1}))
    cache = {}
    usage.history_baseline(root, summary["max_evidence_bytes"], cache=cache)
    with path.open("ab") as stream:
        stream.write(b'{"unfinished":')
    assert usage.history_baseline(
        root, summary["max_evidence_bytes"], cache=cache
    ).diagnostics
    path.unlink()
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"], cache=cache)
    append(path, record(raw={"prompt_tokens": 2}))
    with path.open("ab") as stream:
        stream.write(b'{"unfinished":')
    evidence = usage.capture_usage(root, directory, summary, baseline, "fixture")
    assert evidence["diagnostics"] == ["incomplete_native_tail"]
    assert str(path.relative_to(root)) not in cache


def test_unrelated_history_over_budget_does_not_disable_current_session(tmp_path):
    root, directory, summary = setup_evidence(tmp_path)
    append(root / "project/old.jsonl", record("old", raw={"prompt_tokens": 999}))
    baseline = usage.history_baseline(root, 1)
    append(root / "project/session.jsonl", record(raw={"prompt_tokens": 10}))
    evidence = usage.capture_usage(root, directory, summary, baseline, "fixture")
    assert len(evidence["records"]) == 1 and not evidence["diagnostics"]


@pytest.mark.parametrize(
    "limit", ["files", "bytes", "lines", "line_bytes", "usage_bytes"]
)
def test_capture_limits_refuse_or_mark_incomplete_without_retaining_complete_totals(
    tmp_path, monkeypatch, limit
):
    root, directory, summary = setup_evidence(tmp_path)
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    path = root / "project/session.jsonl"
    append(path, record(raw={"prompt_tokens": 10, "completion_tokens": 2}))
    if limit == "files":
        append(root / "project/other.jsonl", {})
        monkeypatch.setattr(usage, "MAX_HISTORY_FILES", 1)
    elif limit == "bytes":
        monkeypatch.setattr(
            usage, "prompt_requests", lambda *args: ({"r1"}, {"turn"}, [])
        )
        summary["max_evidence_bytes"] = 1
    elif limit == "lines":
        append(path, record(raw={"prompt_tokens": 10}))
        monkeypatch.setattr(usage, "MAX_EVIDENCE_FRAMES", 1)
    elif limit == "line_bytes":
        monkeypatch.setattr(usage, "MAX_EVENT_FRAME", 10)
    else:
        monkeypatch.setattr(usage, "MAX_USAGE_BYTES", 65537)
    if limit == "usage_bytes":
        evidence = usage.capture_usage(root, directory, summary, baseline, "fixture")
        assert evidence["diagnostics"] == ["usage_byte_limit"]
        assert evidence["records"] == []
    else:
        expected = {
            "files": "history_file_limit",
            "bytes": "history_byte_limit",
            "lines": "history_line_limit",
            "line_bytes": "history_line_limit",
        }[limit]
        with pytest.raises(ValueError, match=expected):
            usage.capture_usage(root, directory, summary, baseline, "fixture")
    path.rename(path.with_suffix(".closed"))


def test_native_session_unavailable_and_unrelated_acp_session_are_distinct(tmp_path):
    root, directory, summary = setup_evidence(tmp_path)
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    assert usage.capture_usage(root, directory, summary, baseline, "fixture")[
        "diagnostics"
    ] == ["native_session_unavailable"]
    summary["session_id"] = "other"
    with pytest.raises(ValueError, match="unrelated_session"):
        usage.capture_usage(root, directory, summary, baseline, "fixture")


def test_wrong_session_record_is_not_admitted(tmp_path):
    root, directory, summary = setup_evidence(tmp_path)
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    append(
        root / "project/session.jsonl",
        {**record(raw={"prompt_tokens": 10}), "sessionId": "other"},
    )
    evidence = usage.capture_usage(root, directory, summary, baseline, "2.156.0")
    assert evidence["records"] == []
    assert evidence["diagnostics"] == ["invalid_native_record"]


def test_reparse_history_is_refused_without_opening_it(tmp_path, monkeypatch):
    root, directory, summary = setup_evidence(tmp_path)
    path = root / "project/session.jsonl"
    append(path, record(raw={"prompt_tokens": 10}))
    monkeypatch.setattr(type(path), "is_junction", lambda candidate: candidate == path)
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    assert baseline.diagnostics == ("baseline_unavailable",)
    assert (
        usage.capture_usage(root, directory, summary, baseline, "2.156.0")["records"]
        == []
    )


def test_sdk_usage_stored_as_raw_usage_does_not_prove_cache_zero(tmp_path):
    root, directory, summary = setup_evidence(tmp_path)
    baseline = usage.history_baseline(root, summary["max_evidence_bytes"])
    append(
        root / "project/session.jsonl",
        record(
            raw={
                "inputTokens": 10,
                "outputTokens": 2,
                "inputTokensDetails": {"cached_tokens": 0},
            }
        ),
    )
    evidence = usage.capture_usage(root, directory, summary, baseline, "2.156.0")
    data = trajectory()
    data["final_metrics"] = {"extra": {"retained": "metadata"}}
    data = usage.project_usage(data, evidence, "digest")
    assert "total_cached_tokens" not in data["final_metrics"]
    assert data["final_metrics"]["extra"]["retained"] == "metadata"
