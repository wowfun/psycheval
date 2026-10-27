import assert from "node:assert/strict";
import test from "node:test";
import { SUMMARY_DEFAULTS } from "../../src/psycheval/assets/web/app/workspace-view-contract.js";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin","sources":[]}</script>
`);

const runtime = await import("../../src/psycheval/assets/web/modules/runtime.js");
const catalog = await import("../../src/psycheval/assets/web/modules/serve-catalog.js");
const summaryUi = await import("../../src/psycheval/assets/web/modules/leaderboard-summary.js");
const radarUi = await import("../../src/psycheval/assets/web/modules/leaderboard-radar.js");

test.after(() => browser.cleanup());

function response(payload, { ok = true, status = 200 } = {}) {
  return {
    ok,
    status,
    statusText: ok ? "OK" : "Error",
    text: async () => JSON.stringify(payload),
  };
}

function envelope(generation, matchedCount, label = "overall") {
  return {
    generation,
    checking: false,
    stale: false,
    summary: {
      name: "Leaderboard Summary",
      group_by: runtime.state.leaderboardSummaryGroupBy,
      matched_count: matchedCount,
      groups: [{ key: label, label, count: matchedCount, metrics: [] }],
    },
  };
}

function resetSummaryState() {
  runtime.state.catalogPage = {
    generation: 7,
    total: 125,
    page: 1,
    page_size: 100,
    checking: false,
  };
  runtime.state.catalogQuery = {
    state: "active",
    page: 1,
    page_size: 100,
    search: "",
    sort: "last_turn_end",
    direction: "desc",
    categories: ["b", "a"],
    tags: [],
    agents: [],
    models: [],
    tasks: [],
    jobs: [],
    providers: [],
    datasets: [],
    results: [],
    views: [],
  };
  runtime.state.workspaceViews = [];
  runtime.state.workspaceAppliedViewNames = new Set();
  runtime.state.leaderboardSummaryGroupBy = "overall";
  runtime.state.leaderboardSummaryStatistic = SUMMARY_DEFAULTS.statistic;
  runtime.state.leaderboardSummaryChartType = SUMMARY_DEFAULTS.chart_type;
  runtime.state.leaderboardSummaryRadarGroups = SUMMARY_DEFAULTS.radar_groups;
  runtime.state.leaderboardSummaryMetrics = null;
  runtime.state.leaderboardSummaryRadarSearch = "";
  runtime.state.leaderboardSummaryTableOpen = SUMMARY_DEFAULTS.table_open;
  runtime.state.leaderboardSummary = null;
  runtime.state.leaderboardSummaryLoading = false;
  runtime.state.leaderboardSummaryError = null;
  runtime.state.leaderboardSummaryScopeKey = null;
  runtime.state.leaderboardSummaryRequestKey = null;
  runtime.state.leaderboardSummaryRequestVersion += 1;
  runtime.state.leaderboardSummaryRequestPromise = null;
  runtime.state.leaderboardSummaryCache.clear();
}

test("descriptor changes refresh cached statistics without a new summary request", async () => {
  resetSummaryState();
  const previousFetch = globalThis.fetch;
  const first = { key: "atif.extra:energy", label: "Old", unit: "Wh", direction: "neutral" };
  runtime.state.catalogPage.metric_descriptions = [first];
  runtime.state.catalogPage.metric_revision = "one";
  globalThis.fetch = async () => response({ ...envelope(7, 125), metric_descriptions: [first], metric_revision: "one" });
  try {
    await catalog.loadLeaderboardSummary();
    const statistics = runtime.state.leaderboardSummary.summary;
    runtime.state.catalogPage.metric_descriptions = [{ ...first, label: "New", direction: "lower" }];
    runtime.state.catalogPage.metric_revision = "two";
    runtime.state.leaderboardSummaryMetrics = [first.key];
    globalThis.fetch = () => { throw new Error("must reuse numeric cache"); };
    await catalog.loadLeaderboardSummary();
    assert.equal(runtime.state.leaderboardSummary.summary, statistics);
    assert.equal(runtime.state.leaderboardSummary.metric_descriptions[0].label, "New");
    assert.equal(runtime.state.leaderboardSummary.metric_revision, "two");
    assert.equal([...runtime.state.leaderboardSummaryCache.values()][0].response.metric_descriptions, undefined);
  } finally { globalThis.fetch = previousFetch; resetSummaryState(); }
});

test("detailed XLSX exports normalize table sort keys and preserve the complete filter scope", async () => {
  resetSummaryState();
  const previousFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (path, options) => {
    requests.push({ path, body: JSON.parse(options.body) });
    return { ok: false, status: 400, json: async () => ({ detail: "test export response" }) };
  };
  try {
    runtime.state.catalogQuery.datasets = ["office", "other"];
    runtime.state.catalogQuery.page = 2;
    for (const [column, sort] of Object.entries({ dataset_id: "dataset", task_name: "task", job_name: "job", model_provider: "provider", finished_at_ms: "last_turn_end", session_id: "session", status: "result", model: "model" })) {
      for (const direction of ["asc", "desc"]) {
        runtime.state.catalogQuery.sort = column;
        runtime.state.catalogQuery.direction = direction;
        catalog.exportCurrentScope("xlsx");
        const request = requests.at(-1);
        assert.equal(request.path, "/api/exports");
        assert.equal(request.body.query.sort, sort);
        assert.equal(request.body.query.direction, direction);
        assert.deepEqual(request.body.query.datasets, ["office", "other"]);
        assert.deepEqual(request.body.query.categories, ["b", "a"]);
        assert.equal("page" in request.body.query, false);
        assert.equal("page_size" in request.body.query, false);
        assert.equal(runtime.state.catalogQuery.sort, column);
      }
    }
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("summary cache ignores pagination, sorting, and chart statistic", async () => {
  resetSummaryState();
  const previousFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (path, options = {}) => {
    const body = JSON.parse(String(options.body));
    requests.push({ path: String(path), body });
    return response(envelope(runtime.state.catalogPage.generation, 125));
  };
  try {
    await catalog.loadLeaderboardSummary();
    runtime.state.catalogQuery.page = 2;
    runtime.state.catalogQuery.sort = "session";
    runtime.state.catalogQuery.direction = "asc";
    runtime.state.leaderboardSummaryStatistic = "p95";
    runtime.state.catalogQuery.categories = ["a", "b"];
    await catalog.loadLeaderboardSummary();

    assert.equal(requests.length, 1);
    assert.equal(requests[0].path, "/api/catalog-summaries");
    assert.deepEqual(Object.keys(requests[0].body).sort(), [
      "agents", "browser_views", "categories", "datasets", "group_by", "jobs", "models",
      "providers", "results", "search", "state", "tags", "tasks", "views",
    ]);
    assert.equal(requests[0].body.page, undefined);
    assert.equal(requests[0].body.sort, undefined);
    assert.equal(requests[0].body.source_keys, undefined);

    runtime.state.leaderboardSummaryGroupBy = "model";
    await catalog.loadLeaderboardSummary();
    runtime.state.catalogQuery.search = "needle";
    await catalog.loadLeaderboardSummary();
    runtime.state.catalogPage.generation = 8;
    await catalog.loadLeaderboardSummary();
    runtime.state.catalogQuery.datasets = ["alpha"];
    await catalog.loadLeaderboardSummary();
    assert.equal(requests.length, 5);
    assert.deepEqual(requests.at(-1).body.datasets, ["alpha"]);
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("a newer query owns the summary when responses arrive out of order", async () => {
  resetSummaryState();
  const previousFetch = globalThis.fetch;
  const pending = [];
  globalThis.fetch = (path, options = {}) => new Promise(resolve => {
    pending.push({
      body: JSON.parse(String(options.body)),
      resolve,
    });
  });
  try {
    runtime.state.catalogQuery.search = "old";
    const oldRequest = catalog.loadLeaderboardSummary();
    runtime.state.catalogQuery.search = "new";
    const newRequest = catalog.loadLeaderboardSummary();
    assert.equal(pending.length, 2);

    pending[1].resolve(response(envelope(7, 2, "new")));
    await newRequest;
    pending[0].resolve(response(envelope(7, 99, "old")));
    await oldRequest;

    assert.equal(runtime.state.leaderboardSummary.summary.matched_count, 2);
    assert.equal(runtime.state.leaderboardSummary.summary.groups[0].label, "new");
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("a newer server generation refreshes the catalog instead of showing an empty summary", async () => {
  resetSummaryState();
  const previousFetch = globalThis.fetch;
  const previousSetTimeout = globalThis.setTimeout;
  const scheduled = [];
  globalThis.fetch = async () => response(envelope(8, 126));
  globalThis.setTimeout = (callback, delay) => {
    scheduled.push({ callback, delay });
    return scheduled.length;
  };
  try {
    const result = await catalog.loadLeaderboardSummary();

    assert.equal(result, null);
    assert.equal(runtime.state.leaderboardSummary, null);
    assert.equal(runtime.state.leaderboardSummaryLoading, false);
    assert.match(runtime.state.leaderboardSummaryError, /generation changed/i);
    assert.equal(scheduled.length, 1);
    assert.equal(scheduled[0].delay, 0);
  } finally {
    globalThis.fetch = previousFetch;
    globalThis.setTimeout = previousSetTimeout;
  }
});

test("loading and failure clear the previous query summary", async () => {
  resetSummaryState();
  const previousFetch = globalThis.fetch;
  const target = document.createElement("section");
  target.id = "leaderboard-summary";
  document.body.append(target);
  let resolveRequest;
  globalThis.fetch = () => new Promise(resolve => { resolveRequest = resolve; });
  try {
    runtime.state.leaderboardSummary = envelope(7, 125);
    runtime.state.catalogQuery.search = "different scope";
    const request = catalog.loadLeaderboardSummary();
    assert.equal(runtime.state.leaderboardSummary, null);
    assert.equal(runtime.state.leaderboardSummaryLoading, true);

    resolveRequest(response({ detail: "summary failed" }, { ok: false, status: 500 }));
    await request;
    assert.equal(runtime.state.leaderboardSummary, null);
    assert.equal(runtime.state.leaderboardSummaryLoading, false);
    assert.match(runtime.state.leaderboardSummaryError, /summary failed/);
    summaryUi.renderLeaderboardSummary();
    assert.match(target.textContent, /complete-query summary is unavailable/i);
    assert.match(target.textContent, /summary failed/i);
  } finally {
    globalThis.fetch = previousFetch;
    target.remove();
  }
});

test("a detail request failure does not clear a completed summary", async () => {
  resetSummaryState();
  const previousFetch = globalThis.fetch;
  const summary = envelope(7, 125);
  runtime.state.leaderboardSummary = summary;
  globalThis.fetch = async () => response(
    { detail: "detail failed" },
    { ok: false, status: 500 },
  );
  try {
    await catalog.loadServeSourceReport("missing-source");

    assert.equal(runtime.state.leaderboardSummary, summary);
    assert.equal(runtime.state.leaderboardSummaryError, null);
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("an initial checking envelope keeps the summary in its loading state", () => {
  resetSummaryState();
  const target = document.createElement("section");
  target.id = "leaderboard-summary";
  document.body.append(target);
  try {
    runtime.state.catalogPage = {
      generation: 0,
      total: 0,
      page: 1,
      page_size: 100,
      checking: true,
    };
    runtime.state.leaderboardSummary = {
      ...envelope(0, 0),
      checking: true,
      stale: true,
    };
    runtime.state.leaderboardSummaryLoading = false;

    summaryUi.renderLeaderboardSummary();

    assert.match(target.textContent, /Calculating the complete-query summary/);
    assert.doesNotMatch(target.textContent, /No Trials match/);
    assert.doesNotMatch(target.textContent, /0 matching Trials/);
  } finally {
    target.remove();
  }
});

test("catalog pages without a comparison region skip the summary request", async () => {
  resetSummaryState();
  const previousFetch = globalThis.fetch;
  const previousSelection = runtime.state.selectedSourceKey;
  const previousView = runtime.state.view;
  const previousViewsLoaded = runtime.state.workspaceViewsLoaded;
  const requests = [];
  runtime.state.catalogLoading = false;
  runtime.state.selectedSourceKey = "existing-source";
  runtime.state.view = { trajectory_meta: [{ trial_key: "existing-trial" }] };
  runtime.state.workspaceViewsLoaded = true;
  globalThis.fetch = async path => {
    requests.push(String(path));
    if (String(path) === "/api/catalog-summaries") {
      return response(envelope(7, 125));
    }
    return response({
      generation: 7,
      checking: false,
      stale: false,
      total: 0,
      page: 1,
      page_size: 100,
      items: [],
      facets: {},
      column_presence: {},
    });
  };
  try {
    await catalog.loadCatalogPage();

    assert.equal(requests.length, 1);
    assert.doesNotMatch(requests[0], /catalog\/summary/);
  } finally {
    globalThis.fetch = previousFetch;
    runtime.state.catalogLoading = false;
    runtime.state.selectedSourceKey = previousSelection;
    runtime.state.view = previousView;
    runtime.state.workspaceViewsLoaded = previousViewsLoaded;
  }
});

test("pagination remains responsive while the complete-query summary is pending", async () => {
  resetSummaryState();
  const previousFetch = globalThis.fetch;
  const previousSelection = runtime.state.selectedSourceKey;
  const previousView = runtime.state.view;
  const previousViewsLoaded = runtime.state.workspaceViewsLoaded;
  const comparison = document.createElement("section");
  comparison.id = "comparison";
  document.body.append(comparison);
  const catalogRequests = [];
  let resolveSummary;
  runtime.state.catalogLoading = false;
  runtime.state.selectedSourceKey = "existing-source";
  runtime.state.view = { trajectory_meta: [{ trial_key: "existing-trial" }] };
  runtime.state.workspaceViewsLoaded = true;
  globalThis.fetch = async path => {
    if (String(path) === "/api/catalog-summaries") {
      return new Promise(resolve => { resolveSummary = resolve; });
    }
    const url = new URL(String(path), "http://localhost");
    const page = Number(url.searchParams.get("page") || 1);
    catalogRequests.push(page);
    return response({
      generation: 7,
      checking: false,
      stale: false,
      total: 125,
      page,
      page_size: 100,
      items: [],
      facets: {},
      column_presence: {},
    });
  };
  try {
    const firstLoad = catalog.loadCatalogPage({ page: 1 });
    while (!resolveSummary) await new Promise(resolve => setImmediate(resolve));
    const secondLoad = catalog.loadCatalogPage({ page: 2 });
    resolveSummary(response(envelope(7, 125)));
    await Promise.all([firstLoad, secondLoad]);

    assert.deepEqual(catalogRequests, [1, 2]);
    assert.equal(runtime.state.catalogQuery.page, 2);
    assert.equal(runtime.state.catalogPage.page, 2);
  } finally {
    globalThis.fetch = previousFetch;
    runtime.state.catalogLoading = false;
    runtime.state.selectedSourceKey = previousSelection;
    runtime.state.view = previousView;
    runtime.state.workspaceViewsLoaded = previousViewsLoaded;
    comparison.remove();
  }
});

test("editing an applied server Saved View changes the summary cache identity", async () => {
  resetSummaryState();
  const previousFetch = globalThis.fetch;
  const requests = [];
  runtime.state.workspaceViews = [{
    id: "server:Daily focus",
    origin: "server",
    name: "Daily focus",
    filters: { results: ["passed"] },
    group_by: "agent",
    notes: "",
  }];
  runtime.state.workspaceAppliedViewNames = new Set(["server:Daily focus"]);
  globalThis.fetch = async (path, options = {}) => {
    requests.push({ path: String(path), body: JSON.parse(String(options.body)) });
    return response(envelope(7, requests.length));
  };
  try {
    await catalog.loadLeaderboardSummary();
    runtime.state.workspaceViews = [{
      ...runtime.state.workspaceViews[0],
      filters: { results: ["failed"] },
    }];
    await catalog.loadLeaderboardSummary();

    assert.equal(requests.length, 2);
    assert.deepEqual(requests.map(item => item.body.views), [
      ["Daily focus"],
      ["Daily focus"],
    ]);
    assert.equal(runtime.state.leaderboardSummary.summary.matched_count, 2);
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("an oversized summary remains visible but is not retained in the browser cache", async () => {
  resetSummaryState();
  const previousFetch = globalThis.fetch;
  const oversizedLabel = "x".repeat(9 * 1024 * 1024);
  let requests = 0;
  globalThis.fetch = async () => {
    requests += 1;
    return response(envelope(7, 1, oversizedLabel));
  };
  try {
    await catalog.loadLeaderboardSummary();
    assert.equal(runtime.state.leaderboardSummary.summary.matched_count, 1);
    assert.equal(runtime.state.leaderboardSummaryCache.size, 0);

    await catalog.loadLeaderboardSummary();
    assert.equal(requests, 2);
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("radar controls enforce limits, preserve search and missing axes, and do not fetch data", () => {
  resetSummaryState();
  const target = document.createElement("section");
  target.id = "leaderboard-summary";
  document.body.append(target);
  runtime.state.leaderboardSummaryGroupBy = "model";
  runtime.state.leaderboardSummary = envelope(7, 7);
  runtime.state.leaderboardSummary.summary.groups = Array.from({ length: 7 }, (_, index) => ({ key: `model-${index}`, label: `model-${index}`, count: 1, metrics: [{ key: "score", count: 1, mean: index }] }));
  const previousFetch = globalThis.fetch;
  globalThis.fetch = () => { throw new Error("Presentation must not fetch"); };
  try {
    summaryUi.renderLeaderboardSummary();
    target.querySelector("[data-summary-chart-type=radar]").click();
    assert.equal(target.querySelectorAll("[data-radar-group]:checked").length, 5);
    assert.equal(target.querySelectorAll("[data-radar-group]:disabled").length, 2);
    assert.match(target.textContent, /No data:.*TTFT/);
    assert.equal(target.querySelectorAll("[data-metric-id]:checked").length, 10);
    const context = radarUi.radarContext(runtime.state.leaderboardSummary.summary.groups, summaryUi.leaderboardSummaryDefinitions(), summaryUi.leaderboardSummaryStatistics()[0], summaryUi.leaderboardSummaryValue);
    const option = radarUi.radarOption(context, 600, 440);
    assert.ok(option.series.every(series => series.lineStyle.type === "solid"));
    assert.ok(option.graphic.some(marker => marker.type === "group"));
    assert.equal(context.series[0].points.find(point => point.key === "ttft_ms").value, null);
    assert.equal(target.querySelector("[data-radar-fallback]").hidden, false);
    const search = target.querySelector("[data-radar-search]");
    search.value = "model-1";
    search.dispatchEvent(new Event("input"));
    target.querySelector("[data-radar-group='1']").click();
    assert.equal(target.querySelector("[data-radar-search]").value, "model-1");
    assert.equal(target.querySelectorAll("[data-radar-group-row]:not([hidden])").length, 1);
    assert.equal(target.querySelectorAll("[data-radar-group]:checked").length, 4);
    for (const key of ["cache_hit_rate", "tool_success_rate", "ttft_ms"]) target.querySelector(`[data-metric-id=${key}]`).click();
    target.querySelector("[data-metric-apply]").click();
    assert.equal(target.querySelector("[data-radar-search]").value, "model-1");
    assert.equal(target.querySelectorAll("[data-metric-id]:checked").length, 7);
    assert.equal(target.querySelectorAll("[data-metric-id]:disabled").length, 0);
    target.querySelector("[data-summary-chart-type=bar]").click();
    assert.equal(target.querySelector("[data-summary-radar]"), null);
    target.querySelector("[data-summary-chart-type=radar]").click();
    assert.equal(target.querySelector("[data-radar-search]").value, "model-1");
    assert.equal(target.querySelectorAll("[data-radar-group]:checked").length, 4);
  } finally {
    globalThis.fetch = previousFetch;
    target.remove();
  }
});

test("radar presentation changes preserve the open table and search at 1000 groups", () => {
  resetSummaryState();
  const target = document.createElement("section"); target.id = "leaderboard-summary"; document.body.append(target);
  runtime.state.leaderboardSummary = envelope(7, 1000);
  runtime.state.leaderboardSummary.summary.groups = Array.from({ length: 1000 }, (_, i) => ({ key: `group-${i}`, label: `group-${i}`, count: 1, metrics: [{ key: "score", count: 1, mean: i }] }));
  runtime.state.leaderboardSummaryChartType = "radar";
  runtime.state.leaderboardSummaryGroupBy = "model";
  runtime.state.leaderboardSummaryRadarGroups = ["group-0"];
  runtime.state.leaderboardSummaryTableOpen = true;
  try {
    summaryUi.renderLeaderboardSummary();
    const table = target.querySelector(".leaderboard-summary-table");
    assert.equal(table.tBodies[0].rows.length, 1000);
    const search = target.querySelector("[data-radar-search]"); search.value = "group-999"; search.dispatchEvent(new Event("input"));
    for (const selector of ["[data-radar-group='999']", "[data-summary-statistic=p95]"]) {
      target.querySelector(selector).click();
      assert.equal(target.querySelector(".leaderboard-summary-table"), table);
      assert.equal(target.querySelector("[data-radar-search]").value, "group-999");
      assert.equal(target.querySelectorAll("[data-radar-group-row]:not([hidden])").length, 1);
    }
    assert.ok([...table.querySelectorAll("[data-summary-stat='p95']")].every(cell => cell.classList.contains("summary-selected-stat")));
  } finally { radarUi.disposeLeaderboardRadar(); target.remove(); }
});

test("detached radar controls cannot dispatch into disposed or replacement charts", () => {
  resetSummaryState();
  const target = document.createElement("section");
  target.id = "leaderboard-summary";
  document.body.append(target);
  runtime.state.leaderboardSummaryGroupBy = "model";
  runtime.state.leaderboardSummaryChartType = "radar";
  runtime.state.leaderboardSummary = envelope(7, 1);
  runtime.state.leaderboardSummary.summary.groups = [{ key: "a", label: "a", count: 1, metrics: [] }];
  const instances = [];
  window.echarts = { init: () => {
    const instance = { disposed: false, actions: 0, resize() {}, setOption() {}, on() {}, dispose() { this.disposed = true; }, dispatchAction() { assert.equal(this.disposed, false); this.actions += 1; } };
    instances.push(instance);
    return instance;
  } };
  try {
    summaryUi.renderLeaderboardSummary();
    const old = target.querySelector("[data-radar-group-row]");
    old.querySelector("input").focus();
    summaryUi.renderLeaderboardSummary();
    assert.equal(instances[0].disposed, true);
    const actions = instances[1].actions;
    old.dispatchEvent(new Event("pointerleave"));
    old.dispatchEvent(new Event("focusin"));
    assert.equal(instances[1].actions, actions);
    target.querySelector("[data-summary-chart-type=bar]").click();
    assert.equal(instances[1].disposed, true);
  } finally { delete window.echarts; target.remove(); }
});

test("radar resize skips unchanged sizes, coalesces notifications and cancels pending work", () => {
  resetSummaryState();
  const target = document.createElement("section");
  target.innerHTML = '<div data-summary-radar></div><p data-radar-fallback hidden></p>';
  document.body.append(target);
  const node = target.querySelector("[data-summary-radar]");
  let width = 600;
  Object.defineProperties(node, { clientWidth: { get: () => width }, clientHeight: { value: 440 } });
  const groups = [{ key: "a", label: "a", count: 1, metrics: [] }];
  const context = radarUi.radarContext(groups, summaryUi.leaderboardSummaryDefinitions(), summaryUi.leaderboardSummaryStatistics()[0], summaryUi.leaderboardSummaryValue);
  const previous = { ResizeObserver: globalThis.ResizeObserver, requestAnimationFrame: globalThis.requestAnimationFrame, cancelAnimationFrame: globalThis.cancelAnimationFrame };
  const frames = new Map();
  let notify, sequence = 0, updates = 0;
  globalThis.ResizeObserver = class { constructor(callback) { notify = callback; } observe() {} disconnect() {} };
  globalThis.requestAnimationFrame = callback => { frames.set(++sequence, callback); return sequence; };
  globalThis.cancelAnimationFrame = id => frames.delete(id);
  const flush = () => { const callbacks = [...frames.values()]; frames.clear(); callbacks.forEach(callback => callback()); };
  window.echarts = { init: () => ({ resize() {}, setOption() { updates += 1; }, on() {}, dispose() {} }) };
  try {
    radarUi.bindLeaderboardRadar(target, context, () => {});
    assert.equal(updates, 1);
    notify(); flush();
    assert.equal(updates, 1);
    width = 620; notify(); width = 640; notify();
    assert.equal(frames.size, 1);
    flush();
    assert.equal(updates, 2);
    width = 660; notify();
    radarUi.disposeLeaderboardRadar();
    assert.equal(frames.size, 0);
    flush();
    assert.equal(updates, 2);
  } finally { radarUi.disposeLeaderboardRadar(); Object.assign(globalThis, previous); delete window.echarts; target.remove(); }
});

test("selected group colors follow summary order and unselected groups are neutral", () => {
  resetSummaryState();
  const groups = ["group-0", "group-4", "group-8", "group-12", "group-16"].map(key => ({ key, label: key, count: 1, metrics: [] }));
  const context = radarUi.radarContext(groups, summaryUi.leaderboardSummaryDefinitions(), summaryUi.leaderboardSummaryStatistics()[0], summaryUi.leaderboardSummaryValue);
  assert.equal(new Set(context.series.map(item => item.color)).size, 5);
  const html = radarUi.renderLeaderboardRadar(context);
  for (const item of context.series) assert.ok(html.includes(`--radar-color:${item.color}`));
  runtime.state.leaderboardSummaryRadarGroups = [groups[3].key, groups[1].key];
  const changed = radarUi.radarContext(groups, summaryUi.leaderboardSummaryDefinitions(), summaryUi.leaderboardSummaryStatistics()[0], summaryUi.leaderboardSummaryValue);
  assert.deepEqual(changed.series.map(item => item.group.key), [groups[1].key, groups[3].key]);
  assert.deepEqual(changed.series.map(item => item.color), context.series.slice(0, 2).map(item => item.color));
  assert.match(radarUi.renderLeaderboardRadar(changed), /--radar-color:var\(--rule\)/);
  runtime.state.leaderboardSummaryRadarGroups = groups.filter((_, index) => index !== 2).map(group => group.key);
  const middleRemoved = radarUi.radarContext(groups, summaryUi.leaderboardSummaryDefinitions(), summaryUi.leaderboardSummaryStatistics()[0], summaryUi.leaderboardSummaryValue);
  assert.equal(middleRemoved.series[2].group.key, groups[3].key);
  assert.equal(middleRemoved.series[2].color, context.series[2].color);
});

test("duplicate radar metric labels include metric identities", () => {
  resetSummaryState();
  const definitions = ["one", "two", "three"].map((key, index) => ({ key, direction: "higher", label: index < 2 ? "Quality" : "Speed" }));
  const context = radarUi.radarContext([], definitions, summaryUi.leaderboardSummaryStatistics()[0], summaryUi.leaderboardSummaryValue);
  assert.equal(radarUi.radarMetricLabel(context, "one"), "Quality (one)");
  assert.equal(radarUi.radarMetricLabel(context, "two"), "Quality (two)");
  assert.equal(radarUi.radarMetricLabel(context, "three"), "Speed");
});

test("missing annotations identify individual axes and groups without covering measured zero", () => {
  resetSummaryState();
  const groups = [{ key: "a", label: "a", count: 1, metrics: [{ key: "score", count: 1, mean: 0 }] }, { key: "b", label: "b", count: 1, metrics: [{ key: "score", count: 1, mean: 1 }] }];
  const context = radarUi.radarContext(groups, summaryUi.leaderboardSummaryDefinitions(), summaryUi.leaderboardSummaryStatistics()[0], summaryUi.leaderboardSummaryValue);
  const option = radarUi.radarOption(context, 600, 440);
  const missing = option.graphic.filter(marker => marker.type === "group");
  assert.equal(new Set(missing.map(marker => `${marker.x},${marker.y}`)).size, missing.length);
  assert.ok(missing.every(marker => Math.hypot(marker.x - 300, marker.y - 220) > 11.5));
  assert.ok(option.graphic.some(marker => marker.type === "circle" && marker.shape.cx === 300 && marker.shape.cy === 220));
  assert.equal(context.series[0].points[1].value, null);
  assert.equal(option.series[0].data[0].value[1], 0);
});

test("an unavailable metric definition retains a readable key rather than breaking the radar", () => {
  resetSummaryState();
  const groups = [{ key: "a", label: "a", count: 1, metrics: [] }];
  const context = radarUi.radarContext(groups, [], summaryUi.leaderboardSummaryStatistics()[0], summaryUi.leaderboardSummaryValue);
  assert.doesNotThrow(() => radarUi.renderLeaderboardRadar(context));
  assert.doesNotThrow(() => radarUi.radarOption(context, 600, 440));
});

test("a measured polygon collapsed to the origin is identified separately from wholly missing data", () => {
  resetSummaryState();
  const groups = [{ key: "a", label: "a", count: 1, metrics: [{ key: "score", count: 1, mean: 0 }] }, { key: "b", label: "b", count: 1, metrics: [{ key: "score", count: 1, mean: 1 }] }];
  runtime.state.leaderboardSummaryRadarGroups = ["a"];
  const context = radarUi.radarContext(groups, summaryUi.leaderboardSummaryDefinitions(), summaryUi.leaderboardSummaryStatistics()[0], summaryUi.leaderboardSummaryValue);
  const html = radarUi.renderLeaderboardRadar(context);
  assert.match(html, /Measured relative values are all 0; the outline is at the origin/);
  assert.ok(context.series[0].points.some(point => point.value === 0));
  assert.ok(context.series[0].points.some(point => point.value === null));
  assert.ok(context.series[0].points.every(point => point.coordinate === 0));
  groups[0].metrics = [];
  assert.doesNotMatch(radarUi.renderLeaderboardRadar(radarUi.radarContext(groups, summaryUi.leaderboardSummaryDefinitions(), summaryUi.leaderboardSummaryStatistics()[0], summaryUi.leaderboardSummaryValue)), /Measured relative values are all 0/);
});

test("long Unicode catalog conditions use a POST body without changing the query", async () => {
  resetSummaryState();
  const previousFetch = globalThis.fetch;
  const previousLoaded = runtime.state.workspaceViewsLoaded;
  runtime.state.workspaceViewsLoaded = true;
  runtime.state.catalogLoading = false;
  runtime.state.catalogQuery.search = "中".repeat(15000);
  const originalQuery = structuredClone(runtime.state.catalogQuery);
  const requests = [];
  globalThis.fetch = async (path, options) => {
    requests.push({ path, options });
    return response({ generation: 7, total: 0, items: [], facets: {} });
  };
  try {
    await catalog.loadCatalogPage({}, { skipDetail: true, throwOnError: true });
    const request = requests.find(item => item.path === "/api/catalog-queries");
    assert.ok(request);
    assert.equal(request.options.method, "POST");
    assert.equal(JSON.parse(request.options.body).search, originalQuery.search);
    assert.deepEqual(runtime.state.catalogQuery, originalQuery);
    assert.equal(requests.some(item => item.path.startsWith("/api/catalog?")), false);
  } finally {
    globalThis.fetch = previousFetch;
    runtime.state.workspaceViewsLoaded = previousLoaded;
  }
});

test("successful catalog and fresh or cached detail loads clear scan status without clearing action errors", async () => {
  resetSummaryState();
  const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
  const { setServeStatus } = await import("../../src/psycheval/assets/web/modules/serve-effects.js");
  const target = document.createElement("div");
  target.innerHTML = '<section id="leaderboard-region"><section id="leaderboard"><div class="leaderboard-action-row"></div></section></section>'; document.body.append(target);
  const previousFetch = globalThis.fetch, previousTimeout = globalThis.setTimeout;
  const previous = { view: runtime.state.view, selectedSourceKey: runtime.state.selectedSourceKey, workspaceViewsLoaded: runtime.state.workspaceViewsLoaded };
  runtime.state.workspaceViewsLoaded = true;
  runtime.state.catalogLoading = false;
  let checking = true, detailRequests = 0;
  const scheduled = [];
  const action = beginFeedback("#leaderboard .leaderboard-action-row", { key: "test:preserved-export" });
  const assertSettled = () => {
    assert.equal(target.querySelectorAll('[data-action-feedback="test:preserved-export"]').length, 1);
    assert.equal(target.querySelector('[data-action-feedback$=":load"]'), null);
    assert.match(target.textContent, /Export failed/);
  };
  globalThis.setTimeout = (callback, delay) => {
    if (delay === 200) { scheduled.push(callback); return 0; }
    return previousTimeout(callback, delay);
  };
  globalThis.fetch = async path => {
    if (String(path).startsWith("/api/sources/")) {
      detailRequests += 1;
      return response({ report: { trajectory: [{ steps: [] }], trajectory_meta: [{ trial_key: "status-trial" }] }, artifact_revision: "r1" });
    }
    return response({ generation: 7, checking, total: 0, items: [], facets: {}, page: 1, page_size: 100 });
  };
  try {
    action.error("Export failed");
    await catalog.loadCatalogPage({}, { skipDetail: true });
    assert.match(target.textContent, /Checking runs/);
    assert.equal(scheduled.length, 1);
    checking = false;
    for (const mode of ["active", "archived", "all"]) {
      runtime.state.catalogQuery.state = mode;
      await catalog.loadCatalogPage({}, { skipDetail: true });
      assertSettled();
    }
    target.insertAdjacentHTML("beforeend", '<section id="report-notes"></section><section id="comparison"></section><section id="trace"></section><aside id="detail-sidebar" hidden></aside>');
    setServeStatus("Checking runs");
    await catalog.loadServeSourceReport("status-source", { throwOnError: true });
    await new Promise(resolve => window.requestAnimationFrame(resolve));
    assert.equal(detailRequests, 1);
    assertSettled();
    setServeStatus("Checking runs");
    await catalog.selectServeDetail("status-source", { throwOnError: true });
    await new Promise(resolve => window.requestAnimationFrame(resolve));
    assert.equal(detailRequests, 1);
    assertSettled();
    assert.doesNotMatch(target.textContent, /snapshots|All sessions|Checking runs/);
  } finally {
    setServeStatus(""); action.dispose(); target.remove();
    globalThis.fetch = previousFetch; globalThis.setTimeout = previousTimeout;
    Object.assign(runtime.state, previous);
  }
});
