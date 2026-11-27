import { createColumnControl } from "./column-control.js";
import { loadColumnLayout, normalizeColumnLayout, presenceForColumns, resolveColumns, saveColumnLayout } from "./table-columns.js";
import { bindToolbarMenus } from "./toolbar-menu.js";
import { noteColumn, reportsColumn, createCollectionSidebar } from "./collection-ui.js";
import { createRegistryManager } from "./registry-manager.js";
import { taskColumns, taskRowIdentity, taskSearchText, renderTaskTable, flattenTaskRows } from "./task-table.js";
import {
  discoverCustomColumns,
  encodeCustomColumnKey,
  formatCustomColumnValue,
  isCustomColumnKey,
  loadCustomColumnSchemas,
  openCustomColumnModal,
  parseCustomColumnInput,
  saveCustomColumnSchemas,
} from "./task-custom-columns.js";
import { createTaskSummaryState, renderTaskSummary, exportTasks, exportTaskSummaryImage, taskSummaryExportColumns, uniqueTasks } from "./task-summary.js";
import { beginFeedback, pageFeedback, savedContentPreview } from "./action-feedback.js";
import { openActionForm } from "./action-form.js";
import { watchOperation } from "./operation-feedback.js";
import { RENDER_OPTIONS, adminMode, browserStorage, esc, formatMessage, listValue, t } from "./shared.js";
import { applyDataTableControls, applyDataTableFilters, sortDataTableRows, bindDataTableControls, bindTableRowActivation, renderDataTable, selectionColumn, tableControls } from "./data-tables.js";
import { serveApi, serveEtag } from "./http.js";
import { createTaskBrowser } from "./harbor-task-browser.js";

const HARBOR_TABLE_ID = "harbor-datasets";
const UNCHANGED_METADATA_SENTINEL = "\u0001peval-unchanged";
const OVERVIEW_OVERLAY_SELECTOR = "[data-harbor-overview] [data-table-cell-editor], [data-harbor-overview] details[open], [data-task-columns-control] details[open]";
const trackedWorkbenchOperations = new Set();
const watchedDeferredOverlays = new WeakSet();
let workbenchMutationBusy = false;
let pendingInventoryRender = false;
let customColumnsCache = { inventory: null, schemas: null, version: -1, value: [] };
let taskBrowser = null;
let taskSidebar = null, registryManager = null;

const workbenchState = {
  inventory: null,
  datasetColumns: { layout: null, draft: null, search: "" },
  taskColumns: { layout: null, draft: null, search: "" },
  taskItemColumns: { layout: null, draft: null, search: "" },
  customColumnSchemas: null,
  customMetadataVersion: 0,
  datasetId: null,
  datasetFilter: null,
  taskName: null,
  trashEntryId: null,
  taskDetail: null,
  showTrash: false,
  taskSelection: new Set(),
  busy: false,
  search: "",
  registrySearch: "",
  tableSnapshot: null,
  taskRequestId: 0,
  flattened: false,
  summary: createTaskSummaryState(),
  displayRows: [],
  visibleColumns: [],
};

function taskDetailRoot() {
  return taskSidebar?.root || workbenchRoot();
}

function workbenchRoot() {
  return document.querySelector("[data-harbor-workbench]");
}

function resumeTaskSidebar() { taskSidebar?.resume(); }

function renderDatasetRegistry(force = false) {
  const root = workbenchRoot()?.querySelector("[data-dataset-collections]");
  if (!root || !registryManager) return;
  // Keep a live note editor mounted while another view is invalidated.
  if (!force && root.querySelector("[data-table-cell-editor]")) return;
  const datasets = listValue(workbenchState.inventory?.datasets);
  const registryColumns = registryManager.datasetColumns();
  const publicStart = registryColumns.findIndex(column => column.key === "id") + 1;
  const allColumns = [...registryColumns.slice(0, publicStart),
    { key: "tasks", label: t("tasks", "Tasks"), valueType: "number", sortable: true, value: row => row.task_count },
    ...[["rule_count", "task_rules", "Rules"], ["rubric_count", "task_rubrics", "Rubrics"], ["scoring_item_count", "task_scoring_items", "Scoring items"]].map(([key, label, fallback]) => ({ key, label: t(label, fallback), valueType: "number", sortable: true, value: row => row[key], format: value => value ?? "" })),
    noteColumn("dataset", saved => {
      const current = datasetForId(saved.id);
      if (current) Object.assign(current, { note: saved.note, collection_revision: saved.collection_revision });
    }), reportsColumn("dataset"), ...registryColumns.slice(publicStart)];
  const identity = allColumns.find(column => column.key === "id");
  const identityHtml = identity.html;
  identity.html = row => `${identityHtml ? identityHtml(row) : esc(row.id)}${row.error ? `<span class="harbor-status-rail conflict" title="${esc(row.error)}">${esc(t("harbor_status_unavailable", "Unavailable"))}</span>` : ""}`;
  allColumns.find(column => column.key === "reports").presence = row => row.report_count > 0 ? row.report_count : null;
  const searched = datasets.filter(row => !workbenchState.registrySearch || `${row.id} ${row.note || ""}`.toLowerCase().includes(workbenchState.registrySearch.toLowerCase()));
  const rows = applyDataTableControls("harbor-dataset-registry", searched, allColumns);
  const businessColumns = allColumns.filter(column => !column.select);
  const options = { workspaceId: RENDER_OPTIONS?.workspace_id, tableId: "datasets", storage: browserStorage() };
  const columnState = workbenchState.datasetColumns;
  columnState.layout ||= loadColumnLayout(businessColumns.map(column => column.key), options);
  const layout = normalizeColumnLayout(businessColumns.map(column => column.key), columnState.layout);
  const presence = presenceForColumns(businessColumns, rows, null, tableControls("harbor-dataset-registry").filters);
  const columns = [...allColumns.filter(column => column.select), ...resolveColumns(businessColumns, layout, presence)];
  const columnControl = createColumnControl({ id: "datasets", state: columnState, options,
    context: () => ({ columns: businessColumns, layout, presence }),
    conditionText: column => { const controls = tableControls("harbor-dataset-registry"); return [controls.sort === column.key ? controls.direction : "", controls.filters?.[column.key]?.length ? t("filtered", "Filtered") : ""].filter(Boolean).join(" · "); },
    onRender: () => { renderDatasetRegistry(true); return root; },
  });
  root.innerHTML = `<header class="table-region-head"><div class="table-region-title-stack"><h2>${esc(t("harbor_datasets", "Datasets"))}</h2><input type="search" data-dataset-search aria-label="${esc(t("collection_search_datasets", "Search Datasets"))}" placeholder="${esc(t("collection_search_datasets", "Search Datasets"))}" value="${esc(workbenchState.registrySearch)}"></div><div class="table-region-actions"><button class="action-button" type="button" data-harbor-refresh>${esc(t("serve_refresh", "Refresh"))}</button>${columnControl.render()}${workbenchState.datasetFilter ? `<button class="action-button" data-dataset-clear>${esc(t("clear_filters", "Clear filters"))}: ${esc(workbenchState.datasetFilter)}</button>` : ""}${adminMode() && registryManager.ready ? `<button class="action-button" data-harbor-add-dataset>${esc(t("harbor_add_dataset", "New Dataset"))}</button><button class="action-button" data-harbor-register-dataset>${esc(t("harbor_register_dataset", "Register existing"))}</button><button class="action-button danger" data-harbor-unregister-datasets ${registryManager.selectedDatasets.size ? "" : "disabled"}>${esc(t("harbor_unregister_selected", "Unregister selected"))}</button>` : ""}</div></header><div data-harbor-dataset-registry>${renderDataTable({ tableId: "harbor-dataset-registry", columns, rows, rowKey: row => row.id,
    rowClass: row => row.id === workbenchState.datasetFilter ? "selected-row" : "", rowAttrs: row => `tabindex="0" data-dataset-row="${esc(row.id)}"`, emptyText: t("harbor_dataset_empty", "No Datasets registered") })}</div>`;
  bindDataTableControls(root, { tableId: "harbor-dataset-registry", columns, rows, rowKey: row => row.id, onChange: () => renderDatasetRegistry(true), onSelectionChange: renderDatasetRegistry });
  columnControl.bind(root);
  root.querySelector("[data-harbor-refresh]").addEventListener("click", () => refreshHarborInventory({ check: true }));
  async function selectDataset(id) {
    if (!confirmDiscard()) return;
    workbenchState.datasetFilter = id;
    taskSidebar?.close({ restoreFocus: false });
    setOverviewSelection(null);
    renderDatasetRegistry(); renderHarborWorkbench();
  }
  root.querySelectorAll("[data-dataset-row]").forEach(node => bindTableRowActivation(node, () => selectDataset(node.dataset.datasetRow)));
  root.querySelector("[data-dataset-clear]")?.addEventListener("click", () => selectDataset(null));
  root.querySelector("[data-dataset-search]").addEventListener("input", event => {
    const position = event.target.selectionStart;
    workbenchState.registrySearch = event.target.value;
    renderDatasetRegistry();
    const input = root.querySelector("[data-dataset-search]"); input.focus(); input.setSelectionRange?.(position, position);
  });
  const action = run => async () => { try { await run(); } catch (error) { beginFeedback(root, { page: "datasets" }).error(error); } };
  root.querySelector("[data-harbor-add-dataset]")?.addEventListener("click", action(() => registryManager.createDataset(false)));
  root.querySelector("[data-harbor-register-dataset]")?.addEventListener("click", action(() => registryManager.createDataset(true)));
  root.querySelector("[data-harbor-unregister-datasets]")?.addEventListener("click", action(() => registryManager.removeDatasets()));
}

function selectedDataset() {
  return listValue(workbenchState.inventory?.datasets)
    .find(dataset => dataset?.id === workbenchState.datasetId) || null;
}

function datasetForId(datasetId) {
  return listValue(workbenchState.inventory?.datasets)
    .find(dataset => dataset?.id === datasetId) || null;
}

function datasetIsReadOnly(dataset = selectedDataset()) {
  return Boolean(dataset?.read_only);
}

function canMutateSelectedTask() {
  const dataset = selectedDataset();
  const detail = workbenchState.taskDetail;
  return adminMode()
    && Boolean(dataset && workbenchState.taskName && detail)
    && !datasetIsReadOnly(dataset)
    && !detail.read_only;
}

function selectedTask() {
  const dataset = selectedDataset();
  return listValue(dataset?.tasks)
    .find(task => task?.directory === workbenchState.taskName) || null;
}

function selectedTrashEntry() {
  const dataset = selectedDataset();
  return listValue(dataset?.trash)
    .find(entry => entry?.entry_id === workbenchState.trashEntryId) || null;
}

function isHarborDirty() {
  return Boolean(taskBrowser?.isDirty());
}

function workbenchTaskBrowser() {
  const root = taskDetailRoot()?.querySelector?.("[data-harbor-task-browser]") || taskDetailRoot();
  if (!root) return null;
  if (!taskBrowser) {
    taskBrowser = createTaskBrowser({
      root,
      editable: canMutateSelectedTask(),
      readFile: (taskRef, path) => serveApi(`/api/harbor/datasets/${encodeURIComponent(taskRef.dataset_id)}/tasks/${encodeURIComponent(taskRef.task)}/files/${encodeURIComponent(path)}`),
      onContextMenu: canMutateSelectedTask() ? fileActionMenu : null,
      onError: error => taskFeedback("file", workbenchState.taskName, "read-file").error(error),
    });
  } else if (taskBrowser.state.root !== root) taskBrowser.attach(root);
  return taskBrowser;
}

function confirmDiscard() {
  return !isHarborDirty() || window.confirm(t("harbor_discard_changes", "Discard unsaved file changes?"));
}

function overviewRowKey(row) {
  if (row.kind === "trash") return `dataset:${row.dataset.id}|trash:${row.entry.entry_id}`;
  return `dataset:${row.dataset.id}|task:${row.task?.directory || ""}`;
}

function overviewRows() {
  return listValue(workbenchState.inventory?.datasets).filter(dataset => !workbenchState.datasetFilter || dataset.id === workbenchState.datasetFilter).flatMap(dataset => {
    if (workbenchState.showTrash) {
      return listValue(dataset?.trash).map(entry => ({ kind: "trash", dataset, entry, task: null }));
    }
    const tasks = listValue(dataset?.tasks);
    if (!tasks.length) return [{ kind: "empty", dataset, task: null, entry: null }];
    return tasks.map(task => ({ kind: "task", dataset, task, entry: null }));
  }).map(row => ({ ...row, key: overviewRowKey(row), datasetId: row.dataset.id,
    taskName: rowTaskName(row), packageName: rowPackage(row), status: rowStatusKey(row), diagnostics: rowDiagnostics(row),
  }));
}

function rowTaskName(row) {
  return row.kind === "trash" ? row.entry?.directory || row.entry?.entry_id || "" : row.task?.directory || "";
}

function rowPackage(row) {
  return row.kind === "trash" ? row.entry?.package_name || "-" : row.task?.package_name || "-";
}

function rowStatusKey(row) {
  return row.kind === "empty" ? "empty" : row.kind === "trash" ? "trash" : row.task?.status || "draft";
}

function rowDiagnostics(row) {
  return listValue(row.task?.diagnostics).filter(Boolean).join(" · ");
}

function customSchemaStorageOptions() {
  return { workspaceId: RENDER_OPTIONS?.workspace_id, storage: browserStorage() };
}

function customColumnSchemas() {
  if (!workbenchState.customColumnSchemas) {
    workbenchState.customColumnSchemas = loadCustomColumnSchemas(customSchemaStorageOptions());
  }
  return workbenchState.customColumnSchemas;
}

function setCustomColumnSchemas(next) {
  workbenchState.customColumnSchemas = next;
  saveCustomColumnSchemas(next, customSchemaStorageOptions());
}

function allInventoryTaskRows() {
  return listValue(workbenchState.inventory?.datasets).flatMap(dataset =>
    listValue(dataset?.tasks).map(task => ({
      kind: "task",
      dataset,
      task,
      entry: null,
      key: `dataset:${dataset.id}|task:${task?.directory || ""}`,
      datasetId: dataset.id,
      taskName: task?.directory || "",
    })),
  );
}

function hasWritableDataset() {
  return listValue(workbenchState.inventory?.datasets).some(dataset => !datasetIsReadOnly(dataset));
}

function activeCustomColumns() {
  const inventory = workbenchState.inventory;
  const schemas = customColumnSchemas();
  const version = workbenchState.customMetadataVersion;
  if (
    customColumnsCache.inventory === inventory
    && customColumnsCache.schemas === schemas
    && customColumnsCache.version === version
  ) {
    return customColumnsCache.value;
  }
  const value = discoverCustomColumns(allInventoryTaskRows(), schemas);
  customColumnsCache = { inventory, schemas, version, value };
  return value;
}

function taskColumnOptions(flattened = workbenchState.flattened) {
  return {
    workspaceId: RENDER_OPTIONS?.workspace_id,
    tableId: flattened ? "task-items" : "tasks",
    storage: browserStorage(),
    retainUnknown: isCustomColumnKey,
  };
}

function ensureColumnVisibleInLayouts(columnKey) {
  for (const flattened of [false, true]) {
    const state = flattened ? workbenchState.taskItemColumns : workbenchState.taskColumns;
    const options = taskColumnOptions(flattened);
    const current = state.layout || loadColumnLayout([columnKey], options);
    const next = {
      ...current,
      order: current.order.includes(columnKey) ? [...current.order] : [...current.order, columnKey],
      visibility: { ...(current.visibility || {}), [columnKey]: "show" },
    };
    state.layout = next;
    saveColumnLayout(next, options);
  }
}

function removeColumnFromLayouts(columnKey) {
  for (const flattened of [false, true]) {
    const state = flattened ? workbenchState.taskItemColumns : workbenchState.taskColumns;
    const options = taskColumnOptions(flattened);
    const current = state.layout || loadColumnLayout([], options);
    const visibility = { ...(current.visibility || {}) };
    delete visibility[columnKey];
    const next = {
      ...current,
      order: (current.order || []).filter(key => key !== columnKey),
      visibility,
    };
    state.layout = next;
    saveColumnLayout(next, options);
  }
}

function customColumnSuggestions(col) {
  const values = [];
  const seen = new Set();
  for (const row of allInventoryTaskRows()) {
    const raw = row.task?.custom_metadata?.[col.rawKey];
    const items = col.type === "list"
      ? (Array.isArray(raw) ? raw : [])
      : (typeof raw === "string" ? [raw] : []);
    for (const item of items) {
      const text = String(item ?? "").trim();
      if (!text || seen.has(text)) continue;
      seen.add(text);
      values.push(text);
    }
  }
  return values;
}

function updateInventoryTask(datasetId, taskName, updatedTask) {
  const current = datasetForId(datasetId)?.tasks?.find(task => task.directory === taskName);
  if (current) Object.assign(current, updatedTask);
  if (workbenchState.taskDetail?.task && workbenchState.datasetId === datasetId && workbenchState.taskName === taskName) {
    Object.assign(workbenchState.taskDetail.task, updatedTask);
  }
  workbenchState.customMetadataVersion += 1;
}

function sameCustomValue(left, right) {
  const a = left === undefined ? null : left;
  const b = right === undefined ? null : right;
  if (a === b) return true;
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((item, index) => item === b[index]);
  }
  return false;
}

async function commitTaskMetadataCell(row, col, rawInput) {
  if (!adminMode() || row?.kind !== "task" || datasetIsReadOnly(row.dataset)) {
    throw new Error(t("harbor_dataset_read_only", "Dataset is read-only"));
  }
  if (rawInput === UNCHANGED_METADATA_SENTINEL) return;
  const parsed = parseCustomColumnInput(col.type, rawInput, col.options);
  if (sameCustomValue(row.task?.custom_metadata?.[col.rawKey], parsed)) return;
  const path = `/api/harbor/datasets/${encodeURIComponent(row.datasetId)}/tasks/${encodeURIComponent(row.taskName)}/metadata`;
  try {
    const saved = await serveApi(path, {
      method: "PATCH",
      body: { key: col.rawKey, value: parsed },
      ifMatch: row.task.revision,
    });
    if (saved?.task) {
      Object.assign(row.task, saved.task);
      updateInventoryTask(row.datasetId, row.taskName, saved.task);
    }
    const viewingCleanToml = row.datasetId === workbenchState.datasetId
      && row.taskName === workbenchState.taskName
      && workbenchTaskBrowser()?.currentFile()?.path === "task.toml"
      && !isHarborDirty();
    if (viewingCleanToml) {
      void workbenchTaskBrowser()?.openPath("task.toml", { focus: false });
    }
    if (saved?.id) {
      // The cell updates the shared task projection immediately from saved.task;
      // avoid a post-reconcile full table re-render that could interrupt a follow-up click or editor.
      const feedback = taskFeedback("task", row.taskName, `metadata:${col.rawKey}`);
      void watchOperation(saved.id, {
        feedback,
        committed: true,
      });
    }
  } catch (error) {
    if (error.status === 412) {
      try {
        const fresh = await serveApi(`/api/harbor/datasets/${encodeURIComponent(row.datasetId)}/tasks/${encodeURIComponent(row.taskName)}`);
        if (fresh?.task) {
          row.task.revision = fresh.task.revision;
          updateInventoryTask(row.datasetId, row.taskName, { revision: fresh.task.revision });
          const currentValue = formatCustomColumnValue(fresh.task.custom_metadata?.[col.rawKey], col.type)
            || t("task_custom_unset", "Unset");
          error.savedContent = savedContentPreview(col.label, currentValue);
        }
      } catch (refreshError) {
        error.message += ` (${refreshError.message})`;
      }
    }
    throw error;
  }
}

async function openCreateCustomColumn(opener = document.activeElement) {
  if (!adminMode() || workbenchState.showTrash || workbenchState.busy || !hasWritableDataset()) return null;
  const visibleTasks = uniqueTasks(visibleOverviewRows());
  const visibleEditable = visibleTasks.filter(row => !datasetIsReadOnly(row.dataset));
  const visibleReadOnlyCount = visibleTasks.length - visibleEditable.length;
  const selectedEditable = selectedTaskRows().filter(row => row.kind === "task");
  const existingKeys = new Set(activeCustomColumns().map(col => col.rawKey));
  return openCustomColumnModal({
    mode: "create",
    existingKeys,
    selectedEditableCount: selectedEditable.length,
    visibleEditableCount: visibleEditable.length,
    selectedReadOnlyCount: 0,
    visibleReadOnlyCount,
    opener,
    async onSubmit({ key, type, options, defaultValue, scope }) {
      const schemas = [...customColumnSchemas().filter(item => item.key !== key), { key, type, options }];
      const columnKey = encodeCustomColumnKey(key);
      if (defaultValue !== null) {
        const targets = scope === "selected" && selectedEditable.length ? selectedEditable : visibleEditable;
        setWorkbenchBusy(true);
        try {
          const operation = await serveApi("/api/harbor/task-metadata-operations", {
            method: "POST",
            body: {
              key,
              value: defaultValue,
              overwrite: false,
              items: targets.map(row => ({
                dataset_id: row.datasetId,
                task: row.taskName,
                etag: `"${row.task.revision}"`,
              })),
            },
          });
          setCustomColumnSchemas(schemas);
          ensureColumnVisibleInLayouts(columnKey);
          renderHarborWorkbench();
          trackOperation(operation, {
            feedback: taskFeedback("task", key, "custom-column-create"),
          });
        } finally {
          setWorkbenchBusy(false);
        }
        return true;
      }
      setCustomColumnSchemas(schemas);
      ensureColumnVisibleInLayouts(columnKey);
      renderHarborWorkbench();
      return true;
    },
  });
}

async function openEditCustomColumn(custom, opener = document.activeElement) {
  if (!adminMode() || !custom || workbenchState.busy) return null;
  return openCustomColumnModal({
    mode: "edit",
    column: custom,
    opener,
    async onSubmit({ key, type, options }) {
      const existing = customColumnSchemas();
      const index = existing.findIndex(item => item.key === key);
      const next = [...existing];
      if (index >= 0) next[index] = { key, type, options };
      else next.push({ key, type, options });
      setCustomColumnSchemas(next);
      renderHarborWorkbench();
      return true;
    },
  });
}

async function deleteCustomColumn(custom) {
  if (!adminMode() || !custom || workbenchState.busy) return false;
  const allTasks = allInventoryTaskRows().filter(
    row => row.task?.custom_metadata && Object.prototype.hasOwnProperty.call(row.task.custom_metadata, custom.rawKey),
  );
  const writable = allTasks.filter(row => !datasetIsReadOnly(row.dataset));
  const readOnlyCount = allTasks.length - writable.length;
  if (!writable.length && !custom.defined) return false;
  if (writable.length > 0) {
    const promptText = [
      formatMessage("task_custom_delete_confirm", "Remove custom column “{key}” from {count} editable Task(s)’ task.toml files?", {
        key: custom.rawKey,
        count: writable.length,
      }),
      readOnlyCount > 0
        ? formatMessage("task_custom_delete_readonly_note", "{count} read-only Task(s) keep their original task.toml values.", { count: readOnlyCount })
        : "",
    ].filter(Boolean).join("\n");
    if (!window.confirm(promptText)) return false;
    const feedback = taskFeedback("task", custom.rawKey, "custom-column-delete");
    setWorkbenchBusy(true);
    try {
      const operation = await serveApi("/api/harbor/task-metadata-operations", {
        method: "POST",
        body: {
          key: custom.rawKey,
          value: null,
          overwrite: true,
          items: writable.map(row => ({
            dataset_id: row.datasetId,
            task: row.taskName,
            etag: `"${row.task.revision}"`,
          })),
        },
      });
      setCustomColumnSchemas(customColumnSchemas().filter(item => item.key !== custom.rawKey));
      removeColumnFromLayouts(custom.key);
      renderHarborWorkbench();
      trackOperation(operation, { feedback });
      return true;
    } catch (error) {
      feedback.error(error);
      return false;
    } finally {
      setWorkbenchBusy(false);
    }
  }
  setCustomColumnSchemas(customColumnSchemas().filter(item => item.key !== custom.rawKey));
  removeColumnFromLayouts(custom.key);
  renderHarborWorkbench();
  return true;
}

function harborColumns() {
  const canEditRuleCount = row => adminMode() && registryManager?.ready && row.kind === "task" && row.dataset.format === "workbuddy.v1";
  const canEditCustomMetadata = (row, col) => adminMode() && row.kind === "task" && !datasetIsReadOnly(row.dataset) && col.type !== "readonly";
  return taskColumns({
    scoring: !workbenchState.showTrash,
    flattened: workbenchState.flattened,
    canEditRuleCount,
    customColumns: workbenchState.showTrash ? [] : activeCustomColumns(),
    canEditCustomMetadata,
    customColumnSuggestions,
    editCustomMetadata: (row, col, raw) => {
      if (col.type === "enum") {
        const options = [{ value: "", label: t("task_custom_unset", "Unset") }];
        if (raw == null) {
          for (const option of col.options) options.push({ value: option, label: option });
          return { value: "", options, commit: (_r, value) => commitTaskMetadataCell(row, col, value) };
        }
        if (typeof raw === "string" && col.options.includes(raw)) {
          for (const option of col.options) options.push({ value: option, label: option });
          return { value: raw, options, commit: (_r, value) => commitTaskMetadataCell(row, col, value) };
        }
        const label = formatCustomColumnValue(raw, "text") || String(raw);
        let matched = false;
        for (const option of col.options) {
          if (!matched && option === label) {
            matched = true;
            options.push({ value: UNCHANGED_METADATA_SENTINEL, label: option });
          } else {
            options.push({ value: option, label: option });
          }
        }
        if (!matched) options.splice(1, 0, { value: UNCHANGED_METADATA_SENTINEL, label });
        return { value: UNCHANGED_METADATA_SENTINEL, options, commit: (_r, value) => commitTaskMetadataCell(row, col, value) };
      }
      if (col.type === "boolean") {
        const options = [
          { value: "", label: t("task_custom_unset", "Unset") },
          { value: "true", label: t("yes", "Yes") },
          { value: "false", label: t("no", "No") },
        ];
        if (raw == null || typeof raw === "boolean") {
          const current = typeof raw === "boolean" ? String(raw) : "";
          return { value: current, options, commit: (_r, value) => commitTaskMetadataCell(row, col, value) };
        }
        const label = formatCustomColumnValue(raw, "text") || String(raw);
        options.splice(1, 0, { value: UNCHANGED_METADATA_SENTINEL, label });
        return { value: UNCHANGED_METADATA_SENTINEL, options, commit: (_r, value) => commitTaskMetadataCell(row, col, value) };
      }
      if (col.type === "list") {
        return {
          value: Array.isArray(raw) ? raw : raw != null ? [String(raw)] : [],
          suggestions: () => customColumnSuggestions(col),
          commit: (_r, value) => commitTaskMetadataCell(row, col, value),
        };
      }
      if (col.type === "number") {
        return {
          value: raw ?? "",
          commit: (_r, value) => commitTaskMetadataCell(row, col, value),
        };
      }
      return {
        value: raw ?? "",
        suggestions: () => customColumnSuggestions(col),
        commit: (_r, value) => commitTaskMetadataCell(row, col, value),
      };
    },
    editRuleCount: row => {
      if (!canEditRuleCount(row)) return null;
      const writeCount = registryManager.taskRuleCountWriter(row.datasetId, row.taskName);
      return {
        value: row.task.rule_count ?? "", commit: async (_current, value) => {
          const text = String(value).trim();
          if (text && (!/^\d+$/.test(text) || !Number.isSafeInteger(Number(text)))) throw new Error(t("task_rules_invalid", "Enter a nonnegative whole number, or clear the value"));
          const count = text ? Number(text) : null;
          const saved = await writeCount(count);
          Object.assign(row.task, saved.task);
          const current = datasetForId(row.datasetId)?.tasks?.find(task => task.directory === row.taskName);
          if (current && current !== row.task) Object.assign(current, saved.task);
        },
      };
    },
    selection: adminMode() ? selectionColumn({ key: "__task_select", selectionKey: overviewRowKey,
      selectionSet: () => workbenchState.taskSelection, selectable: row => row.kind !== "empty" && !datasetIsReadOnly(row.dataset),
      rowAriaLabel: (_key, row) => `${t("select_row", "Select row")}: ${rowTaskName(row)}` }) : null,
    rename: row => adminMode() && row.kind !== "empty" && !datasetIsReadOnly(row.dataset) ? {
      value: rowTaskName(row), commit: (_current, value) => renameOverviewTask(row, value),
    } : null,
  });
}

function resolveTaskTableColumns(allColumns, filteredRows) {
  if (workbenchState.showTrash) {
    return { columns: allColumns, businessColumns: allColumns.filter(col => !col.select), layout: null, presence: null, columnState: null, options: null };
  }
  const businessColumns = allColumns.filter(col => !col.select);
  const columnState = workbenchState.flattened ? workbenchState.taskItemColumns : workbenchState.taskColumns;
  const options = taskColumnOptions(workbenchState.flattened);
  columnState.layout ||= loadColumnLayout(businessColumns.map(col => col.key), options);
  const layout = normalizeColumnLayout(businessColumns.map(col => col.key), columnState.layout, options);
  const presence = presenceForColumns(businessColumns, filteredRows, null, tableControls(HARBOR_TABLE_ID).filters);
  const columns = [...allColumns.filter(col => col.select), ...resolveColumns(businessColumns, layout, presence)];
  return { columns, businessColumns, layout, presence, columnState, options };
}

function visibleOverviewRows(rows = overviewRows(), columns = harborColumns()) {
  const query = String(workbenchState.search || "").trim().toLowerCase();
  const searched = query ? rows.filter(row => taskSearchText(row).includes(query)) : rows;
  return workbenchState.flattened && !workbenchState.showTrash
    ? applyDataTableFilters(HARBOR_TABLE_ID, flattenTaskRows(searched), columns)
    : applyDataTableControls(HARBOR_TABLE_ID, searched, columns);
}

function overviewTable() {
  const allRows = overviewRows();
  const columns = harborColumns();
  return { allRows, columns, rows: visibleOverviewRows(allRows, columns) };
}

function selectedOverviewKey() {
  if (!workbenchState.datasetId) return "";
  if (workbenchState.showTrash) {
    return workbenchState.trashEntryId
      ? `dataset:${workbenchState.datasetId}|trash:${workbenchState.trashEntryId}`
      : "";
  }
  return `dataset:${workbenchState.datasetId}|task:${workbenchState.taskName || ""}`;
}

function setOverviewSelection(row) {
  workbenchState.datasetId = row?.dataset?.id || null;
  workbenchState.taskName = row?.kind === "task" ? row.task?.directory || null : null;
  window.dispatchEvent(new window.Event("peval:workspace-context"));
  workbenchState.trashEntryId = row?.kind === "trash" ? row.entry?.entry_id || null : null;
  workbenchState.taskDetail = null;
  workbenchState.taskRequestId += 1;
  clearEditor();
}

function reconcileOverviewSelection(rows) {
  const currentKey = selectedOverviewKey();
  const current = rows.find(row => overviewRowKey(row) === currentKey) || null;
  if (current) return { row: current, changed: false };
  if (isHarborDirty()) return { row: null, changed: false };
  const row = rows[0] || null;
  setOverviewSelection(row);
  return { row, changed: true };
}

function renderTaskColumnControl(surface, resolved) {
  const host = surface.querySelector("[data-task-columns-control]");
  if (!host) return;
  host.hidden = workbenchState.showTrash || !resolved.layout;
  if (host.hidden) {
    host.replaceChildren();
    return;
  }
  const writable = hasWritableDataset();
  const control = createColumnControl({
    id: workbenchState.flattened ? "task-items" : "tasks",
    state: resolved.columnState,
    options: resolved.options,
    context: () => ({
      columns: resolved.businessColumns,
      layout: resolved.layout,
      presence: resolved.presence,
    }),
    conditionText: column => {
      const controls = tableControls(HARBOR_TABLE_ID);
      return [
        controls.sort === column.key ? controls.direction : "",
        controls.filters?.[column.key]?.length ? t("filtered", "Filtered") : "",
      ].filter(Boolean).join(" · ");
    },
    headerAction: adminMode() ? {
      label: `+ ${t("task_custom_column_new", "New custom column")}`,
      disabled: workbenchState.busy || !writable,
      onClick: opener => openCreateCustomColumn(opener),
    } : null,
    rowActions: adminMode() ? column => {
      if (!isCustomColumnKey(column.key)) return [];
      const custom = column.customColumn;
      const canDelete = Boolean(custom && (custom.defined || custom.hasWritableData));
      return [
        {
          key: "edit",
          label: t("edit", "Edit"),
          title: t("task_custom_column_edit", "Edit custom column"),
          disabled: workbenchState.busy,
          onClick: (_col, opener) => openEditCustomColumn(custom, opener),
        },
        {
          key: "delete",
          label: t("delete", "Delete"),
          title: t("task_custom_column_delete", "Delete column"),
          danger: true,
          disabled: workbenchState.busy || !canDelete,
          onClick: () => deleteCustomColumn(custom),
        },
      ];
    } : null,
    onRender: () => {
      renderHarborWorkbench();
      return surface.querySelector("[data-task-columns-control]");
    },
  });
  host.innerHTML = control.render();
  control.bind(host);
}

function renderHarborOverview(surface, { allRows, columns, rows }) {
  const container = surface.querySelector("[data-harbor-overview]");
  if (!container) return;
  const loading = workbenchState.inventory?.checking && !workbenchState.inventory?.generation;
  if (loading) {
    container.innerHTML = `<p role="status">${esc(t("loading", "Loading…"))}</p>`;
    surface.querySelector("[data-task-summary]")?.setAttribute("hidden", "");
    return;
  }
  const flattened = workbenchState.flattened && !workbenchState.showTrash;
  const displayRows = flattened ? sortDataTableRows(HARBOR_TABLE_ID, rows, columns) : rows;
  const resolved = resolveTaskTableColumns(columns, displayRows);
  workbenchState.displayRows = displayRows;
  workbenchState.visibleColumns = resolved.columns;
  renderTaskColumnControl(surface, resolved);
  renderTaskTable({ root: container, tableId: HARBOR_TABLE_ID, allRows, columns: resolved.columns, rows: displayRows,
    selectedKey: selectedOverviewKey(), rowAttribute: "data-harbor-overview-row",
    onActivate: (row, node, column) => selectOverviewRow(row, node, scoringPath(row, column)),
    onChange: () => refreshOverviewAfterControls(() => {
      restoreTableControls();
      renderHarborWorkbench();
    }), onSelectionChange: renderHarborWorkbench });
  const count = surface.querySelector("[data-harbor-overview-count]");
  if (count) count.textContent = `${new Set(rows.map(taskRowIdentity)).size} / ${allRows.length}`;
  renderScoringControls(surface, rows);
}

function scoringPath(row, column) {
  if (workbenchState.showTrash || row?.kind !== "task") return null;
  if (isCustomColumnKey(column)) return "task.toml";
  const resources = { skill_count: "skills", input_file_count: "files", has_prepare: "prepare" };
  if (resources[column]) return { resource: resources[column] };
  if (row.scoringItem) return row.scoringItem.path;
  const kind = column === "rule_count" ? "rule" : ["rubric_count", "scoring_item_count"].includes(column) ? "rubric" : null;
  return kind ? row.task.scoring_paths?.[kind] || row.task.instruction_path || "instruction.md" : null;
}

function renderScoringControls(surface, rows) {
  const tasks = uniqueTasks(rows);
  let actions = surface.querySelector("[data-task-scoring-actions]");
  if (!actions) {
    actions = document.createElement("div"); actions.dataset.taskScoringActions = ""; actions.className = "table-region-actions task-scoring-actions";
    (surface.querySelector(".harbor-workbench-tools") || surface.querySelector(".harbor-overview-head"))?.append(actions);
  }
  actions.hidden = workbenchState.showTrash;
  const viewOptions = surface.querySelector("[data-task-view-options]");
  if (viewOptions) {
    viewOptions.hidden = workbenchState.showTrash;
    viewOptions.innerHTML = `<label class="toolbar-menu-check"><input type="checkbox" data-task-flatten ${workbenchState.flattened ? "checked" : ""}><span>${esc(t("task_flatten", "Flatten scoring items"))}</span></label>`;
    viewOptions.querySelector("[data-task-flatten]").addEventListener("change", event => { workbenchState.flattened = event.target.checked; renderHarborWorkbench(); });
  }
  actions.innerHTML = `<details class="export-menu"><summary class="export-menu-button">${esc(t("export", "Export"))}</summary><div class="export-menu-panel"><button type="button" data-task-export="xlsx">${esc(t("export_excel", "Export Excel"))}</button><button type="button" data-task-export="json">${esc(t("export_json", "Export JSON"))}</button></div></details>`;
  actions.querySelectorAll("[data-task-export]").forEach(button => {
    button.disabled = !tasks.length;
    button.addEventListener("click", () => { button.closest("details").open = false; downloadTaskTable(button.dataset.taskExport); });
  });
  let note = surface.querySelector("[data-task-unexpanded]");
  if (!note) { note = document.createElement("p"); note.dataset.taskUnexpanded = ""; note.className = "copy task-unexpanded"; surface.querySelector("[data-harbor-overview]")?.before(note); }
  const manual = tasks.filter(row => row.task?.rule_count_source === "manual").reduce((total, row) => total + row.task.rule_count, 0);
  const unknown = tasks.filter(row => row.task?.rule_count == null).length;
  note.hidden = workbenchState.showTrash || !workbenchState.flattened || !manual && !unknown;
  note.textContent = [manual ? t("task_unexpanded_rules", "Manually counted rules without item details: {count}.").replace("{count}", String(manual)) : "",
    unknown ? t("task_unknown_rules", "Tasks with an unknown rule count: {count}.").replace("{count}", String(unknown)) : ""].filter(Boolean).join(" ");
  let summary = surface.querySelector("[data-task-summary]");
  if (!summary) {
    summary = document.createElement("section"); summary.dataset.taskSummary = ""; summary.className = "harbor-overview-panel task-summary";
    (surface.querySelector("[data-harbor-overview]")?.closest(".harbor-overview-panel") || surface.querySelector("[data-harbor-overview]"))?.after(summary);
  }
  summary.hidden = workbenchState.showTrash;
  if (!summary.hidden) renderTaskSummary(summary, tasks, workbenchState.summary, {
    customColumns: activeCustomColumns(),
    onChange: () => renderScoringControls(surface, rows),
    onExport: kind => downloadTaskTable(kind, true),
  });
  bindToolbarMenus(surface);
}

async function downloadTaskTable(kind, summary = false) {
  const surface = workbenchRoot();
  const settings = workbenchState.summary;
  if (summary && settings.exporting) return;
  if (!summary && !workbenchState.visibleColumns.length) return;
  const rows = summary ? uniqueTasks(visibleOverviewRows()) : workbenchState.displayRows;
  const feedback = beginFeedback(surface.querySelector(summary ? "[data-task-summary]" : "[data-task-scoring-actions]"), { page: "datasets", key: "datasets:export" });
  try {
    if (summary) { settings.exporting = true; renderScoringControls(surface, rows); }
    if (summary && ["bar", "pie"].includes(kind)) await exportTaskSummaryImage(rows, settings, kind, activeCustomColumns());
    else await exportTasks({ kind, mode: summary ? "summary" : workbenchState.flattened ? "items" : "tasks",
      rows, columns: summary ? taskSummaryExportColumns(settings) : workbenchState.visibleColumns,
      groupBy: settings.groupBy, groups: summary ? settings.groups : null });
    feedback.success();
  } catch (error) { feedback.error(error); }
  finally { if (summary) { settings.exporting = false; renderScoringControls(surface, visibleOverviewRows()); } }
}

function flushDeferredInventoryRender() {
  if (!pendingInventoryRender) return;
  const surface = workbenchRoot();
  if (!surface) {
    pendingInventoryRender = false;
    return;
  }
  if (surface.querySelector(OVERVIEW_OVERLAY_SELECTOR)) return;
  pendingInventoryRender = false;
  renderHarborWorkbench({ preserveEditors: true });
}

function scheduleDeferredInventoryRender(surface) {
  pendingInventoryRender = true;
  surface.querySelectorAll("[data-harbor-overview] details[open], [data-task-columns-control] details[open]").forEach(menu => {
    if (watchedDeferredOverlays.has(menu)) return;
    watchedDeferredOverlays.add(menu);
    menu.addEventListener("toggle", () => {
      if (!menu.open) queueMicrotask(flushDeferredInventoryRender);
    });
  });
  surface.querySelectorAll("[data-harbor-overview] [data-table-cell-editor]").forEach(editor => {
    if (watchedDeferredOverlays.has(editor)) return;
    watchedDeferredOverlays.add(editor);
    editor.addEventListener("keydown", event => {
      if (event.key === "Escape") queueMicrotask(flushDeferredInventoryRender);
    });
  });
}

function renderHarborWorkbench({ preserveEditors = false, table } = {}) {
  const surface = workbenchRoot();
  if (!surface) return { row: null, changed: false };
  const overview = table ?? overviewTable();
  const { allRows, rows } = overview;
  const availableKeys = new Set(allRows
    .filter(row => row.kind !== "empty" && !datasetIsReadOnly(row.dataset))
    .map(overviewRowKey));
  Array.from(workbenchState.taskSelection).forEach(key => {
    if (!availableKeys.has(key)) workbenchState.taskSelection.delete(key);
  });
  const editing = preserveEditors && Boolean(surface.querySelector(OVERVIEW_OVERLAY_SELECTOR));
  const selection = editing ? { row: rows.find(row => overviewRowKey(row) === selectedOverviewKey()), changed: false } : reconcileOverviewSelection(rows);
  if (editing) {
    scheduleDeferredInventoryRender(surface);
  } else {
    pendingInventoryRender = false;
    renderHarborOverview(surface, overview);
  }
  renderContextControls(surface);
  renderSelectedTaskHeading(taskDetailRoot());
  renderFileTree(taskDetailRoot());
  renderDiagnostics(taskDetailRoot());
  syncWorkbenchBusy(surface);
  workbenchState.tableSnapshot = cloneTableControls();
  return selection;
}

function cloneTableControls() {
  return JSON.parse(JSON.stringify(tableControls(HARBOR_TABLE_ID)));
}

function restoreTableControls() {
  const controls = tableControls(HARBOR_TABLE_ID);
  Object.keys(controls).forEach(key => delete controls[key]);
  Object.assign(controls, JSON.parse(JSON.stringify(workbenchState.tableSnapshot || {})));
}

function renderContextControls(surface) {
  const dataset = selectedDataset();
  setDisabled(surface, "[data-harbor-create-task]", workbenchState.busy || !dataset || datasetIsReadOnly(dataset) || workbenchState.showTrash);
  setDisabled(surface, "[data-harbor-add-column]", workbenchState.busy || workbenchState.showTrash || !hasWritableDataset());
  setDisabled(surface, "[data-harbor-sync-manifest]", workbenchState.busy || !dataset || datasetIsReadOnly(dataset) || workbenchState.showTrash);
  setDisabled(surface, "[data-harbor-state-selected]", workbenchState.busy || workbenchState.taskSelection.size < 1);
  setDisabled(surface, "[data-harbor-delete-selected]", workbenchState.busy || workbenchState.taskSelection.size < 1);
  setDisabled(surface, "[data-harbor-show-trash]", workbenchState.busy || !listValue(workbenchState.inventory?.datasets).length);
  const stateButton = surface.querySelector("[data-harbor-state-selected]");
  if (stateButton) stateButton.textContent = workbenchState.showTrash
    ? t("restore_selected", "Restore selected")
    : t("archive_selected", "Archive selected");
  const archivedToggle = surface.querySelector("[data-harbor-show-trash]");
  if (archivedToggle) archivedToggle.checked = workbenchState.showTrash;
}

function setWorkbenchBusy(busy) {
  workbenchMutationBusy = Boolean(busy);
  syncWorkbenchBusyState();
}

function syncWorkbenchBusyState() {
  workbenchState.busy = workbenchMutationBusy || trackedWorkbenchOperations.size > 0;
  const surface = workbenchRoot();
  if (!surface) return;
  renderContextControls(surface);
  syncWorkbenchBusy(surface);
  workbenchTaskBrowser()?.setBusy(workbenchState.busy);
}

function syncWorkbenchBusy(surface = workbenchRoot()) {
  if (!surface) return;
  surface.setAttribute("aria-busy", workbenchState.busy ? "true" : "false");
  surface.querySelectorAll("[data-table-row-select],[data-table-select-visible]").forEach(control => {
    control.disabled = workbenchState.busy;
  });
}

function setDisabled(surface, selector, disabled) {
  const control = surface.querySelector(selector);
  if (control) control.disabled = Boolean(disabled);
}

function renderSelectedTaskHeading(surface) {
  const title = surface.querySelector("[data-harbor-selected-title]");
  const meta = surface.querySelector("[data-harbor-selected-meta]");
  const dataset = selectedDataset();
  const task = workbenchState.taskDetail?.task || selectedTask();
  const trash = selectedTrashEntry();
  let runLink = surface.querySelector('[data-harbor-run-task]');
  if (!runLink && meta) {
    runLink = document.createElement('a');
    runLink.className = 'action-button';
    runLink.dataset.harborRunTask = '';
    runLink.dataset.workspaceRoute = 'jobs';
    meta.after(runLink);
  }
  if (runLink) {
    runLink.hidden = !task || Boolean(trash);
    runLink.textContent = t('jobs_configure_run', 'Configure run');
    runLink.href = `/jobs#task=${encodeURIComponent(`${workbenchState.datasetId}/${task?.directory || ''}`)}`;
  }
  if (title) title.textContent = task?.directory || trash?.directory || t("harbor_task_detail_empty", "Select a Task");
  if (meta) {
    meta.textContent = task
      ? `${workbenchState.datasetId} · ${dataset?.format || "harbor"} · ${datasetIsReadOnly(dataset) ? t("read_only", "Read-only") : t("editable", "Editable")} · ${task.package_name || "-"} · ${t(`harbor_status_${task.status || "draft"}`, task.status || "draft")}`
      : trash
        ? `${workbenchState.datasetId} · ${trash.package_name || "-"} · ${t("harbor_trash", "Archived")}`
        : "";
  }
}

function renderFileTree(surface = taskDetailRoot()) {
  const actions = surface?.querySelector?.("[data-harbor-file-actions]");
  const mutable = canMutateSelectedTask();
  if (actions) actions.hidden = !mutable || !workbenchState.taskDetail || workbenchState.showTrash;
  const browser = workbenchTaskBrowser();
  browser?.setEditable(mutable);
  browser?.setContextMenu(mutable ? fileActionMenu : null);
}

function renderDiagnostics(surface = taskDetailRoot()) {
  const container = surface?.querySelector?.("[data-harbor-diagnostics]");
  if (!container) return;
  container.replaceChildren();
  const task = workbenchState.taskDetail?.task || selectedTask();
  [...listValue(task?.diagnostics), ...listValue(task?.scoring_diagnostics), ...listValue(task?.metadata_diagnostics), ...listValue(task?.resource_diagnostics)].forEach(diagnostic => container.append(textNode("p", diagnostic)));
}

async function selectOverviewRow(row, opener, preferredPath = null) {
  if (!row) return;
  if (overviewRowKey(row) !== selectedOverviewKey() && !confirmDiscard()) return;
  taskSidebar?.open({ opener, openerSelector: `[data-harbor-overview-row][data-task-row-token="${encodeURIComponent(row.key)}"]` });
  if (overviewRowKey(row) === selectedOverviewKey()) {
    if (row.kind === "task" && !workbenchState.taskDetail) await loadSelectedTask(preferredPath);
    else if (preferredPath) await openSelectedPath(preferredPath);
    return;
  }
  setOverviewSelection(row);
  renderHarborWorkbench();
  if (row.kind === "task") await loadSelectedTask(preferredPath);
}

async function openSelectedPath(preferredPath) {
  const detail = workbenchState.taskDetail;
  if (!detail) return;
  if (preferredPath?.resource) { workbenchTaskBrowser()?.showResources(preferredPath.resource); return; }
  const path = detail.tree.some(item => item.kind === "file" && item.path === preferredPath) ? preferredPath : detail.default_file_path;
  if (path && workbenchTaskBrowser()?.currentFile()?.path !== path) await workbenchTaskBrowser()?.openPath(path);
}

async function selectTask(taskName) {
  const row = overviewRows().find(item => item.kind === "task"
    && item.dataset?.id === workbenchState.datasetId
    && item.task?.directory === taskName);
  if (!row) return;
  if (overviewRowKey(row) !== selectedOverviewKey()) {
    if (!confirmDiscard()) return;
    setOverviewSelection(row);
    renderHarborWorkbench();
  }
  await loadSelectedTask();
}

async function loadSelectedTask(preferredPath = null) {
  const datasetId = workbenchState.datasetId;
  const taskName = workbenchState.taskName;
  if (!datasetId || !taskName || workbenchState.showTrash) return;
  const requestId = workbenchState.taskRequestId + 1;
  workbenchState.taskRequestId = requestId;
  workbenchState.taskDetail = null;
  clearEditor();
  renderFileTree();
  const feedback = taskFeedback("file", taskName, "load");
  try {
    const detail = await serveApi(`/api/harbor/datasets/${encodeURIComponent(datasetId)}/tasks/${encodeURIComponent(taskName)}`);
    if (requestId !== workbenchState.taskRequestId || datasetId !== workbenchState.datasetId || taskName !== workbenchState.taskName) return;
    workbenchState.taskDetail = detail;
    renderSelectedTaskHeading(taskDetailRoot());
    renderFileTree(taskDetailRoot());
    renderDiagnostics(taskDetailRoot());
    await workbenchTaskBrowser()?.setTaskDetail(detail, {
      taskRef: { dataset_id: datasetId, task: taskName },
      preferredPath: preferredPath?.resource ? null : preferredPath,
    });
    if (preferredPath?.resource) workbenchTaskBrowser()?.showResources(preferredPath.resource);
  } catch (error) {
    if (requestId === workbenchState.taskRequestId) feedback.error(error);
  }
}

async function refreshOverviewAfterControls(onCancel) {
  const table = overviewTable();
  const selectedKey = selectedOverviewKey();
  if (isHarborDirty() && !table.rows.some(row => taskRowIdentity(row) === selectedKey)) {
    if (!confirmDiscard()) {
      onCancel();
      return;
    }
    clearEditor();
  }
  const selection = renderHarborWorkbench({ table });
  if (selection.changed && selection.row?.kind === "task") await loadSelectedTask();
}

let inventoryObserver = null, inventoryTimer = null, inventoryRequest = 0, inventoryFailures = 0;
function renderTaskInventoryStatus(error = null) {
  const root = workbenchRoot();
  if (!root) return;
  let notice = root.querySelector("[data-task-inventory-status]");
  if (!notice) {
    notice = document.createElement("p");
    notice.dataset.taskInventoryStatus = ""; notice.className = "copy"; notice.setAttribute("role", "status");
    root.querySelector("[data-harbor-workbench-status]")?.after(notice);
  }
  const status = workbenchState.inventory || {};
  const failure = error?.message || error || status.error;
  const message = failure ? [status.generation ? t("task_inventory_stale", "Showing the last saved Task inventory.") : "", failure].filter(Boolean).join(" ")
    : status.checking ? t(status.generation ? "task_inventory_checking" : "loading", status.generation ? "Checking Tasks; showing the last saved inventory." : "Loading…") : "";
  notice.replaceChildren(); notice.hidden = !message;
  if (message) notice.append(document.createTextNode(message));
  if (failure) {
    const retry = document.createElement("button");
    retry.type = "button"; retry.textContent = t("feedback_retry", "Check again");
    retry.addEventListener("click", () => {
      pauseTaskInventory(); resumeTaskInventory();
      void refreshHarborInventory({ check: true, skipGuard: true, skipTaskReload: true });
    });
    notice.append(" ", retry);
  }
}
function pauseTaskInventory() {
  inventoryObserver?.abort(); inventoryObserver = null;
  window.clearTimeout(inventoryTimer); inventoryTimer = null;
}
function resumeTaskInventory() {
  if (inventoryObserver) return;
  inventoryObserver = new AbortController();
  inventoryFailures = 0;
  scheduleTaskInventory();
}
function scheduleTaskInventory() {
  if (!inventoryObserver || inventoryTimer) return;
  const observer = inventoryObserver;
  inventoryTimer = window.setTimeout(async () => {
    inventoryTimer = null;
    try {
      const status = await serveApi("/api/collections/datasets/status", { signal: observer.signal });
      if (observer !== inventoryObserver) return;
      if (status.generation !== workbenchState.inventory?.generation) {
        const payload = await refreshHarborInventory({ quiet: true, skipGuard: true, skipTaskReload: true, signal: observer.signal });
        if (!payload && !observer.signal.aborted) throw new Error(t("feedback_refresh_failed", "Workspace refresh failed"));
      }
      else if (workbenchState.inventory) {
        Object.assign(workbenchState.inventory, status);
        if (!status.generation && !status.checking) renderHarborWorkbench({ preserveEditors: true });
      }
      if (observer !== inventoryObserver) return;
      inventoryFailures = 0;
      renderTaskInventoryStatus();
      if (status.checking) scheduleTaskInventory();
    } catch (error) {
      if (observer.signal.aborted) return;
      renderTaskInventoryStatus(error);
      if (++inventoryFailures === 1) scheduleTaskInventory();
    }
  }, 500);
}
async function refreshHarborInventory(options = {}) {
  if (!options.skipGuard && !confirmDiscard()) return null;
  const feedback = options.quiet ? null : pageFeedback("[data-harbor-workbench-status]");
  feedback?.pending(t("serve_loading_sources", "Loading…"));
  try {
    const request = ++inventoryRequest;
    if (options.check) await serveApi("/api/collections/datasets/refresh", { method: "POST", body: {} });
    const payload = await serveApi("/api/collections/datasets", { signal: options.signal });
    if (request !== inventoryRequest || options.signal?.aborted) return payload;
    const positions = Array.from(workbenchRoot()?.querySelectorAll("[data-workspace-scroll]") || []).map(node => [node.scrollLeft, node.scrollTop]);
    workbenchState.inventory = payload;
    if (!payload.datasets.some(row => row.id === workbenchState.datasetFilter)) workbenchState.datasetFilter = null;
    renderDatasetRegistry();
    const selection = renderHarborWorkbench({ preserveEditors: true });
    Array.from(workbenchRoot()?.querySelectorAll("[data-workspace-scroll]") || []).forEach((node, index) => { if (positions[index]) [node.scrollLeft, node.scrollTop] = positions[index]; });
    if (selection.row?.kind === "task" && !options.skipTaskReload) await loadSelectedTask();
    feedback?.clear();
    inventoryFailures = 0;
    renderTaskInventoryStatus();
    if (payload.checking) scheduleTaskInventory();
    return payload;
  } catch (error) {
    if (!options.signal?.aborted) { feedback?.clear(); renderTaskInventoryStatus(error); }
    return null;
  }
}

async function initializeHarborWorkbench() {
  if (!taskSidebar) {
    taskSidebar = createCollectionSidebar({ id: "dataset-task", pageRoot: workbenchRoot(), content: workbenchRoot().querySelector(".harbor-task-detail"), title: t("task", "Task") });
    registryManager = createRegistryManager({ root: workbenchRoot().querySelector("[data-dataset-collections]"), page: "datasets",
      onRefresh: async () => { if (!await refreshHarborInventory({ skipGuard: true, skipTaskReload: isHarborDirty() })) throw new Error(t("feedback_refresh_failed", "Saved, but workspace refresh failed")); } });
  }
  let configurationError;
  try { await registryManager.refresh(); } catch (error) { configurationError = error; }
  bindHarborWorkbench();
  const inventory = await refreshHarborInventory({ skipGuard: true });
  if (configurationError) beginFeedback(workbenchRoot().querySelector("[data-dataset-collections]"), { page: "datasets" }).error(configurationError);
  return inventory;
}

async function openHarborWorkbench() {
  if (!workbenchRoot()) return false;
  await initializeHarborWorkbench();
  return true;
}

function clearEditor() {
  workbenchTaskBrowser()?.clear();
}

async function saveFile() {
  const file = workbenchTaskBrowser()?.currentFile();
  if (!canMutateSelectedTask() || !file?.dirty || !file.path) return;
  if (workbenchState.busy) {
    taskFeedback("file", workbenchState.taskName, "busy").error(t("harbor_operation_in_progress", "Another Task operation is still running"));
    return;
  }
  const task = selectedTask();
  if (!task) return;
  await mutateFiles({ action: "save", path: file.path, content: file.content, expected_revision: file.revision || task.revision }, { reopen: file.path });
}

async function mutateFiles(body, options = {}) {
  if (!canMutateSelectedTask() || workbenchState.busy) {
    if (options.rethrow) throw new Error(t("harbor_operation_in_progress", "Another Task operation is still running"));
    return null;
  }
  const datasetId = workbenchState.datasetId, taskName = workbenchState.taskName;
  if (options.taskRef && (options.taskRef.datasetId !== datasetId || options.taskRef.taskName !== taskName)) {
    throw new Error(t("feedback_target_changed", "The selected resource changed; reopen the form"));
  }
  const feedback = taskFeedback("file");
  setWorkbenchBusy(true);
  try {
    const base = `/api/harbor/datasets/${encodeURIComponent(datasetId)}/tasks/${encodeURIComponent(taskName)}`;
    const filePath = body.path ? `/${encodeURIComponent(body.path)}` : "";
    let path = `${base}/files${filePath}`;
    let method = "POST";
    let requestBody;
    if (body.action === "save") {
      method = "PUT";
      requestBody = { content: body.content };
    } else if (body.action === "rename") {
      method = "PATCH";
      requestBody = { new_path: body.new_path };
    } else if (body.action === "delete") {
      method = "DELETE";
    } else {
      path = `${base}/files`;
      requestBody = {
        kind: body.action === "upload" ? "upload" : body.kind,
        path: body.path,
        content: body.action === "upload" ? body.content_base64 : undefined,
      };
    }
    const operation = await serveApi(path, {
      method,
      body: requestBody,
      ifMatch: body.expected_revision,
    });
    if (body.action === "save" && datasetId === workbenchState.datasetId && taskName === workbenchState.taskName) workbenchTaskBrowser()?.acceptSave(body.path, body.content);
    trackOperation(operation, { ...options, feedback, datasetId, taskName, reopen: options.reopen || null });
    return operation;
  } catch (error) {
    let currentFile = null;
    if (error.status === 412) {
      try { currentFile = await refreshWorkbenchRevisions(datasetId, taskName, body.action === "save" ? body.path : null); }
      catch (refreshError) { error.message += ` (${refreshError.message})`; }
    }
    if (options.rethrow) { feedback.dispose(); throw error; }
    feedback.error(error, {
      details: currentFile ? [savedContentPreview(body.path, currentFile.content)] : [],
    });
    return null;
  } finally {
    setWorkbenchBusy(false);
  }
}

async function mutateTasks(body, datasetId = workbenchState.datasetId, options = {}) {
  if (!adminMode() || datasetIsReadOnly(datasetForId(datasetId)) || workbenchState.busy) {
    if (options.rethrow) throw new Error(t("harbor_operation_in_progress", "Another Task operation is still running"));
    return null;
  }
  const taskName = workbenchState.taskName;
  const draftBefore = workbenchTaskBrowser()?.currentFile();
  const feedback = taskFeedback("task");
  setWorkbenchBusy(true);
  try {
    const base = `/api/harbor/datasets/${encodeURIComponent(datasetId)}`;
    let path = `${base}/tasks`;
    let method = "POST";
    let requestBody;
    if (body.action === "create") {
      requestBody = { directory: body.directory, package_name: body.package_name, steps: body.steps };
    } else {
      path = body.action === "rename_archived"
        ? `${base}/archived-tasks/${encodeURIComponent(body.entry_id)}`
        : `${base}/tasks/${encodeURIComponent(body.task)}`;
      method = "PATCH";
      requestBody = { new_directory: body.new_directory };
    }
    const operation = await serveApi(path, {
      method,
      body: requestBody,
      ifMatch: body.expected_revision,
    });
    if (body.action === "rename" || body.action === "rename_archived") {
      const datasets = listValue(workbenchState.inventory?.datasets).map(dataset => {
        if (dataset.id !== datasetId) return dataset;
        if (body.action === "rename") {
          return {
            ...dataset,
            tasks: listValue(dataset.tasks).map(task => task.directory === body.task
              ? { ...task, directory: body.new_directory }
              : task),
          };
        }
        return {
          ...dataset,
          trash: listValue(dataset.trash).map(entry => entry.entry_id === body.entry_id
            ? { ...entry, directory: body.new_directory }
            : entry),
        };
      });
      workbenchState.inventory = { ...workbenchState.inventory, datasets };
    }
    if (datasetId === workbenchState.datasetId && taskName === workbenchState.taskName) {
      const browser = workbenchTaskBrowser();
      const draftNow = browser?.currentFile();
      if (draftNow?.path === draftBefore?.path && draftNow?.content === draftBefore?.content) clearEditor();
      else if (body.action === "rename" && body.new_directory === taskName) {
        browser?.rebindTask({ dataset_id: datasetId, task: taskName });
        if (workbenchState.taskDetail?.task) workbenchState.taskDetail = {
          ...workbenchState.taskDetail, task: { ...workbenchState.taskDetail.task, directory: taskName },
        };
      }
    }
    trackOperation(operation, { ...options, feedback, datasetId, taskName });
    return operation;
  } catch (error) {
    if (error.status === 412) {
      try { await refreshWorkbenchRevisions(datasetId, taskName, null); }
      catch (refreshError) { error.message += ` (${refreshError.message})`; }
    }
    if (options.rethrow) { feedback.dispose(); throw error; }
    feedback.set(error.message || String(error), true);
    return null;
  } finally {
    setWorkbenchBusy(false);
  }
}

async function createTask() {
  if (!adminMode() || !confirmDiscard()) return;
  const dataset = selectedDataset();
  if (!dataset || datasetIsReadOnly(dataset)) return;
  return openActionForm({
    title: t("harbor_create_task", "New Task"),
    fields: [
      { name: "directory", label: t("harbor_task_directory_prompt", "Task directory") },
      { name: "package_name", label: t("harbor_task_package_prompt", "Task package name (org/name)"), defaultFrom: "directory", prefix: "local/" },
      { name: "steps", label: t("harbor_step_count_prompt", "Step count (0 for single-step)"), type: "number", value: "0", min: 0, max: 50, step: 1 },
    ],
    async submit(values) {
      const steps = Number(values.steps);
      if (!Number.isInteger(steps) || steps < 0 || steps > 50) throw new Error(t("harbor_steps_invalid", "Step count must be an integer from 0 to 50"));
      await mutateTasks({ action: "create", directory: values.directory.trim(), package_name: values.package_name.trim(), steps, expected_revision: dataset.revision }, dataset.id, {
        selectTask: values.directory.trim(), rethrow: true,
      });
    },
  });
}
async function renameOverviewTask(row, value) {
  if (datasetIsReadOnly(row?.dataset)) {
    throw new Error(t("harbor_dataset_read_only", "Dataset is read-only"));
  }
  if (workbenchState.busy) throw new Error(t("saving", "Saving..."));
  const newDirectory = String(value || "").trim();
  const oldKey = overviewRowKey(row);
  if (!newDirectory) throw new Error(t("harbor_task_directory_required", "Task directory is required"));
  if (newDirectory === rowTaskName(row)) return { rowKey: oldKey };
  if (!confirmDiscard()) throw new Error(t("harbor_discard_changes", "Discard unsaved file changes?"));
  const body = row.kind === "trash"
    ? { action: "rename_archived", entry_id: row.entry.entry_id, new_directory: newDirectory, expected_revision: row.entry.revision }
    : { action: "rename", task: row.task.directory, new_directory: newDirectory, expected_revision: row.task.revision };
  const renamesOpenTask = row.kind === "task"
    && workbenchState.datasetId === row.dataset.id
    && workbenchState.taskName === row.task.directory;
  if (renamesOpenTask) workbenchState.taskName = newDirectory;
  let payload;
  try {
    payload = await mutateTasks(body, row.dataset.id, { rethrow: true });
  } catch (error) {
    if (renamesOpenTask && workbenchState.taskName === newDirectory) {
      workbenchState.taskName = row.task.directory;
    }
    throw error;
  }
  if (!payload) {
    if (renamesOpenTask && workbenchState.taskName === newDirectory) {
      workbenchState.taskName = row.task.directory;
    }
    throw new Error(t("harbor_task_rename_failed", "Task rename failed"));
  }
  const newKey = row.kind === "trash"
    ? oldKey
    : `dataset:${row.dataset.id}|task:${newDirectory}`;
  if (workbenchState.taskSelection.delete(oldKey)) workbenchState.taskSelection.add(newKey);
  return { rowKey: newKey };
}

function selectedTaskRows() {
  const selected = workbenchState.taskSelection;
  return overviewRows().filter(row => selected.has(overviewRowKey(row))
    && row.kind !== "empty" && !datasetIsReadOnly(row.dataset));
}

function taskOperationItem(row) {
  return row.kind === "trash"
    ? { dataset_id: row.dataset.id, entry_id: row.entry.entry_id, directory: row.entry.directory || "", etag: row.entry.revision }
    : { dataset_id: row.dataset.id, task: row.task.directory, etag: row.task.revision };
}

async function mutateSelectedTaskState() {
  if (!adminMode() || !confirmDiscard()) return;
  const rows = selectedTaskRows();
  if (!rows.length) return;
  const feedback = taskFeedback("task");
  setWorkbenchBusy(true);
  try {
    const operation = await serveApi("/api/harbor/task-state-operations", {
      method: "POST",
      body: { archived: !workbenchState.showTrash, items: rows.map(taskOperationItem) },
    });
    trackOperation(operation, { feedback, selectedRows: rows });
    setWorkbenchBusy(false);
  } catch (error) {
    setWorkbenchBusy(false);
    feedback.set(error.message || String(error), true);
  }
}

async function deleteSelectedTasks() {
  if (!adminMode() || !confirmDiscard()) return;
  const rows = selectedTaskRows();
  if (!rows.length || !window.confirm(t("harbor_delete_selected_confirm", "Permanently delete selected Tasks? This cannot be undone."))) return;
  const feedback = taskFeedback("task");
  setWorkbenchBusy(true);
  try {
    const operation = await serveApi("/api/harbor/task-deletion-operations", {
      method: "POST",
      body: { items: rows.map(taskOperationItem) },
    });
    trackOperation(operation, { feedback, selectedRows: rows });
    setWorkbenchBusy(false);
  } catch (error) {
    setWorkbenchBusy(false);
    feedback.set(error.message || String(error), true);
  }
}

async function syncManifest() {
  const dataset = selectedDataset();
  if (!adminMode() || !dataset || datasetIsReadOnly(dataset)) return;
  const feedback = taskFeedback("task");
  setWorkbenchBusy(true);
  try {
    const summary = await serveApi(`/api/harbor/datasets/${encodeURIComponent(dataset.id)}/manifest`, {
      method: "PUT",
      body: {},
      ifMatch: dataset.revision,
    });
    const datasets = listValue(workbenchState.inventory?.datasets).map(item => item.id === summary.id ? summary : item);
    workbenchState.inventory = { ...workbenchState.inventory, datasets };
    renderHarborWorkbench();
    feedback.set(t("harbor_manifest_synced", "Manifest synced"));
  } catch (error) {
    feedback.set(error.message || String(error), true);
  } finally {
    setWorkbenchBusy(false);
  }
}

async function createFile(kind) {
  if (!canMutateSelectedTask()) return;
  const task = selectedTask();
  const taskRef = { datasetId: workbenchState.datasetId, taskName: workbenchState.taskName };
  if (!task) return;
  return openActionForm({
    title: kind === "directory" ? t("harbor_new_directory", "New directory") : t("harbor_new_file", "New file"),
    fields: [{ name: "path", label: t("harbor_new_path_prompt", "New path") }],
    submit: values => mutateFiles({ action: "create", kind, path: values.path.trim(), expected_revision: task.revision }, { rethrow: true, taskRef }),
  });
}
async function uploadFile(file) {
  if (!canMutateSelectedTask()) return;
  const task = selectedTask();
  const taskRef = { datasetId: workbenchState.datasetId, taskName: workbenchState.taskName };
  if (!task || !file) return;
  if (Number(file.size) > 16 * 1024 * 1024) {
    taskFeedback("file", workbenchState.taskName, "upload-validation").error(t("harbor_upload_too_large", "Uploads are limited to 16 MiB"));
    return;
  }
  return openActionForm({
    title: t("harbor_upload", "Upload"),
    fields: [{ name: "path", label: t("harbor_upload_path_prompt", "Upload path"), value: file.name }],
    async submit(values) {
      const buffer = new Uint8Array(await file.arrayBuffer());
      let binary = "";
      for (let offset = 0; offset < buffer.length; offset += 0x8000) binary += String.fromCharCode(...buffer.subarray(offset, offset + 0x8000));
      await mutateFiles({ action: "upload", path: values.path.trim(), content_base64: btoa(binary), expected_revision: task.revision }, { rethrow: true, taskRef });
    },
  });
}
async function fileActionMenu(item) {
  if (!canMutateSelectedTask()) return;
  const task = selectedTask();
  const taskRef = { datasetId: workbenchState.datasetId, taskName: workbenchState.taskName };
  if (!task) return;
  return openActionForm({
    title: item.path, submitLabel: t("rename", "Rename"),
    fields: [{ name: "new_path", label: t("harbor_new_path_prompt", "New path"), value: item.path }],
    submit: values => mutateFiles({ action: "rename", path: item.path, new_path: values.new_path.trim(), expected_revision: task.revision }, { rethrow: true, taskRef }),
    secondaryAction: {
      label: t("delete", "Delete"),
      async run() {
        if (!window.confirm(formatMessage("harbor_delete_file_confirm", "Permanently delete “{name}”?", { name: item.path }))) return false;
        await mutateFiles({ action: "delete", path: item.path, expected_revision: task.revision }, { rethrow: true, taskRef });
      },
    },
  });
}
async function refreshWorkbenchRevisions(datasetId, taskName, filePath) {
  const fresh = await serveApi("/api/harbor/datasets");
  for (const dataset of listValue(workbenchState.inventory?.datasets)) {
    const updated = listValue(fresh.datasets).find(item => item.id === dataset.id);
    if (!updated) continue;
    dataset.revision = updated.revision;
    for (const task of listValue(dataset.tasks)) {
      const current = listValue(updated.tasks).find(item => item.directory === task.directory);
      if (current) task.revision = current.revision;
    }
    for (const entry of listValue(dataset.trash)) {
      const current = listValue(updated.trash).find(item => item.entry_id === entry.entry_id);
      if (current) entry.revision = current.revision;
    }
  }
  if (filePath) {
    const path = `/api/harbor/datasets/${encodeURIComponent(datasetId)}/tasks/${encodeURIComponent(taskName)}/files/${encodeURIComponent(filePath)}`;
    const current = await serveApi(path);
    if (datasetId === workbenchState.datasetId && taskName === workbenchState.taskName) {
      workbenchTaskBrowser()?.acceptRevision(filePath, serveEtag(path));
    }
    return current;
  }
}

function trackOperation(operation, options = {}) {
  const operationId = operation?.id;
  if (operationId) {
    trackedWorkbenchOperations.add(operationId);
    syncWorkbenchBusyState();
    pollHarborOperation(operationId, { datasetId: workbenchState.datasetId, taskName: workbenchState.taskName, ...options });
  }
}

async function pollHarborOperation(operationId, options = {}) {
  if (!adminMode()) return;
  const feedback = options.feedback || taskFeedback();
  await watchOperation(operationId, {
    feedback, committed: !options.selectedRows,
    onBusy(busy) {
      if (busy) trackedWorkbenchOperations.add(operationId);
      else trackedWorkbenchOperations.delete(operationId);
      syncWorkbenchBusyState();
    },
    async onComplete(operation) {
      if (options.selectedRows) {
        const successfulIndexes = new Set(listValue(operation.successes).map(item => Number(item.index)));
        options.selectedRows.forEach((row, index) => {
          if (successfulIndexes.has(index)) workbenchState.taskSelection.delete(overviewRowKey(row));
        });
      }
      const stillSelected = () => options.datasetId === workbenchState.datasetId && options.taskName === workbenchState.taskName;
      const loaded = await refreshHarborInventory({ quiet: true, skipGuard: true, skipTaskReload: !stillSelected() || isHarborDirty() });
      if (!loaded) throw new Error(t("feedback_refresh_failed", "Saved, but workspace refresh failed"));
      const failures = listValue(operation.failures);
      const createdFirstTask = options.taskName === null && options.datasetId === workbenchState.datasetId && options.selectTask === workbenchState.taskName;
      if ((stillSelected() || createdFirstTask) && options.selectTask && !isHarborDirty() && operation.state !== "failed" && !failures.length) {
        await selectTask(options.selectTask);
        taskSidebar?.open();
      }
      if (stillSelected() && options.reopen && workbenchState.taskDetail && !isHarborDirty()) {
        await workbenchTaskBrowser()?.setTaskDetail(workbenchState.taskDetail, {
          taskRef: { dataset_id: options.datasetId, task: options.taskName },
          preferredPath: options.reopen, preserveCurrent: false, focus: false,
        });
      }
    },
  });
}
function taskFeedback(kind = "task", resource = workbenchState.taskName, action = "mutate") {
  const dataset = workbenchState.datasetId;
  const selector = kind === "file" ? ".harbor-editor-head" : ".harbor-overview-head";
  return beginFeedback(() => kind !== "file" || (dataset === workbenchState.datasetId && resource === workbenchState.taskName)
    ? (kind === "file" ? taskDetailRoot() : workbenchRoot())?.querySelector(selector) : null, {
    key: JSON.stringify(["datasets", dataset, resource, kind, action]),
    page: "datasets", label: `${dataset || ""} / ${resource || ""}`,
    async onView() {
      const row = overviewRows().find(row => row.dataset.id === dataset && row.task?.directory === resource);
      if (row) await selectOverviewRow(row);
    },
  });
}
function bindHarborWorkbench() {
  const surface = workbenchRoot();
  if (!surface || surface.dataset.bound === "true") return;
  surface.dataset.bound = "true";
  surface.querySelector("[data-harbor-create-task]")?.addEventListener("click", createTask);
  surface.querySelector("[data-harbor-add-column]")?.addEventListener("click", event => openCreateCustomColumn(event.currentTarget));
  surface.querySelector("[data-harbor-sync-manifest]")?.addEventListener("click", syncManifest);
  surface.querySelector("[data-harbor-state-selected]")?.addEventListener("click", mutateSelectedTaskState);
  surface.querySelector("[data-harbor-delete-selected]")?.addEventListener("click", deleteSelectedTasks);
  surface.querySelector("[data-harbor-show-trash]")?.addEventListener("change", event => {
    if (!confirmDiscard()) { event.target.checked = workbenchState.showTrash; return; }
    workbenchState.showTrash = event.target.checked;
    workbenchState.taskSelection.clear();
    setOverviewSelection(null);
    renderHarborWorkbench();
  });
  surface.querySelector("[data-harbor-search]")?.addEventListener("input", event => {
    const previous = workbenchState.search;
    workbenchState.search = String(event.target.value || "");
    refreshOverviewAfterControls(() => {
      workbenchState.search = previous;
      event.target.value = previous;
    });
  });
  taskDetailRoot().querySelector("[data-harbor-new-file]")?.addEventListener("click", () => createFile("file"));
  taskDetailRoot().querySelector("[data-harbor-new-directory]")?.addEventListener("click", () => createFile("directory"));
  const upload = taskDetailRoot().querySelector("[data-harbor-upload-input]");
  taskDetailRoot().querySelector("[data-harbor-upload]")?.addEventListener("click", () => upload?.click());
  upload?.addEventListener("change", () => {
    const file = upload.files?.[0];
    upload.value = "";
    if (file) uploadFile(file);
  });
  taskDetailRoot().querySelector("[data-harbor-save]")?.addEventListener("click", saveFile);
  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s" && adminMode() && !taskSidebar?.root.hidden) {
      event.preventDefault();
      saveFile();
    }
  });
  window.addEventListener("beforeunload", event => {
    if (!isHarborDirty()) return;
    event.preventDefault();
    event.returnValue = "";
  });
}

function textNode(tag, value) {
  const node = document.createElement(tag);
  node.textContent = String(value ?? "");
  return node;
}

export {
  activeCustomColumns,
  resumeTaskSidebar,
  resumeTaskInventory,
  pauseTaskInventory,
  bindHarborWorkbench,
  confirmDiscard,
  createFile,
  createTask,
  deleteCustomColumn,
  fileActionMenu,
  harborColumns,
  initializeHarborWorkbench,
  isHarborDirty,
  mutateSelectedTaskState,
  deleteSelectedTasks,
  openCreateCustomColumn,
  openHarborWorkbench,
  overviewRows,
  refreshHarborInventory,
  renderHarborWorkbench,
  saveFile,
  setWorkbenchBusy,
  selectedTaskRows,
  selectOverviewRow,
  uploadFile,
  visibleOverviewRows,
  workbenchState,
};
