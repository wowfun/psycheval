"""Local WorkBuddy Office bundle used by CLI and downstream tests."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

SPECIAL_TASK = "recruiting-search-skill-mock-mcp-hardened"


def write_office_bundle(root: Path) -> tuple[str, ...]:
    names = tuple([f"office-{index:02d}" for index in range(49)] + [SPECIAL_TASK])
    (root / "shared" / "verifier").mkdir(parents=True)
    for name in ("plugin.py", "manifest.py", "scoring.py"):
        (root / "shared" / "verifier" / name).write_text("# fixture\n")
    (root / "dataset.toml").write_text(
        """[dataset]
id = "wb-bench-office-v1.0"
schema = "workbuddy.dataset.v1"
version = "1.0"
task_count = 50

[verifier]
schema = "workbuddy.verifier.v1"
engine = "composite"

[layout]
task_root = "tasks"
environment = "environment"
workspace_archive = "environment/workspace.tar.gz"
tests = "tests"
grading_tests = "tests/grading"
gold = "tests/gold"
judge_config = "tests/judge.yaml"
""",
        encoding="utf-8",
    )
    for name in names:
        task = root / "tasks" / name
        (task / "environment").mkdir(parents=True)
        (task / "tests").mkdir()
        (task / "tests" / "test.sh").write_text("#!/bin/sh\nexit 0\n")
        (task / "instruction.md").write_text(f"Complete {name}.\n")
        (task / "task.toml").write_text(
            f'schema_version = "1.3"\n[task]\nname = "workbuddy/{name}"\n',
            encoding="utf-8",
        )
        archive = task / "environment" / "workspace.tar.gz"
        if name == SPECIAL_TASK:
            payload = b"---\nname: recruiting_search\n---\nUse the MCP.\n"
            info = tarfile.TarInfo("agent_pack/skills/recruiting_search/SKILL.md")
            info.size = len(payload)
            with tarfile.open(archive, "w:gz") as stream:
                stream.addfile(info, io.BytesIO(payload))
        else:
            archive.write_bytes(b"fixture")
    return names
