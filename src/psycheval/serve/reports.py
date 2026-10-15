"""HTTP access to report metadata, lifecycle, previews, and readers."""

from urllib.parse import quote

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response

from psycheval.report_library import ReportNotFound
from psycheval.serve.api_access import (
    ADMIN_ACCESS,
    GUEST_ACCESS,
    access,
    mutation_guard,
    require_admin,
)
from psycheval.serve.api_http import ProblemException
from psycheval.serve.api_http import json_response as _json
from psycheval.serve.api_models import (
    ReportBindingsRequest,
    ReportImportRequest,
    ReportStateRequest,
)
from psycheval.serve.api_support import workspace_write, writable_runtime
from psycheval.serve.runtime import ServeRuntime
from psycheval.workspace_reports import (
    PACKAGE_REPORT_REF_PREFIX,
    WorkspaceReportNotFound,
    render_report_preview,
    render_report_reader_page,
)

REPORT_PREVIEW_CSP = "; ".join(
    [
        "default-src 'none'",
        "sandbox allow-scripts",
        "script-src 'unsafe-inline' http: https: data: blob:",
        "style-src 'unsafe-inline' http: https: data: blob:",
        "img-src http: https: data: blob:",
        "media-src http: https: data: blob:",
        "font-src http: https: data: blob:",
        "connect-src http: https: data: blob:",
        "frame-src http: https: data: blob:",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'none'",
    ]
)

REPORT_READER_CSP = "; ".join(
    [
        "default-src 'none'",
        "frame-src 'self'",
        "style-src 'unsafe-inline'",
        "base-uri 'none'",
        "form-action 'none'",
        "frame-ancestors 'none'",
    ]
)


def report_deletion_invalidations(report_ref: str) -> str:
    return (
        "reports"
        if report_ref.startswith(PACKAGE_REPORT_REF_PREFIX)
        else "reports,catalog"
    )


def register_report_routes(app: FastAPI) -> None:
    @app.get("/api/reports")
    @access(GUEST_ACCESS)
    def reports(request: Request) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        return _json(runtime.workspace_report_catalog())

    @app.get("/api/report-library")
    @access(GUEST_ACCESS)
    def report_library(
        request: Request,
        page: int = 1,
        page_size: int = 50,
        search: str = "",
        state: str = "active",
    ) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        try:
            return _json(
                runtime.report_library.query(
                    page=page,
                    page_size=page_size,
                    search=search,
                    kinds=request.query_params.getlist("kind"),
                    datasets=request.query_params.getlist("dataset"),
                    jobs=request.query_params.getlist("job"),
                    state=state,
                )
            )
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc

    @app.get("/api/report-library/targets")
    @access(GUEST_ACCESS)
    def report_targets(
        request: Request,
        kind: str,
        page: int = 1,
        page_size: int = 50,
        search: str = "",
    ) -> JSONResponse:
        try:
            return _json(
                request.app.state.runtime.report_library.targets(
                    kind=kind, page=page, page_size=page_size, search=search
                )
            )
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc

    @app.get("/api/report-library/{report_ref}")
    @access(GUEST_ACCESS)
    def report_metadata(request: Request, report_ref: str) -> JSONResponse:
        try:
            return _json(request.app.state.runtime.report_library.metadata(report_ref))
        except ReportNotFound as exc:
            raise ProblemException(404, str(exc)) from exc

    @app.post(
        "/api/reports",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def import_report(request: Request, body: ReportImportRequest) -> JSONResponse:
        runtime = writable_runtime(request)
        try:
            with workspace_write(runtime):
                bindings = [binding.model_dump() for binding in body.bindings]
                state = runtime.report_library.validate_bindings(bindings)
                report_id = runtime.workspace_reports.import_file(
                    body.path,
                    [
                        binding["key"]
                        for binding in bindings
                        if binding["kind"] == "session"
                    ],
                    dataset_ids=state["dataset_ids"],
                    job_refs=state["job_refs"],
                )
                report = runtime.report_library.metadata("package:" + report_id)
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc
        return _json(
            report,
            status=201,
            headers={
                "Location": f"/api/report-library/{quote(report['report_ref'], safe='')}"
            },
        )

    @app.put(
        "/api/report-library/{report_ref}/bindings",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def replace_report_bindings(
        request: Request, report_ref: str, body: ReportBindingsRequest
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        try:
            runtime.report_library.replace_bindings(
                report_ref,
                [binding.model_dump() for binding in body.bindings],
            )
            report = runtime.report_library.metadata(report_ref)
        except (ReportNotFound, WorkspaceReportNotFound) as exc:
            raise ProblemException(404, str(exc)) from exc
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc
        return _json(report)

    @app.put(
        "/api/report-library/{report_ref}/state",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def set_report_state(
        request: Request, report_ref: str, body: ReportStateRequest
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        try:
            report = runtime.report_library.set_archived(report_ref, body.archived)
        except (ReportNotFound, WorkspaceReportNotFound) as exc:
            raise ProblemException(404, str(exc)) from exc
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc
        return _json(report)

    @app.delete(
        "/api/report-library/{report_ref}",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
        status_code=204,
    )
    @access(ADMIN_ACCESS)
    def delete_report(request: Request, report_ref: str) -> Response:
        runtime = writable_runtime(request)
        try:
            # Each report owner coordinates its own mutation; management waits
            # must not hold the catalog writer.
            runtime.report_library.delete(report_ref)
        except (ReportNotFound, WorkspaceReportNotFound) as exc:
            raise ProblemException(404, str(exc)) from exc
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc
        return Response(
            status_code=204,
            headers={
                "X-Peval-Invalidations": report_deletion_invalidations(report_ref)
            },
        )

    @app.get("/api/report-library/{report_ref}/preview")
    @access(GUEST_ACCESS)
    def report_preview(request: Request, report_ref: str) -> Response:
        runtime: ServeRuntime = request.app.state.runtime
        try:
            report = runtime.report_library.read(report_ref)
        except ReportNotFound as exc:
            raise ProblemException(404, str(exc)) from exc
        return Response(
            render_report_preview(report),
            media_type="text/html",
            headers={
                "Content-Security-Policy": REPORT_PREVIEW_CSP,
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
            },
        )

    @app.get("/api/report-library/{report_ref}/reader")
    @access(GUEST_ACCESS)
    def report_reader(request: Request, report_ref: str) -> Response:
        runtime: ServeRuntime = request.app.state.runtime
        try:
            report = runtime.report_library.read(report_ref)
        except ReportNotFound as exc:
            raise ProblemException(404, str(exc)) from exc
        return Response(
            render_report_reader_page(report),
            media_type="text/html",
            headers={
                "Content-Security-Policy": REPORT_READER_CSP,
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
            },
        )
