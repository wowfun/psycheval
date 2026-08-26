from __future__ import annotations

import http.client
import io
import json
import re
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

from psycheval.config import ToolConfig
from psycheval.serve import (
    LocalHTTPServer,
    ServeAccess,
    ServeRuntime,
    make_handler,
)
from psycheval.state import CatalogQuery, open_workspace_state
from tests.peval.cli_inputs_support import write_trial_cell_artifacts


class ServeAccessHttpTests(unittest.TestCase):
    @staticmethod
    def script_json(content: bytes, element_id: str) -> dict:
        match = re.search(
            rb'<script type="application/json" id="'
            + re.escape(element_id.encode())
            + rb'">(.*?)</script>',
            content,
            re.DOTALL,
        )
        if match is None:
            raise AssertionError(f"missing JSON script: {element_id}")
        return json.loads(match.group(1))

    def running_server(self, root: Path):
        (root / "peval.toml").write_text(
            'analysis_eval_slug = "default"\n', encoding="utf-8"
        )
        store = open_workspace_state(str(root))
        runtime = ServeRuntime(
            store,
            ToolConfig(
                workspace_root=str(root),
                analysis_eval_slug="default",
                adapter_default_db_paths={
                    "psychevo": str(root / "private" / "psychevo.db")
                },
            ),
        )
        access = ServeAccess("correct horse battery staple")
        server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime, access=access))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return store, runtime, server, thread

    def request(
        self,
        server: LocalHTTPServer,
        method: str,
        path: str,
        payload: dict | None = None,
        *,
        cookie: str | None = None,
        origin: str | None = None,
        request_headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers: dict[str, str] = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
            headers["Origin"] = (
                origin
                if origin is not None
                else f"http://127.0.0.1:{server.server_port}"
            )
        if cookie:
            headers["Cookie"] = cookie
        headers.update(request_headers or {})
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_port, timeout=5
        )
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        content = response.read()
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        connection.close()
        return response.status, response_headers, content

    @staticmethod
    def stop(store, server, thread) -> None:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        store.close()

    def test_guest_login_admin_logout_and_fail_closed_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_trial_cell_artifacts(
                root / "runs/default/psychevo/session/trial",
                session_id="session",
                trial_key="trial",
            )
            store, runtime, server, thread = self.running_server(root)
            source_key = runtime.catalog.query(CatalogQuery()).items[0].source_key
            try:
                status, headers, body = self.request(server, "GET", "/api/auth/session")
                self.assertEqual(status, 200)
                self.assertEqual(
                    json.loads(body),
                    {"authentication_enabled": True, "role": "guest"},
                )
                self.assertEqual(headers["cache-control"], "no-store")
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertEqual(headers["referrer-policy"], "no-referrer")

                status, headers, shell = self.request(server, "GET", "/")
                self.assertEqual(status, 200)
                self.assertEqual(headers["x-frame-options"], "DENY")
                guest_markup = re.sub(
                    rb"<script(?:\s[^>]*)?>.*?</script>",
                    b"",
                    shell,
                    flags=re.DOTALL,
                )
                self.assertIn(b"data-admin-login-open", guest_markup)
                self.assertNotIn(b"data-harbor-workbench", guest_markup)
                self.assertIn(b'href="/datasets"', guest_markup)
                self.assertIn(b'href="/reports"', guest_markup)
                self.assertNotIn(b'href="/config"', guest_markup)
                self.assertNotIn(b"data-locale-select", guest_markup)
                self.assertIn(b"data-view-save-dialog", guest_markup)
                self.assertIn(b'value="browser"', guest_markup)
                self.assertNotIn(b'value="workspace"', guest_markup)
                self.assertNotIn(str(root).encode(), guest_markup)
                guest_options = self.script_json(shell, "peval-render-options")
                self.assertEqual(guest_options["role"], "guest")
                self.assertTrue(guest_options["authentication_enabled"])
                self.assertEqual(guest_options["adapter_defaults"], {})
                self.assertNotIn("harbor_mounts", guest_options)
                self.assertNotIn("load_error", guest_options)
                self.assertEqual(guest_options["workspace_id"], runtime.workspace_id)
                self.assertNotIn(str(root), json.dumps(guest_options))

                for asset_path in (
                    "/assets/peval/main.js",
                    "/assets/peval/modules/runtime.js",
                ):
                    status, headers, asset = self.request(server, "GET", asset_path)
                    self.assertEqual(status, 200, asset[:200])
                    self.assertEqual(
                        headers["content-type"],
                        "application/javascript; charset=utf-8",
                    )
                    self.assertEqual(headers["cache-control"], "no-store")
                    self.assertTrue(asset.strip())
                status, headers, stylesheet = self.request(
                    server, "GET", "/assets/peval/workspace.css"
                )
                self.assertEqual(status, 200, stylesheet[:200])
                self.assertEqual(headers["content-type"], "text/css; charset=utf-8")
                self.assertEqual(headers["cache-control"], "no-cache")
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertRegex(headers["etag"], r'^"[0-9a-f]{64}"$')
                self.assertTrue(stylesheet.strip())
                status, cached_headers, cached_stylesheet = self.request(
                    server,
                    "GET",
                    "/assets/peval/workspace.css",
                    request_headers={"If-None-Match": headers["etag"]},
                )
                self.assertEqual(status, 304)
                self.assertEqual(cached_headers["etag"], headers["etag"])
                self.assertEqual(cached_headers["cache-control"], "no-cache")
                self.assertNotIn("content-length", cached_headers)
                self.assertEqual(cached_stylesheet, b"")
                for rejected_path in (
                    "/assets/peval/../report.js",
                    "/assets/peval/report.css",
                    "/assets/peval/missing.js",
                ):
                    status, _headers, _body = self.request(server, "GET", rejected_path)
                    self.assertEqual(status, 404)

                status, _headers, body = self.request(server, "GET", "/api/catalog")
                self.assertEqual(status, 200)
                row = json.loads(body)["items"][0]
                for private in (
                    "artifact_dir",
                    "db_path",
                    "input_path",
                    "last_error",
                    "path",
                    "source_ref",
                ):
                    self.assertNotIn(private, row)

                status, _headers, body = self.request(server, "GET", "/api/sources")
                self.assertEqual(status, 403)
                self.assertIn("administrator", json.loads(body)["error"])
                status, _headers, body = self.request(
                    server, "GET", "/api/config/harbor"
                )
                self.assertEqual(status, 403)
                self.assertIn("administrator", json.loads(body)["error"])
                status, _headers, body = self.request(
                    server, "GET", "/api/harbor/datasets"
                )
                self.assertEqual(status, 200)
                harbor_inventory = json.loads(body)
                self.assertEqual(harbor_inventory, {"datasets": []})
                self.assertNotIn("revision", harbor_inventory)
                status, _headers, datasets_shell = self.request(
                    server, "GET", "/datasets"
                )
                self.assertEqual(status, 200)
                datasets_markup = re.sub(
                    rb"<script(?:\s[^>]*)?>.*?</script>",
                    b"",
                    datasets_shell,
                    flags=re.DOTALL,
                )
                self.assertIn(b"data-harbor-workbench", datasets_markup)
                self.assertIn(b'aria-current="page">Datasets</a>', datasets_markup)
                self.assertNotIn(b"data-harbor-add-dataset", datasets_markup)
                self.assertNotIn(b"data-harbor-download", datasets_markup)
                self.assertNotIn(str(root).encode(), datasets_markup)
                status, _headers, reports_shell = self.request(
                    server, "GET", "/reports"
                )
                self.assertEqual(status, 200)
                self.assertIn(b"data-report-manager", reports_shell)
                status, _headers, _body = self.request(server, "GET", "/config")
                self.assertEqual(status, 403)
                status, _headers, _body = self.request(
                    server,
                    "POST",
                    "/api/harbor/tasks",
                    {"action": "create"},
                )
                self.assertEqual(status, 403)
                status, _headers, _body = self.request(
                    server,
                    "POST",
                    f"/api/sources/{source_key}/alias",
                    {"alias": "forbidden"},
                )
                self.assertEqual(status, 403)
                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/catalog/resolve",
                    {"source_keys": [source_key]},
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["source_keys"], [source_key])
                status, _headers, _body = self.request(
                    server, "GET", "/api/not-classified-yet"
                )
                self.assertEqual(status, 403)

                status, _headers, _body = self.request(
                    server,
                    "POST",
                    "/api/auth/login",
                    {"password": "correct horse battery staple"},
                    origin="http://attacker.invalid",
                )
                self.assertEqual(status, 403)
                status, _headers, _body = self.request(
                    server,
                    "POST",
                    "/api/auth/login",
                    {"password": "wrong"},
                )
                self.assertEqual(status, 401)
                status, headers, body = self.request(
                    server,
                    "POST",
                    "/api/auth/login",
                    {"password": "correct horse battery staple"},
                )
                self.assertEqual(status, 200, body)
                self.assertEqual(json.loads(body)["role"], "admin")
                set_cookie = headers["set-cookie"]
                self.assertIn("HttpOnly", set_cookie)
                self.assertIn("SameSite=Strict", set_cookie)
                self.assertIn("Path=/", set_cookie)
                self.assertNotIn("Secure", set_cookie)
                cookie = set_cookie.split(";", 1)[0]

                status, _headers, body = self.request(
                    server, "GET", "/api/auth/session", cookie=cookie
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["role"], "admin")
                status, _headers, admin_shell = self.request(
                    server, "GET", "/", cookie=cookie
                )
                self.assertEqual(status, 200)
                admin_markup = re.sub(
                    rb"<script(?:\s[^>]*)?>.*?</script>",
                    b"",
                    admin_shell,
                    flags=re.DOTALL,
                )
                self.assertIn(b"data-admin-logout", admin_markup)
                self.assertIn(b'href="/datasets"', admin_markup)
                self.assertIn(b'href="/reports"', admin_markup)
                self.assertIn(b'href="/config"', admin_markup)
                self.assertNotIn(b"data-harbor-workbench", admin_markup)
                self.assertLess(
                    admin_markup.index(b'href="/datasets"'),
                    admin_markup.index(b'href="/reports"'),
                )
                self.assertLess(
                    admin_markup.index(b'href="/reports"'),
                    admin_markup.index(b'href="/config"'),
                )
                self.assertIn(b"data-locale-select", admin_markup)
                self.assertIn(b'value="workspace" checked', admin_markup)
                self.assertIn(b'value="browser"', admin_markup)
                self.assertNotIn(b"data-admin-login-open", admin_markup)
                status, _headers, admin_datasets = self.request(
                    server, "GET", "/datasets", cookie=cookie
                )
                self.assertEqual(status, 200)
                admin_datasets_markup = re.sub(
                    rb"<script(?:\s[^>]*)?>.*?</script>",
                    b"",
                    admin_datasets,
                    flags=re.DOTALL,
                )
                self.assertIn(b"data-harbor-workbench", admin_datasets_markup)
                self.assertNotIn(b"data-config-page", admin_datasets_markup)
                status, _headers, admin_reports = self.request(
                    server, "GET", "/reports", cookie=cookie
                )
                self.assertEqual(status, 200)
                admin_reports_markup = re.sub(
                    rb"<script(?:\s[^>]*)?>.*?</script>",
                    b"",
                    admin_reports,
                    flags=re.DOTALL,
                )
                self.assertIn(b"data-report-manager", admin_reports_markup)
                self.assertNotIn(b"data-harbor-workbench", admin_reports_markup)
                status, _headers, admin_config = self.request(
                    server, "GET", "/config", cookie=cookie
                )
                self.assertEqual(status, 200)
                admin_config_markup = re.sub(
                    rb"<script(?:\s[^>]*)?>.*?</script>",
                    b"",
                    admin_config,
                    flags=re.DOTALL,
                )
                self.assertIn(b"data-config-page", admin_config_markup)
                self.assertNotIn(b"data-report-manager", admin_config_markup)
                status, _headers, _body = self.request(
                    server, "GET", "/sources", cookie=cookie
                )
                self.assertEqual(status, 404)
                status, _headers, body = self.request(
                    server, "GET", "/api/config/harbor", cookie=cookie
                )
                self.assertEqual(status, 200, body)
                self.assertEqual(
                    set(json.loads(body)), {"revision", "datasets", "mounts"}
                )
                status, _headers, body = self.request(
                    server, "GET", "/api/sources", cookie=cookie
                )
                self.assertEqual(status, 200, body)
                self.assertIn("sources", json.loads(body))
                status, _headers, body = self.request(
                    server,
                    "POST",
                    f"/api/sources/{source_key}/alias",
                    {"alias": "admin edit"},
                    cookie=cookie,
                )
                self.assertEqual(status, 200, body)

                status, headers, body = self.request(
                    server,
                    "POST",
                    "/api/auth/logout",
                    {},
                    cookie=cookie,
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["role"], "guest")
                self.assertIn("Max-Age=0", headers["set-cookie"])
                status, _headers, _body = self.request(
                    server, "GET", "/api/sources", cookie=cookie
                )
                self.assertEqual(status, 403)

                for _ in range(5):
                    status, _headers, _body = self.request(
                        server,
                        "POST",
                        "/api/auth/login",
                        {"password": "wrong again"},
                    )
                    self.assertEqual(status, 401)
                status, headers, _body = self.request(
                    server,
                    "POST",
                    "/api/auth/login",
                    {"password": "wrong again"},
                )
                self.assertEqual(status, 429)
                self.assertGreaterEqual(int(headers["retry-after"]), 1)
            finally:
                self.stop(store, server, thread)

    def test_guest_report_view_and_summary_export_routes(self) -> None:
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
                report_path = root / "guest-report.md"
                report_path.write_text(
                    "# Published\n\n<script>blocked()</script>\n", encoding="utf-8"
                )
                report_id = runtime.workspace_reports.import_file(
                    report_path, [source_key]
                )
                status, _headers, body = self.request(server, "GET", "/api/reports")
                self.assertEqual(status, 200, body)

                reports = json.loads(body)["reports"]
                self.assertEqual([item["report_id"] for item in reports], [report_id])

                status, headers, body = self.request(
                    server, "GET", f"/api/reports/{report_id}/preview"
                )
                self.assertEqual(status, 200, body)
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertIn(b"<h1>Published</h1>", body)
                self.assertNotIn(b"<script>blocked()", body)

                status, headers, body = self.request(
                    server, "GET", f"/api/reports/{report_id}/open"
                )
                self.assertEqual(status, 200, body)
                self.assertIn('sandbox="allow-scripts"', body.decode())
                self.assertIn("content-security-policy", headers)

                status, _headers, body = self.request(server, "GET", "/api/views")
                self.assertEqual(status, 200, body)
                self.assertEqual(json.loads(body), {"views": []})
                status, _headers, body = self.request(
                    server, "GET", "/api/views/summary"
                )
                self.assertEqual(status, 200, body)
                self.assertEqual(json.loads(body)["views"], [])

                browser_view = {
                    "name": "Guest local",
                    "filters": {},
                    "group_by": "agent",
                    "notes": "local",
                }
                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/catalog/query",
                    {
                        "state": "active",
                        "page": 1,
                        "page_size": 100,
                        "search": "",
                        "sort": "last_turn_end",
                        "direction": "desc",
                        "categories": [],
                        "tags": [],
                        "agents": [],
                        "models": [],
                        "tasks": [],
                        "jobs": [],
                        "providers": [],
                        "results": [],
                        "views": [],
                        "browser_views": [browser_view],
                    },
                )
                self.assertEqual(status, 200, body)
                self.assertEqual(json.loads(body)["total"], 1)
                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/views/summary",
                    {"browser_views": [browser_view]},
                )
                self.assertEqual(status, 200, body)
                self.assertEqual(json.loads(body)["views"][0]["name"], "Guest local")
                status, _headers, _body = self.request(
                    server,
                    "POST",
                    "/api/views/summary",
                    {"browser_views": [browser_view]},
                    origin="http://attacker.invalid",
                )
                self.assertEqual(status, 403)

                status, headers, body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {
                        "kind": "summary_xlsx",
                        "summary": {
                            "scope": "leaderboard",
                            "source_keys": [source_key],
                            "query": {
                                "state": "active",
                                "search": "",
                                "sort": "last_turn_end",
                                "direction": "desc",
                                "categories": [],
                                "tags": [],
                                "agents": [],
                                "models": [],
                                "tasks": [],
                                "jobs": [],
                                "providers": [],
                                "results": [],
                                "views": [],
                            },
                            "group_by": "agent",
                            "statistic": "mean",
                        },
                    },
                )
                self.assertEqual(status, 200, body[:200])
                self.assertEqual(body[:4], b"PK\x03\x04")
                self.assertIn(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers["content-type"],
                )
            finally:
                self.stop(store, server, thread)

    def test_guest_json_and_xlsx_exports_use_the_same_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cell = root / "runs/default/psychevo/session/trial"
            write_trial_cell_artifacts(
                cell,
                session_id="session",
                trial_key="trial",
            )
            trajectory_path = cell / "agent/trajectory.json"
            trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
            trajectory["steps"][0]["message"] = "Read /published/prompt.txt"
            trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
            meta_path = cell / "agent/trajectory_meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta.update(
                {
                    "data_ref": {
                        "label": r"\\server\private\trial.json",
                        "path": r"\\server\private\trial.json",
                        "relative_path": "../private/trial.json",
                    },
                    "task_metadata": {
                        "path": r"C:\Harbor\Tasks\task-a",
                        "diagnostic": "failed inside private task root",
                        "description": "Published task description",
                        "future_workspace_root": "/srv/future/task-root",
                    },
                    "harbor_provenance": {
                        "future_artifact_path": "/srv/future/artifact.json",
                        "regrade": {
                            "path": "/srv/regrade/source-trial",
                            "trial_id": "original-trial",
                            "future_log_path": "/srv/future/regrade.log",
                        },
                    },
                }
            )
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
            store, runtime, server, thread = self.running_server(root)
            source_key = runtime.catalog.query(CatalogQuery()).items[0].source_key
            try:
                status, _headers, body = self.request(
                    server, "GET", f"/api/report?source_key={source_key}"
                )
                self.assertEqual(status, 200, body)
                guest_report = json.loads(body)["report"]
                self.assertEqual(
                    guest_report["trajectory_meta"][0]["data_ref"],
                    {"label": "trial.json"},
                )
                self.assertEqual(
                    guest_report["trajectory_meta"][0]["task_metadata"],
                    {"description": "Published task description"},
                )
                self.assertEqual(
                    guest_report["trajectory_meta"][0]["harbor_provenance"]["regrade"],
                    {"trial_id": "original-trial"},
                )
                self.assertNotIn("/srv/future/", json.dumps(guest_report))
                self.assertEqual(
                    guest_report["trajectory"][0]["steps"][0]["message"],
                    "Read /published/prompt.txt",
                )

                status, _headers, json_body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {"kind": "json", "source_keys": [source_key]},
                )
                self.assertEqual(status, 200, json_body)
                json_report = json.loads(json_body)
                self.assertEqual(
                    json_report["trajectory_meta"][0]["data_ref"],
                    {"label": "trial.json"},
                )
                self.assertEqual(
                    json_report["trajectory"][0]["steps"][0]["message"],
                    "Read /published/prompt.txt",
                )

                status, _headers, xlsx_body = self.request(
                    server,
                    "POST",
                    "/api/exports",
                    {"kind": "xlsx", "source_keys": [source_key]},
                )
                self.assertEqual(status, 200, xlsx_body[:200])
                with zipfile.ZipFile(io.BytesIO(xlsx_body)) as archive:
                    worksheet = archive.read("xl/worksheets/sheet1.xml").decode()
                self.assertNotIn(r"C:\Harbor\Tasks", worksheet)
                self.assertNotIn("/srv/regrade/source-trial", worksheet)
                self.assertNotIn("/srv/future/", worksheet)
                self.assertNotIn(r"\\server\private", worksheet)
                self.assertIn("Published task description", worksheet)
                self.assertIn("original-trial", worksheet)

                status, headers, login_body = self.request(
                    server,
                    "POST",
                    "/api/auth/login",
                    {"password": "correct horse battery staple"},
                )
                self.assertEqual(status, 200, login_body)
                cookie = headers["set-cookie"].split(";", 1)[0]
                status, _headers, admin_body = self.request(
                    server,
                    "GET",
                    f"/api/report?source_key={source_key}",
                    cookie=cookie,
                )
                self.assertEqual(status, 200, admin_body)
                admin_meta = json.loads(admin_body)["report"]["trajectory_meta"][0]
                self.assertEqual(
                    admin_meta["data_ref"]["path"],
                    r"\\server\private\trial.json",
                )
                self.assertEqual(
                    admin_meta["task_metadata"]["path"],
                    r"C:\Harbor\Tasks\task-a",
                )
                self.assertEqual(
                    admin_meta["harbor_provenance"]["regrade"]["path"],
                    "/srv/regrade/source-trial",
                )
                self.assertEqual(
                    admin_meta["task_metadata"]["future_workspace_root"],
                    "/srv/future/task-root",
                )
                self.assertEqual(
                    admin_meta["harbor_provenance"]["future_artifact_path"],
                    "/srv/future/artifact.json",
                )
            finally:
                self.stop(store, server, thread)

    def test_admin_configures_acp_and_same_name_prompt_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, runtime, server, thread = self.running_server(root)
            try:
                status, headers, body = self.request(
                    server,
                    "POST",
                    "/api/auth/login",
                    {"password": "correct horse battery staple"},
                )
                self.assertEqual(status, 200, body)
                cookie = headers["set-cookie"].split(";", 1)[0]

                status, _headers, body = self.request(
                    server, "GET", "/api/config", cookie=cookie
                )
                self.assertEqual(status, 200, body)
                snapshot = json.loads(body)
                self.assertEqual(snapshot["acp_agents"], [])

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/config/acp/agents",
                    {
                        "action": "upsert",
                        "agent_id": "opencode",
                        "title": "OpenCode",
                        "command": "opencode",
                        "args": ["acp"],
                        "expected_revision": snapshot["revision"],
                    },
                    cookie=cookie,
                )
                self.assertEqual(status, 200, body)
                configured = json.loads(body)
                self.assertEqual(configured["acp_agents"][0]["args"], ["acp"])
                self.assertIn(
                    "[[acp.agents]]",
                    (root / "peval.toml").read_text(encoding="utf-8"),
                )

                status, _headers, _body = self.request(
                    server,
                    "POST",
                    "/api/config/acp/agents",
                    {
                        "action": "upsert",
                        "agent_id": "stale",
                        "title": "Stale",
                        "command": "stale",
                        "args": [],
                        "expected_revision": snapshot["revision"],
                    },
                    cookie=cookie,
                )
                self.assertEqual(status, 409)
                status, _headers, _body = self.request(
                    server,
                    "POST",
                    "/api/config/acp/agents",
                    {
                        "action": "delete",
                        "agent_ids": ["missing"],
                        "expected_revision": configured["revision"],
                    },
                    cookie=cookie,
                )
                self.assertEqual(status, 404)

                status, _headers, body = self.request(
                    server, "GET", "/api/prompts", cookie=cookie
                )
                self.assertEqual(status, 200, body)
                prompt = json.loads(body)["prompts"][0]
                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/prompts",
                    {
                        "action": "save",
                        "prompt_id": prompt["id"],
                        "content": "# Workspace review\n\nUse local criteria.\n",
                        "expected_revision": prompt["revision"],
                    },
                    cookie=cookie,
                )
                self.assertEqual(status, 200, body)
                customized = json.loads(body)["prompt"]
                self.assertTrue(customized["customized"])
                self.assertEqual(
                    (root / "prompts" / prompt["filename"]).read_text(encoding="utf-8"),
                    "# Workspace review\n\nUse local criteria.\n",
                )

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/prompts",
                    {
                        "action": "reset",
                        "prompt_id": prompt["id"],
                        "expected_revision": customized["revision"],
                    },
                    cookie=cookie,
                )
                self.assertEqual(status, 200, body)
                self.assertFalse(json.loads(body)["prompt"]["customized"])
                self.assertFalse((root / "prompts" / prompt["filename"]).exists())

                status, _headers, body = self.request(
                    server,
                    "POST",
                    "/api/config/acp/agents",
                    {
                        "action": "delete",
                        "agent_ids": ["opencode"],
                        "expected_revision": configured["revision"],
                    },
                    cookie=cookie,
                )
                self.assertEqual(status, 200, body)
                self.assertEqual(json.loads(body)["acp_agents"], [])
            finally:
                runtime.close()
                self.stop(store, server, thread)


if __name__ == "__main__":
    unittest.main()
