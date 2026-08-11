from __future__ import annotations

import html
import json
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from markdown_it import MarkdownIt

REPORT_MAX_BYTES = 20 * 1024 * 1024
REPORT_STATE_FILENAME = "state.json"
REPORT_ID_RE = re.compile(
    r"^(?P<timestamp>\d{8}-\d{6}-\d{6})(?:-(?P<collision>[2-9]|[1-9]\d+))?$"
)
REPORT_FORMATS = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
}


@dataclass(frozen=True)
class WorkspaceReport:
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


class WorkspaceReportNotFound(ValueError):
    pass


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

    def import_file(self, source_path: str | Path, source_keys: list[str]) -> str:
        source_refs = self._source_refs_for_source_keys(source_keys)
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
            self._write_state(temp_dir / REPORT_STATE_FILENAME, source_refs)
            temp_dir.replace(final_dir)
        except Exception:
            if temp_dir.exists() and not temp_dir.is_symlink():
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        return report_id

    def catalog(
        self,
        source_rows: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        if not self._reports_root_is_safe():
            return []
        ref_to_source_key = self._ref_to_source_key(source_rows)
        reports: list[WorkspaceReportMetadata] = []
        for child in self.reports_root.iterdir():
            if (
                child.is_symlink()
                or not child.is_dir()
                or not self._is_valid_report_id(child.name)
            ):
                continue
            try:
                reports.append(self._read_package_metadata(child.name))
            except (OSError, UnicodeError, ValueError):
                continue
        reports.sort(
            key=lambda report: self._report_sort_key(report.report_id), reverse=True
        )
        return [
            {
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
        ]

    def read(self, report_id: str) -> WorkspaceReport:
        metadata = self._read_package_metadata(report_id)
        content = self._read_content(metadata.report_path)
        return WorkspaceReport(
            report_id=metadata.report_id,
            filename=metadata.filename,
            format=metadata.format,
            source_refs=metadata.source_refs,
            content=content,
        )

    def replace_bindings(self, report_id: str, source_keys: list[str]) -> None:
        report = self._read_package_metadata(report_id)
        source_refs = self._source_refs_for_source_keys(
            source_keys,
            allow_empty=True,
        )
        package_dir = self._package_dir(report.report_id)
        temp_path = package_dir / f".{REPORT_STATE_FILENAME}.tmp-{uuid4().hex}"
        try:
            self._write_state(temp_path, source_refs)
            temp_path.replace(package_dir / REPORT_STATE_FILENAME)
        finally:
            if temp_path.exists() and not temp_path.is_symlink():
                temp_path.unlink()

    def delete(self, report_id: str) -> None:
        report = self._read_package_metadata(report_id)
        package_dir = self._package_dir(report.report_id)
        tombstone = self.reports_root / f".delete-{report.report_id}-{uuid4().hex}"
        package_dir.replace(tombstone)
        shutil.rmtree(tombstone)

    def _read_package_metadata(self, report_id: str) -> WorkspaceReportMetadata:
        package_dir = self._package_dir(report_id)
        if package_dir.is_symlink() or not package_dir.is_dir():
            raise WorkspaceReportNotFound(f"unknown report: {report_id}")
        entries = list(package_dir.iterdir())
        if len(entries) != 2:
            raise ValueError(f"invalid report package: {report_id}")
        state_path = package_dir / REPORT_STATE_FILENAME
        if state_path.is_symlink() or not state_path.is_file():
            raise ValueError(f"invalid report package: {report_id}")
        report_files = [
            path
            for path in entries
            if path.name != REPORT_STATE_FILENAME
            and path.suffix.lower() in REPORT_FORMATS
        ]
        if len(report_files) != 1:
            raise ValueError(f"invalid report package: {report_id}")
        report_path = report_files[0]
        if report_path.is_symlink() or not report_path.is_file():
            raise ValueError(f"invalid report package: {report_id}")
        if report_path.resolve().parent != package_dir.resolve():
            raise ValueError(f"invalid report package: {report_id}")

        source_refs = self._read_state(state_path)
        if report_path.stat().st_size > REPORT_MAX_BYTES:
            raise ValueError(
                f"report exceeds {REPORT_MAX_BYTES} byte limit: {report_path}"
            )
        return WorkspaceReportMetadata(
            report_id=report_id,
            filename=report_path.name,
            format=self._format_for_filename(report_path.name),
            source_refs=tuple(source_refs),
            report_path=report_path,
        )

    def _read_state(self, state_path: Path) -> list[str]:
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"failed to parse {state_path}: {exc}") from exc
        if not isinstance(payload, dict) or set(payload) != {"source_refs"}:
            raise ValueError(f"{state_path} must contain only source_refs")
        raw_refs = payload["source_refs"]
        if not isinstance(raw_refs, list):
            raise ValueError(f"{state_path} source_refs must be an array")
        source_refs: list[str] = []
        for raw_ref in raw_refs:
            if not isinstance(raw_ref, str):
                raise ValueError(f"{state_path} source_refs must contain strings")
            source_refs.append(self._validate_source_ref(raw_ref))
        if len(set(source_refs)) != len(source_refs):
            raise ValueError(f"{state_path} source_refs must be de-duplicated")
        return source_refs

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
        valid_shape = (len(parts) == 5 and parts[0] == "runs") or (
            len(parts) == 4 and parts[0] == "harbor"
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
        if path.stat().st_size > REPORT_MAX_BYTES:
            raise ValueError(f"report exceeds {REPORT_MAX_BYTES} byte limit: {path}")
        with path.open("rb") as source:
            content = source.read(REPORT_MAX_BYTES + 1)
        cls._validate_content(content, path)
        return content

    @staticmethod
    def _write_state(path: Path, source_refs: list[str]) -> None:
        path.write_text(
            json.dumps({"source_refs": source_refs}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )


def render_workspace_report_preview(report: WorkspaceReport) -> bytes:
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


def render_workspace_report_reader_page(report: WorkspaceReport) -> bytes:
    """Render a top-level shell that preserves the preview iframe sandbox."""
    title = html.escape(report.filename)
    preview_path = f"/api/reports/{quote(report.report_id, safe='')}/preview"
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
