from __future__ import annotations

import hashlib
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

from tests.fixtures.judge_server import judge_server

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "datasets/pbench-v1.0/trend-digest-01"


def hashes(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize("mode", ["partial", "source_failure", "delivery_failure"])
def test_three_step_native_trial_with_local_judge(tmp_path, mode):
    task = tmp_path / "中文 task"
    shutil.copytree(TASK, task, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # Every step's complete YAML replaces this shared declaration, not a field merge.
    (task / "tests/judge.yaml").write_text("shared_only: must not survive\n")
    before = hashes(task)
    jobs = tmp_path / "jobs"
    workspaces = tmp_path / "workspaces"
    host_os = TaskOS.WINDOWS if platform.system() == "Windows" else TaskOS.LINUX
    command = " ".join(
        quote_shell_arg(str(value), host_os)
        for value in (sys.executable, ROOT / "tests/fixtures/trend_harness.py")
    )
    with judge_server() as server:
        server["behavior"] = {
            name: {"passed": False}
            for name in ("summary_faithfulness", "information_value", "clear_chinese")
        }
        args = [
            sys.executable,
            "-X",
            "utf8",
            "-c",
            "from harbor.cli.main import app; app()",
            "run",
            "--path",
            str(task),
            "--jobs-dir",
            str(jobs),
            "--job-name",
            "trend",
            "--agent",
            "psycheval.harbor.agent:ExternalHarnessAgent",
            "--agent-kwarg",
            f"command={command}",
            "--env",
            "psycheval.harbor.environment:HostEnvironment",
            "--environment-kwarg",
            'host_access={"filesystem":true,"process":true}',
            "--environment-kwarg",
            f"workdir_root={workspaces}",
            "--verifier-import-path",
            "psycheval.harbor.verifier.host:HostVerifier",
            "--n-concurrent",
            "1",
            "--quiet",
            "--yes",
        ]
        for name, value in {
            "PEVAL_JUDGE_ENABLED": "true",
            "PEVAL_JUDGE_BASE_URL": server["url"],
            "PEVAL_JUDGE_MODEL": "fixture",
            "PBENCH_TREND_NOW": "2026-08-15T12:00:00Z",
            "PYTHONUTF8": "0",
        }.items():
            args.extend(["--verifier-env", f"{name}={value}"])
        result = subprocess.run(
            args,
            cwd=ROOT,
            capture_output=True,
            encoding="utf-8",
            env={
                **os.environ,
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "TREND_FIXTURE_MODE": mode,
            },
            timeout=100,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        trials = list((jobs / "trend").glob("*/result.json"))
        assert len(trials) == 1
        trial = trials[0].parent
        details = json.loads(trials[0].read_text(encoding="utf-8"))
        assert details.get("exception_info") is None, details
        assert all(
            step.get("exception_info") is None for step in details["step_results"]
        ), details["step_results"]
        step_dirs = list((trial / "steps").iterdir())
        assert {step.name for step in step_dirs} == (
            {"github", "x", "hacker-news"} if mode == "partial" else {"github"}
        )
        gh = json.loads((trial / "steps/github/verifier/reward.json").read_text())
        if mode == "partial":
            assert gh["rule_score"] == 22 / 23
            assert gh["llm_score"] == 0 and gh["reward"] == pytest.approx(0.8 * 22 / 23)
            assert len(server["requests"]) == 9
            assert {
                json.loads(request["messages"][1]["content"])["step_name"]
                for request in server["requests"]
            } == {"github", "x", "hacker-news"}
        else:
            gate = (
                "required_observation" if mode == "source_failure" else "final_answer"
            )
            assert gh[gate] == 0
        assert hashes(task) == before
        assert not any(workspaces.iterdir())
        assert (trial / "prepare.log").exists()
