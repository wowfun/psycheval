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
    managed = {item["id"]: item for item in yaml.safe_load(original) if "id" in item}
    assert managed["skill-filesystem"]["config"] == {
        "includeDefaultRoots": False,
        "customSkillDirs": [],
    }


@pytest.mark.parametrize("skills_kind", ["task", "job", "both"])
def test_harbor_prepares_and_injects_dsh_skills_before_setup(
    tmp_path, monkeypatch, skills_kind
):
    from harbor.job import Job
    from harbor.models.job.config import JobConfig

    task = tmp_path / "task 中文"
    data = task / "environment/data"
    data.mkdir(parents=True)
    has_task = skills_kind in {"task", "both"}
    has_job = skills_kind in {"job", "both"}
    (task / "instruction.md").write_text(
        "Synthetic Skill setup only.", encoding="utf-8"
    )
    (task / "task.toml").write_text(
        'schema_version = "1.4"\n[task]\nname = "fixture/dsh-skills"\n[environment]\nworkdir = "/app"\n'
        + ('skills_dir = "/app/skills"\n' if has_task else ""),
        encoding="utf-8",
    )

    def skill(path, name):
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Fixture skill\n---\nUse scripts/marker.py and references/input.txt.\n",
            encoding="utf-8",
        )
        (path / "scripts").mkdir()
        (path / "scripts/marker.py").write_text("print('fixture')", encoding="utf-8")
        (path / "references").mkdir()
        (path / "references/input.txt").write_text(name, encoding="utf-8")

    if has_task:
        skill(data / "skills/task-skill", "task-skill")
    injected = tmp_path / "Job 注入/job-skill"
    if has_job:
        skill(injected, "job-skill")
    source = tmp_path / "caller.yaml"
    source.write_text(
        "- id: skill-filesystem\n  disabled: true\n  config:\n    includeDefaultRoots: true\n    customSkillDirs: [ambient]\n- id: tool-skill\n  disabled: true\n",
        encoding="utf-8",
    )
    observed = []
    task_config_bytes = (task / "task.toml").read_bytes()
    setup = HostDSHAgent.setup

    async def probe(self, environment):
        return "fixture-version"

    async def capture(self, environment):
        await setup(self, environment)
        config = yaml.safe_load(Path(self.argv[-1]).read_text(encoding="utf-8"))
        managed = {item["id"]: item for item in config if "id" in item}
        root = environment.native_path(self.skills_dir)
        assert managed["skill-filesystem"] == {
            "id": "skill-filesystem",
            "disabled": False,
            "config": {"includeDefaultRoots": False, "customSkillDirs": [str(root)]},
        }
        assert (
            managed["skill"]["disabled"] is False
            and managed["tool-skill"]["disabled"] is False
        )
        assert Path(self.argv[-3]).read_bytes() == source.read_bytes()
        names = sorted(p.name for p in root.iterdir())
        for name in names:
            assert (root / name / "references/input.txt").read_text(
                encoding="utf-8"
            ) == name
            assert (root / name / "scripts/marker.py").read_text(
                encoding="utf-8"
            ) == "print('fixture')"
        argv = list(self.argv)
        await setup(self, environment)
        assert self.argv == argv
        observed.append(names)

    monkeypatch.setattr(HostDSHAgent, "_probe_version", probe)
    monkeypatch.setattr(HostDSHAgent, "setup", capture)

    async def scenario():
        job = await Job.create(
            JobConfig.model_validate(
                {
                    "job_name": "dsh-skills",
                    "jobs_dir": str(tmp_path / "jobs"),
                    "quiet": True,
                    "install_only": True,
                    "tasks": [{"path": str(task)}],
                    "agents": [
                        {
                            "import_path": "psycheval.harbor.agents.dsh:HostDSHAgent",
                            "model_name": "fixture",
                            "skills": [str(injected)] if has_job else [],
                            "kwargs": {
                                "executable": sys.executable,
                                "patch_paths": [str(source)],
                            },
                        }
                    ],
                    "environment": {
                        "import_path": "psycheval.harbor.environment:HostEnvironment",
                        "kwargs": {
                            "host_access": {"filesystem": True, "process": True},
                            "workdir_root": str(tmp_path / "workspaces"),
                        },
                    },
                }
            )
        )
        result = await job.run()
        assert len(result.trial_results) == 1
        assert result.trial_results[0].exception_info is None

    asyncio.run(scenario())
    assert (task / "task.toml").read_bytes() == task_config_bytes
    assert observed == [
        sorted(
            (["task-skill"] if has_task else []) + (["job-skill"] if has_job else [])
        )
    ]


def test_dsh_declared_skill_directory_must_be_readable(tmp_path, monkeypatch):
    import os

    from tests.harbor.environment_support import make_environment

    async def scenario():
        environment = make_environment(
            tmp_path, environment_kwargs={"workdir_root": tmp_path / "workspaces"}
        )
        await environment.start(force_build=False)
        try:
            agent = HostDSHAgent(
                logs_dir=tmp_path / "logs",
                model_name="fixture",
                executable=sys.executable,
                skills_dir="/app/skills",
            )
            root = environment.native_path(agent.skills_dir)
            with pytest.raises(FileNotFoundError):
                await agent.setup(environment)
            root.mkdir()
            scandir = os.scandir

            def denied(path):
                if Path(path) == root:
                    raise PermissionError("fixture denied directory")
                return scandir(path)

            with monkeypatch.context() as scoped:
                scoped.setattr(os, "scandir", denied)
                with pytest.raises(PermissionError, match="fixture denied"):
                    await agent.setup(environment)
            await agent.setup(environment)
            root.rmdir()
            with pytest.raises(FileNotFoundError):
                agent._invocation_host(environment)
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


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
