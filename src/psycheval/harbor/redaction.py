"""Pure trajectory-content filtering; independent of ambient credentials."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|authorization|bearer|credential|password|secret|(?:^|[_-])(?:access[_-]?|refresh[_-]?|auth[_-]?)?token$)",
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
API_SECRET_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")
SECRET_VALUE_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    API_SECRET_RE,
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
