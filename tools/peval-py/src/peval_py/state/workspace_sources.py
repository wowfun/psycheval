from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from peval_py._state.annotations import optional_str
from peval_py._state.artifacts import (
    artifact_segment,
    read_json_object,
    source_key_for_components,
    source_key_for_trial,
    source_key_for_trial_cell_components,
    trial_artifacts,
    write_json_file,
)
from peval_py.atif import (
    ATIF_VERSION,
    convert_db,
    convert_path,
    validate_atif_trajectory,
)
from peval_py.config import HarborMount, ToolConfig, validate_harbor_mount_paths
from peval_py.report import project_meta_from_atif
from peval_py.report.builder import iso_timestamp_ms
from peval_py.report.metrics import final_metric
from peval_py.report.timing import step_meta_reports, trial_active_duration_ms
from peval_py.state.constants import SOURCE_STATE_DIR, SOURCE_STATE_FILENAME
from peval_py.state.harbor_evidence import (
    HarborEvidence,
    HarborTaskIndex,
    read_harbor_evidence,
    read_harbor_task_index,
)

HARBOR_SOURCE_KIND = "harbor-trial"
HARBOR_ADAPTER = "harbor"
HARBOR_OVERLAY_SCHEMA_VERSION = 1
HARBOR_OVERLAY_ROOT = "harbor"
HARBOR_JSON_SOURCE_FILES = (
    "agent/trajectory.json",
    "config.json",
    "lock.json",
    "result.json",
)
HARBOR_OPENCODE_TELEMETRY_FILES = (
    "agent/opencode/xdg-data/opencode/opencode.db",
    "agent/opencode/xdg-data/opencode/opencode.db-wal",
    "agent/opencode/xdg-data/opencode/opencode.db-shm",
)
HARBOR_PSYCHEVO_TELEMETRY_FILES = (
    "agent/psychevo-state.db",
    "agent/psychevo-state.db-wal",
    "agent/psychevo-state.db-shm",
)
HARBOR_HERMES_TELEMETRY_FILES = ("agent/hermes-session.jsonl",)
HARBOR_SOURCE_FILES = (
    HARBOR_JSON_SOURCE_FILES
    + HARBOR_OPENCODE_TELEMETRY_FILES
    + HARBOR_PSYCHEVO_TELEMETRY_FILES
    + HARBOR_HERMES_TELEMETRY_FILES
)
HARBOR_OVERLAY_FILES = (
    "state.json",
    "notes.md",
    "analysis.json",
    "analysis.md",
)
HARBOR_OVERLAY_STATE_FIELDS = frozenset(
    {
        "schema_version",
        "active",
        "source_alias",
        "source_category",
        "source_tags",
    }
)
LOCAL_FINGERPRINT_FILES = (
    "agent/trajectory.json",
    "agent/trajectory_meta.json",
    ".peval/state.json",
    "notes.md",
    "analysis.json",
    "analysis.md",
)


@dataclass(frozen=True)
class SourceCandidate:
    source_ref: str
    kind: str
    path: Path
    fingerprint: str
    source_key: str | None = None
    mount_id: str | None = None
    job_name: str | None = None
    trial_name: str | None = None
    diagnostic: str | None = None
    missing: bool = False
    multi_step: bool = False
    containment_root: Path | None = None
    task_paths: tuple[str, ...] = ()
    harbor_evidence: HarborEvidence | None = None


@dataclass(frozen=True)
class SourceDocument:
    source_ref: str
    source_key: str
    source: dict[str, Any]
    trajectory: dict[str, Any] | None
    meta: dict[str, Any] | None
    fingerprint: str
    updated_at_ms: int
    input_bytes: int
    readable: bool
    refreshable: bool
    snapshot: bool
    active: bool
    last_status: str
    last_error: str | None


@dataclass(frozen=True)
class HarborTelemetry:
    steps: list[dict[str, Any]]
    duration_ms: int | None
    final_metrics: dict[str, Any]
    revision: str


class WorkspaceSources:
    """Own discovery, direct reads, and minimal overlays for workspace sources."""

    def __init__(self, store: Any, config: ToolConfig) -> None:
        self.store = store
        self.config = config
        self.workspace_root = store.paths.root.expanduser().resolve()

    def discover(self) -> list[SourceCandidate]:
        self._reject_legacy_harbor_projections()
        overlay_root = self.workspace_root / HARBOR_OVERLAY_ROOT
        if overlay_root.is_symlink():
            raise ValueError("workspace Harbor overlay root must not be a symlink")
        candidates = self._local_candidates()
        harbor_candidates, present_refs = self._harbor_candidates()
        candidates.extend(harbor_candidates)
        candidates.extend(self._retained_missing_candidates(present_refs))
        return sorted(candidates, key=lambda item: item.source_ref)

    def source_keys(self) -> list[str]:
        return [
            str(candidate.source_key)
            for candidate in self.discover()
            if candidate.kind == HARBOR_SOURCE_KIND and candidate.source_key
        ]

    def load(self, candidate: SourceCandidate) -> SourceDocument:
        if candidate.kind == "artifact-cell":
            return self._load_local(candidate)
        return self._load_harbor(candidate)

    def load_ref(self, source_ref: str) -> SourceDocument:
        wanted = str(source_ref or "").strip()
        for candidate in self.discover():
            if candidate.source_ref == wanted:
                return self.load(candidate)
        raise ValueError(f"unknown source reference: {wanted}")

    def overlay_dir(self, source_ref: str) -> Path:
        parts = Path(str(source_ref)).parts
        if (
            len(parts) != 4
            or parts[0] != HARBOR_OVERLAY_ROOT
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise ValueError(f"invalid Harbor source reference: {source_ref}")
        path = self.workspace_root.joinpath(*parts)
        self._assert_overlay_path(path)
        return path

    def read_overlay(self, source_ref: str) -> dict[str, Any]:
        path = self.overlay_dir(source_ref) / "state.json"
        if not path.exists():
            return {}
        if not _regular_file(path):
            raise ValueError(f"Harbor overlay state must be a regular file: {path}")
        value = read_json_object(path)
        unknown = sorted(set(value) - HARBOR_OVERLAY_STATE_FIELDS)
        if unknown:
            raise ValueError(f"unknown Harbor overlay state field: {unknown[0]}")
        if value.get("schema_version") != HARBOR_OVERLAY_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported Harbor overlay schema: {value.get('schema_version')}"
            )
        if "active" in value and not isinstance(value["active"], bool):
            raise ValueError("Harbor overlay active must be a boolean")
        if value.get("active") is True:
            raise ValueError("Harbor overlay must omit the default active value")
        for field in ("source_alias", "source_category"):
            if field in value and (
                not isinstance(value[field], str) or not value[field].strip()
            ):
                raise ValueError(f"Harbor overlay {field} must be a non-empty string")
        if "source_tags" in value and (
            not isinstance(value["source_tags"], list)
            or not value["source_tags"]
            or any(
                not isinstance(tag, str) or not tag.strip()
                for tag in value["source_tags"]
            )
        ):
            raise ValueError(
                "Harbor overlay source_tags must be a non-empty array of strings"
            )
        if len(value) == 1:
            raise ValueError("empty Harbor overlay state must be removed")
        return value

    def write_overlay(self, source_ref: str, state: dict[str, Any]) -> None:
        path = self.overlay_dir(source_ref)
        payload: dict[str, Any] = {"schema_version": HARBOR_OVERLAY_SCHEMA_VERSION}
        if not bool(state.get("active", True)):
            payload["active"] = False
        for field in ("source_alias", "source_category"):
            value = optional_str(state.get(field))
            if value and value.strip():
                payload[field] = value.strip()
        tags = _normalized_tags(state.get("source_tags"))
        if tags:
            payload["source_tags"] = tags
        state_path = path / "state.json"
        if len(payload) == 1:
            state_path.unlink(missing_ok=True)
            self._remove_empty_overlay_dirs(path)
            return
        self._assert_overlay_path(state_path)
        write_json_file(state_path, payload)

    def annotation_path(self, source_ref: str, filename: str) -> Path:
        if filename not in {"notes.md", "analysis.json", "analysis.md"}:
            raise ValueError(f"unsupported Harbor annotation file: {filename}")
        path = self.overlay_dir(source_ref) / filename
        self._assert_overlay_path(path)
        return path

    def annotation_dir(self, source_ref: str) -> Path:
        if source_ref.startswith("harbor/"):
            document = self.load_ref(source_ref)
            if document.source.get("kind") != HARBOR_SOURCE_KIND:
                raise ValueError(f"source is not a Harbor Trial: {source_ref}")
            return self.overlay_dir(source_ref)
        if not source_ref or "\\" in source_ref:
            raise ValueError("local source_ref must be normalized and relative")
        path = Path(source_ref)
        parts = path.parts
        if (
            path.is_absolute()
            or path.as_posix() != source_ref
            or len(parts) != 5
            or parts[0] != "runs"
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise ValueError(
                "local source_ref must have form "
                "runs/<analysis_eval_slug>/<agent-id>/<session-id>/<cell-key>"
            )
        target = self.workspace_root.joinpath(*parts)
        self._assert_workspace_path(target)
        return target

    def remove_annotation(self, source_ref: str, filename: str) -> None:
        path = self.annotation_path(source_ref, filename)
        path.unlink(missing_ok=True)
        self._remove_empty_overlay_dirs(path.parent)

    def _local_candidates(self) -> list[SourceCandidate]:
        run_root = self.workspace_root / "runs" / self.config.analysis_eval_slug
        if not run_root.is_dir() or run_root.is_symlink():
            return []
        candidates: list[SourceCandidate] = []
        for agent in _child_dirs(run_root):
            for session in _child_dirs(agent):
                for cell in _child_dirs(session):
                    artifacts = trial_artifacts(cell)
                    state_path = cell / SOURCE_STATE_DIR / SOURCE_STATE_FILENAME
                    if not (
                        _regular_file(artifacts.trajectory_path)
                        and _regular_file(artifacts.meta_path)
                    ) and not _regular_file(state_path):
                        continue
                    source_ref = cell.relative_to(self.workspace_root).as_posix()
                    candidates.append(
                        SourceCandidate(
                            source_ref=source_ref,
                            kind="artifact-cell",
                            path=cell,
                            fingerprint=_fingerprint(cell, LOCAL_FINGERPRINT_FILES),
                        )
                    )
        return candidates

    def _harbor_candidates(self) -> tuple[list[SourceCandidate], set[str]]:
        validate_harbor_mount_paths(self.config.harbor_mounts)
        candidates: list[SourceCandidate] = []
        present_refs: set[str] = set()
        resolved_mounts: set[Path] = set()
        for mount in self.config.harbor_mounts:
            lexical_root = Path(os.path.abspath(Path(mount.path).expanduser()))
            diagnostic = self._mount_diagnostic(lexical_root)
            if diagnostic is not None:
                raise ValueError(diagnostic)
            root = lexical_root.resolve()
            if root in resolved_mounts:
                raise ValueError(f"duplicate Harbor mount path: {root}")
            resolved_mounts.add(root)
            _reject_linked_directories(root, "Job")
            task_index = read_harbor_task_index(mount.task_paths)
            for job_dir in _child_dirs(root):
                _reject_linked_directories(job_dir, "Trial")
                for trial_dir in _child_dirs(job_dir):
                    if not _looks_like_trial(trial_dir):
                        continue
                    candidate = self._harbor_trial_candidate(
                        mount,
                        job_dir.name,
                        trial_dir.name,
                        trial_dir,
                        root,
                        task_index,
                    )
                    candidates.append(candidate)
                    present_refs.add(candidate.source_ref)
        return candidates, present_refs

    def _harbor_trial_candidate(
        self,
        mount: HarborMount,
        job_name: str,
        trial_name: str,
        trial_dir: Path,
        mount_root: Path,
        task_index: HarborTaskIndex,
    ) -> SourceCandidate:
        source_ref = f"harbor/{mount.id}/{job_name}/{trial_name}"
        overlay_dir = self.overlay_dir(source_ref)
        source_files = _harbor_source_files(trial_dir)
        evidence: HarborEvidence | None = None
        evidence_revision = "unavailable"
        try:
            evidence = read_harbor_evidence(
                trial_dir,
                jobs_root=mount_root,
                task_paths=mount.task_paths,
                mount_id=mount.id,
                task_index=task_index,
            )
            evidence_revision = evidence.revision
        except (OSError, ValueError):
            pass
        fingerprint = _combined_revision(
            _fingerprint(
                trial_dir,
                source_files,
                extra_root=overlay_dir,
                extra_files=HARBOR_OVERLAY_FILES,
            ),
            evidence_revision,
        )
        return SourceCandidate(
            source_ref=source_ref,
            kind=HARBOR_SOURCE_KIND,
            path=trial_dir,
            fingerprint=fingerprint,
            source_key=_harbor_trial_key(mount.id, job_name, trial_name),
            mount_id=mount.id,
            job_name=job_name,
            trial_name=trial_name,
            multi_step=_is_multi_step_trial(trial_dir),
            containment_root=mount_root,
            task_paths=mount.task_paths,
            harbor_evidence=evidence,
        )

    def _retained_missing_candidates(
        self, present_refs: set[str]
    ) -> list[SourceCandidate]:
        overlay_root = self.workspace_root / HARBOR_OVERLAY_ROOT
        mount_by_id = {mount.id: mount for mount in self.config.harbor_mounts}
        retained_refs = self._bound_harbor_refs()
        if overlay_root.is_dir() and not overlay_root.is_symlink():
            for mount_dir in _child_dirs(overlay_root):
                if mount_dir.name not in mount_by_id:
                    continue
                for job_dir in _child_dirs(mount_dir):
                    for trial_dir in _child_dirs(job_dir):
                        if any(
                            _regular_file(trial_dir / name)
                            for name in HARBOR_OVERLAY_FILES
                        ):
                            retained_refs.add(
                                f"harbor/{mount_dir.name}/{job_dir.name}/{trial_dir.name}"
                            )
        retained: list[SourceCandidate] = []
        for source_ref in sorted(retained_refs - present_refs):
            parts = Path(source_ref).parts
            if len(parts) != 4:
                continue
            _harbor, mount_id, job_name, trial_name = parts
            mount = mount_by_id.get(mount_id)
            if mount is None:
                continue
            overlay_dir = self.overlay_dir(source_ref)
            source_path = Path(mount.path) / job_name / trial_name
            retained.append(
                SourceCandidate(
                    source_ref=source_ref,
                    kind=HARBOR_SOURCE_KIND,
                    path=source_path,
                    fingerprint=_fingerprint(overlay_dir, HARBOR_OVERLAY_FILES),
                    source_key=_harbor_trial_key(mount_id, job_name, trial_name),
                    mount_id=mount_id,
                    job_name=job_name,
                    trial_name=trial_name,
                    diagnostic=f"Harbor Trial source not found: {source_path}",
                    missing=True,
                    containment_root=Path(mount.path),
                )
            )
        return retained

    def _bound_harbor_refs(self) -> set[str]:
        reports_root = self.workspace_root / "reports"
        if not reports_root.is_dir() or reports_root.is_symlink():
            return set()
        source_refs: set[str] = set()
        for report_dir in _child_dirs(reports_root):
            state_path = report_dir / "state.json"
            if not _regular_file(state_path):
                continue
            try:
                payload = read_json_object(state_path)
            except (OSError, ValueError):
                continue
            refs = payload.get("source_refs")
            if not isinstance(refs, list):
                continue
            for ref in refs:
                if not isinstance(ref, str) or not ref.startswith("harbor/"):
                    continue
                try:
                    self.overlay_dir(ref)
                except ValueError:
                    continue
                source_refs.add(ref)
        return source_refs

    def _load_local(self, candidate: SourceCandidate) -> SourceDocument:
        cell_dir = candidate.path
        identity = self.store.cell_path_identity(cell_dir)
        state = self.store.read_source_state(cell_dir)
        source_key = (
            optional_str(state.get("source_key"))
            or self.store.source_key_for_cell_identity(identity)
            or source_key_for_trial_cell_components(
                eval_slug=self.config.analysis_eval_slug,
                agent_id=cell_dir.parent.parent.name,
                session_id=cell_dir.parent.name,
                cell_key=cell_dir.name,
            )
        )
        artifacts = trial_artifacts(cell_dir)
        timestamp = _updated_at_ms(cell_dir, LOCAL_FINGERPRINT_FILES)
        input_bytes = _input_bytes(cell_dir, LOCAL_FINGERPRINT_FILES)
        try:
            if not (
                _regular_file(artifacts.trajectory_path)
                and _regular_file(artifacts.meta_path)
            ):
                raise ValueError(
                    f"Trial cell artifacts not found: {candidate.source_ref}"
                )
            trajectory = read_json_object(artifacts.trajectory_path)
            validate_atif_trajectory(trajectory, str(artifacts.trajectory_path))
            meta = read_json_object(artifacts.meta_path)
            source = self.store.source_row_for_artifact_cell(cell_dir, trajectory, meta)
            source["source_alias"] = optional_str(state.get("source_alias"))
            source["source_category"] = self.store.source_category_from_state(state)
            source["source_tags"] = self.store.source_tags_from_state(state)
            source_key = source_key_for_trial(
                self.config.analysis_eval_slug, source, trajectory, meta
            )
            return SourceDocument(
                source_ref=candidate.source_ref,
                source_key=source_key,
                source=source,
                trajectory=trajectory,
                meta=meta,
                fingerprint=candidate.fingerprint,
                updated_at_ms=timestamp,
                input_bytes=input_bytes,
                readable=True,
                refreshable=False,
                snapshot=True,
                active=bool(state.get("active", True)),
                last_status=optional_str(state.get("last_status")) or "ok",
                last_error=optional_str(state.get("last_error")),
            )
        except Exception as exc:  # noqa: BLE001 - retain a diagnostic catalog row.
            source = self.store.missing_source_row(
                candidate.source_ref, identity, state
            )
            return SourceDocument(
                source_ref=candidate.source_ref,
                source_key=source_key,
                source=source,
                trajectory=None,
                meta=None,
                fingerprint=candidate.fingerprint,
                updated_at_ms=timestamp,
                input_bytes=input_bytes,
                readable=False,
                refreshable=False,
                snapshot=True,
                active=bool(state.get("active", True)),
                last_status="missing"
                if not artifacts.trajectory_path.exists()
                else "error",
                last_error=str(exc),
            )

    def _load_harbor(self, candidate: SourceCandidate) -> SourceDocument:
        assert candidate.source_key is not None
        try:
            overlay = (
                self.read_overlay(candidate.source_ref)
                if candidate.kind == HARBOR_SOURCE_KIND
                else {}
            )
        except ValueError as exc:
            overlay = {}
            candidate = SourceCandidate(
                **{
                    **candidate.__dict__,
                    "diagnostic": str(exc),
                }
            )
        source = _harbor_source(candidate, overlay)
        source_files = _harbor_source_files(candidate.path)
        timestamp = _updated_at_ms(candidate.path, source_files)
        if candidate.diagnostic is not None:
            return SourceDocument(
                source_ref=candidate.source_ref,
                source_key=candidate.source_key,
                source=source,
                trajectory=None,
                meta=None,
                fingerprint=candidate.fingerprint,
                updated_at_ms=timestamp,
                input_bytes=0,
                readable=False,
                refreshable=True,
                snapshot=False,
                active=bool(overlay.get("active", True)),
                last_status="missing" if candidate.missing else "error",
                last_error=candidate.diagnostic,
            )
        values: dict[str, dict[str, Any] | None] = {}
        try:
            if candidate.multi_step:
                raise ValueError("unsupported Harbor multi-step Trial")
            evidence = candidate.harbor_evidence or read_harbor_evidence(
                candidate.path,
                jobs_root=candidate.containment_root or candidate.path.parent.parent,
                task_paths=candidate.task_paths,
                mount_id=candidate.mount_id,
            )
            values = evidence.trial_values
            revision = evidence.revision
            config_json = values.get("config.json")
            lock_json = values.get("lock.json")
            result_json = values.get("result.json")
            raw_trajectory = values.get("agent/trajectory.json")
            if raw_trajectory is None:
                meta = _result_only_meta(
                    candidate,
                    config_json,
                    lock_json,
                    result_json,
                    revision,
                    evidence,
                )
                source = _harbor_source(
                    candidate,
                    overlay,
                    meta=meta,
                    config_json=config_json,
                    result_json=result_json,
                    evidence=evidence,
                )
                lifecycle_status = str(meta.get("status") or "error")
                last_status = (
                    lifecycle_status
                    if lifecycle_status in {"running", "errored"}
                    else "error"
                )
                return SourceDocument(
                    source_ref=candidate.source_ref,
                    source_key=candidate.source_key,
                    source=source,
                    trajectory=None,
                    meta=meta,
                    fingerprint=_combined_revision(
                        _fingerprint(
                            candidate.path,
                            source_files,
                            extra_root=self.overlay_dir(candidate.source_ref),
                            extra_files=HARBOR_OVERLAY_FILES,
                        ),
                        evidence.revision,
                    ),
                    updated_at_ms=_updated_at_ms(candidate.path, source_files),
                    input_bytes=_input_bytes(candidate.path, source_files),
                    readable=False,
                    refreshable=True,
                    snapshot=False,
                    active=bool(overlay.get("active", True)),
                    last_status=last_status,
                    last_error=_result_only_error(candidate, result_json),
                )
            trajectory, source_schema = _compatible_harbor_trajectory(
                raw_trajectory,
                candidate.path / "agent" / "trajectory.json",
            )
            telemetry, telemetry_warning = _harbor_telemetry(
                candidate,
                trajectory,
            )
            trajectory = _project_harbor_metrics(
                trajectory,
                result_json,
                telemetry,
            )
            if telemetry is not None:
                revision = hashlib.sha256(
                    f"{revision}:{telemetry.revision}".encode("utf-8")
                ).hexdigest()
            meta = _trajectory_meta(
                candidate,
                trajectory,
                config_json,
                lock_json,
                result_json,
                revision,
                source_schema=source_schema,
                telemetry=telemetry,
                telemetry_warning=telemetry_warning,
                evidence=evidence,
            )
            source = _harbor_source(
                candidate,
                overlay,
                trajectory=trajectory,
                meta=meta,
                config_json=config_json,
                result_json=result_json,
                evidence=evidence,
            )
            return SourceDocument(
                source_ref=candidate.source_ref,
                source_key=candidate.source_key,
                source=source,
                trajectory=trajectory,
                meta=meta,
                fingerprint=_combined_revision(
                    _fingerprint(
                        candidate.path,
                        source_files,
                        extra_root=self.overlay_dir(candidate.source_ref),
                        extra_files=HARBOR_OVERLAY_FILES,
                    ),
                    evidence.revision,
                ),
                updated_at_ms=_updated_at_ms(candidate.path, source_files),
                input_bytes=_input_bytes(candidate.path, source_files),
                readable=True,
                refreshable=True,
                snapshot=False,
                active=bool(overlay.get("active", True)),
                last_status="ok",
                last_error=None,
            )
        except Exception as exc:  # noqa: BLE001 - one Trial becomes one diagnostic.
            source = _harbor_source(
                candidate,
                overlay,
                config_json=values.get("config.json"),
                result_json=values.get("result.json"),
            )
            return SourceDocument(
                source_ref=candidate.source_ref,
                source_key=candidate.source_key,
                source=source,
                trajectory=None,
                meta=None,
                fingerprint=_fingerprint(
                    candidate.path,
                    source_files,
                    extra_root=self.overlay_dir(candidate.source_ref),
                    extra_files=HARBOR_OVERLAY_FILES,
                ),
                updated_at_ms=_updated_at_ms(candidate.path, source_files),
                input_bytes=_input_bytes(candidate.path, source_files),
                readable=False,
                refreshable=True,
                snapshot=False,
                active=bool(overlay.get("active", True)),
                last_status="unsupported" if candidate.multi_step else "error",
                last_error=str(exc),
            )

    def _mount_diagnostic(self, root: Path) -> str | None:
        if _path_has_symlink(root):
            return f"Harbor mount is excluded because it traverses a symlink: {root}"
        if not root.is_dir():
            return f"Harbor mount not found: {root}"
        if _looks_like_trial(root) or _looks_like_job(root):
            return (
                "Harbor mount must identify a jobs root, not a Job or Trial "
                f"directory: {root}"
            )
        return None

    def _reject_legacy_harbor_projections(self) -> None:
        run_root = self.workspace_root / "runs"
        if not run_root.is_dir():
            return
        for path in run_root.rglob("harbor-link.json"):
            if path.name == "harbor-link.json":
                raise ValueError(
                    "legacy Harbor projections are unsupported; initialize a new "
                    "peval-py workspace instead of reusing harbor-link.json state"
                )

    def _assert_overlay_path(self, path: Path) -> None:
        _assert_safe_descendant(
            self.workspace_root / HARBOR_OVERLAY_ROOT,
            path,
            label="Harbor overlay",
        )

    def _assert_workspace_path(self, path: Path) -> None:
        _assert_safe_descendant(self.workspace_root, path, label="source overlay")

    def _remove_empty_overlay_dirs(self, leaf: Path) -> None:
        root = self.workspace_root / HARBOR_OVERLAY_ROOT
        current = leaf
        while current != root and root in current.parents:
            try:
                current.rmdir()
            except OSError:
                return
            current = current.parent
        if current == root:
            try:
                root.rmdir()
            except OSError:
                pass


def is_harbor_source(value: dict[str, Any]) -> bool:
    return value.get("kind") == HARBOR_SOURCE_KIND


def _harbor_source_key_payload(
    mount_id: str, job_name: str, trial_name: str
) -> dict[str, str]:
    return {
        "kind": HARBOR_SOURCE_KIND,
        "mount_id": mount_id,
        "job_name": job_name,
        "trial_name": trial_name,
    }


def _harbor_trial_key(mount_id: str, job_name: str, trial_name: str) -> str:
    return source_key_for_components(
        _harbor_source_key_payload(mount_id, job_name, trial_name)
    )


def _compatible_harbor_trajectory(
    trajectory: dict[str, Any], path: Path
) -> tuple[dict[str, Any], str]:
    source_schema = str(trajectory.get("schema_version") or "")
    projected = deepcopy(trajectory)
    if source_schema != ATIF_VERSION:
        match = re.fullmatch(r"ATIF-v1\.(\d+)", source_schema)
        if match is None or int(match.group(1)) > 7:
            raise ValueError(
                f"{path}.schema_version is not a supported Harbor ATIF version: "
                f"{source_schema or '<missing>'}"
            )
        projected["schema_version"] = ATIF_VERSION
    validate_atif_trajectory(projected, str(path))
    return projected, source_schema


def _project_harbor_metrics(
    trajectory: dict[str, Any],
    result_json: dict[str, Any] | None,
    telemetry: HarborTelemetry | None,
) -> dict[str, Any]:
    projected = deepcopy(trajectory)
    existing = projected.get("final_metrics")
    metrics = deepcopy(existing) if isinstance(existing, dict) else {}
    supplemental = telemetry.final_metrics if telemetry is not None else {}
    result_metrics = _result_final_metrics(result_json)
    for key in (
        "total_prompt_tokens",
        "total_completion_tokens",
        "total_cached_tokens",
        "total_cost_usd",
    ):
        for source in (supplemental, result_metrics):
            if key not in metrics and source.get(key) is not None:
                metrics[key] = source[key]
    metrics.setdefault("total_steps", len(projected.get("steps") or []))

    extra = (
        deepcopy(metrics.get("extra")) if isinstance(metrics.get("extra"), dict) else {}
    )
    steps = [step for step in projected.get("steps") or [] if isinstance(step, dict)]
    derived = {
        "total_turns": sum(step.get("source") == "agent" for step in steps),
        "total_tool_calls": sum(len(step.get("tool_calls") or []) for step in steps),
        "total_tool_errors": _derived_tool_errors(steps),
    }
    for key, value in derived.items():
        if key in extra:
            continue
        supplemental_value = final_metric(supplemental, key)
        extra[key] = supplemental_value if supplemental_value is not None else value
    supplemental_extra = (
        supplemental.get("extra") if isinstance(supplemental.get("extra"), dict) else {}
    )
    for key, value in supplemental_extra.items():
        extra.setdefault(key, deepcopy(value))
    if extra:
        metrics["extra"] = extra
    projected["final_metrics"] = metrics
    validate_atif_trajectory(projected)
    return projected


def _derived_tool_errors(steps: list[dict[str, Any]]) -> int:
    error_call_ids: set[str] = set()
    anonymous_errors = 0
    for step in steps:
        for result in (step.get("observation") or {}).get("results") or []:
            if not isinstance(result, dict):
                continue
            extra = result.get("extra") if isinstance(result.get("extra"), dict) else {}
            status = str(extra.get("status") or "").lower()
            is_error = extra.get("is_error") is True or any(
                marker in status for marker in ("error", "fail")
            )
            if not is_error:
                continue
            call_id = optional_str(result.get("source_call_id"))
            if call_id:
                error_call_ids.add(call_id)
            else:
                anonymous_errors += 1
    return len(error_call_ids) + anonymous_errors


def _result_final_metrics(result_json: dict[str, Any] | None) -> dict[str, Any]:
    agent_result = (
        result_json.get("agent_result")
        if isinstance((result_json or {}).get("agent_result"), dict)
        else {}
    )
    metrics: dict[str, Any] = {}
    for source_key, target_key in (
        ("n_input_tokens", "total_prompt_tokens"),
        ("n_output_tokens", "total_completion_tokens"),
        ("n_cache_tokens", "total_cached_tokens"),
    ):
        value = agent_result.get(source_key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            metrics[target_key] = value
    cost = agent_result.get("cost_usd")
    if isinstance(cost, (int, float)) and not isinstance(cost, bool) and cost >= 0:
        metrics["total_cost_usd"] = cost
    return metrics


def _harbor_telemetry(
    candidate: SourceCandidate,
    trajectory: dict[str, Any],
) -> tuple[HarborTelemetry | None, str | None]:
    agent = trajectory.get("agent") if isinstance(trajectory.get("agent"), dict) else {}
    adapter = str(agent.get("name") or "").lower()
    telemetry_files = {
        "opencode": HARBOR_OPENCODE_TELEMETRY_FILES,
        "psychevo": HARBOR_PSYCHEVO_TELEMETRY_FILES,
        "hermes": HARBOR_HERMES_TELEMETRY_FILES,
    }.get(adapter)
    if telemetry_files is None:
        return None, None
    session_id = optional_str(trajectory.get("session_id"))
    if not session_id:
        return None, None
    primary = candidate.path / telemetry_files[0]
    try:
        primary_stat = primary.stat(follow_symlinks=False)
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        return None, f"supplemental {adapter} telemetry ignored: {exc}"
    if not stat.S_ISREG(primary_stat.st_mode):
        return None, f"supplemental {adapter} telemetry ignored: not a regular file"
    try:
        files = telemetry_files
        if adapter == "psychevo":
            if (
                Path(session_id).name != session_id
                or "\\" in session_id
                or session_id in {".", ".."}
            ):
                raise ValueError(
                    "Psychevo telemetry session ID is not a safe path segment"
                )
            files = (
                *files,
                f"agent/sessions/{session_id}/events.jsonl",
            )
        contents, revision = _read_consistent_telemetry_files(
            candidate.path,
            candidate.containment_root or candidate.path,
            files,
        )
        conversion = _convert_harbor_telemetry(
            adapter,
            contents,
            session_id,
        )
        if not _telemetry_aligns(
            trajectory,
            conversion.trajectory,
            require_session_identity=adapter != "hermes",
        ):
            raise ValueError(f"{adapter} telemetry does not align with Harbor ATIF")
        started = conversion.started_at_ms or 0
        steps = step_meta_reports(
            conversion.steps_meta,
            started,
            conversion.timestamp_semantics,
        )
        return (
            HarborTelemetry(
                steps=steps,
                duration_ms=trial_active_duration_ms(conversion.steps_meta, steps),
                final_metrics=deepcopy(
                    conversion.trajectory.get("final_metrics") or {}
                ),
                revision=revision,
            ),
            None,
        )
    except Exception as exc:  # noqa: BLE001 - supplemental evidence is optional.
        return None, f"supplemental {adapter} telemetry ignored: {exc}"


def _convert_harbor_telemetry(
    adapter: str,
    contents: dict[str, bytes],
    session_id: str,
):
    with tempfile.TemporaryDirectory(prefix=f"peval-harbor-{adapter}-") as tmp:
        temporary_root = Path(tmp)
        if adapter == "hermes":
            export_path = temporary_root / "hermes-session.jsonl"
            export_path.write_bytes(contents[HARBOR_HERMES_TELEMETRY_FILES[0]])
            return convert_path(str(export_path), ToolConfig(adapter="hermes"))

        files = (
            HARBOR_OPENCODE_TELEMETRY_FILES
            if adapter == "opencode"
            else HARBOR_PSYCHEVO_TELEMETRY_FILES
        )
        database_name = Path(files[0]).name
        temporary_database = temporary_root / database_name
        for relative, content in contents.items():
            name = Path(relative).name
            if name.startswith(database_name):
                (temporary_root / name).write_bytes(content)
            elif adapter == "psychevo" and name == "events.jsonl":
                trace = temporary_root / "sessions" / session_id / name
                trace.parent.mkdir(parents=True)
                trace.write_bytes(content)
        return convert_db(
            str(temporary_database),
            session_id,
            ToolConfig(adapter=adapter),
        )


def _telemetry_aligns(
    trajectory: dict[str, Any],
    telemetry_trajectory: dict[str, Any],
    *,
    require_session_identity: bool = True,
) -> bool:
    source_session_id = optional_str(trajectory.get("session_id"))
    telemetry_session_id = optional_str(telemetry_trajectory.get("session_id"))
    if require_session_identity and (
        not source_session_id or source_session_id != telemetry_session_id
    ):
        return False
    source_steps = trajectory.get("steps")
    telemetry_steps = telemetry_trajectory.get("steps")
    if not isinstance(source_steps, list) or not isinstance(telemetry_steps, list):
        return False
    if len(source_steps) != len(telemetry_steps):
        return False
    for source, telemetry in zip(source_steps, telemetry_steps, strict=True):
        if not isinstance(source, dict) or not isinstance(telemetry, dict):
            return False
        if (source.get("step_id"), source.get("source")) != (
            telemetry.get("step_id"),
            telemetry.get("source"),
        ):
            return False
        source_calls = [
            call.get("tool_call_id")
            for call in source.get("tool_calls") or []
            if isinstance(call, dict)
        ]
        telemetry_calls = [
            call.get("tool_call_id")
            for call in telemetry.get("tool_calls") or []
            if isinstance(call, dict)
        ]
        if source_calls != telemetry_calls:
            return False
        if not _alignment_messages_match(
            source.get("message"), telemetry.get("message")
        ):
            return False
        source_call_shapes = [
            (
                call.get("tool_call_id"),
                call.get("function_name"),
                call.get("arguments"),
            )
            for call in source.get("tool_calls") or []
            if isinstance(call, dict)
        ]
        telemetry_call_shapes = [
            (
                call.get("tool_call_id"),
                call.get("function_name"),
                call.get("arguments"),
            )
            for call in telemetry.get("tool_calls") or []
            if isinstance(call, dict)
        ]
        if source_call_shapes != telemetry_call_shapes:
            return False
    return True


def _alignment_messages_match(left: Any, right: Any) -> bool:
    if not isinstance(left, str) or not isinstance(right, str):
        return left == right
    return bool(_alignment_message_variants(left) & _alignment_message_variants(right))


def _alignment_message_variants(value: str) -> set[str]:
    variants = {value}
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, str):
        variants.add(decoded)
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        inner = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        variants.add(inner)
    return variants


def _read_consistent_telemetry_files(
    trial_dir: Path,
    containment_root: Path,
    relative_files: Iterable[str],
) -> tuple[dict[str, bytes], str]:
    files = tuple(relative_files)
    last_error: Exception | None = None
    for _attempt in range(3):
        before = _file_signature(trial_dir, files)
        contents: dict[str, bytes] = {}
        try:
            for relative in files:
                path = trial_dir / relative
                try:
                    file_stat = path.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if not stat.S_ISREG(file_stat.st_mode):
                    raise ValueError(
                        f"Harbor telemetry file must be a regular file: {path}"
                    )
                contents[relative] = _read_bytes_no_follow(containment_root, path)
        except Exception as exc:  # noqa: BLE001 - retry only if inputs changed.
            last_error = exc
            if before != _file_signature(trial_dir, files):
                continue
            raise
        if before == _file_signature(trial_dir, files):
            if files[0] not in contents:
                raise ValueError(f"Harbor telemetry source not found: {trial_dir}")
            digest = hashlib.sha256()
            for relative, content in sorted(contents.items()):
                digest.update(relative.encode("utf-8") + b"\0" + content + b"\0")
            return contents, digest.hexdigest()
    if last_error is not None:
        raise last_error
    raise ValueError(f"Harbor telemetry changed while it was being read: {trial_dir}")


def _result_duration_ms(
    result_json: dict[str, Any] | None,
    nested_key: str | None = None,
) -> int | None:
    source: Any = result_json
    if nested_key is not None:
        source = (result_json or {}).get(nested_key)
    if not isinstance(source, dict):
        return None
    started = iso_timestamp_ms(source.get("started_at"))
    finished = iso_timestamp_ms(source.get("finished_at"))
    if started is None or finished is None:
        return None
    return max(0, finished - started)


def _result_only_meta(
    candidate: SourceCandidate,
    config_json: dict[str, Any] | None,
    lock_json: dict[str, Any] | None,
    result_json: dict[str, Any] | None,
    revision: str,
    evidence: HarborEvidence,
) -> dict[str, Any]:
    evaluation = _evaluation(result_json)
    identity_hash = hashlib.sha256(candidate.source_ref.encode("utf-8")).hexdigest()[
        :10
    ]
    trial_key = (
        f"harbor-{artifact_segment(candidate.trial_name, 'trial')[:48]}-{identity_hash}"
    )
    trial_name = evidence.trial_name
    data_ref = {
        "kind": HARBOR_SOURCE_KIND,
        "label": f"{candidate.job_name}/{candidate.trial_name}",
        "path": str(candidate.path),
        "source_ref": candidate.source_ref,
        "mount_id": candidate.mount_id,
        "source_revision": revision,
        "trial_name": trial_name,
        "task_name": evidence.task_name,
        "job_name": evidence.job_name,
    }
    data_ref.update(_data_ref_provenance(evidence.provenance))
    meta: dict[str, Any] = {
        "trial_key": trial_key,
        "adapter": HARBOR_ADAPTER,
        "conversion_status": "failed",
        "status": evaluation["status"],
        "failure_class": evaluation.get("failure_class") or "missing-trajectory",
        "score": evaluation.get("score"),
        "score_message": evaluation.get("score_message"),
        "warnings": ["Harbor Trial has no agent/trajectory.json"],
        "data_ref": data_ref,
        "total_events": 0,
        "unmapped_events": 0,
        "prompt_unavailable": True,
        "evaluation": {
            **evaluation,
            "trial_name": trial_name,
            "task_name": evidence.task_name,
            "job_name": evidence.job_name,
            "phase_timing": evidence.phase_timing,
        },
        "task_name": evidence.task_name,
        "job_name": evidence.job_name,
        "trial_name": trial_name,
        "model_provider": evidence.model_provider,
        "task_keywords": list(evidence.task_keywords),
        "rewards": evaluation["rewards"],
        "harbor_provenance": evidence.provenance,
        "task_metadata": evidence.task_metadata,
        "import_context": {
            "kind": HARBOR_SOURCE_KIND,
            "source_revision": revision,
            "config_available": config_json is not None,
            "lock_available": lock_json is not None,
            "result_available": result_json is not None,
        },
        "source_metrics": _result_final_metrics(result_json),
    }
    active = _result_duration_ms(result_json, "agent_execution")
    wall = _result_duration_ms(result_json)
    if active is not None:
        meta["duration_ms"] = active
    if wall is not None:
        meta["wall_duration_ms"] = wall
    return meta


def _result_only_error(
    candidate: SourceCandidate,
    result_json: dict[str, Any] | None,
) -> str:
    exception = (result_json or {}).get("exception_info")
    if isinstance(exception, dict):
        exception_type = optional_str(exception.get("exception_type"))
        exception_message = optional_str(exception.get("exception_message"))
        if exception_type and exception_message:
            return f"{exception_type}: {exception_message}"
        if exception_type or exception_message:
            return exception_type or exception_message or "Harbor Trial failed"
    return f"Harbor Trial has no agent/trajectory.json: {candidate.path}"


def _harbor_source(
    candidate: SourceCandidate,
    overlay: dict[str, Any],
    *,
    trajectory: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    config_json: dict[str, Any] | None = None,
    result_json: dict[str, Any] | None = None,
    evidence: HarborEvidence | None = None,
) -> dict[str, Any]:
    agent = (
        trajectory.get("agent")
        if isinstance((trajectory or {}).get("agent"), dict)
        else {}
    )
    result_agent = (
        result_json.get("agent_info")
        if isinstance((result_json or {}).get("agent_info"), dict)
        else {}
    )
    config_agent = (
        config_json.get("agent")
        if isinstance((config_json or {}).get("agent"), dict)
        else {}
    )
    label = (
        f"{candidate.job_name}/{candidate.trial_name}"
        if candidate.job_name and candidate.trial_name
        else f"Harbor mount: {candidate.mount_id}"
    )
    source_alias = optional_str(overlay.get("source_alias"))
    source_tags = _normalized_tags(overlay.get("source_tags"))
    task_keywords = list(evidence.task_keywords) if evidence is not None else []
    task_name = evidence.task_name if evidence is not None else None
    return {
        "kind": candidate.kind,
        "adapter": HARBOR_ADAPTER,
        "label": label,
        "input_path": None,
        "db_path": None,
        "session_id": optional_str((trajectory or {}).get("session_id")),
        "source_alias": source_alias,
        "source_category": optional_str(overlay.get("source_category")),
        "source_tags": source_tags,
        "display_alias": source_alias or task_name,
        "display_tags": _merged_display_tags(task_keywords, source_tags),
        "task_name": task_name,
        "job_name": evidence.job_name if evidence is not None else candidate.job_name,
        "trial_name": evidence.trial_name
        if evidence is not None
        else candidate.trial_name,
        "model_provider": evidence.model_provider if evidence is not None else None,
        "task_keywords": task_keywords,
        "rewards": _evaluation(result_json)["rewards"],
        "harbor_provenance": evidence.provenance if evidence is not None else {},
        "task_metadata": evidence.task_metadata if evidence is not None else {},
        "agent_name": optional_str(agent.get("name") or result_agent.get("name")),
        "agent_version": optional_str(
            agent.get("version") or result_agent.get("version")
        ),
        "model": optional_str(
            agent.get("model_name") or config_agent.get("model_name")
        ),
        "trial_key": (meta or {}).get("trial_key"),
    }


def _trajectory_meta(
    candidate: SourceCandidate,
    trajectory: dict[str, Any],
    config_json: dict[str, Any] | None,
    lock_json: dict[str, Any] | None,
    result_json: dict[str, Any] | None,
    revision: str,
    *,
    source_schema: str,
    telemetry: HarborTelemetry | None,
    telemetry_warning: str | None,
    evidence: HarborEvidence,
) -> dict[str, Any]:
    evaluation = _evaluation(result_json)
    result_active = _result_duration_ms(result_json, "agent_execution")
    active_duration = (
        telemetry.duration_ms
        if telemetry is not None and telemetry.duration_ms is not None
        else result_active
    )
    wall_duration = _result_duration_ms(result_json)
    agent = trajectory.get("agent") if isinstance(trajectory.get("agent"), dict) else {}
    trial_name = evidence.trial_name
    task_name = evidence.task_name
    job_id = optional_str((config_json or {}).get("job_id"))
    result_id = optional_str((result_json or {}).get("id"))
    identity_hash = hashlib.sha256(candidate.source_ref.encode("utf-8")).hexdigest()[
        :10
    ]
    trial_key = (
        f"harbor-{artifact_segment(candidate.trial_name, 'trial')[:48]}-{identity_hash}"
    )
    data_ref: dict[str, Any] = {
        "kind": HARBOR_SOURCE_KIND,
        "label": f"{candidate.job_name}/{candidate.trial_name}",
        "path": str(candidate.path),
        "source_ref": candidate.source_ref,
        "mount_id": candidate.mount_id,
        "source_revision": revision,
        "trial_name": trial_name,
        "job_name": evidence.job_name,
    }
    data_ref.update(_data_ref_provenance(evidence.provenance))
    for key, value in (
        ("job_id", job_id),
        ("result_id", result_id),
        ("task_name", task_name),
    ):
        if value is not None:
            data_ref[key] = value
    meta: dict[str, Any] = {
        "trial_key": trial_key,
        "adapter": HARBOR_ADAPTER,
        "conversion_status": "passed",
        "status": evaluation["status"],
        "failure_class": evaluation.get("failure_class"),
        "score": evaluation.get("score"),
        "score_message": evaluation.get("score_message"),
        "warnings": [telemetry_warning] if telemetry_warning else [],
        "data_ref": data_ref,
        "total_events": len(trajectory.get("steps") or []),
        "unmapped_events": 0,
        "prompt_unavailable": not any(
            isinstance(step, dict) and step.get("source") == "user"
            for step in trajectory.get("steps") or []
        ),
        "evaluation": {
            **evaluation,
            "trial_name": trial_name,
            "job_name": evidence.job_name,
            **({"task_name": task_name} if task_name else {}),
            **({"job_id": job_id} if job_id else {}),
            **({"result_id": result_id} if result_id else {}),
            "phase_timing": evidence.phase_timing,
        },
        "task_name": task_name,
        "job_name": evidence.job_name,
        "trial_name": trial_name,
        "model_provider": evidence.model_provider,
        "task_keywords": list(evidence.task_keywords),
        "rewards": evaluation["rewards"],
        "harbor_provenance": evidence.provenance,
        "task_metadata": evidence.task_metadata,
        "import_context": {
            "kind": HARBOR_SOURCE_KIND,
            "source_revision": revision,
            "config_available": config_json is not None,
            "lock_available": lock_json is not None,
            "result_available": result_json is not None,
            "agent_name": optional_str(agent.get("name")),
            "source_atif_schema_version": source_schema,
            "supplemental_telemetry": telemetry is not None,
            "source_timing": {
                **(
                    {"duration_ms": active_duration}
                    if active_duration is not None
                    else {}
                ),
                **(
                    {"wall_duration_ms": wall_duration}
                    if wall_duration is not None
                    else {}
                ),
            },
        },
    }
    if telemetry is not None:
        meta["steps"] = telemetry.steps
    if lock_json is not None:
        data_ref["lock_available"] = True
    projected = project_meta_from_atif(trajectory, meta)
    return projected


def _data_ref_provenance(provenance: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "mount_id",
        "job_id",
        "result_id",
        "harbor_version",
        "task_digest",
        "task_digest_source",
        "task_source",
        "task_version",
        "task_checksum",
        "regrade",
    }
    return {key: value for key, value in provenance.items() if key in allowed}


def _merged_display_tags(*values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for tags in values:
        for raw_tag in tags:
            tag = str(raw_tag).strip()
            folded = tag.casefold()
            if not tag or folded in seen:
                continue
            seen.add(folded)
            result.append(tag)
    return result


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
        payload["failure_class"] = (
            optional_str(exception.get("exception_type")) or "harbor-trial"
        )
        payload["exception"] = exception
    return payload


def _read_bytes_no_follow(containment_root: Path, path: Path) -> bytes:
    _assert_safe_descendant(containment_root, path, label="Harbor source")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"cannot read Harbor source file {path}: {exc}") from exc
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError(f"Harbor source file must be a regular file: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            content = handle.read()
    finally:
        os.close(descriptor)
    _assert_safe_descendant(containment_root, path, label="Harbor source")
    return content


def _assert_safe_descendant(root: Path, path: Path, *, label: str) -> None:
    lexical_root = Path(os.path.abspath(root))
    lexical_path = Path(os.path.abspath(path))
    try:
        relative = lexical_path.relative_to(lexical_root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes its root: {path}") from exc
    current = lexical_root
    for part in ("", *relative.parts):
        if part:
            current /= part
        try:
            if current.is_symlink():
                raise ValueError(f"{label} traverses a symlink: {current}")
        except OSError as exc:
            raise ValueError(f"cannot inspect {label} path {current}: {exc}") from exc


def _looks_like_trial(path: Path) -> bool:
    try:
        (path / "agent" / "trajectory.json").stat(follow_symlinks=False)
        return True
    except FileNotFoundError:
        pass
    except OSError:
        return True
    config_path = path / "config.json"
    if _regular_file(config_path):
        try:
            config = read_json_object(config_path)
        except ValueError:
            config = {}
        if any(key in config for key in ("trial_name", "job_id", "trials_dir")):
            return True
    result_path = path / "result.json"
    if _regular_file(result_path):
        try:
            result = read_json_object(result_path)
        except ValueError:
            result = {}
        if any(key in result for key in ("trial_name", "trial_uri", "step_results")):
            return True
    lock_path = path / "lock.json"
    if _regular_file(lock_path):
        try:
            lock = read_json_object(lock_path)
        except ValueError:
            lock = {}
        if any(key in lock for key in ("task", "agent", "environment", "verifier")):
            return True
    steps = path / "steps"
    return (
        any(
            (step / "agent" / "trajectory.json").exists() for step in _child_dirs(steps)
        )
        if steps.is_dir() and not steps.is_symlink()
        else False
    )


def _looks_like_job(path: Path) -> bool:
    config_path = path / "config.json"
    if _regular_file(config_path):
        try:
            config = read_json_object(config_path)
        except ValueError:
            config = {}
        if any(key in config for key in ("job_name", "jobs_dir", "tasks", "agents")):
            return True
    return any(_looks_like_trial(child) for child in _child_dirs(path))


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


def _child_dirs(root: Path) -> Iterator[Path]:
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


def _reject_linked_directories(root: Path, kind: str) -> None:
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                if entry.is_symlink() and entry.is_dir(follow_symlinks=True):
                    raise ValueError(
                        f"Harbor {kind} directory must not be a symlink: {entry.path}"
                    )
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError(f"cannot scan Harbor directory {root}: {exc}") from exc


def _regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink() and not path.parent.is_symlink()


def _path_has_symlink(path: Path) -> bool:
    current = path
    while True:
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
        if current.parent == current:
            return False
        current = current.parent


def _harbor_source_files(trial_dir: Path) -> tuple[str, ...]:
    """Include late-arriving Psychevo trace state in the rebuildable fingerprint."""

    relative_sessions = "agent/sessions"
    files = [*HARBOR_SOURCE_FILES, relative_sessions]
    sessions = trial_dir / relative_sessions
    try:
        sessions_stat = sessions.stat(follow_symlinks=False)
    except OSError:
        return tuple(files)
    if not stat.S_ISDIR(sessions_stat.st_mode):
        return tuple(files)
    try:
        with os.scandir(sessions) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name)
    except OSError:
        return tuple(files)
    for entry in ordered:
        relative_session = f"{relative_sessions}/{entry.name}"
        files.append(relative_session)
        try:
            if entry.is_dir(follow_symlinks=False):
                files.append(f"{relative_session}/events.jsonl")
        except OSError:
            continue
    return tuple(files)


def _fingerprint(
    root: Path,
    relative_files: Iterable[str],
    *,
    extra_root: Path | None = None,
    extra_files: Iterable[str] = (),
) -> str:
    parts = _signature_parts(root, relative_files)
    if extra_root is not None:
        parts.extend(_signature_parts(extra_root, extra_files, prefix="overlay/"))
    return _text_fingerprint("\n".join(parts))


def _combined_revision(*values: str) -> str:
    return _text_fingerprint("\0".join(values))


def _file_signature(root: Path, relative_files: Iterable[str]) -> tuple[str, ...]:
    return tuple(_signature_parts(root, relative_files))


def _signature_parts(
    root: Path, relative_files: Iterable[str], *, prefix: str = ""
) -> list[str]:
    parts: list[str] = []
    for relative in relative_files:
        path = root / relative
        try:
            stat = path.stat(follow_symlinks=False)
            parts.append(
                f"{prefix}{relative}:{stat.st_size}:{stat.st_mtime_ns}:"
                f"{stat.st_ctime_ns}:{stat.st_ino}:{stat.st_mode}"
            )
        except FileNotFoundError:
            parts.append(f"{prefix}{relative}:-")
        except OSError as exc:
            parts.append(f"{prefix}{relative}:error:{exc.errno}")
    return parts


def _text_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _updated_at_ms(root: Path, relative_files: Iterable[str]) -> int:
    values: list[int] = []
    for relative in relative_files:
        try:
            values.append(
                (root / relative).stat(follow_symlinks=False).st_mtime_ns // 1_000_000
            )
        except OSError:
            continue
    return max(values) if values else 0


def _input_bytes(root: Path, relative_files: Iterable[str]) -> int:
    total = 0
    for relative in relative_files:
        try:
            file_stat = (root / relative).stat(follow_symlinks=False)
            if stat.S_ISREG(file_stat.st_mode):
                total += file_stat.st_size
        except OSError:
            continue
    return total


def _normalized_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for raw in value:
        text = str(raw or "").strip()
        folded = text.casefold()
        if text and folded not in seen:
            seen.add(folded)
            tags.append(text)
    return tags


def _nested_string(value: dict[str, Any] | None, *keys: str) -> str | None:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return optional_str(current)
