"""Execute copied Harbor code in a process that cannot import Psycheval."""

from __future__ import annotations

import asyncio
import importlib
import importlib.abc
import io
import json
import logging
import os
import pkgutil
import runpy
import shlex
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

PACKAGE = "downstream._vendor.harbor_copy"


class BlockPsycheval(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname.split(".")[0] == "psycheval":
            raise AssertionError(f"copied code imported original package: {fullname}")
        return None


def module(name: str):
    return importlib.import_module(f"{PACKAGE}.{name}")


def run_module(name: str, *args: str) -> None:
    with patch.object(sys, "argv", [f"{PACKAGE}.{name}", *args]):
        try:
            runpy.run_module(f"{PACKAGE}.{name}", run_name="__main__", alter_sys=True)
        except SystemExit as exc:
            assert exc.code == 0, exc.code


def imports(root: Path) -> None:
    class BlockOptionalRuntime(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            if fullname.split(".")[0] == "workbuddy_bench":
                raise ModuleNotFoundError("optional WorkBuddy runtime is unavailable")
            return None

    sys.meta_path.insert(0, BlockOptionalRuntime())
    package = importlib.import_module(PACKAGE)
    found = list(pkgutil.walk_packages(package.__path__, f"{PACKAGE}."))
    for info in found:
        importlib.import_module(info.name)
    assert any(info.name == f"{PACKAGE}.tasks" for info in found)
    assert (
        module("agent").ExternalHarnessAgent(logs_dir=root, command="fixture").version()
        == package.__version__
    )
    runtime = module("runtime_config")
    assert runtime.HARNESS_PROTOCOL_VERSION == 2
    assert runtime.PEVAL_CONFIG_ENV == "PEVAL_CONFIG"


def native_office(root: Path) -> None:
    from harbor.models.task.config import EnvironmentConfig
    from harbor.models.task.task import Task
    from harbor.models.trial.paths import TrialPaths

    async def scenario():
        task = root / "bundle/tasks/office-00"
        config = root / "peval.toml"
        config.write_text('[harbor.host]\nworkdir_root=""\n')
        os.environ["PEVAL_CONFIG"] = str(config)
        paths = TrialPaths(root / "native trial 中文")
        paths.mkdir()
        environment = module("environment").HostEnvironment(
            environment_dir=task / "environment",
            environment_name="copied-office",
            session_id="copied-office",
            trial_paths=paths,
            task_env_config=EnvironmentConfig(workdir="/workspace"),
            logger=logging.getLogger("copied-office"),
            allow_host_execution=True,
            bootstrap_workbuddy_workspace=True,
            mounts=[
                {
                    "type": "bind",
                    "source": str(paths.agent_dir),
                    "target": "/logs/agent",
                },
                {
                    "type": "bind",
                    "source": str(paths.verifier_dir),
                    "target": "/logs/verifier",
                },
            ],
        )
        await environment.start(force_build=False)
        try:

            async def forbidden_shell(*args, **kwargs):
                raise AssertionError("native verifier invoked a shell")

            environment.exec = forbidden_shell
            verifier = module("workbuddy_verifier").WindowsOfficeVerifier(
                task=Task(task),
                trial_paths=paths,
                environment=environment,
            )
            result = await verifier.verify()
            assert result.rewards["reward"] == 1.0, result
            assert (paths.verifier_dir / "office-adaptation.json").is_file()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def write_runtime(root: Path, *, action: str = "run") -> Path:
    runtime = module("runtime_config")
    path = runtime.write_effective_runtime_config(
        root / "runtime.json",
        runtime.EffectiveRuntimeConfig(
            paths=runtime.RuntimePaths(
                workdir=str(root),
                tests=str(root / "tests"),
                agent_logs=str(root / "agent"),
                verifier_logs=str(root / "verifier"),
                artifacts=str(root / "artifacts"),
            ),
            harness=runtime.HarnessInvocation(action=action),
        ),
    )
    os.environ["PEVAL_CONFIG"] = str(path)
    return path


def trajectory(message: str) -> dict:
    return {
        "schema_version": "ATIF-v1.7",
        "session_id": "copied-session",
        "agent": {"name": "downstream", "version": "1"},
        "steps": [{"step_id": 1, "source": "agent", "message": message}],
        "final_metrics": {"total_prompt_tokens": 12, "total_completion_tokens": 3},
    }


def verifier(root: Path) -> None:
    write_runtime(root)
    (root / "agent").mkdir()
    (root / "agent/trajectory.json").write_text(
        json.dumps(trajectory("done")), encoding="utf-8"
    )
    grader = root / "grader.json"
    for term, reward in (("done", 1), ("missing", 0)):
        grader.write_text(json.dumps({"final_terms": [term]}), encoding="utf-8")
        run_module("verifier", str(grader))
        assert (
            json.loads((root / "verifier/reward.json").read_text())["reward"] == reward
        )
        checks = json.loads((root / "verifier/checks.json").read_text())["checks"]
        assert all(check["passed"] for check in checks) == bool(reward)


def psychevo(root: Path) -> None:
    help_output = io.StringIO()
    with redirect_stdout(help_output):
        run_module("psychevo_harness", "--help")
    assert "--pevo" in help_output.getvalue()
    pevo = root / "fake-pevo"
    pevo.write_text("test-owned executable", encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        if "run" not in command:
            return subprocess.CompletedProcess(command, 0, "pevo 1\n", "")
        assert "PEVAL_CONFIG" not in kwargs["env"]
        commands.append(command)
        Path(kwargs["env"]["PSYCHEVO_DB"]).write_text(
            "retained state", encoding="utf-8"
        )
        events = [
            {"type": "thread.started", "threadId": "exact-session"},
            {
                "type": "item.completed",
                "item": {
                    "id": f"assistant-{len(commands)}",
                    "role": "assistant",
                    "source": "runtime.message",
                    "blocks": [{"kind": "text", "status": "completed", "body": "done"}],
                },
            },
            {
                "type": "turn.completed",
                "threadId": "exact-session",
                "turnId": f"turn-{len(commands)}",
                "outcome": "completed",
                "toolFailures": 0,
                "finalAnswer": "done",
            },
        ]
        return subprocess.CompletedProcess(
            command, 0, "\n".join(map(json.dumps, events)), ""
        )

    for action, instruction in (("run", "start"), ("resume", "continue")):
        write_runtime(root, action=action)
        with (
            patch.object(sys, "stdin", io.StringIO(instruction)),
            patch("subprocess.run", fake_run),
        ):
            run_module("psychevo_harness", "--pevo", str(pevo))
    assert "--session" not in commands[0]
    assert commands[1][commands[1].index("--session") + 1] == "exact-session"
    result = json.loads((root / "agent/trajectory.json").read_text())
    assert result["session_id"] == "exact-session"
    assert result["steps"][0]["message"] == "continue"
    assert "start" not in json.dumps(result)


def workbuddy(root: Path) -> None:
    import yaml

    work = module("workbuddy")
    datasets = module("datasets")
    bundle = root / "bundle"
    resolved = datasets.validate_harbor_dataset(
        dataset_id="office", path=bundle, format="workbuddy.v1"
    )
    assert len(resolved.task_names) == 50 and resolved.read_only
    for name in tuple(os.environ):
        if name.startswith("WORKBUDDY_VERIFIER_LLM_"):
            del os.environ[name]
    output = root / "output"
    output.mkdir()
    config = output / "peval.toml"
    config.write_bytes(b"unreadable workspace config\xff")
    os.environ["PEVAL_CONFIG"] = str(config)
    base = root / "base.yaml"
    base.write_text(
        yaml.safe_dump(
            {
                "agents": [{"name": "opencode", "model_name": "fixture/model"}],
                "environment": {
                    "import_path": f"{PACKAGE}.environment:HostEnvironment",
                    "kwargs": {"allow_host_execution": True},
                },
            }
        ),
        encoding="utf-8",
    )
    captured = io.StringIO()
    with (
        patch.object(
            work,
            "validate_workbuddy_runtime",
            return_value={"version": "fixture", "commit": "local"},
        ),
        patch.object(work, "validate_workbuddy_host_dependencies"),
        patch.object(
            work,
            "compute_official_metrics",
            return_value={"reward": 1, "pass_rate": 1, "n_tasks": 50, "n_trials": 50},
        ) as compute,
        redirect_stdout(captured),
    ):
        plan = work.prepare_workbuddy_plan(
            output_root=output,
            dataset_id="office",
            dataset_path=bundle,
            base_config=base,
        )
        assert plan["host_environment"] is True
        assert len(plan["jobs"]) == 2
        for job in plan["jobs"]:
            generated = yaml.safe_load(Path(job["config"]).read_text())
            assert (
                generated["environment"]["import_path"]
                == f"{PACKAGE}.environment:HostEnvironment"
            )
            assert (
                generated["environment"]["kwargs"]["bootstrap_workbuddy_workspace"]
                is True
            )
        try:
            work.summarize_workbuddy_plan(output_root=output, plan_id=plan["plan_id"])
        except work.WorkBuddyPlanError as exc:
            assert "not terminal" in str(exc)
        else:
            raise AssertionError("nonterminal jobs accepted")
        partial = work.summarize_workbuddy_plan(
            output_root=output, plan_id=plan["plan_id"], provisional=True
        )
        assert partial["provisional"] and len(partial["pending_jobs"]) == 2
        for job in plan["jobs"]:
            job_dir = Path(plan["jobs_root"]) / job["name"]
            job_dir.mkdir()
            (job_dir / "result.json").write_text(
                json.dumps({"finished_at": "2026-09-05T00:00:00Z"}), encoding="utf-8"
            )
        summary = work.summarize_workbuddy_plan(
            output_root=output, plan_id=plan["plan_id"]
        )
        assert not summary["provisional"] and summary["metrics"]["reward"] == 1
        compute.assert_called_with(Path(plan["jobs_root"]), list(resolved.task_names))
        assert (
            work.discover_workbuddy_summaries(output, {"office"})[0]["plan_id"]
            == plan["plan_id"]
        )
        assert work.discover_workbuddy_summaries(output, {"unrelated"}) == []
    assert captured.getvalue() == ""
    assert config.read_bytes() == b"unreadable workspace config\xff"
    assert {path.name for path in output.iterdir()} == {
        "peval.toml",
        "harbor-plans",
        "harbor-jobs",
    }


def synthetic_harness(root: Path) -> None:
    runtime = module("runtime_config").load_effective_runtime_config(
        require_harness=True
    )
    logs = Path(runtime.paths.agent_logs)
    state = logs / "state.json"
    previous = (
        json.loads(state.read_text()) if runtime.harness.action == "resume" else 0
    )
    state.write_text(json.dumps(previous + 1), encoding="utf-8")
    (logs / "trajectory.json").write_text(
        json.dumps(trajectory(sys.stdin.read())), encoding="utf-8"
    )


def host(root: Path) -> None:
    from harbor.models.agent.context import AgentContext
    from harbor.models.task.config import EnvironmentConfig
    from harbor.models.trial.paths import TrialPaths

    async def scenario() -> None:
        config = root / "peval.toml"
        config.write_text('[harbor.host]\nworkdir_root=""\n', encoding="utf-8")
        os.environ["PEVAL_CONFIG"] = str(config)
        environment_dir = root / "environment"
        environment_dir.mkdir()
        (environment_dir / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
        paths = TrialPaths(root / "trial with spaces")
        paths.mkdir()
        artifacts = paths.artifacts_dir / "logs/artifacts"
        artifacts.mkdir(parents=True)
        environment = module("environment").HostEnvironment(
            environment_dir=environment_dir,
            environment_name="vendored",
            session_id="vendored",
            trial_paths=paths,
            task_env_config=EnvironmentConfig(workdir="/app"),
            logger=logging.getLogger("vendored"),
            allow_host_execution=True,
            mounts=[
                {"type": "bind", "source": str(source), "target": target}
                for source, target in (
                    (paths.agent_dir, "/logs/agent"),
                    (paths.verifier_dir, "/logs/verifier"),
                    (artifacts, "/logs/artifacts"),
                )
            ],
        )
        agent = module("agent").ExternalHarnessAgent(
            logs_dir=paths.agent_dir,
            command=shlex.join(
                [
                    sys.executable,
                    "-I",
                    str(Path(__file__).resolve()),
                    str(root),
                    "synthetic_harness",
                ]
            ),
        )
        await environment.start(force_build=False)
        try:
            for action, instruction in (("run", "start"), ("resume", "continue")):
                context = AgentContext()
                await getattr(agent, action)(instruction, environment, context)
                assert context.n_input_tokens == 12 and context.n_output_tokens == 3
                assert context.metadata["harness_action"] == action
                result = json.loads((paths.agent_dir / "trajectory.json").read_text())
                assert result["steps"][0]["message"] == instruction
            assert json.loads((paths.agent_dir / "state.json").read_text()) == 2
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    root = Path(sys.argv[1])
    sys.path.insert(0, str(root))
    sys.meta_path.insert(0, BlockPsycheval())
    scenarios = {
        "imports": imports,
        "verifier": verifier,
        "psychevo": psychevo,
        "workbuddy": workbuddy,
        "host": host,
        "synthetic_harness": synthetic_harness,
        "native_office": native_office,
    }
    scenarios[sys.argv[2]](root)
    assert not any(name.split(".")[0] == "psycheval" for name in sys.modules)
