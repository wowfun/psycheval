from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

MODEL_INFERENCE_KEY = "model_inference"

SUFFICIENT_FIELDS = (
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


def inference_row_metrics(final_metrics: object) -> dict[str, int | float | None]:
    """Return validated sufficient statistics and derived Trial display values."""

    metrics = final_metrics if isinstance(final_metrics, Mapping) else {}
    extra = metrics.get("extra")
    inference = extra.get(MODEL_INFERENCE_KEY) if isinstance(extra, Mapping) else {}
    source = inference if isinstance(inference, Mapping) else {}

    values: dict[str, int | float | None] = {
        field: _number(source.get(field)) for field in SUFFICIENT_FIELDS
    }

    ttft_sum = values["ttft_ms_sum"]
    ttft_count = values["ttft_sample_count"]
    decode_ms = values["decode_duration_ms"]
    decode_tokens = values["decode_token_count"]
    decode_count = values["decode_sample_count"]
    cache_prompt = values["cache_prompt_tokens"]
    cache_read = values["cache_read_tokens"]
    cache_count = values["cache_sample_count"]
    values["ttft_ms"] = (
        ttft_sum / ttft_count
        if ttft_sum is not None and ttft_count is not None and ttft_count > 0
        else None
    )
    values["tps"] = (
        1000 * decode_tokens / decode_ms
        if decode_tokens is not None
        and decode_ms is not None
        and decode_ms > 0
        and decode_count is not None
        and decode_count > 0
        else None
    )
    values["cache_hit_rate"] = (
        cache_read / cache_prompt
        if cache_read is not None
        and cache_prompt is not None
        and cache_prompt > 0
        and cache_read <= cache_prompt
        and cache_count is not None
        and cache_count > 0
        else None
    )
    return values


def aggregate_inference_rows(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate Trial sufficient statistics with ratio-of-sums semantics."""

    values = list(rows)
    ttft_sum, ttft_count, ttft_covered = _sum_pair(
        values, "ttft_ms_sum", "ttft_sample_count", positive_denominator=True
    )
    decode_tokens, decode_ms, tps_covered = _sum_pair(
        values,
        "decode_token_count",
        "decode_duration_ms",
        positive_denominator=True,
        sample_count_key="decode_sample_count",
    )
    cache_read, cache_prompt, cache_covered = _sum_pair(
        values,
        "cache_read_tokens",
        "cache_prompt_tokens",
        positive_denominator=True,
        sample_count_key="cache_sample_count",
        numerator_bounded=True,
    )
    return {
        "matched_trials": len(values),
        "ttft": {
            "value_ms": ttft_sum / ttft_count if ttft_count > 0 else None,
            "covered_trials": ttft_covered,
            "sample_count": ttft_count,
            "ttft_ms_sum": ttft_sum,
        },
        "tps": {
            "value": 1000 * decode_tokens / decode_ms if decode_ms > 0 else None,
            "covered_trials": tps_covered,
            "decode_token_count": decode_tokens,
            "decode_duration_ms": decode_ms,
        },
        "cache_hit_rate": {
            "value": cache_read / cache_prompt if cache_prompt > 0 else None,
            "covered_trials": cache_covered,
            "cache_read_tokens": cache_read,
            "cache_prompt_tokens": cache_prompt,
        },
    }


def _sum_pair(
    rows: list[Mapping[str, Any]],
    numerator_key: str,
    denominator_key: str,
    *,
    positive_denominator: bool,
    sample_count_key: str | None = None,
    numerator_bounded: bool = False,
) -> tuple[float, float, int]:
    numerator = 0.0
    denominator = 0.0
    covered = 0
    for row in rows:
        left = _number(row.get(numerator_key))
        right = _number(row.get(denominator_key))
        if left is None or right is None:
            continue
        if positive_denominator and right <= 0:
            continue
        if sample_count_key is not None:
            sample_count = _number(row.get(sample_count_key))
            if sample_count is None or sample_count <= 0:
                continue
        if numerator_bounded and left > right:
            continue
        numerator += left
        denominator += right
        covered += 1
    return numerator, denominator, covered


def _number(value: object) -> int | float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if not math.isfinite(float(value)) or value < 0:
        return None
    return value
