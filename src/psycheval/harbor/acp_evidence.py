"""Lossless current-prompt ACP evidence projected into Harbor ATIF."""

from __future__ import annotations

import json
from pathlib import Path

from harbor.models.trajectories import Trajectory

from .acp_protocol import (
    DEFAULT_MAX_EVIDENCE_BYTES,
    MAX_EVENT_FRAME,
    MAX_JSON_DEPTH,
    EvidenceReader,
    ProtocolError,
    evidence_frame_limit,
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


def _metadata(state):
    metadata = state.get("_meta")
    if metadata is None:
        return {}
    if not isinstance(metadata, dict):
        raise ProtocolError("invalid retained tool metadata")
    return metadata


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
    if result_format == "codebuddy":
        metadata = _metadata(state)
        native = metadata.get("codebuddy.ai/rawResponse")
        if native is None:
            native = raw
        extra["raw_response"] = native
        content = _text(raw) or content
        if isinstance(native, dict):
            code = native.get("exitCode", native.get("exit_code"))
            signal = native.get("signal")
            extra.update(exit_code=code, signal=signal)
            if (type(code) is int and code != 0) or signal is not None:
                extra.update(status="failed", is_error=True)
            if (
                native.get("interrupted") is True
                or native.get("sandboxDenied") is True
                or native.get("tool_error_code") is not None
            ):
                extra.update(status="failed", is_error=True)
            output = native.get("output")
            if isinstance(output, str):
                content = output
            elif isinstance(output, dict):
                content = (
                    "\n".join(
                        output.get(key, "")
                        for key in ("stdout", "stderr")
                        if isinstance(output.get(key), str) and output[key]
                    )
                    or content
                )
        if (
            (
                state.get("name") == "Bash"
                or state.get("kind") == "execute"
                or isinstance(native, dict)
                and any(key in native for key in ("exitCode", "exit_code", "signal"))
            )
            and normalized == "completed"
            and extra["status"] == "completed"
        ):
            if (
                not isinstance(native, dict)
                or type(native.get("exitCode", native.get("exit_code"))) is not int
                or "signal" not in native
            ):
                extra.update(status="incomplete", is_error=True)
        if metadata.get("codebuddy.ai/businessFailed") is True:
            extra.update(status="failed", is_error=True)
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


def _merge_call(state, update, result_format):
    if "name" in update and state.get("name") not in {None, update["name"]}:
        raise ProtocolError("Tool canonical identity changed")
    if result_format == "codebuddy":
        metadata = _metadata(state)
        incoming = _metadata(update)
        native_name = incoming.get("codebuddy.ai/toolName")
        if native_name is not None:
            if state.get("name") not in (None, native_name) or update.get(
                "name"
            ) not in (None, native_name):
                raise ProtocolError("Tool canonical identity changed")
        metadata.update(
            {key: value for key, value in incoming.items() if value is not None}
        )
        state.update(update)
        state["_meta"] = metadata
        if native_name is not None:
            state["name"] = native_name
    else:
        state.update(update)


def _model_request(step, update, result_format):
    if result_format != "codebuddy":
        return
    identity = _metadata(update).get("codebuddy.ai/modelRequestId")
    if isinstance(identity, str) and identity:
        identities = step.setdefault("extra", {}).setdefault(
            "workbuddy_model_request_ids", []
        )
        if identity not in identities:
            identities.append(identity)


def convert(
    directory: Path, summary: dict, instruction: str, agent: dict, result_format: str
) -> Trajectory | None:
    try:
        return _convert(directory, summary, instruction, agent, result_format)
    except ProtocolError:
        raise
    except (KeyError, TypeError, ValueError, RecursionError, OSError) as exc:
        raise ProtocolError("invalid retained ACP evidence") from exc


def _events(path, maximum, decoded_maximum=None):
    if not path.exists():
        raise ProtocolError("retained ACP events are missing")
    maximum_frames = evidence_frame_limit(maximum)
    reader = EvidenceReader(path, maximum, decoded_maximum)
    pending = bytearray()
    count = 0
    try:
        while chunk := reader.read():
            pending.extend(chunk)
            while (end := pending.find(b"\n")) >= 0:
                if end + 1 > MAX_EVENT_FRAME or count >= maximum_frames:
                    raise ProtocolError("retained ACP evidence exceeds limits")
                event = json.loads(pending[:end])
                del pending[: end + 1]
                count += 1
                if (
                    not isinstance(event, dict)
                    or event.get("direction") not in {"send", "receive"}
                    or event.get("phase") not in {"setup", "replay", "prompt"}
                    or not isinstance(event.get("message"), dict)
                ):
                    raise ProtocolError("invalid retained ACP event")
                yield event
            if len(pending) >= MAX_EVENT_FRAME:
                raise ProtocolError("retained ACP evidence exceeds limits")
        reader.finish()
        if pending:
            raise ProtocolError("incomplete retained ACP event")
    finally:
        reader.close()


def _convert(
    directory: Path, summary: dict, instruction: str, agent: dict, result_format: str
) -> Trajectory | None:
    if not summary.get("prompt_submitted"):
        return None
    verify_evidence(directory, summary)
    events_path = directory / "acp.events.ndjson.gz"
    steps = [{"step_id": 1, "source": "user", "message": instruction}]
    calls = {}
    tool_ids = {}
    text_chunks = {}
    active = None
    for event in _events(
        events_path,
        summary.get("max_evidence_bytes", DEFAULT_MAX_EVIDENCE_BYTES),
        summary.get("max_decoded_evidence_bytes"),
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
            _model_request(active, update, result_format)
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
                state = calls[identity]
                if (
                    result_format == "codebuddy"
                    and state.get("status") in {"pending", "in_progress"}
                    and state.get("name")
                    and _metadata(update).get("codebuddy.ai/toolName") == state["name"]
                ):
                    _merge_call(state, update, result_format)
                    continue
                raise ProtocolError("duplicate Tool call identity")
            if active is None:
                active = {"step_id": len(steps) + 1, "source": "agent", "message": ""}
                steps.append(active)
            state = {}
            _merge_call(state, update, result_format)
            calls[identity] = state
            tool_ids.setdefault(active["step_id"], []).append(identity)
        elif kind == "tool_call_update":
            identity = update["toolCallId"]
            if identity not in calls:
                raise ProtocolError("Tool update without initial identity")
            state = calls[identity]
            _merge_call(state, update, result_format)
    for (step_id, field), chunks in text_chunks.items():
        steps[step_id - 1][field] = "".join(chunks)
    for step in steps:
        identities = tool_ids.get(step["step_id"], [])
        if not identities:
            continue
        tool_calls, observations = [], []
        for identity in identities:
            state = calls[identity]
            _model_request(step, state, result_format)
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
            **agent.get("extra", {}),
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
                "acp_tool_evidence_complete": summary.get("protocol_complete", False)
                and not (
                    result_format == "codebuddy"
                    and any(
                        state.get("name") == "DeferExecuteTool"
                        for state in calls.values()
                    )
                ),
                "acp_stop_reason": summary.get("stop_reason"),
                "cleanup_complete": summary.get("cleanup_complete", False),
            },
        }
    )
