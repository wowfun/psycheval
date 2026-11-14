"""Pure OpenCode 2 export and event projection shared by import and execution."""

from __future__ import annotations

import json
import math
import re

from harbor.agents.installed.opencode import OpenCode
from harbor.models.trajectories import Metrics, Trajectory

from ...family import call_activation, retain
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
                    "native_message_id": message.get("id"),
                    "is_copied_context": message.get("is_copied_context") is True,
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
        if finish.get("is_copied_context"):
            step.is_copied_context = True
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
            "native_message_id": finish.get("native_message_id"),
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
    if any(step.get("is_copied_context") for step in data["steps"]):
        data["final_metrics"] = {}
    return Trajectory.model_validate(finalize_trajectory_metrics(data))


def retain_export_family(data, exported, *, version="unknown"):
    """Project only native descendants, excluding ordinary Session forks."""
    from ...family import MAX_DEPTH

    data.setdefault("trajectory_id", data["session_id"])
    _retain_user_messages(data, exported)
    bodies = {data["session_id"]: data}
    excluded = set()
    depths = {data["session_id"]: 0}
    diagnostics = list(exported.get("family_diagnostics") or [])
    missing = list(exported.get("family_missing") or [])
    missing_ids = {item["trajectory_id"] for item in missing}
    activations = []
    dispatches = {}
    pending = list(exported.get("children") or [])
    while pending:
        remaining = []
        for source in pending:
            info = source["info"]
            if info.get("fork") or info.get("parentID") in excluded:
                excluded.add(info["id"])
                continue
            parent = bodies.get(info.get("parentID"))
            if parent is None:
                if info.get("parentID") in missing_ids:
                    missing.append(
                        {
                            "trajectory_id": info["id"],
                            "session_id": info["id"],
                            "parent_trajectory_id": info["parentID"],
                        }
                    )
                    missing_ids.add(info["id"])
                    continue
                remaining.append(source)
                continue
            identity = info["id"]
            if depths[info["parentID"]] >= MAX_DEPTH:
                missing.append(
                    {
                        "trajectory_id": identity,
                        "session_id": identity,
                        "parent_trajectory_id": info["parentID"],
                    }
                )
                excluded.add(identity)
                diagnostics.append("family_depth_limit")
                continue
            child = native_events_to_trajectory(
                native_session_events(source, diagnostic=True), version=version
            )
            if identity in bodies:
                raise ValueError("duplicate OpenCode child identity")
            if child is None:
                missing.append(
                    {
                        "trajectory_id": identity,
                        "session_id": identity,
                        "parent_trajectory_id": parent["trajectory_id"],
                    }
                )
                missing_ids.add(identity)
                continue
            body = child.to_json_dict()
            body.setdefault("trajectory_id", identity)
            _retain_user_messages(body, source)
            models = {
                f"{m['model']['providerID']}/{m['model']['id']}"
                for m in source["messages"]
                if m.get("type") == "assistant" and isinstance(m.get("model"), dict)
            }
            if len(models) == 1:
                body["agent"]["model_name"] = next(iter(models))
            body.setdefault("extra", {})["tool_evidence"] = (
                "complete" if info.get("outcome") == "succeeded" else "partial"
            )
            body["extra"]["execution_status"] = info.get("outcome") or "unknown"
            if info.get("outcome") != "succeeded":
                body["extra"]["incomplete"] = True
            parent.setdefault("subagent_trajectories", []).append(body)
            bodies[identity] = body
            depths[identity] = depths[info["parentID"]] + 1
            parent_id = parent["trajectory_id"]
            if parent_id not in dispatches:
                dispatches[parent_id] = _dispatch_index(parent)
            for call, result, joined in dispatches[parent_id].get(identity, []):
                refs = result.setdefault("subagent_trajectory_ref", [])
                ref = {"trajectory_id": body["trajectory_id"]}
                if ref not in refs:
                    refs.append(ref)
                activations.append(
                    call_activation(parent, body, call, joined_before_call_id=joined)
                )
        if len(remaining) == len(pending):
            raise ValueError("unproven OpenCode descendant parentage")
        pending = remaining
    missing_by_parent = {}
    for member in missing:
        missing_by_parent.setdefault(member["parent_trajectory_id"], []).append(
            member["trajectory_id"]
        )
    pending = list(excluded) + list(depths)
    for parent in pending:
        for identity in missing_by_parent.get(parent, []):
            if identity in excluded or identity in depths:
                continue
            if parent in excluded:
                excluded.add(identity)
            else:
                depths[identity] = depths[parent] + 1
                if depths[identity] > MAX_DEPTH:
                    excluded.add(identity)
                    diagnostics.append("family_depth_limit")
            pending.append(identity)
    missing = [m for m in missing if m["parent_trajectory_id"] not in excluded]
    data.setdefault("extra", {})["tool_evidence"] = (
        "complete"
        if exported.get("info", {}).get("outcome") == "succeeded"
        else "partial"
    )
    data["extra"]["execution_status"] = (
        exported.get("info", {}).get("outcome") or "unknown"
    )
    retain(
        data,
        missing=missing,
        activations=activations,
        diagnostics=diagnostics,
        complete=exported.get("family_capture_complete", False)
        and not missing
        and not diagnostics,
    )
    return data


def _dispatch_index(parent):
    result, following = {}, None
    for step in reversed(parent["steps"]):
        if step.get("is_copied_context"):
            continue
        calls = step.get("tool_calls") or []
        names = {call["tool_call_id"]: call["function_name"] for call in calls}
        for observation in (step.get("observation") or {}).get("results") or []:
            call = observation.get("source_call_id")
            content = observation.get("content")
            if names.get(call) != "subagent" or not isinstance(content, str):
                continue
            match = re.fullmatch(
                r'<subagent sessionID="([^"<>]+)" state="(completed|running)">[\s\S]*</subagent>',
                content,
            )
            if match:
                result.setdefault(match[1], []).append(
                    (call, observation, following if match[2] == "completed" else None)
                )
        if calls:
            following = calls[0]["tool_call_id"]
    return result


def _retain_user_messages(data, exported):
    messages = exported.get("messages") or []
    if not any(message.get("type") == "user" for message in messages):
        return
    by_id = {
        (step.get("extra") or {}).get("native_message_id"): step
        for step in data["steps"]
        if (step.get("extra") or {}).get("native_message_id")
    }
    ordered = []
    for message in messages:
        if message.get("type") == "user":
            step = {"source": "user", "message": str(message.get("text", ""))}
            timestamp = OpenCode._millis_to_iso(
                (message.get("time") or {}).get("created")
            )
            if timestamp:
                step["timestamp"] = timestamp
            if message.get("is_copied_context"):
                step["is_copied_context"] = True
            ordered.append(step)
        elif message.get("id") in by_id:
            ordered.append(by_id.pop(message["id"]))
    ordered.extend(by_id.values())
    data["steps"] = [
        dict(step, step_id=index + 1) for index, step in enumerate(ordered)
    ]
    data["final_metrics"]["total_steps"] = sum(
        not step.get("is_copied_context") for step in data["steps"]
    )
