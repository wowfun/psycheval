// @ts-check
import { beginFeedback } from "./action-feedback.js";
import { renderDateTime } from "./date-time.js";
import { serveApi } from "./http.js";
import { acceptReport, bindingId, completeSave, draftChanged, editBinding, reportBindingsChanged, reportLibraryStore as store } from "./report-library-store.js";
import { createReportTargetPicker } from "./report-target-picker.js";
import { createSidebarController } from "./sidebar.js";
import { adminMode, esc, t } from "./shared.js";
import { RENDER_OPTIONS } from "../app/render-options.js";

let generation = 0;
let searchTimer;
let sidebar;
let picker;
let detailIdentity = "";
const reportPath = ref => `/api/report-library/${encodeURIComponent(ref)}`;
const kindLabel = kind => ({ session: "Session", dataset: "Dataset", job: "Job", unassociated: t("report_unassociated", "Unassociated") })[kind] || kind;
const canEditAssociations = report => adminMode() && report?.associations_available !== false;

async function initializeReportManagerPage() {
  const root = document.querySelector("[data-report-manager]");
  if (root && root.getAttribute("data-page-bound") !== "true") {
    root.setAttribute("data-page-bound", "true");
    renderToolbar();
    root.addEventListener("click", onClick);
    window.addEventListener("keydown", event => {
      if (!event.defaultPrevented && event.key === "Escape" && sidebar?.close()) event.preventDefault();
    });
    window.addEventListener("peval:workspace-navigate", () => sidebar?.close({ restoreFocus: false }));
    window.addEventListener("beforeunload", event => {
      if (reportBindingsChanged()) { event.preventDefault(); event.returnValue = ""; }
    });
  }
  await loadReportManagerPage();
}

function renderToolbar() {
  const root = document.querySelector("[data-report-toolbar]");
  if (!root) return;
  root.innerHTML = `<div class="report-library-toolbar">
    ${adminMode() ? `<button class="action-button primary" type="button" data-report-import>${esc(t("report_import", "Import report"))}</button>` : ""}
    <button class="action-button" type="button" data-report-manager-reload>${esc(t("serve_reload", "Refresh"))}</button>
    <label class="report-binding-search report-library-search"><span>${esc(t("report_library_search", "Search reports and associated objects"))}</span><input type="search" data-report-search value="${esc(store.search)}"></label>
    <details class="report-filter"><summary>${esc(t("report_association_type", "Association type"))}</summary><div class="report-filter-options">${["session", "dataset", "job", "unassociated"].map(value => `<label><input type="checkbox" data-report-kind="${value}">${esc(kindLabel(value))}</label>`).join("")}</div></details>
    ${["dataset", "job"].map(kind => `<details class="report-filter" data-report-filter="${kind}"><summary>${kindLabel(kind)} <span data-filter-count="${kind}"></span></summary><div data-filter-picker="${kind}"></div></details>`).join("")}
    </div><div data-report-filter-summary class="report-filter-summary"></div>`;
  bindFilterMenus(root);
  root.querySelector("[data-report-search]").addEventListener("input", event => {
    store.search = /** @type {HTMLInputElement} */ (event.target).value;
    generation += 1;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => void loadReportManagerPage({ page: 1 }).catch(() => {}), 150);
  });
  root.querySelectorAll("[data-report-kind]").forEach(input => input.addEventListener("change", () => {
    const values = store.kinds;
    const value = input.getAttribute("data-report-kind");
    if (/** @type {HTMLInputElement} */ (input).checked) values.add(value); else values.delete(value);
    renderFilterSummary();
    void loadReportManagerPage({ page: 1 }).catch(() => {});
  }));
  for (const kind of ["dataset", "job"]) {
    const values = kind === "dataset" ? store.datasets : store.jobs;
    const control = createReportTargetPicker(root.querySelector(`[data-filter-picker="${kind}"]`), {
      kind, selected: () => values,
      onChange(item, selected) {
        if (selected) values.set(bindingId(item), item); else values.delete(bindingId(item));
        renderFilterSummary();
        void loadReportManagerPage({ page: 1 }).catch(() => {});
      },
    });
    root.querySelector(`[data-report-filter="${kind}"]`).addEventListener("toggle", event => {
      if (/** @type {HTMLDetailsElement} */ (event.target).open) void control.load();
    });
  }
}

function bindFilterMenus(root) {
  const closeMenus = (except = null) => {
    root.querySelectorAll(".report-filter[open]").forEach(menu => {
      if (menu !== except) menu.open = false;
    });
  };
  const positionMenu = menu => {
    const panel = menu.querySelector(":scope > div");
    panel.style.setProperty("--report-filter-offset", "0px");
    const rect = panel.getBoundingClientRect();
    const offset = Math.max(16 - rect.left, Math.min(0, window.innerWidth - 16 - rect.right));
    panel.style.setProperty("--report-filter-offset", `${offset}px`);
  };
  document.addEventListener("click", event => {
    const menu = /** @type {Element} */ (event.target).closest(".report-filter");
    closeMenus(root.contains(menu) ? menu : null);
  }, true);
  root.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    const menu = event.target.closest(".report-filter[open]");
    if (!menu) return;
    event.preventDefault();
    event.stopPropagation();
    menu.open = false;
    menu.querySelector("summary").focus();
  });
  root.querySelectorAll(".report-filter").forEach(menu => {
    menu.addEventListener("toggle", () => { if (menu.open) positionMenu(menu); });
  });
  window.addEventListener("resize", () => root.querySelectorAll(".report-filter[open]").forEach(positionMenu));
  window.addEventListener("peval:workspace-navigate", () => closeMenus());
}

function renderFilterSummary() {
  const target = document.querySelector("[data-report-filter-summary]");
  if (target) target.textContent = [...[...store.kinds].map(kindLabel), ...[...store.datasets.values(), ...store.jobs.values()].map(item => item.label)].join(" · ");
  for (const kind of ["dataset", "job"]) {
    const selected = kind === "dataset" ? store.datasets : store.jobs;
    const count = document.querySelector(`[data-filter-count="${kind}"]`);
    if (count) count.textContent = selected.size ? `(${selected.size})` : "";
  }
}

async function loadReportManagerPage({ page = store.page } = {}) {
  const request = ++generation;
  store.page = page;
  store.loading = true;
  renderReportManagerPage();
  const params = new URLSearchParams({ page: String(page), page_size: String(store.pageSize), search: store.search });
  for (const value of store.kinds) params.append("kind", value);
  for (const item of store.datasets.values()) params.append("dataset", item.key);
  for (const item of store.jobs.values()) params.append("job", item.key);
  const feedback = beginFeedback("[data-report-manager]", { page: "reports", key: "reports:load" });
  try {
    const result = await serveApi(`/api/report-library?${params}`);
    if (request !== generation) return;
    store.items = result.items.map(acceptReport);
    store.total = result.total;
    store.page = result.page;
    if (store.activeRef && !store.items.some(item => item.report_ref === store.activeRef)) {
      const ref = store.activeRef;
      try {
        const report = await serveApi(reportPath(ref));
        if (request !== generation) return;
        acceptReport(report);
      } catch (error) {
        if (request !== generation) return;
        const stillSelected = store.activeRef === ref;
        if (error.status === 404) {
          store.reports.delete(ref);
          clearReportSelection(ref, { restoreFocus: false });
        }
        if (stillSelected) feedback.error(error);
      }
    }
    if (request !== generation) return;
    store.loading = false;
    renderReportManagerPage();
    renderDetail();
    if (store.tab === "associations") void picker?.load();
  } catch (error) {
    if (request !== generation) return;
    store.loading = false;
    renderReportManagerPage();
    feedback.error(error);
    throw error;
  }
}

function renderReportManagerPage() {
  const inventory = document.querySelector("[data-report-inventory]");
  if (!inventory) return;
  inventory.setAttribute("aria-busy", String(store.loading));
  inventory.innerHTML = `<table class="report-library-grid"><thead><tr>${[t("report_name", "Report"), t("report_format", "Format"), t("report_associations", "Associations"), t("report_updated", "Updated")].map(label => `<th scope="col">${esc(label)}</th>`).join("")}</tr></thead><tbody>${store.items.map(report => `<tr class="${report.report_ref === store.activeRef ? "selected" : ""}" data-report-row="${esc(report.report_ref)}">
    <td><button class="report-inventory-select" type="button" data-report-select="${esc(report.report_ref)}">${esc(report.title)}</button></td>
    <td>${esc(report.format.toUpperCase())}</td>
    <td title="${esc(report.associations.map(item => `${kindLabel(item.kind)}: ${item.label}`).join("; "))}">${esc(report.associations.map(item => item.label).join(" · ") || t("report_unassociated", "Unassociated"))}</td>
    <td>${renderDateTime(report.updated_at_ms)}</td></tr>`).join("")}</tbody></table>${store.items.length ? "" : `<p class="report-manager-empty">${esc(store.loading ? t("loading", "Loading") : t("report_no_reports", "No reports found"))}</p>`}`;
  const pagination = document.querySelector("[data-report-pagination]");
  if (pagination) pagination.innerHTML = `<button class="action-button" type="button" data-report-prev ${store.page <= 1 ? "disabled" : ""} aria-label="${esc(t("previous", "Previous"))}">‹</button><span>${store.page} / ${Math.max(1, Math.ceil(store.total / store.pageSize))} · ${store.total}</span><button class="action-button" type="button" data-report-next ${store.page * store.pageSize >= store.total ? "disabled" : ""} aria-label="${esc(t("next", "Next"))}">›</button>`;
  document.querySelector("[data-report-import]")?.toggleAttribute("disabled", store.importing);
}

function surface() {
  if (!sidebar) sidebar = createSidebarController({
    id: "report-library-detail", side: "right", root: "#report-library-detail",
    bodyClass: "report-library-detail-open", cssVariable: "--report-library-detail-width",
    workspaceId: RENDER_OPTIONS.workspace_id || "default", minWidth: 360, minWorkspaceWidth: 360,
    defaultWidth: width => Math.min(760, width * .48), resizeLabel: () => t("report_details_resize", "Resize report details"),
    onRequestClose: options => sidebar.close(options),
  });
  return sidebar;
}

function openReportPreview(ref, options = {}) {
  if (!store.reports.has(ref)) return false;
  store.activeRef = ref;
  store.tab = "preview";
  renderReportManagerPage();
  renderDetail();
  const opener = [...document.querySelectorAll("[data-report-select]")].find(button => button.getAttribute("data-report-select") === ref);
  return surface().open({ opener: opener || options.opener || document.activeElement, openerSelector: `[data-report-select="${ref}"]`, focusTarget: "#report-library-detail [data-sidebar-close]" });
}

function clearReportSelection(ref, options = {}) {
  if (store.activeRef !== ref) return;
  picker?.destroy(); picker = null;
  detailIdentity = "";
  store.activeRef = null;
  sidebar?.close(options);
  document.getElementById("report-library-detail")?.replaceChildren();
}

function renderDetail() {
  const root = document.getElementById("report-library-detail");
  const report = store.reports.get(store.activeRef);
  if (!root || !report) return;
  const identity = `${report.report_ref}/${store.tab}/${canEditAssociations(report)}`;
  if (identity !== detailIdentity) {
    picker?.destroy();
    picker = null;
    detailIdentity = identity;
    root.innerHTML = `<div class="report-library-detail-panel"><header class="report-reader-head"><h2>${esc(report.title)}</h2><div class="report-reader-actions"><a class="action-button compact" href="${reportPath(report.report_ref)}/reader" target="_blank" rel="noopener">${esc(t("report_open_new_tab", "Open in new tab"))}</a><button class="action-button compact" type="button" data-sidebar-close>${esc(t("close", "Close"))}</button></div></header>
      <div class="report-detail-tabs" role="tablist">${["preview", "associations"].map(tab => `<button type="button" class="action-button" role="tab" aria-selected="${store.tab === tab}" data-report-tab="${tab}">${esc(t(`report_${tab}`, tab === "preview" ? "Preview" : "Associations"))}</button>`).join("")}</div>
      ${store.tab === "preview" ? `<div class="report-reader-frame-viewport" role="tabpanel"><iframe class="report-reader-frame" src="${reportPath(report.report_ref)}/preview" title="${esc(report.title)}" sandbox="allow-scripts" referrerpolicy="no-referrer"></iframe></div>` : `<div class="report-associations-pane" role="tabpanel"><div data-association-summary></div>${canEditAssociations(report) ? `<label class="report-binding-search"><span>${esc(t("report_add_association", "Add associations"))}</span><select data-binding-kind>${(report.origin === "imported" ? ["session", "dataset", "job"] : ["dataset", "job"]).map(kind => `<option value="${kind}">${kindLabel(kind)}</option>`).join("")}</select></label><div data-binding-picker></div>` : ""}</div>`}</div>`;
    if (store.tab === "associations" && canEditAssociations(report)) {
      const select = /** @type {HTMLSelectElement} */ (root.querySelector("[data-binding-kind]"));
      select.addEventListener("change", () => openBindingPicker(report.report_ref, select.value));
      openBindingPicker(report.report_ref, select.value);
    }
    sidebar?.sync();
  }
  renderAssociationSummary();
}

function openBindingPicker(ref, kind) {
  picker?.destroy();
  picker = createReportTargetPicker(document.querySelector("[data-binding-picker]"), {
    kind, selected: () => store.drafts.get(ref).values,
    onChange(item, selected) { editBinding(ref, item, selected); renderAssociationSummary(); },
  });
  void picker.load();
}

function renderAssociationSummary() {
  const root = document.querySelector("[data-association-summary]");
  const report = store.reports.get(store.activeRef);
  if (!root || !report) return;
  const draft = store.drafts.get(report.report_ref);
  const editable = canEditAssociations(report);
  const row = (item, editable = false) => `<li><span>${esc(kindLabel(item.kind))} · ${esc(item.label)}${item.available ? "" : ` <strong class="report-unavailable">${esc(t("report_unavailable", "Unavailable"))}</strong>`}</span>${editable ? `<button class="action-button compact" type="button" data-binding-remove="${esc(bindingId(item))}" aria-label="${esc(t("report_remove_association", "Remove association") + ": " + item.label)}">×</button>` : ""}</li>`;
  root.innerHTML = `${["source", "inherited"].map(origin => {
    const items = report.associations.filter(item => item.origins.includes(origin));
    return items.length ? `<h3>${esc(t(`report_${origin}_associations`, origin === "source" ? "Original source" : "Session ownership"))}</h3><ul class="report-associated-list">${items.map(item => row(item)).join("")}</ul>` : "";
  }).join("")}
    <h3>${esc(t("report_manual_associations", "Manual associations"))}</h3>${report.associations_available === false ? `<p role="status" class="report-unavailable">${esc(t("report_associations_unavailable", "Report associations could not be read. Repair the association data and refresh to edit."))}</p>` : ""}<ul class="report-associated-list">${[...draft.values.values()].map(item => row(item, editable)).join("") || (report.associations_available === false ? "" : `<li>${esc(t("report_unassociated", "Unassociated"))}</li>`)}</ul>
    ${editable ? `<div class="report-binding-actions"><button class="action-button primary" type="button" data-report-save ${!draftChanged(draft) || draft.saving || draft.deleting ? "disabled" : ""}>${esc(t("report_save_bindings", "Save associations"))}</button>${report.origin === "imported" ? `<button class="action-button danger" type="button" data-report-delete ${draft.saving || draft.deleting ? "disabled" : ""}>${esc(t("report_delete", "Delete report"))}</button>` : ""}</div>` : ""}`;
}

async function saveBindings() {
  const ref = store.activeRef;
  const report = store.reports.get(ref);
  const draft = store.drafts.get(ref);
  if (!report || !canEditAssociations(report) || !draft || draft.saving || draft.deleting || !draftChanged(draft)) return;
  const version = draft.version;
  const submitted = [...draft.values.values()].map(({ kind, key }) => ({ kind, key }));
  draft.saving = true;
  generation += 1;
  store.loading = false;
  renderAssociationSummary();
  const feedback = beginFeedback("[data-report-manager]", { page: "reports", key: `reports:save:${ref}`, label: report.title });
  try {
    const updated = await serveApi(`${reportPath(ref)}/bindings`, { method: "PUT", body: { bindings: submitted } });
    generation += 1;
    completeSave(ref, updated, version, submitted);
    feedback.set(t("report_bindings_saved", "Report associations saved"));
  } catch (error) { feedback.error(error); }
  finally { draft.saving = false; renderAssociationSummary(); }
  await loadReportManagerPage().catch(() => {});
}

async function importReport() {
  if (!adminMode() || store.importing) return;
  store.importing = true;
  renderReportManagerPage();
  const feedback = beginFeedback("[data-report-manager-status]", { page: "reports", key: "reports:import" });
  feedback.pending(t("serve_path_picker_waiting", "Choose a file in the server's file picker"));
  try {
    const selection = await serveApi("/api/path-selections", { method: "POST", body: { multiple: false } });
    const path = selection.paths?.[0];
    if (!path) { feedback.clear(); return; }
    feedback.pending(t("report_importing", "Importing report..."));
    const report = await serveApi("/api/reports", { method: "POST", body: { path, bindings: [] } });
    acceptReport(report);
    openReportPreview(report.report_ref);
    feedback.set(t("report_imported", "Report imported"));
    await loadReportManagerPage();
  } catch (error) { feedback.error(error); }
  finally { store.importing = false; renderReportManagerPage(); }
}

async function deleteReport() {
  const report = store.reports.get(store.activeRef);
  const draft = store.drafts.get(store.activeRef);
  if (!adminMode() || report?.origin !== "imported" || !draft || draft.saving || draft.deleting || !window.confirm(`${t("report_delete", "Delete report")}: ${report.title}?`)) return;
  draft.deleting = true;
  renderAssociationSummary();
  const feedback = beginFeedback("[data-report-manager]", { page: "reports", key: `reports:delete:${report.report_ref}` });
  try {
    await serveApi(`/api/reports/${encodeURIComponent(report.report_id)}`, { method: "DELETE" });
    store.reports.delete(report.report_ref);
    store.drafts.delete(report.report_ref);
    clearReportSelection(report.report_ref);
    feedback.success();
    await loadReportManagerPage();
  } catch (error) { feedback.error(error); }
  finally { draft.deleting = false; renderAssociationSummary(); }
}

function onClick(event) {
  const target = event.target;
  const select = target.closest("[data-report-select],[data-report-row]");
  if (select) openReportPreview(select.getAttribute("data-report-select") || select.getAttribute("data-report-row"), { opener: target });
  const tab = target.closest("[data-report-tab]");
  if (tab) { store.tab = tab.getAttribute("data-report-tab"); renderDetail(); }
  const remove = target.closest("[data-binding-remove]");
  if (remove && adminMode()) {
    const item = store.drafts.get(store.activeRef).values.get(remove.getAttribute("data-binding-remove"));
    if (item) editBinding(store.activeRef, item, false);
    renderAssociationSummary(); picker?.renderSelected();
  }
  if (target.closest("[data-report-manager-reload]")) void loadReportManagerPage().catch(() => {});
  if (target.closest("[data-report-prev]")) void loadReportManagerPage({ page: store.page - 1 }).catch(() => {});
  if (target.closest("[data-report-next]")) void loadReportManagerPage({ page: store.page + 1 }).catch(() => {});
  if (target.closest("[data-report-save]")) void saveBindings();
  if (target.closest("[data-report-import]")) void importReport();
  if (target.closest("[data-report-delete]")) void deleteReport();
}

function activeReportSnapshot() {
  const report = store.reports.get(store.activeRef);
  return { report_ref: report?.report_ref || null, report_name: report?.title || null };
}

export { activeReportSnapshot, initializeReportManagerPage, loadReportManagerPage, openReportPreview, renderReportManagerPage, saveBindings };
