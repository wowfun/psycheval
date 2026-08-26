import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

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
      <span data-harbor-operation-status></span>
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

test("workbench page fills its content when its status notice is hidden", () => {
  const style = document.createElement("style");
  style.textContent = [
    "20-serve-toolbar.css",
    "23-harbor-workbench.css",
  ].map(name => readFileSync(
    new URL(`../../src/psycheval/assets/report_css/${name}`, import.meta.url),
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
    { path: "instruction.md", kind: "file", size: 8, editable: true },
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

test("Dataset overview renders status rails and saves text explicitly", async () => {
  const calls = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => {
    const method = options.method || "GET";
    const body = options.body ? JSON.parse(String(options.body)) : null;
    calls.push({ path: String(path), method, body });
    let payload = {};
    if (String(path) === "/api/harbor/datasets") payload = inventory;
    else if (String(path).startsWith("/api/harbor/task?")) payload = detail;
    else if (String(path).startsWith("/api/harbor/files?") && method === "GET") {
      payload = { path: "instruction.md", content: "Original", revision: "file-r1", task_revision: "task-r1" };
    } else if (String(path) === "/api/harbor/files" && method === "POST") {
      payload = {
        result: { ...detail, task: { ...detail.task, revision: "task-r2" } },
        operation: { operation_id: "file-op" },
      };
    } else if (String(path) === "/api/operations/file-op") {
      payload = {
        operation_id: "file-op",
        operation_type: "harbor-task-reconcile",
        state: "completed",
        completed: 1,
        total: 1,
        successes: [{ index: 0, status: "ok" }],
        failures: [],
      };
    }
    return {
      ok: true,
      status: method === "POST" ? 202 : 200,
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
    const save = calls.find(call => call.path === "/api/harbor/files" && call.method === "POST");
    assert.deepEqual(save.body, {
      action: "save",
      path: "instruction.md",
      content: "Changed",
      expected_revision: "task-r1",
      dataset_id: "pbench",
      task: "valid-task",
    });
    assert.equal(harbor.isHarborDirty(), false);
    assert.equal(calls.filter(call => call.path.startsWith("/api/harbor/task?")).length, 1);
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("dirty guard protects navigation and Archived is a separate overview", async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async path => {
    const requestPath = String(path);
    const payload = requestPath === "/api/harbor/datasets"
      ? inventory
      : requestPath.startsWith("/api/harbor/task?")
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
    const taskName = new URL(String(path), "http://localhost").searchParams.get("task");
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
      tree: [{ path: "draft.md", kind: "file", size: 1, editable: true }],
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
    if (requestPath === "/api/harbor/tasks" && method === "POST") payload = { result: { task: task("renamed-task", "draft", "renamed-r1") } };
    else if (requestPath === "/api/harbor/datasets") payload = renamedInventory;
    else if (requestPath.startsWith("/api/harbor/task?")) {
      const taskName = new URL(requestPath, "http://localhost").searchParams.get("task");
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
    if (requestPath === "/api/harbor/files" && options.method === "POST") {
      saveRequests += 1;
      return new Promise(resolve => pendingSaves.push(() => resolve({
        ok: true,
        status: 200,
        statusText: "OK",
        text: async () => JSON.stringify({ result: detail }),
      })));
    }
    if (requestPath === "/api/harbor/datasets") {
      return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify(inventory) };
    }
    if (requestPath.startsWith("/api/harbor/task?")) {
      return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify(detail) };
    }
    if (requestPath.startsWith("/api/harbor/files?") && (!options.method || options.method === "GET")) {
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
    operation_id: "archive-op",
    operation_type: "harbor-task-archive",
    state: "completed",
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
    if (requestPath === "/api/harbor/tasks/state") payload = { operation_id: operation.operation_id };
    else if (requestPath === "/api/harbor/tasks/delete") payload = { operation_id: operation.operation_id };
    else if (requestPath.startsWith("/api/operations/")) payload = operation;
    else if (requestPath === "/api/harbor/datasets") payload = harbor.workbenchState.inventory;
    else if (requestPath.startsWith("/api/harbor/task?")) {
      const url = new URL(requestPath, "http://localhost");
      const datasetId = url.searchParams.get("dataset_id");
      const taskName = url.searchParams.get("task");
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

    const archive = calls.find(call => call.path === "/api/harbor/tasks/state" && call.method === "POST");
    assert.deepEqual(archive.body, {
      archived: true,
      items: [
        { dataset_id: "one", task: "first", expected_revision: "first-r1" },
        { dataset_id: "two", task: "second", expected_revision: "second-r1" },
      ],
    });
    assert.deepEqual(Array.from(harbor.workbenchState.taskSelection), ["dataset:two|task:second"]);
    assert.match(document.querySelector("[data-harbor-workbench-status]").textContent, /second failed/);
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
    operation = { ...operation, operation_id: "restore-op", operation_type: "harbor-task-restore", total: 1, completed: 1, successes: [{ index: 0, status: "ok" }], failures: [] };
    calls.length = 0;
    harbor.renderHarborWorkbench();
    await harbor.mutateSelectedTaskState();
    await tick();

    const restore = calls.find(call => call.path === "/api/harbor/tasks/state" && call.method === "POST");
    assert.deepEqual(restore.body, {
      archived: false,
      items: [{
        dataset_id: "one",
        entry_id: "archive-1",
        directory: "restore-as-this",
        expected_revision: "archive-r1",
      }],
    });
  } finally {
    globalThis.fetch = previousFetch;
    harbor.workbenchState.busy = false;
    harbor.workbenchState.taskSelection.clear();
  }
});

test("invalid step counts and oversized uploads stop before request or file read", async () => {
  const previousFetch = globalThis.fetch;
  const previousPrompt = window.prompt;
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
    const answers = ["bad-steps", "local/bad-steps", "not-a-number"];
    window.prompt = () => answers.shift();
    await harbor.createTask();

    let reads = 0;
    window.prompt = (_message, fallback) => fallback;
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
      document.querySelector("[data-harbor-workbench-status]").textContent,
      /16 MiB/,
    );
  } finally {
    window.prompt = previousPrompt;
    globalThis.fetch = previousFetch;
  }
});
