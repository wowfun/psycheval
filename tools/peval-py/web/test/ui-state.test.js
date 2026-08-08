import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-py-data">{}</script>
  <script type="application/json" id="peval-py-token-estimates">{}</script>
  <script type="application/json" id="peval-py-i18n">{}</script>
  <script type="application/json" id="peval-py-render-options">{"mode":"serve","sources":[]}</script>
  <strong data-source-count></strong>
  <span data-source-status></span>
  <div data-source-manager hidden><section aria-modal="true"><button data-source-manager-close>Close</button><p data-source-manager-status hidden></p><ul data-source-list></ul></section></div>
  <div data-report-manager hidden><section aria-modal="true"><button data-report-manager-close>Close</button><p data-report-manager-status hidden></p><div data-report-inventory></div><span data-report-count></span><div data-report-bindings></div></section></div>
  <aside id="workspace-report-reader" hidden></aside>
  <div data-view-save-dialog hidden><section aria-modal="true"><button data-view-save-cancel>Cancel</button></section></div>
  <button data-refresh-all>Refresh</button>
  <button data-source-bulk-state disabled>Archive</button>
  <button data-source-bulk-delete disabled>Delete</button>
  <main id="comparison"></main>
  <section id="leaderboard"></section>
`);

const runtime = await import("../src/modules/runtime.js");
const sourceManager = await import("../src/modules/source-manager.js");
const serveEffects = await import("../src/modules/serve-effects.js");
const catalog = await import("../src/modules/serve-catalog.js");
const leaderboardSummary = await import("../src/modules/leaderboard-summary.js");
const modals = await import("../src/modules/modal-surfaces.js");
const reports = await import("../src/modules/workspace-reports.js");
const views = await import("../src/modules/workspace-views.js");
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test.after(() => browser.cleanup());

test("Saved View Category groups preserve a literal overall category", () => {
  const group = { key: "overall", label: "overall" };
  assert.equal(views.workspaceViewGroupLabel(group, "category"), "overall");
  assert.equal(views.workspaceViewGroupLabel(group, "overall"), "Overall");
});

test("Source Manager renders its own page instead of the Leaderboard page", () => {
  runtime.state.serveSources = [];
  runtime.state.sourceManagerRows = [{
    source_key: "source-one",
    label: "runs/source-one",
    active: true,
    readable: true,
  }];
  runtime.state.sourceManagerStatus = { phase: "ready", message: "" };
  sourceManager.renderServeSources();

  assert.match(document.querySelector("[data-source-list]").textContent, /runs\/source-one/);
  assert.doesNotMatch(document.querySelector("[data-source-list]").textContent, /No sources loaded/);

  runtime.state.sourceManagerStatus = { phase: "loading", message: "Loading" };
  sourceManager.renderServeSources();
  assert.match(document.querySelector("[data-source-list]").textContent, /Loading/);

  runtime.state.sourceManagerRows = [];
  runtime.state.sourceManagerStatus = { phase: "error", message: "Catalog failed" };
  sourceManager.renderServeSources();
  assert.match(document.querySelector("[data-source-list]").textContent, /Catalog failed/);
});

test("Source Manager derives a cross-page batch state from every selected source", async () => {
  const requests = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => {
    requests.push({ path: String(path), body: JSON.parse(String(options.body || "{}")) });
    return {
      ok: true,
      statusText: "OK",
      text: async () => "{",
    };
  };

  try {
    runtime.state.sourceSelection.clear();
    runtime.state.sourceManagerStatus = { phase: "ready", message: "" };
    runtime.state.sourceManagerRows = [{
      source_key: "archived-on-page-one",
      label: "Archived on page one",
      active: false,
      readable: true,
    }];
    runtime.state.sourceSelection.add("archived-on-page-one");
    sourceManager.renderServeSources();
    assert.equal(
      document.querySelector("[data-source-bulk-state]").dataset.sourceBulkState,
      "active",
    );

    runtime.state.sourceManagerRows = [{
      source_key: "active-on-page-two",
      label: "Active on page two",
      active: true,
      readable: true,
    }];
    sourceManager.renderServeSources();

    const stateButton = document.querySelector("[data-source-bulk-state]");
    assert.equal(stateButton.textContent, "Activate selected");
    assert.equal(stateButton.dataset.sourceBulkState, "active");
    await serveEffects.mutateSelectedServeSourceState();
    assert.deepEqual(requests, [{
      path: "/api/sources/state",
      body: {
        source_keys: ["archived-on-page-one"],
        active: true,
        report_source_state: "active",
      },
    }]);
  } finally {
    globalThis.fetch = previousFetch;
    runtime.state.sourceSelection.clear();
    runtime.state.sourceManagerRows = [];
    runtime.state.sourceManagerStatus = { phase: "ready", message: "" };
    sourceManager.renderServeSources();
  }
});

test("Source Manager disables deletion when the selection includes a linked Harbor Trial", () => {
  runtime.state.sourceSelection.clear();
  runtime.state.sourceManagerStatus = { phase: "ready", message: "" };
  runtime.state.sourceManagerRows = [{
    source_key: "linked-harbor",
    kind: "harbor-trial",
    label: "jobs/job/trial",
    active: true,
    readable: true,
  }];
  runtime.state.sourceSelection.add("linked-harbor");
  sourceManager.renderServeSources();

  const deleteButton = document.querySelector("[data-source-bulk-delete]");
  assert.equal(deleteButton.disabled, true);
  assert.match(deleteButton.title, /cannot be deleted/);

  runtime.state.sourceSelection.clear();
  runtime.state.sourceManagerRows = [];
  sourceManager.renderServeSources();
});

test("workspace busy state disables and restores controls", () => {
  const refresh = document.querySelector("[data-refresh-all]");
  const bulk = document.querySelector("[data-source-bulk-state]");
  refresh.disabled = false;
  bulk.disabled = true;

  catalog.setWorkspaceWriteControlsDisabled(true);
  assert.equal(refresh.disabled, true);
  assert.equal(refresh.getAttribute("aria-busy"), "true");

  catalog.setWorkspaceWriteControlsDisabled(false);
  assert.equal(refresh.disabled, false);
  assert.equal(refresh.hasAttribute("aria-busy"), false);
  assert.equal(bulk.disabled, true);
});

test("Category filters are multi-select while editor suggestions come from an independent all-workspace facet", async () => {
  const previousFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async path => {
    calls.push(String(path));
    return {
      ok: true,
      statusText: "OK",
      text: async () => JSON.stringify({
        items: [],
        page: 1,
        page_size: 1,
        total: 0,
        generation: 1,
        checking: false,
        facets: {
          categories: [
            { value: "Regression", count: 4 },
            { value: "Evaluation", count: 2 },
          ],
        },
      }),
    };
  };

  try {
    runtime.state.catalogQuery.categories = ["Evaluation", "Regression"];
    const params = new URLSearchParams(catalog.catalogQueryString());
    assert.deepEqual(params.getAll("category"), ["Evaluation", "Regression"]);

    runtime.state.catalogPage.facets = {
      categories: [
        { value: "Regression", count: 4 },
        { value: "Evaluation", count: 2 },
      ],
    };
    assert.deepEqual(catalog.filterOptions({
      key: "source_category",
      value: row => row.source_category,
    }, []), ["Regression", "Evaluation"]);

    await catalog.refreshSourceCategoryOptions();
    assert.deepEqual(runtime.state.sourceCategoryOptions, ["Regression", "Evaluation"]);
    const suggestionRequest = new URL(calls[0], "http://localhost");
    assert.equal(suggestionRequest.pathname, "/api/catalog");
    assert.equal(suggestionRequest.searchParams.get("state"), "all");
    assert.equal(suggestionRequest.searchParams.get("search"), "");
    assert.deepEqual(suggestionRequest.searchParams.getAll("category"), []);
    assert.deepEqual(suggestionRequest.searchParams.getAll("tag"), []);
  } finally {
    globalThis.fetch = previousFetch;
    runtime.state.catalogQuery.categories = [];
    runtime.state.sourceCategoryOptions = [];
  }
});

test("Category suggestions refresh when the initial catalog scan completes", async () => {
  const previousFetch = globalThis.fetch;
  const previousSetTimeout = globalThis.setTimeout;
  const scheduled = [];
  let catalogPageRequests = 0;
  let suggestionRequests = 0;
  const response = payload => ({
    ok: true,
    statusText: "OK",
    text: async () => JSON.stringify(payload),
  });
  globalThis.setTimeout = callback => {
    scheduled.push(callback);
    return scheduled.length;
  };
  globalThis.fetch = async path => {
    const request = new URL(String(path), "http://localhost");
    const suggestions = request.searchParams.get("page_size") === "1";
    if (suggestions) {
      suggestionRequests += 1;
      return response({
        items: [],
        page: 1,
        page_size: 1,
        total: 0,
        generation: suggestionRequests === 1 ? 0 : 1,
        checking: suggestionRequests === 1,
        facets: {
          categories: suggestionRequests === 1
            ? []
            : [{ value: "Regression", count: 1 }],
        },
      });
    }
    catalogPageRequests += 1;
    return response({
      items: [],
      page: 1,
      page_size: 100,
      total: 0,
      generation: catalogPageRequests === 1 ? 0 : 1,
      checking: catalogPageRequests === 1,
      facets: {
        categories: catalogPageRequests === 1
          ? []
          : [{ value: "Regression", count: 1 }],
      },
    });
  };

  try {
    runtime.state.catalogLoading = false;
    runtime.state.catalogPage = {
      generation: 0,
      total: 0,
      page: 1,
      page_size: 100,
      facets: {},
      checking: true,
    };
    runtime.state.catalogRows = [];
    runtime.state.serveSources = [];
    runtime.state.sourceCategoryOptions = [];
    runtime.state.workspaceViews = [];
    runtime.state.workspaceViewsLoaded = true;
    await Promise.all([
      catalog.loadCatalogPage(),
      catalog.refreshSourceCategoryOptions(),
    ]);
    assert.deepEqual(runtime.state.sourceCategoryOptions, []);
    assert.equal(scheduled.length, 1);

    await scheduled.shift()();

    assert.deepEqual(runtime.state.sourceCategoryOptions, ["Regression"]);
  } finally {
    globalThis.fetch = previousFetch;
    globalThis.setTimeout = previousSetTimeout;
    runtime.state.catalogLoading = false;
    runtime.state.catalogRows = [];
    runtime.state.serveSources = [];
    runtime.state.sourceCategoryOptions = [];
    runtime.state.workspaceViewsLoaded = false;
  }
});

test("Category grouping keeps missing values separate from a literal dash category", () => {
  const groups = leaderboardSummary.leaderboardSummaryGroups([
    { source_category: null },
    { source_category: "-" },
  ], "category");
  assert.deepEqual(
    groups.map(group => [group.key, group.label, group.rows.length]),
    [[null, "-", 1], ["-", "-", 1]],
  );
});

test("modal surfaces are mutually exclusive and restore focus", () => {
  const opener = document.createElement("button");
  document.body.append(opener);
  opener.focus();
  const source = document.querySelector("[data-source-manager]");
  const report = document.querySelector("[data-report-manager]");

  modals.openModalSurface(source, {
    opener,
    bodyClass: "source-manager-open",
    focusTarget: source.querySelector("button"),
  });
  assert.equal(source.hidden, false);
  assert.equal(document.activeElement, source.querySelector("button"));

  modals.openModalSurface(report, {
    opener,
    bodyClass: "report-manager-open",
    focusTarget: report.querySelector("button"),
  });
  assert.equal(source.hidden, true);
  assert.equal(report.hidden, false);

  modals.closeModalSurface(report);
  assert.equal(document.activeElement, opener);
});

test("Reports Manager distinguishes loading from empty and clears old errors", () => {
  runtime.state.workspaceReports = [];
  runtime.state.reportManager.loading = true;
  runtime.state.reportManager.busy = false;
  reports.renderWorkspaceReportManager();
  assert.match(document.querySelector("[data-report-inventory]").textContent, /Loading/);
  assert.equal(document.querySelector("[data-report-manager]").getAttribute("aria-busy"), "true");

  runtime.state.reportManager.loading = false;
  reports.setWorkspaceReportManagerStatus("Old error", true);
  reports.setWorkspaceReportManagerStatus("");
  assert.equal(document.querySelector("[data-report-manager-status]").hidden, true);
});

test("serve startup loads existing report bindings for Leaderboard cells", async () => {
  const previousFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async path => {
    calls.push(String(path));
    return {
      ok: true,
      statusText: "OK",
      text: async () => JSON.stringify({
        reports: [{
          report_id: "20260720-120000-000000",
          filename: "startup-analysis.md",
          format: "markdown",
          source_keys: ["session-1"],
        }],
      }),
    };
  };

  try {
    runtime.state.workspaceReports = [];
    await reports.refreshWorkspaceReports({ renderLeaderboard: false });

    assert.deepEqual(calls, ["/api/reports"]);
    assert.match(
      reports.renderWorkspaceReportCell({ source_key: "session-1" }),
      /startup-analysis\.md/,
    );
  } finally {
    globalThis.fetch = previousFetch;
    runtime.state.workspaceReports = [];
  }
});

test("a session with multiple reports lets each report open from the Leaderboard", () => {
  const target = document.createElement("div");
  document.body.append(target);
  try {
    runtime.state.workspaceReports = [
      {
        report_id: "20260725-130000-000000",
        filename: "newer-analysis.md",
        format: "markdown",
        source_keys: ["session-1"],
      },
      {
        report_id: "20260725-120000-000000",
        filename: "older-analysis.html",
        format: "html",
        source_keys: ["session-1"],
      },
    ];
    target.innerHTML = reports.renderWorkspaceReportCell({ source_key: "session-1" });
    reports.bindWorkspaceReportLeaderboardControls(target);

    const picker = target.querySelector("[data-report-preview-select]");
    assert.ok(picker);
    assert.deepEqual(
      Array.from(picker.options, option => option.textContent),
      ["2 reports", "newer-analysis.md", "older-analysis.html"],
    );

    for (const [reportId, filename] of [
      ["20260725-130000-000000", "newer-analysis.md"],
      ["20260725-120000-000000", "older-analysis.html"],
      ["20260725-120000-000000", "older-analysis.html"],
    ]) {
      picker.value = reportId;
      picker.dispatchEvent(new window.Event("change", { bubbles: true }));

      assert.equal(runtime.state.reportReader.openId, reportId);
      assert.equal(document.querySelector("#workspace-report-reader h2").textContent, filename);
      assert.equal(picker.value, "");
      reports.closeWorkspaceReportReader({ restoreFocus: false });
    }
  } finally {
    reports.closeWorkspaceReportReader({ restoreFocus: false });
    runtime.state.workspaceReports = [];
    target.remove();
  }
});

test("Reports Manager keeps the session list stable when a middle binding changes", () => {
  const manager = document.querySelector("[data-report-manager]");
  manager.hidden = false;
  runtime.state.workspaceReports = [{
    report_id: "20260719-120000-000000",
    filename: "analysis.html",
    format: "html",
    source_keys: [],
  }];
  runtime.state.reportManager.selectedId = "20260719-120000-000000";
  runtime.state.reportManager.sourceRows = Array.from({ length: 30 }, (_, index) => ({
    source_key: `session-${index + 1}`,
    label: `Session ${index + 1}`,
    trial_session_id: `trial-${index + 1}`,
    active: true,
    readable: true,
  }));
  runtime.state.reportManager.draftBindings = new Set();
  runtime.state.reportManager.loading = false;
  runtime.state.reportManager.busy = false;
  reports.renderWorkspaceReportManager();

  const list = document.querySelector("[data-report-binding-list]");
  const checkbox = list.querySelector('[data-report-binding-key="session-20"]');
  list.scrollTop = 240;
  checkbox.focus();
  checkbox.checked = true;
  checkbox.dispatchEvent(new window.Event("change", { bubbles: true }));

  assert.equal(document.querySelector("[data-report-binding-list]"), list);
  assert.equal(list.scrollTop, 240);
  assert.equal(document.activeElement, checkbox);
  assert.equal(document.querySelector("[data-report-bindings-save]").disabled, false);

  manager.hidden = true;
  runtime.state.reportManager.sourceRows = [];
});

test("Reports Manager Category editing preserves binding draft, page, search, list scroll, and focus", async () => {
  const previousFetch = globalThis.fetch;
  const requests = [];
  const manager = document.querySelector("[data-report-manager]");
  const reportId = "20260725-135000-000000";
  const source = {
    source_key: "session-category",
    label: "Unrelated session",
    trial_session_id: "trial-category",
    source_category: "Evaluation",
    source_tags: ["nightly"],
    active: true,
    readable: true,
  };
  globalThis.fetch = async (path, options = {}) => {
    const requestPath = String(path);
    requests.push({
      path: requestPath,
      body: options.body ? JSON.parse(String(options.body)) : null,
    });
    if (requestPath === `/api/sources/${source.source_key}/category`) {
      return {
        ok: true,
        statusText: "OK",
        text: async () => JSON.stringify({
          generation: 2,
          change: "category",
          source_keys: [source.source_key],
        }),
      };
    }
    if (requestPath.startsWith("/api/catalog?")) {
      return {
        ok: true,
        statusText: "OK",
        text: async () => JSON.stringify({
          items: [],
          page: 1,
          page_size: 100,
          total: 0,
          generation: 2,
          checking: false,
          facets: { categories: [{ value: "Regression", count: 1 }] },
        }),
      };
    }
    throw new Error(`unexpected request: ${requestPath}`);
  };

  try {
    manager.hidden = false;
    runtime.state.workspaceReports = [{
      report_id: reportId,
      filename: "category-analysis.md",
      format: "markdown",
      source_keys: [],
    }];
    runtime.state.reportManager.selectedId = reportId;
    runtime.state.reportManager.sourceRows = [source];
    runtime.state.reportManager.draftBindings = new Set([source.source_key]);
    runtime.state.reportManager.dirty = true;
    runtime.state.reportManager.search = "evaluation";
    runtime.state.reportManager.page = 3;
    runtime.state.reportManager.pageData = { page: 3, page_size: 100, total: 250 };
    runtime.state.reportManager.loading = false;
    runtime.state.reportManager.busy = false;
    runtime.state.sourceCategoryOptions = ["Evaluation", "Regression"];
    assert.match(reports.workspaceReportSourceSearchText(source), /evaluation/);
    reports.renderWorkspaceReportManager();

    const list = document.querySelector("[data-report-binding-list]");
    const row = list.querySelector("[data-report-binding-row]");
    const checkbox = row.querySelector("[data-report-binding-key]");
    const categoryCell = row.querySelector("[data-report-binding-category]");
    list.scrollTop = 96;

    row.querySelector(".report-binding-row-main").click();
    assert.equal(checkbox.checked, false);
    row.querySelector(".report-binding-row-main").click();
    assert.equal(checkbox.checked, true);
    assert.deepEqual(Array.from(runtime.state.reportManager.draftBindings), [source.source_key]);

    categoryCell.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
    const editor = categoryCell.querySelector("[data-table-cell-editor]");
    const input = editor.querySelector(".table-cell-editor-control");
    editor.querySelector('[data-table-suggestion="Regression"]').click();
    assert.equal(input.value, "Regression");
    assert.equal(checkbox.checked, true);
    assert.deepEqual(Array.from(runtime.state.reportManager.draftBindings), [source.source_key]);
    input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    for (let index = 0; index < 6; index += 1) await tick();

    assert.deepEqual(requests.find(request => request.path.endsWith("/category")), {
      path: `/api/sources/${source.source_key}/category`,
      body: { category: "Regression" },
    });
    assert.equal(document.querySelector("[data-report-binding-list]"), list);
    assert.equal(list.scrollTop, 96);
    assert.equal(runtime.state.reportManager.page, 3);
    assert.equal(runtime.state.reportManager.search, "evaluation");
    assert.deepEqual(Array.from(runtime.state.reportManager.draftBindings), [source.source_key]);
    assert.equal(checkbox.checked, true);
    assert.match(categoryCell.textContent, /Regression/);
    assert.equal(document.activeElement, categoryCell);
  } finally {
    globalThis.fetch = previousFetch;
    manager.hidden = true;
    runtime.state.workspaceReports = [];
    runtime.state.reportManager.selectedId = null;
    runtime.state.reportManager.search = "";
    runtime.state.reportManager.page = 1;
    runtime.state.reportManager.pageData = { page: 1, page_size: 100, total: 0 };
    runtime.state.reportManager.sourceRows = [];
    runtime.state.reportManager.draftBindings = new Set();
    runtime.state.reportManager.dirty = false;
    runtime.state.sourceCategoryOptions = [];
  }
});

test("clearing the final report binding immediately refreshes the rendered Leaderboard", async () => {
  const previousFetch = globalThis.fetch;
  const requests = [];
  const manager = document.querySelector("[data-report-manager]");
  const report = {
    report_id: "20260725-140000-000000",
    filename: "binding-analysis.md",
    format: "markdown",
    source_keys: ["session-a"],
  };
  const rows = [{
    source_key: "session-a",
    trial_key: "session-a",
    trial_session_id: "Session A",
    active: true,
    readable: true,
  }];
  globalThis.fetch = async (path, options = {}) => {
    requests.push({
      path: String(path),
      body: JSON.parse(String(options.body || "{}")),
    });
    return {
      ok: true,
      statusText: "OK",
      text: async () => JSON.stringify({
        reports: [{ ...report, source_keys: [] }],
      }),
    };
  };

  try {
    runtime.state.catalogRows = rows;
    runtime.state.catalogPage.generation = 1;
    runtime.state.workspaceReports = [report];
    runtime.state.reportManager.selectedId = report.report_id;
    runtime.state.reportManager.sourceRows = rows;
    runtime.state.reportManager.draftBindings = new Set(["session-a"]);
    runtime.state.reportManager.dirty = false;
    runtime.state.reportManager.loading = false;
    runtime.state.reportManager.busy = false;
    manager.hidden = false;
    runtime.renderComparisonPanels({ trace: false });

    const reportCell = sourceKey => document.querySelector(
      `[data-source-key="${sourceKey}"] [data-table-column-key="workspace_reports"]`,
    );
    assert.match(reportCell("session-a").textContent, /binding-analysis\.md/);
    reports.renderWorkspaceReportManager();
    const checkbox = document.querySelector('[data-report-binding-key="session-a"]');
    checkbox.checked = false;
    checkbox.dispatchEvent(new window.Event("change", { bubbles: true }));
    assert.equal(document.querySelector("[data-report-bindings-save]").disabled, false);

    await reports.saveWorkspaceReportBindings();

    assert.deepEqual(requests, [{
      path: `/api/reports/${report.report_id}/bindings`,
      body: { source_keys: [] },
    }]);
    assert.doesNotMatch(reportCell("session-a").textContent, /binding-analysis\.md/);
  } finally {
    globalThis.fetch = previousFetch;
    manager.hidden = true;
    runtime.state.catalogRows = [];
    runtime.state.catalogPage.generation = 0;
    runtime.state.workspaceReports = [];
    runtime.state.reportManager.selectedId = null;
    runtime.state.reportManager.sourceRows = [];
    runtime.state.reportManager.draftBindings = new Set();
    runtime.state.reportManager.dirty = false;
    runtime.state.reportManager.busy = false;
    document.querySelector("#leaderboard").innerHTML = "";
  }
});

test("HTML report previews fit an 1180px design viewport into the reader pane", () => {
  assert.deepEqual(reports.reportReaderPreviewGeometry(590, 700), {
    scale: 0.5,
    width: 1180,
    height: 1400,
  });
  assert.deepEqual(reports.reportReaderPreviewGeometry(1280, 700), {
    scale: 1,
    width: 1280,
    height: 700,
  });

  runtime.state.workspaceReports = [{
    report_id: "20260719-130000-000000",
    filename: "wide-report.html",
    format: "html",
    source_keys: ["session-1"],
  }];
  reports.openWorkspaceReportReader("20260719-130000-000000");
  const reader = document.querySelector("#workspace-report-reader");
  const viewport = reader.querySelector("[data-report-reader-viewport]");
  Object.defineProperties(viewport, {
    clientWidth: { configurable: true, value: 590 },
    clientHeight: { configurable: true, value: 700 },
  });
  reports.fitWorkspaceReportReaderPreview(reader);
  const frame = reader.querySelector("[data-report-reader-frame]");

  assert.equal(frame.style.width, "1180px");
  assert.equal(frame.style.height, "1400px");
  assert.equal(frame.style.transform, "scale(0.5)");
  reports.closeWorkspaceReportReader({ restoreFocus: false });
});
