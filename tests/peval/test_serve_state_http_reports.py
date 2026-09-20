from __future__ import annotations

import http.client

from psycheval.evaluation_reports import evaluation_report_ref
from tests.peval.serve_state_support import (
    LocalHTTPServer,
    Path,
    ServeRuntime,
    ToolConfig,
    json,
    make_handler,
    open_workspace_state,
    peval_workspace,
    raw_get_json,
    request_bytes,
    request_json,
    tempfile,
    threading,
    unittest,
    write_trial_cell_artifacts,
)


class PevalServeWorkspaceReportHttpTests(unittest.TestCase):
    def test_report_bindings_can_clear_the_final_association(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            cell = root / "runs" / "default" / "psychevo" / "s1" / "s1_t001"
            write_trial_cell_artifacts(cell, session_id="s1", trial_key="s1_t001")
            report_path = root / "analysis.md"
            report_path.write_text("# Report\n")
            config = ToolConfig(adapter="psychevo", workspace_root=str(root))
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, config)
            source_key = runtime.source_envelope()["sources"][0]["source_key"]
            report_id = runtime.workspace_reports.import_file(report_path, [source_key])
            state_path = root / "reports" / report_id / "state.json"
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                initial_state = {
                    "source_refs": ["runs/default/psychevo/s1/s1_t001"],
                }
                for invalid_payload, expected_status in (
                    ({}, 422),
                    ({"source_keys": None}, 422),
                    ({"source_key": source_key}, 422),
                    ({"source_keys": source_key}, 422),
                    ({"bindings": [{"kind": "session", "key": ""}]}, 422),
                ):
                    status, _, body = request_json(
                        port,
                        "PUT",
                        f"/api/report-library/package:{report_id}/bindings",
                        invalid_payload,
                        origin=origin,
                    )
                    self.assertEqual(status, expected_status)
                    self.assertTrue(body.get("detail"))
                    self.assertEqual(json.loads(state_path.read_text()), initial_state)

                status, _, body = request_json(
                    port,
                    "PUT",
                    f"/api/report-library/package:{report_id}/bindings",
                    {"bindings": []},
                    origin=origin,
                )

                self.assertEqual(status, 200)
                self.assertEqual(body["source_keys"], [])
                self.assertEqual(
                    json.loads(state_path.read_text()),
                    {"source_refs": []},
                )
                get_status, catalog = raw_get_json(port, "/api/reports")
                self.assertEqual(get_status, 200)
                self.assertEqual(catalog[0]["source_keys"], [])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_canonical_evaluation_reports_are_paged_and_read_live_by_opaque_ref(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            source_ref = "runs/default/psychevo/s1/s1_t001"
            cell = root / source_ref
            write_trial_cell_artifacts(cell, session_id="s1", trial_key="s1_t001")
            report_path = cell / "analysis.md"
            report_path.write_text(
                "# Canonical\n\n<script>blocked()</script>\n",
                encoding="utf-8",
            )
            config = ToolConfig(adapter="psychevo", workspace_root=str(root))
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, config)
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            try:
                status, headers, body = request_bytes(
                    port,
                    "/api/report-library?page=1&page_size=1",
                )
                self.assertEqual(status, 200)
                self.assertEqual(headers["cache-control"], "no-store")
                page = json.loads(body)
                self.assertEqual((page["total"], page["page_size"]), (1, 1))
                item = page["items"][0]
                report_ref = evaluation_report_ref(source_ref)
                self.assertEqual(item["report_ref"], report_ref)
                self.assertEqual(item["format"], "markdown")
                self.assertEqual(item["filename"], "analysis.md")
                self.assertEqual(item["source_keys"], [item["primary_source_key"]])
                serialized = json.dumps(item)
                for private in (source_ref, str(root), "revision", "report_path"):
                    self.assertNotIn(private, serialized)

                status, headers, preview = request_bytes(
                    port,
                    f"/api/report-library/{report_ref}/preview",
                )
                self.assertEqual(status, 200)
                self.assertEqual(headers["cache-control"], "no-store")
                self.assertIn(b"<h1>Canonical</h1>", preview)
                self.assertNotIn(b"<script>blocked()", preview)

                report_path.write_text("# Current body\n", encoding="utf-8")
                status, _, preview = request_bytes(
                    port,
                    f"/api/report-library/{report_ref}/preview",
                )
                self.assertEqual(status, 200)
                self.assertIn(b"<h1>Current body</h1>", preview)

                status, _, reader = request_bytes(
                    port,
                    f"/api/report-library/{report_ref}/reader",
                )
                self.assertEqual(status, 200)
                self.assertIn(
                    f"/api/report-library/analysis%3A{report_ref.split(':', 1)[1]}/preview".encode(),
                    reader,
                )

                status, _, body = request_bytes(
                    port,
                    "/api/report-library?page=not-an-integer",
                )
                self.assertEqual(status, 422)
                self.assertIn(b"integer", body)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_report_previews_are_isolated_and_null_or_malformed_origins_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            cell = root / "runs" / "default" / "psychevo" / "s1" / "s1_t001"
            write_trial_cell_artifacts(cell, session_id="s1", trial_key="s1_t001")
            markdown_path = root / "analysis.md"
            markdown_path.write_text(
                "# Report\n\n| A | B |\n| - | - |\n| x | y |\n\n"
                "~~removed~~ <script>alert('unsafe')</script>\n"
            )
            html_path = root / "analysis.html"
            html_bytes = (
                b"<!doctype html><script src='https://example.com/a.js'></script>"
            )
            html_path.write_bytes(html_bytes)
            config = ToolConfig(adapter="psychevo", workspace_root=str(root))
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, config)
            source_key = runtime.source_envelope()["sources"][0]["source_key"]
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            payload = {
                "path": str(markdown_path.resolve()),
                "bindings": [{"kind": "session", "key": source_key}],
            }
            try:
                for rejected_origin in ("null", "not-an-origin", f"{origin}/path"):
                    status, _, body = request_json(
                        port,
                        "POST",
                        "/api/reports",
                        payload,
                        origin=rejected_origin,
                    )
                    self.assertEqual(status, 403)
                    self.assertIn("same-origin Origin", body["detail"])

                request_body = json.dumps(payload)
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                conn.request(
                    "POST",
                    "/api/reports",
                    body=request_body,
                    headers={"Content-Type": "application/json", "Referer": "null"},
                )
                response = conn.getresponse()
                referer_body = json.loads(response.read())
                conn.close()
                self.assertEqual(response.status, 403)
                self.assertIn("same-origin Referer", referer_body["detail"])

                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/reports",
                    payload,
                    origin=origin,
                )
                self.assertEqual(status, 201)
                markdown_id = body["report_id"]
                markdown_ref = body["report_ref"]
                status, headers, preview = request_bytes(
                    port,
                    f"/api/report-library/{markdown_ref}/preview",
                )
                self.assertEqual(status, 200)
                self.assertIn("text/html", headers["content-type"])
                self.assertEqual(headers["referrer-policy"], "no-referrer")
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertEqual(headers["cache-control"], "no-store")
                csp = headers["content-security-policy"]
                self.assertIn("sandbox allow-scripts", csp)
                self.assertIn("object-src 'none'", csp)
                self.assertIn("base-uri 'none'", csp)
                self.assertIn("form-action 'none'", csp)
                preview_text = preview.decode()
                self.assertIn("<table>", preview_text)
                self.assertIn("<s>removed</s>", preview_text)
                self.assertIn("&lt;script&gt;", preview_text)
                self.assertNotIn("<script>alert", preview_text)
                legacy_status, _, _ = request_bytes(
                    port,
                    f"/api/reports/{markdown_id}/preview",
                )
                self.assertEqual(legacy_status, 404)

                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/reports",
                    {
                        "path": str(html_path.resolve()),
                        "bindings": [{"kind": "session", "key": source_key}],
                    },
                    origin=origin,
                )
                self.assertEqual(status, 201)
                html_id = body["report_id"]
                html_ref = body["report_ref"]
                status, headers, preview = request_bytes(
                    port,
                    f"/api/report-library/{html_ref}/preview",
                )
                self.assertEqual(status, 200)
                self.assertEqual(preview, html_bytes)
                self.assertIn(
                    "script-src 'unsafe-inline' http: https:",
                    headers["content-security-policy"],
                )

                status, headers, opened = request_bytes(
                    port,
                    f"/api/report-library/{html_ref}/reader",
                )
                self.assertEqual(status, 200)
                self.assertIn("text/html", headers["content-type"])
                self.assertEqual(headers["referrer-policy"], "no-referrer")
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertEqual(headers["cache-control"], "no-store")
                self.assertIn("default-src 'none'", headers["content-security-policy"])
                self.assertIn("frame-src 'self'", headers["content-security-policy"])
                opened_text = opened.decode()
                self.assertIn(
                    f'<iframe src="/api/report-library/package%3A{html_id}/preview"',
                    opened_text,
                )
                self.assertIn('sandbox="allow-scripts"', opened_text)
                self.assertIn('referrerpolicy="no-referrer"', opened_text)
                self.assertNotIn(html_bytes.decode(), opened_text)

                status, _, missing = request_bytes(
                    port,
                    "/api/report-library/package:20260710-000000-000000/preview",
                )
                self.assertEqual(status, 404)
                self.assertIn(b"unknown report", missing)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()


if __name__ == "__main__":
    unittest.main()
