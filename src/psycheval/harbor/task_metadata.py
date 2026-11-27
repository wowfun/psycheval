"""Read-only custom Task [metadata] contract, validation, and column IDs."""

from __future__ import annotations

import json
import math
import unicodedata
from collections.abc import Mapping
from datetime import date, datetime, time
from typing import Any
from urllib.parse import quote, unquote

RESERVED_TASK_METADATA_KEYS = frozenset(("category", "difficulty", "source_case"))
CUSTOM_COLUMN_PREFIX = "meta:"

MAX_CUSTOM_METADATA_KEYS = 64
MAX_CUSTOM_METADATA_BYTES = 64 * 1024
MAX_CUSTOM_KEY_BYTES = 128
MAX_CUSTOM_STRING_BYTES = 16 * 1024
MAX_CUSTOM_LIST_ITEMS = 128
MAX_CUSTOM_LIST_ITEM_BYTES = 256
_MAX_METADATA_DEPTH = 16
_TOML_INT_MIN = -(1 << 63)
_TOML_INT_MAX = (1 << 63) - 1


def _has_control_chars(value: str) -> bool:
    return any(unicodedata.category(char) == "Cc" for char in value)


def _has_disallowed_text_controls(value: str) -> bool:
    return any(
        unicodedata.category(char) == "Cc" and char not in {"\t", "\n", "\r"}
        for char in value
    )


def validate_custom_metadata_key(key: Any) -> str:
    """Validate one custom [metadata] key in task.toml."""
    if not isinstance(key, str):
        raise ValueError("Custom column key must be a string")
    if not key or key != key.strip():
        raise ValueError("Custom column key must be nonblank without outer spaces")
    if _has_control_chars(key):
        raise ValueError("Custom column key must not contain control characters")
    if len(key.encode("utf-8")) > MAX_CUSTOM_KEY_BYTES:
        raise ValueError(
            f"Custom column key exceeds {MAX_CUSTOM_KEY_BYTES} UTF-8 bytes"
        )
    if key in RESERVED_TASK_METADATA_KEYS:
        raise ValueError(f"Metadata key is reserved: {key}")
    return key


def custom_column_id(key: str) -> str:
    """Return the canonical collision-free column/grouping ID for a metadata key."""
    validated = validate_custom_metadata_key(key)
    return CUSTOM_COLUMN_PREFIX + quote(validated, safe="-._~")


def parse_custom_column_id(column_id: Any) -> str:
    """Decode and validate a canonical meta:<encoded> column or grouping ID."""
    if not isinstance(column_id, str) or not column_id.startswith(CUSTOM_COLUMN_PREFIX):
        raise ValueError(f"Invalid custom column ID: {column_id}")
    encoded = column_id[len(CUSTOM_COLUMN_PREFIX) :]
    try:
        decoded = unquote(encoded, errors="strict")
    except UnicodeError as exc:
        raise ValueError(f"Invalid custom column ID: {column_id}") from exc
    validated = validate_custom_metadata_key(decoded)
    if custom_column_id(validated) != column_id:
        raise ValueError(f"Non-canonical custom column ID: {column_id}")
    return validated


def is_custom_column_id(value: Any) -> bool:
    try:
        parse_custom_column_id(value)
    except ValueError:
        return False
    return True


def validate_custom_metadata_value(value: Any) -> Any:
    """Validate a writable custom [metadata] value; None clears the key."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value < _TOML_INT_MIN or value > _TOML_INT_MAX:
            raise ValueError("Custom number exceeds 64-bit integer range")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Custom number must be finite")
        return value
    if isinstance(value, str):
        if not value.strip():
            raise ValueError("Custom text value must not be blank; use null to clear")
        if _has_disallowed_text_controls(value):
            raise ValueError("Custom text value contains invalid control characters")
        if len(value.encode("utf-8")) > MAX_CUSTOM_STRING_BYTES:
            raise ValueError(
                f"Custom text value exceeds {MAX_CUSTOM_STRING_BYTES} UTF-8 bytes"
            )
        return value
    if isinstance(value, list):
        if not value:
            raise ValueError("Custom list value must not be empty; use null to clear")
        if len(value) > MAX_CUSTOM_LIST_ITEMS:
            raise ValueError(f"Custom list value exceeds {MAX_CUSTOM_LIST_ITEMS} items")
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("Custom list items must be strings")
            text = item.strip()
            if not text:
                raise ValueError("Custom list items must not be blank")
            if _has_control_chars(text):
                raise ValueError(
                    "Custom list items must not contain control characters"
                )
            if len(text.encode("utf-8")) > MAX_CUSTOM_LIST_ITEM_BYTES:
                raise ValueError(
                    f"Custom list item exceeds {MAX_CUSTOM_LIST_ITEM_BYTES} UTF-8 bytes"
                )
            if text not in seen:
                seen.add(text)
                normalized.append(text)
        return normalized
    raise ValueError(
        "Custom metadata value must be text, number, boolean, string list, or null"
    )


def _json_safe_value(value: Any, *, depth: int = 0) -> Any:
    if depth > _MAX_METADATA_DEPTH:
        raise ValueError("metadata value exceeds nesting depth limit")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("metadata number must be finite")
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe_value(item, depth=depth + 1) for item in value]
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe_value(item, depth=depth + 1)
            for key, item in value.items()
        }
    return str(value)


def extract_custom_metadata(
    metadata: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    """Project non-reserved [metadata] entries into bounded JSON-safe values."""
    if not metadata or not isinstance(metadata, Mapping):
        return {}, []
    projected: dict[str, Any] = {}
    diagnostics: list[str] = []
    used_bytes = 2  # "{}"
    for raw_key, raw_value in metadata.items():
        if raw_key in RESERVED_TASK_METADATA_KEYS:
            continue
        try:
            key = validate_custom_metadata_key(raw_key)
        except ValueError as exc:
            diagnostics.append(f"metadata key ignored ({exc})")
            continue
        if len(projected) >= MAX_CUSTOM_METADATA_KEYS:
            diagnostics.append(
                f"custom metadata exceeds {MAX_CUSTOM_METADATA_KEYS} keys; extra keys omitted"
            )
            break
        try:
            safe_value = _json_safe_value(raw_value)
            encoded_entry = json.dumps(
                {key: safe_value},
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            diagnostics.append(f"metadata.{key} ignored ({exc})")
            continue
        entry_bytes = len(encoded_entry) - 1  # approximate comma + key:value overhead
        if used_bytes + entry_bytes > MAX_CUSTOM_METADATA_BYTES:
            diagnostics.append(
                f"metadata.{key} omitted (custom metadata exceeds {MAX_CUSTOM_METADATA_BYTES} bytes)"
            )
            continue
        used_bytes += entry_bytes
        projected[key] = safe_value
    return projected, diagnostics


def _scalar_group_token(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return str(int(value)) if value.is_integer() else str(value)
    if isinstance(value, str):
        return value if value.strip() else None
    if isinstance(value, (Mapping, list)):
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    text = str(value)
    return text if text.strip() else None


def custom_metadata_group_keys(value: Any) -> list[str | None]:
    """Return Task Summary grouping keys for one Task's custom metadata value."""
    if isinstance(value, list):
        keys: list[str | None] = []
        seen: set[str] = set()
        for item in value:
            token = _scalar_group_token(item)
            if token is not None and token not in seen:
                seen.add(token)
                keys.append(token)
        return keys or [None]
    return [_scalar_group_token(value)]
