import { esc, fmtDate, renderReadOnlySourceTags, serveMode, sourceTagsEditValue, sourceTagsValue, state, t } from "./runtime.js";
import { bindDataTableControls, renderDataTable, tableCellContent, tableValueAttributes } from "./data-tables.js";
import { applyDefaultDbToForm, syncAdapterDefaultDbControls } from "./serve-controls.js";
import { commitSourceCellEdit, existingSourceTagOptions, formPayload, normalizeAdapterValue, selectedAdapterValue, serveApi, setAdapterChoice, setServeStatus, showServeNotice } from "./serve-effects.js";
import { applyServeMutationPayload, bindSourceManagerPagination, pruneSourceSelection, renderSourceManagerPagination, sourceRows, sourceSelectionKeys } from "./serve-catalog.js";
import { closeModalSurface } from "./modal-surfaces.js";

const selectedSourceRows = new Map();

function closeServeSourceManager(options = {}) {
  const manager = document.querySelector("[data-source-manager]");
  return closeModalSurface(manager, options);
}
function renderServeSources() {
  if (!serveMode()) return;
  const sources = Array.isArray(state.sourceManagerRows) ? state.sourceManagerRows : [];
  const managerStatus = state.sourceManagerStatus || { phase: "idle", message: "" };
  syncServeLoadingStatus(state.serveSources);
  renderSourceManagerStatus();
  const list = document.querySelector("[data-source-list]");
  if (list) {
    if (managerStatus.phase === "loading") {
      list.innerHTML = `<li class="source-row empty loading">${esc(managerStatus.message || t("loading", "Loading"))}</li>`;
      syncSourceManagerBulkActions([]);
      return;
    }
    if (!sources.length) {
      state.sourceSelection.clear();
      const message = managerStatus.phase === "error"
        ? managerStatus.message
        : t("serve_no_sources", "No sources loaded");
      list.innerHTML = `<li class="source-row empty${managerStatus.phase === "error" ? " danger" : ""}">${esc(message)}</li>`;
      syncSourceManagerBulkActions();
      return;
    }
    pruneSourceSelection();
    const rows = sourceRows();
    const columns = sourceColumns();
    list.innerHTML = `<li class="source-table-item">${renderDataTable({
      tableId: "sources",
      columns,
      rows,
      rowKey: source => source?.source_key,
      tableClass: "source-table",
      shellClass: "source-table-shell",
      rowClass: source => ["source-table-row", source?.active === false ? "archived" : "", source?.last_status === "missing" ? "missing" : "", source?.source_key && source.source_key === state.selectedSourceKey ? "selected-row" : ""].filter(Boolean).join(" "),
      rowAttrs: source => `data-source-row data-source-key="${esc(source?.source_key || "")}"`,
      rowTitle: source => source?.source_key || source?.label || ""
    })}</li>${renderSourceManagerPagination()}`;
    bindDataTableControls(list, {
      tableId: "sources",
      columns,
      rows,
      rowKey: source => source?.source_key,
      onChange: () => renderServeSources(),
    });
    bindSourceSelectionControls(list);
    bindSourceManagerPagination(list);
    syncSourceManagerBulkActions(rows);
  }
}
function renderSourceManagerStatus() {
  const target = document.querySelector("[data-source-manager-status]");
  if (!target) return;
  const status = state.sourceManagerStatus || { phase: "idle", message: "" };
  target.textContent = status.message || "";
  target.classList.toggle("danger", status.phase === "error");
  target.classList.toggle("loading", status.phase === "loading");
  target.hidden = !status.message;
}
function syncServeLoadingStatus(sources = state.serveSources) {
  const countNode = document.querySelector("[data-source-count]");
  const statusNode = document.querySelector("[data-source-status]");
  if (state.serveLoading) {
    if (countNode) countNode.textContent = t("serve_loading_sources", "Loading sources");
    if (statusNode) {
      statusNode.textContent = t("serve_scanning_runs", "Scanning runs; sessions will appear when discovery finishes.");
      statusNode.classList.toggle("danger", false);
      statusNode.classList.toggle("loading", true);
    }
    return;
  }
  const list = Array.isArray(sources) ? sources : [];
  if (countNode) {
    const word = list.length === 1 ? t("serve_source_count", "source") : t("serve_sources_count", "sources");
    countNode.textContent = `${list.length} ${word}`;
  }
  if (statusNode) statusNode.classList.toggle("loading", false);
}
function sourceColumns() {
  return [
    { key: "__source_select", valueType: "selection", sourceSelect: true, label: t("select_rows", "Select rows"), value: source => source?.source_key || "", html: renderSourceSelection },
    { key: "label", label: t("source", "Source"), valueType: "identity", value: source => sourceDisplayLabel(source), html: renderServeSourceLabel, cellTitle: source => source?.label || "" },
    { key: "last_turn_finished_at_ms", label: t("last_turn_end", "Last Turn End"), valueType: "datetime", numeric: true, sortable: true, value: source => source?.last_turn_finished_at_ms, format: fmtDate },
    { key: "status", label: t("status", "status"), valueType: "status", value: source => sourceStatusText(source), html: renderServeSourceStatus },
    { key: "alias", label: t("serve_source_alias", "Alias"), valueType: "text", value: source => String(source?.source_alias || "").trim() || "-", edit: { value: source => String(source?.source_alias || ""), commit: (source, value) => commitSourceCellEdit(source, "alias", value) } },
    { key: "source_tags", label: t("tags", "Tags"), valueType: "list", value: source => sourceTagsValue(source), html: renderReadOnlySourceTags, edit: { value: source => sourceTagsEditValue(source), suggestions: existingSourceTagOptions, commit: (source, value) => commitSourceCellEdit(source, "tags", value) } }
  ];
}
function sourceDisplayLabel(source) {
  const label = source?.label || source?.source_key || "source";
  const alias = String(source?.source_alias || "").trim();
  return alias || label;
}
function sourceStatusText(source) {
  const active = source?.active !== false;
  const stateLabel = active ? t("serve_active", "active") : t("serve_archived", "archived");
  return `${source?.kind || "source"} / ${source?.adapter || "-"} / ${source?.last_status || "-"} / ${stateLabel}`;
}
function renderServeSourceLabel(source) {
  const key = source?.source_key || "";
  const label = source?.label || key || "source";
  const alias = String(source?.source_alias || "").trim();
  const displayLabel = alias || label;
  const origin = alias ? `<span class="source-origin">${esc(label)}</span>` : "";
  const session = source?.trial_session_id || source?.session_id || "";
  const sessionLine = session ? `<span>${esc(t("session", "Session"))}: <code>${esc(session)}</code></span>` : "";
  return `<span class="source-label-stack"><strong>${esc(displayLabel)}</strong>${origin}${sessionLine}</span>`;
}
function renderServeSourceStatus(source) {
  return `<span class="source-status-text">${esc(sourceStatusText(source))}</span>`;
}
function renderSourceSelectionHeader(rows) {
  const visible = sourceVisibleKeys(rows);
  const selected = visible.filter(key => state.sourceSelection.has(key));
  const checked = visible.length > 0 && selected.length === visible.length;
  const partial = selected.length > 0 && selected.length < visible.length;
  return `<th class="select-col table-value-selection" data-value-type="selection"><label class="select-box"><input type="checkbox" data-source-select-visible ${checked ? "checked" : ""} ${partial ? "data-partial=\"true\"" : ""} aria-label="${esc(t("select_visible_sources", "Select visible sources"))}"><span></span></label></th>`;
}
function renderSourceSelection(source) {
  const key = source?.source_key || "";
  const checked = key && state.sourceSelection.has(key);
  return `<label class="select-box"><input type="checkbox" data-source-row-select="${esc(key)}" ${checked ? "checked" : ""} aria-label="${esc(t("select_source", "Select source"))}: ${esc(key)}"><span></span></label>`;
}
function renderServeSourceAliasCell(source) {
  const alias = String(source?.source_alias || "").trim();
  return alias ? esc(alias) : `<span class="muted">-</span>`;
}
async function choosePathSourceFiles(button) {
  const form = button?.closest?.("[data-source-add-form]");
  const field = form?.querySelector?.("[name=\"path\"]");
  if (!field) return;
  try {
    const payload = await serveApi("/api/path-picker", {
      method: "POST",
      body: { multiple: true }
    });
    const paths = Array.isArray(payload?.paths) ? payload.paths.map(path => String(path || "").trim()).filter(Boolean) : [];
    if (!paths.length) return;
    field.value = paths.join("\n");
    setServeStatus(t("serve_path_picker_selected", "Path selection updated"));
  } catch (error) {
    const message = error.message || String(error);
    showServeNotice(message, true);
    setServeStatus(message, true);
  }
}
function sourceVisibleKeys(rows = sourceRows()) {
  return Array.from(new Set(rows.map(source => String(source?.source_key || "").trim()).filter(Boolean)));
}
function sourceSelectedRows(rows = sourceRows()) {
  const selectedKeys = sourceSelectionKeys(rows);
  const selected = new Set(selectedKeys);
  for (const key of selectedSourceRows.keys()) {
    if (!selected.has(key)) selectedSourceRows.delete(key);
  }
  rows.forEach(source => {
    if (source?.source_key && selected.has(source.source_key)) {
      selectedSourceRows.set(source.source_key, source);
    }
  });
  return selectedKeys.map(key => selectedSourceRows.get(key)).filter(Boolean);
}
function sourceBulkStateTarget(rows = sourceRows()) {
  const selected = sourceSelectedRows(rows);
  if (!selected.length) return "archived";
  return selected.every(source => source?.active === false) ? "active" : "archived";
}
function syncSourceManagerBulkActions(rows = sourceRows()) {
  const selected = sourceSelectionKeys(rows);
  const targetMode = sourceBulkStateTarget(rows);
  const stateButton = document.querySelector("[data-source-bulk-state]");
  const deleteButton = document.querySelector("[data-source-bulk-delete]");
  if (stateButton) {
    stateButton.disabled = selected.length < 1;
    stateButton.dataset.sourceBulkState = targetMode;
    stateButton.textContent = targetMode === "active"
      ? t("activate_selected", "Activate selected")
      : t("archive_selected", "Archive selected");
  }
  if (deleteButton) deleteButton.disabled = selected.length < 1;
}
function bindSourceSelectionControls(root) {
  if (!serveMode() || !root) return;
  root.querySelectorAll("[data-source-select-visible]").forEach(input => {
    input.addEventListener("click", event => event.stopPropagation());
    input.addEventListener("change", event => {
      event.stopPropagation();
      const keys = sourceVisibleKeys(sourceRows());
      keys.forEach(key => {
        if (input.checked) state.sourceSelection.add(key);
        else state.sourceSelection.delete(key);
      });
      renderServeSources();
    });
  });
  root.querySelectorAll("[data-source-row-select]").forEach(input => {
    input.addEventListener("click", event => event.stopPropagation());
    input.addEventListener("change", event => {
      event.stopPropagation();
      const key = String(input.dataset.sourceRowSelect || "").trim();
      if (!key) return;
      if (input.checked) state.sourceSelection.add(key);
      else state.sourceSelection.delete(key);
      renderServeSources();
    });
  });
}
async function submitServeSourceForm(form) {
  if (form?.dataset?.sourceKind === "db") applyDefaultDbToForm(form);
  const body = formPayload(form);
  const kind = form.dataset.sourceKind;
  if (!kind) return;
  const sourceValue = String(body[kind] || "").trim();
  if (!sourceValue) return;
  try {
    setServeStatus(t("serve_refresh", "Refresh"));
    const payload = await serveApi("/api/sources", { method: "POST", body });
    form.reset();
    if (kind === "db") syncAdapterDefaultDbControls(form);
    applyServeMutationPayload(payload);
    showImportResultsSummary(payload);
  } catch (error) {
    showServeNotice(`${t("serve_import_failed", "Import failed")}: ${error.message || String(error)}`, true);
    setServeStatus(error.message || String(error), true);
  }
}
function showImportResultsSummary(payload) {
  const results = Array.isArray(payload?.import_results) ? payload.import_results : [];
  if (!results.length) return;
  const imported = results.filter(result => result?.status === "ok").length;
  const failures = results.filter(result => result?.status === "error");
  const failed = failures.length;
  const template = t("serve_import_summary", "Imported {imported}, failed {failed}");
  let message = template.replace("{imported}", String(imported)).replace("{failed}", String(failed));
  const firstError = String(failures[0]?.error || "").trim();
  if (firstError) message = `${message}: ${firstError}`;
  showServeNotice(message, failed > 0);
  setServeStatus(message, failed > 0);
}
async function inspectDbSessions(form) {
  if (!form) return;
  applyDefaultDbToForm(form);
  const body = formPayload(form);
  const db = String(body.db || "").trim();
  if (!db) return;
  const picker = form.querySelector("[data-db-session-picker]");
  try {
    setServeStatus(t("serve_inspect_db", "Inspect DB"));
    const payload = await serveApi("/api/db-sessions", {
      method: "POST",
      body: {
        db,
        adapter: selectedAdapterValue(form)
      }
    });
    if (payload?.adapter) setAdapterChoice(form, payload.adapter);
    syncAdapterDefaultDbControls(form);
    renderDbSessionPicker(form, payload);
    setServeStatus(t("serve_latest_snapshots", "Latest snapshots"));
  } catch (error) {
    if (picker) {
      picker.hidden = false;
      picker.innerHTML = `<p class="copy danger">${esc(error.message || String(error))}</p>`;
    }
    setServeStatus(error.message || String(error), true);
  }
}
function renderDbSessionPicker(form, payload) {
  const picker = form.querySelector("[data-db-session-picker]");
  if (!picker) return;
  const sessions = Array.isArray(payload?.sessions) ? payload.sessions : [];
  form.dataset.inspectedDb = payload?.db || "";
  form.dataset.inspectedAdapter = payload?.adapter || "";
  picker.hidden = false;
  if (!sessions.length) {
    picker.innerHTML = `<div class="db-picker-head"><strong>${esc(t("serve_db_sessions", "DB sessions"))}</strong><span>${esc(t("serve_no_sessions", "No sessions found"))}</span></div>`;
    return;
  }
  const adapterLabel = payload?.inferred ? t("serve_adapter_inferred", "Adapter inferred") : t("serve_adapter_selected", "Adapter selected");
  picker.innerHTML = `
    <div class="db-picker-head">
      <div><strong>${esc(t("serve_db_sessions", "DB sessions"))}</strong><span>${esc(adapterLabel)}: ${esc(payload?.adapter || "-")}</span></div>
      <label class="db-select-all"><input type="checkbox" data-db-select-all> ${esc(t("serve_select_all_visible", "Select all visible"))}</label>
    </div>
    <div class="db-session-table-wrap">
      <table class="data-table db-session-table">
        <thead><tr><th ${tableValueAttributes("selection", t("select_rows", "Select rows"))}></th><th ${tableValueAttributes("number", "#")}>${tableCellContent("#")}</th><th ${tableValueAttributes("identity", t("session", "Session"))}>${tableCellContent(esc(t("session", "Session")))}</th><th ${tableValueAttributes("text", t("serve_session_name", "Name"))}>${tableCellContent(esc(t("serve_session_name", "Name")))}</th></tr></thead>
        <tbody>${sessions.map(renderDbSessionRow).join("")}</tbody>
      </table>
    </div>
    <div class="db-picker-actions">
      <span data-db-selected-count>0 ${esc(t("serve_selected_count", "selected"))}</span>
      <button class="step-toggle-button primary" type="button" data-db-add-selected disabled>${esc(t("serve_add_selected", "Add selected"))}</button>
    </div>
  `;
  bindDbSessionSelectionCounters(picker);
}
function renderDbSessionRow(session) {
  const sessionId = String(session?.session_id || "");
  const index = String(session?.index || "");
  const name = String(session?.name || "-");
  return `<tr>
    <td ${tableValueAttributes("selection", sessionId)}><input type="checkbox" data-db-session-checkbox value="${esc(sessionId)}" aria-label="${esc(sessionId)}"></td>
    <td ${tableValueAttributes("number", index, "num")}>${tableCellContent(esc(index))}</td>
    <td ${tableValueAttributes("identity", sessionId)}>${tableCellContent(`<code>${esc(sessionId)}</code>`)}</td>
    <td ${tableValueAttributes("text", name)}>${tableCellContent(esc(name))}</td>
  </tr>`;
}
function bindDbSessionSelectionCounters(picker) {
  picker.querySelectorAll("[data-db-session-checkbox]").forEach(box => {
    box.addEventListener("change", () => updateDbSelectedCount(picker));
  });
  updateDbSelectedCount(picker);
}
function setDbSessionSelection(picker, checked) {
  picker.querySelectorAll("[data-db-session-checkbox]").forEach(box => {
    box.checked = Boolean(checked);
  });
  updateDbSelectedCount(picker);
}
function selectedDbSessionIds(form) {
  return Array.from(form.querySelectorAll("[data-db-session-checkbox]:checked"))
    .map(box => String(box.value || "").trim())
    .filter(Boolean);
}
function updateDbSelectedCount(picker) {
  const count = picker.querySelectorAll("[data-db-session-checkbox]:checked").length;
  const target = picker.querySelector("[data-db-selected-count]");
  if (target) target.textContent = `${count} ${t("serve_selected_count", "selected")}`;
  const addButton = picker.querySelector("[data-db-add-selected]");
  if (addButton) addButton.disabled = count < 1;
}
async function addSelectedDbSessions(form) {
  if (!form) return;
  const sessionIds = selectedDbSessionIds(form);
  if (!sessionIds.length) {
    setServeStatus(t("serve_select_sessions", "Select sessions"), true);
    return;
  }
  const body = formPayload(form);
  try {
    setServeStatus(t("serve_refresh", "Refresh"));
    const payload = await serveApi("/api/sources", {
      method: "POST",
      body: {
        db: form.dataset.inspectedDb || body.db,
        adapter: form.dataset.inspectedAdapter || selectedAdapterValue(form),
        session_ids: sessionIds,
        alias: body.alias
      }
    });
    form.reset();
    syncAdapterDefaultDbControls(form);
    const picker = form.querySelector("[data-db-session-picker]");
    if (picker) {
      picker.hidden = true;
      picker.innerHTML = "";
    }
    delete form.dataset.inspectedDb;
    delete form.dataset.inspectedAdapter;
    applyServeMutationPayload(payload);
  } catch (error) {
    showServeNotice(`${t("serve_import_failed", "Import failed")}: ${error.message || String(error)}`, true);
    setServeStatus(error.message || String(error), true);
  }
}
async function submitServeUploadForm(form) {
  const formData = new FormData(form);
  const file = formData.get("file");
  if (!file || !file.name || typeof file.text !== "function") return;
  try {
    setServeStatus(t("serve_upload", "Upload"));
    const payload = await serveApi("/api/upload", {
      method: "POST",
      body: {
        filename: file.name,
        content: await file.text(),
        adapter: normalizeAdapterValue(formData.get("adapter")),
        alias: String(formData.get("alias") || "").trim()
      }
    });
    form.reset();
    applyServeMutationPayload(payload);
  } catch (error) {
    showServeNotice(`${t("serve_import_failed", "Import failed")}: ${error.message || String(error)}`, true);
    setServeStatus(error.message || String(error), true);
  }
}
export {
  addSelectedDbSessions,
  bindDbSessionSelectionCounters,
  bindSourceSelectionControls,
  choosePathSourceFiles,
  closeServeSourceManager,
  inspectDbSessions,
  renderDbSessionPicker,
  renderDbSessionRow,
  renderServeSourceAliasCell,
  renderServeSourceLabel,
  renderServeSourceStatus,
  renderServeSources,
  renderSourceManagerStatus,
  renderSourceSelection,
  renderSourceSelectionHeader,
  selectedDbSessionIds,
  setDbSessionSelection,
  showImportResultsSummary,
  sourceBulkStateTarget,
  sourceColumns,
  sourceDisplayLabel,
  sourceSelectedRows,
  sourceStatusText,
  sourceVisibleKeys,
  submitServeSourceForm,
  submitServeUploadForm,
  syncServeLoadingStatus,
  syncSourceManagerBulkActions,
  updateDbSelectedCount,
};
