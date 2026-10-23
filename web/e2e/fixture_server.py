from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import uvicorn

from psycheval.config import AcpAgent, load_config
from psycheval.serve.access import ServeAccess
from psycheval.serve.acp import MAX_ACP_FRAME_BYTES
from psycheval.serve.api import create_app
from psycheval.serve.assets import ECHARTS_VERSION, echarts_cache_path
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import open_workspace_state


def main() -> None:
    with (
        tempfile.TemporaryDirectory(prefix="peval-acp-e2e-") as temporary,
        ExitStack() as resources,
    ):
        root = Path(temporary)
        if os.environ.get("PEVAL_E2E_JOBS") == "1":
            from tests.peval.test_jobs import install_fixture_plugin

            install_fixture_plugin(root)
            sys.path.insert(0, str(root))
            os.environ["PYTHONPATH"] = os.pathsep.join([str(root), str(Path.cwd())])
        if os.environ.get("PEVAL_E2E_CLAUDE") == "1":
            from tests.peval.claude_support import event, family, write_events

            family(root / ".claude")
            write_events(
                root / ".claude/newer.jsonl",
                [event("user", seq=50, content="Newer session", sessionId="newer")],
            )
            (root / ".claude/bad.jsonl").write_text("{bad", encoding="utf-8")
            (root / ".claude/empty.jsonl").touch()
            for name in ("duplicate", "backup"):
                write_events(
                    root / f".claude/{name}.jsonl",
                    [
                        event(
                            "user",
                            content="Duplicate session",
                            sessionId="duplicate-session",
                        )
                    ],
                )
        locale = os.environ.get("PEVAL_E2E_LOCALE", "en")
        (root / "peval.toml").write_text(
            f'locale = {json.dumps(locale)}\nanalysis_eval_slug = "default"\n'
            + (
                '[adapters.claude]\ndefault_session_root = ".claude"\n'
                if os.environ.get("PEVAL_E2E_CLAUDE") == "1"
                else ""
            ),
            encoding="utf-8",
        )
        if os.environ.get("PEVAL_E2E_VERIFICATION") == "1":
            write_verification_trial(root)
        if os.environ.get("PEVAL_E2E_JUDGE") == "1":
            from tests.fixtures.judge_server import judge_server

            provider = resources.enter_context(judge_server())
            write_judge_trial(root, provider["url"])
        if os.environ.get("PEVAL_E2E_TABLES") == "1":
            from tests.peval.test_harbor_evidence import write_task

            for name in ("first", "second"):
                write_task(root / "editable" / name, f"org/{name}")
            with (root / "peval.toml").open("a", encoding="utf-8") as config_file:
                config_file.write(
                    '\n[[harbor.datasets]]\nid = "editable"\npath = "editable"\n'
                )
        write_e2e_trial(
            root / "runs/default/psychevo/e2e-session/e2e-trial",
            "e2e-trial",
        )
        write_e2e_trial(
            root / "runs/default/psychevo/e2e-session/e2e-trial-2",
            "e2e-trial-2",
        )
        if os.environ.get("PEVAL_E2E_METRICS") == "1":
            write_metric_trials(root)
        if os.environ.get("PEVAL_E2E_LINKS") == "1":
            path = (
                root
                / "runs/default/psychevo/e2e-session/e2e-trial/agent/trajectory.json"
            )
            trajectory = json.loads(path.read_text(encoding="utf-8"))
            trajectory["subagent_trajectories"] = [
                {
                    "schema_version": "ATIF-v1.7",
                    "trajectory_id": "child-中文",
                    "session_id": "child-session",
                    "agent": {"name": "child-agent", "version": "test"},
                    "steps": [
                        {"step_id": 1, "source": "user", "message": "Child request"},
                        {"step_id": 2, "source": "agent", "message": "Child response"},
                    ],
                    "final_metrics": {"total_steps": 2},
                }
            ]
            path.write_text(json.dumps(trajectory), encoding="utf-8")
            other = (
                root
                / "runs/default/psychevo/e2e-session/e2e-trial-2/agent/trajectory.json"
            )
            trajectory = json.loads(other.read_text(encoding="utf-8"))
            trajectory["agent"]["name"] = "link-target"
            other.write_text(json.dumps(trajectory), encoding="utf-8")
        if os.environ.get("PEVAL_E2E_TIMELINE") == "1":
            path = (
                root
                / "runs/default/psychevo/e2e-session/e2e-trial/agent/trajectory.json"
            )
            trajectory = json.loads(path.read_text(encoding="utf-8"))
            trajectory["steps"][0]["timestamp"] = "2026-01-01T00:00:00Z"
            trajectory["steps"][1].update(
                timestamp="2026-01-01T00:00:01Z",
                extra={"duration_ms": 1000},
                tool_calls=[
                    {
                        "tool_call_id": call_id,
                        "function_name": name,
                        "arguments": {},
                        "extra": {"execution_duration_ms": duration},
                    }
                    for call_id, name, duration in (
                        ("call-measured", "read_file", 420),
                        ("call-zero", "cached_read", 0),
                        ("call-unknown", "unknown_read", 222),
                    )
                ],
                observation={
                    "results": [
                        {"source_call_id": "call-measured", "content": "ok"},
                        {"source_call_id": "call-zero", "content": "cached"},
                        {
                            "source_call_id": "call-unknown",
                            "content": "unknown",
                            "extra": {"execution_duration_ms": None},
                        },
                    ]
                },
            )
            trajectory["final_metrics"]["extra"].update(
                total_tool_calls=3, total_tool_errors=0
            )
            if os.environ.get("PEVAL_E2E_OBSERVED_TIMING") == "1":
                trajectory["extra"] = {"timestamp_semantics": "event_observed"}
                trajectory["steps"][1]["extra"] = {
                    "duration_ms": 0,
                    "duration_source": "acp_client_observed_output",
                }
                trajectory["steps"][1]["observation"]["results"][0]["extra"] = {
                    "execution_duration_ms": 420,
                    "execution_duration_source": "acp_client_observed_lifecycle",
                }
                trajectory["steps"].extend(
                    [
                        {
                            "step_id": 3,
                            "source": "agent",
                            "message": "short",
                            "timestamp": "2026-01-01T00:00:02Z",
                            "extra": {
                                "duration_ms": 100,
                                "duration_source": "acp_client_observed_output",
                            },
                        },
                        {
                            "step_id": 4,
                            "source": "agent",
                            "message": "long",
                            "timestamp": "2026-01-01T00:00:03Z",
                            "extra": {
                                "duration_ms": 1000,
                                "duration_source": "acp_client_observed_output",
                            },
                        },
                        {
                            "step_id": 5,
                            "source": "agent",
                            "message": "single chunk",
                            "timestamp": "2026-01-01T00:00:05Z",
                        },
                    ]
                )
            if os.environ.get("PEVAL_E2E_NATIVE_TIMING") == "1":
                for step in trajectory["steps"]:
                    if "duration_source" in step.get("extra", {}):
                        step["extra"]["duration_source"] = "opencode_native_model_call"
                step = trajectory["steps"][1]
                for call, result in zip(
                    step["tool_calls"], step["observation"]["results"], strict=True
                ):
                    duration = result.get("extra", call["extra"]).get(
                        "execution_duration_ms"
                    )
                    call["extra"] = {"started_at": "2026-01-01T00:00:01.200Z"}
                    result["extra"] = {
                        "execution_duration_ms": duration,
                        "execution_duration_source": "opencode_native_tool_call",
                    }
            path.write_text(json.dumps(trajectory), encoding="utf-8")
        if os.environ.get("PEVAL_E2E_REPORTS") == "1":
            (root / "library-dataset").mkdir()
            with (root / "peval.toml").open("a", encoding="utf-8") as config_file:
                config_file.write(
                    '\n[[harbor.datasets]]\nid = "empty-library"\npath = "library-dataset"\n'
                )
            (root / "library.md").write_text(
                "# Independent report\n\n中文报告 <script>unsafe()</script>\n",
                encoding="utf-8",
            )
            (root / "library.html").write_text(
                "<!doctype html><h1>HTML report</h1>", encoding="utf-8"
            )
            (
                root / "runs/default/psychevo/e2e-session/e2e-trial/analysis.md"
            ).write_text("# Canonical report\n", encoding="utf-8")
            for index in range(28):
                write_e2e_trial(
                    root / f"runs/default/psychevo/many/session-{index:02}",
                    f"session-{index:02}",
                )
            control = root / ".peval/jobs" / ("a" * 32)
            control.mkdir(parents=True)
            (control / "state.json").write_text(
                json.dumps(
                    {
                        "id": "a" * 32,
                        "harness": "harbor",
                        "job_name": "2026-09-18__10-00-00",
                        "state": "completed",
                        "submitted_at": "2026-09-18T10:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
        agent = Path(__file__).with_name("synthetic_acp.py").resolve()
        command = os.environ.get("PEVAL_E2E_ACP_COMMAND") or str(
            Path(sys.executable).resolve()
        )
        raw_args = os.environ.get("PEVAL_E2E_ACP_ARGS")
        decoded_args = json.loads(raw_args) if raw_args else [str(agent)]
        if not isinstance(decoded_args, list) or not all(
            isinstance(value, str) for value in decoded_args
        ):
            raise ValueError("PEVAL_E2E_ACP_ARGS must be a JSON string array")
        args = tuple(decoded_args)
        store = open_workspace_state(str(root))
        echarts_package = Path(__file__).resolve().parents[2] / "node_modules/echarts"
        package = json.loads(
            (echarts_package / "package.json").read_text(encoding="utf-8")
        )
        if package["version"] != ECHARTS_VERSION:
            raise RuntimeError(
                "The ECharts test dependency must match the workspace asset version"
            )
        chart_asset = echarts_cache_path(store)
        chart_asset.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(echarts_package / "dist/echarts.min.js", chart_asset)
        runtime = ServeRuntime(
            store,
            load_config(workspace_root=root).validated_update(
                acp_agents=(
                    AcpAgent(
                        id="synthetic",
                        title=os.environ.get("PEVAL_E2E_ACP_TITLE", "Synthetic ACP"),
                        command=command,
                        args=args,
                    ),
                ),
            ),
        )
        try:
            if os.environ.get("PEVAL_E2E_MISSING_TASK") == "1":
                runtime.catalog.reconcile()
                task = root / "dataset/tasks/office-one"
                removed = root / "removed-task"
                assert task.resolve().is_relative_to(root.resolve())
                assert removed.resolve().is_relative_to(root.resolve())
                task.rename(removed)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.bind(("127.0.0.1", 0))
                listener.listen(2048)
                origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
                print(f"PEVAL_E2E_ORIGIN={origin}", flush=True)
                config = uvicorn.Config(
                    create_app(
                        runtime, ServeAccess(os.environ.get("PEVAL_E2E_PASSWORD"))
                    ),
                    host="127.0.0.1",
                    port=0,
                    loop="asyncio",
                    http="h11",
                    ws="websockets-sansio",
                    ws_max_size=MAX_ACP_FRAME_BYTES,
                    ws_max_queue=16,
                    lifespan="off",
                    workers=1,
                    proxy_headers=False,
                    access_log=False,
                    server_header=False,
                    log_config=None,
                )
                with patch(
                    "psycheval.serve.assets.download_echarts_asset",
                    side_effect=RuntimeError(
                        "Browser fixtures must use the seeded ECharts asset"
                    ),
                ):
                    uvicorn.Server(config).run(sockets=[listener])
        finally:
            runtime.close()
            store.close()


def write_judge_trial(root: Path, provider_url: str) -> None:
    import asyncio
    from dataclasses import replace

    import tomlkit

    from psycheval.harbor.verifier import JudgeSettings, run_verifier
    from tests.fixtures.judge_task import api_task
    from tests.peval.test_harbor_evidence import write_evidence_trial

    trial = root / "jobs/judge/rubric-trial"
    grader, context = api_task(root / "judge-task")
    write_evidence_trial(
        trial,
        config_task={"path": str(grader.parent.parent)},
        result={
            "task_name": "judge-fixture",
            "finished_at": "2026-01-01T00:00:00Z",
            "verifier_result": {"rewards": {"reward": 1}},
        },
    )
    logs = trial / "verifier"
    logs.mkdir(exist_ok=True)
    (logs / "中文 报告.md").write_text("Faithful evidence.\n", encoding="utf-8")
    context = replace(context, paths=replace(context.paths, verifier_logs=str(logs)))
    asyncio.run(
        run_verifier(
            grader,
            runtime=context,
            judge_settings=JudgeSettings(True, provider_url, "fixture"),
        )
    )
    other = trial.with_name("another-trial")
    shutil.copytree(trial, other)
    result_path = other / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result.update(task_name="judge-other", trial_name="another-trial")
    result_path.write_text(json.dumps(result), encoding="utf-8")
    path = root / "peval.toml"
    config = tomlkit.parse(path.read_text(encoding="utf-8"))
    config["harbor"] = {"mounts": [{"id": "judge", "path": "jobs"}]}
    config["judge"] = {
        "default_profile": "fixture",
        "profiles": {"fixture": {"base_url": provider_url, "model": "fixture"}},
    }
    path.write_text(tomlkit.dumps(config), encoding="utf-8")


def write_verification_trial(root: Path) -> None:
    from tests.peval.test_harbor_evidence import write_evidence_trial
    from tests.peval.test_workbuddy_datasets import _write_workbuddy_bundle

    bundle = _write_workbuddy_bundle(root / "dataset")
    task = bundle / "tasks/office-one"
    (task / "instruction.md").write_text(
        "# Task instructions\n\nCreate the requested artifact.\n\n"
        "| Input | Output |\n| --- | --- |\n| **Evidence** | `Workbook` |\n",
        encoding="utf-8",
    )
    trial = root / "jobs/office/office-one__trial"
    write_evidence_trial(
        trial,
        config_task={"path": str(task)},
        result={
            "task_name": "workbuddy/office-one",
            "verifier_result": {"rewards": {"reward": 0.676}},
        },
    )
    verifier = trial / "verifier"
    if os.environ.get("PEVAL_E2E_PARTIAL") == "1":
        agent = trial / "agent"
        (agent / "trajectory.json").rename(agent / "trajectory.partial.json")
        (agent / "cleanup.json").write_text(
            json.dumps(
                [
                    {
                        "stage": "process_pipes",
                        "error_type": "TimeoutError",
                        "paths": [str(trial / "retained-runtime")],
                    }
                ]
            ),
            encoding="utf-8",
        )
        result_path = trial / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result.update(
            finished_at="2026-01-01T00:00:00Z",
            exception_info={
                "exception_type": "AgentTimeoutError",
                "exception_message": "original timeout",
            },
        )
        result_path.write_text(json.dumps(result), encoding="utf-8")
    (verifier / "artifact_text").mkdir(parents=True)
    (verifier / "raw_artifacts").mkdir()
    (verifier / "artifact_text/report.md").write_text(
        "# Retained workbook\n\nPosition mismatch.\n\n"
        "| Position | Actual |\n| --- | --- |\n| **Total** | `12` |\n",
        encoding="utf-8",
    )
    (verifier / "raw_artifacts/report.xlsx").write_bytes(b"fixture workbook")
    (verifier / "reward.json").write_text('{"reward":0.676}', encoding="utf-8")
    (verifier / "judge").mkdir()
    (verifier / "judge/rubric-0001.json").write_text(
        json.dumps(
            {
                "id": "readability",
                "messages": [
                    {"role": "user", "content": "Retained scoring context.\n" * 200}
                ],
            }
        ),
        encoding="utf-8",
    )
    verdict = {
        "item_id": "position-match",
        "status": "fail",
        "score": 0,
        "reason": "Position totals do not match. <script>unsafe()</script>",
        "evidence_ids": ["workbook"],
    }
    (verifier / "score.json").write_text(
        json.dumps(
            {
                "reward": 0.676,
                "tests_passed": 359,
                "tests_total": 579,
                "test_status": "partial_pass",
                "verdicts": [verdict],
                "metadata": {
                    "score_merge": {
                        "method": "weighted_sum",
                        "rule_weight": 0.8,
                        "rule_score": 0.62,
                        "llm_weight": 0.2,
                        "llm_score": 0.9,
                        "overall": 0.676,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (verifier / "llm_judge.json").write_text(
        json.dumps(
            {"llm_judge": 0.9, "judge_status": "completed", "verdicts": [verdict]}
        ),
        encoding="utf-8",
    )
    (verifier / "artifact_manifest.json").write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "id": "workbook",
                        "text_path": "artifact_text/report.md",
                        "verifier_raw_path": "raw_artifacts/report.xlsx",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cases = "".join(
        f'<testcase classname="rules" name="case-{index}" time="0.1">'
        + (
            '<failure message="Position mismatch">Expected retained evidence</failure>'
            if 359 <= index < 577
            else '<error message="Setup error"/>'
            if index == 577
            else '<skipped message="Optional"/>'
            if index == 578
            else ""
        )
        + "</testcase>"
        for index in range(579)
    )
    (verifier / "results.xml").write_text(
        f"<testsuites><testsuite>{cases}</testsuite></testsuites>", encoding="utf-8"
    )
    with (root / "peval.toml").open("a", encoding="utf-8") as handle:
        handle.write(
            '\n[[harbor.datasets]]\nid = "office"\nformat = "workbuddy.v1"\npath = "dataset"\n'
            '\n[[harbor.mounts]]\nid = "jobs"\npath = "jobs"\ndataset_ids = ["office"]\n'
        )


def write_metric_trials(root: Path) -> None:
    from psycheval.metric_contract import custom_metric_id

    raw = "自定义能耗/大小写 %." + "中文" * 10
    metric_id = custom_metric_id("atif.extra", raw)
    with (root / "peval.toml").open("a", encoding="utf-8") as handle:
        handle.write(
            f'\n[metrics."{metric_id}"]\nlabel = "长中文名称能耗指标——包含空格和特殊符号的下游测量值"\nunit = "Wh"\ndirection = "lower"\n'
        )
    for index, name in enumerate(
        ["e2e-trial", "e2e-trial-2", "metric-2", "metric-3", "metric-4"]
    ):
        cell = root / "runs/default/psychevo/e2e-session" / name
        if not cell.exists():
            write_e2e_trial(cell, name)
        path = cell / "agent/trajectory.json"
        trajectory = json.loads(path.read_text(encoding="utf-8"))
        trajectory["agent"]["model_name"] = f"模型-{index}——用于比较的完整中文模型名称"
        trajectory["final_metrics"]["extra"][raw] = [-3, 0, 2, 6, 9][index]
        path.write_text(json.dumps(trajectory), encoding="utf-8")


def write_e2e_trial(cell: Path, trial_id: str) -> None:
    agent = cell / "agent"
    agent.mkdir(parents=True)
    trajectory = {
        "schema_version": "ATIF-v1.7",
        "trajectory_id": trial_id,
        "session_id": "e2e-session",
        "agent": {"name": "psychevo", "version": "test"},
        "steps": [
            {
                "step_id": 1,
                "source": "user",
                "message": "inspect deterministic evaluation evidence",
            },
            {
                "step_id": 2,
                "source": "agent",
                "message": "the deterministic tool call failed",
                "llm_call_count": 1,
                "tool_calls": [
                    {
                        "tool_call_id": "call_error",
                        "function_name": "exec_command",
                        "arguments": {"cmd": "false"},
                    }
                ],
                "observation": {
                    "results": [
                        {
                            "source_call_id": "call_error",
                            "content": "command failed",
                            "extra": {"status": "error", "is_error": True},
                        }
                    ]
                },
            },
        ],
        "final_metrics": {
            "total_steps": 2,
            "extra": {
                "total_turns": 1,
                "total_tool_calls": 1,
                "total_tool_errors": 1,
            },
        },
    }
    metadata = {
        "trial_key": trial_id,
        "adapter": "psychevo",
        "started_at_ms": 1000,
        "finished_at_ms": 1200,
        "wall_duration_ms": 200,
        "duration_ms": 200,
        "status": "failed",
        "score": 0,
        "score_message": "deterministic fixture failure",
        "warnings": [],
        "total_events": 2,
        "unmapped_events": 0,
        "prompt_unavailable": False,
        "steps": [
            {
                "step_id": 1,
                "tool_calls": [],
                "observations": [],
                "tool_error": False,
                "truncated": False,
            },
            {
                "step_id": 2,
                "tool_calls": [
                    {
                        "tool_call_id": "call_error",
                        "status": "error",
                        "title": "exec_command",
                    }
                ],
                "observations": [{"tool_call_id": "call_error", "status": "error"}],
                "tool_error": True,
                "truncated": False,
            },
        ],
    }
    (agent / "trajectory.json").write_text(json.dumps(trajectory), encoding="utf-8")
    (agent / "trajectory_meta.json").write_text(json.dumps(metadata), encoding="utf-8")


if __name__ == "__main__":
    main()
