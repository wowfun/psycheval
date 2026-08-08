from __future__ import annotations

import json
from pathlib import Path

import pytest
from harbor.models.trajectories import Trajectory

from psycheval.harbor.canned_harness import _trajectory
from psycheval.harbor.verifier import grade

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DATASET_ROOT = _REPOSITORY_ROOT / "datasets" / "pbench-v1.0"


def test_pbench_dataset_exposes_direct_harbor_tasks() -> None:
    task_names = {
        path.name
        for path in _DATASET_ROOT.iterdir()
        if path.is_dir() and (path / "task.toml").is_file()
    }
    assert task_names == {"web-search", "web-fetch", "browser-control"}


@pytest.mark.parametrize(
    "scenario",
    ["web-search", "web-fetch", "browser-control"],
)
def test_pbench_grader_accepts_canned_trajectory(scenario: str, tmp_path: Path) -> None:
    task_root = _DATASET_ROOT / scenario
    config = json.loads(
        (task_root / "tests" / "grader.json").read_text(encoding="utf-8")
    )
    instruction = (task_root / "instruction.md").read_text(encoding="utf-8")
    trajectory = Trajectory(**_trajectory(scenario, instruction, tmp_path))

    checks = grade(trajectory, config, tmp_path)

    assert checks
    assert all(check["passed"] for check in checks), checks
