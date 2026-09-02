// @ts-check

import { bindDataTableEditors } from "./data-tables.js";
import {
  applyEvaluationReportPage,
  evaluationReportForRef,
  evaluationReportStore,
} from "./evaluation-report-store.js";
import { serveApi } from "./http.js";
import {
  applyReportCatalog,
  reportBindingsChanged,
  reportForId,
  reportStore,
  syncReportDraft,
} from "./report-store.js";
import { createReportSidebarAdapter } from "./report-sidebar.js";
import { adminMode, esc, listValue, t } from "./shared.js";

let boundUnload = false;
let evaluationLoadGeneration = 0;
let importedLoadGeneration = 0;
let reportPreviewController = null;

function reportPreviewSurface() {
  if (!reportPreviewController) {
    reportPreviewController = createReportSidebarAdapter({
      ownerId: "reports-page-preview",
      onRequestClose: options => closeReportPreview({ restoreFocus: options.restoreFocus }),
    });
  }
  return reportPreviewController;
}

async function initializeReportManagerPage() {
  bindReportManagerPage();
  await loadReportManagerPage();
}

async function loadReportManagerPage() {
  setStatus("");
  await Promise.all([loadEvaluationReports(), loadImportedReports()]);
}

async function loadEvaluationReports(changes = {}) {
  const generation = ++evaluationLoadGeneration;
  const manager = evaluationReportStore.manager;
  manager.loading = true;
  manager.page = Math.max(1, Number(changes.page || manager.page || 1));
  renderReportManagerPage();
  const params = new URLSearchParams({
    page: String(manager.page),
    page_size: "100",
    search: manager.search || "",
  });
  try {
    const page = await serveApi(`/api/evaluation-reports?${params.toString()}`);
    if (generation !== evaluationLoadGeneration) return;
    applyEvaluationReportPage(page);
    manager.loading = false;
    syncActiveReport();
    renderReportManagerPage();
  } catch (error) {
    if (generation !== evaluationLoadGeneration) return;
    manager.loading = false;
    setStatus(error.message || String(error), true);
    renderReportManagerPage();
    throw error;
  }
}

async function loadImportedReports(changes = {}) {
  const generation = ++importedLoadGeneration;
  const manager = reportStore.manager;
  manager.loading = true;
  manager.page = Math.max(1, Number(changes.page || manager.page || 1));
  renderReportManagerPage();
  try {
    if (!adminMode()) {
      const reports = await serveApi("/api/reports");
      if (generation !== importedLoadGeneration) return;
      applyReportCatalog(Array.isArray(reports) ? reports : []);
      manager.sourceRows = [];
      manager.pageData = { page: 1, page_size: 100, total: 0 };
    } else {
      const params = new URLSearchParams({
        state: "all",
        surface: "sources",
        page: String(manager.page),
        page_size: "100",
        search: manager.search || "",
        sort: "last_turn_end",
        direction: "desc",
      });
      const [reports, page] = await Promise.all([
        serveApi("/api/reports"),
        serveApi(`/api/catalog?${params.toString()}`),
      ]);
      if (generation !== importedLoadGeneration) return;
      applyReportCatalog(Array.isArray(reports) ? reports : []);
      manager.pageData = /** @type {any} */ (page);
      manager.sourceRows = listValue(page?.items).filter(source => source?.readable !== false);
    }
    manager.loading = false;
    syncActiveReport();
    renderReportManagerPage();
  } catch (error) {
    if (generation !== importedLoadGeneration) return;
    manager.loading = false;
    setStatus(error.message || String(error), true);
    renderReportManagerPage();
    throw error;
  }
}

function bindReportManagerPage() {
  const root = document.querySelector("[data-report-manager]");
  if (!root || root.getAttribute("data-page-bound") === "true") return;
  root.setAttribute("data-page-bound", "true");
  root.querySelector("[data-report-manager-reload]")?.addEventListener("click", () => {
    void loadReportManagerPage();
  });
  root.querySelector("[data-evaluation-report-search]")?.addEventListener("input", event => {
    evaluationReportStore.manager.search = /** @type {HTMLInputElement} */ (event.currentTarget).value;
    clearTimeout(evaluationReportStore.manager.searchTimer);
    evaluationReportStore.manager.searchTimer = setTimeout(
      () => void loadEvaluationReports({ page: 1 }),
      150,
    );
  });
  root.querySelector("[data-report-page-search]")?.addEventListener("input", event => {
    reportStore.manager.search = /** @type {HTMLInputElement} */ (event.currentTarget).value;
    clearTimeout(reportStore.manager.searchTimer);
    reportStore.manager.searchTimer = setTimeout(() => void loadImportedReports({ page: 1 }), 150);
  });
  document.addEventListener("keydown", event => {
    if (event.defaultPrevented || event.key !== "Escape") return;
    if (closeReportPreview()) event.preventDefault();
  });
  window.addEventListener("peval:workspace-navigate", () => {
    closeReportPreview({ restoreFocus: false });
  });
  if (!boundUnload) {
    boundUnload = true;
    window.addEventListener("beforeunload", event => {
      if (!reportBindingsChanged()) return;
      event.preventDefault();
      event.returnValue = "";
    });
  }
}

function renderReportManagerPage() {
  const root = document.querySelector("[data-report-manager]");
  const evaluationInventory = root?.querySelector?.("[data-evaluation-report-inventory]");
  const importedInventory = root?.querySelector?.("[data-report-inventory]");
  const bindings = root?.querySelector?.("[data-report-bindings]");
  if (!root || !evaluationInventory || !importedInventory || !bindings) return;
  renderEvaluationInventory(evaluationInventory);
  renderImportedInventory(importedInventory);
  renderBindings(bindings);
  root.setAttribute(
    "aria-busy",
    evaluationReportStore.manager.loading || reportStore.manager.loading || reportStore.manager.busy
      ? "true"
      : "false",
  );
  bindRenderedControls(root);
}

function renderEvaluationInventory(target) {
  const manager = evaluationReportStore.manager;
  const reports = evaluationReportStore.reports;
  const count = document.querySelector("[data-evaluation-report-count]");
  const search = document.querySelector("[data-evaluation-report-search]");
  if (count) {
    count.textContent = `${manager.pageData.total} ${t("evaluation_reports", "Evaluation reports")}`;
  }
  if (search && document.activeElement !== search) {
    /** @type {HTMLInputElement} */ (search).value = manager.search;
  }
  const items = reports.map(report => reportInventoryCard({
    reportRef: report.report_ref,
    title: report.title,
    meta: `${report.filename} · ${report.source_keys.length}`,
    code: report.source_label,
    selectAttribute: "data-evaluation-report-select",
    sourceKey: report.primary_source_key,
  })).join("");
  target.innerHTML = items || `<p class="report-manager-empty${manager.loading ? " loading" : ""}">${esc(
    manager.loading
      ? t("loading", "Loading")
      : t("evaluation_report_empty", "No evaluation reports available"),
  )}</p>`;
  const pagination = document.querySelector("[data-evaluation-report-pagination]");
  if (pagination) {
    pagination.innerHTML = `
      <button class="action-button icon-only" type="button" data-evaluation-report-prev ${manager.page <= 1 ? "disabled" : ""}>‹</button>
      <span>${esc(pageLabel(manager.pageData))}</span>
      <button class="action-button icon-only" type="button" data-evaluation-report-next ${pageEnd(manager.pageData) >= manager.pageData.total ? "disabled" : ""}>›</button>`;
  }
}

function renderImportedInventory(target) {
  const reports = reportStore.reports;
  const count = document.querySelector("[data-report-count]");
  if (count) count.textContent = `${reports.length} ${t("imported_reports", "Imported reports")}`;
  target.innerHTML = reports.length
    ? reports.map(report => reportInventoryCard({
      reportRef: report.report_ref,
      reportId: report.report_id,
      title: report.filename,
      meta: `${report.format.toUpperCase()} · ${report.source_keys.length}`,
      code: report.report_id,
      selectAttribute: "data-report-page-select",
    })).join("")
    : `<p class="report-manager-empty${reportStore.manager.loading ? " loading" : ""}">${esc(
      reportStore.manager.loading ? t("loading", "Loading") : t("report_no_reports", "No reports imported"),
    )}</p>`;
}

function reportInventoryCard({ reportRef, reportId = "", title, meta, code, selectAttribute, sourceKey = "" }) {
  const selected = evaluationReportStore.activeRef === reportRef;
  const encodedRef = encodeURIComponent(reportRef);
  const viewSource = sourceKey
    ? `<a class="action-button compact" href="/#source=${encodeURIComponent(sourceKey)}" data-workspace-route="home" data-report-view-source="${esc(reportRef)}">${esc(t("report_view_source", "View source"))}</a>`
    : "";
  return `<article class="report-inventory-item report-inventory-card${selected ? " selected" : ""}">
    <button class="report-inventory-select" type="button" ${selectAttribute}="${esc(reportId || reportRef)}" data-report-ref="${esc(reportRef)}">
      <strong>${esc(title)}</strong>
      <span>${esc(meta)}</span>
      <code>${esc(code)}</code>
    </button>
    <div class="report-inventory-actions">
      <button class="action-button compact" type="button" data-report-page-preview="${esc(reportRef)}">${esc(t("report_preview", "Preview"))}</button>
      <a class="action-button compact" href="/api/report-library/${encodedRef}/reader" target="_blank" rel="noopener" data-report-open="${esc(reportRef)}">${esc(t("report_open", "Open"))}</a>
      ${viewSource}
    </div>
  </article>`;
}

function renderBindings(target) {
  if (!adminMode()) {
    target.replaceChildren();
    return;
  }
  const manager = reportStore.manager;
  const report = reportForId(manager.selectedId);
  const searchControl = document.querySelector("[data-report-page-search-control]");
  const search = document.querySelector("[data-report-page-search]");
  searchControl?.toggleAttribute("hidden", !report);
  if (search && document.activeElement !== search) {
    /** @type {HTMLInputElement} */ (search).value = manager.search;
  }
  if (manager.loading) {
    target.innerHTML = `<p class="report-manager-empty loading">${esc(t("loading", "Loading"))}</p>`;
    return;
  }
  if (!report) {
    target.innerHTML = `<p class="report-manager-empty">${esc(t("report_no_selection", "Select an imported report to manage its session bindings."))}</p>`;
    return;
  }
  const rows = manager.sourceRows.map(source => {
    const key = String(source?.source_key || "");
    const session = source?.trial_session_id || source?.session_id || key;
    const label = source?.source_alias || source?.label || key;
    const category = sourceCategoryValue(source);
    return `<div class="report-binding-row" data-report-page-row data-table-row-key="${esc(key)}">
      <input type="checkbox" data-report-page-binding="${esc(key)}" ${manager.draftBindings.has(key) ? "checked" : ""}>
      <span class="report-binding-row-main"><strong>${esc(label)}</strong><code>${esc(session)}</code></span>
      <span class="report-binding-category table-value-text table-cell-editable" data-table-column-key="source_category" data-value-type="text" tabindex="0" aria-keyshortcuts="Enter" title="${esc(category)}" aria-label="${esc(`${t("category", "Category")}: ${category}`)}">${renderSourceCategory(source)}</span>
      <span class="report-binding-state${source?.active === false ? " archived" : ""}">${esc(
        source?.active === false ? t("serve_archived", "archived") : t("serve_active", "active"),
      )}</span>
    </div>`;
  }).join("");
  target.innerHTML = `
    <div class="report-binding-summary">
      <div><strong>${esc(report.filename)}</strong><span>${esc(report.format.toUpperCase())} · ${esc(report.report_id)}</span></div>
      <div class="report-binding-actions">
        <button class="action-button danger" type="button" data-report-page-delete="${esc(report.report_id)}">${esc(t("report_delete", "Delete report"))}</button>
      </div>
    </div>
    <div class="report-binding-list" data-table-id="report-bindings">${rows || `<p class="report-manager-empty">${esc(t("report_no_sessions", "No matching readable sessions"))}</p>`}</div>
    <div class="report-binding-footer">
      <span>${manager.draftBindings.size}</span>
      <span class="catalog-page-controls">
        <button class="action-button icon-only" type="button" data-report-page-prev ${manager.page <= 1 ? "disabled" : ""}>‹</button>
        <span>${esc(pageLabel(manager.pageData))}</span>
        <button class="action-button icon-only" type="button" data-report-page-next ${pageEnd(manager.pageData) >= Number(manager.pageData?.total || 0) ? "disabled" : ""}>›</button>
      </span>
      <button class="action-button primary" type="button" data-report-page-save ${reportBindingsChanged() ? "" : "disabled"}>${esc(t("report_save_bindings", "Save bindings"))}</button>
    </div>`;
}

function bindRenderedControls(root) {
  root.querySelectorAll("[data-evaluation-report-select]").forEach(button => {
    button.addEventListener("click", () => {
      selectActiveReport(button.getAttribute("data-report-ref"));
    });
  });
  root.querySelectorAll("[data-report-page-select]").forEach(button => {
    button.addEventListener("click", () => {
      reportStore.manager.selectedId = button.getAttribute("data-report-page-select");
      syncReportDraft();
      selectActiveReport(button.getAttribute("data-report-ref"));
    });
  });
  root.querySelectorAll("[data-report-page-binding]").forEach(input => {
    input.addEventListener("change", () => {
      const key = input.getAttribute("data-report-page-binding");
      if (!key) return;
      if (/** @type {HTMLInputElement} */ (input).checked) reportStore.manager.draftBindings.add(key);
      else reportStore.manager.draftBindings.delete(key);
      reportStore.manager.dirty = reportBindingsChanged();
      root.querySelector("[data-report-page-save]")?.toggleAttribute("disabled", !reportStore.manager.dirty);
    });
  });
  root.querySelectorAll("[data-report-page-row]").forEach(row => {
    row.addEventListener("click", event => {
      if (event.defaultPrevented || event.target?.closest?.("input,button,a,select,textarea,[data-table-column-key]")) return;
      const input = row.querySelector("[data-report-page-binding]");
      if (!input || input.disabled) return;
      input.checked = !input.checked;
      input.dispatchEvent(new window.Event("change"));
      input.focus();
    });
  });
  bindDataTableEditors(root, {
    tableId: "report-bindings",
    columns: [reportCategoryColumn()],
    rows: reportStore.manager.sourceRows,
    rowKey: source => source?.source_key,
    onChange: () => refreshCategoryCells(root),
  });
  root.querySelector("[data-evaluation-report-prev]")?.addEventListener("click", () => {
    void loadEvaluationReports({ page: Math.max(1, evaluationReportStore.manager.page - 1) });
  });
  root.querySelector("[data-evaluation-report-next]")?.addEventListener("click", () => {
    void loadEvaluationReports({ page: evaluationReportStore.manager.page + 1 });
  });
  root.querySelector("[data-report-page-prev]")?.addEventListener("click", () => {
    void loadImportedReports({ page: Math.max(1, reportStore.manager.page - 1) });
  });
  root.querySelector("[data-report-page-next]")?.addEventListener("click", () => {
    void loadImportedReports({ page: reportStore.manager.page + 1 });
  });
  root.querySelector("[data-report-page-save]")?.addEventListener("click", () => void saveBindings());
  root.querySelector("[data-report-page-delete]")?.addEventListener("click", event => {
    void deleteReport(event.currentTarget?.getAttribute?.("data-report-page-delete"));
  });
  root.querySelectorAll("[data-report-page-preview]").forEach(button => {
    button.addEventListener("click", event => {
      const reportRef = event.currentTarget?.getAttribute?.("data-report-page-preview");
      selectActiveReport(reportRef, { render: false });
      renderActiveSelection(root);
      openReportPreview(reportRef, { opener: event.currentTarget });
    });
  });
  root.querySelectorAll("[data-report-open],[data-report-view-source]").forEach(link => {
    link.addEventListener("click", () => {
      selectActiveReport(
        link.getAttribute("data-report-open") || link.getAttribute("data-report-view-source"),
        { render: false },
      );
      renderActiveSelection(root);
    });
  });
}

function renderActiveSelection(root) {
  root.querySelectorAll(".report-inventory-card").forEach(card => {
    const reportRef = card.querySelector("[data-report-ref]")?.getAttribute("data-report-ref");
    card.classList.toggle("selected", reportRef === evaluationReportStore.activeRef);
  });
}

function sourceCategory(source) {
  return String(source?.source_category || "").trim();
}

function sourceCategoryValue(source) {
  return sourceCategory(source) || "-";
}

function renderSourceCategory(source) {
  const value = sourceCategory(source);
  return value ? `<span class="source-category-chip">${esc(value)}</span>` : `<span class="muted">-</span>`;
}

function reportCategoryColumn() {
  const suggestions = [...new Set(reportStore.manager.sourceRows.map(sourceCategory).filter(Boolean))];
  return {
    key: "source_category",
    label: t("category", "Category"),
    valueType: "text",
    value: sourceCategoryValue,
    edit: {
      value: sourceCategory,
      suggestions,
      async commit(source, value) {
        const sourceKey = String(source?.source_key || "");
        if (!sourceKey) throw new Error(t("source_edit_unavailable", "Source editing is unavailable"));
        const category = String(value || "").trim();
        await serveApi(`/api/sources/${encodeURIComponent(sourceKey)}`, {
          method: "PATCH",
          body: { category },
        });
        source.source_category = category || null;
        return { rowKey: sourceKey, source };
      },
    },
  };
}

function refreshCategoryCells(root) {
  const sourceByKey = new Map(reportStore.manager.sourceRows.map(source => [String(source?.source_key || ""), source]));
  root.querySelectorAll('[data-table-id="report-bindings"] [data-table-column-key="source_category"]').forEach(cell => {
    const key = cell.closest("[data-table-row-key]")?.getAttribute("data-table-row-key") || "";
    const source = sourceByKey.get(key);
    if (!source) return;
    const category = sourceCategoryValue(source);
    cell.innerHTML = renderSourceCategory(source);
    cell.setAttribute("title", category);
    cell.setAttribute("aria-label", `${t("category", "Category")}: ${category}`);
  });
}

async function saveBindings() {
  const manager = reportStore.manager;
  const reportId = manager.selectedId;
  if (!reportId || !reportBindingsChanged() || manager.busy) return;
  manager.busy = true;
  renderReportManagerPage();
  try {
    const updated = await serveApi(`/api/reports/${encodeURIComponent(reportId)}/bindings`, {
      method: "PUT",
      body: { source_keys: [...manager.draftBindings] },
    });
    applyReportCatalog([...reportStore.reports.filter(report => report.report_id !== reportId), updated]);
    manager.dirty = false;
    syncActiveReport();
    setStatus(t("report_bindings_saved", "Report bindings saved"));
  } catch (error) {
    setStatus(error.message || String(error), true);
  } finally {
    manager.busy = false;
    renderReportManagerPage();
  }
}

async function deleteReport(reportId) {
  const report = reportForId(reportId);
  if (!report || reportStore.manager.busy) return;
  if (!window.confirm(`${t("report_delete", "Delete report")}: ${report.filename}?`)) return;
  reportStore.manager.busy = true;
  try {
    await serveApi(`/api/reports/${encodeURIComponent(report.report_id)}`, { method: "DELETE" });
    reportStore.manager.selectedId = null;
    reportStore.manager.dirty = false;
    applyReportCatalog(reportStore.reports.filter(item => item.report_id !== report.report_id));
    syncActiveReport();
  } catch (error) {
    setStatus(error.message || String(error), true);
  } finally {
    reportStore.manager.busy = false;
    renderReportManagerPage();
  }
}

function packageReportForRef(reportRef) {
  const wanted = String(reportRef || "");
  return reportStore.reports.find(report => report.report_ref === wanted) || null;
}

function reportForRef(reportRef) {
  return evaluationReportForRef(reportRef) || packageReportForRef(reportRef);
}

function syncActiveReport() {
  if (reportForRef(evaluationReportStore.activeRef)) return;
  evaluationReportStore.activeRef = evaluationReportStore.reports[0]?.report_ref
    || reportStore.reports[0]?.report_ref
    || null;
}

function selectActiveReport(reportRef, options = {}) {
  const report = reportForRef(reportRef);
  if (!report) return false;
  evaluationReportStore.activeRef = report.report_ref;
  if (options.render !== false) renderReportManagerPage();
  return true;
}

function activeReportSnapshot() {
  const report = reportForRef(evaluationReportStore.activeRef);
  if (!report) return { report_ref: null, report_name: null };
  return {
    report_ref: report.report_ref,
    report_name: report.title || report.filename || report.report_ref,
  };
}

function openReportPreview(reportRef, options = {}) {
  const report = reportForRef(reportRef);
  const target = document.getElementById("workspace-report-reader");
  if (!report || !target) return false;
  const title = report.title || report.filename || report.report_ref;
  const encodedRef = encodeURIComponent(report.report_ref);
  const content = `<div class="report-reader-panel" role="dialog" aria-modal="false">
    <header class="report-reader-head"><div><h2>${esc(title)}</h2></div><div class="report-reader-actions">
      <a class="action-button compact" href="/api/report-library/${encodedRef}/reader" target="_blank" rel="noopener">${esc(t("report_open_new_tab", "Open in new tab"))}</a>
      <button class="action-button compact" type="button" data-sidebar-close>${esc(t("close", "Close"))}</button>
    </div></header>
    <div class="report-reader-frame-viewport"><iframe class="report-reader-frame" src="/api/report-library/${encodedRef}/preview" title="${esc(title)}" sandbox="allow-scripts" referrerpolicy="no-referrer"></iframe></div>
  </div>`;
  return reportPreviewSurface().open({
    render: () => { target.innerHTML = content; },
    opener: options.opener || document.activeElement || null,
    openerSelector: "[data-report-page-preview]",
    focusTarget: () => target.querySelector("[data-sidebar-close]"),
  });
}

function closeReportPreview(options = {}) {
  const target = document.getElementById("workspace-report-reader");
  if (!target || target.hidden) return false;
  if (!reportPreviewSurface().close({ restoreFocus: options.restoreFocus })) return false;
  target.replaceChildren();
  return true;
}

function pageEnd(pageData) {
  const page = Number(pageData?.page || 1);
  const size = Number(pageData?.page_size || 100);
  return Math.min(Number(pageData?.total || 0), page * size);
}

function pageLabel(pageData) {
  const page = Number(pageData?.page || 1);
  const size = Number(pageData?.page_size || 100);
  const total = Number(pageData?.total || 0);
  return total ? `${(page - 1) * size + 1}-${pageEnd(pageData)} / ${total}` : "0 / 0";
}

function setStatus(message, error = false) {
  const target = document.querySelector("[data-report-manager-status]");
  if (!target) return;
  target.textContent = message || "";
  target.classList.toggle("danger", Boolean(error));
  target.toggleAttribute("hidden", !message);
}

export {
  activeReportSnapshot,
  initializeReportManagerPage,
  loadEvaluationReports,
  loadImportedReports,
  loadReportManagerPage,
  openReportPreview,
  renderReportManagerPage,
};
