from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from harbor.agents.installed import hermes as harbor_hermes
from harbor.environments.base import ExecResult
from harbor.models.agent.context import AgentContext

from psycheval.harbor.hermes import HermesAgent


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
