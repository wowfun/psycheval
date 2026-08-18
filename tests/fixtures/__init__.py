from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path
from typing import Any


def load_pbench_trajectory(
    fixture_dir: Path,
    instruction: str,
    artifacts_dir: Path,
) -> dict[str, Any]:
    """Load one Task-owned ATIF fixture and materialize its artifacts."""
    trajectory = json.loads(
        (fixture_dir / "trajectory.json").read_text(encoding="utf-8")
    )
    trajectory["steps"][0]["message"] = instruction
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    source_artifacts = fixture_dir / "artifacts"
    if source_artifacts.is_dir():
        for source in source_artifacts.rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(source_artifacts)
            if source.suffix == ".b64":
                target = artifacts_dir / relative.with_suffix("")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(base64.b64decode(source.read_text(encoding="ascii")))
            else:
                target = artifacts_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    return trajectory


__all__ = ["load_pbench_trajectory"]
