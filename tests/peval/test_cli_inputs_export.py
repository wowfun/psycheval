from __future__ import annotations

from tests.peval.cli_inputs_support import (
    FIXTURES,
    Path,
    contextlib,
    create_messages_db,
    io,
    json,
    shutil,
    subprocess,
    sys,
    tempfile,
    unittest,
)


class PevalCliInputsExportTests(unittest.TestCase):
    def test_cli_source_aliases_are_display_only(self) -> None:
        from psycheval.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = root / "common_session.jsonl"
            shutil.copy(FIXTURES / "common_session.jsonl", source_path)
            db_path = root / "state.db"
            create_messages_db(db_path)
            out_path = root / "aliases.json"
            base_args = [
                "view",
                "tr",
                "-m",
                "raw",
                "-a",
                "p1=opencode",
                "-a",
                "d1=psychevo",
                "-p",
                str(source_path),
                "-d",
                str(db_path),
                "-s",
                "d1=db-a",
            ]
            result = main(
                [
                    *base_args,
                    "--source-alias",
                    "1=CLI path alias",
                    "--source-alias",
                    "2=CLI DB alias",
                    "-o",
                    str(out_path),
                ]
            )
            self.assertEqual(result, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [item.get("source_alias") for item in payload["trajectory_meta"]],
                ["CLI path alias", "CLI DB alias"],
            )
            self.assertEqual(
                [item["session_id"] for item in payload["trajectory"]],
                ["common_session", "db-a"],
            )
            self.assertNotIn("comparison", payload)

            for aliases, message in [
                (["2=first", "2=duplicate"], "duplicate --source-alias index: 2"),
                (["3=missing"], "out of range for 2 sessions"),
                (["1="], "text must not be empty"),
            ]:
                with self.subTest(aliases=aliases):
                    stderr = io.StringIO()
                    alias_args = [
                        value
                        for alias in aliases
                        for value in ("--source-alias", alias)
                    ]
                    with contextlib.redirect_stderr(stderr):
                        result = main([*base_args, *alias_args])
                    self.assertNotEqual(result, 0)
                    self.assertIn(message, stderr.getvalue())

    def test_cli_multi_path_rules_and_export_single_session_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "multi.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "psycheval.cli",
                    "view",
                    "tr",
                    "-m",
                    "raw",
                    "-a",
                    "opencode",
                    "-p",
                    str(FIXTURES / "common_session.jsonl"),
                    "-p",
                    str(FIXTURES / "psychevo_session.jsonl"),
                    "-n",
                    "1=First session note",
                    "-o",
                    str(out_path),
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.stderr, "")
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["trajectory"]), 2)
            self.assertNotIn("comparison", payload)

            export_multi = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "psycheval.cli",
                    "export",
                    "tr",
                    "-p",
                    str(FIXTURES / "common_session.jsonl"),
                    "-p",
                    str(FIXTURES / "psychevo_session.jsonl"),
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(export_multi.returncode, 0)
            self.assertIn("exactly one input session", export_multi.stderr)

    def test_cli_help_and_parser_reject_input_table(self) -> None:
        command = shutil.which("peval") or "peval"
        for verb in ["view", "export"]:
            result = subprocess.run(
                [command, verb, "trajectory", "--help"],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertNotIn("--input-table", result.stdout)
            self.assertNotIn("-i,", result.stdout)
            if verb == "view":
                self.assertNotIn("--format", result.stdout)

        serve_help = subprocess.run(
            [command, "serve", "--help"],
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(serve_help.returncode, 0)
        self.assertNotIn("--input-table", serve_help.stdout)

        rejected = subprocess.run(
            [command, "view", "trajectory", "--input-table", "inputs.csv"],
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("no such option", rejected.stderr.lower())


if __name__ == "__main__":
    unittest.main()
