import { $, esc, listValue, lower, readableServeSources, renderComparisonPanels, renderReadOnlySourceTags, serveMode, sourceTagsFor, state, t, workspaceDisplayMode, workspaceSnapshotMode } from "./runtime.js";
import { renderStepDrawer } from "./trajectory-trace.js";
import { closeServeSourceManager, sourceDisplayLabel } from "./source-manager.js";
import { serveApi, setServeStatus } from "./serve-effects.js";
import { leaderboardRows, visibleSelectedSourceKeys } from "./serve-catalog.js";
import { closeModalSurface, focusSoon, openModalSurface } from "./modal-surfaces.js";

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
  return `/api/reports/${encodeURIComponent(report.report_id)}/open`;
}

function normalizedWorkspaceReports(reports = state.workspaceReports) {
  return listValue(reports)
    .filter(report => report && report.report_id && report.filename)
    .map(report => ({
      report_id: String(report.report_id),
      filename: String(report.filename),
      format: lower(report.format) === "html" ? "html" : "markdown",
      source_keys: Array.from(new Set(listValue(report.source_keys).map(key => String(key || "").trim()).filter(Boolean))),
      preview_base64: typeof report.preview_base64 === "string" ? report.preview_base64 : "",
    }))
    .sort((left, right) => right.report_id.localeCompare(left.report_id, undefined, { numeric: true }));
}

function workspaceReports() {
  return normalizedWorkspaceReports();
}

function workspaceReportForId(reportId) {
  const wanted = String(reportId || "");
  return workspaceReports().find(report => report.report_id === wanted) || null;
}

function reportsForSourceKey(sourceKey) {
  const wanted = String(sourceKey || "");
  if (!wanted) return [];
  return workspaceReports().filter(report => report.source_keys.includes(wanted));
}

function applyWorkspaceReportCatalog(reports) {
  const selectedId = state.reportManager.selectedId;
  const selectedStillExists = normalizedWorkspaceReports(reports).some(report => report.report_id === selectedId);
  state.workspaceReports = normalizedWorkspaceReports(reports);
  if (!selectedStillExists) {
    state.reportManager.selectedId = state.workspaceReports[0]?.report_id || null;
    syncWorkspaceReportDraft();
  } else if (!state.reportManager.dirty) {
    syncWorkspaceReportDraft();
  }
  if (state.reportReader.openId && !workspaceReportForId(state.reportReader.openId)) {
    closeWorkspaceReportReader({ restoreFocus: false });
  } else if (state.reportReader.openId) {
    renderWorkspaceReportReader();
  }
  if (workspaceReportManagerOpen()) renderWorkspaceReportManager();
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
  return `<span class="report-cell" data-workspace-report-control>
    <details class="report-cell-menu">
      <summary>${esc(reportMessage("reports_count", "{count} reports", { count: reports.length }))}</summary>
      <span class="report-cell-menu-panel">
        ${reports.map(report => `<button type="button" data-report-preview="${esc(report.report_id)}" title="${esc(report.filename)}">${esc(report.filename)}</button>`).join("")}
      </span>
    </details>
  </span>`;
}

function renderAttachWorkspaceReportAction(rows = leaderboardRows()) {
  const count = visibleSelectedSourceKeys(rows).length;
  return `<button class="step-toggle-button report-attach-button" type="button" data-report-attach data-workspace-report-control ${count ? "" : "disabled"}>${esc(reportMessage("attach_report", "Attach report ({count})", { count }))}</button>`;
}

function bindWorkspaceReportLeaderboardControls(target) {
  if (!workspaceDisplayMode() || !target) return;
  target.querySelectorAll("[data-workspace-report-control]").forEach(control => {
    control.addEventListener("click", event => event.stopPropagation());
  });
  target.querySelectorAll("[data-report-preview]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      button.closest?.("details")?.removeAttribute?.("open");
      openWorkspaceReportReader(button.dataset.reportPreview, { opener: button });
    });
  });
  target.querySelectorAll("[data-report-attach]").forEach(button => {
    if (!serveMode()) return;
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      attachWorkspaceReport(button);
    });
  });
}

async function attachWorkspaceReport(button) {
  const sourceKeys = visibleSelectedSourceKeys();
  if (!sourceKeys.length) return;
  button.disabled = true;
  try {
    const pickerPayload = await serveApi("/api/path-picker", {
      method: "POST",
      body: { multiple: false }
    });
    const path = listValue(pickerPayload?.paths).map(value => String(value || "").trim()).find(Boolean);
    if (!path) return;
    const payload = await serveApi("/api/reports", {
      method: "POST",
      body: { path, source_keys: sourceKeys }
    });
    applyWorkspaceReportCatalog(payload?.reports || []);
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

function bindWorkspaceReportGlobalControls() {
  document.querySelectorAll("[data-report-manager-open]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      openWorkspaceReportManager(button);
    });
  });
  document.querySelectorAll("[data-report-manager-close]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      closeWorkspaceReportManager();
    });
  });
  const manager = document.querySelector("[data-report-manager]");
  manager?.addEventListener?.("click", event => {
    if (event.target === manager) closeWorkspaceReportManager();
  });
}

function workspaceReportManagerOpen() {
  const manager = document.querySelector("[data-report-manager]");
  return Boolean(manager && !manager.hidden);
}

function openWorkspaceReportManager(opener = null) {
  const manager = document.querySelector("[data-report-manager]");
  if (!manager) return;
  closeServeSourceManager();
  closeWorkspaceReportReader({ restoreFocus: false });
  state.selectedStep = null;
  renderStepDrawer();
  if (!workspaceReportForId(state.reportManager.selectedId)) {
    state.reportManager.selectedId = workspaceReports()[0]?.report_id || null;
    syncWorkspaceReportDraft();
  }
  openModalSurface(manager, {
    opener,
    bodyClass: "report-manager-open",
    focusTarget: manager.querySelector("[data-report-manager-close]"),
  });
  renderWorkspaceReportManager();
  loadWorkspaceReportManagerData();
}

async function loadWorkspaceReportManagerData(changes = {}) {
  if (typeof URLSearchParams !== "function" || typeof fetch !== "function") return;
  state.reportManager.loading = true;
  setWorkspaceReportManagerStatus("");
  renderWorkspaceReportManager();
  state.reportManager.page = Math.max(1, Number(changes.page || state.reportManager.page || 1));
  const params = new URLSearchParams({
    state: "all",
    surface: "sources",
    page: String(state.reportManager.page),
    page_size: "100",
    search: state.reportManager.search || "",
    sort: "last_turn_end",
    direction: "desc"
  });
  try {
    const [reportsPayload, page] = await Promise.all([
      serveApi("/api/reports"),
      serveApi(`/api/catalog?${params.toString()}`)
    ]);
    applyWorkspaceReportCatalog(reportsPayload?.reports || []);
    state.reportManager.pageData = page;
    state.reportManager.sourceRows = listValue(page?.items).filter(source => source?.readable !== false);
    state.reportManager.loading = false;
    setWorkspaceReportManagerStatus("");
    renderWorkspaceReportManager();
  } catch (error) {
    state.reportManager.loading = false;
    setWorkspaceReportManagerStatus(error.message || String(error), true);
    renderWorkspaceReportManager();
  }
}

function closeWorkspaceReportManager(options = {}) {
  const manager = document.querySelector("[data-report-manager]");
  return closeModalSurface(manager, options);
}

function syncWorkspaceReportDraft() {
  const report = workspaceReportForId(state.reportManager.selectedId);
  state.reportManager.draftBindings = new Set(report?.source_keys || []);
  state.reportManager.dirty = false;
}

function workspaceReportBindingsChanged() {
  const persisted = new Set(workspaceReportForId(state.reportManager.selectedId)?.source_keys || []);
  const draft = state.reportManager.draftBindings;
  if (persisted.size !== draft.size) return true;
  return Array.from(draft).some(sourceKey => !persisted.has(sourceKey));
}

function selectWorkspaceReport(reportId) {
  const report = workspaceReportForId(reportId);
  if (!report) return;
  state.reportManager.selectedId = report.report_id;
  syncWorkspaceReportDraft();
  renderWorkspaceReportManager();
}

function renderWorkspaceReportManager() {
  const reports = workspaceReports();
  const manager = document.querySelector("[data-report-manager]");
  const inventory = document.querySelector("[data-report-inventory]");
  const count = document.querySelector("[data-report-count]");
  if (count) count.textContent = reportMessage("reports_count", "{count} reports", { count: reports.length });
  if (inventory) {
    inventory.innerHTML = state.reportManager.loading && !reports.length
      ? `<p class="report-manager-empty loading">${esc(t("loading", "Loading"))}</p>`
      : reports.length
        ? reports.map(renderWorkspaceReportInventoryItem).join("")
        : `<p class="report-manager-empty">${esc(t("report_no_reports", "No reports imported"))}</p>`;
  }
  renderWorkspaceReportBindings();
  manager?.setAttribute?.("aria-busy", state.reportManager.loading || state.reportManager.busy ? "true" : "false");
  if (state.reportManager.busy) {
    manager?.querySelectorAll?.("button:not([data-report-manager-close]),input")?.forEach(control => {
      control.disabled = true;
    });
  }
  bindWorkspaceReportManagerControls();
}

function renderWorkspaceReportInventoryItem(report) {
  const selected = report.report_id === state.reportManager.selectedId;
  return `<button class="report-inventory-item ${selected ? "selected" : ""}" type="button" data-report-inventory-id="${esc(report.report_id)}" ${selected ? 'aria-current="true"' : ""}>
    <strong>${esc(report.filename)}</strong>
    <span>${esc(report.format.toUpperCase())} &middot; ${esc(reportMessage("report_sessions_count", "{count} sessions", { count: report.source_keys.length }))}</span>
    <code>${esc(report.report_id)}</code>
  </button>`;
}

function renderWorkspaceReportBindings() {
  const target = document.querySelector("[data-report-bindings]");
  if (!target) return;
  target.setAttribute?.("aria-busy", state.reportManager.loading || state.reportManager.busy ? "true" : "false");
  if (state.reportManager.loading) {
    target.innerHTML = `<p class="report-manager-empty loading">${esc(t("loading", "Loading"))}</p>`;
    return;
  }
  const report = workspaceReportForId(state.reportManager.selectedId);
  if (!report) {
    target.innerHTML = `<p class="report-manager-empty">${esc(t("report_no_selection", "Select a report to manage its session bindings."))}</p>`;
    return;
  }
  const sources = filteredWorkspaceReportSources();
  const selectedCount = state.reportManager.draftBindings.size;
  const sourceRows = sources.length
    ? sources.map(renderWorkspaceReportBindingSource).join("")
    : `<p class="report-manager-empty">${esc(t("report_no_sessions", "No matching readable sessions"))}</p>`;
  target.innerHTML = `
    <div class="report-binding-summary">
      <div>
        <strong>${esc(report.filename)}</strong>
        <span>${esc(report.format.toUpperCase())} &middot; ${esc(report.report_id)}</span>
      </div>
      <div class="report-binding-actions">
        <button class="step-toggle-button" type="button" data-report-manager-preview="${esc(report.report_id)}">${esc(t("report_preview", "Preview"))}</button>
        <button class="step-toggle-button report-delete-button" type="button" data-report-delete="${esc(report.report_id)}">${esc(t("report_delete", "Delete report"))}</button>
      </div>
    </div>
    <label class="report-binding-search">
      <span>${esc(t("report_search_sessions", "Search active and archived sessions"))}</span>
      <input type="search" data-report-binding-search value="${esc(state.reportManager.search)}" placeholder="${esc(t("report_search_sessions", "Search active and archived sessions"))}">
    </label>
    <div class="report-binding-list" data-report-binding-list>${sourceRows}</div>
    <div class="report-binding-footer">
      <span data-report-binding-selection-count>${esc(reportMessage("report_sessions_count", "{count} sessions", { count: selectedCount }))}</span>
      <span class="catalog-page-controls">
        <button class="step-toggle-button" type="button" data-report-bindings-prev ${Number(state.reportManager.pageData?.page || 1) <= 1 ? "disabled" : ""}>‹</button>
        <span>${esc(reportBindingPageLabel())}</span>
        <button class="step-toggle-button" type="button" data-report-bindings-next ${reportBindingPageEnd() >= Number(state.reportManager.pageData?.total || 0) ? "disabled" : ""}>›</button>
      </span>
      <button class="step-toggle-button primary" type="button" data-report-bindings-save ${selectedCount && workspaceReportBindingsChanged() ? "" : "disabled"}>${esc(t("report_save_bindings", "Save bindings"))}</button>
    </div>`;
}

function reportBindingPageEnd() {
  const page = Number(state.reportManager.pageData?.page || 1);
  const size = Number(state.reportManager.pageData?.page_size || 100);
  return Math.min(Number(state.reportManager.pageData?.total || 0), page * size);
}

function reportBindingPageLabel() {
  const page = Number(state.reportManager.pageData?.page || 1);
  const size = Number(state.reportManager.pageData?.page_size || 100);
  const total = Number(state.reportManager.pageData?.total || 0);
  if (!total) return "0 / 0";
  return `${(page - 1) * size + 1}-${reportBindingPageEnd()} / ${total}`;
}

function readableWorkspaceReportSources() {
  if (state.reportManager.sourceRows.length || typeof fetch === "function") {
    return listValue(state.reportManager.sourceRows);
  }
  return readableServeSources("all");
}

function filteredWorkspaceReportSources() {
  const query = lower(state.reportManager.search).trim();
  if (!query) return readableWorkspaceReportSources();
  return readableWorkspaceReportSources().filter(source => workspaceReportSourceSearchText(source).includes(query));
}

function workspaceReportSourceSearchText(source) {
  return [
    sourceDisplayLabel(source),
    source?.label,
    source?.source_key,
    source?.trial_session_id,
    source?.session_id,
    sourceTagsFor(source).join(" "),
    source?.active === false ? t("serve_archived", "archived") : t("serve_active", "active")
  ].filter(Boolean).join(" ").toLowerCase();
}

function renderWorkspaceReportBindingSource(source) {
  const sourceKey = String(source?.source_key || "");
  const checked = state.reportManager.draftBindings.has(sourceKey);
  const session = source?.trial_session_id || source?.session_id || sourceKey;
  const stateLabel = source?.active === false ? t("serve_archived", "archived") : t("serve_active", "active");
  return `<label class="report-binding-row">
    <input type="checkbox" data-report-binding-key="${esc(sourceKey)}" ${checked ? "checked" : ""}>
    <span class="report-binding-row-main">
      <strong>${esc(sourceDisplayLabel(source))}</strong>
      <code>${esc(session)}</code>
    </span>
    <span class="report-binding-tags">${renderReadOnlySourceTags(source)}</span>
    <span class="report-binding-state ${source?.active === false ? "archived" : ""}">${esc(stateLabel)}</span>
  </label>`;
}

function bindWorkspaceReportManagerControls() {
  const manager = document.querySelector("[data-report-manager]");
  if (!manager || manager.hidden) return;
  manager.querySelectorAll?.("[data-report-inventory-id]").forEach(button => {
    button.addEventListener("click", () => selectWorkspaceReport(button.dataset.reportInventoryId));
  });
  manager.querySelectorAll?.("[data-report-manager-preview]").forEach(button => {
    button.addEventListener("click", () => {
      const reportId = button.dataset.reportManagerPreview;
      closeWorkspaceReportManager({ restoreFocus: false });
      openWorkspaceReportReader(reportId, {
        opener: document.querySelector("[data-report-manager-open]")
      });
    });
  });
  manager.querySelectorAll?.("[data-report-delete]").forEach(button => {
    button.addEventListener("click", () => deleteWorkspaceReport(button.dataset.reportDelete));
  });
  bindWorkspaceReportBindingControls(manager);
}

function bindWorkspaceReportBindingControls(manager = document.querySelector("[data-report-manager]")) {
  if (!manager || manager.hidden) return;
  manager.querySelectorAll?.("[data-report-binding-key]").forEach(input => {
    input.addEventListener("change", () => {
      const sourceKey = input.dataset.reportBindingKey;
      if (input.checked) state.reportManager.draftBindings.add(sourceKey);
      else state.reportManager.draftBindings.delete(sourceKey);
      state.reportManager.dirty = workspaceReportBindingsChanged();
      syncWorkspaceReportBindingSelectionControls(manager);
    });
  });
  const search = manager.querySelector?.("[data-report-binding-search]");
  search?.addEventListener?.("input", () => {
    state.reportManager.search = String(search.value || "");
    clearTimeout(state.reportManager.searchTimer);
    state.reportManager.searchTimer = setTimeout(() => {
      loadWorkspaceReportManagerData({ page: 1 });
      focusWorkspaceReportSearch();
    }, 150);
  });
  manager.querySelector?.("[data-report-bindings-prev]")?.addEventListener?.("click", () => {
    loadWorkspaceReportManagerData({ page: Math.max(1, Number(state.reportManager.page || 1) - 1) });
  });
  manager.querySelector?.("[data-report-bindings-next]")?.addEventListener?.("click", () => {
    loadWorkspaceReportManagerData({ page: Number(state.reportManager.page || 1) + 1 });
  });
  manager.querySelector?.("[data-report-bindings-save]")?.addEventListener?.("click", saveWorkspaceReportBindings);
}

function syncWorkspaceReportBindingSelectionControls(manager = document.querySelector("[data-report-manager]")) {
  if (!manager) return;
  const selectedCount = state.reportManager.draftBindings.size;
  const count = manager.querySelector?.("[data-report-binding-selection-count]");
  if (count) count.textContent = reportMessage("report_sessions_count", "{count} sessions", { count: selectedCount });
  const save = manager.querySelector?.("[data-report-bindings-save]");
  if (save) save.disabled = !selectedCount || !workspaceReportBindingsChanged() || state.reportManager.busy;
}

function focusWorkspaceReportSearch() {
  const input = document.querySelector("[data-report-binding-search]");
  if (!input) return;
  input.focus?.();
  const end = String(input.value || "").length;
  input.setSelectionRange?.(end, end);
}

async function saveWorkspaceReportBindings() {
  const reportId = state.reportManager.selectedId;
  const sourceKeys = Array.from(state.reportManager.draftBindings);
  if (!reportId || !sourceKeys.length || !workspaceReportBindingsChanged()) return;
  if (state.reportManager.busy) return;
  state.reportManager.busy = true;
  renderWorkspaceReportManager();
  try {
    const payload = await serveApi(`/api/reports/${encodeURIComponent(reportId)}/bindings`, {
      method: "POST",
      body: { source_keys: sourceKeys }
    });
    state.reportManager.dirty = false;
    applyWorkspaceReportCatalog(payload?.reports || []);
    renderComparisonPanels({ trace: false });
    setWorkspaceReportManagerStatus(t("report_bindings_saved", "Report bindings saved"));
  } catch (error) {
    setWorkspaceReportManagerStatus(error.message || String(error), true);
  } finally {
    state.reportManager.busy = false;
    renderWorkspaceReportManager();
  }
}

async function deleteWorkspaceReport(reportId) {
  const report = workspaceReportForId(reportId);
  if (!report) return;
  const prompt = reportMessage("report_delete_confirm", "Permanently delete {filename}?", { filename: report.filename });
  if (typeof window.confirm === "function" && !window.confirm(prompt)) return;
  if (state.reportManager.busy) return;
  state.reportManager.busy = true;
  renderWorkspaceReportManager();
  try {
    const payload = await serveApi(`/api/reports/${encodeURIComponent(report.report_id)}/delete`, {
      method: "POST",
      body: {}
    });
    if (state.reportReader.openId === report.report_id) closeWorkspaceReportReader({ restoreFocus: false });
    state.reportManager.selectedId = null;
    state.reportManager.dirty = false;
    applyWorkspaceReportCatalog(payload?.reports || []);
    renderComparisonPanels({ trace: false });
    setWorkspaceReportManagerStatus(t("report_deleted", "Report deleted"));
  } catch (error) {
    setWorkspaceReportManagerStatus(error.message || String(error), true);
  } finally {
    state.reportManager.busy = false;
    renderWorkspaceReportManager();
  }
}

function setWorkspaceReportManagerStatus(message, error = false) {
  const target = document.querySelector("[data-report-manager-status]");
  if (!target) return;
  target.textContent = message || "";
  target.classList.toggle("danger", Boolean(error));
  target.classList.toggle("loading", Boolean(state.reportManager.loading));
  target.hidden = !message;
}

function openWorkspaceReportReader(reportId, options = {}) {
  const report = workspaceReportForId(reportId);
  if (!report) return false;
  closeWorkspaceReportManager({ restoreFocus: false });
  state.reportReader.openId = report.report_id;
  state.reportReader.opener = options.opener || document.activeElement || null;
  state.selectedStep = null;
  renderStepDrawer();
  renderWorkspaceReportReader();
  return true;
}

function renderWorkspaceReportReader() {
  const target = $("workspace-report-reader");
  const report = workspaceReportForId(state.reportReader.openId);
  if (!target || !report) return;
  disconnectWorkspaceReportPreviewObserver();
  const previewUrl = workspaceSnapshotMode() ? workspaceSnapshotReportPreviewUrl(report) : workspaceReportPreviewPath(report);
  const openTab = workspaceSnapshotMode() ? "" : `<a class="report-reader-open-tab" data-report-reader-open-tab href="${workspaceReportOpenPath(report)}" target="_blank" rel="noopener">${esc(t("report_open_new_tab", "Open in new tab"))}</a>`;
  const fitAttribute = report.format === "html" ? " data-report-preview-fit" : "";
  target.innerHTML = `<div class="report-reader-panel" role="dialog" aria-modal="false" aria-labelledby="report-reader-title">
    <header class="report-reader-head">
      <div>
        <p class="eyebrow">${esc(t("report_reader_label", "Report preview"))}</p>
        <h2 id="report-reader-title">${esc(report.filename)}</h2>
        <p class="copy">${esc(report.format.toUpperCase())} &middot; ${esc(reportMessage("report_sessions_count", "{count} sessions", { count: report.source_keys.length }))}</p>
      </div>
      <div class="report-reader-actions">
        ${openTab}
        <button class="report-reader-close" type="button" data-report-reader-close aria-label="${esc(t("close", "Close"))}">${esc(t("close", "Close"))}</button>
      </div>
    </header>
    <div class="report-reader-frame-viewport" data-report-reader-viewport${fitAttribute}>
      <iframe class="report-reader-frame" data-report-reader-frame src="${esc(previewUrl)}" title="${esc(report.filename)}" sandbox="allow-scripts" referrerpolicy="no-referrer"></iframe>
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

function workspaceSnapshotReportPreviewUrl(report) {
  if (state.reportReader.objectUrl) URL.revokeObjectURL?.(state.reportReader.objectUrl);
  const binary = atob(report.preview_base64 || "");
  const bytes = Uint8Array.from(binary, character => character.charCodeAt(0));
  state.reportReader.objectUrl = URL.createObjectURL(new Blob([bytes], { type: "text/html; charset=utf-8" }));
  return state.reportReader.objectUrl;
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
  if (state.reportReader.objectUrl) URL.revokeObjectURL?.(state.reportReader.objectUrl);
  state.reportReader.objectUrl = null;
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
  bindWorkspaceReportBindingControls,
  bindWorkspaceReportGlobalControls,
  bindWorkspaceReportLeaderboardControls,
  bindWorkspaceReportManagerControls,
  bindWorkspaceReportReaderControls,
  closeWorkspaceReportManager,
  closeWorkspaceReportReader,
  currentWorkspaceReportReaderWidth,
  deleteWorkspaceReport,
  filteredWorkspaceReportSources,
  fitWorkspaceReportReaderPreview,
  focusSoon,
  focusWorkspaceReportSearch,
  loadWorkspaceReportManagerData,
  normalizedWorkspaceReports,
  openWorkspaceReportManager,
  openWorkspaceReportReader,
  readableWorkspaceReportSources,
  renderAttachWorkspaceReportAction,
  renderWorkspaceReportBindingSource,
  renderWorkspaceReportBindings,
  renderWorkspaceReportCell,
  renderWorkspaceReportInventoryItem,
  renderWorkspaceReportManager,
  renderWorkspaceReportReader,
  reportBindingPageEnd,
  reportBindingPageLabel,
  reportMessage,
  reportReaderMaximumWidth,
  reportReaderPreviewGeometry,
  reportReaderViewportWidth,
  reportsForSourceKey,
  saveWorkspaceReportBindings,
  selectWorkspaceReport,
  setWorkspaceReportManagerStatus,
  setWorkspaceReportReaderWidth,
  syncWorkspaceReportBindingSelectionControls,
  syncWorkspaceReportDraft,
  syncWorkspaceReportReaderResizeHandle,
  workspaceReportBindingsChanged,
  workspaceReportForId,
  workspaceReportLeaderboardColumn,
  workspaceReportManagerOpen,
  workspaceReportOpenPath,
  workspaceReportPreviewPath,
  workspaceReportSourceSearchText,
  workspaceReports,
  workspaceSnapshotReportPreviewUrl,
};
