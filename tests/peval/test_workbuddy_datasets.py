from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from psycheval._harbor_datasets import harbor_task_roots_for_mount
from psycheval.config import (
    HarborDataset,
    HarborMount,
    ToolConfig,
    load_config,
)
from psycheval.harbor.datasets import (
    HarborDatasetError,
    _walk_regular_tree,
    resolve_harbor_dataset,
    validate_harbor_dataset,
)
from psycheval.serve.harbor_workspace import (
    HarborWorkspace,
    HarborWorkspaceError,
    config_revision,
)


def _write_workbuddy_bundle(root: Path, *, declared_count: int = 1) -> Path:
    task = root / "tasks" / "office-one"
    task.mkdir(parents=True)
    (root / "shared" / "verifier").mkdir(parents=True)
    (task / "environment").mkdir()
    (task / "tests" / "grading").mkdir(parents=True)
    (task / "tests" / "gold").mkdir()
    (root / "dataset.toml").write_text(
        f"""[dataset]
id = "wb-bench-office-v1.0"
schema = "workbuddy.dataset.v1"
version = "1.0"
task_count = {declared_count}

[verifier]
schema = "workbuddy.verifier.v1"
engine = "composite"

[layout]
task_root = "tasks"
environment = "environment"
workspace_archive = "environment/workspace.tar.gz"
tests = "tests"
grading_tests = "tests/grading"
gold = "tests/gold"
judge_config = "tests/judge.yaml"
""",
        encoding="utf-8",
    )
    for name in ("plugin.py", "manifest.py", "scoring.py"):
        (root / "shared" / "verifier" / name).write_text("# fixture\n")
    (task / "task.toml").write_text(
        'schema_version = "1.3"\n[task]\nname = "workbuddy/office-one"\n',
        encoding="utf-8",
    )
    (task / "instruction.md").write_text("Create the requested artifact.\n")
    (task / "environment" / "workspace.tar.gz").write_bytes(b"not-lfs")
    (task / "tests" / "judge.yaml").write_text("criteria: []\n")
    (task / "tests" / "test.sh").write_text("#!/bin/sh\nexit 0\n")
    return root


class WorkBuddyDatasetTests(unittest.TestCase):
    def test_partial_registration_survives_config_mount_and_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = _write_workbuddy_bundle(root / "bundle", declared_count=50)
            config_path = root / "peval.toml"
            config_path.write_text("")
            library = HarborWorkspace(config_path, ToolConfig(workspace_root=str(root)))
            before = (bundle / "dataset.toml").read_bytes()
            with self.assertRaisesRegex(HarborWorkspaceError, "declares 50, found 1"):
                library.register_dataset(
                    dataset_id="office",
                    path=str(bundle),
                    expected_revision=config_revision(config_path),
                )
            config = library.register_dataset(
                dataset_id="office",
                path=str(bundle),
                allow_partial=True,
                expected_revision=config_revision(config_path),
            )
            self.assertTrue(config.harbor_datasets[0].allow_partial)
            loaded = load_config(workspace_root=root)
            self.assertTrue(loaded.harbor_datasets[0].allow_partial)
            mount = HarborMount(
                id="jobs", path=str(root / "jobs"), dataset_ids=("office",)
            )
            self.assertEqual(
                harbor_task_roots_for_mount(loaded, mount), (str(bundle / "tasks"),)
            )
            library = HarborWorkspace(config_path, loaded)
            updated = library.update_dataset(
                dataset_id="office",
                new_id="cropped",
                path=str(bundle),
                mount_ids=[],
                expected_revision=config_revision(config_path),
            )
            self.assertTrue(updated.harbor_datasets[0].allow_partial)
            self.assertEqual((bundle / "dataset.toml").read_bytes(), before)

    def test_config_loading_is_lightweight_but_registration_validates_content(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = _write_workbuddy_bundle(root / "bundle")
            (bundle / "shared" / "verifier" / "plugin.py").unlink()
            config_path = root / "peval.toml"
            config_path.write_text(
                '[[harbor.datasets]]\nid = "office"\npath = "bundle"\n'
                'format = "workbuddy.v1"\n',
                encoding="utf-8",
            )

            config = load_config(workspace_root=root)
            self.assertEqual(config.harbor_datasets[0].path, str(bundle.resolve()))
            with self.assertRaisesRegex(HarborDatasetError, "plugin.py"):
                validate_harbor_dataset(
                    dataset_id="office", path=bundle, format="workbuddy.v1"
                )

            config_path.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(HarborWorkspaceError, "plugin.py"):
                HarborWorkspace(
                    config_path, ToolConfig(workspace_root=str(root))
                ).register_dataset(
                    dataset_id="office",
                    path=str(bundle),
                    expected_revision=config_revision(config_path),
                )
            self.assertEqual(config_path.read_text(encoding="utf-8"), "")

    def test_workbuddy_bundle_rejects_an_empty_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            (bundle / "tasks").mkdir(parents=True)
            (bundle / "dataset.toml").write_text(
                "[dataset]\n"
                'schema = "workbuddy.dataset.v1"\n'
                "task_count = 0\n\n"
                "[verifier]\n"
                'schema = "workbuddy.verifier.v1"\n'
                'engine = "composite"\n\n'
                "[layout]\n"
                'task_root = "tasks"\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                HarborDatasetError, "task_count must be a positive integer"
            ):
                resolve_harbor_dataset(
                    dataset_id="office", path=str(bundle), format="workbuddy.v1"
                )

    def test_resolver_exposes_nested_task_root_and_read_only_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_workbuddy_bundle(Path(tmp) / "bundle")
            resolved = resolve_harbor_dataset(
                dataset_id="office", path=str(bundle), format="workbuddy.v1"
            )

            self.assertEqual(resolved.source_root, bundle)
            self.assertEqual(resolved.task_root, bundle / "tasks")
            self.assertEqual(resolved.format, "workbuddy.v1")
            self.assertTrue(resolved.read_only)
            self.assertEqual(resolved.task_names, ("office-one",))
            self.assertEqual(resolved.manifest["dataset"]["task_count"], 1)

    def test_explicit_workbuddy_bundle_rejects_an_invalid_harbor_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_workbuddy_bundle(Path(tmp) / "bundle")
            (bundle / "tasks" / "office-one" / "task.toml").write_text(
                "not valid = [", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                HarborDatasetError, "invalid Harbor Task office-one"
            ):
                validate_harbor_dataset(
                    dataset_id="office", path=str(bundle), format="workbuddy.v1"
                )

    def test_explicit_workbuddy_bundle_rejects_an_oversized_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_workbuddy_bundle(Path(tmp) / "bundle")
            with (bundle / "dataset.toml").open("ab") as stream:
                stream.truncate(256 * 1024 + 1)

            with self.assertRaisesRegex(HarborDatasetError, "exceeds 262144 bytes"):
                validate_harbor_dataset(
                    dataset_id="office", path=str(bundle), format="workbuddy.v1"
                )

    @unittest.skipUnless(
        getattr(os, "O_NONBLOCK", 0), "non-blocking opens are unavailable"
    )
    def test_validation_opens_bundle_files_nonblocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_workbuddy_bundle(Path(tmp) / "bundle")
            real_open = os.open
            opened_flags: list[int] = []

            def recording_open(
                path: str | bytes | os.PathLike[str],
                flags: int,
                *args: object,
                **kwargs: object,
            ) -> int:
                if Path(path).is_relative_to(bundle):
                    opened_flags.append(flags)
                return real_open(path, flags, *args, **kwargs)

            with patch("psycheval.harbor.datasets.os.open", recording_open):
                validate_harbor_dataset(
                    dataset_id="office", path=str(bundle), format="workbuddy.v1"
                )

            self.assertTrue(opened_flags)
            self.assertTrue(
                all(flags & os.O_NONBLOCK for flags in opened_flags), opened_flags
            )

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_explicit_workbuddy_bundle_rejects_linked_task_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = _write_workbuddy_bundle(root / "bundle")
            outside = root / "outside.txt"
            outside.write_text("private", encoding="utf-8")
            (bundle / "tasks" / "office-one" / "linked.txt").symlink_to(outside)
            with self.assertRaisesRegex(HarborDatasetError, "symbolic link"):
                validate_harbor_dataset(
                    dataset_id="office", path=str(bundle), format="workbuddy.v1"
                )

    def test_registration_canonicalizes_symlink_and_persists_detected_format(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            config_path = workspace / "peval.toml"
            config_path.write_text("")
            bundle = _write_workbuddy_bundle(root / "physical")
            linked = root / "linked"
            linked.symlink_to(bundle, target_is_directory=True)

            configured = HarborWorkspace(
                config_path, ToolConfig(workspace_root=str(workspace))
            ).register_dataset(
                dataset_id="office",
                path=str(linked),
                expected_revision=config_revision(config_path),
            )

            self.assertEqual(configured.harbor_datasets[0].path, str(bundle.resolve()))
            self.assertEqual(configured.harbor_datasets[0].format, "workbuddy.v1")
            loaded = load_config(workspace_root=workspace)
            self.assertEqual(loaded.harbor_datasets[0].format, "workbuddy.v1")
            inventory = HarborWorkspace(config_path, loaded).inventory()["datasets"][0]
            self.assertEqual(inventory["format"], "workbuddy.v1")
            self.assertTrue(inventory["read_only"])
            self.assertEqual(
                [item["directory"] for item in inventory["tasks"]], ["office-one"]
            )

    def test_malformed_workbuddy_bundle_fails_without_generic_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval.toml"
            config_path.write_text("")
            bundle = _write_workbuddy_bundle(root / "bundle", declared_count=2)

            with self.assertRaisesRegex(HarborWorkspaceError, "task_count"):
                HarborWorkspace(
                    config_path, ToolConfig(workspace_root=str(root))
                ).register_dataset(
                    dataset_id="office",
                    path=str(bundle),
                    expected_revision=config_revision(config_path),
                )

    def test_workbuddy_mutations_are_rejected_but_text_remains_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval.toml"
            config_path.write_text("")
            bundle = _write_workbuddy_bundle(root / "bundle")
            config = ToolConfig(
                workspace_root=str(root),
                harbor_datasets=(
                    HarborDataset(id="office", path=str(bundle), format="workbuddy.v1"),
                ),
            )
            library = HarborWorkspace(config_path, config)

            detail = library.task_detail("office", "office-one")
            content = library.read_file("office", "office-one", "instruction.md")
            self.assertTrue(detail["read_only"])
            self.assertTrue(detail["tree"])
            self.assertTrue(
                all(not item.get("editable", False) for item in detail["tree"])
            )
            self.assertIn("requested artifact", content["content"])
            with self.assertRaisesRegex(HarborWorkspaceError, "read-only"):
                library.mutate_file(
                    "save",
                    {
                        "dataset_id": "office",
                        "task": "office-one",
                        "path": "instruction.md",
                        "content": "changed",
                        "expected_revision": detail["task"]["revision"],
                    },
                )

    def test_mount_task_paths_use_effective_workbuddy_task_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = _write_workbuddy_bundle(root / "bundle")
            config = ToolConfig(
                harbor_datasets=(
                    HarborDataset(id="office", path=str(bundle), format="workbuddy.v1"),
                ),
                harbor_mounts=(
                    HarborMount(id="jobs", path=str(root), dataset_ids=("office",)),
                ),
            )

            self.assertEqual(
                harbor_task_roots_for_mount(config, config.harbor_mounts[0]),
                (str(bundle / "tasks"),),
            )

    def test_mount_task_root_lookup_does_not_revalidate_task_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = _write_workbuddy_bundle(root / "bundle")
            dataset = HarborDataset(
                id="office", path=str(bundle), format="workbuddy.v1"
            )
            mount = HarborMount(id="jobs", path=str(root), dataset_ids=(dataset.id,))
            config = ToolConfig(harbor_datasets=(dataset,), harbor_mounts=(mount,))

            with patch("psycheval.harbor.datasets._walk_regular_tree") as walk:
                self.assertEqual(
                    harbor_task_roots_for_mount(config, mount),
                    (str(bundle / "tasks"),),
                )

            walk.assert_not_called()

    def test_read_only_inventory_does_not_hash_or_validate_every_task_tree(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval.toml"
            config_path.write_text("")
            bundle = _write_workbuddy_bundle(root / "bundle")
            config = ToolConfig(
                workspace_root=str(root),
                harbor_datasets=(
                    HarborDataset(id="office", path=str(bundle), format="workbuddy.v1"),
                ),
            )

            with (
                patch(
                    "psycheval.serve.harbor_workspace._directory_revision",
                    side_effect=AssertionError("read-only inventory hashed a tree"),
                ),
                patch(
                    "psycheval.serve.harbor_workspace._validate_task",
                    side_effect=AssertionError("read-only inventory validated a Task"),
                ),
            ):
                inventory = HarborWorkspace(config_path, config).inventory()

            task = inventory["datasets"][0]["tasks"][0]
            self.assertEqual(task["directory"], "office-one")
            self.assertEqual(task["status"], "registered")

    def test_read_only_task_detail_validates_only_the_selected_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "peval.toml"
            config_path.write_text("")
            bundle = _write_workbuddy_bundle(root / "bundle")
            config = ToolConfig(
                workspace_root=str(root),
                harbor_datasets=(
                    HarborDataset(id="office", path=str(bundle), format="workbuddy.v1"),
                ),
            )

            with (
                patch.object(
                    HarborWorkspace,
                    "_task_summaries",
                    side_effect=AssertionError("detail enumerated every Task"),
                ),
                patch(
                    "psycheval.serve.harbor_workspace._directory_revision",
                    side_effect=AssertionError("read-only detail hashed file bodies"),
                ),
            ):
                library = HarborWorkspace(config_path, config)
                detail = library.task_detail("office", "office-one")
                content = library.read_file("office", "office-one", "instruction.md")
                (
                    bundle / "tasks" / "office-one" / "environment" / "workspace.tar.gz"
                ).write_bytes(b"changed-archive-payload")
                changed = library.task_detail("office", "office-one")

            self.assertEqual(detail["task"]["directory"], "office-one")
            self.assertEqual(detail["task"]["status"], "valid")
            self.assertEqual(detail["default_file_path"], "instruction.md")
            self.assertEqual(content["task_revision"], detail["task"]["revision"])
            self.assertNotEqual(changed["task"]["revision"], detail["task"]["revision"])

    def test_mount_path_resolution_touches_only_referenced_datasets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = HarborDataset(id="first", path=str(root / "first"))
            second = HarborDataset(id="second", path=str(root / "second"))
            mount = HarborMount(id="jobs", path=str(root), dataset_ids=("second",))
            config = ToolConfig(harbor_datasets=(first, second), harbor_mounts=(mount,))
            (root / "second" / "only-task").mkdir(parents=True)

            paths = harbor_task_roots_for_mount(config, mount)

            self.assertEqual(paths, (str(root / "second"),))
            self.assertFalse((root / "first").exists())

    def test_task_tree_walk_is_not_limited_by_python_recursion_depth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root
            for _index in range(250):
                current /= "d"
                current.mkdir()
            previous_limit = sys.getrecursionlimit()
            try:
                sys.setrecursionlimit(200)
                _walk_regular_tree(root)
            finally:
                sys.setrecursionlimit(previous_limit)


if __name__ == "__main__":
    unittest.main()
