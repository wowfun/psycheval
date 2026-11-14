import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom('<script type="application/json" id="peval-i18n">{}</script><script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin"}</script>');
const { taskColumns, flattenTaskRows, renderTaskTable, taskSearchText } = await import("../../src/psycheval/assets/web/modules/task-table.js");
const { taskSummary, renderTaskSummary, createTaskSummaryState, taskSummaryExportColumns } = await import("../../src/psycheval/assets/web/modules/task-summary.js");
const { selectionColumn } = await import("../../src/psycheval/assets/web/modules/data-tables.js");
test.after(() => browser.cleanup());

function row(name, task) { return { key: name, kind: "task", datasetId: "office", taskName: name, task }; }
const tasks = [row("one", { tags: ["中文"], instruction: "Full long instruction", rule_count: 12, rubric_count: 2, scoring_item_count: 14, scoring_items: [{ key: "a", id: "a", type: "rubric" }, { key: "b", id: "b", type: "rubric" }] }), row("empty", { rule_count: null, rubric_count: 0, scoring_item_count: null, scoring_items: [] })];

test("flattening keeps placeholders and task selection identity without synthesizing manual rules", () => {
  const flat = flattenTaskRows(tasks), selected = new Set();
  assert.equal(flat.length, 3);
  assert.equal(flat[2].scoringItem, null);
  const columns = taskColumns({ scoring: true, flattened: true, selection: selectionColumn({ selectionKey: row => row.taskKey, selectionSet: () => selected }) });
  const root = document.createElement("div");
  document.body.append(root);
  renderTaskTable({ root, tableId: "scoring-test", allRows: flat, columns, onActivate() {}, onChange() {}, onSelectionChange() {} });
  root.querySelector('[data-table-row-select="one"]').click();
  assert.deepEqual([...selected], ["one"]);
  assert.equal(root.querySelectorAll('[data-table-row-select="one"]').length, 2);
  assert.equal(root.querySelectorAll('[data-table-column-key="rule_count"]').length, 0);
  const instruction = root.querySelector('[data-table-column-key="instruction"]');
  assert.equal(instruction.hasAttribute("title"), false);
  instruction.focus();
  assert.equal(instruction.title, "Full long instruction");
});

test("summary follows filtered tasks and counts disjoint unknowns accurately", () => {
  assert.equal(taskSummary(tasks.slice(0, 1), "overall")[0].scoring_item_count, 14);
  const result = taskSummary(tasks, "dataset")[0];
  assert.equal(result.task_count, 2); assert.equal(result.rule_count, null); assert.equal(result.rubric_count, 2);
  const root = document.createElement("div");
  renderTaskSummary(root, [tasks[1], row("bad", { rule_count: 1, rubric_count: null, scoring_item_count: null })], { ...createTaskSummaryState(), groupBy: "overall", open: true }, { onChange() {}, onExport() {} });
  assert.match(root.querySelector('td[data-table-column-key="scoring_item_count"]').title, /2 Tasks/);
  assert.deepEqual(taskColumns({ scoring: true }).map(c => c.key), ["dataset", "task", "tags", "instruction", "skill_count", "input_file_count", "has_prepare", "rule_count", "rubric_count", "scoring_item_count"]);
  assert.deepEqual(taskColumns().map(c => c.key), ["dataset", "task", "package", "status", "diagnostics"]);
});

test("browser summary matches the shared export contract", () => {
  const fixture = JSON.parse(readFileSync(new URL("../../tests/fixtures/task_summary.json", import.meta.url), "utf8"));
  const rows = fixture.tasks.map((task, i) => ({ ...row(String(i), task), datasetId: task.dataset }));
  for (const grouping of ["overall", "dataset", "category", "difficulty", "tags"]) assert.deepEqual(taskSummary(rows, grouping).map(({ key, ...values }) => ({ group: key, ...values })), fixture[grouping]);
});

test("Task identity survives flattening and keeps identically named Tasks in distinct Datasets", () => {
  const rows = ["a", "b"].map(datasetId => ({ ...tasks[0], datasetId, key: `dataset:${datasetId}|task:one` }));
  const flattened = flattenTaskRows(rows);
  flattened[1].taskName = "presentation-only-alias";
  assert.equal(taskSummary(flattened, "overall")[0].task_count, 2);
  assert.throws(() => taskSummary([{ kind: "task", task: tasks[0].task }], "overall"), /identity/i);
});

test("Task Summary shares group selection, metric ordering and empty states across views", () => {
  const root = document.createElement("section"); document.body.append(root);
  const state = createTaskSummaryState();
  const rows = [row("one", { tags: ["one", "two", "one"], category: "coding", difficulty: "hard", rule_count: 0, rubric_count: 0, scoring_item_count: 0 }), tasks[1]];
  const render = () => renderTaskSummary(root, rows, state, { onChange: render, onExport() {} });
  render();
  assert.equal(root.querySelectorAll("table").length, 0);
  assert.equal(root.querySelectorAll("[data-summary-chart]").length, 4);
  assert.equal(root.querySelectorAll(".leaderboard-summary-control > span").length, 0);
  root.querySelector('[data-task-summary-group="tags"]').click();
  assert.match(root.textContent, /group counts may overlap/);
  assert.equal(taskSummary([...rows, rows[0]], "tags")[0].task_count, 1);
  root.querySelector('[data-group-action="none"]').click();
  root.querySelector('[data-comparison-group="2"]').click();
  root.querySelector('[data-group-apply]').click();
  assert.deepEqual(state.groups, [null]);
  root.querySelector('[data-task-summary-toggle]').click();
  assert.equal(root.querySelector('td[data-table-column-key="group"]').textContent, "Unset");
  assert.equal(root.querySelector('td[data-table-column-key="rule_count"]').textContent, "Unknown");
  root.querySelector('[data-metric-action="none"]').click();
  root.querySelector('[data-metric-id="rubric_count"]').click();
  root.querySelector('[data-metric-id="task_count"]').click();
  root.querySelector('[data-metric-apply]').click();
  assert.deepEqual([...root.querySelectorAll('[data-summary-chart]')].map(node => node.dataset.summaryChart), ["rubric_count", "task_count"]);
  assert.deepEqual(taskSummaryExportColumns(state).map(column => column.key), ["group", "rubric_count", "task_count", "missing_rubric_count"]);
  root.querySelector('[data-group-action="none"]').click();
  root.querySelector('[data-group-apply]').click();
  assert.match(root.textContent, /Select at least one comparison group/);
  assert.ok([...root.querySelectorAll('[data-summary-export]')].every(button => button.disabled));
  root.querySelector('[data-task-summary-group="difficulty"]').click();
  assert.equal(state.groups, null);
  assert.deepEqual(state.metrics, ["rubric_count", "task_count"]);
  root.remove();
});

test("large instructions stay out of row HTML until hover or keyboard focus", () => {
  const instruction = "long instruction 中文 ".repeat(10000);
  const rows = Array.from({ length: 100 }, (_, i) => row(String(i), { instruction }));
  const root = document.createElement("div"); document.body.append(root);
  renderTaskTable({ root, tableId: "long-instructions", allRows: rows, columns: taskColumns({ scoring: true }), onActivate() {}, onChange() {} });
  assert.ok(root.innerHTML.length < 500000);
  const cell = root.querySelector("[data-task-instruction]");
  assert.equal(cell.hasAttribute("aria-label"), false);
  cell.focus(); assert.equal(cell.title, instruction);
  assert.equal(cell.getAttribute("aria-description"), instruction);
  assert.equal(taskSearchText(rows[0]), taskSearchText({ ...rows[0] }));
  rows[0].task.instruction = "Replacement needle";
  assert.ok(taskSearchText(rows[0]).includes("replacement needle"));
  root.remove();
});
