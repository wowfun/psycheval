from __future__ import annotations

import hashlib
import json
import os
import posixpath
import stat
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Any, Iterable

import pathspec

from psycheval._state.annotations import optional_str

TRIAL_JSON_FILES = (
    "agent/trajectory.json",
    "config.json",
    "lock.json",
    "result.json",
)
JOB_JSON_FILES = ("config.json", "lock.json", "result.json")
DEFAULT_TASK_IGNORES = (
    "__pycache__/",
    "*.pyc",
    ".DS_Store",
    "*.swp",
    "*.swo",
    "*~",
)


@dataclass(frozen=True)
class HarborEvidence:
    trial_values: dict[str, dict[str, Any] | None]
    job_values: dict[str, dict[str, Any] | None]
    task_name: str | None
    job_name: str
    trial_name: str
    model_provider: str | None
    task_keywords: tuple[str, ...]
    task_metadata: dict[str, Any]
    provenance: dict[str, Any]
    phase_timing: dict[str, Any]
    revision: str


@dataclass(frozen=True)
class _TaskCandidate:
    path: Path
    metadata: dict[str, Any] | None
    error: str | None
    config_bytes: bytes | None


@dataclass(frozen=True)
class HarborTaskIndex:
    candidates: tuple[_TaskCandidate, ...]
    revision: str
    content_digests: dict[Path, tuple[str, str] | Exception] = field(
        default_factory=dict,
        compare=False,
        repr=False,
    )


def read_harbor_evidence(
    trial_dir: Path,
    *,
    jobs_root: Path,
    task_paths: Iterable[str],
    mount_id: str | None,
    task_index: HarborTaskIndex | None = None,
) -> HarborEvidence:
    last_error: Exception | None = None
    job_dir = trial_dir.parent
    for _attempt in range(3):
        before = _json_signatures(trial_dir, TRIAL_JSON_FILES) + _json_signatures(
            job_dir, JOB_JSON_FILES
        )
        try:
            evidence = _read_once(
                trial_dir,
                jobs_root=jobs_root,
                task_paths=task_paths,
                mount_id=mount_id,
                task_index=task_index,
            )
        except Exception as exc:  # noqa: BLE001 - retry only on concurrent changes.
            last_error = exc
            if before != _json_signatures(
                trial_dir, TRIAL_JSON_FILES
            ) + _json_signatures(job_dir, JOB_JSON_FILES):
                continue
            raise
        after = _json_signatures(trial_dir, TRIAL_JSON_FILES) + _json_signatures(
            job_dir, JOB_JSON_FILES
        )
        if before == after:
            return evidence
    if last_error is not None:
        raise last_error
    raise ValueError(f"Harbor evidence changed while it was being read: {trial_dir}")


def _read_once(
    trial_dir: Path,
    *,
    jobs_root: Path,
    task_paths: Iterable[str],
    mount_id: str | None,
    task_index: HarborTaskIndex | None,
) -> HarborEvidence:
    job_dir = trial_dir.parent
    trial_values, trial_revision = _read_json_objects(
        trial_dir, jobs_root, TRIAL_JSON_FILES
    )
    job_values, job_revision = _read_json_objects(job_dir, jobs_root, JOB_JSON_FILES)

    trial_config = trial_values.get("config.json") or {}
    trial_lock = trial_values.get("lock.json") or {}
    result = trial_values.get("result.json") or {}
    trajectory = trial_values.get("agent/trajectory.json") or {}
    job_config = job_values.get("config.json") or {}
    job_lock = job_values.get("lock.json") or {}
    job_result = job_values.get("result.json") or {}

    lock_task = (
        trial_lock.get("task") if isinstance(trial_lock.get("task"), dict) else {}
    )
    config_task = (
        trial_config.get("task") if isinstance(trial_config.get("task"), dict) else {}
    )
    task_name = _task_name(result, lock_task, config_task)
    recorded_digest, recorded_digest_source = _recorded_task_digest(
        lock_task,
        config_task,
    )
    index = task_index or read_harbor_task_index(task_paths)
    task_metadata, selected_revision = _resolve_task_metadata(
        index,
        task_name=task_name,
        task_paths=(lock_task.get("path"), config_task.get("path")),
        recorded_digest=recorded_digest,
        recorded_digest_source=recorded_digest_source,
    )
    task_keywords = tuple(_string_list(task_metadata.get("keywords")))

    job_name = optional_str(job_config.get("job_name")) or job_dir.name
    trial_name = (
        optional_str(result.get("trial_name"))
        or optional_str(trial_config.get("trial_name"))
        or trial_dir.name
    )
    job_id = (
        optional_str(trial_config.get("job_id"))
        or optional_str(job_config.get("job_id"))
        or optional_str(job_result.get("id"))
    )
    result_id = optional_str(result.get("id"))
    harbor_info = (
        job_lock.get("harbor")
        if isinstance(job_lock.get("harbor"), dict)
        else trial_lock.get("harbor")
        if isinstance(trial_lock.get("harbor"), dict)
        else {}
    )
    harbor_version = optional_str(harbor_info.get("version"))
    regrade = _regrade_provenance(trial_config, trial_lock)
    model_provider = _model_provider(result, trial_config, trajectory)
    phase_timing = _phase_timing(result)

    provenance: dict[str, Any] = {
        "mount_id": mount_id,
        "job_id": job_id,
        "result_id": result_id,
        "harbor_version": harbor_version,
        "task_digest": recorded_digest,
        "task_digest_source": recorded_digest_source,
        "task_source": optional_str(lock_task.get("source"))
        or optional_str(config_task.get("source")),
        "task_version": optional_str(lock_task.get("version"))
        or optional_str(config_task.get("version")),
        "task_checksum": optional_str(result.get("task_checksum")),
        "regrade": regrade,
    }
    provenance = {key: value for key, value in provenance.items() if value is not None}

    digest = hashlib.sha256()
    for value in (
        trial_revision,
        job_revision,
        index.revision,
        selected_revision,
    ):
        digest.update(value.encode("utf-8") + b"\0")
    return HarborEvidence(
        trial_values=trial_values,
        job_values=job_values,
        task_name=task_name,
        job_name=job_name,
        trial_name=trial_name,
        model_provider=model_provider,
        task_keywords=task_keywords,
        task_metadata=task_metadata,
        provenance=provenance,
        phase_timing=phase_timing,
        revision=digest.hexdigest(),
    )


def _task_name(
    result: dict[str, Any],
    lock_task: dict[str, Any],
    config_task: dict[str, Any],
) -> str | None:
    direct = optional_str(result.get("task_name"))
    if direct:
        if "/" in direct:
            return direct
        source = optional_str(lock_task.get("source")) or optional_str(
            config_task.get("source")
        )
        return f"{source}/{direct}" if source else direct
    for task in (lock_task, config_task):
        name = optional_str(task.get("name"))
        source = optional_str(task.get("source"))
        path = optional_str(task.get("path"))
        if not name and path:
            name = PurePath(path.replace("\\", "/")).name
        if name:
            return name if "/" in name or not source else f"{source}/{name}"
    return None


def _digest_ref(value: Any) -> str | None:
    ref = optional_str(value)
    return ref if ref and ref.startswith("sha256:") else None


def _recorded_task_digest(
    lock_task: dict[str, Any], config_task: dict[str, Any]
) -> tuple[str | None, str | None]:
    for task, source in (
        (lock_task, "lock.digest"),
        (config_task, "config.digest"),
    ):
        digest = optional_str(task.get("digest"))
        if digest:
            return digest, source
    ref = _digest_ref(config_task.get("ref"))
    return (ref, "config.ref") if ref else (None, None)


def _model_provider(
    result: dict[str, Any],
    trial_config: dict[str, Any],
    trajectory: dict[str, Any],
) -> str | None:
    agent_info = (
        result.get("agent_info") if isinstance(result.get("agent_info"), dict) else {}
    )
    model_info = (
        agent_info.get("model_info")
        if isinstance(agent_info.get("model_info"), dict)
        else {}
    )
    provider = optional_str(model_info.get("provider"))
    if provider:
        return provider
    config_agent = (
        trial_config.get("agent") if isinstance(trial_config.get("agent"), dict) else {}
    )
    trajectory_agent = (
        trajectory.get("agent") if isinstance(trajectory.get("agent"), dict) else {}
    )
    for model_name in (
        optional_str(config_agent.get("model_name")),
        optional_str(trajectory_agent.get("model_name")),
    ):
        if model_name and "/" in model_name:
            prefix, suffix = model_name.split("/", 1)
            if prefix.strip() and suffix.strip():
                return prefix.strip()
    return None


def _regrade_provenance(
    trial_config: dict[str, Any], trial_lock: dict[str, Any]
) -> dict[str, Any] | None:
    source = (
        trial_lock.get("source_trial")
        if isinstance(trial_lock.get("source_trial"), dict)
        else trial_config.get("source_trial")
        if isinstance(trial_config.get("source_trial"), dict)
        else None
    )
    if source is None:
        return None
    task = source.get("task") if isinstance(source.get("task"), dict) else {}
    values = {
        "action": optional_str(source.get("action")),
        "type": optional_str(source.get("type")),
        "trial_id": optional_str(source.get("trial_id")),
        "path": optional_str(source.get("path")),
        "task_digest": optional_str(task.get("digest")),
    }
    return {key: value for key, value in values.items() if value is not None}


def _phase_timing(result: dict[str, Any]) -> dict[str, Any]:
    phases: dict[str, Any] = {}
    for source_key, output_key in (
        (None, "overall"),
        ("environment_setup", "environment_setup"),
        ("agent_setup", "agent_setup"),
        ("agent_execution", "agent_execution"),
        ("verifier", "verifier"),
    ):
        source = result if source_key is None else result.get(source_key)
        if not isinstance(source, dict):
            continue
        started = optional_str(source.get("started_at"))
        finished = optional_str(source.get("finished_at"))
        value: dict[str, Any] = {}
        if started:
            value["started_at"] = started
        if finished:
            value["finished_at"] = finished
        duration = _iso_duration_ms(started, finished)
        if duration is not None:
            value["duration_ms"] = duration
        if value:
            phases[output_key] = value
    return phases


def _iso_duration_ms(started: str | None, finished: str | None) -> int | None:
    if not started or not finished:
        return None
    from datetime import datetime

    try:
        start = datetime.fromisoformat(started.replace("Z", "+00:00"))
        end = datetime.fromisoformat(finished.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0, int((end - start).total_seconds() * 1000))


def _task_candidates(
    task_paths: Iterable[str],
) -> tuple[list[_TaskCandidate], str]:
    roots = tuple(Path(raw_root) for raw_root in task_paths)
    last_error: Exception | None = None
    for _attempt in range(3):
        try:
            before = _task_index_signatures(roots)
            candidates, revision = _task_candidates_once(roots)
            if before == _task_index_signatures(roots):
                return candidates, revision
        except Exception as exc:  # noqa: BLE001 - bounded consistency retry.
            last_error = exc
    if last_error is not None:
        raise last_error
    raise ValueError("Harbor Task allowlist changed while it was being read")


def read_harbor_task_index(task_paths: Iterable[str]) -> HarborTaskIndex:
    candidates, revision = _task_candidates(task_paths)
    return HarborTaskIndex(candidates=tuple(candidates), revision=revision)


def _task_candidates_once(
    task_paths: Iterable[Path],
) -> tuple[list[_TaskCandidate], str]:
    candidates: list[_TaskCandidate] = []
    index_digest = hashlib.sha256()
    for root in task_paths:
        _assert_safe_descendant(root, root)
        task_dirs = (
            [root] if _regular_file(root / "task.toml") else _child_task_dirs(root)
        )
        for task_dir in task_dirs:
            config_path = task_dir / "task.toml"
            try:
                _walk_regular_files(task_dir, task_dir)
                config_bytes = _read_bytes_no_follow(task_dir, config_path)
                from harbor.models.task.task import Task

                validated_task = Task(task_dir)
                task = validated_task.config.task
                if task is None:
                    raise ValueError("task.toml must contain a [task] table")
                metadata = {
                    "name": optional_str(task.name),
                    "version": optional_str(task.version),
                    "description": str(task.description or ""),
                    "keywords": _string_list(task.keywords),
                }
                error = None
            except Exception as exc:  # noqa: BLE001 - Harbor owns validation types.
                config_bytes = None
                metadata = None
                error = str(exc)
            index_digest.update(str(task_dir).encode("utf-8") + b"\0")
            index_digest.update(config_bytes or str(error).encode("utf-8"))
            index_digest.update(b"\0")
            if metadata is not None:
                candidates.append(
                    _TaskCandidate(
                        path=task_dir,
                        metadata=metadata,
                        error=error,
                        config_bytes=config_bytes,
                    )
                )
    return candidates, index_digest.hexdigest()


def _resolve_task_metadata(
    index: HarborTaskIndex,
    *,
    task_name: str | None,
    task_paths: Iterable[Any],
    recorded_digest: str | None,
    recorded_digest_source: str | None,
) -> tuple[dict[str, Any], str]:
    candidates = index.candidates
    if not candidates:
        return {"status": "not_configured", "live": True}, "not-configured"
    selected: _TaskCandidate | None = None
    for raw_path in task_paths:
        if raw_path is None:
            continue
        matches = [
            candidate
            for candidate in candidates
            if _task_path_matches(candidate.path, raw_path)
        ]
        if len(matches) > 1:
            return {
                "status": "ambiguous",
                "live": True,
                "diagnostic": f"Task path matched {len(matches)} allowlisted Tasks",
            }, "ambiguous-path"
        if len(matches) == 1:
            selected = matches[0]
            break
    if selected is None and task_name and "/" in task_name:
        matches = [
            candidate
            for candidate in candidates
            if candidate.metadata is not None
            and candidate.metadata.get("name") == task_name
        ]
        if len(matches) > 1:
            return {
                "status": "ambiguous",
                "live": True,
                "diagnostic": f"Task name matched {len(matches)} allowlisted Tasks",
            }, "ambiguous-name"
        if len(matches) == 1:
            selected = matches[0]
    if selected is None:
        return {
            "status": "not_found",
            "live": True,
            **({"requested_name": task_name} if task_name else {}),
        }, "not-found"
    if selected.metadata is None:
        return {
            "status": "invalid",
            "live": True,
            "path": str(selected.path),
            "diagnostic": selected.error or "invalid task.toml",
        }, hashlib.sha256((selected.error or "invalid").encode()).hexdigest()
    try:
        cached = index.content_digests.get(selected.path)
        if cached is None:
            try:
                cached = _task_content_digest(selected.path)
            except (OSError, ValueError) as exc:
                cached = exc
            index.content_digests[selected.path] = cached
        if isinstance(cached, Exception):
            raise cached
        live_digest, revision = cached
    except (OSError, ValueError) as exc:
        return {
            "status": "invalid",
            "live": True,
            "path": str(selected.path),
            "diagnostic": str(exc),
            **selected.metadata,
        }, hashlib.sha256(str(exc).encode()).hexdigest()
    digest_comparable = recorded_digest_source != "config.ref"
    digest_matches = (
        recorded_digest == live_digest
        if recorded_digest and digest_comparable
        else None
    )
    status = "digest_mismatch" if digest_matches is False else "resolved"
    return {
        "status": status,
        "live": True,
        "path": str(selected.path),
        **selected.metadata,
        "live_digest": live_digest,
        "digest_matches": digest_matches,
        **(
            {"digest_comparison": "not_comparable"}
            if recorded_digest and not digest_comparable
            else {}
        ),
    }, revision


def _task_path_matches(candidate: Path, raw_path: Any) -> bool:
    text = str(raw_path or "").strip().replace("\\", "/")
    if not text:
        return False
    requested = Path(text)
    if requested.is_absolute():
        return os.path.normcase(os.path.normpath(candidate)) == os.path.normcase(
            os.path.normpath(requested)
        )
    normalized = posixpath.normpath(text)
    requested_parts = tuple(
        os.path.normcase(part)
        for part in PurePath(normalized).parts
        if part not in {"", "."}
    )
    while requested_parts and (
        requested_parts[0] == ".." or requested_parts[0].endswith(":")
    ):
        requested_parts = requested_parts[1:]
    candidate_parts = tuple(os.path.normcase(part) for part in candidate.parts)
    return (
        bool(requested_parts)
        and candidate_parts[-len(requested_parts) :] == requested_parts
    )


def _task_content_digest(task_dir: Path) -> tuple[str, str]:
    last_error: Exception | None = None
    for _attempt in range(3):
        try:
            files = _task_files(task_dir)
            relative_files = tuple(
                path.relative_to(task_dir).as_posix() for path in files
            )
            before = _file_signatures(files)
            outer = hashlib.sha256()
            revision = hashlib.sha256()
            for path in files:
                content = _read_bytes_no_follow(task_dir, path)
                relative = path.relative_to(task_dir).as_posix()
                file_hash = hashlib.sha256(content).hexdigest()
                outer.update(f"{relative}\0{file_hash}\n".encode())
                revision.update(relative.encode() + b"\0" + content + b"\0")
            after_files = _task_files(task_dir)
            after_relative_files = tuple(
                path.relative_to(task_dir).as_posix() for path in after_files
            )
            if relative_files == after_relative_files and before == _file_signatures(
                after_files
            ):
                return f"sha256:{outer.hexdigest()}", revision.hexdigest()
        except Exception as exc:  # noqa: BLE001 - bounded consistency retry.
            last_error = exc
    if last_error is not None:
        raise last_error
    raise ValueError(f"Task metadata changed while it was being read: {task_dir}")


def _task_files(task_dir: Path) -> list[Path]:
    gitignore = task_dir / ".gitignore"
    patterns = (
        _read_bytes_no_follow(task_dir, gitignore).decode("utf-8").splitlines()
        if _regular_file(gitignore)
        else DEFAULT_TASK_IGNORES
    )
    spec = pathspec.PathSpec.from_lines("gitignore", patterns)
    files: list[Path] = []
    for name in ("task.toml", "instruction.md", "README.md"):
        path = task_dir / name
        if _regular_file(path):
            files.append(path)
    for name in ("environment", "tests", "solution", "steps"):
        root = task_dir / name
        if not root.exists():
            continue
        files.extend(_walk_regular_files(task_dir, root))
    result = [
        path
        for path in files
        if not spec.match_file(path.relative_to(task_dir).as_posix())
    ]
    result.sort(key=lambda path: path.relative_to(task_dir).as_posix())
    return result


def _walk_regular_files(containment_root: Path, root: Path) -> list[Path]:
    _assert_safe_descendant(containment_root, root)
    result: list[Path] = []
    with os.scandir(root) as entries:
        for entry in sorted(entries, key=lambda item: item.name):
            path = Path(entry.path)
            if entry.is_symlink():
                raise ValueError(f"Harbor Task content must not be a symlink: {path}")
            if entry.is_dir(follow_symlinks=False):
                result.extend(_walk_regular_files(containment_root, path))
            elif entry.is_file(follow_symlinks=False):
                result.append(path)
            else:
                raise ValueError(f"Harbor Task content must be a regular file: {path}")
    return result


def _read_json_objects(
    root: Path, containment_root: Path, relative_files: Iterable[str]
) -> tuple[dict[str, dict[str, Any] | None], str]:
    values: dict[str, dict[str, Any] | None] = {}
    digest = hashlib.sha256()
    for relative in relative_files:
        path = root / relative
        if not _regular_file(path):
            values[relative] = None
            digest.update(relative.encode() + b"\0missing\0")
            continue
        content = _read_bytes_no_follow(containment_root, path)
        try:
            parsed = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"failed to parse {path}: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{path} must contain a JSON object")
        values[relative] = parsed
        digest.update(relative.encode() + b"\0" + content + b"\0")
    return values, digest.hexdigest()


def _read_bytes_no_follow(containment_root: Path, path: Path) -> bytes:
    _assert_safe_descendant(containment_root, path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError(f"Harbor evidence file must be regular: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            return handle.read()
    finally:
        os.close(descriptor)


def _assert_safe_descendant(root: Path, path: Path) -> None:
    lexical_root = Path(os.path.abspath(root))
    lexical_path = Path(os.path.abspath(path))
    current = lexical_root
    while True:
        if current.is_symlink():
            raise ValueError(f"Harbor evidence traverses a symlink: {current}")
        if current.parent == current:
            break
        current = current.parent
    try:
        relative = lexical_path.relative_to(lexical_root)
    except ValueError as exc:
        raise ValueError(f"Harbor evidence escapes its root: {path}") from exc
    current = lexical_root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"Harbor evidence traverses a symlink: {current}")


def _json_signatures(root: Path, relative_files: Iterable[str]) -> tuple[Any, ...]:
    return tuple(_path_signature(root / relative) for relative in relative_files)


def _file_signatures(paths: Iterable[Path]) -> tuple[Any, ...]:
    return tuple(_path_signature(path) for path in paths)


def _task_index_signatures(roots: Iterable[Path]) -> tuple[Any, ...]:
    signatures: list[Any] = []
    for root in roots:
        _assert_safe_descendant(root, root)
        signatures.append(_path_signature(root))
        task_dirs = (
            [root] if _regular_file(root / "task.toml") else _child_task_dirs(root)
        )
        signatures.extend(
            (
                str(task_dir),
                _path_signature(task_dir),
                _path_signature(task_dir / "task.toml"),
            )
            for task_dir in task_dirs
        )
    return tuple(signatures)


def _path_signature(path: Path) -> tuple[Any, ...]:
    try:
        value = path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return (str(path), None)
    return (str(path), value.st_mode, value.st_size, value.st_mtime_ns)


def _regular_file(path: Path) -> bool:
    try:
        value = path.stat(follow_symlinks=False)
    except OSError:
        return False
    return stat.S_ISREG(value.st_mode)


def _child_task_dirs(root: Path) -> list[Path]:
    _assert_safe_descendant(root, root)
    result: list[Path] = []
    with os.scandir(root) as entries:
        for entry in sorted(entries, key=lambda item: item.name):
            if entry.is_dir(follow_symlinks=False) and not entry.is_symlink():
                path = Path(entry.path)
                if _regular_file(path / "task.toml"):
                    result.append(path)
    return result


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        folded = text.casefold()
        if text and folded not in seen:
            seen.add(folded)
            result.append(text)
    return result
