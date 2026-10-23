"""Numeric metric identities and presentation, shared by catalog and exports."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from typing import Any, Mapping
from urllib.parse import quote, unquote

METRIC_LIMIT = 128
METRIC_SELECTION_LIMIT = 32
METRIC_KEY_BYTES = 128

# key, label, message key, unit, direction, Home default, Saved View, column
_BUILTINS = (
    ("score", "Reward", "reward", "", "higher", True, True, "score"),
    (
        "duration_ms",
        "Active Duration",
        "duration",
        "ms",
        "lower",
        True,
        True,
        "duration_ms",
    ),
    ("ttft_ms", "Avg TTFT", "avg_ttft", "ms", "lower", True, True, "ttft_ms"),
    ("tps", "Decode TPS", "decode_tps", "", "higher", True, True, "tps"),
    ("tokens", "Tokens", "tokens", "", "neutral", True, True, "tokens"),
    (
        "cache_hit_rate",
        "Cache Hit",
        "cache_hit",
        "ratio",
        "higher",
        True,
        True,
        "cache_hit_rate",
    ),
    ("turns", "Turns", "turns", "", "neutral", True, True, "turns"),
    (
        "model_duration_ms",
        "Model call duration",
        "model_call_duration",
        "ms",
        "lower",
        True,
        True,
        "",
    ),
    (
        "total_tool_calls",
        "Tool Calls",
        "tool_calls",
        "",
        "neutral",
        True,
        True,
        "total_tool_calls",
    ),
    (
        "tool_success_rate",
        "Tool Success Rate",
        "tool_success_rate",
        "ratio",
        "higher",
        True,
        True,
        "tool_success_rate",
    ),
    ("cost_usd", "Cost", "cost", "USD", "lower", False, False, "cost_usd"),
    (
        "tool_duration_ms",
        "Tool execution duration",
        "metric_tool_duration",
        "ms",
        "lower",
        False,
        False,
        "",
    ),
    (
        "other_duration_ms",
        "Other recorded duration",
        "metric_other_duration",
        "ms",
        "neutral",
        False,
        False,
        "",
    ),
    (
        "tests_passed",
        "Rules passed",
        "metric_tests_passed",
        "",
        "neutral",
        False,
        False,
        "",
    ),
    (
        "tests_total",
        "Rules total",
        "metric_tests_total",
        "",
        "neutral",
        False,
        False,
        "",
    ),
    (
        "test_pass_rate",
        "Rules passed / total",
        "metric_rule_rate",
        "ratio",
        "higher",
        False,
        False,
        "",
    ),
    (
        "total_prompt_tokens",
        "Prompt tokens",
        "metric_prompt_tokens",
        "",
        "neutral",
        False,
        False,
        "",
    ),
    (
        "total_completion_tokens",
        "Completion tokens",
        "metric_completion_tokens",
        "",
        "neutral",
        False,
        False,
        "",
    ),
    (
        "total_cached_tokens",
        "Cached tokens",
        "metric_cached_tokens",
        "",
        "neutral",
        False,
        False,
        "",
    ),
    ("total_steps", "Steps", "metric_steps", "", "neutral", False, False, ""),
    (
        "total_tool_errors",
        "Tool errors",
        "metric_tool_errors",
        "",
        "lower",
        False,
        False,
        "",
    ),
)
BUILTIN_IDS = tuple(item[0] for item in _BUILTINS)
DEFAULT_METRIC_IDS = tuple(item[0] for item in _BUILTINS if item[5])
SAVED_VIEW_METRIC_IDS = tuple(item[0] for item in _BUILTINS if item[6])
RESERVED_EXTRA_KEYS = frozenset(
    (*BUILTIN_IDS, "total_turns", "total_cost_usd", "model_inference", "usage")
)


def finite_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def custom_metric_id(namespace: str, key: str) -> str:
    if namespace not in {"atif.extra", "reward"} or not isinstance(key, str):
        raise ValueError("invalid metric namespace or key")
    if not key.strip() or any(unicodedata.category(c).startswith("C") for c in key):
        raise ValueError("metric key must be nonblank without control characters")
    if len(key.encode("utf-8")) > METRIC_KEY_BYTES:
        raise ValueError("metric key exceeds 128 UTF-8 bytes")
    return namespace + ":" + quote(key, safe="-._~")


def validate_metric_id_syntax(value: str) -> str:
    """Validate transport identities independently of the current registry."""
    if len(value) <= 128 and re.fullmatch(r"[a-z][a-z0-9_]*", value):
        return value
    namespace, sep, key = value.partition(":")
    try:
        if sep and custom_metric_id(namespace, unquote(key, errors="strict")) == value:
            return value
    except (ValueError, UnicodeError):
        pass
    raise ValueError(f"invalid metric ID: {value}")


def validate_metric_id(value: str) -> str:
    validate_metric_id_syntax(value)
    if value not in BUILTIN_IDS and ":" not in value:
        raise ValueError(f"unknown built-in metric ID: {value}")
    return value


def metric_descriptor(key: str) -> dict[str, Any]:
    validate_metric_id(key)
    builtin = next((item for item in _BUILTINS if item[0] == key), None)
    if builtin:
        _, label, message, unit, direction, default, saved, column = builtin
    else:
        label, message, unit, direction = (
            unquote(key.split(":", 1)[1]),
            "",
            "",
            "neutral",
        )
        default, saved, column = False, False, ""
        if key in {"reward:rule_score", "reward:llm_score"}:
            label = "Rule score" if key == "reward:rule_score" else "LLM Judge score"
            message = (
                "metric_rule_score"
                if key == "reward:rule_score"
                else "metric_llm_score"
            )
    return dict(
        key=key,
        label=label,
        message_key=message,
        unit=unit,
        direction=direction,
        default=default,
        saved_view=saved,
        column_key=column or key,
        column_default=bool(column),
        type={"ms": "duration", "ratio": "percent", "USD": "currency"}.get(
            unit, "number"
        ),
    )


def metric_descriptions(
    ids: list[str] | tuple[str, ...], overrides: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    overrides = overrides or {}
    descriptions = []
    for key in ids:
        descriptor = metric_descriptor(key)
        override = overrides.get(key)
        if override is not None:
            values = (
                override.model_dump(exclude_none=True)
                if hasattr(override, "model_dump")
                else dict(override)
            )
            descriptor.update(values)
            if "label" in values:
                descriptor["message_key"] = ""
            descriptor["type"] = {
                "ms": "duration",
                "ratio": "percent",
                "USD": "currency",
            }.get(descriptor["unit"], "number")
        descriptions.append(descriptor)
    diagnostics = [
        f"Metric configured but not discovered: {key}"
        for key in overrides
        if key not in ids
    ]
    revision = hashlib.sha256(
        json.dumps(
            [descriptions, diagnostics], ensure_ascii=False, sort_keys=True
        ).encode()
    ).hexdigest()
    return {
        "metric_descriptions": descriptions,
        "metric_revision": revision,
        "metric_diagnostics": diagnostics,
    }


def selected_metric_ids(value: Any) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) > METRIC_SELECTION_LIMIT
        or any(not isinstance(key, str) for key in value)
    ):
        raise ValueError("select at most 32 metric IDs")
    if len(set(value)) != len(value):
        raise ValueError("metric IDs must be unique")
    return [validate_metric_id_syntax(key) for key in value]
