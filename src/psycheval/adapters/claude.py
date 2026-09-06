"""Read-only Claude Code retained sessions and explicitly linked subagents."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psycheval.adapters.base import ConversionResult, SessionInfo, SessionListing
from psycheval.adapters.common import CommonMessageAdapter, bounded_value
from psycheval.atif import iso_timestamp_ms
from psycheval.config import ToolConfig
from psycheval.redaction import redact_value
from psycheval.sources import MessageRecord

_SAFE_ID = re.compile(r"[A-Za-z0-9_-]+\Z")
_BOOKKEEPING = {
    "mode",
    "permission-mode",
    "atis-latch",
    "file-history-snapshot",
    "ai-title",
    "last-prompt",
    "queue-operation",
    "progress",
    "summary",
    "custom-title",
    "agent-name",
    "agent-color",
    "pr-link",
}
_BOOKKEEPING_ATTACHMENTS = {
    "agent_listing_delta",
    "skill_listing",
    "auto_mode",
    "bash_output_audience_note",
    "batching_reminder_sent",
}


@dataclass(frozen=True)
class _Session:
    info: SessionInfo
    path: Path


@dataclass(frozen=True)
class _Catalog:
    sessions: list[_Session]
    warnings: list[str]


class ClaudeAdapter:
    agent_id = "claude"

    def is_session_id(self, value: str) -> bool:
        return bool(_SAFE_ID.fullmatch(value))

    def resolve_session_id(self, session_id: str, config: ToolConfig) -> str:
        if not self.is_session_id(session_id):
            raise ValueError(f"invalid Claude session ID: {session_id}")
        root = Path(config.adapter_default_session_roots["claude"]).expanduser()
        if not root.is_dir():
            raise ValueError(f"Claude default_session_root does not exist: {root}")
        candidates = [root / f"{session_id}.jsonl"]
        candidates.extend(
            project / f"{session_id}.jsonl"
            for project in sorted(root.iterdir())
            if not project.is_symlink() and project.is_dir()
        )
        matches = []
        for path in candidates:
            if path.is_symlink() or not path.is_file():
                continue
            session = _scan_session(path)
            if session is None or session.info.session_id != session_id:
                raise ValueError(
                    f"Claude session identity does not match {session_id}: {path}"
                )
            matches.append(path)
        if not matches:
            raise ValueError(f"Claude session not found: {session_id} in {root}")
        if len(matches) > 1:
            raise ValueError(
                f"ambiguous Claude session ID {session_id}: {len(matches)} files in {root}"
            )
        return str(matches[0].resolve())

    def list_sessions(self, path: str) -> list[SessionInfo]:
        return self.inspect_sessions(path).sessions

    def inspect_sessions(self, path: str) -> SessionListing:
        source = Path(path).expanduser()
        if source.is_file():
            session = _scan_session(source)
            return SessionListing([session.info] if session else [])
        catalog = _catalog(source)
        return SessionListing(
            [session.info for session in catalog.sessions], catalog.warnings
        )

    def resolve_session_path(self, path: str, session_id: str | None) -> str:
        catalog = _catalog(Path(path).expanduser())
        sessions = catalog.sessions
        if not sessions:
            detail = "; ".join(catalog.warnings)
            raise ValueError(
                f"no Claude sessions found in: {path}"
                + (f"; {detail}" if detail else "")
            )
        if session_id is None:
            return str(sessions[0].path)
        for session in sessions:
            if session.info.session_id == session_id:
                return str(session.path)
        raise ValueError(f"Claude session not found: {session_id}")

    def convert_path(self, path: str, config: ToolConfig) -> ConversionResult:
        source = Path(path).expanduser()
        if source.is_dir():
            source = Path(self.resolve_session_path(str(source), None))
        events = _read_events(source)
        session_id, agent_id = _identity(events, source)
        if not _SAFE_ID.fullmatch(session_id):
            raise ValueError(f"invalid Claude session identity in: {source}")
        child_root = (
            source.parent
            if agent_id and source.parent.name == "subagents"
            else source.parent / session_id / "subagents"
        )
        return _read_family(
            source, events, session_id, agent_id, child_root, config, set()
        )


def _read_events(path: Path) -> list[dict[str, Any]]:
    return list(_iter_events(path))


def _iter_events(path: Path):
    try:
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}: JSONL line {number}: {exc.msg}") from exc
                if not isinstance(event, dict):
                    raise ValueError(f"{path}: JSONL line {number} is not an object")
                yield event
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read Claude session {path}: {exc}") from exc


def _identity(events: list[dict[str, Any]], path: Path) -> tuple[str, str | None]:
    sessions = {e["sessionId"] for e in events if isinstance(e.get("sessionId"), str)}
    agents = {e["agentId"] for e in events if isinstance(e.get("agentId"), str)}
    return _checked_identity(sessions, agents, path)


def _checked_identity(
    sessions: set[str], agents: set[str], path: Path
) -> tuple[str, str | None]:
    if len(sessions) != 1 or len(agents) > 1:
        raise ValueError(f"expected one Claude session identity in: {path}")
    return next(iter(sessions)), next(iter(agents), None)


def _scan_session(path: Path) -> _Session | None:
    sessions: set[str] = set()
    agents: set[str] = set()
    latest = None
    title = None
    main_conversation = False
    sidechain_conversation = False
    for event in _iter_events(path):
        if isinstance(event.get("sessionId"), str):
            sessions.add(event["sessionId"])
        if isinstance(event.get("agentId"), str):
            agents.add(event["agentId"])
        timestamp = iso_timestamp_ms(event.get("timestamp"))
        if timestamp is not None:
            latest = timestamp if latest is None else max(latest, timestamp)
        name = event.get("title") or event.get("customTitle")
        if isinstance(name, str):
            title = name
        if event.get("type") in ("user", "assistant"):
            if event.get("isSidechain") is True:
                sidechain_conversation = True
            else:
                main_conversation = True
    session_id, agent_id = _checked_identity(sessions, agents, path)
    if agent_id or (sidechain_conversation and not main_conversation):
        return None
    if not _SAFE_ID.fullmatch(session_id):
        raise ValueError(f"invalid Claude session identity in: {path}")
    return _Session(
        SessionInfo(session_id, title, latest, str(path)),
        path,
    )


def _catalog(directory: Path) -> _Catalog:
    if not directory.is_dir():
        raise ValueError(f"Claude project directory does not exist: {directory}")
    candidates: dict[str, list[_Session]] = {}
    warnings = []
    for path in sorted(directory.glob("*.jsonl")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            session = _scan_session(path)
        except ValueError as exc:
            warnings.append(f"excluded {path.name}: {exc}")
            continue
        if session is not None:
            candidates.setdefault(session.info.session_id, []).append(session)
    sessions = []
    for session_id, copies in candidates.items():
        if len(copies) > 1:
            warnings.append(
                f"excluded {len(copies)} files with duplicate Claude session identity: {session_id}"
            )
        else:
            sessions.append(copies[0])
    return _Catalog(
        sorted(
            sessions,
            key=lambda s: (
                s.info.updated_at_ms is None,
                -(s.info.updated_at_ms or 0),
                s.info.session_id,
            ),
        ),
        warnings,
    )


def _trajectory_id(session: str, agent: str | None) -> str:
    return f"claude:{session}" + (f":agent:{agent}" if agent else "")


def _read_family(
    source, events, session_id, agent_id, child_root, config, visited, ancestors=()
):
    identity = _trajectory_id(session_id, agent_id)
    visited.add(identity)
    ancestors = (*ancestors, identity)
    result, links = _normalize(events, session_id, agent_id, config)
    children = {}
    for observation, child_id in links:
        child_identity = _trajectory_id(session_id, child_id)
        if child_identity not in children:
            try:
                if not _SAFE_ID.fullmatch(child_id):
                    raise ValueError("invalid agent ID")
                if child_identity in ancestors:
                    raise ValueError("cyclic subagent link")
                if child_identity in visited:
                    raise ValueError("subagent already linked under another parent")
                if not child_root.resolve().is_relative_to(source.parent.resolve()):
                    raise ValueError("subagents directory escapes source directory")
                path = child_root / f"agent-{child_id}.jsonl"
                if path.is_symlink() or not path.resolve().is_relative_to(
                    child_root.resolve()
                ):
                    raise ValueError("subagent file escapes its session directory")
                child_events = _read_events(path)
                if _identity(child_events, path) != (session_id, child_id):
                    raise ValueError("subagent file identity does not match the link")
                child = _read_family(
                    path,
                    child_events,
                    session_id,
                    child_id,
                    child_root,
                    config,
                    visited,
                    ancestors,
                )
                if not child.trajectory["steps"]:
                    raise ValueError("subagent has no retained conversation")
                children[child_identity] = child
            except ValueError as exc:
                result.warnings.append(f"subagent {child_id}: {exc}; link omitted")
                continue
        observation["subagent_trajectory_ref"] = [{"trajectory_id": child_identity}]
    result.subagent_results = list(children.values())
    if not result.trajectory["steps"]:
        raise ValueError(f"no Claude conversation records in: {source}")
    result.warnings = list(dict.fromkeys(result.warnings))
    return result


def _evidence(value: Any, config: ToolConfig) -> Any:
    if config.redact:
        value = redact_value(value)
    return bounded_value(value, config)[0]


class _Messages(CommonMessageAdapter):
    default_agent_name = "claude"

    def step_from_record(self, record, step_id, config):
        result = super().step_from_record(record, step_id, config)
        if result is not None:
            step, _ = result
            extra = record.message.get("claude")
            if extra:
                step["extra"] = {"claude": _evidence(extra, config)}
            if record.message.get("model"):
                step["model_name"] = record.message["model"]
            metrics = step.get("metrics") or {}
            if metrics.get("prompt_tokens") is None:
                metrics.pop("cached_tokens", None)
            if record.message.get("synthetic"):
                step["llm_call_count"] = 0
                step.pop("metrics", None)
                step.pop("reasoning_content", None)
        return result


def _normalize(events, session_id, agent_id, config):
    records: list[MessageRecord] = []
    responses: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    seen_uuids: dict[str, dict[str, Any]] = {}
    linked_agents: dict[str, str] = {}
    unmapped = 0
    source_meta: dict[str, Any] = {"session_id": session_id, "agent_id": agent_id}

    def append(message, event, usage=None):
        message["timestamp_ms"] = iso_timestamp_ms(event.get("timestamp"))
        records.append(
            MessageRecord(message=message, usage=usage, source_session_id=session_id)
        )

    for event in events:
        uuid = event.get("uuid")
        if isinstance(uuid, str):
            if uuid in seen_uuids:
                if event != seen_uuids[uuid]:
                    warnings.append(f"conflicting replay for event {uuid}")
                continue
            seen_uuids[uuid] = event
        kind = event.get("type")
        if event.get("version"):
            source_meta["version"] = event["version"]
        if kind == "cost-state":
            source_meta["cost_state"] = _evidence(event, config)
            continue
        if kind in _BOOKKEEPING or (
            kind == "system" and event.get("subtype") == "turn_duration"
        ):
            continue
        if kind == "attachment":
            attachment = event.get("attachment") or {}
            if (
                isinstance(attachment, dict)
                and attachment.get("type") in _BOOKKEEPING_ATTACHMENTS
            ):
                continue
            if (
                isinstance(attachment, dict)
                and attachment.get("type") == "queued_command"
            ):
                append(
                    {
                        "role": "system",
                        "content": attachment.get("prompt", ""),
                        "claude": {"kind": "queued_command"},
                    },
                    event,
                )
                continue
        message = event.get("message")
        if kind == "assistant" and isinstance(message, dict):
            msg_id = message.get("id")
            key = msg_id if isinstance(msg_id, str) else None
            normalized = responses.get(key) if key else None
            usage = _usage(message.get("usage"), warnings, config)
            if normalized is None:
                normalized = {
                    "role": "assistant",
                    "content": [],
                    "model": message.get("model"),
                    "usage": _merge_usage({}, usage),
                    "synthetic": message.get("model") == "<synthetic>"
                    or event.get("isApiErrorMessage") is True,
                    "claude": {"message_id": msg_id, "events": []},
                }
                append(normalized, event)
                if key:
                    responses[key] = normalized
            elif usage:
                normalized["usage"] = _merge_usage(normalized.get("usage") or {}, usage)
            normalized["claude"]["events"].append(
                {
                    key: event[key]
                    for key in ("uuid", "parentUuid", "apiBlockIndex", "timestamp")
                    if key in event
                }
            )
            for block in _blocks(message.get("content")):
                block_type = block.get("type") if isinstance(block, dict) else None
                if block_type == "text":
                    normalized["content"].append(block)
                elif block_type in {"thinking", "reasoning", "analysis"}:
                    normalized["content"].append(
                        {
                            "type": "reasoning",
                            "text": block.get("thinking", block.get("text", "")),
                        }
                    )
                elif block_type == "tool_use":
                    call_id = block.get("id")
                    if not isinstance(call_id, str) or not call_id:
                        warnings.append("tool_use has no call ID")
                        normalized["claude"].setdefault("unmapped_content", []).append(
                            _evidence(block, config)
                        )
                        continue
                    existing = [
                        b
                        for b in normalized["content"]
                        if b.get("type") == "tool_call" and b.get("id") == call_id
                    ]
                    if existing:
                        continue
                    arguments = block.get("input", {})
                    normalized["content"].append(
                        {
                            "type": "tool_call",
                            "id": call_id,
                            "name": block.get("name") or "tool",
                            "arguments": arguments
                            if isinstance(arguments, dict)
                            else {"input": arguments},
                            "timestamp_ms": iso_timestamp_ms(event.get("timestamp")),
                        }
                    )
                elif block_type == "redacted_thinking":
                    normalized["claude"].setdefault("source_blocks", []).append(
                        _evidence(block, config)
                    )
                else:
                    warnings.append(
                        f"unmapped assistant content: {block_type or '<missing>'}"
                    )
                    normalized["claude"].setdefault("unmapped_content", []).append(
                        _evidence(block, config)
                    )
            continue
        if kind == "user" and isinstance(message, dict):
            content = message.get("content")
            plain = []
            tool_blocks = [
                b
                for b in _blocks(content)
                if isinstance(b, dict) and b.get("type") == "tool_result"
            ]
            batch_meta = event.get("toolUseResult")
            if (
                len(tool_blocks) != 1
                and isinstance(batch_meta, dict)
                and isinstance(batch_meta.get("agentId"), str)
            ):
                warnings.append(
                    f"subagent {batch_meta['agentId']}: ambiguous metadata for "
                    f"{len(tool_blocks)} tool results; link omitted"
                )
            for block in _blocks(content):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    call_id = block.get("tool_use_id")
                    append(
                        {
                            "role": "tool_result",
                            "tool_call_id": call_id,
                            "content": block.get("content", ""),
                            "is_error": block.get("is_error", False),
                        },
                        event,
                    )
                    result_meta = block.get("toolUseResult")
                    if result_meta is None and len(tool_blocks) == 1:
                        result_meta = batch_meta
                    if isinstance(result_meta, dict) and isinstance(
                        result_meta.get("agentId"), str
                    ):
                        if isinstance(call_id, str) and call_id:
                            linked_agents[call_id] = result_meta["agentId"]
                        else:
                            warnings.append(
                                f"subagent {result_meta['agentId']}: "
                                "result has no tool call ID; link omitted"
                            )
                else:
                    plain.append(block)
            if plain:
                origin = event.get("origin") or {}
                local = isinstance(content, str) and content.startswith(
                    ("<local-command-", "<command-name>")
                )
                system = (
                    event.get("isMeta")
                    or local
                    or (
                        isinstance(origin, dict)
                        and origin.get("kind") == "task-notification"
                    )
                )
                unknown = [
                    b
                    for b in plain
                    if not isinstance(b, dict) or b.get("type") != "text"
                ]
                if unknown:
                    warnings.append("unmapped user content retained in source blocks")
                append(
                    {
                        "role": "system" if system else "user",
                        "content": plain,
                        "claude": {
                            "kind": "local_command"
                            if local
                            else "context"
                            if system
                            else "user",
                            "source_blocks": _evidence(plain, config),
                        },
                    },
                    event,
                )
            continue
        if kind == "system":
            content = (
                event.get("content")
                or event.get("message")
                or event.get("subtype")
                or "system"
            )
            append(
                {
                    "role": "system",
                    "content": _text(content),
                    "claude": {
                        "kind": event.get("subtype", "system"),
                        "source": _evidence(event, config),
                    },
                },
                event,
            )
            continue
        unmapped += 1
        warnings.append(f"unmapped Claude event: {kind or '<missing>'}")
        append(
            {
                "role": "system",
                "content": f"[Claude event: {kind or 'unknown'}]",
                "claude": {"source": _evidence(event, config)},
            },
            event,
        )

    for record in records:
        if record.message.get("synthetic"):
            record.message["claude"]["synthetic_usage"] = record.message.pop(
                "usage", {}
            )
    result = _Messages().convert(records, config)
    if agent_id:
        result.trajectory["session_id"] = f"{session_id}:agent:{agent_id}"
    result.trajectory["trajectory_id"] = _trajectory_id(session_id, agent_id)
    result.trajectory["extra"] = {"claude": _evidence(source_meta, config)}
    result.trajectory["final_metrics"]["extra"]["total_turns"] = sum(
        r.message.get("role") == "assistant" and not r.message.get("synthetic")
        for r in records
    )
    result.total_events = len(events)
    result.unmapped_events = unmapped
    result.warnings.extend(warnings)
    links = []
    linked_calls = set()
    for step in result.trajectory["steps"]:
        calls = {call["tool_call_id"] for call in step.get("tool_calls", [])}
        for observation in (step.get("observation") or {}).get("results", []):
            call_id = observation.get("source_call_id")
            if call_id in calls and call_id in linked_agents:
                links.append((observation, linked_agents[call_id]))
                linked_calls.add(call_id)
    for call_id, child_id in linked_agents.items():
        if call_id in linked_calls:
            continue
        result.warnings.append(
            f"subagent {child_id}: no matching tool call {call_id}; link omitted"
        )
    return result, links


def _blocks(content):
    return (
        [{"type": "text", "text": content}]
        if isinstance(content, str)
        else content
        if isinstance(content, list)
        else []
        if content is None
        else [content]
    )


def _text(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _usage(raw, warnings, config):
    if not isinstance(raw, dict):
        return {}
    result = {}
    for source, target in (
        ("input_tokens", "uncached_input_tokens"),
        ("output_tokens", "output_tokens"),
        ("cache_read_input_tokens", "cache_read_tokens"),
        ("cache_creation_input_tokens", "cache_write_tokens"),
    ):
        value = raw.get(source)
        if value is None:
            continue
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            result[target] = value
        else:
            warnings.append(f"invalid Claude usage: {source}")
    result["claude"] = _evidence(raw, config)
    return result


def _merge_usage(previous, update):
    result = {**previous, **update}
    parts = [
        result.get(key)
        for key in ("uncached_input_tokens", "cache_read_tokens", "cache_write_tokens")
    ]
    if all(value is not None for value in parts):
        result["prompt_tokens"] = sum(parts)
    return result
