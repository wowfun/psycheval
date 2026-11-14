import { analysisFor, esc, fmtNum, t } from "./runtime.js";
import { metricExtra } from "./analysis-metrics.js";
import { renderSelectedNotes } from "./analysis-notes.js";
import { autoMetricScalarRows, renderSelectedAnalysis } from "./analysis-rendering.js";
import { renderSourceRefreshControl } from "./source-state-controls.js";

function informationRows(rows) {
  const present = rows.filter(([, value]) => value !== null && value !== undefined
    && (typeof value !== "string" || value.trim())
    && (typeof value !== "object" || Object.keys(value).length));
  return present.length ? `<dl class="trial-info-rows">${present.map(([label, value, format]) => `<div><dt>${esc(label)}</dt><dd>${esc(format ? format(value) : typeof value === "object" ? JSON.stringify(value) : value)}</dd></div>`).join("")}</dl>` : "";
}
function informationSection(label, body) {
  return body ? `<section class="trial-info-section"><h3>${esc(label)}</h3>${body}</section>` : "";
}
function renderSelectedUsage(trajectory, auto = {}) {
  const metrics = trajectory?.final_metrics || {};
  const extra = metricExtra(metrics);
  const usage = extra.usage || {};
  const accounting = extra.accounting || {};
  return informationSection(t("usage_breakdown", "Usage breakdown"), informationRows([
    [t("input", "Input"), usage.input_tokens ?? metrics.total_prompt_tokens, fmtNum],
    [t("output", "Output"), usage.output_tokens ?? metrics.total_completion_tokens, fmtNum],
    [t("cache_read", "Cache read"), usage.cache_read_tokens ?? metrics.total_cached_tokens, fmtNum],
    [t("cache_write", "Cache write"), usage.cache_write_tokens, fmtNum],
    [t("reasoning", "Reasoning"), usage.reasoning_tokens, fmtNum],
    [t("billable_input", "Billable input"), accounting.billable_input_tokens, fmtNum],
    [t("billable_output", "Billable output"), accounting.billable_output_tokens, fmtNum],
    [t("pricing", "Pricing"), accounting.pricing_source],
    ...autoMetricScalarRows("tooling", { distinct_tools: auto.tooling?.distinct_tools }),
    ...autoMetricScalarRows("cost", { cost_per_1k_tokens: auto.cost?.cost_per_1k_tokens }),
  ]));
}
function renderTrialInfo(trajectory, rootMeta, depth = 0, sessionMeta = rootMeta) {
  const provenance = rootMeta.harbor_provenance || {};
  const sessionInTree = trajectory?.session_id === trajectory?.trajectory_id && (depth
    || trajectory?.subagent_trajectories?.length
    || trajectory?.extra?.family?.members?.some(member => member.content_status === "missing"));
  const session = informationRows([
    [t("identifier", "ID"), sessionInTree ? null : trajectory?.session_id],
    [t("source_events", "Source events"), sessionMeta.total_events, fmtNum],
  ]);
  const source = informationRows([
    [t("input_source", "Input source"), rootMeta.data_ref?.relative_path],
    [t("variant", "Variant"), rootMeta.variant_label],
    [t("job_id", "Job ID"), provenance.job_id],
    [t("result_id", "Result ID"), provenance.result_id],
    [t("harbor_version", "Harbor version"), provenance.harbor_version],
    [t("recorded_task_version", "Recorded Task version"), provenance.task_version],
    [t("recorded_task_digest", "Recorded Task digest"), provenance.task_digest],
    [t("recorded_task_digest_source", "Recorded digest source"), provenance.task_digest_source],
    [t("task_source", "Task source"), provenance.task_source],
    [t("regrade_source", "Regrade source"), provenance.regrade],
  ]);
  const refresh = renderSourceRefreshControl(rootMeta.trial_key);
  const auto = depth ? {} : analysisFor(rootMeta.trial_key)?.analysis_metrics?.auto;
  return renderSelectedUsage(trajectory, auto)
    + informationSection(t("session", "Session"), session)
    + informationSection(t("recorded_provenance", "Recorded provenance"), source + refresh)
    + renderSelectedAnalysis(rootMeta.trial_key)
    + renderSelectedNotes(rootMeta.trial_key);
}
function renderSelectedWarnings(meta) {
  const warnings = meta.warnings || [];
  if (!warnings.length) return "";
  return `<article class="selected-evidence-card"><h4>${esc(t("warnings", "Warnings"))}</h4><ul class="evidence-list">${warnings.map(warning => `<li>${esc(warning)}</li>`).join("")}</ul></article>`;
}
function renderIncompleteTrajectory(trajectory) {
  return trajectory?.extra?.diagnostic_only
    ? `<p class="copy danger" role="note">${esc(t("incomplete_trajectory", "Incomplete trajectory — retained for diagnosis, not grading."))}</p>`
    : "";
}
export { informationRows, renderTrialInfo, renderSelectedUsage, renderSelectedWarnings, renderIncompleteTrajectory };
