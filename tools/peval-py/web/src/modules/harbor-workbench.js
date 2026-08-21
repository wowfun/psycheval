import { adminMode, esc, listValue, t } from "./runtime.js";
import { applyDataTableControls, bindDataTableControls, renderDataTable, tableControls } from "./data-tables.js";
import { serveApi } from "./serve-effects.js";

const HARBOR_TABLE_ID = "harbor-datasets";

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
    { key: "dataset", label: t("harbor_dataset", "Dataset"), valueType: "identity", sortable: true, filterable: true, value: row => row.dataset?.id || "-" },
    { key: "task", label: t("task", "Task"), valueType: "identity", sortable: true, filterable: true, value: row => rowTaskName(row) || "-" },
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
    emptyText: workbenchState.showTrash ? t("harbor_trash_empty", "Trash is empty") : t("harbor_dataset_empty", "No Datasets registered"),
    filterOptionsRows: overviewRows(),
  });
  bindDataTableControls(container, {
    tableId: HARBOR_TABLE_ID,
    columns,
    rows,
    rowKey: overviewRowKey,
    onChange: () => refreshOverviewAfterControls({ restoreTable: true }),
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
  const rows = visibleOverviewRows();
  const selection = reconcileOverviewSelection(rows);
  renderHarborOverview(surface, rows);
  renderContextControls(surface);
  renderSelectedTaskHeading(surface);
  renderFileTree(surface);
  renderDiagnostics(surface);
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
  const task = selectedTask();
  const trash = selectedTrashEntry();
  setDisabled(surface, "[data-harbor-edit-dataset]", !dataset);
  setDisabled(surface, "[data-harbor-remove-dataset]", !dataset);
  setDisabled(surface, "[data-harbor-create-task]", !dataset || workbenchState.showTrash);
  setDisabled(surface, "[data-harbor-sync-manifest]", !dataset || workbenchState.showTrash);
  setDisabled(surface, "[data-harbor-rename-task]", !task || workbenchState.showTrash);
  setDisabled(surface, "[data-harbor-trash-task]", !task || workbenchState.showTrash);
  setDisabled(surface, "[data-harbor-restore-task]", !trash || !workbenchState.showTrash);
  setDisabled(surface, "[data-harbor-purge-task]", !trash || !workbenchState.showTrash);
  setDisabled(surface, "[data-harbor-show-trash]", !listValue(workbenchState.inventory?.datasets).length);
  surface.querySelector("[data-harbor-show-trash]")?.classList.toggle("active", workbenchState.showTrash);
  surface.querySelectorAll("[data-harbor-live-action]").forEach(node => { node.hidden = workbenchState.showTrash; });
  surface.querySelectorAll("[data-harbor-trash-action]").forEach(node => { node.hidden = !workbenchState.showTrash; });
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
        ? `${workbenchState.datasetId} · ${trash.package_name || "-"} · ${t("harbor_trash", "Trash")}`
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
  if (save) save.disabled = !adminMode() || !workbenchState.dirty || !workbenchState.filePath;
  const path = surface?.querySelector?.("[data-harbor-editor-path]");
  if (path && workbenchState.filePath) path.textContent = `${workbenchState.filePath}${workbenchState.dirty ? " •" : ""}`;
}

async function saveFile() {
  if (!adminMode() || !workbenchState.dirty || !workbenchState.filePath) return;
  const editor = workbenchRoot()?.querySelector?.("[data-harbor-editor]");
  const task = selectedTask();
  if (!editor || !task) return;
  await mutateFiles({ action: "save", path: workbenchState.filePath, content: editor.value, expected_revision: task.revision }, { reopen: workbenchState.filePath });
}

async function mutateFiles(body, options = {}) {
  if (!adminMode()) return null;
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
  }
}

async function mutateTasks(body) {
  if (!adminMode()) return null;
  try {
    const payload = await serveApi("/api/harbor/tasks", {
      method: "POST",
      body: { ...body, dataset_id: workbenchState.datasetId },
    });
    trackOperation(payload.operation);
    clearEditor();
    await refreshHarborInventory({ quiet: true, skipGuard: true });
    return payload;
  } catch (error) {
    setWorkbenchStatus(error.message || String(error), true);
    return null;
  }
}

async function mutateDatasets(body, options = {}) {
  if (!adminMode()) return null;
  try {
    const payload = await serveApi("/api/harbor/datasets", {
      method: "POST",
      body: { ...body, expected_revision: workbenchState.inventory?.revision },
    });
    if (payload.operation) trackOperation(payload.operation);
    workbenchState.inventory = payload.result || workbenchState.inventory;
    if (options.selectId) workbenchState.datasetId = options.selectId;
    await refreshHarborInventory({ quiet: true, skipGuard: true });
    return payload;
  } catch (error) {
    setWorkbenchStatus(error.message || String(error), true);
    return null;
  }
}

async function createDataset(register = false) {
  if (!adminMode()) return;
  const datasetId = window.prompt(t("harbor_dataset_id_prompt", "Dataset ID"));
  if (!datasetId) return;
  const path = window.prompt(register
    ? t("harbor_existing_dataset_path_prompt", "Existing Dataset path")
    : t("harbor_new_dataset_path_prompt", "New Dataset path"));
  if (!path) return;
  const body = { action: register ? "register" : "create", dataset_id: datasetId.trim(), path: path.trim() };
  if (!register) {
    const packageName = window.prompt(t("harbor_dataset_package_prompt", "Dataset package name (org/name)"), `local/${datasetId.trim()}`);
    if (!packageName) return;
    body.package_name = packageName.trim();
  }
  await mutateDatasets(body, { selectId: datasetId.trim() });
}

async function editDataset(dataset = selectedDataset()) {
  if (!adminMode() || !dataset) return;
  const newId = window.prompt(t("harbor_dataset_id_prompt", "Dataset ID"), dataset.id);
  if (!newId) return;
  const path = window.prompt(t("harbor_dataset_path_prompt", "Dataset path"), dataset.path);
  if (!path) return;
  await mutateDatasets({ action: "update", dataset_id: dataset.id, new_id: newId.trim(), path: path.trim() }, { selectId: newId.trim() });
}

async function removeDataset(dataset = selectedDataset()) {
  if (!adminMode() || !dataset || !window.confirm(harborMessage(
    "harbor_unregister_confirm",
    "Unregister Dataset “{name}”? Files will not be deleted.",
    { name: dataset.id },
  ))) return;
  await mutateDatasets({ action: "remove", dataset_id: dataset.id });
}

async function createTask() {
  if (!adminMode()) return;
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

async function renameTask(task = selectedTask()) {
  if (!adminMode() || !task) return;
  const newDirectory = window.prompt(t("harbor_task_directory_prompt", "Task directory"), task.directory);
  if (!newDirectory || newDirectory.trim() === task.directory) return;
  const result = await mutateTasks({ action: "rename", task: task.directory, new_directory: newDirectory.trim(), expected_revision: task.revision });
  if (result) await selectTask(newDirectory.trim());
}

async function trashTask(task = selectedTask()) {
  if (!adminMode() || !task || !window.confirm(harborMessage(
    "harbor_trash_confirm",
    "Move Task “{name}” to this Dataset's trash?",
    { name: task.directory },
  ))) return;
  await mutateTasks({ action: "trash", task: task.directory, expected_revision: task.revision });
}

async function restoreTrash(entry = selectedTrashEntry()) {
  if (!adminMode() || !entry) return;
  const directory = window.prompt(t("harbor_restore_directory_prompt", "Restore directory"), entry.directory || "");
  if (directory === null) return;
  await mutateTasks({ action: "restore", entry_id: entry.entry_id, directory: directory.trim(), expected_revision: entry.revision });
}

async function purgeTrash(entry = selectedTrashEntry()) {
  if (!adminMode() || !entry || !window.confirm(harborMessage(
    "harbor_purge_confirm",
    "Permanently delete “{name}”? This cannot be undone.",
    { name: entry.directory || entry.entry_id },
  ))) return;
  await mutateTasks({ action: "purge", entry_id: entry.entry_id, expected_revision: entry.revision });
}

async function syncManifest() {
  const dataset = selectedDataset();
  if (!adminMode() || !dataset) return;
  try {
    const summary = await serveApi("/api/harbor/datasets", {
      method: "POST",
      body: { action: "sync_manifest", dataset_id: dataset.id, expected_revision: dataset.revision },
    });
    const datasets = listValue(workbenchState.inventory?.datasets).map(item => item.id === summary.id ? summary : item);
    workbenchState.inventory = { ...workbenchState.inventory, datasets };
    renderHarborWorkbench();
    setWorkbenchStatus(t("harbor_manifest_synced", "Manifest synced"));
  } catch (error) {
    setWorkbenchStatus(error.message || String(error), true);
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

function trackOperation(operation) {
  const operationId = operation?.operation_id;
  if (operationId) pollHarborOperation(operationId);
}

async function pollHarborOperation(operationId) {
  if (!adminMode()) return;
  try {
    const operation = await serveApi(`/api/operations/${encodeURIComponent(operationId)}`);
    const node = workbenchRoot()?.querySelector?.("[data-harbor-operation-status]");
    if (node) node.textContent = `${operation.operation_type}: ${operation.completed}/${operation.total}`;
    if (operation.state === "queued" || operation.state === "running") {
      setTimeout(() => pollHarborOperation(operationId), 250);
      return;
    }
    if (operation.state === "failed" || listValue(operation.failures).length) {
      setWorkbenchStatus(operation.failures?.[0]?.error || t("harbor_reconcile_failed", "Catalog reconcile failed"), true);
    } else {
      await refreshHarborInventory({ quiet: true, skipGuard: true });
    }
  } catch (error) {
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
  surface.querySelector("[data-harbor-add-dataset]")?.addEventListener("click", () => createDataset(false));
  surface.querySelector("[data-harbor-register-dataset]")?.addEventListener("click", () => createDataset(true));
  surface.querySelector("[data-harbor-edit-dataset]")?.addEventListener("click", () => editDataset());
  surface.querySelector("[data-harbor-remove-dataset]")?.addEventListener("click", () => removeDataset());
  surface.querySelector("[data-harbor-create-task]")?.addEventListener("click", createTask);
  surface.querySelector("[data-harbor-sync-manifest]")?.addEventListener("click", syncManifest);
  surface.querySelector("[data-harbor-rename-task]")?.addEventListener("click", () => renameTask());
  surface.querySelector("[data-harbor-trash-task]")?.addEventListener("click", () => trashTask());
  surface.querySelector("[data-harbor-restore-task]")?.addEventListener("click", () => restoreTrash());
  surface.querySelector("[data-harbor-purge-task]")?.addEventListener("click", () => purgeTrash());
  surface.querySelector("[data-harbor-show-trash]")?.addEventListener("click", () => {
    if (!confirmDiscard()) return;
    workbenchState.showTrash = !workbenchState.showTrash;
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
  openHarborWorkbench,
  overviewRows,
  purgeTrash,
  refreshHarborInventory,
  renameTask,
  renderHarborWorkbench,
  restoreTrash,
  saveFile,
  selectOverviewRow,
  trashTask,
  uploadFile,
  visibleOverviewRows,
  workbenchState,
};
