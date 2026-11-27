"""Format-preserving [metadata] mutations for native Harbor task.toml files."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import tomlkit
from harbor.models.task.config import TaskConfig
from tomlkit.exceptions import ConvertError, TOMLKitError
from tomlkit.items import Comment

from psycheval.harbor.task_metadata import (
    extract_custom_metadata,
    validate_custom_metadata_key,
    validate_custom_metadata_value,
)


def _same_typed_value(existing: Any, candidate: Any) -> bool:
    if type(existing) is not type(candidate):
        return False
    if isinstance(existing, list):
        return len(existing) == len(candidate) and all(
            _same_typed_value(left, right) for left, right in zip(existing, candidate)
        )
    return existing == candidate


def _table_has_comments(table: Any) -> bool:
    body = getattr(getattr(table, "value", None), "body", None)
    if not body:
        return False
    return any(isinstance(item, Comment) for _, item in body)


def update_task_toml_metadata(
    content: bytes,
    key: str,
    value: Any,
    *,
    overwrite: bool = True,
    max_bytes: int = 2 * 1024 * 1024,
) -> tuple[bytes, bool]:
    """Update or remove one custom [metadata] key while preserving TOML formatting.

    Returns ``(new_bytes, changed)``. Raises ``ValueError`` on invalid keys,
    values, encodings, syntax, or post-edit Harbor TaskConfig validation failures.
    """
    validated_key = validate_custom_metadata_key(key)
    validated_value = validate_custom_metadata_value(value)
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("task.toml must be UTF-8 text") from exc
    try:
        document = tomlkit.parse(text)
    except TOMLKitError as exc:
        raise ValueError(f"task.toml could not be parsed: {exc}") from exc

    metadata = document.get("metadata")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise ValueError("task.toml [metadata] must be a TOML table")

    if validated_value is None:
        if metadata is None or validated_key not in metadata:
            return content, False
        del metadata[validated_key]
        if len(metadata) == 0 and not _table_has_comments(metadata):
            del document["metadata"]
    else:
        if metadata is not None and validated_key in metadata:
            if not overwrite:
                return content, False
            raw_existing = metadata[validated_key]
            unwrapped = (
                raw_existing.unwrap()
                if hasattr(raw_existing, "unwrap")
                else raw_existing
            )
            if _same_typed_value(unwrapped, validated_value):
                return content, False
        if metadata is None:
            metadata = tomlkit.table()
            document["metadata"] = metadata
        try:
            metadata[validated_key] = tomlkit.item(validated_value)
        except ConvertError as exc:
            raise ValueError(f"Value cannot be encoded in TOML: {exc}") from exc

    rendered = tomlkit.dumps(document)
    eol = (
        "\r\n"
        if "\r\n" in text and text.count("\r\n") * 2 >= text.count("\n")
        else "\n"
    )
    rendered = rendered.replace("\r\n", "\n").replace("\r", "\n")
    if text.endswith(("\r\n", "\n")) and rendered and not rendered.endswith("\n"):
        rendered += "\n"
    if eol == "\r\n":
        rendered = rendered.replace("\n", "\r\n")
    rendered_bytes = rendered.encode("utf-8")
    if len(rendered_bytes) > max_bytes:
        raise ValueError("Updated task.toml exceeds the text file size limit")

    try:
        config = TaskConfig.model_validate_toml(rendered)
    except ValueError as exc:
        raise ValueError(
            f"Updated task.toml is not a valid Harbor Task: {exc}"
        ) from exc
    for field in ("difficulty", "category"):
        if field in config.metadata:
            label = config.metadata[field]
            if not isinstance(label, str) or not label.strip():
                raise ValueError(f"metadata.{field} must be a nonempty string")
    if validated_value is not None:
        projected, diagnostics = extract_custom_metadata(config.metadata)
        if validated_key not in projected:
            detail = (
                diagnostics[-1] if diagnostics else "custom metadata limit exceeded"
            )
            raise ValueError(detail)

    return rendered_bytes, True
