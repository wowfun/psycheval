"""Synthetic Agent for a real, offline three-step Trend Digest Harbor Trial."""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import trend_digest

from psycheval.harbor.runtime_config import load_effective_runtime_config


def main():
    runtime = load_effective_runtime_config(require_harness=True)
    mode = os.environ.get("TREND_FIXTURE_MODE", "partial")
    x_outage = mode in {"x_outage", "x_false_success"}
    instruction = sys.stdin.buffer.read().decode("utf-8")
    first_line = instruction.splitlines()[0]
    step = (
        "github"
        if "GitHub" in first_line
        else "x"
        if "x-daily" in first_line
        else "hacker-news"
    )
    now = datetime.fromisoformat("2026-08-15T12:00:00+00:00")
    workspace, artifacts, logs = (
        Path(getattr(runtime.paths, name))
        for name in ("workdir", "artifacts", "agent_logs")
    )
    artifacts.mkdir(exist_ok=True, parents=True)
    logs.mkdir(exist_ok=True, parents=True)
    assert (workspace / ".trend-digest").is_dir()
    assert not (workspace / ".trend-digest/preparation.json").exists()
    assert runtime.paths.preparation_state is not None
    assert (Path(runtime.paths.preparation_state) / "preparation.json").is_file()
    assert not (workspace / "Dockerfile").exists()
    assert Path(os.environ["TREND_ARTIFACTS_DIR"]) == artifacts
    if step == "github":
        arguments, observation, _ = trend_digest.github(artifacts, now)
    elif step == "x":
        arguments, observation, snapshot = trend_digest.x(workspace, artifacts, now)
    else:
        arguments, observation, snapshot = trend_digest.hacker_news(
            workspace, artifacts, now
        )
    if step != "github":
        with tempfile.TemporaryDirectory() as temporary:
            fixtures = Path(temporary)
            if step == "x":
                if not x_outage:
                    for handle, _ in trend_digest.USERS:
                        (fixtures / f"{handle}-1.xml").write_text(
                            "<rss><channel/></rss>"
                        )
                script = workspace / "skills/x-daily/scripts/fetch.py"
                extra_args = ["--users", str(workspace / "input/x-users.xlsx")]
            else:
                (fixtures / "topstories.json").write_text(
                    json.dumps([story["id"] for story in snapshot["stories"]])
                )
                for story in snapshot["stories"]:
                    (fixtures / f"item-{story['id']}.json").write_text(
                        json.dumps(
                            {
                                **story,
                                "type": "story",
                                "descendants": story["comment_count"],
                                "time": int(now.timestamp()),
                            }
                        )
                    )
                script = workspace / "skills/hackernews-daily/scripts/fetch.py"
                extra_args = []
            argv = [
                sys.executable,
                str(script),
                "--output",
                str(workspace / f".trend-digest/{step}.json"),
                "--fixture-dir",
                str(fixtures),
                "--now",
                now.isoformat(),
                *extra_args,
            ]
            fetched = subprocess.run(argv, capture_output=True, encoding="utf-8")
            assert fetched.returncode == (1 if step == "x" and x_outage else 0), (
                fetched.stderr
            )
            arguments, observation = {"cmd": argv}, fetched.stdout + fetched.stderr
    report = trend_digest.report_path(artifacts, step, now)
    if mode == "partial" and step == "github":
        report.write_text(
            report.read_text(encoding="utf-8").replace(
                "https://github.com/fixture-org-1/fixture-repo-1",
                "https://example.invalid/missing",
                1,
            ),
            encoding="utf-8",
        )
    if mode == "x_outage" and step == "x":
        report.write_text(
            report.read_text(encoding="utf-8")
            .replace("状态：近 24 小时无新推文", "状态：抓取失败")
            .replace(
                "当前窗口没有可报告的新内容。", "来源不可用，无法核实当前窗口的新内容。"
            ),
            encoding="utf-8",
        )
    if mode == "missing_artifact" and step == "github":
        report.unlink()
    extra = {
        "exit_code": 1
        if (mode == "source_failure" and step == "github") or (x_outage and step == "x")
        else 0
    }
    trajectory = {
        "schema_version": "ATIF-v1.7",
        "trajectory_id": "trend-fixture-" + step,
        "agent": {"name": "trend-fixture", "version": "1"},
        "steps": [
            {"step_id": 1, "source": "user", "message": instruction},
            {
                "step_id": 2,
                "source": "agent",
                "message": "",
                "tool_calls": [
                    {
                        "tool_call_id": "source-" + step,
                        "function_name": "web_fetch"
                        if step == "github"
                        else "exec_command",
                        "arguments": arguments,
                    }
                ],
                "observation": {
                    "results": [
                        {
                            "source_call_id": "source-" + step,
                            "content": observation,
                            "extra": extra,
                        }
                    ]
                },
            },
            {
                "step_id": 3,
                "source": "agent",
                "message": "previous.md"
                if mode == "delivery_failure" and step == "github"
                else report.name,
            },
        ],
    }
    (logs / "trajectory.json").write_text(
        json.dumps(trajectory, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
