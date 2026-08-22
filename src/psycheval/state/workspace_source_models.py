from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psycheval.state.harbor_evidence import HarborEvidence

HARBOR_SOURCE_KIND = "harbor-trial"
HARBOR_ADAPTER = "harbor"
HARBOR_OVERLAY_SCHEMA_VERSION = 1
HARBOR_OVERLAY_ROOT = "harbor"
HARBOR_JSON_SOURCE_FILES = (
    "agent/trajectory.json",
    "config.json",
    "lock.json",
    "result.json",
)
HARBOR_OPENCODE_TELEMETRY_FILES = (
    "agent/opencode/xdg-data/opencode/opencode.db",
    "agent/opencode/xdg-data/opencode/opencode.db-wal",
    "agent/opencode/xdg-data/opencode/opencode.db-shm",
)
HARBOR_PSYCHEVO_TELEMETRY_FILES = (
    "agent/psychevo-state.db",
    "agent/psychevo-state.db-wal",
    "agent/psychevo-state.db-shm",
)
HARBOR_HERMES_TELEMETRY_FILES = ("agent/hermes-session.jsonl",)
HARBOR_ANALYSIS_MD_FILE = "artifacts/logs/analysis.md"
HARBOR_SOURCE_FILES = (
    HARBOR_JSON_SOURCE_FILES
    + HARBOR_OPENCODE_TELEMETRY_FILES
    + HARBOR_PSYCHEVO_TELEMETRY_FILES
    + HARBOR_HERMES_TELEMETRY_FILES
)
HARBOR_OVERLAY_FILES = (
    "state.json",
    "notes.md",
    "analysis.json",
    "analysis.md",
)
HARBOR_OVERLAY_STATE_FIELDS = frozenset(
    {
        "schema_version",
        "active",
        "source_alias",
        "source_category",
        "source_tags",
    }
)
LOCAL_FINGERPRINT_FILES = (
    "agent/trajectory.json",
    "agent/trajectory_meta.json",
    ".peval/state.json",
    "notes.md",
    "analysis.json",
    "analysis.md",
)


@dataclass(frozen=True)
class SourceCandidate:
    source_ref: str
    kind: str
    path: Path
    fingerprint: str
    source_key: str | None = None
    mount_id: str | None = None
    job_name: str | None = None
    trial_name: str | None = None
    diagnostic: str | None = None
    missing: bool = False
    multi_step: bool = False
    containment_root: Path | None = None
    task_paths: tuple[str, ...] = ()
    harbor_evidence: HarborEvidence | None = None
    harbor_analysis_relative_path: str | None = None
    data_path: Path | None = None
    step_name: str | None = None
    step_index: int | None = None
    step_count: int | None = None
    step_result: dict[str, Any] | None = None
    trial_result: dict[str, Any] | None = None
    entry_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceDocument:
    source_ref: str
    source_key: str
    source: dict[str, Any]
    trajectory: dict[str, Any] | None
    meta: dict[str, Any] | None
    fingerprint: str
    updated_at_ms: int
    input_bytes: int
    readable: bool
    refreshable: bool
    snapshot: bool
    active: bool
    last_status: str
    last_error: str | None
    harbor_analysis_markdown: str | None = None
    harbor_analysis_relative_path: str | None = None


@dataclass(frozen=True)
class HarborTelemetry:
    steps: list[dict[str, Any]]
    duration_ms: int | None
    final_metrics: dict[str, Any]
    revision: str
