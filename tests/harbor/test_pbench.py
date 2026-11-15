from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from harbor.models.task.config import TaskOS
from harbor.models.task.paths import TaskPaths
from harbor.models.task.task import Task
from harbor.models.trajectories import Trajectory

from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    VerifierInvocation,
)
from psycheval.harbor.verifier import (
    JudgeSettings,
    build_scoring_plan,
    run_verifier,
)
from tests.fixtures import load_pbench_trajectory

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DATASETS_ROOT = _REPOSITORY_ROOT / "datasets"
_FIXTURES_ROOT = _REPOSITORY_ROOT / "tests" / "fixtures" / "pbench"
_TASK_CASES = [
    ("pbench-v1.0", "web-search-01"),
    ("pbench-v1.0", "web-fetch-01"),
    ("pbench-v1.0-plus", "browser-control-01"),
]
_TEMPLATE_ROOT = _REPOSITORY_ROOT / "examples" / "tasks" / "pbench-task-template"


def _assert_fixture_passes(
    task_root: Path, trajectory: Trajectory, tmp_path: Path
) -> None:
    roots = {
        "workdir": tmp_path / "workdir",
        "agent_logs": tmp_path / "agent_logs",
        "verifier_logs": tmp_path / "verifier_logs",
        "artifacts": tmp_path / "artifacts" / "logs" / "artifacts",
    }
    for path in roots.values():
        path.mkdir(parents=True, exist_ok=True)
    (roots["agent_logs"] / "trajectory.json").write_text(
        trajectory.model_dump_json(), encoding="utf-8"
    )
    runtime = EffectiveRuntimeConfig(
        paths=RuntimePaths(
            tests=str(task_root / "tests"),
            **{key: str(path) for key, path in roots.items()},
        ),
        verifier=VerifierInvocation(
            (task_root / "instruction.md").read_text(encoding="utf-8")
        ),
    )
    result = asyncio.run(
        run_verifier(
            task_root / "tests/grader.json",
            runtime=runtime,
            judge_settings=JudgeSettings(enabled=False),
        )
    )
    checks = [
        verdict
        for verdict in result["verdicts"]
        if verdict["judge_type"] == "rule_script"
    ]
    assert checks, result
    assert all(check["status"] == "pass" for check in checks), checks
    assert result["metadata"]["score_merge"]["rule_score"] == 1, result


@pytest.mark.parametrize("grader_path", sorted(_DATASETS_ROOT.rglob("grader.json")))
def test_dataset_tool_patterns_use_one_canonical_spelling(grader_path: Path) -> None:
    config = json.loads(grader_path.read_text(encoding="utf-8"))
    lists = [config.get("forbidden_tool_names", [])]
    lists.extend(
        branch["tool_names"]
        for rule in config.get("required_calls", [])
        for branch in rule["any"]
    )
    for names in lists:
        assert len(names) == len(set(names))
        assert all(
            name == name.casefold() and "-" not in name and "_" not in name
            for name in names
        )


@pytest.mark.parametrize(
    ("dataset_name", "expected_task_dirs"),
    [
        (
            "pbench-v1.0",
            {"web-search-01", "web-fetch-01", "trend-digest-01"},
        ),
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
    ("dataset_name", "task_dir"),
    _TASK_CASES,
)
def test_pbench_grader_accepts_fixture_trajectory(
    dataset_name: str,
    task_dir: str,
    tmp_path: Path,
) -> None:
    task_root = _DATASETS_ROOT / dataset_name / task_dir
    instruction = (task_root / "instruction.md").read_text(encoding="utf-8")
    trajectory = Trajectory(
        **load_pbench_trajectory(
            _FIXTURES_ROOT / task_dir, instruction, tmp_path / "artifacts"
        )
    )

    assert trajectory.agent.name == "pbench-verifier-fixture"
    _assert_fixture_passes(task_root, trajectory, tmp_path)


@pytest.mark.parametrize(
    ("dataset_name", "task_dir", "canonical_name", "alias_name"),
    [
        (
            "pbench-v1.0",
            "web-search-01",
            "web_search",
            "websearch",
        ),
        (
            "pbench-v1.0",
            "web-fetch-01",
            "web_fetch",
            "webfetch",
        ),
    ],
)
def test_pbench_grader_accepts_equivalent_web_tool_spellings(
    dataset_name: str,
    task_dir: str,
    canonical_name: str,
    alias_name: str,
    tmp_path: Path,
) -> None:
    task_root = _DATASETS_ROOT / dataset_name / task_dir
    trajectory = Trajectory(
        **load_pbench_trajectory(
            _FIXTURES_ROOT / task_dir, "Do it", tmp_path / "artifacts"
        )
    )
    call = next(
        call
        for step in trajectory.steps
        for call in (step.tool_calls or [])
        if call.function_name == canonical_name
    )
    call.function_name = alias_name

    _assert_fixture_passes(task_root, trajectory, tmp_path)


def test_pbench_browser_grader_accepts_harbor_computer_actions(
    tmp_path: Path,
) -> None:
    task_root = _DATASETS_ROOT / "pbench-v1.0-plus" / "browser-control-01"
    trajectory = Trajectory(
        **load_pbench_trajectory(
            _FIXTURES_ROOT / "browser-control-01", "Submit it", tmp_path / "artifacts"
        )
    )
    calls = [
        call
        for step in trajectory.steps
        for call in (step.tool_calls or [])
        if call.function_name in {"browser_type", "browser_click"}
    ]
    calls[0].function_name = "computer_action"
    calls[0].arguments = {
        "type": "type_text_at",
        "text": "Morning briefing",
        "x": 100,
        "y": 200,
    }
    calls[1].function_name = "computer_action"
    calls[1].arguments = {"type": "click", "x": 100, "y": 250}

    _assert_fixture_passes(task_root, trajectory, tmp_path)


@pytest.mark.parametrize(
    ("dataset_name", "task_dir"),
    _TASK_CASES,
)
def test_pbench_grader_declares_atomic_custom_checks(
    dataset_name: str,
    task_dir: str,
) -> None:
    config = json.loads(
        (_DATASETS_ROOT / dataset_name / task_dir / "tests" / "grader.json").read_text(
            encoding="utf-8"
        )
    )

    plan = build_scoring_plan(config)
    assert plan.items
    assert plan.custom_ids
    assert len(plan.custom_ids) == len(set(plan.custom_ids))
    # Each Task combines the action, paired source and result into its custom
    # checks instead of also rewarding the same action through builtin items.
    assert all(item.dimension == "custom_outputs" for item in plan.items)
    assert not plan.requires_trajectory


@pytest.mark.parametrize(
    "task_root",
    [
        *[
            _DATASETS_ROOT / dataset_name / task_dir
            for dataset_name, task_dir in _TASK_CASES
        ],
        _TEMPLATE_ROOT,
    ],
)
def test_pbench_tasks_ship_thin_linux_and_windows_verifier_entrypoints(
    task_root: Path,
) -> None:
    paths = TaskPaths(task_root)
    linux_entrypoint = paths.test_path_for(TaskOS.LINUX)
    windows_entrypoint = paths.test_path_for(TaskOS.WINDOWS)

    assert linux_entrypoint.is_file()
    assert windows_entrypoint.is_file()
    for entrypoint in (linux_entrypoint, windows_entrypoint):
        content = entrypoint.read_text(encoding="utf-8")
        assert "psycheval.harbor.verifier" in content
        assert "grader.json" in content
        assert "psycheval-test-entrypoint=" in content
        assert "required_calls" not in content
