"""Run a preinstalled OpenCode 2 CLI on a native HostEnvironment."""

from __future__ import annotations

import asyncio
import copy
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from time import monotonic
from typing import override
from uuid import uuid4

from harbor.agents.capabilities import AgentCapabilities
from harbor.agents.installed.base import NonZeroAgentExitCodeError
from harbor.agents.installed.opencode import OpenCode, OpenCodeOptions
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.trajectories import Trajectory
from pydantic import field_validator

from ..diagnostics import PARTIAL_TRAJECTORY, write_partial
from ..environment import HostEnvironment, _await_owned_task
from ..family import MAX_DEPTH, MAX_MEMBERS
from ..inference_telemetry import (
    populate_context_from_trajectory,
)
from ..measurements import MAX_EVENT_BYTES, unavailable_marker
from .dsh_measurements import bounded_records
from .sessions.opencode_native import native_events_to_trajectory, native_session_events

_STDIN_LAUNCHER = (
    "import subprocess,sys; "
    "f=open(sys.argv[1],'rb'); "
    "sys.exit(subprocess.call(sys.argv[2:],stdin=f))"
)

MAX_FAMILY_EXPORT_BYTES = 128 * 1024 * 1024
MAX_FAMILY_EXPORT_SECONDS = 30


class _FamilyExportByteLimit(ValueError):
    pass


def _json_size(value):
    return sum(
        len(chunk.encode("utf-8"))
        for chunk in json.JSONEncoder(
            ensure_ascii=False, separators=(",", ":")
        ).iterencode(value)
    )


class HostOpenCodeOptions(OpenCodeOptions):
    executable: str = "opencode"
    websearch_provider: str | None = "random"

    @field_validator("websearch_provider", mode="before")
    @classmethod
    def validate_websearch_provider(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise ValueError("websearch_provider must be nonempty and NUL-free")
        return value.strip()

    @field_validator("opencode_config", mode="before")
    @classmethod
    def validate_config(cls, value):
        if value is None:
            return value
        if not isinstance(value, dict):
            raise ValueError("opencode_config must be an object")
        for section in ("skills", "mcp", "provider", "websearch"):
            if section in value and not isinstance(value[section], dict):
                raise ValueError(f"opencode_config.{section} must be an object")
        paths = value.get("skills", {}).get("paths", [])
        if not isinstance(paths, list) or any(
            not isinstance(path, str) for path in paths
        ):
            raise ValueError("opencode_config.skills.paths must be a list of strings")
        return value

    @field_validator("executable")
    @classmethod
    def validate_executable(cls, value: str) -> str:
        if not value or "\x00" in value:
            raise ValueError("OpenCode executable must be nonempty and NUL-free")
        return value

    @field_validator("disable_web_search")
    @classmethod
    def reject_web_search_override(cls, value: bool) -> bool:
        if value:
            raise ValueError(
                "HostOpenCodeAgent does not support disable_web_search=True"
            )
        return value


class HostOpenCodeAgent(OpenCode):
    """Reuse Harbor's OpenCode trajectory conversion without its Bash installer."""

    capabilities = AgentCapabilities(
        atif=True, windows=True, skills=True, mcp_servers=True
    )
    options_model = HostOpenCodeOptions
    options: HostOpenCodeOptions

    def __init__(
        self,
        *args,
        executable: str = "opencode",
        opencode_config: dict | None = None,
        **kwargs,
    ):
        self._trajectory = None
        super().__init__(
            *args, executable=executable, opencode_config=opencode_config, **kwargs
        )
        if not self.model_name or "/" not in self.model_name:
            raise ValueError("Model name must be in the format provider/model_name")
        self.executable = executable
        self._runtime_id = uuid4().hex
        self._websearch_provider_disabled = False

    @staticmethod
    def _host(environment: BaseEnvironment) -> HostEnvironment:
        if not isinstance(environment, HostEnvironment):
            raise TypeError("HostOpenCodeAgent requires HostEnvironment")
        return environment

    @override
    async def setup(self, environment: BaseEnvironment) -> None:
        host = self._host(environment)
        executable = shutil.which(self.executable)
        if executable is None:
            raise FileNotFoundError(f"Install OpenCode first: {self.executable}")
        self.executable = executable
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        env = self._runtime_env(host)
        with (self.logs_dir / "opencode-setup.log").open("w", encoding="utf-8") as log:

            async def capture(text: str, stream: str) -> None:
                log.write(text)
                log.flush()

            try:
                for attempt in range(2):
                    with (
                        host.scoped_exec_env(env),
                        host.scoped_output_callback(capture),
                    ):
                        result = await host.exec_argv(
                            [executable, "--version"], env=env, timeout_sec=30
                        )
                    if result.return_code == 0 and (result.stdout or "").strip():
                        break
                    fallback = self._fallback_env(env) if attempt == 0 else None
                    if fallback is None:
                        raise RuntimeError("OpenCode version probe failed")
                    log.write(
                        "\nRetrying OpenCode version probe without websearch.provider.\n"
                    )
                    log.flush()
                    env = fallback
            except TimeoutError as exc:
                raise RuntimeError(
                    "OpenCode version probe exceeded its 30-second timeout; "
                    "see opencode-setup.log"
                ) from exc
        installed = (result.stdout or "").strip()
        if self._version is not None and self._version != installed:
            raise RuntimeError(
                f"OpenCode version mismatch: expected {self._version}, got {installed}"
            )
        self._version = installed

    def _runtime_env(self, host: HostEnvironment) -> dict[str, str]:
        root = host.runtime_directory(f"opencode-{self._runtime_id}")
        connection = self.model_connection
        env = {**connection.env, **self.extra_env}
        for key, child in (
            ("HOME", "home"),
            ("USERPROFILE", "home"),
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_DATA_HOME", "data"),
            ("XDG_STATE_HOME", "state"),
            ("XDG_CACHE_HOME", "cache"),
            ("OPENCODE_CONFIG_DIR", "config/opencode"),
        ):
            path = root / child
            path.mkdir(parents=True, exist_ok=True)
            env[key] = str(path)
        config_path = root / "config/opencode/opencode.json"
        config_path.write_text("{}\n", encoding="utf-8")
        env["OPENCODE_CONFIG"] = str(config_path)
        provider, model = self.model_name.split("/", 1)
        provider_config = {"models": {model: {}}}
        if connection.configured_base_url and provider in {"openai", "anthropic"}:
            provider_config["options"] = {"baseURL": connection.configured_base_url}
        config = {
            "autoupdate": False,
            "share": "disabled",
            "snapshot": False,
            "permission": "allow",
            "provider": {provider: provider_config},
        }
        if self.options.websearch_provider is not None:
            config["websearch"] = {"provider": self.options.websearch_provider}
        for server in self.mcp_servers:
            if server.transport == "stdio":
                value = {
                    "type": "local",
                    "command": [server.command, *server.args],
                }
            else:
                value = {"type": "remote", "url": server.url}
            config.setdefault("mcp", {})[server.name] = value
        self._deep_merge(config, copy.deepcopy(self._opencode_config))
        plugin = root / "measurement-plugin"
        plugin.mkdir(exist_ok=True)
        shutil.copyfile(
            Path(__file__).with_name("opencode_measurements.mjs"), plugin / "index.mjs"
        )
        (plugin / "package.json").write_text(
            json.dumps(
                {
                    "name": "peval-measurements",
                    "type": "module",
                    "exports": {".": "./index.mjs"},
                }
            ),
            encoding="utf-8",
        )
        config.setdefault("plugins", []).append(plugin.as_uri())
        self._measurement_path = root / "measurement-observer.ndjson"
        env["PEVAL_OPENCODE_MEASUREMENTS"] = str(self._measurement_path)
        if self.skills_dir:
            config.setdefault("skills", {}).setdefault("paths", []).append(
                str(host.native_path(self.skills_dir))
            )
        if self._websearch_provider_disabled:
            self._remove_websearch_provider(config)
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config, ensure_ascii=False)
        return env

    @staticmethod
    def _remove_websearch_provider(config: dict) -> bool:
        websearch = config.get("websearch", {})
        if "provider" not in websearch:
            return False
        del websearch["provider"]
        if not websearch:
            del config["websearch"]
        return True

    def _fallback_env(self, env: dict[str, str]) -> dict[str, str] | None:
        config = json.loads(env["OPENCODE_CONFIG_CONTENT"])
        if not self._remove_websearch_provider(config):
            return None
        self._websearch_provider_disabled = True
        return {
            **env,
            "OPENCODE_CONFIG_CONTENT": json.dumps(config, ensure_ascii=False),
        }

    @override
    def _parse_stdout(self, *, diagnostic=False) -> list[dict]:
        path = self.logs_dir / "opencode.txt"
        if not path.is_file():
            return []
        events = []
        with path.open(encoding="utf-8") as output:
            for line in output:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    if diagnostic and line.lstrip().startswith("{"):
                        break
                    continue
                if isinstance(event, dict):
                    events.append(event)
        return events

    def _session_events(
        self, streamed=None, *, filename="opencode-session.json", diagnostic=False
    ):
        path = self.logs_dir / filename
        if not path.is_file():
            return []
        exported = json.loads(path.read_text(encoding="utf-8"))
        self._family_export = exported if isinstance(exported, dict) else {}
        return native_session_events(
            exported,
            streamed=self._parse_stdout() if streamed is None else streamed,
            model_name=self.model_name,
            diagnostic=diagnostic,
        )

    @override
    def _convert_events_to_trajectory(self, events: list[dict]) -> Trajectory | None:
        trajectory = native_events_to_trajectory(
            events,
            model_name=self.model_name,
            instruction=getattr(self, "_instruction", ""),
            version=self.version(),
        )
        if trajectory is not None:
            from .sessions.opencode_native import retain_export_family

            data = retain_export_family(
                trajectory.to_json_dict(),
                getattr(self, "_family_export", {}),
                version=self.version(),
            )
            trajectory = Trajectory.model_validate(data)
        return trajectory

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
        context.metadata = {
            **(context.metadata or {}),
            "measurements": getattr(self, "_measurement_marker", None)
            or unavailable_marker(),
        }
        context.n_input_tokens = context.n_output_tokens = context.n_cache_tokens = None
        if getattr(self, "_invocation_failed", False):
            return
        trajectory = self._trajectory
        if trajectory is None:
            trajectory = self._convert_events_to_trajectory(self._session_events())
        if trajectory is None:
            return
        data = trajectory.to_json_dict()
        (self.logs_dir / "trajectory.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        populate_context_from_trajectory(context, data)
        if trajectory.final_metrics is not None:
            context.cost_usd = trajectory.final_metrics.total_cost_usd

    @override
    async def run(
        self,
        instruction,
        environment,
        context,
    ):
        self._trajectory = None
        self._invocation_failed = True
        self._diagnostic_env = None
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            for name in (
                "trajectory.json",
                PARTIAL_TRAJECTORY,
                "opencode-session.json",
                "opencode-failed-session.json",
                "opencode-export.stderr.log",
                "opencode.txt",
                "opencode.stderr.log",
                "opencode-first-attempt.txt",
                "opencode-first-attempt.stderr.log",
                "opencode-first-attempt-session.json",
                "opencode-first-attempt-export.stderr.log",
                "opencode-retry.json",
            ):
                (self.logs_dir / name).unlink(missing_ok=True)
            await self._run(instruction, environment, context)
            self._invocation_failed = False
        except BaseException as primary:
            try:
                await _await_owned_task(
                    asyncio.create_task(self._retain_failure(environment))
                )
            except BaseException as error:
                primary.add_note(
                    f"OpenCode diagnostic retention failed: {type(error).__name__}"
                )
            raise
        finally:
            await _await_owned_task(
                asyncio.create_task(
                    asyncio.to_thread(self._publish_measurements, context)
                )
            )
        # Measurement metadata makes AgentContext nonempty, so Harbor will not
        # invoke its fallback population callback after this method returns.
        self.populate_context_post_run(context)

    def _publish_measurements(self, context):
        from ..measurements import publish, unavailable
        from .opencode_measurements import capture

        self._measurement_marker = unavailable_marker()
        published = False
        try:
            partial = self.logs_dir / PARTIAL_TRAJECTORY
            if self._trajectory is not None:
                data = self._trajectory.to_json_dict()
            elif partial.is_file():
                data = json.loads(partial.read_text(encoding="utf-8"))
            else:
                # Cancellation can precede any retained message while native
                # hooks already prove a start and first output. CLI identity is
                # only an association key; its notification times are not used.
                sessions = {
                    event["sessionID"]
                    for event in self._parse_stdout(diagnostic=True)
                    if isinstance(event.get("sessionID"), str) and event["sessionID"]
                }
                if len(sessions) != 1:
                    raise ValueError("measurement_session_identity_unavailable")
                data = {"session_id": sessions.pop(), "steps": []}
            records, linked, complete, diagnostics = capture(
                self._measurement_path, data
            )
            self._measurement_marker = publish(
                self.logs_dir,
                records,
                producer={"name": "opencode", "version": self.version()},
                invocation_id=self._runtime_id,
                session_id=data.get("session_id"),
                complete=complete,
                capabilities={
                    "logical_steps": {
                        "status": "verified" if linked else "unavailable",
                        "reason": diagnostics[0] if diagnostics else None,
                        "basis_id": "native_step_start_to_streamed_v1",
                        "start_boundary": "session.step.started.started (first attempt)",
                        "end_boundary": "session.step.streamed.created",
                        "first_output_quality": "observed",
                        "clock": {
                            "id": "opencode:"
                            + str(data.get("session_id"))
                            + ":epoch_ms",
                            "type": "epoch_ms",
                            "semantics": "in_process_wall_clock",
                            "precision_ms": 1,
                        },
                        "evidence": "incremental HTTP hooks correlated by Session and native assistantMessageID",
                    }
                },
                diagnostics=diagnostics,
            )
            data.setdefault("extra", {})["measurements"] = self._measurement_marker
            published = True
            if self._trajectory is not None:
                self._trajectory = type(self._trajectory).model_validate(data)
            elif partial.is_file():
                partial.write_text(
                    json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8"
                )
        except Exception as error:
            self.logger.warning(
                "OpenCode measurement unavailable (%s)", type(error).__name__
            )
            if not published:
                self._measurement_marker = unavailable(
                    self.logs_dir,
                    producer={"name": "opencode", "version": self.version()},
                    invocation_id=self._runtime_id,
                )
        context.metadata = {
            **(context.metadata or {}),
            "measurements": self._measurement_marker,
        }

    async def _retain_failure(self, environment):
        if self._diagnostic_env is None:
            return
        events = self._parse_stdout(diagnostic=True)
        filename = (
            "opencode-session.json"
            if (self.logs_dir / "opencode-session.json").exists()
            else "opencode-failed-session.json"
        )
        if not (self.logs_dir / filename).exists():
            try:
                await self._export_session(
                    self._host(environment), self._diagnostic_env, events, filename
                )
            except Exception as error:
                self.logger.warning(
                    "OpenCode failed Session export unavailable (%s): %s",
                    type(error).__name__,
                    self.logs_dir,
                )
        source = "opencode.txt"
        try:
            native = self._session_events(events, filename=filename, diagnostic=True)
            if native:
                events, source = native, filename
        except Exception as error:
            self.logger.warning(
                "OpenCode diagnostic export unreadable (%s): %s",
                type(error).__name__,
                self.logs_dir,
            )
        write_partial(self.logs_dir, self._diagnostic_trajectory(events), source)

    def _diagnostic_trajectory(self, events):
        """Project complete turns plus observed content of the unfinished turn."""
        admitted, pending = [], []
        session = None
        for event in events:
            if not isinstance(event, dict):
                break
            identity = event.get("sessionID")
            if (
                not isinstance(identity, str)
                or not identity
                or (session and identity != session)
            ):
                break
            part = event.get("part", {})
            if not isinstance(part, dict):
                break
            if event.get("type") in {"text", "reasoning"} and not isinstance(
                part.get("text"), str
            ):
                break
            if event.get("type") == "tool_use" and (
                not isinstance(part.get("state"), dict)
                or not isinstance(part.get("callID", part.get("id")), str)
                or not isinstance(part.get("tool"), str)
            ):
                break
            session = identity
            if event.get("type") == "step_start":
                if pending:
                    break
                pending = [event]
            elif event.get("type") == "step_finish":
                if pending:
                    admitted.extend([*pending, event])
                    pending = []
            elif pending:
                pending.append(event)
        trajectory = self._convert_events_to_trajectory(admitted) if admitted else None
        data = (
            trajectory.to_json_dict()
            if trajectory
            else {
                "session_id": session,
                "agent": {
                    "name": self.name(),
                    "version": self.version() or "unknown",
                    "model_name": self.model_name,
                },
                "steps": [
                    {"step_id": 1, "source": "user", "message": self._instruction}
                ],
            }
        )
        step = {
            "step_id": len(data["steps"]) + 1,
            "source": "agent",
            "message": "",
            "extra": {"incomplete": True},
        }
        text, reasoning, calls, observations = [], [], [], []
        for event in pending[1:]:
            part = event.get("part", {})
            if event.get("type") in {"text", "reasoning"} and isinstance(
                part.get("text"), str
            ):
                (text if event["type"] == "text" else reasoning).append(part["text"])
            elif event.get("type") == "tool_use":
                identity, name, state = (
                    part.get("callID", part.get("id")),
                    part.get("tool"),
                    part.get("state"),
                )
                if (
                    not isinstance(identity, str)
                    or not isinstance(name, str)
                    or not isinstance(state, dict)
                ):
                    break
                calls.append(
                    {
                        "tool_call_id": identity,
                        "function_name": name,
                        "arguments": state.get("input")
                        if isinstance(state.get("input"), dict)
                        else {},
                    }
                )
                observations.append(
                    {
                        "source_call_id": identity,
                        "content": str(state.get("output", state.get("content", ""))),
                        "extra": {
                            "status": state.get("status", "incomplete"),
                            "is_error": state.get("status") != "completed",
                        },
                    }
                )
        if text or reasoning or calls:
            step["message"] = "\n".join(text)
            if reasoning:
                step["reasoning_content"] = "\n".join(reasoning)
            if calls:
                step.update(tool_calls=calls, observation={"results": observations})
            data["steps"].append(step)
        if len(data["steps"]) <= 1:
            return None
        # Completed-request metrics stay on their steps; the invocation total is unknown.
        data.pop("final_metrics", None)
        return Trajectory.model_validate(data)

    async def _run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        del context
        self._trajectory = None
        host = self._host(environment)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._instruction = self.render_instruction(instruction)
        instruction_path = (
            host.runtime_directory(f"opencode-{self._runtime_id}") / "instruction.txt"
        )
        instruction_path.write_bytes(self._instruction.encode("utf-8"))
        model = self.model_name
        if variant := self._resolved_flags.get("variant"):
            model = f"{model.split('#', 1)[0]}#{variant}"
        argv = [
            sys.executable,
            "-c",
            _STDIN_LAUNCHER,
            str(instruction_path),
            self.executable,
            "run",
            "--standalone",
            "--format=json",
            "--model",
            model,
            "--thinking",
        ]
        env = self._runtime_env(host)
        for attempt in range(2):
            self._diagnostic_env = env
            with (
                (self.logs_dir / "opencode.txt").open("w", encoding="utf-8") as stdout,
                (self.logs_dir / "opencode.stderr.log").open(
                    "w", encoding="utf-8"
                ) as stderr,
            ):

                async def capture(text: str, stream: str) -> None:
                    handle = stdout if stream == "stdout" else stderr
                    handle.write(text)
                    handle.flush()

                with host.scoped_exec_env(env), host.scoped_output_callback(capture):
                    result = await host.exec_argv(argv, env=env)
            failure = (
                NonZeroAgentExitCodeError(
                    f"OpenCode exited with {result.return_code}; see opencode.txt, "
                    "opencode.stderr.log and any opencode-failed-session.json"
                )
                if result.return_code != 0
                else None
            )
            try:
                events = self._parse_stdout()
            except Exception:
                if failure is not None:
                    raise failure
                raise
            if failure is None and any(
                event.get("type") == "error" for event in events
            ):
                failure = NonZeroAgentExitCodeError(
                    "OpenCode emitted error events; see opencode.txt"
                )
            if failure is None:
                break
            fallback = self._fallback_env(env) if attempt == 0 else None
            export_error = None
            try:
                await self._export_session(
                    host,
                    env,
                    events,
                    "opencode-first-attempt-session.json"
                    if fallback is not None
                    else "opencode-failed-session.json",
                )
            except Exception as error:
                if fallback is None:
                    raise failure from error
                export_error = type(error).__name__
            if fallback is None:
                raise failure
            for source, target in (
                ("opencode.txt", "opencode-first-attempt.txt"),
                ("opencode.stderr.log", "opencode-first-attempt.stderr.log"),
                (
                    "opencode-export.stderr.log",
                    "opencode-first-attempt-export.stderr.log",
                ),
            ):
                path = self.logs_dir / source
                if path.exists():
                    path.replace(self.logs_dir / target)
            (self.logs_dir / "opencode-retry.json").write_text(
                json.dumps(
                    {
                        "removed_setting": "websearch.provider",
                        "return_code": result.return_code,
                        "error_event": any(
                            event.get("type") == "error" for event in events
                        ),
                        "failed_session_export_error": export_error,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            env = fallback
        await self._export_session(host, env, events, "opencode-session.json")
        self._trajectory = self._convert_events_to_trajectory(
            self._session_events(events)
        )
        if self._trajectory is None:
            raise RuntimeError(
                "OpenCode exported no completed messages; see Agent logs"
            )

    async def _export_session(self, host, env, events, filename):
        sessions = {event["sessionID"] for event in events if event.get("sessionID")}
        if len(sessions) != 1:
            raise RuntimeError("OpenCode emitted no unique Session; see Agent logs")
        with (
            (self.logs_dir / filename).open("w", encoding="utf-8") as output,
            (self.logs_dir / "opencode-export.stderr.log").open(
                "w", encoding="utf-8"
            ) as errors,
        ):
            export_bytes = 0

            async def capture_export(text: str, stream: str) -> None:
                nonlocal export_bytes
                export_bytes += len(text.encode("utf-8"))
                if export_bytes > MAX_FAMILY_EXPORT_BYTES - 1024:
                    raise ValueError("OpenCode root export byte limit")
                handle = output if stream == "stdout" else errors
                handle.write(text)
                handle.flush()

            with host.scoped_exec_env(env), host.scoped_output_callback(capture_export):
                exported = await host.exec_argv(
                    [
                        self.executable,
                        "session",
                        "export",
                        "--standalone",
                        sessions.pop(),
                    ],
                    env=env,
                    timeout_sec=30,
                )
        if exported.return_code != 0:
            raise RuntimeError(
                "OpenCode Session export failed; see opencode-export.stderr.log"
            )

        if filename == "opencode-session.json":
            path = self.logs_dir / filename
            root = json.loads(path.read_text(encoding="utf-8"))
            await self._capture_export_family(host, env, root)
            fd, temporary = tempfile.mkstemp(
                prefix=".opencode-family-", dir=self.logs_dir
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as output:
                    json.dump(root, output, ensure_ascii=False, separators=(",", ":"))
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)

    async def _capture_export_family(self, host, env, root):
        deadline = monotonic() + MAX_FAMILY_EXPORT_SECONDS
        root_id = root["info"]["id"]
        relations, diagnostics = {}, []
        loaded = False
        observer = getattr(self, "_measurement_path", None)
        if observer and observer.exists():
            for row in bounded_records(observer, [MAX_EVENT_BYTES], diagnostics):
                loaded |= row.get("kind") == "loaded"
                if row.get("kind") == "family" and row.get("parent"):
                    relations[row["session"]] = row["parent"]
        limits = [
            "family_member_limit",
            "family_depth_limit",
            "family_export_byte_limit",
            "family_export_time_limit",
            "child_export_unavailable",
        ]
        root.update(
            children=[],
            family_missing=[],
            family_diagnostics=sorted(set(diagnostics + limits)),
            family_capture_complete=False,
        )
        budget = MAX_FAMILY_EXPORT_BYTES - _json_size(root)
        admitted, members = {root_id}, []
        depths = {root_id: 0}
        pending = [root_id]
        by_parent = {}
        for identity, parent in relations.items():
            by_parent.setdefault(parent, []).append(identity)
        for parent in pending:
            for identity in sorted(by_parent.get(parent, [])):
                if identity in admitted:
                    continue
                if len(admitted) >= MAX_MEMBERS:
                    diagnostics.append("family_member_limit")
                    break
                missing = {
                    "trajectory_id": identity,
                    "session_id": identity,
                    "parent_trajectory_id": parent,
                }
                size = _json_size(missing) + 1
                if size > budget:
                    diagnostics.append("family_export_byte_limit")
                    break
                budget -= size  # Reserve missing metadata before attempting a child.
                admitted.add(identity)
                depths[identity] = depths[parent] + 1
                if depths[identity] <= MAX_DEPTH:
                    pending.append(identity)
                members.append(missing)
        missing = []
        for member in members:
            identity = member["session_id"]
            remaining = deadline - monotonic()
            reason = (
                "family_depth_limit"
                if depths[identity] > MAX_DEPTH
                else "family_export_time_limit"
                if remaining <= 0
                else "family_export_byte_limit"
                if budget <= 0
                else None
            )
            if reason:
                diagnostics.append(reason)
                missing.append(member)
                continue
            try:
                captured_bytes = 0

                async def bound_child_export(text, stream):
                    nonlocal captured_bytes
                    captured_bytes += len(text.encode("utf-8"))
                    if captured_bytes > budget:
                        raise _FamilyExportByteLimit()

                with (
                    host.scoped_exec_env(env),
                    host.scoped_output_callback(bound_child_export),
                ):
                    child = await host.exec_argv(
                        [
                            self.executable,
                            "session",
                            "export",
                            "--standalone",
                            identity,
                        ],
                        env=env,
                        timeout_sec=remaining,
                    )
                if child.return_code != 0:
                    raise ValueError("child export failed")
                if len(child.stdout) > budget:
                    diagnostics.append("family_export_byte_limit")
                    missing.append(member)
                    budget = 0
                    continue
                body = json.loads(child.stdout)
                info = body.get("info") if isinstance(body, dict) else None
                if (
                    not isinstance(info, dict)
                    or info.get("id") != identity
                    or info.get("parentID") != relations[identity]
                ):
                    raise ValueError("child identity mismatch")
                size = _json_size(body) + 1
                if size > budget:
                    diagnostics.append("family_export_byte_limit")
                    missing.append(member)
                    budget = 0
                    continue
            except _FamilyExportByteLimit:
                diagnostics.append("family_export_byte_limit")
                missing.append(member)
                budget = 0
            except (OSError, TimeoutError, ValueError):
                diagnostics.append("child_export_unavailable")
                missing.append(member)
            else:
                root["children"].append(body)
                budget -= size
        root.update(
            family_missing=missing,
            family_diagnostics=sorted(set(diagnostics)),
            family_capture_complete=loaded and not diagnostics and not missing,
        )

    @override
    async def resume(self, *args, **kwargs) -> None:
        raise NotImplementedError("HostOpenCodeAgent supports fresh runs only")
