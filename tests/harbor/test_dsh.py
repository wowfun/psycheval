"""DSH contract pinned to fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159, updates.ts."""

import asyncio
import json
import sys
from pathlib import Path

import pytest
import yaml

from psycheval.harbor.agents.acp.evidence import convert
from psycheval.harbor.agents.dsh import HostDSHAgent
from tests.harbor.test_acp import _current_evidence


def test_dsh_message_identity_and_native_tool_name_are_vendor_specific(tmp_path):
    updates = [
        {
            "sessionUpdate": "agent_thought_chunk",
            "messageId": "one",
            "content": {"type": "text", "text": "think"},
        },
        {
            "sessionUpdate": "agent_message_chunk",
            "messageId": "one",
            "content": {"type": "text", "text": "first"},
        },
        {
            "sessionUpdate": "agent_message_chunk",
            "messageId": "two",
            "content": {"type": "text", "text": "second"},
        },
        {
            "sessionUpdate": "tool_call",
            "toolCallId": "tool",
            "title": "write_file",
            "kind": "other",
            "status": "in_progress",
            "rawInput": {"path": "report.docx"},
        },
        {
            "sessionUpdate": "tool_call_update",
            "toolCallId": "tool",
            "status": "completed",
            "content": [
                {"type": "content", "content": {"type": "text", "text": "saved"}}
            ],
        },
        {
            "sessionUpdate": "agent_message_chunk",
            "messageId": "three",
            "content": {"type": "text", "text": "done"},
        },
        {"sessionUpdate": "usage_update", "used": 12345, "size": 99999},
    ]
    summary = _current_evidence(tmp_path, updates)
    data = convert(
        tmp_path, summary, "task", {"name": "dsh", "version": "1"}, "dsh"
    ).to_json_dict()
    steps = [step for step in data["steps"] if step["source"] == "agent"]
    assert [step["message"] for step in steps] == ["first", "second", "done"]
    assert steps[0]["reasoning_content"] == "think"
    assert steps[1]["tool_calls"][0]["function_name"] == "write_file"
    assert steps[1]["tool_calls"][0]["extra"]["acp_canonical_name"] is True
    assert "total_prompt_tokens" not in data["final_metrics"]
    generic = convert(
        tmp_path, summary, "task", {"name": "acp", "version": "1"}, "acp"
    ).to_json_dict()
    call = next(step for step in generic["steps"] if step.get("tool_calls"))[
        "tool_calls"
    ][0]
    assert call["extra"]["acp_canonical_name"] is False


def test_dsh_rejects_conflicting_model_and_missing_patch_before_launch(tmp_path):
    with pytest.raises(ValueError, match="model_name"):
        HostDSHAgent(
            logs_dir=tmp_path, model_name="model", config_options={"model": "other"}
        )
    agent = HostDSHAgent(
        logs_dir=tmp_path, model_name="model", patch_paths=[tmp_path / "missing.yml"]
    )
    with pytest.raises(FileNotFoundError):
        asyncio.run(agent.setup(None))


def test_dsh_rejects_oversize_or_replaced_patch_before_launch(tmp_path, monkeypatch):
    import os

    from psycheval.harbor.agents import dsh

    patch = tmp_path / "patch.yml"
    patch.write_text("- config: {}\n", encoding="utf-8")
    monkeypatch.setattr(dsh, "MAX_PATCH_BYTES", 2, raising=False)
    agent = HostDSHAgent(logs_dir=tmp_path, model_name="model", patch_paths=[patch])
    with pytest.raises(ValueError, match="DSH patch exceeds"):
        asyncio.run(agent.setup(None))
    monkeypatch.setattr(dsh, "MAX_PATCH_BYTES", 1024)
    other = tmp_path / "other.yml"
    other.write_text("- config: {}\n", encoding="utf-8")
    monkeypatch.setattr(
        dsh,
        "open_read_descriptor",
        lambda _: os.open(other, os.O_RDONLY),
        raising=False,
    )
    with pytest.raises(ValueError, match="DSH patch identity"):
        asyncio.run(agent.setup(None))


@pytest.mark.parametrize(
    "content",
    [
        b"- config: {apiKey: FIXTURE_YAML_CREDENTIAL, incomplete:\n",
        b"- config: {apiKey: FIXTURE_YAML_CREDENTIAL, invalid: \xff}\n",
    ],
)
def test_invalid_patch_diagnostics_do_not_retain_credentials(tmp_path, content):
    import traceback

    patch = tmp_path / "patch.yml"
    patch.write_bytes(content)
    agent = HostDSHAgent(logs_dir=tmp_path, model_name="model", patch_paths=[patch])
    with pytest.raises(ValueError, match="Invalid DSH YAML patch") as caught:
        asyncio.run(agent.setup(None))
    assert agent._state is None
    assert "FIXTURE_YAML_CREDENTIAL" not in "".join(
        traceback.format_exception(caught.value)
    )


@pytest.mark.parametrize("value", ["one", "!!js 1+1"])
def test_dsh_patches_are_seeded_once_and_isolation_wins(tmp_path, monkeypatch, value):
    from psycheval.harbor.agents.acp import HostACPAgent

    source = tmp_path / "patch.yml"
    source.write_text(
        "- name: test\n  config:\n    value: " + value + "\n", encoding="utf-8"
    )

    async def setup(self, environment):
        if self._state is not None:
            return
        self._state = tmp_path / "private"
        self._state.mkdir(exist_ok=True)
        self._child_env = {"HOME": str(self._state)}

    async def probe(self, environment):
        return "0.2.2-rc.1"

    monkeypatch.setattr(HostDSHAgent, "_probe_version", probe)
    monkeypatch.setattr(HostACPAgent, "setup", setup)
    agent = HostDSHAgent(
        logs_dir=tmp_path / "logs",
        executable=sys.executable,
        model_name="model",
        patch_paths=[source],
        extra_env={"DEEPSEEK_API_KEY": "explicit-fixture-key", "DSH_HOME": "forbidden"},
    )
    asyncio.run(agent.setup(None))
    home = agent._child_env["DSH_HOME"]
    assert home != "forbidden"
    assert agent._child_env["DEEPSEEK_API_KEY"] == "explicit-fixture-key"
    seeded = Path(agent.argv[-1])
    original = seeded.read_bytes()
    source.unlink()
    asyncio.run(agent.setup(None))
    assert seeded.read_bytes() == original
    assert agent._child_env["DSH_HOME"] == home
    assert "fixture-key" not in json.dumps(agent._agent_metadata)


def test_native_provider_default_choice_is_admitted_only_for_dsh_reasoning():
    from psycheval.harbor.agents.acp.protocol import (
        ProtocolError,
        sdk_validators,
        validate_payload,
    )

    value = {
        "sessionId": "native",
        "configOptions": [
            {
                "id": "reasoning_effort",
                "name": "Reasoning effort",
                "type": "select",
                "currentValue": "",
                "options": [
                    {"value": "", "name": "Provider default"},
                    {"value": "high", "name": "High"},
                ],
            }
        ],
    }
    validate_payload(sdk_validators("dsh")["session/new"], value, "dsh")
    with pytest.raises(ProtocolError, match="configuration value"):
        validate_payload(sdk_validators()["session/new"], value)


def test_dsh_retry_after_partial_patch_write_does_not_repeat_patches(
    tmp_path, monkeypatch
):
    from psycheval.harbor.agents.acp import HostACPAgent

    sources = [tmp_path / f"source-{index}.yaml" for index in range(2)]
    for source in sources:
        source.write_text("- name: fixture\n  config: {}\n", encoding="utf-8")

    async def setup(self, environment):
        self._state = tmp_path / "private"
        self._state.mkdir(exist_ok=True)
        self._child_env = {"HOME": str(self._state)}

    async def probe(self, environment):
        return "fixture-version"

    write_bytes = Path.write_bytes
    fail_once = True

    def failing_write(path, content):
        nonlocal fail_once
        if path.name == "patch-001.yaml" and fail_once:
            fail_once = False
            raise OSError("fixture partial write failure")
        return write_bytes(path, content)

    monkeypatch.setattr(HostACPAgent, "setup", setup)
    monkeypatch.setattr(HostDSHAgent, "_probe_version", probe)
    monkeypatch.setattr(Path, "write_bytes", failing_write)
    agent = HostDSHAgent(
        logs_dir=tmp_path / "logs", model_name="fixture", patch_paths=sources
    )
    initial_argv = list(agent.argv)
    with pytest.raises(OSError, match="partial write"):
        asyncio.run(agent.setup(None))
    assert agent.argv == initial_argv
    assert agent._dsh_seeded is False
    asyncio.run(agent.setup(None))
    assert agent.argv.count("--patch") == 3
    assert [
        Path(agent.argv[index + 1]).read_bytes()
        for index, arg in enumerate(agent.argv)
        if arg == "--patch"
    ][:-1] == [source.read_bytes() for source in sources]
    measurement_patch = yaml.safe_load(Path(agent.argv[-1]).read_text(encoding="utf-8"))
    assert measurement_patch[0]["config"]["compression"] == "none"
    assert measurement_patch[1]["insert"][0]["id"] == "peval-measurements"


@pytest.mark.parametrize(
    "update",
    [
        {
            "sessionUpdate": "tool_call",
            "toolCallId": "",
            "title": "",
            "status": "in_progress",
        },
        {
            "sessionUpdate": "tool_call",
            "toolCallId": "native",
            "title": "",
            "status": "in_progress",
        },
        {
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "text", "text": "invalid"},
        },
        {
            "sessionUpdate": "agent_message_chunk",
            "messageId": 123,
            "content": {"type": "text", "text": "invalid"},
        },
    ],
)
def test_malformed_native_identity_is_rejected_before_sdk_projection(update):
    from psycheval.harbor.agents.acp.protocol import (
        ProtocolError,
        sdk_validators,
        validate_payload,
    )

    with pytest.raises(ProtocolError):
        validate_payload(
            sdk_validators("dsh")["session/update"],
            {"sessionId": "native", "update": update},
            "dsh",
        )
