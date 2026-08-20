from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import pytest
from harbor.agents.installed import hermes as harbor_hermes
from harbor.environments.base import ExecResult
from harbor.models.agent.context import AgentContext

from psycheval.harbor.hermes import HermesAgent, _enrich_hermes_trajectory


def test_enriches_exact_assistant_message_with_usage_and_cache() -> None:
    trajectory = {
        "steps": [
            {"step_id": 1, "source": "user", "message": "Do it"},
            {"step_id": 2, "source": "agent", "message": "Done"},
        ]
    }
    session = json.dumps(
        {
            "messages": [
                {"role": "user", "content": "Do it"},
                {
                    "role": "assistant",
                    "content": "Done",
                    "usage": {
                        "input_tokens": 120,
                        "output_tokens": 15,
                        "cache_read_input_tokens": 48,
                    },
                },
            ]
        }
    )

    enriched = _enrich_hermes_trajectory(trajectory, session)

    assert enriched["steps"][1]["metrics"]["cached_tokens"] == 48
    assert enriched["final_metrics"]["total_prompt_tokens"] == 120
    assert enriched["final_metrics"]["total_completion_tokens"] == 15
    assert enriched["final_metrics"]["total_cached_tokens"] == 48
    inference = enriched["final_metrics"]["extra"]["model_inference"]
    assert inference["cache_prompt_tokens"] == 120
    assert inference["cache_read_tokens"] == 48
    assert "ttft_ms_sum" not in inference


def test_enriches_structurally_aligned_list_content_and_tool_calls() -> None:
    trajectory = {
        "steps": [
            {"step_id": 1, "source": "user", "message": "Do it"},
            {"step_id": 2, "source": "agent", "message": "All done"},
            {
                "step_id": 3,
                "source": "agent",
                "message": "[tool call]",
                "tool_calls": [{"function_name": "finish", "arguments": {}}],
            },
        ]
    }
    session = json.dumps(
        {
            "messages": [
                {"role": "user", "content": "Do it"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "All"},
                        {"type": "text", "text": "done"},
                    ],
                    "usage": {"input_tokens": 100, "output_tokens": 10},
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "function": {"name": "finish", "arguments": "{}"},
                        }
                    ],
                    "usage": {"input_tokens": 120, "output_tokens": 5},
                },
            ]
        }
    )

    enriched = _enrich_hermes_trajectory(trajectory, session)

    assert enriched["steps"][1]["metrics"]["prompt_tokens"] == 100
    assert enriched["steps"][2]["metrics"]["prompt_tokens"] == 120
    assert enriched["final_metrics"]["total_prompt_tokens"] == 220
    assert enriched["final_metrics"]["total_completion_tokens"] == 15


def test_does_not_apply_usage_when_assistant_structure_is_unaligned(
    caplog: pytest.LogCaptureFixture,
) -> None:
    trajectory = {
        "steps": [
            {"step_id": 1, "source": "agent", "message": "first"},
            {"step_id": 2, "source": "agent", "message": "second"},
        ]
    }
    session = json.dumps(
        {
            "messages": [
                {
                    "role": "assistant",
                    "content": "first",
                    "usage": {"input_tokens": 100, "output_tokens": 10},
                }
            ]
        }
    )

    with caplog.at_level(logging.DEBUG, logger="psycheval.harbor.hermes"):
        enriched = _enrich_hermes_trajectory(trajectory, session)

    assert all("metrics" not in step for step in enriched["steps"])
    assert "total_prompt_tokens" not in enriched["final_metrics"]
    assert "usage enrichment skipped" in caplog.text


def test_setup_requires_native_resume_and_exact_export_capabilities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_setup(self: harbor_hermes.Hermes, environment: object) -> None:
        del self, environment

    monkeypatch.setattr(harbor_hermes.Hermes, "setup", fake_setup)
    agent = HermesAgent(
        logs_dir=tmp_path / "logs",
        model_name="xiaomi/mimo-v2.5-pro",
    )
    environment = _CapabilityEnvironment(
        chat_help="usage: hermes chat --resume SESSION --quiet",
        export_help="usage: hermes sessions export --session-id SESSION",
    )

    asyncio.run(agent.setup(environment))  # type: ignore[arg-type]

    assert any(
        "hermes chat --help" in command for command, _env in environment.commands
    )
    assert any(
        "hermes sessions export --help" in command
        for command, _env in environment.commands
    )


def test_setup_rejects_hermes_without_resume_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_setup(self: harbor_hermes.Hermes, environment: object) -> None:
        del self, environment

    monkeypatch.setattr(harbor_hermes.Hermes, "setup", fake_setup)
    agent = HermesAgent(logs_dir=tmp_path / "logs", model_name="openai/model")
    environment = _CapabilityEnvironment(
        chat_help="usage: hermes chat --quiet",
        export_help="usage: hermes sessions export --session-id SESSION",
    )

    with pytest.raises(RuntimeError, match="--resume"):
        asyncio.run(agent.setup(environment))  # type: ignore[arg-type]


def test_setup_rejects_hermes_without_exact_export_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_setup(self: harbor_hermes.Hermes, environment: object) -> None:
        del self, environment

    monkeypatch.setattr(harbor_hermes.Hermes, "setup", fake_setup)
    agent = HermesAgent(logs_dir=tmp_path / "logs", model_name="openai/model")
    environment = _CapabilityEnvironment(
        chat_help="usage: hermes chat --resume SESSION --quiet",
        export_help="usage: hermes sessions export --source cli",
    )

    with pytest.raises(RuntimeError, match="--session-id"):
        asyncio.run(agent.setup(environment))  # type: ignore[arg-type]


def test_registers_xiaomi_provider_and_delegates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native_providers: dict[str, tuple[str | None, list[str]]] = {}
    monkeypatch.setattr(harbor_hermes, "_NATIVE_PROVIDERS", native_providers)
    calls: list[tuple[str, object, AgentContext]] = []

    async def fake_run(
        self: harbor_hermes.Hermes,
        instruction: str,
        environment: object,
        context: AgentContext,
    ) -> None:
        assert self.name() == "hermes"
        self.logs_dir.mkdir(parents=True)
        (self.logs_dir / "hermes.txt").write_text(
            "output\nsession_id: session_123\n", encoding="utf-8"
        )
        calls.append((instruction, environment, context))

    monkeypatch.setattr(harbor_hermes.Hermes, "run", fake_run)
    agent = HermesAgent(
        logs_dir=tmp_path / "logs",
        model_name="xiaomi/mimo-v2.5-pro",
    )
    environment = _RecordingEnvironment()
    context = AgentContext()

    asyncio.run(agent.run("instruction", environment, context))  # type: ignore[arg-type]

    assert native_providers == {"xiaomi": ("xiaomi", ["XIAOMI_API_KEY"])}
    assert calls == [("instruction", environment, context)]
    assert len(environment.commands) == 1
    command, env = environment.commands[0]
    assert "--source cli --session-id session_123" in command
    assert env == {"HERMES_HOME": "/tmp/hermes"}


def test_rejects_conflicting_upstream_xiaomi_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        harbor_hermes,
        "_NATIVE_PROVIDERS",
        {"xiaomi": ("different", ["DIFFERENT_API_KEY"])},
    )
    agent = HermesAgent(
        logs_dir=tmp_path / "logs",
        model_name="xiaomi/mimo-v2.5-pro",
    )

    with pytest.raises(RuntimeError, match="conflicting Xiaomi provider mapping"):
        asyncio.run(agent.run("instruction", object(), AgentContext()))  # type: ignore[arg-type]


def test_resume_uses_the_last_exact_native_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XIAOMI_API_KEY", "fixture-key")
    monkeypatch.setattr(harbor_hermes, "_NATIVE_PROVIDERS", {})

    async def fake_run(
        self: harbor_hermes.Hermes,
        instruction: str,
        environment: object,
        context: AgentContext,
    ) -> None:
        del instruction, environment, context
        self.logs_dir.mkdir(parents=True)
        (self.logs_dir / "hermes.txt").write_text(
            "session_id: session_123\n", encoding="utf-8"
        )

    monkeypatch.setattr(harbor_hermes.Hermes, "run", fake_run)
    logs_dir = tmp_path / "logs"
    environment = _HermesResumeEnvironment(logs_dir)
    agent = HermesAgent(logs_dir=logs_dir, model_name="xiaomi/mimo-v2.5-pro")

    asyncio.run(agent.run("Start the task", environment, AgentContext()))  # type: ignore[arg-type]
    (logs_dir / "trajectory.json").write_text("previous\n", encoding="utf-8")
    asyncio.run(agent.resume("Continue the task", environment, AgentContext()))  # type: ignore[arg-type]

    assert agent.SUPPORTS_RESUME is True
    assert agent.SUPPORTS_LOAD_NATIVE_TRAJECTORY is False
    assert agent.SUPPORTS_LOAD_ATIF_TRAJECTORY is False
    resume_commands = [
        command for command, _env in environment.commands if "--resume" in command
    ]
    assert len(resume_commands) == 1
    assert "hermes --yolo chat" in resume_commands[0]
    assert "--resume session_123" in resume_commands[0]
    assert any(
        "--session-id session_456" in command for command, _env in environment.commands
    )
    assert not (logs_dir / "trajectory.json").exists()
    assert json.loads(
        (logs_dir / "hermes-session-state.json").read_text(encoding="utf-8")
    ) == {"protocol_version": 1, "session_id": "session_456"}


def test_resume_requires_persisted_exact_session_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(harbor_hermes, "_NATIVE_PROVIDERS", {})
    agent = HermesAgent(
        logs_dir=tmp_path / "logs",
        model_name="xiaomi/mimo-v2.5-pro",
    )
    agent._native_session_id = "memory-only"

    with pytest.raises(RuntimeError, match="valid exact-session state"):
        asyncio.run(agent.resume("Continue", _RecordingEnvironment(), AgentContext()))


def test_resumed_trajectory_contains_only_the_current_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XIAOMI_API_KEY", "fixture-key")
    monkeypatch.setattr(harbor_hermes, "_NATIVE_PROVIDERS", {})

    async def fake_run(
        self: harbor_hermes.Hermes,
        instruction: str,
        environment: object,
        context: AgentContext,
    ) -> None:
        del instruction, environment, context
        self.logs_dir.mkdir(parents=True)
        (self.logs_dir / "hermes.txt").write_text(
            "session_id: session_123\n", encoding="utf-8"
        )

    monkeypatch.setattr(harbor_hermes.Hermes, "run", fake_run)
    logs_dir = tmp_path / "logs"
    environment = _HermesResumeEnvironment(logs_dir)
    agent = HermesAgent(logs_dir=logs_dir, model_name="xiaomi/mimo-v2.5-pro")

    asyncio.run(agent.run("Start the task", environment, AgentContext()))  # type: ignore[arg-type]
    asyncio.run(agent.resume("Continue the task", environment, AgentContext()))  # type: ignore[arg-type]
    context = AgentContext()
    agent.populate_context_post_run(context)

    trajectory = json.loads((logs_dir / "trajectory.json").read_text(encoding="utf-8"))
    messages = [step["message"] for step in trajectory["steps"]]
    assert messages == ["Continue the task", "Second answer"]
    assert trajectory["session_id"] == "session_456"
    assert context.n_input_tokens == 3
    assert context.n_output_tokens == 4


def test_resumed_projection_uses_the_last_repeated_instruction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent, logs_dir = _completed_resumed_agent(tmp_path, monkeypatch)
    repeated_messages = [
        {"role": "user", "content": "Continue the task"},
        {"role": "assistant", "content": "Earlier continuation"},
        {"role": "user", "content": "Continue the task"},
        {"role": "assistant", "content": "Latest continuation"},
    ]
    (logs_dir / "hermes-session.jsonl").write_text(
        json.dumps({"id": "session_456", "messages": repeated_messages}) + "\n",
        encoding="utf-8",
    )

    agent.populate_context_post_run(AgentContext())

    trajectory = json.loads((logs_dir / "trajectory.json").read_text(encoding="utf-8"))
    assert [step["message"] for step in trajectory["steps"]] == [
        "Continue the task",
        "Latest continuation",
    ]


def test_resumed_projection_requires_the_current_instruction_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent, logs_dir = _completed_resumed_agent(tmp_path, monkeypatch)
    (logs_dir / "hermes-session.jsonl").write_text(
        json.dumps(
            {
                "id": "session_456",
                "messages": [
                    {"role": "user", "content": "Different task"},
                    {"role": "assistant", "content": "Different answer"},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="exact current instruction"):
        agent.populate_context_post_run(AgentContext())


def _completed_resumed_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[HermesAgent, Path]:
    monkeypatch.setenv("XIAOMI_API_KEY", "fixture-key")
    monkeypatch.setattr(harbor_hermes, "_NATIVE_PROVIDERS", {})

    async def fake_run(
        self: harbor_hermes.Hermes,
        instruction: str,
        environment: object,
        context: AgentContext,
    ) -> None:
        del instruction, environment, context
        self.logs_dir.mkdir(parents=True)
        (self.logs_dir / "hermes.txt").write_text(
            "session_id: session_123\n", encoding="utf-8"
        )

    monkeypatch.setattr(harbor_hermes.Hermes, "run", fake_run)
    logs_dir = tmp_path / "logs"
    environment = _HermesResumeEnvironment(logs_dir)
    agent = HermesAgent(logs_dir=logs_dir, model_name="xiaomi/mimo-v2.5-pro")
    asyncio.run(agent.run("Start the task", environment, AgentContext()))  # type: ignore[arg-type]
    asyncio.run(agent.resume("Continue the task", environment, AgentContext()))  # type: ignore[arg-type]
    return agent, logs_dir


def test_rejects_missing_reported_session_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(harbor_hermes, "_NATIVE_PROVIDERS", {})

    async def fake_run(
        self: harbor_hermes.Hermes,
        instruction: str,
        environment: object,
        context: AgentContext,
    ) -> None:
        del instruction, environment, context
        self.logs_dir.mkdir(parents=True)
        (self.logs_dir / "hermes.txt").write_text("no session", encoding="utf-8")

    monkeypatch.setattr(harbor_hermes.Hermes, "run", fake_run)
    agent = HermesAgent(
        logs_dir=tmp_path / "logs",
        model_name="xiaomi/mimo-v2.5-pro",
    )

    with pytest.raises(RuntimeError, match="did not report a valid session_id"):
        asyncio.run(agent.run("instruction", _RecordingEnvironment(), AgentContext()))


def test_failed_fresh_run_invalidates_prior_session_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(harbor_hermes, "_NATIVE_PROVIDERS", {})

    async def failing_run(
        self: harbor_hermes.Hermes,
        instruction: str,
        environment: object,
        context: AgentContext,
    ) -> None:
        del self, instruction, environment, context
        raise RuntimeError("model process failed")

    monkeypatch.setattr(harbor_hermes.Hermes, "run", failing_run)
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    state_path = logs_dir / "hermes-session-state.json"
    state_path.write_text(
        '{"protocol_version":1,"session_id":"prior_session"}\n',
        encoding="utf-8",
    )
    agent = HermesAgent(logs_dir=logs_dir, model_name="xiaomi/mimo-v2.5-pro")

    with pytest.raises(RuntimeError, match="model process failed"):
        asyncio.run(agent.run("new instruction", object(), AgentContext()))  # type: ignore[arg-type]

    assert not state_path.exists()


def test_exact_session_export_failure_is_non_fatal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(harbor_hermes, "_NATIVE_PROVIDERS", {})

    async def fake_run(
        self: harbor_hermes.Hermes,
        instruction: str,
        environment: object,
        context: AgentContext,
    ) -> None:
        del instruction, environment, context
        self.logs_dir.mkdir(parents=True)
        (self.logs_dir / "hermes.txt").write_text(
            "session_id: completed_session\n", encoding="utf-8"
        )

    monkeypatch.setattr(harbor_hermes.Hermes, "run", fake_run)
    agent = HermesAgent(
        logs_dir=tmp_path / "logs",
        model_name="xiaomi/mimo-v2.5-pro",
    )

    with caplog.at_level("WARNING"):
        asyncio.run(agent.run("instruction", _FailingEnvironment(), AgentContext()))

    assert "Failed to export exact Hermes session completed_session" in caplog.text
    agent.populate_context_post_run(AgentContext())
    assert not (agent.logs_dir / "trajectory.json").exists()


def test_fresh_exact_export_failure_uses_projectable_upstream_export(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(harbor_hermes, "_NATIVE_PROVIDERS", {})

    async def fake_run(
        self: harbor_hermes.Hermes,
        instruction: str,
        environment: object,
        context: AgentContext,
    ) -> None:
        del environment, context
        self.logs_dir.mkdir(parents=True)
        (self.logs_dir / "hermes.txt").write_text(
            "session_id: completed_session\n", encoding="utf-8"
        )
        (self.logs_dir / "hermes-session.jsonl").write_text(
            json.dumps(
                {
                    "id": "completed_session",
                    "messages": [
                        {"role": "user", "content": instruction},
                        {"role": "assistant", "content": "Completed answer"},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(harbor_hermes.Hermes, "run", fake_run)
    agent = HermesAgent(
        logs_dir=tmp_path / "logs",
        model_name="xiaomi/mimo-v2.5-pro",
    )

    asyncio.run(agent.run("instruction", _FailingEnvironment(), AgentContext()))
    agent.populate_context_post_run(AgentContext())

    trajectory = json.loads(
        (agent.logs_dir / "trajectory.json").read_text(encoding="utf-8")
    )
    assert [step["message"] for step in trajectory["steps"]] == [
        "instruction",
        "Completed answer",
    ]


def test_resumed_exact_session_export_failure_is_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XIAOMI_API_KEY", "fixture-key")
    monkeypatch.setattr(harbor_hermes, "_NATIVE_PROVIDERS", {})

    async def fake_run(
        self: harbor_hermes.Hermes,
        instruction: str,
        environment: object,
        context: AgentContext,
    ) -> None:
        del instruction, environment, context
        self.logs_dir.mkdir(parents=True)
        (self.logs_dir / "hermes.txt").write_text(
            "session_id: session_123\n", encoding="utf-8"
        )

    monkeypatch.setattr(harbor_hermes.Hermes, "run", fake_run)
    logs_dir = tmp_path / "logs"
    environment = _FailingResumeExportEnvironment(logs_dir)
    agent = HermesAgent(logs_dir=logs_dir, model_name="xiaomi/mimo-v2.5-pro")
    asyncio.run(agent.run("Start the task", environment, AgentContext()))  # type: ignore[arg-type]
    (logs_dir / "trajectory.json").write_text("previous\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Failed to export resumed Hermes session"):
        asyncio.run(
            agent.resume("Continue the task", environment, AgentContext())  # type: ignore[arg-type]
        )
    assert not (logs_dir / "trajectory.json").exists()
    assert not (logs_dir / "hermes-session.jsonl").exists()
    assert not (logs_dir / "hermes-session-state.json").exists()


class _RecordingEnvironment:
    def __init__(self) -> None:
        self.commands: list[tuple[str, dict[str, str] | None]] = []

    async def exec(
        self,
        command: str,
        *,
        env: dict[str, str] | None = None,
        **_kwargs: object,
    ) -> ExecResult:
        self.commands.append((command, env))
        return ExecResult(stdout="", stderr="", return_code=0)


class _FailingEnvironment(_RecordingEnvironment):
    async def exec(
        self,
        command: str,
        *,
        env: dict[str, str] | None = None,
        **_kwargs: object,
    ) -> ExecResult:
        self.commands.append((command, env))
        return ExecResult(stdout="", stderr="export failed", return_code=7)


class _CapabilityEnvironment(_RecordingEnvironment):
    def __init__(self, *, chat_help: str, export_help: str) -> None:
        super().__init__()
        self.chat_help = chat_help
        self.export_help = export_help

    async def exec(
        self,
        command: str,
        *,
        env: dict[str, str] | None = None,
        **_kwargs: object,
    ) -> ExecResult:
        self.commands.append((command, env))
        if "hermes chat --help" in command:
            return ExecResult(stdout=self.chat_help, stderr="", return_code=0)
        if "hermes sessions export --help" in command:
            return ExecResult(stdout=self.export_help, stderr="", return_code=0)
        return ExecResult(stdout="", stderr="", return_code=0)


class _HermesResumeEnvironment(_RecordingEnvironment):
    def __init__(self, logs_dir: Path) -> None:
        super().__init__()
        self.logs_dir = logs_dir

    async def exec(
        self,
        command: str,
        *,
        env: dict[str, str] | None = None,
        **_kwargs: object,
    ) -> ExecResult:
        self.commands.append((command, env))
        if "hermes --yolo chat" in command and "--resume" in command:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            (self.logs_dir / "hermes.txt").write_text(
                "session_id: session_456\n", encoding="utf-8"
            )
        if "--session-id session_123" in command:
            self._write_session_export(
                "session_123",
                [
                    {"role": "user", "content": "Start the task"},
                    {
                        "role": "assistant",
                        "content": "First answer",
                        "usage": {"prompt_tokens": 1, "completion_tokens": 2},
                    },
                ],
            )
        if "--session-id session_456" in command:
            self._write_session_export(
                "session_456",
                [
                    {"role": "user", "content": "Start the task"},
                    {
                        "role": "assistant",
                        "content": "First answer",
                        "usage": {"prompt_tokens": 1, "completion_tokens": 2},
                    },
                    {"role": "user", "content": "Continue the task"},
                    {
                        "role": "assistant",
                        "content": "Second answer",
                        "usage": {"prompt_tokens": 3, "completion_tokens": 4},
                    },
                ],
            )
        return ExecResult(stdout="", stderr="", return_code=0)

    def _write_session_export(self, session_id: str, messages: list[dict]) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.logs_dir / "hermes-session.jsonl").write_text(
            json.dumps({"id": session_id, "messages": messages}) + "\n",
            encoding="utf-8",
        )


class _FailingResumeExportEnvironment(_HermesResumeEnvironment):
    async def exec(
        self,
        command: str,
        *,
        env: dict[str, str] | None = None,
        **kwargs: object,
    ) -> ExecResult:
        if "--session-id session_456" in command:
            self.commands.append((command, env))
            return ExecResult(stdout="", stderr="export failed", return_code=7)
        return await super().exec(command, env=env, **kwargs)
