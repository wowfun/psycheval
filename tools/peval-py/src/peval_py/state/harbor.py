from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from peval_py._state.annotations import optional_str
from peval_py._state.artifacts import (
    artifact_segment,
    read_json_object,
    relative_to_root,
    remove_artifact_dir,
    source_key_for_components,
    trial_artifacts,
    trial_cell_dir,
    write_files_atomically,
    write_json_files_atomically,
)
from peval_py.atif import validate_atif_trajectory
from peval_py.config import ToolConfig
from peval_py.report import project_meta_from_atif
from peval_py.state.constants import (
    HARBOR_LINK_FILENAME,
    HARBOR_LINK_SCHEMA_VERSION,
    SOURCE_STATE_DIR,
    SOURCE_STATUS_MISSING,
    SOURCE_STATUS_OK,
)
from peval_py.state.summaries import now_ms

HARBOR_SOURCE_KIND = "harbor-trial"
HARBOR_ROOT_DIAGNOSTIC_KIND = "harbor-root"
HARBOR_ADAPTER = "harbor"
HARBOR_SOURCE_FILES = (
    "agent/trajectory.json",
    "config.json",
    "lock.json",
    "result.json",
)


@dataclass(frozen=True)
class HarborTrialCandidate:
    trial_dir: Path
    mount_id: str
    relative_path: str
    source_key: str
    trial_key: str
    multi_step: bool


@dataclass(frozen=True)
class HarborDiscoveryResult:
    trials: tuple[HarborTrialCandidate, ...]
    missing_roots: tuple[str, ...]


def discover_harbor_trials(
    workspace_root: Path,
    configured_roots: Iterable[str] = (),
) -> HarborDiscoveryResult:
    """Discover Harbor single- and multi-step Trial roots without recursion."""

    workspace = workspace_root.expanduser().resolve()
    roots: list[tuple[Path, bool]] = [
        (workspace, False),
        (workspace / "jobs", False),
    ]
    roots.extend(
        (Path(os.path.abspath(Path(value).expanduser())), True)
        for value in configured_roots
    )
    ordered_roots: list[tuple[Path, bool]] = []
    seen_roots: set[Path] = set()
    for root, configured in roots:
        if root not in seen_roots:
            ordered_roots.append((root, configured))
            seen_roots.add(root)

    found: dict[Path, HarborTrialCandidate] = {}
    missing: list[str] = []
    for lexical_root, configured in ordered_roots:
        if _path_has_symlink(lexical_root) or not lexical_root.is_dir():
            if configured:
                missing.append(str(lexical_root))
            continue
        root = lexical_root.resolve()
        if not root.is_dir():
            if configured:
                missing.append(str(root))
            continue
        for trial_dir in _trial_dirs_for_root(root):
            resolved = trial_dir.resolve()
            if resolved in found:
                continue
            mount_id, relative_path = _source_location(workspace, root, resolved)
            identity = {
                "kind": HARBOR_SOURCE_KIND,
                "mount_id": mount_id,
                "relative_path": relative_path,
            }
            identity_hash = hashlib.sha256(
                json.dumps(identity, sort_keys=True).encode("utf-8")
            ).hexdigest()
            source_key = source_key_for_components(identity)
            leaf = artifact_segment(resolved.name, "trial")[:48]
            found[resolved] = HarborTrialCandidate(
                trial_dir=resolved,
                mount_id=mount_id,
                relative_path=relative_path,
                source_key=source_key,
                trial_key=f"harbor-{leaf}-{identity_hash[:10]}",
                multi_step=_is_multi_step_trial(resolved),
            )
    return HarborDiscoveryResult(
        trials=tuple(sorted(found.values(), key=lambda item: str(item.trial_dir))),
        missing_roots=tuple(missing),
    )


def sync_harbor_trials(
    store: Any,
    config: ToolConfig,
    *,
    source_keys: set[str] | None = None,
    force: bool = False,
) -> list[str]:
    discovery = discover_harbor_trials(store.paths.root, config.harbor_roots)
    existing = _existing_links(store, config.analysis_eval_slug)
    seen: set[str] = set()
    synced: list[str] = []
    missing_root_keys: set[str] = set()
    for root_path in discovery.missing_roots:
        source_key = _root_diagnostic_source_key(root_path)
        if source_keys is not None and source_key not in source_keys:
            continue
        missing_root_keys.add(source_key)
        seen.add(source_key)
        _record_root_diagnostic(store, config, root_path, existing.get(source_key))
        synced.append(source_key)

    _remove_recovered_root_diagnostics(
        store,
        config,
        existing,
        missing_root_keys,
        source_keys,
    )

    for candidate in discovery.trials:
        if source_keys is not None and candidate.source_key not in source_keys:
            continue
        seen.add(candidate.source_key)
        cell_dir, prior_link = existing.get(candidate.source_key, (None, None))
        signature = _source_signature(candidate.trial_dir)
        if (
            not force
            and cell_dir is not None
            and prior_link is not None
            and prior_link.get("observed_signature") == signature
            and optional_str(prior_link.get("last_status"))
            in {SOURCE_STATUS_OK, "error", "unsupported"}
            and _valid_local_projection(
                cell_dir,
                store.paths.root / "runs" / config.analysis_eval_slug,
            )
        ):
            synced.append(candidate.source_key)
            continue
        try:
            if candidate.multi_step:
                raise ValueError("unsupported Harbor multi-step Trial")
            values, revision, source_bytes = _read_source_objects(candidate.trial_dir)
            trajectory = values["agent/trajectory.json"]
            assert isinstance(trajectory, dict)
            validate_atif_trajectory(
                trajectory,
                str(candidate.trial_dir / "agent" / "trajectory.json"),
            )
            config_json = values.get("config.json")
            lock_json = values.get("lock.json")
            result_json = values.get("result.json")
            meta = _trajectory_meta(
                candidate,
                trajectory,
                config_json,
                lock_json,
                result_json,
                revision,
            )
            source = _source_row(candidate, trajectory, meta)
            if cell_dir is None:
                cell_dir = trial_cell_dir(
                    store.paths.root,
                    eval_slug=config.analysis_eval_slug,
                    source=source,
                    trajectory=trajectory,
                    meta=meta,
                )
            _assert_safe_projection_cell(
                cell_dir,
                store.paths.root / "runs" / config.analysis_eval_slug,
            )
            artifact_dir = relative_to_root(store.paths.root, cell_dir)
            link = _link_payload(
                candidate,
                source,
                artifact_dir,
                signature,
                status=SOURCE_STATUS_OK,
                error=None,
                source_revision=revision,
                last_good_revision=revision,
            )
            artifacts = trial_artifacts(cell_dir)
            write_files_atomically(
                [
                    (
                        artifacts.trajectory_path,
                        source_bytes["agent/trajectory.json"],
                    ),
                    (artifacts.meta_path, _json_bytes(meta)),
                    (harbor_link_path(cell_dir), _json_bytes(link)),
                ]
            )
            timestamp = now_ms()
            store.upsert_source_row(
                candidate.source_key,
                source,
                artifact_dir,
                timestamp,
                trajectory=trajectory,
                meta=meta,
                refreshable=True,
                snapshot=False,
                status=SOURCE_STATUS_OK,
            )
            store.log_refresh(
                candidate.source_key, SOURCE_STATUS_OK, 0, None, timestamp
            )
        except Exception as exc:  # noqa: BLE001 - preserve last-good evidence.
            status = "unsupported" if candidate.multi_step else "error"
            cell_dir = _record_source_failure(
                store,
                config,
                candidate,
                cell_dir,
                prior_link,
                signature,
                status,
                str(exc),
            )
        synced.append(candidate.source_key)

    existing_trial_keys = {
        key
        for key, (_cell_dir, link) in existing.items()
        if link.get("kind") == HARBOR_SOURCE_KIND
    }
    missing_keys = (
        existing_trial_keys - seen
        if source_keys is None
        else (existing_trial_keys & source_keys) - seen
    )
    if missing_keys:
        timestamp = now_ms()
        for source_key in sorted(missing_keys):
            cell_dir, link = existing[source_key]
            _assert_safe_projection_cell(
                cell_dir,
                store.paths.root / "runs" / config.analysis_eval_slug,
            )
            source = harbor_source_from_link(link)
            error = f"Harbor Trial source not found: {link.get('input_path')}"
            missing_link = {
                **link,
                "last_status": SOURCE_STATUS_MISSING,
                "last_error": error,
                "synced_at_ms": timestamp,
            }
            write_json_files_atomically([(harbor_link_path(cell_dir), missing_link)])
            store.upsert_source_row(
                source_key,
                source,
                relative_to_root(store.paths.root, cell_dir),
                timestamp,
                refreshable=True,
                snapshot=False,
                status=SOURCE_STATUS_MISSING,
                error=error,
            )
            store.log_refresh(source_key, SOURCE_STATUS_MISSING, 0, error, timestamp)
    return synced


def harbor_link_path(cell_dir: Path) -> Path:
    return cell_dir / SOURCE_STATE_DIR / HARBOR_LINK_FILENAME


def read_harbor_link(cell_dir: Path) -> dict[str, Any] | None:
    path = harbor_link_path(cell_dir)
    if not path.is_file() or path.is_symlink() or path.parent.is_symlink():
        return None
    value = read_json_object(path)
    if value.get("schema_version") != HARBOR_LINK_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported Harbor link schema: {value.get('schema_version')}"
        )
    if value.get("kind") not in {
        HARBOR_SOURCE_KIND,
        HARBOR_ROOT_DIAGNOSTIC_KIND,
    }:
        raise ValueError(f"invalid Harbor link kind: {value.get('kind')}")
    if not optional_str(value.get("source_key")):
        raise ValueError("Harbor link source_key is required")
    return value


def harbor_source_from_link(link: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": link.get("kind"),
        "adapter": HARBOR_ADAPTER,
        "label": optional_str(link.get("label"))
        or optional_str(link.get("relative_path"))
        or "Harbor Trial",
        "input_path": optional_str(link.get("input_path")),
        "db_path": None,
        "session_id": optional_str(link.get("session_id")),
        "source_alias": None,
        "source_category": None,
        "source_tags": [],
        "agent_name": optional_str(link.get("agent_name")),
        "agent_version": optional_str(link.get("agent_version")),
        "model": optional_str(link.get("model")),
    }


def is_harbor_source(value: dict[str, Any]) -> bool:
    return value.get("kind") in {
        HARBOR_SOURCE_KIND,
        HARBOR_ROOT_DIAGNOSTIC_KIND,
    }


def _trial_dirs_for_root(root: Path) -> list[Path]:
    if _looks_like_trial(root):
        return [root]
    found: list[Path] = []
    children = list(_child_dirs(root))
    for child in children:
        if _looks_like_trial(child):
            found.append(child)
    if found:
        return found
    for job_dir in children:
        for trial_dir in _child_dirs(job_dir):
            if _looks_like_trial(trial_dir):
                found.append(trial_dir)
    return found


def _child_dirs(root: Path) -> Iterable[Path]:
    try:
        with os.scandir(root) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name)
    except OSError:
        return
    for entry in ordered:
        try:
            if entry.is_dir(follow_symlinks=False):
                yield Path(entry.path)
        except OSError:
            continue


def _path_has_symlink(path: Path) -> bool:
    current = path
    while True:
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
        parent = current.parent
        if parent == current:
            return False
        current = parent


def _looks_like_trial(path: Path) -> bool:
    if _regular_file(path / "agent" / "trajectory.json"):
        return True
    steps = path / "steps"
    return (
        any(
            _regular_file(step / "agent" / "trajectory.json")
            for step in _child_dirs(steps)
        )
        if steps.is_dir() and not steps.is_symlink()
        else False
    )


def _is_multi_step_trial(path: Path) -> bool:
    steps = path / "steps"
    if (
        steps.is_dir()
        and not steps.is_symlink()
        and any(True for _ in _child_dirs(steps))
    ):
        return True
    result_path = path / "result.json"
    if not _regular_file(result_path):
        return False
    try:
        result = read_json_object(result_path)
    except ValueError:
        return False
    step_results = result.get("step_results")
    return isinstance(step_results, list) and bool(step_results)


def _regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink() and not path.parent.is_symlink()


def _source_location(
    workspace: Path, discovery_root: Path, trial: Path
) -> tuple[str, str]:
    try:
        return "workspace", trial.relative_to(workspace).as_posix() or "."
    except ValueError:
        mount_hash = hashlib.sha256(str(discovery_root).encode("utf-8")).hexdigest()[
            :12
        ]
        return f"configured-{mount_hash}", trial.relative_to(
            discovery_root
        ).as_posix() or "."


def _source_signature(trial_dir: Path) -> dict[str, dict[str, int] | None]:
    signature: dict[str, dict[str, int] | None] = {}
    for relative in HARBOR_SOURCE_FILES:
        path = trial_dir / relative
        try:
            stat = path.stat(follow_symlinks=False)
            signature[relative] = {
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "mode": stat.st_mode,
            }
        except OSError:
            signature[relative] = None
    return signature


def _read_source_objects(
    trial_dir: Path,
) -> tuple[
    dict[str, dict[str, Any] | None],
    str,
    dict[str, bytes],
]:
    values: dict[str, dict[str, Any] | None] = {}
    source_bytes: dict[str, bytes] = {}
    digest = hashlib.sha256()
    for relative in HARBOR_SOURCE_FILES:
        path = trial_dir / relative
        if not path.exists():
            values[relative] = None
            digest.update(relative.encode("utf-8") + b"\0missing\0")
            continue
        if not _regular_file(path):
            raise ValueError(f"Harbor source file must be a regular file: {path}")
        content = path.read_bytes()
        source_bytes[relative] = content
        digest.update(relative.encode("utf-8") + b"\0" + content + b"\0")
        try:
            parsed = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"failed to parse {path}: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{path} must contain a JSON object")
        values[relative] = parsed
    if values["agent/trajectory.json"] is None:
        raise ValueError(f"Harbor Trial has no agent/trajectory.json: {trial_dir}")
    return values, digest.hexdigest(), source_bytes


def _trajectory_meta(
    candidate: HarborTrialCandidate,
    trajectory: dict[str, Any],
    config_json: dict[str, Any] | None,
    lock_json: dict[str, Any] | None,
    result_json: dict[str, Any] | None,
    revision: str,
) -> dict[str, Any]:
    evaluation = _evaluation(result_json)
    agent = trajectory.get("agent") if isinstance(trajectory.get("agent"), dict) else {}
    trial_name = (
        optional_str(
            (result_json or {}).get("trial_name")
            or (config_json or {}).get("trial_name")
        )
        or candidate.trial_dir.name
    )
    task_name = optional_str((result_json or {}).get("task_name")) or _nested_string(
        config_json, "task", "name"
    )
    job_id = optional_str((config_json or {}).get("job_id"))
    result_id = optional_str((result_json or {}).get("id"))
    data_ref: dict[str, Any] = {
        "kind": HARBOR_SOURCE_KIND,
        "label": candidate.relative_path,
        "path": str(candidate.trial_dir),
        "relative_path": candidate.relative_path,
        "mount_id": candidate.mount_id,
        "source_revision": revision,
        "trial_name": trial_name,
    }
    for key, value in (
        ("job_id", job_id),
        ("result_id", result_id),
        ("task_name", task_name),
    ):
        if value is not None:
            data_ref[key] = value
    if lock_json is not None:
        data_ref["lock_available"] = True
    meta = {
        "trial_key": candidate.trial_key,
        "adapter": HARBOR_ADAPTER,
        "conversion_status": "passed",
        "status": evaluation["status"],
        "failure_class": evaluation.get("failure_class"),
        "score": evaluation.get("score"),
        "score_message": evaluation.get("score_message"),
        "warnings": [],
        "data_ref": data_ref,
        "total_events": len(trajectory.get("steps") or []),
        "unmapped_events": 0,
        "prompt_unavailable": not any(
            isinstance(step, dict) and step.get("source") == "user"
            for step in trajectory.get("steps") or []
        ),
        "steps": [],
        "evaluation": {
            **evaluation,
            "trial_name": trial_name,
            **({"task_name": task_name} if task_name else {}),
            **({"job_id": job_id} if job_id else {}),
            **({"result_id": result_id} if result_id else {}),
        },
        "import_context": {
            "kind": HARBOR_SOURCE_KIND,
            "source_revision": revision,
            "config_available": config_json is not None,
            "lock_available": lock_json is not None,
            "result_available": result_json is not None,
            "agent_name": optional_str(agent.get("name")),
        },
    }
    return project_meta_from_atif(trajectory, meta)


def _evaluation(result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return {
            "status": "running",
            "score": None,
            "score_message": "Harbor Trial has no result.json yet",
            "rewards": {},
        }
    exception = result.get("exception_info")
    status = "errored" if isinstance(exception, dict) else "completed"
    rewards: dict[str, int | float] = {}
    verifier = result.get("verifier_result")
    if isinstance(verifier, dict) and isinstance(verifier.get("rewards"), dict):
        rewards = {
            str(key): value
            for key, value in verifier["rewards"].items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    score: int | float | None = None
    score_message = "Harbor Trial completed without a numeric reward"
    if "reward" in rewards:
        score = rewards["reward"]
        score_message = "Harbor verifier reward"
    elif len(rewards) == 1:
        key, score = next(iter(rewards.items()))
        score_message = f"Harbor verifier reward: {key}"
    elif len(rewards) > 1:
        score_message = "Harbor verifier returned multiple reward dimensions"
    payload: dict[str, Any] = {
        "status": status,
        "score": score,
        "score_message": score_message,
        "rewards": rewards,
        "started_at": result.get("started_at"),
        "finished_at": result.get("finished_at"),
    }
    if isinstance(exception, dict):
        failure_class = optional_str(exception.get("exception_type")) or "harbor-trial"
        payload["failure_class"] = failure_class
        payload["exception"] = exception
    return payload


def _source_row(
    candidate: HarborTrialCandidate,
    trajectory: dict[str, Any],
    meta: dict[str, Any],
) -> dict[str, Any]:
    agent = trajectory.get("agent") if isinstance(trajectory.get("agent"), dict) else {}
    return {
        "kind": HARBOR_SOURCE_KIND,
        "adapter": HARBOR_ADAPTER,
        "label": candidate.relative_path,
        "input_path": str(candidate.trial_dir),
        "db_path": None,
        "session_id": optional_str(trajectory.get("session_id")),
        "source_alias": None,
        "source_category": None,
        "source_tags": [],
        "agent_name": optional_str(agent.get("name")),
        "agent_version": optional_str(agent.get("version")),
        "model": optional_str(agent.get("model_name")),
        "artifact_agent_id": "harbor",
        "artifact_session_id": candidate.source_key,
        "trial_key": meta.get("trial_key"),
    }


def _link_payload(
    candidate: HarborTrialCandidate,
    source: dict[str, Any],
    artifact_dir: str,
    signature: dict[str, Any],
    *,
    status: str,
    error: str | None,
    source_revision: str | None,
    last_good_revision: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": HARBOR_LINK_SCHEMA_VERSION,
        "kind": HARBOR_SOURCE_KIND,
        "source_key": candidate.source_key,
        "trial_key": candidate.trial_key,
        "mount_id": candidate.mount_id,
        "relative_path": candidate.relative_path,
        "label": candidate.relative_path,
        "input_path": str(candidate.trial_dir),
        "artifact_dir": artifact_dir,
        "session_id": source.get("session_id"),
        "agent_name": source.get("agent_name"),
        "agent_version": source.get("agent_version"),
        "model": source.get("model"),
        "observed_signature": signature,
        "source_revision": source_revision,
        "last_good_revision": last_good_revision,
        "last_status": status,
        "last_error": error,
        "synced_at_ms": now_ms(),
    }


def _root_diagnostic_source_key(root_path: str) -> str:
    return source_key_for_components(
        {"kind": HARBOR_ROOT_DIAGNOSTIC_KIND, "path": root_path}
    )


def _record_root_diagnostic(
    store: Any,
    config: ToolConfig,
    root_path: str,
    existing: tuple[Path, dict[str, Any]] | None,
) -> None:
    source_key = _root_diagnostic_source_key(root_path)
    digest = hashlib.sha256(root_path.encode("utf-8")).hexdigest()[:12]
    trial_key = f"harbor-root-{digest}"
    label = f"Harbor root: {root_path}"
    source = {
        "kind": HARBOR_ROOT_DIAGNOSTIC_KIND,
        "adapter": HARBOR_ADAPTER,
        "label": label,
        "input_path": root_path,
        "db_path": None,
        "session_id": None,
        "source_alias": None,
        "source_category": None,
        "source_tags": [],
        "agent_name": None,
        "agent_version": None,
        "model": None,
        "artifact_agent_id": "harbor",
        "artifact_session_id": source_key,
    }
    cell_dir = (
        existing[0]
        if existing is not None
        else trial_cell_dir(
            store.paths.root,
            eval_slug=config.analysis_eval_slug,
            source=source,
            trajectory={},
            meta={"trial_key": trial_key, "adapter": HARBOR_ADAPTER},
        )
    )
    run_root = store.paths.root / "runs" / config.analysis_eval_slug
    _assert_safe_projection_cell(cell_dir, run_root)
    artifact_dir = relative_to_root(store.paths.root, cell_dir)
    path = Path(root_path)
    if _path_has_symlink(path):
        error = f"Harbor configured root is excluded because it traverses a symlink: {root_path}"
    else:
        error = f"Harbor configured root not found: {root_path}"
    timestamp = now_ms()
    link = {
        "schema_version": HARBOR_LINK_SCHEMA_VERSION,
        "kind": HARBOR_ROOT_DIAGNOSTIC_KIND,
        "source_key": source_key,
        "trial_key": trial_key,
        "label": label,
        "input_path": root_path,
        "artifact_dir": artifact_dir,
        "last_status": SOURCE_STATUS_MISSING,
        "last_error": error,
        "synced_at_ms": timestamp,
    }
    write_json_files_atomically([(harbor_link_path(cell_dir), link)])
    store.upsert_source_row(
        source_key,
        source,
        artifact_dir,
        timestamp,
        refreshable=True,
        snapshot=False,
        status=SOURCE_STATUS_MISSING,
        error=error,
    )
    store.log_refresh(source_key, SOURCE_STATUS_MISSING, 0, error, timestamp)


def _remove_recovered_root_diagnostics(
    store: Any,
    config: ToolConfig,
    existing: dict[str, tuple[Path, dict[str, Any]]],
    missing_root_keys: set[str],
    source_keys: set[str] | None,
) -> None:
    run_root = store.paths.root / "runs" / config.analysis_eval_slug
    for source_key, (cell_dir, link) in existing.items():
        if link.get("kind") != HARBOR_ROOT_DIAGNOSTIC_KIND:
            continue
        if source_key in missing_root_keys:
            continue
        if source_keys is not None and source_key not in source_keys:
            continue
        _assert_safe_projection_cell(cell_dir, run_root)
        remove_artifact_dir(store.paths.root, cell_dir)


def _record_source_failure(
    store: Any,
    config: ToolConfig,
    candidate: HarborTrialCandidate,
    cell_dir: Path | None,
    prior_link: dict[str, Any] | None,
    signature: dict[str, Any],
    status: str,
    error: str,
) -> Path:
    source = (
        harbor_source_from_link(prior_link)
        if prior_link
        else {
            "kind": HARBOR_SOURCE_KIND,
            "adapter": HARBOR_ADAPTER,
            "label": candidate.relative_path,
            "input_path": str(candidate.trial_dir),
            "db_path": None,
            "session_id": None,
            "source_alias": None,
            "source_category": None,
            "source_tags": [],
            "agent_name": None,
            "agent_version": None,
            "model": None,
            "artifact_agent_id": "harbor",
            "artifact_session_id": candidate.source_key,
        }
    )
    placeholder_meta = {"trial_key": candidate.trial_key, "adapter": HARBOR_ADAPTER}
    if cell_dir is None:
        cell_dir = trial_cell_dir(
            store.paths.root,
            eval_slug=config.analysis_eval_slug,
            source=source,
            trajectory={},
            meta=placeholder_meta,
        )
    _assert_safe_projection_cell(
        cell_dir,
        store.paths.root / "runs" / config.analysis_eval_slug,
    )
    artifact_dir = relative_to_root(store.paths.root, cell_dir)
    link = _link_payload(
        candidate,
        source,
        artifact_dir,
        signature,
        status=status,
        error=error,
        source_revision=optional_str((prior_link or {}).get("source_revision")),
        last_good_revision=optional_str((prior_link or {}).get("last_good_revision")),
    )
    write_json_files_atomically([(harbor_link_path(cell_dir), link)])
    timestamp = now_ms()
    store.upsert_source_row(
        candidate.source_key,
        source,
        artifact_dir,
        timestamp,
        refreshable=True,
        snapshot=False,
        status=status,
        error=error,
    )
    store.log_refresh(candidate.source_key, status, 0, error, timestamp)
    return cell_dir


def _existing_links(
    store: Any,
    eval_slug: str,
) -> dict[str, tuple[Path, dict[str, Any]]]:
    root = store.paths.root / "runs" / eval_slug
    if not root.is_dir() or root.is_symlink():
        return {}
    found: dict[str, tuple[Path, dict[str, Any]]] = {}
    for agent_dir in _child_dirs(root):
        for session_dir in _child_dirs(agent_dir):
            for cell_dir in _child_dirs(session_dir):
                if not _safe_projection_path(cell_dir, root):
                    continue
                try:
                    link = read_harbor_link(cell_dir)
                except ValueError:
                    continue
                if link is None:
                    continue
                source_key = str(link["source_key"])
                found[source_key] = (cell_dir, link)
    return found


def _valid_local_projection(cell_dir: Path, run_root: Path) -> bool:
    try:
        _assert_safe_projection_cell(cell_dir, run_root)
        artifacts = trial_artifacts(cell_dir)
        if not all(
            path.is_file() and not path.is_symlink()
            for path in (artifacts.trajectory_path, artifacts.meta_path)
        ):
            return False
        trajectory = read_json_object(artifacts.trajectory_path)
        validate_atif_trajectory(trajectory, str(artifacts.trajectory_path))
        meta = read_json_object(artifacts.meta_path)
        return project_meta_from_atif(trajectory, meta) == meta
    except (OSError, ValueError):
        return False


def _assert_safe_projection_cell(cell_dir: Path, run_root: Path) -> None:
    artifacts = trial_artifacts(cell_dir)
    targets = (
        cell_dir,
        artifacts.trajectory_path,
        artifacts.meta_path,
        harbor_link_path(cell_dir),
    )
    if not all(_safe_projection_path(path, run_root) for path in targets):
        raise ValueError(
            f"Harbor projection path escapes or traverses a linked run root: {cell_dir}"
        )


def _safe_projection_path(path: Path, run_root: Path) -> bool:
    lexical_root = Path(os.path.abspath(run_root))
    lexical_path = Path(os.path.abspath(path))
    workspace_root = lexical_root.parent.parent
    if not _lexical_descendant_without_links(lexical_root, workspace_root):
        return False
    if not _lexical_descendant_without_links(lexical_path, lexical_root):
        return False
    try:
        resolved_workspace = workspace_root.resolve(strict=False)
        resolved_root = lexical_root.resolve(strict=False)
        resolved_path = lexical_path.resolve(strict=False)
        resolved_root.relative_to(resolved_workspace)
        resolved_path.relative_to(resolved_root)
    except (OSError, ValueError):
        return False
    return True


def _lexical_descendant_without_links(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    current = root
    try:
        if current.is_symlink():
            return False
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                return False
    except OSError:
        return False
    return True


def _nested_string(value: dict[str, Any] | None, *keys: str) -> str | None:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return optional_str(current)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
