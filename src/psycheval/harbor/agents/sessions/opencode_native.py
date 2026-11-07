"""Pure OpenCode 2 export and event projection shared by import and execution."""

from __future__ import annotations

import json
import math

from harbor.agents.installed.opencode import OpenCode
from harbor.models.trajectories import Metrics, Trajectory

from ...inference_telemetry import finalize_trajectory_metrics
from .opencode import _token_count
from .opencode import native_usage_metrics as _usage_metrics


class _NativeContext:
    _millis_to_iso = staticmethod(OpenCode._millis_to_iso)
    _user_event_text = staticmethod(OpenCode._user_event_text)

    def __init__(self, model_name, instruction, version):
        self.model_name, self._instruction, self._version = (
            model_name,
            instruction,
            version,
        )

    def version(self):
        return self._version


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


def native_session_events(
    exported: dict, *, streamed=(), model_name=None, diagnostic=False
) -> list[dict]:
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
    if any(event.get("sessionID") != session_id for event in streamed):
        raise ValueError("OpenCode Session export does not match streamed evidence")
    expected_model = model_name.split("#", 1)[0] if model_name else None
    events = []
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError("Malformed OpenCode Session message")
        if message.get("type") != "assistant":
            continue
        model = message.get("model", {})
        if not isinstance(model, dict):
            raise ValueError("Malformed OpenCode Session model")
        if (
            expected_model is not None
            and f"{model.get('providerID')}/{model.get('id')}" != expected_model
        ):
            raise ValueError("OpenCode Session message does not match requested model")
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
                state = {
                    **state,
                    "output": "\n".join(
                        item.get("text", "")
                        if item.get("type") == "text"
                        else json.dumps(item, ensure_ascii=False)
                        for item in output
                    )
                    or (error.get("message", "") if error is not None else ""),
                }
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
        raise ValueError("OpenCode streamed tool is missing from the Session export")
    return events


def native_events_to_trajectory(
    events: list[dict], *, model_name=None, instruction="", version="unknown"
) -> Trajectory | None:
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
                raise ValueError(f"Malformed OpenCode step boundary at index {index}")
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
    trajectory = OpenCode._convert_events_to_trajectory(
        _NativeContext(model_name, instruction, version), converted_events
    )
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
        step.metrics = Metrics.model_validate({**metrics, **projected, "extra": extra})
    for step in trajectory.steps:
        for call in step.tool_calls or []:
            timing = tool_times.get(call.tool_call_id)
            start = timing.get("ran") if isinstance(timing, dict) else None
            if type(start) is int and start >= 0:
                timestamp = OpenCode._millis_to_iso(start)
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
                timestamp := OpenCode._millis_to_iso(timing["completed"])
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
