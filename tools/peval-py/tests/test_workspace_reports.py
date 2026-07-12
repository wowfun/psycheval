from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from peval_py.workspace_reports import (
    REPORT_MAX_BYTES,
    WorkspaceReportLibrary,
    render_workspace_report_preview,
)


def source_row(source_key: str, artifact_dir: str, *, status: str = "ok") -> dict:
    return {
        "source_key": source_key,
        "artifact_dir": artifact_dir,
        "last_status": status,
    }


class WorkspaceReportLibraryTests(unittest.TestCase):
    def test_import_preserves_bytes_writes_minimal_state_and_orders_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [source_row("cell_a", "runs/default/agent/s1/c1")]
            fixed_now = datetime(2026, 7, 10, 14, 30, 12, 123456)
            library = WorkspaceReportLibrary(root, lambda: rows, now=lambda: fixed_now)
            first = root / "first report.md"
            second = root / "second.HTML"
            first_bytes = "# 分析\n\nExact bytes.\n".encode()
            second_bytes = b"<!doctype html><p>second</p>"
            first.write_bytes(first_bytes)
            second.write_bytes(second_bytes)

            first_id = library.import_file(first, ["cell_a", "cell_a"])
            second_id = library.import_file(second, ["cell_a"])
            later_ids = [library.import_file(second, ["cell_a"]) for _ in range(8)]

            self.assertEqual(first_id, "20260710-143012-123456")
            self.assertEqual(second_id, "20260710-143012-123456-2")
            self.assertEqual(
                json.loads((root / "reports" / first_id / "state.json").read_text()),
                {"source_keys": ["runs/default/agent/s1/c1"]},
            )
            self.assertEqual((root / "reports" / first_id / first.name).read_bytes(), first_bytes)
            self.assertEqual(library.read(first_id).content, first_bytes)
            catalog_ids = [item["report_id"] for item in library.catalog()]
            self.assertEqual(catalog_ids[0], "20260710-143012-123456-10")
            self.assertEqual(catalog_ids[-2:], [second_id, first_id])
            self.assertEqual(later_ids[-1], "20260710-143012-123456-10")
            self.assertEqual(library.catalog()[0]["format"], "html")
            with patch.object(Path, "read_bytes", side_effect=AssertionError("body read")):
                self.assertEqual(len(library.catalog()), 10)

    def test_import_rejects_unsupported_non_utf8_oversize_relative_and_symlink_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [source_row("cell_a", "runs/default/agent/s1/c1")]
            library = WorkspaceReportLibrary(root, lambda: rows)
            unsupported = root / "report.txt"
            unsupported.write_text("no")
            with self.assertRaisesRegex(ValueError, "unsupported report format"):
                library.import_file(unsupported, ["cell_a"])

            non_utf8 = root / "bad.md"
            non_utf8.write_bytes(b"\xff")
            with self.assertRaisesRegex(ValueError, "UTF-8"):
                library.import_file(non_utf8, ["cell_a"])

            oversized = root / "large.html"
            oversized.write_bytes(b"12345")
            with patch("peval_py.workspace_reports.REPORT_MAX_BYTES", 4):
                with self.assertRaisesRegex(ValueError, "byte limit"):
                    library.import_file(oversized, ["cell_a"])

            sparse = root / "sparse.md"
            with sparse.open("wb") as stream:
                stream.seek(REPORT_MAX_BYTES)
                stream.write(b"x")
            with patch.object(Path, "open", side_effect=AssertionError("body opened")):
                with self.assertRaisesRegex(ValueError, "byte limit"):
                    library.import_file(sparse, ["cell_a"])

            valid = root / "valid.md"
            valid.write_text("ok")
            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                with self.assertRaisesRegex(ValueError, "must be absolute"):
                    library.import_file("valid.md", ["cell_a"])
            finally:
                os.chdir(old_cwd)

            link = root / "link.md"
            try:
                link.symlink_to(valid)
            except OSError:
                pass
            else:
                with self.assertRaisesRegex(ValueError, "regular file"):
                    library.import_file(link, ["cell_a"])
            self.assertEqual(library.catalog(), [])

    def test_catalog_silently_projects_missing_sources_and_recovers_without_rewriting_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                source_row("cell_a", "runs/default/agent/s1/c1"),
                source_row("cell_b", "runs/default/agent/s2/c2"),
            ]
            library = WorkspaceReportLibrary(root, lambda: rows)
            report_path = root / "analysis.md"
            report_path.write_text("report")
            report_id = library.import_file(report_path, ["cell_a", "cell_b"])
            state_path = root / "reports" / report_id / "state.json"
            original_state = state_path.read_bytes()

            rows[:] = [source_row("cell_a", "runs/default/agent/s1/c1")]
            self.assertEqual(library.catalog()[0]["source_keys"], ["cell_a"])
            rows.clear()
            self.assertEqual(library.catalog()[0]["source_keys"], [])
            self.assertEqual(state_path.read_bytes(), original_state)
            rows.extend(
                [
                    source_row("cell_a", "runs/default/agent/s1/c1"),
                    source_row("cell_b", "runs/default/agent/s2/c2"),
                ]
            )
            self.assertEqual(library.catalog()[0]["source_keys"], ["cell_a", "cell_b"])

    def test_invalid_packages_paths_ids_and_symlinks_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside_tmp:
            root = Path(tmp)
            outside = Path(outside_tmp)
            reports = root / "reports"
            reports.mkdir()
            valid_id = "20260710-143012-123456"
            package = reports / valid_id
            package.mkdir()
            (package / "report.md").write_text("ok")
            (package / "state.json").write_text(
                json.dumps({"source_keys": ["../outside"]})
            )
            library = WorkspaceReportLibrary(root, lambda: [])
            self.assertEqual(library.catalog(), [])
            with self.assertRaisesRegex(ValueError, "Trial cell"):
                library.read(valid_id)
            with self.assertRaisesRegex(ValueError, "unknown report"):
                library.read("../reports")
            with self.assertRaisesRegex(ValueError, "unknown report"):
                library.read("20261340-256199-999999")

            (package / "state.json").write_text(
                json.dumps(
                    {
                        "source_keys": ["runs/default/agent/s1/c1"],
                        "schema_version": 1,
                    }
                )
            )
            self.assertEqual(library.catalog(), [])

            shutil_target = outside / "escaped"
            shutil_target.mkdir()
            runs = root / "runs"
            runs.mkdir()
            try:
                (runs / "default").symlink_to(shutil_target, target_is_directory=True)
            except OSError:
                pass
            else:
                (package / "state.json").write_text(
                    json.dumps({"source_keys": ["runs/default/agent/s1/c1"]})
                )
                with self.assertRaisesRegex(ValueError, "escapes"):
                    library.read(valid_id)

                (runs / "default").unlink()
                (runs / "default").symlink_to(runs / "default", target_is_directory=True)
                self.assertEqual(library.catalog(), [])

            link_id = "20260710-143012-123457"
            try:
                (reports / link_id).symlink_to(outside, target_is_directory=True)
            except OSError:
                pass
            self.assertEqual(library.catalog(), [])

    def test_replace_bindings_is_atomic_and_delete_is_permanent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                source_row("cell_a", "runs/default/agent/s1/c1"),
                source_row("cell_b", "runs/default/agent/s2/c2"),
                source_row("cell_missing", "runs/default/agent/s3/c3", status="missing"),
            ]
            library = WorkspaceReportLibrary(root, lambda: rows)
            report_path = root / "analysis.htm"
            report_path.write_text("<p>report</p>")
            report_id = library.import_file(report_path, ["cell_a"])

            library.replace_bindings(report_id, ["cell_b", "cell_b"])
            state_path = root / "reports" / report_id / "state.json"
            self.assertEqual(
                json.loads(state_path.read_text()),
                {"source_keys": ["runs/default/agent/s2/c2"]},
            )
            self.assertFalse(any("tmp" in path.name for path in state_path.parent.iterdir()))
            before = state_path.read_bytes()
            with self.assertRaisesRegex(ValueError, "unreadable source"):
                library.replace_bindings(report_id, ["cell_missing"])
            self.assertEqual(state_path.read_bytes(), before)
            with self.assertRaisesRegex(ValueError, "at least one"):
                library.replace_bindings(report_id, [])
            self.assertEqual(state_path.read_bytes(), before)

            library.delete(report_id)
            self.assertEqual(library.catalog(), [])
            self.assertFalse((root / "reports" / report_id).exists())
            with self.assertRaisesRegex(ValueError, "unknown report"):
                library.read(report_id)

    def test_markdown_preview_is_rich_but_escapes_raw_html_and_html_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [source_row("cell_a", "runs/default/agent/s1/c1")]
            library = WorkspaceReportLibrary(root, lambda: rows)
            markdown_path = root / "analysis.markdown"
            markdown_path.write_text(
                "# Title\n\n> Quote\n\n- outer\n  - inner\n\n"
                "```py\nprint('ok')\n```\n\n| A | B |\n| - | - |\n| x | y |\n\n"
                "**bold** and ~~gone~~ and [link](https://example.com)\n\n"
                "<script>alert('unsafe')</script>\n"
            )
            report = library.read(library.import_file(markdown_path, ["cell_a"]))
            preview = render_workspace_report_preview(report).decode()
            self.assertIn("<blockquote>", preview)
            self.assertIn("<table>", preview)
            self.assertIn("<s>gone</s>", preview)
            self.assertIn('<code class="language-py">', preview)
            self.assertIn("&lt;script&gt;", preview)
            self.assertNotIn("<script>alert", preview)

            html_path = root / "analysis.html"
            html_bytes = b"<!doctype html><script>window.ok = true;</script>"
            html_path.write_bytes(html_bytes)
            html_report = library.read(library.import_file(html_path, ["cell_a"]))
            self.assertEqual(render_workspace_report_preview(html_report), html_bytes)


if __name__ == "__main__":
    unittest.main()
