// @ts-check

const BROWSER_VIEW_LIMIT = 100;
const VIEW_NAME_MAX_CHARS = 120;
const VIEW_GROUPS = new Set(["overall", "agent", "model", "category", "task", "job", "provider"]);
const RADAR_METRICS = Object.freeze(["score", "duration_ms", "ttft_ms", "tps", "cache_hit_rate", "model_duration_ms", "tool_success_rate"]);
const DEFAULT_RADAR_METRICS = Object.freeze(RADAR_METRICS.filter(key => key !== "model_duration_ms"));
const RADAR_GROUP_LIMIT = 5;
const SUMMARY_DEFAULTS = Object.freeze({ group_by: "agent", statistic: "mean", table_open: false, chart_type: "bar", radar_metrics: DEFAULT_RADAR_METRICS, radar_groups: null });

function normalizeViewFilterValues(values) {
  if (!Array.isArray(values) || values.some(value => typeof value !== "string" || value.includes("\0"))) throw new Error("View filter values must be strings without NUL characters.");
  return [...new Set(values.map(value => value.trim()).filter(Boolean))];
}

export { BROWSER_VIEW_LIMIT, VIEW_NAME_MAX_CHARS, VIEW_GROUPS, normalizeViewFilterValues, SUMMARY_DEFAULTS, RADAR_METRICS, DEFAULT_RADAR_METRICS, RADAR_GROUP_LIMIT };
