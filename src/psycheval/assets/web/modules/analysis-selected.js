import { esc, fmtDate, fmtMs, fmtNum, hasMetricValue, listValue, t } from "./runtime.js";
import { infoGrid, metricExtra } from "./analysis-metrics.js";

function renderAnalysisPaths(analysis) {
  const paths = analysis.relative_paths || {};
  const rows = [];
  if (paths.json) rows.push(["JSON", paths.json]);
  if (paths.md) rows.push(["Markdown", paths.md]);
  if (!rows.length && analysis.relative_path) rows.push(["Source", analysis.relative_path]);
  return rows.length ? `<div class="analysis-source-list">${rows.map(([label, path]) => `<p class="copy analysis-path"><span class="analysis-source-label">${esc(label)}</span><code>${esc(path)}</code></p>`).join("")}</div>` : "";
}
function renderSelectedEvidence(trajectory, meta) {
  const blocks = [renderSelectedUsage(trajectory), renderSelectedWarnings(meta), renderSelectedSource(meta)].filter(Boolean);
  return blocks.length ? `<section class="selected-extra selected-evidence"><h3>${esc(t("evidence", "Evidence"))}</h3><div class="selected-evidence-list">${blocks.join("")}</div></section>` : "";
}
function renderVerifierEvidence(meta) {
  const evidence = meta?.verifier_evidence;
  if (!evidence || typeof evidence !== "object") return "";
  const tests = evidence.tests && typeof evidence.tests === "object" ? evidence.tests : {};
  const judge = evidence.llm_judge && typeof evidence.llm_judge === "object" ? evidence.llm_judge : {};
  const rows = [
    [t("workbuddy_score", "Canonical score"), evidence.score ?? "-"],
    [t("workbuddy_score_source", "Score source"), evidence.score_source || "-"],
    [t("harbor_reward", "Harbor reward"), evidence.harbor_reward ?? "-"],
    [t("reward_consistency", "Reward consistency"), evidence.reward_consistency || "-"],
    [t("test_status", "Test status"), tests.status || "-"],
    [t("tests_passed_total", "Tests passed / total"), tests.passed !== undefined || tests.total !== undefined ? `${tests.passed ?? "-"} / ${tests.total ?? "-"}` : "-"],
    [t("llm_judge_status", "LLM judge status"), judge.status || "-"],
    [t("llm_judge_score", "LLM judge score"), judge.score ?? "-"],
  ];
  const sourceKey = String(evidence.source_key || "");
  const artifacts = listValue(evidence.artifacts);
  const artifactHtml = artifacts.length ? `<div class="verifier-artifact-list">${artifacts.map(artifact => {
    const artifactId = String(artifact?.id || "");
    const name = String(artifact?.name || t("artifact", "Artifact"));
    const base = sourceKey && artifactId
      ? `/api/harbor/verifier-artifacts/${encodeURIComponent(sourceKey)}/${encodeURIComponent(artifactId)}`
      : "";
    const preview = artifact?.preview && typeof artifact.preview === "object" ? artifact.preview : {};
    const previewHtml = preview.kind === "text"
      ? (base ? `<a class="action-button verifier-artifact-preview" href="${esc(base)}" target="_blank" rel="noreferrer">${esc(t("preview", "Preview"))}</a>` : "")
      : preview.kind === "image" && base
        ? `<img class="verifier-artifact-image" src="${esc(base)}" alt="${esc(name)}" loading="lazy">`
        : "";
    const download = base && artifact?.download_available
      ? `<a class="action-button verifier-artifact-download" href="${esc(base)}?download=true">${esc(t("download", "Download"))}</a>`
      : "";
    return `<section class="verifier-artifact"><div class="verifier-artifact-head"><strong>${esc(name)}</strong>${download}</div>${previewHtml}</section>`;
  }).join("")}</div>` : "";
  return `<article class="selected-evidence-card"><h4>${esc(t("workbuddy_verifier", "WorkBuddy verifier"))}</h4>${infoGrid(rows)}${artifactHtml}</article>`;
}
function renderHarborEvidence(meta) {
  const provenance = meta?.harbor_provenance;
  if (!provenance || typeof provenance !== "object") return "";
  const taskMetadata = meta?.task_metadata && typeof meta.task_metadata === "object" ? meta.task_metadata : {};
  const rewards = meta?.rewards && typeof meta.rewards === "object" ? meta.rewards : {};
  const phases = meta?.evaluation?.phase_timing && typeof meta.evaluation.phase_timing === "object" ? meta.evaluation.phase_timing : {};
  const identity = [
    [t("task", "Task"), meta?.task_name || "-"],
    [t("job", "Job"), meta?.job_name || "-"],
    [t("trial", "Trial"), meta?.trial_name || "-"],
    [t("provider", "Provider"), meta?.model_provider || "-"],
  ];
  const history = [
    [t("job_id", "Job ID"), provenance.job_id || "-"],
    [t("result_id", "Result ID"), provenance.result_id || "-"],
    [t("harbor_version", "Harbor version"), provenance.harbor_version || "-"],
    [t("recorded_task_version", "Recorded Task version"), provenance.task_version || "-"],
    [t("recorded_task_digest", "Recorded Task digest"), provenance.task_digest || "-"],
    [t("recorded_task_digest_source", "Recorded digest source"), provenance.task_digest_source || "-"],
    [t("task_source", "Task source"), provenance.task_source || "-"],
    [t("regrade_source", "Regrade source"), provenance.regrade ? JSON.stringify(provenance.regrade) : "-"],
  ];
  const live = [
    [t("metadata_status", "Metadata status"), taskMetadata.status || "-"],
    [t("live_task_path", "Live Task path"), taskMetadata.path || "-"],
    [t("live_task_name", "Live Task name"), taskMetadata.name || "-"],
    [t("live_task_version", "Live Task version"), taskMetadata.version || "-"],
    [t("task_description", "Description"), taskMetadata.description || "-"],
    [t("live_task_digest", "Live Task digest"), taskMetadata.live_digest || "-"],
    [t("digest_matches", "Digest matches"), taskMetadata.digest_comparison === "not_comparable" ? t("not_comparable", "not comparable") : (taskMetadata.digest_matches === null || taskMetadata.digest_matches === undefined ? "-" : (taskMetadata.digest_matches ? t("yes", "yes") : t("no", "no")))],
    [t("task_keywords", "Task keywords"), listValue(taskMetadata.keywords).join(", ") || "-"],
    [t("diagnostic", "Diagnostic"), taskMetadata.diagnostic || "-"],
  ];
  const rewardRows = Object.entries(rewards).map(([name, value]) => [name, value === null || value === undefined ? "-" : String(value)]);
  const phaseRows = Object.entries(phases).map(([name, value]) => {
    const timing = value && typeof value === "object" ? value : {};
    const duration = hasMetricValue(timing.duration_ms) ? fmtMs(timing.duration_ms) : "-";
    return [t(`phase.${name}`, name.replaceAll("_", " ")), `${duration} · ${fmtDate(timing.started_at)} → ${fmtDate(timing.finished_at)}`];
  });
  return `<section class="selected-extra harbor-evidence"><h3>${esc(t("harbor_evidence", "Harbor Evidence"))}</h3><p class="muted">${esc(t("live_task_metadata_notice", "Task metadata is read live from the configured allowlist; it is not historical Job evidence."))}</p><div class="selected-evidence-list">
    <article class="selected-evidence-card"><h4>${esc(t("identity", "Identity"))}</h4>${infoGrid(identity)}</article>
    <article class="selected-evidence-card"><h4>${esc(t("reward_dimensions", "Reward dimensions"))}</h4>${rewardRows.length ? infoGrid(rewardRows) : `<p class="muted">-</p>`}</article>
    <article class="selected-evidence-card"><h4>${esc(t("phase_timing", "Phase timing"))}</h4>${phaseRows.length ? infoGrid(phaseRows) : `<p class="muted">-</p>`}</article>
    ${renderVerifierEvidence(meta)}
    <article class="selected-evidence-card"><h4>${esc(t("recorded_provenance", "Recorded provenance"))}</h4>${infoGrid(history)}</article>
    <article class="selected-evidence-card"><h4>${esc(t("live_task_metadata", "Live Task metadata"))}</h4>${infoGrid(live)}</article>
  </div></section>`;
}
function renderSelectedUsage(trajectory) {
  const metrics = trajectory?.final_metrics || {};
  const extra = metricExtra(metrics);
  const usage = extra.usage || {};
  const accounting = extra.accounting || {};
  if (!extra.usage && !extra.accounting && !hasMetricValue(metrics.total_prompt_tokens) && !hasMetricValue(metrics.total_completion_tokens) && !hasMetricValue(metrics.total_cached_tokens)) return "";
  return `<article class="selected-evidence-card"><h4>${esc(t("usage_breakdown", "Usage Breakdown"))}</h4>${infoGrid([
    [t("input", "Input"), fmtNum(usage.input_tokens ?? metrics.total_prompt_tokens)],
    [t("output", "Output"), fmtNum(usage.output_tokens ?? metrics.total_completion_tokens)],
    [t("cache_read", "Cache read"), fmtNum(usage.cache_read_tokens ?? metrics.total_cached_tokens)],
    [t("cache_write", "Cache write"), fmtNum(usage.cache_write_tokens)],
    [t("reasoning", "Reasoning"), fmtNum(usage.reasoning_tokens)],
    [t("billable_input", "Billable input"), fmtNum(accounting.billable_input_tokens)],
    [t("billable_output", "Billable output"), fmtNum(accounting.billable_output_tokens)],
    [t("pricing", "Pricing"), accounting.pricing_source || "-"]
  ])}</article>`;
}
function renderSelectedWarnings(meta) {
  const warnings = meta.warnings || [];
  if (!warnings.length) return "";
  return `<article class="selected-evidence-card"><h4>${esc(t("warnings", "Warnings"))}</h4><ul class="evidence-list">${warnings.map(warning => `<li>${esc(warning)}</li>`).join("")}</ul></article>`;
}
function renderSelectedSource(meta) {
  const path = meta.data_ref?.relative_path;
  return path ? `<article class="selected-evidence-card"><h4>${esc(t("input_source", "Input Source"))}</h4><code>${esc(path)}</code></article>` : "";
}
export {
  renderAnalysisPaths,
  renderHarborEvidence,
  renderVerifierEvidence,
  renderSelectedEvidence,
  renderSelectedSource,
  renderSelectedUsage,
  renderSelectedWarnings,
};
