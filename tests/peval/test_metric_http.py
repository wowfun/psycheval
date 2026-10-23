from __future__ import annotations

import json

import pytest

from tests.peval import test_serve_catalog_http as support
from tests.peval.cli_inputs_support import write_trial_cell_artifacts


@pytest.fixture
def metric_server(tmp_path):
    write_trial_cell_artifacts(
        tmp_path / "runs/default/psychevo/session/trial",
        session_id="session",
        trial_key="trial",
    )
    helper = support.ServeCatalogHttpTests()
    store, runtime, server, thread = helper.running_server(tmp_path)
    try:
        yield lambda payload: helper.request(server, "POST", "/api/exports", payload)
    finally:
        helper.stop(store, server, thread)


def summary_export(metrics):
    query = support.leaderboard_summary_query()
    query.pop("group_by")
    return {
        "kind": "summary_xlsx",
        "summary": {
            "scope": "leaderboard",
            "query": query,
            "group_by": "overall",
            "statistic": "mean",
            "metrics": metrics,
        },
    }


@pytest.mark.parametrize(
    "metrics",
    [
        None,
        "score",
        [True],
        ["score", "score"],
        ["reward:%zz"],
        ["foo/bar"],
        [f"reward:k{i}" for i in range(33)],
    ],
)
def test_invalid_metric_selection_is_a_request_error(metric_server, metrics):
    status, headers, body = metric_server(summary_export(metrics))
    assert status == 400, body[:200]
    assert headers["content-type"].startswith("application/problem+json")
    assert json.loads(body)["detail"]


def test_missing_selection_is_required_and_unavailable_ids_are_gaps(metric_server):
    request = summary_export([])
    del request["summary"]["metrics"]
    assert metric_server(request)[0] == 400
    for ids in ([], ["reward:removed"], ["unregistered"]):
        assert metric_server(summary_export(ids))[0] == 400
    for ids in (
        ["total_tool_calls", "reward:removed"],
        ["total_tool_calls", "unregistered"],
    ):
        status, _, body = metric_server(summary_export(ids))
        assert status == 200, body[:200]
        assert body.startswith(b"PK")
