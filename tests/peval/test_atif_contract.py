from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from psycheval._state.artifacts import write_json_files_atomically
from psycheval.atif import validate_atif_trajectory
from psycheval.config import ToolConfig
from psycheval.conversion import convert_atif_trajectory, convert_records
from psycheval.report import build_report, project_meta_from_atif
from psycheval.report.metrics import automatic_analysis_metrics
from psycheval.sources import MessageRecord
from psycheval.state import open_workspace_state


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


def tool_timing_trajectory(call_extra: dict, result_extras: list[dict]) -> dict:
    trajectory = valid_trajectory()
    trajectory["steps"][0].update(
        source="agent",
        timestamp="2026-01-01T00:00:00Z",
        extra={"duration_ms": 1000},
        tool_calls=[
            {
                "tool_call_id": "call-1",
                "function_name": "read_file",
                "arguments": {},
                "extra": call_extra,
            }
        ],
        observation={
            "results": [
                {"source_call_id": "call-1", "content": "ok", "extra": extra}
                for extra in result_extras
            ]
        },
    )
    return trajectory


class PevalAtifContractTests(unittest.TestCase):
    def test_workbuddy_usage_coverage_is_a_read_only_diagnostic(self) -> None:
        trajectory = valid_trajectory()
        trajectory["extra"] = {
            "workbuddy_usage": {
                "status": "partial",
                "expected_requests": 21,
                "coverage": {
                    "prompt_tokens": 19,
                    "completion_tokens": 19,
                    "cached_tokens": 19,
                },
            }
        }
        before = deepcopy(trajectory)
        projected = project_meta_from_atif(
            trajectory,
            {"warnings": ["retained diagnostic"], "conversion_status": "passed"},
        )
        self.assertEqual(projected["conversion_status"], "passed")
        self.assertEqual(projected["warnings"][0], "retained diagnostic")
        self.assertIn("19/21", projected["warnings"][1])
        self.assertEqual(
            project_meta_from_atif(trajectory, projected)["warnings"],
            projected["warnings"],
        )
        self.assertEqual(trajectory, before)
        trajectory["extra"]["workbuddy_usage"]["status"] = "complete"
        self.assertNotIn("warnings", project_meta_from_atif(trajectory, {}))

    def test_partial_cache_coverage_does_not_hide_verified_input_output_totals(self):
        trajectory = valid_trajectory()
        trajectory["final_metrics"] = {
            "total_prompt_tokens": 100,
            "total_completion_tokens": 5,
        }
        trajectory["extra"] = {
            "workbuddy_usage": {
                "status": "partial",
                "expected_requests": 1,
                "coverage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "cached_tokens": 0,
                },
            }
        }
        before = deepcopy(trajectory)
        projected = project_meta_from_atif(trajectory, {})
        self.assertIn("1/1, 1/1, 0/1", projected["warnings"][0])
        self.assertIn(
            "Unverified token fields remain unknown.", projected["warnings"][0]
        )
        self.assertEqual(trajectory, before)

    def test_generation_duration_validates_canonical_and_sidecar_measurements(self):
        for value in (
            True,
            False,
            -1,
            "25",
            2.5,
            2.0,
            float("inf"),
            float("nan"),
            [],
            {},
            None,
            0,
            25,
        ):
            for canonical in (True, False):
                with self.subTest(value=value, canonical=canonical):
                    trajectory = tool_timing_trajectory(
                        {"generation_duration_ms": value} if canonical else {}, [{}]
                    )
                    prior = {
                        "steps": [
                            {
                                "step_id": 1,
                                "tool_calls": [
                                    {
                                        "tool_call_id": "call-1",
                                        "generation_duration_ms": value,
                                    }
                                ],
                            }
                        ]
                    }
                    tool = project_meta_from_atif(trajectory, prior)["steps"][0][
                        "tool_calls"
                    ][0]
                    expected = value if type(value) is int and value >= 0 else None
                    self.assertEqual(tool.get("generation_duration_ms"), expected)

    def test_projected_durations_reject_coercion_and_nonfinite_values(self):
        for value in (float("inf"), float("nan"), "420", 42.7, -1, True):
            with self.subTest(value=value):
                trajectory = tool_timing_trajectory({}, [{}])
                trajectory["steps"][0]["extra"]["duration_ms"] = value
                projected = project_meta_from_atif(
                    trajectory,
                    {
                        "import_context": {"source_timing": {"duration_ms": value}},
                    },
                )
                self.assertIsNone(projected["duration_ms"])
                self.assertIsNone(projected["steps"][0]["duration_ms"])

    def test_tool_execution_timing_ignores_invalid_measurements(self) -> None:
        invalid_values = [
            "bad-string",
            "420",
            42.7,
            42.0,
            -5,
            True,
            False,
            [],
            {},
            float("inf"),
            float("nan"),
        ]
        for value in invalid_values:
            with self.subTest(value=value):
                call_extra = {
                    "execution_duration_ms": 420,
                    "execution_duration_source": "call",
                }
                trajectory = tool_timing_trajectory(
                    call_extra, [{"execution_duration_ms": value}]
                )
                meta = project_meta_from_atif(trajectory, {})
                tool = meta["steps"][0]["tool_calls"][0]
                self.assertEqual(tool["execution_duration_ms"], 420)
                self.assertEqual(tool["execution_duration_source"], "call")
                self.assertEqual(meta["duration_ms"], 1420)

                trajectory = tool_timing_trajectory(
                    {"execution_duration_ms": value}, [{}]
                )
                meta = project_meta_from_atif(trajectory, {})
                self.assertNotIn(
                    "execution_duration_ms", meta["steps"][0]["tool_calls"][0]
                )
                self.assertEqual(meta["duration_ms"], 1000)

                trajectory = tool_timing_trajectory({}, [{}])
                prior = {
                    "steps": [
                        {
                            "step_id": 1,
                            "tool_calls": [
                                {
                                    "tool_call_id": "call-1",
                                    "execution_duration_ms": value,
                                    "execution_duration_source": "old-sidecar",
                                }
                            ],
                        }
                    ]
                }
                meta = project_meta_from_atif(trajectory, prior)
                self.assertNotIn(
                    "execution_duration_ms", meta["steps"][0]["tool_calls"][0]
                )
                self.assertNotIn(
                    "execution_duration_source", meta["steps"][0]["tool_calls"][0]
                )
                self.assertEqual(meta["duration_ms"], 1000)

        for source in (123, True, [], {}, None, "", "   "):
            with self.subTest(source=source):
                trajectory = tool_timing_trajectory(
                    {},
                    [
                        {
                            "execution_duration_ms": 420,
                            "execution_duration_source": source,
                        }
                    ],
                )
                tool = project_meta_from_atif(trajectory, {})["steps"][0]["tool_calls"][
                    0
                ]
                self.assertEqual(tool["execution_duration_ms"], 420)
                self.assertNotIn("execution_duration_source", tool)

    def test_multiple_results_project_only_unambiguous_tool_timing(self) -> None:
        cases = [
            (
                [{"execution_duration_ms": 10}, {"execution_duration_ms": 20}],
                None,
                None,
            ),
            (
                [{"execution_duration_ms": None}, {"execution_duration_ms": 20}],
                None,
                None,
            ),
            ([{"execution_duration_ms": None}, {}], None, None),
            (
                [
                    {
                        "execution_duration_ms": 20,
                        "execution_duration_source": "result",
                    },
                    {
                        "execution_duration_ms": 20,
                        "execution_duration_source": "result",
                    },
                ],
                20,
                "result",
            ),
            (
                [
                    {"execution_duration_ms": 20, "execution_duration_source": "a"},
                    {"execution_duration_ms": 20, "execution_duration_source": "b"},
                ],
                20,
                None,
            ),
            (
                [
                    {"execution_duration_ms": 20, "execution_duration_source": "a"},
                    {"execution_duration_ms": 20},
                ],
                20,
                None,
            ),
            (
                [
                    {},
                    {
                        "execution_duration_ms": 20,
                        "execution_duration_source": "result",
                    },
                ],
                20,
                "result",
            ),
            (
                [
                    {"execution_duration_ms": "bad-string"},
                    {"execution_duration_ms": 20},
                ],
                20,
                None,
            ),
            ([{}, {"execution_duration_ms": "bad-string"}], 420, "call"),
        ]
        for extras, duration, source in cases:
            with self.subTest(extras=extras):
                for ordered in (extras, list(reversed(extras))):
                    trajectory = tool_timing_trajectory(
                        {
                            "execution_duration_ms": 420,
                            "execution_duration_source": "call",
                        },
                        ordered,
                    )
                    original = deepcopy(trajectory)
                    validate_atif_trajectory(trajectory)
                    meta = project_meta_from_atif(trajectory, {})
                    tool = meta["steps"][0]["tool_calls"][0]
                    self.assertEqual(tool.get("execution_duration_ms"), duration)
                    self.assertEqual(tool.get("execution_duration_source"), source)
                    if duration is None:
                        self.assertNotIn("execution_duration_ms", tool)
                    self.assertEqual(meta["duration_ms"], 1000 + (duration or 0))
                    self.assertEqual(len(meta["steps"][0]["observations"]), 2)
                    self.assertEqual(trajectory, original)

    def test_tool_execution_timing_selects_one_canonical_location(self) -> None:
        cases = [
            (
                {"execution_duration_ms": 420, "execution_duration_source": "call"},
                {},
                420,
                "call",
            ),
            (
                {},
                {"execution_duration_ms": 99, "execution_duration_source": "result"},
                99,
                "result",
            ),
            (
                {"execution_duration_ms": 420, "execution_duration_source": "call"},
                {"execution_duration_ms": 99, "execution_duration_source": "result"},
                99,
                "result",
            ),
            (
                {"execution_duration_ms": 420, "execution_duration_source": "call"},
                {"execution_duration_ms": None},
                None,
                None,
            ),
            (
                {"execution_duration_ms": 420, "execution_duration_source": "call"},
                {"execution_duration_ms": 0},
                0,
                None,
            ),
            ({"execution_duration_ms": 0}, {}, 0, None),
            (
                {"execution_duration_ms": 420},
                {"execution_duration_source": "result"},
                420,
                None,
            ),
            (
                {"execution_duration_ms": 420, "execution_duration_source": "call"},
                {"execution_duration_ms": 99},
                99,
                None,
            ),
            ({"execution_duration_source": "call"}, {}, None, None),
            ({}, {}, None, None),
        ]
        for call_extra, result_extra, duration, source in cases:
            with self.subTest(call=call_extra, result=result_extra):
                trajectory = valid_trajectory()
                trajectory["steps"][0].update(
                    source="agent",
                    timestamp="2026-01-01T00:00:00Z",
                    extra={"duration_ms": 1000},
                    tool_calls=[
                        {
                            "tool_call_id": "call-1",
                            "function_name": "read_file",
                            "arguments": {},
                            "extra": {"generation_duration_ms": 1000, **call_extra},
                        }
                    ],
                    observation={
                        "results": [
                            {
                                "source_call_id": "call-1",
                                "content": "ok",
                                "extra": result_extra,
                            }
                        ]
                    },
                )
                original = deepcopy(trajectory)
                report = build_report(
                    convert_atif_trajectory(trajectory),
                    ToolConfig(adapter="atif", redact=False),
                    "inline",
                )
                for meta in (
                    report["trajectory_meta"][0],
                    project_meta_from_atif(trajectory, {}),
                ):
                    tool = meta["steps"][0]["tool_calls"][0]
                    self.assertEqual(tool.get("execution_duration_ms"), duration)
                    if duration is None:
                        self.assertNotIn("execution_duration_ms", tool)
                    self.assertEqual(tool.get("execution_duration_source"), source)
                    if source is None:
                        self.assertNotIn("execution_duration_source", tool)
                    self.assertEqual(tool["generation_duration_ms"], 1000)
                    self.assertEqual(meta["steps"][0]["duration_ms"], 1000)
                    self.assertEqual(meta["duration_ms"], 1000 + (duration or 0))
                    latency = automatic_analysis_metrics(trajectory, meta).get(
                        "latency", {}
                    )
                    self.assertEqual(
                        latency.get("tool_execution_duration_ms", {}).get("max"),
                        duration,
                    )
                self.assertEqual(trajectory, original)

    def test_canonical_tool_duration_replaces_stale_sidecar_provenance(self) -> None:
        trajectory = valid_trajectory()
        trajectory["steps"][0].update(
            source="agent",
            extra={"duration_ms": 1000},
            tool_calls=[
                {
                    "tool_call_id": "call-1",
                    "function_name": "read_file",
                    "arguments": {},
                }
            ],
            observation={"results": [{"source_call_id": "call-1", "content": "ok"}]},
        )
        prior = {
            "steps": [
                {
                    "step_id": 1,
                    "tool_calls": [
                        {
                            "tool_call_id": "call-1",
                            "execution_duration_ms": 900,
                            "execution_duration_source": "old-sidecar",
                        }
                    ],
                }
            ]
        }
        for location in (
            trajectory["steps"][0]["tool_calls"][0],
            trajectory["steps"][0]["observation"]["results"][0],
        ):
            for extra in (
                {"execution_duration_ms": 420},
                {"execution_duration_ms": None},
                {"execution_duration_ms": 0, "execution_duration_source": None},
            ):
                with self.subTest(extra=extra):
                    location["extra"] = extra
                    projected = project_meta_from_atif(trajectory, prior)
                    tool = projected["steps"][0]["tool_calls"][0]
                    self.assertEqual(
                        tool.get("execution_duration_ms"),
                        extra["execution_duration_ms"],
                    )
                    if extra["execution_duration_ms"] is None:
                        self.assertNotIn("execution_duration_ms", tool)
                    self.assertNotIn("execution_duration_source", tool)
            location.pop("extra")
        projected = project_meta_from_atif(trajectory, prior)
        self.assertEqual(
            projected["steps"][0]["tool_calls"][0]["execution_duration_ms"], 900
        )
        self.assertEqual(
            projected["steps"][0]["tool_calls"][0]["execution_duration_source"],
            "old-sidecar",
        )

    def test_tool_execution_timing_matches_results_by_call_identity(self) -> None:
        trajectory = valid_trajectory()
        trajectory["steps"][0].update(
            source="agent",
            extra={"duration_ms": 1000},
            tool_calls=[
                {
                    "tool_call_id": f"call-{index}",
                    "function_name": "read_file",
                    "arguments": {},
                    "extra": {
                        "execution_duration_ms": index * 100,
                        "execution_duration_source": "call",
                    },
                }
                for index in (1, 2)
            ],
            observation={
                "results": [
                    {
                        "source_call_id": "call-2",
                        "content": "second",
                        "extra": {
                            "execution_duration_ms": 42,
                            "execution_duration_source": "result",
                        },
                    },
                    {"source_call_id": "call-1", "content": "first"},
                ]
            },
        )
        projected = project_meta_from_atif(trajectory, {})
        self.assertEqual(
            [
                (tool["execution_duration_ms"], tool["execution_duration_source"])
                for tool in projected["steps"][0]["tool_calls"]
            ],
            [(100, "call"), (42, "result")],
        )
        self.assertEqual(projected["duration_ms"], 1142)

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
