"""Immutable source reads and attempt-scoped evidence publication (stdlib only)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path


class EvidenceLimitError(ValueError):
    """Evidence exceeds an explicit input or publication budget."""


def _positive_limit(value: int, name: str) -> None:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def is_link(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _check_path(path: Path) -> None:
    for part in (path, *path.parents):
        try:
            if is_link(part.lstat()):
                raise ValueError(f"Linked evidence path: {part}")
        except FileNotFoundError:
            continue


def _clear_output(path: Path) -> None:
    """Remove an owned output without following its link or linked parents."""
    _check_path(path.parent)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if is_link(info):
        if stat.S_ISDIR(info.st_mode) and not path.is_symlink():
            path.rmdir()  # Windows junction: remove the link, not its target.
        else:
            path.unlink()
    elif stat.S_ISDIR(info.st_mode):
        shutil.rmtree(path)
    else:
        path.unlink()


@dataclass(frozen=True)
class SourceSnapshot:
    path: Path
    content: bytes

    def __post_init__(self):
        object.__setattr__(self, "path", Path(self.path))
        object.__setattr__(self, "content", bytes(self.content))

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()

    @classmethod
    def read(cls, path: str | Path, *, max_bytes: int = 64 * 1024 * 1024):
        _positive_limit(max_bytes, "max_bytes")
        path = Path(path).absolute()
        _check_path(path)
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"Source is not a regular file: {path}")
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                raise OSError("Source changed while opening")
            content = stream.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise EvidenceLimitError(f"Source exceeds {max_bytes} bytes")
        return cls(path, content)


class EvidenceWriter:
    """Own only the manifest, artifact_text and raw_artifacts in one attempt."""

    def __init__(
        self,
        directory: str | Path,
        *,
        max_total_bytes: int = 256 * 1024 * 1024,
        max_artifacts: int = 64,
        max_text_bytes: int = 4 * 1024 * 1024,
    ):
        for name, limit in (
            ("max_total_bytes", max_total_bytes),
            ("max_artifacts", max_artifacts),
            ("max_text_bytes", max_text_bytes),
        ):
            _positive_limit(limit, name)
        self.directory = Path(directory).absolute()
        self.max_total_bytes = max_total_bytes
        self.max_artifacts = max_artifacts
        self.max_text_bytes = max_text_bytes
        self._written_bytes = 0
        self._records: dict[str, dict] = {}
        self._paths: set[str] = set()
        self._active = False

    def __enter__(self):
        if self._active:
            raise RuntimeError("EvidenceWriter is already active")
        _check_path(self.directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        for name in ("artifact_manifest.json", "artifact_text", "raw_artifacts"):
            _clear_output(self.directory / name)
        self._records.clear()
        self._paths.clear()
        self._written_bytes = 0
        self._active = True
        return self

    def _id(self, artifact_id: str):
        if not self._active:
            raise RuntimeError("Use EvidenceWriter as a context manager")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", artifact_id):
            raise ValueError("Invalid artifact id")
        if artifact_id in self._records:
            raise ValueError(f"Duplicate artifact id: {artifact_id}")
        if len(self._records) >= self.max_artifacts:
            raise EvidenceLimitError(f"Evidence exceeds {self.max_artifacts} artifacts")

    def _write(self, relative: str, content: bytes):
        if not self._active:
            raise RuntimeError("Use EvidenceWriter as a context manager")
        if self._written_bytes + len(content) > self.max_total_bytes:
            raise EvidenceLimitError(
                f"Evidence exceeds {self.max_total_bytes} total bytes"
            )
        if relative == "artifact_manifest.json" and len(content) > 1024 * 1024:
            raise EvidenceLimitError("Evidence manifest exceeds 1048576 bytes")
        path = self.directory / relative
        _check_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".evidence-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
            os.replace(temporary, path)
            self._written_bytes += len(content)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def capture(
        self,
        artifact_id: str,
        source: str | Path | SourceSnapshot,
        *,
        max_bytes: int = 64 * 1024 * 1024,
    ):
        self._id(artifact_id)
        _positive_limit(max_bytes, "max_bytes")
        snapshot = (
            source
            if isinstance(source, SourceSnapshot)
            else SourceSnapshot.read(source, max_bytes=max_bytes)
        )
        if len(snapshot.content) > max_bytes:
            raise EvidenceLimitError(f"Source exceeds {max_bytes} bytes")
        extension = snapshot.path.suffix.lower().lstrip(".")
        if not re.fullmatch(r"[a-z0-9]+", extension):
            raise ValueError("Source needs a format extension")
        relative = f"raw_artifacts/{artifact_id}.{extension}"
        if relative.casefold() in self._paths:
            raise ValueError(f"Duplicate evidence path: {relative}")
        self._write(relative, snapshot.content)
        self._paths.add(relative.casefold())
        self._records[artifact_id] = {
            "id": artifact_id,
            "type": f"raw_{extension}",
            "source_path": str(snapshot.path),
            "verifier_raw_path": relative,
            "sha256": snapshot.sha256,
            "bytes": len(snapshot.content),
            "extract_status": "ok",
        }
        return snapshot

    def add_text(
        self,
        artifact_id: str,
        text: str,
        *,
        source_id: str | None = None,
        path: str | None = None,
    ):
        self._id(artifact_id)
        if source_id is not None and source_id not in self._records:
            raise ValueError(f"Unknown source artifact: {source_id}")
        relative = path or f"artifact_text/{artifact_id}.md"
        parts = relative.replace("\\", "/").split("/")
        if (
            len(parts) < 2
            or parts[0] != "artifact_text"
            or any(
                not re.fullmatch(r"[A-Za-z0-9_.-]+", p) or p in {".", ".."}
                for p in parts
            )
            or not relative.endswith(".md")
        ):
            raise ValueError("Text path must be a Markdown path under artifact_text")
        relative = "/".join(parts)
        if relative.casefold() in self._paths:
            raise ValueError(f"Duplicate evidence path: {relative}")
        if len(text) > self.max_text_bytes:
            raise EvidenceLimitError(f"Text exceeds {self.max_text_bytes} UTF-8 bytes")
        content = text.encode("utf-8")
        if len(content) > self.max_text_bytes:
            raise EvidenceLimitError(f"Text exceeds {self.max_text_bytes} UTF-8 bytes")
        self._write(relative, content)
        self._paths.add(relative.casefold())
        self._records[artifact_id] = {
            "id": artifact_id,
            "type": "md",
            "source_path": relative,
            "text_path": relative,
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
            "extract_status": "ok" if text.strip() else "missing",
            **({"source_artifact_id": source_id} if source_id else {}),
        }

    def unavailable(self, artifact_id: str, reason: str, *, status: str = "missing"):
        self._id(artifact_id)
        if status not in {"missing", "error"}:
            raise ValueError("Unavailable status must be missing or error")
        self._records[artifact_id] = {
            "id": artifact_id,
            "type": "md",
            "extract_status": status,
            "reason": reason,
        }

    def __exit__(self, kind, value, traceback):
        if not self._active:
            raise RuntimeError("EvidenceWriter is not active")
        try:
            if kind is None:
                self._write(
                    "artifact_manifest.json",
                    json.dumps(
                        {"artifacts": list(self._records.values())},
                        ensure_ascii=False,
                        indent=2,
                    ).encode("utf-8"),
                )
        finally:
            self._active = False
