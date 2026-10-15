from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import stat
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path, PurePosixPath
from threading import Lock
from typing import Any, Protocol
from urllib.parse import quote
from uuid import uuid4

from markdown_it import MarkdownIt

from psycheval.file_access import blocking_file_lease, open_read_descriptor

REPORT_MAX_BYTES = 20 * 1024 * 1024
REPORT_STATE_MAX_BYTES = 20 * 1024 * 1024
REPORT_STATE_FILENAME = "state.json"
PACKAGE_REPORT_REF_PREFIX = "package:"
REPORT_ID_RE = re.compile(
    r"^(?P<timestamp>\d{8}-\d{6}-\d{6})(?:-(?P<collision>[2-9]|[1-9]\d+))?$"
)
REPORT_FORMATS = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
}


class RenderableReport(Protocol):
    @property
    def report_ref(self) -> str: ...

    @property
    def filename(self) -> str: ...

    @property
    def format(self) -> str: ...

    @property
    def content(self) -> bytes: ...


@dataclass(frozen=True)
class WorkspaceReport:
    report_ref: str
    report_id: str
    filename: str
    format: str
    source_refs: tuple[str, ...]
    content: bytes


@dataclass(frozen=True)
class WorkspaceReportMetadata:
    report_id: str
    filename: str
    format: str
    source_refs: tuple[str, ...]
    report_path: Path
    dataset_ids: tuple[str, ...]
    job_refs: tuple[str, ...]
    updated_at_ms: int
    archived: bool = False
    associations_available: bool = True


@dataclass(frozen=True)
class ReportManagementState:
    source_refs: tuple[str, ...] = ()
    dataset_ids: tuple[str, ...] = ()
    job_refs: tuple[str, ...] = ()
    archived: bool = False

    def bindings(self) -> dict[str, list[str]]:
        return {
            "source_refs": list(self.source_refs),
            "dataset_ids": list(self.dataset_ids),
            "job_refs": list(self.job_refs),
        }


class WorkspaceReportNotFound(ValueError):
    pass


class ReportDeletionCommittedError(RuntimeError):
    def __init__(
        self,
        report_ref: str,
        error: Exception,
        *,
        metadata_cleared: bool,
        catalog_reconciled: bool,
    ) -> None:
        self.report_ref = report_ref
        self.metadata_cleared = metadata_cleared
        self.catalog_reconciled = catalog_reconciled
        super().__init__(f"Report was removed but finalization failed: {error}")


class WorkspaceReportLibrary:
    """Own workspace report packages and their logical source bindings."""

    def __init__(
        self,
        workspace_root: Path,
        source_rows: Callable[[], list[dict[str, Any]]],
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.workspace_root = workspace_root.expanduser().resolve()
        self.reports_root = self.workspace_root / "reports"
        self._source_rows = source_rows
        self._now = now or datetime.now
        self._bound_source_refs_cache: frozenset[str] | None = None
        self._bound_source_refs_lock = Lock()

    def import_file(
        self,
        source_path: str | Path,
        source_keys: list[str],
        *,
        dataset_ids: list[str] | None = None,
        job_refs: list[str] | None = None,
    ) -> str:
        source_refs = self._source_refs_for_source_keys(source_keys, allow_empty=True)
        source = Path(source_path).expanduser()
        if not source.is_absolute():
            raise ValueError("report path must be absolute")
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"report path must be a regular file: {source}")
        self._format_for_filename(source.name)
        content = self._read_content(source)

        self._ensure_reports_root()
        report_id = self._next_report_id()
        temp_dir = self.reports_root / f".tmp-{report_id}-{uuid4().hex}"
        final_dir = self.reports_root / report_id
        try:
            temp_dir.mkdir()
            (temp_dir / source.name).write_bytes(content)
            self._write_state(
                temp_dir / REPORT_STATE_FILENAME, source_refs, dataset_ids, job_refs
            )
            temp_dir.replace(final_dir)
        except Exception:
            if temp_dir.exists() and not temp_dir.is_symlink():
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        self._invalidate_bound_source_refs()
        return report_id

    def catalog(
        self,
        source_rows: list[dict[str, Any]] | None = None,
        *,
        include_archived: bool = True,
    ) -> list[dict[str, Any]]:
        if not self._reports_root_is_safe():
            return []
        ref_to_source_key = self._ref_to_source_key(source_rows)
        reports = self.metadata()
        return [
            {
                "report_ref": workspace_report_ref(report.report_id),
                "report_id": report.report_id,
                "filename": report.filename,
                "format": report.format,
                "source_keys": [
                    ref_to_source_key[source_ref]
                    for source_ref in report.source_refs
                    if source_ref in ref_to_source_key
                ],
            }
            for report in reports
            if include_archived or not report.archived
        ]

    def metadata(self, report_id: str | None = None) -> list[WorkspaceReportMetadata]:
        if report_id is not None:
            return [self._package_metadata_or_damaged(report_id)]
        if not self._reports_root_is_safe():
            return []
        reports: list[WorkspaceReportMetadata] = []
        for child in self.reports_root.iterdir():
            if (
                child.is_symlink()
                or not child.is_dir()
                or not self._is_valid_report_id(child.name)
            ):
                continue
            try:
                reports.append(self._package_metadata_or_damaged(child.name))
            except (OSError, UnicodeError, ValueError):
                continue
        reports.sort(
            key=lambda report: self._report_sort_key(report.report_id), reverse=True
        )
        return reports

    def bound_source_refs(self) -> set[str]:
        with self._bound_source_refs_lock:
            if self._bound_source_refs_cache is None:
                source_refs = {
                    ref for report in self.metadata() for ref in report.source_refs
                }
                self._bound_source_refs_cache = frozenset(source_refs)
            return set(self._bound_source_refs_cache)

    def read(self, report_id: str) -> WorkspaceReport:
        metadata = self._read_package_metadata(report_id)
        content = self._read_content(metadata.report_path)
        return WorkspaceReport(
            report_ref=workspace_report_ref(metadata.report_id),
            report_id=metadata.report_id,
            filename=metadata.filename,
            format=metadata.format,
            source_refs=metadata.source_refs,
            content=content,
        )

    def management_state(self, report_ref: str) -> tuple[ReportManagementState, int]:
        if report_ref.startswith(PACKAGE_REPORT_REF_PREFIX):
            report = self._read_package_metadata(
                report_ref[len(PACKAGE_REPORT_REF_PREFIX) :]
            )
            if not report.associations_available:
                raise ValueError(
                    "report management state is unavailable; repair it before editing"
                )
            return ReportManagementState(
                report.source_refs, report.dataset_ids, report.job_refs, report.archived
            ), report.updated_at_ms
        path = self._association_path(report_ref)
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError("invalid report associations file")
        if not path.exists():
            return ReportManagementState(), 0
        state, updated_at_ns = self._read_state(path)
        if state.source_refs:
            raise ValueError(
                "canonical report associations cannot contain session bindings"
            )
        return state, updated_at_ns // 1_000_000

    def replace_bindings(
        self,
        report_ref: str,
        resolve_bindings: Callable[[ReportManagementState], dict[str, list[str]]],
    ) -> None:
        with self._management_state_lease(report_ref):
            current, _ = self.management_state(report_ref)
            bindings = resolve_bindings(current)
            source_refs = [
                self._validate_source_ref(ref) for ref in bindings["source_refs"]
            ]
            self._replace_management_state(
                report_ref,
                replace(
                    current,
                    source_refs=tuple(source_refs),
                    dataset_ids=tuple(bindings["dataset_ids"]),
                    job_refs=tuple(bindings["job_refs"]),
                ),
            )

    def set_archived(
        self,
        report_ref: str,
        archived: bool,
        *,
        validate_exists: Callable[[], None] | None = None,
    ) -> None:
        if type(archived) is not bool:
            raise ValueError("archived must be a boolean")
        with self._management_state_lease(report_ref):
            if validate_exists is not None:
                validate_exists()
            current, _ = self.management_state(report_ref)
            if current.archived == archived:
                return
            self._replace_management_state(
                report_ref, replace(current, archived=archived)
            )

    def _replace_management_state(
        self,
        report_ref: str,
        state: ReportManagementState,
    ) -> None:
        if report_ref.startswith(PACKAGE_REPORT_REF_PREFIX):
            path = (
                self._package_dir(report_ref[len(PACKAGE_REPORT_REF_PREFIX) :])
                / REPORT_STATE_FILENAME
            )
        else:
            if state.source_refs:
                raise ValueError(
                    "evaluation report source associations cannot be edited"
                )
            self._ensure_reports_root()
            path = self._association_path(report_ref)
            path.parent.mkdir(exist_ok=True)
        temp_path = self.reports_root / f".state-tmp-{uuid4().hex}"
        try:
            self._write_state(temp_path, **state.bindings(), archived=state.archived)
            temp_path.replace(path)
        finally:
            if temp_path.exists() and not temp_path.is_symlink():
                temp_path.unlink()
        if report_ref.startswith(PACKAGE_REPORT_REF_PREFIX):
            self._invalidate_bound_source_refs()

    @contextmanager
    def _management_state_lease(self, report_ref: str, *, blocking: bool = True):
        if report_ref.startswith(PACKAGE_REPORT_REF_PREFIX):
            self._package_dir(report_ref[len(PACKAGE_REPORT_REF_PREFIX) :])
        else:
            self._association_path(report_ref)
        self._ensure_reports_root()
        root = self.reports_root / ".management-locks"
        if root.is_symlink():
            raise ValueError("report management lock directory must not be a symlink")
        root.mkdir(exist_ok=True)
        path = root / (hashlib.sha256(report_ref.encode("utf-8")).hexdigest() + ".lock")
        with blocking_file_lease(
            path, label="Report management lock", blocking=blocking
        ):
            yield

    def _association_path(self, report_ref: str) -> Path:
        if not re.fullmatch(r"analysis:[0-9a-f]{64}", report_ref):
            raise WorkspaceReportNotFound(f"unknown report: {report_ref}")
        root = self.reports_root / ".associations"
        if self.reports_root.is_symlink() or root.is_symlink():
            raise ValueError("report associations directory must not be a symlink")
        return root / (hashlib.sha256(report_ref.encode("utf-8")).hexdigest() + ".json")

    def delete(self, report_id: str) -> None:
        with self._management_state_lease(workspace_report_ref(report_id)):
            self._delete_package(report_id)

    def _delete_package(self, report_id: str) -> None:
        package_dir = self._package_dir(report_id)
        if package_dir.is_symlink() or not package_dir.is_dir():
            raise WorkspaceReportNotFound(f"unknown report: {report_id}")
        tombstone = self.reports_root / f".delete-{report_id}-{uuid4().hex}"
        package_dir.replace(tombstone)
        self._invalidate_bound_source_refs()
        try:
            shutil.rmtree(tombstone)
        except Exception as exc:
            # Metadata was detached with the package; imported reports have no
            # catalog projection to reconcile. Only tombstone cleanup remains.
            raise ReportDeletionCommittedError(
                workspace_report_ref(report_id),
                exc,
                metadata_cleared=True,
                catalog_reconciled=True,
            ) from exc

    def clear_management_state(self, report_ref: str, *, blocking: bool = True) -> None:
        with self._management_state_lease(report_ref, blocking=blocking):
            path = self._association_path(report_ref)
            if path.exists() and not path.is_symlink() and not path.is_file():
                raise ValueError("invalid report associations file")
            path.unlink(missing_ok=True)

    def _invalidate_bound_source_refs(self) -> None:
        with self._bound_source_refs_lock:
            self._bound_source_refs_cache = None

    def _package_metadata_or_damaged(self, report_id: str) -> WorkspaceReportMetadata:
        try:
            return self._read_package_metadata(report_id)
        except (OSError, UnicodeError, ValueError):
            package = self._package_dir(report_id)
            try:
                info = package.stat(follow_symlinks=False)
            except FileNotFoundError as exc:
                raise WorkspaceReportNotFound(f"unknown report: {report_id}") from exc
            if (
                not stat.S_ISDIR(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise WorkspaceReportNotFound(f"unknown report: {report_id}")
            return WorkspaceReportMetadata(
                report_id,
                report_id,
                "unavailable",
                (),
                package,
                (),
                (),
                info.st_mtime_ns // 1_000_000,
                associations_available=False,
            )

    def _read_package_metadata(self, report_id: str) -> WorkspaceReportMetadata:
        package_dir = self._package_dir(report_id)
        if package_dir.is_symlink() or not package_dir.is_dir():
            raise WorkspaceReportNotFound(f"unknown report: {report_id}")
        entries = list(package_dir.iterdir())
        state_path = package_dir / REPORT_STATE_FILENAME
        report_files = [
            path
            for path in entries
            if path.name != REPORT_STATE_FILENAME
            and path.suffix.lower() in REPORT_FORMATS
        ]
        if len(report_files) != 1:
            raise ValueError(f"invalid report package: {report_id}")
        report_path = report_files[0]
        if any(path not in {state_path, report_path} for path in entries):
            raise ValueError(f"invalid report package: {report_id}")
        if report_path.is_symlink() or not report_path.is_file():
            raise ValueError(f"invalid report package: {report_id}")
        if report_path.resolve().parent != package_dir.resolve():
            raise ValueError(f"invalid report package: {report_id}")

        report_info = report_path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(report_info.st_mode)
            or getattr(report_info, "st_file_attributes", 0) & 0x400
        ):
            raise ValueError(f"invalid report package: {report_id}")
        available = True
        updated_at_ns = 0
        try:
            if state_path.is_symlink() or not state_path.is_file():
                raise ValueError("invalid report state file")
            state, updated_at_ns = self._read_state(state_path)
        except (OSError, UnicodeError, ValueError):
            state, available = ReportManagementState(), False
            try:
                updated_at_ns = state_path.lstat().st_mtime_ns
            except FileNotFoundError:
                pass
        return WorkspaceReportMetadata(
            report_id=report_id,
            filename=report_path.name,
            format=self._format_for_filename(report_path.name),
            source_refs=state.source_refs,
            report_path=report_path,
            dataset_ids=state.dataset_ids,
            job_refs=state.job_refs,
            updated_at_ms=max(updated_at_ns, report_info.st_mtime_ns) // 1_000_000,
            archived=state.archived,
            associations_available=available,
        )

    def _read_state(self, state_path: Path) -> tuple[ReportManagementState, int]:
        content, opened = self._read_file(state_path, REPORT_STATE_MAX_BYTES)
        try:
            payload = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"failed to parse {state_path}: {exc}") from exc
        return self._validate_state(payload, str(state_path)), opened.st_mtime_ns

    def _validate_state(self, payload: Any, label: str) -> ReportManagementState:
        if (
            not isinstance(payload, dict)
            or "source_refs" not in payload
            or set(payload) - {"source_refs", "dataset_ids", "job_refs", "archived"}
        ):
            raise ValueError(
                f"{label} must contain source_refs and optional dataset_ids / job_refs"
            )
        raw_refs = payload["source_refs"]
        if not isinstance(raw_refs, list):
            raise ValueError(f"{label} source_refs must be an array")
        source_refs: list[str] = []
        for raw_ref in raw_refs:
            if not isinstance(raw_ref, str):
                raise ValueError(f"{label} source_refs must contain strings")
            source_refs.append(self._validate_source_ref(raw_ref))
        if len(set(source_refs)) != len(source_refs):
            raise ValueError(f"{label} source_refs must be de-duplicated")
        result = {"source_refs": source_refs}
        for field in ("dataset_ids", "job_refs"):
            values = payload.get(field, [])
            if (
                not isinstance(values, list)
                or any(
                    not isinstance(value, str) or not value.strip() for value in values
                )
                or len(set(values)) != len(values)
            ):
                raise ValueError(
                    f"{label} {field} must contain unique nonempty strings"
                )
            result[field] = values
        archived = payload.get("archived", False)
        if type(archived) is not bool:
            raise ValueError(f"{label} archived must be a boolean")
        return ReportManagementState(
            tuple(source_refs),
            tuple(result["dataset_ids"]),
            tuple(result["job_refs"]),
            archived,
        )

    def _source_refs_for_source_keys(
        self,
        source_keys: list[str],
        *,
        allow_empty: bool = False,
    ) -> list[str]:
        if not isinstance(source_keys, list):
            raise ValueError("source_keys must be an array")
        ordered_keys: list[str] = []
        seen: set[str] = set()
        for raw_key in source_keys:
            key = str(raw_key).strip()
            if key and key not in seen:
                seen.add(key)
                ordered_keys.append(key)
        if not ordered_keys:
            if allow_empty and not source_keys:
                return []
            raise ValueError("source_keys must include at least one source")
        key_to_ref = self._source_key_to_ref()
        source_refs: list[str] = []
        for source_key in ordered_keys:
            source_ref = key_to_ref.get(source_key)
            if source_ref is None:
                raise ValueError(f"unknown or unreadable source: {source_key}")
            source_refs.append(source_ref)
        return source_refs

    def _source_key_to_ref(
        self,
        source_rows: list[dict[str, Any]] | None = None,
    ) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for row in self._source_rows() if source_rows is None else source_rows:
            if not self._row_is_readable(row):
                continue
            source_key = str(row.get("source_key") or "").strip()
            try:
                source_ref = self._validate_source_ref(
                    str(row.get("source_ref") or row.get("artifact_dir") or "")
                )
            except ValueError:
                continue
            mapping.setdefault(source_key, source_ref)
        return mapping

    def _ref_to_source_key(
        self,
        source_rows: list[dict[str, Any]] | None = None,
    ) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for row in self._source_rows() if source_rows is None else source_rows:
            source_key = str(row.get("source_key") or "").strip()
            if not source_key:
                continue
            try:
                source_ref = self._validate_source_ref(
                    str(row.get("source_ref") or row.get("artifact_dir") or "")
                )
            except ValueError:
                continue
            mapping.setdefault(source_ref, source_key)
        return mapping

    @staticmethod
    def _row_is_readable(row: dict[str, Any]) -> bool:
        return (
            bool(row.get("source_key"))
            and bool(row.get("source_ref") or row.get("artifact_dir"))
            and bool(row.get("readable", row.get("last_status") != "missing"))
        )

    def _validate_source_ref(self, raw_ref: str) -> str:
        if not raw_ref or "\\" in raw_ref:
            raise ValueError("report source_ref must be normalized and relative")
        path = PurePosixPath(raw_ref)
        if path.is_absolute() or path.as_posix() != raw_ref:
            raise ValueError("report source_ref must be normalized and relative")
        parts = path.parts
        if not parts:
            raise ValueError("report source_ref must identify a workspace source")
        valid_shape = (len(parts) == 5 and parts[0] == "runs") or (
            parts[0] == "harbor"
            and (len(parts) == 4 or (len(parts) == 6 and parts[4] == "steps"))
        )
        if not valid_shape or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("report source_ref must identify a workspace source")
        if parts[0] == "harbor":
            return path.as_posix()
        try:
            resolved = (self.workspace_root / Path(*parts)).resolve()
        except (OSError, RuntimeError) as exc:
            raise ValueError("report source_ref cannot be resolved safely") from exc
        if (
            self.workspace_root != resolved
            and self.workspace_root not in resolved.parents
        ):
            raise ValueError("report source_ref escapes the workspace")
        return path.as_posix()

    def _package_dir(self, report_id: str) -> Path:
        if not isinstance(report_id, str) or not self._is_valid_report_id(report_id):
            raise WorkspaceReportNotFound(f"unknown report: {report_id}")
        if not self._reports_root_is_safe():
            raise WorkspaceReportNotFound(f"unknown report: {report_id}")
        package_dir = self.reports_root / report_id
        if package_dir.resolve().parent != self.reports_root.resolve():
            raise WorkspaceReportNotFound(f"unknown report: {report_id}")
        return package_dir

    def _ensure_reports_root(self) -> None:
        if self.reports_root.is_symlink():
            raise ValueError("workspace reports directory must not be a symlink")
        if self.reports_root.exists() and not self.reports_root.is_dir():
            raise ValueError("workspace reports path must be a directory")
        self.reports_root.mkdir(parents=True, exist_ok=True)

    def _reports_root_is_safe(self) -> bool:
        return (
            self.reports_root.exists()
            and not self.reports_root.is_symlink()
            and self.reports_root.is_dir()
            and self.reports_root.resolve().parent == self.workspace_root
        )

    def _next_report_id(self) -> str:
        base = self._now().strftime("%Y%m%d-%H%M%S-%f")
        candidate = base
        collision = 2
        while (self.reports_root / candidate).exists() or (
            self.reports_root / candidate
        ).is_symlink():
            candidate = f"{base}-{collision}"
            collision += 1
        return candidate

    @staticmethod
    def _report_sort_key(report_id: str) -> tuple[str, int]:
        match = REPORT_ID_RE.fullmatch(report_id)
        if match is None:
            raise ValueError(f"invalid report id: {report_id}")
        return match.group("timestamp"), int(match.group("collision") or 1)

    @staticmethod
    def _is_valid_report_id(report_id: str) -> bool:
        match = REPORT_ID_RE.fullmatch(report_id)
        if match is None:
            return False
        try:
            datetime.strptime(match.group("timestamp"), "%Y%m%d-%H%M%S-%f")
        except ValueError:
            return False
        return True

    @staticmethod
    def _format_for_filename(filename: str) -> str:
        report_format = REPORT_FORMATS.get(Path(filename).suffix.lower())
        if report_format is None:
            allowed = ", ".join(sorted(REPORT_FORMATS))
            raise ValueError(
                f"unsupported report format: {filename}; expected {allowed}"
            )
        return report_format

    @staticmethod
    def _validate_content(content: bytes, path: Path) -> None:
        if len(content) > REPORT_MAX_BYTES:
            raise ValueError(f"report exceeds {REPORT_MAX_BYTES} byte limit: {path}")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"report must be UTF-8: {path}") from exc

    @classmethod
    def _read_content(cls, path: Path) -> bytes:
        content, _ = cls._read_file(path, REPORT_MAX_BYTES)
        cls._validate_content(content, path)
        return content

    @staticmethod
    def _read_file(path: Path, limit: int) -> tuple[bytes, os.stat_result]:
        before = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or getattr(before, "st_file_attributes", 0) & 0x400
        ):
            raise ValueError(f"report path must be a regular file: {path}")
        if before.st_size > limit:
            raise ValueError(f"report exceeds {limit} byte limit: {path}")
        with os.fdopen(open_read_descriptor(path), "rb") as source:
            opened = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(opened.st_mode)
                or getattr(opened, "st_file_attributes", 0) & 0x400
                or not os.path.samestat(before, opened)
            ):
                raise ValueError(f"report changed while opening: {path}")
            if opened.st_size > limit:
                raise ValueError(f"report exceeds {limit} byte limit: {path}")
            content = source.read(limit + 1)
        if len(content) > limit:
            raise ValueError(f"report exceeds {limit} byte limit: {path}")
        return content, opened

    def _write_state(
        self,
        path: Path,
        source_refs: list[str],
        dataset_ids: list[str] | None = None,
        job_refs: list[str] | None = None,
        *,
        archived: bool = False,
    ) -> None:
        payload: dict[str, Any] = {"source_refs": source_refs}
        if dataset_ids is not None:
            payload["dataset_ids"] = dataset_ids
        if job_refs is not None:
            payload["job_refs"] = job_refs
        if archived:
            payload["archived"] = True
        state = self._validate_state(payload, "report associations")
        payload = {
            key: values
            for key, values in state.bindings().items()
            if key == "source_refs" or values
        }
        if state.archived:
            payload["archived"] = True
        content = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode(
            "utf-8"
        )
        if len(content) > REPORT_STATE_MAX_BYTES:
            raise ValueError(
                f"report state exceeds {REPORT_STATE_MAX_BYTES} byte limit: {path}"
            )
        path.write_bytes(content)


def workspace_report_ref(report_id: str) -> str:
    return f"{PACKAGE_REPORT_REF_PREFIX}{report_id}"


def render_report_preview(report: RenderableReport) -> bytes:
    if report.format == "html":
        return report.content
    markdown = report.content.decode("utf-8")
    rendered = (
        MarkdownIt("commonmark", {"html": False})
        .enable(["table", "strikethrough"])
        .render(markdown)
    )
    title = html.escape(report.filename)
    return (
        "<!doctype html>\n"
        '<html><head><meta charset="utf-8">'
        f"<title>{title}</title>"
        "<style>"
        "body{font:15px/1.6 system-ui,sans-serif;max-width:900px;margin:0 auto;padding:24px;"
        "background:#fffdf8;color:#27231b}"
        "a{color:#315f8f}pre{overflow:auto;padding:12px;background:#f5f3ee}"
        "table{border-collapse:collapse}th,td{border:1px solid #8888;padding:6px 10px}"
        "img{max-width:100%}"
        "</style></head><body>"
        f"{rendered}</body></html>"
    ).encode("utf-8")


def render_report_reader_page(report: RenderableReport) -> bytes:
    """Render a top-level shell that preserves the preview iframe sandbox."""
    title = html.escape(report.filename)
    preview_path = (
        f"/api/report-library/{quote(str(report.report_ref), safe='')}/preview"
    )
    return (
        "<!doctype html>\n"
        '<html><head><meta charset="utf-8">'
        f"<title>{title}</title>"
        "<style>html,body,iframe{width:100%;height:100%;margin:0;border:0}"
        "body{overflow:hidden;background:#fffdf8}</style>"
        "</head><body>"
        f'<iframe src="{preview_path}" title="{title}" sandbox="allow-scripts" '
        'referrerpolicy="no-referrer"></iframe>'
        "</body></html>"
    ).encode("utf-8")
