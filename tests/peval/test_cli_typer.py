from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from typer.main import get_command
from typer.testing import CliRunner

from psycheval.cli import app


class PevalTyperCliTests(unittest.TestCase):
    def test_command_tree_completion_options_and_aliases_are_structured(self) -> None:
        root = get_command(app)
        self.assertEqual(
            set(root.commands),
            {"init", "view", "export", "import", "publish", "serve"},
        )
        root_options = {
            option
            for parameter in root.params
            for option in getattr(parameter, "opts", ())
        }
        self.assertIn("--install-completion", root_options)
        self.assertIn("--show-completion", root_options)

        view = root.commands["view"]
        self.assertEqual(set(view.commands), {"trajectory", "tr"})
        self.assertFalse(view.commands["trajectory"].hidden)
        self.assertTrue(view.commands["tr"].hidden)
        self.assertEqual(
            set(root.commands["publish"].commands),
            {"evaluation-report"},
        )
        view_options = {
            option
            for parameter in view.commands["trajectory"].params
            for option in getattr(parameter, "opts", ())
        }
        self.assertIn("--no-redact", view_options)
        self.assertNotIn("--no-no-redact", view_options)

    def test_help_and_usage_errors_are_plain_text(self) -> None:
        runner = CliRunner()
        for arguments in (
            ["--help"],
            ["view", "--help"],
            ["view", "trajectory", "--help"],
            ["view", "tr", "--help"],
            ["view", "tr", "--unknown"],
        ):
            with self.subTest(arguments=arguments):
                result = runner.invoke(app, arguments, color=True)
                self.assertNotIn("\x1b[", result.output)
                self.assertNotRegex(result.output, "[╭╰│]")
        self.assertEqual(runner.invoke(app, ["--help"]).exit_code, 0)
        self.assertEqual(runner.invoke(app, ["view", "tr", "--unknown"]).exit_code, 2)

        import_help = runner.invoke(app, ["import", "analysis", "--help"])
        self.assertEqual(import_help.exit_code, 0)
        self.assertIn("runs/<evaluation>/<agent>/<session>/<cell>", import_help.output)
        self.assertNotIn("harbor/<mount-id>", import_help.output)

    def test_show_completion_does_not_install_shell_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": tmp,
                    "SHELL": "/bin/bash",
                    "_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION": "1",
                    "XDG_CONFIG_HOME": str(Path(tmp) / "config"),
                }
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "psycheval.cli",
                    "--show-completion",
                    "bash",
                ],
                check=False,
                text=True,
                capture_output=True,
                env=environment,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=f"stdout={result.stdout!r}\nstderr={result.stderr!r}",
            )
            self.assertEqual(result.stderr, "")
            self.assertIn("_PEVAL_COMPLETE", result.stdout)
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
