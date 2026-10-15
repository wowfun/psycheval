import { beginFeedback } from "./action-feedback.js";
import { $, adminMode, esc, homeDetail, listValue, renderComparisonPanels, state, t } from "./runtime.js";
import { serveApi } from "./serve-effects.js";
import { leaderboardRows, visibleSelectedSourceKeys } from "./serve-catalog.js";
import { applyReportCatalog, normalizedReports, reportForId, reportStore } from "./report-store.js";
import { createReportSidebarAdapter } from "./report-sidebar.js";
import { bindWorkspaceLinkButtons, workspaceLinkButton } from "./workspace-links.js";

function reportMessage(key, fallback, values = {}) {
  let message = String(t(key, fallback));
  Object.entries(values).forEach(([name, value]) => {
    message = message.replaceAll(`{${name}}`, String(value));
  });
  return message;
}

const REPORT_READER_PREVIEW_WIDTH = 1180;
let reportReaderController = null;

function reportReaderSurface() {
  if (!reportReaderController) {
    reportReaderController = createReportSidebarAdapter({
      ownerId: "home-report-reader",
      onRequestClose: options => closeWorkspaceReportReader({ restoreFocus: options.restoreFocus, locationKind: options.reason === "dismiss" ? "object" : "replace" }),
      onResize: () => {
        fitWorkspaceReportReaderPreview();
        state.timelineChart?.resize?.();
      },
    });
  }
  return reportReaderController;
}

function workspaceReportPreviewPath(report) {
  return `/api/report-library/${encodeURIComponent(report.report_ref)}/preview`;
}

function workspaceReportOpenPath(report) {
  return `/api/report-library/${encodeURIComponent(report.report_ref)}/reader`;
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
  if (state.reportReader.openRef) {
    const report = workspaceReports().find(item => item.report_ref === state.reportReader.openRef);
    if (report) {
      state.reportReader.report = report;
      renderWorkspaceReportReader();
    }
  }
}

async function refreshWorkspaceReports(options = {}) {
  const request = ++reportCatalogRequestId;
  try {
    const payload = await serveApi("/api/reports", { signal: options.signal });
    if (options.signal?.aborted || request !== reportCatalogRequestId) return;
    applyWorkspaceReportCatalog(Array.isArray(payload) ? payload : []);
    const ref = state.reportReader.openRef;
    if (ref && !workspaceReports().some(report => report.report_ref === ref)) {
      try {
        const report = await serveApi(`/api/report-library/${encodeURIComponent(ref)}`, { signal: options.signal });
        if (request !== reportCatalogRequestId || options.signal?.aborted) return;
        if (state.reportReader.openRef === ref) {
          state.reportReader.report = report;
          renderWorkspaceReportReader();
        }
      } catch (error) {
        if (request !== reportCatalogRequestId || options.signal?.aborted) return;
        if (state.reportReader.openRef === ref && !options.signal?.aborted && error.status === 404) closeWorkspaceReportReader({ restoreFocus: false, locationKind: "replace" });
        else if (!options.signal?.aborted) throw error;
      }
    }
    if (options.renderLeaderboard !== false) renderComparisonPanels({ trace: false });
    return workspaceReports();
  } catch (error) {
    if (options.signal?.aborted || request !== reportCatalogRequestId) return;
    beginFeedback("#leaderboard .leaderboard-action-row", { key: "home:reports:load", page: "home" }).error(error);
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
  const feedback = beginFeedback("#leaderboard .leaderboard-action-row", { page: "home", key: "home:report-attach" });
  try {
    const pickerPayload = await serveApi("/api/path-selections", {
      method: "POST",
      body: { multiple: false }
    });
    const path = listValue(pickerPayload?.paths).map(value => String(value || "").trim()).find(Boolean);
    if (!path) return;
    const payload = await serveApi("/api/reports", {
      method: "POST",
      body: { path, bindings: sourceKeys.map(key => ({ kind: "session", key })) }
    });
    applyWorkspaceReportCatalog([...workspaceReports().filter(report => report.report_id !== payload.report_id), payload]);
    state.rowSelection.clear();
    renderComparisonPanels({ trace: false });
    openWorkspaceReportReader(payload?.report_id, {
      opener: document.querySelector("[data-report-manager-open]")
    });
    feedback.set(t("report_attached", "Report attached"));
  } catch (error) {
    feedback.set(error.message || String(error), true);
  } finally {
    button.disabled = false;
  }
}

function openWorkspaceReportReader(reportId, options = {}) {
  const report = workspaceReportForId(reportId);
  if (!report) return false;
  cancelWorkspaceReportRequest();
  state.reportReader.openRef = report.report_ref;
  state.reportReader.report = report;
  homeDetail.register("report", { cancel: cancelWorkspaceReportRequest, close: closeWorkspaceReportReader });
  homeDetail.activate({ report: report.report_ref });
  renderWorkspaceReportReader({ opener: options.opener || document.activeElement || null });
  return true;
}

let reportRequestId = 0;
let reportCatalogRequestId = 0;
function cancelWorkspaceReportRequest(options = {}) { reportRequestId++; if (options.catalog) reportCatalogRequestId++; }
async function openWorkspaceReportRef(ref, options = {}) {
  homeDetail.register("report", { cancel: cancelWorkspaceReportRequest, close: closeWorkspaceReportReader });
  const request = ++reportRequestId;
  const report = await serveApi(`/api/report-library/${encodeURIComponent(ref)}`, { signal: options.signal });
  if (options.signal?.aborted || request !== reportRequestId) return;
  state.reportReader.openRef = ref;
  state.reportReader.report = report;
  homeDetail.activate({ report: ref }, options.locationKind || "object");
  renderWorkspaceReportReader({ opener: options.opener || null });
}

function renderWorkspaceReportReader(options = {}) {
  const target = $("workspace-report-reader");
  const report = state.reportReader.report;
  if (!target || !report) return;
  disconnectWorkspaceReportPreviewObserver();
  const previewUrl = workspaceReportPreviewPath(report);
  const openTab = `<a class="action-button compact report-reader-open-tab" data-report-reader-open-tab href="${esc(workspaceReportOpenPath(report))}" target="_blank" rel="noopener">${esc(t("report_open_new_tab", "Open in new tab"))}</a>`;
  const fitAttribute = report.format === "html" ? " data-report-preview-fit" : "";
  const preview = `<iframe class="report-reader-frame" data-report-reader-frame src="${esc(previewUrl)}" title="${esc(report.filename)}" sandbox="allow-scripts" referrerpolicy="no-referrer"></iframe>`;
  const content = `<div class="report-reader-panel" role="dialog" aria-modal="false" aria-labelledby="report-reader-title">
    <header class="report-reader-head">
      <div>
        <p class="eyebrow">${esc(t("report_reader_label", "Report preview"))}</p>
        <h2 id="report-reader-title">${esc(report.filename)}</h2>
        <p class="copy">${esc(report.format.toUpperCase())} &middot; ${esc(reportMessage("report_sessions_count", "{count} sessions", { count: report.source_keys.length }))}</p>
      </div>
      <div class="report-reader-actions">
        ${openTab}
        ${workspaceLinkButton()}
        <button class="action-button compact" type="button" data-sidebar-close aria-label="${esc(t("close", "Close"))}">${esc(t("close", "Close"))}</button>
      </div>
    </header>
    <div class="report-reader-frame-viewport" data-report-reader-viewport${fitAttribute}>
      ${preview}
    </div>
  </div>`;
  const explicitOpen = Object.hasOwn(options, "opener");
  reportReaderSurface().open({
    render: () => { target.innerHTML = content; },
    ...(explicitOpen ? {
      opener: options.opener,
      focusTarget: () => target.querySelector("[data-sidebar-close]"),
    } : {}),
  });
  observeWorkspaceReportReaderPreview(target);
  bindWorkspaceLinkButtons(target, "home");
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


function closeWorkspaceReportReader(options = {}) {
  const target = $("workspace-report-reader");
  const surface = reportReaderSurface();
  if (!state.reportReader.openRef) return false;
  cancelWorkspaceReportRequest();
  const ref = state.reportReader.openRef;
  disconnectWorkspaceReportPreviewObserver();
  surface.close({ restoreFocus: options.restoreFocus });
  if (target) target.innerHTML = "";
  state.reportReader.openRef = null;
  state.reportReader.report = null;
  homeDetail.clear("report", options.locationKind || "object");
  return true;
}

export {
  cancelWorkspaceReportRequest,
  openWorkspaceReportRef,
  REPORT_READER_PREVIEW_WIDTH,
  applyWorkspaceReportCatalog,
  attachWorkspaceReport,
  bindWorkspaceReportLeaderboardControls,
  closeWorkspaceReportReader,
  fitWorkspaceReportReaderPreview,
  normalizedWorkspaceReports,
  openWorkspaceReportReader,
  refreshWorkspaceReports,
  renderAttachWorkspaceReportAction,
  renderWorkspaceReportCell,
  renderWorkspaceReportReader,
  reportMessage,
  reportReaderPreviewGeometry,
  reportsForSourceKey,
  workspaceReportForId,
  workspaceReportLeaderboardColumn,
  workspaceReportOpenPath,
  workspaceReportPreviewPath,
  workspaceReports,
};
