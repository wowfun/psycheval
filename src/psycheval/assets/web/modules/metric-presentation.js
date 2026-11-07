import { RENDER_OPTIONS, fmtMs, fmtPct, fmtCost, fmtNum, fmtTtft, fmtTps, t } from "./shared.js";

let descriptionCache = null;
function metricDefinitions(state = {}) {
  const source = state.catalogPage?.metric_descriptions ? state.catalogPage : state.leaderboardSummary?.metric_descriptions ? state.leaderboardSummary : RENDER_OPTIONS;
  if (source.metric_revision && descriptionCache?.revision === source.metric_revision) return descriptionCache.definitions;
  const definitions = (source.metric_descriptions || []).map(item => ({
    ...item,
    label: item.message_key ? t(item.message_key, item.label) : item.label,
    description: item.description_message_key ? t(item.description_message_key, item.description || "") : item.description || "",
  }));
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
function metricProvenanceHint(provenance, key = "") {
  if (!provenance) return t("measurement_missing_provenance", "Measurement source not recorded");
  const unknown = t("measurement_unknown", "unknown");
  const lines = [];
  if (key === "tps") lines.push(t("measurement_effective_tps", "Contract 1: effective output throughput, including retry waiting. Legacy values retain their recorded basis."));
  if (provenance.variants) {
    if (provenance.mixed_basis) lines.push(t("measurement_mixed_basis", "Mixed measurement bases; aggregates retain all contributing Trials."));
    else if (provenance.mixed_sources) lines.push(t("measurement_mixed_sources", "Different sources with the same measurement basis."));
    for (const item of provenance.variants) lines.push(`${item.trials ?? "?"} Trial · ${item.source ?? unknown} · ${item.method ?? unknown} · ${item.scope || "unknown"} · ${item.quality || "unknown"}${item.cost_kinds?.length ? ` · ${costBasisHint(item.cost_kinds)}` : ""} · ${t("measurement_contract", "Contract")}: ${item.contract_version ?? unknown}${item.missing_reason ? ` · ${missingMeasurementReason(item.missing_reason)}` : ""}`);
    if (provenance.other) lines.push(`${t("measurement_other", "Other sources (details truncated)")}: ${provenance.other.trials} Trial`);
    lines.push(`${t("measurement_available", "Available")}: ${provenance.available ?? "?"}; ${t("measurement_missing", "Missing")}: ${provenance.missing ?? "?"}`);
    return lines.join("\n");
  }
  lines.push(`${t("measurement_source", "Source")}: ${provenance.source ?? unknown}${provenance.producer?.version ? ` (${provenance.producer.version})` : ""}`);
  lines.push(`${t("measurement_basis", "Basis")}: ${provenance.method ?? unknown} · ${provenance.scope ?? unknown} · ${provenance.quality ?? unknown}`);
  lines.push(`${t("measurement_contract", "Contract")}: ${provenance.contract_version ?? unknown}`);
  if (provenance.cost_kinds?.length) lines.push(costBasisHint(provenance.cost_kinds));
  if (provenance.start_boundary) lines.push(`${provenance.start_boundary} → ${provenance.end_boundary ?? unknown}`);
  if (provenance.coverage) {
    const c = provenance.coverage;
    lines.push(`${t("measurement_coverage", "Coverage")}: ${c.measured ?? "?"}/${c.total ?? "?"} ${t("measurement_measured", "measured")}; ${c.unknown ?? "?"} ${t("measurement_unknown", "unknown")}`);
  }
  if (provenance.clock && Object.keys(provenance.clock).length) {
    const c = provenance.clock;
    lines.push(`${t("measurement_clock", "Clock")}: ${[c.id, c.type, c.semantics, c.precision_ms != null ? `${c.precision_ms} ms` : ""].filter(Boolean).join(" · ")}`);
  }
  if (provenance.missing_reason) lines.push(missingMeasurementReason(provenance.missing_reason));
  if (provenance.evidence?.length) lines.push(`${t("measurement_evidence", "Evidence")}: ${provenance.evidence.join(", ")}`);
  return lines.join("\n");
}
function missingMeasurementReason(reason) {
  return `${t("measurement_missing", "Missing")}: ${t(`measurement_reason_${reason}`, t("measurement_reason_missing_evidence", "Required evidence was not recorded."))}`;
}
function costBasisHint(kinds) {
  const labels = {billed: "Billed", native_estimate: "Native estimate"};
  return `${t("measurement_cost_basis", "Cost basis")}: ${kinds.map(kind => t(`measurement_cost_${kind}`, labels[kind] || kind)).join(" / ")}`;
}
function metricSelectionHint(groups, key) {
  const summaries = groups.map(group => group.metrics?.find(metric => metric.key === key)?.provenance).filter(Boolean);
  if (!summaries.length) return metricProvenanceHint(null, key);
  const available = summaries.reduce((total, item) => total + (item.available || 0), 0);
  const missing = summaries.reduce((total, item) => total + (item.missing || 0), 0);
  const reasons = [...new Set(summaries.flatMap(item => (item.variants || []).map(v => v.missing_reason).filter(Boolean)))];
  const hints = [`${t("measurement_available", "Available")}: ${available}; ${t("measurement_missing", "Missing")}: ${missing}`];
  if (summaries.some(item => item.mixed_basis)) hints.push(t("measurement_mixed_basis", "Mixed measurement bases; aggregates retain all contributing Trials."));
  hints.push(...reasons.slice(0, 3).map(missingMeasurementReason));
  if (reasons.length > 3 || summaries.some(item => item.details_truncated)) hints.push(t("measurement_other", "Other sources (details truncated)"));
  return hints.join(" · ");
}
export { metricDefinitions, selectedMetricIds, selectedMetricDefinitions, formatMetric, metricSortKey, metricSearchText, metricProvenanceHint, metricSelectionHint };
