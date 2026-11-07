from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...inference_telemetry import InferenceObservation, metrics_from_observations
from .common import CommonMessageAdapter
from .models import ConversionOptions, SessionInfo
from .sources import MessageRecord, read_jsonl

OPENCODE_PART_TIMING_SOURCE = "opencode_part_timestamps"
OPENCODE_EVENT_TOOL_TIMING_SOURCE = "opencode_event_tool_timestamps"
OPENCODE_MODEL_BOUNDARY_ESTIMATE_SOURCE = "opencode_model_boundary_estimate"


@dataclass
class OpencodeToolTiming:
    started_at_ms: int | None = None
    finished_at_ms: int | None = None
    status: str | None = None


class OpencodeAdapter(CommonMessageAdapter):
    agent_id = "opencode"
    default_agent_name = "opencode"

    def convert_path(self, path: str, config: ConversionOptions):
        source = Path(path)
        if source.is_dir() or source.suffix in {".db", ".sqlite", ".sqlite3"}:
            return self.convert_db(str(source), None, config)
        if source.suffix == ".json":
            try:
                exported = json.loads(source.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                exported = None
            if (
                isinstance(exported, dict)
                and "info" in exported
                and "messages" in exported
            ):
                return convert_native_export(exported, config)
        return self.convert(read_jsonl(path), config)

    def convert_db(
        self,
        path: str,
        session_id: str | None,
        config: ConversionOptions,
    ):
        records = read_opencode_db(path, session_id)
        return self.convert(records, config)

    def list_sessions(self, path: str) -> list[SessionInfo]:
        return list_opencode_sessions(resolve_opencode_db(path))


def read_opencode_db(path: str, session_id: str | None) -> list[MessageRecord]:
    db_path = resolve_opencode_db(path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        session = select_session(conn, session_id)
        messages = conn.execute(
            """
            SELECT id, time_created, time_updated, data
            FROM message
            WHERE session_id = ?
            ORDER BY time_created, id
            """,
            (session["id"],),
        ).fetchall()
        parts = conn.execute(
            """
            SELECT id, message_id, time_created, time_updated, data
            FROM part
            WHERE session_id = ?
            ORDER BY time_created, id
            """,
            (session["id"],),
        ).fetchall()
        event_tool_timings = read_opencode_event_tool_timings(
            conn,
            str(session["id"]),
        )
    except sqlite3.Error as exc:
        raise ValueError(f"failed to read OpenCode DB: {exc}") from exc
    finally:
        conn.close()

    grouped_parts: dict[str, list[sqlite3.Row]] = {}
    for part in parts:
        grouped_parts.setdefault(str(part["message_id"]), []).append(part)

    records: list[MessageRecord] = []
    seq = 1
    for row in messages:
        message_data = parse_json_object(row["data"], "message.data")
        record, tool_results = record_from_message_row(
            row,
            message_data,
            grouped_parts.get(str(row["id"]), []),
            session,
            seq,
            event_tool_timings,
        )
        records.append(record)
        seq += 1
        for tool_result in tool_results:
            records.append(with_session_seq(tool_result, seq))
            seq += 1
    return records


def resolve_opencode_db(path: str) -> Path:
    source = Path(path).expanduser()
    if source.is_dir():
        source = source / "opencode.db"
    if not source.exists():
        raise ValueError(f"OpenCode DB not found: {source}")
    return source


def select_session(conn: sqlite3.Connection, session_id: str | None) -> sqlite3.Row:
    if session_id:
        row = conn.execute(
            """
            SELECT id, title, directory, agent, model, time_created, time_updated
            FROM session
            WHERE id = ?
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"OpenCode session not found: {session_id}")
        return row
    row = conn.execute(
        """
        SELECT id, title, directory, agent, model, time_created, time_updated
        FROM session
        ORDER BY time_updated DESC, id DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        raise ValueError("OpenCode DB contains no sessions")
    return row


def list_opencode_sessions(path: Path) -> list[SessionInfo]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            """
            SELECT id, title, time_updated
            FROM session
            ORDER BY time_updated DESC, id DESC
            """
        ).fetchall()
    except sqlite3.Error as exc:
        raise ValueError(f"failed to read OpenCode DB: {exc}") from exc
    finally:
        conn.close()
    return [
        SessionInfo(
            session_id=str(row[0]),
            name=str(row[1]) if row[1] else None,
            updated_at_ms=int(row[2]) if row[2] is not None else None,
        )
        for row in rows
    ]


def record_from_message_row(
    row: sqlite3.Row,
    message_data: dict[str, Any],
    parts: list[sqlite3.Row],
    session: sqlite3.Row,
    seq: int,
    event_tool_timings: dict[str, OpencodeToolTiming],
) -> tuple[MessageRecord, list[MessageRecord]]:
    role = str(message_data.get("role") or "assistant").lower()
    content: list[dict[str, Any]] = []
    tool_results: list[MessageRecord] = []
    usage = usage_from_tokens(message_data.get("tokens"))
    cost = message_data.get("cost")
    first_tool_created_ms: int | None = None

    for part_row in parts:
        part_data = parse_json_object(part_row["data"], "part.data")
        part_type = str(part_data.get("type") or "").lower()
        if part_type == "text":
            text = part_data.get("text")
            if isinstance(text, str) and text:
                content.append({"type": "text", "text": text})
        elif part_type == "reasoning":
            text = part_data.get("text")
            if isinstance(text, str) and text:
                content.append({"type": "reasoning", "text": text})
        elif part_type == "tool":
            first_tool_created_ms = min_known_int(
                first_tool_created_ms,
                int_or_none(part_row["time_created"]),
            )
            tool_call, tool_result = tool_records_from_part(
                part_row,
                part_data,
                session,
                event_tool_timings.get(str(part_row["id"])),
            )
            content.append(tool_call)
            if tool_result:
                tool_results.append(tool_result)
        elif part_type == "step-finish":
            usage = usage or usage_from_tokens(part_data.get("tokens"))
            if cost is None:
                cost = part_data.get("cost")

    message: dict[str, Any] = {
        "role": role,
        "content": content,
        "timestamp_ms": int(row["time_created"]),
    }
    model = model_name(message_data, session)
    if model and role in {"assistant", "agent"}:
        message["model"] = model
    if role == "user" and len(content) == 1 and content[0].get("type") == "text":
        message["content"] = content[0]["text"]

    metadata = metadata_for(session, row["id"])
    if role in {"assistant", "agent"}:
        metadata.update(
            model_boundary_metadata(
                message_data,
                first_tool_created_ms,
            )
        )

    return (
        MessageRecord(
            message=message,
            usage=usage or None,
            metadata=metadata,
            accounting=accounting_from_cost(cost),
            session_seq=seq,
            source_session_id=str(session["id"]),
        ),
        tool_results,
    )


def tool_records_from_part(
    part_row: sqlite3.Row,
    part_data: dict[str, Any],
    session: sqlite3.Row,
    event_timing: OpencodeToolTiming | None = None,
) -> tuple[dict[str, Any], MessageRecord | None]:
    state = part_data.get("state") if isinstance(part_data.get("state"), dict) else {}
    call_id = str(part_data.get("callID") or part_data.get("id") or part_row["id"])
    tool_name = str(part_data.get("tool") or part_data.get("name") or "tool")
    input_value = state.get("input") if isinstance(state, dict) else None
    arguments = input_value if isinstance(input_value, dict) else {"input": input_value}
    tool_call = {
        "type": "tool_call",
        "id": call_id,
        "name": tool_name,
        "arguments": arguments,
    }
    if not isinstance(state, dict) or "output" not in state:
        return tool_call, None
    status = str(state.get("status") or "completed").lower()
    started_at_ms = int(part_row["time_created"])
    finished_at_ms = int(part_row["time_updated"] or part_row["time_created"])
    timing_source = OPENCODE_PART_TIMING_SOURCE
    if (
        event_timing
        and event_timing.started_at_ms is not None
        and event_timing.finished_at_ms is not None
    ):
        started_at_ms = event_timing.started_at_ms
        finished_at_ms = event_timing.finished_at_ms
        timing_source = OPENCODE_EVENT_TOOL_TIMING_SOURCE
        if event_timing.status:
            status = event_timing.status
    metadata = metadata_for(session, part_row["message_id"], part_row["id"])
    metadata.update(
        {
            "started_at_ms": started_at_ms,
            "started_at_ms_source": timing_source,
            "finished_at_ms": finished_at_ms,
            "finished_at_ms_source": timing_source,
            "elapsed_ms": max(0, finished_at_ms - started_at_ms),
            "elapsed_ms_source": timing_source,
        }
    )
    return tool_call, MessageRecord(
        message={
            "role": "tool_result",
            "tool_call_id": call_id,
            "tool_name": tool_name,
            "content": state.get("output"),
            "is_error": status not in {"completed", "success"},
            "timestamp_ms": finished_at_ms,
        },
        metadata=metadata,
        source_session_id=str(session["id"]),
    )


def read_opencode_event_tool_timings(
    conn: sqlite3.Connection,
    session_id: str,
) -> dict[str, OpencodeToolTiming]:
    try:
        rows = conn.execute(
            """
            SELECT seq, type, data
            FROM event
            WHERE aggregate_id = ?
            ORDER BY seq
            """,
            (session_id,),
        ).fetchall()
    except sqlite3.Error:
        return {}

    timings: dict[str, OpencodeToolTiming] = {}
    for row in rows:
        if str(row["type"]) != "message.part.updated.1":
            continue
        data = parse_json_object_or_none(row["data"])
        part = data.get("part") if isinstance(data, dict) else None
        if not isinstance(part, dict) or part.get("type") != "tool":
            continue
        part_id = part.get("id")
        if not part_id:
            continue
        state = part.get("state")
        if not isinstance(state, dict):
            continue
        status = str(state.get("status") or "").lower()
        time = state.get("time")
        if not isinstance(time, dict):
            continue
        timing = timings.setdefault(str(part_id), OpencodeToolTiming())
        if status == "running":
            started_at_ms = int_or_none(time.get("start"))
            if started_at_ms is not None:
                timing.started_at_ms = min_known_int(
                    timing.started_at_ms,
                    started_at_ms,
                )
        elif status in {"completed", "error"}:
            finished_at_ms = int_or_none(time.get("end"))
            if finished_at_ms is not None:
                timing.finished_at_ms = finished_at_ms
                timing.status = status
            started_at_ms = int_or_none(time.get("start"))
            if started_at_ms is not None:
                timing.started_at_ms = min_known_int(
                    timing.started_at_ms,
                    started_at_ms,
                )
    return timings


def model_boundary_metadata(
    message_data: dict[str, Any],
    first_tool_created_ms: int | None,
) -> dict[str, Any]:
    time = message_data.get("time")
    if not isinstance(time, dict):
        return {}
    started_at_ms = int_or_none(time.get("created"))
    if started_at_ms is None:
        return {}
    finished_at_ms = first_tool_created_ms
    if finished_at_ms is None:
        finished_at_ms = int_or_none(time.get("completed"))
    if finished_at_ms is None or finished_at_ms < started_at_ms:
        return {}
    elapsed_ms = finished_at_ms - started_at_ms
    return {
        "started_at_ms": started_at_ms,
        "started_at_ms_source": OPENCODE_MODEL_BOUNDARY_ESTIMATE_SOURCE,
        "finished_at_ms": finished_at_ms,
        "finished_at_ms_source": OPENCODE_MODEL_BOUNDARY_ESTIMATE_SOURCE,
        "elapsed_ms": elapsed_ms,
        "elapsed_ms_source": OPENCODE_MODEL_BOUNDARY_ESTIMATE_SOURCE,
    }


def with_session_seq(record: MessageRecord, seq: int) -> MessageRecord:
    return MessageRecord(
        message=record.message,
        usage=record.usage,
        metadata=record.metadata,
        accounting=record.accounting,
        session_seq=seq,
        source_session_id=record.source_session_id,
    )


def parse_json_object(raw: object, label: str) -> dict[str, Any]:
    try:
        value = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise ValueError(f"failed to parse OpenCode {label}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"OpenCode {label} is not an object")
    return value


def parse_json_object_or_none(raw: object) -> dict[str, Any]:
    try:
        value = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def int_or_none(raw: object) -> int | None:
    if isinstance(raw, bool):
        return None
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return int(value)


def min_known_int(left: int | None, right: int | None) -> int | None:
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)


def metadata_for(
    session: sqlite3.Row,
    message_id: object,
    part_id: object | None = None,
) -> dict[str, Any]:
    metadata = {
        "session_id": str(session["id"]),
        "message_id": str(message_id),
        "session_title": session["title"],
        "session_directory": session["directory"],
        "source": "opencode-db",
    }
    if part_id is not None:
        metadata["part_id"] = str(part_id)
    return metadata


def _token_count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def native_usage_metrics(tokens: object) -> dict:
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


def usage_from_tokens(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    projected = native_usage_metrics(raw)
    usage = {
        key: projected[key]
        for key in ("prompt_tokens", "completion_tokens", "cached_tokens")
        if key in projected
    }
    for source, target in (
        ("input", "input_tokens"),
        ("output", "output_tokens"),
        ("reasoning", "reasoning_tokens"),
        ("total", "total_tokens"),
    ):
        if type(raw.get(source)) is int and raw[source] >= 0:
            usage[target] = raw[source]
    cache = raw.get("cache")
    if isinstance(cache, dict):
        for source, target in (
            ("read", "cache_read_tokens"),
            ("write", "cache_write_tokens"),
        ):
            if type(cache.get(source)) is int and cache[source] >= 0:
                usage[target] = cache[source]
    return usage


def accounting_from_cost(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    return {"estimated_cost_nanodollars": int(float(raw) * 1_000_000_000)}


def model_name(message_data: dict[str, Any], session: sqlite3.Row) -> str | None:
    direct = message_data.get("modelID") or message_data.get("model")
    if isinstance(direct, str) and direct:
        return direct
    session_model = session["model"]
    if not session_model:
        return None
    try:
        value = json.loads(str(session_model))
    except json.JSONDecodeError:
        return str(session_model)
    if isinstance(value, dict) and value.get("id"):
        return str(value["id"])
    return None


def convert_native_export(exported: dict[str, Any], config: ConversionOptions):
    from ...redaction import redact_value
    from .common import bounded_arguments, bounded_text, bounded_value
    from .conversion import convert_atif_trajectory
    from .opencode_native import native_events_to_trajectory, native_session_events

    events = native_session_events(exported)
    model = config.model
    if model is None:
        model = next(
            (
                f"{m.get('model', {}).get('providerID')}/{m.get('model', {}).get('id')}"
                for m in exported["messages"]
                if m.get("type") == "assistant"
            ),
            None,
        )
    trajectory = native_events_to_trajectory(
        events, model_name=model, version=config.agent_version
    )
    if trajectory is None:
        raise ValueError("OpenCode Session export has no completed messages")
    data = trajectory.to_json_dict()
    if config.agent_name:
        data["agent"]["name"] = config.agent_name
    if config.redact:
        data = redact_value(data)
    for step in data["steps"]:
        truncated = False
        for key in ("message", "reasoning_content"):
            if isinstance(step.get(key), str):
                step[key], changed = bounded_text(step[key], config)
                truncated |= changed
        for call in step.get("tool_calls") or []:
            call["arguments"], changed = bounded_arguments(call["arguments"], config)
            truncated |= changed
        for observation in (step.get("observation") or {}).get("results") or []:
            observation["content"], changed = bounded_value(
                observation["content"], config
            )
            truncated |= changed
        if truncated:
            step.setdefault("extra", {})["truncated"] = True
    result = convert_atif_trajectory(data)
    result.total_events = len(exported["messages"])
    return result
