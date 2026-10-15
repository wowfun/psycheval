import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"guest"}</script>
  <section id="leaderboard-region"></section><section id="comparison"></section>
  <section id="trace"></section><section id="report-notes"></section>
  <aside id="detail-sidebar" hidden></aside><aside id="workspace-report-reader" hidden></aside>
`);
const { state, render } = await import("../../src/psycheval/assets/web/modules/runtime.js");
const catalog = await import("../../src/psycheval/assets/web/modules/serve-catalog.js");
const reports = await import("../../src/psycheval/assets/web/modules/workspace-reports.js");
const { closeDetailSidebar } = await import("../../src/psycheval/assets/web/modules/detail-sidebar.js");
const views = await import("../../src/psycheval/assets/web/modules/workspace-views.js");
const { restoreHomeLocation } = await import("../../src/psycheval/assets/web/modules/home-location.js");
const locationCodec = await import("../../src/psycheval/assets/web/app/workspace-location.js");
const report = { report_id: "20261012-000000-123456", report_ref: "package:20261012-000000-123456", filename: "report.md", format: "markdown", source_keys: [] };

test("leaderboard search publishes one debounced location with the final input", async t => {
  const { setWorkspaceApp } = await import("../../src/psycheval/assets/web/app/workspace-runtime.js");
  const commits = [];
  setWorkspaceApp({ locationChanged: page => commits.push({ page, search: state.catalogQuery.search }) });
  t.mock.timers.enable({ apis: ["setTimeout"] });
  globalThis.fetch = () => new Promise(() => {});
  try {
    for (const query of ["a", "ab", "abc"]) {
      state.search = { query };
      catalog.applyLeaderboardSearchMode();
    }
    assert.deepEqual(commits, []);
    t.mock.timers.tick(150);
    assert.deepEqual(commits, [{ page: "home", search: "abc" }]);
  } finally {
    catalog.cancelHomeLocationRequests();
    setWorkspaceApp(null);
    t.mock.timers.reset();
  }
});
const trajectory = { trajectory: [{ trajectory_id: "root", session_id: "session", agent: { name: "agent" }, steps: [{ step_id: 1, source: "user", message: "request" }], final_metrics: {} }], trajectory_meta: [{ trial_key: "trial", adapter: "psychevo", steps: [{ step_id: 1 }] }], annotations: {} };

test("sort clicks continue a restored API sort through descending and default", () => {
  globalThis.fetch = () => new Promise(() => {});
  state.catalogQuery.sort = "task"; state.catalogQuery.direction = "asc";
  try {
    catalog.requestCatalogSort("task_name");
    assert.equal(state.catalogQuery.sort, "task");
    assert.equal(state.catalogQuery.direction, "desc");
    catalog.requestCatalogSort("task_name");
    assert.equal(state.catalogQuery.sort, "last_turn_end");
  } finally { catalog.cancelHomeLocationRequests(); }
});

test("archived Home reader refresh renders once and obsolete detail refreshes cannot overwrite it", async () => {
  state.workspaceReports = [report];
  reports.openWorkspaceReportReader(report.report_id);
  const frame = document.querySelector("#workspace-report-reader iframe");
  const pending = [];
  globalThis.fetch = path => String(path) === "/api/reports"
    ? Promise.resolve(response([]))
    : new Promise(resolve => pending.push(resolve));
  try {
    const old = reports.refreshWorkspaceReports({ renderLeaderboard: false });
    while (!pending.length) await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(document.querySelector("#workspace-report-reader iframe"), frame);
    const fresh = reports.refreshWorkspaceReports({ renderLeaderboard: false });
    while (pending.length < 2) await new Promise(resolve => setTimeout(resolve, 0));
    pending[1](response({ ...report, filename: "new.md" })); await fresh;
    const freshFrame = document.querySelector("#workspace-report-reader iframe");
    pending[0](response({ ...report, filename: "old.md" })); await old;
    assert.equal(state.reportReader.report.filename, "new.md");
    assert.equal(document.querySelector("#workspace-report-reader iframe"), freshFrame);
  } finally {
    for (const resolve of pending) resolve(response(report));
    reports.closeWorkspaceReportReader();
  }
});

test("applied Saved View conditions normalize blanks exactly as the query service", () => {
  const filters = views.workspaceViewFilters({ agents: [" foo ", "", "  ", "foo"], categories: ["", " keep "] });
  assert.deepEqual(filters.agents, ["foo"]);
  assert.deepEqual(filters.categories, ["keep"]);
  const href = locationCodec.encodeWorkspaceLocation("home", { state: { views: [{ name: "Legacy", filters }] } });
  const restored = locationCodec.decodeWorkspaceLocation("home", new URL(href, "http://localhost"));
  assert.deepEqual(restored.state.views[0].filters.agents, filters.agents);
});
const response = value => new Response(JSON.stringify(value));
test.after(() => browser.cleanup());

test("cached missing positions show an error and reject only for explicit callers", async () => {
  state.selectedSourceKey = "cached";
  state.selectedTrajectory = null;
  state.workspaceViewsLoaded = true;
  render(trajectory);
  globalThis.fetch = () => { throw new Error("cached selection must not fetch"); };
  await catalog.selectServeDetail("cached", { openSidebar: true, stepId: "missing" });
  assert.match(document.querySelector("[data-leaderboard-status]")?.textContent || document.querySelector("#leaderboard-region").textContent, /Requested step is unavailable/);
  assert.equal(state.homeLocationTarget.step, "missing");
  await assert.rejects(catalog.selectServeDetail("cached", { openSidebar: true, trajectoryId: "missing", throwOnError: true }), /Requested trajectory is unavailable/);
  closeDetailSidebar({ render: false });
});

test("missing trajectory or step retains prior selection and the requested URL identity", async () => {
  globalThis.fetch = () => Promise.resolve(response({ report: trajectory }));
  state.selectedSourceKey = "prior";
  state.selectedTrial = "prior-trial";
  state.selectedTrajectory = { trialKey: "prior-trial", trajectoryId: "prior-child" };
  state.selectedStep = { trialKey: "prior-trial", stepId: "7" };
  const prior = [state.selectedSourceKey, state.selectedTrial, state.selectedTrajectory, state.selectedStep];
  for (const selection of [{ trajectoryId: "missing" }, { stepId: "missing" }]) {
    await assert.rejects(catalog.selectServeDetail("requested", { openSidebar: true, throwOnError: true, ...selection }), /unavailable/);
    assert.deepEqual([state.selectedSourceKey, state.selectedTrial, state.selectedTrajectory, state.selectedStep], prior);
    assert.equal(state.homeLocationTarget.source, "requested");
  }
  globalThis.fetch = () => Promise.resolve(new Response(JSON.stringify({ detail: "retained source is missing" }), { status: 404 }));
  state.catalogPage.items = [{ source_key: "requested", trial_key: "trial" }];
  await assert.rejects(catalog.selectServeDetail("requested", { openSidebar: true, trajectoryId: "missing", throwOnError: true }), /retained source is missing/);
  state.catalogPage.items = [];
  closeDetailSidebar({ render: false });
});

test("a late Home report cannot replace a newer Trial selection", async () => {
  let release;
  globalThis.fetch = path => String(path).startsWith("/api/report-library/")
    ? new Promise(resolve => { release = resolve; }) : Promise.resolve(response([]));
  const loading = reports.openWorkspaceReportRef(report.report_ref);
  state.selectedSourceKey = "new-trial";
  state.workspaceViewsLoaded = true;
  render(trajectory);
  await catalog.selectServeDetail("new-trial", { openSidebar: true });
  release(response(report)); await loading;
  assert.equal(state.homeLocationTarget.source, "new-trial");
  assert.equal(state.reportReader.openRef, null);
  assert.equal(state.detailSidebar.open, true);
  closeDetailSidebar({ render: false });
});

test("a late Trial cannot replace a Home report, and the readers use one located object", async () => {
  let release;
  globalThis.fetch = path => String(path).startsWith("/api/sources/")
    ? new Promise(resolve => { release = resolve; }) : Promise.resolve(response([]));
  const loading = catalog.selectServeDetail("old-trial", { openSidebar: true });
  state.workspaceReports = [report];
  reports.openWorkspaceReportReader(report.report_id);
  release(response({ report: trajectory })); await loading;
  assert.equal(state.homeLocationTarget.report, report.report_ref);
  assert.equal(state.reportReader.openRef, report.report_ref);
  assert.equal(state.detailSidebar.open, false);
  reports.closeWorkspaceReportReader();
});

test("a new filter cancels a pending catalog request and owns the resulting rows", async () => {
  const pending = new Map();
  globalThis.fetch = (path, options) => {
    if (String(path).startsWith("/api/catalog?")) {
      const search = new URL(path, "http://localhost").searchParams.get("search");
      return new Promise(resolve => { pending.set(search, { resolve, signal: options.signal }); });
    }
    return Promise.resolve(response({ generation: 1, summary: { matched_count: 0, groups: [] } }));
  };
  state.catalogLoading = false; state.selectedSourceKey = null; state.homeLocationTarget = {};
  state.catalogPage = { ...state.catalogPage, generation: 1 };
  const old = catalog.loadCatalogPage({ search: "old" }, { skipDetail: true });
  const newest = catalog.loadCatalogPage({ search: "new" }, { skipDetail: true });
  assert.equal(pending.size, 2);
  assert.equal(pending.get("old").signal.aborted, true);
  const page = search => ({ generation: 1, items: [], total: 0, page: 1, page_size: 100, search });
  pending.get("new").resolve(response(page("new"))); await newest;
  pending.get("old").resolve(response(page("old"))); await old;
  assert.equal(state.catalogPage.search, "new");
  assert.equal(state.catalogQuery.search, "new");
});

test("a stale conflict cannot overwrite a newer catalog after refreshing Saved Views", { timeout: 5000 }, async () => {
  let releaseViews;
  let refreshing;
  const enteredRefresh = new Promise(resolve => { refreshing = resolve; });
  const saved = { name: "Saved", filters: {}, group_by: "agent" };
  globalThis.fetch = path => {
    if (String(path).startsWith("/api/catalog?")) {
      const search = new URL(path, "http://localhost").searchParams.get("search");
      return Promise.resolve(search === "old"
        ? new Response(JSON.stringify({ detail: "old view conflict" }), { status: 409 })
        : response({ generation: 1, items: [], total: 0, page: 1, page_size: 100, search }));
    }
    if (path === "/api/views") {
      refreshing();
      return new Promise(resolve => { releaseViews = resolve; });
    }
    return Promise.resolve(response({ generation: 1, views: [], summary: { matched_count: 0, groups: [] } }));
  };
  state.workspaceViews = [{ ...saved, id: "server:Saved", origin: "server" }];
  state.workspaceViewsLoaded = true;
  state.workspaceViewSummaryGeneration = 1;
  state.workspaceAppliedViewNames = new Set(["server:Saved"]);
  const old = catalog.loadCatalogPage({ search: "old" }, { skipDetail: true });
  await enteredRefresh;
  await catalog.loadCatalogPage({ search: "new" }, { skipDetail: true });
  releaseViews(response([saved]));
  await old;
  assert.equal(state.catalogPage.search, "new");
  assert.equal(state.leaderboardSummaryError, null);
  state.workspaceAppliedViewNames.clear();
});

for (const refreshFails of [false, true]) test(`a late Saved View refresh cannot clear restored shared conditions (failure=${refreshFails})`, { timeout: 5000 }, async () => {
  let releaseViews;
  let firstRead = true;
  const queries = [];
  globalThis.fetch = path => {
    if (path === "/api/views") {
      if (!firstRead) return Promise.resolve(response([]));
      firstRead = false;
      return new Promise(resolve => { releaseViews = resolve; });
    }
    queries.push(path);
    return Promise.resolve(response({ generation: 1, items: [], total: 0, page: 1, page_size: 100 }));
  };
  state.workspaceAppliedViewNames = new Set(["server:Saved"]);
  const pending = views.refreshWorkspaceViews();
  const href = locationCodec.encodeWorkspaceLocation("home", { state: {
    query: { search: "restored search" },
    views: [{ name: "Shared snapshot", filters: { agents: ["retained-agent"] } }],
  } });
  const restored = locationCodec.decodeWorkspaceLocation("home", new URL(href, "http://localhost"));
  restoreHomeLocation(restored);
  releaseViews(refreshFails
    ? new Response(JSON.stringify({ detail: "fixture views unavailable" }), { status: 503 })
    : response([]));
  await pending;
  assert.equal(state.catalogQuery.search, "restored search");
  assert.deepEqual(state.sharedViewSnapshots, restored.state.views);
  assert.deepEqual(queries, [], "Saved View refresh must not reload a broader query");
});
