const SUFFICIENT_FIELDS = [
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
];

function metricNumber(value) {
  if (value === null || value === undefined || value === "" || typeof value === "boolean") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric >= 0 ? numeric : null;
}

function inferenceRowMetrics(finalMetrics = {}) {
  const metrics = finalMetrics && typeof finalMetrics === "object" ? finalMetrics : {};
  const source = metrics?.extra?.model_inference && typeof metrics.extra.model_inference === "object"
    ? metrics.extra.model_inference
    : {};
  const row = Object.fromEntries(SUFFICIENT_FIELDS.map(key => [key, metricNumber(source[key])]));
  row.ttft_ms = row.ttft_ms_sum !== null && row.ttft_sample_count > 0
    ? row.ttft_ms_sum / row.ttft_sample_count
    : null;
  row.tps = row.decode_token_count !== null && row.decode_duration_ms > 0 && row.decode_sample_count > 0
    ? 1000 * row.decode_token_count / row.decode_duration_ms
    : null;
  row.cache_hit_rate = row.cache_read_tokens !== null && row.cache_prompt_tokens > 0 && row.cache_read_tokens <= row.cache_prompt_tokens && row.cache_sample_count > 0
    ? row.cache_read_tokens / row.cache_prompt_tokens
    : null;
  return row;
}

function aggregateInferenceRows(rows = []) {
  const values = Array.isArray(rows) ? rows : [];
  const pair = (numeratorKey, denominatorKey, { sampleCountKey = null, numeratorBounded = false } = {}) => {
    let numerator = 0;
    let denominator = 0;
    let covered = 0;
    values.forEach(row => {
      const left = metricNumber(row?.[numeratorKey]);
      const right = metricNumber(row?.[denominatorKey]);
      if (left === null || right === null || right <= 0) return;
      if (sampleCountKey && !(metricNumber(row?.[sampleCountKey]) > 0)) return;
      if (numeratorBounded && left > right) return;
      numerator += left;
      denominator += right;
      covered += 1;
    });
    return { numerator, denominator, covered };
  };
  const ttft = pair("ttft_ms_sum", "ttft_sample_count");
  const tps = pair("decode_token_count", "decode_duration_ms", { sampleCountKey: "decode_sample_count" });
  const cache = pair("cache_read_tokens", "cache_prompt_tokens", { sampleCountKey: "cache_sample_count", numeratorBounded: true });
  return {
    matched_trials: values.length,
    ttft: { value_ms: ttft.denominator > 0 ? ttft.numerator / ttft.denominator : null, covered_trials: ttft.covered, sample_count: ttft.denominator, ttft_ms_sum: ttft.numerator },
    tps: { value: tps.denominator > 0 ? 1000 * tps.numerator / tps.denominator : null, covered_trials: tps.covered, decode_token_count: tps.numerator, decode_duration_ms: tps.denominator },
    cache_hit_rate: { value: cache.denominator > 0 ? cache.numerator / cache.denominator : null, covered_trials: cache.covered, cache_read_tokens: cache.numerator, cache_prompt_tokens: cache.denominator },
  };
}

export { aggregateInferenceRows, inferenceRowMetrics, metricNumber };
