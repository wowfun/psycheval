function reportMessage(key, fallback, values = {}) {
  let message = String(t(key, fallback));
  Object.entries(values).forEach(([name, value]) => {
    message = message.replaceAll(`{${name}}`, String(value));
  });
  return message;
}

function normalizedWorkspaceReports(reports = state.workspaceReports) {
  return listValue(reports)
    .filter(report => report && report.report_id && report.filename)
    .map(report => ({
      report_id: String(report.report_id),
      filename: String(report.filename),
      format: lower(report.format) === "html" ? "html" : "markdown",
      source_keys: Array.from(new Set(listValue(report.source_keys).map(key => String(key || "").trim()).filter(Boolean)))
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
    width: "170px",
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
  if (!serveMode() || !target) return;
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
  state.reportManager.opener = opener || document.activeElement || null;
  if (!workspaceReportForId(state.reportManager.selectedId)) {
    state.reportManager.selectedId = workspaceReports()[0]?.report_id || null;
    syncWorkspaceReportDraft();
  }
  manager.hidden = false;
  document.body.classList.add("report-manager-open");
  renderWorkspaceReportManager();
  focusSoon(manager.querySelector?.("[data-report-manager-close]"));
}

function closeWorkspaceReportManager(options = {}) {
  const manager = document.querySelector("[data-report-manager]");
  if (!manager || manager.hidden) return false;
  manager.hidden = true;
  document.body.classList.remove("report-manager-open");
  const opener = state.reportManager.opener;
  state.reportManager.opener = null;
  if (options.restoreFocus !== false) focusSoon(opener);
  return true;
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
  const inventory = document.querySelector("[data-report-inventory]");
  const count = document.querySelector("[data-report-count]");
  if (count) count.textContent = reportMessage("reports_count", "{count} reports", { count: reports.length });
  if (inventory) {
    inventory.innerHTML = reports.length
      ? reports.map(renderWorkspaceReportInventoryItem).join("")
      : `<p class="report-manager-empty">${esc(t("report_no_reports", "No reports imported"))}</p>`;
  }
  renderWorkspaceReportBindings();
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
      <span>${esc(reportMessage("report_sessions_count", "{count} sessions", { count: selectedCount }))}</span>
      <button class="step-toggle-button primary" type="button" data-report-bindings-save ${selectedCount && workspaceReportBindingsChanged() ? "" : "disabled"}>${esc(t("report_save_bindings", "Save bindings"))}</button>
    </div>`;
}

function readableWorkspaceReportSources() {
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
      renderWorkspaceReportBindings();
      bindWorkspaceReportBindingControls(manager);
    });
  });
  const search = manager.querySelector?.("[data-report-binding-search]");
  search?.addEventListener?.("input", () => {
    state.reportManager.search = String(search.value || "");
    renderWorkspaceReportBindings();
    bindWorkspaceReportBindingControls(manager);
    focusWorkspaceReportSearch();
  });
  manager.querySelector?.("[data-report-bindings-save]")?.addEventListener?.("click", saveWorkspaceReportBindings);
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
  }
}

async function deleteWorkspaceReport(reportId) {
  const report = workspaceReportForId(reportId);
  if (!report) return;
  const prompt = reportMessage("report_delete_confirm", "Permanently delete {filename}?", { filename: report.filename });
  if (typeof window.confirm === "function" && !window.confirm(prompt)) return;
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
  }
}

function setWorkspaceReportManagerStatus(message, error = false) {
  const target = document.querySelector("[data-report-manager-status]");
  if (!target) return;
  target.textContent = message;
  target.classList.toggle("danger", Boolean(error));
  target.hidden = false;
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
  target.innerHTML = `<div class="report-reader-panel" role="dialog" aria-modal="false" aria-labelledby="report-reader-title">
    <header class="report-reader-head">
      <div>
        <p class="eyebrow">${esc(t("report_reader_label", "Report preview"))}</p>
        <h2 id="report-reader-title">${esc(report.filename)}</h2>
        <p class="copy">${esc(report.format.toUpperCase())} &middot; ${esc(reportMessage("report_sessions_count", "{count} sessions", { count: report.source_keys.length }))}</p>
      </div>
      <button class="report-reader-close" type="button" data-report-reader-close aria-label="${esc(t("close", "Close"))}">${esc(t("close", "Close"))}</button>
    </header>
    <iframe class="report-reader-frame" src="/api/reports/${encodeURIComponent(report.report_id)}/preview" title="${esc(report.filename)}" sandbox="allow-scripts" referrerpolicy="no-referrer"></iframe>
  </div>`;
  target.hidden = false;
  document.body.classList.add("report-reader-open");
  target.querySelectorAll?.("[data-report-reader-close]").forEach(button => {
    button.addEventListener("click", () => closeWorkspaceReportReader());
  });
  focusSoon(target.querySelector?.("[data-report-reader-close]"));
}

function closeWorkspaceReportReader(options = {}) {
  const target = $("workspace-report-reader");
  if (!state.reportReader.openId && (!target || target.hidden)) return false;
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

function focusSoon(target) {
  if (!target || typeof target.focus !== "function") return;
  const apply = () => target.focus();
  if (typeof requestAnimationFrame === "function") requestAnimationFrame(apply);
  else apply();
}
