// @ts-check

import { serveApi } from "./http.js";
import { bindDataTableEditors } from "./data-tables.js";
import {
  applyReportCatalog,
  reportBindingsChanged,
  reportForId,
  reportStore,
  syncReportDraft,
} from "./report-store.js";
import { adminMode, esc, listValue, t } from "./shared.js";

let boundUnload = false;
let loadGeneration = 0;

async function initializeReportManagerPage() {
  bindReportManagerPage();
  await loadReportManagerPage();
}

async function loadReportManagerPage(changes = {}) {
  const generation = ++loadGeneration;
  const manager = reportStore.manager;
  manager.loading = true;
  manager.page = Math.max(1, Number(changes.page || manager.page || 1));
  setStatus("");
  renderReportManagerPage();
  try {
    if (!adminMode()) {
      const reports = await serveApi("/api/reports");
      if (generation !== loadGeneration) return;
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
      if (generation !== loadGeneration) return;
      applyReportCatalog(Array.isArray(reports) ? reports : []);
      manager.pageData = /** @type {any} */ (page);
      manager.sourceRows = listValue(page?.items).filter(source => source?.readable !== false);
    }
    manager.loading = false;
    renderReportManagerPage();
  } catch (error) {
    if (generation !== loadGeneration) return;
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
  root.querySelector("[data-report-page-search]")?.addEventListener("input", event => {
    reportStore.manager.search = /** @type {HTMLInputElement} */ (event.currentTarget).value;
    clearTimeout(reportStore.manager.searchTimer);
    reportStore.manager.searchTimer = setTimeout(() => void loadReportManagerPage({ page: 1 }), 150);
  });
  document.addEventListener("keydown", event => {
    if (event.defaultPrevented || event.key !== "Escape") return;
    if (closeReportPreview()) event.preventDefault();
  });
  window.addEventListener("peval:workspace-navigate", () => {
    closeReportPreview();
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
  const inventory = root?.querySelector?.("[data-report-inventory]");
  const bindings = root?.querySelector?.("[data-report-bindings]");
  const count = root?.querySelector?.("[data-report-count]");
  if (!root || !inventory || !bindings) return;
  const reports = reportStore.reports;
  if (count) count.textContent = `${reports.length} ${t("workspace_reports", "Reports")}`;
  inventory.innerHTML = reports.length
    ? reports.map(report => `
      <button class="report-inventory-item${report.report_id === reportStore.manager.selectedId ? " selected" : ""}"
        type="button" data-report-page-select="${esc(report.report_id)}">
        <strong>${esc(report.filename)}</strong>
        <span>${esc(report.format.toUpperCase())} · ${report.source_keys.length}</span>
        <code>${esc(report.report_id)}</code>
      </button>`).join("")
    : `<p class="report-manager-empty${reportStore.manager.loading ? " loading" : ""}">${esc(
      reportStore.manager.loading ? t("loading", "Loading") : t("report_no_reports", "No reports imported"),
    )}</p>`;
  renderBindings(bindings);
  root.setAttribute("aria-busy", reportStore.manager.loading || reportStore.manager.busy ? "true" : "false");
  bindRenderedControls(root);
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
    target.innerHTML = `<p class="report-manager-empty">${esc(t("report_no_selection", "Select a report to manage its session bindings."))}</p>`;
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
        <button class="action-button" type="button" data-report-page-preview="${esc(report.report_id)}">${esc(t("report_preview", "Preview"))}</button>
        <button class="action-button danger" type="button" data-report-page-delete="${esc(report.report_id)}">${esc(t("report_delete", "Delete report"))}</button>
      </div>
    </div>
    <div class="report-binding-list" data-table-id="report-bindings">${rows || `<p class="report-manager-empty">${esc(t("report_no_sessions", "No matching readable sessions"))}</p>`}</div>
    <div class="report-binding-footer">
      <span>${manager.draftBindings.size}</span>
      <span class="catalog-page-controls">
        <button class="action-button icon-only" type="button" data-report-page-prev ${manager.page <= 1 ? "disabled" : ""}>‹</button>
        <span>${esc(pageLabel())}</span>
        <button class="action-button icon-only" type="button" data-report-page-next ${pageEnd() >= Number(manager.pageData?.total || 0) ? "disabled" : ""}>›</button>
      </span>
      <button class="action-button primary" type="button" data-report-page-save ${reportBindingsChanged() ? "" : "disabled"}>${esc(t("report_save_bindings", "Save bindings"))}</button>
    </div>`;
}

function bindRenderedControls(root) {
  root.querySelectorAll("[data-report-page-select]").forEach(button => {
    button.addEventListener("click", () => {
      reportStore.manager.selectedId = button.getAttribute("data-report-page-select");
      syncReportDraft();
      renderReportManagerPage();
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
  root.querySelector("[data-report-page-prev]")?.addEventListener("click", () => {
    void loadReportManagerPage({ page: Math.max(1, reportStore.manager.page - 1) });
  });
  root.querySelector("[data-report-page-next]")?.addEventListener("click", () => {
    void loadReportManagerPage({ page: reportStore.manager.page + 1 });
  });
  root.querySelector("[data-report-page-save]")?.addEventListener("click", () => void saveBindings());
  root.querySelector("[data-report-page-delete]")?.addEventListener("click", event => {
    void deleteReport(event.currentTarget?.getAttribute?.("data-report-page-delete"));
  });
  root.querySelector("[data-report-page-preview]")?.addEventListener("click", event => {
    openReportPreview(event.currentTarget?.getAttribute?.("data-report-page-preview"));
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
  } catch (error) {
    setStatus(error.message || String(error), true);
  } finally {
    reportStore.manager.busy = false;
    renderReportManagerPage();
  }
}

function openReportPreview(reportId) {
  const report = reportForId(reportId);
  const target = document.getElementById("workspace-report-reader");
  if (!report || !target) return false;
  target.innerHTML = `<div class="report-reader-panel" role="dialog" aria-modal="false">
    <header class="report-reader-head"><div><h2>${esc(report.filename)}</h2></div><div class="report-reader-actions">
      <a class="action-button compact" href="/api/reports/${encodeURIComponent(report.report_id)}/reader" target="_blank" rel="noopener">${esc(t("report_open_new_tab", "Open in new tab"))}</a>
      <button class="action-button compact" type="button" data-report-page-preview-close>${esc(t("close", "Close"))}</button>
    </div></header>
    <div class="report-reader-frame-viewport"><iframe class="report-reader-frame" src="/api/reports/${encodeURIComponent(report.report_id)}/preview" title="${esc(report.filename)}" sandbox="allow-scripts" referrerpolicy="no-referrer"></iframe></div>
  </div>`;
  target.removeAttribute("hidden");
  document.body.classList.add("report-reader-open");
  target.querySelector("[data-report-page-preview-close]")?.addEventListener("click", () => {
    closeReportPreview();
  });
  return true;
}

function closeReportPreview() {
  const target = document.getElementById("workspace-report-reader");
  if (!target || target.hidden) return false;
  target.setAttribute("hidden", "");
  target.replaceChildren();
  document.body.classList.remove("report-reader-open");
  return true;
}

function pageEnd() {
  const page = Number(reportStore.manager.pageData?.page || 1);
  const size = Number(reportStore.manager.pageData?.page_size || 100);
  return Math.min(Number(reportStore.manager.pageData?.total || 0), page * size);
}

function pageLabel() {
  const page = Number(reportStore.manager.pageData?.page || 1);
  const size = Number(reportStore.manager.pageData?.page_size || 100);
  const total = Number(reportStore.manager.pageData?.total || 0);
  return total ? `${(page - 1) * size + 1}-${pageEnd()} / ${total}` : "0 / 0";
}

function setStatus(message, error = false) {
  const target = document.querySelector("[data-report-manager-status]");
  if (!target) return;
  target.textContent = message || "";
  target.classList.toggle("danger", Boolean(error));
  target.toggleAttribute("hidden", !message);
}

export {
  initializeReportManagerPage,
  loadReportManagerPage,
  openReportPreview,
  renderReportManagerPage,
};
