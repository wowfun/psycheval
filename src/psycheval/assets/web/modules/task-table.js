import { esc, t } from "./shared.js";
import { applyDataTableControls, bindDataTableControls, bindTableRowActivation, renderDataTable } from "./data-tables.js";

function taskColumns({ selection, rename } = {}) {
  return [
    ...(selection ? [selection] : []),
    { key: "dataset", label: t("harbor_dataset", "Dataset"), valueType: "identity", sortable: true, filterable: true, value: row => row.datasetId },
    { key: "task", label: t("task", "Task"), valueType: "identity", sortable: true, filterable: true, value: row => row.taskName || "—", edit: rename },
    { key: "package", label: t("harbor_package", "Package"), valueType: "identity", sortable: true, filterable: true, value: row => row.packageName || "—" },
    { key: "status", label: t("status", "Status"), valueType: "status", sortable: true, filterable: true,
      value: row => t(`harbor_status_${row.status}`, row.status),
      html: row => `<span class="harbor-status-rail ${esc(row.status)}">${esc(t(`harbor_status_${row.status}`, row.status))}</span>` },
    { key: "diagnostics", label: t("harbor_diagnostics", "Diagnostics"), valueType: "text", value: row => row.diagnostics || "—", fullText: row => row.diagnostics || "" },
  ];
}

function taskSearchText(row) {
  return [row.datasetId, row.taskName, row.packageName, row.status, t(`harbor_status_${row.status}`, row.status), row.diagnostics].filter(Boolean).join(" ").toLowerCase();
}

function renderTaskTable({ root, tableId, allRows, columns, search = "", selectedKey, onActivate, onChange, onSelectionChange, rowAttribute = "data-task-row" }) {
  const searched = search ? allRows.filter(row => taskSearchText(row).includes(search.trim().toLowerCase())) : allRows;
  const rows = applyDataTableControls(tableId, searched, columns, allRows);
  root.innerHTML = renderDataTable({ tableId, columns, rows, rowKey: row => row.key,
    tableClass: "harbor-overview-table", shellClass: "harbor-overview-table-shell",
    rowClass: row => `harbor-overview-row status-${esc(row.status)} ${row.key === selectedKey ? "selected-row" : ""}`,
    rowAttrs: row => `${rowAttribute} tabindex="0" data-task-row-key="${esc(row.key)}" data-task-row-token="${encodeURIComponent(row.key)}"`,
    filterOptionsRows: allRows, emptyText: t("harbor_task_empty", "No Tasks"),
  });
  bindDataTableControls(root, { tableId, columns, rows, rowKey: row => row.key, onChange, onSelectionChange });
  const byKey = new Map(rows.map(row => [row.key, row]));
  for (const node of root.querySelectorAll(`[${rowAttribute}]`)) {
    bindTableRowActivation(node, () => onActivate(byKey.get(node.dataset.taskRowKey), node));
  }
  return rows;
}

export { taskColumns, taskSearchText, renderTaskTable };
