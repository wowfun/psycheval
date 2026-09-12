import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin","sources":[]}</script>
  <div data-task-browser>
    <div data-harbor-file-tree></div>
    <strong data-harbor-editor-path></strong>
    <span data-harbor-editor-meta></span>
    <button data-harbor-save disabled>Save</button>
    <textarea data-harbor-editor disabled></textarea>
  </div>
`);

const { createTaskBrowser } = await import("../../src/psycheval/assets/web/modules/harbor-task-browser.js");

test.after(() => browser.cleanup());

const tick = () => new Promise(resolve => setTimeout(resolve, 0));

function detail(defaultFilePath = "instruction.md") {
  return {
    dataset_id: "dataset",
    task: { directory: "task" },
    default_file_path: defaultFilePath,
    tree: [
      { path: "instruction.md", kind: "file", size: 4, previewable: true, editable: true },
      { path: "steps/first", kind: "directory", size: null },
      { path: "steps/first/instruction.md", kind: "file", size: 5, previewable: true, editable: true },
    ],
  };
}

test("a Task browser opens the server-selected default and ignores stale file responses", async () => {
  const pending = new Map();
  const taskBrowser = createTaskBrowser({
    root: document.querySelector("[data-task-browser]"),
    editable: true,
    readFile: (_taskRef, path) => new Promise(resolve => pending.set(path, resolve)),
  });

  const loading = taskBrowser.setTaskDetail(detail(), {
    taskRef: { dataset_id: "dataset", task: "task" },
  });
  assert.equal(pending.has("instruction.md"), true);
  pending.get("instruction.md")({ path: "instruction.md", content: "Root", revision: "root-r1" });
  await loading;
  assert.equal(document.querySelector("[data-harbor-editor]").value, "Root");

  const files = document.querySelectorAll(".harbor-file-row.kind-file");
  files[0].click();
  files[1].click();
  pending.get("steps/first/instruction.md")({
    path: "steps/first/instruction.md",
    content: "First",
    revision: "step-r1",
  });
  await tick();
  pending.get("instruction.md")({ path: "instruction.md", content: "Stale", revision: "root-r2" });
  await tick();

  assert.equal(taskBrowser.currentFile().path, "steps/first/instruction.md");
  assert.equal(document.querySelector("[data-harbor-editor]").value, "First");
});

test("same-context Task loads share one request while a new context supersedes the old one", async () => {
  const pending = [];
  let loads = 0;
  const taskBrowser = createTaskBrowser({
    root: document.querySelector("[data-task-browser]"),
    editable: false,
    loadTask: () => new Promise(resolve => {
      loads += 1;
      pending.push(resolve);
    }),
    readFile: async (_taskRef, path) => ({
      path,
      content: path,
      revision: `${path}-r1`,
    }),
  });
  const taskRef = { dataset_id: "dataset", task: "task" };

  const first = taskBrowser.loadTask(taskRef, { contextKey: "same" });
  const second = taskBrowser.loadTask(taskRef, { contextKey: "same" });
  pending.forEach(resolve => resolve(detail()));
  const [firstDetail, secondDetail] = await Promise.all([first, second]);

  assert.equal(loads, 1);
  assert.equal(firstDetail, secondDetail);

  const older = taskBrowser.loadTask(taskRef, { contextKey: "older" });
  const newer = taskBrowser.loadTask(taskRef, { contextKey: "newer" });
  pending[2]?.(detail("steps/first/instruction.md"));
  pending[1]?.(detail());
  await Promise.all([older, newer]);

  assert.equal(loads, 3);
  assert.equal(taskBrowser.state.contextKey, "newer");
  assert.equal(taskBrowser.currentFile().path, "steps/first/instruction.md");
});

test("a synchronously failed Task loader can retry the same context", async () => {
  let attempts = 0;
  const taskBrowser = createTaskBrowser({
    root: document.querySelector("[data-task-browser]"),
    editable: false,
    loadTask: () => {
      attempts += 1;
      throw new Error("Task unavailable");
    },
  });
  const taskRef = { dataset_id: "dataset", task: "task" };

  await taskBrowser.loadTask(taskRef, { contextKey: "retry" });
  await taskBrowser.loadTask(taskRef, { contextKey: "retry" });

  assert.equal(attempts, 2);
});

test("a strict step instruction never falls back and read-only mode exposes no editing", async () => {
  let reads = 0;
  const taskBrowser = createTaskBrowser({
    root: document.querySelector("[data-task-browser]"),
    editable: false,
    readFile: async () => {
      reads += 1;
      return {};
    },
  });

  await taskBrowser.setTaskDetail(detail(), {
    taskRef: { dataset_id: "dataset", task: "task" },
    preferredPath: "steps/missing/instruction.md",
    strictPreferred: true,
  });

  assert.equal(reads, 0);
  assert.match(document.querySelector("[data-harbor-editor-path]").textContent, /steps\/missing\/instruction\.md/);
  assert.match(document.querySelector("[data-harbor-editor]").value, /unavailable/i);
  assert.equal(document.querySelector("[data-harbor-editor]").readOnly, true);
});

test("previewable read-only files load while metadata-only files never request content", async () => {
  const root = document.createElement("div");
  root.innerHTML = `
    <span data-harbor-editor-meta></span>
    <button data-harbor-save disabled>Save</button>
    <textarea data-harbor-editor></textarea>
  `;
  const reads = [];
  const taskBrowser = createTaskBrowser({
    root,
    editable: true,
    readFile: async (_taskRef, path) => {
      reads.push(path);
      return { path, content: "Read only", revision: "r1" };
    },
  });
  const taskDetail = detail();
  taskDetail.tree = [
    { path: "instruction.md", kind: "file", size: 9, previewable: true, editable: false },
    { path: "archive.tar.gz", kind: "file", size: 20, previewable: false, editable: false },
    { path: "large.txt", kind: "file", size: 3 * 1024 * 1024, previewable: false, editable: false },
  ];
  await taskBrowser.setTaskDetail(taskDetail);
  const editor = root.querySelector("[data-harbor-editor]");
  assert.equal(editor.value, "Read only");
  assert.equal(editor.readOnly, true);
  assert.match(root.querySelector("[data-harbor-editor-meta]").textContent, /text/);
  editor.dispatchEvent(new window.Event("input", { bubbles: true }));
  assert.equal(taskBrowser.isDirty(), false);
  assert.equal(root.querySelector("[data-harbor-save]").disabled, true);

  for (const path of ["archive.tar.gz", "large.txt"]) {
    await taskBrowser.openPath(path);
    assert.equal(editor.value, "metadata only");
    assert.equal(editor.readOnly, true);
  }
  assert.deepEqual(reads, ["instruction.md"]);
});

test("capability re-renders preserve an unsaved editor value", async () => {
  const root = document.createElement("div");
  root.innerHTML = `
    <div data-harbor-file-tree></div>
    <strong data-harbor-editor-path></strong>
    <span data-harbor-editor-meta></span>
    <button data-harbor-save disabled>Save</button>
    <textarea data-harbor-editor disabled></textarea>
  `;
  document.body.append(root);
  const taskBrowser = createTaskBrowser({
    root,
    editable: true,
    readFile: async (_taskRef, path) => ({
      path,
      content: "Saved",
      revision: "r1",
    }),
  });
  await taskBrowser.setTaskDetail(detail(), {
    taskRef: { dataset_id: "dataset", task: "task" },
  });
  const editor = root.querySelector("[data-harbor-editor]");
  editor.value = "Unsaved";
  editor.dispatchEvent(new window.Event("input", { bubbles: true }));

  taskBrowser.setEditable(true);
  taskBrowser.setContextMenu(null);

  assert.equal(taskBrowser.isDirty(), true);
  assert.equal(editor.value, "Unsaved");
});

test("Task Markdown defaults to rendering and preserves an editable draft across preview and reattachment", async () => {
  const makeRoot = () => {
    const root = document.createElement("div");
    root.innerHTML = '<header class="harbor-editor-head"></header><button data-harbor-save></button><textarea data-harbor-editor></textarea>';
    return root;
  };
  let root = makeRoot();
  const taskBrowser = createTaskBrowser({ root, editable: true, readFile: async () => ({ content: "# Instruction\n\n**Evidence**\n\n<script>unsafe()</script>", revision: "r1" }) });
  await taskBrowser.setTaskDetail(detail());
  assert.equal(root.querySelector("[data-harbor-editor]").hidden, true);
  assert.equal(root.querySelector(".file-markdown h4").textContent, "Instruction");
  assert.equal(root.querySelector(".file-markdown strong").textContent, "Evidence");
  assert.equal(root.querySelector("script"), null);
  root.querySelector("[data-file-preview-toggle]").click();
  const editor = root.querySelector("[data-harbor-editor]");
  assert.equal(editor.hidden, false);
  editor.value = "# Draft\n\nChanged content";
  editor.dispatchEvent(new window.Event("input"));
  root.querySelector("[data-file-preview-toggle]").click();
  assert.equal(root.querySelector(".file-markdown h4").textContent, "Draft");
  assert.equal(taskBrowser.isDirty(), true);
  assert.equal(root.querySelector("[data-harbor-save]").disabled, false);
  root = makeRoot(); taskBrowser.attach(root);
  assert.equal(root.querySelector(".file-markdown h4").textContent, "Draft");
  root.querySelector("[data-file-preview-toggle]").click();
  assert.equal(taskBrowser.currentFile().content, "# Draft\n\nChanged content");
  taskBrowser.acceptSave("instruction.md", taskBrowser.currentFile().content);
  assert.equal(taskBrowser.isDirty(), false);
});
