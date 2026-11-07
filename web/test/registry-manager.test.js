import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom, submitActionForm } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin"}</script>
`);
const { createRegistryManager } = await import("../../src/psycheval/assets/web/modules/registry-manager.js");
const tables = await import("../../src/psycheval/assets/web/modules/data-tables.js");
test.after(() => browser.cleanup());
const tick = () => new Promise(resolve => setTimeout(resolve, 0));
async function until(check) {
  for (let attempt = 0; attempt < 100 && !check(); attempt++) await tick();
  assert.ok(check(), "expected the pending registry action to settle");
}
function response(value, status = 200, headers = {}) {
  return new Response(JSON.stringify(value), { status, headers });
}

function fixture(config, write) {
  const root = document.createElement("section");
  root.innerHTML = '<div data-harbor-dataset-registry></div>';
  document.body.append(root);
  const target = root.firstElementChild;
  const previousFetch = globalThis.fetch;
  const value = { config, requests: [], revision: 1, refreshes: 0, configError: null };
  const manager = createRegistryManager({ root, page: "datasets", onRefresh: () => { render(); value.refreshes++; } });
  function render() {
    const columns = manager.datasetColumns();
    const rows = value.config.datasets.map(row => ({ ...row, mount_ids: value.config.mounts.filter(m => m.dataset_ids.includes(row.id)).map(m => m.id) }));
    target.innerHTML = tables.renderDataTable({ tableId: "harbor-dataset-registry", columns, rows, rowKey: row => row.id });
    tables.bindDataTableControls(target, { tableId: "harbor-dataset-registry", columns, rows, rowKey: row => row.id, onChange: render, onSelectionChange: render });
  }
  globalThis.fetch = async (path, options = {}) => {
    const request = { path: String(path), method: options.method || "GET", body: options.body ? JSON.parse(options.body) : null, revision: new Headers(options.headers).get("If-Match") };
    value.requests.push(request);
    if (request.path === "/api/config") return value.configError
      ? response({ detail: value.configError }, 503)
      : response(value.config, 200, { ETag: `"r${value.revision}"` });
    if (request.path.startsWith("/api/operations/")) return response({ state: "succeeded", successes: [{ index: 0 }], failures: [] });
    assert.notEqual(request.method, "GET", `unexpected request: ${request.path}`);
    const result = await write(request, value);
    if (result) return result;
    value.revision++;
    return response({ id: `registry-${value.revision}` }, 202);
  };
  return Object.assign(value, {
    root, manager,
    async load() { await manager.refresh(); render(); },
    mountPanel: () => document.querySelector(".registry-manager-panel"),
    datasetCell: (id, key) => [...target.querySelectorAll("[data-table-column-key]")].find(cell => cell.dataset.tableColumnKey === key && cell.closest("tr").dataset.tableRowKey === id),
    mountCell: (id, key) => [...document.querySelectorAll(".registry-manager-panel [data-table-column-key]")].find(cell => cell.dataset.tableColumnKey === key && cell.closest("tr").dataset.tableRowKey === id),
    close() { manager.destroy(); root.remove(); globalThis.fetch = previousFetch; },
  });
}
function edit(cell, text) {
  cell.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
  const input = cell.querySelector("[data-table-cell-editor] input");
  if (text !== undefined) input.value = text;
  return input;
}
function save(input) { input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true })); }

test("registry registers Dataset and Jobs roots from path-only action forms", async () => {
  const f = fixture({ datasets: [], mounts: [] }, (request, state) => {
    if (request.path === "/api/harbor/datasets") state.config.datasets = [{ id: "tasks", path: request.body.path }];
    else if (request.path === "/api/harbor/mounts") state.config.mounts = [{ id: "jobs", path: request.body.path, dataset_ids: [] }];
    else assert.fail(request.path);
  });
  const previousPrompt = window.prompt;
  window.prompt = () => assert.fail("registration must use the action form");
  try {
    await f.load();
    f.manager.createDataset(true);
    submitActionForm({ path: "/workspace/tasks" });
    await until(() => f.refreshes === 1);
    assert.deepEqual(f.requests.find(r => r.path === "/api/harbor/datasets").body, { source: "existing", path: "/workspace/tasks" });
    assert.equal(f.datasetCell("tasks", "path").dataset.valueType, "path");
    await f.manager.openMounts();
    f.mountPanel().querySelector("[data-harbor-add-mount]").click();
    submitActionForm({ path: "/workspace/jobs" });
    await until(() => f.refreshes === 2);
    await f.manager.openMounts();
    assert.deepEqual(f.requests.find(r => r.path === "/api/harbor/mounts").body, { path: "/workspace/jobs" });
    assert.equal(f.mountPanel().querySelectorAll("tbody tr").length, 1);
    assert.match(f.mountPanel().textContent, /jobs/);
    assert.equal(f.mountPanel().querySelector("form"), null);
  } finally { window.prompt = previousPrompt; f.close(); }
});

test("Dataset rename keeps selection and unregisters the selected registration atomically", async () => {
  const f = fixture({ datasets: [{ id: "tasks", path: "/workspace/tasks" }], mounts: [] }, (request, state) => {
    if (request.method === "PATCH") state.config.datasets[0].id = request.body.new_id;
    else state.config.datasets = [];
  });
  try {
    await f.load();
    f.root.querySelector('[data-table-row-select="tasks"]').click();
    save(edit(f.datasetCell("tasks", "id"), "renamed"));
    await until(() => f.refreshes === 1);
    assert.equal(f.root.querySelector('[data-table-row-select="renamed"]').checked, true);
    await f.manager.removeDatasets();
    await until(() => f.refreshes === 2);
    assert.deepEqual(f.requests.filter(r => r.method !== "GET").map(r => ({ path: r.path, body: r.body })), [
      { path: "/api/harbor/datasets/tasks", body: { new_id: "renamed", path: "/workspace/tasks", mount_ids: [] } },
      { path: "/api/harbor/dataset-unregistration-operations", body: { dataset_ids: ["renamed"] } },
    ]);
    assert.equal(f.root.querySelectorAll("[data-table-row-select]").length, 0);
    assert.equal(f.manager.selectedDatasets.size, 0);
  } finally { f.close(); }
});

test("registry edits reciprocal associations, retains rename focus, and batch removes mounts", async () => {
  const f = fixture({ datasets: [{ id: "tasks", path: "/workspace/tasks" }, { id: "other", path: "/workspace/other" }], mounts: [
    { id: "one", path: "/workspace/jobs-one", dataset_ids: ["other"] },
    { id: "two", path: "/workspace/jobs-two", dataset_ids: ["tasks", "other"] },
  ] }, (request, state) => {
    if (request.path === "/api/harbor/datasets/tasks") state.config.mounts[0].dataset_ids = ["other", "tasks"];
    else if (request.method === "PATCH") {
      const row = state.config.mounts.find(row => row.id === request.path.split("/").at(-1));
      Object.assign(row, { id: request.body.new_id, path: request.body.path, dataset_ids: request.body.dataset_ids });
    } else state.config.mounts = state.config.mounts.filter(row => !request.body.mount_ids.includes(row.id));
  });
  try {
    await f.load();
    const mountsCell = f.datasetCell("tasks", "mounts");
    const mountsInput = edit(mountsCell);
    assert.deepEqual([...mountsCell.querySelectorAll("[data-table-suggestion]")].map(node => node.textContent), ["one", "two"]);
    mountsCell.querySelector('[data-table-suggestion="one"]').click();
    save(mountsInput);
    await until(() => f.refreshes === 1);
    assert.deepEqual(f.requests.find(r => r.path === "/api/harbor/datasets/tasks").body, { new_id: "tasks", path: "/workspace/tasks", mount_ids: ["two", "one"] });
    await f.manager.openMounts();
    assert.equal(f.mountPanel().querySelectorAll("tbody tr").length, 2);
    const datasetsCell = f.mountCell("one", "datasets");
    const datasetsInput = edit(datasetsCell);
    datasetsCell.querySelector('[data-table-suggestion="other"]').click();
    save(datasetsInput);
    await until(() => f.refreshes === 2);
    f.mountPanel().querySelector('[data-table-row-select="one"]').click();
    save(edit(f.mountCell("one", "id"), "uno"));
    await until(() => f.refreshes === 3);
    assert.equal(document.activeElement, f.mountCell("uno", "id"));
    assert.equal(f.mountPanel().querySelector('[data-table-row-select="uno"]').checked, true);
    save(edit(f.mountCell("uno", "path"), "/workspace/jobs-renamed"));
    await until(() => f.refreshes === 4);
    f.mountPanel().querySelector('[data-table-row-select="two"]').click();
    f.mountPanel().querySelector("[data-harbor-remove-mounts]").click();
    await until(() => f.refreshes === 5);
    assert.deepEqual(f.requests.filter(r => r.path.startsWith("/api/harbor/mount")).map(r => r.body), [
      { new_id: "one", path: "/workspace/jobs-one", dataset_ids: ["tasks"] },
      { new_id: "uno", path: "/workspace/jobs-one", dataset_ids: ["tasks"] },
      { new_id: "uno", path: "/workspace/jobs-renamed", dataset_ids: ["tasks"] },
      { mount_ids: ["uno", "two"] },
    ]);
    assert.equal(f.mountPanel().querySelectorAll("[data-table-row-select]").length, 0);
  } finally { f.close(); }
});

test("mount conflict retains the draft and explicit retry preserves the latest unrelated fields", async () => {
  let writes = 0;
  const f = fixture({ datasets: [{ id: "source", path: "/tasks" }], mounts: [{ id: "jobs", path: "/original", dataset_ids: [] }] }, (request, state) => {
    if (++writes === 1) {
      state.config.mounts[0] = { id: "jobs", path: "/concurrent", dataset_ids: ["source"] };
      state.revision++;
      return response({ detail: "Changed elsewhere" }, 412, { "Content-Type": "application/problem+json" });
    }
    state.config.mounts[0] = { id: "jobs", path: request.body.path, dataset_ids: request.body.dataset_ids };
  });
  try {
    await f.manager.openMounts();
    const cell = f.mountCell("jobs", "path");
    const input = edit(cell, "/my-draft");
    save(input);
    await until(() => !input.disabled);
    assert.equal(input.value, "/my-draft");
    assert.match(cell.querySelector(".table-cell-editor-status").textContent, /Changed elsewhere/);
    const savedContent = cell.querySelector("details")?.textContent || "";
    assert.equal(writes, 1);
    save(input);
    await until(() => f.refreshes === 1);
    const requests = f.requests.filter(r => r.method === "PATCH");
    assert.equal(requests[1].revision, '"r2"');
    assert.deepEqual(requests[1].body, { new_id: "jobs", path: "/my-draft", dataset_ids: ["source"] });
    assert.match(savedContent, /concurrent/);
  } finally { f.close(); }
});

for (const kind of ["dataset", "mount"]) test(`${kind} conflict cancellation restores saved content and focus without another write`, async () => {
  const f = fixture({ datasets: [{ id: "source", path: "/original" }], mounts: [{ id: "jobs", path: "/original", dataset_ids: [] }] }, (_request, state) => {
    state.config[kind === "dataset" ? "datasets" : "mounts"][0].path = "/concurrent";
    state.revision++;
    return response({ detail: "Changed elsewhere" }, 412);
  });
  try {
    await f.load();
    if (kind === "mount") await f.manager.openMounts();
    const cell = () => kind === "dataset" ? f.datasetCell("source", "path") : f.mountCell("jobs", "path");
    const input = edit(cell(), "/my-draft");
    save(input);
    await until(() => !input.disabled);
    assert.equal(input.value, "/my-draft");
    input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await until(() => f.refreshes === 1 && document.activeElement === cell());
    assert.equal(cell().textContent, "/concurrent");
    assert.equal(f.requests.filter(r => r.method === "PATCH").length, 1);
  } finally { f.close(); }
});

test("a failed conflict refresh keeps the original error and editable draft", async () => {
  const f = fixture({ datasets: [], mounts: [{ id: "jobs", path: "/original", dataset_ids: [] }] }, (_request, state) => {
    state.configError = "Configuration temporarily unavailable";
    return response({ detail: "Changed elsewhere" }, 412);
  });
  try {
    await f.manager.openMounts();
    const cell = f.mountCell("jobs", "path");
    const input = edit(cell, "/my-draft");
    save(input);
    await until(() => !input.disabled);
    assert.equal(input.value, "/my-draft");
    assert.match(cell.querySelector(".table-cell-editor-status").textContent, /Changed elsewhere.*Configuration temporarily unavailable/);
    assert.equal(f.requests.filter(r => r.method === "PATCH").length, 1);
  } finally { f.close(); }
});
