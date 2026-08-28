import { $, adminMode, esc, listValue, renderComparisonPanels, state, t } from "./runtime.js";
import { closeDetailSidebar, renderDetailSidebar } from "./detail-sidebar.js";
import { serveApi, setServeStatus } from "./serve-effects.js";
import { leaderboardRows, visibleSelectedSourceKeys } from "./serve-catalog.js";
import { focusSoon } from "./modal-surfaces.js";
import { applyReportCatalog, normalizedReports, reportForId, reportStore } from "./report-store.js";

function reportMessage(key, fallback, values = {}) {
  let message = String(t(key, fallback));
  Object.entries(values).forEach(([name, value]) => {
    message = message.replaceAll(`{${name}}`, String(value));
  });
  return message;
}

const REPORT_READER_MIN_WIDTH = 360;
const REPORT_READER_MIN_WORKSPACE_WIDTH = 360;
const REPORT_READER_KEYBOARD_STEP = 24;
const REPORT_READER_PREVIEW_WIDTH = 1180;

function workspaceReportPreviewPath(report) {
  return `/api/reports/${encodeURIComponent(report.report_id)}/preview`;
}

function workspaceReportOpenPath(report) {
  return `/api/reports/${encodeURIComponent(report.report_id)}/reader`;
}

function normalizedWorkspaceReports(reports = reportStore.reports) {
  return normalizedReports(reports);
}

function workspaceReports() {
  return normalizedWorkspaceReports();
}

function workspaceReportForId(reportId) {
  return reportForId(reportId);
}

function reportsForSourceKey(sourceKey) {
  const wanted = String(sourceKey || "");
  if (!wanted) return [];
  return workspaceReports().filter(report => report.source_keys.includes(wanted));
}

function applyWorkspaceReportCatalog(reports) {
  applyReportCatalog(reports);
  if (state.reportReader.openId && !workspaceReportForId(state.reportReader.openId)) {
    closeWorkspaceReportReader({ restoreFocus: false });
  } else if (state.reportReader.openId) {
    renderWorkspaceReportReader();
  }
}

async function refreshWorkspaceReports(options = {}) {
  try {
    const payload = await serveApi("/api/reports");
    applyWorkspaceReportCatalog(Array.isArray(payload) ? payload : []);
    if (options.renderLeaderboard !== false) renderComparisonPanels({ trace: false });
    return workspaceReports();
  } catch (error) {
    setServeStatus(error.message || String(error), true);
    return null;
  }
}

function workspaceReportLeaderboardColumn() {
  return {
    key: "workspace_reports",
    label: t("workspace_reports", "Reports"),
    valueType: "list",
    value: row => reportsForSourceKey(row?.source_key).map(report => report.filename).join(", ") || "-",
    html: row => renderWorkspaceReportCell(row)
  };
}

function renderWorkspaceReportCell(row) {
  const reports = reportsForSourceKey(row?.source_key);
  if (!reports.length) return `<span class="muted">&mdash;</span>`;
  if (reports.length === 1) {
    const report = reports[0];
    return `<span class="report-cell" data-workspace-report-control><button class="report-cell-button" type="button" data-report-preview="${esc(report.report_id)}" title="${esc(report.filename)}">${esc(report.filename)}</button></span>`;
  }
  const label = reportMessage("reports_count", "{count} reports", { count: reports.length });
  return `<span class="report-cell" data-workspace-report-control>
    <select class="report-cell-select" data-report-preview-select aria-label="${esc(label)}">
      <option value="">${esc(label)}</option>
      ${reports.map(report => `<option value="${esc(report.report_id)}">${esc(report.filename)}</option>`).join("")}
    </select>
  </span>`;
}

function renderAttachWorkspaceReportAction(rows = leaderboardRows()) {
  if (!adminMode()) return "";
  const count = visibleSelectedSourceKeys(rows).length;
  return `<button class="action-button report-attach-button" type="button" data-report-attach data-workspace-report-control ${count ? "" : "disabled"}>${esc(reportMessage("attach_report", "Attach report ({count})", { count }))}</button>`;
}

function bindWorkspaceReportLeaderboardControls(target) {
  if (!target) return;
  target.querySelectorAll("[data-workspace-report-control]").forEach(control => {
    control.addEventListener("click", event => event.stopPropagation());
  });
  target.querySelectorAll("[data-report-preview]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      openWorkspaceReportReader(button.dataset.reportPreview, { opener: button });
    });
  });
  target.querySelectorAll("[data-report-preview-select]").forEach(select => {
    select.addEventListener("change", event => {
      event.stopPropagation();
      const reportId = select.value;
      if (!reportId) return;
      select.value = "";
      openWorkspaceReportReader(reportId, { opener: select });
    });
  });
  target.querySelectorAll("[data-report-attach]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      attachWorkspaceReport(button);
    });
  });
}

async function attachWorkspaceReport(button) {
  if (!adminMode()) return;
  const sourceKeys = visibleSelectedSourceKeys();
  if (!sourceKeys.length) return;
  button.disabled = true;
  try {
    const pickerPayload = await serveApi("/api/path-selections", {
      method: "POST",
      body: { multiple: false }
    });
    const path = listValue(pickerPayload?.paths).map(value => String(value || "").trim()).find(Boolean);
    if (!path) return;
    const payload = await serveApi("/api/reports", {
      method: "POST",
      body: { path, source_keys: sourceKeys }
    });
    applyWorkspaceReportCatalog([...workspaceReports().filter(report => report.report_id !== payload.report_id), payload]);
    state.rowSelection.clear();
    renderComparisonPanels({ trace: false });
    openWorkspaceReportReader(payload?.report_id, {
      opener: document.querySelector("[data-report-manager-open]")
    });
    setServeStatus(t("report_attached", "Report attached"));
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  } finally {
    button.disabled = false;
  }
}

function openWorkspaceReportReader(reportId, options = {}) {
  const report = workspaceReportForId(reportId);
  if (!report) return false;
  state.reportReader.openId = report.report_id;
  state.reportReader.opener = options.opener || document.activeElement || null;
  closeDetailSidebar({ restoreFocus: false, render: false });
  renderDetailSidebar();
  renderWorkspaceReportReader();
  return true;
}

function renderWorkspaceReportReader() {
  const target = $("workspace-report-reader");
  const report = workspaceReportForId(state.reportReader.openId);
  if (!target || !report) return;
  disconnectWorkspaceReportPreviewObserver();
  const previewUrl = workspaceReportPreviewPath(report);
  const openTab = `<a class="action-button compact report-reader-open-tab" data-report-reader-open-tab href="${workspaceReportOpenPath(report)}" target="_blank" rel="noopener">${esc(t("report_open_new_tab", "Open in new tab"))}</a>`;
  const fitAttribute = report.format === "html" ? " data-report-preview-fit" : "";
  const preview = `<iframe class="report-reader-frame" data-report-reader-frame src="${esc(previewUrl)}" title="${esc(report.filename)}" sandbox="allow-scripts" referrerpolicy="no-referrer"></iframe>`;
  target.innerHTML = `<div class="report-reader-panel" role="dialog" aria-modal="false" aria-labelledby="report-reader-title">
    <header class="report-reader-head">
      <div>
        <p class="eyebrow">${esc(t("report_reader_label", "Report preview"))}</p>
        <h2 id="report-reader-title">${esc(report.filename)}</h2>
        <p class="copy">${esc(report.format.toUpperCase())} &middot; ${esc(reportMessage("report_sessions_count", "{count} sessions", { count: report.source_keys.length }))}</p>
      </div>
      <div class="report-reader-actions">
        ${openTab}
        <button class="action-button compact" type="button" data-report-reader-close aria-label="${esc(t("close", "Close"))}">${esc(t("close", "Close"))}</button>
      </div>
    </header>
    <div class="report-reader-frame-viewport" data-report-reader-viewport${fitAttribute}>
      ${preview}
    </div>
  </div>
  <div class="report-reader-resize" data-report-reader-resize role="separator" aria-orientation="vertical" tabindex="0" aria-label="${esc(t("report_resize", "Resize report reader"))}"></div>`;
  target.hidden = false;
  document.body.classList.add("report-reader-open");
  bindWorkspaceReportReaderControls(target);
  observeWorkspaceReportReaderPreview(target);
  focusSoon(target.querySelector?.("[data-report-reader-close]"));
}

function reportReaderPreviewGeometry(viewportWidth, viewportHeight) {
  const availableWidth = Math.max(1, Number(viewportWidth) || 0);
  const availableHeight = Math.max(1, Number(viewportHeight) || 0);
  const scale = Math.min(1, availableWidth / REPORT_READER_PREVIEW_WIDTH);
  return {
    scale,
    width: scale < 1 ? REPORT_READER_PREVIEW_WIDTH : Math.ceil(availableWidth),
    height: Math.ceil(availableHeight / scale),
  };
}

function fitWorkspaceReportReaderPreview(target = $("workspace-report-reader")) {
  const viewport = target?.querySelector?.("[data-report-reader-viewport][data-report-preview-fit]");
  const frame = viewport?.querySelector?.("[data-report-reader-frame]");
  if (!viewport || !frame) return false;
  const bounds = viewport.getBoundingClientRect?.() || {};
  const width = Number(viewport.clientWidth || bounds.width || 0);
  const height = Number(viewport.clientHeight || bounds.height || 0);
  if (!(width > 0) || !(height > 0)) return false;
  const geometry = reportReaderPreviewGeometry(width, height);
  frame.style.width = `${geometry.width}px`;
  frame.style.height = `${geometry.height}px`;
  frame.style.transform = `scale(${geometry.scale})`;
  return true;
}

function disconnectWorkspaceReportPreviewObserver() {
  state.reportReader.previewObserver?.disconnect?.();
  state.reportReader.previewObserver = null;
}

function observeWorkspaceReportReaderPreview(target = $("workspace-report-reader")) {
  disconnectWorkspaceReportPreviewObserver();
  const viewport = target?.querySelector?.("[data-report-reader-viewport][data-report-preview-fit]");
  if (!viewport) return;
  fitWorkspaceReportReaderPreview(target);
  if (typeof ResizeObserver !== "function") return;
  state.reportReader.previewObserver = new ResizeObserver(() => fitWorkspaceReportReaderPreview(target));
  state.reportReader.previewObserver.observe(viewport);
}


function bindWorkspaceReportReaderControls(target) {
  target.querySelectorAll?.("[data-report-reader-close]").forEach(button => {
    button.addEventListener("click", () => closeWorkspaceReportReader());
  });
  const resizeHandle = target.querySelector?.("[data-report-reader-resize]");
  if (!resizeHandle) return;
  syncWorkspaceReportReaderResizeHandle(target);
  resizeHandle.addEventListener("pointerdown", event => {
    if (event.button !== undefined && event.button !== 0) return;
    event.preventDefault();
    const pointerId = event.pointerId;
    document.body.classList.add("report-reader-resizing");
    resizeHandle.setPointerCapture?.(pointerId);
    const resize = moveEvent => {
      if (pointerId !== undefined && moveEvent.pointerId !== undefined && moveEvent.pointerId !== pointerId) return;
      setWorkspaceReportReaderWidth(moveEvent.clientX, target);
    };
    const finish = finishEvent => {
      if (pointerId !== undefined && finishEvent.pointerId !== undefined && finishEvent.pointerId !== pointerId) return;
      document.body.classList.remove("report-reader-resizing");
      resizeHandle.releasePointerCapture?.(pointerId);
      document.removeEventListener("pointermove", resize);
      document.removeEventListener("pointerup", finish);
      document.removeEventListener("pointercancel", finish);
    };
    document.addEventListener("pointermove", resize);
    document.addEventListener("pointerup", finish);
    document.addEventListener("pointercancel", finish);
  });
  resizeHandle.addEventListener("keydown", event => {
    const direction = event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0;
    if (!direction) return;
    event.preventDefault();
    const step = event.shiftKey ? REPORT_READER_KEYBOARD_STEP * 3 : REPORT_READER_KEYBOARD_STEP;
    setWorkspaceReportReaderWidth(currentWorkspaceReportReaderWidth(target) + direction * step, target);
  });
}

function reportReaderViewportWidth() {
  const documentWidth = Number(document.documentElement?.clientWidth || 0);
  const windowWidth = Number(window.innerWidth || 0);
  return documentWidth || windowWidth || 1180;
}

function reportReaderMaximumWidth() {
  return Math.max(REPORT_READER_MIN_WIDTH, reportReaderViewportWidth() - REPORT_READER_MIN_WORKSPACE_WIDTH);
}

function currentWorkspaceReportReaderWidth(target = $("workspace-report-reader")) {
  const remembered = Number(state.reportReader.width);
  if (Number.isFinite(remembered) && remembered > 0) return remembered;
  const measured = Number(target?.getBoundingClientRect?.().width || 0);
  if (Number.isFinite(measured) && measured > 0) return measured;
  return Math.min(720, Math.round(reportReaderViewportWidth() * 0.44));
}

function setWorkspaceReportReaderWidth(width, target = $("workspace-report-reader")) {
  const maximum = reportReaderMaximumWidth();
  const numeric = Number(width);
  const next = Math.round(Math.min(maximum, Math.max(REPORT_READER_MIN_WIDTH, Number.isFinite(numeric) ? numeric : currentWorkspaceReportReaderWidth(target))));
  state.reportReader.width = next;
  document.documentElement?.style?.setProperty("--report-reader-width", `${next}px`);
  syncWorkspaceReportReaderResizeHandle(target, next);
  fitWorkspaceReportReaderPreview(target);
  state.timelineChart?.resize?.();
  return next;
}

function syncWorkspaceReportReaderResizeHandle(target = $("workspace-report-reader"), width = currentWorkspaceReportReaderWidth(target)) {
  const handle = target?.querySelector?.("[data-report-reader-resize]");
  if (!handle) return;
  const maximum = reportReaderMaximumWidth();
  const current = Math.round(Math.min(maximum, Math.max(REPORT_READER_MIN_WIDTH, Number(width))));
  handle.setAttribute?.("aria-valuemin", String(REPORT_READER_MIN_WIDTH));
  handle.setAttribute?.("aria-valuemax", String(maximum));
  handle.setAttribute?.("aria-valuenow", String(current));
}

function closeWorkspaceReportReader(options = {}) {
  const target = $("workspace-report-reader");
  if (!state.reportReader.openId && (!target || target.hidden)) return false;
  disconnectWorkspaceReportPreviewObserver();
  if (target) {
    target.hidden = true;
    target.innerHTML = "";
  }
  document.body.classList.remove("report-reader-open");
  const opener = state.reportReader.opener;
  state.reportReader.openId = null;
  state.reportReader.opener = null;
  if (options.restoreFocus !== false) focusSoon(opener);
  return true;
}

export {
  REPORT_READER_KEYBOARD_STEP,
  REPORT_READER_MIN_WIDTH,
  REPORT_READER_MIN_WORKSPACE_WIDTH,
  REPORT_READER_PREVIEW_WIDTH,
  applyWorkspaceReportCatalog,
  attachWorkspaceReport,
  bindWorkspaceReportLeaderboardControls,
  bindWorkspaceReportReaderControls,
  closeWorkspaceReportReader,
  currentWorkspaceReportReaderWidth,
  fitWorkspaceReportReaderPreview,
  focusSoon,
  normalizedWorkspaceReports,
  openWorkspaceReportReader,
  refreshWorkspaceReports,
  renderAttachWorkspaceReportAction,
  renderWorkspaceReportCell,
  renderWorkspaceReportReader,
  reportMessage,
  reportReaderMaximumWidth,
  reportReaderPreviewGeometry,
  reportReaderViewportWidth,
  reportsForSourceKey,
  setWorkspaceReportReaderWidth,
  syncWorkspaceReportReaderResizeHandle,
  workspaceReportForId,
  workspaceReportLeaderboardColumn,
  workspaceReportOpenPath,
  workspaceReportPreviewPath,
  workspaceReports,
};
