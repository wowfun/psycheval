from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import islice
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


def evaluation_report_query(raw_query: str) -> tuple[int, int, str]:
    values = parse_qs(raw_query, keep_blank_values=True)

    def integer(key: str, default: int) -> int:
        raw = values.get(key)
        value = str(raw[0]) if raw else str(default)
        try:
            return int(value)
        except ValueError as exc:
            raise HttpError(400, f"{key} must be an integer") from exc

    return (
        integer("page", 1),
        integer("page_size", 100),
        str((values.get("search") or [""])[0]),
    )


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
            {
                "id": dataset.id,
                "path": dataset.path,
                "format": dataset.format,
                "allow_partial": dataset.allow_partial,
            }
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
            allow_partial=payload.get("allow_partial", False),
        )
    elif action == "update":
        config = library.update_dataset(
            dataset_id=required_string(payload, "dataset_id"),
            new_id=required_string(payload, "new_id"),
            path=required_string(payload, "path"),
            mount_ids=harbor_id_list_payload(payload, "mount_ids", allow_empty=True),
            expected_revision=expected_revision,
            allow_partial=payload.get("allow_partial"),
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


@dataclass(frozen=True)
class _ResolvedAcpContext:
    item_id: str
    label: str
    uri: str
    reference: dict[str, Any]
    identity: dict[str, Any]
    optional: dict[str, Any]
    omission: str


def acp_context_items(
    store: ServeStateStore | None,
    runtime: ServeRuntime,
    raw_contexts: list[Any],
    *,
    embedded_context: bool,
) -> list[dict[str, Any]]:
    resolved = [
        _resolve_acp_context(store, runtime, raw_context)
        for raw_context in raw_contexts
    ]
    limit = max(1, runtime.config.max_content_chars)
    minimums = [
        _acp_rendered_length(item, embedded_context=embedded_context)
        for item in resolved
    ]
    if sum(minimums) > limit:
        raise HttpError(
            413,
            "ACP context budget is too small to preserve all selected identities",
        )
    remaining = limit
    items: list[dict[str, Any]] = []
    for index, item in enumerate(resolved):
        future_minimum = sum(minimums[index + 1 :])
        count = len(resolved) - index
        fair_share = max(minimums[index], remaining // count)
        item_limit = min(fair_share, remaining - future_minimum)
        rendered = _render_acp_context(
            item,
            limit=item_limit,
            embedded_context=embedded_context,
        )
        remaining -= _acp_item_text_length(rendered)
        items.append(rendered)
    return items


def _resolve_acp_context(
    store: ServeStateStore | None,
    runtime: ServeRuntime,
    raw_context: Any,
) -> _ResolvedAcpContext:
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
            detail = runtime.detail(source_key).to_dict()
        except ValueError as exc:
            raise HttpError(400, str(exc)) from exc
        report = detail.get("report") if isinstance(detail.get("report"), dict) else {}
        trajectories = (
            report.get("trajectory")
            if isinstance(report.get("trajectory"), list)
            else []
        )
        metas = (
            report.get("trajectory_meta")
            if isinstance(report.get("trajectory_meta"), list)
            else []
        )
        trajectory = (
            trajectories[0]
            if trajectories and isinstance(trajectories[0], dict)
            else {}
        )
        meta = metas[0] if metas and isinstance(metas[0], dict) else {}
        if step_id is not None:
            steps = (
                trajectory.get("steps")
                if isinstance(trajectory.get("steps"), list)
                else []
            )
            selected_steps = [
                step
                for step in steps
                if isinstance(step, dict) and str(step.get("step_id")) == step_id
            ]
            if not selected_steps:
                raise HttpError(400, f"unknown ATIF step_id for source: {step_id}")
            trajectory = {**trajectory, "steps": selected_steps}
        row = runtime.catalog.row_for_key(source_key)
        source_ref = str(row.get("source_ref") or row.get("artifact_dir") or "")
        try:
            evaluation_report = runtime.evaluation_reports.read(source_ref)
        except ValueError as exc:
            raise HttpError(400, str(exc)) from exc
        trial_ref = (
            source_ref.split("/steps/", 1)[0]
            if source_ref.startswith("harbor/")
            else source_ref
        )
        phase = (
            source_ref.rsplit("/", 1)[-1]
            if source_ref.startswith("harbor/") and "/steps/" in source_ref
            else None
        )
        live_task_metadata = meta.get("task_metadata")
        task_metadata = (
            live_task_metadata
            if isinstance(live_task_metadata, dict)
            else row.get("task_metadata")
            if isinstance(row.get("task_metadata"), dict)
            else {}
        )
        live_provenance = meta.get("harbor_provenance")
        provenance = (
            live_provenance
            if isinstance(live_provenance, dict)
            else row.get("harbor_provenance")
            if isinstance(row.get("harbor_provenance"), dict)
            else {}
        )
        live_status = meta.get("status")
        live_score = meta.get("score")
        live_rewards = meta.get("rewards")
        identity = {
            "source_ref": source_ref,
            "trial_ref": trial_ref,
            "phase": phase,
            "task": {
                key: value
                for key, value in {
                    "name": meta.get("task_name") or row.get("task_name"),
                    "status": task_metadata.get("status"),
                    "recorded_digest": provenance.get("task_digest"),
                    "recorded_digest_source": provenance.get("task_digest_source"),
                    "live_digest": task_metadata.get("live_digest"),
                    "digest_matches": task_metadata.get("digest_matches"),
                    "digest_comparison": task_metadata.get("digest_comparison"),
                }.items()
                if value is not None
            },
            "outcome": {
                key: value
                for key, value in {
                    "status": live_status
                    or row.get("status")
                    or row.get("last_status"),
                    "score": live_score if live_score is not None else row.get("score"),
                    "rewards": live_rewards
                    if isinstance(live_rewards, dict)
                    else row.get("rewards"),
                    "failure_class": meta.get("failure_class"),
                    "exception": meta.get("exception"),
                    "diagnostic": row.get("last_error"),
                }.items()
                if value is not None
            },
            "evaluation_report": {
                "present": evaluation_report is not None,
                **(
                    {"report_ref": evaluation_report.report_ref}
                    if evaluation_report is not None
                    else {}
                ),
            },
            "omissions": [],
        }
        context_payload = {
            "trajectory": trajectory,
            "meta": {
                key: value
                for key, value in meta.items()
                if key not in {"data_ref"} and value is not None
            },
            **(
                {
                    "evaluation_report": {
                        "report_ref": evaluation_report.report_ref,
                        "content": evaluation_report.content,
                    }
                }
                if evaluation_report is not None
                else {}
            ),
            **({"step_filter": step_id} if step_id is not None else {}),
        }
        reference = {
            "kind": kind,
            "source_key": source_key,
            **({"step_id": step_id} if step_id is not None else {}),
        }
        item_id = f"source:{source_key}:{step_id or ''}"
        label = f"{source_key} · Step {step_id}" if step_id else source_key
        uri = f"peval://source/{quote(source_key, safe='')}"
        omission = (
            "trajectory evidence was compacted to fit the shared ACP context budget"
        )
    elif kind == "dataset_task":
        _require_acp_context_keys(raw_context, {"kind", "dataset_id", "task"})
        dataset_id = _bounded_acp_context_field(raw_context, "dataset_id")
        task = _bounded_acp_context_field(raw_context, "task")
        if store is None:
            raise HttpError(500, "workspace state is unavailable")
        context_payload = harbor_workspace(store, runtime).task_detail(dataset_id, task)
        identity = {
            "dataset_id": dataset_id,
            "task": task,
            "revision": context_payload.get("revision"),
            "omissions": [],
        }
        reference = {"kind": kind, "dataset_id": dataset_id, "task": task}
        item_id = f"dataset:{dataset_id}:{task}"
        label = f"{dataset_id} / {task}"
        uri = f"peval://dataset/{quote(dataset_id, safe='')}/{quote(task, safe='')}"
        omission = "Task detail was compacted to fit the shared ACP context budget"
    elif kind == "report":
        _require_acp_context_keys(raw_context, {"kind", "report_ref"})
        report_ref = _bounded_acp_context_field(raw_context, "report_ref")
        try:
            report = runtime.report_library.read(report_ref)
        except ValueError as exc:
            raise HttpError(404, str(exc)) from exc
        identity = {
            "report_ref": report.report_ref,
            "title": report.title,
            "filename": report.filename,
            "format": report.format,
            "source_keys": list(report.source_keys),
            "omissions": [],
        }
        context_payload = {"content": report.content.decode("utf-8")}
        reference = {"kind": kind, "report_ref": report_ref}
        item_id = f"report:{report_ref}"
        label = report.title or report.filename or report_ref
        uri = f"peval://report/{quote(report_ref, safe='')}"
        omission = "report content was compacted to fit the shared ACP context budget"
    else:
        raise HttpError(400, "ACP context kind must be source, dataset_task, or report")
    return _ResolvedAcpContext(
        item_id=item_id,
        label=label,
        uri=uri,
        reference=reference,
        identity=identity,
        optional=context_payload,
        omission=omission,
    )


def _render_acp_context(
    item: _ResolvedAcpContext,
    *,
    limit: int,
    embedded_context: bool,
) -> dict[str, Any]:
    prefix = (
        "" if embedded_context else f"Psycheval evaluation context ({item.label}):\n"
    )
    serialized_limit = limit - len(prefix)
    value = {**item.identity, "evidence": item.optional}
    serialized = _acp_json(item.reference, value)
    if len(serialized) > serialized_limit:
        best = None
        for list_limit in (32, 16, 8, 4, 2, 1, 0):
            low, high = 0, max(0, serialized_limit)
            while low <= high:
                string_limit = (low + high) // 2
                compacted = _compact_acp_value(
                    item.optional,
                    string_limit=string_limit,
                    list_limit=list_limit,
                )
                candidate_value = {
                    **item.identity,
                    "omissions": [item.omission],
                    "evidence": compacted,
                }
                candidate = _acp_json(item.reference, candidate_value)
                if len(candidate) <= serialized_limit:
                    best = candidate
                    low = string_limit + 1
                else:
                    high = string_limit - 1
            if best is not None:
                break
        serialized = best or _acp_json(
            item.reference,
            {**item.identity, "omissions": [item.omission]},
        )
    if embedded_context:
        block: dict[str, Any] = {
            "type": "resource",
            "resource": {
                "uri": item.uri,
                "mimeType": "application/json",
                "text": serialized,
            },
        }
    else:
        block = {"type": "text", "text": prefix + serialized}
    return {"id": item.item_id, "label": item.label, "content": [block]}


def _acp_rendered_length(
    item: _ResolvedAcpContext,
    *,
    embedded_context: bool,
) -> int:
    prefix = (
        "" if embedded_context else f"Psycheval evaluation context ({item.label}):\n"
    )
    return len(prefix) + len(
        _acp_json(item.reference, {**item.identity, "omissions": [item.omission]})
    )


def _acp_item_text_length(item: dict[str, Any]) -> int:
    block = item["content"][0]
    if block["type"] == "resource":
        return len(block["resource"]["text"])
    return len(block["text"])


def _acp_json(reference: dict[str, Any], value: dict[str, Any]) -> str:
    return json.dumps(
        {"reference": reference, "value": value},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _compact_acp_value(
    value: Any,
    *,
    string_limit: int,
    list_limit: int,
) -> Any:
    if isinstance(value, str):
        return value if len(value) <= string_limit else value[:string_limit]
    if isinstance(value, list):
        return [
            _compact_acp_value(
                item,
                string_limit=string_limit,
                list_limit=list_limit,
            )
            for item in value[:list_limit]
        ]
    if isinstance(value, dict):
        return {
            str(key): _compact_acp_value(
                item,
                string_limit=string_limit,
                list_limit=list_limit,
            )
            for key, item in islice(value.items(), 32)
        }
    return value


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
                        {
                            "id": dataset.id,
                            "path": dataset.path,
                            "format": dataset.format,
                        }
                        for dataset in datasets
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
