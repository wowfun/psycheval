from __future__ import annotations

import unittest

from peval_py.report.inference import (
    aggregate_inference_rows,
    inference_row_metrics,
)


class InferenceMetricsTests(unittest.TestCase):
    def test_derives_trial_values_from_sufficient_statistics(self) -> None:
        metrics = inference_row_metrics(
            {
                "extra": {
                    "model_inference": {
                        "ttft_ms_sum": 600,
                        "ttft_sample_count": 3,
                        "decode_duration_ms": 2_000,
                        "decode_token_count": 100,
                        "decode_sample_count": 3,
                        "cache_prompt_tokens": 500,
                        "cache_read_tokens": 125,
                        "cache_sample_count": 3,
                    }
                }
            }
        )

        self.assertEqual(metrics["ttft_ms"], 200)
        self.assertEqual(metrics["tps"], 50)
        self.assertEqual(metrics["cache_hit_rate"], 0.25)

    def test_aggregates_ratios_of_sums_and_reports_coverage(self) -> None:
        summary = aggregate_inference_rows(
            [
                {
                    "ttft_ms_sum": 100,
                    "ttft_sample_count": 1,
                    "decode_duration_ms": 100,
                    "decode_token_count": 10,
                    "decode_sample_count": 1,
                    "cache_prompt_tokens": 100,
                    "cache_read_tokens": 90,
                    "cache_sample_count": 1,
                },
                {
                    "ttft_ms_sum": 900,
                    "ttft_sample_count": 9,
                    "decode_duration_ms": 900,
                    "decode_token_count": 45,
                    "decode_sample_count": 1,
                    "cache_prompt_tokens": 900,
                    "cache_read_tokens": 90,
                    "cache_sample_count": 1,
                },
                {},
            ]
        )

        self.assertEqual(summary["matched_trials"], 3)
        self.assertEqual(summary["ttft"]["value_ms"], 100)
        self.assertEqual(summary["ttft"]["covered_trials"], 2)
        self.assertEqual(summary["ttft"]["sample_count"], 10)
        self.assertEqual(summary["tps"]["value"], 55)
        self.assertEqual(summary["tps"]["covered_trials"], 2)
        self.assertEqual(summary["cache_hit_rate"]["value"], 0.18)
        self.assertEqual(summary["cache_hit_rate"]["covered_trials"], 2)

    def test_keeps_unknown_cache_distinct_from_measured_zero(self) -> None:
        unknown = inference_row_metrics(
            {"total_prompt_tokens": 100, "total_completion_tokens": 5}
        )
        legacy_partial_coverage = inference_row_metrics(
            {
                "total_prompt_tokens": 200,
                "total_cached_tokens": 50,
                "total_completion_tokens": 5,
                "extra": {"model_inference": {"attempt_count": 2}},
            }
        )
        measured_miss = inference_row_metrics(
            {
                "extra": {
                    "model_inference": {
                        "cache_prompt_tokens": 100,
                        "cache_read_tokens": 0,
                        "cache_sample_count": 1,
                    }
                },
            }
        )

        self.assertIsNone(unknown["cache_hit_rate"])
        self.assertIsNone(legacy_partial_coverage["cache_hit_rate"])
        self.assertIsNone(legacy_partial_coverage["cache_prompt_tokens"])
        self.assertEqual(measured_miss["cache_hit_rate"], 0)
        summary = aggregate_inference_rows(
            [unknown, legacy_partial_coverage, measured_miss]
        )
        self.assertEqual(summary["cache_hit_rate"]["covered_trials"], 1)
        self.assertEqual(summary["cache_hit_rate"]["value"], 0)

    def test_non_finite_and_zero_decode_evidence_remains_uncovered(self) -> None:
        metrics = inference_row_metrics(
            {
                "extra": {
                    "model_inference": {
                        "ttft_ms_sum": float("nan"),
                        "ttft_sample_count": 1,
                        "decode_duration_ms": 0,
                        "decode_token_count": 10,
                        "decode_sample_count": 1,
                        "cache_prompt_tokens": float("nan"),
                        "cache_read_tokens": 0,
                        "cache_sample_count": 1,
                    }
                }
            }
        )

        self.assertIsNone(metrics["ttft_ms_sum"])
        self.assertIsNone(metrics["ttft_ms"])
        self.assertEqual(metrics["decode_duration_ms"], 0)
        self.assertIsNone(metrics["tps"])
        self.assertIsNone(metrics["cache_hit_rate"])
        summary = aggregate_inference_rows([metrics])
        self.assertEqual(summary["ttft"]["covered_trials"], 0)
        self.assertEqual(summary["tps"]["covered_trials"], 0)
        self.assertEqual(summary["cache_hit_rate"]["covered_trials"], 0)


if __name__ == "__main__":
    unittest.main()
