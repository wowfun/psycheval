import pytest

from psycheval.report.metrics import automatic_analysis_metrics, tool_success_rate
from psycheval.state.catalog import _saved_view_summary
from psycheval.state.catalog_projection import catalog_summary


@pytest.mark.parametrize(
    ("calls", "errors", "expected"),
    [
        (4, 0, 1),
        (4, 1, 0.75),
        (4, 4, 0),
        (0, 0, None),
        (None, 0, None),
        (4, None, None),
        (True, 0, None),
        (4, -1, None),
        (4, 5, None),
        (float("inf"), 0, None),
        ("4", "1", None),
        (4, "1", None),
    ],
)
def test_tool_success_rate_and_automatic_analysis(calls, errors, expected):
    assert tool_success_rate(calls, errors) == expected
    trajectory = {
        "final_metrics": {
            "extra": {
                "total_tool_calls": calls,
                "total_tool_errors": errors,
            }
        }
    }
    metrics = automatic_analysis_metrics(trajectory, {})["tooling"]
    assert metrics.get("tool_success_rate") == expected
    assert "tool_error_rate" not in metrics
    row = catalog_summary(trajectory, {}, 0)
    assert (
        tool_success_rate(row["total_tool_calls"], row["total_tool_errors"]) == expected
    )


@pytest.mark.parametrize("key", ["total_tool_calls", "total_tool_errors"])
@pytest.mark.parametrize("value", ["4", True, float("inf")])
def test_catalog_projection_does_not_coerce_invalid_count_values(key, value):
    counts = {"total_tool_calls": 4, "total_tool_errors": 1, key: value}
    row = catalog_summary({"final_metrics": {"extra": counts}}, {}, 0)
    assert row[key] is None
    other = "total_tool_errors" if key == "total_tool_calls" else "total_tool_calls"
    assert row[other] == counts[other]


def test_success_rate_percentiles_are_recomputed_from_each_measured_trial():
    rows = [
        {"total_tool_calls": calls, "total_tool_errors": errors}
        for calls, errors in [(10, 0), (10, 2), (10, 10), (0, 0), (10, None)]
    ]
    summary = _saved_view_summary("all", "overall", rows)
    metric = next(
        item
        for item in summary["groups"][0]["metrics"]
        if item["key"] == "tool_success_rate"
    )
    assert metric["count"] == 3
    assert metric["mean"] == pytest.approx(0.6)
    assert metric["distribution"]["p95"] == pytest.approx(0.98)
    assert metric["distribution"]["min"] == 0
    assert metric["distribution"]["max"] == 1
