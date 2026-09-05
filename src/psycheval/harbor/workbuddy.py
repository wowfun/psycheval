"""Prepare Harbor 0.21 WorkBuddy Office runs and summarize retained results."""

from __future__ import annotations

import hashlib
import heapq
import importlib
import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable

import yaml
from harbor.models.job.config import JobConfig

from .datasets import ResolvedHarborDataset, validate_harbor_dataset
from .identifiers import HARBOR_ID_RE

PLAN_SCHEMA = "psycheval.workbuddy-run-plan.v2"
SUMMARY_SCHEMA = "psycheval.workbuddy-summary.v2"
_SELECTION_FIELDS = (
    "scope",
    "declared_task_count",
    "available_task_count",
    "expected_tasks",
)
OFFICE_DATASET_ID = "wb-bench-office-v1.0"
OFFICE_TASK_COUNT = 50
SPECIAL_TASK = "recruiting-search-skill-mock-mcp-hardened"
COMPOSITE_VERIFIER = "workbuddy_bench.judge:CompositeVerifier"
WORKBUDDY_VERSION = "0.1.0"
WORKBUDDY_SOURCE_COMMIT = "625b2233093ae4f23e76be28c1f341d41cc70373"
LLM_REQUIRED_ENV = (
    "WORKBUDDY_VERIFIER_LLM_BASE_URL",
    "WORKBUDDY_VERIFIER_LLM_API_KEY",
    "WORKBUDDY_VERIFIER_LLM_MODEL",
)
LLM_OPTIONAL_ENV = "WORKBUDDY_VERIFIER_LLM_MAX_OUTPUT_TOKENS"
PLAN_FILE_LIMIT = 2 * 1024 * 1024
SKILL_FILE_LIMIT = 2 * 1024 * 1024
SKILL_TOTAL_LIMIT = 16 * 1024 * 1024
SKILL_ENTRY_LIMIT = 10_000
PLAN_ID_ATTEMPTS = 8
_PUBLIC_METRIC_KEY = re.compile(r"[A-Za-z0-9_.:-]{1,64}")


class WorkBuddyPlanError(ValueError):
    """A stable, user-facing WorkBuddy preparation or summary failure."""


def prepare_workbuddy_plan(
    *,
    output_root: str | Path,
    dataset_id: str,
    dataset_path: str | Path,
    base_config: str | Path,
    task_selection: list[str] | None = None,
    limit: int | None = None,
    allow_partial: bool = False,
) -> dict[str, Any]:
    root = _output_root(output_root)
    resolved = validate_harbor_dataset(
        dataset_id=dataset_id,
        path=dataset_path,
        format="workbuddy.v1",
        allow_partial=allow_partial,
    )
    _validate_office_dataset(resolved, allow_partial=allow_partial)
    task_names = _select_tasks(resolved.task_names, task_selection, limit)
    runtime = validate_workbuddy_runtime()
    base = _load_base_config(Path(base_config).expanduser().resolve())
    _validate_base_ownership(base)
    _validate_llm_environment()
    host_mode = _adapt_explicit_host_environment(base)

    if host_mode and platform.system() == "Windows":
        from .workbuddy_verifier import validate_office_profile

        validate_office_profile(resolved, task_names)

    plan_id, plan_dir, jobs_root = _reserve_plan_directories(root)
    skill_dir = (
        _extract_special_skill(resolved, plan_dir / "skills")
        if SPECIAL_TASK in task_names
        else None
    )
    normal_names = [name for name in task_names if name != SPECIAL_TASK]
    jobs = []
    for kind, names, skill in (
        ("normal", normal_names, None),
        ("special", [SPECIAL_TASK] if skill_dir is not None else [], skill_dir),
    ):
        if not names:
            continue
        job_name = f"{plan_id}-{kind}"
        path = plan_dir / f"{kind}.yaml"
        config = _compose_job(
            base,
            job_name=job_name,
            jobs_root=jobs_root,
            task_root=resolved.task_root,
            task_names=names,
            skill_dir=skill,
            host_mode=host_mode,
        )
        _write_yaml(path, config)
        jobs.append({"name": job_name, "config": str(path), "tasks": names})
    warnings = _office_warnings() if skill_dir is not None else []
    plan = {
        "schema": PLAN_SCHEMA,
        "plan_id": plan_id,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset_id": resolved.id,
        "dataset_root": str(resolved.source_root),
        "task_root": str(resolved.task_root),
        "jobs_root": str(jobs_root),
        "expected_tasks": task_names,
        "scope": "full" if len(task_names) == OFFICE_TASK_COUNT else "subset",
        "declared_task_count": resolved.manifest["dataset"]["task_count"],
        "available_task_count": len(resolved.task_names),
        "runtime": runtime,
        "host_environment": host_mode,
        "skill_dir": str(skill_dir) if skill_dir is not None else None,
        "jobs": jobs,
        "warnings": warnings,
    }
    _atomic_write_json(plan_dir / "workbuddy-run-plan.json", plan)
    return plan


def summarize_workbuddy_plan(
    *, output_root: str | Path, plan_id: str, provisional: bool = False
) -> dict[str, Any]:
    root = _output_root(output_root)
    if HARBOR_ID_RE.fullmatch(plan_id) is None:
        raise WorkBuddyPlanError("plan id is not path-safe")
    plan_dir = root / "harbor-plans" / plan_id
    _require_unlinked_path(plan_dir, "plan directory")
    plan = _read_plan(plan_dir / "workbuddy-run-plan.json")
    if plan.get("plan_id") != plan_id:
        raise WorkBuddyPlanError("run plan identity does not match its directory")
    jobs_root = _plan_contained_path(root, plan.get("jobs_root"), "jobs_root")
    expected = plan.get("expected_tasks")
    jobs = plan.get("jobs")
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= 2:
        raise WorkBuddyPlanError("run plan must contain one or two nonempty Jobs")
    assigned = []
    names = []
    for job in jobs:
        if (
            not isinstance(job, dict)
            or not isinstance(job.get("tasks"), list)
            or not job["tasks"]
        ):
            raise WorkBuddyPlanError("run plan Job tasks are invalid")
        assigned.extend(job["tasks"])
        names.append(job.get("name"))
    if (
        any(not isinstance(name, str) for name in assigned + names)
        or sorted(assigned) != expected
        or len(set(names)) != len(names)
    ):
        raise WorkBuddyPlanError("run plan Jobs must partition expected_tasks")
    pending = []
    for item in jobs:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("name"), str)
            or HARBOR_ID_RE.fullmatch(item["name"]) is None
        ):
            raise WorkBuddyPlanError("run plan Job entry is invalid")
        job_dir = _plan_contained_path(
            root, str(jobs_root / item["name"]), "Job directory"
        )
        if not _job_is_terminal(job_dir):
            pending.append(item["name"])
    if pending and not provisional:
        raise WorkBuddyPlanError(
            "WorkBuddy Jobs are not terminal: " + ", ".join(pending)
        )
    expected_runtime = plan.get("runtime")
    if not isinstance(expected_runtime, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in expected_runtime.items()
    ):
        raise WorkBuddyPlanError("run plan runtime identity is invalid")
    current_runtime = validate_workbuddy_runtime()
    if current_runtime != expected_runtime:
        raise WorkBuddyPlanError(
            "WorkBuddy runtime identity changed after plan preparation"
        )
    metrics = compute_official_metrics(jobs_root, expected)
    per_task = metrics.get("per_task")
    if isinstance(per_task, dict) and set(per_task) - set(expected):
        raise WorkBuddyPlanError("WorkBuddy results contain tasks outside the run plan")
    snapshot = {
        **{key: plan[key] for key in _SELECTION_FIELDS},
        "schema": SUMMARY_SCHEMA,
        "plan_id": plan_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "provisional": bool(pending),
        "pending_jobs": pending,
        "metrics": metrics,
        "warnings": list(plan.get("warnings") or []),
    }
    _atomic_write_json(plan_dir / "workbuddy-summary.json", snapshot)
    return snapshot


def discover_workbuddy_summaries(
    output_root: str | Path,
    registered_dataset_ids: set[str],
) -> list[dict[str, Any]]:
    """Project safe aggregate snapshots for the Workspace Dataset page."""

    plans_root = _output_root(output_root) / "harbor-plans"
    if not plans_root.is_dir() or plans_root.is_symlink():
        return []
    summaries: list[dict[str, Any]] = []
    try:
        with os.scandir(plans_root) as stream:
            entries = heapq.nsmallest(256, stream, key=lambda item: item.name)
    except OSError:
        return []
    for entry in entries:
        if (
            entry.is_symlink()
            or not entry.is_dir(follow_symlinks=False)
            or HARBOR_ID_RE.fullmatch(entry.name) is None
        ):
            continue
        plan_dir = Path(entry.path)
        try:
            plan = _read_plan(plan_dir / "workbuddy-run-plan.json")
            snapshot = _read_summary(plan_dir / "workbuddy-summary.json")
        except WorkBuddyPlanError:
            continue
        dataset_id = plan.get("dataset_id")
        if (
            plan.get("plan_id") != entry.name
            or snapshot.get("plan_id") != entry.name
            or not isinstance(dataset_id, str)
            or dataset_id not in registered_dataset_ids
            or any(snapshot.get(key) != plan.get(key) for key in _SELECTION_FIELDS)
        ):
            continue
        metrics = _project_summary_metrics(snapshot.get("metrics"))
        if metrics is None:
            continue
        generated_at = snapshot.get("generated_at")
        warnings = snapshot.get("warnings")
        pending = snapshot.get("pending_jobs")
        summaries.append(
            {
                "plan_id": entry.name,
                "dataset_id": dataset_id,
                "scope": snapshot["scope"],
                "selected_task_count": len(snapshot["expected_tasks"]),
                "available_task_count": snapshot["available_task_count"],
                "declared_task_count": snapshot["declared_task_count"],
                "generated_at": (
                    generated_at
                    if isinstance(generated_at, str) and len(generated_at) <= 64
                    else ""
                ),
                "provisional": bool(snapshot.get("provisional")),
                "pending_jobs": [
                    item
                    for item in pending[:2]
                    if isinstance(item, str) and HARBOR_ID_RE.fullmatch(item)
                ]
                if isinstance(pending, list)
                else [],
                "metrics": metrics,
                "warnings": [
                    item
                    for item in warnings[:8]
                    if isinstance(item, str)
                    and len(item) <= 512
                    and "\n" not in item
                    and "\r" not in item
                ]
                if isinstance(warnings, list)
                else [],
            }
        )
    return sorted(summaries, key=lambda item: item["generated_at"], reverse=True)


def validate_workbuddy_runtime() -> dict[str, str]:
    try:
        distribution = importlib.metadata.distribution("workbuddy-bench")
    except importlib.metadata.PackageNotFoundError as exc:
        raise WorkBuddyPlanError(
            "workbuddy-bench 0.1.0 is required; install the reference runtime "
            "without replacing Harbor 0.21.0"
        ) from exc
    version = distribution.version
    if version != WORKBUDDY_VERSION:
        raise WorkBuddyPlanError(
            f"workbuddy-bench version must be {WORKBUDDY_VERSION}, found {version}"
        )
    identity: dict[str, str] = {"version": version}
    commit = _distribution_commit(distribution)
    if commit is not None:
        identity["commit"] = commit
        if commit != WORKBUDDY_SOURCE_COMMIT:
            raise WorkBuddyPlanError(
                "workbuddy-bench source commit must be "
                f"{WORKBUDDY_SOURCE_COMMIT}, found {commit}"
            )
    try:
        module = importlib.import_module("workbuddy_bench.judge")
        verifier = getattr(module, "CompositeVerifier")
    except (ImportError, AttributeError) as exc:
        raise WorkBuddyPlanError(
            "workbuddy-bench does not expose CompositeVerifier"
        ) from exc
    if not callable(verifier):
        raise WorkBuddyPlanError("workbuddy-bench CompositeVerifier is not callable")
    return identity


def validate_workbuddy_host_dependencies() -> None:
    missing_commands = [
        name
        for name in (("git",) if platform.system() == "Windows" else ("bash", "git"))
        if shutil.which(name) is None
    ]
    modules = {
        "bs4": "beautifulsoup4",
        "docx": "python-docx",
        "fitz": "pymupdf",
        "openpyxl": "openpyxl",
        "pandas": "pandas",
        "pdfplumber": "pdfplumber",
        "PIL": "Pillow",
        "pptx": "python-pptx",
        "pytest": "pytest",
        "yaml": "PyYAML",
    }
    missing_modules = [
        package
        for module, package in modules.items()
        if importlib.util.find_spec(module) is None
    ]
    if missing_commands or missing_modules:
        details = []
        if missing_commands:
            details.append("commands: " + ", ".join(missing_commands))
        if missing_modules:
            details.append("Python packages: " + ", ".join(missing_modules))
        raise WorkBuddyPlanError(
            "WorkBuddy HostEnvironment dependencies are missing ("
            + "; ".join(details)
            + ")"
        )


def compute_official_metrics(
    jobs_root: Path, expected_tasks: list[str]
) -> dict[str, Any]:
    try:
        module = importlib.import_module("workbuddy_bench.scorer.metrics")
        compute: Callable[..., Any] = getattr(module, "compute_job_metrics")
    except (ImportError, AttributeError, ValueError) as exc:
        raise WorkBuddyPlanError("WorkBuddy official metrics are unavailable") from exc
    metrics = compute(jobs_root, expected_tasks=expected_tasks)
    if not isinstance(metrics, dict):
        raise WorkBuddyPlanError("WorkBuddy official metrics returned a non-object")
    return metrics


def _validate_office_dataset(
    resolved: ResolvedHarborDataset, *, allow_partial: bool
) -> None:
    manifest_id = resolved.manifest.get("dataset", {}).get("id")
    if resolved.format != "workbuddy.v1" or manifest_id != OFFICE_DATASET_ID:
        raise WorkBuddyPlanError(
            "harbor prepare requires the workbuddy.v1 wb-bench-office-v1.0 Dataset profile"
        )
    if len(resolved.task_names) > OFFICE_TASK_COUNT:
        raise WorkBuddyPlanError(
            f"Office supports at most {OFFICE_TASK_COUNT} Tasks; found {len(resolved.task_names)}"
        )
    if not allow_partial and (
        len(resolved.task_names) != OFFICE_TASK_COUNT
        or SPECIAL_TASK not in resolved.task_names
    ):
        raise WorkBuddyPlanError(
            "full Office preparation requires all 50 Tasks; "
            "use allow_partial=True for a cropped bundle"
        )


def _select_tasks(
    available: tuple[str, ...], selection: list[str] | None, limit: int | None
) -> list[str]:
    if limit is not None and (type(limit) is not int or limit < 1):
        raise WorkBuddyPlanError("limit must be a positive integer")
    if selection is not None:
        if (
            not isinstance(selection, list)
            or not selection
            or any(not isinstance(name, str) or not name for name in selection)
        ):
            raise WorkBuddyPlanError(
                "task_selection must be a nonempty list of Task names"
            )
        if len(set(selection)) != len(selection):
            raise WorkBuddyPlanError("task_selection contains duplicate Task names")
        missing = set(selection) - set(available)
        if missing:
            raise WorkBuddyPlanError(
                "selected Tasks are unavailable: " + ", ".join(sorted(missing))
            )
    return sorted(available if selection is None else selection)[:limit]


def _validate_plan_selection(plan: dict[str, Any]) -> None:
    expected = plan.get("expected_tasks")
    declared = plan.get("declared_task_count")
    available = plan.get("available_task_count")
    if (
        not isinstance(expected, list)
        or not expected
        or any(not isinstance(name, str) or not name for name in expected)
    ):
        raise WorkBuddyPlanError("run plan expected_tasks is invalid")
    if (
        expected != sorted(set(expected))
        or type(declared) is not int
        or type(available) is not int
        or not len(expected) <= available <= declared
        or available > OFFICE_TASK_COUNT
    ):
        raise WorkBuddyPlanError("run plan task counts or selection are invalid")
    if plan.get("scope") != (
        "full" if len(expected) == OFFICE_TASK_COUNT else "subset"
    ):
        raise WorkBuddyPlanError("run plan scope is invalid")


def _load_base_config(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(
            _read_bounded_regular_bytes(path, "base Harbor Job config").decode("utf-8")
        )
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise WorkBuddyPlanError(f"cannot read base Harbor Job config: {path}") from exc
    if not isinstance(value, dict):
        raise WorkBuddyPlanError("base Harbor Job config must be a YAML object")
    return value


def _validate_base_ownership(base: dict[str, Any]) -> None:
    for key, label in (
        ("tasks", "select tasks"),
        ("datasets", "select datasets"),
        ("source_jobs", "derive source_jobs"),
    ):
        if base.get(key):
            raise WorkBuddyPlanError(f"base Harbor Job config must not {label}")
    if base.get("install_only"):
        raise WorkBuddyPlanError("base Harbor Job config must not use install_only")
    agents = base.get("agents")
    if not isinstance(agents, list) or len(agents) != 1:
        raise WorkBuddyPlanError(
            "base Harbor Job config must contain exactly one Agent"
        )
    verifier = base.get("verifier") or {}
    if not isinstance(verifier, dict):
        raise WorkBuddyPlanError("base Harbor verifier must be an object")
    import_path = verifier.get("import_path")
    if import_path not in {None, "", COMPOSITE_VERIFIER}:
        raise WorkBuddyPlanError("base Harbor Job config has a conflicting verifier")
    verifier_env = verifier.get("env") or {}
    if not isinstance(verifier_env, dict):
        raise WorkBuddyPlanError("base Harbor verifier env must be an object")
    for name in (*LLM_REQUIRED_ENV, LLM_OPTIONAL_ENV):
        if name in verifier_env and verifier_env[name] != f"${{{name}}}":
            raise WorkBuddyPlanError(
                f"base Harbor verifier {name} must use its environment reference"
            )
    try:
        JobConfig.model_validate(base)
    except ValueError as exc:
        raise WorkBuddyPlanError(f"invalid base Harbor Job config: {exc}") from exc


def _validate_llm_environment() -> None:
    present = [name for name in LLM_REQUIRED_ENV if os.environ.get(name)]
    if present and len(present) != len(LLM_REQUIRED_ENV):
        raise WorkBuddyPlanError(
            "WORKBUDDY_VERIFIER_LLM_BASE_URL, WORKBUDDY_VERIFIER_LLM_API_KEY, "
            "and WORKBUDDY_VERIFIER_LLM_MODEL must all be set or all be unset"
        )


def _adapt_explicit_host_environment(base: dict[str, Any]) -> bool:
    environment = base.get("environment") or {}
    if not isinstance(environment, dict):
        return False
    if environment.get("import_path") != f"{__package__}.environment:HostEnvironment":
        return False
    kwargs = environment.get("kwargs") or {}
    if not isinstance(kwargs, dict):
        raise WorkBuddyPlanError("HostEnvironment kwargs must be an object")
    allow_host_execution = kwargs.get("allow_host_execution")
    if not (
        allow_host_execution is True
        or (
            isinstance(allow_host_execution, str)
            and allow_host_execution.strip().lower() in {"1", "true", "yes", "on"}
        )
    ):
        raise WorkBuddyPlanError(
            "WorkBuddy host preparation requires explicit "
            "environment.kwargs.allow_host_execution=true"
        )
    validate_workbuddy_host_dependencies()
    kwargs["bootstrap_workbuddy_workspace"] = True
    environment["kwargs"] = kwargs
    environment["force_build"] = False
    environment["override_cpus"] = 0
    environment["override_memory_mb"] = 0
    environment["override_storage_mb"] = 0
    environment["override_gpus"] = 0
    base["environment"] = environment
    return True


def _compose_job(
    base: dict[str, Any],
    *,
    job_name: str,
    jobs_root: Path,
    task_root: Path,
    task_names: list[str],
    skill_dir: Path | None = None,
    host_mode: bool = False,
) -> dict[str, Any]:
    value = deepcopy(base)
    value["job_name"] = job_name
    value["jobs_dir"] = str(jobs_root)
    value["tasks"] = [{"path": str(task_root / name)} for name in task_names]
    value.pop("datasets", None)
    value.pop("source_jobs", None)
    value["n_attempts"] = value.get("n_attempts", 3)
    value["timeout_multiplier"] = value.get("timeout_multiplier", 2.0)
    verifier = dict(value.get("verifier") or {})
    verifier["import_path"] = (
        f"{__package__}.workbuddy_verifier:WindowsOfficeVerifier"
        if host_mode and platform.system() == "Windows"
        else COMPOSITE_VERIFIER
    )
    env = dict(verifier.get("env") or {})
    if all(os.environ.get(name) for name in LLM_REQUIRED_ENV):
        for name in LLM_REQUIRED_ENV:
            env[name] = f"${{{name}}}"
        if os.environ.get(LLM_OPTIONAL_ENV):
            env[LLM_OPTIONAL_ENV] = f"${{{LLM_OPTIONAL_ENV}}}"
    if env:
        verifier["env"] = env
    value["verifier"] = verifier
    if skill_dir is not None:
        agent = deepcopy(value["agents"][0])
        agent["skills"] = [*list(agent.get("skills") or []), str(skill_dir)]
        mcp_script = (
            "environment/mock_mcp/recruiting_search_lab_server.py"
            if host_mode
            else "/workspace/environment/mock_mcp/recruiting_search_lab_server.py"
        )
        mcp_root = "." if host_mode else "/workspace"
        agent["mcp_servers"] = [
            *list(agent.get("mcp_servers") or []),
            {
                "name": "recruiting_search_lab",
                "transport": "stdio",
                "command": sys.executable if host_mode else "python3",
                "args": [
                    mcp_script,
                    "--case-root",
                    mcp_root,
                    "serve-mcp-stdio",
                ],
            },
        ]
        agent_env = dict(agent.get("env") or {})
        workspace_prefix = "" if host_mode else "/workspace/"
        agent_env.update(
            {
                "RECRUITING_SEARCH_LAB_RUNTIME_STATE": f"{workspace_prefix}environment/mock_mcp/runtime_state_capture_by_harness/runtime_state.json",
                "RECRUITING_SEARCH_LAB_METHOD_LOG": f"{workspace_prefix}environment/mock_mcp/runtime_state_capture_by_harness/method_call_log.json",
                "RECRUITING_SEARCH_LAB_SNAPSHOT_DIR": f"{workspace_prefix}environment/mock_mcp/runtime_state_capture_by_harness/snapshots",
                "RECRUITING_SEARCH_LAB_EXPORT_DIR": f"{workspace_prefix}input/workspace/exports",
                "RECRUITING_SEARCH_LAB_RESET_STATE": "1",
            }
        )
        agent["env"] = agent_env
        value["agents"] = [agent]
        artifact_prefix = "" if host_mode else "/workspace/"
        value["artifacts"] = [
            *list(value.get("artifacts") or []),
            f"{artifact_prefix}environment/mock_mcp/runtime_state_capture_by_harness",
            f"{artifact_prefix}input/workspace/exports",
        ]
    try:
        validated = JobConfig.model_validate(value)
    except ValueError as exc:
        raise WorkBuddyPlanError(
            f"generated Harbor Job config is invalid: {exc}"
        ) from exc
    return validated.model_dump(mode="json", exclude_none=True)


def _extract_special_skill(
    resolved: ResolvedHarborDataset, destination_root: Path
) -> Path:
    archive = resolved.task_root / SPECIAL_TASK / "environment" / "workspace.tar.gz"
    destination = destination_root / "recruiting_search"
    prefix = PurePosixPath("agent_pack/skills/recruiting_search")
    total = 0
    found = False
    seen: dict[PurePosixPath, tuple[str, int, int, bytes]] = {}
    try:
        with _open_special_skill_archive(archive) as stream:
            for index, member in enumerate(stream, start=1):
                if index > SKILL_ENTRY_LIMIT:
                    raise WorkBuddyPlanError(
                        "special Skill archive exceeds 10000 entries"
                    )
                path = PurePosixPath(member.name)
                if (
                    path.is_absolute()
                    or "\\" in member.name
                    or any(part == ".." for part in path.parts)
                ):
                    raise WorkBuddyPlanError("special Skill archive path is unsafe")
                if path != prefix and prefix not in path.parents:
                    continue
                relative = path.relative_to(prefix)
                if (path == prefix and not member.isdir()) or any(
                    part.lower() in {"", ".", "..", ".git"} for part in relative.parts
                ):
                    raise WorkBuddyPlanError("special Skill archive path is unsafe")
                if (
                    member.issym()
                    or member.islnk()
                    or not (member.isdir() or member.isfile())
                ):
                    raise WorkBuddyPlanError("special Skill archive has unsafe entries")
                target = destination.joinpath(*relative.parts)
                if member.isdir():
                    identity = ("directory", member.mode & 0o777, 0, b"")
                    previous = seen.get(relative)
                    if previous is not None and previous != identity:
                        raise WorkBuddyPlanError(
                            "special Skill archive has conflicting duplicate paths"
                        )
                    seen[relative] = identity
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if member.size > SKILL_FILE_LIMIT:
                    raise WorkBuddyPlanError("special Skill file exceeds 2 MiB")
                total += member.size
                if total > SKILL_TOTAL_LIMIT:
                    raise WorkBuddyPlanError("special Skill exceeds 16 MiB")
                source = stream.extractfile(member)
                if source is None:
                    raise WorkBuddyPlanError("special Skill file cannot be read")
                content = source.read(SKILL_FILE_LIMIT + 1)
                if len(content) != member.size:
                    raise WorkBuddyPlanError("special Skill file is truncated")
                identity = (
                    "file",
                    member.mode & 0o777,
                    member.size,
                    hashlib.sha256(content).digest(),
                )
                previous = seen.get(relative)
                if previous is not None:
                    if previous != identity:
                        raise WorkBuddyPlanError(
                            "special Skill archive has conflicting duplicate paths"
                        )
                    continue
                seen[relative] = identity
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                target.chmod(member.mode & 0o755)
                found = True
    except (OSError, tarfile.TarError) as exc:
        raise WorkBuddyPlanError("special Skill archive cannot be read") from exc
    if not found or not (destination / "SKILL.md").is_file():
        raise WorkBuddyPlanError("special Skill archive has no recruiting_search Skill")
    return destination


@contextmanager
def _open_special_skill_archive(archive: Path) -> Iterator[tarfile.TarFile]:
    descriptor = -1
    try:
        before = archive.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            raise WorkBuddyPlanError("special Skill archive cannot be read")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(archive, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (
            before.st_ino
            and opened.st_ino
            and (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise WorkBuddyPlanError("special Skill archive cannot be read")
        raw = os.fdopen(descriptor, "rb")
        descriptor = -1
        with raw:
            try:
                stream = tarfile.open(fileobj=raw, mode="r:gz")
            except (OSError, tarfile.TarError) as exc:
                raise WorkBuddyPlanError(
                    "special Skill archive cannot be read"
                ) from exc
            with stream:
                yield stream
    except OSError as exc:
        raise WorkBuddyPlanError("special Skill archive cannot be read") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _office_warnings() -> list[str]:
    return [
        f"{SPECIAL_TASK} declares public network although the harness contract describes offline execution.",
        f"{SPECIAL_TASK} is missing /workspace/case.yaml and the workspace instruction expected by its gold answer; it remains included without patching or reweighting.",
        f"{SPECIAL_TASK} contains a broken upstream sanity-check path; interpret its score with the source-defect warning.",
    ]


def _new_plan_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dt%H%M%Sz").lower()
    return f"workbuddy-office-{stamp}-{secrets.token_hex(3)}"


def _output_root(value: str | Path) -> Path:
    if not str(value).strip():
        raise WorkBuddyPlanError("WorkBuddy output root must be nonempty")
    return Path(value).expanduser().resolve()


def _require_unlinked_path(path: Path, label: str) -> None:
    if path.is_symlink() or path.resolve() != path:
        raise WorkBuddyPlanError(f"WorkBuddy {label} traverses a symbolic link")


def _reserve_plan_directories(root: Path) -> tuple[str, Path, Path]:
    plan_root = root / "harbor-plans"
    jobs_root = root / "harbor-jobs"
    _require_unlinked_path(plan_root, "plan root")
    _require_unlinked_path(jobs_root, "Jobs root")
    try:
        plan_root.mkdir(parents=True, exist_ok=True)
        _require_unlinked_path(plan_root, "plan root")
        jobs_root.mkdir(parents=True, exist_ok=True)
        _require_unlinked_path(jobs_root, "Jobs root")
    except OSError as exc:
        raise WorkBuddyPlanError("cannot create WorkBuddy plan directories") from exc
    for _attempt in range(PLAN_ID_ATTEMPTS):
        plan_id = _new_plan_id()
        plan_dir = plan_root / plan_id
        job_dir = jobs_root / plan_id
        try:
            plan_dir.mkdir()
        except FileExistsError:
            continue
        except OSError as exc:
            raise WorkBuddyPlanError("cannot reserve a WorkBuddy run plan") from exc
        _require_unlinked_path(plan_dir, "plan directory")
        try:
            job_dir.mkdir()
        except FileExistsError:
            try:
                plan_dir.rmdir()
            except OSError as exc:
                raise WorkBuddyPlanError(
                    "cannot release a collided WorkBuddy run plan"
                ) from exc
            continue
        except OSError as exc:
            try:
                plan_dir.rmdir()
            except OSError:
                pass
            raise WorkBuddyPlanError("cannot reserve a WorkBuddy Jobs root") from exc
        _require_unlinked_path(job_dir, "Jobs directory")
        return plan_id, plan_dir, job_dir
    raise WorkBuddyPlanError("cannot allocate a unique WorkBuddy run plan id")


def _write_yaml(path: Path, value: dict[str, Any]) -> None:
    _atomic_write_text(path, yaml.safe_dump(value, sort_keys=False, allow_unicode=True))


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _atomic_write_text(path: Path, content: str) -> None:
    _require_unlinked_path(path, "output file")
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        _require_unlinked_path(path, "output file")
        temporary.replace(path)
    except OSError as exc:
        raise WorkBuddyPlanError(f"cannot write WorkBuddy output: {path}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_plan(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            _read_bounded_regular_bytes(path, "run plan").decode("utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkBuddyPlanError(f"cannot read WorkBuddy run plan: {path}") from exc
    if not isinstance(value, dict) or value.get("schema") != PLAN_SCHEMA:
        raise WorkBuddyPlanError("unsupported WorkBuddy run plan")
    _validate_plan_selection(value)
    return value


def _read_summary(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            _read_bounded_regular_bytes(path, "WorkBuddy summary").decode("utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkBuddyPlanError(f"cannot read WorkBuddy summary: {path}") from exc
    if not isinstance(value, dict) or value.get("schema") != SUMMARY_SCHEMA:
        raise WorkBuddyPlanError("unsupported WorkBuddy summary")
    _validate_plan_selection(value)
    return value


def _project_summary_metrics(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    required: dict[str, Any] = {}
    for key in ("reward", "pass_rate", "n_tasks", "n_trials"):
        item = value.get(key)
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return None
        if not math.isfinite(float(item)):
            return None
        required[key] = item
    missing = value.get("missing_tasks")
    required["missing_task_count"] = (
        len([item for item in missing if isinstance(item, str)])
        if isinstance(missing, list)
        else 0
    )
    attempts = value.get("attempts_per_task")
    if isinstance(attempts, list):
        required["attempts_per_task"] = [
            item for item in attempts[:16] if type(item) is int and 0 <= item <= 10_000
        ]
    sources = value.get("score_sources")
    if isinstance(sources, dict):
        required["score_sources"] = {
            key: item
            for key, item in sources.items()
            if isinstance(key, str)
            and _PUBLIC_METRIC_KEY.fullmatch(key)
            and type(item) is int
            and 0 <= item <= 1_000_000
        }
    per_attempt = value.get("per_attempt")
    if isinstance(per_attempt, list):
        projected_attempts = []
        for item in per_attempt[:16]:
            if not isinstance(item, dict):
                continue
            projected: dict[str, int | float] = {}
            for key in ("attempt", "n_tasks", "reward", "pass_rate"):
                field = item.get(key)
                if (
                    isinstance(field, (int, float))
                    and not isinstance(field, bool)
                    and math.isfinite(float(field))
                ):
                    projected[key] = field
            if projected:
                projected_attempts.append(projected)
        required["per_attempt"] = projected_attempts
    return required


def _plan_contained_path(root: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise WorkBuddyPlanError(f"run plan {label} is invalid")
    path = Path(value)
    absolute = Path(os.path.abspath(path))
    allowed = root / "harbor-jobs"
    if allowed not in absolute.parents:
        raise WorkBuddyPlanError(f"run plan {label} escapes the output root")
    if absolute.resolve(strict=False) != absolute:
        raise WorkBuddyPlanError(f"run plan {label} traverses a symbolic link")
    return absolute


def _job_is_terminal(job_dir: Path) -> bool:
    path = job_dir / "result.json"
    try:
        value = json.loads(
            _read_bounded_regular_bytes(path, "Harbor Job result").decode("utf-8")
        )
    except (WorkBuddyPlanError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(value, dict) and bool(value.get("finished_at"))


def _read_bounded_regular_bytes(path: Path, label: str) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_size > PLAN_FILE_LIMIT:
            raise WorkBuddyPlanError(f"{label} is not a bounded regular file")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or opened.st_size > PLAN_FILE_LIMIT:
                raise WorkBuddyPlanError(f"{label} is not a bounded regular file")
            if (
                before.st_ino
                and opened.st_ino
                and (
                    before.st_dev,
                    before.st_ino,
                )
                != (opened.st_dev, opened.st_ino)
            ):
                raise WorkBuddyPlanError(f"{label} changed while it was opened")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                content = stream.read(PLAN_FILE_LIMIT + 1)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise WorkBuddyPlanError(f"cannot read {label}: {path}") from exc
    if len(content) > PLAN_FILE_LIMIT:
        raise WorkBuddyPlanError(f"{label} is not a bounded regular file")
    return content


def _distribution_commit(
    distribution: importlib.metadata.Distribution,
) -> str | None:
    try:
        text = distribution.read_text("direct_url.json")
        direct = json.loads(text) if text else {}
    except (OSError, json.JSONDecodeError):
        return None
    vcs = direct.get("vcs_info") if isinstance(direct, dict) else None
    if isinstance(vcs, dict) and isinstance(vcs.get("commit_id"), str):
        return vcs["commit_id"]
    if not isinstance(direct, dict) or not isinstance(direct.get("url"), str):
        return None
    url = direct["url"]
    if not url.startswith("file://"):
        return None
    source = Path(url.removeprefix("file://"))
    if not (source / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None
