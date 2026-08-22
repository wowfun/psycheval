from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from tests.peval.test_harbor_trials import (
    atif_trajectory,
    completed_result,
    write_trial,
)


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    from psycheval.cli import main

    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        result = main(argv)
    return result, stdout.getvalue(), stderr.getvalue()


class PevalCliHarborTrialTests(unittest.TestCase):
    def test_single_step_trial_root_preserves_harbor_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trial = Path(tmp) / "jobs" / "job-a" / "trial-a"
            write_trial(trial, result=completed_result(reward=0.8))
            before = {
                path.relative_to(trial).as_posix(): path.read_bytes()
                for path in trial.rglob("*")
                if path.is_file()
            }

            result, stdout, stderr = run_cli(["view", "tr", "-p", str(trial)])
            report_path = Path(tmp) / "report.json"
            raw_result, _, raw_stderr = run_cli(
                [
                    "view",
                    "tr",
                    "-m",
                    "raw",
                    "-p",
                    str(trial),
                    "-f",
                    "json",
                    "-o",
                    str(report_path),
                ]
            )

            self.assertEqual((result, stderr), (0, ""))
            source = json.loads(stdout)["sources"][0]
            self.assertEqual(source["harbor"]["job_name"], "job-a")
            self.assertEqual(source["harbor"]["trial_name"], "trial-a")
            self.assertEqual(source["harbor"]["rewards"], {"reward": 0.8})
            self.assertEqual(source["status"], "completed")
            self.assertEqual(source["score"], 0.8)
            self.assertTrue(source["harbor"]["trajectory_available"])
            self.assertEqual((raw_result, raw_stderr), (0, ""))
            raw = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(raw["trajectory_meta"][0]["adapter"], "harbor")
            self.assertEqual(raw["trajectory_meta"][0]["rewards"], {"reward": 0.8})
            after = {
                path.relative_to(trial).as_posix(): path.read_bytes()
                for path in trial.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_direct_atif_file_remains_one_non_harbor_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trial = Path(tmp) / "jobs" / "job-a" / "trial-a"
            write_trial(trial, result=completed_result())

            result, stdout, stderr = run_cli(
                ["view", "tr", "-p", str(trial / "agent" / "trajectory.json")]
            )

            self.assertEqual((result, stderr), (0, ""))
            payload = json.loads(stdout)
            self.assertEqual(len(payload["sources"]), 1)
            self.assertNotIn("harbor", payload["sources"][0])

    def test_multi_step_descendant_is_not_promoted_to_a_trial_root(self) -> None:
        from psycheval._harbor_trials import load_direct_harbor_trial_bundle
        from psycheval.config import ToolConfig

        with tempfile.TemporaryDirectory() as tmp:
            trial = Path(tmp) / "jobs" / "job-a" / "multi"
            write_trial(trial)
            step = trial / "steps" / "first"
            write_trial(step, trajectory=atif_trajectory("first"))

            bundle = load_direct_harbor_trial_bundle(str(step), ToolConfig())

            self.assertIsNone(bundle)

    def test_invalid_harbor_trajectory_is_an_explicit_inspect_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trial = Path(tmp) / "jobs" / "job-a" / "trial-a"
            invalid = atif_trajectory()
            del invalid["agent"]["version"]
            write_trial(trial, trajectory=invalid, result=completed_result())

            result, stdout, stderr = run_cli(["view", "tr", "-p", str(trial)])

            self.assertEqual((result, stderr), (0, ""))
            source = json.loads(stdout)["sources"][0]
            self.assertFalse(source["harbor"]["trajectory_available"])
            self.assertIn("agent.version is required", source["harbor"]["diagnostic"])
            self.assertEqual(source["status"], "error")

    def test_multi_step_trial_uses_result_order_and_keeps_parent_evaluation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trial = Path(tmp) / "jobs" / "job-a" / "multi"
            write_trial(trial)
            (trial / "agent" / "trajectory.json").unlink()
            for name in ("alpha", "beta", "orphan"):
                write_trial(trial / "steps" / name, trajectory=atif_trajectory(name))
            (trial / "steps" / "beta" / "agent" / "trajectory.json").unlink()
            result_json = completed_result(reward=0.5)
            result_json["step_results"] = [
                {
                    "step_name": "beta",
                    "exception_info": {
                        "exception_type": "RuntimeError",
                        "exception_message": "step failed",
                    },
                },
                {
                    "step_name": "alpha",
                    "verifier_result": {"rewards": {"reward": 0.9}},
                },
            ]
            (trial / "result.json").write_text(
                json.dumps(result_json), encoding="utf-8"
            )

            result, stdout, stderr = run_cli(["view", "tr", "-p", str(trial)])
            raw_result, _, raw_stderr = run_cli(
                ["view", "tr", "-m", "raw", "-p", str(trial), "-f", "json"]
            )

            self.assertEqual((result, stderr), (0, ""))
            sources = json.loads(stdout)["sources"]
            self.assertEqual(
                [source["harbor"]["step"]["name"] for source in sources],
                ["beta", "alpha", "orphan"],
            )
            self.assertFalse(sources[0]["harbor"]["trajectory_available"])
            self.assertEqual(
                sources[0]["harbor"]["failure"]["exception_type"], "RuntimeError"
            )
            self.assertEqual(sources[1]["score"], 0.9)
            self.assertEqual(sources[1]["harbor"]["trial_evaluation"]["score"], 0.5)
            self.assertIn(
                "absent from result.step_results",
                sources[2]["harbor"]["warnings"][0],
            )
            self.assertEqual(raw_result, 1)
            self.assertIn("requires a trajectory for every source", raw_stderr)

    def test_multi_step_source_selector_uses_expanded_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trial = Path(tmp) / "jobs" / "job-a" / "multi"
            write_trial(trial)
            (trial / "agent" / "trajectory.json").unlink()
            first_trajectory = atif_trajectory("first")
            first_trajectory["steps"][1]["tool_calls"] = [
                {
                    "tool_call_id": "harbor-call",
                    "function_name": "search",
                    "arguments": {"query": "evidence"},
                }
            ]
            first_trajectory["steps"][1]["observation"] = {
                "results": [
                    {"source_call_id": "harbor-call", "content": "grounded result"}
                ]
            }
            write_trial(trial / "steps" / "first", trajectory=first_trajectory)
            write_trial(
                trial / "steps" / "second", trajectory=atif_trajectory("second")
            )
            result_json = completed_result()
            result_json["step_results"] = [
                {"step_name": "first"},
                {"step_name": "second"},
            ]
            (trial / "result.json").write_text(
                json.dumps(result_json), encoding="utf-8"
            )

            result, stdout, stderr = run_cli(
                ["view", "tr", "-p", str(trial), "--source", "2"]
            )
            selector_result, selector_stdout, selector_stderr = run_cli(
                [
                    "view",
                    "tr",
                    "-p",
                    str(trial),
                    "--source",
                    "1",
                    "--steps",
                    "2",
                    "--tool-call",
                    "harbor-call",
                ]
            )
            report_path = Path(tmp) / "multi.json"
            raw_result, _, raw_stderr = run_cli(
                [
                    "view",
                    "tr",
                    "-m",
                    "raw",
                    "-p",
                    str(trial),
                    "-f",
                    "json",
                    "-o",
                    str(report_path),
                ]
            )

            self.assertEqual((result, stderr), (0, ""))
            sources = json.loads(stdout)["sources"]
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0]["harbor"]["step"]["name"], "second")
            self.assertEqual((selector_result, selector_stderr), (0, ""))
            selected_source = json.loads(selector_stdout)["sources"][0]
            self.assertEqual(selected_source["selected_steps"][0]["step_id"], 2)
            self.assertEqual(
                selected_source["selected_tool_calls"][0]["tool_call_id"],
                "harbor-call",
            )
            self.assertEqual((raw_result, raw_stderr), (0, ""))
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [meta["harbor_step"]["name"] for meta in report["trajectory_meta"]],
                ["first", "second"],
            )

    def test_mixed_inputs_keep_path_order_and_original_adapter_selectors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trial = root / "jobs" / "job-a" / "multi"
            write_trial(trial)
            (trial / "agent" / "trajectory.json").unlink()
            for name in ("first", "second"):
                write_trial(trial / "steps" / name, trajectory=atif_trajectory(name))
            result_json = completed_result()
            result_json["step_results"] = [
                {"step_name": "first"},
                {"step_name": "second"},
            ]
            (trial / "result.json").write_text(
                json.dumps(result_json), encoding="utf-8"
            )
            ordinary = root / "ordinary.jsonl"
            ordinary.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "role": "user",
                                "content": "question",
                                "timestamp": 1,
                            }
                        ),
                        json.dumps(
                            {
                                "role": "assistant",
                                "content": "answer",
                                "timestamp": 2,
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            direct_atif = root / "direct.json"
            direct_atif.write_text(
                json.dumps(atif_trajectory("direct")), encoding="utf-8"
            )

            result, stdout, stderr = run_cli(
                [
                    "view",
                    "tr",
                    "-p",
                    str(trial),
                    "-p",
                    str(ordinary),
                    "-p",
                    str(direct_atif),
                    "-a",
                    "p2=opencode",
                ]
            )
            selected_result, selected_stdout, selected_stderr = run_cli(
                [
                    "view",
                    "tr",
                    "-p",
                    str(trial),
                    "-p",
                    str(ordinary),
                    "-p",
                    str(direct_atif),
                    "-a",
                    "p2=opencode",
                    "--source",
                    "3",
                ]
            )

            self.assertEqual((result, stderr), (0, ""))
            sources = json.loads(stdout)["sources"]
            self.assertEqual(
                [
                    (source.get("harbor") or {}).get("step", {}).get("name")
                    or source["session_id"]
                    for source in sources
                ],
                ["first", "second", "ordinary", "direct"],
            )
            self.assertEqual((selected_result, selected_stderr), (0, ""))
            selected = json.loads(selected_stdout)["sources"]
            self.assertEqual(
                [source["session_id"] for source in selected], ["ordinary"]
            )

    def test_symlinked_trial_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trial = root / "jobs" / "job-a" / "trial-a"
            write_trial(trial, result=completed_result())
            linked = root / "linked-trial"
            try:
                os.symlink(trial, linked, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")

            result, _, stderr = run_cli(["view", "tr", "-p", str(linked)])

            self.assertEqual(result, 1)
            self.assertIn("traverses a symlink", stderr)


if __name__ == "__main__":
    unittest.main()
