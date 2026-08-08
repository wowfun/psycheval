from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from peval_py._state.artifacts import write_json_files_atomically
from peval_py.atif import convert_records, validate_atif_trajectory
from peval_py.config import ToolConfig
from peval_py.report import build_report, project_meta_from_atif
from peval_py.sources import MessageRecord
from peval_py.state import open_workspace_state


def valid_trajectory() -> dict:
    return {
        "schema_version": "ATIF-v1.7",
        "trajectory_id": "agent:session",
        "session_id": "session",
        "agent": {"name": "agent", "version": "1.0"},
        "steps": [
            {
                "step_id": 1,
                "source": "user",
                "message": "hello",
            }
        ],
        "final_metrics": {"total_steps": 1},
    }


class PevalPyAtifContractTests(unittest.TestCase):
    def test_validator_rejects_required_order_type_and_unknown_field_errors(
        self,
    ) -> None:
        cases = []

        missing_version = valid_trajectory()
        missing_version["agent"].pop("version")
        cases.append((missing_version, r"trajectory\.agent\.version is required"))

        empty_steps = valid_trajectory()
        empty_steps["steps"] = []
        cases.append((empty_steps, r"trajectory\.steps must contain at least one"))

        unordered = valid_trajectory()
        unordered["steps"][0]["step_id"] = 2
        cases.append((unordered, r"trajectory\.steps\[0\]\.step_id must be 1"))

        wrong_type = valid_trajectory()
        wrong_type["steps"][0]["step_id"] = "1"
        cases.append(
            (wrong_type, r"trajectory\.steps\[0\]\.step_id must be an integer")
        )

        unknown = valid_trajectory()
        unknown["steps"][0]["duration_ms"] = 1
        cases.append((unknown, r"trajectory\.steps\[0\].*duration_ms"))

        for trajectory, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    validate_atif_trajectory(trajectory)

    def test_validator_rejects_invalid_content_and_tool_reference(self) -> None:
        invalid_content = valid_trajectory()
        invalid_content["steps"][0]["message"] = [
            {"type": "image", "source": {"media_type": "image/tiff", "path": "a.tiff"}}
        ]
        with self.assertRaisesRegex(
            ValueError,
            r"trajectory\.steps\[0\]\.message\[0\]\.source\.media_type",
        ):
            validate_atif_trajectory(invalid_content)

        dangling = valid_trajectory()
        dangling["steps"][0] = {
            "step_id": 1,
            "source": "agent",
            "message": "",
            "llm_call_count": 0,
            "observation": {
                "results": [{"source_call_id": "missing", "content": "no call"}]
            },
        }
        with self.assertRaisesRegex(
            ValueError,
            r"trajectory\.steps\[0\]\.observation\.results\[0\]\.source_call_id",
        ):
            validate_atif_trajectory(dangling)

    def test_validator_accepts_explicit_null_for_unused_content_members(self) -> None:
        trajectory = valid_trajectory()
        trajectory["steps"][0]["message"] = [
            {"type": "text", "text": "caption", "source": None},
            {
                "type": "image",
                "text": None,
                "source": {"media_type": "image/png", "path": "screen.png"},
            },
        ]

        validate_atif_trajectory(trajectory)

    def test_validator_rejects_duplicate_and_dangling_embedded_subagents(self) -> None:
        trajectory = valid_trajectory()
        child = valid_trajectory()
        child["trajectory_id"] = "child:1"
        trajectory["subagent_trajectories"] = [deepcopy(child), deepcopy(child)]
        with self.assertRaisesRegex(
            ValueError,
            r"trajectory\.subagent_trajectories\[1\]\.trajectory_id must be unique",
        ):
            validate_atif_trajectory(trajectory)

        trajectory["subagent_trajectories"] = [child]
        trajectory["steps"][0] = {
            "step_id": 1,
            "source": "agent",
            "message": "",
            "llm_call_count": 0,
            "observation": {
                "results": [
                    {"subagent_trajectory_ref": [{"trajectory_id": "child:missing"}]}
                ]
            },
        }
        with self.assertRaisesRegex(ValueError, r"trajectory_id does not reference"):
            validate_atif_trajectory(trajectory)

    def test_finalizer_normalizes_content_metrics_and_runtime_facts(self) -> None:
        records = [
            MessageRecord(
                message={"role": "user", "content": "go", "timestamp_ms": 1_000},
                source_session_id="stable",
            ),
            MessageRecord(
                message={
                    "role": "assistant",
                    "content": "",
                    "timestamp_ms": 2_000,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "name": "inspect",
                            "arguments": {"path": "a.txt"},
                            "started_at_ms": 2_100,
                            "generation_duration_ms": 25,
                        }
                    ],
                },
                usage={
                    "input_tokens": 100,
                    "cache_read_tokens": 20,
                    "cache_write_tokens": 5,
                    "output_tokens": 2,
                },
                accounting={
                    "context_input_tokens": 100,
                    "billable_input_tokens": 75,
                    "cache_read_tokens": 20,
                    "cache_write_tokens": 5,
                },
                source_session_id="stable",
            ),
            MessageRecord(
                message={
                    "role": "tool",
                    "tool_call_id": "call-1",
                    "result": {"z": 1, "a": [2, 3]},
                    "timestamp_ms": 2_300,
                },
                source_session_id="stable",
            ),
        ]
        conversion = convert_records(
            records, ToolConfig(adapter="psychevo", redact=False)
        )
        trajectory = conversion.trajectory
        assistant = trajectory["steps"][1]
        result = assistant["observation"]["results"][0]

        self.assertEqual(trajectory["trajectory_id"], "psychevo:stable")
        self.assertEqual(assistant["llm_call_count"], 1)
        self.assertEqual(assistant["metrics"]["prompt_tokens"], 100)
        self.assertEqual(assistant["metrics"]["cached_tokens"], 20)
        self.assertEqual(
            assistant["metrics"]["extra"]["usage"]["cache_write_tokens"], 5
        )
        self.assertEqual(trajectory["final_metrics"]["total_prompt_tokens"], 100)
        self.assertEqual(trajectory["final_metrics"]["total_cached_tokens"], 20)
        self.assertEqual(result["content"], '{"a":[2,3],"z":1}')
        self.assertEqual(result["extra"]["status"], "completed")
        self.assertFalse(result["extra"]["is_error"])
        self.assertTrue(assistant["timestamp"].endswith("Z"))
        self.assertTrue(assistant["tool_calls"][0]["extra"]["started_at"].endswith("Z"))
        self.assertEqual(
            assistant["tool_calls"][0]["extra"]["generation_duration_ms"], 25
        )
        validate_atif_trajectory(trajectory)

        report = build_report(
            conversion, ToolConfig(adapter="psychevo", redact=False), "inline"
        )
        sidecar = report["trajectory_meta"][0]
        self.assertEqual(sidecar["steps"][1]["timestamp_ms"], 2_000)
        self.assertEqual(
            sidecar["steps"][1]["observations"][0]["status"],
            result["extra"]["status"],
        )

    def test_finalizer_keeps_valid_multimodal_results_and_serializes_invalid_lists(
        self,
    ) -> None:
        valid_parts = [
            {"type": "text", "text": "screen"},
            {
                "type": "image",
                "source": {"media_type": "image/png", "path": "images/screen.png"},
            },
        ]
        for content, expected_type in ((valid_parts, list), (["not", "parts"], str)):
            with self.subTest(content=content):
                conversion = convert_records(
                    [
                        MessageRecord(
                            message={
                                "role": "tool_result",
                                "content": content,
                                "timestamp_ms": 1_000,
                            }
                        )
                    ],
                    ToolConfig(adapter="psychevo", redact=False),
                )
                stored = conversion.trajectory["steps"][0]["observation"]["results"][0][
                    "content"
                ]
                self.assertIsInstance(stored, expected_type)

    def test_finalizer_keeps_orphan_observation_sidecar_aligned(self) -> None:
        conversion = convert_records(
            [
                MessageRecord(
                    message={
                        "role": "tool",
                        "tool_call_id": "missing-call",
                        "result": "failed",
                        "timestamp_ms": 2_300,
                    },
                    source_session_id="stable",
                )
            ],
            ToolConfig(adapter="psychevo", redact=False),
        )
        result = conversion.trajectory["steps"][0]["observation"]["results"][0]
        self.assertNotIn("source_call_id", result)
        self.assertEqual(result["extra"]["unmatched_source_call_id"], "missing-call")
        self.assertIsNone(conversion.steps_meta[0].observations[0].source_call_id)

        report = build_report(
            conversion, ToolConfig(adapter="psychevo", redact=False), "inline"
        )
        observation_meta = report["trajectory_meta"][0]["steps"][0]["observations"][0]
        self.assertNotIn("source_call_id", observation_meta)
        self.assertEqual(observation_meta["status"], "completed")
        self.assertEqual(observation_meta["timestamp_ms"], 2_300)

    def test_sidecar_projection_rebuilds_nested_identity_before_merging(self) -> None:
        trajectory = valid_trajectory()
        trajectory["steps"][0] = {
            "step_id": 1,
            "source": "agent",
            "message": "done",
            "llm_call_count": 0,
            "tool_calls": [
                {
                    "tool_call_id": "canonical-call",
                    "function_name": "search",
                    "arguments": {"query": "ATIF"},
                }
            ],
            "observation": {
                "results": [
                    {
                        "source_call_id": "canonical-call",
                        "content": "done",
                        "extra": {"status": "completed", "is_error": False},
                    }
                ]
            },
        }
        stale_meta = {
            "trial_key": "session",
            "duration_ms": 900,
            "steps": [
                {
                    "step_id": 1,
                    "duration_ms": None,
                    "tool_calls": [
                        {
                            "tool_call_id": "stale-call",
                            "status": "failed",
                            "execution_duration_ms": 900,
                        }
                    ],
                    "observations": [
                        {
                            "source_call_id": "stale-call",
                            "status": "failed",
                            "tool_error": True,
                        }
                    ],
                }
            ],
        }

        projected = project_meta_from_atif(trajectory, stale_meta)

        self.assertEqual(
            projected["steps"][0]["tool_calls"][0]["tool_call_id"],
            "canonical-call",
        )
        self.assertNotIn(
            "execution_duration_ms", projected["steps"][0]["tool_calls"][0]
        )
        self.assertEqual(
            projected["steps"][0]["observations"][0]["source_call_id"],
            "canonical-call",
        )
        self.assertEqual(
            projected["steps"][0]["observations"][0]["status"], "completed"
        )
        self.assertIsNone(projected.get("duration_ms"))

    def test_cached_subset_invariants_are_strict(self) -> None:
        trajectory = valid_trajectory()
        trajectory["steps"][0] = {
            "step_id": 1,
            "source": "agent",
            "message": "done",
            "llm_call_count": 1,
            "metrics": {"prompt_tokens": 2, "cached_tokens": 3},
        }
        trajectory["final_metrics"] = {
            "total_prompt_tokens": 2,
            "total_cached_tokens": 3,
        }
        with self.assertRaisesRegex(ValueError, r"cached_tokens must not exceed"):
            validate_atif_trajectory(trajectory)

    def test_prompt_tokens_rebuild_only_when_inclusive_total_is_missing(self) -> None:
        conversion = convert_records(
            [
                MessageRecord(
                    message={"role": "assistant", "content": "done"},
                    accounting={
                        "billable_input_tokens": 75,
                        "billable_output_tokens": 2,
                        "cache_read_tokens": 20,
                        "cache_write_tokens": 5,
                    },
                )
            ],
            ToolConfig(adapter="psychevo", redact=False),
        )
        metrics = conversion.trajectory["steps"][0]["metrics"]
        self.assertEqual(metrics["prompt_tokens"], 100)
        self.assertEqual(metrics["cached_tokens"], 20)
        self.assertEqual(
            conversion.trajectory["final_metrics"]["total_prompt_tokens"], 100
        )

    def test_tool_argument_and_result_truncation_are_canonical_facts(self) -> None:
        conversion = convert_records(
            [
                MessageRecord(
                    message={
                        "role": "assistant",
                        "content": "",
                        "timestamp_ms": 1_000,
                        "tool_calls": [
                            {
                                "id": "large-call",
                                "name": "write",
                                "arguments": {"content": "x" * 80},
                            }
                        ],
                    }
                ),
                MessageRecord(
                    message={
                        "role": "tool_result",
                        "tool_call_id": "large-call",
                        "content": {"result": "y" * 80},
                        "timestamp_ms": 1_100,
                    }
                ),
            ],
            ToolConfig(
                adapter="psychevo",
                redact=False,
                max_content_chars=24,
                max_content_chars_explicit=True,
            ),
        )
        step = conversion.trajectory["steps"][0]
        call = step["tool_calls"][0]
        result = step["observation"]["results"][0]
        self.assertTrue(call["extra"]["arguments_truncated"])
        self.assertIn("_peval_truncated_json", call["arguments"])
        self.assertTrue(result["extra"]["truncated"])
        self.assertIsInstance(result["content"], str)
        validate_atif_trajectory(conversion.trajectory)

    def test_invalid_trial_and_report_snapshot_leave_no_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            store = open_workspace_state(str(root))
            try:
                invalid = valid_trajectory()
                invalid["agent"].pop("version")
                source = {
                    "kind": "snapshot",
                    "adapter": "atif",
                    "label": "invalid",
                    "session_id": "session",
                }
                with self.assertRaisesRegex(ValueError, r"agent\.version"):
                    store.store_trial(
                        invalid,
                        {"trial_key": "invalid", "steps": []},
                        "default",
                        source=source,
                    )
                self.assertEqual(list(root.rglob("trajectory.json")), [])

                report = {
                    "trajectory": [valid_trajectory(), invalid],
                    "trajectory_meta": [
                        {"trial_key": "valid", "steps": [{}]},
                        {"trial_key": "invalid", "steps": [{}]},
                    ],
                }
                with self.assertRaisesRegex(
                    ValueError, r"report\.trajectory\[1\].*version"
                ):
                    store.ingest_report_snapshot(report, "report.json", ToolConfig())
                self.assertEqual(list(root.rglob("trajectory.json")), [])
            finally:
                store.close()

    def test_trajectory_and_sidecar_write_rolls_back_on_second_replace_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trajectory_path = root / "trajectory.json"
            meta_path = root / "trajectory_meta.json"
            trajectory_path.write_text('{"old":"trajectory"}\n', encoding="utf-8")
            meta_path.write_text('{"old":"meta"}\n', encoding="utf-8")
            original_replace = Path.replace

            def fail_meta_replace(path: Path, target: Path) -> Path:
                if Path(target) == meta_path and path.name.endswith(".tmp"):
                    raise OSError("simulated sidecar replace failure")
                return original_replace(path, target)

            with patch.object(Path, "replace", fail_meta_replace):
                with self.assertRaisesRegex(OSError, "simulated"):
                    write_json_files_atomically(
                        [
                            (trajectory_path, {"new": "trajectory"}),
                            (meta_path, {"new": "meta"}),
                        ]
                    )

            self.assertEqual(
                json.loads(trajectory_path.read_text(encoding="utf-8")),
                {"old": "trajectory"},
            )
            self.assertEqual(
                json.loads(meta_path.read_text(encoding="utf-8")),
                {"old": "meta"},
            )
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_invalid_existing_artifact_is_reported_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            store = open_workspace_state(str(root))
            try:
                cell = root / "runs/default/agent/session/cell"
                agent_dir = cell / "agent"
                agent_dir.mkdir(parents=True)
                invalid = valid_trajectory()
                invalid["steps"] = []
                trajectory_path = agent_dir / "trajectory.json"
                original = json.dumps(invalid)
                trajectory_path.write_text(original, encoding="utf-8")
                (agent_dir / "trajectory_meta.json").write_text(
                    json.dumps({"trial_key": "cell", "steps": []}),
                    encoding="utf-8",
                )

                rows = store.source_rows(active_only=False)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["last_status"], "error")
                self.assertIn("Invalid ATIF artifact", rows[0]["last_error"])
                self.assertEqual(trajectory_path.read_text(encoding="utf-8"), original)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
