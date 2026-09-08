from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from psycheval.adapters import adapter_for, available_adapter_ids
from psycheval.config import ToolConfig
from psycheval.inputs import (
    AdapterAssignments,
    LoadedInputs,
    LoadedSession,
    adapter_for_input_path,
    load_inputs,
    parse_adapter_assignments,
    remap_session_selectors,
)
from psycheval.serve.errors import HttpError
from psycheval.serve.payloads import (
    adapter_for_session_inspect,
    adapter_override_payload,
    optional_string,
    source_args_from_payload,
    split_source_path_lines,
)
from psycheval.session_select import inspect_adapter_sessions
from psycheval.state import (
    ServeStateStore,
    discover_complete_trial_cell_dirs,
    loaded_trial_cell_import_session,
)


@dataclass(frozen=True)
class AddSourceResult:
    keys: list[str]
    import_results: list[dict[str, Any]] | None = None


def load_serve_inputs(
    args: Any,
    adapter_assignments: AdapterAssignments,
    config: ToolConfig | None = None,
) -> LoadedInputs:
    return load_inputs(args, adapter_assignments, require_sources=False, config=config)


def add_source_payload(
    store: ServeStateStore,
    config: ToolConfig,
    payload: dict[str, Any],
) -> AddSourceResult:
    path_lines = path_batch_lines(payload)
    if len(path_lines) > 1:
        if payload.get("session_id") or payload.get("session_ids"):
            raise HttpError(
                400,
                "multiple paths require exactly one source; session_id and "
                "session_ids cannot select across them",
            )
        if payload.get("db"):
            raise HttpError(400, "provide exactly one source: path or db")
        return add_path_batch_sources(store, config, payload, path_lines)
    source_args = source_args_from_payload(store, payload)
    assignments = source_adapter_assignments(payload, config)
    loaded = load_payload_sources(source_args, assignments, config)
    loaded = apply_payload_alias(loaded, optional_string(payload.get("alias")))
    keys = store.import_loaded_sources(loaded, config)
    return AddSourceResult(keys=keys)


def path_batch_lines(payload: dict[str, Any]) -> list[str]:
    raw = optional_string(payload.get("path"))
    if raw is None:
        return []
    return split_source_path_lines(raw)


def add_path_batch_sources(
    store: ServeStateStore,
    config: ToolConfig,
    payload: dict[str, Any],
    path_lines: list[str],
) -> AddSourceResult:
    assignments = source_adapter_assignments(payload, config)
    all_keys: list[str] = []
    results: list[dict[str, Any]] = []
    for line in path_lines:
        try:
            source_args = source_args_from_payload(store, {**payload, "path": line})
            loaded = load_payload_sources(source_args, assignments, config)
            loaded = apply_payload_alias(loaded, optional_string(payload.get("alias")))
            keys = store.import_loaded_sources(loaded, config)
            all_keys.extend(keys)
            results.append({"path": line, "status": "ok", "source_keys": keys})
        except Exception as exc:  # noqa: BLE001 - per-line batch result.
            results.append({"path": line, "status": "error", "error": str(exc)})
    return AddSourceResult(keys=all_keys, import_results=results)


def source_adapter_assignments(
    payload: dict[str, Any],
    config: ToolConfig,
) -> AdapterAssignments:
    raw_adapter = adapter_override_payload(payload)
    assignments = parse_adapter_assignments(
        [raw_adapter] if raw_adapter else [],
        config.adapter,
    )
    if raw_adapter:
        return assignments
    return replace(assignments, require_inferred_default=True)


def load_payload_sources(
    source_args: SimpleNamespace,
    assignments: AdapterAssignments,
    config: ToolConfig,
) -> LoadedInputs:
    if not source_args.path:
        return load_serve_inputs(source_args, assignments, config)
    path_values = list(source_args.path)
    recursive_by_index: dict[int, list[LoadedSession]] = {}
    ordinary_paths: list[tuple[int, str]] = []
    available = set(available_adapter_ids())
    for index, path in enumerate(path_values, start=1):
        recursive_sessions = recursive_trial_cell_sessions(path, config)
        if recursive_sessions:
            if source_args.session_id:
                raise HttpError(
                    400, "session selection requires an adapter session directory"
                )
            recursive_by_index[index] = recursive_sessions
            continue
        if Path(path).is_dir():
            adapter_id = adapter_for_input_path(
                path, index, assignments, "path", available
            )
            if not callable(
                getattr(adapter_for(adapter_id), "resolve_session_path", None)
            ):
                raise HttpError(
                    400,
                    f"adapter {adapter_id} does not support session directories: {path}",
                )
        ordinary_paths.append((index, path))
    ordinary_loaded = LoadedInputs(sessions=[], notes=[])
    if ordinary_paths:
        ordinary_loaded = load_serve_inputs(
            SimpleNamespace(
                **{
                    **vars(source_args),
                    "path": [path for _, path in ordinary_paths],
                    "session_id": remap_session_selectors(
                        source_args.session_id or [],
                        [index for index, _ in ordinary_paths],
                    ),
                }
            ),
            remap_path_assignments(assignments, [index for index, _ in ordinary_paths]),
            config,
        )
    ordinary_groups: dict[int, list[LoadedSession]] = {}
    for session in ordinary_loaded.sessions:
        selector = session.input_selector or ""
        if selector.startswith("p"):
            original = ordinary_paths[int(selector[1:]) - 1][0]
            ordinary_groups.setdefault(original, []).append(session)
    ordered_sessions: list[LoadedSession] = []
    for index, _path in enumerate(path_values, start=1):
        if index in recursive_by_index:
            ordered_sessions.extend(recursive_by_index[index])
        else:
            ordered_sessions.extend(ordinary_groups.get(index, []))
    return LoadedInputs(sessions=ordered_sessions, notes=ordinary_loaded.notes)


def recursive_trial_cell_sessions(
    raw_path: str,
    config: ToolConfig,
) -> list[LoadedSession]:
    path = Path(raw_path).expanduser()
    cells = discover_complete_trial_cell_dirs(path)
    if not cells:
        return []
    return [
        replace(
            loaded_trial_cell_import_session(cell, config),
            artifact_eval_slug=config.analysis_eval_slug,
        )
        for cell in cells
    ]


def remap_path_assignments(
    assignments: AdapterAssignments,
    original_indexes: list[int],
) -> AdapterAssignments:
    remapped = {
        next_index: assignments.path_adapters[original_index]
        for next_index, original_index in enumerate(original_indexes, start=1)
        if original_index in assignments.path_adapters
    }
    return AdapterAssignments(
        assignments.default_adapter,
        remapped,
        assignments.db_adapters,
        assignments.default_explicit,
        assignments.require_inferred_default,
    )


def apply_payload_alias(loaded: LoadedInputs, alias: str | None) -> LoadedInputs:
    if alias is None:
        return loaded
    return LoadedInputs(
        sessions=[replace(session, source_alias=alias) for session in loaded.sessions],
        notes=loaded.notes,
    )


def sessions_payload(
    store: ServeStateStore,
    payload: dict[str, Any],
    config: ToolConfig,
) -> dict[str, Any]:
    source_args = source_args_from_payload(store, payload)
    kind = "db" if payload.get("db") else "path"
    paths = getattr(source_args, kind) or []
    if not paths and source_args.session_id:
        loaded = load_serve_inputs(
            source_args, source_adapter_assignments(payload, config), config
        )
        paths = [session.input_path for session in loaded.sessions]
    if len(paths) != 1:
        raise HttpError(400, "Session Inspect requires exactly one source path")
    path = Path(paths[0])
    if not (path.is_file() if kind == "db" else path.is_dir() or path.is_file()):
        raise HttpError(
            400,
            f"{'DB path' if kind == 'db' else 'Session path'} does not exist or has the wrong type: {path}",
        )
    raw_adapter = adapter_override_payload(payload)
    adapter_id, inferred = adapter_for_session_inspect(str(path), raw_adapter)
    if kind == "path" and not callable(
        getattr(adapter_for(adapter_id), "resolve_session_path", None)
    ):
        raise HttpError(
            400, f"adapter {adapter_id} does not support session directories"
        )
    listing = inspect_adapter_sessions(adapter_id, str(path))
    return {
        kind: str(path),
        "adapter": adapter_id,
        "inferred": inferred,
        "selection_required": kind == "db" or path.is_dir(),
        "warnings": listing.warnings,
        "sessions": [
            {
                "index": index,
                "session_id": session.session_id,
                "name": session.name,
                "updated_at_ms": session.updated_at_ms,
            }
            for index, session in enumerate(listing.sessions, start=1)
        ],
    }
