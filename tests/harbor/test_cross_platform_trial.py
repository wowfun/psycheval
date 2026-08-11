from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

from harbor.models.task.config import TaskOS
from harbor.utils.scripts import quote_shell_arg

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_TASK_ROOT = _REPOSITORY_ROOT / "datasets" / "pbench-v1.0" / "web-search-01"


def test_canned_host_trial_selects_native_verifier_entrypoint(tmp_path: Path) -> None:
    native_os = TaskOS.WINDOWS if platform.system() == "Windows" else TaskOS.LINUX
    if native_os == TaskOS.WINDOWS:
        harness_dir = tmp_path / "harness tools"
        harness_dir.mkdir()
        harness_entrypoint = harness_dir / "canned harness.bat"
        harness_entrypoint.write_text(
            "@echo off\r\n"
            f"{quote_shell_arg(sys.executable, native_os)} "
            "-m psycheval.harbor.canned_harness --scenario web-search\r\n",
            encoding="utf-8",
        )
        harness_command = quote_shell_arg(harness_entrypoint, native_os)
    else:
        harness_command = (
            f"{quote_shell_arg(sys.executable, native_os)} "
            "-m psycheval.harbor.canned_harness --scenario web-search"
        )
    jobs_dir = tmp_path / "jobs with spaces"
    job_name = "native-host-canned"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from harbor.cli.main import app; app()",
            "run",
            "--path",
            str(_TASK_ROOT),
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
    assert (trial_dir / "agent" / "trajectory.json").is_file()
    assert (trial_dir / "artifacts" / "manifest.json").is_file()
