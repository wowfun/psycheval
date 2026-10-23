"""Contained, bounded reads of retained evaluation data."""

import json
import os
import stat
from pathlib import Path

from psycheval.file_access import open_read_descriptor
from psycheval.redaction import redact_retained_text

MAX_INPUT_BYTES = 64 * 1024 * 1024


def contained(root: Path, path: Path) -> Path:
    root, path = Path(os.path.abspath(root)), Path(os.path.abspath(path))
    if not path.is_relative_to(root):
        raise ValueError("Judge file is outside its source")
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(
            info, "st_file_attributes", 0
        ) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError("Judge paths must not traverse links or junctions")
    return path


def read_text(root: Path, path: Path, limit=MAX_INPUT_BYTES) -> str:
    path = contained(root, path)
    with os.fdopen(open_read_descriptor(path), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Judge inputs must be regular files")
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Judge file exceeds the read limit")
    return raw.decode("utf-8")


def read_json(root: Path, path: Path, *, optional=False):
    try:
        value = json.loads(read_text(root, path))
    except FileNotFoundError:
        if optional:
            return None
        raise
    if not isinstance(value, dict):
        raise ValueError("Judge file must contain an object")
    return value


def protected(value):
    return json.loads(
        redact_retained_text(json.dumps(value, ensure_ascii=False, allow_nan=False))
    )


def retained_prompt(root: Path, directory: Path, rubric_id: str) -> dict:
    contained(root, directory)
    matches = []
    files = sorted(directory.glob("rubric-*.json"))
    if len(files) > 64:
        raise ValueError("too many Judge diagnostic files")
    for path in files:
        record = read_json(root, path)
        if record.get("id") == rubric_id:
            matches.append(record)
    if len(matches) > 1:
        raise ValueError("ambiguous retained rubric ID")
    if not matches:
        return {
            "id": rubric_id,
            "status": "unavailable",
            "messages": None,
            "attempts": [],
        }
    value = matches[0]
    messages, attempts = value.get("messages"), value.get("attempts", [])
    if messages is not None and (
        not isinstance(messages, list)
        or any(
            not isinstance(item, dict)
            or not isinstance(item.get("role"), str)
            or not isinstance(item.get("content"), str)
            for item in messages
        )
    ):
        raise ValueError("malformed retained prompt messages")
    if not isinstance(attempts, list):
        raise ValueError("malformed retained request attempts")
    return protected(
        {
            "id": rubric_id,
            "status": "recorded"
            if messages is not None
            else "not_requested"
            if not attempts
            else "unavailable",
            "messages": messages,
            "attempts": attempts,
            "result": value.get("result"),
        }
    )
