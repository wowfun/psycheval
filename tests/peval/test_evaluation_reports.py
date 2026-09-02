from __future__ import annotations

import json
import multiprocessing
import os
import queue
import stat
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from unittest.mock import patch

from psycheval import evaluation_reports
from psycheval.evaluation_reports import (
    EVALUATION_REPORT_LOCK_FILE,
    EvaluationReportDurabilityError,
    EvaluationReportReconcileError,
    EvaluationReports,
    evaluation_report_ref,
)
from psycheval.state import CatalogQuery, WorkspaceCatalog
from tests.peval.cli_inputs_support import (
    write_peval_workspace,
    write_trial_cell_artifacts,
)
from tests.peval.test_cli_harbor_trials import run_cli
from tests.peval.test_harbor_evidence import write_task
from tests.peval.test_harbor_trials import (
    atif_trajectory,
    completed_result,
    write_trial,
)


def _evaluation_report_process_worker(
    operation: str,
    workspace: str,
    source_ref: str,
    draft_path: str,
    start: object,
    results: object,
) -> None:
    try:
        start.wait(timeout=20)
        if operation == "import":
            from psycheval.analysis import import_analysis_artifacts

            result = import_analysis_artifacts(
                workspace_root=workspace,
                source_ref=source_ref,
                input_paths=[draft_path],
            )
            payload = result.to_jsonable()
        else:
            reports = EvaluationReports(workspace)
            try:
                payload = reports.publish(
                    source_ref=source_ref,
                    draft_path=draft_path,
                ).to_jsonable()
            finally:
                reports.close()
        results.put((operation, "ok", payload))
    except BaseException as exc:  # noqa: BLE001 - subprocess test boundary.
        results.put((operation, "error", repr(exc)))


class EvaluationReportsTests(unittest.TestCase):
    def harbor_fixture(
        self,
        root: Path,
        *,
        multi_step: bool = False,
        finished: bool = True,
    ) -> tuple[Path, Path]:
        jobs = root / "jobs"
        trial = jobs / "job-a" / "trial-a"
        task = root / "tasks" / "web-search"
        write_task(task, "org/web-search")
        result = completed_result()
        if not finished:
            result["finished_at"] = None
        if multi_step:
            write_trial(trial)
            (trial / "agent" / "trajectory.json").unlink()
            for name in ("first", "second"):
                write_trial(trial / "steps" / name, trajectory=atif_trajectory(name))
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

    def local_fixture(self, root: Path) -> tuple[Path, str, Path]:
        workspace = root / "workspace"
        write_peval_workspace(workspace)
        source_ref = "runs/default/agent-a/session-a/trial-a"
        cell = workspace / source_ref
        write_trial_cell_artifacts(
            cell,
            session_id="session-a",
            trial_key="trial-a",
            agent_id="agent-a",
        )
        return workspace, source_ref, cell

    def test_harbor_publish_is_exact_upsert_with_stable_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, trial = self.harbor_fixture(root)
            first = "  # Reviewed\r\n\r\nFirst body.  "
            second = "# Revised\n\nSecond body.\n"
            first_path = root / "first.md"
            second_path = root / "second.md"
            first_path.write_bytes(first.encode("utf-8"))
            second_path.write_text(second, encoding="utf-8")
            reports = EvaluationReports(workspace)
            try:
                created = reports.publish(
                    source_ref="harbor/jobs/job-a/trial-a",
                    draft_path=first_path,
                )
                report_path = trial / "analysis.md"
                self.assertEqual(report_path.read_bytes(), first.encode("utf-8"))
                self.assertEqual(
                    created.to_jsonable(),
                    {
                        "source_ref": "harbor/jobs/job-a/trial-a",
                        "report_ref": evaluation_report_ref(
                            "harbor/jobs/job-a/trial-a"
                        ),
                        "report_path": "analysis.md",
                        "replaced": False,
                        "catalog_reconciled": True,
                        "catalog_generation": created.catalog_generation,
                    },
                )
                self.assertIsInstance(created.catalog_generation, int)
                self.assertEqual(reports.read(created.source_ref).content, first)

                if os.name != "nt":
                    report_path.chmod(0o640)
                replaced = reports.publish(
                    source_ref="harbor/jobs/job-a/trial-a",
                    draft_path=second_path,
                )
                self.assertTrue(replaced.replaced)
                self.assertEqual(report_path.read_text(encoding="utf-8"), second)
                self.assertEqual(replaced.report_ref, created.report_ref)
                if os.name != "nt":
                    self.assertEqual(stat.S_IMODE(report_path.stat().st_mode), 0o640)
            finally:
                reports.close()

    def test_local_publish_and_generic_view_source_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, source_ref, cell = self.local_fixture(root)
            draft = root / "draft.md"
            draft.write_text("# Local evaluation\n", encoding="utf-8")

            result, stdout, stderr = run_cli(
                [
                    "publish",
                    "evaluation-report",
                    "-r",
                    str(workspace),
                    "--source-ref",
                    source_ref,
                    "-p",
                    str(draft),
                    "--json",
                ]
            )
            self.assertEqual((result, stderr), (0, ""))
            receipt = json.loads(stdout)
            self.assertEqual(receipt["source_ref"], source_ref)
            self.assertEqual(receipt["report_ref"], evaluation_report_ref(source_ref))
            self.assertEqual((cell / "analysis.md").read_text(), "# Local evaluation\n")

            result, stdout, stderr = run_cli(
                ["view", "tr", "-r", str(workspace), "--source-ref", source_ref]
            )
            self.assertEqual((result, stderr), (0, ""))
            payload = json.loads(stdout)
            self.assertEqual(len(payload["sources"]), 1)

            raw_output = root / "raw-report.json"
            result, _, stderr = run_cli(
                [
                    "view",
                    "tr",
                    "-m",
                    "raw",
                    "-r",
                    str(workspace),
                    "--source-ref",
                    source_ref,
                    "-o",
                    str(raw_output),
                ]
            )
            self.assertEqual((result, stderr), (0, ""))
            self.assertEqual(
                json.loads(raw_output.read_text())["annotations"]["analysis"][0][
                    "trial_key"
                ],
                "trial-a",
            )

    def test_harbor_parent_and_phase_share_one_multistep_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, trial = self.harbor_fixture(root, multi_step=True)
            draft = root / "draft.md"
            draft.write_text("# MultiStep evaluation\n", encoding="utf-8")
            reports = EvaluationReports(workspace)
            try:
                parent = reports.resolve("harbor/jobs/job-a/trial-a")
                phase = reports.resolve("harbor/jobs/job-a/trial-a/steps/second")
                self.assertEqual(parent.source_ref, phase.source_ref)
                self.assertEqual(len(parent.source_refs), 2)
                self.assertEqual(parent.source_keys, phase.source_keys)

                receipt = reports.publish(
                    source_ref=phase.requested_ref,
                    draft_path=draft,
                )
                self.assertEqual(receipt.source_ref, parent.source_ref)
                self.assertTrue((trial / "analysis.md").is_file())
                self.assertFalse((trial / "steps/second/analysis.md").exists())
                catalog = WorkspaceCatalog(reports.store, reports.config)
                rows = catalog.query(
                    CatalogQuery(state="all", include_unreadable=True)
                ).items
                self.assertEqual(
                    sorted(row.payload["analysis_count"] for row in rows),
                    [1, 1],
                )
            finally:
                reports.close()

    def test_concurrent_publications_both_succeed_without_mixed_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace_a, trial = self.harbor_fixture(root)
            workspace_b = root / "workspace-b"
            workspace_b.mkdir()
            (workspace_b / "peval.toml").write_text(
                (workspace_a / "peval.toml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            bodies = (
                "# A\n" + "a" * 16_000,
                "# B\n" + "b" * 16_000,
                "# C\n" + "c" * 16_000,
            )
            drafts = (
                root / "draft-a.md",
                root / "draft-b.md",
                root / "draft-c.md",
            )
            for path, body in zip(drafts, bodies, strict=True):
                path.write_text(body, encoding="utf-8")
            rendezvous = threading.Barrier(3)

            def publish(workspace: Path, draft: Path) -> dict[str, object]:
                reports = EvaluationReports(workspace)
                try:
                    rendezvous.wait(timeout=2)
                    return reports.publish(
                        source_ref="harbor/jobs/job-a/trial-a",
                        draft_path=draft,
                    ).to_jsonable()
                finally:
                    reports.close()

            with ThreadPoolExecutor(max_workers=3) as executor:
                receipts = list(
                    executor.map(
                        lambda args: publish(*args),
                        zip(
                            (workspace_a, workspace_a, workspace_b),
                            drafts,
                            strict=True,
                        ),
                    )
                )

            self.assertEqual(len(receipts), 3)
            self.assertTrue(all(item["catalog_reconciled"] for item in receipts))
            self.assertIn((trial / "analysis.md").read_text(), bodies)
            self.assertTrue((trial / EVALUATION_REPORT_LOCK_FILE).is_file())

    def test_cross_process_publishers_and_markdown_import_share_one_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, source_ref, cell = self.local_fixture(root)
            bodies = {
                "publish-a": "# Published A\n" + "a" * 64_000,
                "publish-b": "# Published B\n" + "b" * 64_000,
                "import": "# Imported\n" + "i" * 64_000,
            }
            paths: dict[str, Path] = {}
            for operation, body in bodies.items():
                path = root / f"{operation}.md"
                path.write_text(body, encoding="utf-8")
                paths[operation] = path

            context = multiprocessing.get_context("spawn")
            start = context.Event()
            results = context.Queue()
            processes = [
                context.Process(
                    target=_evaluation_report_process_worker,
                    args=(
                        "import" if operation == "import" else "publish",
                        str(workspace),
                        source_ref,
                        str(path),
                        start,
                        results,
                    ),
                )
                for operation, path in paths.items()
            ]
            try:
                for process in processes:
                    process.start()
                start.set()
                outcomes = [results.get(timeout=30) for _ in processes]
                for process in processes:
                    process.join(timeout=30)
                self.assertEqual(
                    sorted((operation, status) for operation, status, _ in outcomes),
                    [("import", "ok"), ("publish", "ok"), ("publish", "ok")],
                )
                self.assertTrue(all(process.exitcode == 0 for process in processes))
                self.assertIn((cell / "analysis.md").read_text(), bodies.values())
                self.assertTrue((cell / EVALUATION_REPORT_LOCK_FILE).is_file())
            except queue.Empty as exc:
                self.fail(f"evaluation report worker did not finish: {exc}")
            finally:
                for process in processes:
                    if process.is_alive():
                        process.terminate()
                    process.join(timeout=5)
                results.close()

    def test_reconcile_failure_reports_committed_publication_accurately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, source_ref, cell = self.local_fixture(root)
            draft = root / "draft.md"
            draft.write_text("# Committed before reconcile\n", encoding="utf-8")
            reports = EvaluationReports(workspace)
            try:
                with patch.object(
                    WorkspaceCatalog,
                    "_reconcile_locked",
                    side_effect=RuntimeError("reconcile exploded"),
                ):
                    with self.assertRaises(EvaluationReportReconcileError) as raised:
                        reports.publish(source_ref=source_ref, draft_path=draft)
                self.assertEqual(
                    (cell / "analysis.md").read_text(),
                    "# Committed before reconcile\n",
                )
                self.assertEqual(
                    raised.exception.receipt,
                    {
                        "source_ref": source_ref,
                        "report_ref": evaluation_report_ref(source_ref),
                        "report_path": "analysis.md",
                        "replaced": False,
                        "catalog_reconciled": False,
                        "catalog_generation": None,
                    },
                )
            finally:
                reports.close()

    def test_invalid_sources_drafts_and_report_targets_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, source_ref, cell = self.local_fixture(root)
            reports = EvaluationReports(workspace)
            blank = root / "blank.md"
            blank.write_text(" \n\t", encoding="utf-8")
            binary = root / "binary.md"
            binary.write_bytes(b"\xff")
            large = root / "large.md"
            large.write_text("x" * 9, encoding="utf-8")
            try:
                with self.assertRaisesRegex(ValueError, "draft not found"):
                    reports.publish(
                        source_ref=source_ref,
                        draft_path=root / "missing.md",
                    )
                with self.assertRaisesRegex(ValueError, "must not be empty"):
                    reports.publish(source_ref=source_ref, draft_path=blank)
                with self.assertRaisesRegex(ValueError, "must be UTF-8"):
                    reports.publish(source_ref=source_ref, draft_path=binary)
                with patch.object(evaluation_reports, "EVALUATION_REPORT_MAX_BYTES", 8):
                    with self.assertRaisesRegex(ValueError, "exceeds"):
                        reports.publish(source_ref=source_ref, draft_path=large)
                for invalid in (
                    "runs/default/agent-a/session-a/missing",
                    "../outside",
                    "/absolute/source",
                ):
                    with self.subTest(source_ref=invalid):
                        with self.assertRaises(ValueError):
                            reports.resolve(invalid)

                outside = root / "outside.md"
                outside.write_text("outside", encoding="utf-8")
                (cell / "analysis.md").symlink_to(outside)
                with self.assertRaisesRegex(ValueError, "symlink"):
                    reports.publish(source_ref=source_ref, draft_path=large)
                (cell / "analysis.md").unlink()
                (cell / "analysis.md").mkdir()
                with self.assertRaisesRegex(ValueError, "regular file"):
                    reports.publish(source_ref=source_ref, draft_path=large)
                (cell / "analysis.md").rmdir()
                lock_path = cell / EVALUATION_REPORT_LOCK_FILE
                lock_path.unlink()
                lock_path.symlink_to(outside)
                with self.assertRaisesRegex(ValueError, "lock.*symlink"):
                    reports.publish(source_ref=source_ref, draft_path=large)
            finally:
                reports.close()

    def test_read_excludes_unsafe_empty_and_oversized_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, source_ref, cell = self.local_fixture(root)
            report_path = cell / "analysis.md"
            reports = EvaluationReports(workspace)
            try:
                self.assertIsNone(reports.read(source_ref))
                report_path.write_text(" \n", encoding="utf-8")
                self.assertIsNone(reports.read(source_ref))
                report_path.write_bytes(b"\xff")
                self.assertIsNone(reports.read(source_ref))
                report_path.unlink()
                outside = root / "outside.md"
                outside.write_text("unsafe", encoding="utf-8")
                report_path.symlink_to(outside)
                self.assertIsNone(reports.read(source_ref))
                report_path.unlink()
                report_path.write_text("123456789", encoding="utf-8")
                with patch.object(evaluation_reports, "EVALUATION_REPORT_MAX_BYTES", 8):
                    self.assertIsNone(reports.read(source_ref))
            finally:
                reports.close()

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs require POSIX mkfifo")
    def test_fifo_draft_and_current_report_are_rejected_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, source_ref, cell = self.local_fixture(root)
            draft_fifo = root / "draft.md"
            os.mkfifo(draft_fifo)
            reports = EvaluationReports(workspace)
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        reports.publish,
                        source_ref=source_ref,
                        draft_path=draft_fifo,
                    )
                    try:
                        future.result(timeout=1)
                    except ValueError as exc:
                        self.assertIn("regular file", str(exc))
                    except FutureTimeoutError:
                        writer = os.open(
                            draft_fifo,
                            os.O_WRONLY | getattr(os, "O_NONBLOCK", 0),
                        )
                        os.close(writer)
                        with self.assertRaises(ValueError):
                            future.result(timeout=1)
                        self.fail("evaluation report draft FIFO blocked during open")

                report_fifo = cell / "analysis.md"
                os.mkfifo(report_fifo)
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(reports.read, source_ref)
                    try:
                        value = future.result(timeout=1)
                    except FutureTimeoutError:
                        writer = os.open(
                            report_fifo,
                            os.O_WRONLY | getattr(os, "O_NONBLOCK", 0),
                        )
                        os.close(writer)
                        future.result(timeout=1)
                        self.fail(
                            "canonical evaluation report FIFO blocked during open"
                        )
                self.assertIsNone(value)
            finally:
                reports.close()

    def test_publish_does_not_read_the_current_report_as_a_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, source_ref, cell = self.local_fixture(root)
            (cell / "analysis.md").write_text("old report", encoding="utf-8")
            draft = root / "draft.md"
            draft.write_text("new report", encoding="utf-8")
            reports = EvaluationReports(workspace)
            replaced = False
            original_replace = evaluation_reports._atomic_replace_text
            from psycheval.state import workspace_sources as source_module

            original_read = source_module._read_local_evaluation_report

            def tracked_replace(report_dir: Path, report_path: Path, body: str) -> None:
                nonlocal replaced
                original_replace(report_dir, report_path, body)
                replaced = True

            def reject_prewrite_read(candidate: object) -> str | None:
                if not replaced:
                    raise AssertionError("current report was read before replacement")
                return original_read(candidate)

            try:
                with (
                    patch.object(
                        evaluation_reports,
                        "_atomic_replace_text",
                        side_effect=tracked_replace,
                    ),
                    patch.object(
                        source_module,
                        "_read_local_evaluation_report",
                        side_effect=reject_prewrite_read,
                    ),
                ):
                    receipt = reports.publish(
                        source_ref=source_ref,
                        draft_path=draft,
                    )
                self.assertTrue(receipt.replaced)
                self.assertEqual((cell / "analysis.md").read_text(), "new report")
            finally:
                reports.close()

    def test_harbor_publish_does_not_read_the_current_report_as_a_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, trial = self.harbor_fixture(root)
            (trial / "analysis.md").write_text("old report", encoding="utf-8")
            draft = root / "draft.md"
            draft.write_text("new report", encoding="utf-8")
            reports = EvaluationReports(workspace)
            replaced = False
            original_replace = evaluation_reports._atomic_replace_text
            from psycheval.state import workspace_sources as source_module

            original_read = source_module._read_harbor_analysis_markdown

            def tracked_replace(report_dir: Path, report_path: Path, body: str) -> None:
                nonlocal replaced
                original_replace(report_dir, report_path, body)
                replaced = True

            def reject_prewrite_read(candidate: object) -> str | None:
                if not replaced:
                    raise AssertionError(
                        "current Harbor report was read before replacement"
                    )
                return original_read(candidate)

            try:
                with (
                    patch.object(
                        evaluation_reports,
                        "_atomic_replace_text",
                        side_effect=tracked_replace,
                    ),
                    patch.object(
                        source_module,
                        "_read_harbor_analysis_markdown",
                        side_effect=reject_prewrite_read,
                    ),
                ):
                    receipt = reports.publish(
                        "harbor/jobs/job-a/trial-a",
                        draft,
                    )
                self.assertTrue(receipt.replaced)
                self.assertEqual((trial / "analysis.md").read_text(), "new report")
            finally:
                reports.close()

    def test_failed_atomic_replace_preserves_previous_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, source_ref, cell = self.local_fixture(root)
            old = root / "old.md"
            new = root / "new.md"
            old.write_text("old complete report", encoding="utf-8")
            new.write_text("new complete report", encoding="utf-8")
            reports = EvaluationReports(workspace)
            try:
                reports.publish(source_ref=source_ref, draft_path=old)
                with patch.object(
                    Path,
                    "replace",
                    side_effect=PermissionError("replace denied"),
                ):
                    with self.assertRaisesRegex(PermissionError, "replace denied"):
                        reports.publish(source_ref=source_ref, draft_path=new)
                self.assertEqual(
                    (cell / "analysis.md").read_text(), "old complete report"
                )
                self.assertEqual(list(cell.glob(".analysis.md.*")), [])
            finally:
                reports.close()

    @unittest.skipIf(os.name == "nt", "directory fsync is POSIX-specific")
    def test_directory_fsync_failure_returns_a_committed_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, source_ref, cell = self.local_fixture(root)
            draft = root / "draft.md"
            draft.write_text("new visible report", encoding="utf-8")
            reports = EvaluationReports(workspace)
            real_fsync = os.fsync

            def fail_directory_fsync(descriptor: int) -> None:
                if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                    raise OSError("directory fsync failed")
                real_fsync(descriptor)

            try:
                with patch.object(os, "fsync", side_effect=fail_directory_fsync):
                    with self.assertRaises(EvaluationReportDurabilityError) as raised:
                        reports.publish(source_ref=source_ref, draft_path=draft)
                self.assertEqual(
                    (cell / "analysis.md").read_text(),
                    "new visible report",
                )
                self.assertEqual(
                    raised.exception.receipt,
                    {
                        "source_ref": source_ref,
                        "report_ref": evaluation_report_ref(source_ref),
                        "report_path": "analysis.md",
                        "replaced": False,
                        "catalog_reconciled": False,
                        "catalog_generation": None,
                    },
                )
            finally:
                reports.close()

    def test_unfinished_harbor_trial_is_not_publishable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, trial = self.harbor_fixture(root, finished=False)
            draft = root / "draft.md"
            draft.write_text("# Draft\n", encoding="utf-8")
            reports = EvaluationReports(workspace)
            try:
                with self.assertRaisesRegex(ValueError, "after the Harbor Trial"):
                    reports.publish(
                        source_ref="harbor/jobs/job-a/trial-a",
                        draft_path=draft,
                    )
                self.assertFalse((trial / "analysis.md").exists())
            finally:
                reports.close()

    def test_result_only_harbor_source_remains_viewable_as_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, trial = self.harbor_fixture(root)
            (trial / "agent/trajectory.json").unlink()

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


if __name__ == "__main__":
    unittest.main()
