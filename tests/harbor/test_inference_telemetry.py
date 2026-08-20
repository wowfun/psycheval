from __future__ import annotations

from harbor.models.agent.context import AgentContext

from psycheval.harbor.inference_telemetry import (
    InferenceObservation,
    finalize_trajectory_metrics,
    metrics_from_observations,
    observation_from_usage,
    populate_context_from_trajectory,
)


def test_aggregates_exact_attempt_statistics_without_averaging_rates() -> None:
    first = metrics_from_observations(
        [
            InferenceObservation(
                prompt_tokens=100,
                completion_tokens=20,
                cached_tokens=30,
                cache_write_tokens=10,
                ttft_ms=120,
                decode_duration_ms=400,
                timing_source="provider.stream",
                usage_source="provider.usage",
            )
        ]
    )
    second = metrics_from_observations(
        [
            InferenceObservation(
                prompt_tokens=300,
                completion_tokens=30,
                cached_tokens=210,
                ttft_ms=280,
                decode_duration_ms=600,
                timing_source="provider.stream",
                usage_source="provider.usage",
            )
        ]
    )

    trajectory = finalize_trajectory_metrics(
        {"steps": [{"metrics": first}, {"metrics": second}]}
    )

    assert trajectory["final_metrics"]["total_prompt_tokens"] == 400
    assert trajectory["final_metrics"]["total_completion_tokens"] == 50
    assert trajectory["final_metrics"]["total_cached_tokens"] == 240
    inference = trajectory["final_metrics"]["extra"]["model_inference"]
    assert inference["ttft_ms_sum"] == 400
    assert inference["ttft_sample_count"] == 2
    assert inference["decode_duration_ms"] == 1000
    assert inference["decode_token_count"] == 50
    assert inference["cache_prompt_tokens"] == 400
    assert inference["cache_read_tokens"] == 240
    assert inference["cache_sample_count"] == 2


def test_unknown_cache_stays_missing_while_explicit_zero_is_covered() -> None:
    unknown = observation_from_usage(
        {"prompt_tokens": 100, "completion_tokens": 5},
        usage_source="fixture",
    )
    measured_miss = observation_from_usage(
        {"prompt_tokens": 80, "completion_tokens": 4, "cached_tokens": 0},
        usage_source="fixture",
    )
    assert unknown is not None
    assert measured_miss is not None

    unknown_metrics = metrics_from_observations([unknown])
    miss_metrics = metrics_from_observations([measured_miss])

    assert unknown_metrics is not None
    assert "cached_tokens" not in unknown_metrics
    assert "cache_prompt_tokens" not in unknown_metrics["extra"]["model_inference"]
    assert miss_metrics is not None
    assert miss_metrics["cached_tokens"] == 0
    assert miss_metrics["extra"]["model_inference"]["cache_prompt_tokens"] == 80
    assert miss_metrics["extra"]["model_inference"]["cache_read_tokens"] == 0
    assert miss_metrics["extra"]["model_inference"]["cache_sample_count"] == 1


def test_invalid_cache_sample_does_not_contaminate_step_cached_total() -> None:
    metrics = metrics_from_observations(
        [
            InferenceObservation(prompt_tokens=100, cached_tokens=150),
            InferenceObservation(prompt_tokens=200, cached_tokens=20),
        ]
    )

    assert metrics is not None
    assert metrics["prompt_tokens"] == 300
    assert metrics["cached_tokens"] == 20
    inference = metrics["extra"]["model_inference"]
    assert inference["cache_prompt_tokens"] == 200
    assert inference["cache_read_tokens"] == 20
    assert inference["cache_sample_count"] == 1


def test_failed_attempt_usage_counts_but_failed_timing_does_not() -> None:
    metrics = metrics_from_observations(
        [
            InferenceObservation(
                prompt_tokens=40,
                completion_tokens=2,
                cached_tokens=10,
                ttft_ms=20,
                decode_duration_ms=50,
                successful=False,
            ),
            InferenceObservation(
                prompt_tokens=60,
                completion_tokens=8,
                cached_tokens=20,
                ttft_ms=30,
                decode_duration_ms=100,
            ),
        ]
    )

    assert metrics is not None
    inference = metrics["extra"]["model_inference"]
    assert inference["attempt_count"] == 2
    assert inference["successful_attempt_count"] == 1
    assert inference["ttft_ms_sum"] == 30
    assert inference["decode_duration_ms"] == 100
    assert inference["decode_token_count"] == 8
    assert inference["cache_prompt_tokens"] == 100
    assert inference["cache_read_tokens"] == 30


def test_collects_only_explicitly_named_exact_timing_fields() -> None:
    observation = observation_from_usage(
        {
            "inputTokens": 50,
            "outputTokens": 10,
            "ttftMs": 75.5,
            "decodeDurationMs": 250,
            "duration_ms": 999,
        },
        usage_source="fixture.exact",
    )

    assert observation is not None
    assert observation.ttft_ms == 75.5
    assert observation.decode_duration_ms == 250
    metrics = metrics_from_observations([observation])
    assert metrics is not None
    inference = metrics["extra"]["model_inference"]
    assert inference["ttft_ms_sum"] == 75.5
    assert inference["ttft_sample_count"] == 1
    assert inference["decode_duration_ms"] == 250
    assert inference["decode_token_count"] == 10
    assert inference["timing_sources"] == ["fixture.exact"]


def test_null_primary_usage_alias_falls_through_without_losing_zero() -> None:
    observation = observation_from_usage(
        {
            "prompt_tokens": None,
            "input_tokens": 10,
            "completion_tokens": None,
            "output_tokens": 0,
            "cached_tokens": None,
            "cache_read_tokens": 0,
        },
        usage_source="fixture.aliases",
    )

    assert observation is not None
    assert observation.prompt_tokens == 10
    assert observation.completion_tokens == 0
    assert observation.cached_tokens == 0


def test_populates_harbor_context_without_inventing_missing_values() -> None:
    context = AgentContext(n_cache_tokens=7)
    populate_context_from_trajectory(
        context,
        {
            "final_metrics": {
                "total_prompt_tokens": 100,
                "total_completion_tokens": 12,
            }
        },
    )

    assert context.n_input_tokens == 100
    assert context.n_output_tokens == 12
    assert context.n_cache_tokens == 7
