import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-data">{}</script>
  <script type="application/json" id="peval-token-estimates">{}</script>
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin","sources":[]}</script>
  <section data-harbor-workbench>
      <button data-harbor-reload>Reload</button>
      <button data-harbor-add-dataset>New Dataset</button>
      <button data-harbor-register-dataset>Register</button>
      <button data-harbor-edit-dataset>Edit Dataset</button>
      <button data-harbor-remove-dataset>Remove Dataset</button>
      <button data-harbor-create-task>New Task</button>
      <button data-harbor-sync-manifest>Sync</button>
      <button data-harbor-rename-task>Rename Task</button>
      <button data-harbor-trash-task>Trash Task</button>
      <button data-harbor-restore-task hidden>Restore</button>
      <button data-harbor-purge-task hidden>Purge</button>
      <button data-harbor-show-trash>Trash</button>
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
      <div data-harbor-file-tree></div>
      <strong data-harbor-editor-path></strong>
      <span data-harbor-editor-meta></span>
      <button data-harbor-download hidden>Download</button>
      <button data-harbor-save disabled>Save</button>
      <textarea data-harbor-editor disabled></textarea>
      <div data-harbor-diagnostics></div>
  </section>
`);

const harbor = await import("../src/modules/harbor-workbench.js");
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
  tree: [
    { path: "environment", kind: "directory", size: null },
    { path: "instruction.md", kind: "file", size: 8, editable: true, downloadable: true },
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
      payload = { result: { ...detail, task: { ...detail.task, revision: "task-r2" } } };
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
    document.querySelector(".harbor-file-row.kind-file").click();
    await tick();
    await tick();
    const editor = document.querySelector("[data-harbor-editor]");
    assert.equal(editor.value, "Original");
    editor.value = "Changed";
    editor.dispatchEvent(new window.Event("input", { bubbles: true }));
    assert.equal(harbor.isHarborDirty(), true);
    assert.equal(document.querySelector("[data-harbor-save]").disabled, false);

    await harbor.saveFile();
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
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("dirty guard protects navigation and Trash is a separate overview", async () => {
  const surface = document.querySelector("[data-harbor-workbench]");
  harbor.workbenchState.inventory = inventory;
  harbor.workbenchState.datasetId = "pbench";
  harbor.workbenchState.taskName = "valid-task";
  harbor.workbenchState.showTrash = false;
  harbor.workbenchState.search = "";
  harbor.workbenchState.dirty = false;
  harbor.renderHarborWorkbench();
  document.querySelector("[data-harbor-show-trash]").click();
  assert.equal(document.querySelectorAll(".status-trash").length, 1);
  assert.equal(document.querySelectorAll(".status-valid").length, 0);

  harbor.workbenchState.dirty = true;
  const previousConfirm = window.confirm;
  window.confirm = () => false;
  assert.equal(harbor.confirmDiscard(), false);
  assert.equal(harbor.closeHarborWorkbench(), false);
  assert.equal(surface.hidden, false);
  window.confirm = () => true;
  assert.equal(harbor.confirmDiscard(), true);
  assert.equal(harbor.closeHarborWorkbench(), false);
  assert.equal(surface.hidden, false);
  window.confirm = previousConfirm;
  harbor.workbenchState.dirty = false;
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
    harbor.workbenchState.dirty = false;
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

test("the latest overlapping file selection owns the editor", async () => {
  const previousFetch = globalThis.fetch;
  const pending = new Map();
  globalThis.fetch = path => new Promise(resolve => {
    const filePath = new URL(String(path), "http://localhost").searchParams.get("path");
    pending.set(filePath, content => resolve({
      ok: true,
      status: 200,
      statusText: "OK",
      text: async () => JSON.stringify({
        path: filePath,
        content,
        revision: `${filePath}-revision`,
        task_revision: "task-r1",
      }),
    }));
  });
  try {
    harbor.workbenchState.inventory = inventory;
    harbor.workbenchState.datasetId = "pbench";
    harbor.workbenchState.taskName = "valid-task";
    harbor.workbenchState.taskDetail = {
      ...detail,
      tree: [
        { path: "first.md", kind: "file", size: 5, editable: true },
        { path: "second.md", kind: "file", size: 6, editable: true },
      ],
    };
    harbor.workbenchState.filePath = null;
    harbor.workbenchState.dirty = false;
    harbor.renderHarborWorkbench();

    const files = document.querySelectorAll(".harbor-file-row.kind-file");
    files[0].click();
    files[1].click();
    pending.get("second.md")("Second");
    await tick();
    pending.get("first.md")("First");
    await tick();

    assert.equal(harbor.workbenchState.filePath, "second.md");
    assert.equal(document.querySelector("[data-harbor-editor]").value, "Second");
  } finally {
    globalThis.fetch = previousFetch;
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
  harbor.workbenchState.dirty = false;

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
