"""Office-style artifact resolution with bounded, contained UTF-8 reads."""

from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path

from ._judge_config import MAX_CONFIG_BYTES, JudgeConfig, relative_evidence_path

# Owned here for source-copy independence; a reference parity test checks Office's
# shared/verifier/llm.py when the local reference checkout is available.
TEXT_TYPES = frozenset(
    "txt text md markdown csv json yaml yml html htm xml py js ts tsx jsx java go "
    "rs cpp c h hpp css scss sql toml ini log source".split()
)


class EvidenceUnavailable(Exception):
    """Whole-Judge evidence failure; retain rule credit and diagnostic reason."""


def _read_bytes(root: Path, relative: str, limit: int) -> bytes:
    relative_evidence_path(relative, label="evidence path")
    parts = Path(relative).parts
    path = root / relative
    for part in (root, *(root.joinpath(*parts[:n]) for n in range(1, len(parts) + 1))):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(
            info, "st_file_attributes", 0
        ) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError("linked evidence is not supported")
    if not path.resolve().is_relative_to(root.resolve()) or not stat.S_ISREG(
        path.stat().st_mode
    ):
        raise ValueError("evidence must be a contained regular file")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise EvidenceUnavailable("evidence read limit exceeded")
    return raw


def _manifest(root: Path) -> dict[str, dict]:
    def mapping(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate manifest JSON key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("nonfinite manifest number")

    try:
        try:
            raw = _read_bytes(root, "artifact_manifest.json", MAX_CONFIG_BYTES)
        except FileNotFoundError:
            return {}
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=mapping,
            parse_constant=invalid_constant,
        )
        if not isinstance(value, dict) or not isinstance(value.get("artifacts"), list):
            raise ValueError("manifest must contain an artifacts list")
        records = {}
        for record in value["artifacts"]:
            if not isinstance(record, dict):
                raise ValueError("manifest records must be objects")
            identity = record.get("id")
            if not isinstance(identity, str) or not identity.strip():
                raise ValueError("manifest records require nonempty IDs")
            if identity in records:
                raise ValueError("duplicate manifest artifact ID")
            records[identity] = record
        return records
    except (OSError, ValueError, EvidenceUnavailable, RecursionError) as exc:
        raise EvidenceUnavailable(
            f"artifact_manifest.json unavailable: {type(exc).__name__}: {exc}"
        ) from exc


def read_evidence(config: JudgeConfig, root: Path, max_bytes: int) -> tuple[dict, dict]:
    """Read prompt evidence and its content-free diagnostic index together."""
    records = _manifest(root)
    evidence = {}
    diagnostics = {}
    remaining = max_bytes
    for artifact in config.artifacts:
        record = records.get(artifact.id)
        status, text, error = "missing", None, None
        text_path, byte_count, sha256 = None, None, None
        relative = None
        if record is not None:
            status = record.get("extract_status")
            if status == "ok":
                relative = record.get("text_path")
                if not isinstance(relative, str) or not relative.strip():
                    status, error = "error", "missing text_path for extracted evidence"
            elif status != "missing":
                status, error = "error", "artifact extraction failed"
        elif artifact.type.lower().lstrip(".") in TEXT_TYPES:
            relative = artifact.path
        else:
            error = f"artifact type {artifact.type!r} requires a manifest record with extracted text"
        if relative is not None and error is None:
            try:
                text_path = relative_evidence_path(relative, label="evidence path")
                raw = _read_bytes(root, text_path, remaining)
                remaining -= len(raw)
                text = raw.decode("utf-8")
                byte_count, sha256 = len(raw), hashlib.sha256(raw).hexdigest()
                status = "ok"
            except EvidenceUnavailable as exc:
                raise EvidenceUnavailable(
                    "declared evidence exceeds PEVAL_JUDGE_MAX_EVIDENCE_BYTES"
                ) from exc
            except (OSError, ValueError) as exc:
                # A manifest promises an extracted file; its absence is an error.
                status = (
                    "missing"
                    if record is None and isinstance(exc, FileNotFoundError)
                    else "error"
                )
                origin = "manifest text_path" if record else "declared artifact path"
                error = f"{origin}: {type(exc).__name__}"
                if isinstance(exc, ValueError) and not isinstance(exc, UnicodeError):
                    error += f": {exc}"
        state = {
            "error": error,
            "required": artifact.required,
            "extract_status": status,
        }
        evidence[artifact.id] = {"text": text, **state}
        diagnostics[artifact.id] = {
            **state,
            "text_path": text_path,
            "byte_count": byte_count,
            "sha256": sha256,
        }
    return evidence, diagnostics
