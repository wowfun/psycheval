"""Bounded control files, atomic writes and cross-process coordination."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import psutil

from psycheval.file_access import open_read_descriptor

ACTIVE = frozenset({"preparing", "running", "stopping"})


class JobsConflict(ValueError):
    pass


class FileChanged(ValueError):
    pass


def validate_state(value, run_id):
    if not isinstance(value, dict) or any(
        not isinstance(value.get(key), str) or not value[key]
        for key in ("id", "harness", "state", "submitted_at")
    ):
        raise ValueError("invalid Jobs state record")
    if value["id"] != run_id or value["state"] not in ACTIVE | {
        "completed",
        "cancelled",
        "failed",
        "interrupted",
    }:
        raise ValueError("invalid Jobs state identity or status")
    datetime.fromisoformat(value["submitted_at"])
    for key in ("trials_total", "trials_started", "trials_completed"):
        if key in value and (
            type(value[key]) is not int or not 0 <= value[key] <= 10_000
        ):
            raise ValueError("invalid Jobs progress count")
    if not isinstance(value.get("heartbeat", 0), (int, float)):
        raise ValueError("invalid Jobs heartbeat")
    name = value.get("job_name")
    if name is not None and (
        not isinstance(name, str)
        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}__\d{2}-\d{2}-\d{2}", name)
        or datetime.strptime(name, "%Y-%m-%d__%H-%M-%S").strftime("%Y-%m-%d__%H-%M-%S")
        != name
    ):
        raise ValueError("invalid Jobs output timestamp")
    return dict(value)


def read_object(path, default=None):
    value = read_json(path, default)
    if not isinstance(value, dict):
        raise ValueError(f"invalid Jobs object: {path.name}")
    return value


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def safe_path(root: Path, *parts: str) -> Path:
    path = root.joinpath(*parts)
    if any(part in {"..", "."} or ":" in part for part in parts):
        raise ValueError("invalid Jobs path")
    lexical = Path(os.path.abspath(path))
    base = Path(os.path.abspath(root))
    if not lexical.is_relative_to(base):
        raise ValueError("Jobs path escapes its root")
    for item in (*lexical.parents, lexical):
        if os.path.lexists(item):
            info = item.lstat()
            if (
                stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise ValueError("linked Jobs paths are not allowed")
    return path


@contextmanager
def open_regular(path: Path):
    """Open without following links, then verify identity before any read."""
    safe_path(path.parent, path.name)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("Jobs file must be regular")
    descriptor = open_read_descriptor(path)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        safe_path(path.parent, path.name)
        after = path.lstat()
        if not stat.S_ISREG(opened.st_mode) or any(
            (info.st_dev, info.st_ino) != (opened.st_dev, opened.st_ino)
            for info in (before, after)
        ):
            raise FileChanged("Jobs file changed during open")
        yield stream


def read_bytes(path: Path, limit: int):
    for attempt in range(100):
        try:
            with open_regular(path) as stream:
                if os.fstat(stream.fileno()).st_size > limit:
                    raise ValueError("oversized Jobs file")
                value = stream.read(limit + 1)
                if len(value) > limit:
                    raise ValueError("oversized Jobs file")
                return value
        except (PermissionError, FileChanged) as exc:
            if (isinstance(exc, PermissionError) and os.name != "nt") or attempt == 99:
                raise
            # Replacement can briefly deny new readers on Windows as well.
            time.sleep(0.01)
            safe_path(path.parent, path.name)


def read_json(path: Path, default=None):
    def invalid_constant(value):
        raise ValueError(f"invalid JSON number: {value}")

    try:
        value = json.loads(
            read_bytes(path, 16 * 1024 * 1024), parse_constant=invalid_constant
        )
    except FileNotFoundError:
        return default
    except RecursionError as exc:
        raise ValueError("Jobs JSON nesting exceeds 64 levels") from exc
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 64:
            raise ValueError("Jobs JSON nesting exceeds 64 levels")
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
    return value


def write_json(path: Path, value) -> None:
    write_text(
        path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )


def write_text(path: Path, value: str) -> None:
    safe_path(path.parent, path.name)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(100):
            try:
                temporary.replace(path)
                break
            except PermissionError:
                if os.name != "nt" or attempt == 99:
                    raise
                # A Windows reader briefly holds the destination without delete sharing.
                time.sleep(0.01)
                safe_path(path.parent, path.name)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def locked(root: Path):
    safe_path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = safe_path(root, "coordination.sqlite3")
    try:
        connection = sqlite3.connect(path, timeout=5)
    except sqlite3.OperationalError as exc:
        raise JobsConflict("Jobs coordination is unavailable; retry shortly") from exc
    try:
        try:
            connection.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            raise JobsConflict("Jobs coordination is busy; retry shortly") from exc
        yield
        connection.commit()
    finally:
        connection.close()


def process_identity(pid: int) -> dict:
    return {"pid": pid, "created": psutil.Process(pid).create_time()}


def owned_process(identity: dict | None):
    if not identity:
        return None
    try:
        process = psutil.Process(identity["pid"])
        if process.create_time() == identity["created"] and process.is_running():
            return process
    except (psutil.Error, KeyError, TypeError, ValueError):
        pass
    return None
