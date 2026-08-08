from __future__ import annotations

from peval_py_test_support import FIXTURES as FIXTURES
from peval_py_test_support import MessageRecord as MessageRecord
from peval_py_test_support import Path as Path
from peval_py_test_support import ReportSession as ReportSession
from peval_py_test_support import ToolConfig as ToolConfig
from peval_py_test_support import build_multi_report as build_multi_report
from peval_py_test_support import build_report as build_report
from peval_py_test_support import convert_db as convert_db
from peval_py_test_support import convert_records as convert_records
from peval_py_test_support import (
    create_hermes_log_timing_home as create_hermes_log_timing_home,
)
from peval_py_test_support import (
    create_opencode_event_timing_db as create_opencode_event_timing_db,
)
from peval_py_test_support import json as json
from peval_py_test_support import load_asset_text as load_asset_text
from peval_py_test_support import patch as patch
from peval_py_test_support import re as re
from peval_py_test_support import read_jsonl as read_jsonl
from peval_py_test_support import render_html as render_html
from peval_py_test_support import render_serve_html as render_serve_html
from peval_py_test_support import script_json as script_json
from peval_py_test_support import shutil as shutil
from peval_py_test_support import subprocess as subprocess
from peval_py_test_support import tempfile as tempfile
from peval_py_test_support import unittest as unittest


def compact_css_text(value: str) -> str:
    return re.sub(r"\s+", "", value).replace(";}", "}")


def write_cached_analysis(
    root: Path,
    *,
    eval_slug: str = "default",
    agent_id: str = "agent-a",
    session_id: str = "common_session",
    cell_key: str = "session_t001",
    summary: str = "Cached analysis summary.",
    extra: dict | None = None,
) -> Path:
    path = (
        root / "runs" / eval_slug / agent_id / session_id / cell_key / "analysis.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "trial_name": session_id,
        "summary": summary,
        "checks": {},
    }
    if extra:
        payload.update(extra)
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    return path


def write_cached_markdown(
    root: Path,
    *,
    eval_slug: str = "default",
    agent_id: str = "agent-a",
    session_id: str = "common_session",
    cell_key: str = "session_t001",
    markdown: str = "## Finding\n\n- Cached markdown report.",
) -> Path:
    path = root / "runs" / eval_slug / agent_id / session_id / cell_key / "analysis.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def write_cached_note(
    root: Path,
    *,
    eval_slug: str = "default",
    agent_id: str = "agent-a",
    session_id: str = "common_session",
    cell_key: str = "session_t001",
    markdown: str = "Manual cell note.",
) -> Path:
    path = root / "runs" / eval_slug / agent_id / session_id / cell_key / "notes.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path
