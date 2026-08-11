from __future__ import annotations

import json
from pathlib import Path

import pytest
from harbor.models.task.config import TaskOS
from harbor.models.task.task import Task
from harbor.models.trajectories import Trajectory

from psycheval.harbor.canned_harness import _trajectory
from psycheval.harbor.verifier import grade

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DATASETS_ROOT = _REPOSITORY_ROOT / "datasets"
_TASK_CASES = [
    ("web-search", "pbench-v1.0", "web-search-01"),
    ("web-fetch", "pbench-v1.0", "web-fetch-01"),
    ("browser-control", "pbench-v1.0-plus", "browser-control-01"),
]
_TEMPLATE_ROOT = _REPOSITORY_ROOT / "examples" / "tasks" / "pbench-task-template"


@pytest.mark.parametrize(
    ("dataset_name", "expected_task_dirs"),
    [
        ("pbench-v1.0", {"web-search-01", "web-fetch-01"}),
        ("pbench-v1.0-plus", {"browser-control-01"}),
    ],
)
def test_pbench_dataset_exposes_direct_named_harbor_tasks(
    dataset_name: str,
    expected_task_dirs: set[str],
) -> None:
    dataset_root = _DATASETS_ROOT / dataset_name
    task_names = {
        path.name
        for path in dataset_root.iterdir()
        if path.is_dir() and (path / "task.toml").is_file()
    }
    assert task_names == expected_task_dirs

    for task_dir in expected_task_dirs:
        task = Task(dataset_root / task_dir)
        assert task.name == f"{dataset_name}/{task_dir}"


@pytest.mark.parametrize(
    ("scenario", "dataset_name", "task_dir"),
    _TASK_CASES,
)
def test_pbench_grader_accepts_canned_trajectory(
    scenario: str,
    dataset_name: str,
    task_dir: str,
    tmp_path: Path,
) -> None:
    task_root = _DATASETS_ROOT / dataset_name / task_dir
    config = json.loads(
        (task_root / "tests" / "grader.json").read_text(encoding="utf-8")
    )
    instruction = (task_root / "instruction.md").read_text(encoding="utf-8")
    trajectory = Trajectory(**_trajectory(scenario, instruction, tmp_path))

    checks = grade(trajectory, config, tmp_path)

    assert checks
    assert all(check["passed"] for check in checks), checks


@pytest.mark.parametrize(
    ("scenario", "dataset_name", "task_dir", "canonical_name", "alias_name"),
    [
        (
            "web-search",
            "pbench-v1.0",
            "web-search-01",
            "web_search",
            "websearch",
        ),
        (
            "web-fetch",
            "pbench-v1.0",
            "web-fetch-01",
            "web_fetch",
            "webfetch",
        ),
    ],
)
def test_pbench_grader_accepts_explicit_web_tool_aliases(
    scenario: str,
    dataset_name: str,
    task_dir: str,
    canonical_name: str,
    alias_name: str,
    tmp_path: Path,
) -> None:
    task_root = _DATASETS_ROOT / dataset_name / task_dir
    config = json.loads(
        (task_root / "tests" / "grader.json").read_text(encoding="utf-8")
    )
    trajectory = Trajectory(**_trajectory(scenario, "Do it", tmp_path))
    call = next(
        call
        for step in trajectory.steps
        for call in (step.tool_calls or [])
        if call.function_name == canonical_name
    )
    call.function_name = alias_name

    checks = grade(trajectory, config, tmp_path)

    assert all(check["passed"] for check in checks), checks


def test_pbench_browser_grader_accepts_harbor_computer_actions(
    tmp_path: Path,
) -> None:
    task_root = _DATASETS_ROOT / "pbench-v1.0-plus" / "browser-control-01"
    config = json.loads(
        (task_root / "tests" / "grader.json").read_text(encoding="utf-8")
    )
    trajectory = Trajectory(**_trajectory("browser-control", "Submit it", tmp_path))
    calls = [
        call
        for step in trajectory.steps
        for call in (step.tool_calls or [])
        if call.function_name in {"browser_type", "browser_click"}
    ]
    calls[0].function_name = "computer_action"
    calls[0].arguments = {
        "type": "type_text_at",
        "text": "Harbor eval",
        "x": 100,
        "y": 200,
    }
    calls[1].function_name = "computer_action"
    calls[1].arguments = {"type": "click", "x": 100, "y": 250}

    checks = grade(trajectory, config, tmp_path)

    assert all(check["passed"] for check in checks), checks


@pytest.mark.parametrize(
    ("scenario", "dataset_name", "task_dir", "expected_tool_names"),
    [
        (
            "web-search",
            "pbench-v1.0",
            "web-search-01",
            [{"web_search", "websearch"}],
        ),
        (
            "web-fetch",
            "pbench-v1.0",
            "web-fetch-01",
            [{"web_fetch", "webfetch"}],
        ),
        (
            "browser-control",
            "pbench-v1.0-plus",
            "browser-control-01",
            [
                {"browser_type", "computer_action"},
                {"browser_click", "computer_action"},
            ],
        ),
    ],
)
def test_pbench_grader_uses_only_explicit_tool_branches(
    scenario: str,
    dataset_name: str,
    task_dir: str,
    expected_tool_names: list[set[str]],
) -> None:
    del scenario
    config = json.loads(
        (_DATASETS_ROOT / dataset_name / task_dir / "tests" / "grader.json").read_text(
            encoding="utf-8"
        )
    )

    actual = []
    for rule in config["required_calls"]:
        assert set(rule) == {"any"}
        assert rule["any"]
        actual.append(
            {tool_name for branch in rule["any"] for tool_name in branch["tool_names"]}
        )

    assert actual == expected_tool_names
    assert "forbidden_tools" not in config


@pytest.mark.parametrize(
    "task_root",
    [
        *[
            _DATASETS_ROOT / dataset_name / task_dir
            for _scenario, dataset_name, task_dir in _TASK_CASES
        ],
        _TEMPLATE_ROOT,
    ],
)
def test_pbench_tasks_ship_thin_linux_and_windows_verifier_entrypoints(
    task_root: Path,
) -> None:
    task = Task(task_root)
    linux_entrypoint = task.paths.test_path_for(TaskOS.LINUX)
    windows_entrypoint = task.paths.test_path_for(TaskOS.WINDOWS)

    assert linux_entrypoint.is_file()
    assert windows_entrypoint.is_file()
    for entrypoint in (linux_entrypoint, windows_entrypoint):
        content = entrypoint.read_text(encoding="utf-8")
        assert "psycheval.harbor.verifier" in content
        assert "grader.json" in content
        assert "psycheval-test-entrypoint=" in content
        assert "required_calls" not in content
