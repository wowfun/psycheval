from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from psycheval.workspace_views import (
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
    def test_explicit_overwrite_recovers_unreadable_view_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            library = WorkspaceViewLibrary(Path(tmp))
            other = library.save(
                name="other", filters={}, group_by="overall", notes="keep"
            )
            target = library._path_for_name("broken")
            for content in (
                b"not frontmatter",
                b"\xff",
                b"---\nschema_version: 1\ngroup_by: overall\n---\nlegacy",
                b"---\nschema_version: 2\nname: other\ngroup_by: overall\n---\nwrong identity",
            ):
                with self.subTest(content=content):
                    target.write_bytes(content)
                    with self.assertRaises(WorkspaceViewConflict):
                        library.save(
                            name="broken", filters={}, group_by="overall", notes="new"
                        )
                    self.assertEqual(target.read_bytes(), content)
                    recovered = library.save(
                        name="broken",
                        filters={},
                        group_by="model",
                        notes="recovered",
                        overwrite=True,
                    )
                    self.assertEqual(library.get("broken"), recovered)
                    self.assertEqual(library.get("other"), other)

    def test_delete_can_remove_corrupt_current_view_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            library = WorkspaceViewLibrary(Path(tmp))
            library.save(name="broken", filters={}, group_by="overall", notes="old")
            target = library._path_for_name("broken")
            target.write_bytes(b"\xff")
            self.assertEqual(library.delete(["broken"]), ["broken"])
            self.assertFalse(target.exists())

    def test_recovery_rejects_existing_and_dangling_symlink_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = WorkspaceViewLibrary(root / "workspace")
            library.views_root.mkdir(parents=True)
            outside = root / "outside.md"
            outside.write_bytes(b"keep")
            target = library._path_for_name("linked")
            try:
                target.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            for dangling in (False, True):
                if dangling:
                    outside.unlink()
                with self.subTest(dangling=dangling):
                    with self.assertRaisesRegex(ValueError, "regular file"):
                        library.save(
                            name="linked",
                            filters={},
                            group_by="overall",
                            notes="replacement",
                            overwrite=True,
                        )
                    with self.assertRaises(WorkspaceViewNotFound):
                        library.delete(["linked"])
                    self.assertTrue(target.is_symlink())
                    self.assertEqual(outside.exists(), not dangling)
                    if not dangling:
                        self.assertEqual(outside.read_bytes(), b"keep")

    def test_rename_rolls_back_when_removing_old_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            library = WorkspaceViewLibrary(Path(tmp))
            original = library.save(
                name="old", filters={}, group_by="overall", notes="retained"
            )
            source = library._path_for_name("old")
            unlink = Path.unlink

            def fail_source(path, *args, **kwargs):
                if path == source:
                    raise PermissionError("cannot remove old view")
                return unlink(path, *args, **kwargs)

            with patch.object(Path, "unlink", fail_source):
                with self.assertRaisesRegex(PermissionError, "old view"):
                    library.update(name="old", field="name", value="new")
            self.assertEqual(library.list(), [original])
            self.assertFalse(library._path_for_name("new").exists())

    def test_invalid_view_listing_reports_the_file_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            library = WorkspaceViewLibrary(Path(tmp))
            library.views_root.mkdir()
            path = library.views_root / "legacy.md"
            content = b"---\nschema_version: 1\ngroup_by: overall\n---\nkeep"
            path.write_bytes(content)
            with self.assertLogs("psycheval.workspace_views", level="WARNING") as logs:
                self.assertEqual(library.list(), [])
            self.assertIn("legacy.md", "\n".join(logs.output))
            self.assertEqual(path.read_bytes(), content)

    def test_frontmatter_cannot_claim_another_file_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            library = WorkspaceViewLibrary(Path(tmp))
            library.save(name="first", filters={}, group_by="overall", notes="keep")
            path = next(library.views_root.iterdir())
            path.write_text(
                path.read_text(encoding="utf-8").replace("name: first", "name: second"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "does not match"):
                library.get("first")
            self.assertEqual(library.list(), [])

    def test_portable_names_remain_distinct_through_update_rename_and_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            library = WorkspaceViewLibrary(Path(tmp))
            names = ["aaa:", "aaG:", "Daily", "daily", "中" * 119 + ":", "CON"]
            for name in names:
                library.save(name=name, filters={}, group_by="overall", notes=name)
            self.assertEqual({view.name for view in library.list()}, set(names))
            for name in names:
                self.assertEqual(library.get(name).notes, name)
            library.update(name="aaG:", field="notes", value="changed")
            self.assertEqual(library.get("aaa:").notes, "aaa:")
            renamed = library.update(
                name="aaG:", field="name", value="重命名:" + "文" * 100
            )
            self.assertEqual(library.get(renamed.name), renamed)
            library.delete([renamed.name])
            self.assertEqual(library.get("aaa:").notes, "aaa:")
            self.assertTrue(
                all(
                    len(path.name.encode("utf-8")) <= 255
                    for path in library.views_root.iterdir()
                )
            )

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

            path = library._path_for_name("发布 对比")
            self.assertTrue(path.is_file())
            stored = path.read_text(encoding="utf-8")
            self.assertIn("schema_version: 2", stored)
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
            default_text = (library._path_for_name("default")).read_text(
                encoding="utf-8"
            )
            self.assertNotIn("filters:", default_text)
            self.assertEqual(
                default_text,
                "---\nschema_version: 2\nname: default\ngroup_by: agent\n---\n",
            )
            self.assertEqual(default_view.filters.state, "active")

    def test_names_with_windows_filename_characters_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = WorkspaceViewLibrary(root)
            saved = library.save(
                name="All: sessions",
                filters=filters(),
                group_by="agent",
                notes="portable name",
                overwrite=False,
            )
            files = list((root / "views").iterdir())
            self.assertEqual([view.name for view in library.list()], [saved.name])
            self.assertEqual(library.get("All: sessions"), saved)
            self.assertNotIn(":", files[0].name)

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
            stored = (library._path_for_name("Category cohort")).read_text(
                encoding="utf-8"
            )
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

    def test_harbor_filters_and_grouping_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = WorkspaceViewLibrary(root)

            saved = library.save(
                name="Harbor cohort",
                filters=filters(
                    tasks=["pbench-v1.0/web-search-01"],
                    jobs=["opencode-real"],
                    providers=["xiaomi-token-plan-cn"],
                ),
                group_by="task",
                notes="",
                overwrite=False,
            )

            self.assertEqual(saved.filters.tasks, ("pbench-v1.0/web-search-01",))
            self.assertEqual(saved.filters.jobs, ("opencode-real",))
            self.assertEqual(saved.filters.providers, ("xiaomi-token-plan-cn",))
            self.assertEqual(saved.group_by, "task")
            stored = (library._path_for_name("Harbor cohort")).read_text(
                encoding="utf-8"
            )
            self.assertIn("tasks:\n  - pbench-v1.0/web-search-01", stored)
            self.assertIn("jobs:\n  - opencode-real", stored)
            self.assertIn("providers:\n  - xiaomi-token-plan-cn", stored)

            configured = library.update(
                name="Harbor cohort",
                field="configuration",
                value=(
                    "filters:\n"
                    "  tasks: [pbench-v1.0/web-fetch-01]\n"
                    "  jobs: [hermes-real]\n"
                    "  providers: [xiaomi]\n"
                    "group_by: provider\n"
                ),
            )
            self.assertEqual(configured.filters.tasks, ("pbench-v1.0/web-fetch-01",))
            self.assertEqual(configured.filters.jobs, ("hermes-real",))
            self.assertEqual(configured.filters.providers, ("xiaomi",))
            self.assertEqual(configured.group_by, "provider")

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
            self.assertFalse((library._path_for_name("Daily")).exists())
            self.assertTrue((library._path_for_name("Renamed")).is_file())

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
            self.assertTrue((library._path_for_name("Renamed")).is_file())
            self.assertTrue((library._path_for_name("Existing")).is_file())
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
                "---\nschema_version: 999\nname: unsupported\nfilters: {}\ngroup_by: agent\n---\n",
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
