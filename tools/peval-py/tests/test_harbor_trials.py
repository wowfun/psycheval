from __future__ import annotations

import http.client
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from peval_py.config import ToolConfig, load_config
from peval_py.serve import LocalHTTPServer, ServeRuntime, make_handler
from peval_py.serve.errors import HttpError
from peval_py.serve.handler import reject_linked_harbor_delete
from peval_py.state import CatalogQuery, WorkspaceCatalog, open_workspace_state
from peval_py.state.harbor import discover_harbor_trials


def atif_trajectory(session_id: str = "harbor-session") -> dict[str, object]:
    return {
        "schema_version": "ATIF-v1.7",
        "trajectory_id": f"opencode:{session_id}",
        "session_id": session_id,
        "agent": {
            "name": "opencode",
            "version": "1.0.0",
            "model_name": "test-model",
        },
        "steps": [
            {
                "step_id": 1,
                "source": "user",
                "message": "search the web",
                "timestamp": "2026-08-08T01:00:00Z",
            },
            {
                "step_id": 2,
                "source": "agent",
                "message": "done",
                "timestamp": "2026-08-08T01:00:01Z",
                "llm_call_count": 1,
            },
        ],
        "final_metrics": {
            "total_steps": 2,
            "extra": {
                "total_turns": 1,
                "total_tool_calls": 0,
                "total_tool_errors": 0,
            },
        },
    }


def write_trial(
    trial_dir: Path,
    *,
    trajectory: dict[str, object] | str | None = None,
    result: dict[str, object] | None = None,
) -> None:
    agent_dir = trial_dir / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    value = atif_trajectory() if trajectory is None else trajectory
    (agent_dir / "trajectory.json").write_text(
        value if isinstance(value, str) else json.dumps(value),
        encoding="utf-8",
    )
    (trial_dir / "config.json").write_text(
        json.dumps(
            {
                "trial_name": trial_dir.name,
                "job_id": "job-123",
                "task": {"name": "web-search"},
                "agent": {"name": "opencode", "model_name": "test-model"},
            }
        ),
        encoding="utf-8",
    )
    if result is not None:
        (trial_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")


class HarborTrialTests(unittest.TestCase):
    def workspace(self, root: Path, *, harbor_roots: tuple[str, ...] = ()):
        root.mkdir(parents=True, exist_ok=True)
        (root / "peval-py.toml").write_text(
            'analysis_eval_slug = "default"\n', encoding="utf-8"
        )
        config = ToolConfig(
            workspace_root=str(root),
            analysis_eval_slug="default",
            harbor_roots=harbor_roots,
        )
        store = open_workspace_state(str(root))
        return store, config, WorkspaceCatalog(store, config)

    def test_config_and_bounded_discovery_cover_trial_job_jobs_and_custom_roots(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            external = Path(tmp) / "external-jobs"
            trial = root / "jobs" / "job-a" / "trial-a"
            external_trial = external / "job-b" / "trial-b"
            write_trial(trial)
            write_trial(external_trial)
            root.mkdir(parents=True, exist_ok=True)
            (root / "peval-py.toml").write_text(
                '[harbor]\nroots = ["../external-jobs"]\n', encoding="utf-8"
            )
            config = load_config(None, workspace_root=str(root))
            self.assertEqual(config.harbor_roots, (str(external.resolve()),))

            discovered = discover_harbor_trials(root, config.harbor_roots)
            self.assertEqual(
                {item.trial_dir for item in discovered.trials},
                {trial.resolve(), external_trial.resolve()},
            )
            self.assertEqual(len({item.source_key for item in discovered.trials}), 2)

            linked = root / "jobs" / "job-a" / "linked"
            try:
                os.symlink(external_trial, linked, target_is_directory=True)
            except OSError:
                pass
            rediscovered = discover_harbor_trials(root, config.harbor_roots)
            self.assertEqual(len(rediscovered.trials), 2)

    def test_configured_root_symlink_is_rejected_before_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            external = Path(tmp) / "external-jobs"
            write_trial(external / "job-a" / "trial-a")
            linked_root = Path(tmp) / "linked-jobs"
            try:
                os.symlink(external, linked_root, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")
            root.mkdir()
            (root / "peval-py.toml").write_text(
                '[harbor]\nroots = ["../linked-jobs"]\n', encoding="utf-8"
            )

            config = load_config(None, workspace_root=str(root))
            self.assertEqual(config.harbor_roots, (str(linked_root.absolute()),))
            discovery = discover_harbor_trials(root, config.harbor_roots)
            self.assertEqual(discovery.trials, ())
            self.assertEqual(discovery.missing_roots, (str(linked_root.absolute()),))

    def test_windows_mapped_configured_root_keeps_symlink_for_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "workspace"
            external = base / "external-jobs"
            write_trial(external / "job-a" / "trial-a")
            mount_root = base / "mnt"
            linked_root = mount_root / "c" / "jobs"
            linked_root.parent.mkdir(parents=True)
            try:
                os.symlink(external, linked_root, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")
            root.mkdir()
            (root / "peval-py.toml").write_text(
                "[harbor]\nroots = ['C:\\\\jobs']\n", encoding="utf-8"
            )

            with patch("peval_py.config.WINDOWS_DRIVE_MOUNT_ROOT", mount_root):
                config = load_config(None, workspace_root=str(root))

            self.assertEqual(config.harbor_roots, (str(linked_root.absolute()),))
            discovery = discover_harbor_trials(root, config.harbor_roots)
            self.assertEqual(discovery.trials, ())
            self.assertEqual(discovery.missing_roots, (str(linked_root.absolute()),))

    def test_missing_configured_root_is_a_catalog_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            missing_root = Path(tmp) / "missing-jobs"
            store, config, catalog = self.workspace(
                root, harbor_roots=(str(missing_root),)
            )
            try:
                keys = store.sync_harbor_trials(config)
                self.assertEqual(len(keys), 1)
                catalog.reconcile()
                page = catalog.query(CatalogQuery(state="all", include_unreadable=True))
                self.assertEqual(page.total, 1)
                row = page.items[0].to_dict()
                self.assertEqual(row["kind"], "harbor-root")
                self.assertFalse(row["readable"])
                self.assertEqual(row["last_status"], "missing")
                self.assertIn(str(missing_root), row["last_error"])

                missing_root.mkdir()
                self.assertEqual(store.sync_harbor_trials(config), [])
                catalog.reconcile()
                recovered = catalog.query(
                    CatalogQuery(state="all", include_unreadable=True)
                )
                self.assertEqual(recovered.total, 0)
            finally:
                store.close()

    def test_running_trial_projects_then_completes_with_stable_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trial = root / "jobs" / "job-a" / "trial-a"
            trajectory = atif_trajectory()
            trajectory["steps"][1]["tool_calls"] = [
                {
                    "tool_call_id": "call-1",
                    "function_name": "web_search",
                    "arguments": {"query": "example domains"},
                }
            ]
            trajectory["steps"][1]["observation"] = {
                "results": [
                    {
                        "source_call_id": "call-1",
                        "content": "example.com",
                        "extra": {
                            "status": "completed",
                            "is_error": False,
                            "finished_at": "2026-08-08T01:00:01.500Z",
                        },
                    }
                ]
            }
            trajectory["final_metrics"]["extra"]["total_tool_calls"] = 1
            write_trial(trial, trajectory=trajectory)
            source_files_before = {
                path.relative_to(trial).as_posix(): path.read_bytes()
                for path in trial.rglob("*")
                if path.is_file()
            }
            store, config, catalog = self.workspace(root)
            try:
                keys = store.sync_harbor_trials(config)
                self.assertEqual(len(keys), 1)
                first_key = keys[0]
                catalog.reconcile()
                row = catalog.row_for_key(first_key)
                self.assertEqual(row["kind"], "harbor-trial")
                self.assertTrue(row["refreshable"])
                self.assertFalse(row["snapshot"])
                self.assertEqual(row["status"], "running")

                cell = root / row["artifact_dir"]
                copied = json.loads(
                    (cell / "agent" / "trajectory.json").read_text(encoding="utf-8")
                )
                self.assertEqual(copied, trajectory)
                meta = json.loads(
                    (cell / "agent" / "trajectory_meta.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(meta["data_ref"]["kind"], "harbor-trial")
                self.assertEqual(meta["evaluation"]["status"], "running")
                self.assertEqual(len(meta["steps"]), len(trajectory["steps"]))
                self.assertEqual(meta["steps"][1]["timestamp_ms"], 1_786_150_801_000)
                self.assertEqual(
                    meta["steps"][1]["observations"][0]["status"], "completed"
                )

                store.set_source_alias_row(row, "Mounted Trial")
                (cell / "notes.md").write_text("keep me", encoding="utf-8")
                result = {
                    "id": "result-456",
                    "trial_name": "trial-a",
                    "task_name": "web-search",
                    "started_at": "2026-08-08T01:00:00Z",
                    "finished_at": "2026-08-08T01:00:02Z",
                    "verifier_result": {"rewards": {"quality": 0.75}},
                }
                (trial / "result.json").write_text(json.dumps(result), encoding="utf-8")
                self.assertEqual(store.sync_harbor_trials(config), [first_key])
                catalog.reconcile()
                completed = catalog.row_for_key(first_key)
                self.assertEqual(completed["source_alias"], "Mounted Trial")
                self.assertEqual(completed["status"], "completed")
                self.assertEqual(
                    (cell / "notes.md").read_text(encoding="utf-8"), "keep me"
                )
                completed_meta = json.loads(
                    (cell / "agent" / "trajectory_meta.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(completed_meta["score"], 0.75)
                self.assertEqual(
                    completed_meta["evaluation"]["rewards"], {"quality": 0.75}
                )
                self.assertEqual(
                    source_files_before,
                    {
                        path.relative_to(trial).as_posix(): path.read_bytes()
                        for path in trial.rglob("*")
                        if path.is_file() and path.name != "result.json"
                    },
                )
                with self.assertRaisesRegex(ValueError, "cannot be deleted"):
                    store.delete_source_row(completed)
                with self.assertRaisesRegex(HttpError, "cannot be deleted"):
                    reject_linked_harbor_delete([completed])
            finally:
                store.close()

    def test_invalid_refresh_and_missing_source_preserve_last_good_projection(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trial = root / "jobs" / "job-a" / "trial-a"
            write_trial(trial)
            store, config, catalog = self.workspace(root)
            try:
                source_key = store.sync_harbor_trials(config)[0]
                catalog.reconcile()
                row = catalog.row_for_key(source_key)
                cell = root / row["artifact_dir"]
                last_good = (cell / "agent" / "trajectory.json").read_bytes()

                (trial / "agent" / "trajectory.json").write_text("{", encoding="utf-8")
                store.sync_harbor_trials(config)
                catalog.reconcile()
                stale = catalog.row_for_key(source_key)
                self.assertTrue(stale["readable"])
                self.assertEqual(stale["last_status"], "error")
                self.assertIn("failed to parse", stale["last_error"])
                self.assertEqual(
                    (cell / "agent" / "trajectory.json").read_bytes(), last_good
                )

                shutil.rmtree(trial)
                store.sync_harbor_trials(config)
                catalog.reconcile()
                missing = catalog.row_for_key(source_key)
                self.assertTrue(missing["readable"])
                self.assertEqual(missing["last_status"], "missing")
                self.assertEqual(
                    (cell / "agent" / "trajectory.json").read_bytes(), last_good
                )
            finally:
                store.close()

    def test_signature_cache_rebuilds_a_missing_local_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trial = root / "jobs" / "job-a" / "trial-a"
            write_trial(trial)
            store, config, catalog = self.workspace(root)
            try:
                source_key = store.sync_harbor_trials(config)[0]
                catalog.reconcile()
                row = catalog.row_for_key(source_key)
                trajectory_path = root / row["artifact_dir"] / "agent/trajectory.json"
                trajectory_path.unlink()

                self.assertEqual(store.sync_harbor_trials(config), [source_key])
                self.assertTrue(trajectory_path.is_file())
                self.assertEqual(
                    json.loads(trajectory_path.read_text(encoding="utf-8")),
                    atif_trajectory(),
                )
            finally:
                store.close()

    def test_linked_cell_cannot_rewrite_an_external_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "workspace"
            trial = root / "jobs" / "job-a" / "trial-a"
            write_trial(trial)
            store, config, catalog = self.workspace(root)
            try:
                source_key = store.sync_harbor_trials(config)[0]
                catalog.reconcile()
                row = catalog.row_for_key(source_key)
                cell = root / row["artifact_dir"]
                external_cell = base / "external-cell"
                shutil.move(cell, external_cell)
                try:
                    os.symlink(external_cell, cell, target_is_directory=True)
                except OSError as exc:
                    self.skipTest(f"directory symlinks unavailable: {exc}")
                manifest = external_cell / ".peval/harbor-link.json"
                before = manifest.read_bytes()
                shutil.rmtree(trial)

                store.sync_harbor_trials(config)

                self.assertEqual(manifest.read_bytes(), before)
            finally:
                store.close()

    def test_first_invalid_and_multi_step_trials_are_explicit_unreadable_rows(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_trial(root / "jobs" / "job-a" / "invalid", trajectory="{")
            step_agent = root / "jobs" / "job-a" / "multi" / "steps" / "one" / "agent"
            step_agent.mkdir(parents=True)
            (step_agent / "trajectory.json").write_text(
                json.dumps(atif_trajectory("step-session")), encoding="utf-8"
            )
            store, config, catalog = self.workspace(root)
            try:
                keys = store.sync_harbor_trials(config)
                self.assertEqual(len(keys), 2)
                catalog.reconcile()
                page = catalog.query(CatalogQuery(state="all", include_unreadable=True))
                self.assertEqual(page.total, 2)
                rows = {row.payload["label"]: row.to_dict() for row in page.items}
                invalid = next(
                    row for label, row in rows.items() if label.endswith("invalid")
                )
                multi = next(
                    row for label, row in rows.items() if label.endswith("multi")
                )
                self.assertFalse(invalid["readable"])
                self.assertEqual(invalid["last_status"], "error")
                self.assertIn("failed to parse", invalid["last_error"])
                self.assertFalse(multi["readable"])
                self.assertEqual(multi["last_status"], "unsupported")
                self.assertIn("multi-step", multi["last_error"])
            finally:
                store.close()

    def test_http_reload_updates_linked_trial_and_delete_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trial = root / "jobs" / "job-a" / "trial-a"
            write_trial(trial)
            store, config, _catalog = self.workspace(root)
            runtime = ServeRuntime(store, config)
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                page = self.http_json(
                    server.server_port, "GET", "/api/catalog?state=all"
                )
                source_key = page["items"][0]["source_key"]
                result = {
                    "id": "result-789",
                    "trial_name": "trial-a",
                    "task_name": "web-search",
                    "verifier_result": {"rewards": {"reward": 1}},
                }
                (trial / "result.json").write_text(json.dumps(result), encoding="utf-8")
                operation = self.http_json(
                    server.server_port,
                    "POST",
                    "/api/sources/reload",
                    {},
                )
                terminal = self.wait_operation(
                    server.server_port, operation["operation_id"]
                )
                self.assertEqual(terminal["state"], "completed")
                refreshed = self.http_json(
                    server.server_port, "GET", "/api/catalog?state=all"
                )
                self.assertEqual(refreshed["items"][0]["source_key"], source_key)
                self.assertEqual(refreshed["items"][0]["status"], "completed")

                for active in (False, True):
                    state_operation = self.http_json(
                        server.server_port,
                        "POST",
                        "/api/sources/state",
                        {"source_keys": [source_key], "active": active},
                    )
                    state_terminal = self.wait_operation(
                        server.server_port, state_operation["operation_id"]
                    )
                    self.assertEqual(state_terminal["state"], "completed")

                status, rejected = self.http_json_response(
                    server.server_port,
                    "POST",
                    "/api/sources/delete",
                    {"source_keys": [source_key]},
                )
                self.assertEqual(status, 400)
                self.assertIn("cannot be deleted", rejected["error"])

                status, rejected = self.http_json_response(
                    server.server_port,
                    "POST",
                    f"/api/sources/{source_key}/delete",
                    {},
                )
                self.assertEqual(status, 400)
                self.assertIn("cannot be deleted", rejected["error"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def http_json(
        self,
        port: int,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        status, body = self.http_json_response(port, method, path, payload)
        self.assertIn(status, {200, 202}, body)
        return body

    def http_json_response(
        self,
        port: int,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> tuple[int, dict[str, object]]:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        body = json.dumps(payload) if payload is not None else None
        headers = (
            {
                "Content-Type": "application/json",
                "Origin": f"http://127.0.0.1:{port}",
            }
            if body is not None
            else {}
        )
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        parsed = json.loads(response.read().decode("utf-8"))
        status = response.status
        connection.close()
        return status, parsed

    def wait_operation(self, port: int, operation_id: object) -> dict[str, object]:
        for _attempt in range(500):
            result = self.http_json(port, "GET", f"/api/operations/{operation_id}")
            if result.get("state") not in {"queued", "running"}:
                return result
            time.sleep(0.01)
        self.fail(f"operation did not complete: {operation_id}")


if __name__ == "__main__":
    unittest.main()
