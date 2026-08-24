import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-data">{}</script>
  <script type="application/json" id="peval-token-estimates">{}</script>
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin","authentication_enabled":true,"sources":[]}</script>
  <strong data-source-count></strong>
  <span data-source-status></span>
  <div data-config-page hidden></div>
  <div data-report-manager hidden><section aria-modal="true"><button data-report-manager-close>Close</button><p data-report-manager-status hidden></p><div data-report-inventory></div><span data-report-count></span><div data-report-bindings></div></section></div>
  <aside id="workspace-report-reader" hidden></aside>
  <div data-view-save-dialog hidden><section aria-modal="true"><button data-view-save-cancel>Cancel</button></section></div>
  <button data-refresh-all>Refresh</button>
  <button data-source-delete-action disabled>Delete</button>
  <button data-harbor-add-mount>Add mount</button>
  <main id="comparison"></main>
  <section id="leaderboard"></section>
`);

const runtime = await import("../src/modules/runtime.js");
const tables = await import("../src/modules/data-tables.js");
const configuration = await import("../src/modules/configuration.js");
const sourceStateControls = await import("../src/modules/source-state-controls.js");
const catalog = await import("../src/modules/serve-catalog.js");
const leaderboardSummary = await import("../src/modules/leaderboard-summary.js");
const modals = await import("../src/modules/modal-surfaces.js");
const reports = await import("../src/modules/workspace-reports.js");
const views = await import("../src/modules/workspace-views.js");
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test.after(() => browser.cleanup());

test("workspace description renders escaped Markdown and hides blank content", () => {
  const node = document.createElement("div");
  node.dataset.workspaceDescription = "";
  node.hidden = true;
  document.body.append(node);
  try {
    runtime.RENDER_OPTIONS.workspace_description = "**Nightly** <script>alert(1)</script>";
    runtime.renderWorkspaceDescription();
    assert.equal(node.hidden, false);
    assert.match(node.innerHTML, /<strong>Nightly<\/strong>/);
    assert.match(node.innerHTML, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
    assert.doesNotMatch(node.innerHTML, /<script>/);

    runtime.RENDER_OPTIONS.workspace_description = "   ";
    runtime.renderWorkspaceDescription();
    assert.equal(node.hidden, true);
    assert.equal(node.innerHTML, "");
  } finally {
    delete runtime.RENDER_OPTIONS.workspace_description;
    node.remove();
  }
});

test("Harbor semantic Leaderboard columns use Catalog API sort keys", () => {
  assert.equal(catalog.catalogSortKey("task_name"), "task");
  assert.equal(catalog.catalogSortKey("job_name"), "job");
  assert.equal(catalog.catalogSortKey("model_provider"), "provider");
  assert.equal(catalog.catalogSortKey("reward"), "reward");
});

test("initial Catalog sort is shown on the corresponding browser column", () => {
  runtime.state.catalogQuery.sort = "last_turn_end";
  runtime.state.catalogQuery.direction = "desc";
  runtime.state.tables.leaderboard = {};
  const host = document.createElement("div");
  host.innerHTML = tables.renderLeaderboardColumnControls([]);

  const state = host.querySelector('[data-column-row="finished_at_ms"] .column-control-state');
  assert.match(state.textContent, /desc/);

  const column = tables.leaderboardColumns().find(item => item.key === "finished_at_ms");
  host.innerHTML = `<table><thead><tr>${tables.renderTableHeader(
    "leaderboard",
    column,
    tables.tableControls("leaderboard"),
  )}</tr></thead></table>`;
  const header = host.querySelector("th");
  assert.equal(header.getAttribute("aria-sort"), "descending");
  assert.equal(header.querySelector("[data-table-sort]").classList.contains("active"), true);
});

test("the last visible data column remains hideable", () => {
  runtime.state.catalogRows = [];
  runtime.state.catalogPage.column_presence = { task_name: 1, model_provider: 1 };
  runtime.state.leaderboardColumnDraft = null;
  runtime.state.leaderboardColumnLayout = null;

  const host = document.createElement("div");
  host.innerHTML = tables.renderLeaderboardColumnControls([]);

  const visibility = host.querySelector('[data-column-visible="task_name"]');
  assert.equal(visibility.checked, true);
  assert.equal(visibility.disabled, false);
  const providerVisibility = host.querySelector('[data-column-visible="model_provider"]');
  assert.equal(providerVisibility.checked, false);
  assert.equal(providerVisibility.disabled, false);
});

test("column draft actions restore focus after replacing the control panel", () => {
  runtime.state.catalogRows = [];
  runtime.state.catalogPage.column_presence = { session_id: 1, task_name: 1 };
  runtime.state.leaderboardColumnDraft = null;
  runtime.state.leaderboardColumnLayout = null;
  tables.renderLeaderboard([]);

  let details = document.querySelector("#leaderboard .column-control");
  details.open = true;
  details.dispatchEvent(new window.Event("toggle"));

  let visibility = details.querySelector('[data-column-visible="task_name"]');
  visibility.focus();
  visibility.checked = !visibility.checked;
  visibility.dispatchEvent(new window.Event("change", { bubbles: true }));
  assert.equal(document.activeElement?.dataset.columnVisible, "task_name");

  let move = document.querySelector('#leaderboard [data-column-move="task_name"][data-column-direction="1"]');
  move.focus();
  move.click();
  assert.equal(document.activeElement?.dataset.columnMove, "task_name");
  assert.equal(document.activeElement?.dataset.columnDirection, "1");

  let reset = document.querySelector("#leaderboard [data-column-reset]");
  reset.focus();
  reset.click();
  assert.equal(document.activeElement?.hasAttribute("data-column-reset"), true);

  const apply = document.querySelector("#leaderboard [data-column-apply]");
  apply.focus();
  apply.click();
  assert.equal(document.activeElement, document.querySelector("#leaderboard .column-control > summary"));

  runtime.state.leaderboardColumnDraft = null;
  runtime.state.leaderboardColumnLayout = null;
  runtime.state.catalogPage.column_presence = {};
  tables.renderLeaderboard([]);
  details = document.querySelector("#leaderboard .column-control");
  details.open = true;
  details.dispatchEvent(new window.Event("toggle"));
  visibility = details.querySelector('[data-column-visible="task_name"]');
  visibility.checked = true;
  visibility.dispatchEvent(new window.Event("change", { bubbles: true }));
  assert.equal(document.activeElement?.dataset.columnVisible, "task_name");

  runtime.state.leaderboardColumnDraft = null;
  runtime.state.leaderboardColumnLayout = null;
});

test("an expired administrator export reloads into guest state", async () => {
  const previousFetch = globalThis.fetch;
  const navigationErrors = [];
  const onJsdomError = error => navigationErrors.push(error.message);
  browser.dom.virtualConsole.on("jsdomError", onJsdomError);
  globalThis.fetch = async () => ({
    ok: false,
    status: 403,
    statusText: "Forbidden",
    json: async () => ({ error: "administrator access required" }),
  });

  try {
    await catalog.serveDownload("xlsx", { kind: "xlsx", source_keys: ["source"] });
    assert.equal(navigationErrors.some(message => message.includes("navigation")), true);
  } finally {
    browser.dom.virtualConsole.off("jsdomError", onJsdomError);
    globalThis.fetch = previousFetch;
  }
});

test("Saved View Category groups preserve a literal overall category", () => {
  const group = { key: "overall", label: "overall" };
  assert.equal(views.workspaceViewGroupLabel(group, "category"), "overall");
  assert.equal(views.workspaceViewGroupLabel(group, "overall"), "Overall");
});

test("Configuration loads workspace configuration and prompt assets without a source catalog page", async () => {
  const requests = [];
  const previousFetch = globalThis.fetch;
  const root = document.querySelector("[data-config-page]");
  root.hidden = false;
  root.innerHTML = '<p data-config-page-status hidden></p><button data-harbor-config-reload></button><button data-harbor-add-dataset></button><button data-harbor-register-dataset></button><button data-harbor-unregister-datasets></button><div data-harbor-dataset-count></div><div data-harbor-dataset-registry></div><div data-harbor-mount-config></div>';
  delete root.dataset.configBound;
  globalThis.fetch = async path => {
    requests.push(String(path));
    return {
      ok: true,
      statusText: "OK",
      text: async () => JSON.stringify({ revision: "r1", datasets: [{ id: "tasks", path: "/workspace/tasks" }], mounts: [] }),
    };
  };
  try {
    await configuration.initializeConfiguration();
    assert.deepEqual(requests, ["/api/config", "/api/prompts"]);
    assert.match(root.querySelector("[data-harbor-dataset-registry]").textContent, /tasks/);
    assert.equal(root.querySelector("[data-source-list]"), null);
  } finally {
    globalThis.fetch = previousFetch;
    root.hidden = true;
  }
});

test("Configuration adds ACP agents and saves same-name prompt overrides", async () => {
  const requests = [];
  const previousFetch = globalThis.fetch;
  const root = document.querySelector("[data-config-page]");
  root.hidden = false;
  root.innerHTML = `
    <p data-config-page-status hidden></p>
    <button data-harbor-config-reload></button>
    <button data-acp-agent-form-open>Add ACP agent</button>
    <div data-acp-agent-form-panel hidden role="dialog" aria-modal="true">
      <form data-acp-agent-form>
        <p data-acp-agent-form-status hidden></p>
        <input name="agent_id" value="opencode" required>
        <input name="title" value="OpenCode" required>
        <input name="command" value="opencode" required>
        <input name="args" value='["acp"]' required>
        <button type="button" data-acp-agent-form-cancel>Cancel</button>
        <button type="submit">Add ACP agent</button>
      </form>
    </div>
    <button data-acp-remove-agents></button>
    <span data-acp-agent-count></span><div data-acp-agent-config></div>
    <button data-prompt-save disabled></button><button data-prompt-reset disabled></button>
    <span data-prompt-asset-count></span><nav data-prompt-config-list></nav>
    <code data-prompt-filename></code><span data-prompt-origin></span><textarea data-prompt-content></textarea>
    <div data-harbor-dataset-count></div><div data-harbor-dataset-registry></div>
    <div data-harbor-mount-count></div><div data-harbor-mount-config></div>`;
  delete root.dataset.configBound;
  let snapshot = { revision: "r1", datasets: [], mounts: [], acp_agents: [] };
  let prompt = { id: "failure-diagnosis", filename: "failure-diagnosis.md", title: "Failure diagnosis", content: "# Failure diagnosis\n\nDefault.", customized: false, revision: "p1" };
  globalThis.fetch = async (path, options = {}) => {
    const request = { path: String(path), method: options.method || "GET", body: options.body ? JSON.parse(String(options.body)) : null };
    requests.push(request);
    let payload;
    if (request.path === "/api/config/acp/agents") {
      snapshot = { ...snapshot, revision: "r2", acp_agents: [{ id: "opencode", title: "OpenCode", command: "opencode", args: ["acp"], connected: false }] };
      payload = snapshot;
    } else if (request.path === "/api/prompts" && request.method === "POST") {
      prompt = { ...prompt, content: request.body.content, customized: true, revision: "p2" };
      payload = { prompt };
    } else if (request.path === "/api/prompts") {
      payload = { prompts: [prompt] };
    } else {
      payload = snapshot;
    }
    return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify(payload) };
  };

  try {
    await configuration.initializeConfiguration();
    const panel = root.querySelector("[data-acp-agent-form-panel]");
    const open = root.querySelector("[data-acp-agent-form-open]");
    assert.equal(panel.hidden, true);
    open.click();
    assert.equal(panel.hidden, false);
    assert.equal(document.activeElement, root.querySelector('[name="agent_id"]'));
    root.querySelector('[name="agent_id"]').value = "unfinished";
    root.querySelector("[data-acp-agent-form-cancel]").click();
    assert.equal(panel.hidden, true);
    assert.equal(document.activeElement, open);
    open.click();
    assert.equal(root.querySelector('[name="agent_id"]').value, "opencode");
    root.querySelector('[name="agent_id"]').dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    assert.equal(panel.hidden, true);
    open.click();
    root.querySelector('[name="args"]').value = "acp";
    root.querySelector("[data-acp-agent-form]").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
    await tick();
    assert.equal(panel.hidden, false);
    assert.match(root.querySelector("[data-acp-agent-form-status]").textContent, /JSON array/);
    root.querySelector('[name="args"]').value = '["acp"]';
    root.querySelector("[data-acp-agent-form]").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
    await tick();
    await tick();
    assert.deepEqual(requests.find(request => request.path === "/api/config/acp/agents").body, {
      action: "upsert",
      agent_id: "opencode",
      title: "OpenCode",
      command: "opencode",
      args: ["acp"],
      expected_revision: "r1",
    });
    assert.equal(panel.hidden, true);
    assert.equal(document.activeElement, open);
    assert.match(root.querySelector("[data-acp-agent-config]").textContent, /opencode/);

    const editor = root.querySelector("[data-prompt-content]");
    editor.value = "# Team diagnosis\n\nInspect evidence.";
    editor.dispatchEvent(new window.Event("input", { bubbles: true }));
    assert.equal(root.querySelector("[data-prompt-save]").disabled, false);
    root.querySelector("[data-prompt-save]").click();
    await tick();
    await tick();
    const save = requests.find(request => request.path === "/api/prompts" && request.method === "POST");
    assert.deepEqual(save.body, {
      action: "save",
      prompt_id: "failure-diagnosis",
      content: "# Team diagnosis\n\nInspect evidence.",
      expected_revision: "p1",
    });
    assert.match(root.querySelector("[data-prompt-origin]").textContent, /Workspace override/);
  } finally {
    globalThis.fetch = previousFetch;
    configuration.harborConfigState.busy = false;
    configuration.harborConfigState.acpSelection.clear();
    configuration.promptConfigState.dirty = false;
    root.hidden = true;
  }
});

test("Configuration reloads the current prompt after a revision conflict", async () => {
  const requests = [];
  const previousFetch = globalThis.fetch;
  const root = document.querySelector("[data-config-page]");
  root.hidden = false;
  root.innerHTML = `
    <p data-config-page-status hidden></p><button data-harbor-config-reload></button>
    <button data-prompt-save disabled></button><button data-prompt-reset disabled></button>
    <span data-prompt-asset-count></span><nav data-prompt-config-list></nav>
    <code data-prompt-filename></code><span data-prompt-origin></span><textarea data-prompt-content></textarea>
    <div data-harbor-dataset-count></div><div data-harbor-dataset-registry></div>
    <div data-harbor-mount-count></div><div data-harbor-mount-config></div>`;
  delete root.dataset.configBound;
  let conflicted = false;
  globalThis.fetch = async (path, options = {}) => {
    const request = { path: String(path), method: options.method || "GET" };
    requests.push(request);
    if (request.path === "/api/prompts" && request.method === "POST") {
      conflicted = true;
      return { ok: false, status: 409, statusText: "Conflict", text: async () => JSON.stringify({ error: "Workspace prompt changed; refresh before saving" }) };
    }
    if (request.path === "/api/prompts") {
      const prompt = conflicted
        ? { id: "failure-diagnosis", filename: "failure-diagnosis.md", title: "Teammate edit", content: "# Teammate edit\n", customized: true, revision: "p2" }
        : { id: "failure-diagnosis", filename: "failure-diagnosis.md", title: "Failure diagnosis", content: "# Default\n", customized: false, revision: "p1" };
      return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify({ prompts: [prompt] }) };
    }
    return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify({ revision: conflicted ? "r2" : "r1", datasets: [], mounts: [], acp_agents: [] }) };
  };

  try {
    await configuration.initializeConfiguration();
    const editor = root.querySelector("[data-prompt-content]");
    editor.value = "# My stale edit\n";
    editor.dispatchEvent(new window.Event("input", { bubbles: true }));
    root.querySelector("[data-prompt-save]").click();
    await tick();
    await tick();
    await tick();

    assert.equal(requests.filter(request => request.path === "/api/config").length, 2);
    assert.equal(requests.filter(request => request.path === "/api/prompts" && request.method === "GET").length, 2);
    assert.equal(configuration.promptConfigState.prompts[0].revision, "p2");
    assert.equal(editor.value, "# Teammate edit\n");
    assert.match(root.querySelector("[data-config-page-status]").textContent, /refresh before saving/);
  } finally {
    globalThis.fetch = previousFetch;
    configuration.harborConfigState.busy = false;
    configuration.promptConfigState.dirty = false;
    root.hidden = true;
  }
});

test("Configuration registers Dataset and Jobs roots from path-only actions", async () => {
  const requests = [];
  const prompts = [];
  const previousFetch = globalThis.fetch;
  const previousPrompt = window.prompt;
  const root = document.querySelector("[data-config-page]");
  root.hidden = false;
  root.innerHTML = '<p data-config-page-status hidden></p><button data-harbor-config-reload></button><button data-harbor-add-dataset></button><button data-harbor-register-dataset></button><button data-harbor-unregister-datasets></button><div data-harbor-dataset-count></div><div data-harbor-dataset-registry></div><button data-harbor-add-mount></button><button data-harbor-remove-mounts></button><div data-harbor-mount-count></div><div data-harbor-mount-config></div>';
  delete root.dataset.configBound;
  let snapshot = { revision: "r1", datasets: [], mounts: [] };
  globalThis.fetch = async (path, options = {}) => {
    const request = {
      path: String(path),
      method: options.method || "GET",
      body: options.body ? JSON.parse(String(options.body)) : null,
    };
    requests.push(request);
    if (request.path === "/api/config/harbor/datasets") {
      snapshot = { revision: "r2", datasets: [{ id: "tasks", path: "/workspace/tasks" }], mounts: [] };
      return { ok: true, statusText: "OK", text: async () => JSON.stringify({ result: snapshot }) };
    }
    if (request.path === "/api/config/harbor/mounts") {
      snapshot = { revision: "r3", datasets: snapshot.datasets, mounts: [{ id: "jobs", path: "/workspace/jobs", dataset_ids: [] }] };
      return { ok: true, statusText: "OK", text: async () => JSON.stringify({ result: snapshot }) };
    }
    return { ok: true, statusText: "OK", text: async () => JSON.stringify(snapshot) };
  };
  window.prompt = message => {
    prompts.push(message);
    return prompts.length === 1 ? "/workspace/tasks" : "/workspace/jobs";
  };

  try {
    await configuration.initializeConfiguration();
    assert.equal(root.querySelector("[data-harbor-mount-form]"), null);

    root.querySelector("[data-harbor-register-dataset]").click();
    await tick();
    await tick();

    assert.equal(prompts.length, 1);
    assert.deepEqual(
      requests.find(request => request.path === "/api/config/harbor/datasets").body,
      {
        action: "register",
        path: "/workspace/tasks",
        expected_revision: "r1",
      },
    );
    assert.equal(
      root.querySelector('[data-table-column-key="path"]').dataset.valueType,
      "path",
    );

    root.querySelector("[data-harbor-add-mount]").click();
    await tick();
    await tick();
    const mountRequests = requests.filter(
      request => request.path === "/api/config/harbor/mounts",
    );
    assert.deepEqual(
      mountRequests.at(-1).body,
      {
        action: "upsert",
        expected_revision: "r2",
        jobs_path: "/workspace/jobs",
      },
    );
    assert.equal(prompts.length, 2);
    assert.equal(root.querySelector("[data-harbor-mount-count]").textContent, "1");
    assert.match(root.querySelector("[data-harbor-mount-config]").textContent, /jobs/);
    assert.equal(root.querySelector("[data-harbor-mount-form]"), null);
  } finally {
    globalThis.fetch = previousFetch;
    window.prompt = previousPrompt;
    configuration.harborConfigState.busy = false;
    root.hidden = true;
  }
});

test("Configuration edits Dataset cells and atomically unregisters the selected registrations", async () => {
  const requests = [];
  const previousFetch = globalThis.fetch;
  const previousConfirm = window.confirm;
  const root = document.querySelector("[data-config-page]");
  root.hidden = false;
  root.innerHTML = '<p data-config-page-status hidden></p><button data-harbor-config-reload></button><button data-harbor-add-dataset></button><button data-harbor-register-dataset></button><button data-harbor-unregister-datasets></button><div data-harbor-dataset-count></div><div data-harbor-dataset-registry></div><div data-harbor-mount-config></div>';
  delete root.dataset.configBound;
  let snapshot = { revision: "r1", datasets: [{ id: "tasks", path: "/workspace/tasks" }], mounts: [] };
  globalThis.fetch = async (path, options = {}) => {
    const request = {
      path: String(path),
      method: options.method || "GET",
      body: options.body ? JSON.parse(String(options.body)) : null,
    };
    requests.push(request);
    let payload = snapshot;
    if (request.path === "/api/config/harbor/datasets" && request.body.action === "update") {
      snapshot = { revision: "r2", datasets: [{ id: "renamed", path: "/workspace/tasks" }], mounts: [] };
      payload = { result: snapshot, operation: { operation_id: "config-op" } };
    } else if (request.path === "/api/config/harbor/datasets" && request.body.action === "unregister") {
      snapshot = { revision: "r3", datasets: [], mounts: [] };
      payload = { result: snapshot, operation: { operation_id: "config-op" } };
    } else if (request.path === "/api/operations/config-op") {
      payload = { operation_id: "config-op", operation_type: "harbor-dataset-config", state: "completed", completed: 1, total: 1, successes: [{ index: 0 }], failures: [] };
    }
    return {
      ok: true,
      statusText: "OK",
      text: async () => JSON.stringify(payload),
    };
  };
  window.confirm = () => true;

  try {
    await configuration.initializeConfiguration();
    const idCell = root.querySelector('[data-table-column-key="id"]');
    idCell.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
    const editor = idCell.querySelector("[data-table-cell-editor] input");
    editor.value = "renamed";
    editor.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await tick();
    await tick();
    assert.match(root.querySelector("[data-harbor-dataset-registry]").textContent, /renamed/);

    root.querySelector('[data-table-row-select="renamed"]').click();
    root.querySelector("[data-harbor-unregister-datasets]").click();
    await tick();
    await tick();

    const mutations = requests.filter(request => request.path === "/api/config/harbor/datasets");
    assert.deepEqual(mutations.map(request => request.body), [
      {
        action: "update",
        dataset_id: "tasks",
        new_id: "renamed",
        path: "/workspace/tasks",
        mount_ids: [],
        expected_revision: "r1",
      },
      {
        action: "unregister",
        dataset_ids: ["renamed"],
        expected_revision: "r2",
      },
    ]);
    assert.equal(root.querySelectorAll("[data-table-row-select]").length, 0);
    assert.equal(configuration.harborConfigState.datasetSelection.size, 0);
  } finally {
    globalThis.fetch = previousFetch;
    window.confirm = previousConfirm;
    configuration.harborConfigState.busy = false;
    configuration.harborConfigState.datasetSelection.clear();
    root.hidden = true;
  }
});

test("Configuration edits reciprocal Harbor associations and batch removes mounts", async () => {
  const requests = [];
  const previousFetch = globalThis.fetch;
  const previousConfirm = window.confirm;
  const root = document.querySelector("[data-config-page]");
  root.hidden = false;
  root.innerHTML = '<p data-config-page-status hidden></p><button data-harbor-config-reload></button><button data-harbor-add-dataset></button><button data-harbor-register-dataset></button><button data-harbor-unregister-datasets></button><div data-harbor-dataset-count></div><div data-harbor-dataset-registry></div><button data-harbor-add-mount></button><button data-harbor-remove-mounts></button><div data-harbor-mount-count></div><div data-harbor-mount-config></div>';
  delete root.dataset.configBound;
  let revision = 1;
  let snapshot = {
    revision: "r1",
    datasets: [
      { id: "tasks", path: "/workspace/tasks" },
      { id: "other", path: "/workspace/other" },
    ],
    mounts: [
      { id: "one", path: "/workspace/jobs-one", dataset_ids: ["other"] },
      { id: "two", path: "/workspace/jobs-two", dataset_ids: ["tasks", "other"] },
    ],
  };
  globalThis.fetch = async (path, options = {}) => {
    const request = {
      path: String(path),
      method: options.method || "GET",
      body: options.body ? JSON.parse(String(options.body)) : null,
    };
    requests.push(request);
    if (request.path === "/api/config/harbor/datasets") {
      snapshot = {
        ...snapshot,
        revision: `r${++revision}`,
        mounts: [
          { ...snapshot.mounts[0], dataset_ids: ["other", "tasks"] },
          snapshot.mounts[1],
        ],
      };
      return { ok: true, statusText: "OK", text: async () => JSON.stringify({ result: snapshot }) };
    }
    if (request.path === "/api/config/harbor/mounts") {
      if (request.body.action === "delete") {
        const removed = new Set(request.body.mount_ids);
        snapshot = { ...snapshot, revision: `r${++revision}`, mounts: snapshot.mounts.filter(mount => !removed.has(mount.id)) };
      } else {
        snapshot = {
          ...snapshot,
          revision: `r${++revision}`,
          mounts: snapshot.mounts.map(mount => mount.id === request.body.original_id ? {
            id: request.body.mount_id,
            path: request.body.jobs_path,
            dataset_ids: request.body.dataset_ids,
          } : mount),
        };
      }
      return { ok: true, statusText: "OK", text: async () => JSON.stringify({ result: snapshot }) };
    }
    return { ok: true, statusText: "OK", text: async () => JSON.stringify(snapshot) };
  };
  window.confirm = () => true;

  try {
    await configuration.initializeConfiguration();
    assert.equal(root.querySelector("[data-harbor-mount-count]").textContent, "2");

    const mountsCell = root.querySelector('[data-table-id="harbor-dataset-registry"] [data-table-row-key="tasks"] [data-table-column-key="mounts"]');
    mountsCell.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
    assert.deepEqual(
      Array.from(mountsCell.querySelectorAll("[data-table-suggestion]")).map(button => button.textContent),
      ["one", "two"],
    );
    mountsCell.querySelector('[data-table-suggestion="one"]').click();
    mountsCell.querySelector("input").dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await tick();
    await tick();
    assert.deepEqual(
      requests.find(request => request.path === "/api/config/harbor/datasets").body,
      {
        action: "update",
        dataset_id: "tasks",
        new_id: "tasks",
        path: "/workspace/tasks",
        mount_ids: ["two", "one"],
        expected_revision: "r1",
      },
    );

    const datasetsCell = root.querySelector('[data-table-id="harbor-mount-registry"] [data-table-row-key="one"] [data-table-column-key="datasets"]');
    datasetsCell.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
    datasetsCell.querySelector('[data-table-suggestion="other"]').click();
    datasetsCell.querySelector("input").dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await tick();
    await tick();

    let idCell = root.querySelector('[data-table-id="harbor-mount-registry"] [data-table-row-key="one"] [data-table-column-key="id"]');
    idCell.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
    idCell.querySelector("input").value = "uno";
    idCell.querySelector("input").dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await tick();
    await tick();
    assert.equal(document.activeElement.dataset.tableColumnKey, "id");
    assert.equal(document.activeElement.closest("tr").dataset.tableRowKey, "uno");

    const pathCell = root.querySelector('[data-table-id="harbor-mount-registry"] [data-table-row-key="uno"] [data-table-column-key="path"]');
    pathCell.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
    pathCell.querySelector("input").value = "/workspace/jobs-renamed";
    pathCell.querySelector("input").dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await tick();
    await tick();

    root.querySelector('[data-table-id="harbor-mount-registry"] [data-table-row-select="uno"]').click();
    root.querySelector('[data-table-id="harbor-mount-registry"] [data-table-row-select="two"]').click();
    root.querySelector("[data-harbor-remove-mounts]").click();
    await tick();
    await tick();

    const mountRequests = requests.filter(request => request.path === "/api/config/harbor/mounts");
    assert.deepEqual(mountRequests.map(request => request.body), [
      { action: "upsert", original_id: "one", mount_id: "one", jobs_path: "/workspace/jobs-one", dataset_ids: ["tasks"], expected_revision: "r2" },
      { action: "upsert", original_id: "one", mount_id: "uno", jobs_path: "/workspace/jobs-one", dataset_ids: ["tasks"], expected_revision: "r3" },
      { action: "upsert", original_id: "uno", mount_id: "uno", jobs_path: "/workspace/jobs-renamed", dataset_ids: ["tasks"], expected_revision: "r4" },
      { action: "delete", mount_ids: ["uno", "two"], expected_revision: "r5" },
    ]);
    assert.equal(root.querySelectorAll('[data-table-id="harbor-mount-registry"] [data-table-row-select]').length, 0);
    assert.equal(configuration.harborConfigState.mountSelection.size, 0);
  } finally {
    globalThis.fetch = previousFetch;
    window.confirm = previousConfirm;
    configuration.harborConfigState.datasetSelection.clear();
    configuration.harborConfigState.mountSelection.clear();
    configuration.harborConfigState.busy = false;
    root.hidden = true;
  }
});

test("DB session picker reuses the shared visible-selection behavior", () => {
  const form = document.createElement("form");
  form.dataset.sourceAddForm = "";
  form.innerHTML = '<div data-db-session-picker></div>';
  document.body.append(form);
  try {
    configuration.renderDbSessionPicker(form, {
      adapter: "psychevo",
      db: "/tmp/sessions.db",
      sessions: [
        { index: 1, session_id: "session-a", name: "Alpha" },
        { index: 2, session_id: "session-b", name: "Beta" },
      ],
    });
    const picker = form.querySelector("[data-db-session-picker]");
    const rows = picker.querySelectorAll("[data-table-row-select]");
    const header = picker.querySelector("[data-table-select-visible]");
    rows[0].click();
    assert.deepEqual(configuration.selectedDbSessionIds(form), ["session-a"]);
    assert.equal(header.indeterminate, true);
    assert.equal(picker.querySelector("[data-db-selected-count]").textContent, "1 selected");
    header.click();
    assert.deepEqual(configuration.selectedDbSessionIds(form).sort(), ["session-a", "session-b"]);
    assert.equal(Array.from(rows).every(row => row.checked), true);
    assert.equal(header.indeterminate, false);
  } finally {
    form.remove();
  }
});

test("Leaderboard disables permanent deletion for a selected linked Harbor Trial", () => {
  runtime.state.rowSelection.clear();
  runtime.state.rowSelection.add("linked-harbor");
  const host = document.createElement("div");
  host.innerHTML = sourceStateControls.renderServeSourceStateControls([{
    source_key: "linked-harbor",
    kind: "harbor-trial",
  }]);
  const deleteButton = host.querySelector("[data-source-delete-action]");
  assert.equal(deleteButton.disabled, true);
  assert.match(deleteButton.title, /cannot be deleted/);
  runtime.state.rowSelection.clear();
});

test("Leaderboard bulk actions include only selected rows on the visible page", () => {
  runtime.state.rowSelection.clear();
  runtime.state.rowSelection.add("visible-source");
  runtime.state.rowSelection.add("hidden-source");
  try {
    assert.deepEqual(catalog.visibleSelectedSourceKeys([
      { source_key: "visible-source" },
      { source_key: "unselected-source" },
    ]), ["visible-source"]);
  } finally {
    runtime.state.rowSelection.clear();
  }
});

test("workspace busy state disables and restores controls", () => {
  const refresh = document.querySelector("[data-refresh-all]");
  const deleteAction = document.querySelector("[data-source-delete-action]");
  const mountAction = document.querySelector("[data-harbor-add-mount]");
  refresh.disabled = false;
  deleteAction.disabled = true;
  mountAction.disabled = false;

  catalog.setWorkspaceWriteControlsDisabled(true);
  assert.equal(refresh.disabled, true);
  assert.equal(refresh.getAttribute("aria-busy"), "true");
  assert.equal(deleteAction.disabled, true);
  assert.equal(deleteAction.getAttribute("aria-busy"), "true");
  assert.equal(mountAction.disabled, true);
  assert.equal(mountAction.getAttribute("aria-busy"), "true");

  catalog.setWorkspaceWriteControlsDisabled(false);
  assert.equal(refresh.disabled, false);
  assert.equal(refresh.hasAttribute("aria-busy"), false);
  assert.equal(deleteAction.disabled, true);
  assert.equal(deleteAction.hasAttribute("aria-busy"), false);
  assert.equal(mountAction.disabled, false);
  assert.equal(mountAction.hasAttribute("aria-busy"), false);
});

test("Configuration reports nested and background source import results", async () => {
  const previousFetch = globalThis.fetch;
  const root = document.querySelector("[data-config-page]");
  root.hidden = false;
  root.innerHTML = '<p data-config-page-status hidden></p>';

  try {
    configuration.showImportResultsSummary({
      result: {
        import_results: [
          { status: "ok", source_keys: ["source-a"] },
          { status: "error", error: "nested failure" },
        ],
      },
    });
    assert.equal(root.querySelector("[data-config-page-status]").textContent, "Imported 1, failed 1: nested failure");

    const form = document.createElement("form");
    form.dataset.sourceKind = "path";
    form.innerHTML = '<textarea name="path">one.jsonl\nmissing.jsonl</textarea>';
    root.append(form);
    globalThis.fetch = async path => ({
      ok: true,
      status: String(path) === "/api/sources" ? 202 : 200,
      statusText: "OK",
      text: async () => JSON.stringify(String(path) === "/api/sources"
        ? { operation_id: "import-op", operation_type: "source-import", state: "queued", completed: 0, total: 2, successes: [], failures: [] }
        : {
            operation_id: "import-op",
            operation_type: "source-import",
            state: "completed",
            completed: 2,
            total: 2,
            successes: [{ index: 0, status: "ok", path: "one.jsonl", source_keys: ["source-a"] }],
            failures: [{ index: 1, status: "error", error: "missing.jsonl was not found", item: { path: "missing.jsonl" } }],
          }),
    });
    await configuration.submitServeSourceForm(form);
    await tick();
    await tick();
    assert.equal(root.querySelector("[data-config-page-status]").textContent, "Imported 1, failed 1: missing.jsonl was not found");
  } finally {
    globalThis.fetch = previousFetch;
    configuration.harborConfigState.busy = false;
    root.hidden = true;
  }
});

test("one completed Configuration operation does not clear another operation's busy state", async () => {
  const previousFetch = globalThis.fetch;
  const root = document.querySelector("[data-config-page]");
  root.hidden = false;
  root.innerHTML = '<p data-config-page-status hidden></p><button type="button">Action</button>';
  const firstForm = document.createElement("form");
  firstForm.dataset.sourceKind = "path";
  firstForm.innerHTML = '<input name="path" value="first.jsonl">';
  const secondForm = document.createElement("form");
  secondForm.dataset.sourceKind = "path";
  secondForm.innerHTML = '<input name="path" value="second.jsonl">';
  document.body.append(firstForm, secondForm);
  let resolveFirstOperation;
  globalThis.fetch = async (path, options = {}) => {
    const requestPath = String(path);
    if (requestPath === "/api/sources") {
      const body = JSON.parse(String(options.body));
      const operationId = body.path.startsWith("first") ? "first-op" : "second-op";
      return {
        ok: true,
        status: 202,
        statusText: "Accepted",
        text: async () => JSON.stringify({ operation_id: operationId }),
      };
    }
    if (requestPath === "/api/operations/first-op") {
      return new Promise(resolve => { resolveFirstOperation = resolve; });
    }
    if (requestPath === "/api/operations/second-op") {
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        text: async () => JSON.stringify({ operation_id: "second-op", operation_type: "source-import", state: "completed", completed: 1, total: 1, successes: [], failures: [] }),
      };
    }
    throw new Error(`unexpected request: ${requestPath}`);
  };
  try {
    await configuration.submitServeSourceForm(firstForm);
    await tick();
    assert.equal(configuration.harborConfigState.busy, true);

    await configuration.submitServeSourceForm(secondForm);
    await tick();
    assert.equal(configuration.harborConfigState.busy, true);

    resolveFirstOperation({
      ok: true,
      status: 200,
      statusText: "OK",
      text: async () => JSON.stringify({ operation_id: "first-op", operation_type: "source-import", state: "completed", completed: 1, total: 1, successes: [], failures: [] }),
    });
    await tick();
    assert.equal(configuration.harborConfigState.busy, false);
  } finally {
    globalThis.fetch = previousFetch;
    configuration.harborConfigState.busy = false;
    firstForm.remove();
    secondForm.remove();
    root.hidden = true;
  }
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

test("remaining dialog surfaces are mutually exclusive and restore focus", () => {
  const opener = document.createElement("button");
  const login = document.createElement("div");
  const savedView = document.createElement("div");
  login.dataset.adminLoginDialog = "";
  login.innerHTML = '<section aria-modal="true"><button>Login</button></section>';
  savedView.dataset.viewSaveDialog = "";
  savedView.innerHTML = '<section aria-modal="true"><button>Save</button></section>';
  login.hidden = true;
  savedView.hidden = true;
  document.body.append(opener);
  document.body.append(login, savedView);
  opener.focus();

  modals.openModalSurface(login, {
    opener,
    bodyClass: "admin-login-open",
    focusTarget: login.querySelector("button"),
  });
  assert.equal(login.hidden, false);
  assert.equal(document.activeElement, login.querySelector("button"));

  modals.openModalSurface(savedView, {
    opener,
    bodyClass: "view-save-open",
    focusTarget: savedView.querySelector("button"),
  });
  assert.equal(login.hidden, true);
  assert.equal(savedView.hidden, false);

  modals.closeModalSurface(savedView);
  assert.equal(document.activeElement, opener);
  login.remove();
  savedView.remove();
  opener.remove();
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
    assert.equal(reportCell("session-a"), null);
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

test("workspace snapshot report previews fail closed for malformed or oversized data", () => {
  const previousMode = runtime.RENDER_OPTIONS.mode;
  runtime.RENDER_OPTIONS.mode = "workspace_snapshot";
  runtime.state.workspaceReports = [{
    report_id: "20260719-140000-000000",
    filename: "broken-report.html",
    format: "html",
    source_keys: [],
    preview_base64: "%%%not-base64%%%",
  }];
  try {
    assert.doesNotThrow(() => {
      reports.openWorkspaceReportReader("20260719-140000-000000");
    });
    const reader = document.querySelector("#workspace-report-reader");
    assert.match(reader.textContent, /invalid/i);
    assert.equal(reader.querySelector("[data-report-reader-frame]"), null);

    const reportLimit = 20 * 1024 * 1024;
    const oversizedBase64 = "A".repeat(Math.ceil((reportLimit + 1) / 3) * 4);
    assert.throws(
      () => reports.workspaceSnapshotReportPreviewUrl({ preview_base64: oversizedBase64 }),
      /20 MiB/i,
    );
  } finally {
    reports.closeWorkspaceReportReader({ restoreFocus: false });
    runtime.state.workspaceReports = [];
    runtime.RENDER_OPTIONS.mode = previousMode;
  }
});
