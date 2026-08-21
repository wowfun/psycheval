from __future__ import annotations

import http.client
import json
import os
import tempfile
import threading
import time
import unittest
from base64 import b64encode
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from harbor.models.dataset.manifest import DatasetManifest
from peval_py.config import HarborDataset, HarborMount, ToolConfig, apply_toml_config
from peval_py.serve import LocalHTTPServer, ServeAccess, ServeRuntime, make_handler
from peval_py.serve.harbor_workspace import (
    HarborConflictError,
    HarborSizeError,
    HarborWorkspace,
    HarborWorkspaceError,
    _read_regular_file,
    config_revision,
)
from peval_py.state import open_workspace_state
from peval_py.state.harbor_evidence import read_harbor_task_index


class HarborWorkspaceTests(unittest.TestCase):
    @staticmethod
    def _request(
        server: LocalHTTPServer,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> tuple[int, dict[str, object]]:
        raw = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = (
            {
                "Content-Type": "application/json",
                "Origin": f"http://127.0.0.1:{server.server_port}",
            }
            if raw is not None
            else {}
        )
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_port, timeout=5
        )
        connection.request(method, path, body=raw, headers=headers)
        response = connection.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        connection.close()
        return response.status, body

    def _wait_operation(
        self, server: LocalHTTPServer, operation: dict[str, object]
    ) -> None:
        operation_id = str(operation["operation_id"])
        deadline = time.monotonic() + 5
        last_body: dict[str, object] = {}
        while time.monotonic() < deadline:
            status, body = self._request(
                server, "GET", f"/api/operations/{operation_id}"
            )
            last_body = body
            self.assertEqual(status, 200)
            if body["state"] not in {"queued", "running"}:
                self.assertEqual(body["state"], "completed", body)
                return
            time.sleep(0.01)
        self.fail(f"Harbor reconcile operation did not complete: {last_body}")

    @staticmethod
    def _request_bytes(
        server: LocalHTTPServer, path: str
    ) -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_port, timeout=5
        )
        connection.request("GET", path)
        response = connection.getresponse()
        headers = {key.lower(): value for key, value in response.getheaders()}
        content = response.read()
        connection.close()
        return response.status, headers, content

    def test_dataset_registry_rejects_legacy_duplicate_and_unknown_references(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = apply_toml_config(
                ToolConfig(),
                {
                    "harbor": {
                        "datasets": [
                            {"id": "pbench", "path": str(root / "pbench")},
                            {"id": "other", "path": str(root / "other")},
                        ],
                        "mounts": [
                            {
                                "id": "jobs",
                                "path": str(root / "jobs"),
                                "dataset_ids": ["other", "pbench"],
                            }
                        ],
                    }
                },
            )
            self.assertEqual(config.harbor_mounts[0].dataset_ids, ("other", "pbench"))
            with self.assertRaisesRegex(ValueError, "task_paths.*no longer"):
                apply_toml_config(
                    ToolConfig(),
                    {
                        "harbor": {
                            "mounts": [
                                {
                                    "id": "jobs",
                                    "path": str(root / "jobs"),
                                    "task_paths": [str(root / "pbench")],
                                }
                            ]
                        }
                    },
                )
            with self.assertRaisesRegex(ValueError, "unknown dataset id"):
                apply_toml_config(
                    ToolConfig(),
                    {
                        "harbor": {
                            "mounts": [
                                {
                                    "id": "jobs",
                                    "path": str(root / "jobs"),
                                    "dataset_ids": ["missing"],
                                }
                            ]
                        }
                    },
                )

    def test_create_update_and_remove_dataset_preserve_unrelated_toml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workspace" / "peval-py.toml"
            config_path.parent.mkdir()
            config_path.write_text('locale = "zh-CN"\n', encoding="utf-8")
            library = HarborWorkspace(
                config_path,
                ToolConfig(workspace_root=str(config_path.parent), locale="zh-CN"),
            )
            config = library.create_dataset(
                dataset_id="pbench",
                path="../datasets/pbench",
                package_name="local/pbench",
                expected_revision=config_revision(config_path),
            )
            dataset_root = root / "datasets" / "pbench"
            self.assertTrue((dataset_root / "dataset.toml").is_file())
            self.assertTrue((dataset_root / "README.md").is_file())
            self.assertIn('locale = "zh-CN"', config_path.read_text(encoding="utf-8"))
            self.assertIn(
                "[[harbor.datasets]]", config_path.read_text(encoding="utf-8")
            )

            jobs = root / "jobs"
            jobs.mkdir()
            mounted = replace(
                config,
                harbor_mounts=(
                    HarborMount("jobs", str(jobs), dataset_ids=("pbench",)),
                ),
            )
            config = HarborWorkspace(config_path, mounted).update_dataset(
                dataset_id="pbench",
                new_id="pbench-renamed",
                path=str(dataset_root),
                expected_revision=config_revision(config_path),
            )
            self.assertEqual(config.harbor_datasets[0].id, "pbench-renamed")
            self.assertEqual(config.harbor_mounts[0].dataset_ids, ("pbench-renamed",))

            with self.assertRaisesRegex(HarborConflictError, "referenced"):
                HarborWorkspace(config_path, config).remove_dataset(
                    dataset_id="pbench-renamed",
                    expected_revision=config_revision(config_path),
                )

            unreferenced_config = replace(config, harbor_mounts=())
            unreferenced = HarborWorkspace(
                config_path, unreferenced_config
            ).remove_dataset(
                dataset_id="pbench-renamed",
                expected_revision=config_revision(config_path),
            )
            self.assertEqual(unreferenced.harbor_datasets, ())
            self.assertTrue(dataset_root.is_dir(), "unregister must preserve files")

    def test_registration_and_inventory_do_not_validate_dataset_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval-py.toml"
            self.assertEqual(
                config_revision(config_path),
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            )
            config_path.write_text("", encoding="utf-8")
            library = HarborWorkspace(config_path, ToolConfig(workspace_root=str(root)))

            unrelated = root / "unrelated"
            unrelated.mkdir()
            (unrelated / "dataset.toml").write_text(
                "not valid toml",
                encoding="utf-8",
            )
            configured = HarborWorkspace(
                config_path,
                ToolConfig(
                    workspace_root=str(root),
                    harbor_datasets=(HarborDataset("unrelated", str(unrelated)),),
                ),
            )
            inventory = configured.inventory()["datasets"][0]
            self.assertEqual(inventory["tasks"], [])
            self.assertNotIn("manifest_status", inventory)
            self.assertNotIn("manifest_diagnostic", inventory)

            registered = library.register_dataset(
                dataset_id="unrelated",
                path=str(unrelated),
                expected_revision=config_revision(config_path),
            )
            self.assertEqual(registered.harbor_datasets[0].id, "unrelated")

    def test_task_draft_manifest_trash_and_restore_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval-py.toml"
            config_path.write_text("", encoding="utf-8")
            initial = ToolConfig(workspace_root=str(root))
            created = HarborWorkspace(config_path, initial).create_dataset(
                dataset_id="tasks",
                path="dataset",
                package_name="local/tasks",
                expected_revision=config_revision(config_path),
            )
            library = HarborWorkspace(config_path, created)
            dataset = library.inventory()["datasets"][0]
            detail = library.create_task(
                dataset_id="tasks",
                directory="hello",
                package_name="local/hello",
                steps=0,
                expected_revision=dataset["revision"],
            )
            self.assertEqual(detail["task"]["status"], "valid")
            manifest = DatasetManifest.from_toml_file(root / "dataset" / "dataset.toml")
            self.assertEqual(manifest.tasks, [], "Task creation must not sync manifest")

            dataset = library.inventory()["datasets"][0]
            self.assertNotIn("manifest_status", dataset)
            library.sync_manifest(
                dataset_id="tasks", expected_revision=dataset["revision"]
            )
            manifest = DatasetManifest.from_toml_file(root / "dataset" / "dataset.toml")
            self.assertEqual([item.name for item in manifest.tasks], ["local/hello"])

            task = library.task_detail("tasks", "hello")["task"]
            library.mutate_file(
                "save",
                {
                    "dataset_id": "tasks",
                    "task": "hello",
                    "path": "task.toml",
                    "content": "not valid toml",
                    "expected_revision": task["revision"],
                },
            )
            draft = library.task_detail("tasks", "hello")["task"]
            self.assertEqual(draft["status"], "draft")
            self.assertTrue(draft["diagnostics"])
            self.assertEqual(
                read_harbor_task_index((str(root / "dataset"),)).candidates, ()
            )

            task_toml = (
                'schema_version = "1.4"\n\n'
                '[task]\nname = "local/hello"\nversion = "1.0.0"\n\n'
                "[agent]\ntimeout_sec = 600.0\n"
            )
            library.mutate_file(
                "save",
                {
                    "dataset_id": "tasks",
                    "task": "hello",
                    "path": "task.toml",
                    "content": task_toml,
                    "expected_revision": draft["revision"],
                },
            )
            task = library.task_detail("tasks", "hello")["task"]
            trashed = library.trash_task(
                dataset_id="tasks",
                task="hello",
                expected_revision=task["revision"],
            )
            self.assertFalse((root / "dataset" / "hello").exists())
            dataset = library.inventory()["datasets"][0]
            library.sync_manifest(
                dataset_id="tasks", expected_revision=dataset["revision"]
            )
            self.assertEqual(
                DatasetManifest.from_toml_file(root / "dataset" / "dataset.toml").tasks,
                [],
            )
            trash_entry = root / "dataset" / ".peval-py-trash" / trashed["entry_id"]
            with (
                patch.object(Path, "rmdir", side_effect=OSError("blocked")),
                self.assertRaisesRegex(HarborWorkspaceError, "restore cleanup failed"),
            ):
                library.restore_task(
                    dataset_id="tasks",
                    entry_id=trashed["entry_id"],
                    directory="failed-restore",
                    expected_revision=trashed["revision"],
                )
            self.assertFalse((root / "dataset" / "failed-restore").exists())
            self.assertTrue((trash_entry / "task").is_dir())
            self.assertTrue((trash_entry / "metadata.json").is_file())
            restored = library.restore_task(
                dataset_id="tasks",
                entry_id=trashed["entry_id"],
                directory="restored",
                expected_revision=trashed["revision"],
            )
            self.assertEqual(restored["task"]["directory"], "restored")
            self.assertEqual(restored["task"]["package_name"], "local/hello")
            trashed_again = library.trash_task(
                dataset_id="tasks",
                task="restored",
                expected_revision=restored["task"]["revision"],
            )
            library.purge_task(
                dataset_id="tasks",
                entry_id=trashed_again["entry_id"],
                expected_revision=trashed_again["revision"],
            )
            self.assertFalse(
                (
                    root / "dataset" / ".peval-py-trash" / trashed_again["entry_id"]
                ).exists()
            )

    def test_manifest_sync_rechecks_external_changes_before_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval-py.toml"
            config_path.write_text("", encoding="utf-8")
            config = HarborWorkspace(
                config_path, ToolConfig(workspace_root=str(root))
            ).create_dataset(
                dataset_id="tasks",
                path="dataset",
                package_name="local/tasks",
                expected_revision=config_revision(config_path),
            )
            library = HarborWorkspace(config_path, config)
            dataset = library.inventory()["datasets"][0]
            library.create_task(
                dataset_id="tasks",
                directory="hello",
                package_name="local/hello",
                steps=0,
                expected_revision=dataset["revision"],
            )
            dataset = library.inventory()["datasets"][0]
            instruction = root / "dataset" / "hello" / "instruction.md"
            original_summaries = library._task_summaries

            def summaries_with_external_change(dataset_root: Path):
                summaries = original_summaries(dataset_root)
                instruction.write_text("Externally changed.\n", encoding="utf-8")
                return summaries

            with (
                patch.object(
                    library,
                    "_task_summaries",
                    side_effect=summaries_with_external_change,
                ),
                self.assertRaisesRegex(HarborConflictError, "refresh"),
            ):
                library.sync_manifest(
                    dataset_id="tasks",
                    expected_revision=dataset["revision"],
                )

            manifest = DatasetManifest.from_toml_file(root / "dataset" / "dataset.toml")
            self.assertEqual(manifest.tasks, [])

    def test_revisions_paths_upload_limits_and_symlinks_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval-py.toml"
            config_path.write_text("", encoding="utf-8")
            dataset_root = root / "dataset"
            dataset_root.mkdir()
            DatasetManifest.from_toml(
                'schema_version = "1.0"\n[dataset]\nname = "local/tasks"\n'
            ).to_toml()
            (dataset_root / "dataset.toml").write_text(
                'schema_version = "1.0"\n[dataset]\nname = "local/tasks"\n',
                encoding="utf-8",
            )
            config = ToolConfig(
                workspace_root=str(root),
                harbor_datasets=(HarborDataset("tasks", str(dataset_root)),),
            )
            library = HarborWorkspace(config_path, config)
            dataset = library.inventory()["datasets"][0]
            detail = library.create_task(
                dataset_id="tasks",
                directory="safe",
                package_name="local/safe",
                steps=0,
                expected_revision=dataset["revision"],
            )
            with self.assertRaises(HarborConflictError):
                library.rename_task(
                    dataset_id="tasks",
                    task="safe",
                    new_directory="other",
                    expected_revision="stale",
                )
            with self.assertRaisesRegex(HarborWorkspaceError, "safe relative"):
                library.mutate_file(
                    "create",
                    {
                        "dataset_id": "tasks",
                        "task": "safe",
                        "path": "../escape",
                        "kind": "file",
                        "expected_revision": detail["task"]["revision"],
                    },
                )
            with (
                patch("peval_py.serve.harbor_workspace.UPLOAD_LIMIT", 2),
                self.assertRaisesRegex(HarborWorkspaceError, "Uploads are limited"),
            ):
                library.mutate_file(
                    "upload",
                    {
                        "dataset_id": "tasks",
                        "task": "safe",
                        "path": "large.bin",
                        "content_base64": b64encode(b"abc").decode("ascii"),
                        "expected_revision": detail["task"]["revision"],
                    },
                )
            growing = root / "growing.txt"
            growing.write_bytes(b"ab")
            original_fstat = os.fstat
            grew = False

            def grow_after_stat(descriptor: int):
                nonlocal grew
                value = original_fstat(descriptor)
                if not grew:
                    grew = True
                    growing.write_bytes(b"abcd")
                return value

            with (
                patch.object(
                    os,
                    "fstat",
                    side_effect=grow_after_stat,
                ),
                self.assertRaisesRegex(HarborSizeError, "limit"),
            ):
                _read_regular_file(growing, limit=3)
            outside = root / "outside"
            outside.write_text("secret", encoding="utf-8")
            try:
                (dataset_root / "safe" / "linked").symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            with self.assertRaisesRegex(HarborWorkspaceError, "symbolic link"):
                library.task_detail("tasks", "safe")

    def test_missing_harbor_task_templates_fail_safely_without_partial_task(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval-py.toml"
            config_path.write_text("", encoding="utf-8")
            library = HarborWorkspace(config_path, ToolConfig(workspace_root=str(root)))
            config = library.create_dataset(
                dataset_id="tasks",
                path="dataset",
                package_name="local/tasks",
                expected_revision=config_revision(config_path),
            )
            library = HarborWorkspace(config_path, config)
            dataset = library.inventory()["datasets"][0]

            with (
                patch(
                    "harbor.cli.init.__file__",
                    "/server/private/harbor/init.py",
                ),
                self.assertRaisesRegex(
                    HarborWorkspaceError,
                    "Harbor Task templates are unavailable",
                ) as raised,
            ):
                library.create_task(
                    dataset_id="tasks",
                    directory="missing-template",
                    package_name="local/missing-template",
                    steps=0,
                    expected_revision=dataset["revision"],
                )

            self.assertNotIn("/server/private", str(raised.exception))
            self.assertFalse((root / "dataset" / "missing-template").exists())
            self.assertEqual(
                list((root / "dataset").glob(".peval-py-staging-*")),
                [],
            )

    def test_register_dataset_http_validates_roots_without_parsing_manifest(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "peval-py.toml").write_text("", encoding="utf-8")
            existing = root / "existing"
            existing.mkdir()
            (existing / "dataset.toml").write_text(
                "not valid toml",
                encoding="utf-8",
            )
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, ToolConfig(workspace_root=str(root)))
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                self.assertEqual(status, 200)
                status, registered = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets",
                    {
                        "action": "register",
                        "dataset_id": "existing",
                        "path": str(existing),
                        "expected_revision": inventory["revision"],
                    },
                )
                self.assertEqual(status, 202, registered)
                self._wait_operation(server, registered["operation"])

                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                self.assertEqual(status, 200)
                self.assertEqual(
                    [item["id"] for item in inventory["datasets"]], ["existing"]
                )
                status, duplicate = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets",
                    {
                        "action": "register",
                        "dataset_id": "existing",
                        "path": str(existing),
                        "expected_revision": inventory["revision"],
                    },
                )
                self.assertEqual(status, 409, duplicate)

                status, missing = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets",
                    {
                        "action": "register",
                        "dataset_id": "missing",
                        "path": str(root / "missing"),
                        "expected_revision": inventory["revision"],
                    },
                )
                self.assertEqual(status, 404, missing)

                linked = root / "linked"
                try:
                    linked.symlink_to(existing, target_is_directory=True)
                except OSError:
                    linked = None
                if linked is not None:
                    status, symlinked = self._request(
                        server,
                        "POST",
                        "/api/harbor/datasets",
                        {
                            "action": "register",
                            "dataset_id": "linked",
                            "path": str(linked),
                            "expected_revision": inventory["revision"],
                        },
                    )
                    self.assertEqual(status, 400, symlinked)
                    self.assertIn("symbolic link", symlinked["error"])

                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                status, updated = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets",
                    {
                        "action": "update",
                        "dataset_id": "existing",
                        "new_id": "renamed",
                        "path": str(existing),
                        "expected_revision": inventory["revision"],
                    },
                )
                self.assertEqual(status, 202, updated)
                self._wait_operation(server, updated["operation"])
                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                self.assertEqual(
                    [item["id"] for item in inventory["datasets"]], ["renamed"]
                )

                status, removed = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets",
                    {
                        "action": "remove",
                        "dataset_id": "renamed",
                        "expected_revision": inventory["revision"],
                    },
                )
                self.assertEqual(status, 202, removed)
                self._wait_operation(server, removed["operation"])
                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                self.assertEqual(inventory["datasets"], [])
                self.assertTrue(existing.is_dir(), "unregister must preserve files")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_routes_apply_revisions_and_return_safe_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "peval-py.toml").write_text("", encoding="utf-8")
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, ToolConfig(workspace_root=str(root)))
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                self.assertEqual(status, 200)
                self.assertEqual(status, 200)
                status, created = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets",
                    {
                        "action": "create",
                        "dataset_id": "tasks",
                        "path": "dataset",
                        "package_name": "local/tasks",
                        "expected_revision": inventory["revision"],
                    },
                )
                self.assertEqual(status, 202, created)
                self._wait_operation(server, created["operation"])

                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                self.assertEqual(status, 200)
                dataset = inventory["datasets"][0]
                status, created_task = self._request(
                    server,
                    "POST",
                    "/api/harbor/tasks",
                    {
                        "action": "create",
                        "dataset_id": "tasks",
                        "directory": "hello",
                        "package_name": "local/hello",
                        "steps": 0,
                        "expected_revision": dataset["revision"],
                    },
                )
                self.assertEqual(status, 202, created_task)
                self._wait_operation(server, created_task["operation"])

                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                dataset = inventory["datasets"][0]
                status, synchronized = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets",
                    {
                        "action": "sync_manifest",
                        "dataset_id": "tasks",
                        "expected_revision": dataset["revision"],
                    },
                )
                self.assertEqual(status, 200, synchronized)
                self.assertNotIn("manifest_status", synchronized)

                status, detail = self._request(
                    server,
                    "GET",
                    "/api/harbor/task?dataset_id=tasks&task=hello",
                )
                self.assertEqual(status, 200)
                self.assertEqual(detail["task"]["status"], "valid")
                status, text = self._request(
                    server,
                    "GET",
                    "/api/harbor/files?dataset_id=tasks&task=hello&path=instruction.md",
                )
                self.assertEqual(status, 200)
                self.assertIn("content", text)

                status, headers, content = self._request_bytes(
                    server,
                    "/api/harbor/files?dataset_id=tasks&task=hello&"
                    "path=instruction.md&download=1",
                )
                self.assertEqual(status, 200)
                self.assertEqual(content, text["content"].encode("utf-8"))
                self.assertEqual(headers["content-type"], "application/octet-stream")
                self.assertIn("attachment", headers["content-disposition"])
                self.assertIn("etag", headers)
                self.assertIn("x-peval-task-revision", headers)

                status, _headers, unsafe_download = self._request_bytes(
                    server,
                    "/api/harbor/files?dataset_id=tasks&task=hello&"
                    "path=../secret&download=1",
                )
                self.assertEqual(status, 400)
                self.assertNotIn(str(root).encode(), unsafe_download)

                status, conflict = self._request(
                    server,
                    "POST",
                    "/api/harbor/files",
                    {
                        "action": "save",
                        "dataset_id": "tasks",
                        "task": "hello",
                        "path": "instruction.md",
                        "content": "changed\n",
                        "expected_revision": "stale",
                    },
                )
                self.assertEqual(status, 409)
                self.assertIn("refresh", conflict["error"])

                with patch("peval_py.serve.harbor_workspace.UPLOAD_LIMIT", 2):
                    status, oversized = self._request(
                        server,
                        "POST",
                        "/api/harbor/files",
                        {
                            "action": "upload",
                            "dataset_id": "tasks",
                            "task": "hello",
                            "path": "large.bin",
                            "content_base64": b64encode(b"abc").decode("ascii"),
                            "expected_revision": detail["task"]["revision"],
                        },
                    )
                self.assertEqual(status, 413, oversized)

                status, unsafe = self._request(
                    server,
                    "GET",
                    "/api/harbor/files?dataset_id=tasks&task=hello&path=../secret",
                )
                self.assertEqual(status, 400)
                self.assertNotIn(str(root), unsafe["error"])

                status, renamed = self._request(
                    server,
                    "POST",
                    "/api/harbor/tasks",
                    {
                        "action": "rename",
                        "dataset_id": "tasks",
                        "task": "hello",
                        "new_directory": "renamed",
                        "expected_revision": detail["task"]["revision"],
                    },
                )
                self.assertEqual(status, 202, renamed)
                self._wait_operation(server, renamed["operation"])
                renamed_task = renamed["result"]["task"]
                self.assertEqual(renamed_task["directory"], "renamed")

                status, trashed = self._request(
                    server,
                    "POST",
                    "/api/harbor/tasks",
                    {
                        "action": "trash",
                        "dataset_id": "tasks",
                        "task": "renamed",
                        "expected_revision": renamed_task["revision"],
                    },
                )
                self.assertEqual(status, 202, trashed)
                self._wait_operation(server, trashed["operation"])

                status, restored = self._request(
                    server,
                    "POST",
                    "/api/harbor/tasks",
                    {
                        "action": "restore",
                        "dataset_id": "tasks",
                        "entry_id": trashed["result"]["entry_id"],
                        "directory": "restored",
                        "expected_revision": trashed["result"]["revision"],
                    },
                )
                self.assertEqual(status, 202, restored)
                self._wait_operation(server, restored["operation"])

                status, trashed_again = self._request(
                    server,
                    "POST",
                    "/api/harbor/tasks",
                    {
                        "action": "trash",
                        "dataset_id": "tasks",
                        "task": "restored",
                        "expected_revision": restored["result"]["task"]["revision"],
                    },
                )
                self.assertEqual(status, 202, trashed_again)
                self._wait_operation(server, trashed_again["operation"])

                status, purged = self._request(
                    server,
                    "POST",
                    "/api/harbor/tasks",
                    {
                        "action": "purge",
                        "dataset_id": "tasks",
                        "entry_id": trashed_again["result"]["entry_id"],
                        "expected_revision": trashed_again["result"]["revision"],
                    },
                )
                self.assertEqual(status, 202, purged)
                self._wait_operation(server, purged["operation"])
                self.assertEqual(purged["result"]["datasets"][0]["trash"], [])

                status, unknown = self._request(
                    server,
                    "POST",
                    "/api/harbor/tasks",
                    {
                        "action": "unknown",
                        "dataset_id": "tasks",
                        "expected_revision": "unused",
                    },
                )
                self.assertEqual(status, 400, unknown)

                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                status, invalid_steps = self._request(
                    server,
                    "POST",
                    "/api/harbor/tasks",
                    {
                        "action": "create",
                        "dataset_id": "tasks",
                        "directory": "invalid-steps",
                        "package_name": "local/invalid-steps",
                        "steps": "two",
                        "expected_revision": inventory["datasets"][0]["revision"],
                    },
                )
                self.assertEqual(status, 400, invalid_steps)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_guest_can_browse_task_text_without_private_fields_or_downloads(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval-py.toml"
            config_path.write_text("", encoding="utf-8")
            config = HarborWorkspace(
                config_path, ToolConfig(workspace_root=str(root))
            ).create_dataset(
                dataset_id="tasks",
                path="dataset",
                package_name="local/tasks",
                expected_revision=config_revision(config_path),
            )
            library = HarborWorkspace(config_path, config)
            dataset = library.inventory()["datasets"][0]
            library.create_task(
                dataset_id="tasks",
                directory="hello",
                package_name="local/hello",
                steps=0,
                expected_revision=dataset["revision"],
            )
            (root / "dataset" / "hello" / "binary.bin").write_bytes(b"\xff\x00")
            (root / "dataset" / "hello" / "large.txt").write_bytes(
                b"x" * (2 * 1024 * 1024 + 1)
            )

            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, config)
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(runtime, access=ServeAccess("secret")),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                self.assertEqual(status, 200)
                self.assertEqual(set(inventory), {"datasets"})
                public_dataset = inventory["datasets"][0]
                self.assertEqual(
                    set(public_dataset),
                    {"id", "tasks"},
                )
                self.assertNotIn(str(root), json.dumps(inventory))
                self.assertNotIn("revision", json.dumps(inventory))
                self.assertNotIn("trash", json.dumps(inventory))
                status, task_inventory = self._request(
                    server,
                    "GET",
                    "/api/harbor/tasks?dataset_id=tasks",
                )
                self.assertEqual(status, 200)
                self.assertEqual(task_inventory, inventory)

                status, detail = self._request(
                    server,
                    "GET",
                    "/api/harbor/task?dataset_id=tasks&task=hello",
                )
                self.assertEqual(status, 200)
                paths = {item["path"]: item for item in detail["tree"]}
                self.assertIn("solution/solve.sh", paths)
                self.assertIn("tests/test.sh", paths)
                self.assertFalse(paths["binary.bin"]["editable"])
                self.assertFalse(paths["large.txt"]["editable"])
                self.assertTrue(
                    all("downloadable" not in item for item in detail["tree"])
                )

                for path in ("solution/solve.sh", "tests/test.sh"):
                    status, text = self._request(
                        server,
                        "GET",
                        "/api/harbor/files?dataset_id=tasks&task=hello&path=" + path,
                    )
                    self.assertEqual(status, 200)
                    self.assertEqual(set(text), {"path", "content"})

                status, blocked = self._request(
                    server,
                    "GET",
                    "/api/harbor/files?dataset_id=tasks&task=hello&path="
                    "solution/solve.sh&download=1",
                )
                self.assertEqual(status, 403, blocked)
                status, blocked = self._request(
                    server,
                    "POST",
                    "/api/harbor/files",
                    {
                        "action": "save",
                        "dataset_id": "tasks",
                        "task": "hello",
                        "path": "instruction.md",
                        "content": "blocked",
                        "expected_revision": "private",
                    },
                )
                self.assertEqual(status, 403, blocked)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()


if __name__ == "__main__":
    unittest.main()
