from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from psycheval.config import AcpAgent

MAX_ACP_FRAME_BYTES = 2 * 1024 * 1024
MAX_GATEWAY_CONNECTIONS = 16
MAX_AGENT_CONNECTIONS = 4
PROCESS_SHUTDOWN_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class _BridgeFailure(Exception):
    code: int
    reason: str


@dataclass(eq=False, slots=True)
class _Bridge:
    agent_id: str
    session_token: str | None
    loop: asyncio.AbstractEventLoop
    process: asyncio.subprocess.Process
    websocket: WebSocket
    stopping: bool = False
    terminated: bool = False

    def request_stop(self, reason: str, *, code: int = 1012) -> None:
        def schedule() -> None:
            if not self.stopping:
                self.stopping = True
                asyncio.create_task(self.shutdown(code, reason))

        try:
            self.loop.call_soon_threadsafe(schedule)
        except RuntimeError:
            # The owning event loop has already completed its process cleanup.
            pass

    async def shutdown(self, code: int, reason: str) -> None:
        self.stopping = True
        try:
            await self.websocket.close(code=code, reason=reason[:123])
        except (RuntimeError, WebSocketDisconnect):
            pass
        await self.terminate()

    async def terminate(self) -> None:
        if self.terminated:
            return
        self.terminated = True
        process = self.process
        if os.name == "posix":
            await self._terminate_posix_group(process)
            return
        if process.returncode is not None:
            return
        try:
            process.terminate()
        except (ProcessLookupError, PermissionError):
            return
        try:
            await asyncio.wait_for(process.wait(), timeout=PROCESS_SHUTDOWN_SECONDS)
            return
        except TimeoutError:
            pass
        try:
            process.kill()
        except (ProcessLookupError, PermissionError):
            return
        await process.wait()

    @staticmethod
    async def _terminate_posix_group(process: asyncio.subprocess.Process) -> None:
        process_group = process.pid
        try:
            os.killpg(process_group, signal.SIGTERM)
        except ProcessLookupError:
            if process.returncode is None:
                await process.wait()
            return
        except PermissionError:
            return

        loop = asyncio.get_running_loop()
        deadline = loop.time() + PROCESS_SHUTDOWN_SECONDS
        while _process_group_exists(process_group) and loop.time() < deadline:
            await asyncio.sleep(0.02)
        if _process_group_exists(process_group):
            try:
                os.killpg(process_group, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        if process.returncode is None:
            await process.wait()


class AcpGateway:
    """Owns allowlisted ACP process lifetimes and their raw WebSocket bridge."""

    def __init__(
        self, agents: tuple[AcpAgent, ...], workspace_root: str | Path
    ) -> None:
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self._configs = {agent.id: agent for agent in agents}
        self._bridges: dict[str, set[_Bridge]] = {agent.id: set() for agent in agents}
        self._opening: dict[str, int] = {}
        self._lock = threading.RLock()
        self._closed = False

    def agents(self) -> dict[str, object]:
        with self._lock:
            return {
                "cwd": str(self.workspace_root),
                "agents": [
                    {
                        "id": config.id,
                        "title": config.title,
                        "connected": bool(self._bridges.get(config.id)),
                        "connections": len(self._bridges.get(config.id, ()))
                        + self._opening.get(config.id, 0),
                    }
                    for config in self._configs.values()
                ],
            }

    def configuration(self, agent_id: str) -> AcpAgent:
        with self._lock:
            config = self._configs.get(agent_id)
            if config is None:
                raise KeyError(f"unknown ACP agent: {agent_id}")
            return config

    def reconfigure(self, agents: tuple[AcpAgent, ...]) -> None:
        next_configs = {agent.id: agent for agent in agents}
        with self._lock:
            if self._closed:
                return
            changed = {
                agent_id
                for agent_id in self._configs.keys() | next_configs.keys()
                if self._configs.get(agent_id) != next_configs.get(agent_id)
            }
            retiring = [
                bridge
                for agent_id in changed
                for bridge in self._bridges.get(agent_id, ())
            ]
            self._configs = next_configs
            for agent_id in next_configs:
                self._bridges.setdefault(agent_id, set())
        for bridge in retiring:
            bridge.request_stop("ACP agent configuration changed")

    async def serve(
        self, websocket: WebSocket, agent_id: str, session_token: str | None
    ) -> None:
        bridge: _Bridge | None = None
        try:
            config = self._reserve(agent_id)
            process = await self._spawn(config)
            bridge = _Bridge(
                agent_id=agent_id,
                session_token=session_token,
                loop=asyncio.get_running_loop(),
                process=process,
                websocket=websocket,
            )
            if not self._register(config, bridge):
                await bridge.terminate()
                await websocket.close(code=1012, reason="ACP configuration changed")
                return
            await websocket.accept()
            await self._run_bridge(bridge)
        except _BridgeFailure as exc:
            try:
                await websocket.close(code=exc.code, reason=exc.reason[:123])
            except (RuntimeError, WebSocketDisconnect):
                pass
        except (OSError, subprocess.SubprocessError):
            try:
                await websocket.close(code=1011, reason="failed to start ACP agent")
            except (RuntimeError, WebSocketDisconnect):
                pass
        finally:
            if bridge is None:
                self._release_reservation(agent_id)
            else:
                await bridge.terminate()
                self._unregister(bridge)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            bridges = [
                bridge for current in self._bridges.values() for bridge in current
            ]
        for bridge in bridges:
            bridge.request_stop("Psycheval serve is shutting down")

    def revoke_session(self, session_token: str) -> None:
        with self._lock:
            bridges = [
                bridge
                for current in self._bridges.values()
                for bridge in current
                if bridge.session_token == session_token
            ]
        for bridge in bridges:
            bridge.request_stop(
                "administrator session ended",
                code=1008,
            )

    def _reserve(self, agent_id: str) -> AcpAgent:
        with self._lock:
            if self._closed:
                raise _BridgeFailure(1012, "ACP gateway is closed")
            config = self._configs.get(agent_id)
            if config is None:
                raise _BridgeFailure(1008, "unknown ACP agent")
            total = sum(len(bridges) for bridges in self._bridges.values()) + sum(
                self._opening.values()
            )
            per_agent = len(self._bridges.get(agent_id, ())) + self._opening.get(
                agent_id, 0
            )
            if total >= MAX_GATEWAY_CONNECTIONS or per_agent >= MAX_AGENT_CONNECTIONS:
                raise _BridgeFailure(1013, "ACP gateway connection limit reached")
            self._opening[agent_id] = self._opening.get(agent_id, 0) + 1
            return config

    def _release_reservation(self, agent_id: str) -> None:
        with self._lock:
            remaining = self._opening.get(agent_id, 0) - 1
            if remaining > 0:
                self._opening[agent_id] = remaining
            else:
                self._opening.pop(agent_id, None)

    def _register(self, config: AcpAgent, bridge: _Bridge) -> bool:
        with self._lock:
            self._release_reservation(bridge.agent_id)
            if self._closed or self._configs.get(bridge.agent_id) != config:
                return False
            self._bridges.setdefault(bridge.agent_id, set()).add(bridge)
            return True

    def _unregister(self, bridge: _Bridge) -> None:
        with self._lock:
            self._bridges.get(bridge.agent_id, set()).discard(bridge)

    async def _spawn(self, config: AcpAgent) -> asyncio.subprocess.Process:
        process_options: dict[str, object] = {}
        if os.name == "posix":
            process_options["start_new_session"] = True
        elif os.name == "nt":
            process_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        return await asyncio.create_subprocess_exec(
            config.command,
            *config.args,
            cwd=self.workspace_root,
            env=os.environ.copy(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=MAX_ACP_FRAME_BYTES + 1,
            **process_options,
        )

    async def _run_bridge(self, bridge: _Bridge) -> None:
        stderr = asyncio.create_task(self._drain_stderr(bridge.process))
        tasks = {
            asyncio.create_task(self._browser_to_agent(bridge)),
            asyncio.create_task(self._agent_to_browser(bridge)),
            asyncio.create_task(bridge.process.wait()),
        }
        code = 1000
        reason = "ACP connection closed"
        try:
            done, _pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                try:
                    task.result()
                except _BridgeFailure as exc:
                    code, reason = exc.code, exc.reason
                    break
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            stderr.cancel()
            await asyncio.gather(stderr, return_exceptions=True)
            try:
                await bridge.websocket.close(code=code, reason=reason)
            except (RuntimeError, WebSocketDisconnect):
                pass

    async def _browser_to_agent(self, bridge: _Bridge) -> None:
        writer = bridge.process.stdin
        if writer is None:
            raise _BridgeFailure(1011, "ACP stdin is unavailable")
        while True:
            message = await bridge.websocket.receive()
            kind = message.get("type")
            if kind == "websocket.disconnect":
                return
            if message.get("bytes") is not None:
                raise _BridgeFailure(1003, "ACP accepts text frames only")
            text = message.get("text")
            if not isinstance(text, str):
                continue
            encoded = text.encode("utf-8")
            if len(encoded) > MAX_ACP_FRAME_BYTES:
                raise _BridgeFailure(1009, "ACP frame exceeds the gateway limit")
            if "\n" in text or "\r" in text:
                raise _BridgeFailure(1007, "ACP frames must contain one JSON message")
            writer.write(encoded + b"\n")
            try:
                await writer.drain()
            except (BrokenPipeError, ConnectionResetError) as exc:
                raise _BridgeFailure(1011, "ACP agent closed stdin") from exc

    async def _agent_to_browser(self, bridge: _Bridge) -> None:
        reader = bridge.process.stdout
        if reader is None:
            raise _BridgeFailure(1011, "ACP stdout is unavailable")
        while True:
            try:
                raw = await reader.readline()
            except ValueError as exc:
                raise _BridgeFailure(
                    1009, "ACP output exceeds the gateway limit"
                ) from exc
            if not raw:
                return
            raw = raw.removesuffix(b"\n").removesuffix(b"\r")
            if len(raw) > MAX_ACP_FRAME_BYTES:
                raise _BridgeFailure(1009, "ACP output exceeds the gateway limit")
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise _BridgeFailure(1007, "ACP output is not UTF-8") from exc
            await bridge.websocket.send_text(text)

    @staticmethod
    async def _drain_stderr(process: asyncio.subprocess.Process) -> None:
        reader = process.stderr
        if reader is None:
            return
        while await reader.read(64 * 1024):
            pass


def _process_group_exists(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
