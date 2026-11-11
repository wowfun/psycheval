import { esc, t } from "./shared.js";
import { renderDataTable } from "./data-tables.js";
import { downloadBlob } from "./download.js";
import { reloadExpiredAdminSession } from "./http.js";

function taskSummary(rows, groupBy) {
  const groups = new Map();
  for (const row of rows.filter(row => row.kind === "task")) {
    const key = groupBy === "dataset" ? row.datasetId : "overall";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return [...groups].map(([key, tasks]) => {
    const totals = {};
    for (const field of ["rule_count", "rubric_count", "scoring_item_count"]) {
      totals[field] = tasks.some(row => row.task?.[field] == null) ? null : tasks.reduce((total, row) => total + row.task[field], 0);
    }
    return { key, task_count: tasks.length, ...totals,
      missing_rule_count: tasks.filter(row => row.task?.rule_count == null).length,
      missing_scoring_item_count: tasks.filter(row => row.task?.scoring_item_count == null).length,
      missing_rubric_count: tasks.filter(row => row.task?.rubric_count == null).length };
  });
}

function missingCountText(group, field) {
  const count = group[`missing_${field}`];
  return count ? t("task_summary_missing", "{count} Tasks have an unknown count").replace("{count}", String(count)) : "";
}

function renderTaskSummary(root, rows, { groupBy, open, onGroup, onToggle, onExport }) {
  if (!root) return;
  const groups = taskSummary(rows, groupBy);
  const columns = [
    { key: "group", label: groupBy === "dataset" ? t("harbor_dataset", "Dataset") : t("summary_group_by", "Group by"), valueType: "identity", value: row => groupBy === "dataset" ? row.key : t("summary_overall", "Overall") },
    { key: "task_count", label: t("tasks", "Tasks"), valueType: "number", value: row => row.task_count },
    ...[["rule_count", "task_rules", "Rules"], ["rubric_count", "task_rubrics", "Rubrics"], ["scoring_item_count", "task_scoring_items", "Scoring items"]].map(([key, label, fallback]) => ({
      key, label: t(label, fallback), valueType: "number", value: row => row[key], format: value => value ?? "",
      cellTitle: row => missingCountText(row, key),
    })),
  ];
  const missing = groups.filter(group => group.missing_rule_count || group.missing_rubric_count);
  root.innerHTML = `<header class="table-region-head"><h2>${esc(t("task_summary", "Task Summary"))}</h2><div class="table-region-actions">
    <div class="leaderboard-summary-segments" role="group" aria-label="${esc(t("summary_group_by", "Group by"))}">${[["overall", t("summary_overall", "Overall")], ["dataset", t("harbor_dataset", "Dataset")]].map(([key, label]) => `<button type="button" class="leaderboard-summary-segment${key === groupBy ? " active" : ""}" data-task-summary-group="${key}" aria-pressed="${key === groupBy}">${esc(label)}</button>`).join("")}</div>
    <button type="button" class="action-button" data-task-summary-export ${groups.length ? "" : "disabled"}>${esc(t("export_excel", "Export Excel"))}</button>
    <button type="button" class="action-button" data-task-summary-toggle aria-expanded="${open}">${esc(t(open ? "summary_hide_table" : "summary_show_table", open ? "Hide summary table" : "Show summary table"))}</button>
    </div></header>${open ? renderDataTable({ tableId: "task-summary", columns, rows: groups, rowKey: row => row.key, emptyText: t("harbor_task_empty", "No Tasks") }) : ""}
    ${missing.map(group => `<p class="copy task-summary-missing">${esc(groupBy === "dataset" ? `${group.key}: ` : "")}${esc(t("task_missing_rules", "Tasks without a rule count"))}: ${group.missing_rule_count}; ${esc(t("task_missing_rubrics", "Tasks without a rubric count"))}: ${group.missing_rubric_count}</p>`).join("")}`;
  root.querySelectorAll("[data-task-summary-group]").forEach(button => button.addEventListener("click", () => onGroup(button.dataset.taskSummaryGroup)));
  root.querySelector("[data-task-summary-toggle]").addEventListener("click", onToggle);
  root.querySelector("[data-task-summary-export]").addEventListener("click", onExport);
}

async function exportTasks({ kind, mode, rows, columns, groupBy = "overall" }) {
  // Download responses are binary; serveApi parses JSON response bodies.
  const response = await fetch("/api/harbor/task-exports", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, mode, group_by: groupBy, columns: columns.filter(column => !column.select).map(column => column.key),
      rows: rows.filter(row => row.kind === "task").map(row => ({ dataset_id: row.datasetId, task: row.taskName, item_key: row.scoringItem?.key || null })) }),
  });
  if (!response.ok) {
    reloadExpiredAdminSession(response);
    const problem = await response.json().catch(() => ({}));
    throw new Error(problem.detail || response.statusText);
  }
  const blob = await response.blob();
  const filename = response.headers.get("Content-Disposition")?.match(/filename="([^"]+)"/)?.[1] || `peval-task-${mode}.${kind}`;
  downloadBlob(filename, blob.type, blob);
}

export { taskSummary, renderTaskSummary, exportTasks };
