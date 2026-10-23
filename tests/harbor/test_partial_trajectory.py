import asyncio
import gzip
import json
import signal
import sys
from pathlib import Path

import pytest
from harbor.models.agent.context import AgentContext

from psycheval.harbor.acp_agent import HostACPAgent
from psycheval.harbor.acp_evidence import recover
from psycheval.harbor.diagnostics import write_partial
from tests.harbor.test_acp import _current_evidence


@pytest.mark.parametrize(
    "damage", ["none", "gzip-tail", "line-tail", "bad-record", "foreign-session"]
)
def test_diagnostic_acp_recovers_only_valid_current_prefix(tmp_path, damage):
    def event(message):
        return (
            json.dumps({"direction": "receive", "phase": "prompt", "message": message})
            + "\n"
        )

    prompt = {
        "method": "session/prompt",
        "params": {
            "sessionId": "current",
            "prompt": [{"type": "text", "text": "task"}],
        },
    }
    first = (
        json.dumps({"direction": "send", "phase": "prompt", "message": prompt}) + "\n"
    )
    update = {
        "method": "session/update",
        "params": {
            "sessionId": "current",
            "update": {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "kept"},
            },
        },
    }
    raw = first + event(update)
    if damage == "line-tail":
        raw += '{"unfinished":'
    if damage == "bad-record":
        raw += "broken\n" + event(update)
    if damage == "foreign-session":
        update["params"]["sessionId"] = "unrelated"
        raw += event(update)
    compressed = gzip.compress(raw.encode())
    (tmp_path / "acp.events.ndjson.gz").write_bytes(
        compressed[:-8] if damage == "gzip-tail" else compressed
    )
    trajectory = recover(
        tmp_path, {}, "task", {"name": "fixture", "version": "1"}, "acp"
    )
    assert [step.message for step in trajectory.steps] == ["task", "kept"]
    write_partial(tmp_path, trajectory, "acp.events.ndjson.gz")
    assert not (tmp_path / "trajectory.json").exists()
    assert json.loads(
        (tmp_path / "trajectory.partial.json").read_text(encoding="utf-8")
    )["extra"]["diagnostic_only"]


def test_windows_cleanup_warning_does_not_block_formal_trajectory(tmp_path):
    summary = _current_evidence(
        tmp_path,
        [
            {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "answer"},
            }
        ],
    )
    warning = {
        "stage": "process",
        "error_type": "TimeoutError",
        "paths": [str(tmp_path)],
    }
    summary.update(
        host_os="windows", cleanup_complete=False, cleanup_warnings=[warning]
    )
    (tmp_path / "acp.summary.json").write_text(json.dumps(summary))
    agent = HostACPAgent(logs_dir=tmp_path, argv=["fixture"])
    agent._invocation_id = summary["invocation_id"]
    context = AgentContext()
    agent.populate_context_post_run(context)
    assert (tmp_path / "trajectory.json").is_file()
    assert context.metadata["cleanup_warnings"] == [warning]


@pytest.mark.parametrize("failure", ["changed", "seal"])
def test_windows_cleanup_does_not_admit_changed_evidence(tmp_path, failure):
    summary = _current_evidence(
        tmp_path,
        [
            {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "answer"},
            }
        ],
    )
    summary.update(host_os="windows", cleanup_complete=False)
    if failure == "seal":
        summary["evidence_error_type"] = "OSError"
    (tmp_path / "acp.summary.json").write_text(json.dumps(summary))
    if failure == "changed":
        (tmp_path / "acp.events.ndjson.gz").write_bytes(gzip.compress(b"{}\n"))
    agent = HostACPAgent(logs_dir=tmp_path, argv=["fixture"])
    agent._invocation_id = summary["invocation_id"]
    with pytest.raises((ValueError, RuntimeError)):
        agent.populate_context_post_run(AgentContext())
    assert not (tmp_path / "trajectory.json").exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows cleanup policy")
def test_cleanup_failure_still_runs_rules_and_judge(tmp_path, monkeypatch):
    from harbor.environments.base import ExecResult

    from psycheval.harbor import acp_harness
    from psycheval.harbor.verifier import JudgeSettings, run_verifier
    from tests.fixtures.judge_server import judge_server
    from tests.fixtures.judge_task import api_task
    from tests.harbor.environment_support import make_environment
    from tests.harbor.test_acp import PEER

    settle = acp_harness._settle_process

    async def fail_after_settle(*args):
        await settle(*args)
        raise TimeoutError("fixture exit notification")

    monkeypatch.setattr(acp_harness, "_settle_process", fail_after_settle)

    async def scenario(server):
        host = make_environment(tmp_path / "host")
        await host.start(False)
        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir,
            argv=[sys.executable, str(PEER)],
            shutdown_timeout_sec=8,
        )
        await agent.setup(host)

        async def execute(argv, **kwargs):
            handlers = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
            try:
                code = await acp_harness.run(Path(argv[-1]))
            finally:
                for sig, handler in handlers.items():
                    signal.signal(sig, handler)
            return ExecResult(return_code=code, stdout="", stderr="")

        monkeypatch.setattr(host, "exec_argv", execute)
        try:
            context = AgentContext()
            await agent.run("fixture", host, context)
            agent.populate_context_post_run(context)
            assert context.metadata["cleanup_warnings"][0]["paths"]
            summary = json.loads(
                (agent.logs_dir / "acp.summary.json").read_text(encoding="utf-8")
            )
            assert summary["protocol_complete"] and not summary["cleanup_complete"]
            assert "error_type" not in summary
            assert summary["cleanup_diagnostics"]["stage_elapsed_sec"]["process"] >= 0
            assert summary["cleanup_diagnostics"]["active_processes"] == 0
            grader, runtime = api_task(tmp_path / "grading")
            Path(runtime.paths.agent_logs, "trajectory.json").write_bytes(
                (agent.logs_dir / "trajectory.json").read_bytes()
            )
            # Both deterministic transcript evidence and the local model must execute.
            grader.write_text(
                '{"final_terms":["完成"],"custom_checks":["valid"]}', encoding="utf8"
            )
            score = await run_verifier(
                grader,
                runtime=runtime,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
            assert score["reward"] == 1
            assert len(server["requests"]) == 1
            verifier_logs = Path(runtime.paths.verifier_logs)
            assert (
                json.loads((verifier_logs / "reward.json").read_text(encoding="utf-8"))[
                    "reward"
                ]
                == 1
            )
            assert (
                json.loads((verifier_logs / "score.json").read_text(encoding="utf-8"))[
                    "reward"
                ]
                == 1
            )
            assert list((verifier_logs / "judge").glob("rubric-*.json"))
        finally:
            await host.stop(True)

    with judge_server() as server:
        asyncio.run(scenario(server))


@pytest.mark.skipif(sys.platform != "win32", reason="Windows cleanup policy")
def test_windows_directory_cleanup_warns_and_retains_paths(tmp_path, monkeypatch):
    from tests.harbor.environment_support import make_environment

    async def scenario():
        host = make_environment(tmp_path)
        await host.start(False)
        work_dir = host.work_dir
        original = host._remove_owned_runtime

        def locked():
            raise PermissionError("fixture locked directory")

        monkeypatch.setattr(host, "_remove_owned_runtime", locked)
        await host.stop(True)
        warning = json.loads(
            (host.trial_paths.agent_dir / "cleanup.json").read_text(encoding="utf-8")
        )[0]
        assert str(work_dir) in warning["paths"]
        assert work_dir.exists()
        monkeypatch.setattr(host, "_remove_owned_runtime", original)
        await host.stop(True)

    asyncio.run(scenario())


def test_opencode_incomplete_export_preserves_running_tool(tmp_path):
    from psycheval.harbor.opencode import HostOpenCodeAgent
    from tests.harbor.test_opencode import _exported_session

    exported = _exported_session()
    exported["info"]["outcome"] = "interrupted"
    message = exported["messages"][0]
    message["time"].pop("completed")
    message["content"].append(
        {
            "type": "tool",
            "id": "pending",
            "name": "bash",
            "state": {"status": "running", "input": {"command": "work"}, "content": []},
        }
    )
    (tmp_path / "opencode-failed-session.json").write_text(json.dumps(exported))
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent._instruction = "task"
    events = agent._session_events(
        [{"sessionID": "session-fixture"}],
        filename="opencode-failed-session.json",
        diagnostic=True,
    )
    assert all(e["type"] != "step_finish" for e in events)
    data = agent._diagnostic_trajectory(events).to_json_dict()
    assert data["steps"][-1]["extra"]["incomplete"]
    assert (
        data["steps"][-1]["observation"]["results"][0]["extra"]["status"] == "running"
    )
    assert not data.get("final_metrics")


def test_repeated_cancel_keeps_original_cancellation_and_prefix(tmp_path, monkeypatch):
    from psycheval.harbor.opencode import HostOpenCodeAgent

    async def scenario():
        agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
        started, exporting, finish = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def run(*args):
            agent._instruction = "current"
            agent._diagnostic_env = {}
            (tmp_path / "opencode.txt").write_text(
                "\n".join(
                    json.dumps(e)
                    for e in [
                        {"type": "step_start", "sessionID": "current", "timestamp": 1},
                        {
                            "type": "text",
                            "sessionID": "current",
                            "part": {"text": "kept"},
                        },
                    ]
                )
            )
            started.set()
            await asyncio.Event().wait()

        async def export(*args):
            exporting.set()
            await finish.wait()
            raise TimeoutError("export unavailable")

        monkeypatch.setattr(agent, "_run", run)
        monkeypatch.setattr(agent, "_host", lambda env: env)
        monkeypatch.setattr(agent, "_export_session", export)
        task = asyncio.create_task(agent.run("current", object(), AgentContext()))
        await started.wait()
        task.cancel()
        await exporting.wait()
        task.cancel()
        await asyncio.sleep(0)
        finish.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        data = json.loads(
            (tmp_path / "trajectory.partial.json").read_text(encoding="utf-8")
        )
        assert data["session_id"] == "current"
        assert data["steps"][-1]["message"] == "kept"
        assert not (tmp_path / "trajectory.json").exists()

    asyncio.run(scenario())


def test_opencode_bad_record_stops_before_later_content(tmp_path):
    from psycheval.harbor.opencode import HostOpenCodeAgent

    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent._instruction = "task"
    trajectory = agent._diagnostic_trajectory(
        [
            {"type": "step_start", "sessionID": "current"},
            {"type": "text", "sessionID": "current", "part": {"text": "kept"}},
            {"type": "text", "sessionID": "current", "part": None},
            {"type": "text", "sessionID": "current", "part": {"text": "not kept"}},
        ]
    )
    assert trajectory.steps[-1].message == "kept"


def test_new_opencode_invocation_cannot_reuse_old_trajectory(tmp_path, monkeypatch):
    from psycheval.harbor.opencode import HostOpenCodeAgent
    from tests.harbor.test_opencode import _exported_session

    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent._instruction = "old"
    (tmp_path / "opencode-session.json").write_text(json.dumps(_exported_session()))
    for name in ("trajectory.json", "trajectory.partial.json"):
        (tmp_path / name).write_text('{"session_id":"old"}')

    async def fail(*args):
        raise RuntimeError("early startup failure")

    monkeypatch.setattr(agent, "_run", fail)
    with pytest.raises(RuntimeError, match="early startup failure"):
        asyncio.run(agent.run("new", object(), AgentContext()))
    agent.populate_context_post_run(AgentContext())
    assert not list(tmp_path.glob("trajectory*.json"))


def test_windows_post_run_evidence_failure_preserves_execution_error(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from harbor.models.task.config import TaskOS

    agent = HostACPAgent(logs_dir=tmp_path, argv=["fixture"])
    agent._setup_host = SimpleNamespace(os=TaskOS.WINDOWS)
    primary = TimeoutError("original execution timeout")

    async def fail(*args):
        raise primary

    monkeypatch.setattr(agent, "_run_invocation", fail)
    with pytest.raises(TimeoutError) as caught:
        asyncio.run(agent.run("task", object(), AgentContext()))
    context = AgentContext()
    agent.populate_context_post_run(context)
    assert caught.value is primary
    assert context.metadata["trajectory_error"] == "RuntimeError"
    assert not (tmp_path / "trajectory.json").exists()


@pytest.mark.skipif(
    sys.platform != "win32", reason="native Windows pipe and Job mechanics"
)
def test_native_windows_cleanup_drains_flooded_pipes_within_deadline():
    from psycheval.harbor.acp_harness import _discard, _settle
    from psycheval.harbor.windows import WindowsProcessAdapter

    async def scenario():
        adapter = WindowsProcessAdapter()
        process = await adapter.spawn(
            [
                sys.executable,
                "-c",
                "import os,time; os.write(1,b'ready\\n'); os.write(1,b'x'*1048576); os.write(2,b'y'*1048576); time.sleep(60)",
            ],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert await process.stdout.readline() == b"ready\n"
        summary = {"protocol_complete": False}
        stderr = asyncio.create_task(_discard(process.stderr))
        try:
            await asyncio.wait_for(
                _settle(
                    process,
                    None,
                    None,
                    asyncio.Event(),
                    2,
                    summary,
                    adapter,
                    stderr_task=stderr,
                ),
                3,
            )
            assert summary["cleanup_complete"]
            diagnostics = summary["cleanup_diagnostics"]
            assert diagnostics["active_processes"] == 0
            assert diagnostics["stdout_eof"] and diagnostics["stderr_eof"]
        finally:
            if process in adapter._jobs:
                await adapter.settle(process, 2)
            await asyncio.gather(stderr, return_exceptions=True)

    asyncio.run(scenario())


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows file locks")
def test_native_windows_locked_file_retains_directory_and_warns(tmp_path):
    from tests.harbor.environment_support import make_environment

    async def scenario():
        host = make_environment(tmp_path)
        await host.start(False)
        workspace = host.work_dir
        held = workspace / "held.txt"
        held.write_text("locked")
        try:
            with held.open("rb"):
                await host.stop(True)
                assert held.exists()
                warning = json.loads(
                    (host.trial_paths.agent_dir / "cleanup.json").read_text(
                        encoding="utf-8"
                    )
                )[0]
                assert warning["error_type"] == "PermissionError"
                assert str(workspace) in warning["paths"]
        finally:
            await host.stop(True)
        assert not workspace.exists()

    asyncio.run(scenario())
