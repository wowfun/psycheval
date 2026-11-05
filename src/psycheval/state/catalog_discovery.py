"""Non-following dependency observations for the derived catalog scan."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from psycheval.harbor.tasks import PUBLISHABLE_TASK_DIRECTORIES, PUBLISHABLE_TASK_FILES
from psycheval.state.workspace_source_models import SourceCandidate

_TASK_INPUTS = PUBLISHABLE_TASK_FILES | {
    ".gitignore",
    *(name.rstrip("/") for name in PUBLISHABLE_TASK_DIRECTORIES),
}


def manifest_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def path_observation(path: Path, entry: os.DirEntry[str] | None = None) -> list[Any]:
    try:
        # Windows DirEntry.stat omits the device and file identity.
        value = (entry if entry is not None and os.name != "nt" else path).stat(
            follow_symlinks=False
        )
    except OSError as exc:
        return [str(path), "error", exc.errno]
    return [
        str(path),
        value.st_mode,
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
        getattr(value, "st_reparse_tag", 0),
    ]


class DirectoryChecks:
    """Memoize ancestor observations across the probes for one root Trial."""

    def __init__(self) -> None:
        self._checked: dict[Path, list[Any] | None] = {}

    def blocker(self, path: Path) -> list[Any] | None:
        if path in self._checked:
            return self._checked[path]
        missing = []
        while path not in self._checked:
            missing.append(path)
            parent = path.parent
            if parent == path:
                break
            path = parent
        blocker = self._checked.get(path)
        for directory in reversed(missing):
            if blocker is None:
                record = path_observation(directory)
                if isinstance(record[1], int) and (
                    not stat.S_ISDIR(record[1]) or record[-1]
                ):
                    blocker = record
            self._checked[directory] = blocker
        return blocker


def observe_files(
    root: Path, names: tuple[str, ...], checks: DirectoryChecks | None = None
) -> list[list[Any]]:
    # Safe directory timestamps can change because of unrelated siblings.
    checks = checks or DirectoryChecks()
    blocker = checks.blocker(root)
    if blocker is not None:
        return [blocker]
    records = []
    for name in names:
        path = root / name
        blocker = checks.blocker(path.parent)
        if blocker is None:
            records.append(path_observation(path))
        elif blocker not in records:
            records.append(blocker)
    return records


def observe_tree(
    root: Path, *, task_package: bool = False, checks: DirectoryChecks | None = None
) -> list[list[Any]]:
    blocker = (checks or DirectoryChecks()).blocker(root.parent)
    if blocker is not None:
        return [blocker]
    records = []

    def visit(path: Path, entry: os.DirEntry[str] | None, content: bool) -> None:
        # Task validation rejects special entries anywhere in the package. For
        # scratch trees only their safety matters, not regular file metadata.
        record = path_observation(path, entry)
        if not isinstance(record[1], int) or not stat.S_ISDIR(record[1]) or record[-1]:
            records.append(record)
            return
        if path == root:
            # A parent can change after an earlier file or directory probe.
            blocker = DirectoryChecks().blocker(root.parent)
            if blocker is not None:
                records.append(blocker)
                return
        if content:
            records.append(record)
        elif path == root:
            # Directory identity, independent of scratch siblings.
            records.append(record[:4])
        try:
            with os.scandir(path) as entries:
                # A directory (including a child from DirEntry) can be replaced
                # between its first observation and opening the iterator.
                current = path_observation(path)
                if current[:4] != record[:4] or current[-1]:
                    records.append(current)
                    return
                children = sorted(
                    (
                        child
                        for child in entries
                        if content
                        or (path == root and child.name in _TASK_INPUTS)
                        or not child.is_file(follow_symlinks=False)
                    ),
                    key=lambda child: child.name,
                )
            for child in children:
                visit(
                    Path(child.path),
                    child,
                    content or (path == root and child.name in _TASK_INPUTS),
                )
        except OSError as exc:
            records.append([str(path), "enumeration-error", exc.errno])

    visit(root, None, not task_package)
    return records


@dataclass
class DiscoveryBatch:
    source_ref: str
    candidates: list[SourceCandidate]
    dependencies_json: str = ""
    reused: bool = False


class SharedObservations:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def get(self, key: str, observe: Callable[[], Any]) -> str:
        if key not in self._values:
            self._values[key] = hashlib.sha256(
                manifest_json(observe()).encode("utf-8")
            ).hexdigest()
        return self._values[key]
