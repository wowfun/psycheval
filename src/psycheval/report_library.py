from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from psycheval.evaluation_reports import EvaluationReports
from psycheval.state.catalog import WorkspaceCatalog
from psycheval.workspace_reports import (
    PACKAGE_REPORT_REF_PREFIX,
    WorkspaceReportLibrary,
)


@dataclass(frozen=True)
class ReportDocument:
    report_ref: str
    title: str
    filename: str
    format: str
    source_keys: tuple[str, ...]
    primary_source_key: str | None
    content: bytes


class ReportNotFound(ValueError):
    pass


class ReportLibrary:
    """Read canonical analyses and imported report packages by opaque reference."""

    def __init__(
        self,
        catalog: WorkspaceCatalog,
        evaluation_reports: EvaluationReports,
        workspace_reports: WorkspaceReportLibrary,
    ) -> None:
        self.catalog = catalog
        self.evaluation_reports = evaluation_reports
        self.workspace_reports = workspace_reports

    def evaluation_catalog(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        search: str = "",
    ) -> dict[str, Any]:
        return self.catalog.evaluation_report_page(
            page=page,
            page_size=page_size,
            search=search,
        )

    def read(self, report_ref: str) -> ReportDocument:
        value = str(report_ref or "")
        if value.startswith("analysis:"):
            return self._read_evaluation_report(value)
        if value.startswith(PACKAGE_REPORT_REF_PREFIX):
            return self._read_workspace_report(value)
        raise ReportNotFound(f"unknown report: {value}")

    def _read_evaluation_report(self, report_ref: str) -> ReportDocument:
        try:
            metadata = self.catalog.evaluation_report_location(report_ref)
            report = self.evaluation_reports.read(str(metadata["source_ref"]))
        except (OSError, ValueError) as exc:
            raise ReportNotFound(f"unknown report: {report_ref}") from exc
        if report is None or report.report_ref != report_ref:
            raise ReportNotFound(f"unknown report: {report_ref}")
        return ReportDocument(
            report_ref=report_ref,
            title=str(metadata["title"]),
            filename=str(metadata["filename"]),
            format=str(metadata["format"]),
            source_keys=tuple(str(key) for key in metadata["source_keys"]),
            primary_source_key=str(metadata["primary_source_key"]),
            content=report.content.encode("utf-8"),
        )

    def _read_workspace_report(self, report_ref: str) -> ReportDocument:
        report_id = report_ref[len(PACKAGE_REPORT_REF_PREFIX) :]
        if not report_id:
            raise ReportNotFound(f"unknown report: {report_ref}")
        try:
            report = self.workspace_reports.read(report_id)
            metadata = next(
                item
                for item in self.workspace_reports.catalog()
                if item["report_id"] == report_id
            )
        except (OSError, UnicodeError, ValueError, StopIteration) as exc:
            raise ReportNotFound(f"unknown report: {report_ref}") from exc
        source_keys = tuple(str(key) for key in metadata["source_keys"])
        return ReportDocument(
            report_ref=report_ref,
            title=report.filename,
            filename=report.filename,
            format=report.format,
            source_keys=source_keys,
            primary_source_key=source_keys[0] if source_keys else None,
            content=report.content,
        )


__all__ = ["ReportDocument", "ReportLibrary", "ReportNotFound"]
