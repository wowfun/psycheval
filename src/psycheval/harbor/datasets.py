"""Safe, non-executing resolution of registered Harbor Dataset layouts."""

from __future__ import annotations

import os
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Literal, Mapping

from .identifiers import validate_harbor_id
from .tasks import load_harbor_task

DatasetFormat = Literal["harbor", "workbuddy.v1"]

WORKBUDDY_DATASET_SCHEMA = "workbuddy.dataset.v1"
WORKBUDDY_VERIFIER_SCHEMA = "workbuddy.verifier.v1"
WORKBUDDY_VERIFIER_ENGINE = "composite"
DATASET_MANIFEST_LIMIT = 256 * 1024
TASK_TEXT_LIMIT = 2 * 1024 * 1024
TASK_ENTRY_LIMIT = 100_000
REQUIRED_SHARED_VERIFIER_FILES = (
    "shared/verifier/plugin.py",
    "shared/verifier/manifest.py",
    "shared/verifier/scoring.py",
)


class HarborDatasetError(ValueError):
    """A stable failure while resolving a registered Dataset."""


@dataclass(frozen=True, slots=True)
class ResolvedHarborDataset:
    id: str
    source_root: Path
    task_root: Path
    format: DatasetFormat
    read_only: bool
    task_names: tuple[str, ...]
    manifest: Mapping[str, Any]


def detect_harbor_dataset_format(root: Path) -> DatasetFormat:
    """Detect WorkBuddy only from its explicit schema; keep other roots generic."""

    manifest_path = root / "dataset.toml"
    if not manifest_path.exists():
        return "harbor"
    try:
        data = _read_toml(manifest_path)
    except HarborDatasetError:
        if (root / "tasks").is_dir() and (root / "shared").is_dir():
            raise
        return "harbor"
    dataset = data.get("dataset")
    schema = dataset.get("schema") if isinstance(dataset, dict) else None
    if schema == WORKBUDDY_DATASET_SCHEMA:
        return "workbuddy.v1"
    if isinstance(schema, str) and schema.startswith("workbuddy."):
        raise HarborDatasetError(f"unsupported WorkBuddy dataset schema: {schema}")
    return "harbor"


def resolve_harbor_dataset(
    *,
    dataset_id: str,
    path: str | Path,
    format: DatasetFormat = "harbor",
    allow_partial: bool = False,
) -> ResolvedHarborDataset:
    """Resolve a Dataset's effective layout without walking every Task body."""

    if type(allow_partial) is not bool or (allow_partial and format != "workbuddy.v1"):
        raise HarborDatasetError(
            "allow_partial must be a boolean and is only supported for WorkBuddy"
        )
    try:
        dataset_id = validate_harbor_id(dataset_id, kind="dataset")
    except ValueError as exc:
        raise HarborDatasetError(str(exc)) from exc
    if not str(path).strip():
        raise HarborDatasetError("harbor dataset path must be a non-empty string")
    root = Path(path).expanduser().resolve()
    if format == "harbor":
        return ResolvedHarborDataset(
            id=dataset_id,
            source_root=root,
            task_root=root,
            format="harbor",
            read_only=False,
            task_names=tuple(path.name for path in _direct_task_dirs(root)),
            manifest=MappingProxyType({}),
        )
    if format != "workbuddy.v1":
        raise HarborDatasetError(f"unsupported Harbor Dataset format: {format}")
    return _resolve_workbuddy(dataset_id, root, allow_partial=allow_partial)


def validate_harbor_dataset(
    *,
    dataset_id: str,
    path: str | Path,
    format: DatasetFormat = "harbor",
    allow_partial: bool = False,
) -> ResolvedHarborDataset:
    """Fully validate a Dataset at registration and execution-plan gates."""

    resolved = resolve_harbor_dataset(
        dataset_id=dataset_id, path=path, format=format, allow_partial=allow_partial
    )
    if resolved.format != "workbuddy.v1":
        return resolved
    for relative in REQUIRED_SHARED_VERIFIER_FILES:
        _regular_file(resolved.source_root, PurePosixPath(relative))
    layout = _required_table(resolved.manifest, "layout")
    archive_relative = _required_relative(layout, "workspace_archive")
    for task_name in resolved.task_names:
        task_dir = resolved.task_root / task_name
        _walk_regular_tree(task_dir)
        try:
            load_harbor_task(
                task_dir,
                read_bytes=lambda path: _read_regular_bytes(
                    task_dir,
                    path,
                    max_bytes=TASK_TEXT_LIMIT,
                ),
            )
        except Exception as exc:  # noqa: BLE001 - Harbor owns validation types.
            raise HarborDatasetError(
                f"invalid Harbor Task {task_dir.name}: {exc}"
            ) from exc
        archive = _regular_file(task_dir, archive_relative)
        header = _read_regular_prefix(task_dir, archive, size=200)
        if header.startswith(b"version https://git-lfs.github.com/spec/v1"):
            raise HarborDatasetError(
                f"workspace archive is a Git LFS pointer: {archive}"
            )
    return resolved


def _resolve_workbuddy(
    dataset_id: str, root: Path, *, allow_partial: bool
) -> ResolvedHarborDataset:
    manifest = _read_toml(root / "dataset.toml")
    dataset = _required_table(manifest, "dataset")
    verifier = _required_table(manifest, "verifier")
    layout = _required_table(manifest, "layout")
    if dataset.get("schema") != WORKBUDDY_DATASET_SCHEMA:
        raise HarborDatasetError(f"dataset.schema must be {WORKBUDDY_DATASET_SCHEMA!r}")
    if verifier.get("schema") != WORKBUDDY_VERIFIER_SCHEMA:
        raise HarborDatasetError(
            f"verifier.schema must be {WORKBUDDY_VERIFIER_SCHEMA!r}"
        )
    if verifier.get("engine") != WORKBUDDY_VERIFIER_ENGINE:
        raise HarborDatasetError(
            f"verifier.engine must be {WORKBUDDY_VERIFIER_ENGINE!r}"
        )
    task_root = _contained_directory(root, _required_relative(layout, "task_root"))
    task_dirs = _direct_task_dirs(task_root)
    task_count = dataset.get("task_count")
    if type(task_count) is not int or task_count < 1:
        raise HarborDatasetError("dataset.task_count must be a positive integer")
    if (
        not task_dirs
        or len(task_dirs) > task_count
        or (not allow_partial and task_count != len(task_dirs))
    ):
        raise HarborDatasetError(
            f"dataset.task_count declares {task_count}, found {len(task_dirs)} Tasks"
        )
    return ResolvedHarborDataset(
        id=dataset_id,
        source_root=root,
        task_root=task_root,
        format="workbuddy.v1",
        read_only=True,
        task_names=tuple(path.name for path in task_dirs),
        manifest=MappingProxyType(manifest),
    )


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        raw = _read_regular_bytes(
            path.parent,
            path,
            max_bytes=DATASET_MANIFEST_LIMIT,
        )
    except FileNotFoundError as exc:
        raise HarborDatasetError(f"Dataset file not found: {path}") from exc
    try:
        return tomllib.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise HarborDatasetError(f"Dataset manifest is not UTF-8: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise HarborDatasetError(f"malformed Dataset manifest: {path}") from exc


def _required_table(data: Mapping[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise HarborDatasetError(f"Dataset manifest [{name}] must be a table")
    return value


def _required_relative(table: Mapping[str, Any], name: str) -> PurePosixPath:
    value = table.get(name)
    if not isinstance(value, str) or not value.strip():
        raise HarborDatasetError(f"Dataset manifest layout.{name} is required")
    if "\\" in value:
        raise HarborDatasetError(f"Dataset manifest layout.{name} is not path-safe")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise HarborDatasetError(f"Dataset manifest layout.{name} is not path-safe")
    return path


def _contained_directory(root: Path, relative: PurePosixPath) -> Path:
    path = root.joinpath(*relative.parts)
    _assert_contained(root, path)
    try:
        value = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise HarborDatasetError(f"Dataset directory not found: {path}") from exc
    if not stat.S_ISDIR(value.st_mode):
        raise HarborDatasetError(f"Dataset path is not a regular directory: {path}")
    return path


def _regular_file(root: Path, relative: PurePosixPath) -> Path:
    path = root.joinpath(*relative.parts)
    _assert_contained(root, path)
    try:
        value = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise HarborDatasetError(f"Dataset file not found: {path}") from exc
    if not stat.S_ISREG(value.st_mode):
        raise HarborDatasetError(f"Dataset path is not a regular file: {path}")
    return path


def _assert_contained(root: Path, path: Path) -> None:
    absolute_root = Path(os.path.abspath(root))
    absolute_path = Path(os.path.abspath(path))
    if absolute_path != absolute_root and absolute_root not in absolute_path.parents:
        raise HarborDatasetError(f"Dataset path escapes its root: {path}")
    current = absolute_path
    while current != absolute_root:
        if current.is_symlink():
            raise HarborDatasetError(
                f"Dataset path traverses a symbolic link: {current}"
            )
        current = current.parent


def _direct_task_dirs(root: Path) -> list[Path]:
    try:
        entries = list(os.scandir(root))
    except OSError as exc:
        raise HarborDatasetError(f"Dataset Task root is not readable: {root}") from exc
    result = []
    for entry in sorted(entries, key=lambda item: item.name.casefold()):
        if entry.name.startswith(".") or entry.is_symlink():
            continue
        if entry.is_dir(follow_symlinks=False):
            result.append(Path(entry.path))
    return result


def _walk_regular_tree(root: Path) -> None:
    containment_root = root
    directories = [root]
    entry_count = 0
    while directories:
        directory = directories.pop()
        _assert_contained(containment_root, directory)
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            raise HarborDatasetError(
                f"Dataset Task is not readable: {directory}"
            ) from exc
        for entry in entries:
            entry_count += 1
            if entry_count > TASK_ENTRY_LIMIT:
                raise HarborDatasetError(
                    f"Dataset Task exceeds {TASK_ENTRY_LIMIT} filesystem entries"
                )
            path = Path(entry.path)
            if entry.is_symlink():
                raise HarborDatasetError(
                    f"Dataset Task content is a symbolic link: {path}"
                )
            if entry.is_dir(follow_symlinks=False):
                directories.append(path)
            elif not entry.is_file(follow_symlinks=False):
                raise HarborDatasetError(f"Dataset Task content is not regular: {path}")


def _read_regular_bytes(root: Path, path: Path, *, max_bytes: int) -> bytes:
    _assert_contained(root, path)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise HarborDatasetError(f"Dataset file cannot be read: {path}") from exc
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise HarborDatasetError(f"Dataset Task file is not regular: {path}")
        if opened.st_size > max_bytes:
            raise HarborDatasetError(f"Dataset file exceeds {max_bytes} bytes: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            content = handle.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise HarborDatasetError(f"Dataset file exceeds {max_bytes} bytes: {path}")
        return content
    finally:
        os.close(descriptor)


def _read_regular_prefix(root: Path, path: Path, *, size: int) -> bytes:
    _assert_contained(root, path)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise HarborDatasetError(f"Dataset file cannot be read: {path}") from exc
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise HarborDatasetError(f"Dataset Task file is not regular: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            return handle.read(size)
    finally:
        os.close(descriptor)
