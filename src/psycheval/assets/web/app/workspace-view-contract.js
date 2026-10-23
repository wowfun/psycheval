// @ts-check

const BROWSER_VIEW_LIMIT = 100;
const VIEW_NAME_MAX_CHARS = 120;
const VIEW_GROUPS = new Set(["overall", "agent", "model", "category", "task", "job", "provider"]);
const RADAR_GROUP_LIMIT = 5;
const SUMMARY_DEFAULTS = Object.freeze({ group_by: "agent", statistic: "mean", table_open: false, chart_type: "bar", metrics: null, radar_groups: null });

function normalizeViewFilterValues(values) {
  if (!Array.isArray(values) || values.some(value => typeof value !== "string" || value.includes("\0"))) throw new Error("View filter values must be strings without NUL characters.");
  return [...new Set(values.map(value => value.trim()).filter(Boolean))];
}

export { BROWSER_VIEW_LIMIT, VIEW_NAME_MAX_CHARS, VIEW_GROUPS, normalizeViewFilterValues, SUMMARY_DEFAULTS, RADAR_GROUP_LIMIT };
