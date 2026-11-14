"""Admit private WorkBuddy child histories before projecting root ACP events."""

import json
import re

from ..family import MAX_MEMBERS, retain
from .sessions.common import CommonMessageAdapter
from .sessions.conversion import finalize_atif_conversion
from .sessions.models import ConversionOptions, MessageRecord
from .workbuddy_usage import _events, _hash_prefix, _open_history, normalize_usage


def _delegations(directory, summary):
    relations, background = {}, {}
    if not (directory / "acp.events.ndjson.gz").exists():
        return relations
    for event in _events(
        directory / "acp.events.ndjson.gz",
        summary["max_evidence_bytes"],
        summary.get("max_decoded_evidence_bytes"),
    ):
        message = event["message"]
        if event["direction"] != "receive" or message.get("method") != "session/update":
            continue
        params = message.get("params", {})
        if params.get("sessionId") != summary["session_id"]:
            raise ValueError("unrelated_session")
        update = params.get("update") or {}
        meta = update.get("_meta") or {}
        if meta.get("codebuddy.ai/toolName") != "Agent":
            continue
        call = update.get("toolCallId")
        if "codebuddy.ai/isBackground" in meta:
            background[call] = meta["codebuddy.ai/isBackground"]
        output = update.get("rawOutput") or {}
        text = output.get("text", "") if isinstance(output, dict) else ""
        match = re.search(r"\[Agent ID: (agent-[a-zA-Z0-9-]+)\]\s*$", text)
        if match:
            relations[match[1]] = {
                "call": update["toolCallId"],
                "request": meta.get("codebuddy.ai/conversationRequestId"),
                "joined": background.get(call) is False
                and update.get("status") == "completed",
            }
    return relations


def capture(root, summary, baseline, agent, *, directory=None):
    root_id = summary["session_id"]
    matches = [p for p in root.glob("*/*.jsonl") if p.stem == root_id]
    result = {
        "children": {},
        "parent_calls": set(),
        "diagnostics": [],
        "usage": [],
        "links": {},
        "missing": [],
    }
    if len(matches) != 1:
        result["diagnostics"].append("family_root_history_unavailable")
        return result
    declarations = _delegations(directory, summary) if directory is not None else {}
    project = matches[0].parent
    pending = [root_id]
    budget = summary["max_evidence_bytes"]
    seen = {root_id}
    while pending:
        parent = pending.pop()
        child_dir = project / parent / "subagents"
        if not child_dir.exists():
            continue
        for path in sorted(child_dir.glob("*.jsonl")):
            if len(seen) >= MAX_MEMBERS:
                result["diagnostics"].append("family_member_limit")
                break
            identity = path.stem
            if identity in seen:
                result["diagnostics"].append("duplicate_family_identity")
                continue
            records, metadata, requests, native_ids, root_requests = (
                [],
                {},
                {},
                set(),
                set(),
            )
            native_model = None
            finished = False
            tool_starts, tool_outcomes = {}, {}
            reasoning = {}
            with _open_history(path) as (stream, info):
                if info.st_size > budget:
                    result["diagnostics"].append("family_history_byte_limit")
                    continue
                budget -= info.st_size
                previous = baseline.files.get(str(path.relative_to(root)))
                if previous:
                    if (
                        previous[3] is None
                        or (info.st_dev, info.st_ino) != previous[:2]
                    ):
                        raise ValueError("family_baseline_identity")
                    digest, _ = _hash_prefix(stream, previous[2])
                    if digest.hexdigest() != previous[3]:
                        raise ValueError("family_baseline_changed")
                for seq, line in enumerate(stream):
                    if (
                        seq >= 100_000
                        or len(line) > 16 * 1024 * 1024
                        or not line.endswith(b"\n")
                    ):
                        result["diagnostics"].append("family_history_incomplete")
                        break
                    item = json.loads(line)
                    item = item.get("payload", item)
                    if item.get("sessionId"):
                        native_ids.add(item["sessionId"])
                    if item.get("type") == "session-meta":
                        metadata.update(item.get("meta") or {})
                        continue
                    # WorkBuddy stores outer role/content and a nested usage-only message.
                    message = {**item, **(item.get("message") or {})}
                    kind = item.get("type")
                    role = (
                        "assistant"
                        if kind in {"reasoning", "function_call"}
                        else "tool_result"
                        if kind == "function_call_result"
                        else message.get("role", kind)
                    )
                    timing = None
                    if kind == "function_call":
                        arguments = item.get("arguments", {})
                        if isinstance(arguments, str):
                            try:
                                arguments = json.loads(arguments)
                            except ValueError:
                                result["diagnostics"].append(
                                    "family_tool_arguments_unavailable"
                                )
                                arguments = {}
                        message.update(
                            content="",
                            tool_calls=[
                                {
                                    "id": item["callId"],
                                    "name": item["name"],
                                    "arguments": arguments,
                                }
                            ],
                        )
                        tool_starts[item["callId"]] = item.get("timestamp")
                    elif kind == "function_call_result":
                        native = (
                            (item.get("providerData") or {}).get("toolResult") or {}
                        ).get("rawResponse") or {}
                        tool_outcomes[item["callId"]] = {
                            "exit_code": native.get("exitCode"),
                            "signal": native.get("signal"),
                            "cancelled": native.get("interrupted") is True,
                        }
                        message.update(
                            tool_call_id=item["callId"],
                            tool_name=item["name"],
                            content=item.get("output"),
                            is_error=item.get("status") in {"error", "failed"}
                            or native.get("exitCode") not in (None, 0)
                            or native.get("interrupted") is True,
                        )
                        start, end = (
                            tool_starts.get(item["callId"]),
                            item.get("timestamp"),
                        )
                        if type(start) is int and type(end) is int and end >= start:
                            timing = {
                                "started_at_ms": start,
                                "finished_at_ms": end,
                                "elapsed_ms": end - start,
                                "elapsed_ms_source": "workbuddy_private_tool_timestamps",
                            }
                    if role not in {
                        "user",
                        "assistant",
                        "tool",
                        "tool_result",
                        "system",
                    }:
                        continue
                    provider = item.get("providerData") or {}
                    if provider.get("rootRequestId"):
                        root_requests.add(provider["rootRequestId"])
                    native_model = provider.get("model") or native_model
                    request = provider.get("messageId")
                    if item.get("type") == "reasoning":
                        reasoning[request] = "\n".join(
                            b.get("text", "")
                            for b in item.get("rawContent", [])
                            if isinstance(b, dict)
                        )
                        continue
                    finished = role == "assistant" and item.get("status") == "completed"
                    if request in reasoning:
                        message["reasoning_content"] = reasoning.pop(request)
                    usage = normalize_usage(
                        provider.get("rawUsage") or provider.get("usage")
                    )
                    if request and any(v is not None for v in usage.values()):
                        requests[request] = usage
                    content = message.get("content")
                    if isinstance(content, list):
                        message["content"] = [
                            {
                                **b,
                                "type": "text"
                                if b.get("type") in {"input_text", "output_text"}
                                else b.get("type"),
                            }
                            if isinstance(b, dict)
                            else b
                            for b in content
                        ]
                    message.update(role=role, timestamp_ms=item.get("timestamp"))
                    if native_model:
                        message["model"] = native_model
                    records.append(
                        MessageRecord(
                            message=message,
                            metadata=timing,
                            usage=usage,
                            session_seq=seq,
                            source_session_id=next(iter(native_ids), identity),
                        )
                    )
            for text in reasoning.values():
                records.append(
                    MessageRecord(
                        message={"role": "assistant", "reasoning_content": text},
                        source_session_id=next(iter(native_ids), identity),
                    )
                )
                result["diagnostics"].append("family_unfinished_reasoning")
            if len(native_ids) > 1:
                raise ValueError("family_history_identity")
            meta_path = path.with_suffix(".meta.json")
            if meta_path.exists():
                with _open_history(meta_path) as (stream, info):
                    if info.st_size > min(budget, 1024 * 1024):
                        result["diagnostics"].append("family_metadata_byte_limit")
                        continue
                    budget -= info.st_size
                    extra = json.loads(stream.read())
                    metadata.update(extra.get("meta", extra))
            declared_parent = metadata.get(
                "parentSubagentId", metadata.get("parentSessionId")
            )
            declaration = declarations.get(identity)
            proven_call = (
                declaration
                and declaration["request"] in root_requests
                and parent == root_id
            )
            if not proven_call and (
                declared_parent != parent
                or metadata.get("subagentRootSessionId", root_id) != root_id
            ):
                result["diagnostics"].append("unproven_family_parentage")
                continue
            if not records:
                result["diagnostics"].append("family_child_history_empty")
                continue
            native_id = next(iter(native_ids), identity)
            converted = finalize_atif_conversion(
                CommonMessageAdapter().convert(
                    records,
                    ConversionOptions(agent_name="workbuddy", model=native_model),
                ),
                native_id,
            )
            data = converted.trajectory
            data["trajectory_id"] = "workbuddy:" + native_id
            for step in data["steps"]:
                for observation in (step.get("observation") or {}).get("results") or []:
                    observation.setdefault("extra", {}).update(
                        tool_outcomes.get(observation.get("source_call_id"), {})
                    )
            data["agent"] = {
                "name": "workbuddy",
                "version": agent["version"],
                **({"model_name": native_model} if native_model else {}),
            }
            data.setdefault("extra", {})["tool_evidence"] = (
                "partial" if converted.warnings or not finished else "complete"
            )
            data["extra"]["execution_status"] = "completed" if finished else "unknown"
            if not finished:
                data["extra"]["incomplete"] = True
            result["children"][identity] = (parent, data)
            call = (
                declaration["call"]
                if proven_call
                else metadata.get("parentToolUseId", metadata.get("parentToolCallId"))
            )
            if call:
                result["parent_calls"].add(call)
                result["links"][identity] = {
                    "call": call,
                    "joined": bool(proven_call and declaration.get("joined")),
                }
            for request, usage in requests.items():
                result["usage"].append(
                    {
                        "type": "request",
                        "session_id": native_id,
                        "scope": "child",
                        "id": request,
                        "input_tokens": usage["prompt_tokens"],
                        "output_tokens": usage["completion_tokens"],
                        "cached_tokens": usage["cached_tokens"],
                    }
                )
            seen.add(identity)
            pending.append(identity)
    for identity in declarations.keys() - result["children"].keys():
        result["missing"].append(
            {
                "trajectory_id": "workbuddy:" + identity,
                "session_id": identity,
                "parent_trajectory_id": "workbuddy:" + root_id,
            }
        )
    return result


def attach(data, captured):
    from ..family import link_call

    data.setdefault("trajectory_id", "workbuddy:" + data["session_id"])
    bodies = {
        data["session_id"]: data,
        **{identity: body for identity, (_, body) in captured["children"].items()},
    }
    activations = []
    for identity, (parent, body) in captured["children"].items():
        bodies[parent].setdefault("subagent_trajectories", []).append(body)
        if link := captured.get("links", {}).get(identity):
            activations.append(
                link_call(
                    bodies[parent], body, link["call"], terminal_join=link["joined"]
                )
            )
    retain(
        data,
        missing=captured.get("missing", []),
        activations=activations,
        complete=not captured["diagnostics"] and not captured.get("missing"),
        diagnostics=captured["diagnostics"],
    )
    return data
