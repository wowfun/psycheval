from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import psutil
import pytest
from harbor.models.task.task import Task

from psycheval.harbor.verifier import aggregate, build_scoring_plan
from psycheval.harbor.verifier.host import HostVerifier
from tests.harbor.environment_support import assert_process_exited, make_environment
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
    assert "continuation" not in result


def test_descriptions_are_optional_metadata_for_builtin_and_custom_checks():
    config = {
        "final_terms": ["done"],
        "custom_checks": ["content", "delivery"],
        "scoring": {"weights": {"custom:delivery": 0}},
        "continuation_checks": ["custom:delivery"],
    }
    descriptions = {
        "final_answer": "最终回复是否包含所需文字？",
        "custom:delivery": "Check that the artifact was delivered.",
    }
    original = build_scoring_plan(config)
    plan = build_scoring_plan(
        {**config, "scoring": {**config["scoring"], "descriptions": descriptions}}
    )
    assert {item.id: item.description for item in plan.items} == {
        **descriptions,
        "custom:content": None,
    }
    checks = [
        {"id": "final_answer", "passed": True},
        {"id": "custom:content", "passed": True},
        {"id": "custom:delivery", "passed": False},
    ]
    assert aggregate(checks, plan=plan) == aggregate(checks, plan=original)


@pytest.mark.parametrize(
    "descriptions",
    [
        None,
        [],
        "description",
        {"x": "Use the declared ID"},
        {"llm:x": "Judge question"},
        {"custom:x": False},
        {"custom:x": None},
        {"custom:x": ""},
        {"custom:x": " \n\t "},
        {"custom:x": "\ud800"},
    ],
)
def test_invalid_scoring_descriptions(descriptions):
    with pytest.raises(ValueError, match=r"scoring\.descriptions"):
        build_scoring_plan(
            {"custom_checks": ["x"], "scoring": {"descriptions": descriptions}}
        )


@pytest.mark.parametrize("weight", [0, 0.05, 1])
@pytest.mark.parametrize("quality", [False, True])
@pytest.mark.parametrize(
    ("answer", "delivery"),
    [(True, True), (False, True), (None, True), (True, False), (True, None)],
)
def test_continuation_uses_check_results_independently_of_weights(
    weight, quality, answer, delivery
):
    config = {
        "final_terms": ["done"],
        "custom_checks": ["quality", "delivery"],
        "scoring": {"weights": {"final_answer": weight, "custom:delivery": weight}},
    }
    checks = [
        {"id": key, "passed": value}
        for key, value in (
            ("final_answer", answer),
            ("custom:quality", quality),
            ("custom:delivery", delivery),
        )
        if value is not None
    ]
    original = aggregate(checks, plan=build_scoring_plan(config))
    plan = build_scoring_plan(
        {**config, "continuation_checks": ["final_answer", "custom:delivery"]}
    )
    actual = aggregate(checks, plan=plan)
    assert actual.pop("continuation") == float(answer is True and delivery is True)
    assert actual == original
    if weight == 0:
        assert actual["reward"] == float(quality)
        assert actual["final_answer"] == 1  # A neutral dimension is not a gate.


@pytest.mark.parametrize(
    "references",
    [
        None,
        [],
        "custom:x",
        {},
        True,
        [1],
        [[]],
        [""],
        ["x"],
        ["llm:x"],
        ["custom:unknown"],
        ["custom:x", "custom:x"],
    ],
)
def test_invalid_continuation_references(references):
    with pytest.raises(ValueError, match="continuation_checks"):
        build_scoring_plan({"custom_checks": ["x"], "continuation_checks": references})


def test_continuation_still_requires_positive_quality_weight():
    with pytest.raises(ValueError, match="total scoring weight"):
        build_scoring_plan(
            {
                "custom_checks": ["delivery"],
                "scoring": {"weights": {"custom:delivery": 0}},
                "continuation_checks": ["custom:delivery"],
            }
        )


@pytest.mark.parametrize(
    "config",
    [
        {"custom_checks": ["x", "x"]},
        {"custom_checks": [""]},
        {"custom_checks": ["\ud800"]},
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
    assert (
        json.loads((logs / "reward.json").read_text(encoding="utf-8"))["reward"] == 0.75
    )
    raw = (logs / "score.json").read_text(encoding="utf-8")
    assert "读取 GT" in raw
    details = json.loads(raw)
    assert details["verdicts"][0]["reason"] == "读取 GT"
    assert details["verdicts"][1]["metadata"]["missing"] is True
    assert "plan" not in details
    assert [
        (check["item_id"], check["metadata"]["dimension"], check["metadata"]["weight"])
        for check in details["verdicts"]
    ] == [
        ("custom:values", "custom_outputs", 3),
        ("custom:format", "custom_outputs", 1),
    ]
    assert sum(check["metadata"]["weight"] for check in details["verdicts"]) == 4
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
    (logs / "score.json").write_text("{}")
    (logs / "checks.json").write_text("{}")
    result = _run_cli(
        tmp_path / "grader.json", tmp_path / "agent", logs, tmp_path / "artifacts"
    )
    assert result.returncode != 0
    assert not (logs / "reward.json").exists()
    assert not (logs / "reward.txt").exists()
    assert not (logs / "score.json").exists()
    assert not (logs / "checks.json").exists()
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
            identities = [
                (pid, psutil.Process(pid).create_time())
                for pid in json.loads(marker.read_text())
            ]
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(operation, timeout=0.01)
            for pid, created_at in identities:
                assert_process_exited(pid, created_at)
            assert not (logs / "reward.json").exists()
            assert "verifier started" in stdout.read_text(encoding="utf-8")
        finally:
            await host.stop(True)

    asyncio.run(run())


def test_prepared_files_example_rejects_inconsistent_gt(tmp_path, monkeypatch):
    import runpy
    import sys

    example = (
        Path(__file__).resolve().parents[2] / "examples/tasks/native-prepared-files"
    )
    task = tmp_path / "task"
    shutil.copytree(example, task)
    inputs, state = tmp_path / "inputs", tmp_path / "state"
    inputs.mkdir()
    state.mkdir()
    runpy.run_path(str(task / "environment/prepare.py"))["prepare"](
        str(inputs), str(state)
    )
    (task / "tests/gt/expected.json").write_text(
        '{"total": -1, "as_of": "2026-09-17"}', encoding="utf-8"
    )
    context = tmp_path / "context.json"
    context.write_text(
        json.dumps(
            {
                "paths": {
                    "inputs": str(inputs),
                    "preparation_state": str(state),
                    "workdir": str(inputs),
                    "tests": str(task / "tests"),
                    "artifacts": str(tmp_path / "artifacts/logs/artifacts"),
                    "agent_logs": str(tmp_path / "agent"),
                    "verifier_logs": str(tmp_path / "verifier"),
                }
            }
        )
    )
    output = tmp_path / "result.json"
    script = task / "tests/test_outputs.py"
    monkeypatch.setattr(
        sys, "argv", [str(script), "--context", str(context), "--output", str(output)]
    )
    with pytest.raises(ValueError, match="prepared inputs.*GT"):
        runpy.run_path(str(script), run_name="__main__")
    assert not output.exists()


def test_prepared_files_example_scores_partial_credit_end_to_end(tmp_path):
    import logging

    from harbor.trial.artifact_handler import ArtifactHandler

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
                json.dumps({"total": sum(data["values"]), "as_of": "wrong date"}),
                encoding="utf-8",
            )
            task = Task(task_dir)
            await ArtifactHandler(
                artifacts=task.config.artifacts, logger=logging.getLogger(__name__)
            ).download_artifacts(
                host,
                host.trial_paths.artifacts_dir,
                source_artifacts_dir="/logs/artifacts",
            )
            (host.work_dir / "output.json").unlink()
            result = await HostVerifier(
                task=task, trial_paths=host.trial_paths, environment=host
            ).verify()
            assert result.rewards["reward"] == 0.75
            assert not (host.work_dir / "gt").exists()
        finally:
            await host.stop(True)

    asyncio.run(run())
