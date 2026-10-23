import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";
import { encodeWorkspaceLocation, decodeWorkspaceLocation, HOME_QUERY } from "../../src/psycheval/assets/web/app/workspace-location.js";
import { normalizeColumnLayout } from "../../src/psycheval/assets/web/modules/leaderboard-columns.js";

const browser = installBrowserDom('<script id="peval-render-options" type="application/json">{}</script><section id="leaderboard-summary"></section>');
const { state } = await import("../../src/psycheval/assets/web/modules/runtime.js");
const summary = await import("../../src/psycheval/assets/web/modules/leaderboard-summary.js");
const { selectedMetricDefinitions } = await import("../../src/psycheval/assets/web/modules/metric-presentation.js");
const { radarContext } = await import("../../src/psycheval/assets/web/modules/leaderboard-radar.js");
const base = JSON.parse(readFileSync(new URL("./support/metrics.json", import.meta.url), "utf8"));
const extra = { key: "atif.extra:Energy", column_key: "atif.extra:Energy", label: "长中文能耗指标", unit: "Wh", type: "number", direction: "neutral", default: false };
function reset() {
  state.catalogQuery = { ...structuredClone(HOME_QUERY), views: [] };
  state.catalogPage = { total: 2, generation: 1, metric_descriptions: [...base, extra] };
  state.leaderboardSummaryMetrics = null; state.leaderboardMetricDraft = null; state.leaderboardMetricSearch = "";
  state.leaderboardSummaryGroupBy = "model"; state.leaderboardSummaryChartType = "bar";
  state.leaderboardSummaryLoading = false; state.leaderboardSummaryError = "";
  state.leaderboardSummary = { generation: 1, summary: { matched_count: 2, groups: [
    { key: "a", label: "A", count: 1, metrics: [{ key: "score", count: 1, mean: 0 }, { key: extra.key, count: 1, mean: 0 }] },
    { key: "b", label: "B", count: 1, metrics: [{ key: "score", count: 1, mean: 1 }, { key: extra.key, count: 0, mean: null }] },
  ] } };
  summary.renderLeaderboardSummary();
}
test.after(() => browser.cleanup());

test("one ordered selection controls bars, radar direction and export snapshots without fetching", () => {
  reset();
  globalThis.fetch = () => { throw new Error("presentation must not fetch"); };
  assert.equal(document.querySelectorAll("[data-metric-id]:checked").length, 10);
  assert.equal(document.querySelector(`[data-summary-chart="${extra.key}"]`), null);
  document.querySelector(`[data-metric-id="${extra.key}"]`).click();
  document.querySelector("[data-metric-apply]").click();
  assert.ok(document.querySelector(`[data-summary-chart="${extra.key}"]`));
  const snapshot = summary.leaderboardSummaryImageSnapshot();
  const values = snapshot.bars.find(item => item.definition.key === extra.key).values;
  assert.equal(values[0].formatted, "0 Wh"); assert.equal(values[1].value, null);
  assert.equal(snapshot.radar.axes.some(item => item.key === extra.key), false);
  state.catalogPage.metric_descriptions = [...base, { ...extra, direction: "lower" }];
  const radar = radarContext(state.leaderboardSummary.summary.groups, selectedMetricDefinitions(state), { value: row => row?.mean }, summary.leaderboardSummaryValue);
  assert.equal(radar.axes.find(item => item.key === extra.key).direction, -1);
  document.querySelector('[data-metric-action="none"]').click();
  document.querySelector("[data-metric-apply]").click();
  assert.deepEqual(state.leaderboardSummaryMetrics, []);
  assert.equal(document.querySelector('[data-summary-export="xlsx"]').disabled, true);
});

test("search does not narrow select-all and limits do not commit partial selections", () => {
  reset();
  state.catalogPage.metric_descriptions = [...base, ...Array.from({ length: 40 }, (_, i) => ({ ...extra, key: `reward:k${i}` }))];
  summary.renderLeaderboardSummary();
  const search = document.querySelector("[data-metric-search]"); search.value = "score"; search.dispatchEvent(new Event("input"));
  document.querySelector('[data-metric-action="all"]').click();
  assert.match(document.querySelector("[data-metric-error]").textContent, /32/);
  assert.equal(state.leaderboardSummaryMetrics, null);
  assert.equal(document.querySelectorAll("[data-metric-id]:checked").length, 10);
  state.catalogQuery.search = "中".repeat(20000);
  document.querySelector('[data-metric-action="none"]').click();
  const href = window.location.href;
  document.querySelector("[data-metric-apply]").click();
  assert.equal(state.leaderboardSummaryMetrics, null);
  assert.equal(window.location.href, href);
  assert.match(document.querySelector("[data-metric-error]").textContent, /link.*large/);
});

test("registry churn keeps metric choices and column preferences", () => {
  reset(); state.leaderboardSummaryMetrics = [extra.key];
  state.catalogPage.metric_descriptions = base;
  summary.renderLeaderboardSummary();
  assert.match(document.querySelector(".summary-metric-control").textContent, /Currently unavailable/);
  let layout = normalizeColumnLayout([extra.key, "reward"], { order: [extra.key, "reward"], visibility: { [extra.key]: "show" } });
  layout = normalizeColumnLayout(["reward"], layout);
  layout = normalizeColumnLayout(["reward", extra.key], layout);
  assert.deepEqual(layout.order, [extra.key, "reward"]); assert.equal(layout.visibility[extra.key], "show");
  state.catalogPage.metric_descriptions = [...base, extra]; summary.renderLeaderboardSummary();
  assert.ok(document.querySelector(`[data-summary-chart="${extra.key}"]`));
});

test("v2 links preserve unknown metric IDs, order, small selections and long Unicode IDs", () => {
  const id = "reward:" + encodeURIComponent("中文".repeat(20));
  const metrics = [id, "atif.extra:Case", "atif.extra:case"];
  const href = encodeWorkspaceLocation("home", { state: { query: { sort: `metric:${id}` }, summary: { metrics } } }, "http://localhost");
  const restored = decodeWorkspaceLocation("home", new URL(href));
  assert.deepEqual(restored.state.summary.metrics, metrics);
  assert.equal(restored.state.query.sort, `metric:${id}`);
  for (const metrics of [[], ["score"], ["score", "tokens"]]) assert.doesNotThrow(() => encodeWorkspaceLocation("home", { state: { summary: { metrics } } }));
  assert.throws(() => encodeWorkspaceLocation("home", { state: { summary: { metrics: Array.from({ length: 33 }, (_, i) => `reward:k${i}`) } } }));
  assert.throws(() => decodeWorkspaceLocation("home", new URL("http://localhost/#view=" + btoa('{"v":1}'))));
});

test("zero to two directional axes show an explanation and disable radar export", () => {
  reset(); state.leaderboardSummaryChartType = "radar";
  for (const metrics of [[], ["score"], ["score", "duration_ms"]]) {
    state.leaderboardSummaryMetrics = metrics; summary.renderLeaderboardSummary();
    assert.equal(document.querySelector("[data-summary-radar]"), null);
    assert.equal(document.querySelector('[data-summary-export="radar"]').disabled, true);
    assert.match(document.querySelector("#leaderboard-summary").textContent, /at least three/);
  }
  document.querySelector('[data-metric-action="default"]').click();
  document.querySelector("[data-metric-apply]").click();
  assert.equal(state.leaderboardSummaryMetrics.length, 10);
  assert.ok(state.leaderboardSummaryMetrics.includes("model_duration_ms"));
});

test("bar widths share a signed scale and preserve a true zero", () => {
  reset(); state.leaderboardSummaryMetrics = [extra.key];
  state.leaderboardSummary.summary.groups[0].metrics[1].mean = -3;
  state.leaderboardSummary.summary.groups[1].metrics[1] = { key: extra.key, count: 1, mean: 9 };
  const values = summary.leaderboardSummaryImageSnapshot().bars[0].values;
  assert.deepEqual(values.map(({ start, width, zero }) => ({ start, width, zero })), [{ start: 0, width: 25, zero: 25 }, { start: 25, width: 75, zero: 25 }]);
});

test("closing a metric draft restores checkboxes before reopening", () => {
  reset();
  const menu = document.querySelector(".summary-metric-control");
  menu.open = true; menu.dispatchEvent(new Event("toggle"));
  document.querySelector(`[data-metric-id="${extra.key}"]`).click();
  menu.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  menu.dispatchEvent(new Event("toggle"));
  menu.open = true; menu.dispatchEvent(new Event("toggle"));
  assert.equal(document.querySelector(`[data-metric-id="${extra.key}"]`).checked, false);
  assert.equal(document.querySelectorAll("[data-metric-id]:checked").length, 10);
  assert.equal(state.leaderboardSummaryMetrics, null);
});

test("metric reordering is a searchable draft and exports follow the applied order", () => {
  reset(); state.leaderboardSummaryMetrics = ["score", extra.key]; summary.renderLeaderboardSummary();
  const search = document.querySelector("[data-metric-search]");
  search.value = "长中文"; search.dispatchEvent(new Event("input"));
  document.querySelector(`[data-metric-row="${extra.key}"] [data-metric-move="-1"]`).click();
  assert.deepEqual(state.leaderboardSummaryMetrics, ["score", extra.key]);
  assert.deepEqual(state.leaderboardMetricDraft, [extra.key, "score"]);
  assert.equal(search.value, "长中文");
  assert.equal(document.querySelectorAll("[data-metric-row]:not([hidden])").length, 1);
  document.querySelector("[data-metric-apply]").click();
  assert.deepEqual(summary.leaderboardSummaryImageSnapshot().bars.map(item => item.definition.key), [extra.key, "score"]);
  document.querySelector('[data-metric-action="none"]').click(); document.querySelector("[data-metric-apply]").click();
  assert.equal(document.querySelector("#summary-export-help").hidden, false);
  assert.match(document.querySelector("#summary-export-help").textContent, /available metric with data/);
});
