from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import pytest
from harbor.models.task.task import Task

from psycheval.harbor.verifier import aggregate, build_scoring_plan
from psycheval.harbor.verifier.host import HostVerifier
from tests.harbor.test_environment import make_environment
from tests.harbor.test_verifier import _run_cli


def test_fixed_weighted_plan_preserves_missing_items():
    plan = build_scoring_plan(
        {
            "custom_checks": ["values", "format"],
            "scoring": {"weights": {"custom:values": 3}},
        }
    )
    checks = [{"id": "custom:values", "passed": True}]
    assert aggregate(checks, plan=plan)["reward"] == 0.75
    assert aggregate(checks, plan=plan)["custom_outputs"] == 0.75
    assert aggregate([], plan=plan)["reward"] == 0
    assert (
        aggregate(
            checks, plan=build_scoring_plan({"custom_checks": ["values", "format"]})
        )["reward"]
        == 0.5
    )


def test_weights_span_builtin_and_custom_checks_and_allow_zero_weight():
    plan = build_scoring_plan(
        {
            "final_terms": ["done"],
            "custom_checks": ["values", "ignored"],
            "scoring": {"weights": {"final_answer": 3, "custom:ignored": 0}},
        }
    )
    result = aggregate(
        [
            {"id": "final_answer", "passed": False},
            {"id": "custom:values", "passed": True},
            {"id": "custom:ignored", "passed": False},
        ],
        plan=plan,
    )
    assert result["reward"] == 0.25
    assert result["final_answer"] == 0
    assert result["custom_outputs"] == 1


@pytest.mark.parametrize(
    "config",
    [
        {"custom_checks": ["x", "x"]},
        {"custom_checks": [""]},
        *(
            {"custom_checks": ["x"], "scoring": {"weights": {"custom:x": value}}}
            for value in [-1, 0, True, "1", float("inf"), float("nan")]
        ),
        {"custom_checks": ["x"], "scoring": {"weights": {"unknown": 1}}},
    ],
)
def test_invalid_scoring_plans(config):
    with pytest.raises(ValueError):
        build_scoring_plan(config)


@pytest.mark.parametrize(
    "checks",
    [
        [{"id": "custom:y", "passed": True}],
        [{"id": "custom:x", "passed": True}] * 2,
        [{"id": "custom:x", "passed": 1}],
        [{"id": "custom:x", "passed": True, "evidence": {}}],
    ],
)
def test_invalid_result_protocol(checks):
    with pytest.raises(ValueError):
        aggregate(checks, plan=build_scoring_plan({"custom_checks": ["x"]}))


def write_custom_task(tests):
    (tests / "gt").mkdir(parents=True)
    (tests / "gt/answer.txt").write_text("目标数据", encoding="utf-8")
    (tests / "helper.py").write_text(
        "def matches(a, b): return a == b\n", encoding="utf-8"
    )
    (tests / "grader.json").write_text(
        json.dumps(
            {
                "custom_checks": ["values", "format"],
                "scoring": {"weights": {"custom:values": 3}},
            }
        ),
        encoding="utf-8",
    )
    (tests / "test_outputs.py").write_text(
        """import argparse, json
from pathlib import Path
from helper import matches
p = argparse.ArgumentParser()
p.add_argument('--context')
p.add_argument('--output')
args = p.parse_args()
context = json.loads(Path(args.context).read_text(encoding='utf-8'))
workdir = Path(context['paths']['workdir'])
assert Path.cwd() == workdir
assert not (workdir / 'gt').exists()
actual = (workdir / 'answer.txt').read_text(encoding='utf-8')
expected = (Path(__file__).parent / 'gt/answer.txt').read_text(encoding='utf-8')
Path(args.output).write_text(json.dumps({'checks': [{'id': 'values', 'passed': matches(actual, expected), 'evidence': '读取 GT'}]}, ensure_ascii=False), encoding='utf-8')
print('自定义校验完成')
""",
        encoding="utf-8",
    )
    (tests / "test.sh").write_text(
        '#!/bin/sh\npython -m psycheval.harbor.verifier "$(dirname "$0")/grader.json"\n'
    )
    (tests / "test.bat").write_text(
        '@echo off\npython -m psycheval.harbor.verifier "%~dp0grader.json"\n'
    )


def test_custom_only_cli_gt_helpers_and_missing_check_without_trajectory(tmp_path):
    root = tmp_path / "中文 space"
    tests = root / "tests"
    write_custom_task(tests)
    (tests / "answer.txt").write_text("目标数据", encoding="utf-8")
    # Use the Host test below for strict workspace/test isolation. Here the helper
    # config deliberately uses one directory for both paths.
    script = tests / "test_outputs.py"
    script.write_text(
        script.read_text(encoding="utf-8").replace(
            "assert not (workdir / 'gt').exists()",
            "assert not Path(context['paths']['agent_logs']).exists()",
        ),
        encoding="utf-8",
    )
    logs = root / "verifier"
    result = _run_cli(
        tests / "grader.json", root / "no-trajectory", logs, root / "artifacts"
    )
    assert result.returncode == 0, result.stderr
    assert json.loads((logs / "reward.json").read_text())["reward"] == 0.75
    details = json.loads((logs / "checks.json").read_text())
    assert details["checks"][1]["missing"] is True
    assert details["plan"]["total_weight"] == 4
    assert "自定义" in (logs / "custom-stdout.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "failure",
    [
        "exit",
        "malformed",
        "missing",
        "undeclared",
        "missing_script",
        "duplicate",
        "unknown",
    ],
)
def test_custom_verifier_errors_never_reuse_old_reward(tmp_path, failure):
    write_custom_task(tmp_path)
    script = tmp_path / "test_outputs.py"
    if failure == "exit":
        script.write_text("raise RuntimeError('grader crashed')")
    elif failure == "malformed":
        script.write_text(
            "import sys; from pathlib import Path; Path(sys.argv[-1]).write_text('{bad')"
        )
    elif failure == "missing":
        script.write_text("print('no output')")
    elif failure == "undeclared":
        (tmp_path / "grader.json").write_text('{"final_terms":["ok"]}')
    elif failure == "missing_script":
        script.unlink()
    else:
        payload = {
            "checks": (
                [{"id": "values", "passed": True}] * 2
                if failure == "duplicate"
                else [{"id": "unknown", "passed": True}]
            )
        }
        script.write_text(
            f"import sys; from pathlib import Path; Path(sys.argv[-1]).write_text({json.dumps(payload)!r})"
        )
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "reward.json").write_text('{"reward":1}')
    (logs / "reward.txt").write_text("1")
    (logs / "checks.json").write_text("{}")
    result = _run_cli(
        tmp_path / "grader.json", tmp_path / "agent", logs, tmp_path / "artifacts"
    )
    assert result.returncode != 0
    assert not (logs / "reward.json").exists()
    assert not (logs / "reward.txt").exists()
    assert (logs / "verifier-error.txt").is_file()


def test_host_stages_gt_and_clears_previous_step_files(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONUTF8", "0")
    host = make_environment(
        tmp_path / "host", environment_kwargs={"workdir_root": tmp_path / "workspaces"}
    )
    task_dir = host.environment_dir.parent
    (task_dir / "task.toml").write_text('[environment]\nworkdir = "/app"\n')
    (task_dir / "instruction.md").write_text("fixture")
    tests = task_dir / "tests"
    write_custom_task(tests)
    (host.environment_dir / "data/answer.txt").write_text("目标数据", encoding="utf-8")
    task = Task(task_dir)

    async def run():
        await host.start(False)
        try:
            verifier = HostVerifier(
                task=task, trial_paths=host.trial_paths, environment=host
            )
            assert (await verifier.verify()).rewards["reward"] == 0.75
            previous = host.native_path("/tests/previous.py")
            previous.write_text("stale step")
            assert (await verifier.verify()).rewards["reward"] == 0.75
            assert not previous.exists()
            assert not (host.work_dir / "gt").exists()
            assert not (tests / "__pycache__").exists()
        finally:
            await host.stop(True)

    asyncio.run(run())


def test_custom_verifier_timeout_cleans_descendants_without_reward(tmp_path):
    host = make_environment(
        tmp_path / "host",
        environment_kwargs={
            "workdir_root": tmp_path / "workspaces",
            "workspace_baseline": "none",
        },
    )
    task_dir = host.environment_dir.parent
    (task_dir / "task.toml").write_text('[environment]\nworkdir = "/app"\n')
    (task_dir / "instruction.md").write_text("fixture")
    tests = task_dir / "tests"
    write_custom_task(tests)
    marker = tmp_path / "verifier-pids.json"
    (tests / "test_outputs.py").write_text(
        f"""import subprocess, sys, time, json, os
from pathlib import Path
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
Path({str(marker)!r}).write_text(json.dumps([os.getpid(), child.pid]))
print('verifier started', flush=True)
time.sleep(60)
""",
        encoding="utf-8",
    )

    async def run():
        await host.start(False)
        try:
            logs = host.trial_paths.verifier_dir
            (logs / "reward.json").write_text('{"reward":1}')
            verifier = HostVerifier(
                task=Task(task_dir), trial_paths=host.trial_paths, environment=host
            )
            operation = asyncio.create_task(verifier.verify())
            async with asyncio.timeout(10):
                stdout = logs / "custom-stdout.txt"
                while not (
                    marker.exists()
                    and stdout.exists()
                    and "verifier started" in stdout.read_text(encoding="utf-8")
                ):
                    await asyncio.sleep(0.01)
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(operation, timeout=0.01)
            import psutil

            for pid in json.loads(marker.read_text()):
                assert (
                    not psutil.pid_exists(pid)
                    or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
                )
            assert not (logs / "reward.json").exists()
            assert "verifier started" in stdout.read_text(encoding="utf-8")
        finally:
            await host.stop(True)

    asyncio.run(run())


def test_prepared_files_example_scores_partial_credit_end_to_end(tmp_path):
    host = make_environment(
        tmp_path / "host", environment_kwargs={"workdir_root": tmp_path / "workspaces"}
    )
    task_dir = host.environment_dir.parent
    example = (
        Path(__file__).resolve().parents[2] / "examples/tasks/native-prepared-files"
    )
    shutil.copytree(example, task_dir, dirs_exist_ok=True)

    async def run():
        await host.start(False)
        try:
            data = json.loads(
                (host.work_dir / "input.json").read_text(encoding="utf-8")
            )
            assert data["as_of"] == "2026-09-17"
            (host.work_dir / "output.json").write_text(
                json.dumps({"total": sum(data["values"]), "as_of": "wrong date"})
            )
            result = await HostVerifier(
                task=Task(task_dir), trial_paths=host.trial_paths, environment=host
            ).verify()
            assert result.rewards["reward"] == 0.75
            assert not (host.work_dir / "gt").exists()
        finally:
            await host.stop(True)

    asyncio.run(run())
