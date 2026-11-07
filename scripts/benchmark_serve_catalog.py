#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from psycheval.config import HarborDataset, HarborMount, ToolConfig
from psycheval.harbor.atif import ATIF_VERSION
from psycheval.state import (
    CatalogQuery,
    WorkspaceCatalog,
    harbor_evidence,
    open_workspace_state,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and query an isolated synthetic serve catalog."
    )
    parser.add_argument("--cells", type=int, default=1000)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--message-bytes", type=int, default=512)
    args = parser.parse_args()
    if min(args.cells, args.steps, args.message_bytes) < 1:
        parser.error("cells, steps, and message-bytes must be positive")
    with tempfile.TemporaryDirectory(prefix="peval-catalog-benchmark-") as temporary:
        root = Path(temporary)
        config = write_workspace(root, args.cells, args.steps, args.message_bytes)
        store = open_workspace_state(str(root / "workspace"))
        try:
            catalog = WorkspaceCatalog(store, config)
            cold = measure(catalog)
            catalog = WorkspaceCatalog(store, config)
            restarted = measure(catalog)
            page_started = time.perf_counter()
            page = catalog.query(CatalogQuery(page_size=100))
            page_seconds = time.perf_counter() - page_started
            if page.total != args.cells or not page.items:
                raise RuntimeError(
                    f"expected {args.cells} readable Trials, got {page.total}"
                )
            changed = root / "jobs/benchmark/trial-00000/result.json"
            result = json.loads(changed.read_text(encoding="utf-8"))
            result["verifier_result"]["rewards"]["reward"] = 0.25
            changed.write_text(json.dumps(result), encoding="utf-8")
            single_update = measure(catalog)
            details = []
            for row in page.items[:10]:
                started = time.perf_counter()
                catalog.load_detail(row.source_key)
                details.append((time.perf_counter() - started) * 1000)
            print(
                json.dumps(
                    {
                        "trials": args.cells,
                        "steps_per_trial": args.steps,
                        "message_bytes": args.message_bytes,
                        "cold": cold,
                        "restart": restarted,
                        "single_update": single_update,
                        "first_page_seconds": round(page_seconds, 4),
                        "detail_median_ms": round(statistics.median(details), 3),
                    },
                    indent=2,
                ),
                flush=True,
            )
        finally:
            store.close()
    return 0


def measure(catalog: WorkspaceCatalog) -> dict[str, int | float]:
    reads = 0
    original = harbor_evidence._read_bytes_no_follow

    def read(root, path):
        nonlocal reads
        if path.name == "trajectory.json":
            reads += 1
        return original(root, path)

    with patch.object(harbor_evidence, "_read_bytes_no_follow", side_effect=read):
        started = time.perf_counter()
        catalog.reconcile()
        seconds = time.perf_counter() - started
    return {"seconds": round(seconds, 4), "trajectory_body_reads": reads}


def write_workspace(
    root: Path, cells: int, steps: int, message_bytes: int
) -> ToolConfig:
    task = root / "dataset/task"
    task.mkdir(parents=True)
    (task / "task.toml").write_text(
        '[task]\nname = "benchmark/task"\n', encoding="utf-8"
    )
    (task / "instruction.md").write_text(
        "Complete the benchmark task.\n", encoding="utf-8"
    )
    (task / "environment").mkdir()
    (task / "environment/Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    job = root / "jobs/benchmark"
    job.mkdir(parents=True)
    (job / "config.json").write_text(
        json.dumps({"job_name": "benchmark", "tasks": ["task"]}), encoding="utf-8"
    )
    (job / "lock.json").write_text("{}", encoding="utf-8")
    body = "x" * message_bytes
    template = {
        "schema_version": ATIF_VERSION,
        "agent": {"name": "benchmark", "version": "1", "model_name": "fixture"},
        "steps": [
            {
                "step_id": index + 1,
                "source": "user" if index == 0 else "agent",
                "message": body,
            }
            for index in range(steps)
        ],
        "final_metrics": {"total_steps": steps},
    }
    for index in range(cells):
        name = f"trial-{index:05d}"
        trial = job / name
        (trial / "agent").mkdir(parents=True)
        (trial / "agent/trajectory.json").write_text(
            json.dumps(
                {
                    **template,
                    "trajectory_id": name,
                    "session_id": name,
                }
            ),
            encoding="utf-8",
        )
        (trial / "config.json").write_text(
            json.dumps(
                {
                    "trial_name": name,
                    "job_id": "benchmark-job",
                    "task": {"name": "task", "source": "benchmark"},
                }
            ),
            encoding="utf-8",
        )
        (trial / "result.json").write_text(
            json.dumps(
                {
                    "trial_name": name,
                    "task_name": "benchmark/task",
                    "started_at": "2026-01-01T00:00:00Z",
                    "finished_at": "2026-01-01T00:00:01Z",
                    "verifier_result": {"rewards": {"reward": 0.75}},
                }
            ),
            encoding="utf-8",
        )
    return ToolConfig(
        workspace_root=str(root / "workspace"),
        harbor_datasets=(HarborDataset(id="benchmark", path=str(task.parent)),),
        harbor_mounts=(
            HarborMount(
                id="benchmark", path=str(root / "jobs"), dataset_ids=("benchmark",)
            ),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
