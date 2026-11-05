from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

from psycheval.config import HarborMount
from psycheval.serve import ServeAccess
from psycheval.serve.api_support import catalog_query
from psycheval.serve.visibility import project_catalog_payload
from psycheval.state import CatalogQuery
from psycheval.workspace_views import WorkspaceViewLibrary
from tests.peval.catalog_http_support import CatalogHttpTestCase
from tests.peval.cli_inputs_support import write_trial_cell_artifacts
from tests.peval.serve_state_support import wait_catalog_operation
from tests.peval.test_harbor_evidence import write_evidence_trial


class ServeCatalogHttpTests(CatalogHttpTestCase):
    def test_saved_harbor_notes_reach_catalog_and_guest_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence_trial(root / "jobs/job/trial")
            store, runtime, server, thread = self.running_server(root)
            try:
                runtime.set_config(
                    runtime.config.validated_update(
                        harbor_mounts=(
                            HarborMount(id="jobs", path=str(root / "jobs")),
                        ),
                    )
                )
                runtime.catalog.reconcile()
                row = runtime.catalog.query(CatalogQuery()).items[0].to_dict()
                key = row["source_key"]
                self.assertNotEqual(key, row["trial_key"])
                revision = row["artifact_revision"]
                for markdown in (
                    "中文备注\n\n**first**",
                    "Updated <note>",
                    " \n\t",
                    "",
                ):
                    with self.subTest(markdown=markdown):
                        status, _, body = self.request(
                            server,
                            "PATCH",
                            f"/api/sources/{quote(key, safe='')}",
                            {"notes": markdown},
                        )
                        self.assertEqual(status, 200, body)
                        detail = json.loads(body)
                        notes = detail["report"].get("annotations", {}).get("notes", [])
                        self.assertEqual(
                            notes[0]["markdown"] if notes else "", markdown
                        )
                        status, _, body = self.request(server, "GET", "/api/catalog")
                        self.assertEqual(status, 200, body)
                        page = json.loads(body)
                        for role in ("admin", "guest"):
                            projected = project_catalog_payload(page, role)
                            current = projected["items"][0]
                            self.assertEqual(current["notes_markdown"], markdown)
                            self.assertEqual(
                                current["notes_present"], bool(markdown.strip())
                            )
                            self.assertEqual(
                                projected["column_presence"]["notes"],
                                int(bool(markdown.strip())),
                            )
                            self.assertNotEqual(current["artifact_revision"], revision)
                            if role == "guest":
                                self.assertNotIn("source_ref", current)
                        revision = page["items"][0]["artifact_revision"]
            finally:
                self.stop(store, server, thread)

    def test_catalog_query_accepts_repeated_harbor_semantic_filters(self) -> None:
        query = catalog_query(
            "task=pbench-v1.0%2Fweb-search-01"
            "&task=pbench-v1.0%2Fweb-fetch-01"
            "&task=pbench-v1.0%2Fweb-search-01"
            "&job=opencode-real&provider=xiaomi-token-plan-cn"
            "&dataset=alpha&dataset=beta&dataset=alpha&sort=dataset"
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
        self.assertEqual(query.datasets, ("alpha", "beta"))
        self.assertEqual(query.sort, "dataset")

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
                    server, "GET", f"/api/sources/{source_key}"
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
                    "PATCH",
                    f"/api/sources/{source_key}",
                    {"alias": "compact"},
                )
                mutation = json.loads(body)
                self.assertEqual(status, 200)
                self.assertEqual(mutation["source_key"], source_key)
                self.assertEqual(
                    runtime.catalog.query(CatalogQuery())
                    .items[0]
                    .payload["source_alias"],
                    "compact",
                )

                status, _headers, body = self.request(
                    server,
                    "PATCH",
                    f"/api/sources/{source_key}",
                    {"category": "  Regression  "},
                )
                mutation = json.loads(body)
                self.assertEqual(status, 200)
                self.assertEqual(mutation["source_key"], source_key)
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
                    "PATCH",
                    f"/api/sources/{source_key}",
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
                    "/api/source-key-resolutions",
                    {"source_keys": ["missing", source_key]},
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["source_keys"], [source_key])

                status, _headers, body = self.request(
                    server, "GET", "/api/sources/missing"
                )
                self.assertEqual(status, 404)
                self.assertIn("unknown source", json.loads(body)["detail"])
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
                        "/api/source-key-resolutions",
                        {"source_keys": ["missing"]},
                    )
                self.assertEqual(status, 500)
                self.assertEqual(json.loads(body)["detail"], "internal server error")
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
            item_started = threading.Event()
            finish_item = threading.Event()
            scan_started = threading.Event()
            finish_scan = threading.Event()
            build = runtime.catalog._build_generation

            def archive(_item):
                item_started.set()
                self.assertTrue(finish_item.wait(5))

            def scan():
                scan_started.set()
                self.assertTrue(finish_scan.wait(5))
                return build()

            try:
                with patch.object(
                    runtime.catalog, "_build_generation", side_effect=scan
                ):
                    operation = runtime.catalog.start_operation(
                        "archive", [source_key], archive
                    )
                    try:
                        self.assertTrue(item_started.wait(5))
                        for scanning in (False, True):
                            if scanning:
                                finish_item.set()
                                self.assertTrue(scan_started.wait(5))
                            for path in ("/api/catalog", "/api/catalog-status"):
                                status, _, body = self.request(server, "GET", path)
                                self.assertEqual(status, 200)
                                page = json.loads(body)
                                self.assertEqual(page["checking"], scanning)
                                self.assertEqual(page["stale"], scanning)
                                if path == "/api/catalog":
                                    self.assertEqual(page["total"], 1)
                                else:
                                    self.assertEqual(
                                        page["phase"],
                                        "discovering" if scanning else "idle",
                                    )
                            status, _, _ = self.request(
                                server,
                                "PATCH",
                                f"/api/sources/{source_key}",
                                {"alias": "blocked"},
                            )
                            self.assertEqual(status, 409)
                    finally:
                        finish_item.set()
                        finish_scan.set()
                        self.assertEqual(
                            wait_catalog_operation(
                                runtime.catalog, operation.operation_id
                            ).state,
                            "completed",
                        )
                self.assertTrue(runtime.catalog._writer_lock.acquire(blocking=False))
                try:
                    status, _headers, body = self.request(
                        server,
                        "PUT",
                        "/api/views/Blocked%20during%20snapshot",
                        {
                            "filters": {},
                            "group_by": "agent",
                            "notes": "",
                            "overwrite": False,
                        },
                    )
                finally:
                    runtime.catalog._writer_lock.release()
                self.assertEqual(status, 409)
                self.assertIn("writer operation", json.loads(body)["detail"])
                self.assertFalse(
                    (
                        WorkspaceViewLibrary(root)._path_for_name(
                            "Blocked during snapshot"
                        )
                    ).exists()
                )
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
                    "/api/source-state-operations",
                    {"source_keys": keys, "active": False},
                )
                self.assertEqual(status, 202)
                operation_id = json.loads(body)["id"]
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
                self.assertEqual(operation["state"], "failed")
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
                    "/api/source-deletion-operations",
                    {"source_keys": [source_key]},
                )
                self.assertEqual(status, 202, body)
                operation_id = json.loads(body)["id"]
                operation = None
                for _attempt in range(100):
                    status, _headers, body = self.request(
                        server, "GET", f"/api/operations/{operation_id}"
                    )
                    operation = json.loads(body)
                    if operation["state"] not in {"queued", "running"}:
                        break
                    time.sleep(0.01)
                self.assertEqual(operation["state"], "succeeded")
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
                        "/api/source-deletion-operations",
                        {"source_keys": ["normal", "linked"]},
                    )
                finally:
                    runtime.catalog.row_for_key = original_row_for_key
                    store.delete_source_row = original_delete
                self.assertEqual(status, 400, body)
                self.assertIn("linked Harbor Trials", json.loads(body)["detail"])
                self.assertEqual(deleted, [])
            finally:
                self.stop(store, server, thread)


if __name__ == "__main__":
    unittest.main()
