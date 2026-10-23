import { RENDER_OPTIONS, fmtMs, fmtPct, fmtCost, fmtNum, fmtTtft, fmtTps, t } from "./shared.js";

let descriptionCache = null;
function metricDefinitions(state = {}) {
  const source = state.catalogPage?.metric_descriptions ? state.catalogPage : state.leaderboardSummary?.metric_descriptions ? state.leaderboardSummary : RENDER_OPTIONS;
  if (source.metric_revision && descriptionCache?.revision === source.metric_revision) return descriptionCache.definitions;
  const definitions = (source.metric_descriptions || []).map(item => ({ ...item, label: item.message_key ? t(item.message_key, item.label) : item.label }));
  if (source.metric_revision) descriptionCache = { revision: source.metric_revision, definitions };
  return definitions;
}
function selectedMetricIds(state) {
  return state.leaderboardSummaryMetrics ?? metricDefinitions(state).filter(item => item.default).map(item => item.key);
}
function selectedMetricDefinitions(state) {
  const definitions = metricDefinitions(state);
  return selectedMetricIds(state).flatMap(key => definitions.filter(item => item.key === key));
}
function formatMetric(definition, value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  if (definition?.key === "ttft_ms") return fmtTtft(value);
  if (definition?.key === "tps") return fmtTps(value);
  if (definition?.type === "duration") return `${value < 0 ? "−" : ""}${fmtMs(Math.abs(value))}`;
  if (definition?.type === "percent") return fmtPct(value);
  if (definition?.type === "currency") return fmtCost(value);
  return `${fmtNum(value)}${definition?.unit ? " " + definition.unit : ""}`;
}
function metricSortKey(state, key) {
  const definition = metricDefinitions(state).find(item => item.key === key || item.column_key === key);
  return definition ? `metric:${definition.key}` : key;
}
function metricSearchText(label, key) {
  let decoded = key;
  try { decoded = decodeURIComponent(key); } catch { /* Non-metric column identity. */ }
  return `${label} ${key} ${decoded}`.toLocaleLowerCase();
}
export { metricDefinitions, selectedMetricIds, selectedMetricDefinitions, formatMetric, metricSortKey, metricSearchText };
