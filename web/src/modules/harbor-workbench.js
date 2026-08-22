import { adminMode, esc, listValue, t } from "./runtime.js";
import { applyDataTableControls, bindDataTableControls, renderDataTable, selectionColumn, tableControls } from "./data-tables.js";
import { serveApi } from "./serve-effects.js";

const HARBOR_TABLE_ID = "harbor-datasets";
const trackedWorkbenchOperations = new Set();
let workbenchMutationBusy = false;

const workbenchState = {
  inventory: null,
  datasetId: null,
  taskName: null,
  trashEntryId: null,
  taskDetail: null,
  filePath: null,
  fileRevision: null,
  savedText: "",
  dirty: false,
  showTrash: false,
  taskSelection: new Set(),
  busy: false,
  search: "",
  tableSnapshot: null,
  taskRequestId: 0,
  fileRequestId: 0,
};

function workbenchRoot() {
  return document.querySelector("[data-harbor-workbench]");
}

function selectedDataset() {
  return listValue(workbenchState.inventory?.datasets)
    .find(dataset => dataset?.id === workbenchState.datasetId) || null;
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
  return Boolean(workbenchState.dirty);
}

function confirmDiscard() {
  return !isHarborDirty() || window.confirm(t("harbor_discard_changes", "Discard unsaved file changes?"));
}

function harborMessage(key, fallback, values = {}) {
  let message = String(t(key, fallback));
  Object.entries(values).forEach(([name, value]) => {
    message = message.replaceAll(`{${name}}`, String(value));
  });
  return message;
}

function overviewRowKey(row) {
  if (row.kind === "trash") return `dataset:${row.dataset.id}|trash:${row.entry.entry_id}`;
  return `dataset:${row.dataset.id}|task:${row.task?.directory || ""}`;
}

function overviewRows() {
  return listValue(workbenchState.inventory?.datasets).flatMap(dataset => {
    if (workbenchState.showTrash) {
      return listValue(dataset?.trash).map(entry => ({ kind: "trash", dataset, entry, task: null }));
    }
    const tasks = listValue(dataset?.tasks);
    if (!tasks.length) return [{ kind: "empty", dataset, task: null, entry: null }];
    return tasks.map(task => ({ kind: "task", dataset, task, entry: null }));
  });
}

function rowTaskName(row) {
  return row.kind === "trash" ? row.entry?.directory || row.entry?.entry_id || "" : row.task?.directory || "";
}

function rowPackage(row) {
  return row.kind === "trash" ? row.entry?.package_name || "-" : row.task?.package_name || "-";
}

function rowStatus(row) {
  if (row.kind === "empty") return t("harbor_empty_status", "empty");
  const status = row.kind === "trash" ? "trash" : row.task?.status || "draft";
  return t(`harbor_status_${status}`, status);
}

function rowStatusKey(row) {
  return row.kind === "empty" ? "empty" : row.kind === "trash" ? "trash" : row.task?.status || "draft";
}

function rowDiagnostics(row) {
  return listValue(row.task?.diagnostics).filter(Boolean).join(" · ");
}

function harborColumns() {
  return [
    ...(adminMode() ? [selectionColumn({
      key: "__task_select",
      selectionKey: overviewRowKey,
      selectionSet: () => workbenchState.taskSelection,
      selectable: row => row.kind !== "empty",
      rowAriaLabel: (_key, row) => `${t("select_row", "Select row")}: ${rowTaskName(row)}`,
    })] : []),
    { key: "dataset", label: t("harbor_dataset", "Dataset"), valueType: "identity", sortable: true, filterable: true, value: row => row.dataset?.id || "-" },
    {
      key: "task",
      label: t("task", "Task"),
      valueType: "identity",
      sortable: true,
      filterable: true,
      value: row => rowTaskName(row) || "-",
      edit: row => adminMode() && row.kind !== "empty" ? {
        value: rowTaskName(row),
        commit: (_current, value) => renameOverviewTask(row, value),
      } : null,
    },
    { key: "package", label: t("harbor_package", "Package"), valueType: "identity", sortable: true, filterable: true, value: row => rowPackage(row) },
    {
      key: "status",
      label: t("status", "Status"),
      valueType: "status",
      sortable: true,
      filterable: true,
      value: rowStatus,
      html: row => `<span class="harbor-status-rail ${esc(rowStatusKey(row))}">${esc(rowStatus(row))}</span>`,
    },
    { key: "diagnostics", label: t("harbor_diagnostics", "Diagnostics"), valueType: "text", sortable: true, value: row => rowDiagnostics(row) || "-", fullText: rowDiagnostics },
  ];
}

function rowSearchText(row) {
  return [row.dataset?.id, rowTaskName(row), rowPackage(row), rowStatus(row), rowDiagnostics(row)]
    .filter(Boolean).join(" ").toLowerCase();
}

function visibleOverviewRows() {
  const columns = harborColumns();
  const query = String(workbenchState.search || "").trim().toLowerCase();
  const searched = query ? overviewRows().filter(row => rowSearchText(row).includes(query)) : overviewRows();
  return applyDataTableControls(HARBOR_TABLE_ID, searched, columns, searched);
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
  workbenchState.trashEntryId = row?.kind === "trash" ? row.entry?.entry_id || null : null;
  workbenchState.taskDetail = null;
  workbenchState.taskRequestId += 1;
  clearEditor();
}

function reconcileOverviewSelection(rows) {
  const currentKey = selectedOverviewKey();
  const current = rows.find(row => overviewRowKey(row) === currentKey) || null;
  if (current) return { row: current, changed: false };
  const row = rows[0] || null;
  setOverviewSelection(row);
  return { row, changed: true };
}

function renderHarborOverview(surface, rows) {
  const container = surface.querySelector("[data-harbor-overview]");
  if (!container) return;
  const columns = harborColumns();
  const selectedKey = selectedOverviewKey();
  container.innerHTML = renderDataTable({
    tableId: HARBOR_TABLE_ID,
    columns,
    rows,
    rowKey: overviewRowKey,
    tableClass: "harbor-overview-table",
    shellClass: "harbor-overview-table-shell",
    rowClass: row => `harbor-overview-row status-${rowStatusKey(row)} ${overviewRowKey(row) === selectedKey ? "selected-row" : ""}`,
    rowAttrs: row => `data-harbor-overview-row tabindex="0" data-harbor-row-key="${esc(overviewRowKey(row))}"`,
    emptyText: workbenchState.showTrash ? t("harbor_trash_empty", "No archived Tasks") : t("harbor_dataset_empty", "No Datasets registered"),
    filterOptionsRows: overviewRows(),
  });
  bindDataTableControls(container, {
    tableId: HARBOR_TABLE_ID,
    columns,
    rows,
    rowKey: overviewRowKey,
    onChange: () => refreshOverviewAfterControls({ restoreTable: true }),
    onSelectionChange: renderHarborWorkbench,
  });
  const byKey = new Map(rows.map(row => [overviewRowKey(row), row]));
  container.querySelectorAll("[data-harbor-overview-row]").forEach(node => {
    const select = () => selectOverviewRow(byKey.get(node.dataset.harborRowKey));
    node.addEventListener("click", event => {
      if (event.target?.closest?.("button,input,select,textarea,label,details")) return;
      select();
    });
    node.addEventListener("keydown", event => {
      if (!["Enter", " "].includes(event.key)) return;
      event.preventDefault();
      select();
    });
  });
  const count = surface.querySelector("[data-harbor-overview-count]");
  if (count) count.textContent = `${rows.length} / ${overviewRows().length}`;
}

function renderHarborWorkbench() {
  const surface = workbenchRoot();
  if (!surface) return { row: null, changed: false };
  const availableKeys = new Set(overviewRows().filter(row => row.kind !== "empty").map(overviewRowKey));
  Array.from(workbenchState.taskSelection).forEach(key => {
    if (!availableKeys.has(key)) workbenchState.taskSelection.delete(key);
  });
  const rows = visibleOverviewRows();
  const selection = reconcileOverviewSelection(rows);
  renderHarborOverview(surface, rows);
  renderContextControls(surface);
  renderSelectedTaskHeading(surface);
  renderFileTree(surface);
  renderDiagnostics(surface);
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
  setDisabled(surface, "[data-harbor-create-task]", workbenchState.busy || !dataset || workbenchState.showTrash);
  setDisabled(surface, "[data-harbor-sync-manifest]", workbenchState.busy || !dataset || workbenchState.showTrash);
  setDisabled(surface, "[data-harbor-state-selected]", workbenchState.busy || workbenchState.taskSelection.size < 1);
  setDisabled(surface, "[data-harbor-delete-selected]", workbenchState.busy || workbenchState.taskSelection.size < 1);
  setDisabled(surface, "[data-harbor-show-trash]", workbenchState.busy || !listValue(workbenchState.inventory?.datasets).length);
  surface.querySelector("[data-harbor-show-trash]")?.classList.toggle("active", workbenchState.showTrash);
  const stateButton = surface.querySelector("[data-harbor-state-selected]");
  if (stateButton) stateButton.textContent = workbenchState.showTrash
    ? t("restore_selected", "Restore selected")
    : t("archive_selected", "Archive selected");
  const archivedToggle = surface.querySelector("[data-harbor-show-trash]");
  if (archivedToggle) archivedToggle.setAttribute("aria-pressed", workbenchState.showTrash ? "true" : "false");
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
  syncEditorControls();
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
  const task = selectedTask();
  const trash = selectedTrashEntry();
  if (title) title.textContent = task?.directory || trash?.directory || t("harbor_task_detail_empty", "Select a Task");
  if (meta) {
    meta.textContent = task
      ? `${workbenchState.datasetId} · ${task.package_name || "-"} · ${t(`harbor_status_${task.status || "draft"}`, task.status || "draft")}`
      : trash
        ? `${workbenchState.datasetId} · ${trash.package_name || "-"} · ${t("harbor_trash", "Archived")}`
        : "";
  }
}

function renderFileTree(surface = workbenchRoot()) {
  const container = surface?.querySelector?.("[data-harbor-file-tree]");
  const actions = surface?.querySelector?.("[data-harbor-file-actions]");
  if (!container) return;
  container.replaceChildren();
  const tree = listValue(workbenchState.taskDetail?.tree);
  if (actions) actions.hidden = !adminMode() || !workbenchState.taskDetail || workbenchState.showTrash;
  if (!tree.length) {
    container.append(emptyNode(t("harbor_file_empty", "Select a Task to browse its files")));
    return;
  }
  tree.forEach(item => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `harbor-file-row kind-${item.kind}`;
    button.classList.toggle("selected", item.path === workbenchState.filePath);
    button.style.setProperty("--depth", String(item.path.split("/").length - 1));
    button.append(
      textNode("span", item.kind === "directory" ? "▸" : "·"),
      textNode("span", item.path.split("/").at(-1)),
      textNode("small", item.kind === "file" ? formatBytes(item.size) : ""),
    );
    if (item.kind === "file") button.addEventListener("click", () => openFile(item));
    if (adminMode()) {
      button.addEventListener("contextmenu", event => {
        event.preventDefault();
        fileActionMenu(item);
      });
    }
    container.append(button);
  });
}

function renderDiagnostics(surface = workbenchRoot()) {
  const container = surface?.querySelector?.("[data-harbor-diagnostics]");
  if (!container) return;
  container.replaceChildren();
  listValue(selectedTask()?.diagnostics).forEach(diagnostic => container.append(textNode("p", diagnostic)));
}

async function selectOverviewRow(row) {
  if (!row) return;
  if (overviewRowKey(row) === selectedOverviewKey()) {
    if (row.kind === "task" && !workbenchState.taskDetail) await loadSelectedTask();
    return;
  }
  if (!confirmDiscard()) return;
  setOverviewSelection(row);
  renderHarborWorkbench();
  if (row.kind === "task") await loadSelectedTask();
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

async function loadSelectedTask() {
  const datasetId = workbenchState.datasetId;
  const taskName = workbenchState.taskName;
  if (!datasetId || !taskName || workbenchState.showTrash) return;
  const requestId = workbenchState.taskRequestId + 1;
  workbenchState.taskRequestId = requestId;
  workbenchState.taskDetail = null;
  clearEditor();
  renderFileTree();
  try {
    const detail = await serveApi(`/api/harbor/task?dataset_id=${encodeURIComponent(datasetId)}&task=${encodeURIComponent(taskName)}`);
    if (requestId !== workbenchState.taskRequestId || datasetId !== workbenchState.datasetId || taskName !== workbenchState.taskName) return;
    workbenchState.taskDetail = detail;
    renderHarborWorkbench();
  } catch (error) {
    setWorkbenchStatus(error.message || String(error), true);
  }
}

async function refreshOverviewAfterControls(options = {}) {
  const currentVisible = visibleOverviewRows().some(row => overviewRowKey(row) === selectedOverviewKey());
  if (!options.skipGuard && !currentVisible && !confirmDiscard()) {
    if (options.restoreTable) {
      restoreTableControls();
      renderHarborWorkbench();
    }
    return;
  }
  const selection = renderHarborWorkbench();
  if (selection.changed && selection.row?.kind === "task") await loadSelectedTask();
}

async function refreshHarborInventory(options = {}) {
  if (!options.skipGuard && !confirmDiscard()) return null;
  setWorkbenchStatus(t("serve_loading_sources", "Loading…"));
  try {
    const payload = await serveApi("/api/harbor/datasets");
    workbenchState.inventory = payload;
    const selection = renderHarborWorkbench();
    if (selection.row?.kind === "task") await loadSelectedTask();
    if (!options.quiet) setWorkbenchStatus("");
    return payload;
  } catch (error) {
    setWorkbenchStatus(error.message || String(error), true);
    return null;
  }
}

async function initializeHarborWorkbench() {
  bindHarborWorkbench();
  return refreshHarborInventory({ skipGuard: true });
}

async function openHarborWorkbench() {
  if (!workbenchRoot()) return false;
  await initializeHarborWorkbench();
  return true;
}

function closeHarborWorkbench() {
  return false;
}

async function openFile(item) {
  if (!confirmDiscard()) return;
  const requestId = workbenchState.fileRequestId + 1;
  workbenchState.fileRequestId = requestId;
  const datasetId = workbenchState.datasetId;
  const taskName = workbenchState.taskName;
  if (!item.editable) {
    renderFileMetadata(item);
    renderFileTree();
    return;
  }
  try {
    const payload = await serveApi(`/api/harbor/files?dataset_id=${encodeURIComponent(datasetId)}&task=${encodeURIComponent(taskName)}&path=${encodeURIComponent(item.path)}`);
    if (requestId !== workbenchState.fileRequestId
      || datasetId !== workbenchState.datasetId
      || taskName !== workbenchState.taskName) return;
    workbenchState.filePath = item.path;
    workbenchState.fileRevision = payload.revision || null;
    workbenchState.savedText = payload.content;
    workbenchState.dirty = false;
    const editor = workbenchRoot()?.querySelector?.("[data-harbor-editor]");
    if (editor) {
      editor.disabled = false;
      editor.readOnly = !adminMode();
      editor.value = payload.content;
      editor.focus();
    }
    const meta = workbenchRoot()?.querySelector?.("[data-harbor-editor-meta]");
    if (meta) meta.textContent = `${formatBytes(item.size)} · ${t("harbor_text", "text")}`;
    syncEditorControls();
    renderFileTree();
  } catch (error) {
    setWorkbenchStatus(error.message || String(error), true);
  }
}

function renderFileMetadata(item) {
  clearEditor();
  workbenchState.filePath = item.path;
  const surface = workbenchRoot();
  const path = surface?.querySelector?.("[data-harbor-editor-path]");
  const meta = surface?.querySelector?.("[data-harbor-editor-meta]");
  const download = surface?.querySelector?.("[data-harbor-download]");
  if (path) path.textContent = item.path;
  if (meta) meta.textContent = `${formatBytes(item.size)} · ${item.editable ? t("harbor_text", "text") : t("harbor_metadata_only", "metadata only")}`;
  if (download) download.hidden = !adminMode() || !item.downloadable;
}

function clearEditor() {
  workbenchState.fileRequestId += 1;
  workbenchState.filePath = null;
  workbenchState.fileRevision = null;
  workbenchState.savedText = "";
  workbenchState.dirty = false;
  const surface = workbenchRoot();
  const editor = surface?.querySelector?.("[data-harbor-editor]");
  if (editor) {
    editor.value = "";
    editor.disabled = true;
    editor.readOnly = !adminMode();
  }
  const path = surface?.querySelector?.("[data-harbor-editor-path]");
  if (path) path.textContent = t("harbor_editor_empty", "Select a text file");
  const meta = surface?.querySelector?.("[data-harbor-editor-meta]");
  if (meta) meta.textContent = "";
  const download = surface?.querySelector?.("[data-harbor-download]");
  if (download) download.hidden = true;
  syncEditorControls();
}

function syncEditorControls() {
  const surface = workbenchRoot();
  const save = surface?.querySelector?.("[data-harbor-save]");
  if (save) save.disabled = !adminMode() || workbenchState.busy || !workbenchState.dirty || !workbenchState.filePath;
  const path = surface?.querySelector?.("[data-harbor-editor-path]");
  if (path && workbenchState.filePath) path.textContent = `${workbenchState.filePath}${workbenchState.dirty ? " •" : ""}`;
}

async function saveFile() {
  if (!adminMode() || !workbenchState.dirty || !workbenchState.filePath) return;
  if (workbenchState.busy) {
    setWorkbenchStatus(t("harbor_operation_in_progress", "Another Task operation is still running"), true);
    return;
  }
  const editor = workbenchRoot()?.querySelector?.("[data-harbor-editor]");
  const task = selectedTask();
  if (!editor || !task) return;
  await mutateFiles({ action: "save", path: workbenchState.filePath, content: editor.value, expected_revision: task.revision }, { reopen: workbenchState.filePath });
}

async function mutateFiles(body, options = {}) {
  if (!adminMode() || workbenchState.busy) return null;
  setWorkbenchBusy(true);
  try {
    const payload = await serveApi("/api/harbor/files", {
      method: "POST",
      body: { ...body, dataset_id: workbenchState.datasetId, task: workbenchState.taskName },
    });
    workbenchState.taskDetail = payload.result;
    workbenchState.dirty = false;
    trackOperation(payload.operation);
    await refreshHarborInventory({ quiet: true, skipGuard: true });
    if (options.reopen) {
      const item = listValue(workbenchState.taskDetail?.tree).find(value => value.path === options.reopen);
      if (item) await openFile(item);
    }
    return payload;
  } catch (error) {
    setWorkbenchStatus(error.message || String(error), true);
    return null;
  } finally {
    setWorkbenchBusy(false);
  }
}

async function mutateTasks(body, datasetId = workbenchState.datasetId, options = {}) {
  if (!adminMode() || workbenchState.busy) return null;
  setWorkbenchBusy(true);
  try {
    const payload = await serveApi("/api/harbor/tasks", {
      method: "POST",
      body: { ...body, dataset_id: datasetId },
    });
    trackOperation(payload.operation);
    clearEditor();
    await refreshHarborInventory({ quiet: true, skipGuard: true });
    return payload;
  } catch (error) {
    if (options.rethrow) throw error;
    setWorkbenchStatus(error.message || String(error), true);
    return null;
  } finally {
    setWorkbenchBusy(false);
  }
}

async function createTask() {
  if (!adminMode() || !confirmDiscard()) return;
  const dataset = selectedDataset();
  if (!dataset) return;
  const directory = window.prompt(t("harbor_task_directory_prompt", "Task directory"));
  if (!directory) return;
  const packageName = window.prompt(t("harbor_task_package_prompt", "Task package name (org/name)"), `local/${directory.trim()}`);
  if (!packageName) return;
  const rawSteps = window.prompt(t("harbor_step_count_prompt", "Step count (0 for single-step)"), "0");
  if (rawSteps === null) return;
  const steps = Number(rawSteps);
  if (!Number.isInteger(steps) || steps < 0 || steps > 50) {
    setWorkbenchStatus(t("harbor_steps_invalid", "Step count must be an integer from 0 to 50"), true);
    return;
  }
  const result = await mutateTasks({ action: "create", directory: directory.trim(), package_name: packageName.trim(), steps, expected_revision: dataset.revision });
  if (result) await selectTask(directory.trim());
}

async function renameOverviewTask(row, value) {
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
  return overviewRows().filter(row => selected.has(overviewRowKey(row)) && row.kind !== "empty");
}

function taskOperationItem(row) {
  return row.kind === "trash"
    ? { dataset_id: row.dataset.id, entry_id: row.entry.entry_id, directory: row.entry.directory || "", expected_revision: row.entry.revision }
    : { dataset_id: row.dataset.id, task: row.task.directory, expected_revision: row.task.revision };
}

async function mutateSelectedTaskState() {
  if (!adminMode() || !confirmDiscard()) return;
  const rows = selectedTaskRows();
  if (!rows.length) return;
  setWorkbenchBusy(true);
  try {
    const operation = await serveApi("/api/harbor/tasks/state", {
      method: "POST",
      body: { archived: !workbenchState.showTrash, items: rows.map(taskOperationItem) },
    });
    trackOperation(operation, { selectedRows: rows });
    setWorkbenchBusy(false);
  } catch (error) {
    setWorkbenchBusy(false);
    setWorkbenchStatus(error.message || String(error), true);
  }
}

async function deleteSelectedTasks() {
  if (!adminMode() || !confirmDiscard()) return;
  const rows = selectedTaskRows();
  if (!rows.length || !window.confirm(t("harbor_delete_selected_confirm", "Permanently delete selected Tasks? This cannot be undone."))) return;
  setWorkbenchBusy(true);
  try {
    const operation = await serveApi("/api/harbor/tasks/delete", {
      method: "POST",
      body: { items: rows.map(taskOperationItem) },
    });
    trackOperation(operation, { selectedRows: rows });
    setWorkbenchBusy(false);
  } catch (error) {
    setWorkbenchBusy(false);
    setWorkbenchStatus(error.message || String(error), true);
  }
}

async function syncManifest() {
  const dataset = selectedDataset();
  if (!adminMode() || !dataset) return;
  setWorkbenchBusy(true);
  try {
    const summary = await serveApi("/api/harbor/tasks/manifest", {
      method: "POST",
      body: { dataset_id: dataset.id, expected_revision: dataset.revision },
    });
    const datasets = listValue(workbenchState.inventory?.datasets).map(item => item.id === summary.id ? summary : item);
    workbenchState.inventory = { ...workbenchState.inventory, datasets };
    renderHarborWorkbench();
    setWorkbenchStatus(t("harbor_manifest_synced", "Manifest synced"));
  } catch (error) {
    setWorkbenchStatus(error.message || String(error), true);
  } finally {
    setWorkbenchBusy(false);
  }
}

async function createFile(kind) {
  if (!adminMode()) return;
  const task = selectedTask();
  if (!task) return;
  const path = window.prompt(kind === "directory"
    ? t("harbor_new_directory_path_prompt", "New directory path")
    : t("harbor_new_file_path_prompt", "New file path"));
  if (!path) return;
  await mutateFiles({ action: "create", kind, path: path.trim(), expected_revision: task.revision });
}

async function uploadFile(file) {
  if (!adminMode()) return;
  const task = selectedTask();
  if (!task || !file) return;
  if (Number(file.size) > 16 * 1024 * 1024) {
    setWorkbenchStatus(t("harbor_upload_too_large", "Uploads are limited to 16 MiB"), true);
    return;
  }
  const path = window.prompt(t("harbor_upload_path_prompt", "Upload path"), file.name);
  if (!path) return;
  const buffer = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let offset = 0; offset < buffer.length; offset += 0x8000) binary += String.fromCharCode(...buffer.subarray(offset, offset + 0x8000));
  await mutateFiles({ action: "upload", path: path.trim(), content_base64: btoa(binary), expected_revision: task.revision });
}

async function fileActionMenu(item) {
  if (!adminMode()) return;
  const task = selectedTask();
  if (!task) return;
  const action = window.prompt(t("harbor_file_action_prompt", "File action: rename or delete"), "rename");
  if (action === "rename") {
    const newPath = window.prompt(t("harbor_new_path_prompt", "New path"), item.path);
    if (!newPath || newPath === item.path) return;
    await mutateFiles({ action: "rename", path: item.path, new_path: newPath.trim(), expected_revision: task.revision });
  } else if (action === "delete" && window.confirm(harborMessage(
    "harbor_delete_file_confirm",
    "Permanently delete “{name}”?",
    { name: item.path },
  ))) {
    await mutateFiles({ action: "delete", path: item.path, expected_revision: task.revision });
  }
}

function downloadFile() {
  if (!adminMode() || !workbenchState.filePath || !workbenchState.taskName || !workbenchState.datasetId) return;
  window.location.assign(`/api/harbor/files?dataset_id=${encodeURIComponent(workbenchState.datasetId)}&task=${encodeURIComponent(workbenchState.taskName)}&path=${encodeURIComponent(workbenchState.filePath)}&download=1`);
}

function trackOperation(operation, options = {}) {
  const operationId = operation?.operation_id;
  if (operationId) {
    trackedWorkbenchOperations.add(operationId);
    syncWorkbenchBusyState();
    pollHarborOperation(operationId, options);
  }
}

async function pollHarborOperation(operationId, options = {}) {
  if (!adminMode()) return;
  try {
    const operation = await serveApi(`/api/operations/${encodeURIComponent(operationId)}`);
    const node = workbenchRoot()?.querySelector?.("[data-harbor-operation-status]");
    if (node) node.textContent = `${operation.operation_type}: ${operation.completed}/${operation.total}`;
    if (operation.state === "queued" || operation.state === "running") {
      setTimeout(() => pollHarborOperation(operationId, options), 250);
      return;
    }
    trackedWorkbenchOperations.delete(operationId);
    syncWorkbenchBusyState();
    if (options.selectedRows) {
      const successfulIndexes = new Set(listValue(operation.successes).map(item => Number(item.index)));
      options.selectedRows.forEach((row, index) => {
        if (successfulIndexes.has(index)) workbenchState.taskSelection.delete(overviewRowKey(row));
      });
    }
    await refreshHarborInventory({ quiet: true, skipGuard: true });
    const failures = listValue(operation.failures);
    if (operation.state === "failed" || failures.length) {
      setWorkbenchStatus(failures[0]?.error || t("harbor_reconcile_failed", "Catalog reconcile failed"), true);
    } else setWorkbenchStatus("");
  } catch (error) {
    trackedWorkbenchOperations.delete(operationId);
    syncWorkbenchBusyState();
    setWorkbenchStatus(error.message || String(error), true);
  }
}

function setWorkbenchStatus(message, error = false) {
  const node = workbenchRoot()?.querySelector?.("[data-harbor-workbench-status]");
  if (!node) return;
  node.textContent = message || "";
  node.hidden = !message;
  node.classList.toggle("danger", Boolean(error));
}

function bindHarborWorkbench() {
  const surface = workbenchRoot();
  if (!surface || surface.dataset.bound === "true") return;
  surface.dataset.bound = "true";
  surface.querySelector("[data-harbor-reload]")?.addEventListener("click", () => refreshHarborInventory());
  surface.querySelector("[data-harbor-create-task]")?.addEventListener("click", createTask);
  surface.querySelector("[data-harbor-sync-manifest]")?.addEventListener("click", syncManifest);
  surface.querySelector("[data-harbor-state-selected]")?.addEventListener("click", mutateSelectedTaskState);
  surface.querySelector("[data-harbor-delete-selected]")?.addEventListener("click", deleteSelectedTasks);
  surface.querySelector("[data-harbor-show-trash]")?.addEventListener("click", () => {
    if (!confirmDiscard()) return;
    workbenchState.showTrash = !workbenchState.showTrash;
    workbenchState.taskSelection.clear();
    setOverviewSelection(null);
    renderHarborWorkbench();
  });
  surface.querySelector("[data-harbor-search]")?.addEventListener("input", event => {
    const previous = workbenchState.search;
    workbenchState.search = String(event.target.value || "");
    const currentVisible = visibleOverviewRows().some(row => overviewRowKey(row) === selectedOverviewKey());
    if (!currentVisible && !confirmDiscard()) {
      workbenchState.search = previous;
      event.target.value = previous;
      return;
    }
    refreshOverviewAfterControls({ skipGuard: true });
  });
  surface.querySelector("[data-harbor-new-file]")?.addEventListener("click", () => createFile("file"));
  surface.querySelector("[data-harbor-new-directory]")?.addEventListener("click", () => createFile("directory"));
  const upload = surface.querySelector("[data-harbor-upload-input]");
  surface.querySelector("[data-harbor-upload]")?.addEventListener("click", () => upload?.click());
  upload?.addEventListener("change", () => {
    const file = upload.files?.[0];
    upload.value = "";
    if (file) uploadFile(file);
  });
  const editor = surface.querySelector("[data-harbor-editor]");
  editor?.addEventListener("input", () => {
    if (!adminMode()) return;
    workbenchState.dirty = editor.value !== workbenchState.savedText;
    syncEditorControls();
  });
  surface.querySelector("[data-harbor-save]")?.addEventListener("click", saveFile);
  surface.querySelector("[data-harbor-download]")?.addEventListener("click", downloadFile);
  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s" && adminMode()) {
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

function emptyNode(value) {
  const node = textNode("p", value);
  node.className = "copy harbor-empty";
  return node;
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}

export {
  bindHarborWorkbench,
  closeHarborWorkbench,
  confirmDiscard,
  createFile,
  createTask,
  fileActionMenu,
  harborColumns,
  initializeHarborWorkbench,
  isHarborDirty,
  mutateSelectedTaskState,
  deleteSelectedTasks,
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
