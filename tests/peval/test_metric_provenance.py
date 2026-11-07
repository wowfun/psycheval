import json

import pytest

from psycheval.harbor.measurements import calculate, measurement
from psycheval.report.builder import project_meta_from_atif
from psycheval.report.measurements import construct
from psycheval.state.catalog_projection import catalog_summary
from psycheval.state.catalog_summaries import summarize_rows
from psycheval.state.workspace_harbor import _project_harbor_metrics
from psycheval.state.workspace_source_models import HarborTelemetry


def test_catalog_reuses_projected_value_and_source(monkeypatch):
    import psycheval.state.catalog_projection as projection

    trajectory = {"steps": []}
    meta = project_meta_from_atif(trajectory, {})
    monkeypatch.setattr(
        projection, "construct", lambda *_: pytest.fail("duplicate construction")
    )
    row = projection.catalog_summary(trajectory, meta, 0)
    assert row["metric_provenance"] == meta["metric_provenance"]


def test_catalog_end_source_comes_from_same_selection_as_value():
    meta = {
        "finished_at_ms": 12.5,
        "adapter": "harbor",
        "evaluation": {
            "phase_timing": {"agent_execution": {"finished_at": "2026-11-07T00:00:00Z"}}
        },
    }
    row = catalog_summary({"steps": []}, meta, 0)
    assert row["last_turn_finished_at_ms"] == 12.5
    assert row["last_turn_finished_at_source"] == "trajectory"


def test_active_selection_keeps_value_and_provenance_together_including_zero():
    trajectory = {
        "steps": [
            {
                "step_id": 1,
                "source": "agent",
                "message": "OK",
                "extra": {
                    "duration_ms": 25,
                    "duration_source": "opencode_native_model_call",
                },
            }
        ]
    }
    for source, method, value in [
        ("supplemental_telemetry", "sum(aligned_telemetry_contributions)", 0),
        ("harbor.agent_execution", "finished_at-started_at", 80),
    ]:
        meta = project_meta_from_atif(
            trajectory,
            {
                "import_context": {
                    "source_timing": {
                        "duration_ms": value,
                        "duration_source": source,
                        "duration_method": method,
                    }
                }
            },
        )
        assert meta["metric_values"]["duration_ms"] == value
        assert meta["metric_provenance"]["duration_ms"]["source"] == source
        assert (
            catalog_summary(trajectory, meta, 0)["metric_provenance"]
            == meta["metric_provenance"]
        )
    meta = project_meta_from_atif(trajectory, {})
    assert meta["duration_ms"] == 25
    assert (
        meta["metric_provenance"]["duration_ms"]["method"]
        == "sum(agent_and_tool_durations)"
    )


def test_explicit_unknown_blocks_harbor_and_telemetry_source_selection():
    telemetry = HarborTelemetry(
        steps=[],
        duration_ms=None,
        final_metrics={"total_prompt_tokens": 12, "total_completion_tokens": 3},
        revision="fixture",
    )
    projected = _project_harbor_metrics(
        {
            "schema_version": "ATIF-v1.8",
            "session_id": "s",
            "agent": {"name": "fixture", "version": "1"},
            "steps": [{"step_id": 1, "source": "user", "message": "fixture"}],
            "final_metrics": {"total_prompt_tokens": None},
        },
        {"agent_result": {"n_input_tokens": 9, "n_output_tokens": 8}},
        telemetry,
    )
    values, provenance = construct(projected, {})
    assert values["tokens"] == 3  # Historical partial sum is preserved.
    assert provenance["tokens"]["source"] == "supplemental_telemetry"
    assert provenance["tokens"]["contract_version"] == "legacy"


def test_bad_new_evidence_never_uses_legacy_values():
    trajectory = {
        "extra": {"measurements": {"contract_version": 1}},
        "final_metrics": {
            "total_prompt_tokens": 100,
            "total_completion_tokens": 20,
            "extra": {"total_tool_calls": 2, "total_tool_errors": 0},
        },
    }
    values, provenance = construct(
        trajectory, {"measurement_error": "invalid_measurement_evidence"}
    )
    assert values["tokens"] is None and values["tool_success_rate"] is None
    assert provenance["tokens"]["contract_version"] == 1
    assert provenance["tokens"]["missing_reason"] == "invalid_measurement_evidence"


def test_summary_discloses_legacy_denominator_and_keeps_mean_and_overflow_counts():
    rows = []
    for index in range(25):
        item = measurement(
            0.5,
            source=f"agent-{index}",
            method="successes/known" if index else "(calls-errors)/calls",
            basis="known" if index else "legacy",
            version=1 if index else "legacy",
        )
        rows.append(
            {
                "metric_values": {"tool_success_rate": item["value"]},
                "metric_provenance": {"tool_success_rate": item["provenance"]},
            }
        )
    metric = summarize_rows("All", "overall", rows, ["tool_success_rate"])["groups"][0][
        "metrics"
    ][0]
    assert metric["mean"] == 0.5 and metric["count"] == 25
    provenance = metric["provenance"]
    assert provenance["mixed_basis"] and provenance["mixed_sources"]
    assert len(provenance["variants"]) == 16 and provenance["other"]["trials"] == 9
    assert provenance["trials"] == 25
    assert provenance["variants"][0]["method"] == "(calls-errors)/calls"


def test_default_provenance_bounds_and_missing_metadata():
    _, provenance = construct({}, {})
    assert len(provenance) == 12
    assert all(len(json.dumps(item).encode()) <= 2048 for item in provenance.values())
    assert len(json.dumps(provenance).encode()) <= 32768
    assert all(item["contract_version"] == "legacy" for item in provenance.values())


@pytest.mark.parametrize("partial,collection", [(True, "complete"), (False, "partial")])
def test_count_retention_follows_trajectory_not_measurement_collection(
    partial, collection
):
    trajectory = {
        "steps": [{"step_id": 1, "source": "agent", "message": "retained"}],
        "extra": {"measurements": {"contract_version": 1}, "incomplete": partial},
        "final_metrics": {"extra": {"total_tool_calls": 0}},
    }
    values, provenance = construct(trajectory, {"measurement_retention": collection})
    assert values["agent_steps"] == 1 and values["total_tool_calls"] == 0
    for key in ("agent_steps", "total_tool_calls"):
        assert provenance[key]["retention"] == ("partial" if partial else "complete")
        assert provenance[key]["scope"] == (
            "retained_main_trajectory" if partial else "main_session"
        )
        assert provenance[key]["basis_id"].endswith(":retained") == partial


def test_billed_and_native_estimated_cost_remain_distinct_in_summary():
    rows = []
    for kind in ("billed", "native_estimate"):
        result = calculate(
            {
                "producer": {"name": "fixture"},
                "complete": True,
                "events": {"sha256": "0" * 64},
            },
            [
                {
                    "type": "request",
                    "id": "r",
                    "session_id": "s",
                    "cost_usd": 1,
                    "cost_kind": kind,
                }
            ],
        )["cost_usd"]
        assert result["value"] == 1
        assert result["provenance"]["quality"] == (
            "estimated" if kind == "native_estimate" else "reported"
        )
        rows.append(
            {
                "metric_values": {"cost_usd": 1},
                "metric_provenance": {"cost_usd": result["provenance"]},
            }
        )
    summary = summarize_rows("All", "overall", rows, ["cost_usd"])["groups"][0][
        "metrics"
    ][0]
    assert summary["mean"] == 1
    provenance = summary["provenance"]
    assert provenance["mixed_basis"] and not provenance["mixed_sources"]
    assert {tuple(v["cost_kinds"]) for v in provenance["variants"]} == {
        ("billed",),
        ("native_estimate",),
    }


@pytest.mark.parametrize(
    "retained,reason",
    [
        ({"source": "retained", "payload": "x" * 3000}, "metric_provenance_limit"),
        (
            {"source": "retained", "evidence": ["ref"] * 5},
            "metric_evidence_reference_limit",
        ),
    ],
)
def test_retained_selection_cannot_bypass_final_provenance_limits(retained, reason):
    with pytest.raises(ValueError, match=reason):
        construct({}, {"metric_provenance": {"score": retained}})


def test_summary_provenance_capacity_keeps_counts_after_shared_budget_exhaustion():
    from psycheval.harbor.measurements import METRICS

    def rows():
        for group in range(1000):
            for variant in range(17):
                provenance = {
                    key: measurement(
                        1,
                        source=f"source-{variant}",
                        method="sum",
                        basis=f"basis-{variant}",
                        producer={"name": "fixture", "version": "v" * 128},
                        clock={"type": "epoch", "semantics": "observed"},
                    )["provenance"]
                    for key in METRICS
                }
                yield {
                    "agent_name": str(group),
                    "metric_values": dict.fromkeys(METRICS, 1),
                    "metric_provenance": provenance,
                }

    result = summarize_rows("capacity", "agent", rows(), list(METRICS))
    provenance = [
        metric["provenance"]
        for group in result["groups"]
        for metric in group["metrics"]
    ]
    assert len(json.dumps(provenance, ensure_ascii=False).encode()) <= 8 * 1024 * 1024
    assert all(
        item["trials"] == 17 and item["available"] == 17 and item["mixed_basis"]
        for item in provenance
    )
    assert all(
        sum(v["trials"] for v in item["variants"])
        + item.get("other", {}).get("trials", 0)
        == 17
        for item in provenance
    )


def test_excel_keeps_structured_trial_and_summary_provenance():
    import io
    import zipfile
    from xml.etree import ElementTree as E

    from psycheval.serve.exports import xlsx_summary
    from psycheval.serve.summary_xlsx import SummaryWorksheet, summary_workbook

    values, provenance = construct({}, {})
    content = xlsx_summary([{"metric_values": values, "metric_provenance": provenance}])
    with zipfile.ZipFile(io.BytesIO(content)) as workbook:
        names = [
            e.attrib["name"]
            for e in E.fromstring(workbook.read("xl/workbook.xml")).findall(
                ".//{*}sheet"
            )
        ]
        assert names == ["Leaderboard", "Metric Provenance"]
        sheet = E.fromstring(workbook.read("xl/worksheets/sheet2.xml"))
        rows = sheet.findall(".//{*}row")[1:]
        assert len(rows) == 12
        assert all(
            json.loads(row[-1].findtext(".//{*}t"))["contract_version"] == "legacy"
            for row in rows
        )
    summary = summarize_rows(
        "all",
        "overall",
        [{"metric_values": values, "metric_provenance": provenance}],
        ["tokens"],
    )
    content = summary_workbook(
        [
            SummaryWorksheet(
                name="all",
                group_by="overall",
                matched_count=1,
                groups=summary["groups"],
            )
        ]
    )
    with zipfile.ZipFile(io.BytesIO(content)) as workbook:
        strings = E.fromstring(workbook.read("xl/sharedStrings.xml"))
        payload = [
            json.loads(node.text)
            for node in strings.findall(".//{*}t")
            if node.text.startswith("{")
        ]
        assert (
            payload[0]["summary"]["trials"] == 1
            and payload[0]["summary"]["missing"] == 1
        )
