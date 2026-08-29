from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote

from psycheval.config import (
    HarborMount,
    ToolConfig,
    apply_toml_config,
    unique_harbor_id_from_path,
    validate_harbor_mount_paths,
    write_workspace_harbor_mounts,
)
from psycheval.serve.errors import HttpError
from psycheval.serve.harbor_workspace import (
    HarborConflictError,
    HarborNotFoundError,
    HarborSizeError,
    HarborWorkspace,
    HarborWorkspaceError,
    config_revision,
)
from psycheval.serve.payloads import (
    required_string,
)
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import (
    CatalogQuery,
    ServeStateStore,
)
from psycheval.state.workspace_sources import WorkspaceSources, is_harbor_source

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
    payload["locale"] = config.locale
    payload["adapter_defaults"] = dict(config.adapter_default_db_paths)
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
    proposed_config = runtime.config.validated_update(harbor_mounts=mounts)
    WorkspaceSources(store, proposed_config).source_keys()
    saved_mounts = write_workspace_harbor_mounts(store.paths.config_path, mounts)
    runtime.set_config(runtime.config.validated_update(harbor_mounts=saved_mounts))
    return workspace_config_payload(store, runtime)


def acp_context_item(
    store: ServeStateStore | None,
    runtime: ServeRuntime,
    raw_context: Any,
    *,
    embedded_context: bool,
) -> dict[str, Any]:
    if not isinstance(raw_context, dict):
        raise HttpError(400, "ACP context must be an object")
    kind = _bounded_acp_context_field(raw_context, "kind", maximum=32)
    if kind == "source":
        _require_acp_context_keys(raw_context, {"kind", "source_key", "step_id"})
        source_key = _bounded_acp_context_field(raw_context, "source_key")
        step_id = raw_context.get("step_id")
        if step_id is not None:
            if not isinstance(step_id, str) or not step_id or len(step_id) > 128:
                raise HttpError(400, "step_id must be a non-empty bounded string")
        try:
            context_payload: Any = runtime.detail(source_key).to_dict()
        except ValueError as exc:
            raise HttpError(400, str(exc)) from exc
        reference = {
            "kind": kind,
            "source_key": source_key,
            **({"step_id": step_id} if step_id is not None else {}),
        }
        item_id = f"source:{source_key}:{step_id or ''}"
        label = f"{source_key} · Step {step_id}" if step_id else source_key
        uri = f"peval://source/{quote(source_key, safe='')}"
    elif kind == "dataset_task":
        _require_acp_context_keys(raw_context, {"kind", "dataset_id", "task"})
        dataset_id = _bounded_acp_context_field(raw_context, "dataset_id")
        task = _bounded_acp_context_field(raw_context, "task")
        if store is None:
            raise HttpError(500, "workspace state is unavailable")
        context_payload = harbor_workspace(store, runtime).task_detail(dataset_id, task)
        reference = {"kind": kind, "dataset_id": dataset_id, "task": task}
        item_id = f"dataset:{dataset_id}:{task}"
        label = f"{dataset_id} / {task}"
        uri = f"peval://dataset/{quote(dataset_id, safe='')}/{quote(task, safe='')}"
    elif kind == "report":
        _require_acp_context_keys(raw_context, {"kind", "report_id"})
        report_id = _bounded_acp_context_field(raw_context, "report_id")
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
        item_id = f"report:{report_id}"
        label = report.filename or report_id
        uri = f"peval://report/{quote(report_id, safe='')}"
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
    if embedded_context:
        block: dict[str, Any] = {
            "type": "resource",
            "resource": {
                "uri": uri,
                "mimeType": mime_type,
                "text": serialized,
            },
        }
    else:
        prefix = f"Psycheval evaluation context ({label}):\n"
        available = max(0, limit - len(prefix))
        text = prefix[:limit] + serialized[:available]
        block = {"type": "text", "text": text[:limit]}
    return {"id": item_id, "label": label, "content": [block]}


def _bounded_acp_context_field(
    payload: dict[str, Any], key: str, *, maximum: int = 512
) -> str:
    value = required_string(payload, key)
    if len(value) > maximum:
        raise HttpError(400, f"{key} exceeds {maximum} characters")
    return value


def _require_acp_context_keys(payload: dict[str, Any], allowed: set[str]) -> None:
    unexpected = sorted(payload.keys() - allowed)
    if unexpected:
        raise HttpError(400, f"unexpected ACP context fields: {', '.join(unexpected)}")


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
