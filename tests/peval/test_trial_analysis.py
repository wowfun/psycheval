from __future__ import annotations

import json
import os
import stat
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from psycheval import trial_analysis
from psycheval.state import CatalogQuery, WorkspaceCatalog
from psycheval.trial_analysis import TrialAnalysisService, _skill_files
from tests.peval.test_cli_harbor_trials import run_cli
from tests.peval.test_harbor_evidence import write_task
from tests.peval.test_harbor_trials import (
    atif_trajectory,
    completed_result,
    write_trial,
)


class TrialAnalysisTests(unittest.TestCase):
    def fixture(self, root: Path, *, multi_step: bool = False) -> tuple[Path, Path]:
        jobs = root / "jobs"
        trial = jobs / "job-a" / "trial-a"
        task = root / "tasks" / "web-search"
        write_task(task, "org/web-search")
        skill = task / "environment" / "skills" / "skill-a"
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: skill-a\ndescription: Evaluate search.\n---\n\n# Skill A\n",
            encoding="utf-8",
        )
        (skill / "references" / "guide.md").write_text(
            "Use grounded sources.\n", encoding="utf-8"
        )
        result = completed_result()
        if multi_step:
            write_trial(trial)
            (trial / "agent" / "trajectory.json").unlink()
            for name in ("first", "second"):
                write_trial(
                    trial / "steps" / name,
                    trajectory=atif_trajectory(name),
                )
            result["step_results"] = [
                {"step_name": "first"},
                {"step_name": "second"},
            ]
            (trial / "result.json").write_text(json.dumps(result), encoding="utf-8")
        else:
            write_trial(trial, result=result)
        config = json.loads((trial / "config.json").read_text(encoding="utf-8"))
        config["task"] = {
            "name": "web-search",
            "path": str(task),
            "digest": "sha256:recorded",
        }
        (trial / "config.json").write_text(json.dumps(config), encoding="utf-8")

        workspace = root / "workspace"
        workspace.mkdir()
        (workspace / "peval.toml").write_text(
            "[[harbor.datasets]]\n"
            'id = "tasks"\n'
            f"path = {json.dumps(str(task.parent))}\n\n"
            "[[harbor.mounts]]\n"
            'id = "jobs"\n'
            f"path = {json.dumps(str(jobs))}\n"
            'dataset_ids = ["tasks"]\n',
            encoding="utf-8",
        )
        return workspace, trial

    def test_task_skill_snapshot_and_revision_bound_publish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, trial = self.fixture(root)
            draft = root / "draft.md"
            draft.write_text("## Executive conclusion\n\nGrounded.\n", encoding="utf-8")
            service = TrialAnalysisService(workspace)
            try:
                snapshot = service.task_skill("harbor/jobs/job-a/trial-a", "skill-a")
                supporting = service.task_skill(
                    "harbor/jobs/job-a/trial-a",
                    "skill-a",
                    relative_file="references/guide.md",
                )
                self.assertEqual(
                    snapshot.target.phase_refs, (snapshot.target.trial_ref,)
                )
                self.assertEqual(snapshot.selected_file, "SKILL.md")
                self.assertEqual(supporting.content, "Use grounded sources.\n")
                self.assertEqual(snapshot.task["status"], "digest_mismatch")
                self.assertFalse(snapshot.analysis.present)

                receipt = service.publish(
                    source_ref=snapshot.target.trial_ref,
                    skill_name="skill-a",
                    expected_evidence_revision=snapshot.target.evidence_revision,
                    expected_skill_revision=snapshot.revision,
                    draft_path=draft,
                )

                report_path = trial / "analysis.md"
                report = report_path.read_text(encoding="utf-8")
                self.assertIn("<!-- peval:trial-analysis:v1 -->", report)
                self.assertIn("[!WARNING]", report)
                self.assertIn("current live Task", report)
                self.assertIn("Grounded.", report)
                self.assertEqual(receipt["report_path"], "analysis.md")
                self.assertFalse(receipt["replaced"])
                self.assertTrue(receipt["catalog_reconciled"])
                self.assertIsInstance(receipt["catalog_generation"], int)
                if os.name != "nt":
                    self.assertEqual(stat.S_IMODE(report_path.stat().st_mode), 0o644)

                with self.assertRaisesRegex(ValueError, "already exists"):
                    service.publish(
                        source_ref=snapshot.target.trial_ref,
                        skill_name="skill-a",
                        expected_evidence_revision=snapshot.target.evidence_revision,
                        expected_skill_revision=snapshot.revision,
                        draft_path=draft,
                    )
                current = service.task_skill(snapshot.target.trial_ref, "skill-a")
                if os.name != "nt":
                    report_path.chmod(0o640)
                replaced = service.publish(
                    source_ref=snapshot.target.trial_ref,
                    skill_name="skill-a",
                    expected_evidence_revision=current.target.evidence_revision,
                    expected_skill_revision=current.revision,
                    draft_path=draft,
                    replace_revision=current.analysis.revision,
                )
                self.assertTrue(replaced["replaced"])
                if os.name != "nt":
                    self.assertEqual(stat.S_IMODE(report_path.stat().st_mode), 0o640)
            finally:
                service.close()

    def test_publish_escapes_multiline_provenance_as_inline_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, trial = self.fixture(root)
            config_path = trial / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["task"]["digest"] = "sha256:recorded\n- Injected field: true"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            draft = root / "draft.md"
            draft.write_text("# Reviewed\n", encoding="utf-8")
            service = TrialAnalysisService(workspace)
            try:
                snapshot = service.task_skill("harbor/jobs/job-a/trial-a", "skill-a")

                service.publish(
                    source_ref=snapshot.target.trial_ref,
                    skill_name="skill-a",
                    expected_evidence_revision=snapshot.target.evidence_revision,
                    expected_skill_revision=snapshot.revision,
                    draft_path=draft,
                )

                report = (trial / "analysis.md").read_text(encoding="utf-8")
                self.assertNotIn("\n- Injected field", report)
                self.assertIn(
                    "sha256:recorded - Injected field: true",
                    report,
                )
            finally:
                service.close()

    def test_publish_is_serialized_across_workspaces_for_one_trial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace_a, trial = self.fixture(root)
            workspace_b = root / "workspace-b"
            workspace_b.mkdir()
            (workspace_b / "peval.toml").write_text(
                (workspace_a / "peval.toml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            drafts = [root / "draft-a.md", root / "draft-b.md"]
            for index, draft in enumerate(drafts):
                draft.write_text(f"# Draft {index}\n", encoding="utf-8")

            service = TrialAnalysisService(workspace_a)
            try:
                snapshot = service.task_skill("harbor/jobs/job-a/trial-a", "skill-a")
            finally:
                service.close()

            rendezvous = threading.Barrier(2)
            replace_text = trial_analysis._atomic_replace_text

            def synchronized_replace(
                trial_root: Path,
                report_path: Path,
                content: str,
            ) -> None:
                try:
                    rendezvous.wait(timeout=1)
                except threading.BrokenBarrierError:
                    pass
                replace_text(trial_root, report_path, content)

            def publish(workspace: Path, draft: Path) -> tuple[str, str]:
                current = TrialAnalysisService(workspace)
                try:
                    receipt = current.publish(
                        source_ref=snapshot.target.trial_ref,
                        skill_name="skill-a",
                        expected_evidence_revision=snapshot.target.evidence_revision,
                        expected_skill_revision=snapshot.revision,
                        draft_path=draft,
                    )
                    return "published", receipt["analysis_revision"]
                except ValueError as exc:
                    return "rejected", str(exc)
                finally:
                    current.close()

            with patch.object(
                trial_analysis,
                "_atomic_replace_text",
                side_effect=synchronized_replace,
            ):
                with ThreadPoolExecutor(max_workers=2) as executor:
                    results = list(
                        executor.map(
                            lambda values: publish(*values),
                            zip((workspace_a, workspace_b), drafts, strict=True),
                        )
                    )

            self.assertEqual(
                [status for status, _detail in results].count("published"),
                1,
            )
            self.assertEqual(
                [status for status, _detail in results].count("rejected"),
                1,
            )
            self.assertRegex(
                next(detail for status, detail in results if status == "rejected"),
                "already exists|changed",
            )
            self.assertTrue((trial / "analysis.md").is_file())
            self.assertTrue((trial / trial_analysis.TRIAL_ANALYSIS_LOCK_FILE).is_file())
            service = TrialAnalysisService(workspace_a)
            try:
                current = service.task_skill(snapshot.target.trial_ref, "skill-a")
                self.assertEqual(
                    current.target.evidence_revision,
                    snapshot.target.evidence_revision,
                )
            finally:
                service.close()

    @unittest.skipIf(os.name == "nt", "POSIX directory permissions required")
    def test_unreadable_task_skill_directory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "skill-a"
            hidden = skill / "hidden"
            hidden.mkdir(parents=True)
            (skill / "SKILL.md").write_text("skill\n", encoding="utf-8")
            (hidden / "required.md").write_text("required\n", encoding="utf-8")
            hidden.chmod(0)
            try:
                with self.assertRaisesRegex(ValueError, "Task skill is unreadable"):
                    _skill_files(skill)
            finally:
                hidden.chmod(0o700)

    def test_generated_python_cache_does_not_change_skill_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, _trial = self.fixture(root)
            service = TrialAnalysisService(workspace)
            try:
                before = service.task_skill("harbor/jobs/job-a/trial-a", "skill-a")
                cache = root / "tasks/web-search/environment/skills/skill-a/__pycache__"
                cache.mkdir()
                (cache / "generated.pyc").write_bytes(b"generated cache")

                after = service.task_skill("harbor/jobs/job-a/trial-a", "skill-a")

                self.assertEqual(after.revision, before.revision)
                self.assertNotIn("__pycache__/generated.pyc", after.files)
            finally:
                service.close()

    def test_task_skill_file_count_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "skill-a"
            skill.mkdir()
            for index in range(1_001):
                (skill / f"file-{index:04}.txt").write_text("", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "exceeds 1000 files"):
                _skill_files(skill)

    def test_public_cli_resolves_source_ref_and_publishes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, trial = self.fixture(root)
            view_result, view_stdout, view_stderr = run_cli(
                [
                    "view",
                    "tr",
                    "-r",
                    str(workspace),
                    "--source-ref",
                    "harbor/jobs/job-a/trial-a",
                ]
            )
            skill_result, skill_stdout, skill_stderr = run_cli(
                [
                    "view",
                    "task-skill",
                    "-r",
                    str(workspace),
                    "--source-ref",
                    "harbor/jobs/job-a/trial-a",
                    "--name",
                    "skill-a",
                    "--json",
                ]
            )
            self.assertEqual((view_result, view_stderr), (0, ""))
            self.assertEqual(len(json.loads(view_stdout)["sources"]), 1)
            self.assertEqual((skill_result, skill_stderr), (0, ""))
            snapshot = json.loads(skill_stdout)
            draft = root / "draft.md"
            draft.write_text("# Reviewed CLI draft\n", encoding="utf-8")

            result, stdout, stderr = run_cli(
                [
                    "publish",
                    "trial-analysis",
                    "-r",
                    str(workspace),
                    "--source-ref",
                    snapshot["trial_ref"],
                    "--skill",
                    "skill-a",
                    "--expected-evidence-revision",
                    snapshot["evidence_revision"],
                    "--expected-skill-revision",
                    snapshot["skill"]["revision"],
                    "-p",
                    str(draft),
                    "--json",
                ]
            )

            self.assertEqual((result, stderr), (0, ""))
            receipt = json.loads(stdout)
            self.assertEqual(receipt["trial_ref"], snapshot["trial_ref"])
            self.assertTrue((trial / "analysis.md").is_file())

    def test_inspect_source_ref_keeps_result_only_trial_as_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, trial = self.fixture(root)
            (trial / "agent" / "trajectory.json").unlink()

            result, stdout, stderr = run_cli(
                [
                    "view",
                    "tr",
                    "-r",
                    str(workspace),
                    "--source-ref",
                    "harbor/jobs/job-a/trial-a",
                ]
            )

            self.assertEqual((result, stderr), (0, ""))
            source = json.loads(stdout)["sources"][0]
            self.assertFalse(source["harbor"]["trajectory_available"])
            self.assertIn("trajectory", source["harbor"]["diagnostic"].lower())

    def test_stale_revisions_active_trial_and_unsafe_skill_file_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, trial = self.fixture(root)
            draft = root / "draft.md"
            draft.write_text("# Draft\n", encoding="utf-8")
            service = TrialAnalysisService(workspace)
            try:
                snapshot = service.task_skill("harbor/jobs/job-a/trial-a", "skill-a")
                with self.assertRaisesRegex(ValueError, "evidence changed"):
                    service.publish(
                        source_ref=snapshot.target.trial_ref,
                        skill_name="skill-a",
                        expected_evidence_revision="stale",
                        expected_skill_revision=snapshot.revision,
                        draft_path=draft,
                    )
                with self.assertRaisesRegex(ValueError, "Task skill changed"):
                    service.publish(
                        source_ref=snapshot.target.trial_ref,
                        skill_name="skill-a",
                        expected_evidence_revision=snapshot.target.evidence_revision,
                        expected_skill_revision="stale",
                        draft_path=draft,
                    )

                result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
                result["finished_at"] = None
                (trial / "result.json").write_text(json.dumps(result), encoding="utf-8")
                active = service.task_skill(snapshot.target.trial_ref, "skill-a")
                with self.assertRaisesRegex(ValueError, "only be published after"):
                    service.publish(
                        source_ref=active.target.trial_ref,
                        skill_name="skill-a",
                        expected_evidence_revision=active.target.evidence_revision,
                        expected_skill_revision=active.revision,
                        draft_path=draft,
                    )
                with self.assertRaisesRegex(ValueError, "invalid Task skill relative"):
                    service.task_skill(
                        snapshot.target.trial_ref,
                        "skill-a",
                        relative_file="../secret",
                    )
            finally:
                service.close()

    def test_multistep_parent_and_phase_share_one_trial_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, trial = self.fixture(root, multi_step=True)
            draft = root / "draft.md"
            draft.write_text("# MultiStep review\n", encoding="utf-8")
            service = TrialAnalysisService(workspace)
            try:
                parent = service.task_skill("harbor/jobs/job-a/trial-a", "skill-a")
                phase = service.task_skill(
                    "harbor/jobs/job-a/trial-a/steps/second", "skill-a"
                )
                self.assertEqual(parent.target.trial_ref, phase.target.trial_ref)
                self.assertEqual(len(parent.target.phase_refs), 2)
                self.assertEqual(
                    parent.target.evidence_revision,
                    phase.target.evidence_revision,
                )
                service.publish(
                    source_ref=phase.target.requested_ref,
                    skill_name="skill-a",
                    expected_evidence_revision=phase.target.evidence_revision,
                    expected_skill_revision=phase.revision,
                    draft_path=draft,
                )
                self.assertTrue((trial / "analysis.md").is_file())
                self.assertFalse((trial / "steps" / "second" / "analysis.md").exists())
                catalog = WorkspaceCatalog(service.store, service.config)
                rows = catalog.query(
                    CatalogQuery(state="all", include_unreadable=True)
                ).items
                self.assertEqual(
                    [row.payload["analysis_count"] for row in rows], [1, 1]
                )
            finally:
                service.close()
