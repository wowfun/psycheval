"""Application-owned adapter dispatch and configuration translation."""

from __future__ import annotations

from psycheval.adapters import adapter_for
from psycheval.config import ToolConfig
from psycheval.harbor.agents.sessions.conversion import (
    convert_atif_json_path,
    finalize_atif_conversion,
)
from psycheval.harbor.agents.sessions.models import ConversionResult, MessageRecord
from psycheval.harbor.agents.sessions.sources import read_jsonl, read_sqlite_messages


def convert_records(
    records: list[MessageRecord], config: ToolConfig, *, session_hint: str | None = None
) -> ConversionResult:
    adapter = adapter_for(config.adapter)
    convert = getattr(adapter, "convert", None)
    if not callable(convert):
        raise ValueError(f"adapter {config.adapter} does not support record input")
    return finalize_atif_conversion(
        convert(records, config.conversion_options()), session_hint
    )


def convert_path(
    path: str, config: ToolConfig, *, session_hint: str | None = None
) -> ConversionResult:
    atif = convert_atif_json_path(path)
    if atif is not None:
        return atif
    adapter = adapter_for(config.adapter)
    adapter_convert_path = getattr(adapter, "convert_path", None)
    if callable(adapter_convert_path):
        return finalize_atif_conversion(
            adapter_convert_path(path, config.conversion_options()), session_hint
        )
    convert = getattr(adapter, "convert", None)
    if not callable(convert):
        raise ValueError(f"adapter {config.adapter} does not support path input")
    return finalize_atif_conversion(
        convert(read_jsonl(path), config.conversion_options()), session_hint
    )


def convert_db(
    path: str,
    session_id: str | None,
    config: ToolConfig,
) -> ConversionResult:
    adapter = adapter_for(config.adapter)
    adapter_convert_db = getattr(adapter, "convert_db", None)
    if callable(adapter_convert_db):
        return finalize_atif_conversion(
            adapter_convert_db(path, session_id, config.conversion_options()),
            session_id,
        )
    if not session_id:
        raise ValueError(f"adapter {config.adapter} requires --session-id for DB input")
    convert = getattr(adapter, "convert", None)
    if not callable(convert):
        raise ValueError(f"adapter {config.adapter} does not support DB input")
    return finalize_atif_conversion(
        convert(
            read_sqlite_messages(path, session_id, config.db),
            config.conversion_options(),
        ),
        session_id,
    )
