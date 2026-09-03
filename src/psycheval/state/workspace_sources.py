from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Any, Literal

from psycheval._state.annotations import optional_str
from psycheval._state.artifacts import (
    read_json_object,
    source_key_for_trial,
    source_key_for_trial_cell_components,
    trial_artifacts,
    write_json_file,
)
from psycheval.atif import validate_atif_trajectory
from psycheval.config import HarborMount, ToolConfig, validate_harbor_mount_paths
from psycheval.harbor.datasets import (
    ResolvedHarborDataset,
    resolve_harbor_datasets_for_mount,
)
from psycheval.state.constants import SOURCE_STATE_DIR, SOURCE_STATE_FILENAME
from psycheval.state.harbor_evidence import (
    HarborTaskIndex,
    read_harbor_evidence,
    read_harbor_task_index,
)
from psycheval.state.harbor_verifier_evidence import (
    HarborVerifierArtifact,
    HarborVerifierArtifactStream,
    open_harbor_verifier_artifact_download,
    read_harbor_verifier_artifact,
    read_harbor_verifier_evidence,
)
from psycheval.state.workspace_harbor import (
    HARBOR_ANALYSIS_MAX_BYTES,
    _assert_safe_descendant,
    _child_dirs,
    _combined_revision,
    _compatible_harbor_trajectory,
    _direct_harbor_candidate,
    _evaluation,
    _fingerprint,
    _harbor_analysis_relative_path,
    _harbor_candidate_source_files,
    _harbor_entry_source_files,
    _harbor_source,
    _harbor_telemetry,
    _harbor_trial_key,
    _input_bytes,
    _is_multi_step_trial,
    _looks_like_job,
    _looks_like_trial,
    _normalized_tags,
    _path_has_symlink,
    _project_harbor_metrics,
    _read_bytes_no_follow,
    _read_harbor_analysis_markdown,
    _read_harbor_entry_trajectory,
    _regular_file,
    _reject_linked_directories,
    _result_only_error,
    _result_only_meta,
    _trajectory_meta,
    _updated_at_ms,
)
from psycheval.state.workspace_harbor import (
    is_harbor_source as is_harbor_source,
)
from psycheval.state.workspace_source_models import (
    HARBOR_ANALYSIS_MD_FILE,
    HARBOR_JSON_SOURCE_FILES,
    HARBOR_OVERLAY_FILES,
    HARBOR_OVERLAY_ROOT,
    HARBOR_OVERLAY_SCHEMA_VERSION,
    HARBOR_OVERLAY_STATE_FIELDS,
    HARBOR_SOURCE_KIND,
    LOCAL_FINGERPRINT_FILES,
    SourceCandidate,
    SourceDocument,
)

if TYPE_CHECKING:
    from psycheval._harbor_trials import HarborTrialBundle, HarborTrialEntry

_LOCAL_SOURCE_FILES_WITHOUT_REPORT = tuple(
    name for name in LOCAL_FINGERPRINT_FILES if name != HARBOR_ANALYSIS_MD_FILE
)
_HARBOR_IDENTITY_JSON_MAX_BYTES = 4 * 1024 * 1024


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

    def read_harbor_verifier_artifact(
        self,
        source_ref: str,
        artifact_id: str,
        *,
        purpose: Literal["preview", "download"],
    ) -> HarborVerifierArtifact:
        if purpose not in {"preview", "download"}:
            raise ValueError("unsupported verifier artifact purpose")
        data_dir, containment_root = self._workbuddy_artifact_location(source_ref)
        return read_harbor_verifier_artifact(
            data_dir,
            containment_root=containment_root,
            artifact_id=artifact_id,
            purpose=purpose,
        )

    def open_harbor_verifier_artifact_download(
        self,
        source_ref: str,
        artifact_id: str,
    ) -> HarborVerifierArtifactStream:
        data_dir, containment_root = self._workbuddy_artifact_location(source_ref)
        return open_harbor_verifier_artifact_download(
            data_dir,
            containment_root=containment_root,
            artifact_id=artifact_id,
        )

    def _workbuddy_artifact_location(self, source_ref: str) -> tuple[Path, Path]:
        self._reject_legacy_harbor_projections()
        self.overlay_dir(source_ref)
        parts = Path(source_ref).parts
        mount_id, job_name, trial_name = parts[1:4]
        mount = next(
            (item for item in self.config.harbor_mounts if item.id == mount_id),
            None,
        )
        if mount is None:
            raise ValueError("unknown Harbor Trial source")
        datasets_by_id = {
            dataset.id: dataset for dataset in self.config.harbor_datasets
        }
        mount_datasets = tuple(
            datasets_by_id[dataset_id]
            for dataset_id in mount.dataset_ids
            if dataset_id in datasets_by_id
        )
        validate_harbor_mount_paths((mount,), mount_datasets)
        lexical_root = Path(os.path.abspath(Path(mount.path).expanduser()))
        diagnostic = self._mount_diagnostic(lexical_root)
        if diagnostic is not None:
            raise ValueError(diagnostic)
        root = lexical_root.resolve()
        job_dir = self._direct_harbor_directory(root, job_name, "Job")
        trial_dir = self._direct_harbor_directory(job_dir, trial_name, "Trial")
        if not _looks_like_trial(trial_dir):
            raise ValueError("unknown Harbor Trial source")
        resolved = resolve_harbor_datasets_for_mount(self.config, mount)
        formats = {dataset.format for dataset in resolved}
        if "workbuddy.v1" not in formats:
            raise ValueError("Harbor Trial has no WorkBuddy verifier artifacts")
        if len(formats) > 1 and not _trial_records_workbuddy_task(trial_dir, resolved):
            raise ValueError("Harbor Trial has no WorkBuddy verifier artifacts")
        data_dir = trial_dir
        if len(parts) == 6:
            steps_dir = self._direct_harbor_directory(trial_dir, "steps", "Steps")
            data_dir = self._direct_harbor_directory(steps_dir, parts[5], "Step")
        return data_dir, root

    def load(
        self,
        candidate: SourceCandidate,
        *,
        include_evaluation_report: bool = True,
    ) -> SourceDocument:
        if candidate.kind == "artifact-cell":
            return self._load_local(
                candidate,
                include_evaluation_report=include_evaluation_report,
            )
        return self._load_harbor(
            candidate,
            include_evaluation_report=include_evaluation_report,
        )

    def load_ref(
        self,
        source_ref: str,
        *,
        include_evaluation_report: bool = True,
    ) -> SourceDocument:
        wanted = str(source_ref or "").strip()
        if wanted.startswith(f"{HARBOR_OVERLAY_ROOT}/"):
            return self.load(
                self._harbor_candidate_for_ref(
                    wanted,
                    include_evaluation_report=include_evaluation_report,
                ),
                include_evaluation_report=include_evaluation_report,
            )
        if not include_evaluation_report:
            candidate = self._local_candidate_for_ref(wanted)
            return self.load(candidate, include_evaluation_report=False)
        for candidate in self.discover():
            if candidate.source_ref == wanted:
                return self.load(
                    candidate,
                    include_evaluation_report=include_evaluation_report,
                )
        raise ValueError(f"unknown source reference: {wanted}")

    def _harbor_candidate_for_ref(
        self,
        source_ref: str,
        *,
        include_evaluation_report: bool = True,
    ) -> SourceCandidate:
        candidates = self.harbor_candidates_for_ref(
            source_ref,
            include_evaluation_report=include_evaluation_report,
        )
        if len(candidates) != 1:
            raise ValueError(
                "parent MultiStep Harbor source reference identifies multiple phases; "
                "select /steps/<name>"
            )
        return candidates[0]

    def harbor_candidates_for_ref(
        self,
        source_ref: str,
        *,
        include_evaluation_report: bool = True,
    ) -> list[SourceCandidate]:
        self._reject_legacy_harbor_projections()
        overlay_root = self.workspace_root / HARBOR_OVERLAY_ROOT
        if overlay_root.is_symlink():
            raise ValueError("workspace Harbor overlay root must not be a symlink")
        self.overlay_dir(source_ref)
        parts = Path(source_ref).parts
        mount_id, job_name, trial_name = parts[1:4]
        mount = next(
            (
                candidate
                for candidate in self.config.harbor_mounts
                if candidate.id == mount_id
            ),
            None,
        )
        if mount is None:
            raise ValueError(f"unknown source reference: {source_ref}")
        datasets_by_id = {
            dataset.id: dataset for dataset in self.config.harbor_datasets
        }
        mount_datasets = tuple(
            datasets_by_id[dataset_id]
            for dataset_id in mount.dataset_ids
            if dataset_id in datasets_by_id
        )
        validate_harbor_mount_paths((mount,), mount_datasets)
        lexical_root = Path(os.path.abspath(Path(mount.path).expanduser()))
        diagnostic = self._mount_diagnostic(lexical_root)
        if diagnostic is not None:
            raise ValueError(diagnostic)
        root = lexical_root.resolve()
        job_dir = self._direct_harbor_directory(root, job_name, "Job")
        trial_dir = self._direct_harbor_directory(job_dir, trial_name, "Trial")
        if not _looks_like_trial(trial_dir):
            raise ValueError(f"unknown source reference: {source_ref}")
        resolved_datasets = resolve_harbor_datasets_for_mount(self.config, mount)
        dataset_paths = tuple(str(item.task_root) for item in resolved_datasets)
        task_index = read_harbor_task_index(
            dataset_paths,
            dataset_formats=(item.format for item in resolved_datasets),
        )
        candidates = self._harbor_trial_candidates(
            mount,
            job_name,
            trial_name,
            trial_dir,
            root,
            task_index,
            dataset_paths,
            include_evaluation_report=include_evaluation_report,
        )
        if len(parts) == 4:
            return candidates
        for candidate in candidates:
            if candidate.source_ref == source_ref:
                return [candidate]
        raise ValueError(f"unknown source reference: {source_ref}")

    def _local_candidate_for_ref(self, source_ref: str) -> SourceCandidate:
        path = self.annotation_dir(source_ref)
        parts = Path(source_ref).parts
        if (
            parts[1] != self.config.analysis_eval_slug
            or not path.is_dir()
            or _path_has_symlink(path)
        ):
            raise ValueError(f"unknown source reference: {source_ref}")
        artifacts = trial_artifacts(path)
        state_path = path / SOURCE_STATE_DIR / SOURCE_STATE_FILENAME
        if not (
            _regular_file(artifacts.trajectory_path)
            and _regular_file(artifacts.meta_path)
        ) and not _regular_file(state_path):
            raise ValueError(f"unknown source reference: {source_ref}")
        return SourceCandidate(
            source_ref=source_ref,
            kind="artifact-cell",
            path=path,
            fingerprint=_fingerprint(path, _LOCAL_SOURCE_FILES_WITHOUT_REPORT),
        )

    @staticmethod
    def _direct_harbor_directory(root: Path, name: str, kind: str) -> Path:
        path = root / name
        _assert_safe_descendant(root, path, label=f"Harbor {kind}")
        if _path_has_symlink(path):
            raise ValueError(f"Harbor {kind} directory must not be a symlink: {path}")
        if not path.is_dir():
            raise ValueError(f"Harbor {kind} directory not found: {path}")
        return path

    def overlay_dir(self, source_ref: str) -> Path:
        parts = Path(str(source_ref)).parts
        if (
            len(parts) not in {4, 6}
            or parts[0] != HARBOR_OVERLAY_ROOT
            or (len(parts) == 6 and parts[4] != "steps")
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
        validate_harbor_mount_paths(
            self.config.harbor_mounts,
            self.config.harbor_datasets,
        )
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
            resolved_datasets = resolve_harbor_datasets_for_mount(self.config, mount)
            dataset_paths = tuple(str(item.task_root) for item in resolved_datasets)
            task_index = read_harbor_task_index(
                dataset_paths,
                dataset_formats=(item.format for item in resolved_datasets),
            )
            for job_dir in _child_dirs(root):
                _reject_linked_directories(job_dir, "Trial")
                for trial_dir in _child_dirs(job_dir):
                    if not _looks_like_trial(trial_dir):
                        continue
                    trial_candidates = self._harbor_trial_candidates(
                        mount,
                        job_dir.name,
                        trial_dir.name,
                        trial_dir,
                        root,
                        task_index,
                        dataset_paths,
                    )
                    candidates.extend(trial_candidates)
                    present_refs.update(
                        candidate.source_ref for candidate in trial_candidates
                    )
        return candidates, present_refs

    def _harbor_trial_candidates(
        self,
        mount: HarborMount,
        job_name: str,
        trial_name: str,
        trial_dir: Path,
        mount_root: Path,
        task_index: HarborTaskIndex,
        dataset_paths: tuple[str, ...],
        *,
        include_evaluation_report: bool = True,
    ) -> list[SourceCandidate]:
        from psycheval._harbor_trials import load_harbor_trial_bundle

        source_ref = f"harbor/{mount.id}/{job_name}/{trial_name}"
        try:
            bundle = load_harbor_trial_bundle(
                trial_dir,
                jobs_root=mount_root,
                task_paths=dataset_paths,
                mount_id=mount.id,
                source_ref=source_ref,
                task_index=task_index,
            )
        except (OSError, ValueError) as exc:
            overlay_dir = self.overlay_dir(source_ref)
            return [
                SourceCandidate(
                    source_ref=source_ref,
                    kind=HARBOR_SOURCE_KIND,
                    path=trial_dir,
                    fingerprint=_fingerprint(
                        trial_dir,
                        HARBOR_JSON_SOURCE_FILES,
                        extra_root=overlay_dir,
                        extra_files=HARBOR_OVERLAY_FILES,
                    ),
                    source_key=_harbor_trial_key(mount.id, job_name, trial_name),
                    mount_id=mount.id,
                    job_name=job_name,
                    trial_name=trial_name,
                    diagnostic=str(exc),
                    multi_step=_is_multi_step_trial(trial_dir),
                    containment_root=mount_root,
                    task_paths=dataset_paths,
                )
            ]
        return [
            self._candidate_for_harbor_entry(
                bundle,
                entry,
                include_evaluation_report=include_evaluation_report,
            )
            for entry in bundle.entries
        ]

    def _candidate_for_harbor_entry(
        self,
        bundle: HarborTrialBundle,
        entry: HarborTrialEntry,
        *,
        include_evaluation_report: bool = True,
    ) -> SourceCandidate:
        assert entry.source_ref is not None
        job_name = bundle.trial_dir.parent.name
        trial_name = bundle.trial_dir.name
        overlay_dir = self.overlay_dir(entry.source_ref)
        analysis_relative_path = (
            _harbor_analysis_relative_path(bundle.trial_dir)
            if include_evaluation_report
            else None
        )
        source_files = _harbor_entry_source_files(entry, None)
        fingerprint_files = (
            (*source_files, HARBOR_ANALYSIS_MD_FILE)
            if include_evaluation_report
            else source_files
        )
        return SourceCandidate(
            source_ref=entry.source_ref,
            kind=HARBOR_SOURCE_KIND,
            path=bundle.trial_dir,
            data_path=entry.data_dir,
            fingerprint=_combined_revision(
                _fingerprint(
                    bundle.trial_dir,
                    fingerprint_files,
                    extra_root=overlay_dir,
                    extra_files=HARBOR_OVERLAY_FILES,
                ),
                bundle.evidence.revision,
            ),
            source_key=_harbor_trial_key(
                entry.mount_id or "direct",
                job_name,
                trial_name,
                entry.step_name,
            ),
            mount_id=entry.mount_id,
            job_name=job_name,
            trial_name=trial_name,
            multi_step=entry.step_name is not None,
            containment_root=bundle.jobs_root,
            task_paths=entry.task_paths,
            harbor_evidence=bundle.evidence,
            harbor_analysis_relative_path=analysis_relative_path,
            step_name=entry.step_name,
            step_index=entry.step_index,
            step_count=entry.step_count,
            step_result=entry.result,
            trial_result=entry.trial_result,
            entry_warnings=entry.warnings,
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
                        steps_dir = trial_dir / "steps"
                        for step_dir in _child_dirs(steps_dir):
                            if any(
                                _regular_file(step_dir / name)
                                for name in HARBOR_OVERLAY_FILES
                            ):
                                retained_refs.add(
                                    "harbor/"
                                    f"{mount_dir.name}/{job_dir.name}/{trial_dir.name}"
                                    f"/steps/{step_dir.name}"
                                )
        retained: list[SourceCandidate] = []
        for source_ref in sorted(retained_refs - present_refs):
            parts = Path(source_ref).parts
            if len(parts) not in {4, 6}:
                continue
            step_name = None
            if len(parts) == 4:
                _harbor, mount_id, job_name, trial_name = parts
            else:
                _harbor, mount_id, job_name, trial_name, steps, step_name = parts
                if steps != "steps":
                    continue
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
                    source_key=_harbor_trial_key(
                        mount_id, job_name, trial_name, step_name
                    ),
                    mount_id=mount_id,
                    job_name=job_name,
                    trial_name=trial_name,
                    step_name=step_name,
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

    def _load_local(
        self,
        candidate: SourceCandidate,
        *,
        include_evaluation_report: bool = True,
    ) -> SourceDocument:
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
        presentation_files = (
            LOCAL_FINGERPRINT_FILES
            if include_evaluation_report
            else _LOCAL_SOURCE_FILES_WITHOUT_REPORT
        )
        timestamp = _updated_at_ms(cell_dir, presentation_files)
        input_bytes = _input_bytes(cell_dir, presentation_files)
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
            evaluation_report_markdown = (
                _read_local_evaluation_report(candidate)
                if include_evaluation_report
                else None
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
                evaluation_report_markdown=evaluation_report_markdown,
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

    @classmethod
    def load_direct_harbor_entry(
        cls,
        bundle: HarborTrialBundle,
        entry: HarborTrialEntry,
    ) -> SourceDocument:
        candidate = _direct_harbor_candidate(bundle, entry)
        instance = object.__new__(cls)
        return instance._load_harbor(candidate, direct=True)

    def _load_harbor(
        self,
        candidate: SourceCandidate,
        *,
        direct: bool = False,
        include_evaluation_report: bool = True,
    ) -> SourceDocument:
        assert candidate.source_key is not None
        harbor_analysis_markdown = (
            _read_harbor_analysis_markdown(candidate)
            if include_evaluation_report
            else None
        )
        analysis_revision = (
            hashlib.sha256(harbor_analysis_markdown.encode("utf-8")).hexdigest()
            if harbor_analysis_markdown is not None
            else None
        )
        try:
            overlay = (
                self.read_overlay(candidate.source_ref)
                if candidate.kind == HARBOR_SOURCE_KIND and not direct
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
        source_files = _harbor_candidate_source_files(candidate)
        presentation_files = (
            (*source_files, HARBOR_ANALYSIS_MD_FILE)
            if include_evaluation_report
            else source_files
        )
        timestamp = _updated_at_ms(candidate.path, presentation_files)

        def current_fingerprint(*, revision: str | None = None) -> str:
            if direct:
                fingerprint = _fingerprint(candidate.path, presentation_files)
            else:
                fingerprint = _fingerprint(
                    candidate.path,
                    presentation_files,
                    extra_root=self.overlay_dir(candidate.source_ref),
                    extra_files=HARBOR_OVERLAY_FILES,
                )
            return (
                _combined_revision(fingerprint, revision) if revision else fingerprint
            )

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
                evaluation_report_markdown=harbor_analysis_markdown,
            )
        values: dict[str, dict[str, Any] | None] = {}
        try:
            evidence = candidate.harbor_evidence or read_harbor_evidence(
                candidate.path,
                jobs_root=candidate.containment_root or candidate.path.parent.parent,
                task_paths=candidate.task_paths,
                mount_id=candidate.mount_id,
            )
            values = evidence.trial_values
            evidence_revision = _combined_revision(
                _fingerprint(candidate.path, source_files),
                evidence.source_revision,
            )
            revision = evidence.revision
            config_json = values.get("config.json")
            lock_json = values.get("lock.json")
            trial_result_json = values.get("result.json")
            result_json = (
                candidate.step_result
                if candidate.step_name is not None
                else trial_result_json
            )
            verifier_evidence = None
            if evidence.dataset_format == "workbuddy.v1":
                verifier_evidence = read_harbor_verifier_evidence(
                    candidate.data_path or candidate.path,
                    containment_root=candidate.containment_root or candidate.path,
                    dataset_format=evidence.dataset_format,
                    harbor_reward=_evaluation(result_json).get("score"),
                )
                revision = _combined_revision(revision, verifier_evidence.revision)
                evidence_revision = _combined_revision(
                    evidence_revision, verifier_evidence.revision
                )
            raw_trajectory = (
                _read_harbor_entry_trajectory(candidate)
                if candidate.step_name is not None
                else values.get("agent/trajectory.json")
            )
            if raw_trajectory is None:
                meta = _result_only_meta(
                    candidate,
                    config_json,
                    lock_json,
                    result_json,
                    revision,
                    evidence,
                    verifier_evidence,
                    trial_result_json=trial_result_json,
                )
                source = _harbor_source(
                    candidate,
                    overlay,
                    meta=meta,
                    config_json=config_json,
                    result_json=result_json,
                    trial_result_json=trial_result_json,
                    evidence=evidence,
                    verifier_evidence=verifier_evidence,
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
                    fingerprint=current_fingerprint(revision=revision),
                    updated_at_ms=_updated_at_ms(candidate.path, presentation_files),
                    input_bytes=_input_bytes(candidate.path, presentation_files),
                    readable=False,
                    refreshable=True,
                    snapshot=False,
                    active=bool(overlay.get("active", True)),
                    last_status=last_status,
                    last_error=_result_only_error(candidate, result_json),
                    harbor_analysis_markdown=harbor_analysis_markdown,
                    harbor_analysis_relative_path=(
                        candidate.harbor_analysis_relative_path
                        if harbor_analysis_markdown
                        else None
                    ),
                    evaluation_report_markdown=harbor_analysis_markdown,
                    evidence_revision=evidence_revision,
                    analysis_revision=analysis_revision,
                )
            trajectory, source_schema = _compatible_harbor_trajectory(
                raw_trajectory,
                (candidate.data_path or candidate.path) / "agent" / "trajectory.json",
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
                verifier_evidence=verifier_evidence,
                trial_result_json=trial_result_json,
            )
            source = _harbor_source(
                candidate,
                overlay,
                trajectory=trajectory,
                meta=meta,
                config_json=config_json,
                result_json=result_json,
                trial_result_json=trial_result_json,
                evidence=evidence,
                verifier_evidence=verifier_evidence,
            )
            return SourceDocument(
                source_ref=candidate.source_ref,
                source_key=candidate.source_key,
                source=source,
                trajectory=trajectory,
                meta=meta,
                fingerprint=current_fingerprint(revision=revision),
                updated_at_ms=_updated_at_ms(candidate.path, presentation_files),
                input_bytes=_input_bytes(candidate.path, presentation_files),
                readable=True,
                refreshable=True,
                snapshot=False,
                active=bool(overlay.get("active", True)),
                last_status="ok",
                last_error=None,
                harbor_analysis_markdown=harbor_analysis_markdown,
                harbor_analysis_relative_path=(
                    candidate.harbor_analysis_relative_path
                    if harbor_analysis_markdown
                    else None
                ),
                evaluation_report_markdown=harbor_analysis_markdown,
                evidence_revision=evidence_revision,
                analysis_revision=analysis_revision,
            )
        except Exception as exc:  # noqa: BLE001 - one Trial becomes one diagnostic.
            source = _harbor_source(
                candidate,
                overlay,
                config_json=values.get("config.json"),
                result_json=(
                    candidate.step_result
                    if candidate.step_name is not None
                    else values.get("result.json")
                ),
                trial_result_json=values.get("result.json"),
                evidence=candidate.harbor_evidence,
            )
            return SourceDocument(
                source_ref=candidate.source_ref,
                source_key=candidate.source_key,
                source=source,
                trajectory=None,
                meta=None,
                fingerprint=current_fingerprint(),
                updated_at_ms=_updated_at_ms(candidate.path, presentation_files),
                input_bytes=_input_bytes(candidate.path, presentation_files),
                readable=False,
                refreshable=True,
                snapshot=False,
                active=bool(overlay.get("active", True)),
                last_status="error",
                last_error=str(exc),
                evaluation_report_markdown=harbor_analysis_markdown,
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
                    "peval workspace instead of reusing harbor-link.json state"
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


def _read_local_evaluation_report(candidate: SourceCandidate) -> str | None:
    path = candidate.path / HARBOR_ANALYSIS_MD_FILE
    if not _regular_file(path):
        return None
    try:
        content = _read_bytes_no_follow(
            candidate.path,
            path,
            max_bytes=HARBOR_ANALYSIS_MAX_BYTES,
        )
        markdown = content.decode("utf-8")
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return markdown if markdown.strip() else None


def _trial_records_workbuddy_task(
    trial_dir: Path,
    datasets: tuple[ResolvedHarborDataset, ...],
) -> bool:
    recorded_paths: list[str] = []
    for filename in ("config.json", "lock.json", "result.json"):
        try:
            content = _read_bytes_no_follow(
                trial_dir.parent.parent,
                trial_dir / filename,
                max_bytes=_HARBOR_IDENTITY_JSON_MAX_BYTES,
                label="Harbor Trial identity",
            )
            value = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict):
            continue
        for key in ("task", "task_id"):
            task = value.get(key)
            if isinstance(task, dict) and isinstance(task.get("path"), str):
                recorded_paths.append(task["path"])
    for recorded in recorded_paths:
        matches = {
            dataset.format
            for dataset in datasets
            for task_name in dataset.task_names
            if _recorded_task_path_matches(
                dataset.task_root / task_name,
                recorded,
            )
        }
        if matches == {"workbuddy.v1"}:
            return True
    return False


def _recorded_task_path_matches(candidate: Path, recorded: str) -> bool:
    text = recorded.strip().replace("\\", "/")
    if not text:
        return False
    requested = Path(text)
    if requested.is_absolute():
        return os.path.normcase(os.path.normpath(candidate)) == os.path.normcase(
            os.path.normpath(requested)
        )
    requested_parts = tuple(
        os.path.normcase(part)
        for part in PurePath(text).parts
        if part not in {"", ".", ".."} and not part.endswith(":")
    )
    candidate_parts = tuple(os.path.normcase(part) for part in candidate.parts)
    return bool(requested_parts) and candidate_parts[-len(requested_parts) :] == (
        requested_parts
    )
