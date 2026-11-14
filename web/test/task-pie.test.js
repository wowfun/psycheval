import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom('<script type="application/json" id="peval-i18n">{}</script>');
const { summaryPieData, renderSummaryPieChart } = await import("../../src/psycheval/assets/web/modules/summary-pie.js");
const { summaryImageLayout } = await import("../../src/psycheval/assets/web/modules/summary-image.js");
const { createTaskSummaryState, renderTaskSummary } = await import("../../src/psycheval/assets/web/modules/task-summary.js");
test.after(() => browser.cleanup());
const metric = values => ({ definition: { key: "task_count", label: "Tasks" }, values: values.map((value, index) => ({ group: { key: index, label: `Group ${index}` }, value, formatted: value == null ? "Unknown" : String(value) })) });

test("pie percentages exclude unknown and zero values without losing their legend entries", () => {
  const pie = summaryPieData(metric([3, 1, 0, null]));
  assert.deepEqual(pie.values.map(item => item.percentage), ["75%", "25%", "0%", ""]);
  const root = document.createElement("div"); root.innerHTML = renderSummaryPieChart(metric([3, 1, 0, null]));
  assert.equal(root.querySelectorAll("svg path").length, 2);
  assert.equal(root.querySelectorAll("li").length, 4);
  assert.match(root.textContent, /Unknown/);
  assert.equal(summaryPieData(metric([0, null])).empty, true);
  assert.match(renderSummaryPieChart(metric([0, null])), /No positive values/);
  assert.ok(summaryPieData(metric([Number.MAX_VALUE, Number.MAX_VALUE])).values.every(item => item.share === .5));
  assert.equal(new Set(summaryPieData(metric(Array(20).fill(1))).values.map(item => item.color)).size, 20);
});

test("Task Summary pie uses current groups and metrics and keeps its selection through grouping changes", () => {
  const root = document.createElement("div"); document.body.append(root);
  const state = createTaskSummaryState();
  const rows = ["a", "b"].map(key => ({ key, kind: "task", datasetId: key, task: { tags: [key, "overlap"], rule_count: 0, rubric_count: null, scoring_item_count: null } }));
  const exports = [];
  const render = () => renderTaskSummary(root, rows, state, { onChange: render, onExport: kind => exports.push(kind) });
  render(); root.querySelector('[data-task-summary-chart="pie"]').click();
  const disclosure = root.querySelector("[data-task-summary-toggle]");
  assert.ok(root.querySelector(`#${disclosure.getAttribute("aria-controls")}`).hidden);
  assert.equal(state.chartType, "pie");
  assert.equal(root.querySelectorAll(".summary-pie").length, 4);
  assert.equal(root.querySelectorAll(".leaderboard-summary-bar").length, 0);
  root.querySelector('[data-summary-export="pie"]').click(); assert.deepEqual(exports, ["pie"]);
  root.querySelector('[data-task-summary-group="tags"]').click(); assert.equal(state.chartType, "pie");
  assert.match(root.textContent, /overlap/);
  const color = root.querySelector('[data-pie-group=\'"b"\'] i').style.background;
  state.groups = ["b"]; state.metrics = ["task_count"]; render();
  assert.equal(root.querySelectorAll(".summary-pie li").length, 1);
  assert.equal(root.querySelector(".summary-pie li i").style.background, color);
  assert.match(root.textContent, /100%/);
  state.groupBy = "overall"; render();
  assert.equal(root.querySelectorAll(".summary-pie").length, 0);
  assert.ok(root.querySelector('[data-summary-export="pie"]').disabled);
  root.remove();
});

test("pie export uses the same geometry and retains every selected label", () => {
  const snapshot = { title: "Task Summary", subtitle: "Tags", scope: "Overlapping tags", bars: [metric([3, 1, 0, null])] };
  const layout = summaryImageLayout("pie", snapshot, { measureText: text => ({ width: text.length * 7 }) });
  assert.equal(layout.commands.filter(item => item.type === "sector").length, 2);
  const text = layout.commands.flatMap(item => item.lines || []).join(" ");
  for (const label of ["Group 0", "Group 1", "Group 2", "Group 3", "Unknown", "75%", "25%"]) assert.ok(text.includes(label));
});
