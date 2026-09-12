"""Read-only, on-demand access to one retained Trial's verification files."""

from __future__ import annotations

import codecs
import hashlib
import io
import os
import stat
from pathlib import Path
from typing import Any

from psycheval.redaction import protect_retained_bytes, redact_retained_text

from .harbor_verifier_evidence import (
    _IMAGE_TYPES,
    ARTIFACT_DOWNLOAD_MAX_BYTES,
    HarborVerifierArtifact,
    HarborVerifierArtifactStream,
    _assert_contained,
    _is_link,
    _media_type,
    _open_regular,
)

TEXT_PREVIEW_LIMIT = 2 * 1024 * 1024
TREE_ENTRY_LIMIT = 10_000
_ROOTS = ("verifier", "artifacts", "result.json", "exception.txt")
_TEXT_SUFFIXES = {
    "",
    ".txt",
    ".log",
    ".out",
    ".err",
    ".text",
    ".json",
    ".jsonl",
    ".xml",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".yaml",
    ".yml",
    ".toml",
    ".html",
    ".htm",
    ".svg",
    ".patch",
    ".diff",
    ".py",
    ".sh",
    ".bat",
    ".ps1",
    ".js",
    ".css",
    ".sql",
}


def verification_file_tree(data_dir: Path, root: Path) -> list[dict[str, Any]]:
    """Inspect metadata only; links and special files never enter the tree."""
    _assert_contained(root, data_dir)
    pending = [data_dir / name for name in reversed(_ROOTS)]
    result: list[dict[str, Any]] = []
    inspected = 0
    while pending:
        path = pending.pop()
        inspected += 1
        if inspected > TREE_ENTRY_LIMIT:
            raise ValueError("verification file tree exceeds the entry limit")
        if _is_link(path):
            continue
        try:
            value = path.stat(follow_symlinks=False)
        except FileNotFoundError:
            continue
        _assert_contained(root, path)
        relative = path.relative_to(data_dir).as_posix()
        if stat.S_ISDIR(value.st_mode):
            if relative in {"result.json", "exception.txt"}:
                continue
            if path.name == "__pycache__":
                continue
            result.append({"path": relative, "kind": "directory", "size": None})
            with os.scandir(path) as entries:
                children = []
                for entry in entries:
                    if inspected + len(pending) + len(children) >= TREE_ENTRY_LIMIT:
                        raise ValueError(
                            "verification file tree exceeds the entry limit"
                        )
                    children.append(Path(entry.path))
            pending.extend(
                sorted(children, key=lambda item: item.name.casefold(), reverse=True)
            )
        elif stat.S_ISREG(value.st_mode):
            suffix = path.suffix.lower()
            preview_kind = (
                "image"
                if suffix in _IMAGE_TYPES
                and value.st_size <= ARTIFACT_DOWNLOAD_MAX_BYTES
                else "text"
                if suffix in _TEXT_SUFFIXES
                else None
            )
            result.append(
                {
                    "id": hashlib.sha256(relative.encode("utf-8")).hexdigest()[:24],
                    "path": relative,
                    "kind": "file",
                    "size": value.st_size,
                    "preview_kind": preview_kind,
                    "previewable": preview_kind is not None,
                    "downloadable": value.st_size <= ARTIFACT_DOWNLOAD_MAX_BYTES,
                }
            )
    return result


def read_verification_file(
    data_dir: Path, root: Path, file_id: str, *, download: bool = False
) -> dict[str, Any] | HarborVerifierArtifact | HarborVerifierArtifactStream:
    # Re-enumeration binds an opaque ID to the current allowlisted tree, never a
    # browser-supplied filesystem path or a stale cached absolute path.
    entry = next(
        (
            item
            for item in verification_file_tree(data_dir, root)
            if item.get("id") == file_id
        ),
        None,
    )
    if entry is None:
        raise ValueError("unknown verification file")
    path = data_dir / entry["path"]
    if download:
        handle, opened = _open_regular(
            root, path, max_bytes=ARTIFACT_DOWNLOAD_MAX_BYTES
        )
        with handle:
            content = handle.read(min(opened.st_size, ARTIFACT_DOWNLOAD_MAX_BYTES) + 1)
        if len(content) > ARTIFACT_DOWNLOAD_MAX_BYTES:
            raise ValueError("verification download exceeds the size limit")
        content = protect_retained_bytes(
            content,
            text=path.suffix.lower() in _TEXT_SUFFIXES,
            limit=ARTIFACT_DOWNLOAD_MAX_BYTES,
        )
        return HarborVerifierArtifactStream(
            path.name, _media_type(path), len(content), io.BytesIO(content)
        )
    if not entry["previewable"]:
        raise ValueError("verification file is not previewable")
    if entry["preview_kind"] == "image":
        handle, _ = _open_regular(root, path, max_bytes=ARTIFACT_DOWNLOAD_MAX_BYTES)
        with handle:
            content = handle.read(ARTIFACT_DOWNLOAD_MAX_BYTES + 1)
        if len(content) > ARTIFACT_DOWNLOAD_MAX_BYTES:
            raise ValueError("verification image exceeds the preview limit")
        content = protect_retained_bytes(
            content, text=False, limit=ARTIFACT_DOWNLOAD_MAX_BYTES
        )
        return HarborVerifierArtifact(
            path.name, _IMAGE_TYPES[path.suffix.lower()], content
        )
    handle, _ = _open_regular(root, path, max_bytes=None)
    with handle:
        content = handle.read(TEXT_PREVIEW_LIMIT + 1)
    truncated = len(content) > TEXT_PREVIEW_LIMIT
    try:
        decoder = codecs.getincrementaldecoder("utf-8")()
        text = decoder.decode(content[:TEXT_PREVIEW_LIMIT], final=not truncated)
    except UnicodeDecodeError as exc:
        raise ValueError("verification file is not UTF-8 text") from exc
    if "\x00" in text:
        raise ValueError("verification file contains binary data")
    return {
        "path": entry["path"],
        "content": redact_retained_text(text.replace("\r\n", "\n").replace("\r", "\n")),
        "truncated": truncated,
    }
