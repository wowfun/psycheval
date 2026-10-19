"""Shared report/display timing classification, independent of evidence producers."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

_CONTRACT = json.loads(
    files("psycheval.assets")
    .joinpath("web/timing-sources.json")
    .read_text(encoding="utf-8")
)


def timing_source(source: Any) -> dict[str, Any]:
    name = str(source or "").lower()
    family = next(
        (item for item in _CONTRACT["families"] if name.startswith(item["prefix"])), {}
    )
    return {**family, **_CONTRACT["sources"].get(name, {})}


def timestamp_fallback_allowed(timestamp_semantics: str | None) -> bool:
    return (
        str(timestamp_semantics or "").lower()
        not in _CONTRACT["non_duration_timestamps"]
    )
