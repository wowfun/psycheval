from __future__ import annotations

import asyncio
import copy
import json
import os
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from harbor.agents.installed.base import NonZeroAgentExitCodeError
from harbor.models.agent.context import AgentContext
from harbor.models.task.config import MCPServerConfig

from psycheval.harbor.opencode import HostOpenCodeAgent
from psycheval.harbor.trajectory_validation import load_validated_trajectory
from psycheval.harbor.verifier import evaluate
from tests.harbor.test_environment import make_environment


@pytest.mark.parametrize(
    "status,exit_code,passed",
    [
        ("completed", 0, True),
        ("completed", 1, False),
        ("completed", None, True),
        ("error", None, False),
        ("running", None, False),
    ],
)
def test_native_tool_status_and_exit_code_control_observation_gate(
    tmp_path, status, exit_code, passed
):
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent._instruction = "Fetch source"
    events = [
        {"type": "step_start", "sessionID": "fixture"},
        {
            "type": "tool_use",
            "part": {
                "type": "tool",
                "callID": "source",
                "tool": "bash",
                "state": {
                    "status": status,
                    "input": {"command": "python x-daily/fetch.py"},
                    "output": "source fetch result",
                    "metadata": {"exit": exit_code},
                },
            },
        },
        {"type": "step_finish", "part": {}},
        {"type": "step_start", "sessionID": "fixture"},
        {"type": "text", "part": {"type": "text", "text": "done"}},
        {"type": "step_finish", "part": {}},
    ]
    trajectory = agent._convert_events_to_trajectory(events)
    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                {"any": [{"tool_names": ["bash"], "argument_terms": ["x-daily"]}]}
            ]
        },
        tmp_path,
    )
    assert (
        next(check for check in checks if check["id"] == "required_call_1_observation")[
            "passed"
        ]
        is passed
    )
    observation = trajectory.steps[1].observation.results[0]
    assert observation.extra["is_error"] is not passed
    if exit_code is not None:
        assert observation.extra["exit_code"] == exit_code


@pytest.mark.parametrize("field", ["part", "state", "metadata", "status"])
@pytest.mark.parametrize("value", [None, [], "unexpected"])
def test_malformed_tool_data_is_reported_without_mutating_events(
    tmp_path, field, value
):
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent._instruction = "Fetch source"
    part = {
        "type": "tool",
        "callID": "source",
        "tool": "bash",
        "state": {"status": "completed", "input": {}, "output": "source"},
    }
    if field == "part":
        part = value
    elif field == "state":
        part["state"] = value
    else:
        part["state"][field] = value
    events = [
        {"type": "step_start", "sessionID": "fixture"},
        {"type": "tool_use", "part": part},
        {"type": "text", "part": {"type": "text", "text": "retained answer"}},
        {"type": "step_finish", "part": {}},
    ]
    original = copy.deepcopy(events)
    if field in {"part", "state"}:
        with pytest.raises(ValueError, match="Malformed OpenCode tool event"):
            agent._convert_events_to_trajectory(events)
        assert events == original
        return
    trajectory = agent._convert_events_to_trajectory(events)
    assert trajectory.steps[-1].message == "retained answer"
    assert events == original
    if field == "status":
        assert trajectory.steps[-1].observation.results[0].extra["is_error"]


@pytest.mark.parametrize("failure", ["state", "boundary", "unfinished"])
def test_malformed_forbidden_tool_event_cannot_disappear_from_scoring(
    tmp_path, failure
):
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent._instruction = "Do not run forbidden_tool"
    events = [
        {"type": "step_start", "sessionID": "fixture"},
        {
            "type": "tool_use",
            "part": {
                "type": "tool",
                "callID": "forbidden-call",
                "tool": "forbidden_tool",
                "state": None,
            },
        },
        {"type": "text", "part": {"type": "text", "text": "done"}},
        {"type": "step_finish", "part": {}},
    ]
    if failure != "state":
        events[1]["part"]["state"] = {
            "status": "completed",
            "input": {},
            "output": "done",
        }
        if failure == "boundary":
            events[-1]["part"] = None
        else:
            events.pop()
    with pytest.raises(ValueError, match="OpenCode"):
        agent._convert_events_to_trajectory(events)


@pytest.mark.skipif(
    os.environ.get("PEVAL_OPENCODE_CLI_TESTS") != "1",
    reason="opt-in preinstalled OpenCode CLI integration",
)
def test_real_cli_reads_unicode_stdin_and_uses_registered_model(tmp_path):
    executable = shutil.which("opencode")
    assert executable, "Install OpenCode before enabling the CLI integration test"
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, self.headers.get("Authorization"), payload))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for delta, finish in (
                ({"role": "assistant", "content": "完成 🎉"}, None),
                ({}, "stop"),
            ):
                event = {
                    "id": "fixture-completion",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": payload["model"],
                    "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
                }
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def scenario():
        host = make_environment(tmp_path / "host")
        agent = HostOpenCodeAgent(
            logs_dir=tmp_path / "agent logs",
            executable=executable,
            model_name="fixture/unlisted-model",
            extra_env={
                "TEST_API_KEY": "fixture-key",
                "OPENCODE_DISABLE_MODELS_FETCH": "true",
            },
            opencode_config={
                "provider": {
                    "fixture": {
                        "npm": "@ai-sdk/openai-compatible",
                        "models": {
                            "unlisted-model": {"name": "Fixture " + "x" * 40000}
                        },
                        "options": {
                            "baseURL": f"http://127.0.0.1:{server.server_port}/v1",
                            "apiKey": "{env:TEST_API_KEY}",
                        },
                    }
                }
            },
        )
        await host.start(False)
        try:
            await agent.setup(host)
            instruction = '任务 "quoted" & $HOME\n' + "中文" * 18000
            async with asyncio.timeout(60):
                await agent.run(instruction, host, AgentContext())
            agent.populate_context_post_run(AgentContext())
            load_validated_trajectory(agent.logs_dir / "trajectory.json")
            contents = []
            for _, _, payload in requests:
                for message in payload["messages"]:
                    content = message.get("content", "")
                    contents.extend(
                        [content]
                        if isinstance(content, str)
                        else [part.get("text", "") for part in content]
                    )
            assert any(instruction in text for text in contents), [
                (len(text), text[:60]) for text in contents
            ]
            assert requests
            assert all(
                path == "/v1/chat/completions"
                and key == "Bearer fixture-key"
                and payload["model"] == "unlisted-model"
                for path, key, payload in requests
            )
            assert any(
                event.get("type") == "step_finish" for event in agent._parse_stdout()
            )
        finally:
            await host.stop(True)

    try:
        asyncio.run(scenario())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("provider", ["openai", "anthropic", "fixture"])
@pytest.mark.parametrize("override", [False, True])
def test_opencode_registers_model_and_explicit_connection(tmp_path, provider, override):
    config = (
        {"provider": {provider: {"options": {"baseURL": "http://caller.invalid/v1"}}}}
        if override
        else {}
    )
    before = copy.deepcopy(config)
    agent = HostOpenCodeAgent(
        logs_dir=tmp_path / "logs",
        model_name=f"{provider}/unlisted-model",
        extra_env={f"{provider.upper()}_BASE_URL": "http://connection.invalid/v1"},
        opencode_config=config,
    )

    async def runtime_env():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        try:
            return agent._runtime_env(host)
        finally:
            await host.stop(True)

    env = asyncio.run(runtime_env())
    generated = json.loads(env["OPENCODE_CONFIG_CONTENT"])["provider"][provider]
    assert generated["models"] == {"unlisted-model": {}}
    if override or provider in {"openai", "anthropic"}:
        assert generated["options"]["baseURL"] == (
            "http://caller.invalid/v1" if override else "http://connection.invalid/v1"
        )
    else:
        assert "options" not in generated
    assert config == before


@pytest.mark.parametrize(
    "config",
    [
        [],
        {"skills": None},
        {"skills": []},
        {"skills": {"paths": "path"}},
        {"skills": {"paths": [1]}},
        {"mcp": []},
        {"provider": None},
    ],
)
def test_opencode_rejects_invalid_extended_configuration(tmp_path, config):
    with pytest.raises(ValueError, match="opencode_config"):
        HostOpenCodeAgent(
            logs_dir=tmp_path / "logs",
            model_name="fixture/model",
            opencode_config=config,
        )


@pytest.mark.parametrize("transport", ["stdio", "sse"])
@pytest.mark.parametrize("override_endpoint", [False, True])
def test_task_mcp_defaults_preserve_caller_configuration(
    tmp_path, transport, override_endpoint
):
    if transport == "stdio":
        server = MCPServerConfig(
            name="fixture", transport="stdio", command="python", args=["task-server.py"]
        )
        defaults = {"type": "local", "command": ["python", "task-server.py"]}
        caller = {"environment": {"TOKEN": "{env:TEST_API_KEY}"}}
        if override_endpoint:
            caller["command"] = ["python", "caller-server.py"]
    else:
        server = MCPServerConfig(
            name="fixture", transport="sse", url="https://task.invalid/mcp"
        )
        defaults = {"type": "remote", "url": "https://task.invalid/mcp"}
        caller = {"headers": {"Authorization": "Bearer fixture-token"}}
        if override_endpoint:
            caller["url"] = "https://caller.invalid/mcp"
    caller.update(enabled=False, timeout=4321)
    caller_only = {
        "type": "remote",
        "url": "https://extra.invalid/mcp",
        "enabled": False,
    }
    config = {"mcp": {"fixture": caller, "caller-only": caller_only}}
    before = copy.deepcopy(config)
    server_before = server.model_dump()
    agent = HostOpenCodeAgent(
        logs_dir=tmp_path / "logs",
        model_name="fixture/model",
        mcp_servers=[server],
        opencode_config=config,
    )

    async def runtime_env():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        try:
            return agent._runtime_env(host)
        finally:
            await host.stop(True)

    env = asyncio.run(runtime_env())
    generated = json.loads(env["OPENCODE_CONFIG_CONTENT"])["mcp"]
    assert generated == {"fixture": {**defaults, **caller}, "caller-only": caller_only}
    assert config == before
    assert server.model_dump() == server_before


@pytest.mark.parametrize("outcome", ["success", "error", "exit", "empty", "cancel"])
def test_native_opencode_run_retains_evidence_and_isolates_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    script = tmp_path / "fake opencode.py"
    script.write_text(
        "import json,os,sys,time\n"
        "from pathlib import Path\n"
        "prompt=sys.stdin.buffer.read().decode('utf-8')\n"
        "config=json.loads(os.environ['OPENCODE_CONFIG_CONTENT'])\n"
        "Path('observed.json').write_text(json.dumps({'prompt':prompt,"
        "'config':config,'cwd':os.getcwd(),'argv':sys.argv[1:],"
        "'home':os.environ['HOME'],'data':os.environ['XDG_DATA_HOME'],"
        "'key':os.environ['TEST_API_KEY']}),encoding='utf-8')\n"
        "print(json.dumps({'type':'step_start','sessionID':'session-fixture'}),flush=True)\n"
        "print(json.dumps({'type':'text','part':{'type':'text','text':'完成 🎉'}},"
        "ensure_ascii=False),flush=True)\n"
        f"outcome={outcome!r}\n"
        "if outcome=='cancel': time.sleep(60)\n"
        "if outcome=='error': print(json.dumps({'type':'error','error':{'name':'APIError'}}))\n"
        "if outcome=='exit': sys.exit(2)\n"
        "if outcome!='empty': print(json.dumps({'type':'step_finish','part':"
        "{'cost':0.25,'tokens':{'input':12,'output':7,'cache':{'read':3}}}}))\n",
        encoding="utf-8",
    )

    async def scenario() -> None:
        host = make_environment(tmp_path / "host")
        logs = tmp_path / "agent logs"
        agent = HostOpenCodeAgent(
            logs_dir=logs,
            executable=sys.executable,
            model_name="fixture/model",
            variant="high",
            skills_dir="/harbor/skills",
            mcp_servers=[
                MCPServerConfig(name="fixture", transport="stdio", command="python")
            ],
            extra_env={"TEST_API_KEY": "fixture-key", "PYTHONIOENCODING": "utf-8"},
            opencode_config={"permission": {"webfetch": "deny"}},
        )
        await host.start(force_build=False)
        try:
            await host.ensure_dirs(["/harbor/skills"], chmod=False)
            await agent.setup(host)
            execute = host.exec_argv

            async def fake_cli(argv, **kwargs):
                assert not Path(argv[3]).is_relative_to(agent.logs_dir)
                assert not Path(argv[3]).is_relative_to(host.work_dir)
                return await execute([*argv[:5], str(script), *argv[5:]], **kwargs)

            monkeypatch.setattr(host, "exec_argv", fake_cli)
            instruction = '任务 "quoted" & $HOME\n' + "中文" * 18000
            if outcome == "cancel":
                run = asyncio.create_task(agent.run(instruction, host, AgentContext()))
                async with asyncio.timeout(20):
                    while (
                        not (logs / "opencode.txt").exists()
                        or not (logs / "opencode.txt").stat().st_size
                    ):
                        await asyncio.sleep(0.02)
                run.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await run
            elif outcome in {"error", "exit"}:
                with pytest.raises(NonZeroAgentExitCodeError):
                    await agent.run(instruction, host, AgentContext())
            elif outcome == "empty":
                with pytest.raises(RuntimeError, match="no completed step"):
                    await agent.run(instruction, host, AgentContext())
            else:
                await agent.run(instruction, host, AgentContext())
                context = AgentContext()
                agent.populate_context_post_run(context)
                assert context.n_output_tokens == 7
                assert context.cost_usd == 0.25
                trajectory = load_validated_trajectory(logs / "trajectory.json")
                raw_trajectory = (logs / "trajectory.json").read_bytes()
                assert not raw_trajectory.startswith(b"\xef\xbb\xbf")
                assert "完成 🎉".encode("utf-8") in raw_trajectory
                assert trajectory["steps"][-1]["message"] == "完成 🎉"
            observed = json.loads(
                (host.work_dir / "observed.json").read_text(encoding="utf-8")
            )
            assert observed["prompt"] == instruction
            assert Path(observed["cwd"]) == host.work_dir
            assert not Path(observed["home"]).is_relative_to(logs)
            assert Path(observed["home"]).is_relative_to(
                host.runtime_directory(f"opencode-{agent._runtime_id}")
            )
            assert not Path(observed["data"]).is_relative_to(logs)
            assert observed["config"]["permission"] == {"webfetch": "deny"}
            assert observed["config"]["skills"]["paths"] == [
                str(host.native_path("/harbor/skills"))
            ]
            assert observed["config"]["mcp"]["fixture"]["command"] == ["python"]
            assert observed["argv"][-2:] == ["--variant", "high"]
            assert observed["key"] == "fixture-key"
            assert "step_start" in (logs / "opencode.txt").read_text(encoding="utf-8")
        finally:
            await host.stop(delete=True)

    asyncio.run(scenario())


@pytest.mark.parametrize("phase", ["setup", "run"])
@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
def test_generated_opencode_environment_wins_inside_harbor_scope(
    tmp_path, monkeypatch, phase, outcome
):
    path_keys = (
        "HOME",
        "USERPROFILE",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_CACHE_HOME",
        "OPENCODE_CONFIG_DIR",
        "OPENCODE_CONFIG",
    )
    extra = {key: str(tmp_path / "caller" / key) for key in path_keys}
    extra.update(
        OPENCODE_CONFIG_CONTENT='{"permission":"deny"}', TEST_API_KEY="fixture-key"
    )
    keys = (*path_keys, "OPENCODE_CONFIG_CONTENT", "TEST_API_KEY")
    observe = f"json.dumps({{key:os.environ.get(key) for key in {keys!r}}})"
    script = tmp_path / "scoped-opencode.py"
    output = "fixture-version" if phase == "setup" else '{"type":"step_finish"}'
    script.write_text(
        "import json,os,sys,time\nfrom pathlib import Path\n"
        f"Path('observed-env.json').write_text({observe},encoding='utf-8')\n"
        f"print({output!r},flush=True)\n"
        f"if {outcome!r}=='cancel': time.sleep(30)\n"
        f"sys.exit(2 if {outcome!r}=='error' else 0)\n",
        encoding="utf-8",
    )

    async def scenario():
        host = make_environment(tmp_path / "host")
        logs = tmp_path / "agent logs"
        agent = HostOpenCodeAgent(
            logs_dir=logs,
            executable=sys.executable,
            model_name="fixture/model",
            extra_env=extra,
            opencode_config={"permission": {"webfetch": "deny"}},
        )
        before = copy.deepcopy(agent.extra_env)
        await host.start(False)
        execute = host.exec_argv

        async def fake_cli(argv, **kwargs):
            actual = (
                [argv[0], str(script)]
                if phase == "setup"
                else [*argv[:5], str(script), *argv[5:]]
            )
            return await execute(actual, **kwargs)

        async def invoke():
            if phase == "setup":
                await agent.setup(host)
            else:
                await agent.run("fixture instruction", host, AgentContext())

        monkeypatch.setattr(host, "exec_argv", fake_cli)
        try:
            with host.scoped_exec_env(agent.extra_env):
                if outcome == "cancel":
                    task = asyncio.create_task(invoke())
                    log = logs / (
                        "opencode-setup.log" if phase == "setup" else "opencode.txt"
                    )
                    try:
                        async with asyncio.timeout(10):
                            while not log.exists() or not log.stat().st_size:
                                await asyncio.sleep(0.02)
                    finally:
                        task.cancel()
                        with pytest.raises(asyncio.CancelledError):
                            await task
                elif outcome == "error":
                    expected = (
                        RuntimeError if phase == "setup" else NonZeroAgentExitCodeError
                    )
                    with pytest.raises(expected):
                        await invoke()
                else:
                    await invoke()
                observed = json.loads(
                    (host.work_dir / "observed-env.json").read_text(encoding="utf-8")
                )
                for key in path_keys:
                    assert not Path(observed[key]).is_relative_to(logs), key
                config = json.loads(observed["OPENCODE_CONFIG_CONTENT"])
                assert config["provider"]["fixture"]["models"] == {"model": {}}
                assert config["permission"] == {"webfetch": "deny"}
                assert observed["TEST_API_KEY"] == "fixture-key"
                outer = await execute(
                    [sys.executable, "-c", f"import os,json; print({observe})"]
                )
                assert json.loads(outer.stdout) == extra
            assert agent.extra_env == before
        finally:
            await host.stop(True)

    asyncio.run(asyncio.wait_for(scenario(), 20))


def test_opencode_version_mismatch_and_missing_executable(tmp_path: Path) -> None:
    async def scenario() -> None:
        host = make_environment(tmp_path / "host")
        await host.start(force_build=False)
        try:
            for executable, version, error in (
                (sys.executable, "wrong-version", RuntimeError),
                ("missing-opencode-fixture", None, FileNotFoundError),
            ):
                agent = HostOpenCodeAgent(
                    logs_dir=tmp_path / "logs",
                    executable=executable,
                    version=version,
                    model_name="fixture/model",
                )
                with pytest.raises(error):
                    await agent.setup(host)
        finally:
            await host.stop(delete=True)

    asyncio.run(scenario())


def test_agents_with_shared_env_keep_trial_runtime_paths_isolated(tmp_path):
    shared_env = {"TEST_API_KEY": "fixture-key", "HOME": "caller-home"}

    async def scenario():
        host = make_environment(tmp_path / "host")
        agents = [
            HostOpenCodeAgent(
                logs_dir=tmp_path / f"agent-{i}",
                executable=sys.executable,
                model_name="fixture/model",
                extra_env=shared_env,
            )
            for i in range(2)
        ]
        await host.start(force_build=False)
        try:
            # Serial setup catches a previous Trial polluting the next one.
            for agent in agents:
                await agent.setup(host)
                assert agent.extra_env == shared_env
            runtime = [agent._runtime_env(host) for agent in agents]
            for agent, env in zip(agents, runtime, strict=True):
                assert not Path(env["HOME"]).is_relative_to(agent.logs_dir)
                assert env["TEST_API_KEY"] == "fixture-key"
                assert agent.extra_env == shared_env
            assert runtime[0]["HOME"] != runtime[1]["HOME"]
            assert shared_env == {"TEST_API_KEY": "fixture-key", "HOME": "caller-home"}
        finally:
            await host.stop(delete=True)

    asyncio.run(scenario())


def test_opencode_probe_timeout_retains_diagnostic_and_isolated_env(
    tmp_path, monkeypatch
):
    async def scenario():
        host = make_environment(tmp_path / "host")
        logs = tmp_path / "logs"
        agent = HostOpenCodeAgent(
            logs_dir=logs, executable=sys.executable, model_name="fixture/model"
        )
        await host.start(force_build=False)
        try:

            async def timeout(argv, *, env, timeout_sec):
                assert argv[-1] == "--version"
                assert timeout_sec == 30
                assert not Path(env["HOME"]).is_relative_to(logs)
                callback = host._output_callback()
                await callback("startup diagnostic\n", "stderr")
                raise TimeoutError

            monkeypatch.setattr(host, "exec_argv", timeout)
            with pytest.raises(RuntimeError, match="version probe.*30-second"):
                await agent.setup(host)
            assert (logs / "opencode-setup.log").read_text() == "startup diagnostic\n"
        finally:
            await host.stop(delete=True)

    asyncio.run(scenario())
