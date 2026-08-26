from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from psycheval._state.annotations import optional_str
from psycheval.config import (
    HarborMount,
    ToolConfig,
    harbor_dataset_paths_for_mount,
)
from psycheval.state.harbor_evidence import (
    HarborTaskIndex,
    read_harbor_evidence,
    read_harbor_task_index,
)


@dataclass(frozen=True)
class HarborTrialEntry:
    """One inspectable trajectory source within a Harbor Trial."""

    source_ref: str | None
    trial_dir: Path
    data_dir: Path
    job_name: str
    trial_name: str
    mount_id: str | None
    task_paths: tuple[str, ...]
    step_name: str | None
    step_index: int | None
    step_count: int | None
    result: dict[str, Any] | None
    trial_result: dict[str, Any] | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class HarborTrialBundle:
    """A consistent Harbor Trial identity plus its ordered trajectory entries."""

    trial_dir: Path
    jobs_root: Path
    mount_id: str | None
    source_ref: str | None
    task_paths: tuple[str, ...]
    task_index: HarborTaskIndex
    evidence: Any
    entries: tuple[HarborTrialEntry, ...]


def project_harbor_trial_bundle(bundle: HarborTrialBundle) -> list[Any]:
    """Project every bundle entry through the shared read-only Harbor seam."""

    from psycheval.state.workspace_sources import WorkspaceSources

    return [
        WorkspaceSources.load_direct_harbor_entry(bundle, entry)
        for entry in bundle.entries
    ]


def is_harbor_trial_dir(path: Path) -> bool:
    """Recognize only a Harbor Trial root, never one of its descendants."""

    try:
        if not path.is_dir() or path.is_symlink():
            return False
    except OSError:
        return False
    if path.parent.name == "steps":
        return False
    for filename, identity_keys in (
        ("config.json", {"trial_name", "job_id", "task"}),
        ("lock.json", {"task", "agent", "environment", "verifier"}),
        ("result.json", {"trial_name", "trial_uri", "step_results"}),
    ):
        value = _read_optional_object(path / filename)
        if value is not None and identity_keys.intersection(value):
            return True
    return False


def load_harbor_trial_bundle(
    trial_dir: Path,
    *,
    jobs_root: Path | None = None,
    mount_id: str | None = None,
    source_ref: str | None = None,
    task_paths: Iterable[str] = (),
    task_index: HarborTaskIndex | None = None,
) -> HarborTrialBundle:
    """Read one Harbor Trial and expose its sources in authoritative order."""

    lexical_trial = Path(os.path.abspath(trial_dir.expanduser()))
    _reject_symlink_chain(lexical_trial)
    if not is_harbor_trial_dir(lexical_trial):
        raise ValueError(f"not a Harbor Trial directory: {trial_dir}")
    resolved_trial = lexical_trial.resolve()
    resolved_jobs = (
        Path(os.path.abspath(jobs_root.expanduser())).resolve()
        if jobs_root is not None
        else resolved_trial.parent.parent
    )
    try:
        resolved_trial.relative_to(resolved_jobs)
    except ValueError as exc:
        raise ValueError(
            f"Harbor Trial is outside its jobs root: {resolved_trial}"
        ) from exc
    normalized_task_paths = tuple(str(path) for path in task_paths)
    index = task_index or read_harbor_task_index(normalized_task_paths)
    evidence = read_harbor_evidence(
        resolved_trial,
        jobs_root=resolved_jobs,
        task_paths=normalized_task_paths,
        mount_id=mount_id,
        task_index=index,
    )
    trial_result = evidence.trial_values.get("result.json")
    entries = _trial_entries(
        resolved_trial,
        source_ref=source_ref,
        mount_id=mount_id,
        task_paths=normalized_task_paths,
        job_name=evidence.job_name,
        trial_name=evidence.trial_name,
        trial_result=trial_result,
    )
    return HarborTrialBundle(
        trial_dir=resolved_trial,
        jobs_root=resolved_jobs,
        mount_id=mount_id,
        source_ref=source_ref,
        task_paths=normalized_task_paths,
        task_index=index,
        evidence=evidence,
        entries=entries,
    )


def load_direct_harbor_trial_bundle(
    raw_path: str,
    config: ToolConfig,
) -> HarborTrialBundle | None:
    """Resolve a direct CLI path, enriching it only through a matching mount."""

    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = Path(os.path.abspath(path))
    if path.is_symlink() and is_harbor_trial_dir(path.resolve()):
        raise ValueError(f"Harbor Trial path traverses a symlink: {path}")
    if not is_harbor_trial_dir(path):
        return None
    mount = _matching_mount(path, config.harbor_mounts)
    if mount is None:
        return load_harbor_trial_bundle(path)
    task_paths = harbor_dataset_paths_for_mount(config, mount)
    source_ref = f"harbor/{mount.id}/{path.parent.name}/{path.name}"
    return load_harbor_trial_bundle(
        path,
        jobs_root=Path(mount.path),
        mount_id=mount.id,
        source_ref=source_ref,
        task_paths=task_paths,
    )


def entry_source_ref(base: str | None, step_name: str | None) -> str | None:
    if base is None or step_name is None:
        return base
    return f"{base}/steps/{step_name}"


def _trial_entries(
    trial_dir: Path,
    *,
    source_ref: str | None,
    mount_id: str | None,
    task_paths: tuple[str, ...],
    job_name: str,
    trial_name: str,
    trial_result: dict[str, Any] | None,
) -> tuple[HarborTrialEntry, ...]:
    step_results = (
        trial_result.get("step_results")
        if isinstance((trial_result or {}).get("step_results"), list)
        else []
    )
    steps_dir = trial_dir / "steps"
    step_dirs = {
        child.name: child
        for child in _child_dirs(steps_dir)
        if _safe_segment(child.name)
    }
    if not step_results and not step_dirs:
        return (
            HarborTrialEntry(
                source_ref=source_ref,
                trial_dir=trial_dir,
                data_dir=trial_dir,
                job_name=job_name,
                trial_name=trial_name,
                mount_id=mount_id,
                task_paths=task_paths,
                step_name=None,
                step_index=None,
                step_count=None,
                result=trial_result,
                trial_result=trial_result,
            ),
        )

    ordered: list[tuple[str, dict[str, Any] | None, tuple[str, ...]]] = []
    seen: set[str] = set()
    for raw_result in step_results:
        result = raw_result if isinstance(raw_result, dict) else None
        name = optional_str((result or {}).get("step_name"))
        if not name or not _safe_segment(name):
            raise ValueError("Harbor step_result has an invalid step_name")
        if name in seen:
            raise ValueError(f"duplicate Harbor step_result: {name}")
        seen.add(name)
        warnings = (
            () if name in step_dirs else (f"Harbor step directory not found: {name}",)
        )
        ordered.append((name, result, warnings))
    for name in sorted(set(step_dirs) - seen):
        ordered.append(
            (
                name,
                None,
                (f"Harbor step directory is absent from result.step_results: {name}",),
            )
        )

    count = len(ordered)
    entries: list[HarborTrialEntry] = []
    for index, (name, result, warnings) in enumerate(ordered, start=1):
        data_dir = step_dirs.get(name, steps_dir / name)
        if not (data_dir / "agent" / "trajectory.json").is_file():
            root_trajectory = trial_dir / "agent" / "trajectory.json"
            if index == count and root_trajectory.is_file():
                data_dir = trial_dir
                warnings = (
                    *warnings,
                    "Harbor step trajectory is still in the live Trial agent directory",
                )
        entries.append(
            HarborTrialEntry(
                source_ref=entry_source_ref(source_ref, name),
                trial_dir=trial_dir,
                data_dir=data_dir,
                job_name=job_name,
                trial_name=trial_name,
                mount_id=mount_id,
                task_paths=task_paths,
                step_name=name,
                step_index=index,
                step_count=count,
                result=result,
                trial_result=trial_result,
                warnings=warnings,
            )
        )
    return tuple(entries)


def _matching_mount(path: Path, mounts: tuple[HarborMount, ...]) -> HarborMount | None:
    jobs_root = path.parent.parent.resolve()
    matches = [
        mount
        for mount in mounts
        if Path(os.path.abspath(Path(mount.path).expanduser())).resolve() == jobs_root
    ]
    if len(matches) > 1:
        raise ValueError(f"multiple Harbor mounts match Trial directory: {path}")
    return matches[0] if matches else None


def _read_optional_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        import json

        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _safe_segment(value: str) -> bool:
    return (
        bool(value)
        and value not in {".", ".."}
        and "/" not in value
        and "\\" not in value
    )


def _child_dirs(root: Path) -> list[Path]:
    try:
        return sorted(
            (
                Path(entry.path)
                for entry in os.scandir(root)
                if entry.is_dir(follow_symlinks=False)
            ),
            key=lambda path: path.name,
        )
    except OSError:
        return []


def _reject_symlink_chain(path: Path) -> None:
    current = path
    while True:
        if current.is_symlink():
            raise ValueError(f"Harbor Trial path traverses a symlink: {current}")
        if current.parent == current:
            return
        current = current.parent
