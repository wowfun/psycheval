"""Workspace orchestration and CLI output for Harbor run plans."""

from __future__ import annotations

import platform
import shlex
from pathlib import Path
from typing import Any

from psycheval.config import (
    HarborMount,
    ToolConfig,
    load_config,
    write_workspace_harbor_config,
)
from psycheval.harbor import windows, workbuddy
from psycheval.harbor.workbuddy import WorkBuddyPlanError


def prepare_workbuddy_plan(
    *,
    workspace_root: str | Path | None,
    dataset_id: str,
    base_config: str | Path,
    task_selection: list[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    root, config = _workspace(workspace_root)
    registered = next(
        (dataset for dataset in config.harbor_datasets if dataset.id == dataset_id),
        None,
    )
    if registered is None:
        raise WorkBuddyPlanError(f"registered Dataset not found: {dataset_id}")
    plan = workbuddy.prepare_workbuddy_plan(
        output_root=root,
        dataset_id=registered.id,
        dataset_path=registered.path,
        base_config=base_config,
        task_selection=task_selection,
        limit=limit,
        allow_partial=registered.allow_partial,
    )
    plan_id = plan["plan_id"]
    jobs_root = plan["jobs_root"]
    warnings = plan["warnings"]
    host_mode = plan["host_environment"]
    mount = HarborMount(id=plan_id, path=str(jobs_root), dataset_ids=(registered.id,))
    write_workspace_harbor_config(
        root / "peval.toml",
        config.harbor_datasets,
        (*config.harbor_mounts, mount),
    )
    for warning in warnings:
        print(f"warning: {warning}")
    native_windows = platform.system() == "Windows"
    if host_mode and native_windows:
        print(
            "$env:PEVAL_CONFIG = "
            + windows.quote_powershell_literal(str(root / "peval.toml"))
        )
    for item in plan["jobs"]:
        command = ["harbor", "run", "-c", str(item["config"])]
        if host_mode and not native_windows:
            command = ["env", f"PEVAL_CONFIG={root / 'peval.toml'}", *command]
        print(
            windows.powershell_command(command)
            if native_windows
            else shlex.join(command)
        )
    print(
        (windows.powershell_command if native_windows else shlex.join)(
            [
                "peval",
                "harbor",
                "summarize",
                "--root",
                str(root),
                "--plan",
                plan_id,
            ]
        )
    )
    return plan


def summarize_workbuddy_plan(
    *, workspace_root: str | Path | None, plan_id: str, provisional: bool = False
) -> dict[str, Any]:
    root, _config = _workspace(workspace_root)
    snapshot = workbuddy.summarize_workbuddy_plan(
        output_root=root, plan_id=plan_id, provisional=provisional
    )
    metrics = snapshot["metrics"]
    print(f"WorkBuddy Benchmark Summary ({snapshot['scope']})")
    print(f"reward: {float(metrics.get('reward', 0.0)):.4f}")
    print(f"pass_rate: {float(metrics.get('pass_rate', 0.0)):.4f}")
    print(f"tasks: {metrics.get('n_tasks', 0)}; trials: {metrics.get('n_trials', 0)}")
    for warning in snapshot["warnings"]:
        print(f"warning: {warning}")
    return snapshot


def _workspace(root: str | Path | None) -> tuple[Path, ToolConfig]:
    config = load_config(workspace_root=root)
    if config.workspace_root is None:
        raise WorkBuddyPlanError("peval workspace not found; run peval init first")
    workspace = Path(config.workspace_root).resolve()
    return workspace, config
