from __future__ import annotations

import io
import json
import os
import re
import zipfile
import zlib
from collections.abc import Mapping
from typing import Any

SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|authorization|bearer|credential|password|secret|token)",
    re.IGNORECASE,
)
STRONG_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|authorization|bearer|credential|password|secret)",
    re.IGNORECASE,
)
NUMERIC_METRIC_KEY_RE = re.compile(
    r"(tokens|token_count|cost|nanodollars|cache|billable|reasoning)",
    re.IGNORECASE,
)
SECRET_VALUE_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"(api[_-]?key|token|password|secret)=([^\s&]+)", re.IGNORECASE),
]


def redact_text(value: str) -> str:
    text = value
    for pattern in SECRET_VALUE_PATTERNS:
        if pattern.pattern.startswith("("):
            text = pattern.sub(lambda match: f"{match.group(1)}=<redacted>", text)
        else:
            text = pattern.sub("<redacted>", text)
    return text


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if SECRET_KEY_RE.search(str(key)):
                out[str(key)] = (
                    item if safe_numeric_metric(str(key), item) else "<redacted>"
                )
            else:
                out[str(key)] = redact_value(item)
        return out
    return value


def safe_numeric_metric(key: str, value: Any) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and NUMERIC_METRIC_KEY_RE.search(key) is not None
        and STRONG_SECRET_KEY_RE.search(key) is None
    )


_CREDENTIAL_FIELD = re.compile(
    r"api.?key|password|secret|(?:^|[_-])token$|access.?token|authorization", re.I
)
_JSON_STRING = re.compile(r'"(?:[^"\\]|\\[\s\S])*(?:"|\\?$)')


def redact_credentials(value):
    """Remove literal credential values; environment references remain readable."""
    if isinstance(value, dict):
        return {
            key: (
                "[redacted]"
                if _CREDENTIAL_FIELD.search(str(key))
                and item is not None
                and item != ""
                and not (isinstance(item, str) and is_credential_reference(item))
                else redact_credentials(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_credentials(item) for item in value]
    if isinstance(value, str) and not is_credential_reference(value):
        return sanitize_credentials(value)
    return value


def is_credential_reference(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"\$\{[A-Za-z_][A-Za-z0-9_]*\}|\{env:[A-Za-z_][A-Za-z0-9_]*\}", value
        )
    )


def sanitize_credentials(text: str) -> str:
    for key, value in os.environ.items():
        if len(value) >= 8 and re.search(r"KEY|TOKEN|SECRET|PASSWORD", key, re.I):
            text = text.replace(value, "[redacted]")
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{16,}\b", "[redacted]", text)
    return re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[redacted]", text)


def redact_retained_text(text: str) -> str:
    protected = sanitize_credentials(text)
    try:
        value = json.loads(text)
        redacted = redact_credentials(value)
        if redacted != value:
            return json.dumps(redacted, ensure_ascii=False, indent=2)
        return protected
    except (ValueError, RecursionError):
        pass

    def skip_space(position):
        while position < len(protected) and protected[position].isspace():
            position += 1
        return position

    parts = []
    cursor = 0
    tokens = iter(_JSON_STRING.finditer(protected))
    for token in tokens:
        colon = skip_space(token.end())
        if colon >= len(protected) or protected[colon] != ":":
            continue
        try:
            key = json.loads(token[0])
        except ValueError:
            continue
        if not _CREDENTIAL_FIELD.search(key):
            continue
        start = skip_space(colon + 1)
        if start >= len(protected) or protected[start] != '"':
            continue
        value_token = next(tokens)
        try:
            value = json.loads(value_token[0])
            if is_credential_reference(value):
                continue
        except ValueError:
            pass
        parts.extend((protected[cursor:start], '"[redacted]"'))
        cursor = value_token.end()
    parts.append(protected[cursor:])
    return "".join(parts)


def protect_retained_bytes(content: bytes, *, text: bool, limit: int) -> bytes:
    """Protect shared responses; never rewrite the retained source."""
    if text:
        try:
            return redact_retained_text(content.decode("utf-8")).encode("utf-8")
        except UnicodeDecodeError:
            pass

    def check(data):
        decoded = data.decode("utf-8", errors="replace")
        if redact_retained_text(decoded) != decoded:
            raise ValueError("binary artifact contains a recognized credential")

    check(content)
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            remaining = limit
            entries = archive.infolist()
            if len(entries) > 10_000:
                raise ValueError("archive exceeds credential inspection limit")
            for entry in entries:
                if entry.file_size > remaining:
                    raise ValueError("archive exceeds credential inspection limit")
                try:
                    with archive.open(entry) as stream:
                        data = stream.read(remaining + 1)
                except (
                    RuntimeError,
                    zipfile.BadZipFile,
                    NotImplementedError,
                    zlib.error,
                    EOFError,
                    OSError,
                ) as exc:
                    raise ValueError(
                        "archive cannot be inspected for credentials"
                    ) from exc
                remaining -= len(data)
                if remaining < 0:
                    raise ValueError("archive exceeds credential inspection limit")
                check(data)
    return content
