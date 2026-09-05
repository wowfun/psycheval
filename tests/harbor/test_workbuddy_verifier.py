from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import platform
import shutil
import sys
from pathlib import Path

import pytest
from harbor.environments.base import ExecResult
from harbor.models.task.config import EnvironmentConfig
from harbor.models.trial.paths import TrialPaths

from psycheval.harbor.datasets import resolve_harbor_dataset
from psycheval.harbor.environment import HostEnvironment
from psycheval.harbor.workbuddy_verifier import (
    NativeOfficeExecutor,
    OfficeProfileError,
    _adapt_python,
    _load_command,
    _load_rule,
    validate_office_profile,
)
from tests.fixtures.native_office import write_native_office
from tests.harbor.test_environment import make_environment


def make_office_environment(task, root):
    paths = TrialPaths(root / "trial")
    paths.mkdir()
    return HostEnvironment(
        environment_dir=task / "environment",
        environment_name="native-office",
        session_id="native-office",
        trial_paths=paths,
        task_env_config=EnvironmentConfig(workdir="/workspace"),
        logger=logging.getLogger("native-office"),
        allow_host_execution=True,
        bootstrap_workbuddy_workspace=True,
        mounts=[
            {
                "type": "bind",
                "source": str(paths.verifier_dir),
                "target": "/logs/verifier",
            },
            {"type": "bind", "source": str(paths.agent_dir), "target": "/logs/agent"},
        ],
    )


def _digests(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.fixture
def native_task(tmp_path):
    return write_native_office(
        tmp_path / "bundle",
        "def test_pass():\n    assert True\n\ndef test_fail():\n    assert False\n",
    )


def test_profile_validation_is_non_executing_and_rejects_unrecognized_commands(
    native_task,
):
    root = native_task.parents[1]
    before = _digests(root)
    resolved = resolve_harbor_dataset(
        dataset_id="office", path=root, format="workbuddy.v1", allow_partial=True
    )
    validate_office_profile(resolved, [native_task.name])
    assert _digests(root) == before
    path = native_task / "tests/verifier.toml"
    path.write_text(path.read_text().replace("python -m pytest", "bash -c evil"))
    with pytest.raises(OfficeProfileError, match="unsupported Office pytest"):
        validate_office_profile(resolved, [native_task.name])


def test_windows_prepare_selects_the_native_verifier(
    native_task, tmp_path, monkeypatch
):
    import yaml

    from psycheval.harbor import workbuddy

    monkeypatch.setattr(workbuddy.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        workbuddy, "validate_workbuddy_runtime", lambda: {"version": "fixture"}
    )
    monkeypatch.setattr(workbuddy, "validate_workbuddy_host_dependencies", lambda: None)
    base = tmp_path / "base.yaml"
    base.write_text(
        "agents:\n  - name: opencode\n    model_name: fixture/model\nenvironment:\n  import_path: psycheval.harbor.environment:HostEnvironment\n  kwargs:\n    allow_host_execution: true\n"
    )
    plan = workbuddy.prepare_workbuddy_plan(
        output_root=tmp_path / "output",
        dataset_id="office",
        dataset_path=native_task.parents[1],
        base_config=base,
        allow_partial=True,
    )
    config = yaml.safe_load(Path(plan["jobs"][0]["config"]).read_text())
    assert (
        config["verifier"]["import_path"]
        == "psycheval.harbor.workbuddy_verifier:WindowsOfficeVerifier"
    )
    assert config["environment"]["kwargs"]["bootstrap_workbuddy_workspace"] is True
    assert plan["scope"] == "subset"


@pytest.mark.parametrize(
    "old,new",
    [
        ("git diff --staged", "git diff --cached"),
        ("__PYTEST_COMMAND__", "REMOVED_COMMAND"),
        ("PY_SCORE", "REMOVED_SCORE"),
        ("PY_REWARD", "REMOVED_REWARD"),
    ],
)
def test_changed_upstream_pipeline_is_not_silently_replaced(native_task, old, new):
    root = native_task.parents[1]
    path = root / "shared/verifier/rule.py"
    path.write_text(path.read_text().replace(old, new))
    with pytest.raises(OfficeProfileError, match="execution template"):
        _load_rule(root)


@pytest.mark.parametrize("kind", ["rule", "grader"])
@pytest.mark.parametrize("source", ["def broken(:\n", "return 1\n"])
def test_invalid_python_is_a_profile_error(native_task, kind, source):
    root = native_task.parents[1]
    path = (
        root / "shared/verifier/rule.py"
        if kind == "rule"
        else native_task / "tests/grading/test_verify.py"
    )
    path.write_text(source, encoding="utf-8")
    resolved = resolve_harbor_dataset(
        dataset_id="office", path=root, format="workbuddy.v1", allow_partial=True
    )
    with pytest.raises(OfficeProfileError, match="invalid Python"):
        validate_office_profile(resolved, [native_task.name])


def test_adaptation_preserves_logical_comparisons_and_score_conditions(tmp_path):
    source = """from pathlib import Path
import os
import sys
GOLD = Path("/tests/gold/gold_answer.json")
DEFAULT_OUTPUT_PATH = "/workspace/output"
sys.path.insert(0, "/workspace")
def evaluate(value):
    assert value != "/workspace/missing"
    return value.startswith("/workspace/") and 0.75 > 0.5
"""
    mappings = {"/tests": tmp_path / "tests", "/workspace": tmp_path / "workspace"}
    adapted, audit = _adapt_python(source, mappings)
    assert 'assert value != "/workspace/missing"' in adapted
    assert 'value.startswith("/workspace/") and 0.75 > 0.5' in adapted
    assert len(audit) == 3
    assert all(item["kind"] == "file_path" for item in audit)
    with pytest.raises(OfficeProfileError, match="unsupported Office path"):
        _adapt_python('unknown("/workspace/x")\n', mappings)


@pytest.mark.parametrize(
    "source",
    [
        'Path(f"/workspace/{name}")',
        'os.environ.get("OUTPUT", f"/workspace/{name}")',
        'Path("/workspace/../outside")',
        'Path("/workspace/D:/outside")',
        'Path("/workspace/file:stream")',
    ],
)
def test_unsupported_path_adaptations_are_profile_errors(native_task, source):
    (native_task / "tests/grading/test_verify.py").write_text(source, encoding="utf-8")
    resolved = resolve_harbor_dataset(
        dataset_id="office",
        path=native_task.parents[1],
        format="workbuddy.v1",
        allow_partial=True,
    )
    with pytest.raises(OfficeProfileError, match="Office.*line 1"):
        validate_office_profile(resolved, [native_task.name])


@pytest.mark.parametrize(
    "error", [ValueError("overlapping edits"), SyntaxError("invalid replacement")]
)
def test_rewrite_failures_are_reported_as_profile_errors(
    native_task, monkeypatch, error
):
    from psycheval.harbor import windows

    def failed_rewrite(*args, **kwargs):
        raise error

    monkeypatch.setattr(windows, "rewrite_python", failed_rewrite)
    resolved = resolve_harbor_dataset(
        dataset_id="office",
        path=native_task.parents[1],
        format="workbuddy.v1",
        allow_partial=True,
    )
    with pytest.raises(OfficeProfileError, match="Office Python adaptation") as raised:
        validate_office_profile(resolved, [native_task.name])
    assert raised.value.__cause__ is error


def test_adaptation_maps_the_probe_interpreter_only_at_launch(tmp_path):
    source = """def load_mcp_process_config():
    command = "python3"
    args = []
    env = {}
    config_path = "fixture"
    assert command == "python3"
    return [command, *args], env, str(config_path)
"""
    adapted, audit = _adapt_python(source, {})
    namespace = {}
    exec(adapted, namespace)
    assert namespace["load_mcp_process_config"]()[0] == [sys.executable]
    assert 'assert command == "python3"' in adapted
    assert audit[0]["kind"] == "python_launch"


def test_native_pipeline_produces_rule_score_and_all_required_artifacts(
    native_task, tmp_path
):
    async def scenario():
        environment = make_office_environment(native_task, tmp_path / "host space 中文")
        await environment.start(force_build=False)
        try:
            executor = NativeOfficeExecutor(
                environment,
                native_task,
                _load_rule(native_task.parents[1]),
                _load_command(native_task),
            )
            before = _digests(native_task.parents[1])
            environment.native_path("/workspace/input.txt").write_text("after\n")
            await executor.prepare(executor.command.env)
            patch = (executor.logs / "agent.patch").read_text()
            assert "-before" in patch and "+after" in patch
            staged = await environment.exec_argv(
                ["git", "diff", "--staged"], cwd="/workspace"
            )
            assert staged.return_code == 0 and not staged.stdout
            command = executor.rule.template.replace(
                "__PYTEST_COMMAND__", executor.command.command
            )
            with pytest.raises(OfficeProfileError, match="unsupported command"):
                await executor.run(command, cwd="/workspace", shell=False)
            result = await executor.run(
                command, cwd="/workspace", env=executor.command.env, timeout_sec=30
            )
            assert result.return_code == 0, result
            score = json.loads((executor.logs / "score.json").read_text())
            assert score["test_status"] == "partial_pass"
            assert score["tests_passed"] == 1 and score["tests_total"] == 2
            assert score["test_pass_rate"] == 0.5
            assert (executor.logs / "reward.txt").read_text() == "0.5"
            assert (executor.logs / "agent.patch").is_file()
            assert (executor.logs / "results.xml").is_file()
            assert _digests(native_task.parents[1]) == before
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.parametrize("enclosing_repository", [False, True])
def test_native_prepare_rejects_a_workspace_without_git(
    native_task, tmp_path, enclosing_repository
):
    import subprocess

    parent = tmp_path / "enclosing"
    parent.mkdir()
    workspace = parent / "workspace"
    workspace.mkdir()
    if enclosing_repository:
        subprocess.run(["git", "init", "--quiet", str(parent)], check=True)
        (parent / "staged.txt").write_text("preserve the enclosing repository index\n")
        subprocess.run(["git", "add", "staged.txt"], cwd=parent, check=True)
        index = parent / ".git/index"
        before = index.read_bytes()

    async def scenario():
        environment = make_environment(
            parent / "host",
            config=EnvironmentConfig(workdir="/workspace"),
            extra_mounts=[
                {"type": "bind", "source": str(workspace), "target": "/workspace"}
            ],
        )
        await environment.start(force_build=False)
        try:
            assert environment.native_path("/workspace") == workspace
            executor = NativeOfficeExecutor(
                environment,
                native_task,
                _load_rule(native_task.parents[1]),
                _load_command(native_task),
            )
            with pytest.raises(RuntimeError, match="git add.*exit 128"):
                await executor.prepare(executor.command.env)
            assert not (executor.logs / "agent.patch").exists()
            if enclosing_repository:
                assert index.read_bytes() == before
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.parametrize("failed_step", ["diff", "reset"])
def test_native_prepare_does_not_publish_a_patch_after_git_failure(
    native_task, tmp_path, failed_step
):
    async def scenario():
        environment = make_office_environment(native_task, tmp_path / "host")
        await environment.start(force_build=False)
        try:
            environment.native_path("/workspace/input.txt").write_text("after\n")
            executor = NativeOfficeExecutor(
                environment,
                native_task,
                _load_rule(native_task.parents[1]),
                _load_command(native_task),
            )
            (executor.logs / "agent.patch").write_text("stale patch")
            original_exec = environment.exec_argv

            async def fail_git(argv, **kwargs):
                if argv[0] == "git" and failed_step in argv:
                    return ExecResult(return_code=7, stderr="fixture Git failure")
                return await original_exec(argv, **kwargs)

            environment.exec_argv = fail_git
            with pytest.raises(
                RuntimeError, match=f"git {failed_step}.*exit 7.*fixture Git failure"
            ):
                await executor.prepare(executor.command.env)
            assert not (executor.logs / "agent.patch").exists()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.parametrize("separator", [":", ";"])
def test_native_environment_maps_path_entries_and_preserves_native_drives(
    native_task, tmp_path, monkeypatch, separator
):
    from types import SimpleNamespace

    from psycheval.harbor import workbuddy_verifier

    environment = SimpleNamespace(native_path=lambda path: tmp_path / path.lstrip("/"))
    executor = NativeOfficeExecutor(
        environment,
        native_task,
        _load_rule(native_task.parents[1]),
        _load_command(native_task),
    )
    monkeypatch.setattr(workbuddy_verifier.os, "pathsep", separator)
    native = "F:/native modules" if separator == ";" else "/opt/native modules"
    env = executor.env(
        {
            "PATH": separator.join(("/workspace/bin", native)),
            "PYTHONPATH": separator.join(("/tests/helpers", native)),
        }
    )
    assert env["PATH"] == separator.join((executor.path("/workspace/bin"), native))
    assert env["PYTHONPATH"] == separator.join(
        [
            *(executor.path(p) for p in executor.command.pythonpath),
            executor.path("/tests/helpers"),
            native,
        ]
    )


@pytest.mark.parametrize(
    "mode", ["no_junit", "scorer", "postprocess_failure", "timeout"]
)
def test_native_pipeline_failure_and_optional_scorer_paths(native_task, tmp_path, mode):
    async def scenario():
        environment = make_office_environment(native_task, tmp_path / "host")
        await environment.start(force_build=False)
        try:
            executor = NativeOfficeExecutor(
                environment,
                native_task,
                _load_rule(native_task.parents[1]),
                _load_command(native_task),
            )
            if mode == "no_junit":
                original_exec = environment.exec_argv

                async def exec_without_junit(argv, **kwargs):
                    if argv[1:3] == ["-m", "pytest"]:
                        return ExecResult(
                            return_code=2,
                            stdout="ERROR: found no collectors",
                            stderr="",
                        )
                    return await original_exec(argv, **kwargs)

                environment.exec_argv = exec_without_junit
            elif mode == "scorer":
                (
                    native_task / "tests/grading/scorer.py"
                ).write_text("""import argparse, json, os
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--results-xml')
p.add_argument('--log-dir')
p.add_argument('--pytest-exit')
a = p.parse_args()
assert a.pytest_exit == os.environ['PYTEST_EXIT'] == '1'
Path(a.log_dir, 'score.json').write_text(json.dumps({'overall': 0.25, 'tests_passed': 1, 'tests_total': 4}))
""")
            elif mode == "postprocess_failure":
                (native_task / "tests/judge.yaml").write_text("{}\n")
                (
                    native_task / "tests/grading/wb_judge_manifest_postprocess.py"
                ).write_text("raise SystemExit(7)\n")
            else:
                (native_task / "tests/grading/test_verify.py").write_text(
                    "import time\ndef test_slow():\n    time.sleep(60)\n"
                )
            await executor.prepare(executor.command.env)
            result = await executor.run(
                executor.rule.template.replace(
                    "__PYTEST_COMMAND__", executor.command.command
                ),
                cwd="/workspace",
                env=executor.command.env,
                timeout_sec=0.2 if mode == "timeout" else 30,
            )
            if mode == "timeout":
                assert result.timed_out
                assert not environment._active_processes
            elif mode == "postprocess_failure":
                assert result.return_code == 7
                assert not (executor.logs / "reward.json").exists()
            else:
                assert result.return_code == 0, result
                score = json.loads((executor.logs / "score.json").read_text())
                if mode == "no_junit":
                    assert score["test_status"] == "build_error"
                    assert score["tests_total"] == 1
                else:
                    assert score["overall"] == 0.25
                    assert (executor.logs / "reward.txt").read_text() == "0.25"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.skipif(
    platform.system() != "Linux", reason="differential reference execution uses Bash"
)
@pytest.mark.parametrize(
    "test_code",
    [
        "def test_pass():\n    assert True\n",
        "def test_fail():\n    assert False\n",
        "def test_pass():\n    assert True\ndef test_fail():\n    assert False\n",
        "# empty collection\n",
        "raise ImportError('fixture collection failure')\n",
        "import pytest\ndef test_skip():\n    pytest.skip('fixture skip')\n",
    ],
)
def test_native_pipeline_matches_the_source_bash_pipeline(
    native_task, tmp_path, test_code
):
    (native_task / "tests/grading/test_verify.py").write_text(test_code)

    async def scenario():
        outcomes = []
        for native in (False, True):
            environment = make_office_environment(native_task, tmp_path / str(native))
            await environment.start(force_build=False)
            try:
                await environment.upload_dir(native_task / "tests", "/tests")
                # Both paths execute the same independent grader input.
                copied_task = environment.native_path("/tests").parent
                executor = NativeOfficeExecutor(
                    environment,
                    copied_task,
                    _load_rule(native_task.parents[1]),
                    _load_command(native_task),
                )
                await executor.prepare(executor.command.env)
                command = executor.rule.template.replace(
                    "__PYTEST_COMMAND__", executor.command.command
                )
                if native:
                    result = await executor.run(
                        command,
                        cwd="/workspace",
                        env=executor.command.env,
                        timeout_sec=30,
                    )
                else:
                    result = await environment.exec(
                        command,
                        cwd="/workspace",
                        env=executor.command.env,
                        timeout_sec=30,
                    )
                assert result.return_code == 0, result
                score = json.loads((executor.logs / "score.json").read_text())
                outcomes.append(
                    {
                        key: value
                        for key, value in score.items()
                        if key != "wall_time_sec"
                    }
                )
            finally:
                await environment.stop(delete=True)
        assert outcomes[0] == outcomes[1]

    asyncio.run(scenario())


@pytest.mark.skipif(
    os.environ.get("PEVAL_WORKBUDDY_RUNTIME_TESTS") != "1",
    reason="opt-in pinned WorkBuddy runtime integration",
)
def test_real_runtime_metrics_count_missing_selected_tasks(tmp_path):
    from psycheval.harbor.workbuddy import compute_official_metrics

    verifier = tmp_path / "job/one__attempt/verifier"
    verifier.mkdir(parents=True)
    (verifier / "score.json").write_text(
        json.dumps(
            {
                "overall": 1,
                "tests_passed": 1,
                "tests_total": 1,
                "test_status": "full_pass",
            }
        )
    )
    metrics = compute_official_metrics(tmp_path, ["one", "two"])
    assert metrics["n_tasks"] == 2
    assert metrics["reward"] == 0.5
    assert metrics["missing_tasks"] == ["two"]


@pytest.mark.skipif(
    os.environ.get("PEVAL_WORKBUDDY_RUNTIME_TESTS") != "1",
    reason="opt-in pinned WorkBuddy runtime integration",
)
@pytest.mark.parametrize("with_llm", [False, True])
def test_native_verifier_reuses_real_runtime_and_never_mutates_dataset(
    native_task, tmp_path, monkeypatch, with_llm
):
    from dataclasses import replace

    from harbor.models.task.task import Task
    from workbuddy_bench.judge import registry as registry_module
    from workbuddy_bench.judge.core import (
        EvaluationItem,
        JudgeResult,
        JudgeSpec,
        JudgeVerdict,
    )

    from psycheval.harbor import workbuddy_verifier
    from psycheval.harbor.workbuddy_verifier import WindowsOfficeVerifier

    gold = native_task / "tests/gold/gold_answer.json"
    gold.parent.mkdir()
    gold.write_text('{"output_contract":{"path":"/workspace/output"},"threshold":0.75}')
    grader = native_task / "tests/grading/test_verify.py"
    grader.write_text(
        'from pathlib import Path\nassert Path("/tests/gold/gold_answer.json").is_file()\n'
        + grader.read_text()
    )
    grader.chmod(0o444)
    grader_source = grader.read_bytes().decode("utf-8-sig")
    adaptation_roots = []
    original_adapt = workbuddy_verifier._adapt_python

    def record_adaptation(source, mappings):
        if source == grader_source:
            adaptation_roots.append(mappings["/tests"])
        return original_adapt(source, mappings)

    monkeypatch.setattr(workbuddy_verifier, "_adapt_python", record_adaptation)
    original_load = registry_module.load_verifier_registry

    class LLMStub:
        def run(self, context, plan, evidence, judge):
            assert Path(context.host_paths["task_dir"]) != native_task
            assert Path(
                context.host_paths["tests_dir"], "gold/gold_answer.json"
            ).is_file()
            return JudgeResult(
                judge_name="llm",
                judge_type="fixture_llm",
                verdicts=[
                    JudgeVerdict(
                        item_id="llm",
                        status="pass",
                        judge_name="llm",
                        judge_type="fixture_llm",
                    )
                ],
            )

    def load_registry(build_context):
        registry = original_load(build_context)

        def build(context):
            plan = registry.plan_builder(context)
            if with_llm:
                plan = replace(
                    plan,
                    items=[*plan.items, EvaluationItem(id="llm", type="llm")],
                    judges=[
                        *plan.judges,
                        JudgeSpec(name="llm", type="fixture_llm", item_ids=["llm"]),
                    ],
                )
            return plan

        def finalize(score, context, plan):
            return replace(score, numeric={**score.numeric, "fixture_finalized": 1})

        return replace(
            registry,
            plan_builder=build,
            finalize_score=finalize,
            judge_runners={**registry.judge_runners, "fixture_llm": LLMStub()},
        )

    monkeypatch.setattr(registry_module, "load_verifier_registry", load_registry)

    async def scenario():
        environment = make_office_environment(native_task, tmp_path / "host space 中文")
        await environment.start(force_build=False)
        before = _digests(native_task.parents[1])
        try:
            # Verifier execution must succeed even if the shell entry is unavailable.
            async def forbidden_shell(*args, **kwargs):
                pytest.fail("native verifier invoked a shell")

            environment.exec = forbidden_shell
            verifier = WindowsOfficeVerifier(
                task=Task(native_task),
                trial_paths=environment.trial_paths,
                environment=environment,
            )
            result = await verifier.verify()
            assert len(adaptation_roots) == 1
            assert adaptation_roots[0].is_relative_to(environment.native_path("/tests"))
            assert result.rewards["reward"] == (0.75 if with_llm else 0.5)
            assert result.rewards["fixture_finalized"] == 1
            audit = environment.trial_paths.verifier_dir / "office-adaptation.json"
            assert audit.is_file()
            assert (
                json.loads(audit.read_text())["files"][0]["path"]
                == "tests/grading/test_verify.py"
            )
            assert _digests(native_task.parents[1]) == before
            assert list(environment.native_path("/tests").iterdir()) == []
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.skipif(
    os.environ.get("PEVAL_WORKBUDDY_RUNTIME_TESTS") != "1",
    reason="opt-in pinned WorkBuddy runtime integration",
)
@pytest.mark.parametrize("changed_part", ["rule", "command", "grader"])
def test_real_runtime_copy_is_revalidated_before_plugin_loading(
    native_task, tmp_path, monkeypatch, changed_part
):
    from harbor.models.task.task import Task
    from workbuddy_bench.judge import registry

    from psycheval.harbor.workbuddy_verifier import WindowsOfficeVerifier

    root = native_task.parents[1]
    resolved = resolve_harbor_dataset(
        dataset_id="office", path=root, format="workbuddy.v1", allow_partial=True
    )
    validate_office_profile(resolved, [native_task.name])
    before = _digests(root)
    original_copytree = shutil.copytree

    def changed_copy(source, destination, *args, **kwargs):
        result = original_copytree(source, destination, *args, **kwargs)
        source, destination = Path(source), Path(destination)
        if changed_part == "rule" and source == root / "shared":
            path = destination / "verifier/rule.py"
            path.write_text(
                path.read_text().replace("git diff --staged", "git diff --cached")
            )
        elif source == native_task / "tests":
            if changed_part == "command":
                path = destination / "verifier.toml"
                path.write_text(
                    path.read_text().replace("python -m pytest", "python -m unknown")
                )
            elif changed_part == "grader":
                (destination / "grading/test_verify.py").write_text(
                    'unknown("/workspace/output")\n'
                )
        return result

    def forbidden_plugin(*args, **kwargs):
        pytest.fail("invalid runtime copy reached plugin loading")

    monkeypatch.setattr(shutil, "copytree", changed_copy)
    monkeypatch.setattr(registry, "load_verifier_registry", forbidden_plugin)

    async def scenario():
        environment = make_office_environment(native_task, tmp_path / "host")
        await environment.start(force_build=False)
        try:
            verifier = WindowsOfficeVerifier(
                task=Task(native_task),
                environment=environment,
                trial_paths=environment.trial_paths,
            )
            with pytest.raises(OfficeProfileError, match="unsupported Office"):
                await verifier.verify()
            assert not (environment.trial_paths.verifier_dir / "score.json").exists()
            assert not list(environment.native_path("/tests").iterdir())
            assert _digests(root) == before
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.skipif(
    not os.environ.get("PEVAL_WORKBUDDY_OFFICE_DATASET"),
    reason="opt-in local Office Dataset execution",
)
@pytest.mark.parametrize(
    "task_name",
    sorted(
        path.name
        for path in (
            Path(os.environ["PEVAL_WORKBUDDY_OFFICE_DATASET"]) / "tasks"
        ).iterdir()
        if path.is_dir()
    )
    if os.environ.get("PEVAL_WORKBUDDY_OFFICE_DATASET")
    else ["local-office"],
)
def test_local_office_dataset_executes_without_shell_and_stays_read_only(
    tmp_path, monkeypatch, task_name
):
    import logging

    from harbor.models.task.task import Task
    from harbor.models.trial.paths import TrialPaths

    from psycheval.harbor.environment import HostEnvironment
    from psycheval.harbor.workbuddy import LLM_REQUIRED_ENV
    from psycheval.harbor.workbuddy_verifier import WindowsOfficeVerifier

    root = Path(os.environ["PEVAL_WORKBUDDY_OFFICE_DATASET"])
    source = root / "tasks" / task_name
    before = _digests(source)
    shared_before = _digests(root / "shared")
    manifest_before = (root / "dataset.toml").read_bytes()
    for key in LLM_REQUIRED_ENV:
        monkeypatch.delenv(key, raising=False)
    config = tmp_path / "peval.toml"
    config.write_text('[harbor.host]\nworkdir_root=""\n')
    monkeypatch.setenv("PEVAL_CONFIG", str(config))

    async def scenario():
        paths = TrialPaths(tmp_path / "trial space 中文")
        paths.mkdir()
        environment = HostEnvironment(
            environment_dir=source / "environment",
            environment_name="local-office",
            session_id="local-office",
            trial_paths=paths,
            task_env_config=EnvironmentConfig(workdir="/workspace"),
            logger=logging.getLogger("local-office"),
            allow_host_execution=True,
            bootstrap_workbuddy_workspace=True,
            mounts=[
                {
                    "type": "bind",
                    "source": str(paths.verifier_dir),
                    "target": "/logs/verifier",
                },
                {
                    "type": "bind",
                    "source": str(paths.agent_dir),
                    "target": "/logs/agent",
                },
            ],
        )
        await environment.start(force_build=False)
        try:

            async def forbidden_shell(*args, **kwargs):
                pytest.fail("native verifier invoked a shell")

            environment.exec = forbidden_shell
            result = await WindowsOfficeVerifier(
                task=Task(source), trial_paths=paths, environment=environment
            ).verify()
            score = json.loads((paths.verifier_dir / "score.json").read_text())
            assert result.rewards is not None
            assert score["test_status"] not in {"build_error", "judge_error"}, (
                paths.verifier_dir / "test_output.txt"
            ).read_text()
            assert (paths.verifier_dir / "office-adaptation.json").is_file()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())
    assert _digests(source) == before
    assert _digests(root / "shared") == shared_before
    assert (root / "dataset.toml").read_bytes() == manifest_before
