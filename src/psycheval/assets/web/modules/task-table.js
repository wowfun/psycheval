import { esc, t } from "./shared.js";
import { applyDataTableControls, bindDataTableControls, bindTableRowActivation, renderDataTable } from "./data-tables.js";

const searchCache = new WeakMap();
const INSTRUCTION_EXCERPT_LENGTH = 240;

/** @param {{selection?: any, rename?: any, scoring?: boolean, flattened?: boolean, editRuleCount?: any, canEditRuleCount?: any}} options */
function taskColumns({ selection, rename, scoring = false, flattened = false, editRuleCount, canEditRuleCount } = {}) {
  const identity = [
    ...(selection ? [selection] : []),
    { key: "dataset", label: t("harbor_dataset", "Dataset"), valueType: "identity", sortable: true, filterable: true, value: row => row.datasetId },
    { key: "task", label: t("task", "Task"), valueType: "identity", sortable: true, filterable: true, value: row => row.taskName || "—", edit: rename },
  ];
  if (scoring) return [...identity,
    { key: "tags", label: t("tags", "Tags"), valueType: "list", filterable: true, value: row => row.task?.tags || [], filterValues: row => row.task?.tags || [], format: value => value.join(", ") },
    { key: "instruction", label: t("task_instruction", "Instruction"), valueType: "text", value: row => row.task?.instruction || "",
      format: value => value.length > INSTRUCTION_EXCERPT_LENGTH ? `${value.slice(0, INSTRUCTION_EXCERPT_LENGTH)}…` : value,
      fullText: () => "", cellAttrs: 'tabindex="0" data-task-instruction' },
    ...[["skill_count", "task_skills", "Skills"], ["input_file_count", "task_files", "Files"]].map(([key, label, fallback]) => ({ key, label: t(label, fallback), valueType: "number", sortable: true, value: row => row.task?.[key], format: value => value ?? "" })),
    { key: "has_prepare", label: t("task_prepare", "Prepare"), valueType: "status", sortable: true, filterable: true, value: row => row.task?.has_prepare == null ? "" : row.task.has_prepare ? t("yes", "Yes") : t("no", "No") },
    ...(flattened ? scoringItemColumns() : [
      { key: "rule_count", label: t("task_rules", "Rules"), description: t("task_rules_description", "Deterministic scoring rules"), valueType: "number", sortable: true, value: row => row.task?.rule_count, format: value => value ?? "", edit: editRuleCount,
        cellTitle: row => row.task?.rule_count_source === "manual" ? t("task_rules_manual", "Manually entered") : row.dataset?.format === "workbuddy.v1" ? (canEditRuleCount?.(row) ? t("task_rules_edit", "Double-click to enter a rule count") : t("task_rules_unknown", "Rule count unknown")) : t("task_rules_description", "Deterministic scoring rules") },
      { key: "rubric_count", label: t("task_rubrics", "Rubrics"), valueType: "number", sortable: true, value: row => row.task?.rubric_count, format: value => value ?? "" },
      { key: "scoring_item_count", label: t("task_scoring_items", "Scoring items"), valueType: "number", sortable: true, value: row => row.task?.scoring_item_count, format: value => value ?? "" },
    ]),
  ];
  return [...identity,
    { key: "package", label: t("harbor_package", "Package"), valueType: "identity", sortable: true, filterable: true, value: row => row.packageName || "—" },
    { key: "status", label: t("status", "Status"), valueType: "status", sortable: true, filterable: true,
      value: row => t(`harbor_status_${row.status}`, row.status),
      html: row => `<span class="harbor-status-rail ${esc(row.status)}">${esc(t(`harbor_status_${row.status}`, row.status))}</span>` },
    { key: "diagnostics", label: t("harbor_diagnostics", "Diagnostics"), valueType: "text", value: row => row.diagnostics || "—", fullText: row => row.diagnostics || "" },
  ];
}

function scoringItemColumns() {
  return [
    ["step", "task_scoring_step", "Step"], ["id", "task_scoring_id", "ID"],
    ["type", "task_scoring_type", "Type"], ["question", "task_scoring_question", "Question"],
    ["pass_criteria", "task_scoring_pass", "Pass criteria"], ["fail_criteria", "task_scoring_fail", "Fail criteria"],
    ["scope_limits", "task_scoring_scope", "Scope limits"], ["artifact_refs", "task_scoring_artifacts", "Artifact refs"],
  ].map(([key, label, fallback]) => ({ key, label: t(label, fallback), valueType: "text", sortable: ["step", "id", "type"].includes(key),
    value: row => row.scoringItem?.[key] ?? "", format: value => key === "type" && value ? t(`task_scoring_${value}`, value) : scoringText(value),
  }));
}

function scoringText(value) {
  if (Array.isArray(value)) return value.map(scoringText).join("\n");
  return value !== null && typeof value === "object" ? JSON.stringify(value) : String(value ?? "");
}

function taskRowIdentity(row) {
  const key = row.taskKey ?? row.key;
  if (typeof key !== "string" || !key) throw new TypeError("Task row identity is required");
  return key;
}

function flattenTaskRows(rows) {
  return rows.flatMap(row => {
    const taskKey = taskRowIdentity(row);
    return (row.task?.scoring_items?.length ? row.task.scoring_items : [null]).map(item => ({
      ...row, taskKey, key: item ? `${taskKey}|item:${encodeURIComponent(item.key)}` : taskKey, scoringItem: item,
    }));
  });
}

function taskSearchText(row) {
  const context = [row.datasetId, row.taskName, row.packageName, row.status, t(`harbor_status_${row.status}`, row.status), row.diagnostics].filter(Boolean).join(" ");
  const task = row.task;
  if (!task) return context.toLowerCase();
  const cached = searchCache.get(task);
  if (cached && cached.context === context && cached.instruction === task.instruction && cached.tags === task.tags) return cached.text;
  const text = [context, ...(task.tags || []), task.instruction].filter(Boolean).join(" ").toLowerCase();
  searchCache.set(task, { context, instruction: task.instruction, tags: task.tags, text });
  return text;
}

function renderTaskTable({ root, tableId, allRows, columns, search = "", selectedKey, onActivate, onChange, onSelectionChange, rowAttribute = "data-task-row", rows: suppliedRows = null }) {
  const rows = suppliedRows ?? applyDataTableControls(tableId, search ? allRows.filter(row => taskSearchText(row).includes(search.trim().toLowerCase())) : allRows, columns, allRows);
  root.innerHTML = renderDataTable({ tableId, columns, rows, rowKey: row => row.key,
    tableClass: "harbor-overview-table", shellClass: "harbor-overview-table-shell",
    rowClass: row => `harbor-overview-row status-${esc(row.status)} ${taskRowIdentity(row) === selectedKey ? "selected-row" : ""}`,
    rowAttrs: row => `${rowAttribute} tabindex="0" data-task-row-key="${esc(row.key)}" data-task-row-token="${encodeURIComponent(row.key)}"`,
    filterOptionsRows: allRows, emptyText: t("harbor_task_empty", "No Tasks"),
  });
  bindDataTableControls(root, { tableId, columns, rows, rowKey: row => row.key, onChange, onSelectionChange });
  const byKey = new Map(rows.map(row => [row.key, row]));
  for (const node of root.querySelectorAll(`[${rowAttribute}]`)) {
    const row = byKey.get(node.dataset.taskRowKey);
    bindTableRowActivation(node, event => onActivate(row, node, event.target.closest?.("[data-table-column-key]")?.dataset.tableColumnKey || null));
    const instruction = node.querySelector("[data-task-instruction]");
    if (instruction) {
      const reveal = () => { instruction.title = row.task?.instruction || ""; instruction.setAttribute("aria-description", instruction.title); };
      const conceal = () => { if (document.activeElement !== instruction && !instruction.matches(":hover")) { instruction.removeAttribute("title"); instruction.removeAttribute("aria-description"); } };
      instruction.addEventListener("pointerenter", reveal);
      instruction.addEventListener("focus", reveal);
      instruction.addEventListener("pointerleave", conceal);
      instruction.addEventListener("blur", conceal);
    }
  }
  return rows;
}

export { taskColumns, taskSearchText, taskRowIdentity, renderTaskTable, flattenTaskRows, scoringText };
