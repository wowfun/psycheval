from __future__ import annotations

import asyncio
import gzip
import io
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from harbor.models.agent.context import AgentContext
from harbor.models.trajectories import Trajectory

from psycheval.harbor.acp_agent import HostACPAgent
from psycheval.harbor.acp_evidence import convert, outcome
from psycheval.harbor.acp_protocol import ProtocolError, StrictTransport
from psycheval.harbor.workbuddy_agent import HostWorkBuddyAgent, inspect_workbuddy
from tests.harbor.environment_support import make_environment
from tests.harbor.test_acp import _current_evidence

PEER = Path(__file__).resolve().parents[1] / "fixtures/acp_peer.py"
windows = pytest.mark.skipif(
    sys.platform != "win32", reason="native WorkBuddy Windows adapter"
)


@windows
@pytest.mark.parametrize("action", ["run", "resume"])
@pytest.mark.parametrize("state", ["unconfigured", "other_host", "deleted_runtime"])
def test_invocation_checks_host_setup_before_native_usage_paths(
    tmp_path, action, state
):
    host = make_environment(tmp_path / "host")
    agent = HostWorkBuddyAgent(
        logs_dir=host.trial_paths.agent_dir, model_name="b", **installation(tmp_path)
    )
    if state == "other_host":
        agent._setup_host = make_environment(tmp_path / "other")
    elif state == "deleted_runtime":
        agent._setup_host = host
    message = (
        "deleted or replaced"
        if state == "deleted_runtime"
        else "original configured Host"
    )
    with pytest.raises(RuntimeError, match=message):
        asyncio.run(getattr(agent, action)("task", host, AgentContext()))


@pytest.mark.parametrize("grouped", [False, True])
def test_inspection_returns_native_models_without_prompting(
    tmp_path, monkeypatch, grouped
):
    from psycheval.harbor import workbuddy_agent

    choices = [
        {"value": "custom/中文", "name": "自定义", "description": "Fixture"},
        {"value": "builtin", "name": "Built-in"},
    ]
    options = [
        {
            "id": "model",
            "currentValue": "custom/中文",
            "options": [{"group": "vendor", "options": choices}]
            if grouped
            else choices,
        }
    ]
    calls = []

    class Host:
        def __init__(self, **kwargs):
            self.root = kwargs["environment_dir"].parent

        async def start(self, delete):
            calls.append("start")

        async def stop(self, delete):
            calls.append(("stop", delete))

    async def setup(agent, host):
        assert agent._inspection and agent.config_options == {}
        calls.append("setup")

    async def invoke(agent, action, instruction, host):
        assert (action, instruction) == ("inspect", "")
        calls.append(host.root)
        return {"config_options": options}

    monkeypatch.setattr(workbuddy_agent, "HostEnvironment", Host)
    monkeypatch.setattr(HostWorkBuddyAgent, "setup", setup)
    monkeypatch.setattr(HostWorkBuddyAgent, "_invoke", invoke)
    result = asyncio.run(inspect_workbuddy(**installation(tmp_path)))
    assert result.desktop_version == "5.7.7" and result.cli_version == "2.156.0"
    assert result.current_model_id == "custom/中文"
    assert result.available_models == (
        {"modelId": "custom/中文", "name": "自定义", "description": "Fixture"},
        {"modelId": "builtin", "name": "Built-in"},
    )
    assert result.config_options == tuple(options)
    assert calls[:2] == ["start", "setup"] and calls[-1] == ("stop", True)
    assert not calls[2].exists()


@pytest.mark.parametrize("failure", ["setup", "invoke"])
def test_inspection_settles_host_on_failure(tmp_path, monkeypatch, failure):
    from psycheval.harbor import workbuddy_agent

    roots, stopped = [], []

    class Host:
        def __init__(self, **kwargs):
            roots.append(kwargs["environment_dir"].parent)

        async def start(self, delete):
            pass

        async def stop(self, delete):
            stopped.append(delete)

    async def setup(*args):
        if failure == "setup":
            raise RuntimeError("fixture failure")

    async def invoke(*args):
        raise RuntimeError("fixture failure")

    monkeypatch.setattr(workbuddy_agent, "HostEnvironment", Host)
    monkeypatch.setattr(HostWorkBuddyAgent, "setup", setup)
    monkeypatch.setattr(HostWorkBuddyAgent, "_invoke", invoke)
    with pytest.raises(RuntimeError, match="fixture failure"):
        asyncio.run(inspect_workbuddy(**installation(tmp_path)))
    assert stopped == [True] and not roots[0].exists()


def test_bootstrap_watchdog_uses_configured_timeout(tmp_path):
    script = r"""
      const assert = require('node:assert/strict');
      const fs = require('node:fs'), vm = require('node:vm');
      const source = fs.readFileSync(process.argv[1], 'utf8');
      for (const timeout of [250, 60000, 120000]) {
        const timers = [];
        const context = {
          require(name) {
            if (name === 'node:net') return {
              createServer: () => ({listen() {}, unref() {}}),
              createConnection: () => ({on() {}, once() {}}),
            };
            if (name === 'node:crypto') return require(name);
                if (name === 'node:path') return require(name);
                if (name === 'node:child_process') return {
                  spawn(python, args, options) {
                    assert.equal(python, 'fixture-python');
                    assert.equal(options.windowsHide, true);
                    assert.equal(Object.keys(options.env).some(key => key.startsWith('CODEBUDDY_SIDECAR_')), false);
                    return {on() {}, stdout:{on() {}}, stderr:{on() {}}, stdin:{on() {}, end(data, callback) { callback(); }}};
                  },
                };
            assert.equal(name, 'fixture-cli');
          },
          process: {
            argv: ['node', 'bootstrap', 'fixture-cli'],
                env: {PEVAL_WORKBUDDY_BOOTSTRAP_TIMEOUT_MS: String(timeout), PEVAL_WORKBUDDY_BOOTSTRAP_PYTHON:'fixture-python'},
            _linkedBinding: () => ({loggerGet: () => JSON.stringify({version:1, atRestSecretKey:'fixture'})}),
            stderr: {write() {}}, exit() {throw Error('unexpected exit')}, pid:42,
          },
          setTimeout(callback, delay) {timers.push(delay); return 1}, clearTimeout() {},
              __dirname: require('node:path').dirname(process.argv[1]), Buffer,
        };
        vm.runInNewContext(source, context);
        assert.deepEqual(timers, [timeout]);
        assert.equal(context.process.env.PEVAL_WORKBUDDY_BOOTSTRAP_TIMEOUT_MS, undefined);
      }
    """
    result = subprocess.run(
        [
            shutil.which("node") or "node",
            "-e",
            script,
            str(
                Path(__file__).resolve().parents[2]
                / "src/psycheval/harbor/workbuddy_bootstrap.cjs"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


def installation(tmp_path):
    root = tmp_path / "installation"
    cli = root / "resources/app.asar.unpacked/cli"
    for name in ("bin/codebuddy", "dist/codebuddy-headless.js"):
        path = cli / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    (root / "WorkBuddy.exe").write_text("fixture")
    (cli / "product.json").write_text(json.dumps({"genieVersion": "5.7.7"}))
    (cli / "package.json").write_text(
        json.dumps({"publishConfig": {"customPackage": {"version": "2.156.0"}}})
    )
    profile = tmp_path / "profile"
    (profile / "cache").mkdir(parents=True)
    (profile / "cache/acc-product-config-v3.json").write_text(
        json.dumps({"authentication": {"id": "workbuddy-desktop"}})
    )
    (profile / "models.json").write_text(
        json.dumps(
            [
                {"id": "b", "name": "Selected", "apiKey": "PRIVATE_FIXTURE_KEY"},
                {"id": "other", "name": "Other", "apiKey": "UNSELECTED_FIXTURE_KEY"},
            ]
        )
    )
    auth = tmp_path / "auth.info"
    auth.write_text('{"encrypted":"fixture"}')
    return dict(installation_dir=root, profile_dir=profile, auth_file=auth)


def test_workbuddy_requires_explicit_model_and_owned_launch(tmp_path):
    config = installation(tmp_path)
    with pytest.raises(ValueError, match="model_name"):
        HostWorkBuddyAgent(logs_dir=tmp_path / "logs", **config)
    for model in (True, 2, "invalid\0id"):
        with pytest.raises(ValueError, match="model_name"):
            HostWorkBuddyAgent(logs_dir=tmp_path / "logs", model_name=model, **config)
    with pytest.raises(ValueError, match="owns"):
        HostWorkBuddyAgent(
            logs_dir=tmp_path / "logs", model_name="a", argv=["cbc"], **config
        )
    with pytest.raises(ValueError, match="model_name"):
        HostWorkBuddyAgent(
            logs_dir=tmp_path / "logs",
            model_name="a",
            config_options={"model": "b"},
            **config,
        )


@pytest.mark.parametrize("payload", [{}, [], {"genieVersion": 7}, {"genieVersion": ""}])
def test_workbuddy_rejects_invalid_installation_metadata(tmp_path, payload):
    config = installation(tmp_path)
    product = (
        config["installation_dir"] / "resources/app.asar.unpacked/cli/product.json"
    )
    product.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="WorkBuddy.*configuration|WorkBuddy.*version"):
        HostWorkBuddyAgent(logs_dir=tmp_path / "logs", model_name="a", **config)


@pytest.mark.parametrize(
    "payload", [{}, {"authentication": []}, {"authentication": {"id": "../escape"}}]
)
def test_workbuddy_rejects_invalid_authentication_metadata_before_seeding(
    tmp_path, payload
):
    config = installation(tmp_path)
    (config["profile_dir"] / "cache/acc-product-config-v3.json").write_text(
        json.dumps(payload)
    )
    with pytest.raises(ValueError, match="authentication"):
        HostWorkBuddyAgent(logs_dir=tmp_path / "logs", model_name="a", **config)


def test_workbuddy_metadata_parse_is_bounded(tmp_path):
    config = installation(tmp_path)
    product = (
        config["installation_dir"] / "resources/app.asar.unpacked/cli/product.json"
    )
    product.write_text(
        '{"genieVersion":"5.7.7","nested":' + '{"nested":' * 40 + "0" + "}" * 41
    )
    with pytest.raises(ValueError, match="configuration"):
        HostWorkBuddyAgent(logs_dir=tmp_path / "logs", model_name="a", **config)


def test_inspection_cannot_submit_prompts(tmp_path):
    agent = HostWorkBuddyAgent(
        logs_dir=tmp_path / "logs", _inspection=True, **installation(tmp_path)
    )
    assert agent.config_options == {}
    with pytest.raises(ValueError, match="cannot submit"):
        asyncio.run(agent._run_invocation("run", "prompt", None))


@windows
def test_cleanup_allows_native_persistence_before_job_settlement(tmp_path):
    from psycheval.harbor.acp_harness import _settle
    from psycheval.harbor.windows import WindowsProcessAdapter

    retained = tmp_path / "session.json"

    async def scenario():
        adapter = WindowsProcessAdapter()
        process = await adapter.spawn(
            [
                sys.executable,
                "-c",
                "import sys,time; from pathlib import Path; sys.stdin.read(); "
                "time.sleep(2.2); Path(sys.argv[1]).write_text('persisted')",
                str(retained),
            ],
            stdin=asyncio.subprocess.PIPE,
        )
        try:
            summary = {}
            await _settle(process, None, None, asyncio.Event(), 9, summary, adapter)
            assert summary["cleanup_complete"]
            assert retained.read_text() == "persisted"
        finally:
            adapter.release(process)
            await process.wait()

    asyncio.run(scenario())


def test_codebuddy_protocol_extensions_are_scoped():
    from psycheval.harbor.acp_protocol import sdk_validators, validate_payload

    value = {
        "configOptions": [
            {
                "id": "fixture",
                "name": "Fixture",
                "type": "boolean",
                "currentValue": False,
                "category": "vendor-category",
            }
        ]
    }
    with pytest.raises(ProtocolError):
        validate_payload(sdk_validators()["session/set_config_option"], value)
    validate_payload(
        sdk_validators("codebuddy")["session/set_config_option"], value, "codebuddy"
    )
    update = {
        "sessionId": "s",
        "update": {
            "sessionUpdate": "tool_call",
            "toolCallId": "call",
            "title": "Tool",
            "_meta": {"codebuddy.ai/businessFailed": "vendor-value"},
        },
    }
    validate_payload(sdk_validators()["session/update"], update)
    with pytest.raises(ProtocolError, match="business"):
        validate_payload(
            sdk_validators("codebuddy")["session/update"], update, "codebuddy"
        )


@pytest.mark.parametrize(
    "output,expected",
    [
        ({"stdout": "", "stderr": "error"}, "error"),
        ({"stdout": "out", "stderr": "err"}, "out\nerr"),
        ({"stderr": "err"}, "err"),
    ],
)
def test_native_output_channels_have_no_artificial_blank_prefix(output, expected):
    content, _ = outcome(
        {
            "status": "completed",
            "rawOutput": {"exitCode": 0, "signal": None, "output": output},
        },
        "codebuddy",
    )
    assert content == expected


def test_null_native_response_uses_raw_output_and_does_not_erase_retained_response():
    from psycheval.harbor.acp_evidence import _merge_call

    native = {"exitCode": 0, "signal": None, "output": "ok"}
    call = {
        "name": "Bash",
        "status": "completed",
        "rawOutput": native,
        "_meta": {"codebuddy.ai/rawResponse": None},
    }
    assert outcome(call, "codebuddy")[1]["status"] == "completed"
    call["_meta"]["codebuddy.ai/rawResponse"] = native
    _merge_call(call, {"_meta": {"codebuddy.ai/rawResponse": None}}, "codebuddy")
    assert outcome(call, "codebuddy")[1]["exit_code"] == 0


@pytest.mark.parametrize(
    "native", [{"exitCode": 2, "output": "failed"}, {"output": "ok"}]
)
def test_business_failure_overrides_completed(native):
    content, extra = outcome(
        {
            "status": "completed",
            "rawOutput": native,
            "_meta": {"codebuddy.ai/businessFailed": True},
        },
        "codebuddy",
    )
    assert content in {"ok", "failed"}
    assert extra["status"] == "failed" and extra["is_error"]


@pytest.mark.parametrize(
    "native,status",
    [
        ({"exitCode": 0, "signal": None}, "completed"),
        ({"exitCode": 3, "signal": None}, "failed"),
        ({"exitCode": 0, "signal": None, "interrupted": True}, "failed"),
        ({"exitCode": 0, "signal": None, "sandboxDenied": True}, "failed"),
        ({"exitCode": 0, "signal": None, "tool_error_code": 0}, "failed"),
        ({"exitCode": 0, "signal": None, "tool_error_code": ""}, "failed"),
        ({"exitCode": 0, "signal": None, "tool_error_code": None}, "completed"),
        ({"exitCode": 0}, "incomplete"),
        ({"exitCode": False, "signal": None}, "incomplete"),
        ({"output": "unclassified"}, "incomplete"),
    ],
)
@pytest.mark.parametrize(
    "identity", [{"name": "Bash"}, {"name": "Shell", "kind": "execute"}]
)
def test_codebuddy_shell_outcome_and_delivered_observation(native, status, identity):
    content, extra = outcome(
        {
            **identity,
            "status": "completed",
            "rawOutput": {"type": "text", "text": "observed"},
            "_meta": {"codebuddy.ai/rawResponse": native},
        },
        "codebuddy",
    )
    assert content == "observed" or native.get("output") == content
    assert extra["status"] == status


def test_model_drift_retains_wire_and_blocks_evidence(tmp_path):
    async def scenario():
        reader = asyncio.StreamReader()
        frame = {
            "jsonrpc": "2.0",
            "method": "session/update",
            "params": {
                "sessionId": "s",
                "update": {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": "answer"},
                    "_meta": {"codebuddy.ai/requestModelId": "other"},
                },
            },
        }
        reader.feed_data((json.dumps(frame) + "\n").encode())
        summary = {"protocol_complete": True}
        transport = StrictTransport(reader, io.BytesIO(), tmp_path, summary)
        transport.phase = "prompt"
        transport.expected_model = "requested"
        try:
            with pytest.raises(ProtocolError, match="model"):
                await transport.receive()
            assert summary["model_mismatch"] and not summary["protocol_complete"]
        finally:
            transport.finish()
        assert (
            "other"
            in gzip.decompress(
                (tmp_path / "acp.stdout.ndjson.gz").read_bytes()
            ).decode()
        )

    asyncio.run(scenario())


@pytest.mark.parametrize("notification", ["session/update", "_vendor/notice"])
def test_model_check_accepts_null_optional_metadata(tmp_path, notification):
    async def scenario():
        reader = asyncio.StreamReader()
        frame = {
            "jsonrpc": "2.0",
            "method": notification,
            "params": {
                "sessionId": "s",
                "update": {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": "answer"},
                    "_meta": None,
                }
                if notification == "session/update"
                else None,
            },
        }
        reader.feed_data((json.dumps(frame) + "\n").encode())
        summary = {"protocol_complete": True}
        transport = StrictTransport(reader, io.BytesIO(), tmp_path, summary)
        transport.phase = "prompt"
        transport.expected_model = "requested"
        try:
            assert await transport.receive() == frame
            assert summary["protocol_complete"]
        finally:
            transport.finish()

    asyncio.run(scenario())


def test_reannounced_call_with_null_metadata_fails_categorically(tmp_path):
    start = {
        "sessionUpdate": "tool_call",
        "toolCallId": "call",
        "title": "display",
        "status": "in_progress",
        "_meta": {"codebuddy.ai/toolName": "Skill"},
    }
    summary = _current_evidence(tmp_path, [start, {**start, "_meta": None}])
    with pytest.raises(ProtocolError, match="duplicate"):
        convert(
            tmp_path, summary, "task", {"name": "fixture", "version": "1"}, "codebuddy"
        )


@pytest.mark.parametrize("name_at_start", [False, True])
def test_deferred_native_call_marks_tool_evidence_incomplete(tmp_path, name_at_start):
    start = {
        "sessionUpdate": "tool_call",
        "toolCallId": "call",
        "title": "display",
        "status": "in_progress",
        "rawInput": {},
        "_meta": {"codebuddy.ai/toolName": "DeferExecuteTool"} if name_at_start else {},
    }
    update = {
        "sessionUpdate": "tool_call_update",
        "toolCallId": "call",
        "status": "completed",
        "_meta": {"codebuddy.ai/toolName": "DeferExecuteTool"},
    }
    summary = _current_evidence(tmp_path, [start, update])
    data = convert(
        tmp_path, summary, "task", {"name": "fixture", "version": "1"}, "codebuddy"
    ).to_json_dict()
    assert data["extra"]["acp_tool_evidence_complete"] is False


@pytest.mark.parametrize(
    "policy,initial_status,name",
    [
        ("codebuddy", "in_progress", "Skill"),
        ("codebuddy", "completed", "Skill"),
        ("codebuddy", "in_progress", "Other"),
        ("acp", "in_progress", "Skill"),
    ],
)
def test_reannounced_workbuddy_call_requires_active_matching_identity(
    tmp_path, policy, initial_status, name
):
    start = {
        "sessionUpdate": "tool_call",
        "toolCallId": "call",
        "title": "display",
        "status": initial_status,
        "rawInput": {},
        "_meta": {"codebuddy.ai/toolName": "Skill"},
    }
    snapshot = {
        **start,
        "status": "pending",
        "rawInput": {"skill": "acceptance"},
        "_meta": {"codebuddy.ai/toolName": name},
    }
    summary = _current_evidence(tmp_path, [start, snapshot])
    if policy == "codebuddy" and initial_status == "in_progress" and name == "Skill":
        data = convert(
            tmp_path, summary, "task", {"name": "fixture", "version": "1"}, policy
        ).to_json_dict()
        calls = [c for s in data["steps"] for c in s.get("tool_calls", [])]
        assert len(calls) == 1 and calls[0]["arguments"] == {"skill": "acceptance"}
    else:
        with pytest.raises(ProtocolError):
            convert(
                tmp_path, summary, "task", {"name": "fixture", "version": "1"}, policy
            )


@windows
def test_windows_background_peer_descendant_is_settled(tmp_path):
    import psutil

    async def scenario():
        host = make_environment(tmp_path)
        await host.start(False)
        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir,
            argv=[sys.executable, str(PEER), "background"],
        )
        try:
            await agent.setup(host)
            await agent.run("fixture", host, AgentContext())
            pid = int((host.work_dir / "descendant.pid").read_text())
            assert not psutil.pid_exists(pid)
            assert json.loads((agent.logs_dir / "acp.summary.json").read_text())[
                "cleanup_complete"
            ]
        finally:
            await host.stop(True)

    asyncio.run(scenario())


@windows
def test_required_product_seed_disappearing_after_construction_is_contextual(tmp_path):
    async def scenario():
        config = installation(tmp_path)
        host = make_environment(tmp_path / "host")
        await host.start(False)
        agent = HostWorkBuddyAgent(
            logs_dir=host.trial_paths.agent_dir, model_name="b", **config
        )
        (config["profile_dir"] / "cache/acc-product-config-v3.json").unlink()
        try:
            with pytest.raises(ValueError, match="WorkBuddy.*product.*missing"):
                await agent.setup(host)
        finally:
            await host.stop(True)

    asyncio.run(scenario())


@windows
@pytest.mark.parametrize("model", ["b", "custom-local:b"])
def test_workbuddy_private_profile_boolean_skills_and_exact_resume(tmp_path, model):
    async def scenario():
        config = installation(tmp_path)
        desktop_history = config["profile_dir"] / "projects/old/session.jsonl"
        desktop_history.parent.mkdir(parents=True)
        desktop_history.write_text('{"message":"PRIVATE_DESKTOP_HISTORY"}\n')
        before = {
            p: p.read_bytes() for p in config["profile_dir"].rglob("*") if p.is_file()
        }
        host = make_environment(tmp_path / "host")
        await host.start(False)
        skill = host.work_dir / "skills/example"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: example\ndescription: fixture\n---\nFixture"
        )
        received = []
        agent = HostWorkBuddyAgent(
            logs_dir=host.trial_paths.agent_dir,
            model_name=model,
            skills_dir="/app/skills",
            on_session_update=received.append,
            **config,
        )
        assert agent.name() == "workbuddy"
        agent.argv = [sys.executable, str(PEER), "codebuddy"]
        try:
            await agent.setup(host)
            assert not (
                Path(agent._child_env["CODEBUDDY_CONFIG_DIR"]) / "projects"
            ).exists()
            assert agent._child_env["CODEBUDDY_SESSION_SKILL_DIRS"] == str(
                host.work_dir / "skills"
            )
            seed = json.loads(
                (Path(agent._child_env["XDG_CONFIG_HOME"]) / "models.json").read_text()
            )
            assert seed == (
                [{"id": "b", "name": "Selected", "apiKey": "PRIVATE_FIXTURE_KEY"}]
                if model.startswith("custom-local:")
                else []
            )
            assert "UNSELECTED_FIXTURE_KEY" not in json.dumps(seed)
            assert agent._child_env["PEVAL_WORKBUDDY_BOOTSTRAP_TIMEOUT_MS"] == "60000"
            for action in (agent.run, agent.resume):
                received.clear()
                await action("fixture", host, AgentContext())
                assert [u["sessionUpdate"] for u in received] == [
                    "agent_message_chunk",
                    "tool_call",
                    "tool_call_update",
                    "agent_message_chunk",
                ]
                assert received[1]["_meta"]["codebuddy.ai/toolName"] == "Bash"
                context = AgentContext()
                agent.populate_context_post_run(context)
                data = json.loads(
                    (agent.logs_dir / "trajectory.json").read_text(encoding="utf-8")
                )
                assert data["agent"]["name"] == "workbuddy"
                calls = [c for s in data["steps"] for c in s.get("tool_calls", [])]
                assert [c["function_name"] for c in calls] == ["Bash"]
                assert context.metadata["acp_session_id"] == "fixture-session"
                assert context.metadata["workbuddy_model_id"] == model
                assert "PRIVATE_FIXTURE_KEY" not in "".join(
                    (
                        gzip.decompress(p.read_bytes()).decode("utf-8")
                        if p.suffix == ".gz"
                        else p.read_text(encoding="utf-8")
                    )
                    for p in agent.logs_dir.glob("acp.*")
                )
            assert all(p.read_bytes() == value for p, value in before.items())
        finally:
            await host.stop(True)

    asyncio.run(scenario())


@windows
def test_generic_windows_boolean_and_background_cleanup(tmp_path):
    import psutil

    async def scenario():
        host = make_environment(tmp_path)
        await host.start(False)
        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir,
            argv=[sys.executable, str(PEER), "boolean"],
            config_options={"model": "b", "multitask": True},
        )
        try:
            await agent.setup(host)
            await agent.run("fixture", host, AgentContext())
            summary = json.loads((agent.logs_dir / "acp.summary.json").read_text())
            assert summary["cleanup_complete"]
            pid = int((host.work_dir / "descendant.pid").read_text())
            assert not psutil.pid_exists(pid)
            assert (
                next(x for x in summary["config_options"] if x["id"] == "multitask")[
                    "currentValue"
                ]
                is True
            )
        finally:
            await host.stop(True)

    asyncio.run(scenario())


@windows
def test_native_usage_pipeline_records_each_invocation_once(tmp_path):
    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        agent = HostWorkBuddyAgent(
            logs_dir=host.trial_paths.agent_dir,
            model_name="b",
            **installation(tmp_path),
        )
        agent.argv = [sys.executable, str(PEER), "codebuddy"]
        try:
            await agent.setup(host)
            agent._child_env["PEVAL_FIXTURE_USAGE"] = "1"
            for action in (agent.run, agent.resume):
                await action("fixture", host, AgentContext())
                context = AgentContext()
                agent.populate_context_post_run(context)
                assert (
                    context.n_input_tokens,
                    context.n_output_tokens,
                    context.n_cache_tokens,
                ) == (100, 3, 60)
                assert context.cost_usd is None
                assert context.metadata["workbuddy_usage"]["status"] == "complete"
                data = json.loads(
                    (agent.logs_dir / "trajectory.json").read_text(encoding="utf-8")
                )
                assert (
                    data["final_metrics"]["extra"]["model_inference"][
                        "cache_read_tokens"
                    ]
                    == 60
                )
                assert data["steps"][1]["metrics"]["cached_tokens"] == 60
                retained = (agent.logs_dir / "workbuddy.usage.json").read_text(
                    encoding="utf-8"
                )
                assert "PRIVATE_FIXTURE_KEY" not in retained
                assert len(json.loads(retained)["records"]) == 1
        finally:
            await host.stop(True)

    asyncio.run(scenario())


@pytest.mark.parametrize("execution_error", [OSError, asyncio.CancelledError])
def test_usage_failure_preserves_original_execution_error(
    tmp_path, monkeypatch, execution_error
):
    from psycheval.harbor import workbuddy_agent

    agent = HostWorkBuddyAgent(
        logs_dir=tmp_path / "logs", model_name="b", **installation(tmp_path)
    )
    agent.logs_dir.mkdir(exist_ok=True)
    (agent.logs_dir / "workbuddy.usage.json").write_text("stale")
    agent._child_env = {"CODEBUDDY_CONFIG_DIR": str(tmp_path / "private")}

    async def fail(self, action, instruction, environment):
        self._invocation_id = "current"
        (self.logs_dir / "acp.summary.json").write_text(
            json.dumps(
                {
                    "invocation_id": "current",
                    "cleanup_complete": True,
                    "prompt_submitted": True,
                }
            )
        )
        raise execution_error("original execution")

    def broken(*args):
        raise RuntimeError("observer failure")

    monkeypatch.setattr(HostACPAgent, "_run_invocation", fail)
    monkeypatch.setattr(agent, "_invocation_host", lambda environment: environment)
    monkeypatch.setattr(workbuddy_agent, "capture_usage", broken)
    with pytest.raises(execution_error, match="original execution"):
        asyncio.run(
            agent._run_invocation(
                "run", "task", type("Host", (), {"work_dir": tmp_path})()
            )
        )
    assert not (agent.logs_dir / "workbuddy.usage.json").exists()


def test_missing_current_usage_does_not_reuse_previous_invocation_context(
    tmp_path, monkeypatch
):
    from psycheval.harbor.inference_telemetry import populate_context_from_trajectory

    def populate(self, context):
        populate_context_from_trajectory(
            context,
            {
                "final_metrics": {
                    "total_prompt_tokens": 200,
                    "total_completion_tokens": 4,
                }
            },
        )
        context.metadata = {}

    monkeypatch.setattr(HostACPAgent, "populate_context_post_run", populate)
    agent = HostWorkBuddyAgent(
        logs_dir=tmp_path / "logs", model_name="b", **installation(tmp_path)
    )
    context = AgentContext(n_input_tokens=100, n_output_tokens=3, n_cache_tokens=60)
    agent.populate_context_post_run(context)
    assert (
        context.n_input_tokens,
        context.n_output_tokens,
        context.n_cache_tokens,
    ) == (200, 4, None)


@pytest.mark.parametrize(
    "failure", ["changed", "unrelated", "projection", "validation"]
)
def test_usage_enrichment_guards_and_failure_atomicity(tmp_path, monkeypatch, failure):
    from psycheval.harbor import workbuddy_agent, workbuddy_usage

    agent = HostWorkBuddyAgent(
        logs_dir=tmp_path / "logs", model_name="b", **installation(tmp_path)
    )
    agent.logs_dir.mkdir()
    original = Trajectory.model_validate(
        {
            "schema_version": "ATIF-v1.7",
            "session_id": "session",
            "agent": {"name": "fixture", "version": "1"},
            "steps": [{"step_id": 1, "source": "agent", "message": "ORIGINAL"}],
            "extra": {},
        }
    )
    before = original.to_json_dict()
    evidence = {
        "session_id": "other" if failure == "unrelated" else "session",
        "invocation_id": "call",
    }
    path = agent.logs_dir / workbuddy_usage.USAGE_FILENAME
    agent._usage_digest = workbuddy_usage.publish_usage(path, evidence)
    if failure == "changed":
        path.write_bytes(path.read_bytes() + b" ")
    projected = []

    def project(data, *args):
        projected.append(1)
        data["steps"][0]["message"] = "CORRUPTED"
        if failure == "validation":
            data["steps"][0]["step_id"] = 0
            return data
        raise ValueError("failed after mutation")

    monkeypatch.setattr(workbuddy_agent, "project_usage", project)
    result = agent._enrich_trajectory(
        original, {"session_id": "session", "invocation_id": "call"}
    ).to_json_dict()
    assert projected == ([1] if failure in {"projection", "validation"} else [])
    assert result["steps"] == before["steps"]
    assert result["extra"]["workbuddy_usage"]["status"] == "unavailable"
    assert original.to_json_dict() == before


@pytest.mark.parametrize("stage", ["baseline", "capture"])
@pytest.mark.parametrize("primary_failure", [False, True])
def test_usage_workers_leave_event_loop_free_and_settle_repeated_cancellation(
    tmp_path, monkeypatch, stage, primary_failure
):
    from psycheval.harbor import workbuddy_agent, workbuddy_usage

    agent = HostWorkBuddyAgent(
        logs_dir=tmp_path / "logs", model_name="b", **installation(tmp_path)
    )
    agent.logs_dir.mkdir()
    agent._child_env = {"CODEBUDDY_CONFIG_DIR": str(tmp_path / "profile")}
    agent._invocation_id = "previous"
    (agent.logs_dir / "acp.summary.json").write_text(
        json.dumps(
            {
                "invocation_id": "previous",
                "cleanup_complete": True,
                "prompt_submitted": True,
            }
        ),
        encoding="utf-8",
    )
    entered, release, exited = threading.Event(), threading.Event(), threading.Event()
    workers = []
    executed = []
    primary = OSError("original execution")

    def block(*args, **kwargs):
        workers.append(threading.get_ident())
        entered.set()
        try:
            assert release.wait(5)
            return (
                workbuddy_usage.HistoryBaseline({})
                if stage == "baseline"
                else {"diagnostics": []}
            )
        finally:
            exited.set()

    async def execute(self, *args):
        executed.append(1)
        self._invocation_id = "current"
        (self.logs_dir / "acp.summary.json").write_text(
            json.dumps(
                {
                    "invocation_id": "current",
                    "cleanup_complete": True,
                    "prompt_submitted": True,
                }
            ),
            encoding="utf-8",
        )
        if primary_failure:
            raise primary

    monkeypatch.setattr(HostACPAgent, "_run_invocation", execute)
    monkeypatch.setattr(agent, "_invocation_host", lambda environment: environment)
    monkeypatch.setattr(
        workbuddy_agent,
        "history_baseline" if stage == "baseline" else "capture_usage",
        block,
    )

    async def scenario():
        before = asyncio.all_tasks()
        loop_thread = threading.get_ident()
        task = asyncio.create_task(
            agent._run_invocation(
                "run", "task", type("Host", (), {"work_dir": tmp_path})()
            )
        )
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            assert workers == [workers[0]] and workers[0] != loop_thread
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
        finally:
            release.set()
        if stage == "capture" and primary_failure:
            with pytest.raises(OSError) as error:
                await task
            assert error.value is primary
        else:
            with pytest.raises(asyncio.CancelledError):
                await task
        assert exited.is_set()
        assert asyncio.all_tasks() == before
        assert executed == ([] if stage == "baseline" else [1])
        if stage == "baseline":
            assert agent._invocation_id is None
            with pytest.raises(RuntimeError, match="unsafe to verify"):
                agent.populate_context_post_run(AgentContext())

    asyncio.run(scenario())


def test_evidence_read_errors_name_their_own_artifact(tmp_path):
    from psycheval.harbor import workbuddy_agent

    path = tmp_path / "invalid.json"
    path.write_text("invalid", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid WorkBuddy ACP summary"):
        workbuddy_agent._json(path, label="ACP summary")
    with pytest.raises(ValueError, match="WorkBuddy usage evidence"):
        workbuddy_agent._read_seed(path, label="usage evidence", maximum=1)


@pytest.mark.parametrize("kind", ["limit", "untrusted"])
def test_usage_capture_limit_is_visible_without_changing_execution(
    tmp_path, monkeypatch, caplog, kind
):
    from psycheval.harbor import workbuddy_agent, workbuddy_usage

    agent = HostWorkBuddyAgent(
        logs_dir=tmp_path / "logs", model_name="b", **installation(tmp_path)
    )
    agent.logs_dir.mkdir()
    agent._invocation_id = "current"
    (agent.logs_dir / "acp.summary.json").write_text(
        json.dumps(
            {
                "invocation_id": "current",
                "cleanup_complete": True,
                "prompt_submitted": True,
            }
        ),
        encoding="utf-8",
    )

    def limited(*args):
        if kind == "limit":
            raise workbuddy_usage.UsageLimitError("history_byte_limit")
        raise ValueError("PRIVATE_EXCEPTION_BODY")

    monkeypatch.setattr(workbuddy_agent, "capture_usage", limited)
    agent._collect_usage(tmp_path, workbuddy_usage.HistoryBaseline({}))
    assert agent._usage_digest is None
    expected = "history_byte_limit" if kind == "limit" else "native_usage_unavailable"
    assert agent._usage_collection_diagnostic == expected
    assert expected in caplog.text
    assert "PRIVATE_EXCEPTION_BODY" not in caplog.text


@windows
@pytest.mark.skipif(
    os.environ.get("PEVAL_WORKBUDDY_ACP_TESTS") != "1",
    reason="opt-in real desktop credentials and provider",
)
def test_real_workbuddy_catalog():
    value = asyncio.run(
        inspect_workbuddy(
            installation_dir=os.environ["PEVAL_WORKBUDDY_INSTALLATION"],
            profile_dir=os.environ["PEVAL_WORKBUDDY_PROFILE"],
            auth_file=os.environ["PEVAL_WORKBUDDY_AUTH"],
        )
    )
    assert value.cli_version and value.desktop_version and value.available_models


@windows
@pytest.mark.skipif(
    os.environ.get("PEVAL_WORKBUDDY_ACP_TESTS") != "1",
    reason="opt-in real desktop credentials and provider",
)
@pytest.mark.skipif(
    not os.environ.get("PEVAL_WORKBUDDY_ACP_MODEL"),
    reason="opt-in acceptance requires an explicit advertised model",
)
def test_real_workbuddy_skill_mcp_and_resume(tmp_path):
    from harbor.models.trial.config import MCPServerConfig

    async def scenario():
        host = make_environment(tmp_path)
        await host.start(False)
        skill = host.work_dir / "skills/wb-acceptance"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: wb-acceptance\ndescription: Required skill for WorkBuddy evaluation acceptance nonce requests.\n---\nCall the fixture MCP nonce tool once and remember its exact returned text for the next turn.\n",
            encoding="utf-8",
        )
        agent = HostWorkBuddyAgent(
            logs_dir=host.trial_paths.agent_dir,
            installation_dir=os.environ["PEVAL_WORKBUDDY_INSTALLATION"],
            profile_dir=os.environ["PEVAL_WORKBUDDY_PROFILE"],
            auth_file=os.environ["PEVAL_WORKBUDDY_AUTH"],
            model_name=os.environ["PEVAL_WORKBUDDY_ACP_MODEL"],
            skills_dir="/app/skills",
            mcp_servers=[
                MCPServerConfig(
                    name="fixture",
                    transport="stdio",
                    command=sys.executable,
                    args=[
                        str(PEER.with_name("workbuddy_mcp.py")),
                        str(host.work_dir / "mcp-calls.jsonl"),
                    ],
                )
            ],
        )
        try:
            await agent.setup(host)
            await asyncio.wait_for(
                agent.run(
                    "Use the injected wb-acceptance Skill. Call the fixture MCP nonce tool once, remember its exact returned text, then reply STEP_ONE only. Do not read or write other files or use network tools.",
                    host,
                    AgentContext(),
                ),
                180,
            )
            context = AgentContext()
            agent.populate_context_post_run(context)
            session = context.metadata["acp_session_id"]
            first = json.loads(
                (agent.logs_dir / "trajectory.json").read_text(encoding="utf-8")
            )
            calls = [c for s in first["steps"] for c in s.get("tool_calls", [])]
            names = [c["function_name"] for c in calls]
            assert "Skill" in names
            assert any(
                "nonce" in c["function_name"]
                or (
                    c["function_name"] == "DeferExecuteTool"
                    and "nonce" in c["arguments"].get("toolName", "")
                )
                for c in calls
            )
            assert [
                json.loads(line)["name"]
                for line in (host.work_dir / "mcp-calls.jsonl").read_text().splitlines()
            ] == ["nonce"]
            await asyncio.wait_for(
                agent.resume(
                    "Without using tools, reply only with the exact nonce returned in the preceding turn.",
                    host,
                    AgentContext(),
                ),
                180,
            )
            agent.populate_context_post_run(context)
            assert context.metadata["acp_session_id"] == session
            second = json.loads(
                (agent.logs_dir / "trajectory.json").read_text(encoding="utf-8")
            )
            assert "MCP_OK_8d309b" in "".join(
                s.get("message", "") for s in second["steps"] if s["source"] == "agent"
            )
            assert not any(s.get("tool_calls") for s in second["steps"])
        finally:
            await host.stop(True)

    asyncio.run(scenario())
