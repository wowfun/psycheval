from __future__ import annotations

import os
import stat
import threading
from unittest.mock import patch

from psycheval import skill_install
from psycheval.workspace import init_workspace
from tests.peval.peval_test_support import (
    Path,
    json,
    subprocess,
    sys,
    tempfile,
    unittest,
)


class PevalWorkspaceInitTests(unittest.TestCase):
    def test_init_creates_only_peval_state_and_preserves_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            result = init_workspace(str(root))

            self.assertEqual(result.schema_version, 1)
            self.assertEqual(result.root, root.resolve())
            self.assertIsNone(result.agent_skill)
            config_text = (root / "peval.toml").read_text(encoding="utf-8")
            self.assertIn("[adapters.psychevo]\n", config_text)
            self.assertIn('default_db_path = "~/.psychevo/state.db"\n', config_text)
            self.assertIn("[adapters.opencode]\n", config_text)
            self.assertIn(
                'default_db_path = "~/.local/share/opencode/opencode.db"\n',
                config_text,
            )
            self.assertIn("[adapters.hermes]\n", config_text)
            self.assertIn('default_db_path = "~/.hermes/state.db"\n', config_text)
            self.assertEqual(
                result.log_path, root.resolve() / "logs" / "peval-serve.jsonl"
            )
            self.assertTrue((root / "logs").is_dir())
            self.assertFalse((root / ".agents").exists())
            self.assertFalse((root / "state.db").exists())
            for unwanted in [
                "peval-py.toml",
                "runs",
                "datasets",
                "scripts",
                "pidx-psychevo-acp.eval.toml",
                ".gitignore",
            ]:
                self.assertFalse((root / unwanted).exists(), unwanted)

            config = root / "peval.toml"
            config.write_text(
                '[adapters.psychevo]\ndefault_db_path = "custom.db"\n', encoding="utf-8"
            )
            second = init_workspace(str(root))

            self.assertEqual(
                second.log_path, root.resolve() / "logs" / "peval-serve.jsonl"
            )
            self.assertEqual(
                config.read_text(encoding="utf-8"),
                '[adapters.psychevo]\ndefault_db_path = "custom.db"\n',
            )
            self.assertIsNone(second.agent_skill)

    def test_init_explicitly_installs_and_replaces_one_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = write_skill(base / "source" / "peval")
            script = source / "scripts" / "inspect.sh"
            script.parent.mkdir()
            script.write_text("#!/bin/sh\n", encoding="utf-8")
            script.chmod(0o755)
            root = base / "workspace"

            installed = init_workspace(str(root), skill_dir=str(source))
            destination = root.resolve() / ".agents" / "skills" / "peval"
            self.assertEqual(installed.agent_skill.path, destination)
            self.assertEqual(installed.agent_skill.action, "installed")
            self.assertFalse((destination / ".peval-managed.json").exists())
            if os.name != "nt":
                self.assertTrue(
                    (destination / "scripts" / "inspect.sh").stat().st_mode
                    & stat.S_IXUSR
                )

            (destination / "local.md").write_text("workspace edit\n", encoding="utf-8")
            (source / "references").mkdir()
            (source / "references" / "new.md").write_text("new\n", encoding="utf-8")
            replaced = init_workspace(str(root), skill_dir=str(source))

            self.assertEqual(replaced.agent_skill.path, destination)
            self.assertEqual(replaced.agent_skill.action, "replaced")
            self.assertFalse((destination / "local.md").exists())
            self.assertEqual(
                (destination / "references" / "new.md").read_text(encoding="utf-8"),
                "new\n",
            )

    def test_init_installs_named_skill_from_a_cwd_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = write_skill(base / "sources" / "skill-a", name="skill-a")
            root = base / "workspace"
            old_cwd = Path.cwd()
            try:
                os.chdir(base)
                result = init_workspace(str(root), skill_dir="sources/skill-a")
            finally:
                os.chdir(old_cwd)

            destination = root.resolve() / ".agents" / "skills" / "skill-a"
            self.assertEqual(result.agent_skill.path, destination)
            self.assertTrue((destination / "SKILL.md").is_file())
            self.assertEqual(source.resolve().name, destination.name)

    def test_invalid_skill_fails_before_workspace_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "workspace"
            missing = base / "missing-skill"
            missing.mkdir()

            with self.assertRaisesRegex(ValueError, "missing SKILL.md"):
                init_workspace(str(root), skill_dir=str(missing))
            self.assertFalse(root.exists())

            mismatch = write_skill(base / "wrong-name", name="different-name")
            with self.assertRaisesRegex(ValueError, "name must equal"):
                init_workspace(str(root), skill_dir=str(mismatch))
            self.assertFalse(root.exists())

            overlapping_root = base / "overlapping-workspace"
            overlapping = write_skill(overlapping_root / ".agents" / "skills" / "peval")
            with self.assertRaisesRegex(ValueError, "must not overlap"):
                init_workspace(str(overlapping_root), skill_dir=str(overlapping))
            self.assertFalse((overlapping_root / "peval.toml").exists())
            self.assertFalse((overlapping_root / "logs").exists())

    def test_skill_source_symlink_fails_before_workspace_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = write_skill(base / "source" / "peval")
            linked = base / "peval"
            try:
                linked.symlink_to(source, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")
            root = base / "workspace"

            with self.assertRaisesRegex(ValueError, "must not be a symlink"):
                init_workspace(str(root), skill_dir=str(linked))
            self.assertFalse(root.exists())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs unavailable")
    def test_skill_special_file_fails_before_workspace_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = write_skill(base / "source" / "peval")
            os.mkfifo(source / "pipe")
            root = base / "workspace"

            with self.assertRaisesRegex(ValueError, "regular files only"):
                init_workspace(str(root), skill_dir=str(source))
            self.assertFalse(root.exists())

    def test_failed_replacement_restores_the_existing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = write_skill(base / "source" / "peval", body="original\n")
            root = base / "workspace"
            init_workspace(str(root), skill_dir=str(source))
            destination = root.resolve() / ".agents" / "skills" / "peval"
            original = (destination / "SKILL.md").read_text(encoding="utf-8")
            write_skill(source, body="replacement\n")
            replace_path = skill_install._replace_path

            def fail_staged_replace(current: Path, target: Path) -> None:
                if target == destination and current.name.startswith(".peval-skill-"):
                    raise OSError("injected replacement failure")
                replace_path(current, target)

            with patch.object(
                skill_install, "_replace_path", side_effect=fail_staged_replace
            ):
                with self.assertRaisesRegex(OSError, "injected replacement failure"):
                    init_workspace(str(root), skill_dir=str(source))

            self.assertEqual(
                (destination / "SKILL.md").read_text(encoding="utf-8"), original
            )
            self.assertEqual(list(destination.parent.glob(".*.backup")), [])

    def test_skill_cleanup_retries_windows_read_only_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "staged"
            root.mkdir()
            readonly = root / "readonly.md"
            readonly.write_text("content\n", encoding="utf-8")
            readonly.chmod(stat.S_IREAD)
            retried_modes: list[int] = []

            def fake_rmtree(path: Path, *, onexc) -> None:
                def retry(raw_path: str) -> None:
                    retried_modes.append(Path(raw_path).stat().st_mode)
                    Path(raw_path).unlink()

                onexc(
                    retry,
                    str(readonly),
                    PermissionError("injected Windows read-only failure"),
                )
                Path(path).rmdir()

            with patch.object(skill_install.shutil, "rmtree", side_effect=fake_rmtree):
                skill_install._remove_path(root)

            self.assertFalse(root.exists())
            self.assertTrue(retried_modes[0] & stat.S_IWRITE)

    def test_replacement_recovers_an_interrupted_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = write_skill(base / "source" / "peval", body="original\n")
            root = base / "workspace"
            init_workspace(str(root), skill_dir=str(source))
            destination = root.resolve() / ".agents" / "skills" / "peval"
            backup = destination.with_name(f".{destination.name}.{'a' * 32}.backup")
            destination.replace(backup)
            write_skill(source, body="replacement\n")

            result = init_workspace(str(root), skill_dir=str(source))

            self.assertEqual(result.agent_skill.action, "replaced")
            self.assertIn(
                "replacement",
                (destination / "SKILL.md").read_text(encoding="utf-8"),
            )
            self.assertFalse(backup.exists())

    def test_concurrent_skill_replacements_are_serialized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            original = write_skill(base / "original" / "peval", body="original\n")
            first = write_skill(base / "first" / "peval", body="first\n")
            second = write_skill(base / "second" / "peval", body="second\n")
            root = base / "workspace"
            init_workspace(str(root), skill_dir=str(original))
            destination = root.resolve() / ".agents" / "skills" / "peval"
            replace_path = skill_install._replace_path
            first_moved = threading.Event()
            release_first = threading.Event()
            second_swapped = threading.Event()
            results: list[str] = []
            failures: list[Exception] = []

            def coordinated_replace(current: Path, target: Path) -> None:
                thread_name = threading.current_thread().name
                if thread_name == "first-install" and current == destination:
                    replace_path(current, target)
                    first_moved.set()
                    if not release_first.wait(timeout=5):
                        raise TimeoutError("timed out waiting to release first install")
                    return
                replace_path(current, target)
                if (
                    thread_name == "second-install"
                    and target == destination
                    and current.name.startswith(".peval-skill-")
                ):
                    second_swapped.set()

            def install(source: Path) -> None:
                try:
                    result = init_workspace(str(root), skill_dir=str(source))
                    results.append(result.agent_skill.action)
                except Exception as exc:  # noqa: BLE001 - cross-thread test capture.
                    failures.append(exc)

            with patch.object(
                skill_install,
                "_replace_path",
                side_effect=coordinated_replace,
            ):
                first_thread = threading.Thread(
                    target=install,
                    args=(first,),
                    name="first-install",
                )
                second_thread = threading.Thread(
                    target=install,
                    args=(second,),
                    name="second-install",
                )
                first_thread.start()
                self.assertTrue(first_moved.wait(timeout=5))
                second_thread.start()
                second_completed_during_first_swap = second_swapped.wait(timeout=0.5)
                release_first.set()
                first_thread.join(timeout=5)
                second_thread.join(timeout=5)

            self.assertFalse(second_completed_during_first_swap)
            self.assertFalse(first_thread.is_alive())
            self.assertFalse(second_thread.is_alive())
            self.assertEqual(failures, [])
            self.assertEqual(results, ["replaced", "replaced"])
            self.assertIn(
                "second",
                (destination / "SKILL.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(list(destination.parent.glob(".*.backup")), [])

    def test_init_defaults_to_current_directory_without_installing_a_skill(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                result = init_workspace()
            finally:
                os.chdir(old_cwd)
            self.assertEqual(result.root, Path(tmp).resolve())
            self.assertTrue((Path(tmp) / "peval.toml").is_file())
            self.assertTrue((Path(tmp) / "logs").is_dir())
            self.assertFalse((Path(tmp) / ".agents").exists())
            self.assertFalse((Path(tmp) / "state.db").exists())
            self.assertFalse((Path(tmp) / "peval-py.toml").exists())

    def test_init_rejects_invalid_peval_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("peval.toml").write_text("locale = [\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "failed to parse"):
                init_workspace(str(root))

    def test_cli_init_text_and_json_cover_optional_skill_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "workspace"
            text = run_cli(["init", "--root", str(root)])
            self.assertEqual(text.returncode, 0, text.stderr)
            self.assertIn(f"peval workspace: {root.resolve()}", text.stdout)
            self.assertIn("peval config:", text.stdout)
            self.assertIn("serve log:", text.stdout)
            self.assertNotIn("Agent Skill", text.stdout)
            self.assertFalse((root / ".agents").exists())

            plain_json = run_cli(["init", "--root", str(root), "--json"])
            self.assertEqual(plain_json.returncode, 0, plain_json.stderr)
            self.assertIsNone(json.loads(plain_json.stdout)["agent_skill"])

            source = write_skill(base / "sources" / "peval")
            installed = run_cli(
                [
                    "init",
                    "--root",
                    str(root),
                    "--skill",
                    str(source),
                    "--json",
                ]
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            data = json.loads(installed.stdout)
            self.assertEqual(
                sorted(data),
                [
                    "agent_skill",
                    "log_path",
                    "peval_config",
                    "root",
                    "schema_version",
                ],
            )
            self.assertEqual(data["agent_skill"]["action"], "installed")
            self.assertEqual(
                data["agent_skill"]["path"],
                str(root.resolve() / ".agents" / "skills" / "peval"),
            )
            replaced_text = run_cli(
                ["init", "--root", str(root), "--skill", str(source)]
            )
            self.assertEqual(replaced_text.returncode, 0, replaced_text.stderr)
            self.assertIn("Agent Skill (replaced):", replaced_text.stdout)
            self.assertIn("Start a new Copilot session", replaced_text.stdout)

    def test_cli_init_rejects_repeated_skill_and_removed_default_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "workspace"
            first = write_skill(base / "first" / "first", name="first")
            second = write_skill(base / "second" / "second", name="second")
            repeated = run_cli(
                [
                    "init",
                    "--root",
                    str(root),
                    "--skill",
                    str(first),
                    "--skill",
                    str(second),
                ]
            )
            self.assertEqual(repeated.returncode, 2)
            self.assertIn("may be provided only once", repeated.stderr)
            self.assertFalse(root.exists())

            removed = run_cli(["init", "--root", str(root), "--default"])
            self.assertEqual(removed.returncode, 2)
            self.assertIn("No such option: --default", removed.stderr)


def write_skill(
    root: Path, *, name: str = "peval", body: str = "instructions\n"
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    root.joinpath("SKILL.md").write_text(
        f'---\nname: {name}\ndescription: "Test skill"\n---\n\n{body}',
        encoding="utf-8",
    )
    return root


def run_cli(
    args: list[str], *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from psycheval.cli import main; raise SystemExit(main())",
            *args,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )


if __name__ == "__main__":
    unittest.main()
