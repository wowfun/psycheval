from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from psycheval._harbor_trials import is_harbor_trial_dir, load_harbor_trial_bundle
from psycheval.analysis import import_analysis_artifacts
from psycheval.config import (
    HarborDataset,
    HarborMount,
    ToolConfig,
    load_config,
    unique_harbor_id_from_path,
)
from psycheval.conversion import convert_db
from psycheval.serve.exports import build_serve_export
from psycheval.state import CatalogQuery, WorkspaceCatalog, open_workspace_state
from psycheval.state.workspace_harbor import _telemetry_aligns
from psycheval.workspace_reports import WorkspaceReportLibrary
from tests.peval.peval_test_support import (
    create_messages_db,
    create_opencode_event_timing_db,
)


def atif_trajectory(session_id: str = "harbor-session") -> dict[str, object]:
    return {
        "schema_version": "ATIF-v1.7",
        "trajectory_id": f"opencode:{session_id}",
        "session_id": session_id,
        "agent": {
            "name": "opencode",
            "version": "1.0.0",
            "model_name": "test-model",
        },
        "steps": [
            {
                "step_id": 1,
                "source": "user",
                "message": "search the web",
                "timestamp": "2026-08-08T01:00:00Z",
            },
            {
                "step_id": 2,
                "source": "agent",
                "message": "done",
                "timestamp": "2026-08-08T01:00:01Z",
            },
        ],
        "final_metrics": {
            "total_steps": 2,
            "extra": {
                "total_turns": 1,
                "total_tool_calls": 0,
                "total_tool_errors": 0,
            },
        },
    }


def write_trial(
    trial_dir: Path,
    *,
    trajectory: dict[str, object] | str | None = None,
    result: dict[str, object] | None = None,
) -> None:
    if trial_dir.parent.name != "steps":
        job_dir = trial_dir.parent
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "config.json").write_text(
            json.dumps(
                {
                    "job_name": job_dir.name,
                    "jobs_dir": str(job_dir.parent),
                    "agents": ["opencode"],
                    "tasks": ["web-search"],
                }
            ),
            encoding="utf-8",
        )
        (job_dir / "lock.json").write_text(
            json.dumps({"schema_version": 1, "trials": []}), encoding="utf-8"
        )
    agent_dir = trial_dir / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    value = atif_trajectory() if trajectory is None else trajectory
    (agent_dir / "trajectory.json").write_text(
        value if isinstance(value, str) else json.dumps(value), encoding="utf-8"
    )
    (trial_dir / "config.json").write_text(
        json.dumps(
            {
                "trial_name": trial_dir.name,
                "job_id": "job-123",
                "task": {"name": "web-search"},
            }
        ),
        encoding="utf-8",
    )
    if result is not None:
        (trial_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")


def completed_result(*, reward: float = 0.75) -> dict[str, object]:
    return {
        "id": "result-456",
        "trial_name": "trial-a",
        "task_name": "web-search",
        "started_at": "2026-08-08T01:00:00Z",
        "finished_at": "2026-08-08T01:00:02Z",
        "verifier_result": {"rewards": {"reward": reward}},
    }


class HarborTrialTests(unittest.TestCase):
    def test_trial_identity_wins_over_agent_trajectory_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trial = Path(tmp) / "jobs" / "job-a" / "trial-a"
            write_trial(trial)
            (trial / "agent" / "trajectory_meta.json").write_text(
                "{}", encoding="utf-8"
            )

            self.assertTrue(is_harbor_trial_dir(trial))

    def test_detail_load_reads_only_the_selected_harbor_trial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            for name in ("first", "selected", "third", "fourth"):
                write_trial(
                    jobs / "job-a" / name,
                    trajectory=atif_trajectory(name),
                )
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                rows = [item.to_dict() for item in catalog.query(CatalogQuery()).items]
                selected = next(
                    row for row in rows if row["source_ref"].endswith("/selected")
                )

                with patch(
                    "psycheval._harbor_trials.load_harbor_trial_bundle",
                    wraps=load_harbor_trial_bundle,
                ) as load_bundle:
                    detail = catalog.load_detail(selected["source_key"]).report

                self.assertEqual(detail["trajectory"][0]["session_id"], "selected")
                self.assertEqual(load_bundle.call_count, 1)
                self.assertEqual(load_bundle.call_args.args[0].name, "selected")
            finally:
                store.close()

    def test_generated_harbor_ids_are_bounded_and_retry_random_collisions(
        self,
    ) -> None:
        basename = "a" * 64
        self.assertEqual(
            unique_harbor_id_from_path(
                f"/datasets/{basename}", fallback="dataset", existing_ids=()
            ),
            basename,
        )
        with patch(
            "psycheval.config.secrets.token_hex",
            side_effect=["abc123", "abc123", "def456"],
        ):
            shortened = unique_harbor_id_from_path(
                f"/other/{basename}",
                fallback="dataset",
                existing_ids=(basename,),
            )
            fallback = unique_harbor_id_from_path(
                "/jobs/Invalid.Name",
                fallback="jobs",
                existing_ids=("jobs-abc123",),
            )

        self.assertEqual(shortened, f"{'a' * 57}-abc123")
        self.assertEqual(len(shortened), 64)
        self.assertEqual(fallback, "jobs-def456")

    def workspace(self, workspace: Path, jobs_root: Path):
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "peval.toml").write_text(
            "[[harbor.mounts]]\n"
            'id = "jobs-2026-08-08"\n'
            f"path = {json.dumps(str(jobs_root))}\n",
            encoding="utf-8",
        )
        config = ToolConfig(
            workspace_root=str(workspace),
            harbor_mounts=(HarborMount(id="jobs-2026-08-08", path=str(jobs_root)),),
        )
        store = open_workspace_state(str(workspace))
        return store, config, WorkspaceCatalog(store, config)

    def test_mount_config_is_explicit_stable_and_rejects_legacy_or_duplicates(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            workspace = base / "workspace"
            jobs = base / "jobs"
            dataset = base / "dataset"
            (dataset / "task-a").mkdir(parents=True)
            (dataset / "task-a" / "task.toml").write_text(
                '[task]\nname = "task-a"\n', encoding="utf-8"
            )
            write_trial(jobs / "job-a" / "trial-a")
            workspace.mkdir()
            (workspace / "peval.toml").write_text(
                '[[harbor.datasets]]\nid = "pbench"\npath = "../dataset"\n\n'
                '[[harbor.mounts]]\nid = "jobs-2026-08-08"\n'
                'path = "../jobs"\ndataset_ids = ["pbench"]\n',
                encoding="utf-8",
            )
            config = load_config(workspace_root=str(workspace))
            self.assertEqual(config.harbor_mounts[0].id, "jobs-2026-08-08")
            self.assertEqual(config.harbor_mounts[0].path, str(jobs.absolute()))
            self.assertEqual(
                config.harbor_datasets[0].path,
                str(dataset.absolute()),
            )
            self.assertEqual(config.harbor_mounts[0].dataset_ids, ("pbench",))

            duplicate_id = {
                "harbor": {
                    "mounts": [
                        {"id": "same", "path": str(jobs)},
                        {"id": "same", "path": str(base / "other")},
                    ]
                }
            }
            from psycheval.config import apply_toml_config

            with self.assertRaisesRegex(ValueError, "duplicate harbor mount id"):
                apply_toml_config(ToolConfig(), duplicate_id)
            with self.assertRaisesRegex(
                ValueError, "harbor.roots: unknown configuration field"
            ):
                apply_toml_config(ToolConfig(), {"harbor": {"roots": [str(jobs)]}})
            with self.assertRaisesRegex(ValueError, "lowercase path-safe"):
                apply_toml_config(
                    ToolConfig(),
                    {"harbor": {"mounts": [{"id": "Bad ID", "path": str(jobs)}]}},
                )
            with self.assertRaisesRegex(ValueError, "duplicate harbor mount path"):
                apply_toml_config(
                    ToolConfig(),
                    {
                        "harbor": {
                            "mounts": [
                                {"id": "one", "path": str(jobs)},
                                {"id": "two", "path": str(jobs)},
                            ]
                        }
                    },
                )
            with self.assertRaisesRegex(ValueError, "duplicate harbor dataset path"):
                apply_toml_config(
                    ToolConfig(),
                    {
                        "harbor": {
                            "datasets": [
                                {"id": "one", "path": str(dataset)},
                                {"id": "two", "path": str(dataset)},
                            ]
                        }
                    },
                )
            with self.assertRaisesRegex(ValueError, "duplicate dataset id pbench"):
                apply_toml_config(
                    ToolConfig(),
                    {
                        "harbor": {
                            "datasets": [
                                {"id": "pbench", "path": str(dataset)},
                            ],
                            "mounts": [
                                {
                                    "id": "jobs",
                                    "path": str(jobs),
                                    "dataset_ids": ["pbench", "pbench"],
                                }
                            ],
                        }
                    },
                )
            with self.assertRaisesRegex(
                ValueError, "harbor.mounts.0.task_paths: unknown configuration field"
            ):
                apply_toml_config(
                    ToolConfig(),
                    {
                        "harbor": {
                            "mounts": [
                                {
                                    "id": "one",
                                    "path": str(jobs),
                                    "task_paths": [str(dataset)],
                                }
                            ]
                        }
                    },
                )

    def test_windows_mount_path_is_mapped_without_resolving_away_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            workspace = base / "workspace"
            mapped = base / "mnt" / "c" / "jobs"
            write_trial(mapped / "job-a" / "trial-a")
            workspace.mkdir()
            (workspace / "peval.toml").write_text(
                "[[harbor.mounts]]\nid = \"windows-jobs\"\npath = 'C:\\jobs'\n",
                encoding="utf-8",
            )
            with patch("psycheval.config.WINDOWS_DRIVE_MOUNT_ROOT", base / "mnt"):
                config = load_config(workspace_root=str(workspace))
            self.assertEqual(config.harbor_mounts[0].path, str(mapped.absolute()))

    def test_only_configured_jobs_roots_are_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            workspace = base / "workspace"
            jobs = base / "mounted-jobs"
            mounted = jobs / "job-a" / "trial-a"
            implicit = workspace / "jobs" / "job-hidden" / "trial-hidden"
            write_trial(mounted)
            write_trial(implicit)
            store, config, catalog = self.workspace(workspace, jobs)
            try:
                catalog.reconcile()
                page = catalog.query(CatalogQuery(state="all", include_unreadable=True))
                self.assertEqual(page.total, 1)
                row = page.items[0].to_dict()
                self.assertEqual(
                    row["source_ref"],
                    "harbor/jobs-2026-08-08/job-a/trial-a",
                )
                self.assertNotIn("artifact_dir", row)
                self.assertFalse((workspace / "harbor").exists())
            finally:
                store.close()

    def test_legacy_harbor_link_requires_a_new_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            write_trial(jobs / "job-a" / "trial-a")
            workspace = base / "workspace"
            legacy = (
                workspace / "runs/default/harbor/legacy/trial/.peval/harbor-link.json"
            )
            legacy.parent.mkdir(parents=True)
            legacy.write_text("{}", encoding="utf-8")
            store, config, catalog = self.workspace(workspace, jobs)
            try:
                with self.assertRaisesRegex(ValueError, "initialize a new"):
                    catalog.reconcile()
            finally:
                store.close()

    def test_direct_job_trial_missing_and_symlink_mounts_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            workspace = base / "workspace"
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            write_trial(trial)
            for invalid in (jobs / "job-a", trial, base / "missing"):
                store, config, catalog = self.workspace(workspace, invalid)
                try:
                    with self.assertRaisesRegex(ValueError, "jobs root|not found"):
                        catalog.reconcile()
                finally:
                    store.close()
                    shutil.rmtree(workspace)
            linked = base / "linked"
            try:
                os.symlink(jobs, linked, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")
            store, config, catalog = self.workspace(workspace, linked)
            try:
                with self.assertRaisesRegex(ValueError, "symlink"):
                    catalog.reconcile()
            finally:
                store.close()

            task_workspace = base / "task-workspace"
            task_workspace.mkdir()
            store = open_workspace_state(str(task_workspace))
            config = ToolConfig(
                workspace_root=str(task_workspace),
                harbor_datasets=(
                    HarborDataset(
                        id="missing",
                        path=str(base / "missing-dataset"),
                    ),
                ),
                harbor_mounts=(
                    HarborMount(
                        id="jobs-with-tasks",
                        path=str(jobs),
                        dataset_ids=("missing",),
                    ),
                ),
            )
            try:
                with self.assertRaisesRegex(ValueError, "Dataset path.*not found"):
                    WorkspaceCatalog(store, config).reconcile()
            finally:
                store.close()

    def test_workspace_overlay_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            write_trial(jobs / "job-a" / "trial-a")
            workspace = base / "workspace"
            store, config, catalog = self.workspace(workspace, jobs)
            overlay_target = base / "overlay-target"
            overlay_target.mkdir()
            try:
                os.symlink(
                    overlay_target,
                    workspace / "harbor",
                    target_is_directory=True,
                )
            except OSError as exc:
                store.close()
                self.skipTest(f"directory symlinks unavailable: {exc}")
            try:
                with self.assertRaisesRegex(ValueError, "overlay root"):
                    catalog.reconcile()
            finally:
                store.close()

    def test_running_completed_errored_and_multi_step_are_derived(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            write_trial(jobs / "job-a" / "running")
            write_trial(
                jobs / "job-a" / "completed", result=completed_result(reward=0.8)
            )
            unique = completed_result()
            unique["verifier_result"] = {"rewards": {"accuracy": 0.6}}
            write_trial(jobs / "job-a" / "unique", result=unique)
            multi_reward = completed_result()
            multi_reward["verifier_result"] = {
                "rewards": {"accuracy": 0.6, "safety": 1.0}
            }
            write_trial(jobs / "job-a" / "multi-reward", result=multi_reward)
            errored = completed_result()
            errored["exception_info"] = {"exception_type": "RuntimeError"}
            write_trial(jobs / "job-a" / "errored", result=errored)
            multi = jobs / "job-a" / "multi"
            write_trial(multi)
            write_trial(multi / "steps" / "step-1")
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                page = catalog.query(CatalogQuery(state="all", include_unreadable=True))
                rows = {
                    item.to_dict()["label"].split("/")[-1]: item.to_dict()
                    for item in page.items
                }
                self.assertEqual(rows["running"]["status"], "running")
                self.assertEqual(rows["completed"]["status"], "completed")
                self.assertEqual(rows["completed"]["score"], 0.8)
                self.assertEqual(rows["unique"]["score"], 0.6)
                self.assertEqual(rows["unique"]["rewards"], {"accuracy": 0.6})
                self.assertIsNone(rows["multi-reward"]["score"])
                self.assertEqual(
                    rows["multi-reward"]["rewards"],
                    {"accuracy": 0.6, "safety": 1.0},
                )
                summary = catalog.summarize_saved_views(
                    [("all", CatalogQuery(), "overall")]
                )["views"][0]
                score_metric = next(
                    metric
                    for metric in summary["groups"][0]["metrics"]
                    if metric["key"] == "score"
                )
                self.assertEqual(score_metric["count"], 3)
                self.assertEqual(rows["errored"]["status"], "errored")
                multi_row = next(
                    item.to_dict()
                    for item in page.items
                    if item.to_dict()["source_ref"].endswith("/multi/steps/step-1")
                )
                self.assertTrue(multi_row["readable"])
                self.assertEqual(multi_row["status"], "running")
                self.assertEqual(multi_row["step_name"], "step-1")
            finally:
                store.close()

    def test_older_harbor_atif_and_missing_aggregates_are_projected_in_memory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            trajectory = atif_trajectory()
            trajectory["schema_version"] = "ATIF-v1.2"
            trajectory["steps"][1]["tool_calls"] = [
                {
                    "tool_call_id": "call-1",
                    "function_name": "search",
                    "arguments": {"query": "example"},
                }
            ]
            trajectory["steps"][1]["observation"] = {
                "results": [{"source_call_id": "call-1", "content": "result"}]
            }
            trajectory["final_metrics"] = {"total_steps": 2}
            result = completed_result()
            result["agent_execution"] = {
                "started_at": "2026-08-08T01:00:00.250Z",
                "finished_at": "2026-08-08T01:00:01.750Z",
            }
            result["agent_result"] = {
                "n_input_tokens": 7,
                "n_output_tokens": 3,
                "n_cache_tokens": 2,
                "cost_usd": 0.01,
            }
            write_trial(trial, trajectory=trajectory, result=result)
            source_before = (trial / "agent/trajectory.json").read_bytes()
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                row = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertTrue(row["readable"])
                self.assertEqual(row["turns"], 1)
                self.assertEqual(row["total_tool_calls"], 1)
                self.assertEqual(row["total_tool_errors"], 0)
                self.assertEqual(row["tokens"], 10)
                self.assertEqual(row["cost_usd"], 0.01)
                self.assertEqual(row["duration_ms"], 1_500)
                detail = catalog.load_detail(row["source_key"]).report
                self.assertEqual(detail["trajectory"][0]["schema_version"], "ATIF-v1.7")
                self.assertEqual(
                    detail["trajectory"][0]["final_metrics"]["extra"],
                    {
                        "total_turns": 1,
                        "total_tool_calls": 1,
                        "total_tool_errors": 0,
                    },
                )
                self.assertEqual(
                    detail["trajectory_meta"][0]["wall_duration_ms"], 2_000
                )
                self.assertEqual(
                    (trial / "agent/trajectory.json").read_bytes(), source_before
                )
                self.assertFalse((base / "workspace" / "harbor").exists())
            finally:
                store.close()

    def test_multi_step_mount_uses_step_source_refs_and_step_overlays(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "multi"
            write_trial(trial)
            (trial / "agent" / "trajectory.json").unlink()
            write_trial(trial / "steps" / "first", trajectory=atif_trajectory("first"))
            write_trial(
                trial / "steps" / "second", trajectory=atif_trajectory("second")
            )
            result = completed_result(reward=0.5)
            result["step_results"] = [
                {
                    "step_name": "second",
                    "verifier_result": {"rewards": {"reward": 0.2}},
                },
                {
                    "step_name": "first",
                    "verifier_result": {"rewards": {"reward": 0.8}},
                },
            ]
            (trial / "result.json").write_text(json.dumps(result), encoding="utf-8")
            source_before = {
                path.relative_to(trial).as_posix(): path.read_bytes()
                for path in trial.rglob("*")
                if path.is_file()
            }
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                page = catalog.query(CatalogQuery(state="all"))
                rows = {
                    item.to_dict()["step_name"]: item.to_dict() for item in page.items
                }
                self.assertEqual(set(rows), {"first", "second"})
                self.assertTrue(
                    rows["first"]["source_ref"].endswith("/multi/steps/first")
                )
                self.assertEqual(rows["first"]["score"], 0.8)
                self.assertEqual(rows["second"]["score"], 0.2)
                source_ref = rows["first"]["source_ref"]
                catalog.sources.write_overlay(
                    source_ref,
                    {"source_alias": "First phase"},
                )
                catalog.reconcile()
                detail = catalog.load_detail(rows["first"]["source_key"]).report
                self.assertEqual(
                    detail["trajectory_meta"][0]["harbor_step"],
                    {"name": "first", "index": 2, "count": 2},
                )
                self.assertEqual(
                    detail["trajectory_meta"][0]["harbor_trial_evaluation"]["score"],
                    0.5,
                )
                self.assertEqual(
                    (base / "workspace" / source_ref / "state.json").is_file(),
                    True,
                )
                source_after = {
                    path.relative_to(trial).as_posix(): path.read_bytes()
                    for path in trial.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(source_after, source_before)
                shutil.rmtree(trial)
                catalog.reconcile()
                retained = catalog.row_for_key(rows["first"]["source_key"])
                self.assertFalse(retained["readable"])
                self.assertEqual(retained["last_status"], "missing")
                self.assertEqual(retained["source_ref"], source_ref)
            finally:
                store.close()

    def test_aligned_opencode_telemetry_refines_active_timing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            database = trial / "agent/opencode/xdg-data/opencode/opencode.db"
            database.parent.mkdir(parents=True)
            create_opencode_event_timing_db(database)
            converted = convert_db(
                str(database), "ses-latest", ToolConfig(adapter="opencode")
            )
            trajectory = deepcopy(converted.trajectory)
            trajectory["final_metrics"].pop("extra", None)
            for step in trajectory["steps"]:
                step.pop("extra", None)
                for call in step.get("tool_calls") or []:
                    call.pop("extra", None)
                for observation in (step.get("observation") or {}).get("results") or []:
                    observation.pop("extra", None)
            result = completed_result()
            result["agent_execution"] = {
                "started_at": "1970-01-01T00:00:02Z",
                "finished_at": "1970-01-01T00:01:00Z",
            }
            write_trial(trial, trajectory=trajectory, result=result)
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                row = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertEqual(row["duration_ms"], 48_100)
                self.assertEqual(row["turns"], 1)
                self.assertEqual(row["total_tool_calls"], 1)
                self.assertEqual(row["total_tool_errors"], 0)
                self.assertEqual(row["model_duration_ms"], 100)
            finally:
                store.close()

    def test_aligned_hermes_session_export_supplies_usage_and_model_timing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            trajectory = atif_trajectory("hermes-export")
            trajectory["trajectory_id"] = "hermes:hermes-export"
            trajectory["agent"] = {
                "name": "hermes",
                "version": "0.20.0",
                "model_name": "hermes-export-model",
            }
            trajectory["schema_version"] = "ATIF-v1.2"
            trajectory["steps"][0]["message"] = "hello"
            trajectory["steps"][1]["message"] = "answer"
            trajectory["final_metrics"] = {"total_steps": 2}
            write_trial(trial, trajectory=trajectory, result=completed_result())
            export_path = trial / "agent/hermes-session.jsonl"
            export_path.write_text(
                json.dumps(
                    {
                        "id": "native-hermes-session",
                        "model": "hermes-export-model",
                        "started_at": 100.0,
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "cache_read_tokens": 30,
                        "cache_write_tokens": 5,
                        "reasoning_tokens": 2,
                        "messages": [
                            {
                                "id": 1,
                                "session_id": "native-hermes-session",
                                "role": "user",
                                "content": "hello",
                                "timestamp": 100.0,
                            },
                            {
                                "id": 2,
                                "session_id": "native-hermes-session",
                                "role": "assistant",
                                "content": "answer",
                                "timestamp": 102.5,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                row = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertEqual(row["tokens"], 155)
                self.assertEqual(row["model_duration_ms"], 2_500)
                self.assertEqual(row["duration_ms"], 2_500)
            finally:
                store.close()

    def test_supplemental_telemetry_must_belong_to_the_same_session(self) -> None:
        source = atif_trajectory("harbor-session")
        telemetry = deepcopy(source)
        telemetry["session_id"] = "different-session"

        self.assertFalse(_telemetry_aligns(source, telemetry))

    def test_late_psychevo_trace_invalidates_catalog_and_supplies_exact_timing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            database = trial / "agent/psychevo-state.db"
            database.parent.mkdir(parents=True)
            create_messages_db(database)
            converted = convert_db(
                str(database), "db-b", ToolConfig(adapter="psychevo")
            )
            trajectory = deepcopy(converted.trajectory)
            trajectory["final_metrics"] = {"total_steps": len(trajectory["steps"])}
            for step in trajectory["steps"]:
                step.pop("metrics", None)
                step.pop("extra", None)
            write_trial(trial, trajectory=trajectory, result=completed_result())
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                row = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertIsNone(row["model_duration_ms"])
                self.assertEqual(row["tokens"], 12)

                trace_dir = trial / "agent/sessions/db-b"
                trace_dir.mkdir(parents=True)
                (trace_dir / "events.jsonl").write_text(
                    json.dumps(
                        {
                            "schema_version": 2,
                            "seq": 1,
                            "session_id": "db-b",
                            "kind": "generation_end",
                            "timestamp_ms": 440,
                            "payload": {"elapsed_ms": 42},
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                catalog.reconcile()
                row = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertEqual(row["model_duration_ms"], 42)
                self.assertEqual(row["tokens"], 12)
            finally:
                store.close()

    def test_result_only_failure_keeps_catalog_diagnostic_without_trajectory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            result = completed_result()
            result["exception_info"] = {
                "exception_type": "AgentExitError",
                "exception_message": "agent command exited with status 17",
            }
            result["agent_info"] = {"name": "opencode", "version": "1.18.15"}
            result["agent_execution"] = {
                "started_at": "2026-08-08T01:00:00.250Z",
                "finished_at": "2026-08-08T01:00:01.750Z",
            }
            write_trial(trial, result=result)
            (trial / "agent/trajectory.json").unlink()
            config_payload = json.loads((trial / "config.json").read_text())
            config_payload["agent"] = {
                "name": "preinstalled:OpenCode",
                "model_name": "test-model",
            }
            (trial / "config.json").write_text(json.dumps(config_payload))
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                row = (
                    catalog.query(CatalogQuery(state="all", include_unreadable=True))
                    .items[0]
                    .to_dict()
                )
                self.assertFalse(row["readable"])
                self.assertEqual(row["last_status"], "errored")
                self.assertEqual(row["status"], "errored")
                self.assertEqual(row["agent_name"], "opencode")
                self.assertEqual(row["model"], "test-model")
                self.assertEqual(row["duration_ms"], 1_500)
                self.assertEqual(
                    row["last_error"],
                    "AgentExitError: agent command exited with status 17",
                )
                self.assertIsNone(row.get("step_outline"))
                with self.assertRaisesRegex(ValueError, "not readable"):
                    catalog.load_detail(row["source_key"])
            finally:
                store.close()

    def test_direct_refresh_keeps_identity_and_never_modifies_harbor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            write_trial(trial)
            before = {
                path.relative_to(trial).as_posix(): path.read_bytes()
                for path in trial.rglob("*")
                if path.is_file()
            }
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                first = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertEqual(first["status"], "running")
                detail = catalog.load_detail(first["source_key"])
                self.assertEqual(
                    detail.report["trajectory"][0]["session_id"], "harbor-session"
                )
                self.assertEqual(
                    store.harbor_source_keys(config), [first["source_key"]]
                )
                (trial / "result.json").write_text(
                    json.dumps(completed_result()), encoding="utf-8"
                )
                catalog.reconcile()
                second = catalog.row_for_key(first["source_key"])
                self.assertEqual(second["status"], "completed")
                self.assertEqual(second["source_ref"], first["source_ref"])
                after_without_result = {
                    path.relative_to(trial).as_posix(): path.read_bytes()
                    for path in trial.rglob("*")
                    if path.is_file() and path.name != "result.json"
                }
                self.assertEqual(after_without_result, before)
                self.assertFalse((base / "workspace" / "runs").exists())
                self.assertFalse(
                    any(path.name == ".peval" for path in trial.rglob("*"))
                )
                self.assertFalse((trial / "agent" / "trajectory_meta.json").exists())
                moved_jobs = base / "moved-jobs"
                jobs.rename(moved_jobs)
                moved_config = ToolConfig(
                    workspace_root=str(base / "workspace"),
                    harbor_mounts=(
                        HarborMount(id="jobs-2026-08-08", path=str(moved_jobs)),
                    ),
                )
                moved_catalog = WorkspaceCatalog(store, moved_config)
                moved_catalog.reconcile()
                moved_row = moved_catalog.row_for_key(first["source_key"])
                self.assertEqual(moved_row["source_ref"], first["source_ref"])
                self.assertEqual(
                    moved_catalog.load_detail(first["source_key"]).report["trajectory"][
                        0
                    ]["session_id"],
                    "harbor-session",
                )
            finally:
                store.close()

    def test_overlay_is_lazy_minimal_and_removed_when_defaults_are_restored(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            write_trial(jobs / "job-a" / "trial-a")
            workspace = base / "workspace"
            store, config, catalog = self.workspace(workspace, jobs)
            try:
                catalog.reconcile()
                row = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertFalse((workspace / "harbor").exists())
                store.set_source_alias_row(row, "Primary")
                state_path = (
                    workspace / "harbor/jobs-2026-08-08/job-a/trial-a/state.json"
                )
                self.assertEqual(
                    json.loads(state_path.read_text(encoding="utf-8")),
                    {"schema_version": 1, "source_alias": "Primary"},
                )
                catalog._delete_database_files()
                rebuilt = WorkspaceCatalog(store, config)
                rebuilt.reconcile()
                rebuilt_row = rebuilt.query(CatalogQuery()).items[0].to_dict()
                self.assertEqual(rebuilt_row["source_alias"], "Primary")
                store.set_source_alias_row(row, None)
                self.assertFalse((workspace / "harbor").exists())
            finally:
                store.close()

    def test_deleted_sources_disappear_unless_overlay_or_report_retains_them(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            write_trial(trial)
            workspace = base / "workspace"
            store, config, catalog = self.workspace(workspace, jobs)
            reports = WorkspaceReportLibrary(workspace, catalog.binding_rows)
            try:
                catalog.reconcile()
                row = catalog.query(CatalogQuery()).items[0].to_dict()
                source_key = row["source_key"]
                shutil.rmtree(trial)
                catalog.reconcile()
                self.assertEqual(
                    catalog.query(
                        CatalogQuery(state="all", include_unreadable=True)
                    ).total,
                    0,
                )

                write_trial(trial)
                catalog.reconcile()
                row = catalog.row_for_key(source_key)
                store.set_source_alias_row(row, "Keep")
                shutil.rmtree(trial)
                catalog.reconcile()
                missing = catalog.row_for_key(source_key)
                self.assertFalse(missing["readable"])
                self.assertEqual(missing["last_status"], "missing")
                self.assertEqual(missing["source_alias"], "Keep")

                write_trial(trial)
                catalog.reconcile()
                restored = catalog.row_for_key(source_key)
                self.assertTrue(restored["readable"])
                store.set_source_alias_row(restored, None)
                report_file = base / "report.md"
                report_file.write_text("# Report", encoding="utf-8")
                reports.import_file(report_file, [source_key])
                shutil.rmtree(trial)
                catalog.reconcile()
                self.assertFalse(catalog.row_for_key(source_key)["readable"])
                self.assertEqual(reports.catalog()[0]["source_keys"], [source_key])
            finally:
                store.close()

    def test_invalid_current_trajectory_has_no_last_good_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            write_trial(trial)
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                source_key = catalog.query(CatalogQuery()).items[0].source_key
                (trial / "agent" / "trajectory.json").write_text("{", encoding="utf-8")
                catalog.reconcile()
                row = catalog.row_for_key(source_key)
                self.assertFalse(row["readable"])
                self.assertIn("failed to parse", row["last_error"])
                with self.assertRaisesRegex(ValueError, "not readable"):
                    catalog.load_detail(source_key)
            finally:
                store.close()

    def test_only_trial_root_analysis_markdown_is_presented(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            write_trial(trial)
            harbor_analysis = trial / "analysis.md"
            harbor_analysis.write_text("# Harbor review\n", encoding="utf-8")
            workspace = base / "workspace"
            store, config, catalog = self.workspace(workspace, jobs)
            overlay = workspace / "harbor/jobs-2026-08-08/job-a/trial-a/analysis.md"
            overlay.parent.mkdir(parents=True)
            overlay.write_text("# Workspace review\n", encoding="utf-8")
            before = {
                path.relative_to(trial).as_posix(): path.read_bytes()
                for path in trial.rglob("*")
                if path.is_file()
            }
            try:
                catalog.reconcile()
                row = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertEqual(row["analysis_count"], 1)
                self.assertNotIn("analysised", row)
                analysis = catalog.load_detail(row["source_key"]).report["annotations"][
                    "analysis"
                ][0]
                self.assertNotIn("md_report", analysis)
                self.assertEqual(
                    analysis["markdown_reports"],
                    [
                        {
                            "source": "harbor_trial",
                            "markdown": "# Harbor review\n",
                            "relative_path": "analysis.md",
                        },
                    ],
                )
                json_export = build_serve_export(
                    catalog,
                    store,
                    config,
                    kind="json",
                    source_keys=[row["source_key"]],
                )
                json_analysis = json.loads(json_export.content)["annotations"][
                    "analysis"
                ][0]
                self.assertEqual(
                    json_analysis["markdown_reports"],
                    analysis["markdown_reports"],
                )

                after = {
                    path.relative_to(trial).as_posix(): path.read_bytes()
                    for path in trial.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(after, before)

                harbor_analysis.unlink()
                catalog.reconcile()
                self.assertEqual(
                    catalog.row_for_key(row["source_key"])["analysis_count"], 0
                )
                overlay_only = catalog.load_detail(row["source_key"]).report[
                    "annotations"
                ]["analysis"][0]
                self.assertNotIn("markdown_reports", overlay_only)
                self.assertEqual(
                    overlay.read_text(encoding="utf-8"), "# Workspace review\n"
                )
            finally:
                store.close()

    def test_harbor_analysis_refreshes_and_unsafe_inputs_stay_supplemental(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            write_trial(trial)
            analysis = trial / "analysis.md"
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                row = catalog.query(CatalogQuery()).items[0].to_dict()
                source_key = row["source_key"]
                first_revision = row["artifact_revision"]
                self.assertEqual(row["analysis_count"], 0)

                analysis.write_text("first", encoding="utf-8")
                catalog.reconcile()
                row = catalog.row_for_key(source_key)
                second_revision = row["artifact_revision"]
                self.assertNotEqual(second_revision, first_revision)
                self.assertEqual(row["analysis_count"], 1)
                self.assertEqual(
                    catalog.load_detail(source_key).report["annotations"]["analysis"][
                        0
                    ]["markdown_reports"][0]["markdown"],
                    "first",
                )

                analysis.write_text("second and longer", encoding="utf-8")
                catalog.reconcile()
                row = catalog.row_for_key(source_key)
                self.assertNotEqual(row["artifact_revision"], second_revision)
                self.assertEqual(
                    catalog.load_detail(source_key).report["annotations"]["analysis"][
                        0
                    ]["markdown_reports"][0]["markdown"],
                    "second and longer",
                )

                for content in (b" \n", b"\xff\xfe"):
                    analysis.write_bytes(content)
                    catalog.reconcile()
                    row = catalog.row_for_key(source_key)
                    self.assertTrue(row["readable"])
                    self.assertEqual(row["analysis_count"], 0)
                    self.assertNotIn(
                        "markdown_reports",
                        catalog.load_detail(source_key).report["annotations"][
                            "analysis"
                        ][0],
                    )

                analysis.unlink()
                secret = base / "secret.md"
                secret.write_text("must not leak", encoding="utf-8")
                try:
                    analysis.symlink_to(secret)
                except OSError:
                    pass
                else:
                    catalog.reconcile()
                    row = catalog.row_for_key(source_key)
                    self.assertTrue(row["readable"])
                    self.assertEqual(row["analysis_count"], 0)
                    self.assertNotIn(
                        "must not leak",
                        json.dumps(catalog.load_detail(source_key).report),
                    )
                    analysis.unlink()

                analysis.mkdir()
                catalog.reconcile()
                row = catalog.row_for_key(source_key)
                self.assertTrue(row["readable"])
                self.assertEqual(row["analysis_count"], 0)
                analysis.rmdir()

                catalog.reconcile()
                row = catalog.row_for_key(source_key)
                self.assertEqual(row["analysis_count"], 0)
            finally:
                store.close()

    def test_harbor_analysis_ignores_nested_log_fallbacks(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            write_trial(trial)
            first = trial / "artifacts/logs/a/analysis.md"
            second = trial / "artifacts/logs/z/analysis.md"
            second.parent.mkdir(parents=True)
            first.parent.mkdir(parents=True)
            second.write_text("# Second path\n", encoding="utf-8")
            first.write_text("# First path\n", encoding="utf-8")
            external = base / "external-analysis"
            external.mkdir()
            (external / "analysis.md").write_text("must not traverse", encoding="utf-8")
            linked = trial / "artifacts/logs/0-linked"
            try:
                linked.symlink_to(external, target_is_directory=True)
            except OSError:
                pass
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                row = catalog.query(CatalogQuery()).items[0].to_dict()
                source_key = row["source_key"]
                nested_revision = row["artifact_revision"]
                self.assertEqual(row["analysis_count"], 0)
                self.assertNotIn(
                    "markdown_reports",
                    catalog.load_detail(source_key).report["annotations"]["analysis"][
                        0
                    ],
                )
                self.assertNotIn(
                    "must not traverse",
                    json.dumps(catalog.load_detail(source_key).report),
                )

                canonical = trial / "analysis.md"
                canonical.write_text("# Canonical\n", encoding="utf-8")
                catalog.reconcile()
                row = catalog.row_for_key(source_key)
                self.assertNotEqual(row["artifact_revision"], nested_revision)
                canonical_revision = row["artifact_revision"]
                self.assertEqual(
                    catalog.load_detail(source_key).report["annotations"]["analysis"][
                        0
                    ]["markdown_reports"][0]["relative_path"],
                    "analysis.md",
                )

                canonical.unlink()
                catalog.reconcile()
                row = catalog.row_for_key(source_key)
                self.assertNotEqual(row["artifact_revision"], canonical_revision)
                self.assertNotIn(
                    "markdown_reports",
                    catalog.load_detail(source_key).report["annotations"]["analysis"][
                        0
                    ],
                )
            finally:
                store.close()

    def test_deep_harbor_analysis_fallback_is_ignored_without_scanning(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            write_trial(trial)
            nested = trial / "artifacts" / "logs"
            nested.mkdir(parents=True)
            nested_directories: list[Path] = []
            for _index in range(1_050):
                nested /= "d"
                nested.mkdir()
                nested_directories.append(nested)
            analysis = nested / "analysis.md"
            analysis.write_text("# Deep review\n", encoding="utf-8")
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                catalog.reconcile()
                row = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertEqual(row["analysis_count"], 0)
                analysis_payload = catalog.load_detail(row["source_key"]).report[
                    "annotations"
                ]["analysis"][0]
                self.assertNotIn("markdown_reports", analysis_payload)
            finally:
                store.close()
                analysis.unlink(missing_ok=True)
                for directory in reversed(nested_directories):
                    directory.rmdir()

    def test_oversized_harbor_analysis_is_hidden_without_breaking_trial(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            write_trial(trial)
            analysis = trial / "analysis.md"
            analysis.write_text("too large", encoding="utf-8")
            store, config, catalog = self.workspace(base / "workspace", jobs)
            try:
                with patch(
                    "psycheval.state.workspace_harbor.HARBOR_ANALYSIS_MAX_BYTES",
                    4,
                ):
                    catalog.reconcile()
                    row = catalog.query(CatalogQuery()).items[0].to_dict()
                    self.assertTrue(row["readable"])
                    self.assertEqual(row["analysis_count"], 0)
                    self.assertNotIn(
                        "markdown_reports",
                        catalog.load_detail(row["source_key"]).report["annotations"][
                            "analysis"
                        ][0],
                    )
            finally:
                store.close()

    def test_analysis_import_rejects_harbor_source_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            write_trial(jobs / "job-a" / "trial-a")
            workspace = base / "workspace"
            store, config, catalog = self.workspace(workspace, jobs)
            analysis = base / "analysis.json"
            analysis.write_text(json.dumps({"summary": "direct"}), encoding="utf-8")
            try:
                with self.assertRaisesRegex(
                    ValueError,
                    "peval publish evaluation-report",
                ):
                    import_analysis_artifacts(
                        workspace_root=workspace,
                        source_ref="harbor/jobs-2026-08-08/job-a/trial-a",
                        input_paths=[str(analysis)],
                    )
                self.assertFalse(
                    (
                        workspace / "harbor/jobs-2026-08-08/job-a/trial-a/analysis.json"
                    ).exists()
                )
                self.assertFalse(
                    (jobs / "job-a" / "trial-a" / "analysis.json").exists()
                )
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
