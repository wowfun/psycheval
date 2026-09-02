import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"guest","authentication_enabled":true,"sources":[]}</script>
  <button data-admin-login-open>Login</button>
  <div data-admin-login-dialog hidden>
    <section aria-modal="true">
      <button data-admin-login-close>Close</button>
      <form data-admin-login-form>
        <input name="password" type="password" value="wrong">
        <p data-admin-login-status hidden></p>
        <button type="submit">Login</button>
      </form>
    </section>
  </div>
  <div data-report-manager hidden><section aria-modal="true"><button data-report-manager-close>Close</button><p data-report-manager-status hidden></p><div data-report-inventory></div><span data-report-count></span><div data-report-bindings>stale admin content</div></section></div>
  <aside id="workspace-report-reader" hidden></aside>
  <section data-harbor-workbench>
    <button data-harbor-reload>Reload</button>
    <input data-harbor-search type="search">
    <span data-harbor-overview-count></span>
    <div data-harbor-overview></div>
    <h2 data-harbor-selected-title></h2>
    <span data-harbor-selected-meta></span>
    <p data-harbor-workbench-status hidden></p>
    <div data-harbor-file-actions hidden></div>
    <div data-harbor-file-tree></div>
    <strong data-harbor-editor-path></strong>
    <span data-harbor-editor-meta></span>
    <textarea data-harbor-editor disabled></textarea>
    <div data-harbor-diagnostics></div>
  </section>
  <main id="comparison"></main>
  <section id="leaderboard"></section>
  <aside id="workspace-views"></aside>
  <div data-view-save-dialog hidden>
    <form data-view-save-form>
      <input data-view-name-input name="name">
      <textarea data-view-notes-input name="notes"></textarea>
      <input type="hidden" name="view_location" value="browser">
      <dl data-view-current-configuration></dl>
      <button data-view-save-cancel type="button">Cancel</button>
    </form>
  </div>
`);

const runtime = await import("../../src/psycheval/assets/web/modules/runtime.js");
const tables = await import("../../src/psycheval/assets/web/modules/data-tables.js");
const notes = await import("../../src/psycheval/assets/web/modules/analysis-notes.js");
const sourceState = await import("../../src/psycheval/assets/web/modules/source-state-controls.js");
const configuration = await import("../../src/psycheval/assets/web/modules/configuration.js");
const catalog = await import("../../src/psycheval/assets/web/modules/serve-catalog.js");
const effects = await import("../../src/psycheval/assets/web/modules/serve-effects.js");
const reports = await import("../../src/psycheval/assets/web/modules/workspace-reports.js");
const views = await import("../../src/psycheval/assets/web/modules/workspace-views.js");
const shell = await import("../../src/psycheval/assets/web/modules/global-shell.js");
const harbor = await import("../../src/psycheval/assets/web/modules/harbor-workbench.js");
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test.after(() => browser.cleanup());

test("guest surfaces keep browsing controls and omit every workspace mutation", async () => {
  assert.equal(runtime.adminMode(), false);
  assert.equal(runtime.authenticationEnabled(), true);

  const columns = tables.leaderboardColumns();
  assert.equal(columns.find(column => column.key === "task_name").edit, undefined);
  assert.equal(columns.find(column => column.key === "source_category").edit, undefined);
  assert.equal(columns.find(column => column.key === "source_tags").edit, undefined);
  assert.equal(notes.renderNotesAction("trial"), "");
  assert.equal(reports.renderAttachWorkspaceReportAction([]), "");

  const sourceControls = sourceState.renderServeSourceStateControls([]);
  assert.match(sourceControls, /data-source-state-toggle/);
  assert.doesNotMatch(sourceControls, /data-source-state-action/);

  runtime.state.workspaceViews = [
    {
      id: "server:Readonly view",
      origin: "server",
      name: "Readonly view",
      filters: {},
      group_by: "agent",
      notes: "Published notes",
    },
    {
      id: "browser:My view",
      origin: "browser",
      name: "My view",
      filters: {},
      group_by: "agent",
      notes: "Local notes",
    },
  ];
  runtime.state.workspaceViewSelection = new Set(["server:Readonly view", "browser:My view"]);
  const viewNameColumn = views.workspaceViewColumns().find(column => column.key === "name");
  assert.equal(viewNameColumn.edit(runtime.state.workspaceViews[0]), undefined);
  assert.ok(viewNameColumn.edit(runtime.state.workspaceViews[1]));
  assert.match(views.renderWorkspaceViewControls(), /data-view-save/);
  const viewIndex = views.renderWorkspaceViewIndex();
  assert.match(viewIndex, /data-view-apply-selected/);
  assert.match(viewIndex, /data-view-export-selected/);
  assert.match(viewIndex, /data-view-delete-selected/);
  assert.match(viewIndex, /Delete local \(1\)/);

  await assert.rejects(
    effects.commitSourceCellEdit({ source_key: "source" }, "alias", "blocked"),
    /unavailable/,
  );
});

test("Home report refresh does not render into the Reports page-owned manager", () => {
  const inventory = document.querySelector("[data-report-inventory]");
  inventory.innerHTML = '<span data-reports-page-owner>owned by Reports page</span>';

  reports.applyWorkspaceReportCatalog([{
    report_id: "report-2",
    report_ref: "package:report-2",
    filename: "new-report.md",
    format: "markdown",
    source_keys: [],
  }]);

  assert.ok(inventory.querySelector("[data-reports-page-owner]"));
});

test("guest Dataset page loads Task text as read-only without download controls", async () => {
  const calls = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async path => {
    calls.push(String(path));
    const value = String(path);
    const payload = value === "/api/harbor/datasets"
      ? { datasets: [{ id: "public", tasks: [{ directory: "task-1", package_name: "org/task", status: "valid", diagnostics: [] }] }] }
      : value === "/api/harbor/datasets/public/tasks/task-1"
        ? { dataset_id: "public", task: { directory: "task-1", package_name: "org/task", status: "valid", diagnostics: [] }, tree: [{ path: "solution/solve.sh", kind: "file", size: 9, editable: true }] }
        : { path: "solution/solve.sh", content: "echo done" };
    return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify(payload) };
  };
  try {
    await harbor.initializeHarborWorkbench();
    assert.deepEqual(calls.slice(0, 2), [
      "/api/harbor/datasets",
      "/api/harbor/datasets/public/tasks/task-1",
    ]);
    document.querySelector(".harbor-file-row.kind-file").click();
    await tick();
    assert.equal(document.querySelector("[data-harbor-editor]").value, "echo done");
    assert.equal(document.querySelector("[data-harbor-editor]").readOnly, true);
    assert.equal(document.querySelector("[data-harbor-download]"), null);
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("serve API preserves HTTP errors when an upstream returns non-JSON", async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 502,
    statusText: "Bad Gateway",
    text: async () => "<html>proxy failure</html>",
  });
  try {
    await assert.rejects(
      effects.serveApi("/api/views"),
      error => error?.message === "Bad Gateway" && error?.status === 502,
    );
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("guest administrator action functions issue no requests when invoked directly", async () => {
  const previousFetch = globalThis.fetch;
  const previousConfirm = window.confirm;
  const previousPrompt = window.prompt;
  let requests = 0;
  globalThis.fetch = async () => {
    requests += 1;
    throw new Error("guest action reached the network");
  };
  window.confirm = () => true;
  const sourceForm = document.createElement("form");
  sourceForm.dataset.sourceKind = "path";
  sourceForm.innerHTML = '<input name="path" value="/tmp/source.json">';
  const dbForm = document.createElement("form");
  dbForm.dataset.sourceKind = "db";
  dbForm.innerHTML = '<input name="db" value="/tmp/source.db">';
  try {
    await catalog.refreshServeSourcesFromServer();
    await shell.changeLocale("zh-CN");
    await configuration.submitServeSourceForm(sourceForm);
    await configuration.inspectDbSessions(dbForm);
    await configuration.addHarborMount();
    await configuration.removeSelectedHarborMounts();
    await harbor.saveFile();
    const task = { directory: "private-task", revision: "task-r1" };
    const trash = { entry_id: "trash-1", directory: "private-task", revision: "trash-r1" };
    harbor.workbenchState.inventory = {
      datasets: [{ id: "private", revision: "dataset-r1", tasks: [task], trash: [trash] }],
    };
    harbor.workbenchState.datasetId = "private";
    harbor.workbenchState.taskName = "private-task";
    harbor.workbenchState.taskSelection = new Set([
      "dataset:private|task:private-task",
      "dataset:private|trash:trash-1",
    ]);
    let prompts = 0;
    let confirms = 0;
    let fileReads = 0;
    window.prompt = () => {
      prompts += 1;
      return "blocked";
    };
    window.confirm = () => {
      confirms += 1;
      return true;
    };
    await harbor.createFile("file");
    await harbor.uploadFile({
      name: "private.bin",
      size: 1,
      arrayBuffer: async () => {
        fileReads += 1;
        return new ArrayBuffer(1);
      },
    });
    await harbor.fileActionMenu({ path: "private.txt" });
    await harbor.mutateSelectedTaskState();
    await harbor.deleteSelectedTasks();
    assert.equal(requests, 0);
    assert.equal(prompts, 0);
    assert.equal(confirms, 0);
    assert.equal(fileReads, 0);
  } finally {
    globalThis.fetch = previousFetch;
    window.confirm = previousConfirm;
    window.prompt = previousPrompt;
    harbor.workbenchState.inventory = null;
    harbor.workbenchState.datasetId = null;
    harbor.workbenchState.taskName = null;
    harbor.workbenchState.taskSelection.clear();
  }
});

test("guest saves a view only to workspace-scoped browser storage", async () => {
  const calls = [];
  const published = {
    name: "Published",
    filters: {},
    group_by: "agent",
    notes: "Workspace view",
  };
  let serverViews = [published];
  const previousFetch = globalThis.fetch;
  window.localStorage.clear();
  globalThis.fetch = async (path, options = {}) => {
    calls.push({
      path: String(path),
      method: options.method || "GET",
      body: options.body ? JSON.parse(String(options.body)) : null,
    });
    const payload = String(path) === "/api/views"
      ? serverViews
      : String(path) === "/api/view-summaries"
      ? { generation: 1, views: [{ name: "Guest local", matched_count: 0, groups: [] }] }
      : { views: [] };
    return {
      ok: true,
      status: 200,
      statusText: "OK",
      text: async () => JSON.stringify(payload),
    };
  };
  window.fetch = globalThis.fetch;
  try {
    runtime.state.workspaceViews = [];
    runtime.state.workspaceViewsLoaded = false;
    runtime.state.workspaceViewsRefreshPromise = null;
    runtime.state.workspaceViewsRefreshQueued = false;
    await views.refreshWorkspaceViews();
    const dialog = document.querySelector("[data-view-save-dialog]");
    dialog.querySelector("[data-view-name-input]").value = "Guest local";
    dialog.querySelector("[data-view-notes-input]").value = "Only here";
    await views.saveWorkspaceView(dialog);

    assert.deepEqual(views.workspaceViews().map(view => [view.id, view.notes]), [
      ["browser:Guest local", "Only here"],
      ["server:Published", "Workspace view"],
    ]);
    assert.equal(calls.some(call => call.path === "/api/views" && call.method === "POST"), false);
    assert.equal(
      JSON.parse(window.localStorage.getItem("peval.saved-views.v1.default")).views[0].name,
      "Guest local",
    );
    await views.commitWorkspaceViewCellEdit(
      views.workspaceViewForId("browser:Guest local"),
      "notes",
      "Edited locally",
    );
    assert.equal(
      JSON.parse(window.localStorage.getItem("peval.saved-views.v1.default")).views[0].notes,
      "Edited locally",
    );
    assert.equal(calls.some(call => call.path === "/api/views/update"), false);
    runtime.state.workspaceViewSelection = new Set(["browser:Guest local"]);
    await views.applySelectedWorkspaceViews();
    const catalogQuery = calls.find(call => call.path === "/api/catalog-queries");
    assert.deepEqual(catalogQuery.body.browser_views, [{
      name: "Guest local",
      filters: {},
      group_by: "agent",
      notes: "Edited locally",
    }]);
    assert.deepEqual(catalogQuery.body.views, []);

    serverViews = [
      {
        name: "Guest local",
        filters: { results: ["passed"] },
        group_by: "overall",
        notes: "Workspace definition",
      },
      published,
    ];
    await views.refreshWorkspaceViews();
    assert.deepEqual(
      views.workspaceViews().map(view => view.id),
      ["server:Guest local", "server:Published"],
    );
    assert.deepEqual(Array.from(runtime.state.workspaceAppliedViewNames), []);
    assert.deepEqual(runtime.state.catalogQuery.views, []);

    serverViews = [published];
    await views.refreshWorkspaceViews();
    assert.deepEqual(
      views.workspaceViews().map(view => view.id),
      ["browser:Guest local", "server:Published"],
    );
    const previousConfirm = window.confirm;
    window.confirm = () => true;
    runtime.state.workspaceViewSelection = new Set([
      "server:Published",
      "browser:Guest local",
    ]);
    await views.deleteSelectedWorkspaceViews();
    window.confirm = previousConfirm;
    assert.deepEqual(Array.from(runtime.state.workspaceViewSelection), ["server:Published"]);
    assert.equal(calls.some(call => call.path === "/api/views/delete"), false);
    assert.deepEqual(
      JSON.parse(window.localStorage.getItem("peval.saved-views.v1.default")).views,
      [],
    );
  } finally {
    globalThis.fetch = previousFetch;
    window.fetch = previousFetch;
    window.localStorage.clear();
  }
});

test("guest login dialog submits credentials, reports failure, and closes", async () => {
  const calls = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => {
    calls.push({ path: String(path), body: JSON.parse(String(options.body)) });
    return {
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      text: async () => JSON.stringify({ detail: "invalid administrator password" }),
    };
  };
  try {
    shell.bindAuthenticationControls();
    document.querySelector("[data-admin-login-open]").click();
    const dialog = document.querySelector("[data-admin-login-dialog]");
    assert.equal(dialog.hidden, false);
    dialog.querySelector("form").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
    await tick();
    assert.deepEqual(calls, [{
      path: "/api/session",
      body: { password: "wrong" },
    }]);
    assert.equal(dialog.querySelector("[data-admin-login-status]").hidden, false);
    assert.match(dialog.querySelector("[data-admin-login-status]").textContent, /invalid administrator password/);
    dialog.querySelector("[data-admin-login-close]").click();
    assert.equal(dialog.hidden, true);
  } finally {
    globalThis.fetch = previousFetch;
  }
});
