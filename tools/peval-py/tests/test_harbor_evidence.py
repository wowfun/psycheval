from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from peval_py._inspection.frames import InspectFrames
from peval_py.config import HarborDataset, HarborMount, ToolConfig
from peval_py.serve.exports import build_serve_export
from peval_py.state import (
    CatalogQuery,
    WorkspaceCatalog,
    harbor_evidence,
    open_workspace_state,
)
from peval_py.state.harbor_evidence import read_harbor_evidence
from peval_py.state.workspace_sources import WorkspaceSources


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_task(
    path: Path,
    name: str,
    *,
    keywords: tuple[str, ...] = ("web-agent", "web-search"),
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    keyword_list = ", ".join(json.dumps(value) for value in keywords)
    (path / "task.toml").write_text(
        "[task]\n"
        f"name = {json.dumps(name)}\n"
        'version = "1.0"\n'
        'description = "Live description"\n'
        f"keywords = [{keyword_list}]\n",
        encoding="utf-8",
    )
    (path / "instruction.md").write_text("Do the task.\n", encoding="utf-8")
    (path / "environment").mkdir()
    (path / "environment" / "Dockerfile").write_text(
        "FROM python:3.12-slim\n", encoding="utf-8"
    )
    (path / "tests").mkdir()
    (path / "tests" / "test.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")


def write_evidence_trial(
    trial: Path,
    *,
    config_task: dict[str, object] | None = None,
    lock_task: dict[str, object] | None = None,
    result: dict[str, object] | None = None,
    model_name: str = "model-without-provider",
) -> None:
    job = trial.parent
    write_json(
        job / "config.json",
        {
            "job_name": "configured-job",
            "jobs_dir": str(job.parent),
            "agents": ["agent"],
            "tasks": ["task"],
        },
    )
    write_json(
        job / "lock.json",
        {"schema_version": 1, "trials": [], "harbor": {"version": "0.21.0"}},
    )
    write_json(job / "result.json", {"id": "job-result-id"})
    write_json(
        trial / "config.json",
        {
            "trial_name": "config-trial",
            "job_id": "job-id",
            "task": config_task or {},
            "agent": {"model_name": model_name},
        },
    )
    if lock_task is not None:
        write_json(
            trial / "lock.json",
            {
                "task": lock_task,
                "source_trial": {
                    "action": "regrade",
                    "trial_id": "original-trial",
                    "task": {"digest": "sha256:source"},
                },
            },
        )
    write_json(
        trial / "agent" / "trajectory.json",
        {
            "schema_version": "ATIF-v1.7",
            "trajectory_id": "trial",
            "session_id": "session",
            "agent": {"name": "agent", "version": "1", "model_name": model_name},
            "steps": [
                {
                    "step_id": 1,
                    "source": "user",
                    "message": "task",
                    "timestamp": "2026-08-12T00:00:00Z",
                }
            ],
            "final_metrics": {"total_steps": 1},
        },
    )
    if result is not None:
        write_json(trial / "result.json", result)


class HarborEvidenceTests(unittest.TestCase):
    def read(self, trial: Path, task_paths: tuple[Path, ...] = ()):
        return read_harbor_evidence(
            trial,
            jobs_root=trial.parents[1],
            task_paths=tuple(str(path) for path in task_paths),
            mount_id="jobs",
        )

    def test_identity_provider_provenance_and_phase_timing_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset"
            task = dataset / "web-search-01"
            write_task(task, "pbench-v1.0/web-search-01")
            trial = root / "jobs" / "job-dir" / "trial-dir"
            result = {
                "id": "result-id",
                "trial_name": "result-trial",
                "task_name": "pbench-v1.0/web-search-01",
                "started_at": "2026-08-12T00:00:00Z",
                "finished_at": "2026-08-12T00:00:10Z",
                "agent_info": {"model_info": {"provider": "explicit-provider"}},
                "environment_setup": {
                    "started_at": "2026-08-12T00:00:00Z",
                    "finished_at": "2026-08-12T00:00:01Z",
                },
                "agent_setup": {
                    "started_at": "2026-08-12T00:00:01Z",
                    "finished_at": "2026-08-12T00:00:02Z",
                },
                "agent_execution": {
                    "started_at": "2026-08-12T00:00:02Z",
                    "finished_at": "2026-08-12T00:00:08Z",
                },
                "verifier": {
                    "started_at": "2026-08-12T00:00:08Z",
                    "finished_at": "2026-08-12T00:00:10Z",
                },
            }
            write_evidence_trial(
                trial,
                config_task={"name": "config-task"},
                lock_task={
                    "name": "lock-task",
                    "source": "pbench-v1.0",
                    "path": "datasets/pbench-v1.0/web-search-01",
                    "digest": "sha256:recorded",
                    "version": "recorded-version",
                },
                result=result,
                model_name="fallback-provider/model",
            )

            evidence = self.read(trial, (dataset,))

            self.assertEqual(evidence.task_name, "pbench-v1.0/web-search-01")
            self.assertEqual(evidence.job_name, "configured-job")
            self.assertEqual(evidence.trial_name, "result-trial")
            self.assertEqual(evidence.model_provider, "explicit-provider")
            self.assertEqual(evidence.task_keywords, ("web-agent", "web-search"))
            self.assertEqual(evidence.task_metadata["status"], "digest_mismatch")
            self.assertTrue(evidence.task_metadata["live"])
            self.assertEqual(evidence.provenance["job_id"], "job-id")
            self.assertEqual(evidence.provenance["result_id"], "result-id")
            self.assertEqual(evidence.provenance["harbor_version"], "0.21.0")
            self.assertEqual(evidence.provenance["task_digest"], "sha256:recorded")
            self.assertEqual(evidence.provenance["task_source"], "pbench-v1.0")
            self.assertEqual(evidence.provenance["task_version"], "recorded-version")
            self.assertEqual(
                evidence.provenance["regrade"]["trial_id"], "original-trial"
            )
            self.assertEqual(
                set(evidence.phase_timing),
                {
                    "overall",
                    "environment_setup",
                    "agent_setup",
                    "agent_execution",
                    "verifier",
                },
            )
            self.assertEqual(evidence.phase_timing["overall"]["duration_ms"], 10_000)
            self.assertEqual(
                evidence.phase_timing["agent_execution"]["duration_ms"], 6_000
            )

    def test_consistency_check_retries_then_rejects_unstable_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trial = root / "jobs" / "job" / "trial"
            write_evidence_trial(trial)
            changing = [(str(index),) for index in range(12)]
            with patch(
                "peval_py.state.harbor_evidence._json_signatures",
                side_effect=changing,
            ):
                with self.assertRaisesRegex(ValueError, "changed while"):
                    self.read(trial)

    def test_task_name_falls_back_from_result_to_lock_then_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trial = root / "jobs" / "job" / "trial"
            write_evidence_trial(
                trial,
                config_task={"name": "config-task", "source": "config-source"},
                lock_task={"name": "lock-task", "source": "lock-source"},
                result={"task_name": "result-task"},
            )
            self.assertEqual(self.read(trial).task_name, "lock-source/result-task")
            (trial / "result.json").unlink()
            self.assertEqual(self.read(trial).task_name, "lock-source/lock-task")
            (trial / "lock.json").unlink()
            self.assertEqual(self.read(trial).task_name, "config-source/config-task")

    def test_task_metadata_path_match_name_ambiguity_and_digest_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "dataset-a" / "task"
            second = root / "dataset-b" / "task"
            write_task(first, "org/task")
            write_task(second, "org/task", keywords=("duplicate",))
            trial = root / "jobs" / "job" / "trial"
            write_evidence_trial(
                trial,
                config_task={"name": "task", "source": "org"},
                lock_task={"name": "task", "source": "org"},
            )

            ambiguous = self.read(trial, (first.parent, second.parent))
            self.assertEqual(ambiguous.task_metadata["status"], "ambiguous")
            self.assertEqual(ambiguous.task_keywords, ())

            write_json(
                trial / "lock.json",
                {
                    "task": {
                        "name": "task",
                        "source": "org",
                        "path": "nested/../dataset-a/./task",
                    }
                },
            )
            selected = self.read(trial, (first.parent, second.parent))
            self.assertEqual(selected.task_metadata["status"], "resolved")
            self.assertEqual(selected.task_keywords, ("web-agent", "web-search"))
            write_json(
                trial / "lock.json",
                {
                    "task": {
                        "name": "task",
                        "source": "org",
                        "path": "dataset-a/task",
                        "digest": selected.task_metadata["live_digest"],
                    }
                },
            )
            matched = self.read(trial, (first.parent, second.parent))
            self.assertEqual(matched.task_metadata["status"], "resolved")
            self.assertTrue(matched.task_metadata["digest_matches"])

            write_json(trial.parent / "lock.json", {"schema_version": 1})
            lock = json.loads((trial / "lock.json").read_text(encoding="utf-8"))
            lock["harbor"] = {"version": "0.21.0-trial"}
            write_json(trial / "lock.json", lock)
            self.assertEqual(
                self.read(trial, (first.parent, second.parent)).provenance[
                    "harbor_version"
                ],
                "0.21.0-trial",
            )

    def test_package_ref_digest_is_provenance_not_a_local_digest_comparison(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task = root / "dataset" / "task"
            write_task(task, "org/task")
            trial = root / "jobs" / "job" / "trial"
            write_evidence_trial(
                trial,
                config_task={
                    "name": "task",
                    "source": "org",
                    "ref": "sha256:published-artifact",
                },
            )

            evidence = self.read(trial, (task.parent,))

            self.assertEqual(evidence.task_metadata["status"], "resolved")
            self.assertIsNone(evidence.task_metadata["digest_matches"])
            self.assertEqual(
                evidence.task_metadata["digest_comparison"], "not_comparable"
            )
            self.assertEqual(
                evidence.provenance["task_digest"], "sha256:published-artifact"
            )
            self.assertEqual(evidence.provenance["task_digest_source"], "config.ref")

    def test_provider_requires_explicit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trial = root / "jobs" / "job" / "trial"
            write_evidence_trial(trial, model_name="plain-model")
            self.assertIsNone(self.read(trial).model_provider)
            write_evidence_trial(trial, model_name="provider/model")
            self.assertEqual(self.read(trial).model_provider, "provider")

    def test_task_metadata_reports_unconfigured_missing_and_invalid_states(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trial = root / "jobs" / "job" / "trial"
            write_evidence_trial(
                trial,
                config_task={"name": "wanted", "source": "org"},
            )
            self.assertEqual(self.read(trial).task_metadata["status"], "not_configured")

            dataset = root / "dataset"
            write_task(dataset / "other", "org/other")
            self.assertEqual(
                self.read(trial, (dataset,)).task_metadata["status"], "not_found"
            )

            invalid = dataset / "invalid"
            invalid.mkdir()
            (invalid / "task.toml").write_text("not toml = [", encoding="utf-8")
            write_json(
                trial / "lock.json",
                {
                    "task": {
                        "name": "wanted",
                        "source": "org",
                        "path": "dataset/invalid",
                    }
                },
            )
            metadata = self.read(trial, (dataset,)).task_metadata
            self.assertEqual(metadata["status"], "not_found")

    def test_parent_job_and_live_task_changes_invalidate_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs = root / "jobs"
            task = root / "dataset" / "task"
            write_task(task, "org/task")
            trial = jobs / "job" / "trial"
            write_evidence_trial(
                trial,
                config_task={
                    "name": "task",
                    "source": "org",
                    "digest": "sha256:recorded",
                },
                result={
                    "id": "result-id",
                    "task_name": "org/task",
                    "verifier_result": {"rewards": {"reward": 0}},
                },
                model_name="provider/model",
            )
            workspace = root / "workspace"
            store = open_workspace_state(str(workspace))
            config = ToolConfig(
                workspace_root=str(workspace),
                harbor_datasets=(HarborDataset(id="tasks", path=str(task.parent)),),
                harbor_mounts=(
                    HarborMount(
                        id="jobs",
                        path=str(jobs),
                        dataset_ids=("tasks",),
                    ),
                ),
            )
            try:
                catalog = WorkspaceCatalog(store, config)
                catalog.reconcile()
                first = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertEqual(first["score"], 0)
                self.assertEqual(first["display_alias"], "org/task")
                self.assertEqual(first["display_tags"], ["web-agent", "web-search"])
                self.assertEqual(first["model_provider"], "provider")
                self.assertEqual(
                    catalog.query(CatalogQuery(tasks=("org/task",))).total, 1
                )
                self.assertEqual(
                    catalog.query(CatalogQuery(jobs=("configured-job",))).total, 1
                )
                self.assertEqual(
                    catalog.query(CatalogQuery(providers=("provider",))).total, 1
                )
                self.assertEqual(
                    first["task_name"],
                    catalog.query(CatalogQuery(sort="task"))
                    .items[0]
                    .to_dict()["task_name"],
                )
                facets = catalog.query(CatalogQuery()).facets
                self.assertEqual(facets["tasks"][0]["value"], "org/task")
                self.assertEqual(facets["jobs"][0]["value"], "configured-job")
                self.assertEqual(facets["providers"][0]["value"], "provider")
                self.assertEqual(
                    catalog.query(CatalogQuery(search="web-search")).total, 1
                )
                detail = catalog.load_detail(first["source_key"]).report
                meta = detail["trajectory_meta"][0]
                self.assertEqual(meta["data_ref"]["result_id"], "result-id")
                self.assertEqual(
                    meta["data_ref"]["task_digest_source"], "config.digest"
                )
                self.assertEqual(meta["evaluation"]["rewards"], {"reward": 0})
                self.assertEqual(
                    meta["task_metadata"]["description"], "Live description"
                )
                self.assertTrue(
                    {"environment", "kwargs", "command"}.isdisjoint(meta["data_ref"])
                )

                json_export = build_serve_export(
                    catalog,
                    store,
                    config,
                    kind="json",
                    source_keys=[first["source_key"]],
                )
                exported_report = json.loads(json_export.content)
                exported_meta = exported_report["trajectory_meta"][0]
                self.assertEqual(exported_meta["task_name"], "org/task")
                self.assertEqual(exported_meta["display_alias"], "org/task")
                self.assertEqual(
                    exported_meta["display_tags"], ["web-agent", "web-search"]
                )
                frames = InspectFrames.from_report(exported_report, preview_chars=100)
                source = frames.sources.iloc[0].to_dict()
                self.assertEqual(source["job_name"], "configured-job")
                self.assertEqual(source["rewards"], {"reward": 0})
                self.assertEqual(source["harbor_provenance"]["result_id"], "result-id")

                table_export = build_serve_export(
                    catalog,
                    store,
                    config,
                    kind="xlsx",
                    query=CatalogQuery(),
                )
                with zipfile.ZipFile(io.BytesIO(table_export.content)) as archive:
                    workbook_xml = "\n".join(
                        archive.read(name).decode("utf-8")
                        for name in archive.namelist()
                        if name.endswith(".xml")
                    )
                for heading in (
                    "Task Keywords",
                    "Task / Alias",
                    "Reward Dimensions",
                    "Harbor Provenance",
                    "Live Task Metadata",
                ):
                    self.assertIn(heading, workbook_xml)
                summaries = catalog.summarize_saved_views(
                    [
                        ("Task", CatalogQuery(), "task"),
                        ("Job", CatalogQuery(), "job"),
                        ("Provider", CatalogQuery(), "provider"),
                    ]
                )["views"]
                self.assertEqual(summaries[0]["groups"][0]["label"], "org/task")
                self.assertEqual(summaries[1]["groups"][0]["label"], "configured-job")
                self.assertEqual(summaries[2]["groups"][0]["label"], "provider")
                reward_metric = next(
                    metric
                    for metric in summaries[0]["groups"][0]["metrics"]
                    if metric["key"] == "score"
                )
                self.assertEqual(reward_metric["count"], 1)
                self.assertEqual(reward_metric["mean"], 0)
                first_revision = first["artifact_revision"]

                store.set_source_alias_row(first, "Custom alias")
                store.set_source_tags_row(first, ["WEB-AGENT", "custom"])
                catalog.reconcile()
                customized = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertEqual(customized["source_alias"], "Custom alias")
                self.assertEqual(customized["display_alias"], "Custom alias")
                self.assertEqual(
                    customized["display_tags"],
                    ["web-agent", "web-search", "custom"],
                )
                store.set_source_alias_row(customized, None)
                store.set_source_tags_row(customized, [])
                catalog.reconcile()
                restored = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertEqual(restored["display_alias"], "org/task")
                self.assertEqual(restored["display_tags"], ["web-agent", "web-search"])

                write_json(
                    trial.parent / "config.json",
                    {
                        "job_name": "renamed-job",
                        "jobs_dir": str(jobs),
                        "agents": ["agent"],
                        "tasks": ["task"],
                    },
                )
                (task / "task.toml").write_text(
                    '[task]\nname = "org/task"\nkeywords = ["changed"]\n',
                    encoding="utf-8",
                )
                catalog.reconcile()
                second = catalog.query(CatalogQuery()).items[0].to_dict()
                self.assertNotEqual(second["artifact_revision"], first_revision)
                self.assertEqual(second["job_name"], "renamed-job")
                self.assertEqual(second["display_tags"], ["changed"])
            finally:
                store.close()

    def test_mount_reuses_task_index_and_selected_digest_across_trials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs = root / "jobs"
            task = root / "dataset" / "task"
            write_task(task, "org/task")
            for name in ("trial-a", "trial-b"):
                write_evidence_trial(
                    jobs / "job" / name,
                    config_task={"name": "task", "source": "org"},
                )
            workspace = root / "workspace"
            store = open_workspace_state(str(workspace))
            config = ToolConfig(
                workspace_root=str(workspace),
                harbor_datasets=(HarborDataset(id="tasks", path=str(task.parent)),),
                harbor_mounts=(
                    HarborMount(
                        id="jobs",
                        path=str(jobs),
                        dataset_ids=("tasks",),
                    ),
                ),
            )
            try:
                with (
                    patch.object(
                        harbor_evidence,
                        "_task_candidates_once",
                        wraps=harbor_evidence._task_candidates_once,
                    ) as candidates_once,
                    patch.object(
                        harbor_evidence,
                        "_task_content_digest",
                        wraps=harbor_evidence._task_content_digest,
                    ) as content_digest,
                ):
                    candidates = WorkspaceSources(store, config).discover()

                self.assertEqual(len(candidates), 2)
                self.assertEqual(candidates_once.call_count, 1)
                self.assertEqual(content_digest.call_count, 1)
            finally:
                store.close()

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_task_content_symlink_is_rejected_without_hiding_the_trial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task = root / "dataset" / "task"
            write_task(task, "org/task")
            target = root / "outside.txt"
            target.write_text("secret", encoding="utf-8")
            try:
                (task / "environment" / "linked.txt").symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            trial = root / "jobs" / "job" / "trial"
            write_evidence_trial(
                trial,
                config_task={"name": "task", "source": "org"},
            )
            evidence = self.read(trial, (task.parent,))
            self.assertEqual(evidence.task_metadata["status"], "not_configured")


if __name__ == "__main__":
    unittest.main()
