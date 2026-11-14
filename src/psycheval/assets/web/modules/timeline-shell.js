import { analysisFor, esc, fmtMs, hasMetricValue, state, t } from "./runtime.js";
import { ensureEcharts } from "../app/echarts.js";
import { timelineTrace } from "./timeline-model.js";
import { openTimelineStep, timelineChartOption } from "./timeline-chart.js";
import { bindTimelineControls, fmtTimelineDuration, renderTimelineDetailTable } from "./timeline-table.js";
import { renderLatencyComparison } from "./analysis-rendering.js";
import { renderDateTime } from "./date-time.js";
import { closeModalSurface, openModalSurface } from "./modal-surfaces.js";
import { downloadBlob } from "./download.js";
import { timelineImageBlob } from "./timeline-export.js";

function timingCoverage(trace) {
  return `${t("timeline_compressed_hint", "Gaps without recorded activity are compressed; overlapping stages retain their relative positions.")} ${t("timing_total_hint", "Recorded duration total; contributions may overlap.")}${trace.partial ? ` ${t("timing_partial", "Partial coverage: some intervals are unknown.")}` : ""}`;
}
function renderTimelineSection(className, title, body, open = true) {
  return `<details class="timeline-section ${esc(className)}"${open ? " open" : ""}><summary class="timeline-head"><h3>${esc(title)}</h3></summary><div class="timeline-section-body">${body}</div></details>`;
}
function renderTimelineWaterfall(trace, expanded = false) {
  const height = expanded ? "100%" : `${Math.max(300, Math.min(560, trace.stages.length * 34 + 96))}px`;
  return `<div class="timeline-waterfall-shell"><div class="timeline-waterfall-chart" data-timeline-chart style="height:${height}"></div><p class="timeline-fallback" data-timeline-fallback hidden>${esc(t("timeline_echarts_unavailable", "ECharts did not load. Timeline Waterfall is unavailable, but the detail table is still shown."))}</p></div>`;
}
function renderPhaseTiming(meta) {
  const rows = Object.entries(meta?.evaluation?.phase_timing || {}).flatMap(([name, timing]) => {
    if (!timing || (!hasMetricValue(timing.duration_ms) && !timing.started_at && !timing.finished_at)) return [];
    const times = [timing.started_at, timing.finished_at].filter(Boolean).map(value => renderDateTime(value)).join(" → ");
    return [`<div><dt>${esc(t(`phase.${name}`, name.replaceAll("_", " ")))}</dt><dd>${hasMetricValue(timing.duration_ms) ? esc(fmtMs(timing.duration_ms)) : ""}${times ? `<small>${times}</small>` : ""}</dd></div>`];
  });
  return rows.length ? `<dl class="trial-info-rows">${rows.join("")}</dl>` : "";
}
function renderTimelineDiagnostics(trajectory, meta, options = {}) {
  const trace = options.trace || timelineTrace(trajectory, meta);
  const disclosure = options.disclosure || {};
  const body = trace.stages.length ? `<section class="timeline-waterfall-section">
    <div class="timeline-head"><h3>${esc(t("timeline_waterfall", "Timeline Waterfall"))}</h3><button type="button" class="action-button compact" data-timeline-expand title="${esc(t("timeline_expand", "Expand waterfall"))}" aria-label="${esc(t("timeline_expand", "Expand waterfall"))}"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M3 3l6 6m12-6-6 6M3 21l6-6m12 6-6-6"/></svg></button></div>
    <p class="timeline-total">${esc(t("timeline_active_total", "Cumulative active duration"))}: ${trace.model.active_total_ms === null ? "—" : esc(fmtTimelineDuration(trace.model.active_total_ms))}</p>
    <p class="copy">${esc(timingCoverage(trace))}</p>${renderTimelineWaterfall(trace)}</section>
    ${renderTimelineSection("timeline-table-section", t("timeline_detail_table", "Timeline Detail Table"), renderTimelineDetailTable(trace.stages, trace.model, options.tableId), disclosure.table)}`
    : `<p class="timeline-empty">${esc(t("timeline_empty", "No timed step or tool durations available."))}</p>`;
  const phases = options.rootMeta ? renderPhaseTiming(options.rootMeta) : "";
  const latency = options.isRoot ? renderLatencyComparison(analysisFor(meta.trial_key)?.analysis_metrics?.auto?.latency || {}) : "";
  return `<div class="timeline-diagnostics">${phases ? renderTimelineSection("timeline-phases-section", t("phase_timing", "Phase timing"), phases, disclosure.phases) : ""}${body}${latency ? renderTimelineSection("timeline-distribution-section", t("metric_group_latency", "Latency"), latency, disclosure.distribution) : ""}</div>`;
}
function createWaterfall(root, trace, onStep) {
  const node = root.querySelector("[data-timeline-chart]");
  if (!node) return { dispose() {} };
  let disposed = false, chart = null, observer = null;
  const resize = () => {
    if (!chart || !node.clientWidth) return;
    chart.resize();
    const option = timelineChartOption(trace, { width: node.clientWidth });
    chart.setOption({ grid: option.grid, yAxis: { axisLabel: option.yAxis.axisLabel } });
  };
  void ensureEcharts().then(() => {
    if (disposed || !node.isConnected) return;
    chart = window.echarts.init(node, null, { renderer: "canvas" });
    chart.setOption(timelineChartOption(trace, { width: node.clientWidth }), true);
    chart.on("click", params => onStep(params?.data?.trace_item));
    if (typeof ResizeObserver === "function") { observer = new ResizeObserver(resize); observer.observe(node); }
  }).catch(() => {
    if (disposed) return;
    observer?.disconnect(); chart?.dispose(); chart = null;
    node.hidden = true;
    root.querySelector("[data-timeline-fallback]").hidden = false;
    const expand = root.querySelector("[data-timeline-expand]");
    if (expand) expand.disabled = true;
  });
  return { dispose() { disposed = true; observer?.disconnect(); chart?.dispose(); chart = null; } };
}
function timingIdentity(trajectory, meta, scope = state.catalogQuery.metric_scope) {
  const trajectoryId = trajectory?.trajectory_id || trajectory?.session_id || "root";
  return {
    key: `timing:${[meta.trial_key, trajectoryId, scope].map(encodeURIComponent).join(":")}`,
    trialKey: meta.trial_key,
    trajectoryId,
    scope: scope === "family" ? t("timing_scope_family", "Selected session and sub-sessions") : t("current_session", "Current session"),
  };
}
function mountTimingPanel(target, trajectory, meta, options = {}) {
  const trace = timelineTrace(trajectory, meta);
  const identity = timingIdentity(trajectory, meta);
  const tableId = identity.key;
  let waterfall = null, modal = null, expanded = null, disposed = false;
  const disclosure = options.disclosure || {};
  function closeExpanded(restoreFocus = true) {
    if (!modal) return false;
    const surface = modal;
    closeModalSurface(surface, { restoreFocus });
    return true;
  }
  function openStep(item) { closeExpanded(false); openTimelineStep(item); }
  function expand(opener) {
    if (modal) return;
    modal = document.createElement("div");
    modal.className = "timeline-modal";
    modal.hidden = true;
    modal.setAttribute("role", "dialog"); modal.setAttribute("aria-modal", "true"); modal.setAttribute("aria-labelledby", "timeline-expanded-title");
    modal.innerHTML = `<div class="timeline-modal-panel"><header><div><h2 id="timeline-expanded-title">${esc(t("timeline_waterfall", "Timeline Waterfall"))}</h2><p class="copy">${esc([...new Set([identity.trialKey, identity.trajectoryId])].filter(Boolean).join(" / "))} / ${esc(identity.scope)}</p></div><div class="timeline-modal-actions"><button class="action-button" type="button" data-timeline-export>${esc(t("timeline_export_png", "Export PNG"))}</button><button class="action-button" type="button" data-timeline-close>${esc(t("close", "Close"))}</button></div></header><p class="copy timeline-coverage">${esc(timingCoverage(trace))}</p><p class="copy danger" role="alert" data-timeline-error hidden></p>${renderTimelineWaterfall(trace, true)}</div>`;
    document.body.appendChild(modal);
    const surface = modal;
    openModalSurface(surface, { opener, bodyClass: "timeline-modal-open", focusTarget: surface.querySelector("[data-timeline-close]"), onRequestClose: () => closeExpanded(), onClose: () => { expanded?.dispose(); expanded = null; surface.remove(); modal = null; } });
    surface.addEventListener("keydown", event => { if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); closeExpanded(); } });
    surface.querySelector("[data-timeline-close]").addEventListener("click", () => closeExpanded());
    surface.querySelector("[data-timeline-export]").addEventListener("click", async event => {
      const button = event.currentTarget;
      const error = surface.querySelector("[data-timeline-error]");
      button.disabled = true; error.hidden = true;
      try {
        const blob = await timelineImageBlob(trace, identity, timingCoverage(trace));
        if (disposed || modal !== surface) return;
        const name = `${identity.trialKey}-${identity.trajectoryId}`.replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 160);
        downloadBlob(`peval-timeline-${name}.png`, "image/png", blob);
      } catch (failure) {
        if (modal === surface) { error.textContent = `${t("timeline_export_failed", "Image export failed")}: ${failure.message || failure}`; error.hidden = false; }
      } finally { button.disabled = false; }
    });
    expanded = createWaterfall(surface, trace, openStep);
  }
  target.innerHTML = renderTimelineDiagnostics(trajectory, meta, { ...options, trace, tableId, disclosure });
  const table = target.querySelector(".timeline-table-section > .timeline-section-body");
  function renderTable() {
    const scrollLeft = table.querySelector(".table-wrap")?.scrollLeft || 0;
    table.innerHTML = renderTimelineDetailTable(trace.stages, trace.model, tableId);
    bindTimelineControls(table, trace, tableId, renderTable);
    const wrap = table.querySelector(".table-wrap");
    if (wrap) wrap.scrollLeft = scrollLeft;
  }
  if (table) bindTimelineControls(table, trace, tableId, renderTable);
  for (const [key, selector] of [["table", ".timeline-table-section"], ["phases", ".timeline-phases-section"], ["distribution", ".timeline-distribution-section"]]) {
    const section = target.querySelector(selector);
    section?.addEventListener("toggle", () => { if (section.isConnected) disclosure[key] = section.open; });
  }
  target.querySelector("[data-timeline-expand]")?.addEventListener("click", event => expand(event.currentTarget));
  waterfall = createWaterfall(target, trace, openStep);
  return { dispose() { disposed = true; closeExpanded(false); waterfall?.dispose(); } };
}
export { timingIdentity, renderPhaseTiming, mountTimingPanel, renderTimelineDiagnostics, renderTimelineSection, renderTimelineWaterfall };
