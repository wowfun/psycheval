"""Run a preinstalled OpenCode 2 CLI on a native HostEnvironment."""

from __future__ import annotations

import asyncio
import copy
import json
import math
import shutil
import sys
from typing import override
from uuid import uuid4

from harbor.agents.capabilities import AgentCapabilities
from harbor.agents.installed.base import NonZeroAgentExitCodeError
from harbor.agents.installed.opencode import OpenCode, OpenCodeOptions
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.trajectories import Metrics, Trajectory
from pydantic import field_validator

from .diagnostics import PARTIAL_TRAJECTORY, write_partial
from .environment import HostEnvironment, _await_owned_task
from .inference_telemetry import (
    InferenceObservation,
    finalize_trajectory_metrics,
    metrics_from_observations,
    populate_context_from_trajectory,
)

_STDIN_LAUNCHER = (
    "import subprocess,sys; "
    "f=open(sys.argv[1],'rb'); "
    "sys.exit(subprocess.call(sys.argv[2:],stdin=f))"
)


def _token_count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _usage_metrics(tokens: object) -> dict:
    tokens = tokens if isinstance(tokens, dict) else {}
    cache = tokens.get("cache")
    cache = cache if isinstance(cache, dict) else {}

    buckets = [
        _token_count(tokens.get("input")),
        _token_count(cache.get("read", 0)),
        _token_count(cache.get("write", 0)),
    ]
    prompt = sum(buckets) if all(value is not None for value in buckets) else None
    metrics = metrics_from_observations(
        [
            InferenceObservation(
                prompt_tokens=prompt,
                completion_tokens=_token_count(tokens.get("output")),
                cached_tokens=_token_count(cache.get("read")),
                cache_write_tokens=_token_count(cache.get("write")),
                usage_source="opencode-session",
            )
        ]
    )
    assert metrics is not None  # One completed message always supplies an observation.
    reasoning = _token_count(tokens.get("reasoning"))
    if reasoning is not None:
        metrics["extra"]["reasoning_tokens"] = reasoning
    return metrics


def _native_duration(
    timing: object, start: str, end: str
) -> tuple[int | None, str | None]:
    if not isinstance(timing, dict):
        return None, "missing_native_timing"
    first, last = timing.get(start), timing.get(end)
    if first is None or last is None:
        return None, "missing_native_timing_boundary"
    if any(type(value) is not int or value < 0 for value in (first, last)):
        return None, "invalid_native_timing_boundary"
    if any(OpenCode._millis_to_iso(value) is None for value in (first, last)):
        return None, "invalid_native_timing_boundary"
    if last < first:
        return None, "reversed_native_timing_boundary"
    return last - first, None


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
        self,
        streamed: list[dict] | None = None,
        *,
        filename="opencode-session.json",
        diagnostic=False,
    ) -> list[dict]:
        path = self.logs_dir / filename
        if not path.is_file():
            return []
        exported = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(exported, dict):
            raise ValueError("Malformed OpenCode Session export")
        info, messages = exported.get("info"), exported.get("messages")
        if not isinstance(info, dict) or not isinstance(messages, list):
            raise ValueError("Malformed OpenCode Session export")
        session_id = info.get("id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("OpenCode Session export has no identity")
        if not diagnostic and info.get("outcome") != "succeeded":
            raise ValueError("OpenCode Session export is not a successful invocation")
        if streamed is None:
            streamed = self._parse_stdout()
        if any(event.get("sessionID") != session_id for event in streamed):
            raise ValueError("OpenCode Session export does not match streamed evidence")
        expected_model = self.model_name.split("#", 1)[0]
        events = []
        for message in messages:
            if not isinstance(message, dict):
                raise ValueError("Malformed OpenCode Session message")
            if message.get("type") != "assistant":
                continue
            model = message.get("model", {})
            if not isinstance(model, dict):
                raise ValueError("Malformed OpenCode Session model")
            if f"{model.get('providerID')}/{model.get('id')}" != expected_model:
                raise ValueError(
                    "OpenCode Session message does not match requested model"
                )
            timing, content = message.get("time", {}), message.get("content")
            if not isinstance(timing, dict):
                raise ValueError("Malformed OpenCode Session time")
            completed = timing.get("completed")
            if (completed is None and not diagnostic) or not isinstance(content, list):
                raise ValueError("OpenCode Session contains an incomplete message")
            if completed is not None and (
                type(completed) not in {int, float}
                or (type(completed) is float and not math.isfinite(completed))
            ):
                raise ValueError("Malformed OpenCode Session completion time")
            events.append(
                {
                    "type": "step_start",
                    "sessionID": session_id,
                    "timestamp": timing.get("created"),
                }
            )
            for part in content:
                if not isinstance(part, dict):
                    raise ValueError("Malformed OpenCode Session content")
                kind = part.get("type")
                if kind == "tool":
                    state = part.get("state", {})
                    if not isinstance(state, dict):
                        raise ValueError("Malformed OpenCode Session tool state")
                    output = state.get("content", [])
                    if not isinstance(output, list) or any(
                        not isinstance(item, dict)
                        or (
                            item.get("type") == "text"
                            and not isinstance(item.get("text", ""), str)
                        )
                        for item in output
                    ):
                        raise ValueError("Malformed OpenCode Session tool content")
                    error = state.get("error")
                    if error is not None and (
                        not isinstance(error, dict)
                        or not isinstance(error.get("message", ""), str)
                    ):
                        raise ValueError("Malformed OpenCode Session tool error")
                    state["output"] = "\n".join(
                        item.get("text", "")
                        if item.get("type") == "text"
                        else json.dumps(item, ensure_ascii=False)
                        for item in output
                    ) or (error.get("message", "") if error is not None else "")
                    part = {
                        "type": "tool",
                        "callID": part.get("id"),
                        "tool": part.get("name"),
                        "state": state,
                        "time": part.get("time"),
                    }
                    kind = "tool_use"
                if kind not in {"text", "reasoning", "tool_use"}:
                    raise ValueError(f"Unsupported OpenCode Session content: {kind}")
                events.append({"type": kind, "sessionID": session_id, "part": part})
            if completed is None:
                break
            events.append(
                {
                    "type": "step_finish",
                    "sessionID": session_id,
                    "part": {
                        "cost": message.get("cost"),
                        "tokens": message.get("tokens", {}),
                        "time": timing,
                    },
                }
            )
        native_tools = {
            (event["part"].get("callID"), event["part"].get("tool"))
            for event in events
            if event["type"] == "tool_use"
        }
        if any(
            (
                event.get("part", {}).get("callID", event.get("part", {}).get("id")),
                event.get("part", {}).get("tool"),
            )
            not in native_tools
            for event in streamed
            if event.get("type") == "tool_use"
        ):
            raise ValueError(
                "OpenCode streamed tool is missing from the Session export"
            )
        return events

    @override
    def _convert_events_to_trajectory(self, events: list[dict]) -> Trajectory | None:
        converted_events = []
        states = {}
        tool_times = {}
        identities = set()
        finishes = []
        in_step = False
        for index, event in enumerate(events):
            if not isinstance(event, dict):
                continue
            part = event.get("part", {})
            if event.get("type") == "tool_use":
                if not isinstance(part, dict) or part.get("type") != "tool":
                    raise ValueError(
                        f"Malformed OpenCode tool event at index {index}: expected a tool part"
                    )
                call_id = part.get("callID", part.get("id"))
                name, state = part.get("tool"), part.get("state")
                if (
                    not isinstance(call_id, str)
                    or not call_id
                    or not isinstance(name, str)
                    or not name
                    or not isinstance(state, dict)
                ):
                    raise ValueError(
                        f"Malformed OpenCode tool event at index {index}: expected identity and state"
                    )
                identities.add((call_id, name))
                states[call_id] = state
                tool_times[call_id] = part.get("time")
            elif not isinstance(part, dict):
                if event.get("type") in {"step_start", "step_finish"}:
                    raise ValueError(
                        f"Malformed OpenCode step boundary at index {index}"
                    )
                continue
            if event.get("type") == "step_start":
                in_step = True
            elif event.get("type") == "step_finish" and in_step:
                finishes.append(part)
                in_step = False
                # Harbor handles content and cost; native usage is projected below.
                tokens = part.get("tokens")
                tokens = tokens if isinstance(tokens, dict) else {}
                cache = tokens.get("cache")
                cache = cache if isinstance(cache, dict) else {}
                event = {
                    **event,
                    "part": {
                        **part,
                        "tokens": {
                            key: _token_count(tokens.get(key)) or 0
                            for key in ("input", "output", "reasoning")
                        }
                        | {
                            "cache": {
                                key: _token_count(cache.get(key)) or 0
                                for key in ("read", "write")
                            }
                        },
                    },
                }
            converted_events.append(event)
        trajectory = super()._convert_events_to_trajectory(converted_events)
        represented = (
            {
                (call.tool_call_id, call.function_name)
                for step in trajectory.steps
                for call in (step.tool_calls or [])
            }
            if trajectory is not None
            else set()
        )
        if identities - represented:
            raise ValueError("OpenCode tool events could not be represented in ATIF")
        if trajectory is None:
            return None
        agent_steps = [step for step in trajectory.steps if step.source == "agent"]
        if len(agent_steps) != len(finishes):
            raise ValueError(
                "OpenCode completed message usage does not align with ATIF steps"
            )
        for step, finish in zip(agent_steps, finishes):
            timing = finish.get("time")
            duration, diagnostic = _native_duration(timing, "created", "streamed")
            if duration is not None:
                lifecycle, lifecycle_error = _native_duration(
                    timing, "created", "completed"
                )
                if lifecycle_error or lifecycle < duration:
                    duration, diagnostic = None, "invalid_native_model_lifecycle"
            step.extra = {
                **(step.extra or {}),
                "duration_ms": duration,
                "duration_source": "opencode_native_model_call",
                **({"timing_diagnostic": diagnostic} if diagnostic else {}),
            }
            projected = _usage_metrics(finish.get("tokens", {}))
            metrics = step.metrics.model_dump(exclude_none=True) if step.metrics else {}
            if finish.get("cost") is not None:
                metrics["cost_usd"] = finish["cost"]
            for field in ("prompt_tokens", "completion_tokens", "cached_tokens"):
                metrics.pop(field, None)
            extra = metrics.pop("extra", {})
            extra.pop("cache_write_tokens", None)
            extra.update(projected.pop("extra"))
            step.metrics = Metrics.model_validate(
                {**metrics, **projected, "extra": extra}
            )
        for step in trajectory.steps:
            for call in step.tool_calls or []:
                timing = tool_times.get(call.tool_call_id)
                start = timing.get("ran") if isinstance(timing, dict) else None
                if type(start) is int and start >= 0:
                    timestamp = self._millis_to_iso(start)
                    if timestamp is not None:
                        call.extra = {**(call.extra or {}), "started_at": timestamp}
            for observation in step.observation.results if step.observation else []:
                state = states.get(observation.source_call_id)
                if state is None:
                    continue
                status = state.get("status")
                metadata = state.get("metadata")
                metadata = metadata if isinstance(metadata, dict) else {}
                exit_code = metadata.get("exit")
                extra = dict(observation.extra or {})
                extra["status"] = (
                    status
                    if isinstance(status, str) and status in {"completed", "error"}
                    else "incomplete"
                )
                extra["is_error"] = bool(extra.get("is_error")) or status != "completed"
                if type(exit_code) is int:
                    extra["exit_code"] = exit_code
                    extra["is_error"] = bool(extra.get("is_error")) or exit_code != 0
                if "content" in state:
                    extra["raw_output"] = state["content"]
                timing = tool_times.get(observation.source_call_id)
                duration, diagnostic = _native_duration(timing, "ran", "completed")
                if not isinstance(status, str) or status not in {"completed", "error"}:
                    duration, diagnostic = None, "nonterminal_native_tool"
                extra.update(
                    execution_duration_ms=duration,
                    execution_duration_source="opencode_native_tool_call",
                )
                if diagnostic:
                    extra["timing_diagnostic"] = diagnostic
                elif (
                    timestamp := self._millis_to_iso(timing["completed"])
                ) is not None:
                    extra["finished_at"] = timestamp
                observation.extra = extra or None
        data = trajectory.to_json_dict()
        data["extra"] = {
            **(data.get("extra") or {}),
            "timestamp_semantics": "event_observed",
        }
        for field in (
            "total_prompt_tokens",
            "total_completion_tokens",
            "total_cached_tokens",
        ):
            data["final_metrics"].pop(field, None)
        return Trajectory.model_validate(finalize_trajectory_metrics(data))

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
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

            async def capture_export(text: str, stream: str) -> None:
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

    @override
    async def resume(self, *args, **kwargs) -> None:
        raise NotImplementedError("HostOpenCodeAgent supports fresh runs only")
