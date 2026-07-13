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

from cli_inputs_support import write_trial_cell_artifacts
from peval_py.config import ToolConfig
from peval_py.serve import LocalHTTPServer, ServeRuntime, make_handler
from peval_py.state import CatalogQuery, open_workspace_state


class ServeCatalogHttpTests(unittest.TestCase):
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
            finally:
                with runtime.catalog._state_lock:
                    runtime.catalog._checking = False
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

    def test_server_exports_filtered_xlsx_and_selected_json_html(self) -> None:
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
                self.assertEqual(status, 200)
                self.assertIn("text/html", headers["content-type"])
                self.assertIn(items[1].payload["trial_session_id"].encode(), body)
                self.assertNotIn(items[0].payload["trial_session_id"].encode(), body)
            finally:
                self.stop(store, server, thread)


if __name__ == "__main__":
    unittest.main()
