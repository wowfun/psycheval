import json
import shutil
from copy import deepcopy
from dataclasses import replace

import pytest

from psycheval.adapters import adapter_for
from psycheval.atif import validate_atif_trajectory
from psycheval.config import ToolConfig
from psycheval.conversion import convert_path, finalize_atif_conversion
from psycheval.models import ReportSession
from psycheval.report import build_multi_report, build_report
from tests.peval.claude_support import event, family, write_events

CONFIG = ToolConfig(adapter="claude", redact=False)


def test_split_responses_preserve_tools_context_and_last_usage(tmp_path):
    first = event(
        "assistant",
        seq=2,
        message_id="response",
        content=[{"type": "thinking", "thinking": "Reason"}],
    )
    last = event(
        "assistant",
        seq=3,
        message_id="response",
        content=[
            {"type": "text", "text": "Answer"},
            {
                "type": "tool_use",
                "id": "call",
                "name": "Bash",
                "input": {"command": "pwd"},
            },
        ],
    )
    last["message"]["usage"]["output_tokens"] = 10
    result = event(
        "user",
        seq=4,
        content=[
            {
                "type": "tool_result",
                "tool_use_id": "call",
                "content": "",
                "is_error": True,
            },
            {"type": "text", "text": "Continue"},
        ],
    )
    events = [
        event("user", content="Hello"),
        first,
        last,
        deepcopy(last),
        result,
        event(
            "attachment",
            seq=5,
            attachment={"type": "queued_command", "prompt": "Notice"},
        ),
        event("system", seq=6, subtype="compact_boundary", content="Compacted"),
        event("user", seq=7, content="<command-name>/status</command-name>"),
        event("cost-state", seq=8, cost=900),
    ]
    path = write_events(tmp_path / "session.jsonl", events)
    before = path.read_bytes()
    converted = convert_path(str(path), CONFIG)
    trajectory = converted.trajectory
    validate_atif_trajectory(trajectory)
    assistant = trajectory["steps"][1]
    assert assistant["reasoning_content"] == "Reason"
    assert assistant["message"] == "Answer"
    assert assistant["llm_call_count"] == 1
    assert assistant["metrics"]["completion_tokens"] == 10
    assert assistant["metrics"]["prompt_tokens"] == 12
    assert assistant["metrics"]["cached_tokens"] == 4
    assert assistant["observation"]["results"][0]["content"] == ""
    assert assistant["observation"]["results"][0]["extra"]["is_error"] is True
    assert [s["message"] for s in trajectory["steps"]][2:] == [
        "Continue",
        "Notice",
        "Compacted",
        "<command-name>/status</command-name>",
    ]
    assert trajectory["final_metrics"]["total_completion_tokens"] == 10
    assert "total_cost_usd" not in trajectory["final_metrics"]
    assert trajectory["extra"]["claude"]["cost_state"]["cost"] == 900
    assert converted.warnings == []
    assert path.read_bytes() == before


def test_embedded_family_has_independent_metrics_and_survives_export(tmp_path):
    path = family(tmp_path / ".claude")
    result = convert_path(str(path), CONFIG.validated_update(agent_name="Display name"))
    root = result.trajectory
    assert root["trajectory_id"] == "claude:root-session"
    assert len(root["subagent_trajectories"]) == 6
    assert len(root["subagent_trajectories"][0]["subagent_trajectories"]) == 2
    assert root["final_metrics"]["total_prompt_tokens"] == 12
    assert result.warnings == []
    for child in root["subagent_trajectories"]:
        assert child["steps"][0]["step_id"] == 1
        assert child["final_metrics"]["total_prompt_tokens"] == 12
        assert child["session_id"].startswith("root-session:agent:")
    refs = root["steps"][1]["observation"]["results"]
    assert refs[0]["subagent_trajectory_ref"] == [
        {"trajectory_id": "claude:root-session:agent:child-0"}
    ]
    report = build_report(result, CONFIG, "fixture")
    assert len(report["trajectory_meta"][0]["subagent_meta"]) == 6
    exported = tmp_path / "portable.json"
    exported.write_text(json.dumps(root), encoding="utf-8")
    shutil.rmtree(path.parent)
    imported = convert_path(str(exported), CONFIG)
    assert imported.trajectory == root
    assert len(imported.subagent_results[0].subagent_results) == 2
    restored = build_report(imported, CONFIG, "export")
    assert len(restored["trajectory_meta"][0]["subagent_meta"]) == 6


@pytest.mark.parametrize(
    "failure", ["missing", "malformed", "identity", "symlink", "cycle"]
)
def test_child_failures_preserve_parent_with_diagnostics(tmp_path, failure):
    source = family(tmp_path)
    child = tmp_path / "root-session/subagents/agent-child-0.jsonl"
    if failure == "missing":
        child.unlink()
    elif failure == "malformed":
        child.write_text("{bad", encoding="utf-8")
    elif failure == "identity":
        write_events(child, [event("user", agent="wrong", content="Wrong")])
    elif failure == "symlink":
        child.unlink()
        try:
            child.symlink_to(source)
        except OSError as exc:
            pytest.skip(f"symlink creation unavailable: {exc}")
    else:
        write_events(
            child,
            [
                event(
                    "assistant",
                    agent="child-0",
                    content=[
                        {"type": "tool_use", "id": "loop", "name": "Agent", "input": {}}
                    ],
                ),
                event(
                    "user",
                    agent="child-0",
                    seq=2,
                    content=[
                        {"type": "tool_result", "tool_use_id": "loop", "content": ""}
                    ],
                    toolUseResult={"agentId": "child-0"},
                ),
            ],
        )
    result = convert_path(str(source), CONFIG)
    validate_atif_trajectory(result.trajectory)
    assert any("child-0" in warning for warning in result.warnings)
    assert len(result.subagent_results) == (6 if failure == "cycle" else 5)


def test_unknown_synthetic_missing_usage_and_orphan_are_explicit(tmp_path):
    synthetic = event("assistant", content=[{"type": "text", "text": "Interrupted"}])
    synthetic["message"]["model"] = "<synthetic>"
    synthetic["message"]["usage"] = {}
    unknown = event(
        "assistant", seq=3, content=[{"type": "image", "source": {"data": "opaque"}}]
    )
    unknown["message"]["usage"] = {"input_tokens": None, "output_tokens": 0}
    source = write_events(
        tmp_path / "session.jsonl",
        [
            synthetic,
            event(
                "user",
                seq=2,
                content=[
                    {
                        "type": "tool_result",
                        "tool_use_id": "missing",
                        "content": "orphan",
                    }
                ],
            ),
            unknown,
        ],
    )
    converted = convert_path(str(source), CONFIG)
    steps = converted.trajectory["steps"]
    assert steps[0]["llm_call_count"] == 0
    assert "metrics" not in steps[0]
    assert (
        steps[1]["observation"]["results"][0]["extra"]["unmatched_source_call_id"]
        == "missing"
    )
    assert "prompt_tokens" not in steps[2]["metrics"]
    assert steps[2]["metrics"]["completion_tokens"] == 0
    assert steps[2]["extra"]["claude"]["unmapped_content"]
    assert len(converted.warnings) == 2


def test_directory_catalog_orders_by_activity_and_resolves_owned_ids(tmp_path):
    family(tmp_path)
    newer = event("user", seq=50, content="Newer", sessionId="newer")
    write_events(tmp_path / "renamed.jsonl", [newer])
    adapter = adapter_for("claude")
    assert [s.session_id for s in adapter.list_sessions(str(tmp_path))] == [
        "newer",
        "root-session",
    ]
    assert adapter.resolve_session_path(str(tmp_path), None).endswith("renamed.jsonl")
    assert adapter.resolve_session_path(str(tmp_path), "root-session").endswith(
        "root-session.jsonl"
    )
    with pytest.raises(ValueError, match="not found"):
        adapter.resolve_session_path(str(tmp_path), "../root-session")


def test_redaction_and_limits_apply_to_raw_evidence_and_arguments(tmp_path):
    source = write_events(
        tmp_path / "session.jsonl",
        [
            event("user", content="x" * 100),
            event(
                "assistant",
                seq=2,
                content=[
                    {
                        "type": "tool_use",
                        "id": "secret",
                        "name": "Bash",
                        "input": {"api_key": "sensitive", "text": "z" * 100},
                    }
                ],
            ),
        ],
    )
    result = convert_path(
        str(source), CONFIG.validated_update(redact=True, max_content_chars=40)
    )
    serialized = json.dumps(result.trajectory)
    assert "sensitive" not in serialized
    assert "z" * 100 not in serialized
    assert result.steps_meta[0].truncated


def test_bad_root_has_line_diagnostic(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("{}\ninvalid\n", encoding="utf-8")
    with pytest.raises(ValueError, match="JSONL line 2"):
        convert_path(str(path), CONFIG)


def test_partial_usage_updates_recompute_prompt_without_losing_known_counts(tmp_path):
    first = event("assistant", seq=1, message_id="shared", content="First")
    last = event("assistant", seq=2, message_id="shared", content="Last")
    last["message"]["usage"] = {"input_tokens": 8, "output_tokens": None}
    source = write_events(tmp_path / "session.jsonl", [first, last])
    result = convert_path(str(source), CONFIG)
    metrics = result.trajectory["steps"][0]["metrics"]
    assert metrics["prompt_tokens"] == 17
    assert metrics["completion_tokens"] == 6


def test_direct_child_retains_native_identity_without_reusing_root_session(tmp_path):
    family(tmp_path)
    child = tmp_path / "root-session/subagents/agent-child-0.jsonl"
    result = convert_path(str(child), CONFIG)
    assert result.trajectory["session_id"] == "root-session:agent:child-0"
    assert result.trajectory["extra"]["claude"]["session_id"] == "root-session"
    assert len(result.subagent_results) == 2


def test_synthetic_usage_is_evidence_without_contributing_to_totals(tmp_path):
    synthetic = event("assistant", content="Unavailable")
    synthetic["message"]["model"] = "<synthetic>"
    path = write_events(tmp_path / "session.jsonl", [synthetic])
    result = convert_path(str(path), CONFIG)
    assert "usage" not in result.trajectory["final_metrics"]["extra"]
    assert result.trajectory["steps"][0]["extra"]["claude"]["synthetic_usage"]


def test_unknown_scalar_content_is_retained_with_diagnostic(tmp_path):
    path = write_events(tmp_path / "session.jsonl", [event("assistant", content=42)])
    result = convert_path(str(path), CONFIG)
    assert result.trajectory["steps"][0]["extra"]["claude"]["unmapped_content"] == [42]
    assert result.warnings


def test_file_order_survives_backwards_time_and_parent_branches(tmp_path):
    path = write_events(
        tmp_path / "session.jsonl",
        [
            event("user", seq=40, content="First"),
            event("assistant", seq=30, content="Second", parentUuid="main-40"),
            event("user", seq=20, content="Third", parentUuid="main-40"),
        ],
    )
    result = convert_path(str(path), CONFIG)
    assert [step["message"] for step in result.trajectory["steps"]] == [
        "First",
        "Second",
        "Third",
    ]


def test_escaped_child_directory_preserves_root_without_reading_children(tmp_path):
    project = tmp_path / "project"
    source = family(project)
    child_root = project / "root-session/subagents"
    outside = tmp_path / "outside"
    child_root.rename(outside)
    try:
        child_root.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    result = convert_path(str(source), CONFIG)
    assert result.subagent_results == []
    assert len(result.trajectory["steps"]) == 2
    assert all("directory escapes" in warning for warning in result.warnings)
    assert len(result.warnings) == 6


def test_catalog_isolates_bad_empty_and_duplicate_files(tmp_path):
    write_events(tmp_path / "good.jsonl", [event("user", content="Good")])
    (tmp_path / "bad.jsonl").write_text("{bad", encoding="utf-8")
    (tmp_path / "empty.jsonl").touch()
    for name in ("duplicate", "backup"):
        write_events(
            tmp_path / f"{name}.jsonl",
            [event("user", content=name, sessionId="ambiguous")],
        )
    adapter = adapter_for("claude")
    assert [s.session_id for s in adapter.list_sessions(str(tmp_path))] == [
        "root-session"
    ]
    assert adapter.resolve_session_path(str(tmp_path), None).endswith("good.jsonl")
    listing = adapter.inspect_sessions(str(tmp_path))
    assert len(listing.warnings) == 3
    assert any("bad.jsonl" in warning for warning in listing.warnings)
    assert any("empty.jsonl" in warning for warning in listing.warnings)
    assert any("ambiguous" in warning for warning in listing.warnings)
    with pytest.raises(ValueError, match="ambiguous"):
        adapter.resolve_session_path(str(tmp_path), "ambiguous")


def test_stray_sidechain_record_does_not_hide_main_session(tmp_path):
    write_events(
        tmp_path / "main.jsonl",
        [
            event("user", content="Main"),
            event("user", seq=2, content="Sidechain", isSidechain=True),
        ],
    )
    write_events(
        tmp_path / "sidechain.jsonl",
        [
            event("user", content="Child", isSidechain=True, sessionId="child-session"),
        ],
    )
    assert [
        s.session_id for s in adapter_for("claude").list_sessions(str(tmp_path))
    ] == ["root-session"]


def test_streamed_catalog_uses_latest_valid_timestamp_without_epoch_clamping(tmp_path):
    for identity, timestamp in (
        ("earlier", "1960-01-01T00:00:00Z"),
        ("later", "1961-01-01T00:00:00Z"),
    ):
        write_events(
            tmp_path / f"{identity}.jsonl",
            [
                event(
                    "user", content=identity, sessionId=identity, timestamp=timestamp
                ),
                event(
                    "user",
                    seq=2,
                    content="Invalid clock",
                    sessionId=identity,
                    timestamp="invalid",
                ),
            ],
        )
    write_events(
        tmp_path / "unknown.jsonl",
        [event("user", sessionId="unknown", content="No clock", timestamp=None)],
    )
    sessions = adapter_for("claude").list_sessions(str(tmp_path))
    assert [s.session_id for s in sessions] == ["later", "earlier", "unknown"]
    assert [s.updated_at_ms for s in sessions] == [-283996800000, -315619200000, None]


def test_aggregate_usage_includes_cache_like_prompt_metrics(tmp_path):
    path = write_events(
        tmp_path / "session.jsonl", [event("assistant", content="Answer")]
    )
    trajectory = convert_path(str(path), CONFIG).trajectory
    assert trajectory["final_metrics"]["total_prompt_tokens"] == 12
    assert trajectory["final_metrics"]["extra"]["usage"]["input_tokens"] == 12
    assert (
        trajectory["steps"][0]["metrics"]["extra"]["usage"]["uncached_input_tokens"]
        == 3
    )


@pytest.mark.parametrize(
    ("timestamps", "expected"),
    [
        ([None, "invalid"], None),
        (["1970-01-01T00:00:00Z", None], 0),
        (["2026-01-01T08:00:50+08:00", "2026-01-01T00:00:01Z"], 1767225650000),
    ],
)
def test_session_update_time_is_latest_valid_event_or_unknown(
    tmp_path, timestamps, expected
):
    write_events(
        tmp_path / "session.jsonl",
        [
            event("user", seq=index, content="Update", timestamp=timestamp)
            for index, timestamp in enumerate(timestamps)
        ],
    )
    session = adapter_for("claude").list_sessions(str(tmp_path))[0]
    assert session.updated_at_ms == expected


@pytest.mark.parametrize("per_result", [False, True])
def test_batched_subagent_metadata_is_linked_only_when_unambiguous(
    tmp_path, per_result
):
    source = family(tmp_path)
    records = [json.loads(line) for line in source.read_text().splitlines()]
    blocks = []
    for record in records[2:]:
        block = record["message"]["content"][0]
        if per_result:
            block["toolUseResult"] = record["toolUseResult"]
        blocks.append(block)
    write_events(
        source,
        [
            *records[:2],
            event(
                "user",
                seq=3,
                content=blocks,
                **({} if per_result else {"toolUseResult": {"agentId": "child-0"}}),
            ),
        ],
    )
    result = convert_path(str(source), CONFIG)
    if per_result:
        assert len(result.subagent_results) == 6
        assert len(result.subagent_results[0].subagent_results) == 2
        assert result.warnings == []
    else:
        assert result.subagent_results == []
        assert any(
            "child-0" in w and "ambiguous" in w and "omitted" in w
            for w in result.warnings
        )


def test_orphan_subagent_link_has_specific_diagnostic(tmp_path):
    source = family(tmp_path)
    records = [json.loads(line) for line in source.read_text().splitlines()]
    write_events(source, [records[0], records[2]])
    result = convert_path(str(source), CONFIG)
    assert result.subagent_results == []
    assert any(
        "child-0" in w and "no matching tool call" in w and "omitted" in w
        for w in result.warnings
    )


def test_shared_child_omission_is_distinct_from_cycle(tmp_path):
    source = family(tmp_path)
    child = tmp_path / "root-session/subagents/agent-child-1.jsonl"
    write_events(
        child,
        [
            event(
                "assistant",
                agent="child-1",
                content=[
                    {"type": "tool_use", "id": "shared", "name": "Agent", "input": {}}
                ],
            ),
            event(
                "user",
                agent="child-1",
                seq=2,
                content=[
                    {"type": "tool_result", "tool_use_id": "shared", "content": ""}
                ],
                toolUseResult={"agentId": "grand-0"},
            ),
        ],
    )
    result = convert_path(str(source), CONFIG)
    assert len(result.subagent_results) == 6
    assert result.subagent_results[1].subagent_results == []
    assert any(
        "grand-0" in w and "another parent" in w and "omitted" in w
        for w in result.warnings
    )


def test_missing_embedded_identity_reports_atif_field_error(tmp_path):
    source = write_events(tmp_path / "main.jsonl", [event("user", content="Main")])
    parent = convert_path(str(source), CONFIG)
    child = deepcopy(parent)
    child.trajectory.pop("session_id")
    child.trajectory.pop("trajectory_id")
    child.warnings = ["retained warning"]
    with pytest.raises(ValueError, match=r"subagent_trajectories\[0\]\.trajectory_id"):
        finalize_atif_conversion(replace(parent, subagent_results=[child]))


@pytest.mark.parametrize("adapter_id", ["claude", "atif"])
def test_child_metadata_inherits_input_adapter(tmp_path, adapter_id):
    source = family(tmp_path)
    result = convert_path(str(source), CONFIG)
    if adapter_id == "atif":
        exported = tmp_path / "portable.json"
        exported.write_text(json.dumps(result.trajectory), encoding="utf-8")
        result = convert_path(str(exported), ToolConfig())
    report = build_multi_report(
        [ReportSession(result, input_label="family", adapter_id=adapter_id)],
        ToolConfig(),
    )
    root = report["trajectory_meta"][0]
    child = root["subagent_meta"]["claude:root-session:agent:child-0"]
    assert child["adapter"] == root["adapter"] == adapter_id
    assert all(
        meta["adapter"] == adapter_id for meta in child["subagent_meta"].values()
    )


def test_omitted_cache_measurements_leave_inclusive_prompt_unknown(tmp_path):
    response = event("assistant", content="Answer")
    response["message"]["usage"] = {"input_tokens": 10, "output_tokens": 5}
    source = write_events(tmp_path / "session.jsonl", [response])
    trajectory = convert_path(str(source), CONFIG).trajectory
    metrics = trajectory["steps"][0]["metrics"]
    assert "prompt_tokens" not in metrics
    assert "total_prompt_tokens" not in trajectory["final_metrics"]
    assert metrics["completion_tokens"] == 5
    assert metrics["extra"]["usage"]["uncached_input_tokens"] == 10


def test_repeated_invalid_usage_has_one_diagnostic_and_retains_each_response(tmp_path):
    events = [event("assistant", seq=index, content="Answer") for index in (1, 2)]
    for response in events:
        response["message"]["usage"]["input_tokens"] = "invalid"
    source = write_events(tmp_path / "session.jsonl", events)
    result = convert_path(str(source), CONFIG)
    assert result.warnings == ["invalid Claude usage: input_tokens"]
    assert len(result.trajectory["steps"]) == 2
    assert all(
        step["metrics"]["extra"]["usage"]["claude"]["input_tokens"] == "invalid"
        for step in result.trajectory["steps"]
    )


@pytest.mark.parametrize("missing", ["input_tokens", "cache_creation_input_tokens"])
def test_partial_input_with_known_cache_keeps_valid_atif(tmp_path, missing):
    response = event("assistant", content="Answer")
    response["message"]["usage"].pop(missing)
    source = write_events(tmp_path / "session.jsonl", [response])
    trajectory = convert_path(str(source), CONFIG).trajectory
    metrics = trajectory["steps"][0]["metrics"]
    assert "prompt_tokens" not in metrics
    assert "cached_tokens" not in metrics
    assert "total_prompt_tokens" not in trajectory["final_metrics"]
    assert "total_cached_tokens" not in trajectory["final_metrics"]
    assert metrics["extra"]["usage"]["claude"]["cache_read_input_tokens"] == 4
    validate_atif_trajectory(trajectory)
