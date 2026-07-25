import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-py-data">{}</script>
  <script type="application/json" id="peval-py-token-estimates">{}</script>
  <script type="application/json" id="peval-py-i18n">{}</script>
  <script type="application/json" id="peval-py-render-options">{"mode":"serve","sources":[]}</script>
  <div id="table-root"></div>
  <button id="outside">Outside</button>
  <div class="workspace-main-scroll" data-workspace-main-scroll></div>
  <section id="leaderboard-summary"></section>
  <aside id="workspace-views" hidden></aside>
`);

const tables = await import("../src/modules/data-tables.js");
const runtime = await import("../src/modules/runtime.js");
const sourceManager = await import("../src/modules/source-manager.js");
const views = await import("../src/modules/workspace-views.js");

const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test.after(() => browser.cleanup());

test("value types drive cell metadata, truncation classes, sorting, and read-only behavior", () => {
  const row = {
    id: "row-1",
    number: 12,
    datetime: 1_725_000_000_000,
    status: "passed",
    enum: "agent",
    text: "a long text value",
    list: ["alpha", "beta"],
    scalarList: ["Safety, Eval", "Regression"],
    identity: "session-1",
    path: "/tmp/a/long/path",
    markdown: "first line\nsecond line\nthird line",
    yaml: "state: active\n",
  };
  const columns = [
    { key: "number", label: "Number", valueType: "number", sortable: true, value: item => item.number },
    { key: "datetime", label: "Datetime", valueType: "datetime", sortable: true, value: item => item.datetime },
    { key: "status", label: "Status", valueType: "status", value: item => item.status },
    { key: "enum", label: "Enum", valueType: "enum", value: item => item.enum },
    { key: "text", label: "Text", valueType: "text", value: item => item.text },
    { key: "list", label: "List", valueType: "list", value: item => item.list.join(", ") },
    { key: "scalarList", label: "Scalar list", valueType: "scalar-list", value: item => item.scalarList.join(", ") },
    { key: "identity", label: "Identity", valueType: "identity", value: item => item.identity },
    { key: "path", label: "Path", valueType: "path", value: item => item.path },
    { key: "markdown", label: "Markdown", valueType: "markdown", value: item => item.markdown },
    { key: "yaml", label: "YAML", valueType: "yaml", value: item => item.yaml },
  ];
  const root = document.querySelector("#table-root");
  root.innerHTML = tables.renderDataTable({ tableId: "types", columns, rows: [row], rowKey: item => item.id });

  for (const column of columns) {
    const cell = root.querySelector(`[data-table-column-key="${column.key}"]`);
    assert.equal(cell.dataset.valueType, column.valueType);
    assert.equal(cell.classList.contains(`table-value-${column.valueType}`), true);
    assert.equal(cell.getAttribute("title"), String(column.value(row)));
    assert.equal(cell.getAttribute("aria-label"), String(column.value(row)));
    assert.equal(cell.hasAttribute("tabindex"), false);
  }
  assert.equal(tables.tableSortType(columns[0]), "number");
  assert.equal(tables.tableSortType(columns[1]), "number");
  assert.equal(tables.tableSortType(columns[4]), "text");
  assert.equal(tables.compareTableValues(2, 11, "number", "asc"), -9);
  assert.deepEqual(tables.normalizeTableListValue(" alpha， beta,alpha, ,gamma "), ["alpha", "beta", "gamma"]);
  assert.deepEqual(
    tables.normalizeTableScalarListValue([" Safety, Eval ", "Regression", "Safety, Eval"]),
    ["Safety, Eval", "Regression"],
  );
});

function mountEditor(valueType, { value = "draft", options, suggestions, commit }) {
  const root = document.querySelector("#table-root");
  const row = { id: `row-${valueType}`, value };
  const columns = [{
    key: "value",
    label: valueType,
    valueType,
    value: item => Array.isArray(item.value) ? item.value.join(", ") : item.value,
    edit: { value: item => item.value, options, suggestions, commit },
  }];
  const render = () => {
    root.innerHTML = tables.renderDataTable({ tableId: `edit-${valueType}`, columns, rows: [row], rowKey: item => item.id });
    tables.bindDataTableControls(root, { tableId: `edit-${valueType}`, columns, rows: [row], rowKey: item => item.id, onChange: render });
  };
  render();
  const cell = root.querySelector("[data-table-column-key=value]");
  cell.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
  return { root, row, columns, cell, input: cell.querySelector(".table-cell-editor-control") };
}

test("text, enum, markdown, and yaml editors share keyboard, blur, and cancel semantics", async () => {
  const commits = [];
  let mounted = mountEditor("text", { commit: async (_row, value) => commits.push(["text", value]) });
  mounted.input.value = "  renamed  ";
  mounted.input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  await tick();
  assert.deepEqual(commits.pop(), ["text", "renamed"]);
  assert.equal(document.activeElement.dataset.tableColumnKey, "value");

  mounted = mountEditor("text", { commit: async (_row, value) => commits.push(["blur", value]) });
  mounted.input.value = "blurred";
  document.querySelector("#outside").focus();
  await tick();
  await tick();
  assert.deepEqual(commits.pop(), ["blur", "blurred"]);

  mounted = mountEditor("enum", {
    value: "agent",
    options: [{ value: "agent", label: "Agent" }, { value: "model", label: "Model" }],
    commit: async (_row, value) => commits.push(["enum", value]),
  });
  mounted.input.value = "model";
  mounted.input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  await tick();
  assert.deepEqual(commits.pop(), ["enum", "model"]);

  mounted = mountEditor("markdown", { value: "notes", commit: async (_row, value) => commits.push(["markdown", value]) });
  mounted.input.value = "updated notes";
  mounted.input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  assert.equal(commits.length, 0);
  document.querySelector("#outside").focus();
  await tick();
  assert.equal(commits.length, 0);
  mounted.input.focus();
  mounted.input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", ctrlKey: true, bubbles: true }));
  await tick();
  assert.deepEqual(commits.pop(), ["markdown", "updated notes"]);

  mounted = mountEditor("yaml", { value: "state: active\n", commit: async (_row, value) => commits.push(["yaml", value]) });
  mounted.input.value = "state: archived\n";
  mounted.cell.querySelector(".table-cell-editor-actions .primary").click();
  await tick();
  assert.deepEqual(commits.pop(), ["yaml", "state: archived\n"]);

  mounted = mountEditor("text", { commit: async (_row, value) => commits.push(["cancelled", value]) });
  mounted.input.value = "discard me";
  mounted.input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  await tick();
  assert.equal(commits.length, 0);
  assert.equal(document.activeElement, mounted.cell);
});

test("list suggestions normalize values and editor events do not select the row", async () => {
  let rowClicks = 0;
  let committed = null;
  const mounted = mountEditor("list", {
    value: ["alpha"],
    suggestions: ["alpha", "beta"],
    commit: async (_row, value) => { committed = value; },
  });
  mounted.cell.closest("tr").addEventListener("click", () => { rowClicks += 1; });
  mounted.cell.querySelector('[data-table-suggestion="beta"]').click();
  mounted.input.value += "， alpha, gamma";
  mounted.input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  await tick();
  assert.deepEqual(committed, ["alpha", "beta", "gamma"]);
  assert.equal(rowClicks, 0);
});

test("scalar suggestions replace the value while custom text and blank clears remain valid", async () => {
  const commits = [];
  let mounted = mountEditor("text", {
    value: "Alpha",
    suggestions: ["Alpha", "Beta"],
    commit: async (_row, value) => commits.push(value),
  });
  mounted.cell.querySelector('[data-table-suggestion="Beta"]').click();
  assert.equal(mounted.input.value, "Beta");
  assert.equal(mounted.cell.querySelector('[data-table-suggestion="Alpha"]').getAttribute("aria-pressed"), "false");
  assert.equal(mounted.cell.querySelector('[data-table-suggestion="Beta"]').getAttribute("aria-pressed"), "true");
  mounted.input.value = "Custom category";
  mounted.input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  await tick();
  assert.deepEqual(commits, ["Custom category"]);

  mounted = mountEditor("text", {
    value: "Alpha",
    suggestions: ["Alpha", "Beta"],
    commit: async (_row, value) => commits.push(value),
  });
  mounted.input.value = "   ";
  mounted.input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  await tick();
  assert.deepEqual(commits, ["Custom category", ""]);
});

test("pending and failed saves preserve the editor value, error, and focus", async () => {
  let rejectCommit;
  const pending = new Promise((_resolve, reject) => { rejectCommit = reject; });
  const mounted = mountEditor("text", { value: "original", commit: () => pending });
  mounted.input.value = "unsaved input";
  mounted.input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  assert.equal(mounted.cell.querySelector("[data-table-cell-editor]").getAttribute("aria-busy"), "true");
  assert.equal(mounted.input.disabled, true);
  rejectCommit(new Error("write failed"));
  await tick();
  assert.equal(mounted.input.value, "unsaved input");
  assert.equal(mounted.input.disabled, false);
  assert.match(mounted.cell.querySelector(".table-cell-editor-status").textContent, /write failed/);
  assert.equal(document.activeElement, mounted.input);
});

test("saved views close and reopen without losing independent scroll state", async () => {
  runtime.state.workspaceViews = [{ name: "One", filters: {}, group_by: "agent", notes: "" }];
  runtime.state.workspaceViewSummaries = [{ name: "One", matched_count: 0, groups: [] }];
  runtime.state.workspaceViewsLoaded = true;
  runtime.state.workspaceViewsClosed = false;
  views.renderWorkspaceViewRail();

  const analysis = document.querySelector("[data-workspace-main-scroll]");
  const index = document.querySelector("#workspace-views .workspace-view-index-shell .table-wrap");
  const cards = document.querySelector("#workspace-views [data-workspace-view-list]");
  analysis.scrollTop = 31;
  index.scrollTop = 17;
  index.scrollLeft = 9;
  cards.scrollTop = 23;
  document.querySelector("[data-workspace-views-close]").click();

  assert.equal(runtime.state.workspaceViewsClosed, true);
  assert.equal(document.querySelector("#workspace-views").hidden, true);
  assert.equal(document.body.classList.contains("workspace-views-open"), false);
  assert.deepEqual(runtime.state.workspaceViewScroll, { analysisTop: 31, indexTop: 17, indexLeft: 9, cardsTop: 23 });
  assert.ok(document.querySelector("[data-workspace-views-open]"));

  document.querySelector("[data-workspace-views-open]").click();
  assert.equal(runtime.state.workspaceViewsClosed, false);
  assert.equal(document.querySelector("#workspace-views").hidden, false);
  assert.equal(document.body.classList.contains("workspace-views-open"), true);
  assert.equal(document.querySelector("#workspace-views .workspace-view-index-shell .table-wrap").scrollTop, 17);
  assert.equal(document.querySelector("#workspace-views [data-workspace-view-list]").scrollTop, 23);
  assert.equal(document.activeElement, document.querySelector("[data-workspace-views-close]"));
  await tick();
});

test("source and saved-view adapters keep persistence behind the shared edit seam", async () => {
  const calls = [];
  const originalFetch = globalThis.fetch;
  const response = payload => ({
    ok: true,
    statusText: "OK",
    async text() { return JSON.stringify(payload); },
  });
  globalThis.fetch = async (url, options = {}) => {
    const path = String(url);
    const body = options.body ? JSON.parse(options.body) : null;
    calls.push({ path, method: options.method || "GET", body });
    if (path.includes("/api/sources/source-1/category")) return response({ generation: 2, change: "category", source_keys: ["source-1"] });
    if (path.includes("/api/sources/source-1/tags")) return response({});
    if (path.includes("/api/catalog?")) return response({ items: [], page: 1, page_size: 100, total: 0, generation: 0, checking: false, facets: { categories: [{ value: "Evaluation", count: 1 }] } });
    if (path === "/api/views/update") {
      const updated = { name: "Daily", filters: { tags: ["daily", "nightly"], results: ["passed"] }, group_by: "agent", notes: "Note" };
      return response({ view: updated, views: [updated] });
    }
    if (path === "/api/views") return response({ views: runtime.state.workspaceViews });
    if (path === "/api/views/summary") return response({ views: [], generation: 0 });
    throw new Error(`unexpected request: ${path}`);
  };
  window.fetch = globalThis.fetch;

  const leaderboardColumns = tables.leaderboardColumns();
  const managerColumns = sourceManager.sourceColumns();
  const leaderboardTags = leaderboardColumns.find(column => column.key === "source_tags");
  const managerTags = managerColumns.find(column => column.key === "source_tags");
  const leaderboardCategory = leaderboardColumns.find(column => column.key === "source_category");
  const managerCategory = managerColumns.find(column => column.key === "source_category");
  assert.deepEqual(leaderboardColumns.slice(0, 2).map(column => column.key), ["source_category", "source_tags"]);
  assert.equal(managerColumns.indexOf(managerCategory) + 1, managerColumns.indexOf(managerTags));
  assert.equal(leaderboardCategory.valueType, "text");
  assert.equal(managerCategory.valueType, "text");
  assert.equal(leaderboardTags.valueType, "list");
  assert.equal(managerTags.valueType, "list");
  assert.equal(typeof leaderboardCategory.edit.commit, "function");
  assert.equal(typeof managerCategory.edit.commit, "function");
  assert.equal(typeof leaderboardTags.edit.commit, "function");
  assert.equal(typeof managerTags.edit.commit, "function");
  await managerTags.edit.commit({ source_key: "source-1", trial_key: "trial-1" }, ["green", "blue"]);
  assert.deepEqual(calls[0], {
    path: "/api/sources/source-1/tags",
    method: "POST",
    body: { report_source_state: "active", tags: ["green", "blue"] },
  });
  runtime.state.sourceCategoryOptions = ["Evaluation", "Regression"];
  assert.deepEqual(managerCategory.edit.suggestions(), ["Evaluation", "Regression"]);
  await managerCategory.edit.commit({ source_key: "source-1", trial_key: "trial-1" }, "  Evaluation  ");
  assert.deepEqual(calls.find(call => call.path === "/api/sources/source-1/category"), {
    path: "/api/sources/source-1/category",
    method: "POST",
    body: { category: "Evaluation" },
  });

  runtime.state.workspaceViews = [{ name: "Daily", filters: { results: ["passed"] }, group_by: "agent", notes: "Note" }];
  runtime.state.workspaceViewsLoaded = true;
  runtime.state.workspaceViewsRefreshVersion = 0;
  runtime.state.workspaceViewsRefreshPromise = null;
  runtime.state.workspaceViewsRefreshQueued = false;
  const view = views.workspaceViewForName("Daily");
  await views.commitWorkspaceViewCellEdit(view, "tags", ["daily", "nightly"]);
  const update = calls.find(call => call.path === "/api/views/update");
  assert.equal(update.body.field, "configuration");
  assert.match(update.body.value, /tags:\n    - "daily"\n    - "nightly"/);
  assert.match(update.body.value, /results:\n    - "passed"/);

  const columns = views.workspaceViewColumns();
  assert.deepEqual(columns.filter(column => column.edit).map(column => [column.key, column.valueType]), [
    ["name", "text"],
    ["categories", "scalar-list"],
    ["tags", "list"],
    ["models", "list"],
    ["group_by", "enum"],
    ["other_conditions", "yaml"],
    ["notes", "markdown"],
  ]);
  await tick();
  globalThis.fetch = originalFetch;
  window.fetch = originalFetch;
});

test("Saved View Category editing preserves a scalar value containing a comma", async () => {
  const calls = [];
  const originalFetch = globalThis.fetch;
  const view = {
    name: "Comma category",
    filters: { categories: ["Safety, Eval"] },
    group_by: "category",
    notes: "",
  };
  const response = payload => ({
    ok: true,
    statusText: "OK",
    async text() { return JSON.stringify(payload); },
  });
  globalThis.fetch = async (url, options = {}) => {
    const path = String(url);
    const body = options.body ? JSON.parse(options.body) : null;
    calls.push({ path, body });
    if (path === "/api/views/update") return response({ view, views: [view] });
    if (path === "/api/views") return response({ views: [view] });
    if (path === "/api/views/summary") return response({ views: [], generation: 1 });
    throw new Error(`unexpected request: ${path}`);
  };
  window.fetch = globalThis.fetch;

  try {
    runtime.state.workspaceViews = [view];
    runtime.state.workspaceViewsLoaded = true;
    runtime.state.workspaceViewsRefreshPromise = null;
    runtime.state.workspaceViewsRefreshQueued = false;
    const column = views.workspaceViewColumns().find(item => item.key === "categories");
    const root = document.querySelector("#table-root");
    root.innerHTML = tables.renderDataTable({
      tableId: "saved-view-category-comma",
      columns: [column],
      rows: [view],
      rowKey: item => item.name,
    });
    tables.bindDataTableEditors(root, {
      tableId: "saved-view-category-comma",
      columns: [column],
      rows: [view],
      rowKey: item => item.name,
    });
    const cell = root.querySelector('[data-table-column-key="categories"]');
    cell.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
    const input = cell.querySelector(".table-cell-editor-control");
    assert.equal(input.value, "");
    assert.equal(
      cell.querySelector('[data-table-suggestion="Safety, Eval"]').getAttribute("aria-pressed"),
      "true",
    );
    input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    for (let index = 0; index < 5; index += 1) await tick();

    const update = calls.find(call => call.path === "/api/views/update");
    assert.match(update.body.value, /categories:\n    - "Safety, Eval"/);
    assert.doesNotMatch(update.body.value, /categories:\n    - "Safety"\n    - "Eval"/);
  } finally {
    globalThis.fetch = originalFetch;
    window.fetch = originalFetch;
    runtime.state.workspaceViews = [];
    runtime.state.workspaceViewsLoaded = false;
    runtime.state.workspaceViewsRefreshPromise = null;
    runtime.state.workspaceViewsRefreshQueued = false;
  }
});
