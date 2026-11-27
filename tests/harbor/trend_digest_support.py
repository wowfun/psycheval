"""Shared fixtures and grading helpers for PBench trend-digest tests."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from types import ModuleType
from typing import Iterator

from harbor.models.trajectories import Trajectory

from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    VerifierInvocation,
)
from psycheval.harbor.verifier import aggregate, build_scoring_plan, evaluate
from tests.fixtures import trend_digest as trend_fixtures

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TASK_ROOT = REPOSITORY_ROOT / "datasets" / "pbench-v1.0" / "trend-digest-01"
NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


def score_without(config: dict, *failed_ids: str) -> float:
    items = build_scoring_plan(config).items
    return sum(item.weight for item in items if item.id not in failed_ids) / sum(
        item.weight for item in items
    )


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    finally:
        sys.dont_write_bytecode = previous_bytecode
    return module


@contextmanager
def loaded_task_module(name: str, relative_path: Path) -> Iterator[ModuleType]:
    module = load_module(name, TASK_ROOT / relative_path)
    try:
        yield module
    finally:
        sys.modules.pop(name, None)


def rss(handle: str, posts: list[tuple[str, datetime, str]]) -> str:
    items = []
    for post_id, published, text in posts:
        items.append(
            "<item>"
            f"<guid>https://nitter.example/{handle}/status/{post_id}</guid>"
            f"<link>https://nitter.example/{handle}/status/{post_id}</link>"
            f"<description><![CDATA[{text}]]></description>"
            f"<pubDate>{format_datetime(published)}</pubDate>"
            "</item>"
        )
    return "<rss><channel>" + "".join(items) + "</channel></rss>"


def write_trajectory(
    path: Path,
    *,
    arguments: dict,
    observation: str,
    function_name: str,
    final_answer: str,
    observation_extra: dict | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "ATIF-v1.7",
                "trajectory_id": "fixture",
                "agent": {"name": "fixture", "version": "1"},
                "steps": [
                    {"step_id": 1, "source": "user", "message": "collect"},
                    {
                        "step_id": 2,
                        "source": "agent",
                        "message": "",
                        "tool_calls": [
                            {
                                "tool_call_id": "call-1",
                                "function_name": function_name,
                                "arguments": arguments,
                            }
                        ],
                        "observation": {
                            "results": [
                                {
                                    "source_call_id": "call-1",
                                    "content": observation,
                                    "extra": {
                                        "is_error": False,
                                        **(observation_extra or {}),
                                    },
                                }
                            ]
                        },
                    },
                    {"step_id": 3, "source": "agent", "message": final_answer},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def make_case(tmp_path: Path, platform: str):
    workspace = tmp_path / "app"
    shutil.copytree(TASK_ROOT / "environment" / "data", workspace)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    logs = tmp_path / "agent"
    if platform == "github":
        arguments, observation, snapshot = trend_fixtures.github(artifacts, NOW)
    elif platform == "x":
        arguments, observation, snapshot = trend_fixtures.x(workspace, artifacts, NOW)
    else:
        arguments, observation, snapshot = trend_fixtures.hacker_news(
            workspace, artifacts, NOW
        )
    report = next(artifacts.iterdir())
    write_trajectory(
        logs / "trajectory.json",
        arguments=arguments,
        observation=observation,
        function_name="web_fetch" if platform == "github" else "exec_command",
        final_answer=report.name,
    )
    verifier_logs = tmp_path / "verifier"
    verifier_logs.mkdir()
    runtime = EffectiveRuntimeConfig(
        paths=RuntimePaths(
            str(workspace),
            str(TASK_ROOT / "steps" / platform / "tests"),
            str(logs),
            str(verifier_logs),
            str(artifacts),
        ),
        verifier=VerifierInvocation("当前步骤中文指令", platform),
    )
    config = json.loads(
        (TASK_ROOT / "steps" / platform / "tests/grader.json").read_text(
            encoding="utf-8"
        )
    )
    return runtime, config, report, snapshot


def grade(
    verifier: ModuleType,
    runtime: EffectiveRuntimeConfig,
    config: dict,
    *,
    now: datetime = NOW,
):
    trajectory = Trajectory(
        **json.loads(
            (Path(runtime.paths.agent_logs) / "trajectory.json").read_text(
                encoding="utf-8"
            )
        )
    )
    checks = evaluate(trajectory, config, Path(runtime.paths.artifacts))
    checks += [
        {**check, "id": "custom:" + check["id"]}
        for check in verifier.check_outputs(runtime.to_dict(), config, now=now)
    ]
    return aggregate(checks, plan=build_scoring_plan(config)), {
        check["id"]: check for check in checks
    }
