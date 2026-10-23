import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom('<script id="peval-i18n" type="application/json">{}</script><script id="peval-render-options" type="application/json">{"mode":"serve","role":"admin"}</script>');
const { state } = await import("../../src/psycheval/assets/web/modules/runtime.js");
const summary = await import("../../src/psycheval/assets/web/modules/leaderboard-summary.js");
const images = await import("../../src/psycheval/assets/web/modules/leaderboard-summary-export.js");
const { downloadBlob } = await import("../../src/psycheval/assets/web/modules/export.js");
test.after(() => browser.cleanup());

const tick = () => new Promise(resolve => setImmediate(resolve));
function setup() {
  document.body.insertAdjacentHTML("beforeend", '<section id="leaderboard-summary"></section>');
  Object.assign(state, {
    catalogPage: { total: 9, generation: 7 },
    catalogQuery: { state: "active", page: 2, page_size: 2, search: "fixture", categories: ["office"] },
    workspaceViews: [], workspaceAppliedViewNames: new Set(),
    leaderboardSummaryLoading: false, leaderboardSummaryError: null,
    leaderboardSummaryGroupBy: "model", leaderboardSummaryChartType: "bar", leaderboardSummaryStatistic: "mean",
    leaderboardSummaryTableOpen: false, leaderboardSummaryRadarGroups: null,
    leaderboardSummaryMetrics: ["score", "duration_ms", "tps"], leaderboardSummaryRadarSearch: "",
    leaderboardSummary: { generation: 7, checking: false, summary: { matched_count: 9, groups: Array.from({ length: 6 }, (_, i) => ({
      key: `g${i}`, label: i === 0 ? "长中文模型名称".repeat(15) : `model-${i}`, count: i + 1,
      metrics: [
        { key: "score", type: "number", count: 1, mean: i, distribution: { p95: i + 10 } },
        { key: "duration_ms", type: "duration", count: 1, mean: (6 - i) * 1000, distribution: { p95: (6 - i) * 2000 } },
        { key: "tps", type: "number", count: i === 0 ? 0 : 1, mean: i === 0 ? null : 20, distribution: { p95: i === 0 ? null : 30 } },
        { key: "tokens", type: "number", count: 0 },
      ],
    })) } },
  });
  return document.querySelector("#leaderboard-summary");
}
const measure = { measureText: text => ({ width: [...text].length * 8 }) };

test("image layouts retain every group, current statistic, missing values, and complete radar legend", () => {
  const target = setup();
  try {
    state.leaderboardSummaryStatistic = "p95";
    state.leaderboardSummaryRadarGroups = ["g0", "g2", "g3", "g4", "g5"];
    state.leaderboardSummaryRadarSearch = "model-2";
    const snapshot = summary.leaderboardSummaryImageSnapshot();
    assert.equal(snapshot.subtitle, "P95 · Model");
    assert.match(snapshot.scope, /9 matching/);
    assert.deepEqual(snapshot.bars.map(bar => bar.definition.key), ["score", "duration_ms", "tps"]);
    assert.equal(snapshot.bars[0].values.length, 6);
    assert.equal(snapshot.bars[0].values[0].value, 10);
    assert.equal(snapshot.bars[2].values[0].value, null);
    assert.equal(snapshot.bars[2].values[0].formatted, "-");
    const bar = images.summaryImageLayout("bar", snapshot, measure);
    const radar = images.summaryImageLayout("radar", snapshot, measure);
    const text = layout => layout.commands.filter(command => command.type === "text").map(command => command.lines.join("")).join("\n");
    assert.match(text(bar), /- = No data/);
    for (const group of state.leaderboardSummary.summary.groups) assert.ok(text(bar).includes(group.label));
    assert.ok(bar.commands.some(command => command.x > bar.width / 2));
    assert.equal(snapshot.radar.series.length, 5);
    for (const item of snapshot.radar.series) {
      assert.ok(text(radar).includes(item.group.label));
      assert.ok(radar.commands.some(command => command.type === "rect" && command.color === item.color));
    }
    assert.match(text(radar), /No data: Decode TPS/);
    assert.match(text(radar), /No group difference/);
    state.leaderboardSummary.summary.groups[0].label = "Changed after click";
    assert.ok(!text(bar).includes("Changed after click"));
    state.leaderboardSummaryStatistic = "mean";
    assert.equal(summary.leaderboardSummaryImageSnapshot().bars[0].values[0].value, 0);
  } finally { target.remove(); }
});

test("export menu updates availability with presentation and closes with Escape", () => {
  const target = setup();
  try {
    const button = kind => target.querySelector(`[data-summary-export=${kind}]`);
    summary.renderLeaderboardSummary();
    assert.equal(target.querySelectorAll("[data-summary-export]").length, 3);
    for (const kind of ["xlsx", "bar", "radar"]) assert.equal(button(kind).disabled, false);
    state.leaderboardSummaryRadarGroups = [];
    summary.setLeaderboardSummaryStatistic("p95");
    assert.equal(button("radar").disabled, true);
    assert.equal(button("bar").disabled, false);
    assert.match(target.querySelector("#summary-export-help").textContent, /Select up to five/);
    state.leaderboardSummaryGroupBy = "overall";
    summary.renderLeaderboardSummary();
    assert.equal(button("xlsx").disabled, false);
    assert.equal(button("bar").disabled, true);
    assert.match(target.querySelector("#summary-export-help").textContent, /Select a grouping/);
    for (const property of ["leaderboardSummaryLoading", "leaderboardSummaryError"]) {
      state.leaderboardSummaryGroupBy = "model";
      state[property] = true;
      summary.renderLeaderboardSummary();
      assert.equal(button("bar").disabled, true);
      state[property] = false;
    }
    state.leaderboardSummary.checking = true;
    summary.renderLeaderboardSummary();
    assert.equal(button("bar").disabled, true);
    state.leaderboardSummary.checking = false;
    state.leaderboardSummary.summary.matched_count = 0;
    state.catalogPage.total = 0;
    summary.renderLeaderboardSummary();
    for (const kind of ["xlsx", "bar", "radar"]) assert.equal(button(kind).disabled, true);
    const menu = target.querySelector("details"); menu.open = true;
    menu.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    assert.equal(menu.open, false);
    assert.equal(document.activeElement, menu.querySelector("summary"));
  } finally { target.remove(); }
});

test("Excel menu keeps the complete-query summary export request", async () => {
  const target = setup();
  const previous = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (_path, options) => {
    requests.push(JSON.parse(options.body));
    return { ok: false, json: async () => ({ detail: "fixture" }) };
  };
  try {
    summary.renderLeaderboardSummary();
    target.querySelector("[data-summary-export=xlsx]").click();
    await tick();
    assert.equal(requests.length, 1);
    assert.equal(requests[0].kind, "summary_xlsx");
    assert.equal(requests[0].summary.group_by, "model");
    assert.equal(requests[0].summary.statistic, "mean");
    assert.equal(requests[0].summary.query.search, "fixture");
    assert.deepEqual(requests[0].summary.query.categories, ["office"]);
    assert.equal(requests[0].summary.query.page, undefined);
    assert.equal(requests[0].summary.query.page_size, undefined);
  } finally { globalThis.fetch = previous; target.remove(); }
});

function canvasMock() {
  const prototype = window.HTMLCanvasElement.prototype;
  const previous = { getContext: prototype.getContext, toBlob: prototype.toBlob };
  const canvases = [], charts = [];
  const context = { ...measure, scale() {}, fillRect() {}, fillText() {}, drawImage() {} };
  prototype.getContext = function () { canvases.push(this); return context; };
  prototype.toBlob = function (callback) { callback(new Blob(["png"], { type: "image/png" })); };
  window.echarts = { init: host => {
    const chart = { host, disposed: false, setOption(option) { this.option = option; }, renderToCanvas() { const canvas = document.createElement("canvas"); canvases.push(canvas); return canvas; }, dispose() { this.disposed = true; } };
    charts.push(chart); return chart;
  } };
  return { canvases, charts, restore() { Object.assign(prototype, previous); delete window.echarts; } };
}

test("offscreen radar uses current selection without fetching or replacing the page chart, and releases resources", async () => {
  const target = setup(), mock = canvasMock();
  const previousFetch = globalThis.fetch;
  globalThis.fetch = () => { throw new Error("Image export must not fetch"); };
  try {
    summary.renderLeaderboardSummary();
    summary.setLeaderboardSummaryStatistic("p95");
    const href = window.location.href;
    const chartType = state.leaderboardSummaryChartType;
    const snapshot = summary.leaderboardSummaryImageSnapshot();
    const blob = await images.summaryImageBlob("radar", snapshot);
    assert.equal(blob.type, "image/png");
    assert.equal(mock.charts.length, 1);
    assert.equal(mock.charts[0].option.series.length, 5);
    assert.equal(mock.charts[0].option.series[0].lineStyle.color, snapshot.radar.series[0].color);
    assert.equal(mock.charts[0].disposed, true);
    assert.equal(mock.charts[0].host.isConnected, false);
    assert.equal(state.leaderboardSummaryChartType, chartType);
    assert.equal(window.location.href, href);
    assert.ok(mock.canvases.every(canvas => canvas.width === 0 && canvas.height === 0));
    window.HTMLCanvasElement.prototype.toBlob = callback => callback(null);
    await assert.rejects(images.summaryImageBlob("radar", snapshot), /Image rendering is unavailable/);
    assert.ok(mock.charts.every(chart => chart.disposed));
    assert.ok(mock.canvases.every(canvas => canvas.width === 0));
  } finally { globalThis.fetch = previousFetch; mock.restore(); target.remove(); }
});

test("oversized images fail without truncation, and failed exports restore the menu", async () => {
  const target = setup(), mock = canvasMock();
  try {
    const snapshot = summary.leaderboardSummaryImageSnapshot();
    snapshot.bars[0].values = Array.from({ length: 1000 }, () => snapshot.bars[0].values[0]);
    await assert.rejects(images.summaryImageBlob("bar", snapshot), /image is too large/);
    assert.ok(mock.canvases.every(canvas => canvas.width === 0));
    window.HTMLCanvasElement.prototype.toBlob = () => { throw new Error("Encoding failed"); };
    summary.renderLeaderboardSummary();
    target.querySelector("[data-summary-export=bar]").click();
    assert.equal(target.querySelector("[data-summary-export=bar]").disabled, true);
    await tick();
    assert.equal(target.querySelector("[data-summary-export=bar]").disabled, false);
    assert.match(target.querySelector(".action-feedback").textContent, /Could not export.*Encoding failed/);
    assert.ok(mock.canvases.every(canvas => canvas.width === 0));
  } finally { mock.restore(); target.remove(); }
});

test("download failure still revokes its object URL and removes the temporary link", () => {
  const previous = { create: URL.createObjectURL, revoke: URL.revokeObjectURL, click: window.HTMLAnchorElement.prototype.click };
  const revoked = [];
  URL.createObjectURL = () => "blob:fixture";
  URL.revokeObjectURL = url => revoked.push(url);
  window.HTMLAnchorElement.prototype.click = () => { throw new Error("Download failed"); };
  try {
    assert.throws(() => downloadBlob("test.png", "image/png", new Blob()), /Download failed/);
    assert.deepEqual(revoked, ["blob:fixture"]);
    assert.equal(document.querySelector("a[download]"), null);
  } finally {
    URL.createObjectURL = previous.create; URL.revokeObjectURL = previous.revoke;
    window.HTMLAnchorElement.prototype.click = previous.click;
  }
});
