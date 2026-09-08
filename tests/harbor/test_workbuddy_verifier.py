from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import platform
import shutil
import sys
import tempfile
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


def make_office_environment(task, root, *, workdir_root=None):
    paths = TrialPaths(root / "trial")
    paths.mkdir()
    return HostEnvironment(
        environment_dir=task / "environment",
        environment_name="native-office",
        session_id="native-office",
        trial_paths=paths,
        task_env_config=EnvironmentConfig(workdir="/workspace"),
        logger=logging.getLogger("native-office"),
        host_access={"filesystem": True, "process": True},
        bootstrap_workbuddy_workspace=True,
        **({"workdir_root": workdir_root} if workdir_root is not None else {}),
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


def test_workbuddy_trial_uploads_skills_using_native_host_paths(native_task, tmp_path):
    from harbor.models.task.task import Task
    from harbor.models.trial.config import TrialConfig
    from harbor.trial.trial import Trial

    skill = tmp_path / "example-skill"
    skill.mkdir()
    content = (
        "---\nname: example-skill\ndescription: Fixture skill\n---\nUse the fixture.\n"
    )
    (skill / "SKILL.md").write_text(content, encoding="utf-8")
    before = _digests(native_task)
    independent_task = Task(native_task)
    original_environment = independent_task.config.environment.model_dump()

    async def scenario():
        trial = await Trial.create(
            TrialConfig.model_validate(
                {
                    "task": {"path": str(native_task)},
                    "trials_dir": str(tmp_path / "trials"),
                    "install_only": True,
                    "agent": {
                        "import_path": "psycheval.harbor.agent:ExternalHarnessAgent",
                        "kwargs": {"command": "unused"},
                        "skills": [str(skill)],
                    },
                    "environment": {
                        "import_path": "psycheval.harbor.environment:HostEnvironment",
                        "kwargs": {
                            "host_access": {"filesystem": True, "process": True},
                            "bootstrap_workbuddy_workspace": True,
                        },
                    },
                }
            )
        )
        host = trial.agent_environment
        assert host.task_env_config is trial.task.config.environment
        assert host.task_env_config is not independent_task.config.environment
        assert independent_task.config.environment.model_dump() == original_environment
        await host.start(force_build=False)
        try:
            await trial._upload_injected_skills()
            assert trial.task.config.environment.os == host.os
            uploaded = host.native_path("/harbor/skills/example-skill/SKILL.md")
            assert uploaded.read_text(encoding="utf-8") == content
            assert not uploaded.is_relative_to(host.work_dir)
        finally:
            await host.stop(delete=True)
        assert not uploaded.exists()

    async def bounded_scenario():
        async with asyncio.timeout(60):
            await scenario()

    asyncio.run(bounded_scenario())
    assert _digests(native_task) == before


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
        "agents:\n  - name: opencode\n    model_name: fixture/model\nenvironment:\n  import_path: psycheval.harbor.environment:HostEnvironment\n  kwargs:\n    host_access: {filesystem: true, process: true}\n"
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
        ("__PYTEST_COMMAND__", "REMOVED_COMMAND"),
        ("PY_SCORE", "REMOVED_SCORE"),
        ("PY_REWARD", "REMOVED_REWARD"),
    ],
)
def test_missing_pipeline_entry_points_are_profile_errors(native_task, old, new):
    root = native_task.parents[1]
    path = root / "shared/verifier/rule.py"
    path.write_text(path.read_text().replace(old, new))
    with pytest.raises(OfficeProfileError, match="execution template"):
        _load_rule(root)


def test_rule_source_changes_do_not_block_native_adaptation(native_task):
    root = native_task.parents[1]
    path = root / "shared/verifier/rule.py"
    original = _load_rule(root)
    source = path.read_text().replace("git diff --staged", "git diff --cached")
    source += "\nUNRELATED_METADATA = 'local revision'\n"
    path.write_text(source, encoding="utf-8")
    rule = _load_rule(root)
    assert "git diff --cached" in source
    assert rule.template == original.template
    assert rule.score_python == original.score_python
    assert rule.reward_python == original.reward_python
    assert rule.source_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    resolved = resolve_harbor_dataset(
        dataset_id="office", path=root, format="workbuddy.v1", allow_partial=True
    )
    validate_office_profile(resolved, [native_task.name])


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


@pytest.mark.parametrize("opener", ["open", "builtins.open", "io.open", "os.open"])
@pytest.mark.parametrize("keyword", [False, True])
def test_native_io_openers_read_the_mapped_workspace(tmp_path, opener, keyword):
    workspace = tmp_path / "native-workspace"
    workspace.mkdir()
    (workspace / "payload.txt").write_bytes(b"managed workspace")
    path_arg = "path" if opener == "os.open" else "file"
    argument = (
        f'{path_arg}="/workspace/payload.txt"'
        if keyword
        else '"/workspace/payload.txt"'
    )
    if opener == "os.open":
        invocation = f"os.fdopen(os.open({argument}, flags=os.O_RDONLY), 'rb')"
    else:
        invocation = f"{opener}({argument}, mode='rb')"
    source = (
        "import builtins, io, os\n"
        f"with {invocation} as stream:\n    content = stream.read()\n"
        'label = open.__name__ + "/workspace/logical"\n'
    )
    adapted, audit = _adapt_python(source, {"/workspace": workspace})
    assert sorted(item["kind"] for item in audit) == ["file_path", "skipped"]
    namespace = {}
    exec(adapted, namespace)
    assert namespace["content"] == b"managed workspace"
    assert namespace["label"] == "open/workspace/logical"


def test_open_non_path_arguments_keep_logical_values(tmp_path):
    source = 'open("data.txt", mode="/workspace/not-a-path")\n'
    adapted, audit = _adapt_python(source, {"/workspace": tmp_path})
    assert adapted == source
    assert audit[0]["kind"] == "skipped"


@pytest.mark.parametrize(
    "source",
    [
        'unknown("/workspace/x")\n',
        'Path(f"/workspace/{name}")\n',
        'os.environ.get("OUTPUT", f"/workspace/{name}")\n',
        'def load_mcp_process_config():\n    return [], {}, "fixture"\n',
        "def load_mcp_process_config():\n    return ()\n",
        "def load_mcp_process_config():\n    if flag:\n        return []\n    return []\n",
    ],
)
def test_unknown_source_expressions_are_retained_and_audited(native_task, source):
    adapted, audit = _adapt_python(source, {"/workspace": Path("native")})
    assert adapted == source
    assert audit and all(item["kind"] == "skipped" for item in audit)
    assert all(item["reason"] for item in audit)
    (native_task / "tests/grading/test_verify.py").write_text(source, encoding="utf-8")
    resolved = resolve_harbor_dataset(
        dataset_id="office",
        path=native_task.parents[1],
        format="workbuddy.v1",
        allow_partial=True,
    )
    validate_office_profile(resolved, [native_task.name])


@pytest.mark.parametrize(
    "source",
    [
        'Path("/workspace/../outside")',
        'Path("/workspace/D:/outside")',
        'Path("/workspace/file:stream")',
    ],
)
def test_invalid_mapped_paths_are_profile_errors(native_task, source):
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


@pytest.mark.parametrize(
    ("function", "root"),
    [
        ("_compute_snapshot", "root"),
        ("_compute_workspace_snapshot", "workspace_root"),
        ("_protected_root_rollup", "base"),
    ],
)
def test_snapshot_hash_traversal_retains_posix_order(tmp_path, function, root):
    source = f"""import hashlib
def {function}({root}):
    digest = hashlib.sha256()
    for path in sorted(p for p in {root}.rglob("*") if p.is_file()):
        digest.update(path.relative_to({root}).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
"""
    for name in ("README.md", "notes/a.txt", "notes.md"):
        path = tmp_path / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(name.encode())
    adapted, audit = _adapt_python(source, {})
    namespace = {}
    exec(adapted, namespace)
    # POSIX compares case-sensitive path components, not full path strings:
    # the notes directory comes before notes.md, and README comes first.
    expected = hashlib.sha256()
    for name in ("README.md", "notes/a.txt", "notes.md"):
        expected.update(name.encode() * 2)
    assert namespace[function](tmp_path) == expected.hexdigest()
    assert [item["kind"] for item in audit] == ["path_order"]
    unknown = source.replace('rglob("*")', 'glob("*")')
    adapted, audit = _adapt_python(unknown, {})
    assert adapted == unknown
    assert [item["kind"] for item in audit] == ["skipped"]


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
    (native_task / "tests/conftest.py").write_text(
        "import pytest\n@pytest.fixture\ndef owned_fixture():\n    return 42\n"
    )
    (native_task / "tests/grading/test_verify.py").write_text(
        "def test_pass(owned_fixture):\n    assert owned_fixture == 42\n"
        "def test_fail():\n    assert False\n"
    )
    (native_task / "conftest.py").write_text(
        "raise AssertionError('Task ancestor conftest loaded')\n"
    )

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
            environment.native_path("/workspace/conftest.py").write_text(
                "raise AssertionError('workspace conftest loaded')\n"
            )
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
                command,
                cwd=Path("/workspace"),
                env=executor.command.env,
                timeout_sec=30,
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


def test_native_pytest_collection_with_workspace_on_another_drive(
    native_task, tmp_path
):
    repository = Path(__file__).resolve().parents[2]
    if not tmp_path.drive or tmp_path.drive.lower() == repository.drive.lower():
        pytest.skip("requires checkout and temporary tests on different Windows drives")

    async def scenario(workdir_root):
        host = make_office_environment(
            native_task, tmp_path / "host", workdir_root=workdir_root
        )
        await host.start(force_build=False)
        try:
            executor = NativeOfficeExecutor(
                host,
                native_task,
                _load_rule(native_task.parents[1]),
                _load_command(native_task),
            )
            await executor.prepare({})
            command = executor.rule.template.replace(
                "__PYTEST_COMMAND__", executor.command.command
            )
            result = await executor.run(command, cwd=Path("/workspace"), timeout_sec=30)
            assert result.return_code == 0
            score = json.loads(
                (executor.logs / "score.json").read_text(encoding="utf-8")
            )
            assert score["test_status"] == "partial_pass"
            assert score["tests_total"] == 2
        finally:
            await host.stop(delete=True)

    local = repository / ".local"
    local.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pytest-office-", dir=local) as directory:
        asyncio.run(scenario(Path(directory)))


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
@pytest.mark.parametrize(
    "score", [None, b"{", b"\xff", b"{}", b"[]", b"null", b'{"overall": 0.5}']
)
def test_real_runtime_metric_projection_preserves_missing_and_invalid_scores(
    tmp_path, score
):
    from workbuddy_bench.scorer.metrics import compute_job_metrics

    from psycheval.harbor.workbuddy import compute_official_metrics

    trial = tmp_path / "job/one__attempt"
    (trial / "verifier").mkdir(parents=True)
    (trial / "result.json").write_text(
        json.dumps({"task_name": "one", "trial_name": trial.name}), encoding="utf-8"
    )
    if score is not None:
        (trial / "verifier/score.json").write_bytes(score)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    expected = compute_job_metrics(tmp_path, expected_tasks=["one", "missing"])
    actual = compute_official_metrics(tmp_path, ["one", "missing"])

    assert actual == expected
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


@pytest.mark.skipif(
    os.environ.get("PEVAL_WORKBUDDY_RUNTIME_TESTS") != "1",
    reason="opt-in pinned WorkBuddy runtime integration",
)
def test_real_runtime_metrics_preserve_long_names_and_duplicate_trial_names(tmp_path):
    from psycheval.harbor.workbuddy import compute_official_metrics

    name = "task-with-a-name-longer-than-thirty-two-characters"
    trial_name = name[:32] + "__same-id"
    for job, reward in (("one", 0.5), ("two", 1.0)):
        trial = tmp_path / job / trial_name
        (trial / "verifier").mkdir(parents=True)
        (trial / "config.json").write_text(
            json.dumps({"task": {"path": f"/dataset/tasks/{name}"}}), encoding="utf-8"
        )
        (trial / "verifier/score.json").write_text(
            json.dumps({"overall": reward, "reason": "中文 🎯"}, ensure_ascii=False),
            encoding="utf-8",
        )
    metrics = compute_official_metrics(tmp_path, [name, "missing"])
    assert metrics["n_tasks"] == 2
    assert metrics["n_trials"] == 3
    assert metrics["reward"] == 0.375
    assert metrics["missing_tasks"] == ["missing"]
    attempts = metrics["per_task"][name]["attempts"]
    assert len(attempts) == 2
    assert {attempt["trial"] for attempt in attempts} == {trial_name}
    assert metrics["run_dir"] == str(tmp_path)


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
    helper = native_task / "tests/grading/helper.py"
    helper_bytes = (
        b'\xef\xbb\xbfdef optional_contract():\r\n    return "/workspace/unmapped"\r\n'
    )
    helper.write_bytes(helper_bytes)
    helper.chmod(0o444)
    rule_path = native_task.parents[1] / "shared/verifier/rule.py"
    rule_path.write_text(
        rule_path.read_text().replace("git diff --staged", "git diff --cached")
    )
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
        copied_helper = build_context.contract.task_dir / "tests/grading/helper.py"
        assert copied_helper.read_bytes() == helper_bytes
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
            recorded = json.loads(audit.read_text())
            assert (
                recorded["rule_source_sha256"]
                == hashlib.sha256(rule_path.read_bytes()).hexdigest()
            )
            files = {item["path"]: item for item in recorded["files"]}
            assert (
                files["tests/grading/test_verify.py"]["edits"][0]["kind"] == "file_path"
            )
            skipped = files["tests/grading/helper.py"]
            assert skipped["source_sha256"] == skipped["adapted_sha256"]
            assert [item["kind"] for item in skipped["edits"]] == ["skipped"]
            score = json.loads(
                (environment.trial_paths.verifier_dir / "score.json").read_text(
                    encoding="utf-8"
                )
            )
            assert score["diagnostics"]["native_adaptation"]["skipped"] == 1
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
                path.read_text().replace("__PYTEST_COMMAND__", "REMOVED_COMMAND")
            )
        elif source == native_task / "tests":
            if changed_part == "command":
                path = destination / "verifier.toml"
                path.write_text(
                    path.read_text().replace("python -m pytest", "python -m unknown")
                )
            elif changed_part == "grader":
                (destination / "grading/test_verify.py").write_text(
                    'Path("/workspace/../outside")\n'
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
            with pytest.raises(OfficeProfileError, match="Office"):
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

    async def scenario():
        paths = TrialPaths(tmp_path / "trial space 中文")
        paths.mkdir()
        environment = HostEnvironment(
            environment_dir=source / "environment",
            environment_name="local-office",
            workdir_root=None,
            session_id="local-office",
            trial_paths=paths,
            task_env_config=EnvironmentConfig(workdir="/workspace"),
            logger=logging.getLogger("local-office"),
            host_access={"filesystem": True, "process": True},
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
            assert score["test_status"] not in {"build_error", "judge_error"}, score
            assert (paths.verifier_dir / "office-adaptation.json").is_file()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())
    assert _digests(source) == before
    assert _digests(root / "shared") == shared_before
    assert (root / "dataset.toml").read_bytes() == manifest_before
