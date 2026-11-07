"""Workspace-owned notes and archival state for source collections."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path

from psycheval.file_access import blocking_file_lease
from psycheval.jobs.storage import read_bytes, safe_path, write_json, write_text

NOTE_LIMIT = 64 * 1024


class CollectionConflict(ValueError):
    """The collection changed since the editor loaded it."""


def directory_identity(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path.expanduser()))


class CollectionStore:
    def __init__(self, workspace: Path):
        self.workspace = workspace

    def key(self, path: Path) -> str:
        return hashlib.sha256(directory_identity(path).encode("utf-8")).hexdigest()

    def root(self, kind: str, path: Path) -> Path:
        if kind not in {"dataset", "job"}:
            raise ValueError("unknown collection kind")
        return safe_path(self.workspace, ".peval", "collections", kind, self.key(path))

    def _state(self, kind: str, path: Path) -> tuple[dict, bytes]:
        target = self.root(kind, path) / "state.json"
        try:
            raw = read_bytes(target, NOTE_LIMIT)
        except FileNotFoundError:
            return {"archived": False, "trial_count": None}, b""
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError):
            value = None
        if (
            not isinstance(value, dict)
            or type(value.get("archived")) is not bool
            or value.get("trial_count") is not None
            and (type(value["trial_count"]) is not int or value["trial_count"] < 0)
        ):
            return {
                "archived": True,
                "trial_count": None,
                "state_error": "Invalid collection archival state; restore to repair",
            }, raw
        return value, raw

    def archived(self, path: Path) -> bool:
        return self._state("job", path)[0]["archived"]

    def read(self, kind: str, path: Path) -> dict:
        state, raw = self._state(kind, path)
        try:
            note = read_bytes(self.root(kind, path) / "notes.md", NOTE_LIMIT)
        except FileNotFoundError:
            note = b""
        return {
            **state,
            "note": note.decode("utf-8"),
            "revision": hashlib.sha256(raw + b"\0" + note).hexdigest(),
        }

    @contextmanager
    def edit(self, kind: str, path: Path, revision: str):
        root = self.root(kind, path)
        root.mkdir(parents=True, exist_ok=True)
        with blocking_file_lease(root / ".lock", label="Collection update"):
            current = self.read(kind, path)
            if not revision or current["revision"] != revision:
                raise CollectionConflict("Collection changed; reload the saved version")
            yield root, current

    def save_note(self, kind: str, path: Path, note: str, revision: str) -> dict:
        if not isinstance(note, str) or len(note.encode("utf-8")) > NOTE_LIMIT:
            raise ValueError("Collection notes must be UTF-8 text of at most 64 KiB")
        with self.edit(kind, path, revision) as (root, _current):
            if note:
                write_text(root / "notes.md", note)
            else:
                safe_path(root, "notes.md").unlink(missing_ok=True)
            return self.read(kind, path)

    def set_archived(
        self, path: Path, archived: bool, trial_count: int | None, revision: str
    ) -> dict:
        if type(archived) is not bool:
            raise ValueError("archived must be a boolean")
        with self.edit("job", path, revision) as (root, current):
            write_json(
                root / "state.json",
                {
                    "archived": archived,
                    "trial_count": trial_count if archived else current["trial_count"],
                },
            )
            return self.read("job", path)
