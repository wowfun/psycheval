import { $, esc, finalMetricsFor, fmtCost, fmtDate, fmtMs, fmtNum, fmtScore, hasMetricValue, listValue, lower, renderComparisonPanels, selectedKey, sourceAliasFor, sourceDisplayFor, sourceIdentityFor, state, statusLabel, t } from "./runtime.js";
import { agentNameFor, bindDataTableSelection, renderRowSelection, selectionColumn } from "./data-tables.js";
import { bindServeSourceStateControls, renderServeSourceStateControls } from "./source-state-controls.js";
import { catalogStepOutline, leaderboardRows, metaFor, selectServeDetail, trajectoryFor } from "./serve-catalog.js";
import { finalMetric, infoGrid, maxPositiveMetric, reasoningExposed, systemExposed, timeTitle, timingRatio, tokenTotal, trajectoryDurationHeatClass, trialWallDurationMs } from "./analysis-metrics.js";
import { renderSelectedNotes } from "./analysis-notes.js";
import { renderSelectedAnalysis } from "./analysis-rendering.js";
import { renderHarborEvidence, renderSelectedEvidence } from "./analysis-selected.js";
import { disposeTimelineChart, initTimelineDiagnostics, renderTimelineDiagnostics } from "./timeline-shell.js";
import { bindTimelineControls } from "./timeline-table.js";
import { toolCallRatio, valuePreview } from "./steps.js";

function renderTrajectoryOverview(rows = leaderboardRows()) {
  const target = $("trajectory-overview");
  if (!target) return;
  const body = rows.length
    ? rows.map(row => renderTrajectoryOverviewRow(row)).join("")
    : `<div class="trajectory-empty">${esc(t("no_matching_rows", "No matching rows"))}</div>`;
  target.innerHTML = `
    <div class="panel-head"><h2 id="trajectory-overview-title">${esc(t("trajectory_overview", "Trajectory Overview"))}</h2>${renderServeSourceStateControls(rows)}</div>
    <div class="trajectory-overview-list">${body}</div>
  `;
  bindTrajectoryControls(target);
}
function renderTrajectoryOverviewRow(row) {
  const catalogSourceKey = row.source_key;
  const steps = catalogStepOutline(row.step_outline);
  const selected = catalogSourceKey === state.selectedSourceKey;
  const session = sourceDisplayFor(row);
  const agent = agentNameFor(row);
  const secondary = sourceAliasFor(row) ? `${sourceIdentityFor(row)} / ${agent}` : agent;
  const timingModel = trajectoryOverviewTimingModel(steps);
  const classes = ["trajectory-row", "trajectory-row-selectable", selected ? "selected-row" : ""].filter(Boolean).join(" ");
  return `<div class="${esc(classes)}" data-source-key="${esc(catalogSourceKey)}" title="${esc(row.trial_key)}" tabindex="0"><div class="trajectory-select">${renderRowSelection(row)}</div><div class="trajectory-label"><strong>${esc(session)}</strong><span>${esc(secondary)}</span></div><div class="trajectory-track">${steps.map((step, index) => renderTrajectoryNode(step, index, catalogSourceKey, timingModel)).join("")}</div></div>`;
}
function trajectoryOverviewTimingModel(steps = []) {
  return { maxStepDurationMs: maxPositiveMetric(steps.map(item => item.duration_ms)) };
}
function overviewStepMeta(meta, stepId) {
  return (meta?.steps || []).find(item => String(item.step_id) === String(stepId)) || {};
}
function renderTrajectoryNode(step, index, sourceKey, timingModel) {
  const rawStepId = step?.step_id ?? index + 1;
  const stepId = String(rawStepId);
  const selected = state.selectedSourceKey === sourceKey && String(state.selectedStep?.stepId) === stepId;
  const stepDuration = step?.duration_ms;
  const ratio = timingRatio(stepDuration, timingModel?.maxStepDurationMs);
  const classes = ["trajectory-node", selected ? "selected-node" : "", trajectoryDurationHeatClass(ratio)].filter(Boolean).join(" ");
  const label = stepTitle(step, index, stepDuration, ratio);
  return `<button class="${esc(classes)}" type="button" data-source-key="${esc(sourceKey)}" data-step-id="${esc(stepId)}" title="${esc(label)}" aria-label="${esc(label)}"><span class="trajectory-node-letter">${esc(roleLetter(step?.source))}</span></button>`;
}
function roleLetter(source) {
  const role = lower(source);
  if (role === "system") return "S";
  if (role === "user") return "U";
  if (role === "agent") return "A";
  return "?";
}
function stepTitle(step, index, stepDuration = null, durationRatio = null) {
  const id = step?.step_id ?? index + 1;
  const role = step?.source || "unknown";
  const preview = stepPreviewText(step);
  const duration = hasMetricValue(stepDuration) ? timeTitle("step", stepDuration, durationRatio, "slowest step") : "";
  const head = duration ? `#${id} ${role}; ${duration}` : `#${id} ${role}`;
  return preview ? `${head}: ${preview}` : head;
}
function bindTrajectoryControls(target, rows = leaderboardRows()) {
  bindServeSourceStateControls(target);
  bindDataTableSelection(target, {
    columns: [selectionColumn()],
    rows,
    onChange: () => renderComparisonPanels({ trace: false }),
  });
  target.querySelectorAll("[data-step-id]").forEach(node => {
    node.addEventListener("click", event => {
      event.stopPropagation();
      selectServeDetail(node.dataset.sourceKey, {
        stepId: node.dataset.stepId,
        openSidebar: true,
        opener: node,
        openerSelector: `[data-source-key="${cssAttributeValue(node.dataset.sourceKey)}"][data-step-id="${cssAttributeValue(node.dataset.stepId)}"]`,
      });
    });
  });
  target.querySelectorAll(".trajectory-row[data-source-key]").forEach(row => {
    const open = event => {
      if (event.target !== row && event.target?.closest?.("input,button,a,select,textarea,label,[contenteditable='true']")) return;
      event.stopPropagation();
      selectServeDetail(row.dataset.sourceKey, {
        openSidebar: true,
        opener: row,
        openerSelector: `.trajectory-row[data-source-key="${cssAttributeValue(row.dataset.sourceKey)}"]`,
      });
    };
    row.addEventListener("click", open);
    row.addEventListener("keydown", event => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      open(event);
    });
  });
}
function firstToolName(step) {
  const tool = (step?.tool_calls || [])[0];
  return tool?.function_name || "";
}
function cssAttributeValue(value) {
  return String(value ?? "").replaceAll("\\", "\\\\").replaceAll('"', '\\"');
}
function shortText(value) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > 80 ? `${text.slice(0, 80)}...` : text;
}
function stepPreviewText(step) {
  if (!step) return "";
  return shortText(valuePreview(step?.message).trim() || valuePreview(step?.reasoning_content).trim());
}
function renderTrace() {
  const target = $("trace");
  const trial = metaFor(selectedKey());
  if (!trial?.trial_key) {
    state.selectedTrial = null;
    state.selectedStep = null;
    disposeTimelineChart();
    if (target) target.innerHTML = "";
    return;
  }
  state.selectedTrial = trial.trial_key;
  const trajectory = trajectoryFor(trial.trial_key);
  const metrics = finalMetricsFor(trial.trial_key);
  const status = lower(trial.status || "passed");
  const agentName = trajectory?.agent?.name || "-";
  const model = trajectory?.agent?.model_name || "-";
  const runItems = [
    [t("trial", "Trial"), trial.trial_key || "-"],
    [t("variant", "Variant"), trial.variant_label || "-"],
    [t("session", "Session"), trajectory?.session_id || "-"],
    [t("agent_model", "Agent / model"), `${agentName} / ${model}`],
    [t("time", "Time"), `${fmtDate(trial.started_at_ms)} -> ${fmtDate(trial.finished_at_ms)}`],
    [t("wall_duration", "Wall duration"), fmtMs(trialWallDurationMs(trial))],
    [t("steps_events", "Steps/events"), `${(trajectory?.steps || []).length}/${trial.total_events ?? "-"}`],
    [t("system_exposed", "System exposed"), systemExposed(trajectory) ? t("yes", "yes") : t("no", "no")],
    [t("reasoning_exposed", "Reasoning exposed"), reasoningExposed(trajectory) ? t("yes", "yes") : t("no", "no")]
  ];
  if (trial.source_alias) {
    runItems.splice(3, 0, [t("source_alias", "Source alias"), trial.source_alias]);
  }
  disposeTimelineChart();
  target.innerHTML = `
    <div class="trace-head"><div><p class="eyebrow">${esc(t("selected_trial_trajectory", "selected trial trajectory"))}</p><h2 id="trace-title" class="trace-title"><span>${esc(t("selected_session_label", "session"))}</span><code>${esc(trial.trial_key || "-")}</code></h2></div><span class="status ${status}">${esc(statusLabel(status))}</span></div>
    <h3>${esc(t("run", "Run"))}</h3>
    ${infoGrid(runItems)}
    <h3>${esc(t("result", "Result"))}</h3>
    ${infoGrid([
      [t("status", "Status"), statusLabel(trial.status || "-")],
      [t("score", "Score"), fmtScore(trial.score)],
      [t("evaluator", "Evaluator"), trial.score_message || "-"],
      [t("tokens", "Tokens"), fmtNum(tokenTotal(metrics))],
      [t("turns", "Turns"), finalMetric(metrics, "total_turns") ?? "-"],
      [t("tool_success_total", "Tool success / total"), toolCallRatio(finalMetric(metrics, "total_tool_calls") ?? 0, finalMetric(metrics, "total_tool_errors") ?? 0)],
      [t("cost", "Cost"), fmtCost(metrics.total_cost_usd)]
    ])}
    ${renderHarborEvidence(trial)}
    ${renderSelectedNotes(trial.trial_key)}
    ${renderSelectedAnalysis(trial.trial_key)}
    ${renderSelectedEvidence(trajectory, trial)}
    ${renderTimelineDiagnostics(trajectory, trial)}
  `;
  initTimelineDiagnostics(trajectory, trial);
  bindTimelineControls(trajectory, trial);
}
export {
  bindTrajectoryControls,
  firstToolName,
  overviewStepMeta,
  renderTrace,
  renderTrajectoryNode,
  renderTrajectoryOverview,
  renderTrajectoryOverviewRow,
  roleLetter,
  shortText,
  stepPreviewText,
  stepTitle,
  trajectoryOverviewTimingModel,
};
