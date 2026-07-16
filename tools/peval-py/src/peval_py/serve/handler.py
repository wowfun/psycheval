from __future__ import annotations

import json
from dataclasses import replace
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from peval_py.config import ToolConfig, write_workspace_adapter_default_db, write_workspace_locale
from peval_py.html import render_serve_html
from peval_py.i18n import normalize_locale
from peval_py.serve.assets import ECHARTS_ASSET_PATH, cached_echarts_asset
from peval_py.serve.constants import MAX_JSON_BODY_BYTES
from peval_py.serve.errors import HttpError
from peval_py.serve.exports import (
    build_serve_export,
    build_summary_serve_export,
    build_workspace_snapshot_export,
)
from peval_py.serve.payloads import (
    adapter_default_db_payload,
    adapter_override_payload,
    alias_payload,
    markdown_payload,
    required_bool,
    required_string,
    source_action_path,
    source_keys_payload,
    summary_export_payload,
    tags_payload,
    workspace_snapshot_export_payload,
)
from peval_py.serve.path_picker import PathPickerUnavailable, pick_file_paths
from peval_py.serve.runtime import ServeRuntime
from peval_py.serve.sources import add_source_payload, db_sessions_payload
from peval_py.state import CatalogBusyError, CatalogQuery, ServeStateStore
from peval_py.workspace_reports import (
    WorkspaceReportNotFound,
    render_workspace_report_reader_page,
    render_workspace_report_preview,
)
from peval_py.workspace_views import WorkspaceViewConflict, WorkspaceViewNotFound


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
) -> type[BaseHTTPRequestHandler]:
    if isinstance(store_or_runtime, ServeRuntime):
        runtime = store_or_runtime
        store = runtime.store
    else:
        if config is None:
            raise ValueError("config is required when make_handler receives a store")
        store = store_or_runtime
        runtime = ServeRuntime(store, config)

    class ServeHandler(BaseHTTPRequestHandler):
        server_version = "peval-py-serve/1"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def do_GET(self) -> None:  # noqa: N802
            parsed_url = urlsplit(self.path)
            path = parsed_url.path
            try:
                if path == "/":
                    self.write_html(
                        render_serve_html(
                            runtime.shell_report(),
                            locale=runtime.config.locale,
                            sources=[],
                            reports=[],
                            adapter_defaults=runtime.config.adapter_default_db_paths,
                            loading=not runtime.catalog.has_generation or runtime.is_loading(),
                            load_error=runtime.load_error(),
                        )
                    )
                    return
                if path == ECHARTS_ASSET_PATH:
                    self.write_js(cached_echarts_asset(store))
                    return
                if path == "/api/catalog":
                    try:
                        page = runtime.catalog_page(
                            catalog_query(parsed_url.query),
                            view_names=catalog_view_names(parsed_url.query),
                        )
                    except WorkspaceViewNotFound as exc:
                        raise HttpError(400, str(exc)) from exc
                    self.write_json(page.to_dict())
                    return
                if path == "/api/report":
                    source_key = single_query_value(parsed_url.query, "source_key")
                    if not source_key:
                        raise HttpError(400, "source_key is required")
                    try:
                        self.write_json(runtime.detail(source_key).to_dict())
                    except ValueError as exc:
                        raise HttpError(400, str(exc)) from exc
                    return
                if path == "/api/sources":
                    self.write_json(runtime.source_envelope())
                    return
                if path == "/api/reports":
                    self.write_json({"reports": runtime.workspace_report_catalog()})
                    return
                if path == "/api/views":
                    self.write_json({"views": runtime.workspace_view_catalog()})
                    return
                if path == "/api/views/summary":
                    self.write_json(runtime.workspace_view_summaries())
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
                        self.write_report_preview(render_workspace_report_preview(report))
                    else:
                        self.write_report_reader(render_workspace_report_reader_page(report))
                    return
                raise HttpError(404, "not found")
            except HttpError as exc:
                self.write_error(exc.status, exc.message)
            except CatalogBusyError as exc:
                self.write_error(409, str(exc))
            except Exception as exc:  # noqa: BLE001 - HTTP boundary.
                self.write_error(500, str(exc))

        def do_POST(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            self._workspace_write_lease = None
            try:
                payload = self.read_json_payload()
                if path == "/api/catalog/resolve":
                    self.write_json(
                        {
                            "generation": runtime.catalog.generation,
                            "source_keys": runtime.resolve_keys(source_keys_payload(payload) or []),
                        }
                    )
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
                    resolved = write_workspace_adapter_default_db(
                        store.paths.config_path,
                        adapter_id,
                        raw_db_path,
                    )
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
                if path == "/api/db-sessions":
                    runtime.ensure_ready()
                    self.write_json(db_sessions_payload(store, payload))
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
                        if summary_request.scope == "leaderboard":
                            sheets = [
                                runtime.leaderboard_summary_worksheet(
                                    summary_request.source_keys,
                                    group_by=summary_request.group_by,
                                    statistic=summary_request.statistic,
                                )
                            ]
                        else:
                            sheets = runtime.workspace_view_summary_worksheets(
                                summary_request.views
                            )
                        export = build_summary_serve_export(
                            sheets,
                            runtime.config,
                            scope=summary_request.scope,
                        )
                        self.write_download(
                            export.content,
                            export.content_type,
                            export.filename,
                        )
                        return
                    if export_kind.strip().lower() == "workspace_html":
                        snapshot_request = workspace_snapshot_export_payload(payload)
                        export = build_workspace_snapshot_export(
                            runtime.catalog,
                            store,
                            runtime.workspace_views,
                            runtime.workspace_reports,
                            runtime.config,
                            query=snapshot_request.query,
                            query_view_names=snapshot_request.view_names,
                            selected_source_keys=snapshot_request.selected_source_keys,
                            presentation=snapshot_request.presentation,
                            echarts_js=cached_echarts_asset(store),
                        )
                        self.write_download(
                            export.content,
                            export.content_type,
                            export.filename,
                        )
                        return
                    raw_export_query = payload.get("query")
                    export_query = catalog_query_payload(raw_export_query)
                    view_names = catalog_view_names_payload(raw_export_query)
                    export = build_serve_export(
                        runtime.catalog,
                        store,
                        runtime.config,
                        kind=export_kind,
                        query=export_query,
                        view_queries=runtime.workspace_view_queries(view_names),
                        source_keys=source_keys_payload(payload),
                    )
                    self.write_download(export.content, export.content_type, export.filename)
                    return
                if path == "/api/reports":
                    runtime.ensure_ready()
                    self.require_workspace_writable()
                    source_keys = source_keys_payload(payload) or []
                    report_id = runtime.workspace_reports.import_file(
                        required_string(payload, "path"),
                        source_keys,
                    )
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
                        raise HttpError(400, "source_keys must include at least one source")
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
                        raise HttpError(400, "source_keys must include at least one source")
                    rows = [runtime.catalog.row_for_key(key) for key in source_keys]
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
                                **({"path": item.get("path")} if item.get("path") else {}),
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
                    response = runtime.mutate(
                        "source-import",
                        [],
                        lambda: add_source_result_payload(
                            add_source_payload(store, runtime.config, payload)
                        ),
                    )
                    self.write_json(response)
                    return
                if path == "/api/sources/reload":
                    runtime.ensure_ready()
                    operation = runtime.start_operation("reload", [None], lambda _item: None)
                    self.write_json(operation.to_dict(), status=202)
                    return
                if path == "/api/upload":
                    runtime.ensure_ready()
                    filename = required_string(payload, "filename")
                    content = required_string(payload, "content")
                    adapter = adapter_override_payload(payload)
                    upload_alias = alias_payload(payload)
                    self.write_json(
                        runtime.mutate(
                            "upload",
                            [],
                            lambda: upload_source(
                                store,
                                runtime.config,
                                filename,
                                content,
                                adapter,
                                upload_alias,
                            ),
                        )
                    )
                    return
                if path == "/api/refresh":
                    runtime.ensure_ready()
                    source_keys = source_keys_payload(payload) or []
                    if not source_keys:
                        raise HttpError(400, "source_keys must include at least one source")
                    rows = [runtime.catalog.row_for_key(key) for key in source_keys]
                    operation = runtime.start_operation(
                        "refresh",
                        rows,
                        lambda row: refresh_source_operation(store, runtime.config, row),
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
                            runtime.workspace_reports.replace_bindings(
                                report_id,
                                source_keys_payload(payload) or [],
                            )
                        elif action == "delete":
                            runtime.workspace_reports.delete(report_id)
                        else:
                            raise HttpError(404, "unknown report action")
                    except WorkspaceReportNotFound as exc:
                        raise HttpError(404, str(exc)) from exc
                    self.write_json({"reports": runtime.workspace_report_catalog()})
                    return

                source_action = source_action_path(path)
                if source_action is not None:
                    runtime.ensure_ready()
                    source_key, action = source_action
                    row = runtime.catalog.row_for_key(source_key)
                    if action == "archive":
                        mutate = lambda: store.set_source_active_row(row, False)
                    elif action == "activate":
                        mutate = lambda: store.set_source_active_row(row, True)
                    elif action == "refresh":
                        mutate = lambda: store.refresh_source(row, runtime.config)
                    elif action == "delete":
                        mutate = lambda: store.delete_source_row(row)
                    elif action == "alias":
                        mutate = lambda: store.set_source_alias_row(row, alias_payload(payload))
                    elif action == "tags":
                        mutate = lambda: store.set_source_tags_row(row, tags_payload(payload))
                    elif action == "notes":
                        mutate = lambda: store.save_source_notes_row(
                            row,
                            markdown_payload(payload),
                            runtime.config,
                        )
                    else:
                        raise HttpError(404, "unknown source action")
                    self.write_json(
                        runtime.mutate(action, [source_key], mutate)
                    )
                    return

                raise HttpError(404, "not found")
            except HttpError as exc:
                self.write_error(exc.status, exc.message)
            except CatalogBusyError as exc:
                self.write_error(409, str(exc))
            except Exception as exc:  # noqa: BLE001 - HTTP boundary.
                self.write_error(400, str(exc))
            finally:
                lease = self._workspace_write_lease
                self._workspace_write_lease = None
                if lease is not None:
                    lease.__exit__(None, None, None)

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
                raise HttpError(413, "request body exceeds serve upload limit")
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
            if origin is not None and not self.is_same_origin(origin, origin_header=True):
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
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def write_json(self, payload: Any, status: int = 200) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def write_js(self, data: bytes, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
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
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
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
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def write_error(self, status: int, message: str) -> None:
            if urlsplit(self.path).path.startswith("/api/"):
                self.write_json({"error": message}, status=status)
                return
            self.write_html(f"{status} {message}\n", status=status)

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


def catalog_view_names(raw_query: str) -> tuple[str, ...]:
    values = parse_qs(raw_query, keep_blank_values=True)
    names = [str(value).strip() for value in values.get("view", []) if str(value).strip()]
    return tuple(dict.fromkeys(names))


def catalog_view_names_payload(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, dict):
        raise HttpError(400, "query must be an object")
    raw_names = value.get("views", [])
    if not isinstance(raw_names, list) or any(not isinstance(name, str) for name in raw_names):
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
                result.extend(part.strip() for part in str(raw).split(",") if part.strip())
        return tuple(dict.fromkeys(result))

    try:
        return CatalogQuery(
            state=first("state", "active"),
            page=integer("page", 1),
            page_size=integer("page_size", 100),
            search=first("search", ""),
            sort=first("sort", "last_turn_end"),
            direction=first("direction", "desc"),
            tags=many("tag", "tags"),
            agents=many("agent", "agents"),
            models=many("model", "models"),
            results=many("result", "results"),
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
            tags=tuple(value.get("tags") or ()),
            agents=tuple(value.get("agents") or ()),
            models=tuple(value.get("models") or ()),
            results=tuple(value.get("results") or ()),
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


def upload_source(
    store: ServeStateStore,
    config: ToolConfig,
    filename: str,
    content: str,
    adapter: str | None,
    alias: str | None,
) -> dict[str, Any]:
    keys = store.ingest_upload(
        filename,
        content,
        config,
        adapter=adapter,
        source_alias=alias,
    )
    return {"source_keys": keys}
