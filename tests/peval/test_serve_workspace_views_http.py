from __future__ import annotations

import json
import sqlite3
import tempfile
import time
import unittest
import zipfile
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from psycheval.workspace_views import WorkspaceViewLibrary
from tests.peval.catalog_http_support import (
    CatalogHttpTestCase,
    leaderboard_summary_query,
    summary_request,
)
from tests.peval.cli_inputs_support import write_trial_cell_artifacts


class ServeWorkspaceViewsHttpTests(CatalogHttpTestCase):
    def test_combined_view_limit_and_deduplication_apply_to_every_query_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cell = root / "runs/default/psychevo/s0/s0_t001"
            write_trial_cell_artifacts(cell, session_id="s0", trial_key="s0_t001")
            store, runtime, server, thread = self.running_server(root)
            try:
                filters = [{"search": f"condition-{index}"} for index in range(100)]
                runtime.workspace_views.save(
                    name="Existing",
                    filters=filters[0],
                    group_by="overall",
                    notes="retained",
                )
                retained = {p: p.read_bytes() for p in (root / "views").iterdir()}
                for extra, expected in (
                    (filters[0], 200),
                    ({"search": "condition-100"}, 400),
                ):
                    browser = [
                        {
                            "name": "Browser",
                            "filters": extra,
                            "group_by": "overall",
                            "notes": "",
                        }
                    ]
                    summary = leaderboard_summary_query(
                        views=["Existing"], browser_views=browser, inline_views=filters
                    )
                    query = {k: v for k, v in summary.items() if k != "group_by"}
                    for route, payload in (
                        (
                            "/api/catalog-queries",
                            {
                                **query,
                                "page": 1,
                                "page_size": 100,
                                "sort": "session",
                                "direction": "asc",
                            },
                        ),
                        ("/api/catalog-summaries", summary),
                        ("/api/exports", {"kind": "xlsx", "query": query}),
                        (
                            "/api/exports",
                            {
                                "kind": "summary_xlsx",
                                "summary": summary_request(query, "overall", "mean"),
                            },
                        ),
                    ):
                        with self.subTest(extra=extra, route=route):
                            status, _, body = self.request(
                                server, "POST", route, payload
                            )
                            self.assertEqual(status, expected, body[:200])
                            if expected == 400:
                                self.assertIn(
                                    "combined View conditions",
                                    json.loads(body)["detail"],
                                )
                for index in range(101):
                    runtime.workspace_views.save(
                        name=f"Unique-{index}",
                        filters={"search": f"unique-{index}"},
                        group_by="overall",
                        notes="",
                    )
                status, _, body = self.request(
                    server,
                    "GET",
                    "/api/catalog?"
                    + "&".join(f"view=Unique-{index}" for index in range(101)),
                )
                self.assertEqual(status, 400, body[:200])
                self.assertIn("combined View conditions", json.loads(body)["detail"])
                self.assertTrue(
                    all(p.read_bytes() == content for p, content in retained.items())
                )
            finally:
                self.stop(store, server, thread)

    def test_inline_view_snapshots_share_query_summary_and_export_without_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, result in enumerate(("passed", "failed")):
                cell = root / f"runs/default/psychevo/s{index}/s{index}_t001"
                write_trial_cell_artifacts(
                    cell, session_id=f"s{index}", trial_key=f"s{index}_t001"
                )
                path = cell / "agent/trajectory_meta.json"
                meta = json.loads(path.read_text(encoding="utf-8"))
                meta["status"] = result
                path.write_text(json.dumps(meta), encoding="utf-8")
            store, runtime, server, thread = self.running_server(root)
            connect = runtime.catalog._connect

            @contextmanager
            def limited_connect(**kwargs):
                with connect(**kwargs) as connection:
                    connection.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 128)
                    yield connection

            limited = patch.object(runtime.catalog, "_connect", limited_connect)
            limited.start()
            try:
                runtime.workspace_views.save(
                    name="Existing",
                    filters={"results": ["failed"]},
                    group_by="overall",
                    notes="unchanged",
                )
                retained = {p: p.read_bytes() for p in (root / "views").iterdir()}
                query = leaderboard_summary_query(
                    state="all",
                    search="s0",
                    inline_views=[{"results": ["passed"]}, {"results": ["failed"]}],
                    agents=["psychevo", *[f"absent-{i}" for i in range(500)]],
                )
                table_query = {k: v for k, v in query.items() if k != "group_by"}
                status, _, body = self.request(
                    server,
                    "POST",
                    "/api/catalog-queries",
                    {
                        **table_query,
                        "page": 1,
                        "page_size": 100,
                        "sort": "session",
                        "direction": "asc",
                    },
                )
                self.assertEqual(status, 200, body)
                self.assertEqual(json.loads(body)["total"], 1)
                status, _, body = self.request(
                    server, "POST", "/api/catalog-summaries", query
                )
                self.assertEqual(status, 200, body)
                self.assertEqual(json.loads(body)["summary"]["matched_count"], 1)
                for changes, expected in (
                    ({"search": "", "inline_views": [{"results": ["passed"]}]}, 1),
                    (
                        {
                            "search": "",
                            "views": ["Existing"],
                            "inline_views": [{"results": ["passed"]}],
                        },
                        2,
                    ),
                    ({"search": "s0", "inline_views": [{"results": ["failed"]}]}, 0),
                ):
                    status, _, body = self.request(
                        server, "POST", "/api/catalog-summaries", {**query, **changes}
                    )
                    self.assertEqual(status, 200, body)
                    self.assertEqual(
                        json.loads(body)["summary"]["matched_count"], expected
                    )
                for payload in (
                    {"kind": "xlsx", "query": table_query},
                    {
                        "kind": "summary_xlsx",
                        "summary": summary_request(table_query, "overall", "mean"),
                    },
                ):
                    status, _, body = self.request(
                        server, "POST", "/api/exports", payload
                    )
                    self.assertEqual(status, 200, body[:200])
                    with zipfile.ZipFile(BytesIO(body)) as archive:
                        sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
                        if payload["kind"] == "xlsx":
                            self.assertEqual(sheet.count("<row "), 2)
                            self.assertIn("<t>s0</t>", sheet)
                            self.assertNotIn("<t>s1</t>", sheet)
                        else:
                            strings = archive.read("xl/sharedStrings.xml").decode(
                                "utf-8"
                            )
                            self.assertIn("Match count", strings)
                            self.assertIn("<v>1</v>", sheet)
                self.assertEqual(
                    {p: p.read_bytes() for p in (root / "views").iterdir()}, retained
                )
                for invalid in (
                    [{"notes": "not a query"}],
                    [{"models": "wrong"}],
                    [{"state": True}],
                    [{}] * 101,
                ):
                    status, _, body = self.request(
                        server,
                        "POST",
                        "/api/catalog-summaries",
                        {**query, "inline_views": invalid},
                    )
                    self.assertEqual(status, 400, body)
            finally:
                limited.stop()
                self.stop(store, server, thread)

    def test_saved_views_round_trip_conflict_overwrite_and_full_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(2):
                write_trial_cell_artifacts(
                    root / f"runs/default/psychevo/s{index}/s{index}_t001",
                    session_id=f"s{index}",
                    trial_key=f"s{index}_t001",
                )
            store, runtime, server, thread = self.running_server(root)
            payload = {
                "name": "Daily focus",
                "filters": {
                    "state": "active",
                    "search": "",
                    "tags": [],
                    "agents": [],
                    "models": [],
                    "results": [],
                },
                "group_by": "agent",
                "notes": "# Daily\n\nKeep this note exactly.",
                "overwrite": False,
            }
            try:
                status, _headers, body = self.request(server, "GET", "/api/views")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body), [])

                status, _headers, body = self.request(
                    server,
                    "PUT",
                    "/api/views/Daily%20focus",
                    {key: value for key, value in payload.items() if key != "name"},
                )
                self.assertEqual(status, 201)
                saved = json.loads(body)
                self.assertEqual(saved["name"], "Daily focus")
                self.assertEqual(saved["notes"], payload["notes"])
                self.assertEqual(saved["filters"], {})
                stored = (
                    WorkspaceViewLibrary(root)._path_for_name("Daily focus")
                ).read_text(encoding="utf-8")
                self.assertIn("group_by: agent", stored)
                self.assertNotIn("filters:", stored)
                self.assertTrue(stored.endswith(payload["notes"]))

                status, _headers, body = self.request(
                    server, "GET", "/api/view-summaries"
                )
                self.assertEqual(status, 200)
                summary = json.loads(body)
                self.assertEqual(summary["views"][0]["name"], "Daily focus")
                self.assertEqual(summary["views"][0]["matched_count"], 2)
                self.assertEqual(summary["views"][0]["group_by"], "agent")

                status, _headers, body = self.request(
                    server,
                    "PUT",
                    "/api/views/Daily%20focus",
                    {key: value for key, value in payload.items() if key != "name"},
                )
                self.assertEqual(status, 409)
                self.assertIn("already exists", json.loads(body)["detail"])
                self.assertEqual(
                    (
                        WorkspaceViewLibrary(root)._path_for_name("Daily focus")
                    ).read_text(encoding="utf-8"),
                    stored,
                )

                payload["notes"] = "Replacement notes"
                payload["overwrite"] = True
                status, _headers, body = self.request(
                    server,
                    "PUT",
                    "/api/views/Daily%20focus",
                    {key: value for key, value in payload.items() if key != "name"},
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["notes"], "Replacement notes")
                self.assertEqual(
                    (WorkspaceViewLibrary(root)._path_for_name("Daily focus"))
                    .read_text(encoding="utf-8")
                    .split("---\n", 2)[-1],
                    "Replacement notes",
                )

                other_payload = {
                    **payload,
                    "name": "Other view",
                    "notes": "Other notes",
                    "overwrite": False,
                }
                status, _headers, _body = self.request(
                    server,
                    "PUT",
                    "/api/views/Other%20view",
                    {
                        key: value
                        for key, value in other_payload.items()
                        if key != "name"
                    },
                )
                self.assertEqual(status, 201)

                status, _headers, body = self.request(
                    server,
                    "PATCH",
                    "/api/views/Daily%20focus",
                    {
                        "field": "notes",
                        "value": "Edited **Markdown**",
                    },
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["notes"], "Edited **Markdown**")

                configuration = (
                    "filters:\n  results:\n    - passed\ngroup_by: overall\n"
                )
                status, _headers, body = self.request(
                    server,
                    "PATCH",
                    "/api/views/Daily%20focus",
                    {
                        "field": "configuration",
                        "value": configuration,
                    },
                )
                self.assertEqual(status, 200)
                updated = json.loads(body)
                self.assertEqual(updated["filters"], {"results": ["passed"]})
                self.assertEqual(updated["group_by"], "overall")

                status, _headers, body = self.request(
                    server,
                    "PATCH",
                    "/api/views/Daily%20focus",
                    {
                        "field": "configuration",
                        "value": "schema_version: 1\ngroup_by: agent\n",
                    },
                )
                self.assertEqual(status, 400)
                self.assertIn("optional filters", json.loads(body)["detail"])

                status, _headers, body = self.request(
                    server,
                    "PATCH",
                    "/api/views/Daily%20focus",
                    {"field": "name", "value": "Other view"},
                )
                self.assertEqual(status, 409)
                self.assertIn("already exists", json.loads(body)["detail"])

                status, _headers, body = self.request(
                    server,
                    "PATCH",
                    "/api/views/Daily%20focus",
                    {"field": "name", "value": "Renamed view"},
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["name"], "Renamed view")
                self.assertFalse(
                    (WorkspaceViewLibrary(root)._path_for_name("Daily focus")).exists()
                )

                status, _headers, _body = self.request(
                    server,
                    "DELETE",
                    "/api/views/Missing%20view",
                    None,
                )
                self.assertEqual(status, 404)
                self.assertTrue(
                    (
                        WorkspaceViewLibrary(root)._path_for_name("Renamed view")
                    ).is_file()
                )
                self.assertTrue(
                    (WorkspaceViewLibrary(root)._path_for_name("Other view")).is_file()
                )

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/view-deletion-operations",
                    {"names": ["Renamed view", "Missing view"]},
                )
                self.assertEqual(status, 202)
                operation_id = json.loads(body)["id"]
                deadline = time.monotonic() + 5
                while True:
                    status, _headers, body = self.request(
                        server, "GET", f"/api/operations/{operation_id}"
                    )
                    self.assertEqual(status, 200)
                    operation = json.loads(body)
                    if operation["state"] not in {"queued", "running"}:
                        break
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.01)
                self.assertEqual(operation["state"], "failed")
                self.assertTrue(
                    (
                        WorkspaceViewLibrary(root)._path_for_name("Renamed view")
                    ).is_file()
                )
                self.assertTrue(
                    (WorkspaceViewLibrary(root)._path_for_name("Other view")).is_file()
                )

                status, _headers, body = self.request(
                    server,
                    "DELETE",
                    "/api/views/Renamed%20view",
                    None,
                )
                self.assertEqual(status, 204)
                status, _headers, body = self.request(
                    server,
                    "DELETE",
                    "/api/views/Other%20view",
                    None,
                )
                self.assertEqual(status, 204)
                status, _headers, body = self.request(server, "GET", "/api/views")
                self.assertEqual(json.loads(body), [])
            finally:
                self.stop(store, server, thread)

    def test_browser_view_catalog_query_and_summary_share_server_validation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, result in enumerate(("passed", "failed", "passed")):
                cell = root / f"runs/default/psychevo/s{index}/s{index}_t001"
                write_trial_cell_artifacts(
                    cell,
                    session_id=f"s{index}",
                    trial_key=f"s{index}_t001",
                )
                meta_path = cell / "agent" / "trajectory_meta.json"
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["status"] = result
                meta["finished_at_ms"] = 1_000 + index
                meta_path.write_text(json.dumps(meta), encoding="utf-8")
            store, _runtime, server, thread = self.running_server(root)
            browser_view = {
                "name": "Failed locally",
                "filters": {"results": ["failed"]},
                "group_by": "overall",
                "notes": "browser note",
            }
            try:
                status, _headers, _body = self.request(
                    server,
                    "PUT",
                    "/api/views/Passed",
                    {
                        "filters": {"results": ["passed"]},
                        "group_by": "agent",
                        "notes": "",
                        "overwrite": False,
                    },
                )
                self.assertEqual(status, 201)

                query = {
                    "state": "all",
                    "page": 1,
                    "page_size": 100,
                    "search": "",
                    "sort": "session",
                    "direction": "asc",
                    "categories": [],
                    "tags": [],
                    "agents": [],
                    "models": [],
                    "tasks": [],
                    "jobs": [],
                    "providers": [],
                    "datasets": [],
                    "results": [],
                    "views": ["Passed"],
                    "browser_views": [browser_view],
                }
                status, _headers, body = self.request(
                    server, "POST", "/api/catalog-queries", query
                )
                self.assertEqual(status, 200, body)
                self.assertEqual(
                    [item["session_id"] for item in json.loads(body)["items"]],
                    ["s0", "s1", "s2"],
                )

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/catalog-queries",
                    {**query, "results": ["failed"]},
                )
                self.assertEqual(status, 200, body)
                self.assertEqual(
                    [item["session_id"] for item in json.loads(body)["items"]],
                    ["s1"],
                )

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/view-summaries",
                    {"browser_views": [browser_view]},
                )
                self.assertEqual(status, 200, body)
                summary = json.loads(body)
                self.assertEqual(summary["views"][0]["name"], "Failed locally")
                self.assertEqual(summary["views"][0]["notes"], "browser note")
                self.assertEqual(summary["views"][0]["matched_count"], 1)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/view-summaries",
                    {"browser_views": [{**browser_view, "name": "Passed"}]},
                )
                self.assertEqual(status, 409, body)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/view-summaries",
                    {"browser_views": [{**browser_view, "unexpected": True}]},
                )
                self.assertEqual(status, 400, body)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/view-summaries",
                    {"browser_views": [browser_view, browser_view]},
                )
                self.assertEqual(status, 400, body)
                self.assertIn("duplicate", json.loads(body)["detail"])

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/view-summaries",
                    {
                        "browser_views": [
                            {**browser_view, "name": f"Local {index}"}
                            for index in range(101)
                        ]
                    },
                )
                self.assertEqual(status, 400, body)
                self.assertIn("at most 100", json.loads(body)["detail"])
            finally:
                self.stop(store, server, thread)

    def test_browser_views_flow_through_table_and_summary_exports(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, result in enumerate(("passed", "failed")):
                cell = root / f"runs/default/psychevo/s{index}/s{index}_t001"
                write_trial_cell_artifacts(
                    cell,
                    session_id=f"s{index}",
                    trial_key=f"s{index}_t001",
                )
                meta_path = cell / "agent" / "trajectory_meta.json"
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["status"] = result
                meta_path.write_text(json.dumps(meta), encoding="utf-8")
            store, _runtime, server, thread = self.running_server(root)
            local = {
                "name": "Failed locally",
                "filters": {"results": ["failed"]},
                "group_by": "overall",
                "notes": "local export note",
            }
            query = {
                "state": "all",
                "search": "",
                "sort": "session",
                "direction": "asc",
                "categories": [],
                "tags": [],
                "agents": [],
                "models": [],
                "tasks": [],
                "jobs": [],
                "providers": [],
                "datasets": [],
                "results": [],
                "views": ["Passed"],
                "browser_views": [local],
            }
            try:
                status, _headers, _body = self.request(
                    server,
                    "PUT",
                    "/api/views/Passed",
                    {
                        "filters": {"results": ["passed"]},
                        "group_by": "agent",
                        "notes": "server export note",
                        "overwrite": False,
                    },
                )
                self.assertEqual(status, 201)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {"kind": "xlsx", "query": query},
                )
                self.assertEqual(status, 200, body[:200])
                with zipfile.ZipFile(BytesIO(body)) as archive:
                    strings = "\n".join(
                        archive.read(name).decode("utf-8", errors="ignore")
                        for name in archive.namelist()
                        if name.endswith(".xml")
                    )
                self.assertIn("s0", strings)
                self.assertIn("s1", strings)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "xlsx",
                        "query": {
                            **query,
                            "views": [],
                            "browser_views": [{**local, "name": "Passed"}],
                        },
                    },
                )
                self.assertEqual(status, 409, body)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": {
                            "scope": "saved_views",
                            "views": ["Passed"],
                            "browser_views": [local],
                        },
                    },
                )
                self.assertEqual(status, 200, body[:200])
                with zipfile.ZipFile(BytesIO(body)) as archive:
                    workbook = archive.read("xl/workbook.xml").decode("utf-8")
                    strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
                self.assertIn('name="Passed"', workbook)
                self.assertIn('name="Failed locally"', workbook)
                self.assertIn("local export note", strings)
            finally:
                self.stop(store, server, thread)

    def test_catalog_and_export_apply_repeated_saved_views_as_or(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, result in enumerate(("passed", "failed", "passed")):
                cell = root / f"runs/default/psychevo/s{index}/s{index}_t001"
                write_trial_cell_artifacts(
                    cell,
                    session_id=f"s{index}",
                    trial_key=f"s{index}_t001",
                )
                meta_path = cell / "agent" / "trajectory_meta.json"
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["status"] = result
                meta["finished_at_ms"] = 1_000 + index
                meta_path.write_text(json.dumps(meta), encoding="utf-8")
            store, _runtime, server, thread = self.running_server(root)
            try:
                for name, result in (("Passed", "passed"), ("Failed", "failed")):
                    status, _headers, _body = self.request(
                        server,
                        "PUT",
                        f"/api/views/{name}",
                        {
                            "filters": {"results": [result]},
                            "group_by": "agent",
                            "notes": "",
                            "overwrite": False,
                        },
                    )
                    self.assertEqual(status, 201)

                status, _headers, body = self.request(
                    server,
                    "GET",
                    "/api/catalog?state=all&view=Passed&view=Failed&page=1&page_size=2&sort=session&direction=asc",
                )
                self.assertEqual(status, 200)
                first_page = json.loads(body)
                self.assertEqual(first_page["total"], 3)
                self.assertEqual(
                    [item["session_id"] for item in first_page["items"]],
                    ["s0", "s1"],
                )
                self.assertEqual(
                    {
                        item["value"]: item["count"]
                        for item in first_page["facets"]["results"]
                    },
                    {"failed": 1, "passed": 2},
                )

                status, _headers, body = self.request(
                    server,
                    "GET",
                    "/api/catalog?state=all&view=Passed&view=Failed&search=s1",
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["total"], 1)

                status, headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "xlsx",
                        "query": {
                            "state": "all",
                            "sort": "session",
                            "direction": "asc",
                            "views": ["Passed", "Failed"],
                        },
                    },
                )
                self.assertEqual(status, 200)
                self.assertIn("spreadsheetml", headers["content-type"])
                with zipfile.ZipFile(BytesIO(body)) as archive:
                    sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
                self.assertEqual(sheet.count("<row "), 4)

                status, _headers, body = self.request(
                    server, "GET", "/api/catalog?view=Missing"
                )
                self.assertEqual(status, 400)
                self.assertIn("does not exist", json.loads(body)["detail"])
            finally:
                self.stop(store, server, thread)


if __name__ == "__main__":
    unittest.main()
