"""Run an explicitly configured ACP Agent in a native Harbor Host."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path
from uuid import uuid4

from harbor.agents.base import BaseAgent
from harbor.agents.installed.base import NonZeroAgentExitCodeError
from harbor.models.task.config import TaskOS

from . import __version__
from .acp_evidence import convert
from .acp_protocol import (
    DEFAULT_MAX_EVIDENCE_BYTES,
    FORCED_CLEANUP_RESERVE_SEC,
    MAX_CONFIG_ID_BYTES,
    MAX_CONFIG_OPTIONS,
    MAX_CONFIG_VALUE_BYTES,
    verify_evidence,
)
from .environment import HostEnvironment, _await_owned_task
from .inference_telemetry import populate_context_from_trajectory


class HostACPAgent(BaseAgent):
    SUPPORTS_ATIF = True
    SUPPORTS_RESUME = True
    SUPPORTS_WINDOWS = True
    _supports_skills = False

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
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if (
            not isinstance(argv, list)
            or not argv
            or any(not isinstance(arg, str) or "\0" in arg for arg in argv)
            or not argv[0]
        ):
            raise ValueError(
                "ACP argv requires an executable and NUL-free string arguments"
            )
        if self.skills_dir and not self._supports_skills:
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
        if type(max_evidence_bytes) is not int or max_evidence_bytes <= 0:
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
        return "psycheval-host-acp"

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

    async def run(self, instruction, environment, context):
        await self._invoke("run", instruction, environment)

    async def resume(self, instruction, environment, context):
        await self._invoke("resume", instruction, environment)

    async def _invoke(self, action, instruction, environment):
        if self._invoking:
            raise RuntimeError("ACP invocation is already active")
        self._invoking = True
        try:
            return await self._run_invocation(action, instruction, environment)
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
        host = self._host(environment)
        if self._setup_host is not host:
            raise RuntimeError("ACP invocation requires its original configured Host")
        self._check_runtime(host)
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
            "tool_result_format": self.tool_result_format,
        }
        config_path = invocation / "request.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
        result = None
        try:
            result = await host.exec_argv(
                [sys.executable, "-m", f"{__package__}.acp_harness", str(config_path)],
                **(
                    {"termination_grace_sec": self.shutdown_timeout_sec + 5}
                    if host.os == TaskOS.LINUX
                    else {}
                ),
            )
        finally:
            await _await_owned_task(
                asyncio.create_task(asyncio.to_thread(self._publish_call, invocation))
            )
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
                not summary.get("cleanup_complete")
                or not summary.get("inspection_complete")
                or summary.get("error_type")
            ):
                raise RuntimeError("ACP inspection failed; see current Agent evidence")
            verify_evidence(self.logs_dir, summary)
            return summary
        if not summary.get("cleanup_complete") or not summary.get("prompt_submitted"):
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
        trajectory_path = self.logs_dir / "trajectory.json"
        trajectory_path.unlink(missing_ok=True)
        path = self.logs_dir / "acp.summary.json"
        summary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if (
            not self._invocation_id
            or summary.get("invocation_id") != self._invocation_id
            or not summary.get("cleanup_complete")
            or not summary.get("prompt_submitted")
            or summary.get("model_mismatch")
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
