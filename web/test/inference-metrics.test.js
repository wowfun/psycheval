import assert from "node:assert/strict";
import test from "node:test";

import { inferenceRowMetrics } from "../../src/psycheval/assets/web/modules/inference-metrics.js";

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
});
