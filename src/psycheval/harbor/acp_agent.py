"""Run an explicitly configured ACP Agent in a native Harbor Host."""

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import json
import math
import shutil
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from harbor.agents.base import BaseAgent
from harbor.agents.capabilities import AgentCapabilities
from harbor.agents.installed.base import NonZeroAgentExitCodeError
from harbor.models.task.config import TaskOS

from . import __version__
from .acp_evidence import convert, recover
from .acp_protocol import (
    DEFAULT_MAX_EVIDENCE_BYTES,
    FORCED_CLEANUP_RESERVE_SEC,
    MAX_CONFIG_ID_BYTES,
    MAX_CONFIG_OPTIONS,
    MAX_CONFIG_VALUE_BYTES,
    MAX_EVENT_FRAME,
    EvidenceReader,
    verify_evidence,
)
from .diagnostics import PARTIAL_TRAJECTORY, warning_text, write_partial
from .environment import HostEnvironment, _await_owned_task
from .inference_telemetry import populate_context_from_trajectory

SessionUpdateCallback = Callable[[dict[str, Any]], None | Awaitable[None]]
_UPDATE_POLL_SEC = 0.05
# Poll the already-flushed evidence file portably, without watcher dependencies.
_UPDATE_CALLBACK_TIMEOUT_SEC = 5.0
_UPDATE_DRAIN_TIMEOUT_SEC = 5.0
_UPDATE_READ_BYTES = 64 * 1024


class _SessionUpdateRelay:
    """Observe flushed wire records without entering the evidence trust path."""

    def __init__(
        self,
        path,
        callback,
        logger,
        maximum=DEFAULT_MAX_EVIDENCE_BYTES,
        decoded_maximum=None,
    ):
        self.path, self.callback, self.logger = path, callback, logger
        self.maximum, self.decoded_maximum = maximum, decoded_maximum
        self.finished = asyncio.Event()
        self.warned = False
        self.task = asyncio.create_task(self._run())

    def _warn(self, error):
        if not self.warned:
            self.warned = True
            self.logger.warning("ACP session update observer disabled (%s)", error)

    async def _deliver(self, record):
        if record["direction"] != "receive" or record["phase"] != "prompt":
            return
        message = record["message"]
        if message.get("method") != "session/update":
            return
        result = self.callback(message["params"]["update"])
        if inspect.isawaitable(result):
            async with asyncio.timeout(_UPDATE_CALLBACK_TIMEOUT_SEC):
                await result
        elif result is not None:
            raise TypeError("session update callback must return None or an awaitable")

    async def _follow(self):
        stream = None
        pending = bytearray()
        try:
            while True:
                if stream is None:
                    try:
                        stream = EvidenceReader(
                            self.path, self.maximum, self.decoded_maximum
                        )
                    except FileNotFoundError:
                        pass
                if stream is not None and (chunk := stream.read(_UPDATE_READ_BYTES)):
                    pending.extend(chunk)
                    while (end := pending.find(b"\n")) >= 0:
                        if end + 1 > MAX_EVENT_FRAME:
                            raise ValueError("oversized ACP observer record")
                        record = json.loads(pending[:end])
                        del pending[: end + 1]
                        await self._deliver(record)
                    if len(pending) >= MAX_EVENT_FRAME:
                        raise ValueError("oversized ACP observer record")
                    await asyncio.sleep(0)
                    continue
                if self.finished.is_set():
                    if stream is not None:
                        stream.finish()
                    if pending:
                        raise ValueError("incomplete ACP observer record")
                    return
                try:
                    await asyncio.wait_for(self.finished.wait(), _UPDATE_POLL_SEC)
                except TimeoutError:
                    pass
        finally:
            if stream is not None:
                stream.close()

    async def _run(self):
        try:
            await self._follow()
        except (Exception, asyncio.CancelledError) as error:
            # This task is separately owned; callback cancellation stays here.
            self._warn(type(error).__name__)

    async def finish(self):
        self.finished.set()
        if self.task.cancelled():
            self._warn("CancelledError")
            return
        try:
            async with asyncio.timeout(_UPDATE_DRAIN_TIMEOUT_SEC):
                await asyncio.shield(self.task)
        except TimeoutError:
            self._warn("TimeoutError")
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)


class HostACPAgent(BaseAgent):
    capabilities = AgentCapabilities(
        atif=True, resume=True, windows=True, mcp_servers=True
    )

    def __init__(
        self,
        *args,
        argv=None,
        config_dir=None,
        config_options=None,
        authenticate_method_id=None,
        permission_mode="allow",
        tool_result_format="acp",
        handshake_timeout_sec=60.0,
        shutdown_timeout_sec=45.0,
        max_evidence_bytes=DEFAULT_MAX_EVIDENCE_BYTES,
        max_decoded_evidence_bytes=None,
        on_session_update: SessionUpdateCallback | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if on_session_update is not None and not callable(on_session_update):
            raise ValueError("ACP on_session_update must be callable or None")
        self._on_session_update = on_session_update
        if (
            not isinstance(argv, list)
            or not argv
            or any(not isinstance(arg, str) or "\0" in arg for arg in argv)
            or not argv[0]
        ):
            raise ValueError(
                "ACP argv requires an executable and NUL-free string arguments"
            )
        if self.skills_dir and not self.capabilities.skills:
            raise ValueError("This ACP Agent does not support Skills")
        if self.load_trajectory:
            raise ValueError("ACP Agents do not support trajectory import")
        if permission_mode not in {"allow", "deny"} or tool_result_format not in {
            "acp",
            "rsiversi",
            "codebuddy",
        }:
            raise ValueError("unsupported ACP permission mode or result format")
        config_options = {} if config_options is None else config_options
        if (
            not isinstance(config_options, dict)
            or len(config_options) > MAX_CONFIG_OPTIONS
            or any(
                not isinstance(key, str)
                or not key
                or len(key.encode()) > MAX_CONFIG_ID_BYTES
                or "\0" in key
                or (
                    type(value) is not bool
                    and (
                        not isinstance(value, str)
                        or not value
                        or len(value.encode()) > MAX_CONFIG_VALUE_BYTES
                        or "\0" in value
                    )
                )
                for key, value in config_options.items()
            )
        ):
            raise ValueError(
                "ACP config_options requires bounded exact select or boolean assignments"
            )
        for value in (handshake_timeout_sec, shutdown_timeout_sec):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError("ACP timeouts must be finite and positive")
        if shutdown_timeout_sec <= FORCED_CLEANUP_RESERVE_SEC:
            raise ValueError("ACP shutdown budget must exceed five seconds")
        if max_decoded_evidence_bytes is None:
            max_decoded_evidence_bytes = max_evidence_bytes
        if any(
            type(n) is not int or n <= 0
            for n in (max_evidence_bytes, max_decoded_evidence_bytes)
        ):
            raise ValueError("ACP evidence byte budget must be a positive integer")
        if authenticate_method_id is not None and (
            not isinstance(authenticate_method_id, str)
            or not authenticate_method_id
            or "\0" in authenticate_method_id
        ):
            raise ValueError("invalid ACP authentication method")
        self.argv, self.config_options = list(argv), dict(config_options)
        self.config_dir = (
            Path(config_dir).absolute() if config_dir is not None else None
        )
        self.authenticate_method_id, self.permission_mode = (
            authenticate_method_id,
            permission_mode,
        )
        self.tool_result_format = tool_result_format
        self.max_evidence_bytes = max_evidence_bytes
        self.max_decoded_evidence_bytes = max_decoded_evidence_bytes
        self.handshake_timeout_sec, self.shutdown_timeout_sec = (
            handshake_timeout_sec,
            shutdown_timeout_sec,
        )
        self._runtime_id = uuid4().hex
        self._state = None
        self._setup_host = None
        self._instruction = ""
        self._invocation_id = None
        self._invoking = False
        self._agent_metadata = {}

    @staticmethod
    def name():
        return "acp"

    def version(self):
        return __version__

    @staticmethod
    def _host(environment):
        if not isinstance(environment, HostEnvironment) or environment.os not in {
            TaskOS.LINUX,
            TaskOS.WINDOWS,
        }:
            raise TypeError(
                "HostACPAgent requires a native Linux or Windows HostEnvironment"
            )
        return environment

    async def setup(self, environment):
        host = self._host(environment)
        if self._setup_host is not None:
            if self._setup_host is not host:
                raise RuntimeError("ACP state belongs to a different Host")
            self._check_runtime(host)
            return
        if sys.version_info >= (3, 15) or importlib.util.find_spec("acp") is None:
            raise RuntimeError(
                "HostACPAgent requires agent-client-protocol==0.12.1 and Python 3.12-3.14"
            )
        executable = shutil.which(self.argv[0])
        if executable is None:
            raise FileNotFoundError(
                "ACP executable is unavailable; install it before evaluation"
            )
        self.argv[0] = executable
        self._state = host.runtime_directory(f"acp-state-{self._runtime_id}")
        paths = {
            key: self._state / child
            for key, child in (
                ("HOME", "home"),
                ("XDG_CONFIG_HOME", "config"),
                ("XDG_DATA_HOME", "data"),
                ("XDG_STATE_HOME", "state"),
                ("XDG_CACHE_HOME", "cache"),
            )
        }
        runtime = host.runtime_directory(
            f"acp-runtime-{self._runtime_id}", short_path=host.os == TaskOS.LINUX
        )
        if host.os == TaskOS.LINUX and len(str(runtime).encode()) > 28:
            raise RuntimeError("ACP XDG runtime exceeds the RSIversi socket budget")
        paths["XDG_RUNTIME_DIR"] = runtime
        if host.os == TaskOS.WINDOWS:
            paths.update(
                USERPROFILE=paths["HOME"],
                APPDATA=paths["HOME"] / "AppData/Roaming",
                LOCALAPPDATA=paths["HOME"] / "AppData/Local",
            )
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
        self._child_env = {key: str(path) for key, path in paths.items()}
        if self.config_dir is not None:
            for source in [self.config_dir, *self.config_dir.parents]:
                if source.is_symlink():
                    raise ValueError("ACP config seed traverses a link")
            if not self.config_dir.is_dir():
                raise ValueError("ACP config seed must be a directory")
            for source in self.config_dir.rglob("*"):
                if source.is_symlink():
                    raise ValueError("ACP config seed contains a link")
            await _await_owned_task(
                asyncio.create_task(
                    asyncio.to_thread(
                        shutil.copytree,
                        self.config_dir,
                        paths["XDG_CONFIG_HOME"],
                        dirs_exist_ok=True,
                    )
                )
            )
        self._setup_host = host

    def _check_runtime(self, host):
        if (
            self._state is None
            or not self._state.is_dir()
            or host.runtime_directory(f"acp-state-{self._runtime_id}") != self._state
            or not Path(self._child_env["XDG_RUNTIME_DIR"]).is_dir()
        ):
            raise RuntimeError(
                "ACP Host runtime was deleted or replaced; create a new Agent"
            )

    def _invocation_host(self, environment):
        host = self._host(environment)
        if self._setup_host is not host:
            raise RuntimeError("ACP invocation requires its original configured Host")
        self._check_runtime(host)
        return host

    async def run(self, instruction, environment, context):
        await self._invoke("run", instruction, environment)

    async def resume(self, instruction, environment, context):
        await self._invoke("resume", instruction, environment)

    async def _invoke(self, action, instruction, environment):
        if self._invoking:
            raise RuntimeError("ACP invocation is already active")
        self._invoking = True
        self._execution_error = None
        self._invocation_id = None
        try:
            for filename in ("trajectory.json", PARTIAL_TRAJECTORY):
                (self.logs_dir / filename).unlink(missing_ok=True)
            return await self._run_invocation(action, instruction, environment)
        except BaseException as error:
            self._execution_error = error
            self._retain_partial()
            raise
        finally:
            self._invoking = False

    async def _run_invocation(self, action, instruction, environment):
        self._instruction = instruction
        self._invocation_id = uuid4().hex
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        for path in self.logs_dir.glob("acp.*"):
            if path.is_file():
                path.unlink()
        (self.logs_dir / "trajectory.json").unlink(missing_ok=True)
        (self.logs_dir / "trajectory.tmp").unlink(missing_ok=True)
        (self.logs_dir / PARTIAL_TRAJECTORY).unlink(missing_ok=True)
        host = self._invocation_host(environment)
        invocation = host.runtime_directory(f"acp-call-{self._runtime_id}")
        for path in invocation.glob("acp.*"):
            if path.is_file():
                path.unlink()
        (invocation / "instruction.txt").write_text(instruction, encoding="utf-8")
        config = {
            "invocation_id": self._invocation_id,
            "argv": self.argv,
            "action": action,
            "cwd": str(host.work_dir),
            "state": str(self._state),
            "child_env": self._child_env,
            "config_options": self.config_options,
            "mcp_servers": [
                server.model_dump(mode="json", exclude_none=True)
                for server in self.mcp_servers
            ],
            "authenticate_method_id": self.authenticate_method_id,
            "permission_mode": self.permission_mode,
            "handshake_timeout_sec": self.handshake_timeout_sec,
            "shutdown_timeout_sec": self.shutdown_timeout_sec,
            "max_evidence_bytes": self.max_evidence_bytes,
            "max_decoded_evidence_bytes": self.max_decoded_evidence_bytes,
            "tool_result_format": self.tool_result_format,
        }
        config_path = invocation / "request.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
        relay = (
            _SessionUpdateRelay(
                invocation / "acp.events.ndjson.gz",
                self._on_session_update,
                self.logger,
                self.max_evidence_bytes,
                self.max_decoded_evidence_bytes,
            )
            if self._on_session_update is not None
            else None
        )

        async def publish():
            if relay is not None:
                await relay.finish()
            await asyncio.to_thread(self._publish_call, invocation)

        result = None
        primary_error = None
        try:
            result = await host.exec_argv(
                [sys.executable, "-m", f"{__package__}.acp_harness", str(config_path)],
                **(
                    {"termination_grace_sec": self.shutdown_timeout_sec + 5}
                    if host.os == TaskOS.LINUX
                    else {}
                ),
            )
        except BaseException as error:
            primary_error = error
            raise
        finally:
            try:
                await _await_owned_task(asyncio.create_task(publish()))
            except BaseException as error:
                if primary_error is None:
                    raise
                primary_error.add_note(
                    f"ACP publication cleanup failed: {type(error).__name__}"
                )
            if primary_error is not None:
                self._retain_partial()
        summary_path = self.logs_dir / "acp.summary.json"
        try:
            summary = (
                json.loads(summary_path.read_text(encoding="utf-8"))
                if summary_path.exists()
                else {}
            )
        except (OSError, ValueError):
            self._retain_harness_diagnostics(result)
            raise
        if (
            not isinstance(summary, dict)
            or summary.get("invocation_id") != self._invocation_id
        ):
            self._retain_harness_diagnostics(result)
            raise RuntimeError(
                "ACP setup or cleanup failed; see current Agent evidence"
            )
        if action == "inspect":
            if (
                not self._cleanup_admitted(summary)
                or not summary.get("inspection_complete")
                or summary.get("error_type")
            ):
                raise RuntimeError("ACP inspection failed; see current Agent evidence")
            verify_evidence(self.logs_dir, summary)
            return summary
        if not self._cleanup_admitted(summary) or not summary.get("prompt_submitted"):
            raise RuntimeError(
                "ACP setup or cleanup failed; see current Agent evidence"
            )
        verify_evidence(self.logs_dir, summary)
        if result.return_code != 0:
            raise NonZeroAgentExitCodeError(
                "ACP prompt failed after cleanup; see current Agent evidence"
            )

    def _retain_harness_diagnostics(self, result):
        # An early harness failure has no wire budget or summary. Bound these
        # diagnostic tails separately, prioritizing the traceback on stderr.
        remaining = self.max_evidence_bytes
        for name, value in (("stderr", result.stderr), ("stdout", result.stdout)):
            encoded = (value or "").encode("utf-8", errors="replace")
            tail = encoded[-remaining:] if remaining else b""
            tail = tail.decode("utf-8", errors="ignore").encode("utf-8")
            (self.logs_dir / f"acp.harness.{name}.log").write_bytes(tail)
            remaining -= len(tail)

    def _publish_call(self, invocation):
        for source in sorted(
            invocation.glob("acp.*"), key=lambda path: path.name == "acp.summary.json"
        ):
            if source.is_file() and not source.is_symlink():
                shutil.move(source, self.logs_dir / source.name)
        for name in ("request.json", "instruction.txt"):
            (invocation / name).unlink(missing_ok=True)

    def populate_context_post_run(self, context):
        try:
            self._populate_context(context)
        except Exception as error:
            self._retain_partial()
            primary = getattr(self, "_execution_error", None)
            if (
                primary is not None
                and getattr(self._setup_host, "os", None) == TaskOS.WINDOWS
            ):
                primary.add_note(
                    f"ACP post-run evidence unavailable: {type(error).__name__}"
                )
                context.metadata = {
                    **(context.metadata or {}),
                    "trajectory_error": type(error).__name__,
                }
                self.logger.warning(
                    "ACP post-run evidence unavailable (%s): %s",
                    type(error).__name__,
                    self.logs_dir,
                )
                return
            raise

    @staticmethod
    def _cleanup_admitted(summary):
        return summary.get("cleanup_complete") or summary.get("host_os") == "windows"

    def _retain_partial(self):
        if not self._invocation_id or (self.logs_dir / PARTIAL_TRAJECTORY).exists():
            return
        try:
            path = self.logs_dir / "acp.summary.json"
            summary = (
                json.loads(path.read_text(encoding="utf-8"))
                if path.exists()
                else {
                    "max_evidence_bytes": self.max_evidence_bytes,
                    "max_decoded_evidence_bytes": self.max_decoded_evidence_bytes,
                }
            )
            if summary.get("invocation_id", self._invocation_id) != self._invocation_id:
                return
            trajectory = recover(
                self.logs_dir,
                summary,
                self._instruction,
                {
                    "name": self.name(),
                    "version": self.version(),
                    "model_name": self.model_name,
                },
                self.tool_result_format,
            )
            write_partial(self.logs_dir, trajectory, "acp.events.ndjson.gz")
        except Exception as error:
            self.logger.warning(
                "ACP diagnostic trajectory unavailable (%s): %s",
                type(error).__name__,
                self.logs_dir,
            )

    def _populate_context(self, context):
        trajectory_path = self.logs_dir / "trajectory.json"
        trajectory_path.unlink(missing_ok=True)
        path = self.logs_dir / "acp.summary.json"
        summary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if (
            not self._invocation_id
            or summary.get("invocation_id") != self._invocation_id
            or not self._cleanup_admitted(summary)
            or not summary.get("prompt_submitted")
            or summary.get("model_mismatch")
            or summary.get("evidence_error_type")
        ):
            raise RuntimeError(
                "ACP invocation is unsafe to verify; see current Agent evidence"
            )
        trajectory = convert(
            self.logs_dir,
            summary,
            self._instruction,
            {
                "name": self.name(),
                "version": self.version(),
                "model_name": self.model_name,
                "extra": self._agent_metadata,
            },
            self.tool_result_format,
        )
        if trajectory is None:
            raise RuntimeError("ACP prompt evidence did not yield a trajectory")
        trajectory = self._enrich_trajectory(trajectory, summary)
        data = trajectory.to_json_dict()
        temporary = trajectory_path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
        temporary.replace(trajectory_path)
        populate_context_from_trajectory(context, data)
        context.metadata = {
            **(context.metadata or {}),
            "acp_session_id": summary.get("session_id"),
            "acp_stop_reason": summary.get("stop_reason"),
        }
        if warnings := summary.get("cleanup_warnings"):
            context.metadata["cleanup_warnings"] = warnings
            for warning in warnings:
                self.logger.warning(warning_text(warning))

    def _enrich_trajectory(self, trajectory, summary):
        return trajectory
