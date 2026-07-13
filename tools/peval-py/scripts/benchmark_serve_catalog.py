#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

from peval_py.config import ToolConfig
from peval_py.state import CatalogQuery, WorkspaceCatalog, open_workspace_state


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and query a synthetic peval-py serve catalog."
    )
    parser.add_argument("--cells", type=int, default=10_000)
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()
    if args.cells < 1:
        parser.error("--cells must be positive")

    temporary = None
    if args.workspace is None:
        temporary = tempfile.TemporaryDirectory(prefix="peval-py-catalog-benchmark-")
        root = Path(temporary.name)
    else:
        root = args.workspace.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
    try:
        write_workspace(root, args.cells)
        store = open_workspace_state(str(root))
        config = ToolConfig(
            workspace_root=str(root), analysis_eval_slug="benchmark"
        )
        catalog = WorkspaceCatalog(store, config)

        cold_start = time.perf_counter()
        catalog.reconcile()
        cold_seconds = time.perf_counter() - cold_start

        warm_start = time.perf_counter()
        catalog.reconcile()
        warm_seconds = time.perf_counter() - warm_start

        page_start = time.perf_counter()
        page = catalog.query(CatalogQuery(page_size=100))
        page_seconds = time.perf_counter() - page_start

        detail_samples: list[float] = []
        sample_keys = [item.source_key for item in page.items[:100]]
        for source_key in sample_keys:
            started = time.perf_counter()
            catalog.load_detail(source_key)
            detail_samples.append((time.perf_counter() - started) * 1000)

        print(
            json.dumps(
                {
                    "workspace": str(root),
                    "cells": args.cells,
                    "generation": catalog.generation,
                    "cold_rebuild_seconds": round(cold_seconds, 4),
                    "warm_reconcile_seconds": round(warm_seconds, 4),
                    "first_page_seconds": round(page_seconds, 4),
                    "detail_p95_ms": round(percentile(detail_samples, 95), 3),
                    "detail_median_ms": round(statistics.median(detail_samples), 3),
                },
                indent=2,
            )
        )
        store.close()
        return 0
    finally:
        if temporary is not None:
            temporary.cleanup()


def write_workspace(root: Path, cells: int) -> None:
    (root / "peval-py.toml").write_text(
        'analysis_eval_slug = "benchmark"\n', encoding="utf-8"
    )
    trajectory_template = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "benchmark-agent", "model_name": "benchmark-model"},
        "steps": [
            {"step_id": 1, "source": "user", "message": "benchmark prompt"},
            {"step_id": 2, "source": "assistant", "message": "benchmark response"},
        ],
        "final_metrics": {
            "total_prompt_tokens": 10,
            "total_completion_tokens": 20,
            "extra": {"total_turns": 1, "total_tool_calls": 0, "total_tool_errors": 0},
        },
    }
    meta_template = {
        "adapter": "benchmark",
        "started_at_ms": 1_000,
        "finished_at_ms": 1_100,
        "duration_ms": 100,
        "wall_duration_ms": 100,
        "status": "passed",
        "warnings": [],
        "steps": [],
    }
    for index in range(cells):
        session_id = f"session-{index:05d}"
        trial_key = f"trial-{index:05d}"
        agent_dir = (
            root
            / "runs"
            / "benchmark"
            / "benchmark-agent"
            / session_id
            / trial_key
            / "agent"
        )
        agent_dir.mkdir(parents=True, exist_ok=True)
        trajectory = {**trajectory_template, "trajectory_id": trial_key, "session_id": session_id}
        meta = {**meta_template, "trial_key": trial_key, "finished_at_ms": 1_100 + index}
        (agent_dir / "trajectory.json").write_text(
            json.dumps(trajectory, separators=(",", ":")), encoding="utf-8"
        )
        (agent_dir / "trajectory_meta.json").write_text(
            json.dumps(meta, separators=(",", ":")), encoding="utf-8"
        )


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile_value / 100
    lower = int(rank)
    upper = min(len(ordered) - 1, lower + 1)
    fraction = rank - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


if __name__ == "__main__":
    raise SystemExit(main())
