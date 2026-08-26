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

export { inferenceRowMetrics, metricNumber };
