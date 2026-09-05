from __future__ import annotations

import os

from psycheval.config import ToolConfig, write_workspace_adapter_default_db
from tests.peval.peval_test_support import (
    BrokenEntryPoint,
    CustomPathAdapter,
    FakeEntryPoint,
    FakeEntryPoints,
    Path,
    SimpleNamespace,
    adapter_for,
    apply_overrides,
    available_adapter_ids,
    config_for_adapter,
    load_config,
    patch,
    tempfile,
    unittest,
)


class PevalConfigAdapterTests(unittest.TestCase):
    def test_harbor_identifiers_in_toml_must_be_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for table in ("datasets", "mounts"):
                root.joinpath("peval.toml").write_text(
                    f'[[harbor.{table}]]\nid = 1\npath = "."\n', encoding="utf-8"
                )
                with (
                    self.subTest(table=table),
                    self.assertRaisesRegex(
                        ValueError,
                        rf"harbor\.{table}\.0\.id: Input should be a valid string",
                    ),
                ):
                    load_config(workspace_root=root)

    def test_config_discovery_honors_peval_root_outside_the_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            workspace = base / "workspace"
            outside = base / "outside"
            workspace.mkdir()
            outside.mkdir()
            workspace.joinpath("peval.toml").write_text(
                'description = "Environment workspace"\n', encoding="utf-8"
            )
            old_cwd = Path.cwd()
            try:
                os.chdir(outside)
                with patch.dict(os.environ, {"PEVAL_ROOT": str(workspace)}):
                    discovered = load_config()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(discovered.workspace_root, str(workspace.resolve()))
            self.assertEqual(discovered.description, "Environment workspace")

    def test_config_discovers_workspace_and_rejects_removed_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            child = root / "nested" / "child"
            child.mkdir(parents=True)
            root.joinpath("peval.toml").write_text(
                'locale = "zh"\nanalysis_eval_slug = "custom-eval"\n'
                '[defaults]\nadapter = "opencode"\n',
                encoding="utf-8",
            )
            old_cwd = Path.cwd()
            try:
                os.chdir(child)
                discovered = load_config()
                self.assertEqual(discovered.locale, "zh-CN")
                self.assertEqual(discovered.analysis_eval_slug, "custom-eval")
                self.assertEqual(discovered.adapter, "opencode")
                self.assertEqual(discovered.workspace_root, str(root.resolve()))
            finally:
                os.chdir(old_cwd)

            for legacy in ("agent", "locale", "trajectory_id"):
                root.joinpath("peval.toml").write_text(
                    f'[defaults]\n{legacy} = "removed"\n', encoding="utf-8"
                )
                with (
                    self.subTest(legacy=legacy),
                    self.assertRaisesRegex(
                        ValueError, rf"defaults\.{legacy}: unknown configuration field"
                    ),
                ):
                    load_config(workspace_root=root)

    def test_config_is_strict_frozen_and_reports_source_field_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("peval.toml").write_text(
                'description = "**Nightly** evaluation workspace"\n',
                encoding="utf-8",
            )
            discovered = load_config(workspace_root=root)
            self.assertEqual(discovered.description, "**Nightly** evaluation workspace")
            with self.assertRaisesRegex(Exception, "frozen"):
                discovered.locale = "en"  # type: ignore[misc]
            with self.assertRaises(ValueError):
                ToolConfig(max_content_chars="10")  # type: ignore[arg-type]

            root.joinpath("peval.toml").write_text(
                "description = 42\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                ValueError,
                rf"{root / 'peval.toml'}: description: Input should be a valid string",
            ):
                load_config(workspace_root=root)

            root.joinpath("peval.toml").write_text("unknown = true\n", encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError, "unknown: unknown configuration field"
            ):
                load_config(workspace_root=root)

            root.joinpath("peval.toml").write_text(
                "[adapters.opencode]\ndefault_db_path = 42\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError,
                r"adapters\.opencode\.default_db_path: Input should be a valid string",
            ):
                load_config(workspace_root=root)

    def test_config_passes_selected_adapter_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "peval.toml"
            config_path.write_text(
                """
[defaults]
adapter = "opencode"

[adapters.custom]
label_prefix = "configured"
enabled = true
""",
                encoding="utf-8",
            )
            config = load_config(workspace_root=tmp)
            self.assertEqual(config.adapter, "opencode")
            self.assertEqual(config.adapter_options, {})

            overridden = apply_overrides(
                config,
                SimpleNamespace(adapter="custom", no_redact=False),
            )
            self.assertEqual(overridden.adapter, "custom")
            self.assertEqual(
                overridden.adapter_options,
                {"label_prefix": "configured", "enabled": True},
            )

            list_override = apply_overrides(
                config,
                SimpleNamespace(adapter=["custom", "p1=opencode"], no_redact=False),
            )
            self.assertEqual(list_override.adapter, "custom")
            self.assertEqual(
                list_override.adapter_options,
                {"label_prefix": "configured", "enabled": True},
            )

            selected = config_for_adapter(config, "custom")
            self.assertEqual(
                selected.adapter_options,
                {"label_prefix": "configured", "enabled": True},
            )

    def test_adapter_default_db_path_resolves_relative_to_defining_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / "configs"
            config_dir.mkdir()
            config_path = config_dir / "peval.toml"
            config_path.write_text(
                """
[adapters.psychevo]
default_db_path = "state.db"
label_prefix = "configured"

[adapters.hermes]
default_db_path = "../hermes/state.db"
""",
                encoding="utf-8",
            )

            config = load_config(workspace_root=config_dir)
            self.assertEqual(
                config.adapter_default_db_paths,
                {
                    "psychevo": str((config_dir / "state.db").resolve()),
                    "hermes": str((config_dir / "../hermes/state.db").resolve()),
                },
            )
            self.assertEqual(
                config.adapter_options_by_id["psychevo"],
                {"label_prefix": "configured"},
            )
            self.assertEqual(config.adapter_options_by_id["hermes"], {})

    def test_adapter_default_db_path_expands_home_and_absolute_like_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            config_path = root / "peval.toml"
            windows_path = r"C:\Users\me\AppData\Local\opencode\opencode.db"
            unc_path = r"\\server\share\hermes\state.db"
            config_path.write_text(
                f"""
[adapters.psychevo]
default_db_path = "~/.psychevo/state.db"

[adapters.opencode]
default_db_path = '{windows_path}'

[adapters.hermes]
default_db_path = '{unc_path}'
""",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"HOME": str(home)}):
                config = load_config(workspace_root=root)

            self.assertEqual(
                config.adapter_default_db_paths["psychevo"],
                str((home / ".psychevo/state.db").resolve()),
            )
            self.assertEqual(config.adapter_default_db_paths["opencode"], windows_path)
            self.assertEqual(config.adapter_default_db_paths["hermes"], unc_path)

    def test_write_workspace_adapter_default_db_uses_tilde_for_home_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            config_path = root / "peval.toml"
            config_path.write_text('locale = "en"\n', encoding="utf-8")
            home_db = home / ".psychevo" / "state.db"

            with patch.dict(os.environ, {"HOME": str(home)}):
                resolved = write_workspace_adapter_default_db(
                    config_path,
                    "psychevo",
                    str(home_db),
                )
                config = load_config(workspace_root=root)

            self.assertEqual(resolved, str(home_db.resolve()))
            self.assertEqual(
                config.adapter_default_db_paths["psychevo"],
                str(home_db.resolve()),
            )
            self.assertIn(
                'default_db_path = "~/.psychevo/state.db"\n',
                config_path.read_text(encoding="utf-8"),
            )

    def test_write_workspace_adapter_default_db_preserves_adapter_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "peval.toml"
            config_path.write_text(
                """
locale = "en"

[adapters.opencode]
label_prefix = "configured"
default_db_path = "old.db"
enabled = true

[adapters.hermes]
default_db_path = "hermes.db"
""",
                encoding="utf-8",
            )

            resolved = write_workspace_adapter_default_db(
                config_path,
                "opencode",
                "db/new.db",
            )

            self.assertEqual(resolved, str((Path(tmp) / "db/new.db").resolve()))
            config = load_config(workspace_root=tmp)
            self.assertEqual(
                config.adapter_default_db_paths["opencode"],
                str((Path(tmp) / "db/new.db").resolve()),
            )
            self.assertEqual(
                config.adapter_default_db_paths["hermes"],
                str((Path(tmp) / "hermes.db").resolve()),
            )
            self.assertEqual(
                config.adapter_options_by_id["opencode"],
                {"label_prefix": "configured", "enabled": True},
            )
            text = config_path.read_text(encoding="utf-8")
            self.assertIn('default_db_path = "db/new.db"\n', text)
            self.assertIn('label_prefix = "configured"\n', text)
            self.assertIn("enabled = true\n", text)

            cleared = write_workspace_adapter_default_db(
                config_path,
                "opencode",
                "",
            )

            self.assertIsNone(cleared)
            config = load_config(workspace_root=tmp)
            self.assertNotIn("opencode", config.adapter_default_db_paths)
            self.assertEqual(
                config.adapter_default_db_paths["hermes"],
                str((Path(tmp) / "hermes.db").resolve()),
            )
            self.assertEqual(
                config.adapter_options_by_id["opencode"],
                {"label_prefix": "configured", "enabled": True},
            )
            text = config_path.read_text(encoding="utf-8")
            opencode_section = text.split("[adapters.opencode]", 1)[1].split(
                "[adapters.hermes]",
                1,
            )[0]
            self.assertNotIn("default_db_path", opencode_section)
            self.assertIn('default_db_path = "hermes.db"\n', text)

    def test_adapter_registry_discovers_builtins_and_entry_points_lazily(self) -> None:
        custom_entry = FakeEntryPoint("custom", CustomPathAdapter)
        unused_entry = BrokenEntryPoint("unused", object())
        with patch(
            "psycheval.adapters.entry_points",
            return_value=FakeEntryPoints([custom_entry, unused_entry]),
        ):
            self.assertEqual(adapter_for("psychevo").agent_id, "psychevo")
            self.assertIn("custom", available_adapter_ids())
            self.assertEqual(custom_entry.load_count, 0)
            self.assertEqual(unused_entry.load_count, 0)

            adapter = adapter_for("custom")
            self.assertEqual(adapter.agent_id, "custom")
            self.assertEqual(custom_entry.load_count, 1)
            self.assertEqual(unused_entry.load_count, 0)

    def test_adapter_registry_accepts_class_factory_and_instance_entry_points(
        self,
    ) -> None:
        values = [CustomPathAdapter, lambda: CustomPathAdapter(), CustomPathAdapter()]
        for value in values:
            with self.subTest(value=type(value).__name__):
                with patch(
                    "psycheval.adapters.entry_points",
                    return_value=FakeEntryPoints([FakeEntryPoint("custom", value)]),
                ):
                    adapter = adapter_for("custom")
                    self.assertTrue(callable(getattr(adapter, "convert_path", None)))

    def test_adapter_registry_reports_duplicate_and_unknown_ids(self) -> None:
        duplicate = FakeEntryPoint("opencode", CustomPathAdapter)
        with patch(
            "psycheval.adapters.entry_points",
            return_value=FakeEntryPoints([duplicate]),
        ):
            with self.assertRaisesRegex(ValueError, "duplicate adapter id: opencode"):
                available_adapter_ids()
            self.assertEqual(duplicate.load_count, 0)

        custom = FakeEntryPoint("custom", CustomPathAdapter)
        with patch(
            "psycheval.adapters.entry_points",
            return_value=FakeEntryPoints([custom]),
        ):
            with self.assertRaisesRegex(ValueError, "unsupported adapter: missing"):
                adapter_for("missing")
            self.assertEqual(custom.load_count, 0)

    def test_adapter_registry_does_not_read_removed_entry_point_groups(self) -> None:
        for removed_group in ("peval_py.adapters", "psycheval.peval.adapters"):
            with self.subTest(group=removed_group):
                legacy = FakeEntryPoint("custom", CustomPathAdapter)

                class LegacyOnlyEntryPoints:
                    def select(self, *, group: str):
                        return [legacy] if group == removed_group else []

                with patch(
                    "psycheval.adapters.entry_points",
                    return_value=LegacyOnlyEntryPoints(),
                ):
                    self.assertNotIn("custom", available_adapter_ids())
                    self.assertEqual(legacy.load_count, 0)
