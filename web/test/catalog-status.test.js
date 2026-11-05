import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin"}</script>
  <section id="leaderboard"><div class="leaderboard-action-row"><button data-catalog-refresh>Refresh</button></div>
    <p data-catalog-progress hidden></p><span data-catalog-phase role="status"></span><table><tbody><tr><td>Cached Trial</td></tr></tbody></table>
  </section>
`);
const catalog = await import("../../src/psycheval/assets/web/modules/serve-catalog.js");
const { state } = await import("../../src/psycheval/assets/web/modules/runtime.js");
const { RENDER_OPTIONS } = await import("../../src/psycheval/assets/web/modules/shared.js");
const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
const { setServeStatus } = await import("../../src/psycheval/assets/web/modules/serve-effects.js");

test.after(() => { catalog.stopCatalogStatusObservation(); browser.cleanup(); });

test("Refresh is offered only to administrators", () => {
  const previous = RENDER_OPTIONS.role;
  try {
    assert.match(catalog.renderLeaderboardPanelControls([]), /data-catalog-refresh/);
    state.workspaceWriteBusy = true;
    assert.match(catalog.renderLeaderboardPanelControls([]), /data-catalog-refresh disabled aria-busy="true"/);
    RENDER_OPTIONS.role = "guest";
    assert.doesNotMatch(catalog.renderLeaderboardPanelControls([]), /data-catalog-refresh/);
  } finally { RENDER_OPTIONS.role = previous; state.workspaceWriteBusy = false; }
});

test("equivalent API and column sort names retain the requested direction", async () => {
  const previousFetch = globalThis.fetch;
  const previous = { ...state.catalogQuery };
  state.workspaceViewsLoaded = true;
  globalThis.fetch = async () => new Response(JSON.stringify({
    generation: 7, checking: false, total: 0, items: [], facets: {}, page: 1, page_size: 100, effective_sort: "dataset",
  }));
  try {
    await catalog.loadCatalogPage({ sort: "dataset_id", direction: "asc" }, { skipDetail: true });
    assert.equal(state.catalogQuery.direction, "asc");
  } finally { globalThis.fetch = previousFetch; state.catalogQuery = previous; }
});

test("progress reads only lightweight status, survives other feedback, and stops away from Home", async () => {
  const previousFetch = globalThis.fetch, previousTimeout = globalThis.setTimeout;
  const scheduled = [], requests = [];
  let completed = 1;
  state.catalogLoading = false;
  state.catalogPage = { generation: 7, checking: true, total: 1000, page: 1, page_size: 100, facets: {} };
  globalThis.setTimeout = (callback, delay) => {
    if (delay === 250) { scheduled.push(callback); return 0; }
    return previousTimeout(callback, delay);
  };
  globalThis.fetch = async path => {
    requests.push(path);
    return new Response(JSON.stringify({ generation: 7, checking: true, phase: "checking", completed, total: 1000 }));
  };
  const action = beginFeedback("#leaderboard .leaderboard-action-row", { key: "test:export" });
  try {
    action.error("Export failed");
    await catalog.startCatalogStatusObservation();
    const progress = document.querySelector("[data-catalog-progress]");
    assert.equal(progress.textContent, "Checking trajectories: 1/1000");
    assert.equal(progress.hidden, false);
    assert.equal(document.querySelector("[data-catalog-refresh]").disabled, true);
    assert.match(document.querySelector("tbody").textContent, /Cached Trial/);
    setServeStatus("");
    assert.equal(progress.textContent, "Checking trajectories: 1/1000");
    const live = document.querySelector('[data-catalog-phase]');
    assert.equal(live.textContent, "Checking trajectories");
    const announced = live.firstChild;
    completed = 317;
    await scheduled.shift()();
    assert.equal(document.querySelector("[data-catalog-progress]"), progress);
    assert.equal(live.firstChild, announced);
    assert.match(progress.textContent, /317\/1000/);
    assert.match(document.querySelector(".leaderboard-action-row").textContent, /Export failed/);
    assert.deepEqual(requests, ["/api/catalog-status", "/api/catalog-status"]);
    window.dispatchEvent(new window.CustomEvent("peval:workspace-navigate", { detail: { to: "config" } }));
    await scheduled.shift()();
    assert.equal(requests.length, 2);
  } finally {
    action.dispose(); catalog.stopCatalogStatusObservation();
    globalThis.fetch = previousFetch; globalThis.setTimeout = previousTimeout;
  }
});

test("status read recovery never submits a refresh and restores the button", async () => {
  const previousFetch = globalThis.fetch;
  let fail = true;
  const methods = [];
  globalThis.fetch = async (path, options) => {
    methods.push(options?.method || "GET");
    if (fail) throw new Error("Status temporarily unavailable");
    return new Response(JSON.stringify({ generation: 7, checking: false, phase: "idle", completed: 1000, total: 1000 }));
  };
  try {
    await catalog.startCatalogStatusObservation();
    const feedback = document.querySelector('[data-action-feedback="home:catalog-status"]');
    assert.match(feedback.textContent, /Status temporarily unavailable/);
    fail = false;
    await catalog.startCatalogStatusObservation();
    assert.equal(document.querySelector("[data-catalog-progress]").hidden, true);
    assert.equal(document.querySelector("[data-catalog-refresh]").disabled, false);
    assert.deepEqual(methods, ["GET", "GET"]);
  } finally { catalog.stopCatalogStatusObservation(); globalThis.fetch = previousFetch; }
});

test("manual refresh keeps its busy gate through data refresh and shares operation progress", async () => {
  const { setWorkspaceApp } = await import("../../src/psycheval/assets/web/app/workspace-runtime.js");
  const previousFetch = globalThis.fetch;
  const requests = [];
  let finish, observed;
  const pending = new Promise(resolve => { finish = resolve; });
  const refreshed = new Promise(resolve => { observed = resolve; });
  globalThis.fetch = async path => {
    requests.push(String(path));
    if (path === "/api/source-discovery-operations") return new Response(JSON.stringify({ id: "refresh-gate" }));
    if (String(path).startsWith("/api/operations/")) return new Response(JSON.stringify({
      id: "refresh-gate", kind: "source-discovery", state: "succeeded",
      catalog_status: { generation: 8, checking: false, phase: "idle", completed: 2, total: 2 },
    }));
    if (path === "/api/catalog-status") return new Response(JSON.stringify({ generation: state.catalogPage.generation, checking: false, phase: "idle" }));
    return new Response(JSON.stringify({ generation: 8, checking: false, total: 0, items: [], facets: {}, page: 1, page_size: 100 }));
  };
  setWorkspaceApp({ invalidate() {}, async navigate() {
    await catalog.loadCatalogPage({}, { force: true, skipDetail: true });
    observed();
    await pending;
  } });
  try {
    await catalog.startCatalogStatusObservation();
    requests.length = 0;
    const action = catalog.refreshServeSourcesFromServer();
    await refreshed;
    assert.equal(document.querySelector("[data-catalog-refresh]").disabled, true);
    assert.equal(requests.filter(path => path === "/api/catalog-status").length, 0);
    finish();
    await action;
    assert.equal(document.querySelector("[data-catalog-refresh]").disabled, false);
    assert.equal(requests.filter(path => path === "/api/source-discovery-operations").length, 1);
    assert.equal(requests.filter(path => path === "/api/catalog-status").length, 1);
  } finally {
    finish(); catalog.stopCatalogStatusObservation(); setWorkspaceApp(null); globalThis.fetch = previousFetch;
  }
});

test("idle polls and page reads cannot unlock archive controls before submission and observation finish", async () => {
  const { mutateVisibleServeSourceState } = await import("../../src/psycheval/assets/web/modules/source-state-controls.js");
  const originalFetch = globalThis.fetch, originalTimeout = window.setTimeout;
  const page = {generation:7, checking:false, page:1, page_size:100, total:1, facets:{}, items:[{source_key:"selected", readable:true}]};
  const { setWorkspaceApp } = await import("../../src/psycheval/assets/web/app/workspace-runtime.js");
  let reloads = 0;
  setWorkspaceApp({ invalidate() {}, async navigate() { reloads++; }, locationChanged() {} });
  let accept, tick, writes = 0, operationReads = 0;
  const pendingPost = new Promise(resolve => { accept = resolve; });
  const control = document.createElement("button");
  control.dataset.sourceStateAction = "";
  document.querySelector(".leaderboard-action-row").append(control);
  state.catalogPage = page;
  state.catalogRows = page.items;
  state.rowSelection.add("selected");
  window.setTimeout = (fn, ms, ...args) => {
    if (ms === 250) { tick = fn; return 0; }
    return originalTimeout.call(window, fn, ms, ...args);
  };
  globalThis.fetch = async path => {
    if (path === "/api/source-state-operations") { writes++; await pendingPost; return Response.json({id:"archive-test"}); }
    if (path === "/api/operations/archive-test") return Response.json({
      state: ++operationReads === 1 ? "running" : "completed", kind:"archive", successes:[], completed:1, total:1,
    });
    if (path === "/api/catalog-status") return Response.json({checking:false, generation:7 + Number(operationReads > 0), operation_id:"archive-test", phase:"idle"});
    return Response.json(page);
  };
  try {
    await catalog.startCatalogStatusObservation();
    const archive = mutateVisibleServeSourceState();
    for (const phase of ["submitting", "observing"]) {
      if (phase === "observing") { accept(); await archive; }
      await catalog.startCatalogStatusObservation();
      await catalog.loadCatalogPage({}, {force:true, skipDetail:true});
      assert.equal(control.disabled, true, phase);
      await mutateVisibleServeSourceState();
      assert.equal(writes, 1);
    }
    assert.equal(reloads, 0);
    await tick();
    assert.equal(control.disabled, false);
  } finally {
    setWorkspaceApp(null); accept(); catalog.stopCatalogStatusObservation(); control.remove(); state.rowSelection.clear();
    window.setTimeout = originalTimeout; globalThis.fetch = originalFetch;
  }
});

test("a checking page restarts an idle observer, retries one failed status read, then offers manual retry", async () => {
  const originalFetch = globalThis.fetch, originalTimeout = globalThis.setTimeout;
  let reads = 0;
  const scheduled = [];
  let timerReady;
  const firstTimer = new Promise(resolve => { timerReady = resolve; });
  const page = {generation:7, checking:true, page:1, page_size:100, total:0, items:[], facets:{}};
  globalThis.setTimeout = (fn, ms) => {
    if (ms === 250) { scheduled.push(fn); timerReady(); return 0; }
    return originalTimeout(fn, ms);
  };
  globalThis.fetch = async path => {
    if (path === "/api/catalog-status") {
      if (++reads > 1) throw new Error("status unavailable");
      return Response.json({checking:false, generation:7, phase:"idle"});
    }
    return Response.json(page);
  };
  try {
    await catalog.startCatalogStatusObservation();
    await catalog.loadCatalogPage({}, {force:true, skipDetail:true});
    assert.equal(reads, 2);
    await firstTimer;
    assert.equal(scheduled.length, 1);
    await scheduled.shift()();
    assert.equal(scheduled.length, 0);
    assert.match(document.querySelector('[data-action-feedback="home:catalog-status"]').textContent, /status unavailable/);
  } finally {
    catalog.stopCatalogStatusObservation(); globalThis.fetch = originalFetch; globalThis.setTimeout = originalTimeout;
  }
});
