from __future__ import annotations

import http.client
import json
import os
import tempfile
import threading
import time
import unittest
from base64 import b64encode
from pathlib import Path
from unittest.mock import patch

from harbor.models.dataset.manifest import DatasetManifest

from psycheval.config import (
    HarborDataset,
    HarborMount,
    ToolConfig,
    apply_toml_config,
)
from psycheval.serve import (
    ServeAccess,
    ServeRuntime,
)
from psycheval.serve.harbor_workspace import (
    TEXT_EDIT_LIMIT,
    HarborConflictError,
    HarborNotFoundError,
    HarborSizeError,
    HarborWorkspace,
    HarborWorkspaceError,
    _read_regular_file,
    config_revision,
)
from psycheval.state import open_workspace_state
from psycheval.state.harbor_evidence import read_harbor_task_index
from tests.peval.asgi_server import LocalHTTPServer, make_handler


class HarborWorkspaceTests(unittest.TestCase):
    @staticmethod
    def _request(
        server: LocalHTTPServer,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        *,
        request_headers: dict[str, str] | None = None,
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
        headers.update(request_headers or {})
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_port, timeout=5
        )
        connection.request(method, path, body=raw, headers=headers)
        response = connection.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        connection.close()
        return response.status, body

    def _wait_operation(
        self,
        server: LocalHTTPServer,
        operation: dict[str, object],
        *,
        expected_state: str = "succeeded",
    ) -> dict[str, object]:
        operation_id = str(operation.get("id") or operation.get("operation_id"))
        deadline = time.monotonic() + 5
        last_body: dict[str, object] = {}
        while time.monotonic() < deadline:
            status, body = self._request(
                server, "GET", f"/api/operations/{operation_id}"
            )
            last_body = body
            self.assertEqual(status, 200)
            if body["state"] not in {"queued", "running"}:
                self.assertEqual(body["state"], expected_state, body)
                return body
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

    def _get_json(
        self, server: LocalHTTPServer, path: str
    ) -> tuple[int, dict[str, str], dict[str, object]]:
        status, headers, content = self._request_bytes(server, path)
        return status, headers, json.loads(content)

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
            with self.assertRaisesRegex(
                ValueError, "harbor.mounts.0.task_paths: unknown configuration field"
            ):
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
            config_path = root / "workspace" / "peval.toml"
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
            mounted = config.validated_update(
                harbor_mounts=(
                    HarborMount(id="jobs", path=str(jobs), dataset_ids=("pbench",)),
                ),
            )
            config = HarborWorkspace(config_path, mounted).update_dataset(
                dataset_id="pbench",
                new_id="pbench-renamed",
                path=str(dataset_root),
                mount_ids=("jobs",),
                expected_revision=config_revision(config_path),
            )
            self.assertEqual(config.harbor_datasets[0].id, "pbench-renamed")
            self.assertEqual(config.harbor_mounts[0].dataset_ids, ("pbench-renamed",))

            with self.assertRaisesRegex(HarborConflictError, "referenced"):
                HarborWorkspace(config_path, config).remove_dataset(
                    dataset_id="pbench-renamed",
                    expected_revision=config_revision(config_path),
                )

            unreferenced_config = config.validated_update(harbor_mounts=())
            unreferenced = HarborWorkspace(
                config_path, unreferenced_config
            ).remove_dataset(
                dataset_id="pbench-renamed",
                expected_revision=config_revision(config_path),
            )
            self.assertEqual(unreferenced.harbor_datasets, ())
            self.assertTrue(dataset_root.is_dir(), "unregister must preserve files")

    def test_update_dataset_reconciles_mount_membership_without_reordering(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval.toml"
            config_path.write_text("", encoding="utf-8")
            for name in (
                "alpha",
                "pbench",
                "beta",
                "jobs-one",
                "jobs-two",
                "jobs-three",
            ):
                (root / name).mkdir()
            config = ToolConfig(
                workspace_root=str(root),
                harbor_datasets=(
                    HarborDataset(id="alpha", path=str(root / "alpha")),
                    HarborDataset(id="pbench", path=str(root / "pbench")),
                    HarborDataset(id="beta", path=str(root / "beta")),
                ),
                harbor_mounts=(
                    HarborMount(
                        id="one",
                        path=str(root / "jobs-one"),
                        dataset_ids=("alpha", "pbench", "beta"),
                    ),
                    HarborMount(
                        id="two", path=str(root / "jobs-two"), dataset_ids=("alpha",)
                    ),
                    HarborMount(
                        id="three",
                        path=str(root / "jobs-three"),
                        dataset_ids=("pbench", "alpha"),
                    ),
                ),
            )

            updated = HarborWorkspace(config_path, config).update_dataset(
                dataset_id="pbench",
                new_id="pbench-v1.0",
                path=str(root / "pbench"),
                mount_ids=("one", "two"),
                expected_revision=config_revision(config_path),
            )

            self.assertEqual(
                [mount.dataset_ids for mount in updated.harbor_mounts],
                [
                    ("alpha", "pbench-v1.0", "beta"),
                    ("alpha", "pbench-v1.0"),
                    ("alpha",),
                ],
            )

            before = config_path.read_bytes()
            with self.assertRaisesRegex(HarborNotFoundError, "missing"):
                HarborWorkspace(config_path, updated).update_dataset(
                    dataset_id="pbench-v1.0",
                    new_id="pbench-v1.0",
                    path=str(root / "pbench"),
                    mount_ids=("missing",),
                    expected_revision=config_revision(config_path),
                )
            self.assertEqual(config_path.read_bytes(), before)

    def test_registration_and_inventory_do_not_validate_dataset_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval.toml"
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
                    harbor_datasets=(
                        HarborDataset(id="unrelated", path=str(unrelated)),
                    ),
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

    def test_batch_unregister_is_atomic_when_any_dataset_is_mounted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval.toml"
            config_path.write_text("", encoding="utf-8")
            for name in ("one", "two"):
                (root / name).mkdir()
            config = ToolConfig(
                workspace_root=str(root),
                harbor_datasets=(
                    HarborDataset(id="one", path=str(root / "one")),
                    HarborDataset(id="two", path=str(root / "two")),
                ),
                harbor_mounts=(
                    HarborMount(
                        id="jobs", path=str(root / "jobs"), dataset_ids=("two",)
                    ),
                ),
            )
            before = config_path.read_bytes()
            with self.assertRaisesRegex(HarborConflictError, "two: jobs"):
                HarborWorkspace(config_path, config).remove_datasets(
                    dataset_ids=("one", "two"),
                    expected_revision=config_revision(config_path),
                )
            self.assertEqual(config_path.read_bytes(), before)
            self.assertEqual(
                [dataset.id for dataset in config.harbor_datasets], ["one", "two"]
            )

    def test_task_draft_manifest_trash_and_restore_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval.toml"
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
            self.assertEqual(detail["default_file_path"], "instruction.md")
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
            self.assertEqual(
                [
                    item.name
                    for item in DatasetManifest.from_toml_file(
                        root / "dataset" / "dataset.toml"
                    ).tasks
                ],
                ["local/hello"],
                "archive must not implicitly rewrite the manifest",
            )
            dataset = library.inventory()["datasets"][0]
            library.sync_manifest(
                dataset_id="tasks", expected_revision=dataset["revision"]
            )
            self.assertEqual(
                DatasetManifest.from_toml_file(root / "dataset" / "dataset.toml").tasks,
                [],
            )
            trash_entry = root / "dataset" / ".peval-trash" / trashed["entry_id"]
            trashed = library.rename_archived_task(
                dataset_id="tasks",
                entry_id=trashed["entry_id"],
                new_directory="restored",
                expected_revision=trashed["revision"],
            )
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
            (root / "dataset" / "restored").mkdir()
            with self.assertRaisesRegex(HarborConflictError, "already exists"):
                library.restore_task(
                    dataset_id="tasks",
                    entry_id=trashed["entry_id"],
                    directory=None,
                    expected_revision=trashed["revision"],
                )
            (root / "dataset" / "restored").rmdir()
            restored = library.restore_task(
                dataset_id="tasks",
                entry_id=trashed["entry_id"],
                directory=None,
                expected_revision=trashed["revision"],
            )
            self.assertEqual(restored["task"]["directory"], "restored")
            self.assertEqual(restored["task"]["package_name"], "local/hello")

            dataset = library.inventory()["datasets"][0]
            delete_me = library.create_task(
                dataset_id="tasks",
                directory="delete-me",
                package_name="local/delete-me",
                steps=0,
                expected_revision=dataset["revision"],
            )
            dataset = library.inventory()["datasets"][0]
            library.sync_manifest(
                dataset_id="tasks", expected_revision=dataset["revision"]
            )
            manifest_before_delete = (root / "dataset" / "dataset.toml").read_bytes()
            library.delete_task(
                dataset_id="tasks",
                task="delete-me",
                expected_revision=delete_me["task"]["revision"],
            )
            self.assertFalse((root / "dataset" / "delete-me").exists())
            self.assertEqual(
                (root / "dataset" / "dataset.toml").read_bytes(),
                manifest_before_delete,
                "permanent delete must not implicitly rewrite the manifest",
            )
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
                (root / "dataset" / ".peval-trash" / trashed_again["entry_id"]).exists()
            )

    def test_manifest_sync_rechecks_external_changes_before_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval.toml"
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
            config_path = root / "peval.toml"
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
                harbor_datasets=(HarborDataset(id="tasks", path=str(dataset_root)),),
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
                patch("psycheval.serve.harbor_workspace.UPLOAD_LIMIT", 2),
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
            config_path = root / "peval.toml"
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
                list((root / "dataset").glob(".peval-staging-*")),
                [],
            )

    def test_task_detail_selects_only_the_configured_default_instruction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset"
            dataset.mkdir()
            single = dataset / "single"
            single.mkdir()
            (single / "task.toml").write_text(
                'schema_version = "1.4"\n[task]\nname = "local/single"\n',
                encoding="utf-8",
            )
            (single / "instruction.md").write_text("Single\n", encoding="utf-8")
            multi = dataset / "multi"
            (multi / "steps" / "zeta").mkdir(parents=True)
            (multi / "steps" / "alpha").mkdir(parents=True)
            (multi / "task.toml").write_text(
                'schema_version = "1.4"\n'
                '[[steps]]\nname = "zeta"\n'
                '[[steps]]\nname = "alpha"\n',
                encoding="utf-8",
            )
            (multi / "instruction.md").write_text(
                "Do not fall back\n", encoding="utf-8"
            )
            (multi / "steps" / "zeta" / "instruction.md").write_text(
                "First configured\n", encoding="utf-8"
            )
            (multi / "steps" / "alpha" / "instruction.md").write_text(
                "Second configured\n", encoding="utf-8"
            )
            library = HarborWorkspace(
                root / "peval.toml",
                ToolConfig(
                    workspace_root=str(root),
                    harbor_datasets=(HarborDataset(id="tasks", path=str(dataset)),),
                ),
            )

            self.assertEqual(
                library.task_detail("tasks", "single")["default_file_path"],
                "instruction.md",
            )
            self.assertEqual(
                library.task_detail("tasks", "multi")["default_file_path"],
                "steps/zeta/instruction.md",
            )

            (multi / "steps" / "zeta" / "instruction.md").unlink()
            self.assertIsNone(
                library.task_detail("tasks", "multi")["default_file_path"]
            )
            (single / "instruction.md").write_bytes(b"\xff")
            self.assertIsNone(
                library.task_detail("tasks", "single")["default_file_path"]
            )
            (single / "instruction.md").write_bytes(b"x" * (TEXT_EDIT_LIMIT + 1))
            self.assertIsNone(
                library.task_detail("tasks", "single")["default_file_path"]
            )

    def test_register_dataset_http_validates_roots_without_parsing_manifest(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "peval.toml").write_text("", encoding="utf-8")
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
                status, legacy = self._request(
                    server, "POST", "/api/harbor/datasets", {}
                )
                self.assertEqual(status, 422, legacy)
                status, legacy = self._request(
                    server, "POST", "/api/config/harbor-mount", {}
                )
                self.assertEqual(status, 404, legacy)
                status, headers, inventory = self._get_json(
                    server, "/api/harbor/datasets"
                )
                self.assertEqual(status, 200)
                status, registered = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets",
                    {"source": "existing", "path": str(existing)},
                    request_headers={"If-Match": headers["etag"]},
                )
                self.assertEqual(status, 202, registered)
                self._wait_operation(server, registered)

                status, headers, inventory = self._get_json(
                    server, "/api/harbor/datasets"
                )
                self.assertEqual(status, 200)
                self.assertEqual(
                    [item["id"] for item in inventory["datasets"]], ["existing"]
                )
                status, duplicate = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets",
                    {"source": "existing", "path": str(existing)},
                    request_headers={"If-Match": headers["etag"]},
                )
                self.assertEqual(status, 409, duplicate)

                status, missing = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets",
                    {"source": "existing", "path": str(root / "missing")},
                    request_headers={"If-Match": headers["etag"]},
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
                        {"source": "existing", "path": str(linked)},
                        request_headers={"If-Match": headers["etag"]},
                    )
                    self.assertEqual(status, 400, symlinked)
                    self.assertIn("symbolic link", symlinked["detail"])

                status, headers, inventory = self._get_json(
                    server, "/api/harbor/datasets"
                )
                status, updated = self._request(
                    server,
                    "PATCH",
                    "/api/harbor/datasets/existing",
                    {
                        "new_id": "renamed",
                        "path": str(existing),
                        "mount_ids": [],
                    },
                    request_headers={"If-Match": headers["etag"]},
                )
                self.assertEqual(status, 202, updated)
                self._wait_operation(server, updated)
                status, headers, inventory = self._get_json(
                    server, "/api/harbor/datasets"
                )
                self.assertEqual(
                    [item["id"] for item in inventory["datasets"]], ["renamed"]
                )

                status, removed = self._request(
                    server,
                    "POST",
                    "/api/harbor/dataset-unregistration-operations",
                    {"dataset_ids": ["renamed"]},
                    request_headers={"If-Match": headers["etag"]},
                )
                self.assertEqual(status, 202, removed)
                self._wait_operation(server, removed)
                status, _headers, inventory = self._get_json(
                    server, "/api/harbor/datasets"
                )
                self.assertEqual(inventory["datasets"], [])
                self.assertTrue(existing.is_dir(), "unregister must preserve files")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_register_dataset_derives_id_from_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "peval.toml").write_text("", encoding="utf-8")
            dataset = root / "pbench-v1.0"
            dataset.mkdir()
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, ToolConfig(workspace_root=str(root)))
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, headers, inventory = self._get_json(
                    server, "/api/harbor/datasets"
                )
                self.assertEqual(status, 200)
                status, registered = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets",
                    {"source": "existing", "path": str(dataset)},
                    request_headers={"If-Match": headers["etag"]},
                )
                self.assertEqual(status, 202, registered)
                self._wait_operation(server, registered)

                status, _headers, inventory = self._get_json(
                    server, "/api/harbor/datasets"
                )
                self.assertEqual(status, 200)
                self.assertEqual(inventory["datasets"][0]["id"], "pbench-v1.0")
                self.assertEqual(inventory["datasets"][0]["path"], str(dataset))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_register_dataset_suffixes_conflicts_and_invalid_basenames(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "peval.toml").write_text("", encoding="utf-8")
            paths = [
                root / "one" / "shared",
                root / "two" / "shared",
                root / "Invalid.Name",
            ]
            for path in paths:
                path.mkdir(parents=True)
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, ToolConfig(workspace_root=str(root)))
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with patch(
                    "psycheval.config.secrets.token_hex",
                    side_effect=["abc123", "def456"],
                ):
                    for path in paths:
                        status, headers, inventory = self._get_json(
                            server, "/api/harbor/datasets"
                        )
                        self.assertEqual(status, 200)
                        status, registered = self._request(
                            server,
                            "POST",
                            "/api/harbor/datasets",
                            {"source": "existing", "path": str(path)},
                            request_headers={"If-Match": headers["etag"]},
                        )
                        self.assertEqual(status, 202, registered)
                        self._wait_operation(server, registered)

                status, _headers, inventory = self._get_json(
                    server, "/api/harbor/datasets"
                )
                self.assertEqual(status, 200)
                self.assertEqual(
                    [item["id"] for item in inventory["datasets"]],
                    ["shared", "shared-abc123", "dataset-def456"],
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_add_harbor_mount_derives_id_and_starts_without_datasets(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "peval.toml").write_text("", encoding="utf-8")
            jobs = root / "nightly-jobs"
            jobs.mkdir()
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, ToolConfig(workspace_root=str(root)))
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, headers, inventory = self._get_json(
                    server, "/api/harbor/mounts"
                )
                self.assertEqual(status, 200)
                self.assertEqual(inventory, [])
                status, mounted = self._request(
                    server,
                    "POST",
                    "/api/harbor/mounts",
                    {"path": str(jobs)},
                    request_headers={"If-Match": headers["etag"]},
                )
                self.assertEqual(status, 202, mounted)
                self._wait_operation(server, mounted)
                status, _headers, mounts = self._get_json(server, "/api/harbor/mounts")
                self.assertEqual(
                    mounts,
                    [
                        {
                            "id": "nightly-jobs",
                            "path": str(jobs),
                            "dataset_ids": [],
                        }
                    ],
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_dataset_update_sets_mount_membership_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "tasks"
            jobs_one = root / "jobs-one"
            jobs_two = root / "jobs-two"
            for path in (dataset, jobs_one, jobs_two):
                path.mkdir()
            config_path = root / "peval.toml"
            config_path.write_text(
                '[[harbor.datasets]]\nid = "tasks"\npath = "tasks"\n\n'
                '[[harbor.mounts]]\nid = "one"\npath = "jobs-one"\n'
                'dataset_ids = ["tasks"]\n\n'
                '[[harbor.mounts]]\nid = "two"\npath = "jobs-two"\n',
                encoding="utf-8",
            )
            config = ToolConfig(
                workspace_root=str(root),
                harbor_datasets=(HarborDataset(id="tasks", path=str(dataset)),),
                harbor_mounts=(
                    HarborMount(id="one", path=str(jobs_one), dataset_ids=("tasks",)),
                    HarborMount(id="two", path=str(jobs_two), dataset_ids=()),
                ),
            )
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, config)
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, headers, inventory = self._get_json(
                    server, "/api/harbor/datasets"
                )
                self.assertEqual(status, 200)
                status, updated = self._request(
                    server,
                    "PATCH",
                    "/api/harbor/datasets/tasks",
                    {
                        "new_id": "tasks",
                        "path": str(dataset),
                        "mount_ids": ["two"],
                    },
                    request_headers={"If-Match": headers["etag"]},
                )
                self.assertEqual(status, 202, updated)
                self._wait_operation(server, updated)
                status, headers, _updated_inventory = self._get_json(
                    server, "/api/harbor/datasets"
                )
                mount_status, _mount_headers, mounts = self._get_json(
                    server, "/api/harbor/mounts"
                )
                self.assertEqual(mount_status, 200)
                self.assertEqual(
                    [mount["dataset_ids"] for mount in mounts],
                    [[], ["tasks"]],
                )

                before = config_path.read_bytes()
                status, rejected = self._request(
                    server,
                    "PATCH",
                    "/api/harbor/datasets/tasks",
                    {
                        "new_id": "tasks",
                        "path": str(dataset),
                        "mount_ids": ["missing"],
                    },
                    request_headers={"If-Match": headers["etag"]},
                )
                self.assertEqual(status, 404, rejected)
                self.assertEqual(config_path.read_bytes(), before)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_batch_remove_harbor_mounts_is_atomic_and_preserves_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs_one = root / "jobs-one"
            jobs_two = root / "jobs-two"
            jobs_one.mkdir()
            jobs_two.mkdir()
            config_path = root / "peval.toml"
            config_path.write_text(
                '[[harbor.mounts]]\nid = "one"\npath = "jobs-one"\n\n'
                '[[harbor.mounts]]\nid = "two"\npath = "jobs-two"\n',
                encoding="utf-8",
            )
            config = ToolConfig(
                workspace_root=str(root),
                harbor_mounts=(
                    HarborMount(id="one", path=str(jobs_one)),
                    HarborMount(id="two", path=str(jobs_two)),
                ),
            )
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, config)
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, headers, inventory = self._get_json(
                    server, "/api/harbor/mounts"
                )
                self.assertEqual(status, 200)
                self.assertEqual([item["id"] for item in inventory], ["one", "two"])
                before = config_path.read_bytes()
                status, rejected = self._request(
                    server,
                    "POST",
                    "/api/harbor/mount-deletion-operations",
                    {"mount_ids": ["one", "missing"]},
                    request_headers={"If-Match": headers["etag"]},
                )
                self.assertEqual(status, 404, rejected)
                self.assertEqual(config_path.read_bytes(), before)

                status, removed = self._request(
                    server,
                    "POST",
                    "/api/harbor/mount-deletion-operations",
                    {"mount_ids": ["one", "two"]},
                    request_headers={"If-Match": headers["etag"]},
                )
                self.assertEqual(status, 202, removed)
                self._wait_operation(server, removed)
                status, _headers, mounts = self._get_json(server, "/api/harbor/mounts")
                self.assertEqual(mounts, [])
                self.assertTrue(jobs_one.is_dir())
                self.assertTrue(jobs_two.is_dir())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_routes_apply_revisions_and_return_safe_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "peval.toml").write_text("", encoding="utf-8")
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, ToolConfig(workspace_root=str(root)))
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, headers, inventory = self._get_json(
                    server, "/api/harbor/datasets"
                )
                self.assertEqual(status, 200)
                status, created = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets",
                    {
                        "source": "new",
                        "id": "tasks",
                        "path": "dataset",
                        "package_name": "local/tasks",
                    },
                    request_headers={"If-Match": headers["etag"]},
                )
                self.assertEqual(status, 202, created)
                self._wait_operation(server, created)

                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                self.assertEqual(status, 200)
                dataset = inventory["datasets"][0]
                status, created_task = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets/tasks/tasks",
                    {
                        "directory": "hello",
                        "package_name": "local/hello",
                        "steps": 0,
                    },
                    request_headers={"If-Match": f'"{dataset["revision"]}"'},
                )
                self.assertEqual(status, 202, created_task)
                self._wait_operation(server, created_task)

                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                dataset = inventory["datasets"][0]
                self.assertTrue(runtime.catalog._writer_lock.acquire(blocking=False))
                try:
                    status, blocked = self._request(
                        server,
                        "PUT",
                        "/api/harbor/datasets/tasks/manifest",
                        {},
                        request_headers={"If-Match": f'"{dataset["revision"]}"'},
                    )
                finally:
                    runtime.catalog._writer_lock.release()
                self.assertEqual(status, 409, blocked)
                self.assertIn("writer operation", blocked["detail"])

                status, synchronized = self._request(
                    server,
                    "PUT",
                    "/api/harbor/datasets/tasks/manifest",
                    {},
                    request_headers={"If-Match": f'"{dataset["revision"]}"'},
                )
                self.assertEqual(status, 200, synchronized)
                self.assertNotIn("manifest_status", synchronized)

                status, detail = self._request(
                    server,
                    "GET",
                    "/api/harbor/datasets/tasks/tasks/hello",
                )
                self.assertEqual(status, 200)
                self.assertEqual(detail["task"]["status"], "valid")
                status, text = self._request(
                    server,
                    "GET",
                    "/api/harbor/datasets/tasks/tasks/hello/files/instruction.md",
                )
                self.assertEqual(status, 200)
                self.assertIn("content", text)

                status, _headers, content = self._request_bytes(
                    server,
                    "/api/harbor/datasets/tasks/tasks/hello/files/"
                    "instruction.md?download=1",
                )
                self.assertEqual(status, 400)
                self.assertNotIn("content-disposition", _headers)
                status, _headers, content = self._request_bytes(
                    server,
                    "/api/harbor/datasets/tasks/tasks/hello/files/"
                    "instruction.md?download=",
                )
                self.assertEqual(status, 400)
                self.assertNotIn("content-disposition", _headers)

                status, conflict = self._request(
                    server,
                    "PUT",
                    "/api/harbor/datasets/tasks/tasks/hello/files/instruction.md",
                    {"content": "changed\n"},
                    request_headers={"If-Match": '"stale"'},
                )
                self.assertEqual(status, 412)
                self.assertIn("refresh", conflict["detail"])

                with patch("psycheval.serve.harbor_workspace.UPLOAD_LIMIT", 2):
                    status, oversized = self._request(
                        server,
                        "POST",
                        "/api/harbor/datasets/tasks/tasks/hello/files",
                        {
                            "kind": "upload",
                            "path": "large.bin",
                            "content": b64encode(b"abc").decode("ascii"),
                        },
                        request_headers={"If-Match": f'"{detail["task"]["revision"]}"'},
                    )
                self.assertEqual(status, 413, oversized)

                status, unsafe = self._request(
                    server,
                    "GET",
                    "/api/harbor/datasets/tasks/tasks/hello/files/%2E%2E%2Fsecret",
                )
                self.assertEqual(status, 400)
                self.assertNotIn(str(root), unsafe["detail"])

                status, renamed = self._request(
                    server,
                    "PATCH",
                    "/api/harbor/datasets/tasks/tasks/hello",
                    {"new_directory": "renamed"},
                    request_headers={"If-Match": f'"{detail["task"]["revision"]}"'},
                )
                self.assertEqual(status, 202, renamed)
                self._wait_operation(server, renamed)
                status, renamed_detail = self._request(
                    server, "GET", "/api/harbor/datasets/tasks/tasks/renamed"
                )
                renamed_task = renamed_detail["task"]
                self.assertEqual(renamed_task["directory"], "renamed")

                status, trashed = self._request(
                    server,
                    "POST",
                    "/api/harbor/task-state-operations",
                    {
                        "archived": True,
                        "items": [
                            {
                                "dataset_id": "tasks",
                                "task": "renamed",
                                "etag": f'"{renamed_task["revision"]}"',
                            }
                        ],
                    },
                )
                self.assertEqual(status, 202, trashed)
                self._wait_operation(server, trashed)

                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                archived = inventory["datasets"][0]["trash"][0]

                status, restored = self._request(
                    server,
                    "POST",
                    "/api/harbor/task-state-operations",
                    {
                        "archived": False,
                        "items": [
                            {
                                "dataset_id": "tasks",
                                "entry_id": archived["entry_id"],
                                "directory": "restored",
                                "etag": f'"{archived["revision"]}"',
                            }
                        ],
                    },
                )
                self.assertEqual(status, 202, restored)
                self._wait_operation(server, restored)

                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                restored_task = inventory["datasets"][0]["tasks"][0]

                status, trashed_again = self._request(
                    server,
                    "POST",
                    "/api/harbor/task-state-operations",
                    {
                        "archived": True,
                        "items": [
                            {
                                "dataset_id": "tasks",
                                "task": "restored",
                                "etag": f'"{restored_task["revision"]}"',
                            }
                        ],
                    },
                )
                self.assertEqual(status, 202, trashed_again)
                self._wait_operation(server, trashed_again)

                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                archived_again = inventory["datasets"][0]["trash"][0]

                status, purged = self._request(
                    server,
                    "POST",
                    "/api/harbor/task-deletion-operations",
                    {
                        "items": [
                            {
                                "dataset_id": "tasks",
                                "entry_id": archived_again["entry_id"],
                                "etag": f'"{archived_again["revision"]}"',
                            }
                        ],
                    },
                )
                self.assertEqual(status, 202, purged)
                self._wait_operation(server, purged)
                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                self.assertEqual(inventory["datasets"][0]["trash"], [])

                status, unknown = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets/tasks/tasks",
                    {
                        "action": "unknown",
                    },
                )
                self.assertEqual(status, 422, unknown)

                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                status, invalid_steps = self._request(
                    server,
                    "POST",
                    "/api/harbor/datasets/tasks/tasks",
                    {
                        "directory": "invalid-steps",
                        "package_name": "local/invalid-steps",
                        "steps": "two",
                    },
                    request_headers={
                        "If-Match": f'"{inventory["datasets"][0]["revision"]}"'
                    },
                )
                self.assertEqual(status, 422, invalid_steps)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_task_batch_isolates_failures_and_active_delete_preserves_manifest(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval.toml"
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
            for directory in ("first", "second"):
                dataset = library.inventory()["datasets"][0]
                library.create_task(
                    dataset_id="tasks",
                    directory=directory,
                    package_name=f"local/{directory}",
                    steps=0,
                    expected_revision=dataset["revision"],
                )
            tasks = {
                task["directory"]: task
                for task in library.inventory()["datasets"][0]["tasks"]
            }
            manifest_before = (root / "dataset" / "dataset.toml").read_bytes()

            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, config)
            server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, operation = self._request(
                    server,
                    "POST",
                    "/api/harbor/task-state-operations",
                    {
                        "archived": True,
                        "items": [
                            {
                                "dataset_id": "tasks",
                                "task": "first",
                                "etag": f'"{tasks["first"]["revision"]}"',
                            },
                            {
                                "dataset_id": "tasks",
                                "task": "second",
                                "etag": '"stale"',
                            },
                        ],
                    },
                )
                self.assertEqual(status, 202, operation)
                completed = self._wait_operation(
                    server, operation, expected_state="failed"
                )
                self.assertEqual(len(completed["successes"]), 1)
                self.assertEqual(len(completed["failures"]), 1)
                self.assertIn("refresh", completed["failures"][0]["error"])

                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                self.assertEqual(status, 200)
                dataset = inventory["datasets"][0]
                self.assertEqual(
                    [task["directory"] for task in dataset["tasks"]], ["second"]
                )
                self.assertEqual(len(dataset["trash"]), 1)

                status, operation = self._request(
                    server,
                    "POST",
                    "/api/harbor/task-deletion-operations",
                    {
                        "items": [
                            {
                                "dataset_id": "tasks",
                                "task": "second",
                                "etag": f'"{dataset["tasks"][0]["revision"]}"',
                            }
                        ]
                    },
                )
                self.assertEqual(status, 202, operation)
                completed = self._wait_operation(server, operation)
                self.assertEqual(len(completed["successes"]), 1)
                status, inventory = self._request(server, "GET", "/api/harbor/datasets")
                self.assertEqual(status, 200)
                self.assertEqual(inventory["datasets"][0]["tasks"], [])
                self.assertEqual(
                    (root / "dataset" / "dataset.toml").read_bytes(),
                    manifest_before,
                )
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
            config_path = root / "peval.toml"
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
                    "/api/harbor/datasets/tasks/tasks",
                )
                self.assertEqual(status, 200)
                self.assertEqual(task_inventory, inventory)

                status, detail = self._request(
                    server,
                    "GET",
                    "/api/harbor/datasets/tasks/tasks/hello",
                )
                self.assertEqual(status, 200)
                paths = {item["path"]: item for item in detail["tree"]}
                self.assertEqual(detail["default_file_path"], "instruction.md")
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
                        "/api/harbor/datasets/tasks/tasks/hello/files/" + path,
                    )
                    self.assertEqual(status, 200)
                    self.assertEqual(set(text), {"path", "content"})

                status, headers, content = self._request_bytes(
                    server,
                    "/api/harbor/datasets/tasks/tasks/hello/files/"
                    "solution/solve.sh?download=1",
                )
                self.assertEqual(status, 400, content)
                self.assertNotIn("content-disposition", headers)
                self.assertIn(b"downloads are not supported", content)
                status, blocked = self._request(
                    server,
                    "PUT",
                    "/api/harbor/datasets/tasks/tasks/hello/files/instruction.md",
                    {"content": "blocked"},
                )
                self.assertEqual(status, 403, blocked)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()


if __name__ == "__main__":
    unittest.main()
