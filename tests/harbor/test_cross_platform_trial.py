from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from harbor.models.task.config import TaskOS
from harbor.utils.scripts import quote_shell_arg

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_SINGLE_STEP_TASK_ROOT = _REPOSITORY_ROOT / "tests" / "fixtures" / "harbor-single-step"
_MULTI_STEP_TASK_ROOT = _REPOSITORY_ROOT / "tests" / "fixtures" / "harbor-multi-step"
_SYNTHETIC_HARNESS = _REPOSITORY_ROOT / "tests" / "fixtures" / "synthetic_harness.py"


def _run_multi_step_job(
    task_root: Path,
    jobs_dir: Path,
    job_name: str,
    *,
    resume: bool = False,
    load_trajectory: Path | None = None,
    workspace: Path | None = None,
    peval_config: Path | None = None,
    delete: bool = True,
    n_attempts: int = 1,
    n_concurrent: int = 1,
) -> subprocess.CompletedProcess[str]:
    native_os = TaskOS.WINDOWS if platform.system() == "Windows" else TaskOS.LINUX
    harness_command = (
        f"{quote_shell_arg(sys.executable, native_os)} "
        f"{quote_shell_arg(str(_SYNTHETIC_HARNESS), native_os)} --mode multi-step"
    )
    command = [
        sys.executable,
        "-c",
        "from harbor.cli.main import app; app()",
        "run",
        "--path",
        str(task_root),
        "--agent",
        "psycheval.harbor.agent:ExternalHarnessAgent",
        "--agent-kwarg",
        f"command={harness_command}",
        "--env",
        "psycheval.harbor.environment:HostEnvironment",
        "--environment-kwarg",
        "allow_host_execution=true",
        "--jobs-dir",
        str(jobs_dir),
        "--job-name",
        job_name,
        "--n-concurrent",
        str(n_concurrent),
        "--quiet",
        "--yes",
    ]
    if resume:
        command.append("--resume-trajectory")
    if n_attempts != 1:
        command.extend(["--n-attempts", str(n_attempts)])
    if not delete:
        command.append("--no-delete")
    if load_trajectory is not None:
        command.extend(["--load-trajectory", str(load_trajectory)])
    if workspace is not None:
        command.extend(
            [
                "--mounts",
                json.dumps(
                    [
                        {
                            "type": "bind",
                            "source": str(workspace),
                            "target": "/workspace",
                        }
                    ]
                ),
                "--agent-kwarg",
                "workdir=/workspace",
            ]
        )
    environment = os.environ.copy()
    if peval_config is not None:
        environment["PEVAL_CONFIG"] = str(peval_config)
    return subprocess.run(
        command,
        cwd=_REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        env=environment,
        timeout=90,
        check=False,
    )


def _only_trial_result(jobs_dir: Path, job_name: str) -> tuple[Path, dict]:
    result_paths = list((jobs_dir / job_name).glob("*/result.json"))
    assert len(result_paths) == 1
    return (
        result_paths[0].parent,
        json.loads(result_paths[0].read_text(encoding="utf-8")),
    )


def _copy_multi_step_fixture(tmp_path: Path) -> Path:
    task_root = tmp_path / "harbor-multi-step"
    shutil.copytree(_MULTI_STEP_TASK_ROOT, task_root)
    return task_root


def _make_seed_artifact_check_fail(task_root: Path) -> None:
    grader = task_root / "steps" / "seed" / "tests" / "grader.json"
    config = json.loads(grader.read_text(encoding="utf-8"))
    config["required_artifacts"] = ["missing-seed.txt"]
    grader.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def test_synthetic_host_trial_selects_native_verifier_entrypoint(
    tmp_path: Path,
) -> None:
    native_os = TaskOS.WINDOWS if platform.system() == "Windows" else TaskOS.LINUX
    if native_os == TaskOS.WINDOWS:
        harness_dir = tmp_path / "harness tools"
        harness_dir.mkdir()
        harness_entrypoint = harness_dir / "synthetic fixture.bat"
        harness_entrypoint.write_text(
            "@echo off\r\n"
            f"{quote_shell_arg(sys.executable, native_os)} "
            f"{quote_shell_arg(str(_SYNTHETIC_HARNESS), native_os)} "
            "--mode single-step\r\n",
            encoding="utf-8",
        )
        harness_command = quote_shell_arg(harness_entrypoint, native_os)
    else:
        harness_command = (
            f"{quote_shell_arg(sys.executable, native_os)} "
            f"{quote_shell_arg(str(_SYNTHETIC_HARNESS), native_os)} "
            "--mode single-step"
        )
    jobs_dir = tmp_path / "jobs with spaces"
    job_name = "native-host-synthetic"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from harbor.cli.main import app; app()",
            "run",
            "--path",
            str(_SINGLE_STEP_TASK_ROOT),
            "--agent",
            "psycheval.harbor.agent:ExternalHarnessAgent",
            "--agent-kwarg",
            f"command={harness_command}",
            "--env",
            "psycheval.harbor.environment:HostEnvironment",
            "--environment-kwarg",
            "allow_host_execution=true",
            "--jobs-dir",
            str(jobs_dir),
            "--job-name",
            job_name,
            "--n-concurrent",
            "1",
            "--quiet",
            "--yes",
        ],
        cwd=_REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    job_dir = jobs_dir / job_name
    reward_paths = list(job_dir.glob("*/verifier/reward.json"))
    assert len(reward_paths) == 1
    trial_dir = reward_paths[0].parents[1]
    trial_result = json.loads((trial_dir / "result.json").read_text(encoding="utf-8"))
    rewards = json.loads(reward_paths[0].read_text(encoding="utf-8"))
    test_stdout = (trial_dir / "verifier" / "test-stdout.txt").read_text(
        encoding="utf-8"
    )

    assert trial_result["exception_info"] is None
    assert rewards
    assert set(rewards.values()) == {1}
    expected_entrypoint = "bat" if native_os == TaskOS.WINDOWS else "sh"
    assert f"psycheval-test-entrypoint={expected_entrypoint}" in test_stdout
    trajectory = json.loads(
        (trial_dir / "agent" / "trajectory.json").read_text(encoding="utf-8")
    )
    assert trajectory["agent"]["name"] == "psycheval-test-fixture"
    assert (trial_dir / "artifacts" / "manifest.json").is_file()


@pytest.mark.parametrize("resume", [False, True], ids=["fresh", "resume"])
def test_synthetic_host_multi_step_trial_is_step_local(
    tmp_path: Path, resume: bool
) -> None:
    jobs_dir = tmp_path / "multi step jobs"
    job_name = "native-host-multi-step-" + ("resume" if resume else "fresh")
    completed = _run_multi_step_job(
        _MULTI_STEP_TASK_ROOT, jobs_dir, job_name, resume=resume
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    trial_dir, result = _only_trial_result(jobs_dir, job_name)
    assert result["exception_info"] is None
    assert [step["step_name"] for step in result["step_results"]] == [
        "seed",
        "continue",
        "finish",
    ]
    assert all(step["exception_info"] is None for step in result["step_results"])
    assert set(result["verifier_result"]["rewards"].values()) == {1.0}

    trajectories = [
        json.loads(
            (trial_dir / "steps" / name / "agent" / "trajectory.json").read_text(
                encoding="utf-8"
            )
        )
        for name in ("seed", "continue", "finish")
    ]
    assert {trajectory["agent"]["name"] for trajectory in trajectories} == {
        "psycheval-test-fixture"
    }
    expected_actions = ["run", "resume", "resume"] if resume else ["run"] * 3
    assert [trajectory["extra"]["harness_action"] for trajectory in trajectories] == (
        expected_actions
    )
    expected_sequences = [1, 2, 3] if resume else [1, 1, 1]
    assert [trajectory["extra"]["session_sequence"] for trajectory in trajectories] == (
        expected_sequences
    )
    session_ids = [trajectory["session_id"] for trajectory in trajectories]
    assert (len(set(session_ids)) == 1) is resume
    assert (
        trial_dir
        / "steps"
        / "continue"
        / "artifacts"
        / "logs"
        / "agent"
        / "trajectory.json"
    ).is_file()
    for name in ("seed", "continue", "finish"):
        step_dir = trial_dir / "steps" / name
        assert (step_dir / "verifier" / "checks.json").is_file()
        assert (step_dir / "verifier" / "reward.json").is_file()
        assert (step_dir / "artifacts" / "logs" / "artifacts" / f"{name}.txt").is_file()


def test_synthetic_host_multi_step_uses_bound_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "bound workspace"
    workspace.mkdir()
    unrelated = workspace / "keep.txt"
    unrelated.write_text("keep\n", encoding="utf-8")
    jobs_dir = tmp_path / "workspace jobs"
    job_name = "native-host-bound-workspace"

    completed = _run_multi_step_job(
        _MULTI_STEP_TASK_ROOT,
        jobs_dir,
        job_name,
        resume=True,
        workspace=workspace,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    trial_dir, result = _only_trial_result(jobs_dir, job_name)
    assert result["exception_info"] is None
    assert [step["step_name"] for step in result["step_results"]] == [
        "seed",
        "continue",
        "finish",
    ]
    assert (workspace / "multi-step-workspace.txt").read_text(
        encoding="utf-8"
    ) == "workspace-ready\n"
    assert unrelated.read_text(encoding="utf-8") == "keep\n"
    assert all(
        (trial_dir / "steps" / name / "agent" / "trajectory.json").is_file()
        for name in ("seed", "continue", "finish")
    )
    assert all(
        (
            trial_dir
            / "steps"
            / name
            / "artifacts"
            / "logs"
            / "artifacts"
            / f"{name}.txt"
        ).is_file()
        for name in ("seed", "continue", "finish")
    )


def test_synthetic_host_multi_step_uses_isolated_anonymous_workspaces(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "anonymous workspaces"
    config = tmp_path / "peval.toml"
    config.write_text(
        f"[harbor.host]\nworkdir_root = {json.dumps(str(workspace_root))}\n",
        encoding="utf-8",
    )
    original_config = config.read_bytes()
    jobs_dir = tmp_path / "anonymous jobs"
    job_name = "native-host-anonymous-workspaces"

    completed = _run_multi_step_job(
        _MULTI_STEP_TASK_ROOT,
        jobs_dir,
        job_name,
        resume=True,
        peval_config=config,
        delete=False,
        n_attempts=2,
        n_concurrent=2,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    trial_dirs = sorted(
        path.parent for path in (jobs_dir / job_name).glob("*/result.json")
    )
    workspaces = sorted(path for path in workspace_root.iterdir() if path.is_dir())
    assert len(trial_dirs) == 2
    assert len(workspaces) == 2
    assert {path.name for path in workspaces} == {
        path.name.rsplit("__", 1)[-1] for path in trial_dirs
    }
    assert all(len(path.name) == 7 for path in workspaces)
    assert all((path / "multi-step-workspace.txt").is_file() for path in workspaces)
    for trial_dir in trial_dirs:
        result = json.loads((trial_dir / "result.json").read_text(encoding="utf-8"))
        assert result["exception_info"] is None
        assert [step["step_name"] for step in result["step_results"]] == [
            "seed",
            "continue",
            "finish",
        ]
        assert all(
            (trial_dir / "steps" / name / "agent" / "trajectory.json").is_file()
            for name in ("seed", "continue", "finish")
        )
        assert all(
            (
                trial_dir
                / "steps"
                / name
                / "artifacts"
                / "logs"
                / "artifacts"
                / f"{name}.txt"
            ).is_file()
            for name in ("seed", "continue", "finish")
        )
    assert config.read_bytes() == original_config


def test_synthetic_host_multi_step_final_reward_selects_last_step(
    tmp_path: Path,
) -> None:
    task_root = _copy_multi_step_fixture(tmp_path / "task")
    task_config = task_root / "task.toml"
    source = task_config.read_text(encoding="utf-8")
    source = source.replace(
        'multi_step_reward_strategy = "mean"',
        'multi_step_reward_strategy = "final"',
    )
    source = source.replace("min_reward = 1.0\n", "", 1)
    task_config.write_text(source, encoding="utf-8")
    _make_seed_artifact_check_fail(task_root)

    jobs_dir = tmp_path / "jobs"
    job_name = "multi-step-final"
    completed = _run_multi_step_job(task_root, jobs_dir, job_name)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    _trial_dir, result = _only_trial_result(jobs_dir, job_name)

    assert [
        step["verifier_result"]["rewards"]["reward"] for step in result["step_results"]
    ] == [0, 1, 1]
    assert result["verifier_result"] == result["step_results"][-1]["verifier_result"]


def test_synthetic_host_multi_step_min_reward_stops_remaining_steps(
    tmp_path: Path,
) -> None:
    task_root = _copy_multi_step_fixture(tmp_path / "task")
    _make_seed_artifact_check_fail(task_root)

    jobs_dir = tmp_path / "jobs"
    job_name = "multi-step-stop"
    completed = _run_multi_step_job(task_root, jobs_dir, job_name)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    trial_dir, result = _only_trial_result(jobs_dir, job_name)

    assert [step["step_name"] for step in result["step_results"]] == ["seed"]
    assert result["step_results"][0]["verifier_result"]["rewards"]["reward"] == 0
    assert not (trial_dir / "steps" / "continue").exists()
    assert not (trial_dir / "steps" / "finish").exists()


def test_external_harness_load_trajectory_fails_before_execution(
    tmp_path: Path,
) -> None:
    seed = tmp_path / "seed.json"
    seed.write_text("{}\n", encoding="utf-8")
    jobs_dir = tmp_path / "jobs"
    job_name = "multi-step-load-fail"

    completed = _run_multi_step_job(
        _MULTI_STEP_TASK_ROOT,
        jobs_dir,
        job_name,
        load_trajectory=seed,
    )

    assert completed.returncode != 0
    output = completed.stdout + completed.stderr
    assert "does not support loading an" in output
    assert "ATIF trajectory" in output
    assert not list((jobs_dir / job_name).glob("*/agent/external-harness.stdout.log"))
