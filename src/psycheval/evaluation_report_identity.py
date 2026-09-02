from __future__ import annotations

import hashlib


def evaluation_report_ref(source_ref: str) -> str:
    normalized = str(source_ref or "").strip()
    if not normalized:
        raise ValueError("evaluation report source reference must not be empty")
    return "analysis:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


__all__ = ["evaluation_report_ref"]
