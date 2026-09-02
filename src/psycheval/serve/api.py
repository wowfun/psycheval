from __future__ import annotations

import os
import re
import secrets
import stat
import tempfile
import tomllib
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any, Iterator
from urllib.parse import quote

from fastapi import (
    Depends,
    FastAPI,
    Header,
    Request,
    Response,
    WebSocket,
    WebSocketException,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from psycheval.adapters import available_adapter_ids, normalize_adapter_id
from psycheval.config import (
    AcpAgent,
    ToolConfig,
    apply_toml_config,
    load_config,
    write_workspace_acp_agents,
    write_workspace_adapter_default_db,
    write_workspace_locale,
)
from psycheval.html import render_serve_html
from psycheval.report_library import ReportNotFound
from psycheval.serve.access import (
    ADMIN_ROLE,
    GUEST_ROLE,
    AuthenticationDisabled,
    InvalidCredentials,
    LoginRateLimited,
    ServeAccess,
)
from psycheval.serve.api_access import (
    ADMIN_ACCESS,
    GUEST_ACCESS,
    access,
    mutation_guard,
    require_admin,
    require_admin_websocket,
    require_same_origin_websocket,
    role_for,
)
from psycheval.serve.api_access import (
    verify_route_access as _verify_route_access,
)
from psycheval.serve.api_http import (
    BodyLimitMiddleware,
    Problem,
    ProblemException,
)
from psycheval.serve.api_http import (
    etag as _etag,
)
from psycheval.serve.api_http import (
    expect_revision as _expect_revision,
)
from psycheval.serve.api_http import (
    if_match_value as _if_match_value,
)
from psycheval.serve.api_http import (
    json_response as _json,
)
from psycheval.serve.api_http import (
    problem_slug as _problem_slug,
)
from psycheval.serve.api_http import (
    problem_title as _problem_title,
)
from psycheval.serve.api_models import (
    AcpContextRequest,
    BrowserViewsRequest,
    CatalogQueryRequest,
    CatalogSummaryRequest,
    ConfigPatchRequest,
    DatabaseInspectionRequest,
    DatasetCreateRequest,
    DatasetPatchRequest,
    DatasetUnregisterRequest,
    ExportRequest,
    FileCreateRequest,
    FilePatchRequest,
    FilePutRequest,
    LoginRequest,
    ManifestPutRequest,
    MountCreateRequest,
    MountDeletionRequest,
    MountPatchRequest,
    PathSelectionRequest,
    PromptPutRequest,
    ReportBindingsRequest,
    ReportImportRequest,
    SourceImportRequest,
    SourceKeysRequest,
    SourcePatchRequest,
    SourceStateOperationRequest,
    TaskCreateRequest,
    TaskDeletionRequest,
    TaskPatchRequest,
    TaskStateOperationRequest,
    ViewDeletionRequest,
    ViewPatchRequest,
    ViewPutRequest,
)
from psycheval.serve.api_support import (
    REPORT_PREVIEW_CSP,
    REPORT_READER_CSP,
    acp_context_items,
    add_source_result_payload,
    catalog_query,
    catalog_query_payload,
    catalog_view_names,
    catalog_view_names_payload,
    delete_harbor_task,
    delete_source_operation,
    evaluation_report_query,
    harbor_config_payload,
    harbor_error_status,
    harbor_workspace,
    mutate_harbor_dataset,
    mutate_harbor_task,
    mutate_harbor_task_state,
    refresh_source_operation,
    reject_linked_harbor_delete,
    source_state_operation,
    update_harbor_mount_config,
    workspace_config_payload,
)
from psycheval.serve.assets import (
    ECHARTS_ASSET_PATH,
    PEVAL_WEB_ASSET_PREFIX,
    WORKSPACE_STYLESHEET_PATH,
    cached_echarts_asset,
    packaged_web_asset_with_etag,
    workspace_stylesheet_asset,
)
from psycheval.serve.errors import HttpError
from psycheval.serve.exports import build_serve_export, build_summary_serve_export
from psycheval.serve.harbor_workspace import (
    HarborWorkspaceError,
    config_revision,
)
from psycheval.serve.path_picker import PathPickerUnavailable, pick_file_paths
from psycheval.serve.payloads import (
    catalog_post_query_payload,
    catalog_summary_payload,
    source_keys_payload,
    summary_export_payload,
)
from psycheval.serve.prompt_assets import PromptAssetConflict
from psycheval.serve.runtime import ServeRuntime
from psycheval.serve.sources import add_source_payload, db_sessions_payload
from psycheval.serve.visibility import (
    project_catalog_payload,
    project_detail_payload,
    project_guest_error,
    project_harbor_inventory,
    project_harbor_task,
    project_harbor_text_file,
)
from psycheval.state import CatalogBusyError, CatalogSummaryCapacityError
from psycheval.workspace_reports import (
    WorkspaceReportNotFound,
    render_report_preview,
    render_report_reader_page,
)
from psycheval.workspace_views import WorkspaceViewConflict, WorkspaceViewNotFound


def writable_runtime(request: Request) -> ServeRuntime:
    runtime: ServeRuntime = request.app.state.runtime
    runtime.ensure_ready()
    if runtime.is_loading():
        raise ProblemException(409, "serve catalog is checking runs")
    return runtime


def _source_rows(runtime: ServeRuntime, source_keys: list[str]) -> list[dict[str, Any]]:
    try:
        return [runtime.catalog.row_for_key(key) for key in source_keys]
    except ValueError as exc:
        raise ProblemException(404, str(exc)) from exc


@contextmanager
def workspace_write(runtime: ServeRuntime) -> Iterator[None]:
    with runtime.catalog.workspace_write_guard():
        yield


def _problem_response(
    request: Request,
    status: int,
    detail: str,
    *,
    slug: str | None = None,
    errors: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    safe_detail = project_guest_error(status, detail, role_for(request))
    problem = Problem(
        type=f"urn:peval:problem:{slug or _problem_slug(status)}",
        title=_problem_title(status),
        status=status,
        detail=safe_detail,
        instance=request.url.path,
        errors=errors,
    )
    return _json(
        problem.model_dump(exclude_none=True),
        status=status,
        media_type="application/problem+json",
        headers=headers,
    )


def _operation_payload(operation: Any) -> dict[str, Any]:
    state = operation.state
    if state == "completed":
        state = "failed" if operation.failures else "succeeded"
    return {
        "id": operation.operation_id,
        "kind": operation.operation_type,
        "state": state,
        "completed": operation.completed,
        "total": operation.total,
        "successes": list(operation.successes),
        "failures": list(operation.failures),
    }


def _operation_response(
    operation: Any, *, headers: dict[str, str] | None = None
) -> JSONResponse:
    location = f"/api/operations/{quote(operation.operation_id)}"
    response_headers = {"Location": location, "Retry-After": "1"}
    response_headers.update(headers or {})
    return _json(
        _operation_payload(operation),
        status=202,
        headers=response_headers,
    )


def _config_operation_response(runtime: ServeRuntime, operation: Any) -> JSONResponse:
    return _operation_response(
        operation,
        headers={"ETag": _etag(config_revision(runtime.store.paths.config_path))},
    )


def _config_response(runtime: ServeRuntime) -> JSONResponse:
    revision = config_revision(runtime.store.paths.config_path)
    payload = workspace_config_payload(runtime.store, runtime)
    payload.pop("revision", None)
    return _json(payload, headers={"ETag": _etag(revision)})


def _patch_workspace_config(
    runtime: ServeRuntime, body: ConfigPatchRequest, expected_revision: str
) -> None:
    adapter_defaults: dict[str, str | None] | None = None
    if body.adapter_defaults is not None:
        available = set(available_adapter_ids())
        adapter_defaults = {}
        for raw_adapter, default_path in body.adapter_defaults.items():
            adapter_id = normalize_adapter_id(raw_adapter)
            if adapter_id not in available:
                options = ", ".join(sorted(available)) or "<none>"
                raise ProblemException(
                    422,
                    f"unsupported adapter: {raw_adapter}; available adapters: {options}",
                )
            if adapter_id in adapter_defaults:
                raise ProblemException(422, f"duplicate adapter id: {adapter_id}")
            adapter_defaults[adapter_id] = default_path
    path = runtime.store.paths.config_path
    source = path.read_bytes() if path.exists() else b""
    if config_revision(path) != expected_revision:
        raise ProblemException(
            412,
            "workspace configuration changed",
            headers={"ETag": _etag(config_revision(path))},
        )
    mode = 0o600
    if path.exists():
        file_mode = path.stat(follow_symlinks=False).st_mode
        if not stat.S_ISREG(file_mode):
            raise ProblemException(409, "workspace config must be a regular file")
        mode = stat.S_IMODE(file_mode)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.patch.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(source)
            handle.flush()
            os.fsync(handle.fileno())
        if body.locale is not None:
            write_workspace_locale(temporary, body.locale)
        if adapter_defaults is not None:
            for adapter_id, default_path in adapter_defaults.items():
                write_workspace_adapter_default_db(temporary, adapter_id, default_path)
        if body.acp_agents is not None:
            agents = tuple(
                AcpAgent(
                    id=agent.id,
                    title=agent.title,
                    command=agent.command,
                    args=tuple(agent.args),
                )
                for agent in body.acp_agents
            )
            write_workspace_acp_agents(temporary, agents)
        rendered = temporary.read_bytes()
        if rendered == source:
            raise ProblemException(400, "configuration patch made no change")
        try:
            document = tomllib.loads(rendered.decode("utf-8")) if rendered else {}
            apply_toml_config(
                ToolConfig(workspace_root=str(path.parent)),
                document,
                base_dir=path.parent,
            )
        except (UnicodeDecodeError, tomllib.TOMLDecodeError, ValueError) as exc:
            raise ProblemException(422, str(exc)) from exc
        current_revision = config_revision(path)
        if current_revision != expected_revision:
            raise ProblemException(
                412,
                "workspace configuration changed",
                headers={"ETag": _etag(current_revision)},
            )
        os.chmod(temporary, mode)
        temporary.replace(path)
    except ProblemException:
        raise
    except ValueError as exc:
        raise ProblemException(422, str(exc)) from exc
    finally:
        temporary.unlink(missing_ok=True)


def _harbor_inventory_response(
    runtime: ServeRuntime, payload: dict[str, Any], role: str
) -> JSONResponse:
    revision = str(
        payload.pop("revision", config_revision(runtime.store.paths.config_path))
    )
    return _json(
        project_harbor_inventory(payload, role), headers={"ETag": _etag(revision)}
    )


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemException)
    async def problem_exception_handler(
        request: Request, exc: ProblemException
    ) -> JSONResponse:
        return _problem_response(
            request,
            exc.status,
            exc.detail,
            slug=exc.slug,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        raw_errors = exc.errors()
        malformed = any(error.get("type") == "json_invalid" for error in raw_errors)
        status = 400 if malformed else 422
        errors = None
        if not malformed:
            errors = []
            for error in raw_errors:
                location = list(error.get("loc", ()))
                if location and location[0] in {"body", "query", "path", "header"}:
                    location = location[1:]
                pointer = "/" + "/".join(
                    str(part).replace("~", "~0").replace("/", "~1") for part in location
                )
                errors.append({"pointer": pointer, "detail": str(error["msg"])})
        return _problem_response(
            request,
            status,
            "request body is not valid JSON"
            if malformed
            else "request validation failed",
            errors=errors,
        )

    @app.exception_handler(HttpError)
    async def http_error_handler(request: Request, exc: HttpError) -> Response:
        if request.url.path.startswith("/api/"):
            return _problem_response(request, exc.status, exc.message)
        return PlainTextResponse(
            f"{exc.status} {exc.message}\n",
            status_code=exc.status,
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> Response:
        detail = str(exc.detail)
        if request.url.path.startswith("/api/"):
            return _problem_response(request, exc.status_code, detail)
        return PlainTextResponse(
            f"{exc.status_code} {detail}\n",
            status_code=exc.status_code,
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.exception_handler(HarborWorkspaceError)
    async def harbor_error_handler(
        request: Request, exc: HarborWorkspaceError
    ) -> JSONResponse:
        return _problem_response(request, harbor_error_status(exc), str(exc))

    @app.exception_handler(CatalogBusyError)
    async def catalog_busy_handler(
        request: Request, exc: CatalogBusyError
    ) -> JSONResponse:
        return _problem_response(request, 409, str(exc))

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        detail = str(exc) if role_for(request) == ADMIN_ROLE else "request failed"
        return _problem_response(request, 500, detail)


def create_app(runtime: ServeRuntime, access_control: ServeAccess) -> FastAPI:
    app = FastAPI(
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        redirect_slashes=False,
        strict_content_type=True,
    )
    app.state.runtime = runtime
    app.state.access = access_control
    app.add_middleware(BodyLimitMiddleware)
    _install_error_handlers(app)
    _register_static_routes(app)
    _register_session_routes(app)
    _register_catalog_routes(app)
    _register_source_routes(app)
    _register_config_routes(app)
    _register_view_report_routes(app)
    _register_harbor_routes(app)
    _register_acp_routes(app)
    _verify_route_access(app)
    return app


def _register_static_routes(app: FastAPI) -> None:
    @app.get("/", response_class=HTMLResponse)
    @access(GUEST_ACCESS)
    def home(request: Request) -> HTMLResponse:
        return _serve_page(request, "home")

    @app.get("/datasets", response_class=HTMLResponse)
    @access(GUEST_ACCESS)
    def datasets_page(request: Request) -> HTMLResponse:
        return _serve_page(request, "datasets")

    @app.get("/reports", response_class=HTMLResponse)
    @access(GUEST_ACCESS)
    def reports_page(request: Request) -> HTMLResponse:
        return _serve_page(request, "reports")

    @app.get(
        "/config", response_class=HTMLResponse, dependencies=[Depends(require_admin)]
    )
    @access(ADMIN_ACCESS)
    def config_page(request: Request) -> HTMLResponse:
        return _serve_page(request, "config")

    @app.get(ECHARTS_ASSET_PATH)
    @access(GUEST_ACCESS)
    def echarts(request: Request) -> Response:
        runtime: ServeRuntime = request.app.state.runtime
        return Response(
            cached_echarts_asset(runtime.store),
            media_type="application/javascript; charset=utf-8",
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.get(WORKSPACE_STYLESHEET_PATH)
    @access(GUEST_ACCESS)
    def workspace_css(request: Request) -> Response:
        data, etag = workspace_stylesheet_asset()
        headers = {
            "Cache-Control": "no-cache",
            "ETag": etag,
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        }
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        return Response(data, media_type="text/css", headers=headers)

    @app.get(f"{PEVAL_WEB_ASSET_PREFIX}{{asset_path:path}}")
    @access(GUEST_ACCESS)
    def web_asset(request: Request, asset_path: str) -> Response:
        path = f"{PEVAL_WEB_ASSET_PREFIX}{asset_path}"
        data, etag = packaged_web_asset_with_etag(path)
        headers = {
            "Cache-Control": "no-cache",
            "ETag": etag,
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        }
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        return Response(
            data,
            media_type=(
                "application/json; charset=utf-8"
                if path.endswith(".js.map")
                else "application/javascript; charset=utf-8"
            ),
            headers=headers,
        )


def _serve_page(request: Request, page: str) -> HTMLResponse:
    runtime: ServeRuntime = request.app.state.runtime
    access_control: ServeAccess = request.app.state.access
    role = role_for(request)
    csp_nonce = secrets.token_urlsafe(24)
    return HTMLResponse(
        render_serve_html(
            locale=runtime.config.locale,
            adapter_defaults=(
                runtime.config.adapter_default_db_paths if role == ADMIN_ROLE else {}
            ),
            loading=not runtime.catalog.has_generation or runtime.is_loading(),
            load_error=(
                runtime.load_error()
                if role == ADMIN_ROLE
                else "workspace failed to load"
                if runtime.load_error()
                else None
            ),
            workspace_id=runtime.workspace_id,
            workspace_description=runtime.config.description,
            role=role,
            authentication_enabled=access_control.authentication_enabled,
            serve_page=page,
            csp_nonce=csp_nonce,
        ),
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": _workspace_csp(request, csp_nonce),
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        },
    )


_CSP_HOST = re.compile(
    r"(?:\[[0-9A-Fa-f:.]+\]|[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)(?::[0-9]{1,5})?"
)


def _workspace_csp(request: Request, nonce: str) -> str:
    host = request.headers.get("host", "")
    websocket_source = ""
    if _CSP_HOST.fullmatch(host):
        raw_port = host.rpartition(":")[2]
        if not raw_port.isdigit() or int(raw_port) <= 65535:
            scheme = "wss" if request.url.scheme == "https" else "ws"
            websocket_source = f" {scheme}://{host}"
    return "; ".join(
        [
            "default-src 'none'",
            f"script-src 'self' 'nonce-{nonce}'",
            f"style-src-elem 'self' 'nonce-{nonce}'",
            "style-src-attr 'unsafe-inline'",
            "img-src 'self' data: blob:",
            "media-src 'self' data: blob:",
            "font-src 'self'",
            f"connect-src 'self'{websocket_source}",
            "frame-src 'self'",
            "object-src 'none'",
            "base-uri 'none'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
    )


def _register_session_routes(app: FastAPI) -> None:
    @app.get("/api/session")
    @access(GUEST_ACCESS)
    def session(request: Request) -> JSONResponse:
        access_control: ServeAccess = request.app.state.access
        return _json(access_control.session_payload(request.headers.get("cookie")))

    @app.post("/api/session", dependencies=[Depends(mutation_guard)])
    @access(GUEST_ACCESS)
    def login(request: Request, body: LoginRequest) -> JSONResponse:
        access_control: ServeAccess = request.app.state.access
        client = request.client.host if request.client is not None else "unknown"
        try:
            token = access_control.login(body.password, client)
        except AuthenticationDisabled as exc:
            raise ProblemException(409, str(exc)) from exc
        except InvalidCredentials as exc:
            raise ProblemException(401, str(exc)) from exc
        except LoginRateLimited as exc:
            raise ProblemException(
                429,
                "too many failed login attempts",
                headers={"Retry-After": str(exc.retry_after)},
            ) from exc
        return _json(
            {"authentication_enabled": True, "role": ADMIN_ROLE},
            headers={"Set-Cookie": access_control.session_cookie(token)},
        )

    @app.delete("/api/session", dependencies=[Depends(mutation_guard)])
    @access(GUEST_ACCESS)
    def logout(request: Request) -> JSONResponse:
        access_control: ServeAccess = request.app.state.access
        token = access_control.logout(request.headers.get("cookie"))
        if token is not None:
            runtime: ServeRuntime = request.app.state.runtime
            runtime.acp.revoke_session(token)
        return _json(
            {
                "authentication_enabled": access_control.authentication_enabled,
                "role": (
                    GUEST_ROLE if access_control.authentication_enabled else ADMIN_ROLE
                ),
            },
            headers={"Set-Cookie": access_control.expired_session_cookie()},
        )


def _register_catalog_routes(app: FastAPI) -> None:
    @app.get("/api/catalog")
    @access(GUEST_ACCESS)
    def get_catalog(request: Request) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        try:
            page = runtime.catalog_page(
                catalog_query(request.url.query),
                view_names=catalog_view_names(request.url.query),
            )
        except WorkspaceViewNotFound as exc:
            raise ProblemException(400, str(exc)) from exc
        return _json(project_catalog_payload(page.to_dict(), role_for(request)))

    @app.post("/api/catalog-queries", dependencies=[Depends(mutation_guard)])
    @access(GUEST_ACCESS)
    def query_catalog(request: Request, body: CatalogQueryRequest) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        query, view_names, raw_browser_views = catalog_post_query_payload(
            body.payload()
        )
        try:
            browser_views = runtime.validated_browser_views(raw_browser_views)
            page = runtime.catalog_page(
                query, view_names=view_names, browser_views=browser_views
            )
            runtime.ensure_browser_view_names_available(browser_views)
        except WorkspaceViewConflict as exc:
            raise ProblemException(409, str(exc)) from exc
        except (WorkspaceViewNotFound, ValueError) as exc:
            raise ProblemException(400, str(exc)) from exc
        return _json(project_catalog_payload(page.to_dict(), role_for(request)))

    @app.post("/api/catalog-summaries", dependencies=[Depends(mutation_guard)])
    @access(GUEST_ACCESS)
    def summarize_catalog(
        request: Request, body: CatalogSummaryRequest
    ) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        summary_request = catalog_summary_payload(body.payload())
        try:
            browser_views = runtime.validated_browser_views(
                summary_request.browser_views
            )
            result = runtime.leaderboard_summary(
                summary_request.query,
                view_names=summary_request.views,
                browser_views=browser_views,
                group_by=summary_request.group_by,
            )
            runtime.ensure_browser_view_names_available(browser_views)
        except WorkspaceViewConflict as exc:
            raise ProblemException(409, str(exc)) from exc
        except CatalogSummaryCapacityError as exc:
            raise ProblemException(413, str(exc)) from exc
        except (WorkspaceViewNotFound, ValueError) as exc:
            raise ProblemException(400, str(exc)) from exc
        return _json(result)

    @app.post("/api/source-key-resolutions", dependencies=[Depends(mutation_guard)])
    @access(GUEST_ACCESS)
    def resolve_source_keys(request: Request, body: SourceKeysRequest) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        return _json(
            {
                "generation": runtime.catalog.generation,
                "source_keys": runtime.resolve_keys(body.source_keys),
            }
        )

    @app.post("/api/exports", dependencies=[Depends(mutation_guard)])
    @access(GUEST_ACCESS)
    def export_catalog(request: Request, body: ExportRequest) -> Response:
        runtime: ServeRuntime = request.app.state.runtime
        payload = body.payload()
        if body.kind.strip().lower() == "summary_xlsx":
            summary_request = summary_export_payload(body.summary)
            try:
                if summary_request.scope == "leaderboard":
                    assert summary_request.query is not None
                    browser_views = runtime.validated_browser_views(
                        summary_request.browser_views
                    )
                    sheets = [
                        runtime.leaderboard_summary_worksheet(
                            summary_request.query,
                            view_names=summary_request.query_views,
                            browser_views=browser_views,
                            group_by=summary_request.group_by,
                            statistic=summary_request.statistic,
                        )
                    ]
                else:
                    browser_views = runtime.validated_browser_views(
                        summary_request.browser_views
                    )
                    sheets = runtime.workspace_view_summary_worksheets(
                        summary_request.views, browser_views
                    )
                export = build_summary_serve_export(
                    sheets, runtime.config, scope=summary_request.scope
                )
                runtime.ensure_browser_view_names_available(browser_views)
            except WorkspaceViewConflict as exc:
                raise ProblemException(409, str(exc)) from exc
            except CatalogSummaryCapacityError as exc:
                raise ProblemException(413, str(exc)) from exc
            except ValueError as exc:
                raise ProblemException(400, str(exc)) from exc
        else:
            export_query = catalog_query_payload(body.query)
            view_names = catalog_view_names_payload(body.query)
            try:
                browser_views = runtime.validated_browser_views(
                    body.query.get("browser_views", []) if body.query else []
                )
                export = build_serve_export(
                    runtime.catalog,
                    runtime.store,
                    runtime.config,
                    kind=body.kind,
                    query=export_query,
                    view_queries=runtime.workspace_view_queries(
                        view_names, browser_views
                    ),
                    source_keys=source_keys_payload(payload),
                    audience=role_for(request),
                )
                runtime.ensure_browser_view_names_available(browser_views)
            except WorkspaceViewConflict as exc:
                raise ProblemException(409, str(exc)) from exc
            except ValueError as exc:
                raise ProblemException(400, str(exc)) from exc
        return Response(
            export.content,
            media_type=export.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{export.filename}"',
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            },
        )


def _register_source_routes(app: FastAPI) -> None:
    @app.get("/api/sources", dependencies=[Depends(require_admin)])
    @access(ADMIN_ACCESS)
    def sources(request: Request) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        return _json(runtime.source_envelope())

    @app.get("/api/sources/{source_key:path}")
    @access(GUEST_ACCESS)
    def source_detail(request: Request, source_key: str) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        try:
            detail = runtime.detail(source_key).to_dict()
        except ValueError as exc:
            raise ProblemException(404, str(exc)) from exc
        return _json(project_detail_payload(detail, role_for(request)))

    @app.patch(
        "/api/sources/{source_key:path}",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def patch_source(
        request: Request, source_key: str, body: SourcePatchRequest
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        try:
            row = runtime.catalog.row_for_key(source_key)
        except ValueError as exc:
            raise ProblemException(404, str(exc)) from exc

        try:
            if body.notes is not None:
                runtime.store.validate_source_notes_row(row, body.notes, runtime.config)
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc

        def mutate() -> None:
            if "alias" in body.model_fields_set:
                alias = body.alias.strip() if body.alias else None
                runtime.store.set_source_alias_row(row, alias or None)
            if "category" in body.model_fields_set:
                category = body.category.strip() if body.category else None
                runtime.store.set_source_category_row(row, category or None)
            if body.tags is not None:
                runtime.store.set_source_tags_row(row, list(dict.fromkeys(body.tags)))
            if body.notes is not None:
                runtime.store.save_source_notes_row(row, body.notes, runtime.config)
            if body.active is not None:
                runtime.store.set_source_active_row(row, body.active)

        try:
            runtime.mutate("source-update", [source_key], mutate)
            detail = runtime.detail(source_key).to_dict()
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc
        return _json(project_detail_payload(detail, ADMIN_ROLE))

    @app.post(
        "/api/source-import-operations",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def import_sources(request: Request, body: SourceImportRequest) -> JSONResponse:
        runtime = writable_runtime(request)
        payloads = [body.payload()]
        raw_path = body.path
        if raw_path is not None:
            lines = [line.strip() for line in raw_path.splitlines() if line.strip()]
            if len(lines) > 1:
                payloads = [{**body.payload(), "path": line} for line in lines]
        if body.session_ids and len(body.session_ids) > 1:
            payloads = [
                {
                    **body.payload(),
                    "session_ids": None,
                    "session_id": session_id,
                }
                for session_id in body.session_ids
            ]
        operation = runtime.start_operation(
            "source-import",
            payloads,
            lambda item: add_source_result_payload(
                add_source_payload(runtime.store, runtime.config, item)
            ),
        )
        return _operation_response(operation)

    @app.post(
        "/api/source-discovery-operations",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def discover_sources(request: Request) -> JSONResponse:
        runtime = writable_runtime(request)
        operation = runtime.start_operation(
            "source-discovery",
            [None],
            lambda _item: {
                "source_keys": runtime.store.harbor_source_keys(runtime.config)
            },
        )
        return _operation_response(operation)

    @app.post(
        "/api/source-state-operations",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def set_source_state(
        request: Request, body: SourceStateOperationRequest
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        rows = _source_rows(runtime, body.source_keys)
        operation = runtime.start_operation(
            "activate" if body.active else "archive",
            rows,
            lambda row: source_state_operation(runtime.store, row, body.active),
        )
        return _operation_response(operation)

    @app.post(
        "/api/source-refresh-operations",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def refresh_sources(request: Request, body: SourceKeysRequest) -> JSONResponse:
        runtime = writable_runtime(request)
        rows = _source_rows(runtime, body.source_keys)
        operation = runtime.start_operation(
            "source-refresh",
            rows,
            lambda row: refresh_source_operation(runtime.store, runtime.config, row),
        )
        return _operation_response(operation)

    @app.post(
        "/api/source-deletion-operations",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def delete_sources(request: Request, body: SourceKeysRequest) -> JSONResponse:
        runtime = writable_runtime(request)
        rows = _source_rows(runtime, body.source_keys)
        reject_linked_harbor_delete(rows)
        operation = runtime.start_operation(
            "source-delete",
            rows,
            lambda row: delete_source_operation(runtime.store, row),
        )
        return _operation_response(operation)

    @app.get("/api/operations/{operation_id}", dependencies=[Depends(require_admin)])
    @access(ADMIN_ACCESS)
    def operation(request: Request, operation_id: str) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        try:
            status = runtime.operation(operation_id)
        except ValueError as exc:
            raise ProblemException(404, str(exc)) from exc
        headers = {"Retry-After": "1"} if status.state in {"queued", "running"} else {}
        return _json(_operation_payload(status), headers=headers)

    @app.post(
        "/api/database-inspections",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def inspect_database(
        request: Request, body: DatabaseInspectionRequest
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        try:
            return _json(db_sessions_payload(runtime.store, body.payload()))
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc

    @app.post(
        "/api/path-selections",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def select_paths(body: PathSelectionRequest) -> JSONResponse:
        try:
            return _json({"paths": pick_file_paths(multiple=body.multiple)})
        except PathPickerUnavailable as exc:
            raise ProblemException(503, str(exc)) from exc


def _register_config_routes(app: FastAPI) -> None:
    @app.get("/api/config", dependencies=[Depends(require_admin)])
    @access(ADMIN_ACCESS)
    def get_config(request: Request) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        return _config_response(runtime)

    @app.patch(
        "/api/config",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def patch_config(
        request: Request,
        body: ConfigPatchRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        current_revision = config_revision(runtime.store.paths.config_path)
        expected = _expect_revision(if_match, current_revision)
        with workspace_write(runtime):
            _patch_workspace_config(runtime, body, expected)
            runtime.set_config(load_config(workspace_root=runtime.store.paths.root))
        return _config_response(runtime)

    @app.get("/api/prompts", dependencies=[Depends(require_admin)])
    @access(ADMIN_ACCESS)
    def prompts(request: Request) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        try:
            return _json(runtime.prompt_assets.catalog()["prompts"])
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc

    @app.get("/api/prompts/{prompt_id}", dependencies=[Depends(require_admin)])
    @access(ADMIN_ACCESS)
    def get_prompt(request: Request, prompt_id: str) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        try:
            prompt = runtime.prompt_assets.read(prompt_id)
        except ValueError as exc:
            raise ProblemException(404, str(exc)) from exc
        return _json(prompt.to_dict(), headers={"ETag": _etag(prompt.revision)})

    @app.put(
        "/api/prompts/{prompt_id}",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def put_prompt(
        request: Request,
        prompt_id: str,
        body: PromptPutRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        try:
            current = runtime.prompt_assets.read(prompt_id)
        except ValueError as exc:
            raise ProblemException(404, str(exc)) from exc
        expected = _expect_revision(if_match, current.revision)
        with workspace_write(runtime):
            try:
                prompt = runtime.prompt_assets.save(
                    prompt_id, body.content, expected_revision=expected
                )
            except PromptAssetConflict as exc:
                current = runtime.prompt_assets.read(prompt_id)
                raise ProblemException(
                    412, str(exc), headers={"ETag": _etag(current.revision)}
                ) from exc
            except ValueError as exc:
                raise ProblemException(400, str(exc)) from exc
        return _json(prompt.to_dict(), headers={"ETag": _etag(prompt.revision)})

    @app.delete(
        "/api/prompts/{prompt_id}/override",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def reset_prompt(
        request: Request,
        prompt_id: str,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        try:
            current = runtime.prompt_assets.read(prompt_id)
        except ValueError as exc:
            raise ProblemException(404, str(exc)) from exc
        expected = _expect_revision(if_match, current.revision)
        with workspace_write(runtime):
            try:
                prompt = runtime.prompt_assets.reset(
                    prompt_id, expected_revision=expected
                )
            except PromptAssetConflict as exc:
                current = runtime.prompt_assets.read(prompt_id)
                raise ProblemException(
                    412, str(exc), headers={"ETag": _etag(current.revision)}
                ) from exc
            except ValueError as exc:
                raise ProblemException(400, str(exc)) from exc
        return _json(prompt.to_dict(), headers={"ETag": _etag(prompt.revision)})


def _register_view_report_routes(app: FastAPI) -> None:
    @app.get("/api/views")
    @access(GUEST_ACCESS)
    def views(request: Request) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        return _json(runtime.workspace_view_catalog())

    @app.put(
        "/api/views/{name}",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def put_view(request: Request, name: str, body: ViewPutRequest) -> JSONResponse:
        runtime = writable_runtime(request)
        existing = {item["name"] for item in runtime.workspace_view_catalog()}
        try:
            with workspace_write(runtime):
                view = runtime.workspace_views.save(
                    name=name,
                    filters=body.filters,
                    group_by=body.group_by,
                    notes=body.notes,
                    overwrite=body.overwrite,
                )
        except WorkspaceViewConflict as exc:
            raise ProblemException(409, str(exc)) from exc
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc
        return _json(
            view.to_dict(),
            status=200 if name in existing else 201,
            headers={"Location": f"/api/views/{quote(view.name)}"},
        )

    @app.patch(
        "/api/views/{name}",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def patch_view(request: Request, name: str, body: ViewPatchRequest) -> JSONResponse:
        runtime = writable_runtime(request)
        try:
            with workspace_write(runtime):
                view = runtime.workspace_views.update(
                    name=name, field=body.field, value=body.value
                )
        except WorkspaceViewConflict as exc:
            raise ProblemException(409, str(exc)) from exc
        except WorkspaceViewNotFound as exc:
            raise ProblemException(404, str(exc)) from exc
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc
        return _json(view.to_dict())

    @app.delete(
        "/api/views/{name}",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
        status_code=204,
    )
    @access(ADMIN_ACCESS)
    def delete_view(request: Request, name: str) -> Response:
        runtime = writable_runtime(request)
        try:
            with workspace_write(runtime):
                runtime.workspace_views.delete([name])
        except WorkspaceViewNotFound as exc:
            raise ProblemException(404, str(exc)) from exc
        return Response(status_code=204)

    @app.post(
        "/api/view-deletion-operations",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def delete_views(request: Request, body: ViewDeletionRequest) -> JSONResponse:
        runtime = writable_runtime(request)
        operation = runtime.start_operation(
            "view-delete",
            [body.names],
            lambda names: {
                "names": runtime.workspace_views.delete(names),
            },
        )
        return _operation_response(operation)

    @app.get("/api/view-summaries")
    @access(GUEST_ACCESS)
    def view_summaries(request: Request) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        try:
            return _json(runtime.workspace_view_summaries())
        except CatalogSummaryCapacityError as exc:
            raise ProblemException(413, str(exc)) from exc

    @app.post("/api/view-summaries", dependencies=[Depends(mutation_guard)])
    @access(GUEST_ACCESS)
    def browser_view_summaries(
        request: Request, body: BrowserViewsRequest
    ) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        try:
            views = runtime.validated_browser_views(body.browser_views)
            result = runtime.browser_view_summaries(views)
            runtime.ensure_browser_view_names_available(views)
        except WorkspaceViewConflict as exc:
            raise ProblemException(409, str(exc)) from exc
        except CatalogSummaryCapacityError as exc:
            raise ProblemException(413, str(exc)) from exc
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc
        return _json(result)

    @app.get("/api/reports")
    @access(GUEST_ACCESS)
    def reports(request: Request) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        return _json(runtime.workspace_report_catalog())

    @app.get("/api/evaluation-reports")
    @access(GUEST_ACCESS)
    def evaluation_reports(request: Request) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        page, page_size, search = evaluation_report_query(request.url.query)
        return _json(
            runtime.evaluation_report_catalog(
                page=page,
                page_size=page_size,
                search=search,
            )
        )

    @app.post(
        "/api/reports",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def import_report(request: Request, body: ReportImportRequest) -> JSONResponse:
        runtime = writable_runtime(request)
        try:
            with workspace_write(runtime):
                report_id = runtime.workspace_reports.import_file(
                    body.path, body.source_keys
                )
                report = next(
                    item
                    for item in runtime.workspace_report_catalog()
                    if item["report_id"] == report_id
                )
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc
        return _json(
            report,
            status=201,
            headers={"Location": f"/api/reports/{quote(report_id)}"},
        )

    @app.put(
        "/api/reports/{report_id}/bindings",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def replace_report_bindings(
        request: Request, report_id: str, body: ReportBindingsRequest
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        try:
            with workspace_write(runtime):
                runtime.workspace_reports.replace_bindings(report_id, body.source_keys)
                report = next(
                    item
                    for item in runtime.workspace_report_catalog()
                    if item["report_id"] == report_id
                )
        except WorkspaceReportNotFound as exc:
            raise ProblemException(404, str(exc)) from exc
        except ValueError as exc:
            raise ProblemException(400, str(exc)) from exc
        return _json(report)

    @app.delete(
        "/api/reports/{report_id}",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
        status_code=204,
    )
    @access(ADMIN_ACCESS)
    def delete_report(request: Request, report_id: str) -> Response:
        runtime = writable_runtime(request)
        try:
            with workspace_write(runtime):
                runtime.workspace_reports.delete(report_id)
        except WorkspaceReportNotFound as exc:
            raise ProblemException(404, str(exc)) from exc
        return Response(status_code=204)

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


def _register_harbor_routes(app: FastAPI) -> None:
    @app.get("/api/harbor/datasets")
    @access(GUEST_ACCESS)
    def harbor_datasets(request: Request) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        payload = harbor_workspace(runtime.store, runtime).inventory()
        return _harbor_inventory_response(runtime, payload, role_for(request))

    @app.post(
        "/api/harbor/datasets",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def create_harbor_dataset(
        request: Request,
        body: DatasetCreateRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        revision = config_revision(runtime.store.paths.config_path)
        expected = _expect_revision(if_match, revision)
        if body.source == "new" and (not body.id or not body.package_name):
            raise ProblemException(422, "new Dataset requires id and package_name")
        payload = {
            "action": "create" if body.source == "new" else "register",
            "dataset_id": body.id,
            "path": body.path,
            "package_name": body.package_name,
            "description": body.description,
            "expected_revision": expected,
        }
        result = runtime.mutate_with_background_reconcile(
            "harbor-dataset-config",
            lambda: mutate_harbor_dataset(
                runtime.store, runtime, payload["action"], payload
            ),
        )
        operation_id = result["operation"]["operation_id"]
        return _config_operation_response(runtime, runtime.operation(operation_id))

    @app.patch(
        "/api/harbor/datasets/{dataset_id}",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def patch_harbor_dataset(
        request: Request,
        dataset_id: str,
        body: DatasetPatchRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        expected = _expect_revision(
            if_match, config_revision(runtime.store.paths.config_path)
        )
        payload = {
            "dataset_id": dataset_id,
            "new_id": body.new_id,
            "path": body.path,
            "mount_ids": body.mount_ids,
            "expected_revision": expected,
        }
        result = runtime.mutate_with_background_reconcile(
            "harbor-dataset-config",
            lambda: mutate_harbor_dataset(runtime.store, runtime, "update", payload),
        )
        return _config_operation_response(
            runtime, runtime.operation(result["operation"]["operation_id"])
        )

    @app.post(
        "/api/harbor/dataset-unregistration-operations",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def unregister_harbor_datasets(
        request: Request,
        body: DatasetUnregisterRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        expected = _expect_revision(
            if_match, config_revision(runtime.store.paths.config_path)
        )
        payload = {
            "dataset_ids": body.dataset_ids,
            "expected_revision": expected,
        }
        result = runtime.mutate_with_background_reconcile(
            "harbor-dataset-unregister",
            lambda: mutate_harbor_dataset(
                runtime.store, runtime, "unregister", payload
            ),
        )
        return _config_operation_response(
            runtime, runtime.operation(result["operation"]["operation_id"])
        )

    @app.get("/api/harbor/datasets/{dataset_id}/tasks")
    @access(GUEST_ACCESS)
    def harbor_tasks(request: Request, dataset_id: str) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        payload = harbor_workspace(runtime.store, runtime).task_inventory(dataset_id)
        return _harbor_inventory_response(runtime, payload, role_for(request))

    @app.post(
        "/api/harbor/datasets/{dataset_id}/tasks",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def create_harbor_task(
        request: Request,
        dataset_id: str,
        body: TaskCreateRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        expected = _if_match_value(if_match)
        payload = {
            "action": "create",
            "dataset_id": dataset_id,
            "directory": body.directory,
            "package_name": body.package_name,
            "steps": body.steps,
            "expected_revision": expected,
        }
        result = runtime.mutate_with_background_reconcile(
            "harbor-task-reconcile",
            lambda: mutate_harbor_task(
                harbor_workspace(runtime.store, runtime), payload
            ),
        )
        return _operation_response(
            runtime.operation(result["operation"]["operation_id"])
        )

    @app.get("/api/harbor/datasets/{dataset_id}/tasks/{task}")
    @access(GUEST_ACCESS)
    def harbor_task(request: Request, dataset_id: str, task: str) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        payload = harbor_workspace(runtime.store, runtime).task_detail(dataset_id, task)
        projected = project_harbor_task(payload, role_for(request))
        revision = str(payload["task"]["revision"])
        return _json(projected, headers={"ETag": _etag(revision)})

    @app.patch(
        "/api/harbor/datasets/{dataset_id}/tasks/{task}",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def rename_harbor_task(
        request: Request,
        dataset_id: str,
        task: str,
        body: TaskPatchRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        payload = {
            "action": "rename",
            "dataset_id": dataset_id,
            "task": task,
            "new_directory": body.new_directory,
            "expected_revision": _if_match_value(if_match),
        }
        result = runtime.mutate_with_background_reconcile(
            "harbor-task-reconcile",
            lambda: mutate_harbor_task(
                harbor_workspace(runtime.store, runtime), payload
            ),
        )
        return _operation_response(
            runtime.operation(result["operation"]["operation_id"])
        )

    @app.patch(
        "/api/harbor/datasets/{dataset_id}/archived-tasks/{entry_id}",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def rename_archived_harbor_task(
        request: Request,
        dataset_id: str,
        entry_id: str,
        body: TaskPatchRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        payload = {
            "action": "rename_archived",
            "dataset_id": dataset_id,
            "entry_id": entry_id,
            "new_directory": body.new_directory,
            "expected_revision": _if_match_value(if_match),
        }
        result = runtime.mutate_with_background_reconcile(
            "harbor-task-reconcile",
            lambda: mutate_harbor_task(
                harbor_workspace(runtime.store, runtime), payload
            ),
        )
        return _operation_response(
            runtime.operation(result["operation"]["operation_id"])
        )

    @app.put(
        "/api/harbor/datasets/{dataset_id}/manifest",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def sync_harbor_manifest(
        request: Request,
        dataset_id: str,
        body: ManifestPutRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        del body
        runtime = writable_runtime(request)
        with workspace_write(runtime):
            result = harbor_workspace(runtime.store, runtime).sync_manifest(
                dataset_id=dataset_id, expected_revision=_if_match_value(if_match)
            )
        return _json(result, headers={"ETag": _etag(str(result["revision"]))})

    @app.post(
        "/api/harbor/task-state-operations",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def harbor_task_state(
        request: Request, body: TaskStateOperationRequest
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        items = [
            {
                **item.model_dump(exclude_none=True, exclude={"etag"}),
                "expected_revision": _if_match_value(item.etag),
            }
            for item in body.items
        ]
        operation = runtime.start_operation(
            "harbor-task-archive" if body.archived else "harbor-task-restore",
            items,
            lambda item: mutate_harbor_task_state(
                harbor_workspace(runtime.store, runtime),
                item,
                archived=body.archived,
            ),
        )
        return _operation_response(operation)

    @app.post(
        "/api/harbor/task-deletion-operations",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def harbor_task_deletion(
        request: Request, body: TaskDeletionRequest
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        items = [
            {
                **item.model_dump(exclude_none=True, exclude={"etag"}),
                "expected_revision": _if_match_value(item.etag),
            }
            for item in body.items
        ]
        operation = runtime.start_operation(
            "harbor-task-delete",
            items,
            lambda item: delete_harbor_task(
                harbor_workspace(runtime.store, runtime), item
            ),
        )
        return _operation_response(operation)

    _register_harbor_file_routes(app)
    _register_harbor_mount_routes(app)


def _register_harbor_file_routes(app: FastAPI) -> None:
    base = "/api/harbor/datasets/{dataset_id}/tasks/{task}/files/{file_path:path}"

    @app.get(base)
    @access(GUEST_ACCESS)
    def read_harbor_file(
        request: Request,
        dataset_id: str,
        task: str,
        file_path: str,
        download: str | None = None,
    ) -> JSONResponse:
        if download is not None:
            raise ProblemException(400, "Task file downloads are not supported")
        runtime: ServeRuntime = request.app.state.runtime
        payload = harbor_workspace(runtime.store, runtime).read_file(
            dataset_id, task, file_path
        )
        projected = project_harbor_text_file(payload, role_for(request))
        return _json(projected, headers={"ETag": _etag(str(payload["revision"]))})

    @app.put(base, dependencies=[Depends(require_admin), Depends(mutation_guard)])
    @access(ADMIN_ACCESS)
    def save_harbor_file(
        request: Request,
        dataset_id: str,
        task: str,
        file_path: str,
        body: FilePutRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        library = harbor_workspace(runtime.store, runtime)
        current = library.read_file(dataset_id, task, file_path)
        _expect_revision(if_match, str(current["revision"]))
        result = runtime.mutate_with_background_reconcile(
            "harbor-task-file",
            lambda: library.mutate_file(
                "save",
                {
                    "dataset_id": dataset_id,
                    "task": task,
                    "path": file_path,
                    "content": body.content,
                    "expected_revision": current["task_revision"],
                },
            ),
        )
        return _operation_response(
            runtime.operation(result["operation"]["operation_id"])
        )

    @app.patch(base, dependencies=[Depends(require_admin), Depends(mutation_guard)])
    @access(ADMIN_ACCESS)
    def rename_harbor_file(
        request: Request,
        dataset_id: str,
        task: str,
        file_path: str,
        body: FilePatchRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        result = runtime.mutate_with_background_reconcile(
            "harbor-task-file",
            lambda: harbor_workspace(runtime.store, runtime).mutate_file(
                "rename",
                {
                    "dataset_id": dataset_id,
                    "task": task,
                    "path": file_path,
                    "new_path": body.new_path,
                    "expected_revision": _if_match_value(if_match),
                },
            ),
        )
        return _operation_response(
            runtime.operation(result["operation"]["operation_id"])
        )

    @app.delete(base, dependencies=[Depends(require_admin), Depends(mutation_guard)])
    @access(ADMIN_ACCESS)
    def delete_harbor_file(
        request: Request,
        dataset_id: str,
        task: str,
        file_path: str,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        result = runtime.mutate_with_background_reconcile(
            "harbor-task-file",
            lambda: harbor_workspace(runtime.store, runtime).mutate_file(
                "delete",
                {
                    "dataset_id": dataset_id,
                    "task": task,
                    "path": file_path,
                    "expected_revision": _if_match_value(if_match),
                },
            ),
        )
        return _operation_response(
            runtime.operation(result["operation"]["operation_id"])
        )

    @app.post(
        "/api/harbor/datasets/{dataset_id}/tasks/{task}/files",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def create_harbor_file(
        request: Request,
        dataset_id: str,
        task: str,
        body: FileCreateRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        payload = {
            "dataset_id": dataset_id,
            "task": task,
            "path": body.path,
            "expected_revision": _if_match_value(if_match),
        }
        if body.kind == "upload":
            payload["content_base64"] = body.content
            action = "upload"
        else:
            payload["kind"] = body.kind
            action = "create"
        result = runtime.mutate_with_background_reconcile(
            "harbor-task-file",
            lambda: harbor_workspace(runtime.store, runtime).mutate_file(
                action, payload
            ),
        )
        return _operation_response(
            runtime.operation(result["operation"]["operation_id"])
        )


def _register_harbor_mount_routes(app: FastAPI) -> None:
    @app.get("/api/harbor/mounts", dependencies=[Depends(require_admin)])
    @access(ADMIN_ACCESS)
    def harbor_mounts(request: Request) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        payload = harbor_config_payload(runtime.store, runtime)
        revision = str(payload.pop("revision"))
        return _json(payload["mounts"], headers={"ETag": _etag(revision)})

    @app.post(
        "/api/harbor/mounts",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def create_harbor_mount(
        request: Request,
        body: MountCreateRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        expected = _expect_revision(
            if_match, config_revision(runtime.store.paths.config_path)
        )
        payload = {
            "action": "upsert",
            "jobs_path": body.path,
            "expected_revision": expected,
        }
        result = runtime.mutate_with_background_reconcile(
            "harbor-mount-config",
            lambda: update_harbor_mount_config(runtime.store, runtime, payload),
        )
        return _config_operation_response(
            runtime, runtime.operation(result["operation"]["operation_id"])
        )

    @app.patch(
        "/api/harbor/mounts/{mount_id}",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def patch_harbor_mount(
        request: Request,
        mount_id: str,
        body: MountPatchRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        expected = _expect_revision(
            if_match, config_revision(runtime.store.paths.config_path)
        )
        payload = {
            "action": "upsert",
            "original_id": mount_id,
            "mount_id": body.new_id,
            "jobs_path": body.path,
            "dataset_ids": body.dataset_ids,
            "expected_revision": expected,
        }
        result = runtime.mutate_with_background_reconcile(
            "harbor-mount-config",
            lambda: update_harbor_mount_config(runtime.store, runtime, payload),
        )
        return _config_operation_response(
            runtime, runtime.operation(result["operation"]["operation_id"])
        )

    @app.post(
        "/api/harbor/mount-deletion-operations",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def delete_harbor_mounts(
        request: Request,
        body: MountDeletionRequest,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> JSONResponse:
        runtime = writable_runtime(request)
        expected = _expect_revision(
            if_match, config_revision(runtime.store.paths.config_path)
        )
        payload = {
            "action": "delete",
            "mount_ids": body.mount_ids,
            "expected_revision": expected,
        }
        result = runtime.mutate_with_background_reconcile(
            "harbor-mount-delete",
            lambda: update_harbor_mount_config(runtime.store, runtime, payload),
        )
        return _config_operation_response(
            runtime, runtime.operation(result["operation"]["operation_id"])
        )


def _register_acp_routes(app: FastAPI) -> None:
    admin_get = [Depends(require_admin)]
    admin_mutation = [Depends(require_admin), Depends(mutation_guard)]

    @app.get("/api/acp/agents", dependencies=admin_get)
    @access(ADMIN_ACCESS)
    def acp_agents(request: Request) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        return _json(runtime.acp.agents())

    @app.websocket(
        "/api/acp/agents/{agent_id}/ws",
        dependencies=[
            Depends(require_admin_websocket),
            Depends(require_same_origin_websocket),
        ],
    )
    @access(ADMIN_ACCESS)
    async def acp_websocket(websocket: WebSocket, agent_id: str) -> None:
        runtime: ServeRuntime = websocket.app.state.runtime
        access_control: ServeAccess = websocket.app.state.access
        session_token = access_control.active_session_token(
            websocket.headers.get("cookie")
        )
        if access_control.authentication_enabled and session_token is None:
            raise WebSocketException(code=1008, reason="administrator access required")
        try:
            runtime.acp.configuration(agent_id)
        except KeyError as exc:
            raise WebSocketException(code=1008, reason="unknown ACP agent") from exc
        await runtime.acp.serve(websocket, agent_id, session_token)

    @app.post("/api/acp/context-resolutions", dependencies=admin_mutation)
    @access(ADMIN_ACCESS)
    def resolve_acp_context(request: Request, body: AcpContextRequest) -> JSONResponse:
        runtime: ServeRuntime = request.app.state.runtime
        items = acp_context_items(
            runtime.store,
            runtime,
            body.contexts,
            embedded_context=body.embedded_context,
        )
        return _json({"items": items})
