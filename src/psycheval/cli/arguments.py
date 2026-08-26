from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CliArgs:
    command: str
    scenario: str | None = None
    root: str | None = None
    config: str | None = None
    adapter: tuple[str, ...] | None = None
    path: tuple[str, ...] | None = None
    db: tuple[str, ...] | None = None
    session_id: tuple[str, ...] | None = None
    max_content_chars: int | None = None
    output: object | None = None
    agent_name: str | None = None
    agent_version: str | None = None
    model: str | None = None
    no_redact: bool = False
    mode: str = "inspect"
    list_sessions: bool = False
    list_interactive: bool = False
    note: tuple[str, ...] = ()
    source_alias: tuple[str, ...] = ()
    head: int | None = None
    tail: int | None = None
    top: int | None = None
    steps: tuple[str, ...] | None = None
    tool_call: tuple[str, ...] | None = None
    source: tuple[int, ...] | None = None
    source_ref: str | None = None
    json: bool = False
    host: str = "127.0.0.1"
    port: int | None = None
