import assert from "node:assert/strict";
import test from "node:test";

import { aggregateInferenceRows, inferenceRowMetrics } from "../../src/psycheval/assets/web/modules/inference-metrics.js";

test("derives trial inference values from sufficient statistics", () => {
  const row = inferenceRowMetrics({
    extra: {
      model_inference: {
        ttft_ms_sum: 600,
        ttft_sample_count: 3,
        decode_duration_ms: 2000,
        decode_token_count: 100,
        decode_sample_count: 3,
        cache_prompt_tokens: 500,
        cache_read_tokens: 125,
        cache_sample_count: 3,
      },
    },
  });

  assert.equal(row.ttft_ms, 200);
  assert.equal(row.tps, 50);
  assert.equal(row.cache_hit_rate, 0.25);
});

test("aggregates inference values as ratios of sums with query coverage", () => {
  const summary = aggregateInferenceRows([
    { ttft_ms_sum: 100, ttft_sample_count: 1, decode_duration_ms: 100, decode_token_count: 10, decode_sample_count: 1, cache_prompt_tokens: 100, cache_read_tokens: 90, cache_sample_count: 1 },
    { ttft_ms_sum: 900, ttft_sample_count: 9, decode_duration_ms: 900, decode_token_count: 45, decode_sample_count: 1, cache_prompt_tokens: 900, cache_read_tokens: 90, cache_sample_count: 1 },
    {},
  ]);

  assert.equal(summary.matched_trials, 3);
  assert.deepEqual(summary.ttft, { value_ms: 100, covered_trials: 2, sample_count: 10, ttft_ms_sum: 1000 });
  assert.deepEqual(summary.tps, { value: 55, covered_trials: 2, decode_token_count: 55, decode_duration_ms: 1000 });
  assert.deepEqual(summary.cache_hit_rate, { value: 0.18, covered_trials: 2, cache_read_tokens: 180, cache_prompt_tokens: 1000 });
});

test("distinguishes unknown cache from a measured zero hit", () => {
  const unknown = inferenceRowMetrics({ total_prompt_tokens: 100 });
  const legacyPartialCoverage = inferenceRowMetrics({
    total_prompt_tokens: 200,
    total_cached_tokens: 50,
    extra: { model_inference: { attempt_count: 2 } },
  });
  const measuredMiss = inferenceRowMetrics({
    extra: {
      model_inference: {
        cache_prompt_tokens: 100,
        cache_read_tokens: 0,
        cache_sample_count: 1,
      },
    },
  });

  assert.equal(unknown.cache_hit_rate, null);
  assert.equal(legacyPartialCoverage.cache_hit_rate, null);
  assert.equal(legacyPartialCoverage.cache_prompt_tokens, null);
  assert.equal(measuredMiss.cache_hit_rate, 0);
  assert.equal(aggregateInferenceRows([unknown, legacyPartialCoverage, measuredMiss]).cache_hit_rate.covered_trials, 1);
});
