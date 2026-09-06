import { esc, fmtMs, fmtNum, hasMetricValue, listValue, lower, stepMeta, t } from "./runtime.js";
import { stepPreviewText } from "./trajectory-trace.js";
import { metricExtra, timeGradientClass, timeGradientStyle, timeTitle, timingRatio } from "./analysis-metrics.js";
import { bindCopyButton } from "./clipboard.js";

function renderStepsHeader(trajectory, options = {}) {
  const count = (trajectory?.steps || []).length;
  const headingId = options.headingId ? ` id="${esc(options.headingId)}"` : "";
  return `<div class="steps-head"><h3${headingId}>${esc(t("steps", "Steps"))} (${count})</h3><button class="action-button" type="button" data-step-action="toggle" ${count ? "" : "disabled"}>${esc(t("expand_all", "Expand all"))}</button></div>`;
}
function valuePreview(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}
function renderStep(step, meta, timingStats, options = {}) {
  const sm = stepMeta(meta, step.step_id);
  const preview = stepPreviewText(step) || "(No Message)";
  return `<details class="step" data-step="${esc(step.step_id)}"${options.open ? " open" : ""}><summary><div class="step-row"><span class="step-id">#${esc(step.step_id)}</span><span class="role ${esc(step.source)}">${esc(step.source)}</span><span class="preview">${esc(preview)}</span></div><div class="rail">${renderStepRail(step, sm, timingStats)}</div></summary><div class="step-body">${renderBlocks(step, sm, timingStats, options.childIds)}</div></details>`;
}
function renderBlocks(step, meta, timingStats, childIds = new Set()) {
  let html = "";
  if (step.reasoning_content) html += block("Reasoning", step.reasoning_content, "reasoning-block");
  const message = valuePreview(step.message);
  if (message.trim()) html += block(step.source === "system" ? "System Prompt" : "Message", message, "message-block");
  html += renderStepActivityBlocks(step, meta, timingStats, childIds);
  return html || `<p class="copy">No visible content.</p>`;
}
function renderStepActivityBlocks(step, meta, timingStats, childIds = new Set()) {
  const entries = [];
  (step.tool_calls || []).forEach(tool => {
    const toolMeta = toolMetaFor(meta, tool.tool_call_id);
    entries.push({
      timestamp: blockTimestamp(toolMeta?.timestamp_ms),
      order: entries.length,
      html: renderToolCallBlock(tool, toolMeta, timingStats),
    });
  });
  ((step.observation && step.observation.results) || []).forEach(observation => {
    const observationMeta = observationMetaFor(meta, observation.source_call_id);
    entries.push({
      timestamp: blockTimestamp(observationMeta?.timestamp_ms),
      order: entries.length,
      html: renderObservationBlock(observation, observationMeta, childIds),
    });
  });
  return entries.sort(compareStepActivityBlocks).map(entry => entry.html).join("");
}
function renderToolCallBlock(tool, toolMeta, timingStats) {
  const ratio = timingRatio(toolMeta?.execution_duration_ms, timingStats?.maxToolExecutionMs);
  const content = valuePreview(tool.arguments || {});
  return `<div class="block tool-block">${blockHeader("Tool Calls", content)}<p>${renderToolNameChip(tool, toolMeta, "", ratio)} <span class="muted">ID: ${esc(tool.tool_call_id || "-")}${toolMeta?.status ? ` / ${esc(toolMeta.status)}` : ""}${renderToolTiming(toolMeta)}</span></p><pre>${esc(content)}</pre></div>`;
}
function renderObservationBlock(observation, observationMeta, childIds = new Set()) {
  const children = (observation.subagent_trajectory_ref || []).filter(ref => childIds.has(ref.trajectory_id)).map(ref => `<button class="action-button" type="button" data-trajectory-id="${esc(ref.trajectory_id)}">${esc(t("view_subagent", "View subagent"))}</button>`).join("");
  const content = valuePreview(observation.content);
  return `<div class="block observation-block">${blockHeader("Observations", content, observationMeta?.tool_error ? "danger" : "")}<p class="muted">Result for: ${esc(observation.source_call_id || "-")}${observationMeta?.status ? ` / ${esc(observationMeta.status)}` : ""}</p><pre>${esc(content)}</pre>${children}</div>`;
}
function compareStepActivityBlocks(a, b) {
  if (a.timestamp !== null && b.timestamp !== null && a.timestamp !== b.timestamp) return a.timestamp - b.timestamp;
  if (a.timestamp !== null && b.timestamp === null) return -1;
  if (a.timestamp === null && b.timestamp !== null) return 1;
  return a.order - b.order;
}
function blockTimestamp(value) {
  return hasMetricValue(value) ? Number(value) : null;
}
function blockHeader(title, content, headingClass = "") {
  const canCopy = Boolean(content.trim());
  const copyLabel = canCopy ? t("copy_block_content", "Copy block content") : t("no_block_content_to_copy", "No block content to copy");
  return `<div class="block-head"><h4 class="${esc(headingClass)}">${esc(title)}</h4><button class="block-copy" type="button" data-block-copy title="${esc(copyLabel)}" aria-label="${esc(`${copyLabel}: ${title}`)}" aria-live="polite"${canCopy ? "" : " disabled"}>${esc(t("copy", "Copy"))}</button></div>`;
}
function block(title, content, cls) { return `<div class="block ${cls}">${blockHeader(title, content)}<pre>${esc(content)}</pre></div>`; }
function bindBlockCopyControls(target) {
  target.querySelectorAll("[data-block-copy]").forEach(button => {
    const card = button.closest(".block");
    bindCopyButton(button, () => card.querySelector("pre")?.textContent || "", card.querySelector("h4")?.textContent || "");
  });
}
function fmtRailTokens(value) {
  if (!hasMetricValue(value)) return "-";
  const number = Number(value);
  return Math.abs(number) >= 1000 ? `${(number / 1000).toFixed(1)}k` : fmtNum(number);
}
function toolExecutionText(toolMeta) { return hasMetricValue(toolMeta?.execution_duration_ms) ? fmtMs(toolMeta.execution_duration_ms) : ""; }
function toolFailed(toolMeta) {
  const status = lower(toolMeta?.status);
  return status === "error" || status === "failed";
}
function renderToolNameChip(tool, toolMeta, extraClass = "", timingFill = null) {
  const name = tool.function_name || toolMeta?.title || "tool";
  const exec = toolExecutionText(toolMeta);
  const titleText = exec ? timeTitle("tool exec", toolMeta?.execution_duration_ms, timingFill, "slowest tool") : "";
  const title = titleText ? ` title="${esc(titleText)}"` : "";
  const execHtml = exec ? ` <span class="tool-exec-inline">${esc(exec)}</span>` : "";
  const classes = ["chip", "tool-name-chip", extraClass, toolFailed(toolMeta) ? "tool-error-chip" : "", timeGradientClass(timingFill)].filter(Boolean).join(" ");
  return `<span class="${esc(classes)}"${timeGradientStyle(timingFill)}${title}>${esc(name)}${execHtml}</span>`;
}
function renderToolTiming(toolMeta) {
  const parts = [];
  if (hasMetricValue(toolMeta?.generation_duration_ms)) parts.push(`generation ${fmtMs(toolMeta.generation_duration_ms)}`);
  return parts.length ? ` / ${parts.map(esc).join(" / ")}` : "";
}
function stepToolChips(step, meta, timingStats) {
  const chips = [];
  (step.tool_calls || []).forEach(tool => {
    const toolMeta = toolMetaFor(meta, tool.tool_call_id);
    const name = String(tool.function_name || toolMeta?.title || "").trim();
    const ratio = timingRatio(toolMeta?.execution_duration_ms, timingStats?.maxToolExecutionMs);
    if (name) chips.push(renderToolNameChip(tool, toolMeta, "rail-chip-tool-list", ratio));
  });
  return chips;
}
function renderStepRail(step, meta, timingStats) {
  const summaryItems = [];
  const toolCalls = (step.tool_calls || []).length;
  const observations = (step.observation?.results || []).length;
  const toolErrors = toolErrorCount(meta);
  if (toolCalls || toolErrors) summaryItems.push(`<span class="rail-chip rail-chip-tools">${esc(toolCallRatio(toolCalls, toolErrors))} tools</span>`);
  else if (observations) summaryItems.push(`<span class="rail-chip rail-chip-tools">${esc(observations)} observations</span>`);
  const tokenInfo = stepTokenInfo(step);
  if (tokenInfo) {
    const classes = ["rail-chip", "rail-chip-tokens", tokenInfo.estimated ? "rail-chip-estimated" : ""].filter(Boolean).join(" ");
    const prefix = tokenInfo.estimated ? "≈" : "";
    const title = tokenInfo.estimated ? `estimated tokens (${tokenInfo.method}; from visible step text): ${fmtNum(tokenInfo.tokens)}` : `${fmtNum(tokenInfo.tokens)} tokens`;
    summaryItems.push(`<span class="${esc(classes)}" title="${esc(title)}">${esc(`${prefix}${fmtRailTokens(tokenInfo.tokens)} tok`)}</span>`);
  }
  const stepRatio = timingRatio(meta?.duration_ms, timingStats?.maxStepDurationMs);
  const elapsedRatio = timingRatio(meta?.elapsed_ms, timingStats?.elapsedMaxMs);
  const stepClasses = ["rail-chip", "rail-chip-step-time", timeGradientClass(stepRatio)].filter(Boolean).join(" ");
  const elapsedClasses = ["rail-chip", "rail-chip-elapsed-time", timeGradientClass(elapsedRatio)].filter(Boolean).join(" ");
  const time = `<div class="rail-time"><span class="${esc(stepClasses)}"${timeGradientStyle(stepRatio)} title="${esc(timeTitle("step span", meta?.duration_ms, stepRatio, "slowest step"))}">step ${esc(fmtMs(meta?.duration_ms))}</span><span class="${esc(elapsedClasses)}"${timeGradientStyle(elapsedRatio)} title="${esc(timeTitle("elapsed", meta?.elapsed_ms, elapsedRatio, "trajectory"))}">elapsed ${esc(fmtMs(meta?.elapsed_ms))}</span></div>`;
  const summary = `<div class="rail-summary">${summaryItems.join("")}${time}</div>`;
  const toolChips = stepToolChips(step, meta, timingStats);
  return `${summary}${toolChips.length ? `<div class="rail-tool-row">${toolChips.join("")}</div>` : ""}`;
}
function toolCallRatio(total, errors) {
  const callTotal = Math.max(0, Number(total || 0));
  const errorTotal = Math.max(0, Number(errors || 0));
  return `${Math.max(0, callTotal - errorTotal)}/${callTotal}`;
}
function toolErrorCount(meta) {
  return listValue(meta?.tool_calls).filter(tool => lower(tool?.status) === "error").length;
}
function toolMetaFor(meta, toolCallId) { return (meta?.tool_calls || []).find(item => item.tool_call_id === toolCallId) || null; }
function observationMetaFor(meta, sourceCallId) { return (meta?.observations || []).find(item => item.source_call_id === sourceCallId) || null; }
function stepTokenInfo(step) {
  const exact = stepTokenTotal(step);
  if (exact !== null && exact !== undefined) return { tokens: exact, estimated: false, method: "exact" };
  return null;
}
function stepTokenTotal(step) {
  const metrics = step.metrics || {};
  const values = [metrics.prompt_tokens, metrics.completion_tokens].filter(hasMetricValue).map(Number);
  if (values.length) return values.reduce((sum, value) => sum + value, 0);
  const direct = metricExtra(metrics).usage?.total_tokens;
  return hasMetricValue(direct) ? Number(direct) : null;
}
function bindStepToggle(root = document, listSelector = "#step-list") {
  const button = root.querySelector("[data-step-action='toggle']");
  if (!button) return;
  const rows = () => Array.from(root.querySelectorAll(`${listSelector} .step`));
  function refresh() {
    const allOpen = rows().length > 0 && rows().every(row => row.open);
    button.textContent = allOpen ? t("collapse_all", "Collapse all") : t("expand_all", "Expand all");
    button.setAttribute("aria-pressed", allOpen ? "true" : "false");
  }
  rows().forEach(row => row.addEventListener("toggle", refresh));
  button.addEventListener("click", () => {
    const shouldOpen = !rows().every(row => row.open);
    rows().forEach(row => { row.open = shouldOpen; });
    refresh();
  });
  refresh();
}
export {
  bindBlockCopyControls,
  bindStepToggle,
  block,
  blockTimestamp,
  compareStepActivityBlocks,
  fmtRailTokens,
  observationMetaFor,
  renderBlocks,
  renderObservationBlock,
  renderStep,
  renderStepActivityBlocks,
  renderStepRail,
  renderStepsHeader,
  renderToolCallBlock,
  renderToolNameChip,
  renderToolTiming,
  stepTokenInfo,
  stepTokenTotal,
  stepToolChips,
  toolCallRatio,
  toolErrorCount,
  toolExecutionText,
  toolFailed,
  toolMetaFor,
  valuePreview,
};
