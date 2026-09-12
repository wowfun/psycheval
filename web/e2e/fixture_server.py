from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
from pathlib import Path

import uvicorn

from psycheval.config import AcpAgent, load_config
from psycheval.serve.access import ServeAccess
from psycheval.serve.acp import MAX_ACP_FRAME_BYTES
from psycheval.serve.api import create_app
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import open_workspace_state


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="peval-acp-e2e-") as temporary:
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
        write_e2e_trial(
            root / "runs/default/psychevo/e2e-session/e2e-trial",
            "e2e-trial",
        )
        write_e2e_trial(
            root / "runs/default/psychevo/e2e-session/e2e-trial-2",
            "e2e-trial-2",
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
                uvicorn.Server(config).run(sockets=[listener])
        finally:
            runtime.close()
            store.close()


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
    (verifier / "artifact_text").mkdir(parents=True)
    (verifier / "raw_artifacts").mkdir()
    (verifier / "artifact_text/report.md").write_text(
        "# Retained workbook\n\nPosition mismatch.\n\n"
        "| Position | Actual |\n| --- | --- |\n| **Total** | `12` |\n",
        encoding="utf-8",
    )
    (verifier / "raw_artifacts/report.xlsx").write_bytes(b"fixture workbook")
    (verifier / "reward.json").write_text('{"reward":0.676}', encoding="utf-8")
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
