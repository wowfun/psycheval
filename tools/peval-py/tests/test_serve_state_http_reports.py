from __future__ import annotations

import http.client

from serve_state_support import *


class PevalPyServeWorkspaceReportHttpTests(unittest.TestCase):
    def test_loading_and_ready_envelopes_keep_report_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_py_workspace(Path(tmp))
            cell = root / "runs" / "default" / "psychevo" / "s1" / "s1_t001"
            write_trial_cell_artifacts(cell, session_id="s1", trial_key="s1_t001")
            report_path = root / "analysis.md"
            report_path.write_text("report")
            config = ToolConfig(adapter="psychevo", workspace_root=str(root))
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, config)
            source_key = runtime.source_envelope()["sources"][0]["source_key"]
            report_id = runtime.workspace_reports.import_file(report_path, [source_key])
            original_sync = store.sync_artifact_sources
            release_sync = threading.Event()

            def slow_sync(sync_config):
                release_sync.wait(timeout=5)
                return original_sync(sync_config)

            store.sync_artifact_sources = slow_sync
            runtime.start_initial_load(
                serve_args(),
                parse_adapter_assignments([], config.adapter),
            )
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            try:
                status, _, body = request_bytes(port, "/api/sources")
                self.assertEqual(status, 200)
                loading = json.loads(body)
                self.assertTrue(loading["loading"])
                self.assertEqual(loading["reports"][0]["report_id"], report_id)
                self.assertEqual(loading["reports"][0]["source_keys"], [])

                release_sync.set()
                self.assertTrue(runtime.wait_until_ready(timeout=5))
                status, _, body = request_bytes(port, "/api/sources")
                self.assertEqual(status, 200)
                ready = json.loads(body)
                self.assertFalse(ready["loading"])
                self.assertEqual(ready["reports"][0]["source_keys"], [source_key])
            finally:
                release_sync.set()
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                runtime.wait_until_ready(timeout=5)
                store.close()

    def test_report_import_rebind_delete_and_source_projection_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_py_workspace(Path(tmp))
            first_cell = root / "runs" / "default" / "psychevo" / "s1" / "s1_t001"
            second_cell = root / "runs" / "default" / "psychevo" / "s2" / "s2_t001"
            write_trial_cell_artifacts(first_cell, session_id="s1", trial_key="s1_t001")
            write_trial_cell_artifacts(second_cell, session_id="s2", trial_key="s2_t001")
            report_path = root / "cross-session-report.md"
            report_path.write_text("# Cross-session report\n")
            config = ToolConfig(adapter="psychevo", workspace_root=str(root))
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, config)
            sources = runtime.source_envelope()["sources"]
            source_keys = {
                source["trial_session_id"]: source["source_key"] for source in sources
            }
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/reports",
                    {
                        "path": str(report_path.resolve()),
                        "source_keys": [source_keys["s1"], source_keys["s2"]],
                    },
                    origin=origin,
                )
                self.assertEqual(status, 200)
                report_id = body["report_id"]
                self.assertEqual(body["reports"][0]["source_keys"], [source_keys["s1"], source_keys["s2"]])
                state_path = root / "reports" / report_id / "state.json"
                self.assertEqual(
                    json.loads(state_path.read_text()),
                    {
                        "source_keys": [
                            "runs/default/psychevo/s1/s1_t001",
                            "runs/default/psychevo/s2/s2_t001",
                        ]
                    },
                )

                status, _, sources_body = request_bytes(port, "/api/sources")
                self.assertEqual(status, 200)
                self.assertEqual(
                    json.loads(sources_body)["reports"][0]["report_id"],
                    report_id,
                )
                status, _, html = request_text(port, "/")
                self.assertEqual(status, 200)
                self.assertEqual(
                    script_json(html, "peval-py-render-options")["reports"][0]["report_id"],
                    report_id,
                )

                status, _, archive_body = request_json(
                    port,
                    "POST",
                    f"/api/sources/{source_keys['s2']}/archive",
                    {},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(
                    archive_body["reports"][0]["source_keys"],
                    [source_keys["s1"], source_keys["s2"]],
                )
                status, _, body = request_json(
                    port,
                    "POST",
                    f"/api/reports/{report_id}/bindings",
                    {"source_keys": [source_keys["s2"]]},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["reports"][0]["source_keys"], [source_keys["s2"]])
                self.assertEqual(
                    json.loads(state_path.read_text()),
                    {"source_keys": ["runs/default/psychevo/s2/s2_t001"]},
                )

                shutil.rmtree(second_cell)
                status, _, sources_body = request_bytes(port, "/api/sources")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(sources_body)["reports"][0]["source_keys"], [])
                self.assertEqual(
                    json.loads(state_path.read_text()),
                    {"source_keys": ["runs/default/psychevo/s2/s2_t001"]},
                )
                write_trial_cell_artifacts(second_cell, session_id="s2", trial_key="s2_t001")
                status, _, sources_body = request_bytes(port, "/api/sources")
                self.assertEqual(status, 200)
                self.assertEqual(
                    json.loads(sources_body)["reports"][0]["source_keys"],
                    [source_keys["s2"]],
                )

                status, _, body = request_json(
                    port,
                    "POST",
                    f"/api/reports/{report_id}/bindings",
                    {"source_keys": ["cell_unknown"]},
                    origin=origin,
                )
                self.assertEqual(status, 400)
                self.assertIn("unknown or unreadable source", body["error"])
                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/reports/20260710-000000-000000/delete",
                    {},
                    origin=origin,
                )
                self.assertEqual(status, 404)
                self.assertIn("unknown report", body["error"])

                status, _, body = request_json(
                    port,
                    "POST",
                    f"/api/reports/{report_id}/delete",
                    {},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body, {"reports": []})
                self.assertFalse((root / "reports" / report_id).exists())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_report_previews_are_isolated_and_null_or_malformed_origins_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_py_workspace(Path(tmp))
            cell = root / "runs" / "default" / "psychevo" / "s1" / "s1_t001"
            write_trial_cell_artifacts(cell, session_id="s1", trial_key="s1_t001")
            markdown_path = root / "analysis.md"
            markdown_path.write_text(
                "# Report\n\n| A | B |\n| - | - |\n| x | y |\n\n"
                "~~removed~~ <script>alert('unsafe')</script>\n"
            )
            html_path = root / "analysis.html"
            html_bytes = b"<!doctype html><script src='https://example.com/a.js'></script>"
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
            payload = {"path": str(markdown_path.resolve()), "source_keys": [source_key]}
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
                    self.assertIn("same-origin Origin", body["error"])

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
                self.assertIn("same-origin Referer", referer_body["error"])

                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/reports",
                    payload,
                    origin=origin,
                )
                self.assertEqual(status, 200)
                markdown_id = body["report_id"]
                status, headers, preview = request_bytes(
                    port,
                    f"/api/reports/{markdown_id}/preview",
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

                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/reports",
                    {"path": str(html_path.resolve()), "source_keys": [source_key]},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                html_id = body["report_id"]
                status, headers, preview = request_bytes(
                    port,
                    f"/api/reports/{html_id}/preview",
                )
                self.assertEqual(status, 200)
                self.assertEqual(preview, html_bytes)
                self.assertIn("script-src 'unsafe-inline' http: https:", headers["content-security-policy"])

                status, _, missing = request_bytes(
                    port,
                    "/api/reports/20260710-000000-000000/preview",
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
