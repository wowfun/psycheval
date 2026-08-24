import { adminMode, esc, t } from "./runtime.js";
import { applyDataTableControls, bindDataTableControls, bindDataTableSelection, renderDataTable, selectionColumn } from "./data-tables.js";
import { closeModalSurface, openModalSurface } from "./modal-surfaces.js";
import { applyDefaultDbToForm, syncAdapterDefaultDbControls } from "./serve-controls.js";
import { formPayload, selectedAdapterValue, serveApi, setAdapterChoice, showServeNotice } from "./serve-effects.js";

const harborConfigState = {
  snapshot: null,
  datasetSelection: new Set(),
  mountSelection: new Set(),
  acpSelection: new Set(),
  busy: false,
};
const activeConfigurationOperations = new Set();
let configurationMutationBusy = false;
const promptConfigState = {
  prompts: [],
  selectedId: "",
  renderedId: "",
  dirty: false,
};
const dbSessionSelections = new WeakMap();

function setConfigurationStatus(message = "", error = false) {
  const target = document.querySelector("[data-config-page-status]");
  if (!target) return;
  target.textContent = message;
  target.classList.toggle("danger", Boolean(error));
  target.hidden = !message;
}
function setAcpAgentFormStatus(message = "", error = false) {
  const target = document.querySelector("[data-acp-agent-form-status]");
  if (!target) return;
  target.textContent = message;
  target.classList.toggle("danger", Boolean(error));
  target.hidden = !message;
}
async function initializeConfiguration() {
  if (!adminMode()) return false;
  bindConfigurationActions();
  await refreshHarborConfig();
  return true;
}
async function refreshHarborConfig() {
  setConfigurationBusy(true);
  setConfigurationStatus(t("loading", "Loading"));
  try {
    const [configPayload, promptPayload] = await Promise.all([
      serveApi("/api/config"),
      serveApi("/api/prompts"),
    ]);
    harborConfigState.snapshot = configPayload;
    promptConfigState.prompts = Array.isArray(promptPayload?.prompts) ? promptPayload.prompts : [];
    if (!promptConfigState.prompts.some(prompt => prompt.id === promptConfigState.selectedId)) {
      promptConfigState.selectedId = promptConfigState.prompts[0]?.id || "";
      promptConfigState.dirty = false;
      promptConfigState.renderedId = "";
    }
    const knownDatasets = new Set((harborConfigState.snapshot?.datasets || []).map(dataset => dataset.id));
    Array.from(harborConfigState.datasetSelection).forEach(id => {
      if (!knownDatasets.has(id)) harborConfigState.datasetSelection.delete(id);
    });
    const knownMounts = new Set((harborConfigState.snapshot?.mounts || []).map(mount => mount.id));
    Array.from(harborConfigState.mountSelection).forEach(id => {
      if (!knownMounts.has(id)) harborConfigState.mountSelection.delete(id);
    });
    const knownAgents = new Set((harborConfigState.snapshot?.acp_agents || []).map(agent => agent.id));
    Array.from(harborConfigState.acpSelection).forEach(id => {
      if (!knownAgents.has(id)) harborConfigState.acpSelection.delete(id);
    });
    renderHarborConfiguration();
    setConfigurationBusy(false);
    setConfigurationStatus();
  } catch (error) {
    setConfigurationBusy(false);
    setConfigurationStatus(error.message || String(error), true);
  }
}
async function refreshConfigurationAfterConflict(error, { discardPrompt = false } = {}) {
  if (error?.status !== 409 || !/changed.*(?:refresh|reload) before saving/i.test(String(error?.message || ""))) return;
  if (discardPrompt) {
    promptConfigState.dirty = false;
    promptConfigState.renderedId = "";
  }
  await refreshHarborConfig();
}
function datasetMounts(dataset) {
  return (harborConfigState.snapshot?.mounts || [])
    .filter(mount => (mount.dataset_ids || []).includes(dataset.id))
    .map(mount => mount.id);
}
function referenceListHtml(values) {
  return values.length
    ? `<span class="source-tag-list">${values.map(value => `<span class="source-tag-chip">${esc(value)}</span>`).join("")}</span>`
    : "-";
}
function harborDatasetColumns() {
  return [
    selectionColumn({
      key: "__dataset_select",
      selectionKey: dataset => dataset.id,
      selectionSet: () => harborConfigState.datasetSelection,
      rowAriaLabel: id => `${t("select_row", "Select row")}: ${id}`,
    }),
    { key: "id", label: t("harbor_dataset", "Dataset"), valueType: "identity", sortable: true, value: dataset => dataset.id, edit: { value: dataset => dataset.id, commit: (dataset, value) => updateHarborDataset(dataset, { new_id: value }) } },
    { key: "path", label: t("harbor_dataset_path", "Dataset path"), valueType: "path", value: dataset => dataset.path, edit: { value: dataset => dataset.path, commit: (dataset, value) => updateHarborDataset(dataset, { path: value }) } },
    { key: "mounts", label: t("serve_harbor_mounts", "Harbor mounts"), valueType: "list", value: dataset => datasetMounts(dataset), format: values => values.join(", ") || "-", html: dataset => referenceListHtml(datasetMounts(dataset)), edit: { value: dataset => datasetMounts(dataset), suggestions: () => (harborConfigState.snapshot?.mounts || []).map(mount => mount.id), allowCustom: false, commit: (dataset, value) => updateHarborDataset(dataset, { mount_ids: value }) } },
  ];
}
function harborMountColumns() {
  return [
    selectionColumn({
      key: "__mount_select",
      selectionKey: mount => mount.id,
      selectionSet: () => harborConfigState.mountSelection,
      rowAriaLabel: id => `${t("select_row", "Select row")}: ${id}`,
    }),
    { key: "id", label: t("serve_harbor_mount_id", "Mount ID"), valueType: "identity", sortable: true, value: mount => mount.id, edit: { value: mount => mount.id, commit: (mount, value) => updateHarborMount(mount, { mount_id: value }) } },
    { key: "path", label: t("serve_harbor_jobs_path", "Jobs path"), valueType: "path", value: mount => mount.path, edit: { value: mount => mount.path, commit: (mount, value) => updateHarborMount(mount, { jobs_path: value }) } },
    { key: "datasets", label: t("harbor_mount_datasets", "Datasets (in evidence lookup order)"), valueType: "list", value: mount => mount.dataset_ids || [], format: values => values.join(", ") || "-", html: mount => referenceListHtml(mount.dataset_ids || []), edit: { value: mount => mount.dataset_ids || [], suggestions: () => (harborConfigState.snapshot?.datasets || []).map(dataset => dataset.id), allowCustom: false, commit: (mount, value) => updateHarborMount(mount, { dataset_ids: value }) } },
  ];
}
function acpAgentColumns() {
  return [
    selectionColumn({
      key: "__acp_agent_select",
      selectionKey: agent => agent.id,
      selectionSet: () => harborConfigState.acpSelection,
      rowAriaLabel: id => `${t("select_row", "Select row")}: ${id}`,
    }),
    { key: "id", label: t("acp_agent", "Agent"), valueType: "identity", sortable: true, value: agent => agent.id, edit: { value: agent => agent.id, commit: (agent, value) => updateAcpAgent(agent, { agent_id: value }) } },
    { key: "title", label: t("name", "Name"), valueType: "text", value: agent => agent.title, edit: { value: agent => agent.title, commit: (agent, value) => updateAcpAgent(agent, { title: value }) } },
    { key: "command", label: t("serve_acp_command", "Executable"), valueType: "path", value: agent => agent.command, edit: { value: agent => agent.command, commit: (agent, value) => updateAcpAgent(agent, { command: value }) } },
    { key: "args", label: t("serve_acp_args", "Arguments (JSON)"), valueType: "text", value: agent => JSON.stringify(agent.args || []), edit: { value: agent => JSON.stringify(agent.args || []), commit: (agent, value) => updateAcpAgent(agent, { args: parseAcpArgs(value) }) } },
    { key: "status", label: t("status", "Status"), valueType: "status", value: agent => agent.connected ? t("serve_acp_connected", "Connected") : t("serve_acp_idle", "Not connected"), html: agent => `<span class="acp-config-status${agent.connected ? " connected" : ""}">${esc(agent.connected ? t("serve_acp_connected", "Connected") : t("serve_acp_idle", "Not connected"))}</span>` },
  ];
}
async function choosePathSourceFiles(button) {
  if (!adminMode()) return;
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
    setConfigurationStatus(t("serve_path_picker_selected", "Path selection updated"));
  } catch (error) {
    const message = error.message || String(error);
    showServeNotice(message, true);
    setConfigurationStatus(message, true);
  }
}
function renderHarborConfiguration() {
  renderAcpAgentConfiguration();
  renderPromptConfiguration();
  renderHarborDatasetRegistry();
  renderHarborMountConfiguration();
  syncConfigurationBusy();
}
function renderAcpAgentConfiguration() {
  const root = document.querySelector("[data-acp-agent-config]");
  if (!root) return;
  const agents = harborConfigState.snapshot?.acp_agents || [];
  const columns = acpAgentColumns();
  const rows = applyDataTableControls("acp-agent-registry", agents, columns);
  root.innerHTML = renderDataTable({
    tableId: "acp-agent-registry",
    columns,
    rows,
    rowKey: agent => agent.id,
    emptyText: t("serve_acp_empty", "No ACP agents configured"),
  });
  bindDataTableControls(root, {
    tableId: "acp-agent-registry",
    columns,
    rows,
    rowKey: agent => agent.id,
    onChange: renderAcpAgentConfiguration,
    onSelectionChange: renderAcpAgentConfiguration,
  });
  const count = document.querySelector("[data-acp-agent-count]");
  if (count) count.textContent = `${agents.length}`;
  const remove = document.querySelector("[data-acp-remove-agents]");
  if (remove) {
    remove.disabled = harborConfigState.acpSelection.size < 1;
    remove.textContent = harborConfigState.acpSelection.size
      ? `${t("serve_remove_selected_agents", "Remove selected")} (${harborConfigState.acpSelection.size})`
      : t("serve_remove_selected_agents", "Remove selected");
  }
}
function selectedPromptAsset() {
  return promptConfigState.prompts.find(prompt => prompt.id === promptConfigState.selectedId) || null;
}
function renderPromptConfiguration() {
  const list = document.querySelector("[data-prompt-config-list]");
  const editor = document.querySelector("[data-prompt-content]");
  if (!list || !editor) return;
  list.innerHTML = promptConfigState.prompts.map(prompt => `
    <button type="button" class="${prompt.id === promptConfigState.selectedId ? "active" : ""}" data-prompt-select="${esc(prompt.id)}" aria-pressed="${prompt.id === promptConfigState.selectedId ? "true" : "false"}">
      <strong>${esc(prompt.title)}</strong><code>${esc(prompt.filename)}</code>
    </button>`).join("");
  const prompt = selectedPromptAsset();
  if (promptConfigState.renderedId !== prompt?.id || !promptConfigState.dirty) {
    editor.value = prompt?.content || "";
    promptConfigState.renderedId = prompt?.id || "";
  }
  editor.disabled = !prompt;
  const filename = document.querySelector("[data-prompt-filename]");
  if (filename) filename.textContent = prompt ? `prompts/${prompt.filename}` : "—";
  const origin = document.querySelector("[data-prompt-origin]");
  if (origin) origin.textContent = prompt?.customized
    ? t("serve_prompt_override", "Workspace override")
    : t("serve_prompt_default", "Repository default");
  const count = document.querySelector("[data-prompt-asset-count]");
  if (count) count.textContent = `${promptConfigState.prompts.length}`;
  const save = document.querySelector("[data-prompt-save]");
  if (save) save.disabled = !prompt || !promptConfigState.dirty || !String(editor.value || "").trim();
  const reset = document.querySelector("[data-prompt-reset]");
  if (reset) reset.disabled = !prompt?.customized;
}
function setConfigurationBusy(busy) {
  configurationMutationBusy = Boolean(busy);
  syncConfigurationBusyState();
}
function syncConfigurationBusyState() {
  harborConfigState.busy = configurationMutationBusy || activeConfigurationOperations.size > 0;
  syncConfigurationBusy();
}
function syncConfigurationBusy() {
  const root = document.querySelector("[data-config-page]");
  if (!root) return;
  root.setAttribute("aria-busy", harborConfigState.busy ? "true" : "false");
  root.querySelectorAll("button,input,select,textarea").forEach(control => {
    if (control.closest("[data-table-cell-editor]") && !harborConfigState.busy) return;
    if (harborConfigState.busy) {
      if (!Object.prototype.hasOwnProperty.call(control.dataset, "configPreviousDisabled")) {
        control.dataset.configPreviousDisabled = control.disabled ? "true" : "false";
      }
      control.disabled = true;
    } else if (Object.prototype.hasOwnProperty.call(control.dataset, "configPreviousDisabled")) {
      control.disabled = control.dataset.configPreviousDisabled === "true";
      delete control.dataset.configPreviousDisabled;
    }
  });
}
function renderHarborDatasetRegistry() {
  const root = document.querySelector("[data-harbor-dataset-registry]");
  if (!root) return;
  const datasets = harborConfigState.snapshot?.datasets || [];
  const columns = harborDatasetColumns();
  const rows = applyDataTableControls("harbor-dataset-registry", datasets, columns);
  root.innerHTML = renderDataTable({
    tableId: "harbor-dataset-registry",
    columns,
    rows,
    rowKey: dataset => dataset.id,
    emptyText: t("harbor_dataset_empty", "No Datasets registered"),
  });
  bindDataTableControls(root, {
    tableId: "harbor-dataset-registry",
    columns,
    rows,
    rowKey: dataset => dataset.id,
    onChange: renderHarborDatasetRegistry,
    onSelectionChange: renderHarborDatasetRegistry,
  });
  const count = document.querySelector("[data-harbor-dataset-count]");
  if (count) count.textContent = `${datasets.length}`;
  const unregister = document.querySelector("[data-harbor-unregister-datasets]");
  if (unregister) {
    unregister.disabled = harborConfigState.datasetSelection.size < 1;
    unregister.textContent = harborConfigState.datasetSelection.size
      ? `${t("harbor_unregister_selected", "Unregister selected")} (${harborConfigState.datasetSelection.size})`
      : t("harbor_unregister_selected", "Unregister selected");
  }
}
function renderHarborMountConfiguration() {
  const root = document.querySelector("[data-harbor-mount-config]");
  if (!root) return;
  const mounts = harborConfigState.snapshot?.mounts || [];
  const columns = harborMountColumns();
  const rows = applyDataTableControls("harbor-mount-registry", mounts, columns);
  root.innerHTML = renderDataTable({
    tableId: "harbor-mount-registry",
    columns,
    rows,
    rowKey: mount => mount.id,
    emptyText: t("harbor_mount_empty", "No Harbor mounts configured"),
  });
  bindDataTableControls(root, {
    tableId: "harbor-mount-registry",
    columns,
    rows,
    rowKey: mount => mount.id,
    onChange: renderHarborMountConfiguration,
    onSelectionChange: renderHarborMountConfiguration,
  });
  const count = document.querySelector("[data-harbor-mount-count]");
  if (count) count.textContent = `${mounts.length}`;
  const remove = document.querySelector("[data-harbor-remove-mounts]");
  if (remove) {
    remove.disabled = harborConfigState.mountSelection.size < 1;
    remove.textContent = harborConfigState.mountSelection.size
      ? `${t("harbor_remove_selected_mounts", "Remove selected")} (${harborConfigState.mountSelection.size})`
      : t("harbor_remove_selected_mounts", "Remove selected");
  }
}
function bindConfigurationActions() {
  const root = document.querySelector("[data-config-page]");
  if (!root || root.dataset.configBound === "true") return;
  root.dataset.configBound = "true";
  root.querySelector("[data-harbor-add-dataset]")?.addEventListener("click", () => createHarborDataset(false));
  root.querySelector("[data-harbor-register-dataset]")?.addEventListener("click", () => createHarborDataset(true));
  root.querySelector("[data-harbor-unregister-datasets]")?.addEventListener("click", unregisterSelectedHarborDatasets);
  root.querySelector("[data-harbor-add-mount]")?.addEventListener("click", addHarborMount);
  root.querySelector("[data-harbor-remove-mounts]")?.addEventListener("click", removeSelectedHarborMounts);
  root.querySelector("[data-acp-agent-form-open]")?.addEventListener("click", openAcpAgentForm);
  root.querySelector("[data-acp-agent-form]")?.addEventListener("submit", addAcpAgent);
  root.querySelector("[data-acp-agent-form-cancel]")?.addEventListener("click", () => closeAcpAgentForm());
  const acpAgentPanel = root.querySelector("[data-acp-agent-form-panel]");
  acpAgentPanel?.addEventListener("click", event => {
    if (event.target === acpAgentPanel) closeAcpAgentForm();
  });
  acpAgentPanel?.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    closeAcpAgentForm();
  });
  root.querySelector("[data-acp-remove-agents]")?.addEventListener("click", removeSelectedAcpAgents);
  root.querySelector("[data-prompt-config-list]")?.addEventListener("click", selectPromptAsset);
  root.querySelector("[data-prompt-content]")?.addEventListener("input", () => {
    promptConfigState.dirty = true;
    renderPromptConfiguration();
  });
  root.querySelector("[data-prompt-save]")?.addEventListener("click", savePromptAsset);
  root.querySelector("[data-prompt-reset]")?.addEventListener("click", resetPromptAsset);
  root.querySelector("[data-harbor-config-reload]")?.addEventListener("click", reloadConfiguration);
  root.querySelector("[data-source-config-rescan]")?.addEventListener("click", rescanTrajectorySources);
}
function openAcpAgentForm(event) {
  if (!adminMode()) return false;
  const panel = document.querySelector("[data-acp-agent-form-panel]");
  const form = panel?.querySelector("[data-acp-agent-form]");
  form?.reset?.();
  setAcpAgentFormStatus();
  return openModalSurface(panel, {
    opener: event?.currentTarget,
    bodyClass: "acp-agent-form-open",
    focusTarget: panel?.querySelector('[name="agent_id"]'),
  });
}
function closeAcpAgentForm(options = {}) {
  return closeModalSurface(
    document.querySelector("[data-acp-agent-form-panel]"),
    options,
  );
}
async function reloadConfiguration() {
  if (promptConfigState.dirty && !window.confirm(t("serve_prompt_discard_confirm", "Discard unsaved prompt changes?"))) return;
  promptConfigState.dirty = false;
  promptConfigState.renderedId = "";
  await refreshHarborConfig();
}
function parseAcpArgs(value) {
  let parsed;
  try {
    parsed = JSON.parse(String(value || ""));
  } catch {
    throw new Error(t("serve_acp_args_invalid", "Arguments must be a JSON array of strings"));
  }
  if (!Array.isArray(parsed) || !parsed.every(item => typeof item === "string")) {
    throw new Error(t("serve_acp_args_invalid", "Arguments must be a JSON array of strings"));
  }
  return parsed;
}
async function mutateAcpAgents(body) {
  setConfigurationBusy(true);
  try {
    harborConfigState.snapshot = await serveApi("/api/config/acp/agents", {
      method: "POST",
      body: { ...body, expected_revision: harborConfigState.snapshot?.revision },
    });
    setConfigurationBusy(false);
    return harborConfigState.snapshot;
  } catch (error) {
    setConfigurationBusy(false);
    await refreshConfigurationAfterConflict(error);
    throw error;
  }
}
async function addAcpAgent(event) {
  event.preventDefault();
  if (!adminMode()) return;
  const fields = formPayload(event.currentTarget);
  const agentId = String(fields.agent_id || "").trim();
  const title = String(fields.title || "").trim();
  const command = String(fields.command || "").trim();
  if (!agentId || !title || !command) {
    setAcpAgentFormStatus(t("required", "Required"), true);
    return;
  }
  try {
    setAcpAgentFormStatus(t("saving", "Saving..."));
    await mutateAcpAgents({ action: "upsert", agent_id: agentId, title, command, args: parseAcpArgs(fields.args) });
    renderAcpAgentConfiguration();
    setAcpAgentFormStatus();
    closeAcpAgentForm();
  } catch (error) {
    setAcpAgentFormStatus(error.message || String(error), true);
  }
}
async function updateAcpAgent(agent, changes) {
  const next = {
    agent_id: String(changes.agent_id ?? agent.id).trim(),
    title: String(changes.title ?? agent.title).trim(),
    command: String(changes.command ?? agent.command).trim(),
    args: Array.isArray(changes.args) ? changes.args : (agent.args || []),
  };
  if (!next.agent_id || !next.title || !next.command) throw new Error(t("required", "Required"));
  try {
    await mutateAcpAgents({ action: "upsert", original_id: agent.id, ...next });
    if (next.agent_id !== agent.id && harborConfigState.acpSelection.delete(agent.id)) harborConfigState.acpSelection.add(next.agent_id);
    renderAcpAgentConfiguration();
    return { rowKey: next.agent_id };
  } catch (error) {
    setConfigurationStatus(error.message || String(error), true);
    throw error;
  }
}
async function removeSelectedAcpAgents() {
  const agentIds = Array.from(harborConfigState.acpSelection);
  if (!agentIds.length || !window.confirm(t("serve_acp_remove_confirm", "Remove selected ACP agents? Connected processes will be stopped."))) return;
  try {
    setConfigurationStatus(t("saving", "Saving..."));
    await mutateAcpAgents({ action: "delete", agent_ids: agentIds });
    harborConfigState.acpSelection.clear();
    renderAcpAgentConfiguration();
    setConfigurationStatus();
  } catch (error) {
    setConfigurationStatus(error.message || String(error), true);
  }
}
function selectPromptAsset(event) {
  const button = event.target.closest?.("[data-prompt-select]");
  if (!button) return;
  const nextId = String(button.dataset.promptSelect || "");
  if (!nextId || nextId === promptConfigState.selectedId) return;
  if (promptConfigState.dirty && !window.confirm(t("serve_prompt_discard_confirm", "Discard unsaved prompt changes?"))) return;
  promptConfigState.selectedId = nextId;
  promptConfigState.dirty = false;
  promptConfigState.renderedId = "";
  renderPromptConfiguration();
}
function replacePromptAsset(prompt) {
  const index = promptConfigState.prompts.findIndex(item => item.id === prompt.id);
  if (index >= 0) promptConfigState.prompts[index] = prompt;
}
async function savePromptAsset() {
  const prompt = selectedPromptAsset();
  const content = document.querySelector("[data-prompt-content]")?.value || "";
  if (!prompt || !String(content).trim()) return;
  try {
    setConfigurationBusy(true);
    setConfigurationStatus(t("saving", "Saving..."));
    const payload = await serveApi("/api/prompts", { method: "POST", body: { action: "save", prompt_id: prompt.id, content, expected_revision: prompt.revision } });
    replacePromptAsset(payload.prompt);
    promptConfigState.dirty = false;
    setConfigurationBusy(false);
    renderPromptConfiguration();
    setConfigurationStatus();
  } catch (error) {
    setConfigurationBusy(false);
    await refreshConfigurationAfterConflict(error, { discardPrompt: true });
    setConfigurationStatus(error.message || String(error), true);
  }
}
async function resetPromptAsset() {
  const prompt = selectedPromptAsset();
  if (!prompt?.customized || !window.confirm(t("serve_prompt_reset_confirm", "Remove this workspace override and restore the repository default?"))) return;
  try {
    setConfigurationBusy(true);
    const payload = await serveApi("/api/prompts", { method: "POST", body: { action: "reset", prompt_id: prompt.id, expected_revision: prompt.revision } });
    replacePromptAsset(payload.prompt);
    promptConfigState.dirty = false;
    setConfigurationBusy(false);
    renderPromptConfiguration();
    setConfigurationStatus();
  } catch (error) {
    setConfigurationBusy(false);
    await refreshConfigurationAfterConflict(error, { discardPrompt: true });
    setConfigurationStatus(error.message || String(error), true);
  }
}
async function rescanTrajectorySources() {
  try {
    setConfigurationBusy(true);
    setConfigurationStatus(t("serve_scanning_runs", "Checking runs"));
    const operation = await serveApi("/api/sources/reload", { method: "POST", body: {} });
    setConfigurationBusy(false);
    await pollConfigurationOperation(operation.operation_id);
  } catch (error) {
    setConfigurationBusy(false);
    setConfigurationStatus(error.message || String(error), true);
  }
}
async function pollConfigurationOperation(operationId) {
  if (!operationId) return;
  activeConfigurationOperations.add(operationId);
  syncConfigurationBusyState();
  try {
    const operation = await serveApi(`/api/operations/${encodeURIComponent(operationId)}`);
    setConfigurationStatus(`${operation.operation_type}: ${operation.completed}/${operation.total}`);
    if (["queued", "running"].includes(operation.state)) {
      setTimeout(() => pollConfigurationOperation(operationId), 250);
      return;
    }
    const failures = Array.isArray(operation.failures) ? operation.failures : [];
    activeConfigurationOperations.delete(operationId);
    syncConfigurationBusyState();
    if (!showImportResultsSummary(operation)) {
      setConfigurationStatus(failures[0]?.error || "", failures.length > 0 || operation.state === "failed");
    }
  } catch (error) {
    activeConfigurationOperations.delete(operationId);
    syncConfigurationBusyState();
    setConfigurationStatus(error.message || String(error), true);
  }
}
async function mutateHarborDataset(body) {
  setConfigurationBusy(true);
  try {
    const payload = await serveApi("/api/config/harbor/datasets", {
      method: "POST",
      body: { ...body, expected_revision: harborConfigState.snapshot?.revision },
    });
    harborConfigState.snapshot = payload.result || harborConfigState.snapshot;
    if (payload.operation?.operation_id) {
      setConfigurationBusy(false);
      pollConfigurationOperation(payload.operation.operation_id);
    }
    else setConfigurationBusy(false);
    return payload;
  } catch (error) {
    setConfigurationBusy(false);
    await refreshConfigurationAfterConflict(error);
    throw error;
  }
}
async function updateHarborDataset(dataset, changes) {
  const newId = String(changes.new_id ?? dataset.id).trim();
  const path = String(changes.path ?? dataset.path).trim();
  const mountIds = Array.isArray(changes.mount_ids) ? changes.mount_ids : datasetMounts(dataset);
  if (!newId || !path) throw new Error(t("required", "Required"));
  try {
    await mutateHarborDataset({ action: "update", dataset_id: dataset.id, new_id: newId, path, mount_ids: mountIds });
    if (newId !== dataset.id && harborConfigState.datasetSelection.delete(dataset.id)) harborConfigState.datasetSelection.add(newId);
    renderHarborConfiguration();
    return { rowKey: newId };
  } catch (error) {
    setConfigurationStatus(error.message || String(error), true);
    throw error;
  }
}
async function createHarborDataset(register = false) {
  if (!adminMode()) return;
  const datasetId = register
    ? ""
    : window.prompt(t("harbor_dataset_id_prompt", "Dataset ID"));
  if (!register && !datasetId) return;
  const path = window.prompt(register
    ? t("harbor_existing_dataset_path_prompt", "Existing Dataset directory")
    : t("harbor_dataset_path_prompt", "Dataset path"));
  if (!path) return;
  const body = register
    ? { action: "register", path }
    : { action: "create", dataset_id: datasetId, path };
  if (!register) {
    const packageName = window.prompt(t("harbor_dataset_package_prompt", "Dataset package name (org/name)"), datasetId);
    if (!packageName) return;
    body.package_name = packageName;
    body.description = window.prompt(t("harbor_dataset_description_prompt", "Dataset description"), "") || "";
  }
  try {
    setConfigurationStatus(t("saving", "Saving..."));
    await mutateHarborDataset(body);
    renderHarborConfiguration();
    setConfigurationStatus();
  } catch (error) {
    setConfigurationStatus(error.message || String(error), true);
  }
}
async function unregisterSelectedHarborDatasets() {
  const datasetIds = Array.from(harborConfigState.datasetSelection);
  if (!datasetIds.length || !window.confirm(t("harbor_unregister_selected_confirm", "Unregister selected Datasets? Files will not be deleted."))) return;
  try {
    setConfigurationStatus(t("saving", "Saving..."));
    await mutateHarborDataset({ action: "unregister", dataset_ids: datasetIds });
    harborConfigState.datasetSelection.clear();
    renderHarborConfiguration();
    setConfigurationStatus();
  } catch (error) {
    setConfigurationStatus(error.message || String(error), true);
  }
}
async function submitServeSourceForm(form) {
  if (!adminMode()) return;
  if (form?.dataset?.sourceKind === "db") applyDefaultDbToForm(form);
  const body = formPayload(form);
  const kind = form.dataset.sourceKind;
  if (!kind) return;
  const sourceValue = String(body[kind] || "").trim();
  if (!sourceValue) return;
  try {
    setConfigurationBusy(true);
    setConfigurationStatus(t("serve_refresh", "Refresh"));
    const payload = await serveApi("/api/sources", { method: "POST", body });
    form.reset();
    if (kind === "db") syncAdapterDefaultDbControls(form);
    setConfigurationBusy(false);
    if (payload?.operation_id) pollConfigurationOperation(payload.operation_id);
    showImportResultsSummary(payload);
  } catch (error) {
    setConfigurationBusy(false);
    showServeNotice(`${t("serve_import_failed", "Import failed")}: ${error.message || String(error)}`, true);
    setConfigurationStatus(error.message || String(error), true);
  }
}
function showImportResultsSummary(payload) {
  let results = Array.isArray(payload?.import_results)
    ? payload.import_results
    : Array.isArray(payload?.result?.import_results)
    ? payload.result.import_results
    : [];
  if (!results.length && payload?.operation_type === "source-import") {
    results = [
      ...(Array.isArray(payload?.successes) ? payload.successes : []),
      ...(Array.isArray(payload?.failures) ? payload.failures : []),
    ].sort((left, right) => Number(left?.index || 0) - Number(right?.index || 0));
  }
  if (!results.length) return false;
  const imported = results.filter(result => result?.status === "ok").length;
  const failures = results.filter(result => result?.status === "error");
  const failed = failures.length;
  const template = t("serve_import_summary", "Imported {imported}, failed {failed}");
  let message = template.replace("{imported}", String(imported)).replace("{failed}", String(failed));
  const firstError = String(failures[0]?.error || "").trim();
  if (firstError) message = `${message}: ${firstError}`;
  showServeNotice(message, failed > 0);
  setConfigurationStatus(message, failed > 0);
  return true;
}
async function inspectDbSessions(form) {
  if (!adminMode()) return;
  if (!form) return;
  applyDefaultDbToForm(form);
  const body = formPayload(form);
  const db = String(body.db || "").trim();
  if (!db) return;
  const picker = form.querySelector("[data-db-session-picker]");
  try {
    setConfigurationStatus(t("serve_inspect_db", "Inspect DB"));
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
    setConfigurationStatus(t("serve_latest_snapshots", "Latest snapshots"));
  } catch (error) {
    if (picker) {
      picker.hidden = false;
      picker.innerHTML = `<p class="copy danger">${esc(error.message || String(error))}</p>`;
    }
    setConfigurationStatus(error.message || String(error), true);
  }
}
function renderDbSessionPicker(form, payload) {
  const picker = form.querySelector("[data-db-session-picker]");
  if (!picker) return;
  const sessions = Array.isArray(payload?.sessions) ? payload.sessions : [];
  const selection = new Set();
  dbSessionSelections.set(form, selection);
  form.dataset.inspectedDb = payload?.db || "";
  form.dataset.inspectedAdapter = payload?.adapter || "";
  picker.hidden = false;
  if (!sessions.length) {
    picker.innerHTML = `<div class="db-picker-head"><strong>${esc(t("serve_db_sessions", "DB sessions"))}</strong><span>${esc(t("serve_no_sessions", "No sessions found"))}</span></div>`;
    return;
  }
  const adapterLabel = payload?.inferred ? t("serve_adapter_inferred", "Adapter inferred") : t("serve_adapter_selected", "Adapter selected");
  const columns = [
    selectionColumn({
      key: "__db_session_select",
      selectionKey: session => String(session?.session_id || ""),
      selectionSet: () => selection,
      rowAriaLabel: id => `${t("select_row", "Select row")}: ${id}`,
    }),
    { key: "index", label: "#", valueType: "number", numeric: true, value: session => session?.index ?? "-" },
    { key: "session_id", label: t("session", "Session"), valueType: "identity", value: session => session?.session_id || "-", html: session => `<code>${esc(session?.session_id || "-")}</code>` },
    { key: "name", label: t("serve_session_name", "Name"), valueType: "text", value: session => session?.name || "-" },
  ];
  picker.innerHTML = `
    <div class="db-picker-head">
      <div><strong>${esc(t("serve_db_sessions", "DB sessions"))}</strong><span>${esc(adapterLabel)}: ${esc(payload?.adapter || "-")}</span></div>
      <div class="db-picker-actions">
        <span data-db-selected-count>0 ${esc(t("serve_selected_count", "selected"))}</span>
        <button class="action-button primary" type="button" data-db-add-selected disabled>${esc(t("serve_add_selected", "Add selected"))}</button>
      </div>
    </div>
    <div class="db-session-table-wrap">${renderDataTable({
      tableId: "db-sessions",
      columns,
      rows: sessions,
      rowKey: session => session?.session_id || "",
      tableClass: "db-session-table",
    })}</div>
  `;
  bindDataTableSelection(picker, {
    columns,
    rows: sessions,
    onChange: () => updateDbSelectedCount(picker, form),
  });
  updateDbSelectedCount(picker, form);
}
function selectedDbSessionIds(form) {
  return Array.from(dbSessionSelections.get(form) || []);
}
function updateDbSelectedCount(picker, form = picker?.closest?.("[data-source-add-form]")) {
  const count = dbSessionSelections.get(form)?.size || 0;
  const target = picker.querySelector("[data-db-selected-count]");
  if (target) target.textContent = `${count} ${t("serve_selected_count", "selected")}`;
  const addButton = picker.querySelector("[data-db-add-selected]");
  if (addButton) addButton.disabled = count < 1;
}
async function addSelectedDbSessions(form) {
  if (!adminMode()) return;
  if (!form) return;
  const sessionIds = selectedDbSessionIds(form);
  if (!sessionIds.length) {
    setConfigurationStatus(t("serve_select_sessions", "Select sessions"), true);
    return;
  }
  const body = formPayload(form);
  try {
    setConfigurationBusy(true);
    setConfigurationStatus(t("serve_refresh", "Refresh"));
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
    dbSessionSelections.delete(form);
    delete form.dataset.inspectedDb;
    delete form.dataset.inspectedAdapter;
    setConfigurationBusy(false);
    if (payload?.operation_id) pollConfigurationOperation(payload.operation_id);
  } catch (error) {
    setConfigurationBusy(false);
    showServeNotice(`${t("serve_import_failed", "Import failed")}: ${error.message || String(error)}`, true);
    setConfigurationStatus(error.message || String(error), true);
  }
}
async function mutateHarborMount(body) {
  if (!adminMode()) return;
  setConfigurationBusy(true);
  try {
    const payload = await serveApi("/api/config/harbor/mounts", {
      method: "POST",
      body: { ...body, expected_revision: harborConfigState.snapshot?.revision },
    });
    harborConfigState.snapshot = payload.result || harborConfigState.snapshot;
    if (payload.operation?.operation_id) {
      setConfigurationBusy(false);
      pollConfigurationOperation(payload.operation.operation_id);
    }
    else setConfigurationBusy(false);
    return payload;
  } catch (error) {
    setConfigurationBusy(false);
    await refreshConfigurationAfterConflict(error);
    throw error;
  }
}
async function addHarborMount() {
  if (!adminMode()) return;
  const jobsPath = window.prompt(t("serve_harbor_jobs_path_prompt", "Jobs path"));
  if (!jobsPath) return;
  try {
    setConfigurationStatus(t("saving", "Saving..."));
    await mutateHarborMount({ action: "upsert", jobs_path: jobsPath });
    renderHarborConfiguration();
    setConfigurationStatus();
  } catch (error) {
    setConfigurationStatus(error.message || String(error), true);
  }
}
async function updateHarborMount(mount, changes) {
  const mountId = String(changes.mount_id ?? mount.id).trim();
  const jobsPath = String(changes.jobs_path ?? mount.path).trim();
  const datasetIds = Array.isArray(changes.dataset_ids) ? changes.dataset_ids : (mount.dataset_ids || []);
  if (!mountId || !jobsPath) throw new Error(t("required", "Required"));
  try {
    await mutateHarborMount({
      action: "upsert",
      original_id: mount.id,
      mount_id: mountId,
      jobs_path: jobsPath,
      dataset_ids: datasetIds,
    });
    if (mountId !== mount.id && harborConfigState.mountSelection.delete(mount.id)) harborConfigState.mountSelection.add(mountId);
    renderHarborConfiguration();
    return { rowKey: mountId };
  } catch (error) {
    setConfigurationStatus(error.message || String(error), true);
    throw error;
  }
}
async function removeSelectedHarborMounts() {
  const mountIds = Array.from(harborConfigState.mountSelection);
  if (!mountIds.length || !window.confirm(t("harbor_remove_selected_mounts_confirm", "Remove selected Harbor mounts? Jobs files will not be deleted."))) return;
  try {
    setConfigurationStatus(t("saving", "Saving..."));
    await mutateHarborMount({ action: "delete", mount_ids: mountIds });
    harborConfigState.mountSelection.clear();
    renderHarborConfiguration();
    setConfigurationStatus();
  } catch (error) {
    setConfigurationStatus(error.message || String(error), true);
  }
}
export {
  addHarborMount,
  addSelectedDbSessions,
  choosePathSourceFiles,
  initializeConfiguration,
  inspectDbSessions,
  renderDbSessionPicker,
  removeSelectedHarborMounts,
  selectedDbSessionIds,
  showImportResultsSummary,
  submitServeSourceForm,
  updateDbSelectedCount,
  harborConfigState,
  promptConfigState,
  setConfigurationBusy,
};
