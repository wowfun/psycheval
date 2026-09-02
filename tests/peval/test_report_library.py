from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from psycheval.config import HarborMount, ToolConfig
from psycheval.evaluation_reports import evaluation_report_ref
from psycheval.report_library import ReportNotFound
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import open_workspace_state
from tests.peval.cli_inputs_support import write_trial_cell_artifacts
from tests.peval.serve_state_support import peval_workspace
from tests.peval.test_harbor_trials import (
    atif_trajectory,
    completed_result,
    write_trial,
)


class ReportLibraryTests(unittest.TestCase):
    def test_canonical_report_ref_is_a_content_independent_source_hash(self) -> None:
        source_ref = "runs/default/agent/session/trial"
        expected = "analysis:" + hashlib.sha256(source_ref.encode("utf-8")).hexdigest()
        self.assertEqual(evaluation_report_ref(source_ref), expected)

    def test_local_catalog_uses_stable_ref_and_reads_current_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            source_ref = "runs/default/agent/session/trial"
            cell = root / source_ref
            write_trial_cell_artifacts(
                cell,
                session_id="session",
                trial_key="trial",
            )
            report_path = cell / "analysis.md"
            report_path.write_text("# First\n", encoding="utf-8")
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, ToolConfig(workspace_root=str(root)))
            try:
                page = runtime.evaluation_report_catalog()
                self.assertEqual(page["total"], 1)
                item = page["items"][0]
                expected_ref = evaluation_report_ref(source_ref)
                self.assertEqual(item["report_ref"], expected_ref)
                self.assertEqual(item["filename"], "analysis.md")
                self.assertEqual(item["format"], "markdown")
                self.assertEqual(item["source_keys"], [item["primary_source_key"]])
                self.assertNotIn("source_ref", item)
                self.assertNotIn("revision", item)
                self.assertEqual(
                    runtime.evaluation_report_catalog(
                        search=item["primary_source_key"]
                    )["total"],
                    1,
                )
                self.assertEqual(
                    runtime.evaluation_report_catalog(search="does-not-match")["total"],
                    0,
                )

                first = runtime.report_library.read(expected_ref)
                self.assertEqual(first.content, b"# First\n")
                report_path.write_text("# Replaced\n", encoding="utf-8")
                second = runtime.report_library.read(expected_ref)
                self.assertEqual(second.content, b"# Replaced\n")
                self.assertEqual(second.report_ref, first.report_ref)
            finally:
                runtime.close()
                store.close()

    def test_projection_excludes_json_only_and_unsafe_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            cells: dict[str, Path] = {}
            for name in ("valid", "json", "blank", "binary", "large", "linked"):
                cell = root / f"runs/default/agent/session/{name}"
                write_trial_cell_artifacts(
                    cell,
                    session_id="session",
                    trial_key=name,
                )
                cells[name] = cell
            (cells["valid"] / "analysis.md").write_text("okay", encoding="utf-8")
            (cells["json"] / "analysis.json").write_text("{}", encoding="utf-8")
            (cells["blank"] / "analysis.md").write_text(" \n", encoding="utf-8")
            (cells["binary"] / "analysis.md").write_bytes(b"\xff")
            (cells["large"] / "analysis.md").write_text("large", encoding="utf-8")
            outside = root / "outside.md"
            outside.write_text("linked", encoding="utf-8")
            try:
                (cells["linked"] / "analysis.md").symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")

            store = open_workspace_state(str(root))
            try:
                with patch(
                    "psycheval.state.workspace_sources.HARBOR_ANALYSIS_MAX_BYTES",
                    4,
                ):
                    runtime = ServeRuntime(
                        store,
                        ToolConfig(workspace_root=str(root)),
                    )
                try:
                    page = runtime.evaluation_report_catalog()
                    self.assertEqual(page["total"], 1)
                    self.assertEqual(
                        page["items"][0]["report_ref"],
                        evaluation_report_ref("runs/default/agent/session/valid"),
                    )
                finally:
                    runtime.close()
            finally:
                store.close()

    def test_harbor_trial_is_cataloged_by_parent_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            write_trial(trial)
            (trial / "analysis.md").write_text("# Harbor report\n", encoding="utf-8")
            root = peval_workspace(base / "workspace")
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(
                store,
                ToolConfig(
                    workspace_root=str(root),
                    harbor_mounts=(HarborMount(id="jobs", path=str(jobs)),),
                ),
            )
            try:
                page = runtime.evaluation_report_catalog()
                self.assertEqual(page["total"], 1)
                item = page["items"][0]
                parent_ref = "harbor/jobs/job-a/trial-a"
                self.assertEqual(item["report_ref"], evaluation_report_ref(parent_ref))
                self.assertEqual(item["source_keys"], [item["primary_source_key"]])
                report = runtime.report_library.read(item["report_ref"])
                self.assertEqual(report.content, b"# Harbor report\n")
            finally:
                runtime.close()
                store.close()

    def test_multistep_phases_share_one_parent_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            jobs = base / "jobs"
            trial = jobs / "job-a" / "trial-a"
            write_trial(trial)
            (trial / "agent/trajectory.json").unlink()
            for step in ("first", "second"):
                write_trial(
                    trial / "steps" / step,
                    trajectory=atif_trajectory(step),
                )
            result = completed_result()
            result["step_results"] = [
                {"step_name": "first"},
                {"step_name": "second"},
            ]
            (trial / "result.json").write_text(json.dumps(result), encoding="utf-8")
            (trial / "steps/first/agent/trajectory.json").write_text(
                "{",
                encoding="utf-8",
            )
            (trial / "analysis.md").write_text("# Parent\n", encoding="utf-8")
            root = peval_workspace(base / "workspace")
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(
                store,
                ToolConfig(
                    workspace_root=str(root),
                    harbor_mounts=(HarborMount(id="jobs", path=str(jobs)),),
                ),
            )
            try:
                page = runtime.evaluation_report_catalog()
                self.assertEqual(page["total"], 1)
                item = page["items"][0]
                parent_ref = "harbor/jobs/job-a/trial-a"
                self.assertEqual(item["report_ref"], evaluation_report_ref(parent_ref))
                self.assertEqual(len(item["source_keys"]), 2)
                self.assertIn(item["primary_source_key"], item["source_keys"])
                self.assertTrue(
                    runtime.catalog.row_for_key(item["primary_source_key"])["readable"]
                )
                report = runtime.report_library.read(item["report_ref"])
                self.assertEqual(report.content, b"# Parent\n")
            finally:
                runtime.close()
                store.close()

    def test_package_adapter_uses_prefixed_ref_and_tracks_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            cell = root / "runs/default/agent/session/trial"
            write_trial_cell_artifacts(cell, session_id="session", trial_key="trial")
            store = open_workspace_state(str(root))
            runtime = ServeRuntime(store, ToolConfig(workspace_root=str(root)))
            try:
                source_key = runtime.catalog.binding_rows()[0]["source_key"]
                imported = root / "imported.html"
                imported.write_text("<h1>Imported</h1>", encoding="utf-8")
                report_id = runtime.workspace_reports.import_file(
                    imported,
                    [source_key],
                )
                item = runtime.workspace_report_catalog()[0]
                self.assertEqual(item["report_ref"], f"package:{report_id}")
                report = runtime.report_library.read(item["report_ref"])
                self.assertEqual(report.format, "html")
                self.assertEqual(report.source_keys, (source_key,))
                runtime.workspace_reports.delete(report_id)
                with self.assertRaises(ReportNotFound):
                    runtime.report_library.read(item["report_ref"])
            finally:
                runtime.close()
                store.close()


if __name__ == "__main__":
    unittest.main()
