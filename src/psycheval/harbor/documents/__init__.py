"""Optional, relocatable document inspection. Reports contain facts, never scores."""

from __future__ import annotations

import importlib
import io
import os
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..evidence import EvidenceLimitError, SourceSnapshot, _check_path, is_link
from ._limits import DocumentLimitError, DocumentLimits, DocumentParseError
from .models import (  # noqa: F401
    DocxReport,
    PdfReport,
    PptxOptions,
    PptxReport,
    XlsxReport,
)


class MissingDocumentDependency(ImportError):
    """Install the named optional extra before verification."""


@dataclass(frozen=True)
class DocumentSelection:
    selected: Path | None
    candidates: tuple[Path, ...]
    reason: str


def select_document(
    roots,
    *,
    format: str,
    preferred_stem: str | None = None,
    max_entries: int = 100000,
    max_depth: int = 64,
):
    if format not in {"pdf", "pptx", "xlsx", "docx"}:
        raise ValueError(f"Unsupported document format: {format}")
    if type(max_entries) is not int or max_entries < 1:
        raise ValueError("max_entries must be a positive integer")
    if type(max_depth) is not int or max_depth < 0:
        raise ValueError("max_depth must be a nonnegative integer")
    found, visited = {}, set()
    count = 0
    scans = []

    def visit(entry, info, depth):
        nonlocal count
        count += 1
        if count > max_entries:
            raise ValueError(f"scan entry limit reached ({max_entries})")
        if is_link(info):
            return
        identity = os.path.normcase(str(entry))
        if stat.S_ISDIR(info.st_mode):
            if identity in visited:
                return
            if depth > max_depth:
                raise ValueError(f"scan depth limit reached ({max_depth})")
            visited.add(identity)
            scans.append((os.scandir(entry), depth))
        elif (
            stat.S_ISREG(info.st_mode)
            and entry.suffix.lower() == f".{format}"
            and not entry.name.startswith("~$")
        ):
            found[identity] = entry

    try:
        for root in roots:
            root = Path(os.path.abspath(root))
            try:
                _check_path(root)
            except ValueError:
                continue
            try:
                info = root.lstat()
            except FileNotFoundError:
                continue
            visit(root, info, 0)
            while scans:
                entries, depth = scans[-1]
                child = next(entries, None)
                if child is None:
                    entries.close()
                    scans.pop()
                else:
                    visit(
                        Path(child.path), child.stat(follow_symlinks=False), depth + 1
                    )
    except (OSError, ValueError) as error:
        return DocumentSelection(
            None,
            tuple(sorted(found.values())),
            f"incomplete document scan: {type(error).__name__}: {error}",
        )
    finally:
        for entries, _ in scans:
            entries.close()
    options = tuple(sorted(found.values()))
    named = [path for path in options if path.stem == preferred_stem]
    if len(named) == 1:
        return DocumentSelection(named[0], options, "unique exact filename")
    if not named and len(options) == 1:
        return DocumentSelection(
            options[0], options, f"only {format.upper()} candidate"
        )
    return DocumentSelection(
        None,
        options,
        f"ambiguous {format.upper()} candidates" if options else f"no {format.upper()}",
    )


def inspect_document(
    source: str | Path | SourceSnapshot,
    *,
    format: str | None = None,
    pptx_options: PptxOptions | None = None,
    limits: DocumentLimits = DocumentLimits(),
):
    try:
        snapshot = (
            source
            if isinstance(source, SourceSnapshot)
            else SourceSnapshot.read(source, max_bytes=limits.source_bytes)
        )
    except EvidenceLimitError as error:
        raise DocumentLimitError(str(error)) from error
    kind = format or snapshot.path.suffix.lower().lstrip(".")
    if kind not in {"pdf", "pptx", "xlsx", "docx"}:
        raise DocumentParseError(f"Unsupported document format: {kind}")
    module_name = {"pdf": "pypdf", "pptx": "pptx", "xlsx": "openpyxl", "docx": "docx"}[
        kind
    ]
    try:
        backend = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        missing = error.name or module_name
        raise MissingDocumentDependency(
            f"Missing dependency {missing!r}; install or repair psycheval[{kind}] before inspection"
        ) from error
    if len(snapshot.content) > limits.source_bytes:
        raise DocumentLimitError("Document exceeds source byte limit")
    try:
        if kind != "pdf":
            with zipfile.ZipFile(io.BytesIO(snapshot.content)) as archive:
                members = archive.infolist()
                if any(item.flag_bits & 1 for item in members):
                    raise DocumentParseError("Encrypted OOXML is unsupported")
                if (
                    len(members) > limits.archive_entries
                    or sum(item.file_size for item in members) > limits.expanded_bytes
                ):
                    raise DocumentLimitError("OOXML archive exceeds document limits")
        if kind == "pptx":
            from ._pptx import inspect

            return inspect(snapshot, backend, pptx_options or PptxOptions(), limits)
        from . import _formats

        return getattr(_formats, f"inspect_{kind}")(snapshot, backend, limits)
    except DocumentParseError:
        raise
    except (
        ValueError,
        KeyError,
        IndexError,
        zipfile.BadZipFile,
        EOFError,
        SyntaxError,
    ) as error:
        raise DocumentParseError(f"Cannot read {kind.upper()}: {error}") from error
