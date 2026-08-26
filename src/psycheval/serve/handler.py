from __future__ import annotations

import json
from dataclasses import replace
from functools import partial
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from psycheval.config import (
    AcpAgent,
    HarborMount,
    ToolConfig,
    apply_toml_config,
    unique_harbor_id_from_path,
    validate_harbor_mount_paths,
    write_workspace_acp_agents,
    write_workspace_adapter_default_db,
    write_workspace_harbor_mounts,
    write_workspace_locale,
)
from psycheval.html import render_serve_html
from psycheval.i18n import normalize_locale
from psycheval.serve.access import (
    ADMIN_ROLE,
    GUEST_ROLE,
    AuthenticationDisabled,
    InvalidCredentials,
    LoginRateLimited,
    ServeAccess,
)
from psycheval.serve.acp import AcpError
from psycheval.serve.assets import (
    ECHARTS_ASSET_PATH,
    PEVAL_WEB_ASSET_PREFIX,
    WORKSPACE_STYLESHEET_PATH,
    cached_echarts_asset,
    packaged_web_asset,
    workspace_stylesheet_asset,
)
from psycheval.serve.constants import MAX_JSON_BODY_BYTES
from psycheval.serve.errors import HttpError
from psycheval.serve.exports import (
    build_serve_export,
    build_summary_serve_export,
)
from psycheval.serve.harbor_workspace import (
    HarborConflictError,
    HarborNotFoundError,
    HarborSizeError,
    HarborWorkspace,
    HarborWorkspaceError,
    config_revision,
)
from psycheval.serve.path_picker import PathPickerUnavailable, pick_file_paths
from psycheval.serve.payloads import (
    adapter_default_db_payload,
    alias_payload,
    catalog_post_query_payload,
    catalog_summary_payload,
    category_payload,
    markdown_payload,
    required_bool,
    required_string,
    source_action_path,
    source_keys_payload,
    summary_export_payload,
    tags_payload,
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
from psycheval.state import (
    CatalogBusyError,
    CatalogQuery,
    CatalogSummaryCapacityError,
    ServeStateStore,
)
from psycheval.state.workspace_sources import WorkspaceSources, is_harbor_source
from psycheval.workspace_reports import (
    WorkspaceReportNotFound,
    render_workspace_report_preview,
    render_workspace_report_reader_page,
)
from psycheval.workspace_views import WorkspaceViewConflict, WorkspaceViewNotFound

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


def make_handler(
    store_or_runtime: ServeStateStore | ServeRuntime,
    config: ToolConfig | None = None,
    *,
    access: ServeAccess | None = None,
) -> type[BaseHTTPRequestHandler]:
    if isinstance(store_or_runtime, ServeRuntime):
        runtime = store_or_runtime
        store = runtime.store
    else:
        if config is None:
            raise ValueError("config is required when make_handler receives a store")
        store = store_or_runtime
        runtime = ServeRuntime(store, config)
    access_control = access or ServeAccess(None)

    class ServeHandler(BaseHTTPRequestHandler):
        server_version = "peval-serve/1"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def do_GET(self) -> None:  # noqa: N802
            parsed_url = urlsplit(self.path)
            path = parsed_url.path
            self.begin_request(path)
            try:
                self.require_route_access("GET", path)
                if path == "/api/auth/session":
                    self.write_json(
                        access_control.session_payload(self.headers.get("Cookie"))
                    )
                    return
                serve_page = {
                    "/": "home",
                    "/datasets": "datasets",
                    "/reports": "reports",
                    "/config": "config",
                }.get(path)
                if serve_page is not None:
                    self.write_html(
                        render_serve_html(
                            locale=runtime.config.locale,
                            adapter_defaults=(
                                runtime.config.adapter_default_db_paths
                                if self._serve_role == ADMIN_ROLE
                                else {}
                            ),
                            loading=not runtime.catalog.has_generation
                            or runtime.is_loading(),
                            load_error=(
                                runtime.load_error()
                                if self._serve_role == ADMIN_ROLE
                                else (
                                    "workspace failed to load"
                                    if runtime.load_error()
                                    else None
                                )
                            ),
                            workspace_id=runtime.workspace_id,
                            workspace_description=runtime.config.description,
                            role=self._serve_role,
                            authentication_enabled=access_control.authentication_enabled,
                            serve_page=serve_page,
                        )
                    )
                    return
                if path == ECHARTS_ASSET_PATH:
                    self.write_js(cached_echarts_asset(store))
                    return
                if path == WORKSPACE_STYLESHEET_PATH:
                    data, etag = workspace_stylesheet_asset()
                    self.write_workspace_css(data, etag)
                    return
                if path.startswith(PEVAL_WEB_ASSET_PREFIX):
                    self.write_js(packaged_web_asset(path), cache_control="no-store")
                    return
                if path == "/api/acp/agents":
                    self.write_json(runtime.acp.agents())
                    return
                if path == "/api/acp/sessions":
                    agent_id = required_query_value(parsed_url.query, "agent_id")
                    self.write_json(
                        runtime.acp.sessions(
                            agent_id,
                            refresh=single_query_value(parsed_url.query, "refresh")
                            == "1",
                        )
                    )
                    return
                if path == "/api/acp/events":
                    try:
                        after = int(
                            single_query_value(parsed_url.query, "after") or "0"
                        )
                        wait = float(
                            single_query_value(parsed_url.query, "wait") or "20"
                        )
                    except ValueError as exc:
                        raise HttpError(400, "after and wait must be numbers") from exc
                    if after < 0:
                        raise HttpError(400, "after must not be negative")
                    self.write_json(
                        runtime.acp.events(
                            required_query_value(parsed_url.query, "agent_id"),
                            required_query_value(parsed_url.query, "session_id"),
                            after=after,
                            wait=wait,
                        )
                    )
                    return
                if path == "/api/catalog":
                    try:
                        page = runtime.catalog_page(
                            catalog_query(parsed_url.query),
                            view_names=catalog_view_names(parsed_url.query),
                        )
                    except WorkspaceViewNotFound as exc:
                        raise HttpError(400, str(exc)) from exc
                    self.write_json(
                        project_catalog_payload(page.to_dict(), self._serve_role)
                    )
                    return
                if path == "/api/report":
                    source_key = single_query_value(parsed_url.query, "source_key")
                    if not source_key:
                        raise HttpError(400, "source_key is required")
                    try:
                        self.write_json(
                            project_detail_payload(
                                runtime.detail(source_key).to_dict(),
                                self._serve_role,
                            )
                        )
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    return
                if path == "/api/sources":
                    self.write_json(runtime.source_envelope())
                    return
                if path == "/api/config":
                    self.write_json(workspace_config_payload(store, runtime))
                    return
                if path == "/api/config/harbor":
                    self.write_json(harbor_config_payload(store, runtime))
                    return
                if path == "/api/prompts":
                    try:
                        self.write_json(runtime.prompt_assets.catalog())
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    return
                if path == "/api/harbor/datasets":
                    self.write_json(
                        project_harbor_inventory(
                            harbor_workspace(store, runtime).inventory(),
                            self._serve_role,
                        )
                    )
                    return
                if path == "/api/harbor/tasks":
                    self.write_json(
                        project_harbor_inventory(
                            harbor_workspace(store, runtime).task_inventory(
                                single_query_value(parsed_url.query, "dataset_id")
                            ),
                            self._serve_role,
                        )
                    )
                    return
                if path == "/api/harbor/task":
                    self.write_json(
                        project_harbor_task(
                            harbor_workspace(store, runtime).task_detail(
                                required_query_value(parsed_url.query, "dataset_id"),
                                required_query_value(parsed_url.query, "task"),
                            ),
                            self._serve_role,
                        )
                    )
                    return
                if path == "/api/harbor/files":
                    if "download" in parse_qs(parsed_url.query, keep_blank_values=True):
                        raise HttpError(400, "Task file downloads are not supported")
                    file_payload = harbor_workspace(store, runtime).read_file(
                        required_query_value(parsed_url.query, "dataset_id"),
                        required_query_value(parsed_url.query, "task"),
                        required_query_value(parsed_url.query, "path"),
                    )
                    self.write_json(
                        project_harbor_text_file(
                            file_payload,
                            self._serve_role,
                        )
                    )
                    return
                if path == "/api/reports":
                    self.write_json({"reports": runtime.workspace_report_catalog()})
                    return
                if path == "/api/views":
                    self.write_json({"views": runtime.workspace_view_catalog()})
                    return
                if path == "/api/views/summary":
                    try:
                        self.write_json(runtime.workspace_view_summaries())
                    except CatalogSummaryCapacityError as exc:
                        raise HttpError(413, str(exc)) from exc
                    return
                operation_id = operation_status_path(path)
                if operation_id is not None:
                    try:
                        self.write_json(runtime.operation(operation_id).to_dict())
                    except ValueError as exc:
                        raise HttpError(404, str(exc)) from exc
                    return
                report_action = report_action_path(path)
                if report_action is not None:
                    report_id, action = report_action
                    if action not in {"preview", "open"}:
                        raise HttpError(404, "unknown report action")
                    try:
                        report = runtime.workspace_reports.read(report_id)
                    except ValueError as exc:
                        raise HttpError(404, str(exc)) from exc
                    if action == "preview":
                        self.write_report_preview(
                            render_workspace_report_preview(report)
                        )
                    else:
                        self.write_report_reader(
                            render_workspace_report_reader_page(report)
                        )
                    return
                raise HttpError(404, "not found")
            except HttpError as exc:
                self.write_error(exc.status, exc.message)
            except HarborWorkspaceError as exc:
                self.write_error(harbor_error_status(exc), str(exc))
            except CatalogBusyError as exc:
                self.write_error(409, str(exc))
            except AcpError as exc:
                self.write_error(exc.status, str(exc))
            except Exception as exc:  # noqa: BLE001 - HTTP boundary.
                self.write_error(500, str(exc))

        def do_POST(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            self.begin_request(path)
            try:
                self.require_route_access("POST", path)
                payload = self.read_json_payload()
                if path == "/api/auth/login":
                    password = payload.get("password")
                    if not isinstance(password, str) or not password:
                        raise HttpError(400, "password must be a non-empty string")
                    try:
                        token = access_control.login(password, self.client_address[0])
                    except AuthenticationDisabled as exc:
                        raise HttpError(409, str(exc)) from exc
                    except InvalidCredentials as exc:
                        raise HttpError(401, str(exc)) from exc
                    except LoginRateLimited as exc:
                        self._response_headers["Retry-After"] = str(exc.retry_after)
                        raise HttpError(429, "too many failed login attempts") from exc
                    self._serve_role = ADMIN_ROLE
                    self._response_headers["Set-Cookie"] = (
                        access_control.session_cookie(token)
                    )
                    self.write_json(
                        {
                            "authentication_enabled": True,
                            "role": ADMIN_ROLE,
                        }
                    )
                    return
                if path == "/api/auth/logout":
                    access_control.logout(self.headers.get("Cookie"))
                    self._serve_role = GUEST_ROLE
                    self._response_headers["Set-Cookie"] = (
                        access_control.expired_session_cookie()
                    )
                    self.write_json(
                        {
                            "authentication_enabled": (
                                access_control.authentication_enabled
                            ),
                            "role": (
                                GUEST_ROLE
                                if access_control.authentication_enabled
                                else ADMIN_ROLE
                            ),
                        }
                    )
                    return
                if path == "/api/acp/connect":
                    self.write_json(
                        runtime.acp.connect(required_string(payload, "agent_id"))
                    )
                    return
                if path == "/api/acp/disconnect":
                    self.write_json(
                        runtime.acp.disconnect(required_string(payload, "agent_id"))
                    )
                    return
                if path == "/api/acp/sessions":
                    resume_session_id = payload.get("resume_session_id")
                    if resume_session_id is not None and not isinstance(
                        resume_session_id, str
                    ):
                        raise HttpError(400, "resume_session_id must be a string")
                    self.write_json(
                        runtime.acp.open_session(
                            required_string(payload, "agent_id"),
                            resume_session_id=(resume_session_id or None),
                        ),
                        status=201,
                    )
                    return
                if path == "/api/acp/prompt":
                    prompt = required_string(payload, "prompt")
                    blocks = acp_prompt_blocks(
                        store, runtime, prompt, payload.get("context")
                    )
                    self.write_json(
                        runtime.acp.prompt(
                            required_string(payload, "agent_id"),
                            required_string(payload, "session_id"),
                            blocks,
                        ),
                        status=202,
                    )
                    return
                if path == "/api/acp/cancel":
                    self.write_json(
                        runtime.acp.cancel(
                            required_string(payload, "agent_id"),
                            required_string(payload, "session_id"),
                        )
                    )
                    return
                if path == "/api/acp/close":
                    self.write_json(
                        runtime.acp.close_session(
                            required_string(payload, "agent_id"),
                            required_string(payload, "session_id"),
                        )
                    )
                    return
                if path == "/api/acp/permission":
                    request_id = payload.get("request_id")
                    if not isinstance(request_id, (int, str)) or isinstance(
                        request_id, bool
                    ):
                        raise HttpError(400, "request_id must be a string or number")
                    option_id = payload.get("option_id")
                    if option_id is not None and not isinstance(option_id, str):
                        raise HttpError(400, "option_id must be a string")
                    self.write_json(
                        runtime.acp.permission(
                            required_string(payload, "agent_id"),
                            required_string(payload, "session_id"),
                            request_id,
                            option_id,
                            cancelled=payload.get("cancelled") is True,
                        )
                    )
                    return
                if path == "/api/acp/session-mode":
                    self.write_json(
                        runtime.acp.set_mode(
                            required_string(payload, "agent_id"),
                            required_string(payload, "session_id"),
                            required_string(payload, "mode_id"),
                        )
                    )
                    return
                if path == "/api/acp/session-config":
                    if "value" not in payload:
                        raise HttpError(400, "value is required")
                    self.write_json(
                        runtime.acp.set_config(
                            required_string(payload, "agent_id"),
                            required_string(payload, "session_id"),
                            required_string(payload, "option_id"),
                            payload["value"],
                        )
                    )
                    return
                if path == "/api/catalog/resolve":
                    self.write_json(
                        {
                            "generation": runtime.catalog.generation,
                            "source_keys": runtime.resolve_keys(
                                source_keys_payload(payload) or []
                            ),
                        }
                    )
                    return
                if path == "/api/catalog/query":
                    query, view_names, raw_browser_views = catalog_post_query_payload(
                        payload
                    )
                    try:
                        browser_views = runtime.validated_browser_views(
                            raw_browser_views
                        )
                        page = runtime.catalog_page(
                            query,
                            view_names=view_names,
                            browser_views=browser_views,
                        )
                        runtime.ensure_browser_view_names_available(browser_views)
                    except WorkspaceViewConflict as exc:
                        raise HttpError(409, str(exc)) from exc
                    except (WorkspaceViewNotFound, ValueError) as exc:
                        raise HttpError(400, str(exc)) from exc
                    self.write_json(
                        project_catalog_payload(page.to_dict(), self._serve_role)
                    )
                    return
                if path == "/api/catalog/summary":
                    summary_request = catalog_summary_payload(payload)
                    try:
                        browser_views = runtime.validated_browser_views(
                            summary_request.browser_views
                        )
                        summary = runtime.leaderboard_summary(
                            summary_request.query,
                            view_names=summary_request.views,
                            browser_views=browser_views,
                            group_by=summary_request.group_by,
                        )
                        runtime.ensure_browser_view_names_available(browser_views)
                    except WorkspaceViewConflict as exc:
                        raise HttpError(409, str(exc)) from exc
                    except CatalogSummaryCapacityError as exc:
                        raise HttpError(413, str(exc)) from exc
                    except (WorkspaceViewNotFound, ValueError) as exc:
                        raise HttpError(400, str(exc)) from exc
                    self.write_json(summary)
                    return
                if path == "/api/config/acp/agents":
                    runtime.ensure_ready()
                    self.require_workspace_writable()
                    try:
                        self.write_json(mutate_acp_agents(store, runtime, payload))
                    except HarborConflictError:
                        raise
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    return
                if path == "/api/prompts":
                    runtime.ensure_ready()
                    self.require_workspace_writable()
                    action = required_string(payload, "action")
                    prompt_id = required_string(payload, "prompt_id")
                    expected_revision = required_string(payload, "expected_revision")
                    try:
                        if action == "save":
                            content = payload.get("content")
                            if not isinstance(content, str):
                                raise ValueError("prompt content must be a string")
                            prompt_asset = runtime.prompt_assets.save(
                                prompt_id,
                                content,
                                expected_revision=expected_revision,
                            )
                        elif action == "reset":
                            prompt_asset = runtime.prompt_assets.reset(
                                prompt_id,
                                expected_revision=expected_revision,
                            )
                        else:
                            raise ValueError("prompt action must be save or reset")
                    except PromptAssetConflict as exc:
                        raise HttpError(409, str(exc)) from exc
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    self.write_json({"prompt": prompt_asset.to_dict()})
                    return
                if path == "/api/config/harbor/datasets":
                    runtime.ensure_ready()
                    action = required_string(payload, "action")
                    self.write_json(
                        runtime.mutate_with_background_reconcile(
                            "harbor-dataset-config",
                            lambda: mutate_harbor_dataset(
                                store,
                                runtime,
                                action,
                                payload,
                            ),
                        ),
                        status=202,
                    )
                    return
                if path == "/api/harbor/tasks/manifest":
                    runtime.ensure_ready()
                    self.require_workspace_writable()
                    self.write_json(
                        harbor_workspace(store, runtime).sync_manifest(
                            dataset_id=required_string(payload, "dataset_id"),
                            expected_revision=required_string(
                                payload, "expected_revision"
                            ),
                        )
                    )
                    return
                if path == "/api/harbor/tasks":
                    runtime.ensure_ready()
                    self.write_json(
                        runtime.mutate_with_background_reconcile(
                            "harbor-task-reconcile",
                            lambda: mutate_harbor_task(
                                harbor_workspace(store, runtime), payload
                            ),
                        ),
                        status=202,
                    )
                    return
                if path == "/api/harbor/tasks/state":
                    runtime.ensure_ready()
                    archived = required_bool(payload, "archived")
                    items = harbor_task_items_payload(payload)
                    operation = runtime.start_operation(
                        "harbor-task-archive" if archived else "harbor-task-restore",
                        items,
                        lambda item: mutate_harbor_task_state(
                            harbor_workspace(store, runtime), item, archived=archived
                        ),
                    )
                    self.write_json(operation.to_dict(), status=202)
                    return
                if path == "/api/harbor/tasks/delete":
                    runtime.ensure_ready()
                    items = harbor_task_items_payload(payload)
                    operation = runtime.start_operation(
                        "harbor-task-delete",
                        items,
                        lambda item: delete_harbor_task(
                            harbor_workspace(store, runtime), item
                        ),
                    )
                    self.write_json(operation.to_dict(), status=202)
                    return
                if path == "/api/harbor/files":
                    runtime.ensure_ready()
                    self.write_json(
                        runtime.mutate_with_background_reconcile(
                            "harbor-task-reconcile",
                            lambda: harbor_workspace(store, runtime).mutate_file(
                                required_string(payload, "action"), payload
                            ),
                        ),
                        status=202,
                    )
                    return
                if path == "/api/views/summary":
                    if set(payload) != {"browser_views"}:
                        raise HttpError(
                            400, "browser view summary fields must be browser_views"
                        )
                    try:
                        views = runtime.validated_browser_views(
                            payload.get("browser_views")
                        )
                    except WorkspaceViewConflict as exc:
                        raise HttpError(409, str(exc)) from exc
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    try:
                        result = runtime.browser_view_summaries(views)
                    except CatalogSummaryCapacityError as exc:
                        raise HttpError(413, str(exc)) from exc
                    try:
                        runtime.ensure_browser_view_names_available(views)
                    except WorkspaceViewConflict as exc:
                        raise HttpError(409, str(exc)) from exc
                    self.write_json(result)
                    return
                if path == "/api/config/locale":
                    runtime.ensure_ready()
                    self.require_workspace_writable()
                    locale = normalize_locale(required_string(payload, "locale"))
                    write_workspace_locale(store.paths.config_path, locale)
                    runtime.set_config(replace(runtime.config, locale=locale))
                    self.write_json({"locale": locale})
                    return
                if path == "/api/config/adapter-default-db":
                    runtime.ensure_ready()
                    self.require_workspace_writable()
                    adapter_id, raw_db_path = adapter_default_db_payload(payload)
                    try:
                        resolved = write_workspace_adapter_default_db(
                            store.paths.config_path,
                            adapter_id,
                            raw_db_path,
                        )
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    adapter_defaults = dict(runtime.config.adapter_default_db_paths)
                    if resolved:
                        adapter_defaults[adapter_id] = resolved
                    else:
                        adapter_defaults.pop(adapter_id, None)
                    runtime.set_config(
                        replace(
                            runtime.config,
                            adapter_default_db_paths=adapter_defaults,
                        )
                    )
                    self.write_json(
                        {
                            "adapter": adapter_id,
                            "default_db_path": resolved,
                            "adapter_defaults": adapter_defaults,
                        }
                    )
                    return
                if path == "/api/config/harbor/mounts":
                    runtime.ensure_ready()
                    try:
                        self.write_json(
                            runtime.mutate(
                                "harbor-config",
                                [],
                                lambda: update_harbor_mount_config(
                                    store,
                                    runtime,
                                    payload,
                                ),
                            )
                        )
                    except HarborWorkspaceError:
                        raise
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    return
                if path == "/api/db-sessions":
                    runtime.ensure_ready()
                    try:
                        self.write_json(db_sessions_payload(store, payload))
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    return
                if path == "/api/path-picker":
                    multiple = payload.get("multiple", True)
                    if not isinstance(multiple, bool):
                        raise HttpError(400, "multiple must be true or false")
                    try:
                        self.write_json({"paths": pick_file_paths(multiple=multiple)})
                    except PathPickerUnavailable as exc:
                        raise HttpError(503, str(exc)) from exc
                    return
                if path == "/api/exports":
                    export_kind = required_string(payload, "kind")
                    if export_kind.strip().lower() == "summary_xlsx":
                        summary_request = summary_export_payload(payload.get("summary"))
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
                                    summary_request.views,
                                    browser_views,
                                )
                            export = build_summary_serve_export(
                                sheets,
                                runtime.config,
                                scope=summary_request.scope,
                            )
                            runtime.ensure_browser_view_names_available(browser_views)
                        except WorkspaceViewConflict as exc:
                            raise HttpError(409, str(exc)) from exc
                        except CatalogSummaryCapacityError as exc:
                            raise HttpError(413, str(exc)) from exc
                        except ValueError as exc:
                            raise HttpError(400, str(exc)) from exc
                        self.write_download(
                            export.content,
                            export.content_type,
                            export.filename,
                        )
                        return
                    raw_export_query = payload.get("query")
                    export_query = catalog_query_payload(raw_export_query)
                    view_names = catalog_view_names_payload(raw_export_query)
                    try:
                        browser_views = runtime.validated_browser_views(
                            raw_export_query.get("browser_views", [])
                            if isinstance(raw_export_query, dict)
                            else []
                        )
                        export = build_serve_export(
                            runtime.catalog,
                            store,
                            runtime.config,
                            kind=export_kind,
                            query=export_query,
                            view_queries=runtime.workspace_view_queries(
                                view_names, browser_views
                            ),
                            source_keys=source_keys_payload(payload),
                            audience=self._serve_role,
                        )
                        runtime.ensure_browser_view_names_available(browser_views)
                    except WorkspaceViewConflict as exc:
                        raise HttpError(409, str(exc)) from exc
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    self.write_download(
                        export.content, export.content_type, export.filename
                    )
                    return
                if path == "/api/reports":
                    runtime.ensure_ready()
                    self.require_workspace_writable()
                    source_keys = source_keys_payload(payload) or []
                    try:
                        report_id = runtime.workspace_reports.import_file(
                            required_string(payload, "path"),
                            source_keys,
                        )
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    self.write_json(
                        {
                            "reports": runtime.workspace_report_catalog(),
                            "report_id": report_id,
                        }
                    )
                    return
                if path == "/api/views/update":
                    runtime.ensure_ready()
                    self.require_workspace_writable()
                    value = payload.get("value")
                    if not isinstance(value, str):
                        raise HttpError(400, "value must be a string")
                    try:
                        view = runtime.workspace_views.update(
                            name=required_string(payload, "name"),
                            field=required_string(payload, "field"),
                            value=value,
                        )
                    except WorkspaceViewConflict as exc:
                        raise HttpError(409, str(exc)) from exc
                    except WorkspaceViewNotFound as exc:
                        raise HttpError(404, str(exc)) from exc
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    self.write_json(
                        {
                            "view": view.to_dict(),
                            "views": runtime.workspace_view_catalog(),
                        }
                    )
                    return
                if path == "/api/views/delete":
                    runtime.ensure_ready()
                    self.require_workspace_writable()
                    try:
                        deleted = runtime.workspace_views.delete(payload.get("names"))
                    except WorkspaceViewNotFound as exc:
                        raise HttpError(404, str(exc)) from exc
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    self.write_json(
                        {
                            "deleted": deleted,
                            "views": runtime.workspace_view_catalog(),
                        }
                    )
                    return
                if path == "/api/views":
                    runtime.ensure_ready()
                    self.require_workspace_writable()
                    overwrite = payload.get("overwrite")
                    if not isinstance(overwrite, bool):
                        raise HttpError(400, "overwrite must be true or false")
                    try:
                        view = runtime.workspace_views.save(
                            name=required_string(payload, "name"),
                            filters=payload.get("filters"),
                            group_by=payload.get("group_by"),
                            notes=payload.get("notes", ""),
                            overwrite=overwrite,
                        )
                    except WorkspaceViewConflict as exc:
                        raise HttpError(409, str(exc)) from exc
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    self.write_json(
                        {
                            "view": view.to_dict(),
                            "views": runtime.workspace_view_catalog(),
                        }
                    )
                    return
                if path == "/api/sources/state":
                    runtime.ensure_ready()
                    source_keys = source_keys_payload(payload)
                    if not source_keys:
                        raise HttpError(
                            400, "source_keys must include at least one source"
                        )
                    active = required_bool(payload, "active")
                    rows = [runtime.catalog.row_for_key(key) for key in source_keys]
                    operation = runtime.start_operation(
                        "activate" if active else "archive",
                        rows,
                        lambda row: source_state_operation(store, row, active),
                    )
                    self.write_json(operation.to_dict(), status=202)
                    return
                if path == "/api/sources/delete":
                    runtime.ensure_ready()
                    source_keys = source_keys_payload(payload)
                    if not source_keys:
                        raise HttpError(
                            400, "source_keys must include at least one source"
                        )
                    rows = [runtime.catalog.row_for_key(key) for key in source_keys]
                    reject_linked_harbor_delete(rows)
                    operation = runtime.start_operation(
                        "delete",
                        rows,
                        lambda row: delete_source_operation(store, row),
                    )
                    self.write_json(operation.to_dict(), status=202)
                    return
                if path == "/api/sources":
                    runtime.ensure_ready()
                    operation_payloads = source_operation_payloads(payload)
                    if len(operation_payloads) > 1:
                        operation = runtime.start_operation(
                            "source-import",
                            operation_payloads,
                            lambda item: {
                                **(
                                    {"path": item.get("path")}
                                    if item.get("path")
                                    else {}
                                ),
                                **(
                                    {"session_id": item.get("session_id")}
                                    if item.get("session_id")
                                    else {}
                                ),
                                **add_source_result_payload(
                                    add_source_payload(store, runtime.config, item)
                                ),
                            },
                        )
                        self.write_json(operation.to_dict(), status=202)
                        return
                    try:
                        response = runtime.mutate(
                            "source-import",
                            [],
                            lambda: add_source_result_payload(
                                add_source_payload(store, runtime.config, payload)
                            ),
                        )
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    self.write_json(response)
                    return
                if path == "/api/sources/reload":
                    runtime.ensure_ready()
                    operation = runtime.start_operation(
                        "reload",
                        [None],
                        lambda _item: {
                            "source_keys": store.harbor_source_keys(runtime.config)
                        },
                    )
                    self.write_json(operation.to_dict(), status=202)
                    return
                if path == "/api/refresh":
                    runtime.ensure_ready()
                    source_keys = source_keys_payload(payload) or []
                    if not source_keys:
                        raise HttpError(
                            400, "source_keys must include at least one source"
                        )
                    rows = [runtime.catalog.row_for_key(key) for key in source_keys]
                    operation = runtime.start_operation(
                        "refresh",
                        rows,
                        lambda row: refresh_source_operation(
                            store, runtime.config, row
                        ),
                    )
                    self.write_json(operation.to_dict(), status=202)
                    return

                report_action = report_action_path(path)
                if report_action is not None:
                    runtime.ensure_ready()
                    self.require_workspace_writable()
                    report_id, action = report_action
                    try:
                        if action == "bindings":
                            if not isinstance(payload.get("source_keys"), list):
                                raise HttpError(400, "source_keys must be an array")
                            source_keys = source_keys_payload(payload)
                            assert source_keys is not None
                            runtime.workspace_reports.replace_bindings(
                                report_id,
                                source_keys,
                            )
                        elif action == "delete":
                            runtime.workspace_reports.delete(report_id)
                        else:
                            raise HttpError(404, "unknown report action")
                    except WorkspaceReportNotFound as exc:
                        raise HttpError(404, str(exc)) from exc
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    self.write_json({"reports": runtime.workspace_report_catalog()})
                    return

                source_action = source_action_path(path)
                if source_action is not None:
                    runtime.ensure_ready()
                    source_key, action = source_action
                    row = runtime.catalog.row_for_key(source_key)
                    if action == "archive":
                        mutate = partial(store.set_source_active_row, row, False)
                    elif action == "activate":
                        mutate = partial(store.set_source_active_row, row, True)
                    elif action == "refresh":
                        mutate = partial(store.refresh_source, row, runtime.config)
                    elif action == "delete":
                        reject_linked_harbor_delete([row])
                        mutate = partial(store.delete_source_row, row)
                    elif action == "alias":
                        mutate = partial(
                            store.set_source_alias_row,
                            row,
                            alias_payload(payload),
                        )
                    elif action == "category":
                        mutate = partial(
                            store.set_source_category_row,
                            row,
                            category_payload(payload),
                        )
                    elif action == "tags":
                        mutate = partial(
                            store.set_source_tags_row,
                            row,
                            tags_payload(payload),
                        )
                    elif action == "notes":
                        mutate = partial(
                            store.save_source_notes_row,
                            row,
                            markdown_payload(payload),
                            runtime.config,
                        )
                    else:
                        raise HttpError(404, "unknown source action")
                    try:
                        self.write_json(runtime.mutate(action, [source_key], mutate))
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    return

                raise HttpError(404, "not found")
            except HttpError as exc:
                self.write_error(exc.status, exc.message)
            except HarborWorkspaceError as exc:
                self.write_error(harbor_error_status(exc), str(exc))
            except CatalogBusyError as exc:
                self.write_error(409, str(exc))
            except AcpError as exc:
                self.write_error(exc.status, str(exc))
            except Exception as exc:  # noqa: BLE001 - HTTP boundary.
                self.write_error(500, str(exc))
            finally:
                lease = self._workspace_write_lease
                self._workspace_write_lease = None
                if lease is not None:
                    lease.__exit__(None, None, None)

        def begin_request(self, path: str) -> None:
            del path
            self._workspace_write_lease = None
            self._response_headers: dict[str, str] = {}
            self._serve_role = access_control.role(self.headers.get("Cookie"))

        def require_route_access(self, method: str, path: str) -> None:
            if not access_control.permits(method, path, self._serve_role):
                raise HttpError(403, "administrator access required")

        def read_json_payload(self) -> dict[str, Any]:
            self.require_same_origin()
            content_type = self.headers.get("Content-Type", "")
            media_type = content_type.split(";", 1)[0].strip().lower()
            if media_type != "application/json":
                raise HttpError(415, "mutating APIs require application/json POST")
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise HttpError(400, "invalid Content-Length") from exc
            if content_length > MAX_JSON_BODY_BYTES:
                raise HttpError(413, "request body exceeds serve limit")
            raw = self.rfile.read(content_length) if content_length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise HttpError(400, "request body must be a JSON object") from exc
            if not isinstance(payload, dict):
                raise HttpError(400, "request body must be a JSON object")
            return payload

        def require_same_origin(self) -> None:
            origin = self.headers.get("Origin")
            if origin is not None and not self.is_same_origin(
                origin, origin_header=True
            ):
                raise HttpError(403, "mutating APIs require same-origin Origin")
            referer = self.headers.get("Referer")
            if referer is not None and not self.is_same_origin(referer):
                raise HttpError(403, "mutating APIs require same-origin Referer")

        def require_workspace_writable(self) -> None:
            if runtime.is_loading():
                raise HttpError(409, "serve catalog is checking runs")
            if self._workspace_write_lease is not None:
                return
            lease = runtime.catalog.workspace_write_guard()
            lease.__enter__()
            self._workspace_write_lease = lease

        def is_same_origin(self, value: str, *, origin_header: bool = False) -> bool:
            try:
                parsed = urlsplit(value)
            except ValueError:
                return False
            if parsed.scheme != "http" or not parsed.netloc:
                return False
            if origin_header and (parsed.path or parsed.query or parsed.fragment):
                return False
            host = self.headers.get("Host")
            if not host:
                return False
            return parsed.netloc.lower() == host.lower()

        def write_html(self, html: str, status: int = 200) -> None:
            data = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("X-Frame-Options", "DENY")
            self.write_common_headers()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def write_json(self, payload: Any, status: int = 200) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.write_common_headers()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def write_js(
            self,
            data: bytes,
            status: int = 200,
            *,
            cache_control: str = "public, max-age=31536000, immutable",
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Cache-Control", cache_control)
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.write_pending_headers()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def write_workspace_css(self, data: bytes, etag: str) -> None:
            not_modified = self.headers.get("If-None-Match") == etag
            self.send_response(304 if not_modified else 200)
            self.send_header("Content-Type", "text/css; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("ETag", etag)
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.write_pending_headers()
            if not not_modified:
                self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if not not_modified:
                self.wfile.write(data)

        def write_download(
            self,
            data: bytes,
            content_type: str,
            filename: str,
            status: int = 200,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header(
                "Content-Disposition", f'attachment; filename="{filename}"'
            )
            self.write_common_headers()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def write_report_preview(self, data: bytes, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Security-Policy", REPORT_PREVIEW_CSP)
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.write_pending_headers()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def write_report_reader(self, data: bytes, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Security-Policy", REPORT_READER_CSP)
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.write_pending_headers()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def write_common_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.write_pending_headers()

        def write_pending_headers(self) -> None:
            for name, value in self._response_headers.items():
                self.send_header(name, value)

        def write_error(self, status: int, message: str) -> None:
            safe_message = project_guest_error(status, message, self._serve_role)
            if urlsplit(self.path).path.startswith("/api/"):
                self.write_json({"error": safe_message}, status=status)
                return
            self.write_html(f"{status} {safe_message}\n", status=status)

    return ServeHandler


def report_action_path(path: str) -> tuple[str, str] | None:
    prefix = "/api/reports/"
    if not path.startswith(prefix):
        return None
    parts = path[len(prefix) :].split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise HttpError(404, "unknown report action")
    return unquote(parts[0]), parts[1]


def operation_status_path(path: str) -> str | None:
    prefix = "/api/operations/"
    if not path.startswith(prefix):
        return None
    operation_id = unquote(path[len(prefix) :]).strip()
    if not operation_id or "/" in operation_id:
        raise HttpError(404, "unknown operation")
    return operation_id


def single_query_value(query: str, key: str) -> str | None:
    values = parse_qs(query).get(key) or []
    for value in values:
        text = str(value).strip()
        if text:
            return text
    return None


def required_query_value(query: str, key: str) -> str:
    value = single_query_value(query, key)
    if value is None:
        raise HttpError(400, f"{key} is required")
    return value


def harbor_error_status(exc: HarborWorkspaceError) -> int:
    if isinstance(exc, HarborConflictError):
        return 409
    if isinstance(exc, HarborNotFoundError):
        return 404
    if isinstance(exc, HarborSizeError):
        return 413
    return 400


def harbor_workspace(
    store: ServeStateStore,
    runtime: ServeRuntime,
) -> HarborWorkspace:
    return HarborWorkspace(store.paths.config_path, runtime.config)


def catalog_view_names(raw_query: str) -> tuple[str, ...]:
    values = parse_qs(raw_query, keep_blank_values=True)
    names = [
        str(value).strip() for value in values.get("view", []) if str(value).strip()
    ]
    return tuple(dict.fromkeys(names))


def catalog_view_names_payload(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, dict):
        raise HttpError(400, "query must be an object")
    raw_names = value.get("views", [])
    if not isinstance(raw_names, list) or any(
        not isinstance(name, str) for name in raw_names
    ):
        raise HttpError(400, "query views must be a string array")
    names = [name.strip() for name in raw_names if name.strip()]
    return tuple(dict.fromkeys(names))


def catalog_query(raw_query: str) -> CatalogQuery:
    values = parse_qs(raw_query, keep_blank_values=True)

    def first(key: str, default: str) -> str:
        raw = values.get(key)
        return str(raw[0]) if raw else default

    def integer(key: str, default: int) -> int:
        try:
            return int(first(key, str(default)))
        except ValueError as exc:
            raise HttpError(400, f"{key} must be an integer") from exc

    def many(*keys: str) -> tuple[str, ...]:
        result: list[str] = []
        for key in keys:
            for raw in values.get(key, []):
                result.extend(
                    part.strip() for part in str(raw).split(",") if part.strip()
                )
        return tuple(dict.fromkeys(result))

    def repeated(*keys: str) -> tuple[str, ...]:
        result = [
            str(raw).strip()
            for key in keys
            for raw in values.get(key, [])
            if str(raw).strip()
        ]
        return tuple(dict.fromkeys(result))

    try:
        return CatalogQuery(
            state=first("state", "active"),
            page=integer("page", 1),
            page_size=integer("page_size", 100),
            search=first("search", ""),
            sort=first("sort", "last_turn_end"),
            direction=first("direction", "desc"),
            categories=repeated("category", "categories"),
            tags=many("tag", "tags"),
            agents=many("agent", "agents"),
            models=many("model", "models"),
            results=many("result", "results"),
            tasks=repeated("task", "tasks"),
            jobs=repeated("job", "jobs"),
            providers=repeated("provider", "providers"),
            include_unreadable=first("surface", "leaderboard") == "sources",
        ).normalized()
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc


def source_operation_payloads(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_path = payload.get("path")
    if isinstance(raw_path, str):
        lines = [line.strip() for line in raw_path.splitlines() if line.strip()]
        if len(lines) > 1:
            return [{**payload, "path": line} for line in lines]
    session_ids = payload.get("session_ids")
    if isinstance(session_ids, list) and len(session_ids) > 1:
        return [
            {
                **payload,
                "session_ids": None,
                "session_id": str(session_id),
            }
            for session_id in session_ids
        ]
    return [payload]


def catalog_query_payload(value: Any) -> CatalogQuery:
    if value is None:
        return CatalogQuery()
    if not isinstance(value, dict):
        raise HttpError(400, "query must be an object")
    try:
        return CatalogQuery(
            state=str(value.get("state") or "active"),
            page=1,
            page_size=100,
            search=str(value.get("search") or ""),
            sort=str(value.get("sort") or "last_turn_end"),
            direction=str(value.get("direction") or "desc"),
            categories=tuple(value.get("categories") or ()),
            tags=tuple(value.get("tags") or ()),
            agents=tuple(value.get("agents") or ()),
            models=tuple(value.get("models") or ()),
            results=tuple(value.get("results") or ()),
            tasks=tuple(value.get("tasks") or ()),
            jobs=tuple(value.get("jobs") or ()),
            providers=tuple(value.get("providers") or ()),
        ).normalized()
    except (TypeError, ValueError) as exc:
        raise HttpError(400, str(exc)) from exc


def add_source_result_payload(result: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"source_keys": list(result.keys)}
    if result.import_results is not None:
        payload["import_results"] = list(result.import_results)
    return payload


def source_state_operation(
    store: ServeStateStore,
    row: dict[str, Any],
    active: bool,
) -> dict[str, Any]:
    store.set_source_active_row(row, active)
    return {"source_key": row["source_key"]}


def refresh_source_operation(
    store: ServeStateStore,
    config: ToolConfig,
    row: dict[str, Any],
) -> dict[str, Any]:
    store.refresh_source(row, config)
    return {"source_key": row["source_key"]}


def delete_source_operation(
    store: ServeStateStore,
    row: dict[str, Any],
) -> dict[str, Any]:
    store.delete_source_row(row)
    return {"source_key": row["source_key"]}


def reject_linked_harbor_delete(rows: list[dict[str, Any]]) -> None:
    if any(is_harbor_source(row) for row in rows):
        raise HttpError(
            400,
            "linked Harbor Trials cannot be deleted; archive the source instead",
        )


def harbor_config_payload(
    store: ServeStateStore,
    runtime: ServeRuntime,
    *,
    config: ToolConfig | None = None,
) -> dict[str, Any]:
    current = config or runtime.config
    return {
        "revision": config_revision(store.paths.config_path),
        "datasets": [
            {"id": dataset.id, "path": dataset.path}
            for dataset in current.harbor_datasets
        ],
        "mounts": [harbor_mount_payload(mount) for mount in current.harbor_mounts],
    }


def workspace_config_payload(
    store: ServeStateStore, runtime: ServeRuntime
) -> dict[str, Any]:
    config, acp_status = runtime.config_with_acp_status()
    status_by_id = {item["id"]: item for item in acp_status.get("agents", [])}
    payload = harbor_config_payload(store, runtime, config=config)
    payload["acp_agents"] = [
        {
            "id": agent.id,
            "title": agent.title,
            "command": agent.command,
            "args": list(agent.args),
            "connected": bool(status_by_id.get(agent.id, {}).get("connected")),
            "protocol_version": status_by_id.get(agent.id, {}).get("protocol_version"),
        }
        for agent in config.acp_agents
    ]
    return payload


def mutate_acp_agents(
    store: ServeStateStore,
    runtime: ServeRuntime,
    payload: dict[str, Any],
) -> dict[str, Any]:
    expected_revision = required_string(payload, "expected_revision")
    if config_revision(store.paths.config_path) != expected_revision:
        raise HarborConflictError(
            "Workspace configuration changed; refresh before saving"
        )
    action = required_string(payload, "action")
    current = list(runtime.config.acp_agents)
    if action == "delete":
        raw_ids = payload.get("agent_ids")
        if (
            not isinstance(raw_ids, list)
            or not raw_ids
            or not all(isinstance(item, str) and item.strip() for item in raw_ids)
        ):
            raise ValueError("agent_ids must be a non-empty array of strings")
        agent_ids = list(dict.fromkeys(item.strip() for item in raw_ids))
        unknown = [
            agent_id
            for agent_id in agent_ids
            if agent_id not in {agent.id for agent in current}
        ]
        if unknown:
            raise HttpError(404, f"ACP agent not found: {', '.join(unknown)}")
        selected = set(agent_ids)
        proposed = tuple(agent for agent in current if agent.id not in selected)
    elif action == "upsert":
        raw_args = payload.get("args", [])
        if not isinstance(raw_args, list) or not all(
            isinstance(item, str) for item in raw_args
        ):
            raise ValueError("args must be an array of strings")
        candidate = AcpAgent(
            id=required_string(payload, "agent_id"),
            title=required_string(payload, "title"),
            command=required_string(payload, "command"),
            args=tuple(raw_args),
        )
        candidate = apply_toml_config(
            ToolConfig(),
            {
                "acp": {
                    "agents": [
                        {
                            "id": candidate.id,
                            "title": candidate.title,
                            "command": candidate.command,
                            "args": list(candidate.args),
                        }
                    ]
                }
            },
        ).acp_agents[0]
        original_id = str(payload.get("original_id") or "").strip()
        existing_ids = {agent.id for agent in current}
        if original_id:
            if original_id not in existing_ids:
                raise HttpError(404, f"ACP agent not found: {original_id}")
            if candidate.id != original_id and candidate.id in existing_ids:
                raise ValueError(f"duplicate acp agent id: {candidate.id}")
            proposed = tuple(
                candidate if agent.id == original_id else agent for agent in current
            )
        else:
            if candidate.id in existing_ids:
                raise ValueError(f"duplicate acp agent id: {candidate.id}")
            proposed = (*current, candidate)
    else:
        raise ValueError("ACP agent action must be upsert or delete")
    saved = write_workspace_acp_agents(store.paths.config_path, tuple(proposed))
    runtime.set_config(replace(runtime.config, acp_agents=saved))
    return workspace_config_payload(store, runtime)


def mutate_harbor_dataset(
    store: ServeStateStore,
    runtime: ServeRuntime,
    action: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    library = harbor_workspace(store, runtime)
    expected_revision = required_string(payload, "expected_revision")
    if action == "create":
        config = library.create_dataset(
            dataset_id=required_string(payload, "dataset_id"),
            path=required_string(payload, "path"),
            package_name=required_string(payload, "package_name"),
            description=str(payload.get("description") or ""),
            expected_revision=expected_revision,
        )
    elif action == "register":
        path = required_string(payload, "path")
        config = library.register_dataset(
            dataset_id=unique_harbor_id_from_path(
                path,
                fallback="dataset",
                existing_ids=(item.id for item in runtime.config.harbor_datasets),
                base_dir=store.paths.config_path.parent,
            ),
            path=path,
            expected_revision=expected_revision,
        )
    elif action == "update":
        config = library.update_dataset(
            dataset_id=required_string(payload, "dataset_id"),
            new_id=required_string(payload, "new_id"),
            path=required_string(payload, "path"),
            mount_ids=harbor_id_list_payload(payload, "mount_ids", allow_empty=True),
            expected_revision=expected_revision,
        )
    elif action == "unregister":
        config = library.remove_datasets(
            dataset_ids=dataset_ids_payload(payload),
            expected_revision=expected_revision,
        )
    else:
        raise HarborWorkspaceError(
            "Dataset action must be create, register, update, or unregister"
        )
    runtime.set_config(config)
    return workspace_config_payload(store, runtime)


def mutate_harbor_task(
    library: HarborWorkspace,
    payload: dict[str, Any],
) -> dict[str, Any]:
    action = required_string(payload, "action")
    common = {
        "dataset_id": required_string(payload, "dataset_id"),
        "expected_revision": required_string(payload, "expected_revision"),
    }
    if action == "create":
        raw_steps = payload.get("steps", 0)
        if not isinstance(raw_steps, int) or isinstance(raw_steps, bool):
            raise HarborWorkspaceError("steps must be an integer")
        return library.create_task(
            **common,
            directory=required_string(payload, "directory"),
            package_name=required_string(payload, "package_name"),
            steps=raw_steps,
        )
    if action == "rename":
        return library.rename_task(
            **common,
            task=required_string(payload, "task"),
            new_directory=required_string(payload, "new_directory"),
        )
    if action == "rename_archived":
        return library.rename_archived_task(
            **common,
            entry_id=required_string(payload, "entry_id"),
            new_directory=required_string(payload, "new_directory"),
        )
    raise HarborWorkspaceError("Task action must be create, rename, or rename_archived")


def harbor_task_items_payload(payload: dict[str, Any]) -> list[dict[str, str]]:
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise HttpError(400, "items must be a non-empty array")
    items: list[dict[str, str]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise HttpError(400, "each Task item must be an object")
        item = {
            "dataset_id": required_string(raw, "dataset_id"),
            "expected_revision": required_string(raw, "expected_revision"),
        }
        task = str(raw.get("task") or "").strip()
        entry_id = str(raw.get("entry_id") or "").strip()
        if bool(task) == bool(entry_id):
            raise HttpError(400, "each Task item must identify task or entry_id")
        if task:
            item["task"] = task
        else:
            item["entry_id"] = entry_id
        if raw.get("directory") is not None:
            if not isinstance(raw["directory"], str):
                raise HttpError(400, "directory must be a string")
            item["directory"] = raw["directory"].strip()
        items.append(item)
    return items


def mutate_harbor_task_state(
    library: HarborWorkspace, item: dict[str, str], *, archived: bool
) -> dict[str, Any]:
    common = {
        "dataset_id": item["dataset_id"],
        "expected_revision": item["expected_revision"],
    }
    if archived:
        task = item.get("task")
        if not task:
            raise HarborWorkspaceError("Only active Tasks can be archived")
        result = library.trash_task(**common, task=task)
        return {
            "dataset_id": item["dataset_id"],
            "task": task,
            "entry_id": result["entry_id"],
        }
    entry_id = item.get("entry_id")
    if not entry_id:
        raise HarborWorkspaceError("Only archived Tasks can be restored")
    result = library.restore_task(
        **common,
        entry_id=entry_id,
        directory=item.get("directory") or None,
    )
    return {
        "dataset_id": item["dataset_id"],
        "entry_id": entry_id,
        "task": result["task"]["directory"],
    }


def delete_harbor_task(
    library: HarborWorkspace, item: dict[str, str]
) -> dict[str, Any]:
    common = {
        "dataset_id": item["dataset_id"],
        "expected_revision": item["expected_revision"],
    }
    if item.get("task"):
        return library.delete_task(**common, task=item["task"])
    entry_id = item["entry_id"]
    library.purge_task(**common, entry_id=entry_id)
    return {"dataset_id": item["dataset_id"], "entry_id": entry_id}


def dataset_ids_payload(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("dataset_ids")
    if (
        not isinstance(raw, list)
        or not raw
        or not all(isinstance(value, str) and value.strip() for value in raw)
    ):
        raise HttpError(400, "dataset_ids must be a non-empty array of strings")
    return list(dict.fromkeys(value.strip() for value in raw))


def harbor_id_list_payload(
    payload: dict[str, Any], key: str, *, allow_empty: bool
) -> list[str]:
    raw = payload.get(key)
    if not isinstance(raw, list) or not all(
        isinstance(value, str) and value.strip() for value in raw
    ):
        raise HttpError(400, f"{key} must be an array of non-empty strings")
    values = [value.strip() for value in raw]
    if not allow_empty and not values:
        raise HttpError(400, f"{key} must not be empty")
    if len(set(values)) != len(values):
        raise HttpError(400, f"{key} must not contain duplicates")
    return values


def update_harbor_mount_config(
    store: ServeStateStore,
    runtime: ServeRuntime,
    payload: dict[str, Any],
) -> dict[str, Any]:
    expected_revision = required_string(payload, "expected_revision")
    if config_revision(store.paths.config_path) != expected_revision:
        raise HarborConflictError(
            "Workspace configuration changed; refresh before saving"
        )
    mounts = harbor_mounts_from_payload(
        runtime.config.harbor_mounts,
        payload,
        base_dir=store.paths.config_path.parent,
        datasets=runtime.config.harbor_datasets,
    )
    validate_harbor_mount_paths(mounts, runtime.config.harbor_datasets)
    proposed_config = replace(runtime.config, harbor_mounts=mounts)
    WorkspaceSources(store, proposed_config).source_keys()
    saved_mounts = write_workspace_harbor_mounts(store.paths.config_path, mounts)
    runtime.set_config(replace(runtime.config, harbor_mounts=saved_mounts))
    return workspace_config_payload(store, runtime)


def acp_prompt_blocks(
    store: ServeStateStore,
    runtime: ServeRuntime,
    prompt: str,
    raw_context: Any,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    if raw_context is None:
        return blocks
    if not isinstance(raw_context, dict):
        raise HttpError(400, "ACP context must be an object")
    kind = required_string(raw_context, "kind")
    if kind == "source":
        source_key = required_string(raw_context, "source_key")
        try:
            context_payload: Any = runtime.detail(source_key).to_dict()
        except ValueError as exc:
            raise HttpError(400, str(exc)) from exc
        reference = {
            "kind": kind,
            "source_key": source_key,
            "step_id": raw_context.get("step_id"),
        }
        uri = f"peval://source/{source_key}"
    elif kind == "dataset_task":
        dataset_id = required_string(raw_context, "dataset_id")
        task = required_string(raw_context, "task")
        context_payload = harbor_workspace(store, runtime).task_detail(dataset_id, task)
        reference = {"kind": kind, "dataset_id": dataset_id, "task": task}
        uri = f"peval://dataset/{dataset_id}/{task}"
    elif kind == "report":
        report_id = required_string(raw_context, "report_id")
        try:
            report = runtime.workspace_reports.read(report_id)
        except ValueError as exc:
            raise HttpError(404, str(exc)) from exc
        context_payload = {
            "report_id": report.report_id,
            "filename": report.filename,
            "format": report.format,
            "source_refs": list(report.source_refs),
            "content": report.content.decode("utf-8", errors="replace"),
        }
        reference = {"kind": kind, "report_id": report_id}
        uri = f"peval://report/{report_id}"
    else:
        raise HttpError(400, "ACP context kind must be source, dataset_task, or report")
    serialized = json.dumps(
        {"reference": reference, "value": context_payload},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    limit = max(1, runtime.config.max_content_chars)
    mime_type = "application/json"
    if len(serialized) > limit:
        marker = "\n[peval context truncated]"
        serialized = (serialized[: max(0, limit - len(marker))] + marker)[:limit]
        mime_type = "text/plain"
    blocks.append(
        {
            "type": "resource",
            "resource": {
                "uri": uri,
                "mimeType": mime_type,
                "text": serialized,
            },
        }
    )
    return blocks


def harbor_mounts_from_payload(
    current: tuple[HarborMount, ...],
    payload: dict[str, Any],
    *,
    base_dir: Path,
    datasets: tuple[Any, ...],
) -> tuple[HarborMount, ...]:
    action = required_string(payload, "action")
    if action not in {"upsert", "delete"}:
        raise HttpError(400, "Harbor mount action must be upsert or delete")
    original_id = str(payload.get("original_id") or "").strip()
    if action == "delete":
        mount_ids = harbor_id_list_payload(payload, "mount_ids", allow_empty=False)
        known_mount_ids = {mount.id for mount in current}
        unknown_mount_ids = [
            mount_id for mount_id in mount_ids if mount_id not in known_mount_ids
        ]
        if unknown_mount_ids:
            raise HarborNotFoundError(
                f"Harbor mount not found: {', '.join(unknown_mount_ids)}"
            )
        selected = set(mount_ids)
        return tuple(mount for mount in current if mount.id not in selected)

    jobs_path = required_string(payload, "jobs_path")
    if original_id:
        mount_id = required_string(payload, "mount_id")
        raw_dataset_ids = payload.get("dataset_ids", [])
        if isinstance(raw_dataset_ids, list) and all(
            isinstance(item, str) for item in raw_dataset_ids
        ):
            dataset_ids = [item.strip() for item in raw_dataset_ids if item.strip()]
        else:
            raise HttpError(400, "dataset_ids must be an array of strings")
    else:
        mount_id = unique_harbor_id_from_path(
            jobs_path,
            fallback="jobs",
            existing_ids=(mount.id for mount in current),
            base_dir=base_dir,
        )
        dataset_ids = []

    raw_mounts: list[dict[str, Any]] = []
    replaced = False
    for mount in current:
        raw = harbor_mount_payload(mount)
        if original_id and mount.id == original_id:
            raw = {"id": mount_id, "path": jobs_path, "dataset_ids": dataset_ids}
            replaced = True
        raw_mounts.append(raw)
    if original_id and not replaced:
        raise HttpError(404, f"unknown Harbor mount: {original_id}")
    if not original_id:
        raw_mounts.append(
            {"id": mount_id, "path": jobs_path, "dataset_ids": dataset_ids}
        )
    try:
        return apply_toml_config(
            ToolConfig(workspace_root=str(base_dir)),
            {
                "harbor": {
                    "datasets": [
                        {"id": dataset.id, "path": dataset.path} for dataset in datasets
                    ],
                    "mounts": raw_mounts,
                }
            },
            base_dir=base_dir,
        ).harbor_mounts
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc


def harbor_mount_payload(mount: HarborMount) -> dict[str, Any]:
    return {
        "id": mount.id,
        "path": mount.path,
        "dataset_ids": list(mount.dataset_ids),
    }
