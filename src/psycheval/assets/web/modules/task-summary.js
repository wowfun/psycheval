import { radarColors } from "./summary-chart.js";
import { esc, fmtNum, t } from "./shared.js";
import { renderDataTable } from "./data-tables.js";
import { downloadBlob } from "./download.js";
import { reloadExpiredAdminSession } from "./http.js";
import { renderSummaryGroupControl, bindSummaryGroupControl } from "./summary-groups.js";
import { renderSummaryMetricControl, bindSummaryMetricControl } from "./summary-metrics.js";
import { comparisonGroups } from "./summary-chart.js";
import { renderSummarySegments, renderSummaryHeader, renderSummaryDisclosure, renderSummaryExportMenu, summaryBarData, renderSummaryBarChart } from "./summary-ui.js";
import { downloadSummaryImage } from "./summary-image.js";
import { bindToolbarMenus } from "./toolbar-menu.js";
import { renderSummaryPieChart } from "./summary-pie.js";
import { taskRowIdentity } from "./task-table.js";

const COUNT_FIELDS = ["rule_count", "rubric_count", "scoring_item_count"];
const METRICS = ["task_count", ...COUNT_FIELDS];
function createTaskSummaryState() {
  return { id: "task-summary", groupBy: "dataset", chartType: "bar", open: false, groups: null, groupDraft: null, groupSearch: "", metrics: [...METRICS], metricDraft: null, metricSearch: "", exporting: false };
}
function taskSummaryDefinitions() {
  return [["task_count", "tasks", "Tasks"], ["rule_count", "task_rules", "Rules"], ["rubric_count", "task_rubrics", "Rubrics"], ["scoring_item_count", "task_scoring_items", "Scoring items"]].map(([key, label, fallback]) => ({ key, label: t(label, fallback), default: true }));
}
function taskSummaryGroupings() {
  return [["overall", "summary_overall", "Overall"], ["dataset", "harbor_dataset", "Dataset"], ["category", "category", "Category"], ["difficulty", "task_difficulty", "Difficulty"], ["tags", "tags", "Tags"]].map(([key, label, fallback]) => ({ key, label: t(label, fallback) }));
}
function uniqueTasks(rows) {
  const seen = new Set();
  return rows.filter(row => {
    if (row.kind !== "task") return false;
    const key = taskRowIdentity(row);
    if (seen.has(key)) return false;
    seen.add(key); return true;
  });
}
function taskSummary(rows, groupBy) {
  const groups = new Map();
  for (const row of uniqueTasks(rows)) {
    let keys = groupBy === "overall" ? ["overall"] : groupBy === "dataset" ? [row.datasetId] : groupBy === "tags" ? [...new Set((row.task?.tags || []).filter(Boolean))] : [row.task?.[groupBy] ?? null];
    if (!keys.length) keys = [null];
    for (const key of keys) {
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(row);
    }
  }
  return [...groups].map(([key, tasks]) => {
    const totals = {}, missing = {};
    for (const field of COUNT_FIELDS) {
      missing[`missing_${field}`] = tasks.filter(row => row.task?.[field] == null).length;
      totals[field] = missing[`missing_${field}`] ? null : tasks.reduce((sum, row) => sum + row.task[field], 0);
    }
    return { key, task_count: tasks.length, ...totals, ...missing };
  });
}
function missingCountText(group, field) {
  const count = group[`missing_${field}`];
  return count ? t("task_summary_missing", "{count} Tasks have an unknown count").replace("{count}", String(count)) : "";
}
function summaryModel(rows, state) {
  const allGroups = taskSummary(rows, state.groupBy).map(group => ({ ...group, count: group.task_count,
    label: state.groupBy === "overall" ? t("summary_overall", "Overall") : group.key ?? t("task_group_unset", "Unset") }));
  const groups = comparisonGroups(allGroups, state.groups);
  const definitions = state.metrics.flatMap(key => taskSummaryDefinitions().filter(item => item.key === key));
  const palette = radarColors(allGroups.length);
  const colors = new Map(allGroups.map((group, index) => [group.key, palette[index]]));
  const bars = definitions.map(definition => summaryBarData(definition, groups.map(group => ({ group, color: colors.get(group.key),
    row: { count: group.task_count }, value: group[definition.key], hint: missingCountText(group, definition.key), valueHint: missingCountText(group, definition.key),
  })), value => value == null ? t("task_count_unknown", "Unknown") : fmtNum(value)));
  return { allGroups, groups, definitions, bars };
}
function taskSummaryScope(rows, state) {
  const scope = t("task_summary_scope", "{count} matching Tasks.").replace("{count}", fmtNum(uniqueTasks(rows).length));
  return scope + (state.groupBy === "tags" ? ` ${t("task_summary_tag_overlap", "A Task can belong to multiple tags; group counts may overlap.")}` : "");
}
function taskSummaryExportColumns(state) {
  return ["group", ...state.metrics, ...state.metrics.filter(key => COUNT_FIELDS.includes(key)).map(key => `missing_${key}`)].map(key => ({ key }));
}
function renderTaskSummary(root, rows, state, { onChange, onExport }) {
  if (!root) return;
  const { allGroups, groups, definitions, bars } = summaryModel(rows, state);
  const groupLabel = taskSummaryGroupings().find(item => item.key === state.groupBy).label;
  const overall = taskSummary(rows, "overall")[0] || {};
  const options = { definitions: taskSummaryDefinitions(), defaults: METRICS, hint: key => missingCountText(overall, key) };
  const disabledReason = kind => !groups.length ? t("summary_group_select", "Select at least one comparison group.") : !definitions.length ? t("metric_select", "Select at least one available metric with data.") : ["bar", "pie"].includes(kind) && state.groupBy === "overall" ? t("summary_export_group_required", "Select a grouping to export charts.") : state.exporting ? t("summary_export_generating", "Generating image…") : "";
  const actions = renderSummarySegments(t("summary_group_by", "Group by"), taskSummaryGroupings(), state.groupBy, "data-task-summary-group")
    + renderSummarySegments(t("summary_chart_type", "Chart"), [{ key: "bar", label: t("summary_bar", "Bar chart") }, { key: "pie", label: t("summary_pie", "Pie chart") }], state.chartType, "data-task-summary-chart")
    + renderSummaryGroupControl(state, allGroups) + renderSummaryMetricControl(state, options)
    + renderSummaryExportMenu({ id: state.id, kinds: [{ key: "xlsx", label: t("export_excel", "Export Excel") }, { key: "bar", label: t("summary_export_bar", "Bar chart (.png)") }, { key: "pie", label: t("summary_export_pie", "Pie chart (.png)") }], disabledReason });
  const columns = [{ key: "group", label: groupLabel, valueType: "identity", value: row => row.label }, ...definitions.map(definition => ({ ...definition, numeric: true, valueType: "number", value: row => row[definition.key], format: value => value == null ? t("task_count_unknown", "Unknown") : fmtNum(value), cellTitle: row => missingCountText(row, definition.key) }))];
  const empty = !allGroups.length ? t("harbor_task_empty", "No Tasks") : !groups.length ? t("summary_group_select", "Select at least one comparison group.") : !definitions.length ? t("metric_select", "Select at least one available metric with data.") : "";
  root.innerHTML = renderSummaryHeader({ id: state.id, title: t("task_summary", "Task Summary"), scope: taskSummaryScope(rows, state), actions })
    + (empty ? `<p class="leaderboard-summary-empty">${esc(empty)}</p>` : renderSummaryDisclosure({ id: "task-summary-table-region", open: state.open, summary: `${definitions.length} ${t("summary_metrics", "metrics")} · ${groups.length} ${groupLabel}`, attribute: "data-task-summary-toggle", table: state.open ? renderDataTable({ tableId: "task-summary", columns, rows: groups, rowKey: row => JSON.stringify(row.key) }) : "" })
      + (state.groupBy === "overall" ? "" : `<section class="leaderboard-summary-chart-panel" aria-label="${esc(state.chartType === "pie" ? t("summary_pie", "Pie chart") : t("summary_bar", "Bar chart"))}"><div class="leaderboard-summary-chart-head"><div><h3>${esc(groupLabel)}</h3><p>${esc(state.chartType === "pie" ? t("summary_pie_note", "Each pie shows selected groups’ shares of known positive totals. Unknown values have no slice.") : t("summary_scale_note", "Each metric has its own scale. Compare bars only within a metric."))}</p></div></div><div class="leaderboard-summary-chart-grid">${bars.map(bar => state.chartType === "pie" ? renderSummaryPieChart(bar) : renderSummaryBarChart(bar, t("task_summary_total", "Total"))).join("")}</div></section>`));
  const change = selector => { onChange(); if (selector) root.querySelector(selector)?.focus({ preventScroll: true }); };
  bindSummaryGroupControl(root, state, allGroups, onChange);
  bindSummaryMetricControl(root, state, onChange, options);
  bindToolbarMenus(root);
  root.querySelectorAll("[data-task-summary-group]").forEach(button => button.addEventListener("click", () => {
    state.groupBy = button.dataset.taskSummaryGroup; state.groups = null; state.groupDraft = null; state.groupSearch = "";
    change(`[data-task-summary-group="${state.groupBy}"]`);
  }));
  root.querySelectorAll("[data-task-summary-chart]").forEach(button => button.addEventListener("click", () => { state.chartType = button.dataset.taskSummaryChart; change(`[data-task-summary-chart="${state.chartType}"]`); }));
  root.querySelector("[data-task-summary-toggle]")?.addEventListener("click", () => { state.open = !state.open; change("[data-task-summary-toggle]"); });
  const menu = root.querySelector(".leaderboard-summary-export");
  root.querySelectorAll("[data-summary-export]").forEach(button => button.addEventListener("click", () => {
    if (disabledReason(button.dataset.summaryExport)) return;
    menu.open = false; menu.querySelector("summary").focus({ preventScroll: true }); onExport(button.dataset.summaryExport);
  }));
}
async function exportTaskSummaryImage(rows, state, kind = state.chartType || "bar") {
  const snapshot = structuredClone({ title: t("task_summary", "Task Summary"), subtitle: taskSummaryGroupings().find(item => item.key === state.groupBy).label,
    scope: taskSummaryScope(rows, state), bars: summaryModel(rows, state).bars });
  await downloadSummaryImage(kind, snapshot, `peval-task-summary-${kind}.png`);
}
async function exportTasks({ kind, mode, rows, columns, groupBy = "overall", groups = null }) {
  const response = await fetch("/api/harbor/task-exports", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, mode, group_by: groupBy, comparison_groups: groups, columns: columns.filter(column => !column.select).map(column => column.key),
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
export { createTaskSummaryState, taskSummary, renderTaskSummary, exportTasks, exportTaskSummaryImage, taskSummaryExportColumns };
