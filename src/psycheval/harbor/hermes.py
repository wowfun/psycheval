from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import override

from harbor.agents.installed import hermes as harbor_hermes
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

_XIAOMI_PROVIDER = "xiaomi"
_XIAOMI_NATIVE_MAPPING = ("xiaomi", ["XIAOMI_API_KEY"])
_SESSION_ID = re.compile(r"^session_id:\s*([A-Za-z0-9_-]+)\s*$", re.MULTILINE)
_SESSION_TAIL_BYTES = 256 * 1024


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

    @override
    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        _register_xiaomi_provider()
        await super().run(instruction, environment, context)
        session_id = _reported_session_id(self.logs_dir / "hermes.txt")
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
            self.logger.warning(
                "Failed to export exact Hermes session %s: %s", session_id, exc
            )
