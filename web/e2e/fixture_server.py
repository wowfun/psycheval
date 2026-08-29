from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import uvicorn

from psycheval.config import AcpAgent, ToolConfig
from psycheval.serve.access import ServeAccess
from psycheval.serve.acp import MAX_ACP_FRAME_BYTES
from psycheval.serve.api import create_app
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import open_workspace_state


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="peval-acp-e2e-") as temporary:
        root = Path(temporary)
        locale = os.environ.get("PEVAL_E2E_LOCALE", "en")
        (root / "peval.toml").write_text(
            f"locale = {json.dumps(locale)}\nanalysis_eval_slug = \"default\"\n",
            encoding="utf-8",
        )
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
            ToolConfig(
                workspace_root=str(root),
                locale=locale,
                analysis_eval_slug="default",
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
            uvicorn.run(
                create_app(runtime, ServeAccess(None)),
                host="127.0.0.1",
                port=4178,
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
        finally:
            runtime.close()
            store.close()


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
