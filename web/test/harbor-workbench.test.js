import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { installBrowserDom, submitActionForm } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin","sources":[]}</script>
  <section data-harbor-workbench>
      <button data-harbor-reload>Reload</button>
      <button data-harbor-create-task>New Task</button>
      <button data-harbor-sync-manifest>Sync</button>
      <button data-harbor-state-selected>Archive selected</button>
      <button data-harbor-delete-selected>Delete selected</button>
      <button data-harbor-show-trash>Show archived</button>
      <p data-harbor-workbench-status hidden></p>
      <div class="harbor-overview-head"></div><div class="harbor-editor-head"></div>
      <input data-harbor-search type="search">
      <span data-harbor-overview-count></span>
      <div data-harbor-overview></div>
      <h2 data-harbor-selected-title></h2>
      <span data-harbor-selected-meta></span>
      <div data-harbor-file-actions hidden>
        <button data-harbor-new-file>New file</button>
        <button data-harbor-new-directory>New folder</button>
        <button data-harbor-upload>Upload</button>
        <input type="file" data-harbor-upload-input>
      </div>
      <div data-harbor-task-browser>
        <div data-harbor-file-tree></div>
        <strong data-harbor-editor-path></strong>
        <span data-harbor-editor-meta></span>
        <button data-harbor-save disabled>Save</button>
        <textarea data-harbor-editor disabled></textarea>
      </div>
      <div data-harbor-diagnostics></div>
  </section>
`);

const harbor = await import("../../src/psycheval/assets/web/modules/harbor-workbench.js");
const tick = () => new Promise(resolve => setTimeout(resolve, 0));
harbor.bindHarborWorkbench();

test.after(() => browser.cleanup());
test.afterEach(() => {
  document.querySelectorAll(".action-feedback button").forEach(button => {
    if (button.textContent === "Close") button.click();
  });
});

test("workbench page fills its content when its status notice is hidden", () => {
  const style = document.createElement("style");
  style.textContent = [
    "20-serve-toolbar.css",
    "23-harbor-workbench.css",
  ].map(name => readFileSync(
    new URL(`../../src/psycheval/assets/css/${name}`, import.meta.url),
    "utf8",
  )).join("\n");
  const workbench = document.createElement("section");
  workbench.className = "harbor-workbench";
  workbench.innerHTML = `
    <header></header>
    <p class="serve-notice harbor-workbench-status" hidden></p>
    <div class="harbor-workbench-tools"></div>
    <div class="harbor-workbench-grid"></div>
  `;
  document.head.append(style);
  document.body.append(workbench);
  try {
    const status = workbench.querySelector(".harbor-workbench-status");
    const grid = workbench.querySelector(".harbor-workbench-grid");
    const workbenchStyle = window.getComputedStyle(workbench);
    assert.equal(workbenchStyle.display, "flex");
    assert.equal(workbenchStyle.flexDirection, "column");
    assert.equal(window.getComputedStyle(status).position, "static");
    assert.equal(window.getComputedStyle(grid).flexGrow, "1");
  } finally {
    workbench.remove();
    style.remove();
  }
});

function task(directory, status, revision = `${directory}-revision`) {
  return {
    directory,
    package_name: `local/${directory}`,
    status,
    revision,
    diagnostics: status === "draft" ? ["task.toml: missing field"] : [],
  };
}

const detail = {
  dataset_id: "pbench",
  task: task("valid-task", "valid", "task-r1"),
  default_file_path: "instruction.md",
  tree: [
    { path: "environment", kind: "directory", size: null },
    { path: "instruction.md", kind: "file", size: 8, previewable: true, editable: true },
  ],
};

const inventory = {
  revision: "config-r1",
  datasets: [{
    id: "pbench",
    path: "/datasets/pbench",
    revision: "dataset-r1",
    manifest_status: "stale",
    manifest_diagnostic: null,
    tasks: [task("valid-task", "valid", "task-r1"), task("draft-task", "draft")],
    trash: [{
      entry_id: "trash-1",
      directory: "old-task",
      package_name: "local/old-task",
      status: "trash",
      revision: "trash-r1",
    }],
  }],
};

for (const reconcileFails of [false, true]) test(`Dataset file save stays committed when reconcile ${reconcileFails ? "fails" : "succeeds"}`, async () => {
  const calls = [];
  let committedContent = "Original";
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => {
    const method = options.method || "GET";
    const body = options.body ? JSON.parse(String(options.body)) : null;
    calls.push({ path: String(path), method, body });
    let payload = {};
    if (String(path) === "/api/harbor/datasets") payload = inventory;
    else if (String(path) === "/api/harbor/datasets/pbench/tasks/valid-task") payload = detail;
    else if (String(path).endsWith("/tasks/valid-task/files/instruction.md") && method === "GET") {
      payload = { path: "instruction.md", content: committedContent, revision: "file-r1", task_revision: "task-r1" };
    } else if (String(path).endsWith("/tasks/valid-task/files/instruction.md") && method === "PUT") {
      committedContent = body.content;
      payload = { id: "file-op", kind: "harbor-task-file", state: "queued", completed: 0, total: 1, successes: [], failures: [] };
    } else if (String(path) === "/api/operations/file-op") {
      payload = {
        id: "file-op",
        kind: "harbor-task-file",
        state: reconcileFails ? "failed" : "succeeded",
        completed: 1,
        total: 1,
        successes: [{ index: 0, status: "ok" }],
        failures: reconcileFails ? [{ error: "Index offline" }] : [],
      };
    }
    return {
      ok: true,
      status: method === "PUT" ? 202 : 200,
      statusText: "OK",
      text: async () => JSON.stringify(payload),
    };
  };
  try {
    assert.equal(await harbor.openHarborWorkbench(), true);
    assert.equal(document.querySelectorAll(".harbor-overview-row").length, 2);
    assert.equal(document.querySelectorAll(".status-valid").length, 1);
    assert.equal(document.querySelectorAll(".status-draft").length, 1);
    assert.doesNotMatch(document.querySelector("[data-harbor-overview]").textContent, /Manifest|stale/);

    assert.equal(document.querySelectorAll(".harbor-file-row").length, 2);
    const editor = document.querySelector("[data-harbor-editor]");
    assert.equal(editor.value, "Original");
    assert.equal(document.querySelector("[data-harbor-download]"), null);
    editor.value = "Changed";
    editor.dispatchEvent(new window.Event("input", { bubbles: true }));
    assert.equal(harbor.isHarborDirty(), true);
    assert.equal(document.querySelector("[data-harbor-save]").disabled, false);

    await harbor.saveFile();
    await tick();
    await tick();
    const save = calls.find(call => call.path.endsWith("/tasks/valid-task/files/instruction.md") && call.method === "PUT");
    assert.deepEqual(save.body, {
      content: "Changed",
    });
    assert.equal(harbor.isHarborDirty(), false);
    assert.equal(editor.value, "Changed");
    if (reconcileFails) {
      const status = document.querySelector(".harbor-editor-head");
      assert.match(status.textContent, /Saved, but background reconciliation failed/);
      [...status.querySelectorAll("button")].find(button => button.textContent === "Refresh").click();
      await tick(); await tick();
      assert.equal(calls.filter(call => call.method === "PUT").length, 1);
    }
    assert.ok(calls.filter(call => call.path === "/api/harbor/datasets/pbench/tasks/valid-task").length >= 2);
  } finally {
    globalThis.fetch = previousFetch;
  }
});

for (const large of [false, true]) test(`a file conflict retains the draft with a bounded saved preview (large=${large})`, async () => {
  const previousFetch = globalThis.fetch;
  const writes = [];
  let conflicted = false;
  globalThis.fetch = async (path, options = {}) => {
    if (options.method === "PUT") {
      writes.push({ body: JSON.parse(options.body), revision: options.headers["If-Match"] });
      conflicted = true;
      return new Response(JSON.stringify({ detail: "File changed elsewhere" }), { status: 412 });
    }
    const payload = path === "/api/harbor/datasets" ? inventory
      : path.endsWith("/files/instruction.md")
        ? { path: "instruction.md", content: conflicted ? (large ? "Remote change\n" + "x".repeat(2 * 1024 * 1024 - 30) + "END OF FILE" : "Remote change") : "Original", revision: conflicted ? "file-r2" : "file-r1" }
        : detail;
    return new Response(JSON.stringify(payload), { headers: { ETag: conflicted ? '"file-r2"' : '"file-r1"' } });
  };
  try {
    await harbor.openHarborWorkbench();
    const editor = document.querySelector("[data-harbor-editor]");
    editor.value = "My draft";
    editor.dispatchEvent(new window.Event("input", { bubbles: true }));
    await harbor.saveFile();
    assert.equal(editor.value, "My draft");
    assert.equal(harbor.isHarborDirty(), true);
    assert.match(document.querySelector(".harbor-editor-head").textContent, /File changed elsewhere/);
    assert.match(document.querySelector(".harbor-editor-head details").textContent, /Remote change/);
    if (large) {
      const preview = document.querySelector(".harbor-editor-head details").textContent;
      assert.ok(preview.length < 20000);
      assert.match(preview, /Preview truncated/);
      assert.doesNotMatch(preview, /END OF FILE/);
    }
    assert.equal(writes.length, 1);
    await harbor.saveFile();
    assert.deepEqual(writes, [
      { body: { content: "My draft" }, revision: '"file-r1"' },
      { body: { content: "My draft" }, revision: '"file-r2"' },
    ]);
  } finally {
    document.querySelector("[data-harbor-editor]").value = "Original";
    document.querySelector("[data-harbor-editor]").dispatchEvent(new window.Event("input", { bubbles: true }));
    globalThis.fetch = previousFetch;
  }
});

test("Task rename preserves edits made during the request and rebinds file reads", async () => {
  const previousFetch = globalThis.fetch, previousConfirm = window.confirm;
  let accept, renamed = false;
  const requests = [];
  globalThis.fetch = async (path, options = {}) => {
    requests.push({ path, method: options.method });
    if (options.method === "PATCH") return new Promise(resolve => {
      accept = () => {
        renamed = true;
        resolve(new Response(JSON.stringify({ id: "rename-draft-op" }), { status: 202 }));
      };
    });
    const currentInventory = structuredClone(inventory);
    if (renamed) currentInventory.datasets[0].tasks[0].directory = "renamed-live";
    const payload = path === "/api/harbor/datasets" ? currentInventory
      : path === "/api/operations/rename-draft-op" ? { state: "failed", failures: [{ error: "Index offline" }] }
        : path.includes("/files/") ? { path: "instruction.md", content: "Original", revision: "file-r1" }
          : detail;
    return new Response(JSON.stringify(payload));
  };
  try {
    window.confirm = () => true;
    await harbor.openHarborWorkbench();
    const cell = document.querySelector('[data-table-column-key="task"][data-table-editable]')
      || document.querySelector('[data-table-column-key="task"]');
    cell.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
    const input = cell.querySelector(".table-cell-editor-control");
    input.value = "renamed-live";
    input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await tick();
    assert.equal(typeof accept, "function");
    const editor = document.querySelector("[data-harbor-editor]");
    assert.equal(editor.disabled, false);
    editor.value = "Typed while rename was pending";
    editor.dispatchEvent(new window.Event("input", { bubbles: true }));
    accept();
    await tick(); await tick();
    assert.equal(editor.value, "Typed while rename was pending");
    assert.equal(harbor.isHarborDirty(), true);
    assert.equal(harbor.workbenchState.taskName, "renamed-live");
    const beforeRead = requests.length;
    document.querySelector("[data-harbor-file-tree] .kind-file").click();
    await tick();
    assert.ok(requests.slice(beforeRead).some(request => request.path.includes("/tasks/renamed-live/files/")));
  } finally {
    globalThis.fetch = previousFetch; window.confirm = previousConfirm;
    harbor.workbenchState.taskName = "valid-task";
  }
});

test("dirty guard protects navigation and Archived is a separate overview", async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async path => {
    const requestPath = String(path);
    const payload = requestPath === "/api/harbor/datasets"
      ? inventory
      : requestPath === "/api/harbor/datasets/pbench/tasks/valid-task"
        ? detail
        : { path: "instruction.md", content: "Original", revision: "file-r1" };
    return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify(payload) };
  };
  const surface = document.querySelector("[data-harbor-workbench]");
  const previousConfirm = window.confirm;
  try {
    harbor.workbenchState.showTrash = false;
    harbor.workbenchState.search = "";
    await harbor.openHarborWorkbench();
    const editor = document.querySelector("[data-harbor-editor]");
    editor.value = "Changed";
    editor.dispatchEvent(new window.Event("input", { bubbles: true }));

    window.confirm = () => false;
    assert.equal(harbor.confirmDiscard(), false);
    document.querySelector("[data-harbor-show-trash]").click();
    assert.equal(document.querySelectorAll(".status-valid").length, 1);
    assert.equal(harbor.closeHarborWorkbench(), false);
    assert.equal(surface.hidden, false);

    window.confirm = () => true;
    document.querySelector("[data-harbor-show-trash]").click();
    assert.equal(document.querySelectorAll(".status-trash").length, 1);
    assert.equal(document.querySelectorAll(".status-valid").length, 0);
  } finally {
    window.confirm = previousConfirm;
    globalThis.fetch = previousFetch;
  }
});

test("the latest overlapping Task selection owns the file tree", async () => {
  const previousFetch = globalThis.fetch;
  const pending = new Map();
  globalThis.fetch = path => new Promise(resolve => {
    const taskName = decodeURIComponent(String(path).split("/tasks/")[1] || "");
    pending.set(taskName, payload => resolve({
      ok: true,
      status: 200,
      statusText: "OK",
      text: async () => JSON.stringify(payload),
    }));
  });
  try {
    const surface = document.querySelector("[data-harbor-workbench]");
    harbor.workbenchState.inventory = inventory;
    harbor.workbenchState.datasetId = "pbench";
    harbor.workbenchState.taskName = null;
    harbor.workbenchState.taskDetail = null;
    harbor.workbenchState.showTrash = false;
    harbor.workbenchState.search = "";
    harbor.renderHarborWorkbench();

    document.querySelectorAll("[data-harbor-overview-row]")[0].click();
    document.querySelectorAll("[data-harbor-overview-row]")[1].click();
    pending.get("draft-task")({
      dataset_id: "pbench",
      task: task("draft-task", "draft"),
      tree: [{ path: "draft.md", kind: "file", size: 1, previewable: true, editable: true }],
    });
    await tick();
    pending.get("valid-task")(detail);
    await tick();

    assert.equal(harbor.workbenchState.taskName, "draft-task");
    assert.equal(harbor.workbenchState.taskDetail.task.directory, "draft-task");
    assert.match(document.querySelector("[data-harbor-file-tree]").textContent, /draft\.md/);
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("renaming the open Task keeps the renamed Task selected", async () => {
  const previousFetch = globalThis.fetch;
  const renamedInventory = {
    ...inventory,
    datasets: [{
      ...inventory.datasets[0],
      tasks: [task("valid-task", "valid", "task-r1"), task("renamed-task", "draft", "renamed-r1")],
    }],
  };
  globalThis.fetch = async (path, options = {}) => {
    const requestPath = String(path);
    const method = options.method || "GET";
    let payload;
    if (requestPath === "/api/harbor/datasets/pbench/tasks/draft-task" && method === "PATCH") {
      payload = { id: "rename-op", kind: "harbor-task-reconcile", state: "queued", completed: 0, total: 1, successes: [], failures: [] };
    }
    else if (requestPath === "/api/operations/rename-op") payload = { id: "rename-op", kind: "harbor-task-reconcile", state: "succeeded", completed: 1, total: 1, successes: [{ index: 0, status: "ok" }], failures: [] };
    else if (requestPath === "/api/harbor/datasets") payload = renamedInventory;
    else if (requestPath.includes("/api/harbor/datasets/pbench/tasks/")) {
      const taskName = decodeURIComponent(requestPath.split("/tasks/")[1]);
      payload = { dataset_id: "pbench", task: task(taskName, taskName === "valid-task" ? "valid" : "draft"), tree: [] };
    } else throw new Error(`unexpected request: ${requestPath}`);
    return {
      ok: true,
      status: 200,
      statusText: "OK",
      text: async () => JSON.stringify(payload),
    };
  };
  try {
    harbor.workbenchState.inventory = inventory;
    harbor.workbenchState.datasetId = "pbench";
    harbor.workbenchState.taskName = "draft-task";
    harbor.workbenchState.taskDetail = { dataset_id: "pbench", task: task("draft-task", "draft"), tree: [] };
    harbor.workbenchState.showTrash = false;
    harbor.workbenchState.search = "";
    harbor.workbenchState.busy = false;
    harbor.renderHarborWorkbench();

    const row = Array.from(document.querySelectorAll("[data-harbor-overview-row]"))
      .find(node => node.textContent.includes("draft-task"));
    const taskCell = row.querySelector('[data-table-column-key="task"]');
    taskCell.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
    const input = taskCell.querySelector(".table-cell-editor-control");
    input.value = "renamed-task";
    input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await tick();
    await tick();
    await tick();

    assert.equal(harbor.workbenchState.taskName, "renamed-task");
    assert.equal(document.querySelector("[data-harbor-selected-title]").textContent, "renamed-task");
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("a pending file save rejects an overlapping save", async () => {
  const previousFetch = globalThis.fetch;
  const pendingSaves = [];
  let saveRequests = 0;
  globalThis.fetch = async (path, options = {}) => {
    const requestPath = String(path);
    if (requestPath.endsWith("/tasks/valid-task/files/instruction.md") && options.method === "PUT") {
      saveRequests += 1;
      return new Promise(resolve => pendingSaves.push(() => resolve({
        ok: true,
        status: 200,
        statusText: "OK",
        text: async () => JSON.stringify({ id: "save-op", kind: "harbor-task-file", state: "queued", completed: 0, total: 1, successes: [], failures: [] }),
      })));
    }
    if (requestPath === "/api/harbor/datasets") {
      return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify(inventory) };
    }
    if (requestPath === "/api/harbor/datasets/pbench/tasks/valid-task") {
      return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify(detail) };
    }
    if (requestPath.endsWith("/tasks/valid-task/files/instruction.md") && (!options.method || options.method === "GET")) {
      return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify({ path: "instruction.md", content: "Original", revision: "file-r1" }) };
    }
    throw new Error(`unexpected request: ${requestPath}`);
  };
  try {
    harbor.workbenchState.busy = false;
    harbor.workbenchState.showTrash = false;
    harbor.workbenchState.search = "";
    await harbor.openHarborWorkbench();
    const editor = document.querySelector("[data-harbor-editor]");
    editor.value = "Changed";
    editor.dispatchEvent(new window.Event("input", { bubbles: true }));

    const first = harbor.saveFile();
    const second = harbor.saveFile();
    await tick();
    assert.equal(saveRequests, 1);
    pendingSaves[0]();
    await Promise.all([first, second]);
    for (let attempt = 0; harbor.workbenchState.busy && attempt < 50; attempt++) await tick();
    assert.equal(harbor.workbenchState.busy, false);
  } finally {
    globalThis.fetch = previousFetch;
    harbor.workbenchState.busy = false;
  }
});

test("cross-field search coordinates selection and keeps empty Datasets visible", () => {
  harbor.workbenchState.inventory = {
    revision: "config-r2",
    datasets: [
      inventory.datasets[0],
      {
        id: "empty-dataset",
        revision: "empty-r1",
        tasks: [],
        trash: [],
      },
    ],
  };
  harbor.workbenchState.showTrash = false;
  harbor.workbenchState.search = "missing field";
  harbor.workbenchState.datasetId = "pbench";
  harbor.workbenchState.taskName = "valid-task";
  harbor.workbenchState.taskDetail = detail;

  harbor.renderHarborWorkbench();
  assert.equal(document.querySelectorAll("[data-harbor-overview-row]").length, 1);
  assert.equal(harbor.workbenchState.taskName, "draft-task");

  harbor.workbenchState.search = "empty-dataset";
  harbor.renderHarborWorkbench();
  assert.equal(document.querySelectorAll(".status-empty").length, 1);
  assert.equal(harbor.workbenchState.datasetId, "empty-dataset");
  assert.equal(harbor.workbenchState.taskName, null);

  harbor.workbenchState.search = "no-such-task";
  harbor.renderHarborWorkbench();
  assert.equal(document.querySelectorAll("[data-harbor-overview-row]").length, 0);
  assert.equal(harbor.workbenchState.datasetId, null);
  assert.equal(document.querySelectorAll(".harbor-file-row").length, 0);
});

test("Task batches span Datasets, restore edited archive names, and retain only failures", async () => {
  const previousFetch = globalThis.fetch;
  const first = task("first", "valid", "first-r1");
  const second = task("second", "valid", "second-r1");
  const multiInventory = {
    revision: "config-r3",
    datasets: [
      { id: "one", revision: "one-r1", tasks: [first], trash: [] },
      { id: "two", revision: "two-r1", tasks: [second], trash: [] },
    ],
  };
  const calls = [];
  let operation = {
    id: "archive-op",
    kind: "harbor-task-archive",
    state: "succeeded",
    completed: 2,
    total: 2,
    successes: [{ index: 0, status: "ok" }],
    failures: [{ index: 1, status: "error", error: "second failed" }],
  };
  globalThis.fetch = async (path, options = {}) => {
    const requestPath = String(path);
    const method = options.method || "GET";
    const body = options.body ? JSON.parse(String(options.body)) : null;
    calls.push({ path: requestPath, method, body });
    let payload;
    if (requestPath === "/api/harbor/task-state-operations") payload = operation;
    else if (requestPath === "/api/harbor/task-deletion-operations") payload = operation;
    else if (requestPath.startsWith("/api/operations/")) payload = operation;
    else if (requestPath === "/api/harbor/datasets") payload = harbor.workbenchState.inventory;
    else if (requestPath.includes("/api/harbor/datasets/") && requestPath.includes("/tasks/")) {
      const [, suffix] = requestPath.split("/api/harbor/datasets/");
      const [datasetId, taskName] = suffix.split("/tasks/").map(decodeURIComponent);
      payload = { dataset_id: datasetId, task: task(taskName, "valid"), tree: [] };
    } else throw new Error(`unexpected request: ${requestPath}`);
    return {
      ok: true,
      status: method === "POST" ? 202 : 200,
      statusText: "OK",
      text: async () => JSON.stringify(payload),
    };
  };

  try {
    harbor.workbenchState.inventory = multiInventory;
    harbor.workbenchState.datasetId = "one";
    harbor.workbenchState.taskName = "first";
    harbor.workbenchState.showTrash = false;
    harbor.workbenchState.search = "";
    harbor.workbenchState.busy = false;
    harbor.workbenchState.taskSelection = new Set([
      "dataset:one|task:first",
      "dataset:two|task:second",
    ]);
    harbor.renderHarborWorkbench();
    await harbor.mutateSelectedTaskState();
    await tick();
    await tick();

    const archive = calls.find(call => call.path === "/api/harbor/task-state-operations" && call.method === "POST");
    assert.deepEqual(archive.body, {
      archived: true,
      items: [
        { dataset_id: "one", task: "first", etag: "first-r1" },
        { dataset_id: "two", task: "second", etag: "second-r1" },
      ],
    });
    assert.deepEqual(Array.from(harbor.workbenchState.taskSelection), ["dataset:two|task:second"]);
    assert.match(document.querySelector(".harbor-overview-head").textContent, /second failed/);
    assert.equal(harbor.workbenchState.busy, false);

    const archivedEntry = {
      entry_id: "archive-1",
      directory: "restore-as-this",
      package_name: "local/old",
      status: "trash",
      revision: "archive-r1",
    };
    harbor.workbenchState.inventory = {
      revision: "config-r4",
      datasets: [{ id: "one", revision: "one-r2", tasks: [], trash: [archivedEntry] }],
    };
    harbor.workbenchState.showTrash = true;
    harbor.workbenchState.taskSelection = new Set(["dataset:one|trash:archive-1"]);
    harbor.workbenchState.busy = false;
    operation = { ...operation, id: "restore-op", kind: "harbor-task-restore", total: 1, completed: 1, successes: [{ index: 0, status: "ok" }], failures: [] };
    calls.length = 0;
    harbor.renderHarborWorkbench();
    await harbor.mutateSelectedTaskState();
    await tick();

    const restore = calls.find(call => call.path === "/api/harbor/task-state-operations" && call.method === "POST");
    assert.deepEqual(restore.body, {
      archived: false,
      items: [{
        dataset_id: "one",
        entry_id: "archive-1",
        directory: "restore-as-this",
        etag: "archive-r1",
      }],
    });
  } finally {
    globalThis.fetch = previousFetch;
    harbor.workbenchState.busy = false;
    harbor.workbenchState.taskSelection.clear();
  }
});

test("a newly created Task is selected after its queued reconcile completes", async () => {
  const previousFetch = globalThis.fetch;
  const previousPrompt = window.prompt;
  const createdInventory = {
    ...inventory,
    datasets: [{
      ...inventory.datasets[0],
      tasks: [...inventory.datasets[0].tasks, task("new-task", "valid", "new-r1")],
    }],
  };
  const answers = ["new-task", "local/new-task", "0"];
  window.prompt = () => answers.shift();
  globalThis.fetch = async (path, options = {}) => {
    const requestPath = String(path);
    const method = options.method || "GET";
    let payload;
    if (requestPath === "/api/harbor/datasets/pbench/tasks" && method === "POST") {
      payload = { id: "create-op", kind: "harbor-task-reconcile", state: "queued", completed: 0, total: 1, successes: [], failures: [] };
    } else if (requestPath === "/api/operations/create-op") {
      payload = { id: "create-op", kind: "harbor-task-reconcile", state: "succeeded", completed: 1, total: 1, successes: [{ index: 0, status: "ok" }], failures: [] };
    } else if (requestPath === "/api/harbor/datasets") {
      payload = createdInventory;
    } else if (requestPath.includes("/api/harbor/datasets/pbench/tasks/")) {
      const taskName = decodeURIComponent(requestPath.split("/tasks/")[1]);
      payload = {
        dataset_id: "pbench",
        task: task(taskName, "valid", taskName === "new-task" ? "new-r1" : "task-r1"),
        default_file_path: null,
        tree: [],
      };
    } else throw new Error(`unexpected request: ${requestPath}`);
    return {
      ok: true,
      status: method === "POST" ? 202 : 200,
      statusText: "OK",
      text: async () => JSON.stringify(payload),
    };
  };

  try {
    harbor.workbenchState.inventory = inventory;
    harbor.workbenchState.datasetId = "pbench";
    harbor.workbenchState.taskName = "valid-task";
    harbor.workbenchState.taskDetail = detail;
    harbor.workbenchState.showTrash = false;
    harbor.workbenchState.search = "";
    harbor.workbenchState.busy = false;
    harbor.renderHarborWorkbench();

    await harbor.createTask();
    submitActionForm({ directory: "new-task", package_name: "local/new-task", steps: "0" });
    for (let index = 0; index < 5; index += 1) await tick();

    assert.equal(harbor.workbenchState.taskName, "new-task");
    assert.equal(harbor.workbenchState.taskDetail.task.directory, "new-task");
  } finally {
    window.prompt = previousPrompt;
    globalThis.fetch = previousFetch;
    harbor.workbenchState.busy = false;
  }
});

test("invalid step counts and oversized uploads stop before request or file read", async () => {
  const previousFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (...args) => {
    calls.push(args);
    throw new Error("unexpected request");
  };
  harbor.workbenchState.inventory = inventory;
  harbor.workbenchState.datasetId = "pbench";
  harbor.workbenchState.taskName = "valid-task";
  harbor.workbenchState.taskDetail = detail;
  try {
    await harbor.createTask();
    const form = submitActionForm({ directory: "bad-steps", package_name: "local/bad-steps", steps: "51" });
    assert.equal(form.checkValidity(), false);
    form.querySelector('[type="button"]').click();

    let reads = 0;
    await harbor.uploadFile({
      name: "large.bin",
      size: 16 * 1024 * 1024 + 1,
      arrayBuffer: async () => {
        reads += 1;
        return new ArrayBuffer(0);
      },
    });

    assert.equal(calls.length, 0);
    assert.equal(reads, 0);
    assert.match(
      document.querySelector(".harbor-editor-head").textContent,
      /16 MiB/,
    );
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("WorkBuddy Datasets remain browsable while every editing surface is disabled", async () => {
  const previousFetch = globalThis.fetch;
  const previousPrompt = window.prompt;
  const calls = [];
  const readonlyInventory = {
    revision: "config-r2",
    datasets: [{
      id: "wb-office",
      format: "workbuddy.v1",
      read_only: true,
      revision: "dataset-r2",
      tasks: [task("office-task", "registered", "task-r2")],
      trash: [],
    }],
  };
  const readonlyDetail = {
    dataset_id: "wb-office",
    format: "workbuddy.v1",
    read_only: true,
    task: task("office-task", "valid", "task-r2"),
    default_file_path: "instruction.md",
    tree: [{ path: "instruction.md", kind: "file", size: 11, previewable: true, editable: false }],
  };
  globalThis.fetch = async (path, options = {}) => {
    calls.push({ path: String(path), method: options.method || "GET" });
    const requestPath = String(path);
    const payload = requestPath === "/api/harbor/datasets"
      ? readonlyInventory
      : requestPath === "/api/harbor/datasets/wb-office/tasks/office-task"
        ? readonlyDetail
        : requestPath.endsWith("/files/instruction.md")
          ? { path: "instruction.md", content: "Read me only", revision: "file-r2" }
          : {};
    return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify(payload) };
  };
  window.prompt = () => {
    throw new Error("read-only actions must not prompt");
  };
  try {
    harbor.workbenchState.taskSelection.clear();
    harbor.workbenchState.busy = false;
    harbor.workbenchState.showTrash = false;
    harbor.workbenchState.search = "";
    await harbor.openHarborWorkbench();

    assert.equal(document.querySelectorAll("[data-table-row-select]").length, 0);
    assert.equal(document.querySelector("[data-harbor-create-task]").disabled, true);
    assert.equal(document.querySelector("[data-harbor-sync-manifest]").disabled, true);
    assert.equal(document.querySelector("[data-harbor-file-actions]").hidden, true);
    assert.equal(document.querySelector("[data-workbuddy-summaries]"), null);
    assert.match(document.querySelector("[data-harbor-selected-meta]").textContent, /workbuddy\.v1/);
    assert.match(document.querySelector("[data-harbor-selected-meta]").textContent, /Read-only/);
    assert.match(document.querySelector("[data-harbor-selected-meta]").textContent, /valid/);
    assert.equal(document.querySelectorAll(".status-registered").length, 1);
    const editor = document.querySelector("[data-harbor-editor]");
    assert.equal(editor.value, "Read me only");
    assert.equal(editor.readOnly, true);
    assert.equal(document.querySelector("[data-harbor-save]").disabled, true);

    const taskCell = document.querySelector('[data-table-column-key="task"]');
    taskCell.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
    assert.equal(taskCell.querySelector(".table-cell-editor-control"), null);
    await harbor.createTask();
    await harbor.createFile("file");
    await harbor.saveFile();
    assert.ok(calls.every(call => call.method === "GET"));
  } finally {
    window.prompt = previousPrompt;
    globalThis.fetch = previousFetch;
  }
});


test("repeated failures loading one Task replace that action's feedback", async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error("Task read failed"); };
  try {
    harbor.workbenchState.inventory = inventory;
    harbor.workbenchState.datasetId = "pbench";
    harbor.workbenchState.taskName = null;
    harbor.workbenchState.taskDetail = null;
    harbor.workbenchState.showTrash = false;
    harbor.workbenchState.search = "";
    harbor.workbenchState.busy = false;
    harbor.renderHarborWorkbench();
    const row = harbor.overviewRows().find(row => row.task?.directory === "valid-task");
    for (let index = 0; index < 5; index++) await harbor.selectOverviewRow(row);
    const errors = [...document.querySelectorAll(".harbor-editor-head .action-feedback")]
      .filter(node => node.textContent.includes("Task read failed"));
    assert.equal(errors.length, 1);
  } finally { globalThis.fetch = previousFetch; }
});
