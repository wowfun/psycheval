from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from psycheval.evaluation_reports import EvaluationReports
from psycheval.report_targets import ReportTargets
from psycheval.state.catalog import WorkspaceCatalog
from psycheval.workspace_reports import (
    PACKAGE_REPORT_REF_PREFIX,
    WorkspaceReportLibrary,
    workspace_report_ref,
)

logger = logging.getLogger(__name__)


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

    def _targets(self) -> ReportTargets:
        return ReportTargets(
            self.workspace_reports.workspace_root,
            self.catalog.config,
            self.catalog.binding_rows(),
        )

    def query(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        search: str = "",
        kinds: list[str] | None = None,
        datasets: list[str] | None = None,
        jobs: list[str] | None = None,
    ) -> dict[str, Any]:
        if any(
            kind not in {"session", "dataset", "job", "unassociated"}
            for kind in kinds or []
        ):
            raise ValueError("unknown association kind")
        targets = self._targets()
        items = self._metadata(targets)
        needle = search.strip().casefold()
        jobs = [targets.job_aliases.get(key, key) for key in jobs or []]

        def matches(item: dict[str, Any]) -> bool:
            associations = item["associations"]
            if (
                kinds
                and not any(target["kind"] in kinds for target in associations)
                and not ("unassociated" in kinds and not associations)
            ):
                return False
            if datasets and not any(
                target["kind"] == "dataset" and target["key"] in datasets
                for target in associations
            ):
                return False
            if jobs and not any(
                target["kind"] == "job" and target["key"] in jobs
                for target in associations
            ):
                return False
            return (
                not needle
                or needle
                in " ".join(
                    [
                        item["title"],
                        item["filename"],
                        *[
                            str(target["label"]) + " " + str(target["key"])
                            for target in associations
                        ],
                    ]
                ).casefold()
            )

        items = [item for item in items if matches(item)]
        items.sort(key=lambda item: (-item["updated_at_ms"], item["report_ref"]))
        return _page(items, page, page_size)

    def targets(
        self, *, kind: str, page: int = 1, page_size: int = 50, search: str = ""
    ) -> dict[str, Any]:
        if kind not in {"session", "dataset", "job"}:
            raise ValueError("association kind must be session, dataset or job")
        needle = search.strip().casefold()
        items = [
            item
            for item in self._targets().items.values()
            if item["kind"] == kind
            and item["available"]
            and (not needle or needle in (item["label"] + " " + item["key"]).casefold())
        ]
        items.sort(key=lambda item: (item["label"].casefold(), item["key"]))
        return _page(items, page, page_size)

    def metadata(self, report_ref: str) -> dict[str, Any]:
        for item in self._metadata(self._targets()):
            if item["report_ref"] == report_ref:
                return item
        raise ReportNotFound(f"unknown report: {report_ref}")

    def validate_bindings(
        self, bindings: list[dict[str, str]], *, report_ref: str | None = None
    ) -> dict[str, list[str]]:
        targets = self._targets()
        previous: list[dict[str, Any]] = []
        if report_ref is not None:
            metadata = self.metadata(report_ref)
            if metadata.get("associations_available") is False:
                raise ValueError(
                    "report associations are unavailable; repair the association data before editing"
                )
            state, _ = self.workspace_reports.associations(report_ref)
            previous = targets.bindings(state)
        retained = {(item["kind"], item["key"]) for item in previous}
        state = {"source_refs": [], "dataset_ids": [], "job_refs": []}
        for binding in bindings:
            kind, key = binding["kind"], binding["key"]
            if kind not in {"session", "dataset", "job"}:
                raise ValueError("unknown association kind")
            if kind == "session" and report_ref and report_ref.startswith("analysis:"):
                raise ValueError(
                    "evaluation report source associations cannot be edited"
                )
            target = targets.resolve(kind, key)
            key = target["key"]
            if not target["available"] and (kind, key) not in retained:
                raise ValueError(f"unknown or unavailable {kind}: {key}")
            field = {
                "session": "source_refs",
                "dataset": "dataset_ids",
                "job": "job_refs",
            }[kind]
            value = targets.session_refs[key] if kind == "session" else key
            if value not in state[field]:
                state[field].append(value)
        return state

    def _metadata(self, targets: ReportTargets) -> list[dict[str, Any]]:
        items = []
        for row in self.catalog.evaluation_report_rows():
            available = True
            try:
                state, updated = self.workspace_reports.associations(row["report_ref"])
                bindings = targets.bindings(state)
            except (OSError, UnicodeError, ValueError):
                logger.warning(
                    "Cannot read associations for report %s", row["report_ref"]
                )
                bindings, updated, available = [], 0, False
            items.append(
                {
                    **row,
                    "origin": "evaluation",
                    "bindings": bindings,
                    "associations_available": available,
                    "associations": targets.associations(row["source_keys"], bindings),
                    "updated_at_ms": max(row["updated_at_ms"], updated),
                }
            )
        for report in self.workspace_reports.metadata():
            bindings = targets.bindings(
                {
                    "source_refs": list(report.source_refs),
                    "dataset_ids": list(report.dataset_ids),
                    "job_refs": list(report.job_refs),
                }
            )
            source_keys = [
                target["key"]
                for target in bindings
                if target["kind"] == "session" and target["available"]
            ]
            items.append(
                {
                    "report_ref": workspace_report_ref(report.report_id),
                    "report_id": report.report_id,
                    "title": report.filename,
                    "filename": report.filename,
                    "format": report.format,
                    "source_keys": source_keys,
                    "primary_source_key": source_keys[0] if source_keys else None,
                    "origin": "imported",
                    "bindings": bindings,
                    "associations": targets.associations([], bindings),
                    "updated_at_ms": report.updated_at_ms,
                }
            )
        return items

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
            content=report.content.replace("\r\n", "\n")
            .replace("\r", "\n")
            .encode("utf-8"),
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


def _page(items: list[dict[str, Any]], page: int, page_size: int) -> dict[str, Any]:
    page_size = max(1, min(100, page_size))
    page = min(max(1, page), max(1, (len(items) + page_size - 1) // page_size))
    return {
        "items": items[(page - 1) * page_size : page * page_size],
        "total": len(items),
        "page": page,
        "page_size": page_size,
    }
