import pytest

from psycheval.adapters.base import StepMeta, ToolMeta
from psycheval.report.metrics import latency_metrics
from psycheval.report.timing import (
    is_model_duration_source,
    node_duration,
    step_duration_ms,
)
from psycheval.state.catalog_projection import model_duration_ms, step_outline
from psycheval.timing_contract import timestamp_fallback_allowed, timing_source


def test_observed_output_does_not_become_model_latency_or_timestamp_estimate():
    trajectory = {
        "steps": [{"step_id": 1, "source": "agent"}, {"step_id": 2, "source": "agent"}]
    }
    meta = {
        "timestamp_semantics": "event_observed",
        "steps": [
            {
                "step_id": 1,
                "timestamp_ms": 1000,
                "duration_ms": 20,
                "duration_source": "acp_client_observed_output",
            },
            {"step_id": 2, "timestamp_ms": 2000, "duration_ms": None},
        ],
    }
    assert model_duration_ms(trajectory, meta) is None
    assert "model_duration_ms" not in latency_metrics(trajectory, meta)
    assert (
        step_duration_ms(
            StepMeta(step_id=2, source="agent", timestamp_ms=2000),
            3000,
            "event_observed",
        )
        is None
    )
    assert (
        step_outline(trajectory, meta)[0]["duration_source"]
        == "acp_client_observed_output"
    )
    assert "duration_ms" not in step_outline(trajectory, meta)[1]


def test_untimed_tools_allow_whole_step_node_estimates_but_never_model_estimates():
    step = StepMeta(
        step_id=1,
        source="agent",
        timestamp_ms=100,
        tool_calls=[ToolMeta(tool_call_id="a")],
    )
    assert step_duration_ms(step, 200, None) is None
    assert node_duration({"timestamp_ms": 100, "tool_calls": [{}]}, 200, None) == (
        100,
        "step_boundary_estimate",
    )
    assert node_duration(
        {"timestamp_ms": 100, "tool_calls": [{}]}, 200, "event_observed"
    ) == (None, None)
    assert node_duration(
        {"tool_calls": [{}, {"execution_duration_ms": 0}]}, 200, None
    ) == (0, "tool_activity_estimate")


@pytest.mark.parametrize(
    "source",
    [
        "acp_client_observed_output",
        "acp_client_observed_lifecycle",
        "tool_activity_estimate",
        "step_boundary_estimate",
        "opencode_native_tool_call",
    ],
)
def test_non_model_timing_sources_cannot_pollute_model_metrics(source):
    trajectory = {"steps": [{"step_id": 1, "source": "agent"}]}
    meta = {"steps": [{"step_id": 1, "duration_ms": 42, "duration_source": source}]}
    assert not is_model_duration_source(source)
    assert model_duration_ms(trajectory, meta) is None
    assert "model_duration_ms" not in latency_metrics(trajectory, meta)


def test_shared_timing_classification_retains_native_unknown_and_observed_semantics():
    assert is_model_duration_source("opencode_native_model_call")
    assert is_model_duration_source(None)
    assert timing_source("unknown") == {}
    assert timing_source("opencode_model_boundary_estimate")["estimated"]
    assert timing_source("hermes_message_boundary_estimate")["estimated"]
    assert timing_source("acp_client_observed_future")["observed"]
    assert not timestamp_fallback_allowed("EVENT_OBSERVED")
    assert not timestamp_fallback_allowed("order_only")
    assert timestamp_fallback_allowed(None)


def test_nodes_fall_back_to_tools_then_eligible_boundaries_without_model_pollution():
    trajectory = {"steps": [{"step_id": i, "source": "agent"} for i in range(1, 5)]}
    meta = {
        "steps": [
            {
                "step_id": 1,
                "timestamp_ms": 100,
                "tool_calls": [{"execution_duration_ms": 0}],
            },
            {
                "step_id": 2,
                "timestamp_ms": 200,
                "tool_calls": [
                    {"execution_duration_ms": 20},
                    {"execution_duration_ms": 30},
                ],
            },
            {"step_id": 3, "timestamp_ms": 300},
            {"step_id": 4, "timestamp_ms": 400},
        ]
    }
    outline = step_outline(trajectory, meta)
    assert [step.get("duration_ms") for step in outline] == [0, 50, 100, None]
    assert outline[1]["duration_source"] == "tool_activity_estimate"
    assert outline[2]["duration_source"] == "step_boundary_estimate"
    assert model_duration_ms(trajectory, meta) is None
