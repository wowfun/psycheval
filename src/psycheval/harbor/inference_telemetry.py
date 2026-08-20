from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from harbor.models.agent.context import AgentContext

MODEL_INFERENCE_KEY = "model_inference"
MODEL_INFERENCE_SCHEMA_VERSION = 1

_AGGREGATE_FIELDS = (
    "ttft_ms_sum",
    "ttft_sample_count",
    "decode_duration_ms",
    "decode_token_count",
    "decode_sample_count",
    "cache_prompt_tokens",
    "cache_read_tokens",
    "cache_sample_count",
    "attempt_count",
    "successful_attempt_count",
)


@dataclass(frozen=True)
class InferenceObservation:
    """One provider attempt's exact usage and timing evidence."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cached_tokens: int | None = None
    cache_write_tokens: int | None = None
    ttft_ms: float | None = None
    decode_duration_ms: float | None = None
    successful: bool = True
    timing_source: str | None = None
    usage_source: str | None = None


def observation_from_usage(
    value: object,
    *,
    usage_source: str,
    successful: bool = True,
) -> InferenceObservation | None:
    """Normalize a provider usage mapping without converting unknown cache to zero."""

    if not isinstance(value, Mapping):
        return None
    prompt = _optional_int(
        _first(value, "prompt_tokens", "input_tokens", "inputTokens")
    )
    completion = _optional_int(
        _first(value, "completion_tokens", "output_tokens", "outputTokens")
    )
    cached = _optional_int(
        _first(
            value,
            "cached_tokens",
            "cache_read_tokens",
            "cacheReadTokens",
            "cache_read_input_tokens",
            "prompt_cache_hit_tokens",
        )
    )
    cache_write = _optional_int(
        _first(
            value,
            "cache_write_tokens",
            "cacheWriteTokens",
            "cache_creation_input_tokens",
        )
    )
    ttft_ms = _optional_number(_first(value, "ttft_ms", "ttftMs"))
    decode_duration_ms = _optional_number(
        _first(value, "decode_duration_ms", "decodeDurationMs", "decode_ms", "decodeMs")
    )
    usage_present = any(
        item is not None for item in (prompt, completion, cached, cache_write)
    )
    timing_present = ttft_ms is not None or decode_duration_ms is not None
    if not usage_present and not timing_present:
        return None
    return InferenceObservation(
        prompt_tokens=prompt,
        completion_tokens=completion,
        cached_tokens=cached,
        cache_write_tokens=cache_write,
        ttft_ms=ttft_ms,
        decode_duration_ms=decode_duration_ms,
        successful=successful,
        timing_source=usage_source if timing_present else None,
        usage_source=usage_source if usage_present else None,
    )


def metrics_from_observations(
    observations: Iterable[InferenceObservation],
) -> dict[str, Any] | None:
    """Project attempts into one ATIF step metrics object."""

    accepted = list(observations)
    if not accepted:
        return None

    prompt_total = _sum_present(item.prompt_tokens for item in accepted)
    completion_total = _sum_present(item.completion_tokens for item in accepted)
    cached_total = _sum_present(
        item.cached_tokens for item in accepted if _valid_cache_sample(item)
    )
    cache_write_total = _sum_present(item.cache_write_tokens for item in accepted)

    inference = _empty_aggregate()
    timing_sources: set[str] = set()
    usage_sources: set[str] = set()
    for item in accepted:
        inference["attempt_count"] += 1
        if item.successful:
            inference["successful_attempt_count"] += 1
        if item.usage_source:
            usage_sources.add(item.usage_source)

        if _valid_cache_sample(item):
            assert item.prompt_tokens is not None
            assert item.cached_tokens is not None
            inference["cache_prompt_tokens"] += item.prompt_tokens
            inference["cache_read_tokens"] += item.cached_tokens
            inference["cache_sample_count"] += 1

        if not item.successful:
            continue
        if _non_negative_number(item.ttft_ms):
            inference["ttft_ms_sum"] += float(item.ttft_ms)
            inference["ttft_sample_count"] += 1
            if item.timing_source:
                timing_sources.add(item.timing_source)
        if _positive_number(item.decode_duration_ms) and _non_negative_int(
            item.completion_tokens
        ):
            assert item.decode_duration_ms is not None
            assert item.completion_tokens is not None
            inference["decode_duration_ms"] += float(item.decode_duration_ms)
            inference["decode_token_count"] += item.completion_tokens
            inference["decode_sample_count"] += 1
            if item.timing_source:
                timing_sources.add(item.timing_source)

    inference = _compact_aggregate(inference)
    if timing_sources:
        inference["timing_sources"] = sorted(timing_sources)
    if usage_sources:
        inference["usage_sources"] = sorted(usage_sources)

    metrics: dict[str, Any] = {}
    if prompt_total is not None:
        metrics["prompt_tokens"] = prompt_total
    if completion_total is not None:
        metrics["completion_tokens"] = completion_total
    if cached_total is not None and _valid_cached_total(cached_total, prompt_total):
        metrics["cached_tokens"] = cached_total

    extra: dict[str, Any] = {MODEL_INFERENCE_KEY: inference}
    if cache_write_total is not None:
        extra["usage"] = {"cache_write_tokens": cache_write_total}
    metrics["extra"] = extra
    return metrics


def finalize_trajectory_metrics(trajectory: dict[str, Any]) -> dict[str, Any]:
    """Rebuild portable Trial totals from aligned ATIF step metrics."""

    prompt_values: list[int] = []
    completion_values: list[int] = []
    cached_values: list[int] = []
    aggregate = _empty_aggregate()
    timing_sources: set[str] = set()
    usage_sources: set[str] = set()
    for step in trajectory.get("steps", []):
        if not isinstance(step, Mapping):
            continue
        metrics = step.get("metrics")
        if not isinstance(metrics, Mapping):
            continue
        _append_int(prompt_values, metrics.get("prompt_tokens"))
        _append_int(completion_values, metrics.get("completion_tokens"))
        _append_int(cached_values, metrics.get("cached_tokens"))
        extra = metrics.get("extra")
        inference = (
            extra.get(MODEL_INFERENCE_KEY) if isinstance(extra, Mapping) else None
        )
        if not isinstance(inference, Mapping):
            continue
        _merge_aggregate(aggregate, inference)
        timing_sources.update(_string_list(inference.get("timing_sources")))
        usage_sources.update(_string_list(inference.get("usage_sources")))

    existing = trajectory.get("final_metrics")
    final_metrics = dict(existing) if isinstance(existing, Mapping) else {}
    final_metrics["total_steps"] = len(trajectory.get("steps", []))
    if prompt_values:
        final_metrics["total_prompt_tokens"] = sum(prompt_values)
    if completion_values:
        final_metrics["total_completion_tokens"] = sum(completion_values)
    if cached_values:
        final_metrics["total_cached_tokens"] = sum(cached_values)

    compact = _compact_aggregate(aggregate)
    if timing_sources:
        compact["timing_sources"] = sorted(timing_sources)
    if usage_sources:
        compact["usage_sources"] = sorted(usage_sources)
    final_extra = final_metrics.get("extra")
    final_extra = dict(final_extra) if isinstance(final_extra, Mapping) else {}
    if compact.get("attempt_count", 0) > 0:
        final_extra[MODEL_INFERENCE_KEY] = compact
    if final_extra:
        final_metrics["extra"] = final_extra
    trajectory["final_metrics"] = final_metrics
    return trajectory


def populate_context_from_trajectory(
    context: AgentContext,
    trajectory: Mapping[str, Any],
) -> None:
    """Fill Harbor's token context while preserving missing values."""

    final_metrics = trajectory.get("final_metrics")
    if not isinstance(final_metrics, Mapping):
        return
    prompt = _optional_int(final_metrics.get("total_prompt_tokens"))
    completion = _optional_int(final_metrics.get("total_completion_tokens"))
    cached = _optional_int(final_metrics.get("total_cached_tokens"))
    if prompt is not None:
        context.n_input_tokens = prompt
    if completion is not None:
        context.n_output_tokens = completion
    if cached is not None:
        context.n_cache_tokens = cached


def load_trajectory(path: Path) -> dict[str, Any]:
    import json

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("ATIF trajectory must be an object")
    return value


def _empty_aggregate() -> dict[str, int | float]:
    return {field: 0 for field in _AGGREGATE_FIELDS}


def _compact_aggregate(value: Mapping[str, int | float]) -> dict[str, Any]:
    result: dict[str, Any] = {"schema_version": MODEL_INFERENCE_SCHEMA_VERSION}
    paired_fields = {
        "ttft_ms_sum": "ttft_sample_count",
        "ttft_sample_count": "ttft_sample_count",
        "decode_duration_ms": "decode_sample_count",
        "decode_token_count": "decode_sample_count",
        "decode_sample_count": "decode_sample_count",
        "cache_prompt_tokens": "cache_sample_count",
        "cache_read_tokens": "cache_sample_count",
        "cache_sample_count": "cache_sample_count",
    }
    for field in _AGGREGATE_FIELDS:
        raw = value.get(field, 0)
        coverage_field = paired_fields.get(field)
        covered = coverage_field is not None and value.get(coverage_field, 0) > 0
        if (
            raw != 0
            or covered
            or field in {"attempt_count", "successful_attempt_count"}
        ):
            result[field] = raw
    return result


def _merge_aggregate(target: dict[str, int | float], value: Mapping[str, Any]) -> None:
    for field in _AGGREGATE_FIELDS:
        raw = value.get(field)
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            continue
        if not math.isfinite(float(raw)) or raw < 0:
            continue
        target[field] += raw


def _valid_cache_sample(item: InferenceObservation) -> bool:
    if not _non_negative_int(item.prompt_tokens) or not _non_negative_int(
        item.cached_tokens
    ):
        return False
    assert item.prompt_tokens is not None
    assert item.cached_tokens is not None
    if item.cached_tokens > item.prompt_tokens:
        return False
    if item.cache_write_tokens is not None:
        if not _non_negative_int(item.cache_write_tokens):
            return False
        if item.cached_tokens + item.cache_write_tokens > item.prompt_tokens:
            return False
    return item.prompt_tokens > 0


def _valid_cached_total(cached: int, prompt: int | None) -> bool:
    return prompt is None or cached <= prompt


def _sum_present(values: Iterable[int | None]) -> int | None:
    present = [value for value in values if _non_negative_int(value)]
    return sum(present) if present else None


def _append_int(target: list[int], value: object) -> None:
    normalized = _optional_int(value)
    if normalized is not None:
        target.append(normalized)


def _optional_int(value: object) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return None
    return value


def _optional_number(value: object) -> float | None:
    if not _non_negative_number(value):
        return None
    return float(value)


def _non_negative_int(value: object) -> bool:
    return _optional_int(value) is not None


def _non_negative_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and value >= 0
    )


def _positive_number(value: object) -> bool:
    return _non_negative_number(value) and float(value) > 0


def _first(value: Mapping[str, Any], *keys: str) -> object:
    for key in keys:
        if key in value and value[key] is not None:
            return value[key]
    return None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]
