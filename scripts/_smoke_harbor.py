from __future__ import annotations

import json
from pathlib import Path


def write_harbor_trial(root: Path) -> Path:
    jobs = root / "harbor-jobs"
    job = jobs / "smoke-job"
    trial = job / "smoke-trial"
    agent = trial / "agent"
    agent.mkdir(parents=True)
    (job / "config.json").write_text(
        json.dumps(
            {
                "job_name": "smoke-job",
                "jobs_dir": str(jobs),
                "agents": ["smoke-agent"],
                "tasks": ["smoke-task"],
            }
        ),
        encoding="utf-8",
    )
    (job / "lock.json").write_text(
        json.dumps({"schema_version": 1, "trials": []}),
        encoding="utf-8",
    )
    (trial / "config.json").write_text(
        json.dumps(
            {
                "trial_name": "smoke-trial",
                "job_id": "smoke-job-id",
                "task": {"name": "smoke-task"},
            }
        ),
        encoding="utf-8",
    )
    (trial / "result.json").write_text(
        json.dumps(
            {
                "id": "smoke-result-id",
                "trial_name": "smoke-trial",
                "task_name": "smoke-task",
                "verifier_result": {"rewards": {"reward": 1.0}},
            }
        ),
        encoding="utf-8",
    )
    (agent / "trajectory.json").write_text(
        json.dumps(
            {
                "schema_version": "ATIF-v1.7",
                "trajectory_id": "smoke:trial",
                "session_id": "smoke-session",
                "agent": {
                    "name": "smoke-agent",
                    "version": "1.0.0",
                    "model_name": "smoke-model",
                },
                "steps": [
                    {"step_id": 1, "source": "user", "message": "smoke"},
                    {"step_id": 2, "source": "agent", "message": "done"},
                ],
                "final_metrics": {"total_steps": 2},
            }
        ),
        encoding="utf-8",
    )
    return trial


def assert_harbor_inspect(raw: str) -> None:
    payload = json.loads(raw)
    source = payload["sources"][0]
    if payload.get("inspect_schema_version") != 3:
        raise RuntimeError("installed peval returned an unexpected inspect schema")
    if source.get("status") != "completed" or source.get("score") != 1.0:
        raise RuntimeError("installed peval omitted the Harbor Trial outcome")
    harbor = source.get("harbor") or {}
    if (
        harbor.get("job_name") != "smoke-job"
        or harbor.get("trial_name") != "smoke-trial"
        or harbor.get("trajectory_available") is not True
    ):
        raise RuntimeError("installed peval omitted Harbor Trial identity")
