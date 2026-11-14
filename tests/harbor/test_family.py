from copy import deepcopy

import pytest

from psycheval.harbor.family import coverage, retain, selected, tools_complete, validate
from psycheval.harbor.measurements import calculate
from psycheval.report.builder import project_meta_from_atif


def trajectory(identity, tokens=10):
    return {
        "schema_version": "ATIF-v1.8",
        "trajectory_id": identity,
        "session_id": identity,
        "agent": {"name": "fixture", "version": "1"},
        "steps": [{"step_id": 1, "source": "agent", "message": "answer"}],
        "final_metrics": {"total_prompt_tokens": tokens, "total_completion_tokens": 2},
        "extra": {"tool_evidence": "complete"},
    }


def test_embed_once_multiple_references_and_metrics_are_derived():
    root, child = trajectory("root"), trajectory("child", 20)
    root["subagent_trajectories"] = [child]
    root["steps"][0]["observation"] = {
        "results": [
            {
                "content": "done",
                "subagent_trajectory_ref": [{"trajectory_id": "child"}],
            },
            {
                "content": "continued",
                "subagent_trajectory_ref": [{"trajectory_id": "child"}],
            },
        ]
    }
    retain(root)
    before = deepcopy(root)
    meta = project_meta_from_atif(root, {})
    assert root == before
    assert len(selected(root)) == 2
    assert meta["metric_sets"]["root"]["metric_values"]["tokens"] == 12
    assert meta["metric_sets"]["family"]["metric_values"]["tokens"] == 34
    assert tools_complete(root)
    root["subagent_trajectories"].append(deepcopy(child))
    with pytest.raises(ValueError, match="duplicate"):
        validate(root)


def test_missing_child_is_not_an_empty_body_or_complete_tool_evidence():
    root = retain(
        trajectory("root"),
        missing=[{"trajectory_id": "missing", "parent_trajectory_id": "root"}],
    )
    assert coverage(root)["missing_members"] == 1
    assert not tools_complete(root)
    assert tools_complete(root, "root")
    assert len(selected(root)) == 1


def test_family_tool_success_excludes_unknown_outcomes_from_denominator():
    root, child = trajectory("root"), trajectory("child")
    root["steps"][0]["tool_calls"] = [
        {"tool_call_id": "same", "function_name": "shell", "arguments": {}}
    ]
    child["steps"][0]["tool_calls"] = [
        {"tool_call_id": "same", "function_name": "shell", "arguments": {}}
    ]
    child["steps"][0]["observation"] = {
        "results": [
            {
                "source_call_id": "same",
                "content": "failed",
                "extra": {"status": "failed", "exit_code": 1},
            }
        ]
    }
    root["subagent_trajectories"] = [child]
    family = project_meta_from_atif(retain(root), {})["metric_sets"]["family"]
    assert family["metric_values"]["tool_success_rate"] == 0
    assert family["metric_provenance"]["tool_success_rate"]["coverage"]["unknown"] == 1


def test_family_samples_include_child_but_root_remains_separate():
    rows = []
    for identity, scope, first, end, output in [
        ("root", "main", 100, 1000, 9),
        ("child", "child", 300, 2000, 34),
    ]:
        rows.append(
            {
                "type": "step",
                "id": "1",
                "session_id": identity,
                "scope": scope,
                "clock_id": identity,
                "start_ms": 0,
                "first_ms": first,
                "end_ms": end,
                "output_tokens": output,
                "complete": True,
                "token_basis": "final_output_includes_reasoning",
            }
        )
    manifest = {
        "producer": {"name": "fixture"},
        "complete": True,
        "events": {"sha256": "0" * 64},
        "capabilities": {"logical_steps": {"status": "verified"}},
    }
    assert calculate(manifest, rows, "root")["ttft_ms"]["value"] == 100
    assert calculate(manifest, rows, "family")["ttft_ms"]["value"] == 200
    assert calculate(manifest, rows, "family")["tps"]["value"] == pytest.approx(
        43 / 2.6
    )


def test_native_child_projection_keeps_own_samples_separate():
    root = trajectory("root")
    root["subagent_trajectories"] = [trajectory("child")]
    retain(root)
    native = {
        "ttft_ms": {
            "value": 123,
            "provenance": {
                "contract_version": 2,
                "source": "fixture",
                "basis_id": "fixture",
                "scope": "root",
                "quality": "reported",
            },
        }
    }
    meta = project_meta_from_atif(
        root, {}, native_members={"child": {"root": native, "family": native}}
    )
    assert (
        meta["subagent_meta"]["child"]["native_measurements"]["ttft_ms"]["value"] == 123
    )
    assert "metric_sets" not in meta["subagent_meta"]["child"]


def test_family_projection_constructs_scope_sets_only_at_root(monkeypatch):
    from psycheval.report import measurements

    root = trajectory("root")
    node = root
    for index in range(40):
        child = trajectory(str(index))
        node["subagent_trajectories"] = [child]
        node = child
    calls = []
    original = measurements.project

    def record(body, meta):
        calls.append(body["session_id"])
        return original(body, meta)

    monkeypatch.setattr(measurements, "project", record)
    result = project_meta_from_atif(root, {})
    assert calls == ["root"]
    assert result["metric_values"]["tokens"] == 41 * 12
    child_meta = result
    for index in range(40):
        child_meta = child_meta["subagent_meta"][str(index)]
        assert (
            not {
                "metric_sets",
                "metric_values",
                "metric_provenance",
                "family_coverage",
                "metric_scope",
            }
            & child_meta.keys()
        )
    assert project_meta_from_atif(root, result) == result


def test_pooled_family_measurements_report_matching_member_coverage():
    root, child, unknown = (
        trajectory("root"),
        trajectory("child"),
        trajectory("unknown"),
    )
    root["subagent_trajectories"] = [child, unknown]
    for item, ttft in [(root, 100), (child, 200)]:
        item["final_metrics"]["extra"] = {
            "model_inference": {
                "ttft_ms_sum": ttft,
                "ttft_sample_count": 1,
                "decode_duration_ms": 1000,
                "decode_token_count": 10,
                "decode_sample_count": 1,
                "cache_prompt_tokens": 100,
                "cache_read_tokens": 25,
                "cache_sample_count": 1,
            }
        }
    family = project_meta_from_atif(root, {})["metric_sets"]["family"]
    assert family["metric_values"]["ttft_ms"] == 150
    assert family["metric_values"]["tps"] == 10
    assert family["metric_values"]["cache_hit_rate"] == 0.25
    for key in ("ttft_ms", "tps", "cache_hit_rate"):
        source = family["metric_provenance"][key]
        assert source["scope"] == "family"
        assert source["source"] == "atif.family"
        assert source["coverage"] == {"measured": 2, "unknown": 1, "total": 3}


def test_family_pooling_never_pairs_unrelated_members_incomplete_statistics():
    root, child = trajectory("root"), trajectory("child")
    root["subagent_trajectories"] = [child]
    root["final_metrics"]["extra"] = {
        "model_inference": {
            "ttft_ms_sum": 100,
            "decode_token_count": 10,
            "cache_read_tokens": 30,
        }
    }
    child["final_metrics"]["extra"] = {
        "model_inference": {
            "ttft_sample_count": 1,
            "decode_duration_ms": 1000,
            "decode_sample_count": 1,
            "cache_prompt_tokens": 100,
            "cache_sample_count": 1,
        }
    }
    result = project_meta_from_atif(root, {})["metric_sets"]["family"]
    for key in ("ttft_ms", "tps", "cache_hit_rate"):
        assert result["metric_values"][key] is None
        assert result["metric_provenance"][key]["coverage"] == {
            "measured": 0,
            "unknown": 2,
            "total": 2,
        }


def test_inclusive_parent_usage_does_not_fabricate_exclusive_root():
    manifest = {
        "producer": {"name": "fixture"},
        "events": {"sha256": "0" * 64},
        "complete": True,
    }
    rows = [
        {
            "type": "request",
            "session_id": "root",
            "id": "1",
            "scope": "main",
            "input_tokens": 100,
            "output_tokens": 20,
            "includes_children": True,
        }
    ]
    assert calculate(manifest, rows, "family")["tokens"]["value"] == 120
    assert calculate(manifest, rows, "root")["tokens"]["value"] is None


def test_family_tool_durations_sum_own_contributions_without_summing_entry_time():
    root, child = trajectory("root"), trajectory("child")
    for body, duration in [(root, 10), (child, 20)]:
        body["steps"][0].update(
            tool_calls=[
                {"tool_call_id": "same", "function_name": "shell", "arguments": {}}
            ],
            observation={
                "results": [
                    {
                        "source_call_id": "same",
                        "content": "done",
                        "extra": {
                            "execution_duration_ms": duration,
                            "execution_duration_source": "native_tool_call",
                            "status": "completed",
                        },
                    }
                ]
            },
        )
    root["subagent_trajectories"] = [child]
    retain(root)
    meta = project_meta_from_atif(root, {})
    scopes = meta["metric_sets"]
    assert scopes["root"]["metric_values"]["tool_duration_ms"] == 10
    assert scopes["family"]["metric_values"]["tool_duration_ms"] == 30
    assert (
        scopes["root"]["metric_values"]["duration_ms"]
        == scopes["family"]["metric_values"]["duration_ms"]
    )
