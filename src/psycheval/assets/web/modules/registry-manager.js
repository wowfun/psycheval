import { adminMode, esc, t } from "./shared.js";
import { serveApi, serveEtag } from "./http.js";
import { openActionForm } from "./action-form.js";
import { beginFeedback, savedContentPreview } from "./action-feedback.js";
import { watchOperation } from "./operation-feedback.js";
import { closeModalSurface, openModalSurface } from "./modal-surfaces.js";
import { applyDataTableControls, bindDataTableControls, renderDataTable, selectionColumn } from "./data-tables.js";
import { invalidateWorkspace } from "../app/workspace-runtime.js";

/** Dataset registration and mount management share revisioned configuration. */
function createRegistryManager({ root, page, onRefresh }) {
  let snapshot = null, revision = null, busy = false, panel = null;
  const selectedDatasets = new Set(), selectedMounts = new Set();
  async function refresh() {
    if (!adminMode()) return;
    snapshot = await serveApi("/api/config");
    revision = serveEtag("/api/config");
    for (const [selection, items] of [[selectedDatasets, snapshot.datasets], [selectedMounts, snapshot.mounts]]) {
      const known = new Set(items.map(item => item.id));
      for (const id of selection) if (!known.has(id)) selection.delete(id);
    }
  }
  async function mutate(path, method, body) {
    if (busy) throw new Error(t("feedback_saved_refreshing", "Saved; refreshing the workspace…"));
    busy = true;
    try {
      const operation = await serveApi(path, { method, body, ifMatch: revision });
      const label = path.startsWith("/api/harbor/mount") ? t("serve_harbor_mounts", "Harbor mounts") : t("harbor_dataset", "Dataset");
      const feedback = beginFeedback(root, { page, key: `${page}:registry`, label });
      setTimeout(() => watchOperation(operation.id, {
        feedback, committed: true,
        onBusy(value) { busy = value; },
        async onComplete() {
          await refresh();
          invalidateWorkspace("dataset-registry");
          await onRefresh();
          if (panel && !panel.hidden) renderMounts();
        },
      }), 0);
      return operation;
    } catch (error) {
      busy = false;
      if (error.status === 412) {
        try {
          await refresh();
          error.savedContent = savedContentPreview("config", JSON.stringify(snapshot, null, 2));
          error.onEditorCancel = async () => {
            try {
              await onRefresh();
              if (panel && !panel.hidden) renderMounts();
            } catch (refreshError) { beginFeedback(root, { page }).error(refreshError); }
          };
        } catch (refreshError) {
          error.message += ` (${t("feedback_conflict_refresh_failed", "Could not load the current saved version")}: ${refreshError.message})`;
        }
      }
      throw error;
    }
  }
  function datasetMounts(id) { return (snapshot?.mounts || []).filter(m => m.dataset_ids.includes(id)).map(m => m.id); }
  async function updateDataset(row, changes) {
    const current = snapshot.datasets.find(item => item.id === row.id) || row;
    const next = { new_id: current.id, path: current.path, mount_ids: datasetMounts(current.id), ...changes };
    await mutate(`/api/harbor/datasets/${encodeURIComponent(row.id)}`, "PATCH", next);
    Object.assign(row, { id: next.new_id, path: next.path, mount_ids: next.mount_ids });
    if (selectedDatasets.delete(current.id)) selectedDatasets.add(next.new_id);
    return { rowKey: next.new_id };
  }
  function datasetColumns() {
    const identity = { key: "id", label: t("harbor_dataset", "Dataset"), valueType: "identity", sortable: true, filterable: true, value: row => row.id };
    if (!adminMode() || !snapshot) return [identity];
    return [
      selectionColumn({ key: "__dataset_select", selectionKey: row => row.id, selectionSet: () => selectedDatasets }),
      { ...identity, edit: row => ({ value: row.id, commit: (_row, new_id) => updateDataset(row, { new_id }) }) },
      { key: "path", label: t("harbor_dataset_path", "Dataset path"), valueType: "path", value: row => row.path, edit: row => ({ value: row.path, commit: (_row, path) => updateDataset(row, { path }) }) },
      { key: "mounts", label: t("serve_harbor_mounts", "Harbor mounts"), valueType: "list", value: row => row.mount_ids || [], edit: row => ({ value: datasetMounts(row.id), suggestions: snapshot?.mounts.map(m => m.id) || [], allowCustom: false, commit: (_row, mount_ids) => updateDataset(row, { mount_ids }) }) },
    ];
  }
  function createDataset(existing) {
    if (!adminMode()) return false;
    const title = existing ? t("harbor_register_dataset", "Register existing") : t("harbor_add_dataset", "New Dataset");
    return openActionForm({ title, submitLabel: title, fields: [
      ...(!existing ? [{ name: "id", label: t("harbor_dataset_id_prompt", "Dataset ID") }] : []),
      { name: "path", label: t("harbor_dataset_path", "Dataset path") },
      ...(!existing ? [
        { name: "package_name", label: t("harbor_dataset_package_prompt", "Dataset package name (org/name)"), defaultFrom: "id" },
        { name: "description", label: t("harbor_dataset_description_prompt", "Dataset description"), required: false },
      ] : []),
    ], submit: values => mutate("/api/harbor/datasets", "POST", { source: existing ? "existing" : "new", ...values }) });
  }
  async function removeDatasets() {
    if (!adminMode()) return false;
    if (!selectedDatasets.size || !window.confirm(t("harbor_unregister_selected_confirm", "Unregister selected Datasets? Files will not be deleted."))) return;
    await mutate("/api/harbor/dataset-unregistration-operations", "POST", { dataset_ids: [...selectedDatasets] });
    selectedDatasets.clear();
  }
  function renderMounts() {
    const target = panel.querySelector("[data-harbor-mount-config]");
    const focusedCell = target.contains(document.activeElement) ? document.activeElement.closest("[data-table-column-key]") : null;
    const focusedRow = focusedCell?.closest("[data-table-row-key]")?.dataset.tableRowKey;
    const update = async (row, changes) => {
      const oldId = row.id;
      const current = snapshot.mounts.find(item => item.id === oldId) || row;
      const next = { new_id: current.id, path: current.path, dataset_ids: current.dataset_ids, ...changes };
      await mutate(`/api/harbor/mounts/${encodeURIComponent(oldId)}`, "PATCH", next);
      const saved = { id: next.new_id, path: next.path, dataset_ids: next.dataset_ids };
      Object.assign(current, saved);
      Object.assign(row, saved);
      if (selectedMounts.delete(oldId)) selectedMounts.add(next.new_id);
      return { rowKey: next.new_id };
    };
    const columns = [
      selectionColumn({ key: "__mount_select", selectionKey: row => row.id, selectionSet: () => selectedMounts }),
      { key: "id", label: t("serve_harbor_mount_id", "Mount ID"), valueType: "identity", sortable: true, value: row => row.id, edit: row => ({ value: row.id, commit: (_row, new_id) => update(row, { new_id }) }) },
      { key: "path", label: t("serve_harbor_jobs_path", "Jobs path"), valueType: "path", value: row => row.path, edit: row => ({ value: row.path, commit: (_row, path) => update(row, { path }) }) },
      { key: "datasets", label: t("harbor_mount_datasets", "Datasets (in evidence lookup order)"), valueType: "list", value: row => row.dataset_ids, edit: row => ({ value: row.dataset_ids, suggestions: snapshot.datasets.map(d => d.id), allowCustom: false, commit: (_row, dataset_ids) => update(row, { dataset_ids }) }) },
    ];
    const rows = applyDataTableControls("harbor-mount-registry", snapshot.mounts, columns);
    target.innerHTML = renderDataTable({ tableId: "harbor-mount-registry", columns, rows, rowKey: row => row.id });
    bindDataTableControls(target, { tableId: "harbor-mount-registry", columns, rows, rowKey: row => row.id, onChange: renderMounts, onSelectionChange: renderMounts });
    panel.querySelector("[data-harbor-remove-mounts]").disabled = !selectedMounts.size;
    if (focusedCell) [...target.querySelectorAll("[data-table-column-key]")].find(cell =>
      cell.dataset.tableColumnKey === focusedCell.dataset.tableColumnKey && cell.closest("[data-table-row-key]")?.dataset.tableRowKey === focusedRow,
    )?.focus();
  }
  async function openMounts(opener) {
    if (!adminMode()) return false;
    await refresh();
    if (!panel) {
      panel = document.createElement("div");
      panel.className = "action-form-overlay";
      panel.hidden = true;
      panel.setAttribute("role", "dialog"); panel.setAttribute("aria-modal", "true");
      panel.setAttribute("aria-label", t("serve_harbor_mounts", "Harbor mounts"));
      panel.innerHTML = `<section class="registry-manager-panel"><header class="table-region-head"><h2>${esc(t("serve_harbor_mounts", "Harbor mounts"))}</h2><div class="table-region-actions"><button class="action-button" data-harbor-add-mount>${esc(t("serve_add_harbor_mount", "Add Harbor mount"))}</button><button class="action-button danger" data-harbor-remove-mounts>${esc(t("harbor_remove_selected_mounts", "Remove selected"))}</button><button class="action-button" data-close>${esc(t("close", "Close"))}</button></div></header><div data-harbor-mount-config></div></section>`;
      document.body.append(panel);
      panel.querySelector("[data-close]").addEventListener("click", () => closeModalSurface(panel));
      panel.addEventListener("keydown", event => { if (event.key === "Escape") { event.preventDefault(); closeModalSurface(panel); } });
      panel.querySelector("[data-harbor-add-mount]").addEventListener("click", () => openActionForm({
        title: t("serve_harbor_mounts", "Harbor mounts"), fields: [{ name: "path", label: t("serve_harbor_jobs_path_prompt", "Jobs path") }],
        submit: values => mutate("/api/harbor/mounts", "POST", values),
      }));
      panel.querySelector("[data-harbor-remove-mounts]").addEventListener("click", async () => {
        if (!window.confirm(t("harbor_remove_selected_mounts_confirm", "Remove selected Harbor mounts? Jobs files will not be deleted."))) return;
        try { await mutate("/api/harbor/mount-deletion-operations", "POST", { mount_ids: [...selectedMounts] }); selectedMounts.clear(); }
        catch (error) { beginFeedback(panel, { page }).error(error); }
      });
    }
    renderMounts();
    openModalSurface(panel, { opener, focusTarget: panel.querySelector("[data-close]"), onRequestClose: () => closeModalSurface(panel) });
  }
  return { get ready() { return snapshot !== null; }, refresh, datasetColumns, selectedDatasets, createDataset, removeDatasets, openMounts, destroy() { if (panel) { closeModalSurface(panel, { restoreFocus: false }); panel.remove(); } } };
}

export { createRegistryManager };
