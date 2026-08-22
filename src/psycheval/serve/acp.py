from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from psycheval.config import AcpAgent

ACP_V2_REVISION = "dce4d0e101c1331130855d859cbd3b9c5b2305e3"
REQUEST_TIMEOUT_SECONDS = 20.0
PROMPT_TIMEOUT_SECONDS = 24 * 60 * 60.0
INITIALIZATION_LIVENESS_GRACE_SECONDS = 0.05
EVENT_LIMIT = 1200
SESSION_LIMIT = 500
STDOUT_LINE_LIMIT = 4 * 1024 * 1024
STDERR_LINE_LIMIT = 64 * 1024


class AcpError(RuntimeError):
    def __init__(self, message: str, *, status: int = 502, code: int | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


@dataclass
class _Pending:
    done: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: dict[str, Any] | None = None


@dataclass
class _Session:
    agent_id: str
    session_id: str
    title: str = ""
    cwd: str = ""
    active_prompt: bool = False
    closed: bool = False
    loaded: bool = False
    revision: int = 0
    events: deque[dict[str, Any]] = field(
        default_factory=lambda: deque(maxlen=EVENT_LIMIT)
    )
    modes: dict[str, Any] | None = None
    config_options: list[dict[str, Any]] = field(default_factory=list)
    current_mode: str | None = None
    usage: dict[str, Any] | None = None
    error: str | None = None

    def payload(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "title": self.title or self.session_id,
            "cwd": self.cwd,
            "active_prompt": self.active_prompt,
            "closed": self.closed,
            "loaded": self.loaded,
            "revision": self.revision,
            "modes": self.modes,
            "config_options": self.config_options,
            "current_mode": self.current_mode,
            "usage": self.usage,
            "error": self.error,
        }


class _Connection:
    def __init__(self, manager: AcpManager, config: AcpAgent, cwd: Path) -> None:
        self.manager = manager
        self.config = config
        self.cwd = cwd
        self.process: subprocess.Popen[bytes] | None = None
        self.protocol_version: int | None = None
        self.agent_info: dict[str, Any] = {}
        self.capabilities: dict[str, Any] = {}
        self.auth_methods: list[dict[str, Any]] = []
        self._next_id = 1
        self._pending: dict[int | str, _Pending] = {}
        self._permission_requests: set[int | str] = set()
        self._pending_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._connect_lock = threading.Lock()
        self._close_lock = threading.Lock()
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self.stderr_tail: deque[str] = deque(maxlen=20)

    @property
    def connected(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def connect(self) -> dict[str, Any]:
        with self._connect_lock:
            if self.connected and self.protocol_version is not None:
                return self.payload()
            try:
                fallback = False
                try:
                    result = self._start_and_initialize(2)
                    fallback = int(result.get("protocolVersion", 2)) == 1
                except AcpError as exc:
                    fallback = exc.code in {-32601, -32602}
                    if not fallback:
                        raise
                if fallback:
                    self.close()
                    result = self._start_and_initialize(1)
                self._confirm_process_survived_initialization()
                self.protocol_version = int(result.get("protocolVersion", 1))
                self.agent_info = _dict(result.get("agentInfo"))
                self.capabilities = _dict(result.get("agentCapabilities"))
                self.auth_methods = _list_of_dicts(result.get("authMethods"))
            except Exception:
                self.close()
                raise
            self.manager.publish_agent(
                self.config.id,
                {
                    "type": "connection",
                    "status": "connected",
                    "protocol_version": self.protocol_version,
                },
            )
            return self.payload()

    def payload(self) -> dict[str, Any]:
        return {
            "id": self.config.id,
            "title": self.config.title,
            "connected": self.connected and self.protocol_version is not None,
            "protocol_version": self.protocol_version,
            "protocol_revision": ACP_V2_REVISION
            if self.protocol_version == 2
            else None,
            "agent_info": self.agent_info,
            "capabilities": self.capabilities,
            "auth_methods": self.auth_methods,
            "stderr_tail": list(self.stderr_tail),
        }

    def request(
        self,
        method: str,
        params: dict[str, Any],
        *,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
    ) -> Any:
        if not self.connected:
            raise AcpError("ACP agent is not connected", status=409)
        with self._pending_lock:
            request_id = self._next_id
            self._next_id += 1
            pending = _Pending()
            self._pending[request_id] = pending
        try:
            self._write(
                {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
            )
            if not pending.done.wait(timeout):
                raise AcpError(f"ACP request timed out: {method}", status=504)
            if pending.error is not None:
                code = pending.error.get("code")
                message = str(
                    pending.error.get("message") or f"ACP request failed: {method}"
                )
                raise AcpError(
                    message,
                    status=400 if code in {-32600, -32601, -32602} else 502,
                    code=code if isinstance(code, int) else None,
                )
            return pending.result
        finally:
            with self._pending_lock:
                self._pending.pop(request_id, None)

    def notify(self, method: str, params: dict[str, Any]) -> None:
        if not self.connected:
            raise AcpError("ACP agent is not connected", status=409)
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def respond_permission(
        self, request_id: int | str, option_id: str | None, *, cancelled: bool
    ) -> None:
        with self._pending_lock:
            if request_id not in self._permission_requests:
                raise AcpError("permission request is no longer pending", status=409)
            self._permission_requests.remove(request_id)
        outcome = (
            {"outcome": "cancelled"}
            if cancelled
            else {
                "outcome": "selected",
                "optionId": option_id,
            }
        )
        self._write(
            {"jsonrpc": "2.0", "id": request_id, "result": {"outcome": outcome}}
        )

    def close(self) -> None:
        with self._close_lock:
            process = self.process
            self.process = None
            self.protocol_version = None
            if process is not None:
                _terminate_process(process)
            with self._pending_lock:
                pending = list(self._pending.values())
                self._pending.clear()
                self._permission_requests.clear()
            for item in pending:
                item.error = {"code": -32000, "message": "ACP agent disconnected"}
                item.done.set()

    def _start_and_initialize(self, protocol_version: int) -> dict[str, Any]:
        self._spawn()
        result = self.request(
            "initialize",
            {
                "protocolVersion": protocol_version,
                "clientCapabilities": {},
                "clientInfo": {"name": "peval", "version": "0.1.0"},
            },
        )
        if not isinstance(result, dict):
            raise AcpError("ACP initialize returned a non-object result")
        return result

    def _confirm_process_survived_initialization(self) -> None:
        process = self.process
        if process is None:
            raise AcpError("ACP agent exited during initialization", status=502)
        try:
            process.wait(timeout=INITIALIZATION_LIVENESS_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            if self.process is process and process.poll() is None:
                return
        raise AcpError("ACP agent exited during initialization", status=502)

    def _spawn(self) -> None:
        try:
            process = subprocess.Popen(
                [self.config.command, *self.config.args],
                cwd=self.cwd,
                env=os.environ.copy(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )
        except OSError as exc:
            raise AcpError(f"failed to start ACP agent: {exc}", status=503) from exc
        self.process = process
        self._stdout_thread = threading.Thread(
            target=self._read_stdout, args=(process,), daemon=True
        )
        self._stderr_thread = threading.Thread(
            target=self._read_stderr, args=(process,), daemon=True
        )
        self._stdout_thread.start()
        self._stderr_thread.start()

    def _write(self, payload: dict[str, Any]) -> None:
        process = self.process
        if process is None or process.stdin is None or process.poll() is not None:
            raise AcpError("ACP agent exited", status=502)
        encoded = (
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        try:
            with self._write_lock:
                process.stdin.write(encoded)
                process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise AcpError("failed to write to ACP agent", status=502) from exc

    def _read_stdout(self, process: subprocess.Popen[bytes]) -> None:
        if process.stdout is None:
            return
        failure = "ACP agent exited"
        try:
            while True:
                raw, exceeded = _bounded_readline(process.stdout, STDOUT_LINE_LIMIT)
                if exceeded:
                    self.manager.publish_agent(
                        self.config.id,
                        {
                            "type": "error",
                            "message": "ACP stdout line exceeded the client limit",
                        },
                    )
                    continue
                if not raw:
                    break
                try:
                    message = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    self.manager.publish_agent(
                        self.config.id,
                        {
                            "type": "error",
                            "message": f"malformed ACP output: {exc}",
                        },
                    )
                    continue
                if not isinstance(message, dict):
                    continue
                try:
                    if "method" in message:
                        self._handle_inbound_method(message)
                    elif "id" in message:
                        self._handle_response(message)
                except AcpError as exc:
                    self.manager.publish_agent(
                        self.config.id,
                        {
                            "type": "error",
                            "message": f"invalid ACP message: {exc}",
                        },
                    )
        except Exception as exc:  # noqa: BLE001 - child protocol boundary.
            failure = f"invalid ACP message: {exc}"
        with self._close_lock:
            if self.process is not process:
                return
            self.process = None
            self.protocol_version = None
        _terminate_process(process)
        self._fail_pending(failure)
        self.manager.connection_exited(self.config.id, process.poll(), message=failure)

    def _read_stderr(self, process: subprocess.Popen[bytes]) -> None:
        if process.stderr is None:
            return
        while True:
            raw, exceeded = _bounded_readline(process.stderr, STDERR_LINE_LIMIT)
            if exceeded:
                self.stderr_tail.append("ACP stderr line exceeded the client limit")
                continue
            if not raw:
                break
            text = raw.decode("utf-8", errors="replace").rstrip()
            if text:
                self.stderr_tail.append(text)

    def _handle_response(self, message: dict[str, Any]) -> None:
        request_id = _rpc_id(message.get("id"))
        with self._pending_lock:
            pending = self._pending.get(request_id)
        if pending is None:
            return
        error = message.get("error")
        pending.error = error if isinstance(error, dict) else None
        pending.result = message.get("result")
        pending.done.set()

    def _fail_pending(self, message: str) -> None:
        with self._pending_lock:
            pending = list(self._pending.values())
        for item in pending:
            item.error = {"code": -32000, "message": message}
            item.done.set()

    def _handle_inbound_method(self, message: dict[str, Any]) -> None:
        method = str(message.get("method") or "")
        params = _dict(message.get("params"))
        raw_request_id = message.get("id")
        request_id = _rpc_id(raw_request_id) if raw_request_id is not None else None
        if method == "session/update":
            session_id = str(params.get("sessionId") or "")
            update = _dict(params.get("update"))
            self.manager.handle_update(self.config.id, session_id, update)
            return
        if method == "session/request_permission" and request_id is not None:
            session_id = str(params.get("sessionId") or "")
            with self._pending_lock:
                self._permission_requests.add(request_id)
            self.manager.publish(
                self.config.id,
                session_id,
                {
                    "type": "permission",
                    "request_id": request_id,
                    "tool_call": params.get("toolCall"),
                    "options": params.get("options") or [],
                },
            )
            return
        if request_id is not None:
            self._write(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"client method not supported: {method}",
                    },
                }
            )


class AcpManager:
    def __init__(
        self, agents: tuple[AcpAgent, ...], workspace_root: str | Path
    ) -> None:
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self._configs = {agent.id: agent for agent in agents}
        self._connections: dict[str, _Connection] = {}
        self._retiring_connections: set[_Connection] = set()
        self._sessions: dict[tuple[str, str], _Session] = {}
        self._agent_events: dict[str, deque[dict[str, Any]]] = {
            agent.id: deque(maxlen=100) for agent in agents
        }
        self._condition = threading.Condition(threading.RLock())
        self._closed = False

    def agents(self) -> dict[str, Any]:
        with self._condition:
            return {
                "agents": [
                    self._agent_payload(config) for config in self._configs.values()
                ]
            }

    def reconfigure(self, agents: tuple[AcpAgent, ...]) -> None:
        next_configs = {agent.id: agent for agent in agents}
        with self._condition:
            changed_ids = {
                agent_id
                for agent_id, config in self._configs.items()
                if next_configs.get(agent_id) != config
            }
            connections = [
                self._connections.pop(agent_id)
                for agent_id in changed_ids
                if agent_id in self._connections
            ]
            self._configs = next_configs
            for agent_id in next_configs:
                self._agent_events.setdefault(agent_id, deque(maxlen=100))
            for (agent_id, _), session in self._sessions.items():
                if agent_id in changed_ids:
                    session.loaded = False
                    session.active_prompt = False
                    session.error = "ACP agent configuration changed"
            self._condition.notify_all()
        if connections:
            with self._condition:
                self._retiring_connections.update(connections)
            threading.Thread(
                target=self._close_retiring_connections,
                args=(tuple(connections),),
                daemon=True,
            ).start()

    def connect(self, agent_id: str) -> dict[str, Any]:
        return self._connection(agent_id).connect()

    def disconnect(self, agent_id: str) -> dict[str, Any]:
        connection = self._connections.get(agent_id)
        if connection is not None:
            connection.close()
        with self._condition:
            for (current_agent, _), session in self._sessions.items():
                if current_agent == agent_id:
                    session.loaded = False
                    session.active_prompt = False
        self.publish_agent(agent_id, {"type": "connection", "status": "disconnected"})
        return self._agent_payload(self._config(agent_id))

    def sessions(self, agent_id: str, *, refresh: bool = False) -> dict[str, Any]:
        connection = self._connection(agent_id)
        if refresh and connection.connected:
            try:
                result = connection.request("session/list", {})
                for item in _list_of_dicts(_dict(result).get("sessions")):
                    session_id = str(item.get("sessionId") or item.get("id") or "")
                    if session_id:
                        session = self._ensure_session(agent_id, session_id)
                        session.title = str(
                            item.get("title") or item.get("name") or session.title
                        )
                        session.cwd = str(item.get("cwd") or session.cwd)
            except AcpError as exc:
                if exc.code != -32601:
                    raise
        with self._condition:
            items = [
                session.payload()
                for (current_agent, _), session in self._sessions.items()
                if current_agent == agent_id
            ]
        return {"sessions": items}

    def open_session(
        self, agent_id: str, *, resume_session_id: str | None = None
    ) -> dict[str, Any]:
        connection = self._connection(agent_id)
        connection.connect()
        params = {"cwd": str(self.workspace_root), "mcpServers": []}
        if resume_session_id:
            params["sessionId"] = resume_session_id
            try:
                result = connection.request("session/resume", params)
            except AcpError as exc:
                if exc.code != -32601:
                    raise
                result = connection.request("session/load", params)
            session_id = str(_dict(result).get("sessionId") or resume_session_id)
        else:
            result = connection.request("session/new", params)
            session_id = str(_dict(result).get("sessionId") or "")
        if not session_id:
            raise AcpError("ACP agent did not return a session id")
        result_dict = _dict(result)
        with self._condition:
            session = self._ensure_session(agent_id, session_id)
            session.cwd = str(self.workspace_root)
            session.closed = False
            session.loaded = True
            session.modes = _dict(result_dict.get("modes")) or None
            session.config_options = _list_of_dicts(result_dict.get("configOptions"))
            session.current_mode = _current_mode(session.modes)
        self.publish(
            agent_id,
            session_id,
            {
                "type": "session",
                "status": "resumed" if resume_session_id else "created",
                "session_id": session_id,
            },
        )
        return session.payload()

    def prompt(
        self,
        agent_id: str,
        session_id: str,
        prompt: list[dict[str, Any]],
    ) -> dict[str, Any]:
        connection = self._connected(agent_id)
        prompt = _compatible_prompt_blocks(connection.capabilities, prompt)
        with self._condition:
            session = self._session(agent_id, session_id)
            if session.active_prompt:
                raise AcpError(
                    "this ACP session already has an active prompt", status=409
                )
            if session.closed:
                raise AcpError("ACP session is closed", status=409)
            if not session.loaded:
                raise AcpError("resume the ACP session before prompting", status=409)
            session.active_prompt = True
        user_text = "\n".join(
            str(block.get("text") or "")
            for block in prompt
            if block.get("type") == "text"
        ).strip()
        self.publish(agent_id, session_id, {"type": "user_message", "text": user_text})
        thread = threading.Thread(
            target=self._run_prompt,
            args=(connection, agent_id, session_id, prompt),
            daemon=True,
        )
        thread.start()
        return session.payload()

    def cancel(self, agent_id: str, session_id: str) -> dict[str, Any]:
        connection = self._connected(agent_id)
        session = self._session(agent_id, session_id)
        if session.active_prompt:
            connection.notify("session/cancel", {"sessionId": session_id})
            self.publish(
                agent_id, session_id, {"type": "status", "status": "cancelling"}
            )
        return session.payload()

    def close_session(self, agent_id: str, session_id: str) -> dict[str, Any]:
        connection = self._connected(agent_id)
        session = self._session(agent_id, session_id)
        if session.active_prompt:
            raise AcpError(
                "cancel the active prompt before closing the session", status=409
            )
        try:
            connection.request("session/close", {"sessionId": session_id})
        except AcpError as exc:
            if exc.code != -32601:
                raise
        with self._condition:
            session.closed = True
            session.loaded = False
        self.publish(agent_id, session_id, {"type": "session", "status": "closed"})
        return session.payload()

    def permission(
        self,
        agent_id: str,
        session_id: str,
        request_id: int | str,
        option_id: str | None,
        *,
        cancelled: bool,
    ) -> dict[str, Any]:
        connection = self._connected(agent_id)
        session = self._session(agent_id, session_id)
        if not cancelled and not option_id:
            raise AcpError("option_id is required", status=400)
        connection.respond_permission(request_id, option_id, cancelled=cancelled)
        self.publish(
            agent_id,
            session_id,
            {
                "type": "permission_result",
                "request_id": request_id,
                "option_id": option_id,
                "cancelled": cancelled,
            },
        )
        return session.payload()

    def set_mode(self, agent_id: str, session_id: str, mode_id: str) -> dict[str, Any]:
        result = self._connected(agent_id).request(
            "session/set_mode", {"sessionId": session_id, "modeId": mode_id}
        )
        session = self._session(agent_id, session_id)
        with self._condition:
            session.current_mode = mode_id
        self.publish(agent_id, session_id, {"type": "mode", "mode_id": mode_id})
        return {"session": session.payload(), "result": result}

    def set_config(
        self, agent_id: str, session_id: str, option_id: str, value: Any
    ) -> dict[str, Any]:
        result = self._connected(agent_id).request(
            "session/set_config_option",
            {"sessionId": session_id, "configId": option_id, "value": value},
        )
        self.publish(
            agent_id,
            session_id,
            {"type": "config", "option_id": option_id, "value": value},
        )
        return {
            "session": self._session(agent_id, session_id).payload(),
            "result": result,
        }

    def events(
        self,
        agent_id: str,
        session_id: str,
        *,
        after: int,
        wait: float,
    ) -> dict[str, Any]:
        wait = max(0.0, min(wait, 20.0))
        deadline = time.monotonic() + wait
        with self._condition:
            session = self._session(agent_id, session_id)
            while session.revision <= after and wait > 0 and not self._closed:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(remaining)
            first_revision = (
                session.events[0]["revision"]
                if session.events
                else session.revision + 1
            )
            reset = after < first_revision - 1
            events = (
                list(session.events)
                if reset
                else [
                    event for event in session.events if int(event["revision"]) > after
                ]
            )
            return {
                "session": session.payload(),
                "events": events,
                "revision": session.revision,
                "reset": reset,
            }

    def handle_update(
        self, agent_id: str, session_id: str, update: dict[str, Any]
    ) -> None:
        update_type = str(
            update.get("sessionUpdate") or update.get("type") or "unknown"
        )
        event: dict[str, Any] = {
            "type": _event_type(update_type),
            "update_type": update_type,
        }
        if update_type in {
            "agent_message_chunk",
            "agent_thought_chunk",
            "user_message_chunk",
        }:
            event["text"] = _content_text(update.get("content"))
        elif update_type in {"tool_call", "tool_call_update"}:
            event.update(
                {
                    "tool_call_id": update.get("toolCallId"),
                    "title": update.get("title"),
                    "kind": update.get("kind"),
                    "status": update.get("status"),
                    "locations": update.get("locations"),
                    "content": update.get("content"),
                    "raw_input": update.get("rawInput"),
                    "raw_output": update.get("rawOutput"),
                }
            )
        elif update_type == "plan":
            event["entries"] = update.get("entries") or []
        elif update_type == "available_commands_update":
            event["commands"] = (
                update.get("availableCommands") or update.get("commands") or []
            )
        else:
            event["payload"] = update
        session = self._ensure_session(agent_id, session_id)
        if update_type == "current_mode_update":
            session.current_mode = str(update.get("currentModeId") or "") or None
        if update_type == "config_option_update":
            session.config_options = _list_of_dicts(update.get("configOptions"))
        if update_type == "usage_update":
            session.usage = update
        self.publish(agent_id, session_id, event)

    def publish(self, agent_id: str, session_id: str, event: dict[str, Any]) -> None:
        with self._condition:
            session = self._ensure_session(agent_id, session_id)
            session.revision += 1
            payload = {**event, "revision": session.revision}
            session.events.append(payload)
            self._condition.notify_all()

    def publish_agent(self, agent_id: str, event: dict[str, Any]) -> None:
        with self._condition:
            self._agent_events.setdefault(agent_id, deque(maxlen=100)).append(event)
            self._condition.notify_all()

    def connection_exited(
        self, agent_id: str, return_code: int | None, *, message: str | None = None
    ) -> None:
        message = message or f"ACP agent exited with status {return_code}"
        self.publish_agent(agent_id, {"type": "error", "message": message})
        with self._condition:
            sessions = [
                item
                for (current_agent, _), item in self._sessions.items()
                if current_agent == agent_id
            ]
            for session in sessions:
                session.active_prompt = False
                session.loaded = False
                session.error = message
                self.publish(
                    agent_id, session.session_id, {"type": "error", "message": message}
                )

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()
            connections = list(
                {*self._connections.values(), *self._retiring_connections}
            )
        for connection in connections:
            connection.close()

    def _close_retiring_connections(self, connections: tuple[_Connection, ...]) -> None:
        try:
            for connection in connections:
                connection.close()
        finally:
            with self._condition:
                self._retiring_connections.difference_update(connections)
                self._condition.notify_all()

    def _run_prompt(
        self,
        connection: _Connection,
        agent_id: str,
        session_id: str,
        prompt: list[dict[str, Any]],
    ) -> None:
        try:
            result = connection.request(
                "session/prompt",
                {"sessionId": session_id, "prompt": prompt},
                timeout=PROMPT_TIMEOUT_SECONDS,
            )
            self.publish(
                agent_id,
                session_id,
                {
                    "type": "prompt_complete",
                    "stop_reason": _dict(result).get("stopReason"),
                    "result": result,
                },
            )
        except AcpError as exc:
            session = self._session(agent_id, session_id)
            session.error = str(exc)
            self.publish(agent_id, session_id, {"type": "error", "message": str(exc)})
        finally:
            with self._condition:
                self._session(agent_id, session_id).active_prompt = False
                self._condition.notify_all()

    def _agent_payload(self, config: AcpAgent) -> dict[str, Any]:
        connection = self._connections.get(config.id)
        if connection is None:
            return {
                "id": config.id,
                "title": config.title,
                "connected": False,
                "protocol_version": None,
                "protocol_revision": None,
                "agent_info": {},
                "capabilities": {},
                "auth_methods": [],
                "stderr_tail": [],
            }
        return connection.payload()

    def _config(self, agent_id: str) -> AcpAgent:
        config = self._configs.get(agent_id)
        if config is None:
            raise AcpError("unknown ACP agent", status=404)
        return config

    def _connection(self, agent_id: str) -> _Connection:
        config = self._config(agent_id)
        with self._condition:
            if self._closed:
                raise AcpError("ACP runtime is closed", status=409)
            connection = self._connections.get(agent_id)
            if connection is None:
                connection = _Connection(self, config, self.workspace_root)
                self._connections[agent_id] = connection
            return connection

    def _connected(self, agent_id: str) -> _Connection:
        connection = self._connection(agent_id)
        if not connection.connected:
            raise AcpError("ACP agent is not connected", status=409)
        return connection

    def _ensure_session(self, agent_id: str, session_id: str) -> _Session:
        if not session_id:
            raise AcpError("ACP event is missing sessionId")
        key = (agent_id, session_id)
        with self._condition:
            session = self._sessions.pop(key, None)
            if session is None:
                if len(self._sessions) >= SESSION_LIMIT:
                    evictable = next(
                        (
                            current_key
                            for current_key, current in self._sessions.items()
                            if current.closed and not current.active_prompt
                        ),
                        None,
                    )
                    if evictable is None:
                        evictable = next(
                            (
                                current_key
                                for current_key, current in self._sessions.items()
                                if not current.loaded and not current.active_prompt
                            ),
                            None,
                        )
                    if evictable is None:
                        evictable = next(
                            (
                                current_key
                                for current_key, current in self._sessions.items()
                                if not current.active_prompt
                            ),
                            None,
                        )
                    if evictable is None:
                        raise AcpError("ACP session limit reached", status=429)
                    self._sessions.pop(evictable)
                session = _Session(agent_id=agent_id, session_id=session_id)
            self._sessions[key] = session
            return session

    def _session(self, agent_id: str, session_id: str) -> _Session:
        session = self._sessions.get((agent_id, session_id))
        if session is None:
            raise AcpError("unknown ACP session", status=404)
        return session


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _rpc_id(value: Any) -> int | str:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise AcpError("ACP message id must be a string or integer")
    return value


def _bounded_readline(stream: Any, limit: int) -> tuple[bytes, bool]:
    raw = stream.readline(limit + 1)
    if not raw:
        return b"", False
    if len(raw) <= limit:
        return raw, False
    while raw and not raw.endswith(b"\n"):
        raw = stream.readline(limit + 1)
    return b"", True


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            return


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _current_mode(modes: dict[str, Any] | None) -> str | None:
    if not modes:
        return None
    value = modes.get("currentModeId")
    return str(value) if value is not None else None


def _content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("text") or value.get("content") or "")
    return ""


def _event_type(update_type: str) -> str:
    return {
        "agent_message_chunk": "message",
        "agent_thought_chunk": "thought",
        "user_message_chunk": "user_message",
        "tool_call": "tool",
        "tool_call_update": "tool",
        "plan": "plan",
        "available_commands_update": "commands",
        "current_mode_update": "mode",
        "config_option_update": "config",
        "usage_update": "usage",
    }.get(update_type, "unknown")


def _compatible_prompt_blocks(
    capabilities: dict[str, Any], blocks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    prompt_capabilities = _dict(capabilities.get("promptCapabilities"))
    if prompt_capabilities.get("embeddedContext") is True:
        return blocks
    compatible: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("type") != "resource":
            compatible.append(block)
            continue
        resource = _dict(block.get("resource"))
        text = str(resource.get("text") or "")
        if text:
            compatible.append(
                {
                    "type": "text",
                    "text": f"\n\n[Attached evaluation context: {resource.get('uri') or 'peval'}]\n{text}",
                }
            )
    return compatible


__all__ = ["ACP_V2_REVISION", "AcpError", "AcpManager"]
