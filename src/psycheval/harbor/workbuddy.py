"""Adapt Harbor Job models and read WorkBuddy's official retained metrics."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import os
import stat
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from harbor.models.job.config import JobConfig
from harbor.models.job.lock import JobLock, TrialLock
from harbor.models.trial.config import TaskConfig

from .environment import HostAccessPolicy
from .runtime_config import DEFAULT_WORKDIR_ROOT, HostSettings, resolve_workdir_root

COMPOSITE_VERIFIER = "workbuddy_bench.judge:CompositeVerifier"
WORKBUDDY_VERSION = "0.1.0"
EVIDENCE_FILE_LIMIT = 16 * 1024 * 1024


class WorkBuddyError(ValueError):
    """Invalid WorkBuddy configuration, runtime, or retained evidence."""


def prepare_workbuddy_job(
    config: JobConfig, *, host_settings: HostSettings | None = None
) -> JobConfig:
    """Return a validated private model; Harbor owns selection and execution."""
    if not isinstance(config, JobConfig):
        raise TypeError("config must be a Harbor JobConfig")
    if host_settings is not None and not isinstance(host_settings, HostSettings):
        raise TypeError("host_settings must be HostSettings")
    value = JobConfig.model_validate(_job_values(config.model_copy(deep=True)))
    verifier_path = f"{__package__}.workbuddy_verifier:WorkBuddyVerifier"
    if value.verifier.import_path not in {None, COMPOSITE_VERIFIER, verifier_path}:
        raise WorkBuddyError("configuration replaces the WorkBuddy verifier")
    value.verifier.import_path = verifier_path
    environment = value.environment
    host_path = f"{__package__}.workbuddy_environment:WorkBuddyHostEnvironment"
    if environment.import_path in {
        f"{__package__}.environment:HostEnvironment",
        host_path,
    }:
        kwargs = environment.kwargs
        access = HostAccessPolicy.from_value(kwargs.get("host_access"))
        if not access.filesystem or not access.process:
            raise WorkBuddyError(
                "WorkBuddy Host requires filesystem and process access"
            )
        root = kwargs.get(
            "workdir_root",
            (
                host_settings.workdir_root
                if host_settings
                else Path(DEFAULT_WORKDIR_ROOT).expanduser()
            ),
        )
        kwargs["workdir_root"] = str(resolve_workdir_root(root))
        environment.import_path = host_path
        environment.force_build = False
        # Native Hosts cannot provision resource quotas from container defaults.
        environment.override_cpus = 0
        environment.override_memory_mb = 0
        environment.override_storage_mb = 0
        environment.override_gpus = 0
    return JobConfig.model_validate(_job_values(value))


def _job_values(config: JobConfig) -> dict[str, Any]:
    """Export for validation, not persistence; preserve in-memory environment."""
    values = config.model_dump(
        mode="python", warnings=False, context={"redact_sensitive_env": False}
    )
    # Harbor 0.21 only exposes the no-redaction context on AgentConfig.
    values["environment"]["env"] = dict(config.environment.env)
    values["verifier"]["env"] = dict(config.verifier.env)
    return values


def validate_workbuddy_runtime() -> dict[str, str]:
    try:
        distribution = importlib.metadata.distribution("workbuddy-bench")
    except importlib.metadata.PackageNotFoundError as exc:
        raise WorkBuddyError(
            "workbuddy-bench 0.1.0 is required; install the reference runtime "
            "without replacing Harbor 0.21.0"
        ) from exc
    version = distribution.version
    if version != WORKBUDDY_VERSION:
        raise WorkBuddyError(
            f"workbuddy-bench version must be {WORKBUDDY_VERSION}, found {version}"
        )
    identity: dict[str, str] = {"version": version}
    commit = _distribution_commit(distribution)
    if commit is not None:
        identity["commit"] = commit
    try:
        module = importlib.import_module("workbuddy_bench.judge")
        verifier = getattr(module, "CompositeVerifier")
    except (ImportError, AttributeError) as exc:
        raise WorkBuddyError(
            "workbuddy-bench does not expose CompositeVerifier"
        ) from exc
    if not callable(verifier):
        raise WorkBuddyError("workbuddy-bench CompositeVerifier is not callable")
    return identity


def compute_official_metrics(
    job_dir: str | Path, *, expected_tasks: Sequence[str] | None = None
) -> dict[str, Any]:
    jobs_root = Path(job_dir).expanduser().resolve()
    _require_unlinked_path(Path(job_dir).expanduser().absolute(), "Job directory")
    if not jobs_root.is_dir():
        raise WorkBuddyError("Job directory does not exist")
    if expected_tasks is None:
        expected_tasks = _expected_tasks(jobs_root)
    if (
        isinstance(expected_tasks, (str, bytes))
        or not expected_tasks
        or any(
            not isinstance(name, str) or not name or "\0" in name
            for name in expected_tasks
        )
        or len(set(expected_tasks)) != len(expected_tasks)
    ):
        raise WorkBuddyError("expected_tasks must contain distinct Task names")
    expected_tasks = list(expected_tasks)
    aliases = {name: f"task-{index:06d}" for index, name in enumerate(expected_tasks)}
    names = {alias: name for name, alias in aliases.items()}
    try:
        module = importlib.import_module("workbuddy_bench.scorer.metrics")
        compute: Callable[..., Any] = getattr(module, "compute_job_metrics")
    except (ImportError, AttributeError, ValueError) as exc:
        raise WorkBuddyError("WorkBuddy official metrics are unavailable") from exc
    with tempfile.TemporaryDirectory(prefix="workbuddy-metrics-") as directory:
        view = Path(directory)
        originals = _project_metric_trials(jobs_root, view, aliases)
        originals.update(
            {
                f"{alias}__never_ran": f"{name}__never_ran"
                for alias, name in names.items()
            }
        )
        metrics = compute(view, expected_tasks=list(names))
    if not isinstance(metrics, dict):
        raise WorkBuddyError("WorkBuddy official metrics returned a non-object")
    missing = metrics.get("missing_tasks", [])
    per_task = metrics.get("per_task", {})
    if not isinstance(missing, list) or not isinstance(per_task, dict):
        raise WorkBuddyError(
            "WorkBuddy official metrics returned malformed Task entries"
        )
    if any(
        not isinstance(name, str) or name not in names for name in [*missing, *per_task]
    ):
        raise WorkBuddyError(
            "WorkBuddy official metrics returned unexpected Task aliases"
        )
    for task in per_task.values():
        if not isinstance(task, dict) or not isinstance(task.get("attempts", []), list):
            raise WorkBuddyError(
                "WorkBuddy official metrics returned malformed Task entries"
            )
        if any(
            not isinstance(attempt, dict)
            or not isinstance(attempt.get("trial", ""), str)
            for attempt in task.get("attempts", [])
        ):
            raise WorkBuddyError(
                "WorkBuddy official metrics returned malformed Task attempts"
            )
    metrics["run_dir"] = str(jobs_root)
    if "missing_tasks" in metrics:
        metrics["missing_tasks"] = sorted(
            names[name] for name in metrics["missing_tasks"]
        )
    if "per_task" in metrics:
        metrics["per_task"] = dict(
            sorted((names[name], task) for name, task in metrics["per_task"].items())
        )
    for task in metrics.get("per_task", {}).values():
        for attempt in task.get("attempts", []):
            name = attempt.get("trial")
            if name in originals:
                attempt["trial"] = originals[name]
    return metrics


def _expected_tasks(job_dir: Path) -> list[str]:
    try:
        lock = JobLock.model_validate_json(
            _read_bounded_regular_bytes(job_dir / "lock.json", "Harbor Job lock")
        )
    except ValueError as exc:
        raise WorkBuddyError(
            "cannot determine expected Tasks from lock.json; supply expected_tasks"
        ) from exc
    identities = {}
    for trial in lock.trials:
        task = trial.task
        previous = identities.setdefault(task.name, task.digest)
        if previous != task.digest:
            raise WorkBuddyError(f"conflicting Task identities named {task.name!r}")
    if not identities:
        raise WorkBuddyError(
            "Job lock contains no expected Tasks; supply expected_tasks"
        )
    return sorted(identities)


def _project_metric_trials(
    jobs_root: Path, view: Path, expected: Mapping[str, str]
) -> dict[str, str]:
    """Bridge Harbor's truncated Trial names to the WorkBuddy scorer's directory API."""
    originals = {}
    identities = {}
    if not jobs_root.exists():
        return originals
    _require_unlinked_path(jobs_root, "Jobs root")
    for trial in jobs_root.iterdir():
        if not trial.is_dir():
            continue
        _require_unlinked_path(trial, "Trial directory")
        if any(
            child.is_dir()
            and "__" in child.name
            and (
                (child / "result.json").exists()
                or (child / "verifier/score.json").exists()
            )
            for child in trial.iterdir()
        ):
            raise WorkBuddyError(
                "metrics require one Harbor Job directory, not a parent of Jobs"
            )
        if "__" not in trial.name:
            continue
        score = trial / "verifier/score.json"
        result = trial / "result.json"
        if not score.exists() and not result.exists():
            continue
        task_name, suffix = trial.name.rsplit("__", 1)
        config_path = trial / "config.json"
        config = None
        if config_path.exists():
            raw = _read_bounded_regular_bytes(config_path, "Trial configuration")
            try:
                config = json.loads(raw.decode("utf-8"))
            except ValueError as exc:
                raise WorkBuddyError("invalid Trial Task identity") from exc
        has_task = isinstance(config, dict) and "task" in config
        if not score.exists() and not has_task:
            raw = _read_bounded_regular_bytes(result, "Harbor result")
            try:
                result_data = json.loads(raw.decode("utf-8"))
            except ValueError as exc:
                raise WorkBuddyError("invalid Harbor result") from exc
            if not (
                isinstance(result_data, dict)
                and isinstance(result_data.get("task_name"), str)
                and isinstance(result_data.get("trial_name"), str)
            ):
                continue  # A Job summary is not Trial evidence.
        task_identities = {}
        if config_path.exists():
            try:
                task_config = TaskConfig.model_validate(config["task"])
                if task_config.path is not None:
                    task_path = str(task_config.path).replace("\\", "/")
                    task_name = PurePosixPath(task_path).name
                    if not task_name:
                        raise ValueError("missing Task identity")
                    task_identities["path"] = task_path
                elif task_config.name:
                    task_name = task_config.name
                else:
                    raise ValueError("missing Task identity")
            except (KeyError, TypeError, ValueError) as exc:
                raise WorkBuddyError("invalid Trial Task identity") from exc
        lock_path = trial / "lock.json"
        if lock_path.exists():
            try:
                lock = TrialLock.model_validate_json(
                    _read_bounded_regular_bytes(lock_path, "Harbor Trial lock")
                )
            except ValueError as exc:
                raise WorkBuddyError(
                    "invalid Trial Task identity in lock.json"
                ) from exc
            task_name = lock.task.name
            task_identities["digest"] = lock.task.digest
        for kind, identity in task_identities.items():
            previous = identities.setdefault((task_name, kind), identity)
            if previous != identity:
                raise WorkBuddyError(f"conflicting Task identities named {task_name!r}")
        if task_name not in expected:
            raise WorkBuddyError(
                "WorkBuddy results contain tasks outside expected_tasks"
            )
        identity = hashlib.sha256(
            str(trial.relative_to(jobs_root)).encode()
        ).hexdigest()[:12]
        projected = view / f"{expected[task_name]}__{suffix}-{identity}"
        projected.mkdir()
        originals[projected.name] = trial.name
        (projected / "result.json").write_text("{}", encoding="ascii")
        if score.exists():
            _require_unlinked_path(score.parent, "verifier directory")
            raw = _read_bounded_regular_bytes(score, "WorkBuddy score")
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                payload = {}  # The official scorer treats unreadable scores as missing.
            (projected / "verifier").mkdir()
            (projected / "verifier/score.json").write_text(
                json.dumps(payload, ensure_ascii=True), encoding="ascii"
            )
    return originals


def _require_unlinked_path(path: Path, label: str) -> None:
    for current in (path, *path.parents):
        if current.is_symlink() or current.is_junction():
            raise WorkBuddyError(f"WorkBuddy {label} traverses a symbolic link")


def _read_bounded_regular_bytes(path: Path, label: str) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_size > EVIDENCE_FILE_LIMIT:
            raise WorkBuddyError(f"{label} is not a bounded regular file")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or opened.st_size > EVIDENCE_FILE_LIMIT:
                raise WorkBuddyError(f"{label} is not a bounded regular file")
            if (
                before.st_ino
                and opened.st_ino
                and (
                    before.st_dev,
                    before.st_ino,
                )
                != (opened.st_dev, opened.st_ino)
            ):
                raise WorkBuddyError(f"{label} changed while it was opened")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                content = stream.read(EVIDENCE_FILE_LIMIT + 1)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise WorkBuddyError(f"cannot read {label}: {path}") from exc
    if len(content) > EVIDENCE_FILE_LIMIT:
        raise WorkBuddyError(f"{label} is not a bounded regular file")
    return content


def _distribution_commit(
    distribution: importlib.metadata.Distribution,
) -> str | None:
    """Read optional installation provenance without inspecting source checkouts."""
    try:
        text = distribution.read_text("direct_url.json")
        direct = json.loads(text) if text else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    vcs = direct.get("vcs_info") if isinstance(direct, dict) else None
    commit = vcs.get("commit_id") if isinstance(vcs, dict) else None
    return commit if isinstance(commit, str) and commit else None
