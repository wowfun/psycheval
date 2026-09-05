from __future__ import annotations

import json
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

from .inference_telemetry import (
    finalize_trajectory_metrics,
    metrics_from_observations,
    observation_from_usage,
)


def parse_ndjson(raw: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid Psychevo JSON on stdout line {line_number}: {exc.msg}"
            ) from exc
        if not isinstance(value, dict):
            raise TypeError(
                f"invalid Psychevo event on stdout line {line_number}: expected object"
            )
        events.append(value)
    return events


def terminal_event(events: list[dict[str, Any]]) -> dict[str, Any]:
    terminals = [
        event
        for event in events
        if event.get("type") in {"turn.completed", "turn.failed"}
    ]
    if not terminals:
        raise ValueError("Psychevo transcript has no terminal turn event")
    terminal = terminals[-1]
    if (
        terminal.get("type") != "turn.completed"
        or terminal.get("outcome") != "completed"
        or terminal.get("toolFailures") not in {None, 0}
    ):
        reason = terminal.get("terminalMessage") or terminal.get("outcome")
        raise ValueError(f"Psychevo turn did not complete successfully: {reason}")
    return terminal


def psychevo_events_to_atif(
    events: list[dict[str, Any]],
    *,
    instruction: str,
    agent_version: str,
) -> dict[str, Any]:
    terminal = terminal_event(events)
    completed_occurrences: list[tuple[dict[str, Any], tuple[str, ...]]] = []
    active_tool_ids: dict[str, set[str]] = {}
    event_items: list[dict[str, Any]] = []
    tool_records: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for event in events:
        event_type = event.get("type")
        if event_type not in {
            "item.started",
            "item.updated",
            "item.completed",
        }:
            continue
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        event_items.append(item)
        item_id = item.get("id")
        lifecycle_ids = (
            active_tool_ids.setdefault(item_id, set())
            if isinstance(item_id, str) and item_id
            else set()
        )
        for block in _blocks(item):
            metadata = _dict(block.get("metadata"))
            tool_name = metadata.get("tool_name")
            if tool_name is None:
                continue
            call_id = metadata.get("tool_call_id") or metadata.get("provider_tool_id")
            if isinstance(call_id, str) and call_id:
                lifecycle_ids.add(call_id)

        current_provider_id = _single_provider_id(lifecycle_ids, tool_records)
        for block in _blocks(item):
            metadata = _dict(block.get("metadata"))
            projection = metadata.get("projection")
            if _is_provider_source(block, metadata):
                if event_type == "item.completed" and current_provider_id is not None:
                    record = tool_records.get(current_provider_id)
                    if record is not None:
                        source = _provider_source(block, metadata)
                        if source not in record["sources"]:
                            record["sources"].append(source)
                continue
            tool_name = metadata.get("tool_name")
            direct_call_id = metadata.get("tool_call_id") or metadata.get(
                "provider_tool_id"
            )
            if projection == "provider_tool":
                if not isinstance(tool_name, str) or not tool_name:
                    raise ValueError("Psychevo provider tool block has no tool name")
                if not isinstance(direct_call_id, str) or not direct_call_id:
                    raise ValueError(
                        f"Psychevo tool block {tool_name!r} has no call identity"
                    )
                record = tool_records.setdefault(
                    direct_call_id,
                    {
                        "name": tool_name,
                        "arguments": {},
                        "result": None,
                        "is_error": False,
                        "status": None,
                        "provider": True,
                        "sources": [],
                    },
                )
                action = _object_value(metadata.get("action"))
                if action is not None:
                    record["arguments"] = action
                status = metadata.get("status", block.get("status"))
                if status is not None:
                    record["status"] = status
                if status in {"failed", "incomplete", "cancelled"}:
                    record["is_error"] = True
                current_provider_id = direct_call_id
                continue

            call_id = direct_call_id
            if not isinstance(call_id, str) or not call_id:
                call_id = _runtime_fallback_id(
                    lifecycle_ids, tool_records, block, metadata
                )
            if tool_name is None and isinstance(call_id, str):
                record = tool_records.get(call_id)
                tool_name = record["name"] if record is not None else None
            if tool_name is None:
                continue
            if not isinstance(call_id, str) or not call_id:
                raise ValueError(
                    f"Psychevo tool block {tool_name!r} has no call identity"
                )
            record = tool_records.setdefault(
                call_id,
                {
                    "name": str(tool_name),
                    "arguments": {},
                    "result": None,
                    "is_error": False,
                    "status": block.get("status"),
                    "provider": False,
                    "sources": [],
                },
            )
            if record["provider"]:
                continue
            arguments = metadata.get("arguments", metadata.get("args"))
            parsed_arguments = _object_value(arguments)
            if parsed_arguments is not None:
                record["arguments"] = parsed_arguments
            result = block.get("result")
            if isinstance(result, dict):
                content = result.get("content")
                if content is not None:
                    record["result"] = _text_value(content)
                record["is_error"] = bool(result.get("isError"))
                record["status"] = result.get("status", record["status"])
            if record["result"] is None and "result" in metadata:
                record["result"] = _text_value(metadata["result"])
            status = block.get("status")
            if status is not None:
                record["status"] = status
            if (
                status in {"completed", "failed", "cancelled"}
                and block.get("body") is not None
                and not (isinstance(result, dict) and result.get("content") is not None)
                and "result" not in metadata
            ):
                record["result"] = _text_value(block["body"])
            if status in {"failed", "cancelled"}:
                record["is_error"] = True

        if event_type == "item.completed":
            completed_occurrences.append((item, tuple(lifecycle_ids)))
            if isinstance(item_id, str):
                active_tool_ids.pop(item_id, None)

    for record in tool_records.values():
        if not record["provider"]:
            continue
        record["result"] = _text_value(
            {
                "action": record["arguments"],
                "sources": record["sources"],
                "status": record["status"],
            }
        )

    steps: list[dict[str, Any]] = [
        {"step_id": 1, "source": "user", "message": instruction}
    ]
    emitted_calls: set[str] = set()
    for item, lifecycle_ids in completed_occurrences:
        text_parts: list[str] = []
        call_ids: list[str] = []
        for block in _blocks(item):
            metadata = _dict(block.get("metadata"))
            call_id = metadata.get("tool_call_id") or metadata.get("provider_tool_id")
            if not isinstance(call_id, str) or not call_id:
                call_id = _runtime_fallback_id(
                    set(lifecycle_ids), tool_records, block, metadata
                )
            if isinstance(call_id, str) and call_id in tool_records:
                if call_id not in emitted_calls:
                    call_ids.append(call_id)
                    emitted_calls.add(call_id)
                continue
            if block.get("kind") == "text" and isinstance(block.get("body"), str):
                body = block["body"].strip()
                if body:
                    text_parts.append(body)
        if not text_parts and not call_ids:
            continue
        step: dict[str, Any] = {
            "step_id": len(steps) + 1,
            "source": "agent",
            "message": "\n\n".join(text_parts),
            "extra": {
                "psychevo_item_id": item.get("id"),
                "psychevo_source": item.get("source"),
            },
        }
        timestamp = _timestamp(item.get("createdAtMs"))
        if timestamp:
            step["timestamp"] = timestamp
        usage = observation_from_usage(
            item.get("usage"), usage_source="psychevo.item.usage"
        )
        if usage is not None:
            step["metrics"] = metrics_from_observations([usage])
        if call_ids:
            step["tool_calls"] = [
                {
                    "tool_call_id": call_id,
                    "function_name": tool_records[call_id]["name"],
                    "arguments": tool_records[call_id]["arguments"],
                }
                for call_id in call_ids
            ]
            observations = []
            for call_id in call_ids:
                record = tool_records[call_id]
                if record["result"] is None:
                    continue
                observations.append(
                    {
                        "source_call_id": call_id,
                        "content": record["result"],
                        "extra": {
                            "is_error": record["is_error"],
                            "status": record["status"],
                        },
                    }
                )
            if observations:
                step["observation"] = {"results": observations}
        steps.append(step)

    final_answer = terminal.get("finalAnswer")
    if isinstance(final_answer, str) and final_answer.strip():
        last_message = next(
            (
                step["message"]
                for step in reversed(steps)
                if step.get("source") == "agent" and step.get("message")
            ),
            None,
        )
        if last_message != final_answer:
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "source": "agent",
                    "message": final_answer,
                }
            )

    thread_id = str(terminal.get("threadId") or "unknown")
    agent: dict[str, Any] = {
        "name": "psychevo",
        "version": agent_version or "unknown",
    }
    model_name = _model_name(event_items)
    if model_name:
        agent["model_name"] = model_name
    trajectory = {
        "schema_version": "ATIF-v1.7",
        "session_id": thread_id,
        "trajectory_id": f"psychevo:{thread_id}",
        "agent": agent,
        "steps": steps,
        "extra": {
            "turn_id": terminal.get("turnId"),
            "outcome": terminal.get("outcome"),
            "tool_failures": terminal.get("toolFailures", 0),
        },
    }
    return finalize_trajectory_metrics(trajectory)


def _single_provider_id(
    call_ids: set[str], records: OrderedDict[str, dict[str, Any]]
) -> str | None:
    provider_ids = [
        call_id
        for call_id in call_ids
        if call_id in records and records[call_id]["provider"]
    ]
    return provider_ids[0] if len(provider_ids) == 1 else None


def _runtime_fallback_id(
    call_ids: set[str],
    records: OrderedDict[str, dict[str, Any]],
    block: dict[str, Any],
    metadata: dict[str, Any],
) -> str | None:
    if block.get("kind") == "text" or _is_provider_source(block, metadata):
        return None
    projection = metadata.get("projection")
    if isinstance(projection, str) and projection not in {"tool"}:
        return None
    runtime_ids = [
        call_id
        for call_id in call_ids
        if call_id in records and not records[call_id]["provider"]
    ]
    return runtime_ids[0] if len(runtime_ids) == 1 else None


def _is_provider_source(block: dict[str, Any], metadata: dict[str, Any]) -> bool:
    return block.get("source") == "provider.source" or metadata.get("projection") in {
        "url_citation",
        "web_image_source",
        "provider_source",
    }


def _provider_source(block: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    source: dict[str, Any] = {
        "projection": metadata.get("projection") or "provider_source",
    }
    for key in (
        "url",
        "title",
        "start_index",
        "end_index",
        "image_url",
        "thumbnail_url",
        "source_website_url",
        "caption",
        "kind",
        "data",
    ):
        if key in metadata:
            source[key] = metadata[key]
    body = block.get("body")
    if isinstance(body, str) and body:
        source["body"] = body
    return source


def _blocks(item: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = item.get("blocks")
    if not isinstance(blocks, list):
        return []
    return [block for block in blocks if isinstance(block, dict)]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _object_value(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _text_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _timestamp(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    try:
        milliseconds = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc).isoformat()


def _model_name(items: Any) -> str | None:
    for item in reversed(list(items)):
        candidates = [_dict(item.get("metadata"))]
        candidates.extend(_dict(block.get("metadata")) for block in _blocks(item))
        for metadata in candidates:
            model = metadata.get("model")
            if isinstance(model, str) and model.strip():
                return model.strip()
    return None
