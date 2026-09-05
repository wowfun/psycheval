from __future__ import annotations

import json
import logging
import os
import re
import shlex
from pathlib import Path
from typing import override

from harbor.agents.installed import hermes as harbor_hermes
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from .inference_telemetry import (
    finalize_trajectory_metrics,
    metrics_from_observations,
    observation_from_usage,
    populate_context_from_trajectory,
)

_XIAOMI_PROVIDER = "xiaomi"
_XIAOMI_NATIVE_MAPPING = ("xiaomi", ["XIAOMI_API_KEY"])
_SESSION_ID = re.compile(r"^session_id:\s*([A-Za-z0-9_-]+)\s*$", re.MULTILINE)
_SESSION_TAIL_BYTES = 256 * 1024
_SESSION_STATE_FILENAME = "hermes-session-state.json"
_LOGGER = logging.getLogger(__name__)


def _register_xiaomi_provider() -> None:
    native_providers = harbor_hermes._NATIVE_PROVIDERS
    existing = native_providers.get(_XIAOMI_PROVIDER)
    if existing is not None and existing != _XIAOMI_NATIVE_MAPPING:
        raise RuntimeError(
            "Harbor's Hermes Agent defines a conflicting Xiaomi provider mapping"
        )
    native_providers[_XIAOMI_PROVIDER] = _XIAOMI_NATIVE_MAPPING


def _reported_session_id(log_path: Path) -> str:
    try:
        with log_path.open("rb") as handle:
            handle.seek(0, 2)
            handle.seek(max(0, handle.tell() - _SESSION_TAIL_BYTES))
            text = handle.read(_SESSION_TAIL_BYTES).decode("utf-8", errors="replace")
    except OSError as exc:
        raise RuntimeError(f"Hermes session log is unavailable: {log_path}") from exc
    matches = _SESSION_ID.findall(text)
    if not matches:
        raise RuntimeError("Hermes did not report a valid session_id")
    return matches[-1]


class HermesAgent(harbor_hermes.Hermes):
    """Delegate to Harbor's Hermes Agent with its native Xiaomi route enabled."""

    SUPPORTS_RESUME = True
    SUPPORTS_LOAD_NATIVE_TRAJECTORY = False
    SUPPORTS_LOAD_ATIF_TRAJECTORY = False

    @override
    async def setup(self, environment: BaseEnvironment) -> None:
        await super().setup(environment)
        probe_env = {"HERMES_HOME": "/tmp/hermes"}
        for command, capability in (
            ("hermes chat --help", "--resume"),
            ("hermes sessions export --help", "--session-id"),
        ):
            result = await self.exec_as_agent(
                environment,
                command=f'export PATH="$HOME/.local/bin:$PATH" && {command}',
                env=probe_env,
                timeout_sec=30,
            )
            output = "\n".join((result.stdout or "", result.stderr or ""))
            if result.return_code != 0 or capability not in output:
                raise RuntimeError(
                    "installed Hermes Agent does not expose required capability "
                    f"{capability!r} in `{command}`"
                )

    @override
    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        _register_xiaomi_provider()
        (self.logs_dir / "trajectory.json").unlink(missing_ok=True)
        (self.logs_dir / "hermes-session.jsonl").unlink(missing_ok=True)
        self._invalidate_session_state()
        self._current_instruction = self.render_instruction(instruction)
        self._current_was_resume = False
        self._native_session_id = None
        await super().run(instruction, environment, context)
        session_id = _reported_session_id(self.logs_dir / "hermes.txt")
        self._native_session_id = session_id
        await self._export_exact_session(environment, session_id, required=False)
        self._write_session_state(session_id)

    @override
    async def resume(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        del context
        _register_xiaomi_provider()
        (self.logs_dir / "trajectory.json").unlink(missing_ok=True)
        (self.logs_dir / "hermes-session.jsonl").unlink(missing_ok=True)
        session_id = self._read_session_state()
        rendered_instruction = self.render_instruction(instruction)
        env, cli_model, provider_flag = self._resume_runtime(rendered_instruction)
        self._invalidate_session_state()
        self._native_session_id = None
        self._current_instruction = rendered_instruction
        self._current_was_resume = True
        cli_parts = [
            'export PATH="$HOME/.local/bin:$PATH"',
            "hermes --yolo chat",
            f"--resume {shlex.quote(session_id)}",
            '-q "$HARBOR_INSTRUCTION"',
            "-Q",
            f"--model {shlex.quote(cli_model)}",
        ]
        if provider_flag:
            cli_parts.append(f"--provider {shlex.quote(provider_flag)}")
        toolsets_flag = self._resolved_flags.get("toolsets")
        if toolsets_flag:
            cli_parts.append(f"--toolsets {shlex.quote(str(toolsets_flag))}")
        command = (
            f"{cli_parts[0]} && {' '.join(cli_parts[1:])} "
            "2>&1 | stdbuf -oL tee /logs/agent/hermes.txt"
        )
        await self.exec_as_agent(environment, command=command, env=env)
        resumed_session_id = _reported_session_id(self.logs_dir / "hermes.txt")
        self._native_session_id = resumed_session_id
        await self._export_exact_session(environment, resumed_session_id, required=True)
        self._write_session_state(resumed_session_id)

    def _write_session_state(self, session_id: str) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.logs_dir / _SESSION_STATE_FILENAME).write_text(
            json.dumps(
                {"protocol_version": 1, "session_id": session_id},
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )

    def _invalidate_session_state(self) -> None:
        (self.logs_dir / _SESSION_STATE_FILENAME).unlink(missing_ok=True)

    def _read_session_state(self) -> str:
        state_path = self.logs_dir / _SESSION_STATE_FILENAME
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "Hermes resume requires valid exact-session state"
            ) from exc
        session_id = state.get("session_id") if isinstance(state, dict) else None
        if (
            not isinstance(state, dict)
            or state.get("protocol_version") != 1
            or not isinstance(session_id, str)
            or re.fullmatch(r"[A-Za-z0-9_-]+", session_id) is None
        ):
            raise RuntimeError("Hermes resume exact-session state is invalid")
        return session_id

    def _resume_runtime(
        self, instruction: str
    ) -> tuple[dict[str, str], str, str | None]:
        if not self.model_name or "/" not in self.model_name:
            raise ValueError("Model name must be in the format provider/model_name")
        provider, model = self.model_name.split("/", 1)
        env = {
            "HERMES_HOME": "/tmp/hermes",
            "TERMINAL_ENV": "local",
            "HARBOR_INSTRUCTION": instruction,
        }
        provider_flag: str | None = None
        use_native = False
        if provider in harbor_hermes._NATIVE_PROVIDERS:
            native_flag, key_names = harbor_hermes._NATIVE_PROVIDERS[provider]
            for key_name in key_names:
                key_value = os.environ.get(key_name)
                if key_value:
                    env[key_name] = key_value
                    provider_flag = native_flag
                    use_native = True
                    break
            if use_native and provider == "openai":
                if base_url := os.environ.get("OPENAI_BASE_URL"):
                    env["OPENAI_BASE_URL"] = base_url
        if not use_native:
            openrouter_key = os.environ.get("OPENROUTER_API_KEY")
            if not openrouter_key:
                native_info = harbor_hermes._NATIVE_PROVIDERS.get(provider)
                if native_info:
                    key_hint = " or ".join(native_info[1])
                    raise ValueError(
                        f"No API key found. Set {key_hint} or OPENROUTER_API_KEY."
                    )
                raise ValueError("No API key found. Set OPENROUTER_API_KEY.")
            env["OPENROUTER_API_KEY"] = openrouter_key
        cli_model = model if provider_flag else self.model_name
        return env, cli_model, provider_flag

    async def _export_exact_session(
        self,
        environment: BaseEnvironment,
        session_id: str,
        *,
        required: bool,
    ) -> None:
        try:
            await self.exec_as_agent(
                environment,
                command=(
                    'export PATH="$HOME/.local/bin:$PATH" && '
                    "hermes sessions export /logs/agent/hermes-session.jsonl "
                    f"--source cli --session-id {shlex.quote(session_id)}"
                ),
                env={"HERMES_HOME": "/tmp/hermes"},
                timeout_sec=30,
            )
        except Exception as exc:  # noqa: BLE001 - post-run telemetry is best effort.
            if required:
                raise RuntimeError(
                    f"Failed to export resumed Hermes session {session_id}: {exc}"
                ) from exc
            self.logger.warning(
                "Failed to export exact Hermes session %s: %s", session_id, exc
            )

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
        session_path = self.logs_dir / "hermes-session.jsonl"
        if not session_path.is_file():
            if getattr(self, "_current_was_resume", False):
                raise RuntimeError("resumed Hermes session export is unavailable")
            return
        instruction = getattr(self, "_current_instruction", None)
        session_id = getattr(self, "_native_session_id", None)
        if not instruction or not session_id:
            if getattr(self, "_current_was_resume", False):
                raise RuntimeError("resumed Hermes session projection has no boundary")
            return
        try:
            current_turn = _current_turn_export(
                session_path.read_text(encoding="utf-8"), instruction
            )
            trajectory = self._convert_hermes_session_to_atif(current_turn, session_id)
            if trajectory is None:
                raise ValueError("current Hermes turn produced no ATIF steps")
            trajectory_value = _enrich_hermes_trajectory(
                trajectory.to_json_dict(), current_turn
            )
            trajectory_path = self.logs_dir / "trajectory.json"
            trajectory_path.write_text(
                json.dumps(trajectory_value, indent=2), encoding="utf-8"
            )
            populate_context_from_trajectory(context, trajectory_value)
        except Exception as exc:
            if getattr(self, "_current_was_resume", False):
                raise RuntimeError(
                    f"failed to project current resumed Hermes turn: {exc}"
                ) from exc
            self.logger.debug("Error writing current Hermes ATIF trajectory: %s", exc)


def _current_turn_export(jsonl_text: str, instruction: str) -> str:
    records: list[dict] = []
    for raw_line in jsonl_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            continue
        records.append(value)

    for record in reversed(records):
        messages = record.get("messages")
        if not isinstance(messages, list):
            continue
        boundary = _last_instruction_index(messages, instruction)
        if boundary is None:
            continue
        projected = dict(record)
        projected["messages"] = messages[boundary:]
        return json.dumps(projected, ensure_ascii=False)

    boundary = _last_instruction_index(records, instruction)
    if boundary is None:
        raise ValueError("exact current instruction was not found in Hermes export")
    return "\n".join(
        json.dumps(record, ensure_ascii=False) for record in records[boundary:]
    )


def _enrich_hermes_trajectory(trajectory: dict, current_turn_export: str) -> dict:
    records = [
        value
        for line in current_turn_export.splitlines()
        if line.strip()
        for value in [json.loads(line)]
        if isinstance(value, dict)
    ]
    messages = (
        records[0].get("messages")
        if len(records) == 1 and isinstance(records[0].get("messages"), list)
        else records
    )
    assistants = [
        message
        for message in messages
        if isinstance(message, dict)
        and message.get("role") == "assistant"
        and _assistant_emits_step(message)
    ]
    assistant_steps = [
        step
        for step in trajectory.get("steps", [])
        if isinstance(step, dict) and step.get("source") in {"agent", "assistant"}
    ]
    if len(assistant_steps) != len(assistants):
        _LOGGER.debug(
            "Hermes usage enrichment skipped: %d ATIF assistant steps for %d "
            "session assistant messages",
            len(assistant_steps),
            len(assistants),
        )
        return finalize_trajectory_metrics(trajectory)
    for step, assistant in zip(assistant_steps, assistants, strict=True):
        observation = observation_from_usage(
            assistant.get("usage"),
            usage_source="hermes.session.message.usage",
        )
        if observation is not None:
            step["metrics"] = metrics_from_observations([observation])
    return finalize_trajectory_metrics(trajectory)


def _assistant_emits_step(message: dict) -> bool:
    content = message.get("content", "")
    if isinstance(content, list):
        content = " ".join(
            str(part.get("text") or "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return bool(content or message.get("tool_calls"))


def _last_instruction_index(messages: list, instruction: str) -> int | None:
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        if str(content) == instruction:
            return index
    return None
