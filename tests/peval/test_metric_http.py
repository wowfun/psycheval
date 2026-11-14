from __future__ import annotations

import json

import pytest

from tests.peval import catalog_http_support as support
from tests.peval.cli_inputs_support import write_trial_cell_artifacts


@pytest.fixture
def metric_server(tmp_path):
    write_trial_cell_artifacts(
        tmp_path / "runs/default/psychevo/session/trial",
        session_id="session",
        trial_key="trial",
    )
    helper = support.CatalogHttpTestCase()
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
            "comparison_groups": None,
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


@pytest.mark.parametrize("groups", [False, "all", [False], [1], [""], ["bad\0key"]])
def test_invalid_comparison_groups_are_request_errors(metric_server, groups):
    request = summary_export(["total_tool_calls"])
    request["summary"]["comparison_groups"] = groups
    assert metric_server(request)[0] == 400


def test_summary_export_filters_groups_without_changing_match_count(metric_server):
    import io
    import xml.etree.ElementTree as ET
    import zipfile

    request = summary_export(["total_tool_calls"])
    for keys, selected_count in (
        (None, 1),
        (["overall"], 1),
        ([], 0),
        ([None, "missing"], 0),
    ):
        request["summary"]["comparison_groups"] = keys
        status, _, body = metric_server(request)
        assert status == 200, body[:200]
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            namespace = {
                "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            }
            strings = [
                "".join(node.itertext())
                for node in ET.fromstring(archive.read("xl/sharedStrings.xml"))
            ]
            rows = ET.fromstring(archive.read("xl/worksheets/sheet1.xml")).findall(
                ".//s:row", namespace
            )
            values = []
            for row in rows:
                values.append(
                    [
                        strings[int(cell.find("s:v", namespace).text)]
                        if cell.get("t") == "s"
                        else cell.findtext("s:v", namespaces=namespace)
                        for cell in row
                        if cell.find("s:v", namespace) is not None
                    ]
                )
            assert ["Selected groups", str(selected_count)] in values
            assert ["Match count", "1"] in values
            assert any("Overall" in row for row in values) == bool(selected_count)
