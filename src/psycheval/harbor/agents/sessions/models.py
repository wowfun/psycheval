from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, field_validator


@dataclass(frozen=True)
class MessageRecord:
    message: dict[str, Any]
    usage: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    accounting: dict[str, Any] | None = None
    session_seq: int | None = None
    source_session_id: str | None = None


class DbMapping(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        validate_default=True,
        hide_input_in_errors=True,
    )
    messages_table: str = "messages"
    session_id_column: str = "session_id"
    sequence_column: str = "session_seq"
    message_column: str = "message_json"
    usage_column: str = "usage_json"
    metadata_column: str = "metadata_json"

    @field_validator("*")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ValueError(f"unsafe SQL identifier: {value}")
        return value


@dataclass(frozen=True)
class ConversionOptions:
    agent_name: str | None = None
    agent_version: str = "0.1.0"
    model: str | None = None
    max_content_chars: int = 128 * 1024
    redact: bool = True
    db: DbMapping = field(default_factory=DbMapping)
    adapter_options: dict[str, Any] = field(default_factory=dict)
    session_root: str | None = None


ACTIVE_DURATION_FALLBACK_CAP_MS = 600_000
TIMESTAMP_SEMANTICS_ORDER_ONLY = "order_only"


def timestamp_fallback_duration_ms(
    start_ms: int | None,
    end_ms: int | None,
) -> int | None:
    if start_ms is None or end_ms is None:
        return None
    duration = end_ms - start_ms
    if 0 <= duration <= ACTIVE_DURATION_FALLBACK_CAP_MS:
        return duration
    return None


@dataclass
class ToolMeta:
    tool_call_id: str
    status: str | None = None
    title: str | None = None
    timestamp_ms: int | None = None
    generation_duration_ms: int | None = None
    execution_duration_ms: int | None = None
    execution_duration_source: str | None = None
    truncated: bool = False


@dataclass
class ObservationMeta:
    source_call_id: str | None = None
    status: str | None = None
    title: str | None = None
    timestamp_ms: int | None = None
    tool_error: bool = False
    truncated: bool = False


@dataclass
class StepMeta:
    step_id: int
    source: str | None = None
    tool_calls: list[ToolMeta] = field(default_factory=list)
    observations: list[ObservationMeta] = field(default_factory=list)
    tool_error: bool = False
    timestamp_ms: int | None = None
    elapsed_ms: int | None = None
    duration_ms: int | None = None
    duration_source: str | None = None
    truncated: bool = False


@dataclass
class ConversionResult:
    trajectory: dict[str, Any]
    steps_meta: list[StepMeta]
    warnings: list[str]
    total_events: int
    unmapped_events: int
    started_at_ms: int | None
    finished_at_ms: int | None
    timestamp_semantics: str | None = None
    subagent_results: list[ConversionResult] = field(default_factory=list)


@dataclass(frozen=True)
class SessionInfo:
    session_id: str
    name: str | None = None
    updated_at_ms: int | None = None
    path: str | None = None


@dataclass
class SessionListing:
    sessions: list[SessionInfo]
    warnings: list[str] = field(default_factory=list)


class Adapter(Protocol):
    agent_id: str


class RecordAdapter(Adapter, Protocol):
    def convert(
        self, records: list[MessageRecord], config: ConversionOptions
    ) -> ConversionResult: ...


class PathAdapter(Adapter, Protocol):
    def convert_path(
        self, path: str, config: ConversionOptions
    ) -> ConversionResult: ...


class DirectorySessionAdapter(PathAdapter, Protocol):
    def list_sessions(self, path: str) -> list[SessionInfo]: ...

    def resolve_session_path(self, path: str, session_id: str | None) -> str: ...


class DbAdapter(Adapter, Protocol):
    def convert_db(
        self,
        path: str,
        session_id: str | None,
        config: ConversionOptions,
    ) -> ConversionResult: ...


class SessionListAdapter(Adapter, Protocol):
    def list_sessions(self, path: str) -> list[SessionInfo]: ...
