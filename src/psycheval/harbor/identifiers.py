"""Shared path-safe identifiers for Harbor registrations and run plans."""

from __future__ import annotations

import re

HARBOR_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?$")


def validate_harbor_id(value: object, *, kind: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"harbor {kind} id must be a string")
    identifier = value.strip()
    if HARBOR_ID_RE.fullmatch(identifier) is None:
        raise ValueError(f"harbor {kind} id must be a lowercase path-safe identifier")
    return identifier
