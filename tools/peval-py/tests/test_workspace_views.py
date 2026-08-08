from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from peval_py.workspace_views import (
    WorkspaceViewConflict,
    WorkspaceViewLibrary,
    WorkspaceViewNotFound,
    render_view_markdown,
)


def filters(**overrides):
    value = {
        "state": "active",
        "search": "",
        "categories": [],
        "tags": [],
        "agents": [],
        "models": [],
        "results": [],
    }
    value.update(overrides)
    return value


class WorkspaceViewLibraryTests(unittest.TestCase):
    def test_save_round_trips_unicode_notes_and_requires_explicit_overwrite(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = WorkspaceViewLibrary(root)
            view = library.save(
                name="发布 对比",
                filters=filters(search="release", tags=["core", "发布"]),
                group_by="model",
                notes="# Release notes\n\nCompare the candidate models.",
                overwrite=False,
            )

            path = root / "views" / "发布 对比.md"
            self.assertTrue(path.is_file())
            stored = path.read_text(encoding="utf-8")
            self.assertIn("schema_version: 1", stored)
            self.assertNotIn("state: active", stored)
            self.assertNotIn("agents:", stored)
            self.assertNotIn("models:", stored)
            self.assertNotIn("results:", stored)
            self.assertEqual(library.list(), [view])
            self.assertEqual(
                render_view_markdown(view),
                path.read_text(encoding="utf-8"),
            )

            with self.assertRaisesRegex(WorkspaceViewConflict, "already exists"):
                library.save(
                    name="发布 对比",
                    filters=filters(),
                    group_by="overall",
                    notes="replacement",
                    overwrite=False,
                )
            self.assertIn("Release notes", path.read_text(encoding="utf-8"))

            replacement = library.save(
                name="发布 对比",
                filters=filters(state="archived", results=["failed"]),
                group_by="overall",
                notes="replacement",
                overwrite=True,
            )
            self.assertEqual(library.list(), [replacement])
            self.assertEqual(replacement.notes, "replacement")
            self.assertEqual(replacement.filters.state, "archived")
            self.assertFalse(
                any(".tmp-" in item.name for item in path.parent.iterdir())
            )

            default_view = library.save(
                name="default",
                filters=filters(),
                group_by="agent",
                notes="",
                overwrite=False,
            )
            default_text = (root / "views" / "default.md").read_text(encoding="utf-8")
            self.assertNotIn("filters:", default_text)
            self.assertEqual(
                default_text,
                "---\nschema_version: 1\ngroup_by: agent\n---\n",
            )
            self.assertEqual(default_view.filters.state, "active")

    def test_category_filters_and_grouping_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = WorkspaceViewLibrary(root)

            saved = library.save(
                name="Category cohort",
                filters=filters(categories=["frontend", "未分类"], tags=["daily"]),
                group_by="category",
                notes="Compare source categories.",
                overwrite=False,
            )

            self.assertEqual(saved.filters.categories, ("frontend", "未分类"))
            self.assertEqual(saved.group_by, "category")
            stored = (root / "views" / "Category cohort.md").read_text(encoding="utf-8")
            self.assertIn("categories:\n  - frontend\n  - 未分类", stored)
            self.assertIn("group_by: category", stored)
            self.assertEqual(library.list(), [saved])

            configured = library.update(
                name="Category cohort",
                field="configuration",
                value=(
                    "filters:\n"
                    "  categories: [backend, infra]\n"
                    "  models: [m1]\n"
                    "group_by: category\n"
                ),
            )
            self.assertEqual(configured.filters.categories, ("backend", "infra"))
            self.assertEqual(configured.filters.models, ("m1",))
            self.assertEqual(configured.group_by, "category")
            self.assertEqual(configured.notes, "Compare source categories.")

    def test_update_rename_configuration_notes_and_prevalidated_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = WorkspaceViewLibrary(root)
            library.save(
                name="Daily",
                filters=filters(tags=["old"]),
                group_by="agent",
                notes="Original",
                overwrite=False,
            )
            library.save(
                name="Existing",
                filters=filters(),
                group_by="overall",
                notes="Keep",
                overwrite=False,
            )

            configured = library.update(
                name="Daily",
                field="configuration",
                value=(
                    "filters:\n"
                    "  state: archived\n"
                    "  search: failure\n"
                    "  tags: [red, blue]\n"
                    "group_by: model\n"
                ),
            )
            self.assertEqual(configured.filters.state, "archived")
            self.assertEqual(configured.filters.search, "failure")
            self.assertEqual(configured.filters.tags, ("red", "blue"))
            self.assertEqual(configured.group_by, "model")
            self.assertEqual(configured.notes, "Original")

            emptied = library.update(name="Daily", field="notes", value="")
            self.assertEqual(emptied.notes, "")
            renamed = library.update(name="Daily", field="name", value="Renamed")
            self.assertEqual(renamed.name, "Renamed")
            self.assertFalse((root / "views" / "Daily.md").exists())
            self.assertTrue((root / "views" / "Renamed.md").is_file())

            with self.assertRaisesRegex(WorkspaceViewConflict, "already exists"):
                library.update(name="Renamed", field="name", value="Existing")
            with self.assertRaisesRegex(ValueError, "optional filters"):
                library.update(
                    name="Renamed",
                    field="configuration",
                    value="schema_version: 1\ngroup_by: agent\n",
                )
            with self.assertRaisesRegex(ValueError, "group_by"):
                library.update(
                    name="Renamed",
                    field="configuration",
                    value="filters: {}\n",
                )

            with self.assertRaisesRegex(WorkspaceViewNotFound, "Missing"):
                library.delete(["Renamed", "Missing"])
            self.assertTrue((root / "views" / "Renamed.md").is_file())
            self.assertTrue((root / "views" / "Existing.md").is_file())
            self.assertEqual(
                library.delete(["Renamed", "Existing"]), ["Renamed", "Existing"]
            )
            self.assertEqual(library.list(), [])

    def test_invalid_or_unsafe_files_do_not_enter_catalog(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            tempfile.TemporaryDirectory() as outside_tmp,
        ):
            root = Path(tmp)
            outside = Path(outside_tmp)
            library = WorkspaceViewLibrary(root)
            library.save(
                name="valid",
                filters=filters(),
                group_by="agent",
                notes="ok",
                overwrite=False,
            )
            views = root / "views"
            (views / "broken.md").write_text("not frontmatter", encoding="utf-8")
            (views / "unsupported.md").write_text(
                "---\nschema_version: 2\nfilters: {}\ngroup_by: agent\n---\n",
                encoding="utf-8",
            )
            target = outside / "outside.md"
            target.write_text("outside", encoding="utf-8")
            try:
                (views / "linked.md").symlink_to(target)
            except OSError:
                pass

            self.assertEqual([view.name for view in library.list()], ["valid"])
            with self.assertRaisesRegex(ValueError, "filename stem"):
                library.update(name="valid", field="name", value="../escape")
            if (views / "linked.md").is_symlink():
                with self.assertRaisesRegex(WorkspaceViewNotFound, "linked"):
                    library.delete(["linked"])
                self.assertEqual(target.read_text(encoding="utf-8"), "outside")
            for invalid in ("", ".", "..", "a/b", "a\\b", "bad\nname"):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    library.save(
                        name=invalid,
                        filters=filters(),
                        group_by="agent",
                        notes="",
                        overwrite=False,
                    )
