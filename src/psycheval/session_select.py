from __future__ import annotations

from datetime import datetime, timezone

from psycheval.adapters import adapter_for
from psycheval.adapters.base import SessionInfo, SessionListing


def inspect_adapter_sessions(adapter_id: str, path: str) -> SessionListing:
    adapter = adapter_for(adapter_id)
    inspect_sessions = getattr(adapter, "inspect_sessions", None)
    if callable(inspect_sessions):
        return inspect_sessions(path)
    list_sessions = getattr(adapter, "list_sessions", None)
    if not callable(list_sessions):
        raise ValueError(f"adapter {adapter_id} does not support session listing")
    return SessionListing(list(list_sessions(path)))


def resolve_session_selectors(
    adapter_id: str,
    path: str,
    selectors: list[str],
    *,
    sessions: list[SessionInfo] | None = None,
) -> list[str]:
    if sessions is None and any(s.startswith("#") or s.isdigit() for s in selectors):
        sessions = inspect_adapter_sessions(adapter_id, path).sessions
    available = sessions or []
    ids = {session.session_id for session in available}
    resolved = []
    for text in selectors:
        if not text.startswith("#") and (not text.isdigit() or text in ids):
            resolved.append(text)
            continue
        raw_index = text.removeprefix("#")
        if not raw_index.isdigit():
            raise ValueError(f"session index must be a positive integer: #{raw_index}")
        index = int(raw_index)
        if index < 1 or index > len(available):
            raise ValueError(
                f"session index out of range: #{index} (available sessions: {len(available)})"
            )
        resolved.append(available[index - 1].session_id)
    return resolved


def resolve_directory_session_paths(
    adapter_id: str, path: str, selectors: list[str]
) -> list[tuple[str, str]]:
    listing = inspect_adapter_sessions(adapter_id, path)
    if not listing.sessions:
        detail = "; ".join(listing.warnings)
        raise ValueError(
            f"no {adapter_id.capitalize()} sessions found in: {path}"
            + (f"; {detail}" if detail else "")
        )
    ids = (
        resolve_session_selectors(
            adapter_id, path, selectors, sessions=listing.sessions
        )
        if selectors
        else [listing.sessions[0].session_id]
    )
    sessions = {session.session_id: session for session in listing.sessions}
    resolved = []
    for identifier in ids:
        session = sessions.get(identifier)
        if session is None:
            raise ValueError(
                f"{adapter_id.capitalize()} session not found: {identifier}"
            )
        concrete = session.path or adapter_for(adapter_id).resolve_session_path(
            path, identifier
        )
        resolved.append((identifier, concrete))
    return resolved


def format_session_table(sessions: list[SessionInfo]) -> str:
    headers = ["#", "session_id", "updated_at (UTC)", "name"]
    rows = [
        [
            str(index),
            session.session_id,
            datetime.fromtimestamp(session.updated_at_ms / 1000, timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
            if session.updated_at_ms is not None
            else "-",
            session.name or "-",
        ]
        for index, session in enumerate(sessions, start=1)
    ]
    widths = [
        max(len(row[column]) for row in [headers, *rows])
        for column in range(len(headers))
    ]
    lines = [format_table_row(headers, widths)]
    lines.extend(format_table_row(row, widths) for row in rows)
    return "\n".join(lines) + "\n"


def format_table_row(row: list[str], widths: list[int]) -> str:
    return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))


def parse_session_selection(text: str, session_count: int) -> list[int]:
    stripped = text.strip().lower()
    if not stripped:
        return []
    if stripped == "all":
        return list(range(1, session_count + 1))
    selected: list[int] = []
    seen: set[int] = set()
    for raw_part in stripped.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            raw_start, raw_end = part.split("-", 1)
            start = parse_selection_index(raw_start, session_count)
            end = parse_selection_index(raw_end, session_count)
            if end < start:
                raise ValueError(f"invalid descending session range: {part}")
            indexes = range(start, end + 1)
        else:
            indexes = [parse_selection_index(part, session_count)]
        for index in indexes:
            if index not in seen:
                selected.append(index)
                seen.add(index)
    return selected


def parse_selection_index(text: str, session_count: int) -> int:
    if not text.isdigit():
        raise ValueError(f"session selection must use indexes, ranges, or all: {text}")
    index = int(text)
    if index < 1 or index > session_count:
        raise ValueError(
            f"session index out of range: {index} (available sessions: {session_count})"
        )
    return index
