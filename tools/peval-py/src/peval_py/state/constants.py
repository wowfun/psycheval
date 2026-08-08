from __future__ import annotations

STATE_SCHEMA_VERSION = 1
SOURCE_STATE_DIR = ".peval"
SOURCE_STATE_FILENAME = "state.json"
HARBOR_LINK_FILENAME = "harbor-link.json"
HARBOR_LINK_SCHEMA_VERSION = 1
SERVE_LOG_RELATIVE_PATH = "logs/peval-py-serve.jsonl"
UPLOAD_LIMIT_BYTES = 20 * 1024 * 1024
REFRESH_LOG_LIMIT = 200
SOURCE_STATUS_MISSING = "missing"
SOURCE_STATUS_OK = "ok"
TRIAL_CELL_SIDECARS = ("analysis.json", "analysis.md", "notes.md")
