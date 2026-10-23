from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from psycheval.config import ToolConfig, apply_toml_config
from psycheval.metric_contract import (
    BUILTIN_IDS,
    custom_metric_id,
    metric_descriptions,
    validate_metric_id,
)
from psycheval.state import CatalogQuery, WorkspaceCatalog, open_workspace_state
from psycheval.state.catalog import CatalogSummaryCapacityError
from psycheval.state.catalog_projection import catalog_summary
from tests.peval.cli_inputs_support import write_trial_cell_artifacts


def write_cell(root, index, extra):
    cell = root / "runs/default/psychevo" / f"session-{index}" / f"trial-{index}"
    write_trial_cell_artifacts(
        cell, session_id=f"session-{index}", trial_key=f"trial-{index}"
    )
    path = cell / "agent/trajectory.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value.setdefault("final_metrics", {}).setdefault("extra", {}).update(extra)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.fixture
def catalog(tmp_path):
    (tmp_path / "peval.toml").write_text("", encoding="utf-8")
    store = open_workspace_state(str(tmp_path))
    current = WorkspaceCatalog(store, ToolConfig(workspace_root=str(tmp_path)))
    yield current
    store.close()


def test_ids_scalars_aliases_and_explicit_unknowns():
    raw = "中文.'\"/% Score"
    metric = custom_metric_id("atif.extra", raw)
    assert validate_metric_id(metric) == metric
    assert custom_metric_id("atif.extra", "Score") != custom_metric_id(
        "atif.extra", "score"
    )
    for key in ("", " ", "x\0", "测" * 43):
        with pytest.raises(ValueError):
            custom_metric_id("atif.extra", key)
    row = catalog_summary(
        {
            "final_metrics": {
                "extra": {
                    raw: 0,
                    "total_turns": 2,
                    "model_inference": 42,
                    "usage": 7,
                    "nested": {"value": 2},
                    "truth": True,
                    "string": "5",
                    "nan": float("nan"),
                    "\n": 3,
                }
            }
        },
        {"rewards": {raw: 4}},
        0,
    )
    assert row["metric_values"][metric] == 0
    assert row["metric_values"][custom_metric_id("reward", raw)] == 4
    assert row["metric_values"]["turns"] == 2
    assert {key for key in row["metric_values"] if key.startswith("atif.extra:")} == {
        metric
    }
    assert row["metric_diagnostics"]


def test_browser_fixture_matches_authoritative_metric_descriptions():
    fixture = Path(__file__).parents[2] / "web/test/support/metrics.json"
    assert (
        json.loads(fixture.read_text(encoding="utf-8"))
        == metric_descriptions(BUILTIN_IDS)["metric_descriptions"]
    )


def test_reward_dimension_presence_does_not_create_a_primary_measurement(
    tmp_path, catalog
):
    trajectory = write_cell(tmp_path, 0, {})
    meta_path = trajectory.with_name("trajectory_meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update(score=None, rewards={"accuracy": 1, "safety": 0})
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    catalog.reconcile()
    page = catalog.query(CatalogQuery())
    assert page.column_presence["score"] == 1
    assert "score" not in page.items[0].payload["metric_values"]
    assert page.column_presence["reward:accuracy"] == 1


def test_descriptor_cache_is_isolated_and_refreshes_with_config_or_generation(
    tmp_path, catalog
):
    write_cell(tmp_path, 0, {"energy": 0})
    catalog.reconcile()
    with patch(
        "psycheval.state.catalog.metric_descriptions", wraps=metric_descriptions
    ) as build:
        first = catalog.metric_metadata()
        first["metric_descriptions"][0]["label"] = "mutated by caller"
        assert catalog.metric_metadata()["metric_descriptions"][0]["label"] == "Reward"
        assert build.call_count == 1
        catalog.config = apply_toml_config(
            catalog.config, {"metrics": {"score": {"label": "Changed"}}}
        )
        assert catalog.metric_metadata()["metric_descriptions"][0]["label"] == "Changed"
        assert build.call_count == 2
        write_cell(tmp_path, 1, {"new": 0})
        catalog.reconcile()
        assert any(
            item["key"] == "atif.extra:new"
            for item in catalog.metric_metadata()["metric_descriptions"]
        )
        assert build.call_count == 3


def test_timing_and_rule_counts_are_evidence_based():
    trajectory = {"steps": [{"source": "agent"}, {"source": "agent"}]}
    meta = {
        "steps": [
            {
                "duration_ms": 0,
                "duration_source": "opencode_native_model_call",
                "tool_calls": [{"execution_duration_ms": 12}],
            },
            {
                "duration_ms": 9,
                "duration_source": "acp_client_observed_output",
                "tool_calls": [{"execution_duration_ms": None}],
            },
        ],
        "verifier_evidence": {"tests": {"passed": 0, "total": 4}},
        "rewards": {"rule_score": 0},
    }
    values = catalog_summary(trajectory, meta, 0)["metric_values"]
    assert (
        values["model_duration_ms"],
        values["tool_duration_ms"],
        values["other_duration_ms"],
    ) == (0, 12, 9)
    assert values["test_pass_rate"] == 0
    assert "reward:llm_score" not in values
    meta["verifier_evidence"]["tests"] = {"passed": 0, "total": 0}
    assert "test_pass_rate" not in catalog_summary(trajectory, meta, 0)["metric_values"]
    assert (
        "other_duration_ms"
        not in catalog_summary({}, {"duration_ms": 100}, 0)["metric_values"]
    )


def test_index_full_scope_safe_sort_missing_last_and_cache(tmp_path, catalog):
    key = "x'\".); DROP TABLE cells; --"
    metric = custom_metric_id("atif.extra", key)
    write_cell(tmp_path, 0, {key: 0})
    write_cell(tmp_path, 1, {key: -3})
    write_cell(tmp_path, 2, {})
    catalog.reconcile()
    page = catalog.query(
        CatalogQuery(sort="metric:" + metric, direction="asc", page_size=1)
    )
    assert page.total == 3 and page.column_presence[metric] == 2
    assert page.items[0].payload["metric_values"][metric] == -3
    last = catalog.query(
        CatalogQuery(sort="metric:" + metric, direction="asc", page=3, page_size=1)
    )
    assert metric not in last.items[0].payload["metric_values"]
    summary = catalog.summarize_query(CatalogQuery(), name="Home", group_by="overall")
    stats = next(
        item
        for item in summary["summary"]["groups"][0]["metrics"]
        if item["key"] == metric
    )
    assert stats["count"] == 2 and stats["mean"] == -1.5
    catalog.config = apply_toml_config(
        catalog.config,
        {"metrics": {metric: {"label": "Updated", "direction": "lower"}}},
    )
    with patch(
        "psycheval.state.catalog._summary_rows",
        side_effect=AssertionError("numeric cache must be reused"),
    ):
        fresh = catalog.summarize_query(
            CatalogQuery(page=2), name="Home", group_by="overall"
        )
    assert fresh["summary"] is summary["summary"]
    assert fresh["metric_revision"] != summary["metric_revision"]
    assert (
        next(item for item in fresh["metric_descriptions"] if item["key"] == metric)[
            "label"
        ]
        == "Updated"
    )
    saved = catalog.summarize_saved_views([("saved", CatalogQuery(), "overall")])
    assert len(saved["views"][0]["groups"][0]["metrics"]) == 10
    assert metric not in {
        item["key"] for item in saved["views"][0]["groups"][0]["metrics"]
    }
    assert (
        catalog.query(CatalogQuery(sort="metric:reward:gone")).to_dict()[
            "effective_sort"
        ]
        == "last_turn_end"
    )


def test_capacity_failure_preserves_generation(tmp_path, catalog):
    write_cell(tmp_path, 1, {"first": 1})
    catalog.reconcile()
    generation = catalog.generation
    write_cell(tmp_path, 2, {f"metric_{index}": index for index in range(128)})
    with pytest.raises(CatalogSummaryCapacityError, match="128"):
        catalog.reconcile()
    assert catalog.generation == generation
    assert catalog.query(CatalogQuery()).total == 1
    assert len(catalog.metric_metadata()["metric_descriptions"]) == len(BUILTIN_IDS) + 1


def test_config_validation_and_pending_diagnostics(catalog):
    for values in (
        {"unknown": {}},
        {"score": {"unit": "ms"}},
        {"reward:x": {"direction": "up"}},
        {"reward:x": {"unexpected": True}},
    ):
        with pytest.raises(ValueError):
            apply_toml_config(ToolConfig(), {"metrics": values})
    catalog.config = apply_toml_config(
        catalog.config,
        {
            "metrics": {
                "reward:pending": {"label": "Pending"},
                "tokens": {"direction": "lower"},
            }
        },
    )
    metadata = catalog.metric_metadata()
    assert metadata["metric_diagnostics"] == [
        "Metric configured but not discovered: reward:pending"
    ]
    assert (
        next(
            item for item in metadata["metric_descriptions"] if item["key"] == "tokens"
        )["direction"]
        == "lower"
    )


@pytest.mark.parametrize("step", [False, True])
def test_harbor_scores_without_atif_and_next_reconcile_revision(tmp_path, step):
    from tests.peval.test_harbor_trials import (
        HarborTrialTests,
        completed_result,
        write_trial,
    )

    jobs = tmp_path / "jobs"
    trial = jobs / "job-a/trial-a"
    write_trial(trial, result=completed_result())
    data = trial / "steps/first" if step else trial
    result = completed_result(reward=0.8)
    result["verifier_result"]["rewards"].update(rule_score=0, llm_score=0.6)
    write_trial(data, result=result)
    (data / "agent/trajectory.json").unlink()
    if step:
        (trial / "agent/trajectory.json").unlink()
        (trial / "result.json").write_text(
            json.dumps(
                {
                    **completed_result(),
                    "step_results": [{**result, "step_name": "first"}],
                }
            ),
            encoding="utf-8",
        )
    (data / "verifier").mkdir()
    score_path = data / "verifier/score.json"
    score_path.write_text(
        json.dumps({"reward": 0.1, "tests_passed": 0, "tests_total": 4}),
        encoding="utf-8",
    )
    store, _config, catalog = HarborTrialTests().workspace(tmp_path / "workspace", jobs)
    try:
        catalog.reconcile()
        before = catalog.query(CatalogQuery()).items[0].to_dict()
        values = before["metric_values"]
        assert values["score"] == values["reward:reward"] == 0.8
        assert values["reward:rule_score"] == 0 and values["reward:llm_score"] == 0.6
        assert (
            values["tests_passed"],
            values["tests_total"],
            values["test_pass_rate"],
        ) == (0, 4, 0)
        with patch.object(catalog.sources, "load", wraps=catalog.sources.load) as load:
            catalog.reconcile()
            load.assert_not_called()
        score_path.write_text(
            json.dumps({"tests_passed": 3, "tests_total": 4}), encoding="utf-8"
        )
        assert (
            catalog.query(CatalogQuery())
            .items[0]
            .to_dict()["metric_values"]["test_pass_rate"]
            == 0
        )
        catalog.reconcile()
        after = catalog.query(CatalogQuery()).items[0].to_dict()
        assert before["artifact_revision"] != after["artifact_revision"]
        assert after["metric_values"]["test_pass_rate"] == 0.75
        assert after["metric_values"]["score"] == 0.8
        with patch.object(catalog.sources, "load", wraps=catalog.sources.load) as load:
            catalog.reconcile()
            load.assert_not_called()
        assert not (data / "agent/trajectory.json").exists()
    finally:
        store.close()


def test_invalid_verifier_config_remains_a_single_trial_diagnostic(tmp_path):
    from tests.peval.test_harbor_trials import (
        HarborTrialTests,
        completed_result,
        write_trial,
    )

    jobs = tmp_path / "jobs"
    for name in ("good", "bad"):
        write_trial(jobs / "job" / name, result=completed_result())
    config_path = jobs / "job/bad/config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["verifier"] = []
    config_path.write_text(json.dumps(config), encoding="utf-8")
    store, _, catalog = HarborTrialTests().workspace(tmp_path / "workspace", jobs)
    try:
        catalog.reconcile()
        rows = [
            item.to_dict()
            for item in catalog.query(CatalogQuery(include_unreadable=True)).items
        ]
        assert len(rows) == 2
        assert sum(row["readable"] for row in rows) == 1
        assert "verifier configuration must be an object" in next(
            row["last_error"] for row in rows if not row["readable"]
        )
        with patch.object(catalog.sources, "load", wraps=catalog.sources.load) as load:
            catalog.reconcile()
            load.assert_not_called()
    finally:
        store.close()


@pytest.mark.parametrize("value", [True, "3", float("inf"), float("nan")])
def test_builtin_values_do_not_coerce_unknowns(value):
    row = catalog_summary(
        {
            "final_metrics": {
                "total_prompt_tokens": value,
                "total_cost_usd": value,
                "extra": {"total_turns": value},
            }
        },
        {"duration_ms": value, "score": value},
        0,
    )
    assert not row["metric_values"]


def test_finite_large_numbers_remain_queryable_and_summarizable(tmp_path, catalog):
    write_cell(tmp_path, 0, {"large": 1e308, "large_int": 2**90})
    write_cell(tmp_path, 1, {"large": 1e308})
    catalog.reconcile()
    page = catalog.query(CatalogQuery(sort="metric:atif.extra:large_int"))
    assert page.items[0].payload["metric_values"]["atif.extra:large_int"] == 2**90
    summary = catalog.summarize_query(CatalogQuery(), name="Home", group_by="overall")
    large = next(
        item
        for item in summary["summary"]["groups"][0]["metrics"]
        if item["key"] == "atif.extra:large"
    )
    assert large["mean"] == 1e308
    json.dumps(summary, allow_nan=False)


def test_rule_count_projection_rejects_coercions(tmp_path):
    from psycheval.state.harbor_verifier_evidence import read_harbor_verifier_evidence

    verifier = tmp_path / "verifier"
    verifier.mkdir()
    for passed in (True, "3", 3.1, -1):
        (verifier / "score.json").write_text(
            json.dumps({"tests_passed": passed, "tests_total": 4}), encoding="utf-8"
        )
        evidence = read_harbor_verifier_evidence(
            tmp_path,
            containment_root=tmp_path,
            dataset_format="harbor",
            harbor_reward=1,
        )
        assert "passed" not in evidence.tests


def test_selected_excel_and_runtime_descriptor_refresh(tmp_path, catalog):
    from io import BytesIO
    from xml.etree import ElementTree as ET
    from zipfile import ZipFile

    from psycheval.serve import ServeRuntime
    from psycheval.serve.exports import build_serve_export
    from psycheval.serve.summary_xlsx import summary_workbook

    write_cell(tmp_path, 0, {"energy": 0, "another": 5})
    runtime = ServeRuntime(catalog.store, catalog.config)
    try:
        runtime.catalog.reconcile()
        query = CatalogQuery()
        previous = runtime.leaderboard_summary(query, group_by="overall")
        runtime.set_config(
            apply_toml_config(
                runtime.config,
                {"metrics": {"atif.extra:energy": {"label": "Energy", "unit": "Wh"}}},
            )
        )
        with patch(
            "psycheval.state.catalog._summary_rows",
            side_effect=AssertionError("selection/config must reuse numeric cache"),
        ):
            sheet = runtime.leaderboard_summary_worksheet(
                query,
                group_by="overall",
                statistic="p95",
                metrics=["atif.extra:energy"],
            )
        assert (
            len(sheet.metric_descriptions) == 1
            and sheet.metric_descriptions[0]["unit"] == "Wh"
        )
        assert (
            runtime.leaderboard_summary(query, group_by="overall")["metric_revision"]
            != previous["metric_revision"]
        )
        with ZipFile(BytesIO(summary_workbook([sheet]))) as archive:
            strings = archive.read("xl/sharedStrings.xml").decode()
            assert "Energy (Wh)" in strings and "another" not in strings
            assert "<v>0</v>" in archive.read("xl/worksheets/sheet1.xml").decode()
        detailed = build_serve_export(
            runtime.catalog, catalog.store, runtime.config, kind="xlsx"
        )
        with ZipFile(BytesIO(detailed.content)) as archive:
            rows = ET.fromstring(archive.read("xl/worksheets/sheet1.xml")).findall(
                "{*}sheetData/{*}row"
            )
            header = ["".join(cell.itertext()) for cell in rows[0]]
            value = rows[1][header.index("Energy (Wh)")]
            assert value.get("t") in (None, "n") and value.findtext("{*}v") == "0"
    finally:
        runtime.close()
