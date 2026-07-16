from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import unquote

from peval_py.adapters import available_adapter_ids, normalize_adapter_id
from peval_py.inputs import infer_adapter_from_path, validate_selected_adapter
from peval_py.serve.constants import WINDOWS_DRIVE_MOUNT_ROOT, WINDOWS_DRIVE_PATH_RE
from peval_py.serve.errors import HttpError
from peval_py.session_select import list_adapter_sessions
from peval_py.state import CatalogQuery, ServeStateStore


SUMMARY_GROUP_BY_VALUES = frozenset({"overall", "agent", "model"})
SUMMARY_STATISTIC_VALUES = frozenset(
    {"mean", "min", "q1", "p50", "q3", "p95", "max"}
)


@dataclass(frozen=True)
class SummaryExportPayload:
    scope: str
    source_keys: tuple[str, ...] = ()
    views: tuple[str, ...] = ()
    group_by: str = "agent"
    statistic: str = "mean"


@dataclass(frozen=True)
class WorkspaceSnapshotPresentation:
    summary_group_by: str
    summary_statistic: str
    summary_table_open: bool
    selected_source_key: str | None
    selected_step_id: str | None
    visible_view_names: tuple[str, ...]
    workspace_view_filters: dict[str, tuple[str, ...]]
    open_view_tables: tuple[str, ...]


@dataclass(frozen=True)
class WorkspaceSnapshotExportPayload:
    query: CatalogQuery
    view_names: tuple[str, ...]
    selected_source_keys: tuple[str, ...]
    presentation: WorkspaceSnapshotPresentation


def workspace_snapshot_export_payload(payload: Any) -> WorkspaceSnapshotExportPayload:
    if not isinstance(payload, dict):
        raise HttpError(400, "export payload must be an object")
    if set(payload) != {"kind", "query", "selected_source_keys", "presentation"}:
        raise HttpError(
            400,
            "workspace snapshot fields must be kind, query, selected_source_keys, and presentation",
        )
    query_value = payload.get("query")
    if not isinstance(query_value, dict):
        raise HttpError(400, "query must be an object")
    query_fields = {
        "state", "search", "sort", "direction", "tags", "agents", "models",
        "results", "views",
    }
    if set(query_value) != query_fields:
        raise HttpError(400, "workspace snapshot query fields are invalid")
    try:
        query = CatalogQuery(
            state=_required_text(query_value.get("state"), "query state"),
            page=1,
            page_size=100,
            search=_string_value(query_value.get("search"), "query search"),
            sort=_required_text(query_value.get("sort"), "query sort"),
            direction=_required_text(query_value.get("direction"), "query direction"),
            tags=tuple(_string_array(query_value.get("tags"), "query tags")),
            agents=tuple(_string_array(query_value.get("agents"), "query agents")),
            models=tuple(_string_array(query_value.get("models"), "query models")),
            results=tuple(_string_array(query_value.get("results"), "query results")),
        ).normalized()
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    view_names = tuple(_string_array(query_value.get("views"), "query views"))
    selected = tuple(
        _string_array(payload.get("selected_source_keys"), "selected_source_keys")
    )

    presentation_value = payload.get("presentation")
    if not isinstance(presentation_value, dict):
        raise HttpError(400, "presentation must be an object")
    presentation_fields = {
        "summary_group_by", "summary_statistic", "summary_table_open",
        "selected_source_key", "selected_step_id", "visible_view_names",
        "workspace_view_filters", "open_view_tables",
    }
    if set(presentation_value) != presentation_fields:
        raise HttpError(400, "workspace snapshot presentation fields are invalid")
    group_by = presentation_value.get("summary_group_by")
    statistic = presentation_value.get("summary_statistic")
    if group_by not in SUMMARY_GROUP_BY_VALUES:
        raise HttpError(400, "summary_group_by must be overall, agent, or model")
    if statistic not in SUMMARY_STATISTIC_VALUES:
        raise HttpError(
            400,
            "summary_statistic must be mean, min, q1, p50, q3, p95, or max",
        )
    table_open = presentation_value.get("summary_table_open")
    if not isinstance(table_open, bool):
        raise HttpError(400, "summary_table_open must be true or false")
    selected_source_key = _nullable_text(
        presentation_value.get("selected_source_key"), "selected_source_key"
    )
    raw_step_id = presentation_value.get("selected_step_id")
    if raw_step_id is not None and not isinstance(raw_step_id, (str, int)):
        raise HttpError(400, "selected_step_id must be a string, integer, or null")
    filters = presentation_value.get("workspace_view_filters")
    if not isinstance(filters, dict) or set(filters) != {"tags", "models", "group_by"}:
        raise HttpError(400, "workspace_view_filters fields must be tags, models, and group_by")
    filter_values = {
        key: tuple(_string_array(filters.get(key), f"workspace_view_filters {key}"))
        for key in ("tags", "models", "group_by")
    }
    invalid_groups = [value for value in filter_values["group_by"] if value not in SUMMARY_GROUP_BY_VALUES]
    if invalid_groups:
        raise HttpError(400, "workspace_view_filters group_by values are invalid")
    presentation = WorkspaceSnapshotPresentation(
        summary_group_by=group_by,
        summary_statistic=statistic,
        summary_table_open=table_open,
        selected_source_key=selected_source_key,
        selected_step_id=None if raw_step_id is None else str(raw_step_id),
        visible_view_names=tuple(
            _string_array(presentation_value.get("visible_view_names"), "visible_view_names")
        ),
        workspace_view_filters=filter_values,
        open_view_tables=tuple(
            _string_array(presentation_value.get("open_view_tables"), "open_view_tables")
        ),
    )
    return WorkspaceSnapshotExportPayload(
        query=query,
        view_names=view_names,
        selected_source_keys=selected,
        presentation=presentation,
    )


def _string_array(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise HttpError(400, f"{field} must be a string array")
    return list(dict.fromkeys(item.strip() for item in value if item.strip()))


def _string_value(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise HttpError(400, f"{field} must be a string")
    return value


def _required_text(value: Any, field: str) -> str:
    text = _string_value(value, field).strip()
    if not text:
        raise HttpError(400, f"{field} must be a non-empty string")
    return text


def _nullable_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field)


def summary_export_payload(value: Any) -> SummaryExportPayload:
    if not isinstance(value, dict):
        raise HttpError(400, "summary must be an object")
    scope = value.get("scope")
    if scope == "leaderboard":
        expected = {"scope", "source_keys", "group_by", "statistic"}
        if set(value) != expected:
            raise HttpError(
                400,
                "leaderboard summary fields must be scope, source_keys, group_by, and statistic",
            )
        group_by = value.get("group_by")
        statistic = value.get("statistic")
        if group_by not in SUMMARY_GROUP_BY_VALUES:
            raise HttpError(400, "group_by must be overall, agent, or model")
        if statistic not in SUMMARY_STATISTIC_VALUES:
            raise HttpError(
                400,
                "statistic must be mean, min, q1, p50, q3, p95, or max",
            )
        return SummaryExportPayload(
            scope=scope,
            source_keys=tuple(
                _ordered_string_values(value.get("source_keys"), "source_keys")
            ),
            group_by=group_by,
            statistic=statistic,
        )
    if scope == "saved_views":
        if set(value) != {"scope", "views"}:
            raise HttpError(400, "saved views summary fields must be scope and views")
        return SummaryExportPayload(
            scope=scope,
            views=tuple(_ordered_string_values(value.get("views"), "views")),
        )
    raise HttpError(400, "summary scope must be leaderboard or saved_views")


def _ordered_string_values(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise HttpError(400, f"{field} must include at least one value")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise HttpError(400, f"{field} must be a non-empty string array")
    return list(dict.fromkeys(value))

def adapter_default_db_payload(payload: dict[str, Any]) -> tuple[str, str | None]:
    adapter_id = validate_selected_adapter(
        normalize_adapter_id(required_string(payload, "adapter")),
        set(available_adapter_ids()),
        "adapter default DB",
    )
    return adapter_id, optional_string(payload.get("default_db_path"))


def adapter_for_db_inspect(path: str, raw_adapter: str | None) -> tuple[str, bool]:
    available = set(available_adapter_ids())
    if raw_adapter:
        return validate_selected_adapter(
            normalize_adapter_id(raw_adapter),
            available,
            "DB session inspect",
        ), False
    adapter_id = infer_adapter_from_path(path, available)
    if adapter_id is None:
        options = ", ".join(sorted(available)) or "<none>"
        raise HttpError(
            400,
            f"could not infer adapter for {path}; choose adapter "
            f"(available adapters: {options})",
        )
    return adapter_id, True


def source_args_from_payload(
    store: ServeStateStore,
    payload: dict[str, Any],
) -> SimpleNamespace:
    paths = source_path_values(store, payload, "path")
    dbs = source_path_values(store, payload, "db")
    input_table = optional_string(payload.get("input_table"))
    present = [value for value in [paths, dbs, input_table] if value]
    if len(present) != 1:
        raise HttpError(400, "provide exactly one source: path, db, or input_table")
    session_id = optional_string(payload.get("session_id"))
    session_ids = session_ids_payload(payload)
    if session_id and session_ids:
        raise HttpError(400, "provide either session_id or session_ids, not both")
    if (session_id or session_ids) and not dbs:
        raise HttpError(400, "session_id and session_ids are only valid with db sources")
    if (session_id or session_ids) and len(dbs) != 1:
        raise HttpError(400, "session_id and session_ids require exactly one db source")
    return SimpleNamespace(
        path=paths or None,
        db=dbs or None,
        input_table=[workspace_relative_path(store, input_table)] if input_table else None,
        session_id=([session_id] if session_id and dbs else session_ids if dbs else None),
        adapter=[],
        note=[],
    )


def source_path_values(
    store: ServeStateStore,
    payload: dict[str, Any],
    key: str,
) -> list[str]:
    raw = optional_string(payload.get(key))
    if raw is None:
        return []
    parts = split_source_path_lines(raw) if key == "path" else split_source_path_list(raw, key)
    if not parts:
        raise HttpError(400, f"{key} path list is empty")
    return [workspace_relative_path(store, part) for part in parts]


def split_source_path_lines(raw: str) -> list[str]:
    return [
        unquote_path_token(line)
        for line in str(raw).splitlines()
        if unquote_path_token(line)
    ]


def split_source_path_list(raw: str, key: str) -> list[str]:
    try:
        raw_parts = shlex.split(raw, posix=False)
    except ValueError as exc:
        raise HttpError(400, f"{key} path list is invalid: {exc}") from exc
    return [
        unquote_path_token(part)
        for part in raw_parts
        if unquote_path_token(part)
    ]


def unquote_path_token(raw: object) -> str:
    text = str(raw).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    return text


def adapter_override_payload(payload: dict[str, Any]) -> str | None:
    adapter = optional_string(payload.get("adapter"))
    if adapter is None or adapter.lower() == "auto":
        return None
    return adapter


def session_ids_payload(payload: dict[str, Any]) -> list[str] | None:
    raw = payload.get("session_ids")
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise HttpError(400, "session_ids must be an array")
    session_ids: list[str] = []
    for value in raw:
        text = optional_string(value)
        if text is not None:
            session_ids.append(text)
    if not session_ids:
        raise HttpError(400, "session_ids must include at least one session id")
    return session_ids


def workspace_relative_path(
    store: ServeStateStore,
    raw_path: str | None,
    *,
    windows_mount_root: Path | None = None,
) -> str | None:
    if raw_path is None:
        return None
    text = unquote_path_token(raw_path)
    if not text:
        return None
    if is_windows_absolute_like_path(text):
        return resolve_windows_absolute_like_path(text, windows_mount_root)
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = store.paths.root / path
    return str(path)


def is_windows_absolute_like_path(path: str) -> bool:
    return bool(WINDOWS_DRIVE_PATH_RE.match(path)) or path.startswith("\\\\") or path.startswith("//")


def resolve_windows_absolute_like_path(
    raw_path: str,
    windows_mount_root: Path | None = None,
) -> str:
    if os.name == "nt":
        return str(Path(raw_path).expanduser())
    original = Path(raw_path).expanduser()
    if original.exists():
        return str(original)
    mapped = windows_drive_mount_path(
        raw_path,
        windows_mount_root or patched_windows_drive_mount_root(),
    )
    if mapped is not None and mapped.exists():
        return str(mapped)
    return raw_path


def patched_windows_drive_mount_root() -> Path:
    try:
        from peval_py import serve as serve_facade

        return Path(getattr(serve_facade, "WINDOWS_DRIVE_MOUNT_ROOT"))
    except Exception:  # noqa: BLE001 - optional patch compatibility only.
        return WINDOWS_DRIVE_MOUNT_ROOT


def windows_drive_mount_path(raw_path: str, mount_root: Path) -> Path | None:
    if not WINDOWS_DRIVE_PATH_RE.match(raw_path):
        return None
    drive = raw_path[0].lower()
    rest = raw_path[2:].lstrip("\\/")
    parts = [part for part in re.split(r"[\\/]+", rest) if part]
    return Path(mount_root) / drive / Path(*parts)


def source_keys_payload(payload: dict[str, Any]) -> list[str] | None:
    raw_keys = payload.get("source_keys")
    if raw_keys is None and payload.get("source_key") is not None:
        raw_keys = [payload["source_key"]]
    if raw_keys is None:
        return None
    if not isinstance(raw_keys, list):
        raise HttpError(400, "source_keys must be an array")
    return [str(key) for key in raw_keys]


def required_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise HttpError(400, f"{key} must be true or false")
    return value


def source_state_payload(
    value: Any,
    *,
    default: str = "active",
    field: str = "source_state",
    allow_all: bool = False,
) -> str:
    text = str(value if value is not None else default).strip().lower()
    if not text:
        text = default
    allowed = {"active", "archived", "all"} if allow_all else {"active", "archived"}
    if text not in allowed:
        expected = "active, archived, or all" if allow_all else "active or archived"
        raise HttpError(400, f"{field} must be {expected}")
    return text


def source_action_path(path: str) -> tuple[str, str] | None:
    prefix = "/api/sources/"
    if not path.startswith(prefix):
        return None
    parts = path[len(prefix) :].split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise HttpError(404, "unknown source action")
    return unquote(parts[0]), parts[1]


def required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise HttpError(400, f"{key} is required")
    return value


def markdown_payload(payload: dict[str, Any]) -> str:
    value = payload.get("markdown")
    if not isinstance(value, str):
        raise HttpError(400, "markdown is required")
    return value


def alias_payload(payload: dict[str, Any]) -> str | None:
    value = payload.get("alias")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def tags_payload(payload: dict[str, Any]) -> list[str]:
    value = payload.get("tags", payload.get("source_tags"))
    if isinstance(value, list):
        parts = [str(item).strip() for item in value]
    else:
        parts = re.split(r"[,，]", str(value or ""))
    tags: list[str] = []
    seen: set[str] = set()
    for part in parts:
        tag = part.strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)
    return tags


def optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
