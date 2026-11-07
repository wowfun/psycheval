from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from psycheval.config import HarborDataset, HarborMount
from psycheval.state import CatalogQuery, CatalogSummaryCapacityError
from tests.peval.catalog_http_support import (
    CatalogHttpTestCase,
    leaderboard_summary_query,
    summary_request,
)
from tests.peval.cli_inputs_support import write_trial_cell_artifacts
from tests.peval.test_harbor_evidence import write_evidence_trial, write_task


class ServeCatalogSummaryHttpTests(CatalogHttpTestCase):
    def test_dataset_queries_summaries_and_exports_cover_all_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for dataset_id, count in (("alpha", 105), ("beta", 2)):
                write_task(root / dataset_id / dataset_id, f"org/{dataset_id}")
                for index in range(count):
                    write_evidence_trial(
                        root / "jobs" / dataset_id / f"trial-{index:03d}",
                        config_task={"name": dataset_id, "source": "org"},
                    )
            write_trial_cell_artifacts(
                root / "runs/default/psychevo/local/local",
                session_id="local",
                trial_key="local",
            )
            store, runtime, server, thread = self.running_server(root)
            try:
                runtime.set_config(
                    runtime.config.validated_update(
                        harbor_datasets=tuple(
                            HarborDataset(id=key, path=str(root / key))
                            for key in ("alpha", "beta")
                        ),
                        harbor_mounts=(
                            HarborMount(
                                id="jobs",
                                path=str(root / "jobs"),
                                dataset_ids=("alpha", "beta"),
                            ),
                        ),
                    )
                )
                runtime.catalog.reconcile()
                for direction, expected in (("asc", "alpha"), ("desc", "beta")):
                    status, _, body = self.request(
                        server,
                        "GET",
                        f"/api/catalog?sort=dataset&direction={direction}",
                    )
                    self.assertEqual(status, 200, body)
                    page = json.loads(body)
                    self.assertEqual(page["items"][0]["dataset_id"], expected)
                    self.assertEqual(page["column_presence"]["dataset_id"], 107)
                    status, _, body = self.request(
                        server,
                        "GET",
                        f"/api/catalog?sort=dataset&direction={direction}&page=2",
                    )
                    self.assertIsNone(json.loads(body)["items"][-1]["dataset_id"])
                status, _, body = self.request(
                    server, "GET", "/api/catalog?dataset=alpha&sort=dataset&page=2"
                )
                self.assertEqual(status, 200, body)
                page = json.loads(body)
                self.assertEqual(page["total"], 105)
                self.assertEqual(len(page["items"]), 5)
                self.assertEqual(
                    page["facets"]["datasets"],
                    [{"value": "alpha", "count": 105}, {"value": "beta", "count": 2}],
                )
                runtime.workspace_views.save(
                    name="Alpha",
                    filters={"tasks": ["org/alpha"]},
                    group_by="overall",
                    notes="",
                )
                for datasets, expected in (
                    (["alpha"], 105),
                    (["beta"], 2),
                    (["alpha", "beta"], 107),
                    (["missing"], 0),
                ):
                    query = leaderboard_summary_query(datasets=datasets)
                    status, _, body = self.request(
                        server, "POST", "/api/catalog-summaries", query
                    )
                    self.assertEqual(status, 200, body)
                    self.assertEqual(
                        json.loads(body)["summary"]["matched_count"], expected
                    )
                    page_query = {
                        key: value for key, value in query.items() if key != "group_by"
                    }
                    page_query.update(
                        page=1,
                        page_size=100,
                        sort="dataset",
                        direction="asc",
                        views=["Alpha"],
                    )
                    status, _, body = self.request(
                        server, "POST", "/api/catalog-queries", page_query
                    )
                    self.assertEqual(status, 200, body)
                    self.assertEqual(
                        json.loads(body)["total"], 105 if "alpha" in datasets else 0
                    )
                status, _, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "xlsx",
                        "query": {
                            "datasets": ["alpha"],
                            "sort": "dataset",
                            "direction": "asc",
                        },
                    },
                )
                self.assertEqual(status, 200, body[:200])
                with zipfile.ZipFile(BytesIO(body)) as archive:
                    sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
                self.assertEqual(sheet.count("<row "), 106)
                self.assertIn('<c r="A1" s="1" t="inlineStr"><is><t>Dataset</t>', sheet)
                self.assertIn('<c r="A2" t="inlineStr"><is><t>alpha</t>', sheet)
                query = leaderboard_summary_query(datasets=["beta"])
                query.pop("group_by")
                status, _, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": summary_request(query, "overall", "mean"),
                    },
                )
                self.assertEqual(status, 200, body[:200])
                with zipfile.ZipFile(BytesIO(body)) as archive:
                    self.assertIn(b"<v>2</v>", archive.read("xl/worksheets/sheet1.xml"))
            finally:
                self.stop(store, server, thread)

    def test_server_exports_filtered_xlsx_selected_json_and_rejects_legacy_html(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(2):
                write_trial_cell_artifacts(
                    root / f"runs/default/psychevo/s{index}/s{index}_t001",
                    session_id=f"s{index}",
                    trial_key=f"s{index}_t001",
                )
            store, runtime, server, thread = self.running_server(root)
            items = runtime.catalog.query(CatalogQuery()).items
            try:
                status, _headers, body = self.request(
                    server,
                    "PATCH",
                    f"/api/sources/{items[0].source_key}",
                    {"category": "Regression"},
                )
                self.assertEqual(status, 200, body)
                status, headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {"kind": "xlsx", "query": {"state": "active"}},
                )
                self.assertEqual(status, 200)
                self.assertIn("spreadsheetml", headers["content-type"])
                with zipfile.ZipFile(BytesIO(body)) as archive:
                    sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
                self.assertIn("s0", sheet)
                self.assertIn("s1", sheet)
                self.assertLess(sheet.index("Category"), sheet.index("Tags"))

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {"kind": "json", "source_keys": [items[0].source_key]},
                )
                report = json.loads(body)
                self.assertEqual(status, 200)
                self.assertEqual(len(report["trajectory"]), 1)
                self.assertEqual(
                    report["trajectory"][0]["session_id"],
                    items[0].payload["trial_session_id"],
                )
                self.assertEqual(
                    report["trajectory_meta"][0]["source_category"],
                    "Regression",
                )

                status, headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {"kind": "html", "source_keys": [items[1].source_key]},
                )
                self.assertEqual(status, 400)
                self.assertIn("xlsx or json", json.loads(body)["detail"])

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {"kind": "workspace_html", "source_keys": [items[1].source_key]},
                )
                self.assertEqual(status, 400)
                self.assertIn("xlsx or json", json.loads(body)["detail"])
            finally:
                self.stop(store, server, thread)

    def test_leaderboard_summary_and_export_cover_all_125_matching_trials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(125):
                cell = root / f"runs/default/psychevo/s{index:03d}/t{index:03d}"
                write_trial_cell_artifacts(
                    cell,
                    session_id=f"s{index:03d}",
                    trial_key=f"t{index:03d}",
                )
                meta_path = cell / "agent" / "trajectory_meta.json"
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["status"] = "failed" if index % 10 == 0 else "passed"
                meta_path.write_text(json.dumps(meta), encoding="utf-8")
                trajectory_path = cell / "agent/trajectory.json"
                trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
                trajectory["steps"][1]["extra"] = {"duration_ms": index}
                trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
                if index % 2 == 0:
                    state_path = cell / ".peval/state.json"
                    state_path.parent.mkdir(parents=True, exist_ok=True)
                    state_path.write_text(
                        json.dumps(
                            {"source_category": "even", "source_tags": ["even"]}
                        ),
                        encoding="utf-8",
                    )
            store, runtime, server, thread = self.running_server(root)
            runtime.workspace_views.save(
                name="Passed",
                filters={"results": ["passed"]},
                group_by="overall",
                notes="",
            )
            browser_view = {
                "name": "Failed local",
                "filters": {"results": ["failed"]},
                "group_by": "overall",
                "notes": "",
            }
            try:
                page_query = {
                    **leaderboard_summary_query(
                        views=["Passed"], browser_views=[browser_view]
                    ),
                    "page": 1,
                    "page_size": 100,
                    "sort": "session",
                    "direction": "asc",
                }
                page_query.pop("group_by")
                status, _headers, body = self.request(
                    server, "POST", "/api/catalog-queries", page_query
                )
                self.assertEqual(status, 200, body)
                page = json.loads(body)
                self.assertEqual(page["total"], 125)
                self.assertEqual(len(page["items"]), 100)

                summary_query = leaderboard_summary_query(
                    views=["Passed"], browser_views=[browser_view]
                )
                status, _headers, body = self.request(
                    server, "POST", "/api/catalog-summaries", summary_query
                )
                self.assertEqual(status, 200, body)
                payload = json.loads(body)
                self.assertEqual(payload["generation"], page["generation"])
                self.assertEqual(payload["summary"]["matched_count"], 125)
                self.assertEqual(payload["summary"]["groups"][0]["count"], 125)
                duration = next(
                    item
                    for item in payload["summary"]["groups"][0]["metrics"]
                    if item["key"] == "duration_ms"
                )
                self.assertEqual(duration["count"], 125)
                self.assertEqual(duration["mean"], 62)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/catalog-summaries",
                    leaderboard_summary_query(group_by="category"),
                )
                self.assertEqual(status, 200, body)
                groups = json.loads(body)["summary"]["groups"]
                self.assertEqual(
                    {group["key"]: group["count"] for group in groups},
                    {None: 62, "even": 63},
                )

                for forbidden in (
                    "page",
                    "page_size",
                    "sort",
                    "direction",
                    "source_keys",
                ):
                    status, _headers, _body = self.request(
                        server,
                        "POST",
                        "/api/catalog-summaries",
                        {**summary_query, forbidden: 1},
                    )
                    self.assertEqual(status, 422, forbidden)
                status, _headers, _body = self.request(
                    server,
                    "POST",
                    "/api/catalog-summaries",
                    {**summary_query, "group_by": "session"},
                )
                self.assertEqual(status, 400)
                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/catalog-summaries",
                    leaderboard_summary_query(views=["Missing"]),
                )
                self.assertEqual(status, 400)
                self.assertIn("does not exist", json.loads(body)["detail"])

                export_query = dict(summary_query)
                export_query.pop("group_by")
                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": summary_request(export_query, "overall", "mean"),
                    },
                )
                self.assertEqual(status, 200, body[:200])
                with zipfile.ZipFile(BytesIO(body)) as archive:
                    sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
                    strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
                self.assertIn("Complete Leaderboard query", strings)
                self.assertIn("<v>125</v>", sheet)
            finally:
                self.stop(store, server, thread)

    def test_oversized_grouped_summary_and_export_return_413(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_trial_cell_artifacts(
                root / "runs/default/psychevo/session/trial",
                session_id="session",
                trial_key="trial",
            )
            store, runtime, server, thread = self.running_server(root)
            error = CatalogSummaryCapacityError(
                "grouped summaries support at most 1000 groups"
            )
            try:
                with patch.object(
                    runtime.catalog,
                    "summarize_query",
                    side_effect=error,
                ):
                    status, _headers, body = self.request(
                        server,
                        "POST",
                        "/api/catalog-summaries",
                        leaderboard_summary_query(group_by="job"),
                    )
                    self.assertEqual(status, 413, body)
                    self.assertIn("at most 1000 groups", json.loads(body)["detail"])

                    query = leaderboard_summary_query()
                    query.pop("group_by")
                    status, _headers, body = self.request(
                        server,
                        "POST",
                        "/api/exports",
                        {
                            "kind": "summary_xlsx",
                            "summary": summary_request(query, "job", "mean"),
                        },
                    )
                    self.assertEqual(status, 413, body)
                    self.assertIn("at most 1000 groups", json.loads(body)["detail"])
            finally:
                self.stop(store, server, thread)

    def test_server_exports_leaderboard_and_saved_view_summary_workbooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(2):
                write_trial_cell_artifacts(
                    root / f"runs/default/psychevo/s{index}/s{index}_t001",
                    session_id=f"s{index}",
                    trial_key=f"s{index}_t001",
                    tool_error=index == 1,
                )
                trajectory_path = (
                    root
                    / f"runs/default/psychevo/s{index}/s{index}_t001/agent/trajectory.json"
                )
                trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
                trajectory["steps"][1]["extra"] = {"duration_ms": 200}
                trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
            store, runtime, server, thread = self.running_server(root)
            items = runtime.catalog.query(CatalogQuery()).items
            runtime.catalog.mutate(
                lambda: store.set_source_category_row(
                    runtime.catalog.row_for_key(items[0].source_key),
                    "Regression",
                )
            )
            runtime.workspace_views.save(
                name="All: sessions",
                filters={},
                group_by="agent",
                notes="=literal note",
            )
            runtime.workspace_views.save(
                name="Failed only",
                filters={"results": ["failed"]},
                group_by="model",
                notes="No matches",
            )
            try:
                status, headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": summary_request(
                            {
                                key: value
                                for key, value in leaderboard_summary_query().items()
                                if key != "group_by"
                            },
                            "category",
                            "max",
                        ),
                    },
                )
                self.assertEqual(status, 200)
                self.assertIn(
                    "peval-leaderboard-summary.xlsx", headers["content-disposition"]
                )
                with zipfile.ZipFile(BytesIO(body)) as archive:
                    names = set(archive.namelist())
                    strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
                self.assertEqual(
                    len(
                        {
                            name
                            for name in names
                            if name.startswith("xl/charts/") and name.endswith(".xml")
                        }
                    ),
                    5,
                )
                self.assertIn("Complete Leaderboard query", strings)
                self.assertIn("Category", strings)
                self.assertIn("Regression", strings)
                self.assertIn("<t>-</t>", strings)
                self.assertIn("Active Duration", strings)
                self.assertIn("Model call duration", strings)
                self.assertIn("Agent steps", strings)
                self.assertIn("Tool Calls", strings)
                self.assertIn("Tool Success Rate", strings)
                self.assertNotIn("Reward", strings)
                self.assertNotIn("Avg TTFT", strings)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": summary_request(
                            {
                                key: value
                                for key, value in leaderboard_summary_query().items()
                                if key != "group_by"
                            },
                            "agent",
                            "mean",
                        ),
                    },
                )
                self.assertEqual(status, 200)
                with zipfile.ZipFile(BytesIO(body)) as archive:
                    strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
                self.assertIn("Complete Leaderboard query", strings)
                self.assertNotIn("Avg TTFT", strings)
                self.assertNotIn("Decode TPS", strings)
                self.assertNotIn("Cache Hit", strings)

                status, headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": {
                            "scope": "saved_views",
                            "views": ["All: sessions", "Failed only"],
                        },
                    },
                )
                self.assertEqual(status, 200)
                self.assertIn("peval-saved-views.xlsx", headers["content-disposition"])
                with zipfile.ZipFile(BytesIO(body)) as archive:
                    names = set(archive.namelist())
                    workbook = archive.read("xl/workbook.xml").decode("utf-8")
                    strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
                self.assertIn('name="All_ sessions"', workbook)
                self.assertIn('name="Failed only"', workbook)
                self.assertIn("=literal note", strings)
                self.assertIn("Model call duration", strings)
                self.assertEqual(
                    len(
                        {
                            name
                            for name in names
                            if name.startswith("xl/charts/") and name.endswith(".xml")
                        }
                    ),
                    5,
                )

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": summary_request(
                            {
                                **{
                                    key: value
                                    for key, value in leaderboard_summary_query().items()
                                    if key != "group_by"
                                },
                                "views": ["Missing"],
                            },
                            "agent",
                            "mean",
                        ),
                    },
                )
                self.assertEqual(status, 400)
                self.assertIn("does not exist", json.loads(body)["detail"])

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": {"scope": "saved_views", "views": ["Missing"]},
                    },
                )
                self.assertEqual(status, 400)
                self.assertIn("does not exist", json.loads(body)["detail"])
            finally:
                self.stop(store, server, thread)

    def test_leaderboard_summary_export_rejects_an_invalid_catalog_generation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, runtime, server, thread = self.running_server(root)
            try:
                with runtime.catalog._connect() as connection:
                    runtime.catalog._set_meta(connection, "valid_generation", "0")
                    connection.commit()
                query = leaderboard_summary_query()
                query.pop("group_by")

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": summary_request(query, "overall", "mean"),
                    },
                )

                self.assertEqual(status, 400, body[:200])
                self.assertIn("no valid generation", json.loads(body)["detail"])
            finally:
                self.stop(store, server, thread)


if __name__ == "__main__":
    unittest.main()
