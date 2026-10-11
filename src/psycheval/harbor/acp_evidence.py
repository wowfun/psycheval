"""Lossless current-prompt ACP evidence projected into Harbor ATIF."""

from __future__ import annotations

import json
from pathlib import Path

from harbor.models.trajectories import Trajectory

from .acp_protocol import (
    DEFAULT_MAX_EVIDENCE_BYTES,
    MAX_EVENT_FRAME,
    MAX_EVIDENCE_FRAMES,
    MAX_JSON_DEPTH,
    ProtocolError,
    verify_evidence,
)


def _text(content, depth=0):
    if depth > MAX_JSON_DEPTH:
        raise ProtocolError("retained content exceeds depth limit")
    if isinstance(content, dict):
        if content.get("type") == "text":
            text = content.get("text", "")
            if not isinstance(text, str):
                raise ProtocolError("invalid retained text content")
            return text
        return ""
    if isinstance(content, list):
        return "\n".join(
            _text(item.get("content", item), depth + 1)
            for item in content
            if isinstance(item, dict)
        )
    return ""


def outcome(state, result_format):
    raw = state.get("rawOutput")
    status = state.get("status")
    normalized = (
        "completed"
        if status == "completed"
        else "failed"
        if status == "failed"
        else "incomplete"
    )
    extra = {
        "status": normalized,
        "acp_status": status,
        "raw_output": raw,
        "is_error": normalized != "completed",
    }
    content = _text(state.get("content", []))
    if (
        result_format == "rsiversi"
        and normalized == "completed"
        and (
            not isinstance(raw, dict)
            or type(raw.get("is_error")) is not bool
            or "value" not in raw
            or not isinstance(raw.get("content"), list)
        )
    ):
        extra.update(status="incomplete", is_error=True)
    if result_format == "rsiversi" and isinstance(raw, dict):
        extra["is_error"] |= raw.get("is_error") is True
        if "content" in raw:
            content = _text(raw["content"]) or content
        value = raw.get("value")
        execution = isinstance(value, dict) and (
            any(field in value for field in ("exit_code", "signal", "job_id"))
            or (
                isinstance(value.get("status"), str)
                and value["status"] in {"running", "exited", "timed_out"}
            )
        )
        if (state.get("name") == "bash" or execution) and normalized == "completed":
            value = value if isinstance(value, dict) else {}
            streams = [value.get(name) for name in ("stdout", "stderr")]
            content = "\n".join(
                _text({"type": "text", "text": stream.get("text", "")})
                for stream in streams
                if isinstance(stream, dict) and stream.get("text")
            )
            code, signal, terminal = (
                value.get("exit_code"),
                value.get("signal"),
                value.get("status"),
            )
            extra.update(exit_code=code, signal=signal, execution_status=terminal)
            if (
                terminal == "timed_out"
                or signal is not None
                or (type(code) is int and code != 0)
            ):
                extra["status"] = "failed"
            elif terminal != "exited" or type(code) is not int or "signal" not in value:
                extra["status"] = "incomplete"
            extra["is_error"] |= extra["status"] != "completed"
        if extra["is_error"] and extra["status"] == "completed":
            extra["status"] = "failed"
    return content, extra


def convert(
    directory: Path, summary: dict, instruction: str, agent: dict, result_format: str
) -> Trajectory | None:
    try:
        return _convert(directory, summary, instruction, agent, result_format)
    except ProtocolError:
        raise
    except (KeyError, TypeError, ValueError, RecursionError, OSError) as exc:
        raise ProtocolError("invalid retained ACP evidence") from exc


def _events(path, maximum):
    if not path.exists():
        raise ProtocolError("retained ACP events are missing")
    consumed = 0
    with path.open("rb") as stream:
        for index in range(MAX_EVIDENCE_FRAMES + 1):
            line = stream.readline(MAX_EVENT_FRAME + 1)
            if not line:
                return
            consumed += len(line)
            if (
                index == MAX_EVIDENCE_FRAMES
                or len(line) > MAX_EVENT_FRAME
                or consumed > maximum
            ):
                raise ProtocolError("retained ACP evidence exceeds limits")
            event = json.loads(line)
            if (
                not isinstance(event, dict)
                or event.get("direction") not in {"send", "receive"}
                or event.get("phase") not in {"setup", "replay", "prompt"}
                or not isinstance(event.get("message"), dict)
            ):
                raise ProtocolError("invalid retained ACP event")
            yield event


def _convert(
    directory: Path, summary: dict, instruction: str, agent: dict, result_format: str
) -> Trajectory | None:
    if not summary.get("prompt_submitted"):
        return None
    verify_evidence(directory, summary)
    events_path = directory / "acp.events.ndjson"
    steps = [{"step_id": 1, "source": "user", "message": instruction}]
    calls = {}
    tool_ids = {}
    text_chunks = {}
    active = None
    for event in _events(
        events_path, summary.get("max_evidence_bytes", DEFAULT_MAX_EVIDENCE_BYTES)
    ):
        message = event["message"]
        if (
            event["direction"] != "receive"
            or event["phase"] != "prompt"
            or message.get("method") != "session/update"
        ):
            continue
        params = message["params"]
        if params["sessionId"] != summary.get("session_id"):
            raise ProtocolError("update for an unrelated Session")
        update = params["update"]
        if not isinstance(update, dict):
            raise ProtocolError("invalid retained Session update")
        kind = update["sessionUpdate"]
        if kind in {"agent_message_chunk", "agent_thought_chunk"}:
            if not isinstance(update["content"], dict):
                raise ProtocolError("invalid retained content block")
            if active is None or tool_ids.get(active["step_id"]):
                active = {"step_id": len(steps) + 1, "source": "agent", "message": ""}
                steps.append(active)
            field = "message" if kind == "agent_message_chunk" else "reasoning_content"
            text_chunks.setdefault((active["step_id"], field), []).append(
                _text(update["content"])
            )
            if update["content"].get("type") != "text":
                active.setdefault("extra", {}).setdefault("acp_content", []).append(
                    update
                )
        elif kind == "tool_call":
            identity = update["toolCallId"]
            if identity in calls:
                raise ProtocolError("duplicate Tool call identity")
            if active is None:
                active = {"step_id": len(steps) + 1, "source": "agent", "message": ""}
                steps.append(active)
            state = dict(update)
            calls[identity] = state
            tool_ids.setdefault(active["step_id"], []).append(identity)
        elif kind == "tool_call_update":
            identity = update["toolCallId"]
            if identity not in calls:
                raise ProtocolError("Tool update without initial identity")
            state = calls[identity]
            if "name" in update and state.get("name") not in {None, update["name"]}:
                raise ProtocolError("Tool canonical identity changed")
            state.update(update)
    for (step_id, field), chunks in text_chunks.items():
        steps[step_id - 1][field] = "".join(chunks)
    for step in steps:
        identities = tool_ids.get(step["step_id"], [])
        if not identities:
            continue
        tool_calls, observations = [], []
        for identity in identities:
            state = calls[identity]
            canonical = isinstance(state.get("name"), str) and bool(state["name"])
            raw_input = state.get("rawInput")
            tool_calls.append(
                {
                    "tool_call_id": identity,
                    "function_name": state.get("name") or state["title"],
                    "arguments": raw_input if isinstance(raw_input, dict) else {},
                    "extra": {
                        "acp_canonical_name": canonical,
                        "title": state["title"],
                        "kind": state.get("kind"),
                        "raw_input": raw_input,
                        "arguments_available": isinstance(raw_input, dict),
                    },
                }
            )
            content, extra = outcome(state, result_format)
            observations.append(
                {"source_call_id": identity, "content": content, "extra": extra}
            )
        step["tool_calls"] = tool_calls
        step["observation"] = {"results": observations}
    agent = {
        **agent,
        "extra": {
            "acp_agent_info": summary.get("agent_info"),
            "config_options": summary.get("config_options", []),
        },
    }
    return Trajectory.model_validate(
        {
            "session_id": summary.get("session_id"),
            "agent": agent,
            "steps": steps,
            "extra": {
                "acp_tool_evidence_complete": summary.get("protocol_complete", False),
                "acp_stop_reason": summary.get("stop_reason"),
                "cleanup_complete": summary.get("cleanup_complete", False),
            },
        }
    )
