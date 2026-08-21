from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from uuid import uuid4

from harbor.models.dataset.manifest import DatasetInfo, DatasetManifest, DatasetTaskRef
from harbor.models.task.config import PackageInfo, TaskConfig
from harbor.models.task.task import Task
from harbor.publisher.packager import Packager

from peval_py.config import (
    HarborDataset,
    ToolConfig,
    write_workspace_harbor_config,
)

TEXT_EDIT_LIMIT = 2 * 1024 * 1024
UPLOAD_LIMIT = 16 * 1024 * 1024
DOWNLOAD_LIMIT = 20 * 1024 * 1024
TRASH_DIRNAME = ".peval-py-trash"
TRASH_METADATA = "metadata.json"
TASK_DIR_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$")
DATASET_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,62}[a-z0-9])?$")


class HarborWorkspaceError(ValueError):
    """A safe, user-facing Harbor workspace error."""


class HarborConflictError(HarborWorkspaceError):
    """The requested mutation conflicts with current workspace state."""


class HarborNotFoundError(HarborWorkspaceError):
    """The requested Dataset, Task, or file no longer exists."""


class HarborSizeError(HarborWorkspaceError):
    """The requested content exceeds a workbench limit."""


def config_revision(config_path: Path) -> str:
    try:
        content = _read_regular_file(config_path, limit=None)
    except FileNotFoundError:
        content = b""
    return hashlib.sha256(content).hexdigest()


class HarborWorkspace:
    """Owns safe Dataset registration, Task lifecycle, and file mutations."""

    def __init__(self, config_path: Path, config: ToolConfig) -> None:
        self.config_path = config_path.expanduser()
        self.config = config

    def inventory(self) -> dict[str, Any]:
        return {
            "revision": config_revision(self.config_path),
            "datasets": [
                self._dataset_summary(item) for item in self.config.harbor_datasets
            ],
        }

    def task_inventory(self, dataset_id: str | None = None) -> dict[str, Any]:
        datasets = self.config.harbor_datasets
        if dataset_id is not None:
            datasets = (self._dataset(dataset_id),)
        return {
            "revision": config_revision(self.config_path),
            "datasets": [self._dataset_summary(item) for item in datasets],
        }

    def create_dataset(
        self,
        *,
        dataset_id: str,
        path: str,
        package_name: str,
        description: str = "",
        expected_revision: str,
    ) -> ToolConfig:
        self._expect_config_revision(expected_revision)
        self._validate_dataset_id(dataset_id)
        if any(item.id == dataset_id for item in self.config.harbor_datasets):
            raise HarborConflictError(f"Dataset id already exists: {dataset_id}")
        root = self._config_path(path)
        self._ensure_unique_dataset_path(root)
        try:
            dataset_info = DatasetInfo(
                name=package_name,
                version="1.0.0",
                description=description,
            )
        except ValueError as exc:
            raise HarborWorkspaceError(str(exc)) from exc
        if root.exists():
            if not root.is_dir() or root.is_symlink():
                raise HarborConflictError("Dataset path is not a regular directory")
            if any(root.iterdir()):
                raise HarborConflictError("New Dataset path must be empty")
            created_root = False
        else:
            _assert_unlinked_ancestors(root.parent)
            root.mkdir(parents=True)
            created_root = True
        try:
            manifest = DatasetManifest(dataset=dataset_info)
            _atomic_write(root / "dataset.toml", manifest.to_toml().encode("utf-8"))
            _atomic_write(root / "README.md", f"# {package_name}\n".encode("utf-8"))
            return self._save_config(
                (*self.config.harbor_datasets, HarborDataset(dataset_id, str(root))),
                self.config.harbor_mounts,
            )
        except Exception:
            if created_root:
                shutil.rmtree(root, ignore_errors=True)
            else:
                (root / "dataset.toml").unlink(missing_ok=True)
                (root / "README.md").unlink(missing_ok=True)
            raise

    def register_dataset(
        self,
        *,
        dataset_id: str,
        path: str,
        expected_revision: str,
    ) -> ToolConfig:
        self._expect_config_revision(expected_revision)
        self._validate_dataset_id(dataset_id)
        if any(item.id == dataset_id for item in self.config.harbor_datasets):
            raise HarborConflictError(f"Dataset id already exists: {dataset_id}")
        root = self._config_path(path)
        self._ensure_unique_dataset_path(root)
        self._validate_dataset_directory(root)
        return self._save_config(
            (*self.config.harbor_datasets, HarborDataset(dataset_id, str(root))),
            self.config.harbor_mounts,
        )

    def update_dataset(
        self,
        *,
        dataset_id: str,
        new_id: str,
        path: str,
        expected_revision: str,
    ) -> ToolConfig:
        self._expect_config_revision(expected_revision)
        current = self._dataset(dataset_id)
        self._validate_dataset_id(new_id)
        if new_id != dataset_id and any(
            item.id == new_id for item in self.config.harbor_datasets
        ):
            raise HarborConflictError(f"Dataset id already exists: {new_id}")
        root = self._config_path(path)
        self._ensure_unique_dataset_path(root, excluding=dataset_id)
        self._validate_dataset_directory(root)
        datasets = tuple(
            HarborDataset(new_id, str(root)) if item.id == current.id else item
            for item in self.config.harbor_datasets
        )
        mounts = tuple(
            replace(
                mount,
                dataset_ids=tuple(
                    new_id if item == dataset_id else item for item in mount.dataset_ids
                ),
            )
            for mount in self.config.harbor_mounts
        )
        return self._save_config(datasets, mounts)

    def remove_dataset(self, *, dataset_id: str, expected_revision: str) -> ToolConfig:
        self._expect_config_revision(expected_revision)
        self._dataset(dataset_id)
        referencing = [
            mount.id
            for mount in self.config.harbor_mounts
            if dataset_id in mount.dataset_ids
        ]
        if referencing:
            raise HarborConflictError(
                f"Dataset {dataset_id} is referenced by mount(s): {', '.join(referencing)}"
            )
        return self._save_config(
            tuple(
                item for item in self.config.harbor_datasets if item.id != dataset_id
            ),
            self.config.harbor_mounts,
        )

    def create_task(
        self,
        *,
        dataset_id: str,
        directory: str,
        package_name: str,
        steps: int,
        expected_revision: str,
    ) -> dict[str, Any]:
        dataset = self._dataset(dataset_id)
        root = self._dataset_root(dataset)
        self._expect_revision(root, expected_revision)
        task_name = self._task_directory(directory)
        target = root / task_name
        if target.exists():
            raise HarborConflictError(f"Task directory already exists: {task_name}")
        if steps < 0 or steps > 50:
            raise HarborWorkspaceError("steps must be between 0 and 50")
        try:
            package = PackageInfo(name=package_name, version="1.0.0")
        except ValueError as exc:
            raise HarborWorkspaceError(str(exc)) from exc
        staging = root / f".peval-py-staging-{uuid4().hex}"
        try:
            self._write_task_scaffold(staging, package, steps)
            staging.replace(target)
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
        return self.task_detail(dataset_id, task_name)

    def rename_task(
        self,
        *,
        dataset_id: str,
        task: str,
        new_directory: str,
        expected_revision: str,
    ) -> dict[str, Any]:
        dataset = self._dataset(dataset_id)
        root = self._dataset_root(dataset)
        source = self._task_path(root, task)
        self._expect_revision(source, expected_revision)
        new_name = self._task_directory(new_directory)
        target = root / new_name
        if target.exists():
            raise HarborConflictError(f"Task directory already exists: {new_name}")
        source.replace(target)
        return self.task_detail(dataset_id, new_name)

    def trash_task(
        self,
        *,
        dataset_id: str,
        task: str,
        expected_revision: str,
    ) -> dict[str, Any]:
        dataset = self._dataset(dataset_id)
        root = self._dataset_root(dataset)
        source = self._task_path(root, task)
        self._expect_revision(source, expected_revision)
        package_name = self._task_package_name(source)
        deleted_at = datetime.now(UTC).isoformat()
        entry_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:12]}"
        entry = root / TRASH_DIRNAME / entry_id
        entry.mkdir(parents=True)
        metadata = {
            "dataset_id": dataset_id,
            "directory": source.name,
            "package_name": package_name,
            "deleted_at": deleted_at,
        }
        try:
            _atomic_write(
                entry / TRASH_METADATA,
                json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8")
                + b"\n",
            )
            source.replace(entry / "task")
        except Exception:
            if (entry / "task").exists() and not source.exists():
                (entry / "task").replace(source)
            shutil.rmtree(entry, ignore_errors=True)
            raise
        return self._trash_summary(dataset, entry)

    def restore_task(
        self,
        *,
        dataset_id: str,
        entry_id: str,
        directory: str | None,
        expected_revision: str,
    ) -> dict[str, Any]:
        dataset = self._dataset(dataset_id)
        root = self._dataset_root(dataset)
        entry = self._trash_entry(root, entry_id)
        self._expect_revision(entry, expected_revision)
        metadata = self._trash_metadata(entry)
        metadata_path = entry / TRASH_METADATA
        metadata_bytes = _read_regular_file(metadata_path, limit=TEXT_EDIT_LIMIT)
        target_name = self._task_directory(directory or str(metadata["directory"]))
        target = root / target_name
        if target.exists():
            raise HarborConflictError(f"Task directory already exists: {target_name}")
        (entry / "task").replace(target)
        try:
            metadata_path.unlink()
            entry.rmdir()
        except Exception as exc:
            try:
                entry.mkdir(parents=True, exist_ok=True)
                target.replace(entry / "task")
                if not metadata_path.exists():
                    _atomic_write(metadata_path, metadata_bytes)
            except Exception as rollback_exc:
                raise HarborWorkspaceError(
                    "Task restore cleanup failed and rollback did not complete"
                ) from rollback_exc
            raise HarborWorkspaceError(
                "Task restore cleanup failed; restore was rolled back"
            ) from exc
        return self.task_detail(dataset_id, target_name)

    def purge_task(
        self,
        *,
        dataset_id: str,
        entry_id: str,
        expected_revision: str,
    ) -> dict[str, Any]:
        dataset = self._dataset(dataset_id)
        root = self._dataset_root(dataset)
        entry = self._trash_entry(root, entry_id)
        self._expect_revision(entry, expected_revision)
        shutil.rmtree(entry)
        return self.task_inventory(dataset_id)

    def task_detail(self, dataset_id: str, task: str) -> dict[str, Any]:
        dataset = self._dataset(dataset_id)
        root = self._dataset_root(dataset)
        task_dir = self._task_path(root, task)
        summary = next(
            (
                item
                for item in self._task_summaries(root)
                if item["directory"] == task_dir.name
            ),
            self._task_summary(task_dir),
        )
        return {
            "dataset_id": dataset_id,
            "task": summary,
            "tree": self._file_tree(task_dir),
        }

    def read_file(
        self, dataset_id: str, task: str, relative_path: str, *, download: bool
    ) -> dict[str, Any]:
        task_dir = self._task_path(self._dataset_root(self._dataset(dataset_id)), task)
        path = self._safe_task_file(task_dir, relative_path, must_exist=True)
        limit = DOWNLOAD_LIMIT if download else TEXT_EDIT_LIMIT
        content = _read_regular_file(path, limit=limit)
        revision = _file_revision(content)
        if download:
            return {
                "name": re.sub(r"[^A-Za-z0-9._-]", "_", path.name) or "download.bin",
                "content": content,
                "revision": revision,
                "task_revision": _directory_revision(task_dir),
            }
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HarborWorkspaceError("Binary files must be downloaded") from exc
        return {
            "path": relative_path,
            "content": text,
            "revision": revision,
            "task_revision": _directory_revision(task_dir),
        }

    def mutate_file(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        dataset_id = _required_string(payload, "dataset_id")
        task_name = _required_string(payload, "task")
        task_dir = self._task_path(
            self._dataset_root(self._dataset(dataset_id)), task_name
        )
        self._expect_revision(task_dir, _required_string(payload, "expected_revision"))
        relative = _required_string(payload, "path")
        if action == "save":
            content = payload.get("content")
            if not isinstance(content, str):
                raise HarborWorkspaceError("content must be a string")
            data = content.encode("utf-8")
            if len(data) > TEXT_EDIT_LIMIT:
                raise HarborSizeError("Text files are limited to 2 MiB")
            path = self._safe_task_file(task_dir, relative, must_exist=True)
            _atomic_write(path, data)
        elif action == "upload":
            encoded = payload.get("content_base64")
            if not isinstance(encoded, str):
                raise HarborWorkspaceError("content_base64 must be a string")
            try:
                data = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise HarborWorkspaceError("content_base64 is invalid") from exc
            if len(data) > UPLOAD_LIMIT:
                raise HarborSizeError("Uploads are limited to 16 MiB")
            path = self._safe_task_file(task_dir, relative, must_exist=False)
            if path.exists():
                raise HarborConflictError(f"File already exists: {relative}")
            path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(path, data)
        elif action == "create":
            kind = str(payload.get("kind") or "file")
            path = self._safe_task_file(task_dir, relative, must_exist=False)
            if path.exists():
                raise HarborConflictError(f"Path already exists: {relative}")
            if kind == "directory":
                path.mkdir(parents=False)
            elif kind == "file":
                path.parent.mkdir(parents=True, exist_ok=True)
                _atomic_write(path, b"")
            else:
                raise HarborWorkspaceError("kind must be file or directory")
        elif action == "rename":
            destination = self._safe_task_file(
                task_dir,
                _required_string(payload, "new_path"),
                must_exist=False,
            )
            source = self._safe_task_file(task_dir, relative, must_exist=True)
            if destination.exists():
                raise HarborConflictError("Destination already exists")
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.replace(destination)
        elif action == "delete":
            path = self._safe_task_file(task_dir, relative, must_exist=True)
            if path.is_dir():
                _walk_tree(path)
                shutil.rmtree(path)
            else:
                path.unlink()
        else:
            raise HarborWorkspaceError(f"Unknown file action: {action}")
        return self.task_detail(dataset_id, task_name)

    def sync_manifest(
        self, *, dataset_id: str, expected_revision: str
    ) -> dict[str, Any]:
        dataset = self._dataset(dataset_id)
        root = self._dataset_root(dataset)
        self._expect_revision(root, expected_revision)
        manifest_path = root / "dataset.toml"
        try:
            manifest = DatasetManifest.from_toml_file(manifest_path)
        except (OSError, ValueError) as exc:
            raise HarborWorkspaceError(
                f"Invalid dataset.toml: {_safe_diagnostic(exc, root, '<dataset>')}"
            ) from exc
        incoming: list[DatasetTaskRef] = []
        for summary in self._task_summaries(root):
            if summary["status"] == "valid":
                incoming.append(_task_ref(root / str(summary["directory"])))
        by_name = {item.name: item for item in manifest.tasks}
        order = [item.name for item in manifest.tasks]
        trashed_names = {
            str(item.get("package_name"))
            for item in self._trash_metadata_items(root)
            if item.get("package_name")
        }
        order = [name for name in order if name not in trashed_names]
        for name in trashed_names:
            by_name.pop(name, None)
        for item in incoming:
            if item.name not in by_name:
                order.append(item.name)
            by_name[item.name] = item
        manifest.tasks = [by_name[name] for name in order]
        self._expect_revision(root, expected_revision)
        _atomic_write(manifest_path, manifest.to_toml().encode("utf-8"))
        return self._dataset_summary(dataset)

    def _dataset_summary(self, dataset: HarborDataset) -> dict[str, Any]:
        root = self._dataset_root(dataset)
        tasks = self._task_summaries(root)
        trash_root = root / TRASH_DIRNAME
        trash = []
        if trash_root.exists():
            _assert_safe_directory(root, trash_root)
            trash = [
                self._trash_summary(dataset, entry) for entry in _child_dirs(trash_root)
            ]
        return {
            "id": dataset.id,
            "path": dataset.path,
            "revision": _directory_revision(root),
            "root_files": {
                name: _regular_path(root / name)
                for name in ("dataset.toml", "README.md", "metric.py")
            },
            "tasks": tasks,
            "trash": trash,
        }

    def _task_summary(self, task_dir: Path) -> dict[str, Any]:
        try:
            revision = _directory_revision(task_dir)
        except HarborWorkspaceError as exc:
            return {
                "directory": task_dir.name,
                "status": "conflict",
                "revision": hashlib.sha256(str(exc).encode()).hexdigest(),
                "diagnostics": [str(exc)],
                "package_name": None,
            }
        valid, diagnostic = _validate_task(task_dir)
        package_name = self._task_package_name(task_dir)
        return {
            "directory": task_dir.name,
            "status": "valid" if valid else "draft",
            "revision": revision,
            "diagnostics": [] if valid else [diagnostic or "Invalid Harbor Task"],
            "package_name": package_name,
        }

    def _task_summaries(self, root: Path) -> list[dict[str, Any]]:
        summaries = [self._task_summary(path) for path in self._task_dirs(root)]
        package_counts: dict[str, int] = {}
        for summary in summaries:
            package_name = summary.get("package_name")
            if summary["status"] == "valid" and package_name:
                package_counts[str(package_name)] = (
                    package_counts.get(str(package_name), 0) + 1
                )
        for summary in summaries:
            package_name = summary.get("package_name")
            if package_name and package_counts.get(str(package_name), 0) > 1:
                summary["status"] = "conflict"
                summary["diagnostics"] = [
                    f"Duplicate Task package identity: {package_name}"
                ]
        return summaries

    def _trash_summary(self, dataset: HarborDataset, entry: Path) -> dict[str, Any]:
        _assert_safe_directory(Path(dataset.path), entry)
        metadata = self._trash_metadata(entry)
        return {
            "entry_id": entry.name,
            "status": "trash",
            "revision": _directory_revision(entry),
            **metadata,
        }

    def _trash_metadata(self, entry: Path) -> dict[str, Any]:
        try:
            value = json.loads(
                _read_regular_file(entry / TRASH_METADATA, limit=TEXT_EDIT_LIMIT)
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise HarborWorkspaceError(
                f"Invalid trash metadata for {entry.name}"
            ) from exc
        if not isinstance(value, dict):
            raise HarborWorkspaceError(f"Invalid trash metadata for {entry.name}")
        return value

    def _trash_metadata_items(self, root: Path) -> Iterable[dict[str, Any]]:
        trash_root = root / TRASH_DIRNAME
        if not trash_root.exists():
            return ()
        return tuple(self._trash_metadata(entry) for entry in _child_dirs(trash_root))

    def _file_tree(self, task_dir: Path) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for path in _walk_tree(task_dir):
            relative = path.relative_to(task_dir).as_posix()
            value = path.stat(follow_symlinks=False)
            item = {
                "path": relative,
                "kind": "directory" if stat.S_ISDIR(value.st_mode) else "file",
                "size": value.st_size if stat.S_ISREG(value.st_mode) else None,
            }
            if stat.S_ISREG(value.st_mode):
                item["editable"] = value.st_size <= TEXT_EDIT_LIMIT and _is_utf8(path)
                item["downloadable"] = value.st_size <= DOWNLOAD_LIMIT
            result.append(item)
        return result

    def _save_config(
        self,
        datasets: tuple[HarborDataset, ...],
        mounts: tuple[Any, ...],
    ) -> ToolConfig:
        try:
            saved_datasets, saved_mounts = write_workspace_harbor_config(
                self.config_path,
                datasets,
                mounts,
            )
        except ValueError as exc:
            raise HarborWorkspaceError(str(exc)) from exc
        return replace(
            self.config,
            harbor_datasets=saved_datasets,
            harbor_mounts=saved_mounts,
        )

    def _dataset(self, dataset_id: str) -> HarborDataset:
        for dataset in self.config.harbor_datasets:
            if dataset.id == dataset_id:
                return dataset
        raise HarborNotFoundError(f"Dataset not found: {dataset_id}")

    def _dataset_root(self, dataset: HarborDataset) -> Path:
        root = Path(dataset.path)
        self._validate_dataset_directory(root)
        return root

    def _validate_dataset_directory(self, root: Path) -> None:
        _assert_safe_directory(root, root)

    def _task_dirs(self, root: Path) -> list[Path]:
        result: list[Path] = []
        with os.scandir(root) as entries:
            for entry in sorted(entries, key=lambda value: value.name.casefold()):
                if entry.name.startswith("."):
                    continue
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    result.append(Path(entry.path))
        return result

    def _task_path(self, root: Path, task: str) -> Path:
        name = self._task_directory(task)
        path = root / name
        _assert_safe_directory(root, path)
        return path

    def _trash_entry(self, root: Path, entry_id: str) -> Path:
        name = self._task_directory(entry_id)
        path = root / TRASH_DIRNAME / name
        _assert_safe_directory(root, path)
        if not (path / "task").is_dir():
            raise HarborNotFoundError(f"Trash entry not found: {entry_id}")
        return path

    def _safe_task_file(
        self, task_dir: Path, relative_path: str, *, must_exist: bool
    ) -> Path:
        relative = _safe_relative_path(relative_path)
        path = task_dir.joinpath(*relative.parts)
        _assert_safe_child(task_dir, path, allow_missing=not must_exist)
        if must_exist and not path.exists():
            raise HarborNotFoundError(f"Task path not found: {relative_path}")
        return path

    def _expect_config_revision(self, expected: str) -> None:
        actual = config_revision(self.config_path)
        if not expected or expected != actual:
            raise HarborConflictError(
                "Workspace configuration changed; refresh before saving"
            )

    def _expect_revision(self, path: Path, expected: str) -> None:
        actual = _directory_revision(path)
        if not expected or expected != actual:
            raise HarborConflictError("Content changed; refresh before saving")

    def _ensure_unique_dataset_path(
        self, path: Path, *, excluding: str | None = None
    ) -> None:
        identity = os.path.normcase(os.path.normpath(path))
        for dataset in self.config.harbor_datasets:
            if (
                dataset.id != excluding
                and os.path.normcase(os.path.normpath(dataset.path)) == identity
            ):
                raise HarborConflictError(f"Dataset path already registered: {path}")

    def _config_path(self, value: str) -> Path:
        text = str(value).strip()
        if not text:
            raise HarborWorkspaceError("Dataset path must not be empty")
        if any(ord(character) < 32 or ord(character) == 127 for character in text):
            raise HarborWorkspaceError("Dataset path contains control characters")
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = self.config_path.parent / path
        return Path(os.path.abspath(path))

    def _validate_dataset_id(self, value: str) -> None:
        if DATASET_ID_RE.fullmatch(value) is None:
            raise HarborWorkspaceError(
                "Dataset id must be a lowercase path-safe identifier"
            )

    def _task_directory(self, value: str) -> str:
        name = str(value).strip()
        if TASK_DIR_RE.fullmatch(name) is None or name.startswith("."):
            raise HarborWorkspaceError("Task directory name is not path-safe")
        return name

    def _task_package_name(self, task_dir: Path) -> str | None:
        try:
            config = TaskConfig.model_validate_toml(
                _read_regular_file(
                    task_dir / "task.toml", limit=TEXT_EDIT_LIMIT
                ).decode("utf-8")
            )
            return config.task.name if config.task else None
        except Exception:  # noqa: BLE001 - summary may describe invalid drafts.
            return None

    def _write_task_scaffold(
        self, task_dir: Path, package: PackageInfo, steps: int
    ) -> None:
        import harbor.cli.init

        template = Path(harbor.cli.init.__file__).parent / "template-task"
        required_files = (template / ".gitignore", template / "instruction.md")
        required_directories = (
            template / "environment",
            template / "pytest-tests",
            template / "solution",
        )
        if not all(path.is_file() for path in required_files) or not all(
            path.is_dir() for path in required_directories
        ):
            raise _missing_harbor_templates_error()
        try:
            task_dir.mkdir()
            shutil.copyfile(template / ".gitignore", task_dir / ".gitignore")
            shutil.copytree(template / "environment", task_dir / "environment")
            config_data: dict[str, Any] = {
                "task": package,
                "agent": {"timeout_sec": 600.0},
            }
            if steps:
                config_data["steps"] = [
                    {"name": f"step-{index + 1}"} for index in range(steps)
                ]
            config = TaskConfig.model_validate(config_data)
            _atomic_write(
                task_dir / "task.toml", config.model_dump_toml().encode("utf-8")
            )
            _atomic_write(task_dir / "README.md", f"# {package.name}\n".encode("utf-8"))
            if steps:
                for index in range(steps):
                    step = task_dir / "steps" / f"step-{index + 1}"
                    step.mkdir(parents=True)
                    shutil.copyfile(
                        template / "instruction.md", step / "instruction.md"
                    )
                    shutil.copytree(template / "pytest-tests", step / "tests")
                    shutil.copytree(template / "solution", step / "solution")
            else:
                shutil.copyfile(
                    template / "instruction.md", task_dir / "instruction.md"
                )
                shutil.copytree(template / "pytest-tests", task_dir / "tests")
                shutil.copytree(template / "solution", task_dir / "solution")
        except FileNotFoundError as exc:
            missing = Path(exc.filename) if isinstance(exc.filename, str) else None
            if missing is not None and missing.is_relative_to(template):
                raise _missing_harbor_templates_error() from exc
            raise


def _validate_task(task_dir: Path) -> tuple[bool, str | None]:
    try:
        _walk_tree(task_dir)
        Task(task_dir)
        return True, None
    except Exception as exc:  # noqa: BLE001 - Harbor owns validation types.
        return False, _safe_diagnostic(exc, task_dir, "<task>")


def _missing_harbor_templates_error() -> HarborWorkspaceError:
    return HarborWorkspaceError(
        "Harbor Task templates are unavailable; reinstall peval-py with Harbor "
        "package data (PyInstaller builds require --collect-data harbor)"
    )


def _task_ref(task_dir: Path) -> DatasetTaskRef:
    task = Task(task_dir)
    if task.config.task is None:
        raise HarborWorkspaceError("Task package metadata is missing")
    content_hash, _ = Packager.compute_content_hash(task_dir)
    return DatasetTaskRef(
        name=task.config.task.name,
        digest=f"sha256:{content_hash}",
    )


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise HarborWorkspaceError(f"{key} must be a non-empty string")
    return value.strip()


def _safe_diagnostic(exc: Exception, root: Path, label: str) -> str:
    return str(exc).replace(str(root), label)


def _safe_relative_path(value: str) -> PurePosixPath:
    text = str(value).strip()
    if (
        not text
        or "\\" in text
        or any(ord(character) < 32 or ord(character) == 127 for character in text)
    ):
        raise HarborWorkspaceError("Task path is not a safe relative path")
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise HarborWorkspaceError("Task path is not a safe relative path")
    if any(part.startswith(".peval-py-") for part in path.parts):
        raise HarborWorkspaceError("Task path uses a reserved control directory")
    return path


def _assert_unlinked_ancestors(path: Path) -> None:
    current = path
    while True:
        if current.is_symlink():
            raise HarborWorkspaceError("Path traverses a symbolic link")
        if current.parent == current:
            break
        current = current.parent


def _assert_safe_directory(root: Path, path: Path) -> None:
    _assert_safe_child(root, path, allow_missing=False)
    try:
        value = path.stat(follow_symlinks=False)
    except FileNotFoundError as exc:
        raise HarborNotFoundError("Directory not found") from exc
    if not stat.S_ISDIR(value.st_mode):
        raise HarborWorkspaceError("Path must be a regular directory")


def _assert_safe_child(root: Path, path: Path, *, allow_missing: bool) -> None:
    lexical_root = Path(os.path.abspath(root))
    lexical_path = Path(os.path.abspath(path))
    _assert_unlinked_ancestors(lexical_root)
    try:
        relative = lexical_path.relative_to(lexical_root)
    except ValueError as exc:
        raise HarborWorkspaceError("Task path escapes its Dataset") from exc
    current = lexical_root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise HarborWorkspaceError("Task path traverses a symbolic link")
        if not current.exists():
            if allow_missing:
                continue
            raise HarborNotFoundError("Task path not found")
        mode = current.stat(follow_symlinks=False).st_mode
        if current != lexical_path and not stat.S_ISDIR(mode):
            raise HarborWorkspaceError("Task path traverses a non-directory")
        if current == lexical_path and not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise HarborWorkspaceError("Task path must be a regular file or directory")


def _walk_tree(root: Path) -> list[Path]:
    _assert_safe_directory(root, root)
    result: list[Path] = []
    with os.scandir(root) as entries:
        for entry in sorted(entries, key=lambda item: item.name.casefold()):
            path = Path(entry.path)
            if entry.is_symlink():
                raise HarborWorkspaceError(
                    f"Task content is a symbolic link: {entry.name}"
                )
            if entry.is_dir(follow_symlinks=False):
                result.append(path)
                result.extend(_walk_tree(path))
            elif entry.is_file(follow_symlinks=False):
                result.append(path)
            else:
                raise HarborWorkspaceError(
                    f"Task content is not a regular file: {entry.name}"
                )
    return result


def _child_dirs(root: Path) -> list[Path]:
    result: list[Path] = []
    with os.scandir(root) as entries:
        for entry in sorted(entries, key=lambda item: item.name.casefold()):
            if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                raise HarborWorkspaceError("Trash contains an unsafe entry")
            result.append(Path(entry.path))
    return result


def _directory_revision(root: Path) -> str:
    digest = hashlib.sha256()
    for path in _walk_tree(root):
        relative = path.relative_to(root).as_posix()
        value = path.stat(follow_symlinks=False)
        if stat.S_ISDIR(value.st_mode):
            digest.update(f"d\0{relative}\0".encode())
            continue
        digest.update(f"f\0{relative}\0{value.st_size}\0".encode())
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _read_regular_file(path: Path, *, limit: int | None) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        value = os.fstat(descriptor)
        if not stat.S_ISREG(value.st_mode):
            raise HarborWorkspaceError("Path is not a regular file")
        if limit is not None and value.st_size > limit:
            raise HarborSizeError(
                f"File exceeds the {limit // (1024 * 1024)} MiB limit"
            )
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            content = handle.read(limit + 1 if limit is not None else -1)
        if limit is not None and len(content) > limit:
            raise HarborSizeError(
                f"File exceeds the {limit // (1024 * 1024)} MiB limit"
            )
        return content
    finally:
        os.close(descriptor)


def _regular_path(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.stat(follow_symlinks=False).st_mode)
    except OSError:
        return False


def _is_utf8(path: Path) -> bool:
    try:
        _read_regular_file(path, limit=TEXT_EDIT_LIMIT).decode("utf-8")
        return True
    except (OSError, UnicodeDecodeError, HarborWorkspaceError):
        return False


def _file_revision(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _atomic_write(path: Path, content: bytes) -> None:
    _assert_unlinked_ancestors(path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise HarborWorkspaceError("Destination is a symbolic link")
    if path.exists() and not stat.S_ISREG(path.stat(follow_symlinks=False).st_mode):
        raise HarborWorkspaceError("Destination must be a regular file")
    mode = path.stat(follow_symlinks=False).st_mode & 0o777 if path.exists() else None
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            temporary.chmod(mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
