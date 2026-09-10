import { beginFeedback, pageFeedback, savedContentPreview } from "./action-feedback.js";
import { openActionForm } from "./action-form.js";
import { watchOperation } from "./operation-feedback.js";
import { adminMode, esc, listValue, t } from "./shared.js";
import { applyDataTableControls, bindDataTableControls, renderDataTable, selectionColumn, tableControls } from "./data-tables.js";
import { serveApi, serveEtag } from "./http.js";
import { createTaskBrowser } from "./harbor-task-browser.js";

const HARBOR_TABLE_ID = "harbor-datasets";
const trackedWorkbenchOperations = new Set();
let workbenchMutationBusy = false;
let taskBrowser = null;

const workbenchState = {
  inventory: null,
  datasetId: null,
  taskName: null,
  trashEntryId: null,
  taskDetail: null,
  showTrash: false,
  taskSelection: new Set(),
  busy: false,
  search: "",
  tableSnapshot: null,
  taskRequestId: 0,
};

function workbenchRoot() {
  return document.querySelector("[data-harbor-workbench]");
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
  const root = workbenchRoot()?.querySelector?.("[data-harbor-task-browser]") || workbenchRoot();
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
      selectable: row => row.kind !== "empty" && !datasetIsReadOnly(row.dataset),
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
      edit: row => adminMode() && row.kind !== "empty" && !datasetIsReadOnly(row.dataset) ? {
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
  const availableKeys = new Set(overviewRows()
    .filter(row => row.kind !== "empty" && !datasetIsReadOnly(row.dataset))
    .map(overviewRowKey));
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
  setDisabled(surface, "[data-harbor-create-task]", workbenchState.busy || !dataset || datasetIsReadOnly(dataset) || workbenchState.showTrash);
  setDisabled(surface, "[data-harbor-sync-manifest]", workbenchState.busy || !dataset || datasetIsReadOnly(dataset) || workbenchState.showTrash);
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
  if (title) title.textContent = task?.directory || trash?.directory || t("harbor_task_detail_empty", "Select a Task");
  if (meta) {
    meta.textContent = task
      ? `${workbenchState.datasetId} · ${dataset?.format || "harbor"} · ${datasetIsReadOnly(dataset) ? t("read_only", "Read-only") : t("editable", "Editable")} · ${task.package_name || "-"} · ${t(`harbor_status_${task.status || "draft"}`, task.status || "draft")}`
      : trash
        ? `${workbenchState.datasetId} · ${trash.package_name || "-"} · ${t("harbor_trash", "Archived")}`
        : "";
  }
}

function renderFileTree(surface = workbenchRoot()) {
  const actions = surface?.querySelector?.("[data-harbor-file-actions]");
  const mutable = canMutateSelectedTask();
  if (actions) actions.hidden = !mutable || !workbenchState.taskDetail || workbenchState.showTrash;
  const browser = workbenchTaskBrowser();
  browser?.setEditable(mutable);
  browser?.setContextMenu(mutable ? fileActionMenu : null);
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
  const feedback = taskFeedback("file", taskName, "load");
  try {
    const detail = await serveApi(`/api/harbor/datasets/${encodeURIComponent(datasetId)}/tasks/${encodeURIComponent(taskName)}`);
    if (requestId !== workbenchState.taskRequestId || datasetId !== workbenchState.datasetId || taskName !== workbenchState.taskName) return;
    workbenchState.taskDetail = detail;
    renderHarborWorkbench();
    await workbenchTaskBrowser()?.setTaskDetail(detail, {
      taskRef: { dataset_id: datasetId, task: taskName },
    });
  } catch (error) {
    if (requestId === workbenchState.taskRequestId) feedback.error(error);
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
  const feedback = options.quiet ? null : pageFeedback("[data-harbor-workbench-status]");
  feedback?.pending(t("serve_loading_sources", "Loading…"));
  try {
    const payload = await serveApi("/api/harbor/datasets");
    workbenchState.inventory = payload;
    const selection = renderHarborWorkbench();
    if (selection.row?.kind === "task" && !options.skipTaskReload) await loadSelectedTask();
    feedback?.clear();
    return payload;
  } catch (error) {
    feedback?.error(error);
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
        if (!window.confirm(harborMessage("harbor_delete_file_confirm", "Permanently delete “{name}”?", { name: item.path }))) return false;
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
      if (stillSelected() && options.selectTask && !isHarborDirty() && operation.state !== "failed" && !failures.length) await selectTask(options.selectTask);
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
    ? workbenchRoot()?.querySelector(selector) : null, {
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
  surface.querySelector("[data-harbor-save]")?.addEventListener("click", saveFile);
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
