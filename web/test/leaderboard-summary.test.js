import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin","sources":[]}</script>
`);

const runtime = await import("../../src/psycheval/assets/web/modules/runtime.js");
const catalog = await import("../../src/psycheval/assets/web/modules/serve-catalog.js");
const summaryUi = await import("../../src/psycheval/assets/web/modules/leaderboard-summary.js");

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
    results: [],
    views: [],
  };
  runtime.state.workspaceViews = [];
  runtime.state.workspaceAppliedViewNames = new Set();
  runtime.state.leaderboardSummaryGroupBy = "overall";
  runtime.state.leaderboardSummaryStatistic = "mean";
  runtime.state.leaderboardSummary = null;
  runtime.state.leaderboardSummaryLoading = false;
  runtime.state.leaderboardSummaryError = null;
  runtime.state.leaderboardSummaryScopeKey = null;
  runtime.state.leaderboardSummaryRequestKey = null;
  runtime.state.leaderboardSummaryRequestVersion += 1;
  runtime.state.leaderboardSummaryRequestPromise = null;
  runtime.state.leaderboardSummaryCache.clear();
}

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
      "agents", "browser_views", "categories", "group_by", "jobs", "models",
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
    assert.equal(requests.length, 4);
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
