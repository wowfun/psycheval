import { formatUtcDate } from "./date-time.js";
import { listValue, lower, state } from "./runtime.js";
import { exportCurrentScope, selectServeDetail } from "./serve-catalog.js";
import { bindTableRowActivation } from "./data-tables.js";
function bindServeExportControls(target) {
  target.querySelectorAll("[data-export-kind]").forEach(button => {
    button.addEventListener("click", event => {
      event.stopPropagation();
      exportCurrentScope(button.dataset.exportKind || "xlsx");
      button.closest("details")?.removeAttribute("open");
    });
  });
}
function bindTrialSelection(root) {
  root.querySelectorAll("tr[data-source-key]").forEach(node => {
    node.setAttribute("tabindex", "0");
    const open = event => {
      event.stopPropagation();
      selectServeDetail(node.dataset.sourceKey, {
        openSidebar: true,
        opener: node,
        openerSelector: `tr[data-source-key="${cssAttributeValue(node.dataset.sourceKey)}"]`,
      });
    };
    bindTableRowActivation(node, open);
  });
}
function cssAttributeValue(value) {
  return String(value ?? "").replaceAll("\\", "\\\\").replaceAll('"', '\\"');
}
function firstUserStepSelection(trialKey, view = state.view) {
  const index = listValue(view?.trajectory_meta).findIndex(meta => meta?.trial_key === trialKey);
  const step = listValue(view?.trajectory?.[index >= 0 ? index : 0]?.steps).find(item => {
    return lower(item?.source) === "user" && item?.step_id !== null && item?.step_id !== undefined;
  });
  return step ? { trialKey, stepId: String(step.step_id) } : null;
}
function xlsxTableRows(rows, columns) {
  return [
    columns.map(column => column.label),
    ...rows.map(row => columns.map(column => exportTableText(row, column)))
  ];
}
function exportTableText(row, column) {
  const raw = column.value(row);
  if (column.exportFormat) return column.exportFormat(raw, row);
  if (column.valueType === "datetime") return formatUtcDate(raw);
  return column.format ? column.format(raw, row) : (raw ?? "-");
}
function downloadBlob(filename, mime, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  try {
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
  } finally {
    link.remove();
    URL.revokeObjectURL(url);
  }
}
export {
  bindServeExportControls,
  bindTrialSelection,
  downloadBlob,
  firstUserStepSelection,
  xlsxTableRows,
};
