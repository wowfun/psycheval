"""Read DSH's isolated v4 Session log after process settlement."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path

from ..measurements import (
    MAX_NATIVE_RECORD_BYTES,
    MAX_PRIVATE_BYTES,
    MAX_RECORDS,
    nonnegative,
)
from ..windows import open_read_descriptor


def native_records(path, budget):
    for item in (path, *path.parents):
        if item.is_symlink() or item.is_junction():
            raise ValueError("linked_native_measurement")
    with os.fdopen(open_read_descriptor(path), "rb") as stream:
        while line := stream.readline(min(MAX_NATIVE_RECORD_BYTES, budget[0]) + 1):
            budget[0] -= len(line)
            if budget[0] < 0 or len(line) > MAX_NATIVE_RECORD_BYTES:
                raise ValueError("native_measurement_read_limit")
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError("native_measurement_non_object")
            yield record


def bounded_records(path, budget, diagnostics):
    try:
        yield from native_records(path, budget)
    except (OSError, ValueError) as error:
        diagnostics.append(
            str(error)
            if str(error)
            in {"native_measurement_read_limit", "linked_native_measurement"}
            else "native_measurement_unreadable"
        )


def first_output(stream):
    for record in stream or []:
        kind = record.get("type")
        if kind == "chunk":
            chunk = record.get("chunk") or {}
            if (
                chunk.get("type") in {"text-delta", "reasoning-delta"}
                and chunk.get("text")
            ) or (
                chunk.get("type") == "tool-call-delta"
                and (chunk.get("argumentsDelta") or chunk.get("name"))
            ):
                return nonnegative(record.get("time"))
        elif kind in {"text-chunks", "reasoning-chunks", "tool-call-chunks"}:
            timestamp = nonnegative(record.get("time0"))
            if timestamp is None:
                return None
            if kind == "tool-call-chunks" and record.get("name"):
                return timestamp
            fragments = (
                record.get("args" if kind == "tool-call-chunks" else "texts") or []
            )
            deltas = record.get("dt") or []
            for index, fragment in enumerate(fragments):
                if index:
                    delta = (
                        nonnegative(deltas[index - 1]) if index <= len(deltas) else None
                    )
                    if delta is None:
                        return None  # Clock regressions are not repaired.
                    timestamp += delta
                if fragment:
                    return timestamp
    return None


def normalize(
    events, session_id, *, main_session, after_seq=-1, diagnostics=None, seeded=False
):
    """Fold native step identities; never merge using text or temporal adjacency."""
    steps, requests, tools, ends = {}, [], {}, []
    maximum, finished = after_seq, False
    clock = "dsh:" + session_id + ":epoch_ms"
    scope = "main" if session_id == main_session else "child"
    seen = {}
    seed_boundary_seen = not seeded or after_seq >= 0
    for event in events:
        if len(seen) >= MAX_RECORDS:
            if diagnostics is not None:
                diagnostics.append("native_measurement_record_limit")
            finished = False
            break
        seq = event.get("seq")
        if type(seq) is not int or seq <= after_seq:
            continue
        digest = hashlib.sha256(
            json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
        ).digest()
        if seq in seen:
            if seen[seq] != digest:
                raise ValueError("conflicting_native_event")
            continue
        if seq < maximum:
            raise ValueError("out_of_order_native_event")
        seen[seq] = digest
        maximum = seq
        kind, data = event.get("type"), event.get("data") or {}
        if kind == "session/end-seed" and data.get("inherited") is True:
            steps, requests, tools, ends = {}, [], {}, []
            finished, seed_boundary_seen = False, True
            continue
        if kind in {"step/start", "assistant/attempt", "assistant/message"} and any(
            type(data.get(key)) is not int for key in ("turn", "step")
        ):
            raise ValueError("missing_native_step_identity")
        identity = f"{data.get('turn')}:{data.get('step')}"
        base = {
            "session_id": session_id,
            "scope": scope,
            "clock_id": clock,
            "source_sha256": digest.hex(),
        }
        if kind == "step/start":
            if identity in steps:
                raise ValueError("conflicting_native_step")
            steps[identity] = {
                **base,
                "type": "step",
                "id": identity,
                "step_id": identity,
                "start_ms": event.get("time"),
                "complete": False,
                "attempts": 0,
            }
        elif kind in {"assistant/attempt", "assistant/message"}:
            step = steps.setdefault(
                identity,
                {
                    **base,
                    "type": "step",
                    "id": identity,
                    "step_id": identity,
                    "complete": False,
                    "attempts": 0,
                },
            )
            if step.get("complete"):
                raise ValueError("conflicting_native_step_completion")
            step["attempts"] += 1
            first = first_output(data.get("stream"))
            if step.get("first_ms") is None and first is not None:
                step["first_ms"] = first
            usage = data.get("usage") or {}
            if not usage:
                usage = next(
                    (
                        r.get("chunk", {}).get("usage", {})
                        for r in reversed(data.get("stream") or [])
                        if r.get("chunk", {}).get("type") == "usage"
                    ),
                    {},
                )
            prompt, cached, output, total = (
                nonnegative(usage.get(k))
                for k in (
                    "inputTokens",
                    "cacheReadTokens",
                    "outputTokens",
                    "totalTokens",
                )
            )
            # DSH input is uncached. A reported total also includes cache creation.
            inclusive = (
                total - output
                if total is not None and output is not None and total >= output
                else None
            )
            if inclusive is None and prompt is not None and cached is not None:
                write = nonnegative(usage.get("cacheWriteTokens"))
                inclusive = prompt + cached + write if write is not None else None
            requests.append(
                {
                    **base,
                    "type": "request",
                    "id": str(seq),
                    "request_id": str(seq),
                    "step_id": identity,
                    "input_tokens": inclusive,
                    "cached_tokens": cached,
                    "output_tokens": output,
                }
            )
            if kind == "assistant/message":
                step.update(
                    end_ms=event.get("time"),
                    complete=True,
                    output_tokens=output,
                    token_basis="final_output_includes_reasoning",
                    end_source_sha256=digest.hex(),
                )
        elif kind == "tool/call":
            call = data.get("callId")
            if isinstance(call, str):
                tools[call] = {
                    **base,
                    "type": "tool",
                    "id": call,
                    "call_id": call,
                    "start_ms": event.get("time"),
                    "status": "unknown",
                }
        elif kind == "tool/result":
            message = data.get("message") or {}
            call = (message.get("source") or {}).get("callId")
            if call in tools:
                # Absence of error is insufficient for shell success. The hook supplies status.
                tools[call].update(
                    end_ms=event.get("time"),
                    is_error=message.get("isError") is True or bool(data.get("error")),
                    end_source_sha256=digest.hex(),
                )
        elif kind == "turn/end":
            finished = True
            ends.append(
                {
                    **base,
                    "type": "end",
                    "id": str(seq),
                    "end_ms": event.get("time"),
                    "source": "turn/end",
                }
            )
    if not seed_boundary_seen:
        raise ValueError("missing_inherited_seed_boundary")
    for step in steps.values():
        if not step["attempts"]:
            requests.append(
                {
                    "type": "request",
                    "id": "unfinished:" + step["id"],
                    "step_id": step["id"],
                    "session_id": session_id,
                    "scope": scope,
                }
            )
    return [*steps.values(), *requests, *tools.values(), *ends], maximum, finished


def capture(home, session_id, offsets, hook_path):
    records, diagnostics, complete = [], [], False
    budget = [MAX_PRIVATE_BYTES]
    # Admit only the selected root and explicitly declared subagent descendants.
    candidates = list(
        itertools.islice((Path(home) / "sessions").glob("*/*/session.v4.jsonl"), 1025)
    )
    if len(candidates) > 1024:
        raise ValueError("native_measurement_file_limit")
    headers = {}
    for path in candidates:
        iterator = bounded_records(path, budget, diagnostics)
        try:
            header = next(iterator, {})
        finally:
            iterator.close()
        if header.get("version") == 4 and header.get("id") == path.parent.name:
            headers[header["id"]] = (path, header)
    admitted = {session_id}
    while True:
        children = {
            identity
            for identity, (_, header) in headers.items()
            if header.get("origin") == "subagent"
            and header.get("parentSession") in admitted
        }
        if children <= admitted:
            break
        admitted |= children
    for identity in sorted(admitted):
        if identity not in headers:
            diagnostics.append("native_session_unavailable")
            continue
        path, header = headers[identity]
        iterator = bounded_records(path, budget, diagnostics)
        if next(iterator, {}) != header:
            raise ValueError("native_session_identity")
        previous = offsets.get(identity)
        collected, last, finished = normalize(
            iterator,
            identity,
            main_session=session_id,
            after_seq=offsets.get(identity, -1),
            diagnostics=diagnostics,
            seeded=header.get("isSeeded") is True,
        )
        records.extend(collected)
        offsets[identity] = last
        if identity == session_id:
            complete = finished
        elif not finished and (previous is None or last > previous):
            records.append(
                {
                    "type": "request",
                    "id": "incomplete_child",
                    "session_id": identity,
                    "scope": "child",
                }
            )
    tool_records = {
        (r["session_id"], r["id"]): r for r in records if r["type"] == "tool"
    }
    if Path(hook_path).exists():
        for result in bounded_records(Path(hook_path), budget, diagnostics):
            if result.get("diagnostic") == "truncated":
                diagnostics.append("tool_observer_truncated")
                continue
            identity = (result.get("session_id"), result.get("id"))
            if identity in tool_records:
                tool_records[identity].update(
                    {
                        key: result[key]
                        for key in (
                            "exit_code",
                            "is_error",
                            "timed_out",
                            "cancelled",
                            "status",
                            "source",
                        )
                        if key in result
                    }
                )
    if not records:
        diagnostics.append("native_session_unavailable")
    return records, complete and not diagnostics, diagnostics
