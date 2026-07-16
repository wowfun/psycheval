from __future__ import annotations

import http.client
import base64
import json
import re
import tempfile
import threading
import time
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from cli_inputs_support import write_trial_cell_artifacts
from peval_py.config import ToolConfig
from peval_py.serve import LocalHTTPServer, ServeRuntime, make_handler
from peval_py.serve.errors import HttpError
from peval_py.state import CatalogQuery, open_workspace_state


class ServeCatalogHttpTests(unittest.TestCase):
    @staticmethod
    def workspace_snapshot_payload(**overrides):
        payload = {
            "kind": "workspace_html",
            "query": {
                "state": "active",
                "search": "",
                "sort": "last_turn_end",
                "direction": "desc",
                "tags": [],
                "agents": [],
                "models": [],
                "results": [],
                "views": [],
            },
            "selected_source_keys": [],
            "presentation": {
                "summary_group_by": "agent",
                "summary_statistic": "mean",
                "summary_table_open": False,
                "selected_source_key": None,
                "selected_step_id": None,
                "visible_view_names": [],
                "workspace_view_filters": {"tags": [], "models": [], "group_by": []},
                "open_view_tables": [],
            },
        }
        for key, value in overrides.items():
            payload[key] = value
        return payload

    @staticmethod
    def snapshot_projection(content: bytes) -> dict:
        match = re.search(
            rb'<script type="application/json" id="peval-py-workspace-snapshot">(.*?)</script>',
            content,
            re.DOTALL,
        )
        if match is None:
            raise AssertionError("workspace snapshot projection script is missing")
        return json.loads(match.group(1))

    def running_server(self, root: Path):
        (root / "peval-py.toml").write_text(
            'analysis_eval_slug = "default"\n', encoding="utf-8"
        )
        store = open_workspace_state(str(root))
        runtime = ServeRuntime(
            store,
            ToolConfig(workspace_root=str(root), analysis_eval_slug="default"),
        )
        server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
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

    def test_workspace_snapshot_export_is_full_query_offline_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(2):
                cell = root / f"runs/default/psychevo/s{index}/cell-{index}"
                write_trial_cell_artifacts(
                    cell,
                    session_id=f"session-{index}",
                    trial_key="duplicate-trial",
                )
                meta_path = cell / "agent/trajectory_meta.json"
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["finished_at_ms"] = 1_000 + index
                meta_path.write_text(json.dumps(meta), encoding="utf-8")
                state_path = cell / ".peval/state.json"
                state_path.parent.mkdir(parents=True, exist_ok=True)
                state_path.write_text(
                    json.dumps({"active": True, "source_tags": ["daily" if index == 1 else "other"]}),
                    encoding="utf-8",
                )
            store, runtime, server, thread = self.running_server(root)
            try:
                rows = [item.to_dict() for item in runtime.catalog.query(CatalogQuery()).items]
                source_keys = [row["source_key"] for row in rows]
                runtime.workspace_views.save(
                    name="Daily",
                    filters={"tags": ["daily"]},
                    group_by="agent",
                    notes="# Daily\n\nKeep <script>alert(1)</script> escaped.",
                    overwrite=False,
                )
                markdown_path = root / "analysis.md"
                markdown_path.write_text("# Safe\n\n<script>alert(1)</script>", encoding="utf-8")
                runtime.workspace_reports.import_file(markdown_path, [source_keys[0]])
                html_path = root / "analysis.html"
                html_path.write_text("<!doctype html><script>window.rawReport=true</script>", encoding="utf-8")
                runtime.workspace_reports.import_file(html_path, [source_keys[0]])
                echarts = b"window.__PEVAL_ECHARTS_OFFLINE__=true;"
                echarts_path = root / ".cache/echarts/6.0.0/echarts.min.js"
                echarts_path.parent.mkdir(parents=True, exist_ok=True)
                echarts_path.write_bytes(echarts)

                payload = self.workspace_snapshot_payload()
                payload["presentation"].update(
                    {
                        "selected_source_key": source_keys[0],
                        "selected_step_id": "1",
                        "visible_view_names": ["Daily"],
                        "workspace_view_filters": {
                            "tags": ["daily"],
                            "models": [],
                            "group_by": ["agent"],
                        },
                        "open_view_tables": ["Daily"],
                    }
                )
                status, headers, body = self.request(server, "POST", "/api/exports", payload)
                self.assertEqual(status, 200, body.decode("utf-8", errors="replace"))
                self.assertEqual(headers["content-type"], "text/html; charset=utf-8")
                self.assertIn("peval-workspace-snapshot.html", headers["content-disposition"])
                self.assertIn(echarts, body)
                self.assertNotIn(b"cdn.jsdelivr.net/npm/echarts", body)
                self.assertIn(b'class="serve-mode workspace-snapshot-mode"', body)
                initial_markup = re.sub(rb"<script(?:\s[^>]*)?>.*?</script>", b"", body, flags=re.DOTALL)
                self.assertNotIn(b"data-source-manager-open", initial_markup)
                self.assertNotIn(b"data-report-manager-open", initial_markup)
                self.assertNotIn(b"data-view-save-dialog", initial_markup)
                projection = self.snapshot_projection(body)
                self.assertEqual(
                    [row["trial_session_id"] for row in projection["catalog_rows"]],
                    ["session-1", "session-0"],
                )
                self.assertEqual(len(set(projection["source_trial_keys"].values())), 2)
                self.assertEqual([view["name"] for view in projection["views"]], ["Daily"])
                self.assertEqual(projection["view_summaries"][0]["matched_count"], 1)
                self.assertEqual(len(projection["reports"]), 2)
                previews = {
                    report["format"]: base64.b64decode(report["preview_base64"])
                    for report in projection["reports"]
                }
                self.assertIn(b"&lt;script&gt;alert(1)&lt;/script&gt;", previews["markdown"])
                self.assertEqual(
                    previews["html"],
                    b"<!doctype html><script>window.rawReport=true</script>",
                )

                selected_payload = self.workspace_snapshot_payload(
                    selected_source_keys=[source_keys[1]]
                )
                status, _headers, selected_body = self.request(
                    server, "POST", "/api/exports", selected_payload
                )
                self.assertEqual(status, 200)
                self.assertEqual(
                    [row["source_key"] for row in self.snapshot_projection(selected_body)["catalog_rows"]],
                    [source_keys[1]],
                )

                unknown_payload = self.workspace_snapshot_payload(
                    selected_source_keys=["unknown-source"]
                )
                status, _headers, error = self.request(
                    server, "POST", "/api/exports", unknown_payload
                )
                self.assertEqual(status, 400)
                self.assertIn("unknown source", json.loads(error)["error"])

                empty_payload = self.workspace_snapshot_payload()
                empty_payload["query"]["search"] = "definitely-no-match"
                status, _headers, error = self.request(
                    server, "POST", "/api/exports", empty_payload
                )
                self.assertEqual(status, 400)
                self.assertIn("matched no sources", json.loads(error)["error"])

                invalid_payload = self.workspace_snapshot_payload()
                del invalid_payload["presentation"]["open_view_tables"]
                status, _headers, error = self.request(
                    server, "POST", "/api/exports", invalid_payload
                )
                self.assertEqual(status, 400)
                self.assertIn("presentation fields", json.loads(error)["error"])

                with patch(
                    "peval_py.serve.handler.cached_echarts_asset",
                    side_effect=HttpError(502, "failed to cache ECharts: unavailable"),
                ):
                    status, _headers, error = self.request(
                        server,
                        "POST",
                        "/api/exports",
                        self.workspace_snapshot_payload(),
                    )
                self.assertEqual(status, 502)
                self.assertIn("failed to cache ECharts", json.loads(error)["error"])

                status, _headers, error = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {"kind": "html", "source_keys": [source_keys[0]]},
                )
                self.assertEqual(status, 400)
                self.assertIn("xlsx or json", json.loads(error)["error"])
            finally:
                self.stop(store, server, thread)

    def test_catalog_http_facets_ignore_search_and_column_filters_within_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            definitions = [
                ("alpha", "passed", "needle active", True),
                ("beta", "failed", "other active", True),
                ("archived", "passed", "other archived", False),
            ]
            for index, (tag, result, message, active) in enumerate(definitions):
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
                    json.dumps({"active": active, "source_tags": [tag]}),
                    encoding="utf-8",
                )

            store, _runtime, server, thread = self.running_server(root)
            try:
                status, _headers, body = self.request(
                    server,
                    "GET",
                    "/api/catalog?search=needle&tag=alpha&result=passed",
                )
                self.assertEqual(status, 200)
                active = json.loads(body)
                self.assertEqual(active["total"], 1)
                self.assertEqual(
                    {item["value"]: item["count"] for item in active["facets"]["tags"]},
                    {"alpha": 1, "beta": 1},
                )
                self.assertEqual(
                    {item["value"]: item["count"] for item in active["facets"]["results"]},
                    {"failed": 1, "passed": 1},
                )

                status, _headers, body = self.request(
                    server,
                    "GET",
                    "/api/catalog?state=archived&tag=archived",
                )
                self.assertEqual(status, 200)
                archived = json.loads(body)
                self.assertEqual(archived["total"], 1)
                self.assertEqual(
                    [item["value"] for item in archived["facets"]["tags"]],
                    ["archived"],
                )

                status, _headers, body = self.request(
                    server,
                    "GET",
                    "/api/catalog?state=all&search=needle&tag=alpha",
                )
                self.assertEqual(status, 200)
                all_states = json.loads(body)
                self.assertEqual(all_states["total"], 1)
                self.assertEqual(
                    {item["value"] for item in all_states["facets"]["tags"]},
                    {"alpha", "beta", "archived"},
                )
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
                    (root / "views" / "Daily focus.md").read_text(encoding="utf-8").split("---\n", 2)[-1],
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
                    {"name": "Daily focus", "field": "notes", "value": "Edited **Markdown**"},
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["view"]["notes"], "Edited **Markdown**")

                configuration = "filters:\n  results:\n    - passed\ngroup_by: overall\n"
                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/views/update",
                    {"name": "Daily focus", "field": "configuration", "value": configuration},
                )
                self.assertEqual(status, 200)
                updated = json.loads(body)["view"]
                self.assertEqual(updated["filters"], {"results": ["passed"]})
                self.assertEqual(updated["group_by"], "overall")

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/views/update",
                    {"name": "Daily focus", "field": "configuration", "value": "schema_version: 1\ngroup_by: agent\n"},
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
                    {item["value"]: item["count"] for item in first_page["facets"]["results"]},
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

                echarts_path = root / ".cache/echarts/6.0.0/echarts.min.js"
                echarts_path.parent.mkdir(parents=True, exist_ok=True)
                echarts_path.write_text("window.echarts={};", encoding="utf-8")
                snapshot_payload = self.workspace_snapshot_payload()
                snapshot_payload["query"].update(
                    {
                        "state": "all",
                        "sort": "session",
                        "direction": "asc",
                        "views": ["Passed", "Failed"],
                    }
                )
                status, _headers, body = self.request(
                    server, "POST", "/api/exports", snapshot_payload
                )
                self.assertEqual(status, 200)
                self.assertEqual(
                    [row["trial_session_id"] for row in self.snapshot_projection(body)["catalog_rows"]],
                    ["s0", "s1", "s2"],
                )

                snapshot_payload["query"]["views"] = ["Missing"]
                status, _headers, body = self.request(
                    server, "POST", "/api/exports", snapshot_payload
                )
                self.assertEqual(status, 400)
                self.assertIn("does not exist", json.loads(body)["error"])

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
            keys = [item.source_key for item in runtime.catalog.query(CatalogQuery()).items]
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
                self.assertIn("intentional item failure", operation["failures"][0]["error"])
                self.assertEqual(runtime.catalog.query(CatalogQuery(state="archived")).total, 1)
            finally:
                self.stop(store, server, thread)

    def test_server_exports_filtered_xlsx_selected_json_and_rejects_legacy_html(self) -> None:
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

                status, headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {"kind": "html", "source_keys": [items[1].source_key]},
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
                            "source_keys": [items[0].source_key],
                            "group_by": "overall",
                            "statistic": "max",
                        },
                    },
                )
                self.assertEqual(status, 200)
                self.assertIn("peval-leaderboard-summary.xlsx", headers["content-disposition"])
                with zipfile.ZipFile(BytesIO(body)) as archive:
                    names = set(archive.namelist())
                    strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
                self.assertIn("xl/charts/chart6.xml", names)
                self.assertNotIn("xl/charts/chart7.xml", names)
                self.assertIn("Current visible Leaderboard page", strings)
                self.assertNotIn("s1_t001", strings)

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
                self.assertIn("xl/charts/chart6.xml", names)
                self.assertNotIn("xl/charts/chart7.xml", names)

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": {
                            "scope": "leaderboard",
                            "source_keys": ["missing"],
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
