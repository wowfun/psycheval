from __future__ import annotations

import io
import json
import os
import shutil
import sqlite3
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from psycheval.config import ToolConfig
from psycheval.serve.exports import (
    MAX_REPORT_EXPORT_CELLS,
    MAX_REPORT_EXPORT_INPUT_BYTES,
    build_serve_export,
    build_workspace_snapshot_export,
)
from psycheval.serve.payloads import WorkspaceSnapshotPresentation
from psycheval.state import (
    CatalogBusyError,
    CatalogQuery,
    WorkspaceCatalog,
    open_workspace_state,
)
from psycheval.state.catalog import (
    CATALOG_SCHEMA_VERSION,
    _count_matching_source_refs,
)
from psycheval.workspace_reports import WorkspaceReportLibrary
from psycheval.workspace_views import WorkspaceViewLibrary
from tests.peval.cli_inputs_support import write_trial_cell_artifacts


class WorkspaceCatalogTests(unittest.TestCase):
    def test_invalid_generation_retains_the_complete_zero_presence_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, catalog = self.catalog(root)
            try:
                unavailable = catalog.query(CatalogQuery(), include_facets=False)
                self.write_cell(root, 1)
                catalog.reconcile()
                available = catalog.query(CatalogQuery(), include_facets=False)

                self.assertEqual(
                    set(unavailable.column_presence), set(available.column_presence)
                )
                self.assertTrue(unavailable.column_presence)
                self.assertTrue(
                    all(value == 0 for value in unavailable.column_presence.values())
                )
            finally:
                store.close()

    def test_column_presence_uses_session_value_and_preserves_zero_analysis(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cell = self.write_cell(root, 1)
            trajectory_path = cell / "agent" / "trajectory.json"
            trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
            trajectory.pop("session_id", None)
            trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
            store, catalog = self.catalog(root)
            try:
                catalog.reconcile()
                page = catalog.query(CatalogQuery(), include_facets=False)

                self.assertIsNone(page.items[0].payload["trial_session_id"])
                self.assertEqual(page.column_presence["session_id"], 0)
                self.assertEqual(page.items[0].payload["analysis_count"], 0)
                self.assertEqual(page.column_presence["analysis_count"], 1)
            finally:
                store.close()

    def test_report_binding_count_uses_one_set_valued_query(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE cells (active INTEGER, source_ref TEXT)")
        refs = [f"runs/default/agent/s{index}/c{index}" for index in range(1_205)]
        connection.executemany(
            "INSERT INTO cells (active, source_ref) VALUES (1, ?)",
            [(source_ref,) for source_ref in refs],
        )
        statements: list[str] = []
        connection.set_trace_callback(statements.append)

        self.assertEqual(
            _count_matching_source_refs(connection, "active = ?", [1], refs),
            len(refs),
        )
        selects = [
            statement
            for statement in statements
            if statement.lstrip().upper().startswith("SELECT")
        ]
        self.assertEqual(len(selects), 1)
        connection.close()

    def test_inference_summary_and_presence_cover_the_full_filtered_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self.write_cell(root, 1)
            second = self.write_cell(root, 2)
            self.write_cell(root, 3)
            self.write_inference_metrics(
                first,
                ttft_sum=100,
                ttft_count=1,
                decode_ms=100,
                decode_tokens=10,
                cache_prompt=100,
                cache_read=90,
            )
            self.write_inference_metrics(
                second,
                ttft_sum=900,
                ttft_count=9,
                decode_ms=900,
                decode_tokens=45,
                cache_prompt=900,
                cache_read=90,
            )
            store, catalog = self.catalog(root)
            catalog.reconcile()

            real_json_loads = json.loads
            with patch(
                "psycheval.state.catalog.json.loads", wraps=real_json_loads
            ) as loads:
                page = catalog.query(CatalogQuery(page_size=1), include_facets=False)

            self.assertEqual(page.total, 3)
            self.assertEqual(len(page.items), 1)
            self.assertEqual(loads.call_count, 1)
            self.assertFalse(hasattr(page, "matched_source_keys"))
            self.assertEqual(page.inference_summary["matched_trials"], 3)
            self.assertEqual(page.inference_summary["ttft"]["value_ms"], 100)
            self.assertEqual(page.inference_summary["ttft"]["covered_trials"], 2)
            self.assertEqual(page.inference_summary["tps"]["value"], 55)
            self.assertEqual(page.inference_summary["cache_hit_rate"]["value"], 0.18)
            self.assertEqual(page.column_presence["ttft_ms"], 2)
            self.assertEqual(page.column_presence["tps"], 2)
            self.assertEqual(page.column_presence["cache_hit_rate"], 2)
            linked = catalog.query(
                CatalogQuery(page_size=1),
                include_facets=False,
                workspace_report_source_refs=(page.items[0].payload["source_ref"],),
            )
            self.assertEqual(linked.column_presence["workspace_reports"], 1)

            sorted_page = catalog.query(
                CatalogQuery(sort="tps", direction="desc", page_size=3)
            )
            self.assertEqual(sorted_page.items[0].payload["trial_key"], "trial-0001")
            self.assertIsNone(sorted_page.items[-1].payload["tps"])
            store.close()

    def test_snapshot_rows_hold_one_generation_validate_selection_and_preserve_sort(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_cell(root, 1)
            self.write_cell(root, 2)
            store, catalog = self.catalog(root)
            catalog.reconcile()
            expected = [
                item.source_key
                for item in catalog.query(
                    CatalogQuery(sort="last_turn_end", direction="asc")
                ).items
            ]
            resolver_called = False

            def resolve_view_queries():
                nonlocal resolver_called
                resolver_called = True
                with self.assertRaisesRegex(CatalogBusyError, "writer operation"):
                    with catalog.workspace_write_guard():
                        pass
                return ()

            with catalog.read_snapshot_rows(
                CatalogQuery(sort="last_turn_end", direction="asc"),
                any_queries=resolve_view_queries,
            ) as (generation, rows):
                self.assertEqual(generation, catalog.generation)
                self.assertEqual([row["source_key"] for row in rows], expected)
                with self.assertRaisesRegex(CatalogBusyError, "writer operation"):
                    catalog.mutate(lambda: None)
                with self.assertRaisesRegex(CatalogBusyError, "writer operation"):
                    with catalog.workspace_write_guard():
                        pass
            self.assertTrue(resolver_called)

            with catalog.read_snapshot_rows(
                CatalogQuery(search="session-0001"),
                selected_source_keys=expected,
            ) as (_generation, rows):
                self.assertEqual(
                    [row["trial_session_id"] for row in rows], ["session-0001"]
                )

            with self.assertRaisesRegex(ValueError, "unknown source"):
                with catalog.read_snapshot_rows(
                    CatalogQuery(), selected_source_keys=["unknown"]
                ):
                    pass

            self.assertTrue(catalog._writer_lock.acquire(blocking=False))
            try:
                with self.assertRaisesRegex(CatalogBusyError, "writer operation"):
                    with catalog.read_snapshot_rows(CatalogQuery()):
                        pass
            finally:
                catalog._writer_lock.release()
            store.close()

    def test_background_reconcile_reports_lifecycle_contention_and_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, catalog = self.catalog(root)
            try:
                self.assertTrue(catalog._writer_lock.acquire(blocking=False))
                try:
                    with self.assertRaisesRegex(CatalogBusyError, "writer operation"):
                        catalog.mutate_with_background_reconcile(
                            "blocked", lambda: None
                        )
                finally:
                    catalog._writer_lock.release()

                entered = threading.Event()
                release = threading.Event()

                def reconcile() -> None:
                    entered.set()
                    self.assertTrue(release.wait(timeout=5))

                with patch.object(catalog, "_reconcile_locked", side_effect=reconcile):
                    result, status = catalog.mutate_with_background_reconcile(
                        "harbor-task-reconcile",
                        lambda: {"changed": True},
                    )
                    self.assertEqual(result, {"changed": True})
                    self.assertTrue(entered.wait(timeout=5))
                    running = catalog.operation(status.operation_id)
                    self.assertEqual(running.state, "running")
                    with self.assertRaisesRegex(CatalogBusyError, "writer operation"):
                        catalog.mutate(lambda: None)
                    release.set()
                    completed = self._wait_catalog_operation(
                        catalog, status.operation_id
                    )
                self.assertEqual(completed.state, "completed")
                self.assertEqual(completed.completed, 1)
                self.assertEqual(completed.failures, [])

                with patch.object(
                    catalog,
                    "_reconcile_locked",
                    side_effect=RuntimeError("reconcile failed"),
                ):
                    _result, failed_status = catalog.mutate_with_background_reconcile(
                        "harbor-task-reconcile",
                        lambda: None,
                    )
                    failed = self._wait_catalog_operation(
                        catalog, failed_status.operation_id
                    )
                self.assertEqual(failed.state, "failed")
                self.assertIn("reconcile failed", failed.failures[0]["error"])
            finally:
                store.close()

    def test_workspace_snapshot_limits_include_unique_bound_report_content(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_cell(root, 1)
            store, catalog = self.catalog(root)
            catalog.reconcile()
            rows = [item.to_dict() for item in catalog.query(CatalogQuery()).items]
            reports = WorkspaceReportLibrary(root, catalog.binding_rows)
            report_path = root / "bound.md"
            report_path.write_text("# Bound\n\n" + ("x" * 128), encoding="utf-8")
            reports.import_file(report_path, [rows[0]["source_key"]])
            views = WorkspaceViewLibrary(root)
            presentation = WorkspaceSnapshotPresentation(
                summary_group_by="agent",
                summary_statistic="mean",
                summary_table_open=False,
                selected_source_key=None,
                selected_step_id=None,
                leaderboard_columns={
                    "version": 1,
                    "order": [],
                    "visibility": {},
                },
                visible_view_names=(),
                workspace_view_filters={
                    "categories": (),
                    "tags": (),
                    "models": (),
                    "group_by": (),
                },
                open_view_tables=(),
            )
            import psycheval.serve.exports as export_module

            self.assertEqual(MAX_REPORT_EXPORT_CELLS, 100)
            with patch.object(export_module, "MAX_REPORT_EXPORT_CELLS", 0):
                with self.assertRaisesRegex(ValueError, "limited to 0 cells"):
                    build_workspace_snapshot_export(
                        catalog,
                        store,
                        views,
                        reports,
                        catalog.config,
                        query=CatalogQuery(),
                        query_view_names=(),
                        selected_source_keys=(),
                        presentation=presentation,
                        echarts_js=b"window.echarts={};",
                    )

            row_bytes = int(rows[0].get("input_bytes") or 0)
            report_bytes = report_path.stat().st_size
            with patch.object(
                export_module,
                "MAX_REPORT_EXPORT_INPUT_BYTES",
                row_bytes + report_bytes - 1,
            ):
                with self.assertRaisesRegex(ValueError, "report input exceeds"):
                    build_workspace_snapshot_export(
                        catalog,
                        store,
                        views,
                        reports,
                        catalog.config,
                        query=CatalogQuery(),
                        query_view_names=(),
                        selected_source_keys=(),
                        presentation=presentation,
                        echarts_js=b"window.echarts={};",
                    )

            snapshot = build_workspace_snapshot_export(
                catalog,
                store,
                views,
                reports,
                ToolConfig(
                    workspace_root=str(root),
                    description="**Nightly** workspace",
                ),
                query=CatalogQuery(),
                query_view_names=(),
                selected_source_keys=(),
                presentation=presentation,
                echarts_js=b"window.echarts={};",
            )
            snapshot_html = snapshot.content.decode("utf-8")
            self.assertIn(
                'class="workspace-description note-body" '
                "data-workspace-description hidden",
                snapshot_html,
            )
            self.assertIn(
                '"workspace_description": "**Nightly** workspace"', snapshot_html
            )
            self.assertEqual(MAX_REPORT_EXPORT_INPUT_BYTES, 50 * 1024 * 1024)
            store.close()

    def catalog(
        self, root: Path, *, slug: str = "default"
    ) -> tuple[object, WorkspaceCatalog]:
        (root / "peval.toml").write_text(
            f'analysis_eval_slug = "{slug}"\n', encoding="utf-8"
        )
        store = open_workspace_state(str(root))
        config = ToolConfig(workspace_root=str(root), analysis_eval_slug=slug)
        return store, WorkspaceCatalog(store, config)

    def _wait_catalog_operation(
        self,
        catalog: WorkspaceCatalog,
        operation_id: str,
    ):
        deadline = time.monotonic() + 5
        status = catalog.operation(operation_id)
        while status.state in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(0.01)
            status = catalog.operation(operation_id)
        self.assertNotIn(status.state, {"queued", "running"}, status.to_dict())
        return status

    def write_cell(
        self,
        root: Path,
        index: int,
        *,
        slug: str = "default",
        status: str = "passed",
        text: str | None = None,
    ) -> Path:
        session = f"session-{index:04d}"
        trial_key = f"trial-{index:04d}"
        cell = root / "runs" / slug / "psychevo" / session / trial_key
        write_trial_cell_artifacts(cell, session_id=session, trial_key=trial_key)
        meta_path = cell / "agent" / "trajectory_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["status"] = status
        meta["finished_at_ms"] = 1_000 + index
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        if text is not None:
            trajectory_path = cell / "agent" / "trajectory.json"
            trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
            trajectory["steps"][0]["message"] = text
            trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
        return cell

    def write_inference_metrics(
        self,
        cell: Path,
        *,
        ttft_sum: int,
        ttft_count: int,
        decode_ms: int,
        decode_tokens: int,
        cache_prompt: int,
        cache_read: int,
    ) -> None:
        trajectory_path = cell / "agent" / "trajectory.json"
        trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
        trajectory["final_metrics"] = {
            **trajectory.get("final_metrics", {}),
            "extra": {
                "model_inference": {
                    "schema_version": 1,
                    "ttft_ms_sum": ttft_sum,
                    "ttft_sample_count": ttft_count,
                    "decode_duration_ms": decode_ms,
                    "decode_token_count": decode_tokens,
                    "decode_sample_count": 1,
                    "cache_prompt_tokens": cache_prompt,
                    "cache_read_tokens": cache_read,
                    "cache_sample_count": 1,
                }
            },
        }
        trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")

    def test_cold_build_warm_zero_parse_change_delete_and_detail_reads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cells = [self.write_cell(root, index) for index in range(3)]
            store, catalog = self.catalog(root)
            import psycheval.state.workspace_sources as sources_module

            original_read = sources_module.read_json_object
            cold_reads: list[Path] = []

            def count_cold(path: Path):
                cold_reads.append(path)
                return original_read(path)

            with patch.object(
                sources_module, "read_json_object", side_effect=count_cold
            ):
                self.assertEqual(catalog.reconcile(), 1)
            self.assertEqual(len(cold_reads), 6)

            with patch.object(sources_module, "read_json_object") as warm_read:
                self.assertEqual(catalog.reconcile(), 2)
                warm_read.assert_not_called()

            changed_meta = cells[1] / "agent" / "trajectory_meta.json"
            payload = json.loads(changed_meta.read_text(encoding="utf-8"))
            payload["status"] = "failed"
            changed_meta.write_text(json.dumps(payload) + " ", encoding="utf-8")
            changed_reads: list[Path] = []

            def count_changed(path: Path):
                changed_reads.append(path)
                return original_read(path)

            with patch.object(
                sources_module, "read_json_object", side_effect=count_changed
            ):
                catalog.reconcile()
            self.assertEqual(len(changed_reads), 2)

            shutil.rmtree(cells[2])
            catalog.reconcile()
            page = catalog.query(CatalogQuery())
            self.assertEqual(page.total, 2)
            target = page.items[0].source_key
            detail_reads: list[Path] = []
            import psycheval.state.artifacts as artifacts_module

            original_artifact_read = artifacts_module.read_json_object

            def count_detail(path: Path):
                detail_reads.append(path)
                return original_artifact_read(path)

            with patch.object(
                artifacts_module, "read_json_object", side_effect=count_detail
            ):
                detail = catalog.load_detail(target)
            self.assertEqual(detail.source_key, target)
            self.assertEqual(len(detail_reads), 2)
            store.close()

    def test_fixed_slug_symlink_exclusion_and_parse_error_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = self.write_cell(root, 1, slug="chosen")
            self.write_cell(root, 2, slug="other")
            broken = root / "runs" / "chosen" / "psychevo" / "broken" / "broken_t001"
            write_trial_cell_artifacts(
                broken, session_id="broken", trial_key="broken_t001"
            )
            (broken / "agent" / "trajectory.json").write_text("{", encoding="utf-8")
            link = root / "runs" / "chosen" / "linked-agent"
            try:
                os.symlink(good.parent.parent, link, target_is_directory=True)
            except OSError:
                link = None
            store, catalog = self.catalog(root, slug="chosen")
            catalog.reconcile()
            source_page = catalog.query(
                CatalogQuery(state="all", include_unreadable=True)
            )
            self.assertEqual(source_page.total, 2)
            self.assertEqual(
                len(
                    [item for item in source_page.items if item.payload.get("readable")]
                ),
                1,
            )
            leaderboard = catalog.query(CatalogQuery(state="all"))
            self.assertEqual(leaderboard.total, 1)
            self.assertEqual(
                leaderboard.items[0].payload["artifact_dir"],
                good.relative_to(root).as_posix(),
            )
            if link is not None:
                self.assertNotIn("linked-agent", json.dumps(source_page.to_dict()))
            store.close()

    def test_catalog_projects_measured_model_duration_for_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cell = self.write_cell(root, 1)
            trajectory_path = cell / "agent" / "trajectory.json"
            trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
            trajectory["agent"]["model_name"] = "shared-model"
            trajectory["steps"].extend(
                [
                    {"step_id": 3, "source": "agent", "message": "estimated"},
                    {"step_id": 4, "source": "user", "message": "tool"},
                ]
            )
            trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
            meta_path = cell / "agent" / "trajectory_meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["steps"][0]["duration_ms"] = 100
            meta["steps"][1]["duration_ms"] = 250
            meta["steps"][1]["duration_source"] = "measured"
            meta["steps"].extend(
                [
                    {
                        "step_id": 3,
                        "duration_ms": 800,
                        "duration_source": "boundary_estimate",
                    },
                    {"step_id": 4, "duration_ms": 400},
                ]
            )
            meta_path.write_text(json.dumps(meta), encoding="utf-8")

            store, catalog = self.catalog(root)
            catalog.reconcile()
            payload = catalog.query(CatalogQuery()).items[0].payload

            self.assertEqual(payload["model"], "shared-model")
            self.assertEqual(payload["model_duration_ms"], 1_050)
            store.close()

    def test_catalog_projects_compact_step_outline_without_step_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cell = self.write_cell(root, 1)
            trajectory_path = cell / "agent" / "trajectory.json"
            trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
            trajectory["steps"] = [
                {
                    "step_id": 1,
                    "source": "user",
                    "message": "must not enter the catalog",
                },
                {
                    "step_id": 2,
                    "source": "agent",
                    "message": "must not enter either",
                    "tool_calls": [
                        {
                            "tool_call_id": "call-secret",
                            "function_name": "secret",
                            "arguments": {"token": "secret"},
                        }
                    ],
                },
            ]
            trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
            meta_path = cell / "agent" / "trajectory_meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["steps"] = [
                {"step_id": 1, "duration_ms": 125},
                {"step_id": 2, "duration_ms": 250},
            ]
            meta_path.write_text(json.dumps(meta), encoding="utf-8")

            store, catalog = self.catalog(root)
            catalog.reconcile()
            payload = catalog.query(CatalogQuery()).items[0].payload

            self.assertEqual(
                payload["step_outline"],
                [
                    {"step_id": 1, "source": "user", "duration_ms": 125},
                    {"step_id": 2, "source": "agent", "duration_ms": 250},
                ],
            )
            self.assertNotIn("must not enter", json.dumps(payload))
            self.assertNotIn("private reasoning", json.dumps(payload))
            self.assertNotIn("secret", json.dumps(payload))
            store.close()

    def test_paging_facets_literal_search_short_search_and_key_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(125):
                cell = self.write_cell(
                    root,
                    index,
                    status="failed" if index % 10 == 0 else "passed",
                    text="中文检索 needle" if index == 42 else f"message {index}",
                )
                if index % 2 == 0:
                    state_path = cell / ".peval" / "state.json"
                    state_path.parent.mkdir(parents=True, exist_ok=True)
                    state_path.write_text(
                        json.dumps(
                            {
                                "source_category": "even-category",
                                "source_tags": ["even"],
                            }
                        ),
                        encoding="utf-8",
                    )
            store, catalog = self.catalog(root)
            catalog.reconcile()
            first = catalog.query(CatalogQuery(page=1))
            second = catalog.query(CatalogQuery(page=2))
            self.assertEqual(len(first.items), 100)
            self.assertEqual(len(second.items), 25)
            self.assertEqual(first.total, 125)
            self.assertTrue(
                set(item.source_key for item in first.items).isdisjoint(
                    item.source_key for item in second.items
                )
            )
            self.assertEqual(catalog.query(CatalogQuery(search="中文检索")).total, 1)
            self.assertEqual(catalog.query(CatalogQuery(search="42")).total, 1)
            self.assertEqual(catalog.query(CatalogQuery(search="%")).total, 0)
            self.assertEqual(catalog.query(CatalogQuery(search="_")).total, 0)
            self.assertEqual(
                catalog.query(CatalogQuery(categories=("even-category",))).total,
                63,
            )
            self.assertEqual(catalog.query(CatalogQuery(tags=("even",))).total, 63)
            self.assertEqual(
                next(
                    item["count"]
                    for item in first.facets["results"]
                    if item["value"] == "failed"
                ),
                13,
            )
            selected = [
                first.items[0].source_key,
                second.items[-1].source_key,
                "missing",
            ]
            self.assertEqual(catalog.resolve_keys(selected), selected[:2])
            store.close()

    def test_facets_cover_complete_readable_current_source_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            definitions = [
                (0, "alpha", "shared", "passed", "needle active", True),
                (1, "beta", "secondary", "failed", "other active", True),
                (2, "archived", "archive-category", "passed", "other archived", False),
                (3, "ghost", "ghost-category", "passed", "unreadable", True),
            ]
            for index, tag, category, status, text, active in definitions:
                cell = self.write_cell(root, index, status=status, text=text)
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
                if tag == "ghost":
                    (cell / "agent" / "trajectory.json").write_text(
                        "{", encoding="utf-8"
                    )

            store, catalog = self.catalog(root)
            try:
                catalog.reconcile()
                active = catalog.query(
                    CatalogQuery(
                        search="needle",
                        categories=("shared",),
                        tags=("alpha",),
                        results=("passed",),
                    )
                )
                self.assertEqual(active.total, 1)
                self.assertEqual(
                    {
                        item["value"]: item["count"]
                        for item in active.facets["categories"]
                    },
                    {"secondary": 1, "shared": 1},
                )
                self.assertEqual(
                    {item["value"]: item["count"] for item in active.facets["tags"]},
                    {"alpha": 1, "beta": 1},
                )
                self.assertEqual(
                    {item["value"]: item["count"] for item in active.facets["results"]},
                    {"failed": 1, "passed": 1},
                )

                archived = catalog.query(
                    CatalogQuery(
                        state="archived",
                        categories=("archive-category",),
                        tags=("archived",),
                    )
                )
                self.assertEqual(archived.total, 1)
                self.assertEqual(
                    [item["value"] for item in archived.facets["tags"]],
                    ["archived"],
                )
                self.assertEqual(
                    [item["value"] for item in archived.facets["categories"]],
                    ["archive-category"],
                )

                all_states = catalog.query(
                    CatalogQuery(
                        state="all",
                        search="needle",
                        categories=("shared", "secondary"),
                        tags=("alpha",),
                    )
                )
                self.assertEqual(all_states.total, 1)
                self.assertEqual(
                    {item["value"] for item in all_states.facets["tags"]},
                    {"alpha", "beta", "archived"},
                )
                self.assertNotIn(
                    "ghost", {item["value"] for item in all_states.facets["tags"]}
                )
                self.assertEqual(
                    {item["value"] for item in all_states.facets["categories"]},
                    {"shared", "secondary", "archive-category"},
                )
                self.assertEqual(
                    catalog.query(
                        CatalogQuery(categories=("shared", "secondary"))
                    ).total,
                    2,
                )
                self.assertEqual(catalog.query(CatalogQuery(search="shared")).total, 1)
            finally:
                store.close()

    def test_saved_view_summaries_cover_entire_matching_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(125):
                cell = self.write_cell(root, index)
                trajectory_path = cell / "agent" / "trajectory.json"
                trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
                trajectory["agent"]["model_name"] = (
                    "model-a" if index % 4 else "model-b"
                )
                trajectory_path.write_text(json.dumps(trajectory), encoding="utf-8")
                meta_path = cell / "agent" / "trajectory_meta.json"
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["duration_ms"] = index
                meta_path.write_text(json.dumps(meta), encoding="utf-8")
                if index % 2 == 0 or index == 1:
                    state_path = cell / ".peval" / "state.json"
                    state_path.parent.mkdir(parents=True, exist_ok=True)
                    state_path.write_text(
                        json.dumps(
                            {
                                "source_category": (
                                    "even-category" if index % 2 == 0 else "-"
                                ),
                                "source_tags": ["even"] if index % 2 == 0 else [],
                            }
                        ),
                        encoding="utf-8",
                    )

            store, catalog = self.catalog(root)
            try:
                catalog.reconcile()
                self.assertEqual(len(catalog.query(CatalogQuery()).items), 100)
                payload = catalog.summarize_saved_views(
                    [
                        ("all", CatalogQuery(), "overall"),
                        ("even", CatalogQuery(tags=("even",)), "model"),
                        ("category", CatalogQuery(), "category"),
                    ]
                )
                all_view, even_view, category_view = payload["views"]
                self.assertEqual(all_view["matched_count"], 125)
                self.assertEqual(all_view["groups"][0]["count"], 125)
                duration = all_view["groups"][0]["metrics"][0]
                self.assertEqual(duration["count"], 125)
                self.assertEqual(duration["mean"], 62)
                self.assertEqual(duration["distribution"]["p50"], 62)
                self.assertEqual(even_view["matched_count"], 63)
                self.assertEqual(
                    [(group["label"], group["count"]) for group in even_view["groups"]],
                    [("model-a", 31), ("model-b", 32)],
                )
                self.assertEqual(
                    [
                        (group["key"], group["label"], group["count"])
                        for group in category_view["groups"]
                    ],
                    [
                        (None, "-", 61),
                        ("-", "-", 1),
                        ("even-category", "even-category", 63),
                    ],
                )
            finally:
                store.close()

    def test_saved_view_queries_or_full_predicates_then_apply_and_refinement(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            definitions = [
                (0, "red", "passed", "needle zero", True),
                (1, "red", "failed", "other one", True),
                (2, "blue", "passed", "needle two", False),
                (3, "green", "passed", "needle three", True),
            ]
            for index, tag, status, text, active in definitions:
                cell = self.write_cell(root, index, status=status, text=text)
                state_path = cell / ".peval" / "state.json"
                state_path.parent.mkdir(parents=True, exist_ok=True)
                state_path.write_text(
                    json.dumps({"active": active, "source_tags": [tag]}),
                    encoding="utf-8",
                )

            store, catalog = self.catalog(root)
            try:
                catalog.reconcile()
                view_queries = [
                    CatalogQuery(state="active", tags=("red",)),
                    CatalogQuery(state="all", search="needle"),
                ]
                union = catalog.query(
                    CatalogQuery(state="all", sort="last_turn_end", direction="asc"),
                    any_queries=view_queries,
                )
                self.assertEqual(union.total, 4)
                self.assertEqual(len({item.source_key for item in union.items}), 4)
                self.assertEqual(
                    {item["value"]: item["count"] for item in union.facets["tags"]},
                    {"red": 2, "blue": 1, "green": 1},
                )

                refined = catalog.query(
                    CatalogQuery(
                        state="all",
                        sort="last_turn_end",
                        direction="asc",
                        results=("passed",),
                    ),
                    any_queries=view_queries,
                )
                self.assertEqual(refined.total, 3)
                self.assertEqual(
                    [item.payload["session_id"] for item in refined.items],
                    ["session-0000", "session-0002", "session-0003"],
                )

                exported = build_serve_export(
                    catalog,
                    store,
                    catalog.config,
                    kind="xlsx",
                    query=CatalogQuery(state="all", results=("passed",)),
                    view_queries=view_queries,
                )
                with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
                    worksheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
                self.assertEqual(worksheet.count("<row "), 4)
                self.assertLess(worksheet.index("Category"), worksheet.index("Tags"))
                self.assertIn("#Analysis", worksheet)
                self.assertIn("Decode Samples", worksheet)
                self.assertIn("Cache Samples", worksheet)
            finally:
                store.close()

    def test_corrupt_and_version_mismatched_cache_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_cell(root, 1)
            store, catalog = self.catalog(root)
            catalog.reconcile()
            cache_path = catalog.path
            with catalog._connect(readonly=True) as connection:
                columns = {
                    str(row["name"])
                    for row in connection.execute("PRAGMA table_info(cells)")
                }
                indexes = {
                    str(row["name"])
                    for row in connection.execute("PRAGMA index_list(cells)")
                }
                self.assertEqual(
                    catalog._meta_int(connection, "schema_version", -1),
                    CATALOG_SCHEMA_VERSION,
                )
            self.assertIn("category", columns)
            self.assertIn("cells_category", indexes)
            cache_path.write_bytes(b"not sqlite")
            rebuilt = WorkspaceCatalog(catalog.store, catalog.config)
            self.assertFalse(rebuilt.has_generation)
            rebuilt.reconcile()
            self.assertEqual(rebuilt.query(CatalogQuery()).total, 1)
            with rebuilt._connect() as connection:
                rebuilt._set_meta(
                    connection, "schema_version", str(CATALOG_SCHEMA_VERSION - 1)
                )
                connection.commit()
            version_rebuilt = WorkspaceCatalog(catalog.store, catalog.config)
            self.assertFalse(version_rebuilt.has_generation)
            version_rebuilt.reconcile()
            self.assertEqual(version_rebuilt.query(CatalogQuery()).total, 1)
            store.close()

    def test_next_generation_is_not_visible_until_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_cell(root, 1)
            store, catalog = self.catalog(root)
            catalog.reconcile()
            self.write_cell(root, 2)
            entered = threading.Event()
            release = threading.Event()
            original_parse = catalog._row_for_document

            def blocked_parse(document):
                if document.source_ref.endswith("/trial-0002"):
                    entered.set()
                    release.wait(timeout=5)
                return original_parse(document)

            with patch.object(catalog, "_row_for_document", side_effect=blocked_parse):
                thread = threading.Thread(target=catalog.reconcile)
                thread.start()
                self.assertTrue(entered.wait(timeout=5))
                stale = catalog.query(CatalogQuery())
                self.assertEqual(stale.generation, 1)
                self.assertEqual(stale.total, 1)
                self.assertTrue(stale.checking)
                release.set()
                thread.join(timeout=5)
            fresh = catalog.query(CatalogQuery())
            self.assertEqual(fresh.generation, 2)
            self.assertEqual(fresh.total, 2)
            store.close()

    def test_json_export_limits_are_checked_before_report_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(101):
                self.write_cell(root, index)
            store, catalog = self.catalog(root)
            catalog.reconcile()
            first_page = catalog.query(CatalogQuery(page=1))
            second_page = catalog.query(CatalogQuery(page=2))
            hundred_keys = [item.source_key for item in first_page.items]
            export = build_serve_export(
                catalog,
                store,
                catalog.config,
                kind="json",
                source_keys=hundred_keys,
            )
            self.assertEqual(
                len(json.loads(export.content)["trajectory"]),
                100,
            )
            with patch.object(store, "report_for_rows") as report_builder:
                with self.assertRaisesRegex(ValueError, "limited to 100"):
                    build_serve_export(
                        catalog,
                        store,
                        catalog.config,
                        kind="json",
                        source_keys=[*hundred_keys, second_page.items[0].source_key],
                    )
                report_builder.assert_not_called()

            source_key = first_page.items[0].source_key
            with catalog._connect() as connection:
                record = connection.execute(
                    "SELECT row_json FROM cells WHERE source_key = ?", (source_key,)
                ).fetchone()
                row = json.loads(record[0])
                row["input_bytes"] = MAX_REPORT_EXPORT_INPUT_BYTES
                connection.execute(
                    "UPDATE cells SET row_json = ? WHERE source_key = ?",
                    (json.dumps(row), source_key),
                )
                connection.commit()
            exact = build_serve_export(
                catalog,
                store,
                catalog.config,
                kind="json",
                source_keys=[source_key],
            )
            self.assertEqual(len(json.loads(exact.content)["trajectory"]), 1)
            row["input_bytes"] = MAX_REPORT_EXPORT_INPUT_BYTES + 1
            with catalog._connect() as connection:
                connection.execute(
                    "UPDATE cells SET row_json = ? WHERE source_key = ?",
                    (json.dumps(row), source_key),
                )
                connection.commit()
            with patch.object(store, "report_for_rows") as report_builder:
                with self.assertRaisesRegex(ValueError, "exceeds 50 MiB"):
                    build_serve_export(
                        catalog,
                        store,
                        catalog.config,
                        kind="json",
                        source_keys=[source_key],
                    )
                report_builder.assert_not_called()
            store.close()


if __name__ == "__main__":
    unittest.main()
