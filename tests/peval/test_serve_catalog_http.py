from __future__ import annotations

import http.client
import json
import tempfile
import threading
import time
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from psycheval.config import ToolConfig
from psycheval.serve import (
    LocalHTTPServer,
    ServeAccess,
    ServeRuntime,
    make_handler,
)
from psycheval.serve.handler import catalog_query
from psycheval.state import CatalogQuery, open_workspace_state
from tests.peval.cli_inputs_support import write_trial_cell_artifacts


class ServeCatalogHttpTests(unittest.TestCase):
    def test_catalog_query_accepts_repeated_harbor_semantic_filters(self) -> None:
        query = catalog_query(
            "task=pbench-v1.0%2Fweb-search-01"
            "&task=pbench-v1.0%2Fweb-fetch-01"
            "&task=pbench-v1.0%2Fweb-search-01"
            "&job=opencode-real&provider=xiaomi-token-plan-cn"
        )

        self.assertEqual(
            query.tasks,
            (
                "pbench-v1.0/web-search-01",
                "pbench-v1.0/web-fetch-01",
            ),
        )
        self.assertEqual(query.jobs, ("opencode-real",))
        self.assertEqual(query.providers, ("xiaomi-token-plan-cn",))

    def running_server(self, root: Path, *, access: ServeAccess | None = None):
        (root / "peval.toml").write_text(
            'analysis_eval_slug = "default"\n', encoding="utf-8"
        )
        store = open_workspace_state(str(root))
        runtime = ServeRuntime(
            store,
            ToolConfig(workspace_root=str(root), analysis_eval_slug="default"),
        )
        server = LocalHTTPServer(
            ("127.0.0.1", 0),
            make_handler(runtime, access=access),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return store, runtime, server, thread

    def request(
        self,
        server: LocalHTTPServer,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {}
        if body is not None:
            headers = {
                "Content-Type": "application/json",
                "Origin": f"http://127.0.0.1:{server.server_port}",
            }
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_port, timeout=5
        )
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        content = response.read()
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        connection.close()
        return response.status, response_headers, content

    def stop(self, store, server, thread) -> None:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        store.close()

    def test_shell_catalog_detail_and_resolve_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cell = root / "runs/default/psychevo/private-session/private-trial"
            write_trial_cell_artifacts(
                cell, session_id="private-session", trial_key="private-trial"
            )
            store, runtime, server, thread = self.running_server(root)
            try:
                status, _headers, shell = self.request(server, "GET", "/")
                self.assertEqual(status, 200)
                self.assertNotIn(b"private-session", shell)
                self.assertNotIn(b"private-trial", shell)

                status, _headers, body = self.request(server, "GET", "/api/catalog")
                self.assertEqual(status, 200)
                page = json.loads(body)
                self.assertEqual(page["page_size"], 100)
                self.assertEqual(page["total"], 1)
                source_key = page["items"][0]["source_key"]
                report_path = root / "published.md"
                report_path.write_text("# Published\n", encoding="utf-8")
                runtime.workspace_reports.import_file(report_path, [source_key])
                status, _headers, body = self.request(server, "GET", "/api/catalog")
                self.assertEqual(status, 200)
                self.assertEqual(
                    json.loads(body)["column_presence"]["workspace_reports"], 1
                )

                status, _headers, body = self.request(
                    server, "GET", f"/api/report?source_key={source_key}"
                )
                detail = json.loads(body)
                self.assertEqual(status, 200)
                self.assertEqual(detail["source_key"], source_key)
                self.assertEqual(detail["generation"], page["generation"])
                self.assertEqual(
                    detail["report"]["trajectory"][0]["session_id"],
                    "private-session",
                )

                status, _headers, body = self.request(
                    server,
                    "POST",
                    f"/api/sources/{source_key}/alias",
                    {"alias": "compact"},
                )
                mutation = json.loads(body)
                self.assertEqual(status, 200)
                self.assertEqual(mutation["change"], "alias")
                self.assertEqual(mutation["source_keys"], [source_key])
                self.assertNotIn("sources", mutation)
                self.assertNotIn("report", mutation)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    f"/api/sources/{source_key}/category",
                    {"category": "  Regression  "},
                )
                mutation = json.loads(body)
                self.assertEqual(status, 200)
                self.assertEqual(mutation["change"], "category")
                self.assertEqual(mutation["source_keys"], [source_key])
                self.assertNotIn("sources", mutation)
                self.assertNotIn("report", mutation)
                category_page = runtime.catalog.query(
                    CatalogQuery(categories=("Regression",))
                )
                self.assertEqual(category_page.total, 1)
                self.assertEqual(
                    category_page.items[0].payload["source_category"],
                    "Regression",
                )

                status, _headers, body = self.request(
                    server,
                    "POST",
                    f"/api/sources/{source_key}/category",
                    {"category": "  "},
                )
                self.assertEqual(status, 200, body)
                cleared_page = runtime.catalog.query(CatalogQuery(state="all"))
                self.assertIsNone(cleared_page.items[0].payload["source_category"])
                self.assertNotIn(
                    "Regression",
                    {item["value"] for item in cleared_page.facets["categories"]},
                )

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/catalog/resolve",
                    {"source_keys": ["missing", source_key]},
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["source_keys"], [source_key])

                status, _headers, body = self.request(server, "GET", "/api/report")
                self.assertEqual(status, 400)
                self.assertIn("source_key is required", json.loads(body)["error"])
            finally:
                self.stop(store, server, thread)

    def test_unclassified_value_error_is_an_internal_guest_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, runtime, server, thread = self.running_server(
                root,
                access=ServeAccess("password"),
            )
            try:
                with patch.object(
                    runtime,
                    "resolve_keys",
                    side_effect=ValueError("internal resolver invariant"),
                ):
                    status, _headers, body = self.request(
                        server,
                        "POST",
                        "/api/catalog/resolve",
                        {"source_keys": []},
                    )
                self.assertEqual(status, 500)
                self.assertEqual(json.loads(body)["error"], "internal server error")
            finally:
                self.stop(store, server, thread)

    def test_catalog_http_facets_ignore_search_and_column_filters_within_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            definitions = [
                ("alpha", "shared", "passed", "needle active", True),
                ("beta", "Safety, Eval", "failed", "other active", True),
                ("archived", "archive-category", "passed", "other archived", False),
            ]
            for index, (tag, category, result, message, active) in enumerate(
                definitions
            ):
                cell = root / f"runs/default/psychevo/s{index}/s{index}_t001"
                write_trial_cell_artifacts(
                    cell,
                    session_id=f"s{index}",
                    trial_key=f"s{index}_t001",
                )
                trajectory_path = cell / "agent" / "trajectory.json"
                trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
                trajectory["steps"][0]["message"] = message
                trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
                meta_path = cell / "agent" / "trajectory_meta.json"
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["status"] = result
                meta_path.write_text(json.dumps(meta), encoding="utf-8")
                state_path = cell / ".peval" / "state.json"
                state_path.parent.mkdir(parents=True, exist_ok=True)
                state_path.write_text(
                    json.dumps(
                        {
                            "active": active,
                            "source_category": category,
                            "source_tags": [tag],
                        }
                    ),
                    encoding="utf-8",
                )

            store, _runtime, server, thread = self.running_server(root)
            try:
                status, _headers, body = self.request(
                    server,
                    "GET",
                    "/api/catalog?search=needle&category=shared&tag=alpha&result=passed",
                )
                self.assertEqual(status, 200)
                active = json.loads(body)
                self.assertEqual(active["total"], 1)
                self.assertEqual(
                    {
                        item["value"]: item["count"]
                        for item in active["facets"]["categories"]
                    },
                    {"Safety, Eval": 1, "shared": 1},
                )
                self.assertEqual(
                    {item["value"]: item["count"] for item in active["facets"]["tags"]},
                    {"alpha": 1, "beta": 1},
                )
                self.assertEqual(
                    {
                        item["value"]: item["count"]
                        for item in active["facets"]["results"]
                    },
                    {"failed": 1, "passed": 1},
                )

                status, _headers, body = self.request(
                    server,
                    "GET",
                    "/api/catalog?state=archived&category=archive-category&tag=archived",
                )
                self.assertEqual(status, 200)
                archived = json.loads(body)
                self.assertEqual(archived["total"], 1)
                self.assertEqual(
                    [item["value"] for item in archived["facets"]["tags"]],
                    ["archived"],
                )
                self.assertEqual(
                    [item["value"] for item in archived["facets"]["categories"]],
                    ["archive-category"],
                )

                status, _headers, body = self.request(
                    server,
                    "GET",
                    "/api/catalog?category=Safety%2C%20Eval",
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["total"], 1)

                status, _headers, body = self.request(
                    server,
                    "GET",
                    "/api/catalog?state=all&search=needle"
                    "&category=shared&category=Safety%2C%20Eval&tag=alpha",
                )
                self.assertEqual(status, 200)
                all_states = json.loads(body)
                self.assertEqual(all_states["total"], 1)
                self.assertEqual(
                    {item["value"] for item in all_states["facets"]["tags"]},
                    {"alpha", "beta", "archived"},
                )
                self.assertEqual(
                    {item["value"] for item in all_states["facets"]["categories"]},
                    {"shared", "Safety, Eval", "archive-category"},
                )

                status, _headers, body = self.request(
                    server,
                    "GET",
                    "/api/catalog?category=shared&categories=Safety%2C%20Eval",
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["total"], 2)
            finally:
                self.stop(store, server, thread)

    def test_checking_serves_old_page_and_rejects_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_trial_cell_artifacts(
                root / "runs/default/psychevo/s1/s1_t001",
                session_id="s1",
                trial_key="s1_t001",
            )
            store, runtime, server, thread = self.running_server(root)
            source_key = runtime.catalog.query(CatalogQuery()).items[0].source_key
            try:
                with runtime.catalog._state_lock:
                    runtime.catalog._checking = True
                status, _headers, body = self.request(server, "GET", "/api/catalog")
                page = json.loads(body)
                self.assertEqual(status, 200)
                self.assertTrue(page["checking"])
                self.assertEqual(page["total"], 1)
                status, _headers, body = self.request(
                    server,
                    "POST",
                    f"/api/sources/{source_key}/alias",
                    {"alias": "blocked"},
                )
                self.assertEqual(status, 409)
                self.assertIn("checking runs", json.loads(body)["error"])
                with runtime.catalog._state_lock:
                    runtime.catalog._checking = False
                self.assertTrue(runtime.catalog._writer_lock.acquire(blocking=False))
                try:
                    status, _headers, body = self.request(
                        server,
                        "POST",
                        "/api/views",
                        {
                            "name": "Blocked during snapshot",
                            "filters": {},
                            "group_by": "agent",
                            "notes": "",
                            "overwrite": False,
                        },
                    )
                finally:
                    runtime.catalog._writer_lock.release()
                self.assertEqual(status, 409)
                self.assertIn("writer operation", json.loads(body)["error"])
                self.assertFalse((root / "views/Blocked during snapshot.md").exists())
            finally:
                with runtime.catalog._state_lock:
                    runtime.catalog._checking = False
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
                self.assertEqual(json.loads(body), {"views": []})

                status, _headers, body = self.request(
                    server, "POST", "/api/views", payload
                )
                self.assertEqual(status, 200)
                saved = json.loads(body)
                self.assertEqual(saved["view"]["name"], "Daily focus")
                self.assertEqual(saved["view"]["notes"], payload["notes"])
                self.assertEqual(saved["view"]["filters"], {})
                stored = (root / "views" / "Daily focus.md").read_text(encoding="utf-8")
                self.assertIn("group_by: agent", stored)
                self.assertNotIn("filters:", stored)
                self.assertTrue(stored.endswith(payload["notes"]))

                status, _headers, body = self.request(
                    server, "GET", "/api/views/summary"
                )
                self.assertEqual(status, 200)
                summary = json.loads(body)
                self.assertEqual(summary["views"][0]["name"], "Daily focus")
                self.assertEqual(summary["views"][0]["matched_count"], 2)
                self.assertEqual(summary["views"][0]["group_by"], "agent")

                status, _headers, body = self.request(
                    server, "POST", "/api/views", payload
                )
                self.assertEqual(status, 409)
                self.assertIn("already exists", json.loads(body)["error"])

                payload["notes"] = "Replacement notes"
                payload["overwrite"] = True
                status, _headers, body = self.request(
                    server, "POST", "/api/views", payload
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["view"]["notes"], "Replacement notes")
                self.assertEqual(
                    (root / "views" / "Daily focus.md")
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
                    server, "POST", "/api/views", other_payload
                )
                self.assertEqual(status, 200)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/views/update",
                    {
                        "name": "Daily focus",
                        "field": "notes",
                        "value": "Edited **Markdown**",
                    },
                )
                self.assertEqual(status, 200)
                self.assertEqual(
                    json.loads(body)["view"]["notes"], "Edited **Markdown**"
                )

                configuration = (
                    "filters:\n  results:\n    - passed\ngroup_by: overall\n"
                )
                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/views/update",
                    {
                        "name": "Daily focus",
                        "field": "configuration",
                        "value": configuration,
                    },
                )
                self.assertEqual(status, 200)
                updated = json.loads(body)["view"]
                self.assertEqual(updated["filters"], {"results": ["passed"]})
                self.assertEqual(updated["group_by"], "overall")

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/views/update",
                    {
                        "name": "Daily focus",
                        "field": "configuration",
                        "value": "schema_version: 1\ngroup_by: agent\n",
                    },
                )
                self.assertEqual(status, 400)
                self.assertIn("optional filters", json.loads(body)["error"])

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/views/update",
                    {"name": "Daily focus", "field": "name", "value": "Other view"},
                )
                self.assertEqual(status, 409)
                self.assertIn("already exists", json.loads(body)["error"])

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/views/update",
                    {"name": "Daily focus", "field": "name", "value": "Renamed view"},
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["view"]["name"], "Renamed view")
                self.assertFalse((root / "views" / "Daily focus.md").exists())

                status, _headers, _body = self.request(
                    server,
                    "POST",
                    "/api/views/delete",
                    {"names": ["Renamed view", "Missing view"]},
                )
                self.assertEqual(status, 404)
                self.assertTrue((root / "views" / "Renamed view.md").is_file())
                self.assertTrue((root / "views" / "Other view.md").is_file())

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/views/delete",
                    {"names": ["Renamed view", "Other view"]},
                )
                self.assertEqual(status, 200)
                self.assertEqual(
                    json.loads(body),
                    {"deleted": ["Renamed view", "Other view"], "views": []},
                )
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
                    "POST",
                    "/api/views",
                    {
                        "name": "Passed",
                        "filters": {"results": ["passed"]},
                        "group_by": "agent",
                        "notes": "",
                        "overwrite": False,
                    },
                )
                self.assertEqual(status, 200)

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
                    "results": [],
                    "views": ["Passed"],
                    "browser_views": [browser_view],
                }
                status, _headers, body = self.request(
                    server, "POST", "/api/catalog/query", query
                )
                self.assertEqual(status, 200, body)
                self.assertEqual(
                    [item["session_id"] for item in json.loads(body)["items"]],
                    ["s0", "s1", "s2"],
                )

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/catalog/query",
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
                    "/api/views/summary",
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
                    "/api/views/summary",
                    {"browser_views": [{**browser_view, "name": "Passed"}]},
                )
                self.assertEqual(status, 409, body)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/views/summary",
                    {"browser_views": [{**browser_view, "unexpected": True}]},
                )
                self.assertEqual(status, 400, body)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/views/summary",
                    {"browser_views": [browser_view, browser_view]},
                )
                self.assertEqual(status, 400, body)
                self.assertIn("duplicate", json.loads(body)["error"])

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/views/summary",
                    {
                        "browser_views": [
                            {**browser_view, "name": f"Local {index}"}
                            for index in range(101)
                        ]
                    },
                )
                self.assertEqual(status, 400, body)
                self.assertIn("at most 100", json.loads(body)["error"])
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
                "results": [],
                "views": ["Passed"],
                "browser_views": [local],
            }
            try:
                status, _headers, _body = self.request(
                    server,
                    "POST",
                    "/api/views",
                    {
                        "name": "Passed",
                        "filters": {"results": ["passed"]},
                        "group_by": "agent",
                        "notes": "server export note",
                        "overwrite": False,
                    },
                )
                self.assertEqual(status, 200)

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
                        "POST",
                        "/api/views",
                        {
                            "name": name,
                            "filters": {"results": [result]},
                            "group_by": "agent",
                            "notes": "",
                            "overwrite": False,
                        },
                    )
                    self.assertEqual(status, 200)

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
                self.assertIn("does not exist", json.loads(body)["error"])
            finally:
                self.stop(store, server, thread)

    def test_background_operation_progress_and_partial_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(2):
                write_trial_cell_artifacts(
                    root / f"runs/default/psychevo/s{index}/s{index}_t001",
                    session_id=f"s{index}",
                    trial_key=f"s{index}_t001",
                )
            store, runtime, server, thread = self.running_server(root)
            keys = [
                item.source_key for item in runtime.catalog.query(CatalogQuery()).items
            ]
            original = store.set_source_active_row

            def partial(row, active):
                if row["source_key"] == keys[1]:
                    raise ValueError("intentional item failure")
                return original(row, active)

            store.set_source_active_row = partial
            try:
                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/sources/state",
                    {"source_keys": keys, "active": False},
                )
                self.assertEqual(status, 202)
                operation_id = json.loads(body)["operation_id"]
                operation = None
                for _attempt in range(100):
                    status, _headers, body = self.request(
                        server, "GET", f"/api/operations/{operation_id}"
                    )
                    operation = json.loads(body)
                    if operation["state"] not in {"queued", "running"}:
                        break
                    time.sleep(0.01)
                self.assertEqual(status, 200)
                self.assertEqual(operation["state"], "completed")
                self.assertEqual(operation["completed"], 2)
                self.assertEqual(len(operation["successes"]), 1)
                self.assertEqual(len(operation["failures"]), 1)
                self.assertIn(
                    "intentional item failure", operation["failures"][0]["error"]
                )
                self.assertEqual(
                    runtime.catalog.query(CatalogQuery(state="archived")).total, 1
                )
            finally:
                self.stop(store, server, thread)

    def test_permanent_source_delete_and_linked_harbor_rejection_are_atomic(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_trial_cell_artifacts(
                root / "runs/default/psychevo/session/trial",
                session_id="session",
                trial_key="trial",
            )
            store, runtime, server, thread = self.running_server(root)
            try:
                source_key = runtime.catalog.query(CatalogQuery()).items[0].source_key
                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/sources/delete",
                    {"source_keys": [source_key]},
                )
                self.assertEqual(status, 202, body)
                operation_id = json.loads(body)["operation_id"]
                operation = None
                for _attempt in range(100):
                    status, _headers, body = self.request(
                        server, "GET", f"/api/operations/{operation_id}"
                    )
                    operation = json.loads(body)
                    if operation["state"] not in {"queued", "running"}:
                        break
                    time.sleep(0.01)
                self.assertEqual(operation["state"], "completed")
                self.assertEqual(len(operation["successes"]), 1)
                self.assertEqual(runtime.catalog.query(CatalogQuery()).total, 0)

                rows = {
                    "normal": {"source_key": "normal", "kind": "path"},
                    "linked": {
                        "source_key": "linked",
                        "kind": "harbor-trial",
                    },
                }
                original_row_for_key = runtime.catalog.row_for_key
                runtime.catalog.row_for_key = lambda key: rows[key]
                deleted = []
                original_delete = store.delete_source_row
                store.delete_source_row = lambda row: deleted.append(row["source_key"])
                try:
                    status, _headers, body = self.request(
                        server,
                        "POST",
                        "/api/sources/delete",
                        {"source_keys": ["normal", "linked"]},
                    )
                finally:
                    runtime.catalog.row_for_key = original_row_for_key
                    store.delete_source_row = original_delete
                self.assertEqual(status, 400, body)
                self.assertIn("linked Harbor Trials", json.loads(body)["error"])
                self.assertEqual(deleted, [])
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
                    "POST",
                    f"/api/sources/{items[0].source_key}/category",
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
                self.assertIn("xlsx or json", json.loads(body)["error"])

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {"kind": "workspace_html", "source_keys": [items[1].source_key]},
                )
                self.assertEqual(status, 400)
                self.assertIn("xlsx or json", json.loads(body)["error"])
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
                        "summary": {
                            "scope": "leaderboard",
                            "source_keys": [
                                items[0].source_key,
                                items[1].source_key,
                            ],
                            "query": {
                                "state": "active",
                                "search": "",
                                "sort": "last_turn_end",
                                "direction": "desc",
                                "categories": [],
                                "tags": [],
                                "agents": [],
                                "models": [],
                                "results": [],
                                "views": [],
                            },
                            "group_by": "category",
                            "statistic": "max",
                        },
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
                    10,
                )
                self.assertIn("Current visible Leaderboard page", strings)
                self.assertIn("Category", strings)
                self.assertIn("Regression", strings)
                self.assertIn("<t>-</t>", strings)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": {
                            "scope": "leaderboard",
                            "source_keys": [items[0].source_key],
                            "query": {
                                "state": "active",
                                "search": "",
                                "sort": "last_turn_end",
                                "direction": "desc",
                                "categories": [],
                                "tags": [],
                                "agents": [],
                                "models": [],
                                "results": [],
                                "views": [],
                            },
                            "group_by": "agent",
                            "statistic": "mean",
                        },
                    },
                )
                self.assertEqual(status, 200)
                with zipfile.ZipFile(BytesIO(body)) as archive:
                    strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
                self.assertIn("Complete query", strings)
                self.assertIn("0/2 trials", strings)

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
                self.assertEqual(
                    len(
                        {
                            name
                            for name in names
                            if name.startswith("xl/charts/") and name.endswith(".xml")
                        }
                    ),
                    10,
                )

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": {
                            "scope": "leaderboard",
                            "source_keys": ["missing"],
                            "query": {
                                "state": "active",
                                "search": "",
                                "sort": "last_turn_end",
                                "direction": "desc",
                                "categories": [],
                                "tags": [],
                                "agents": [],
                                "models": [],
                                "results": [],
                                "views": [],
                            },
                            "group_by": "agent",
                            "statistic": "mean",
                        },
                    },
                )
                self.assertEqual(status, 400)
                self.assertIn("unknown source", json.loads(body)["error"])

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
                self.assertIn("does not exist", json.loads(body)["error"])
            finally:
                self.stop(store, server, thread)


if __name__ == "__main__":
    unittest.main()
