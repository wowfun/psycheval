import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom('<script type="application/json" id="peval-i18n">{}</script><script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin"}</script>');
const { taskColumns, flattenTaskRows, renderTaskTable, taskSearchText } = await import("../../src/psycheval/assets/web/modules/task-table.js");
const { taskSummary, renderTaskSummary } = await import("../../src/psycheval/assets/web/modules/task-summary.js");
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
  renderTaskSummary(root, [tasks[1], row("bad", { rule_count: 1, rubric_count: null, scoring_item_count: null })], { groupBy: "overall", open: true, onGroup() {}, onToggle() {}, onExport() {} });
  assert.match(root.querySelector('td[data-table-column-key="scoring_item_count"]').title, /2 Tasks/);
  assert.deepEqual(taskColumns({ scoring: true }).map(c => c.key), ["dataset", "task", "tags", "instruction", "rule_count", "rubric_count", "scoring_item_count"]);
  assert.deepEqual(taskColumns().map(c => c.key), ["dataset", "task", "package", "status", "diagnostics"]);
});

test("browser summary matches the shared export contract", () => {
  const fixture = JSON.parse(readFileSync(new URL("../../tests/fixtures/task_summary.json", import.meta.url), "utf8"));
  const rows = fixture.tasks.map((task, i) => ({ ...row(String(i), task), datasetId: task.dataset }));
  for (const grouping of ["overall", "dataset"]) assert.deepEqual(taskSummary(rows, grouping).map(({ key, ...values }) => ({ group: key, ...values })), fixture[grouping]);
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
