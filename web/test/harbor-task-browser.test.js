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

test("scoring draft previews preserve source on errors and ignore responses after switching files", async () => {
  const root = document.createElement("div");
  root.innerHTML = '<header class="harbor-editor-head"></header><button data-harbor-save></button><textarea data-harbor-editor></textarea>';
  const parsed = id => ({ kind: "judge", items: [{ id, question: "Safe <script> text" }], config: { artifacts: { report: {} } } });
  const pending = [];
  const taskBrowser = createTaskBrowser({ root, editable: true,
    readFile: async (_ref, path) => ({ content: path.endsWith("yaml") ? "saved source" : "# Instruction", preview: path.endsWith("yaml") ? parsed("saved") : null }),
    previewFile: (_ref, path, content) => new Promise(resolve => pending.push({ path, content, resolve })),
  });
  const taskDetail = detail("tests/judge.yaml");
  taskDetail.tree.push({ path: "tests/judge.yaml", kind: "file", previewable: true, editable: true });
  await taskBrowser.setTaskDetail(taskDetail, { taskRef: { dataset_id: "dataset", task: "task" } });
  assert.equal(root.querySelector(".task-scoring-preview h3").textContent, "saved");
  assert.equal(root.querySelector("script"), null);
  const toggle = root.querySelector("[data-file-preview-toggle]"), editor = root.querySelector("[data-harbor-editor]");
  toggle.click(); editor.value = "draft source"; editor.dispatchEvent(new window.Event("input")); toggle.click();
  assert.equal(pending[0].content, "draft source");
  pending[0].resolve({ preview: null, preview_error: "Invalid YAML" }); await tick();
  assert.equal(editor.hidden, false); assert.equal(editor.value, "draft source"); assert.equal(taskBrowser.isDirty(), true);
  assert.equal(root.querySelector("[data-task-preview-error]").textContent, "Invalid YAML");
  editor.value = "valid draft"; editor.dispatchEvent(new window.Event("input")); toggle.click();
  pending[1].resolve({ preview: parsed("draft"), preview_error: null }); await tick();
  assert.equal(root.querySelector(".task-scoring-preview h3").textContent, "draft");
  assert.equal(taskBrowser.isDirty(), true);
  toggle.click(); editor.value = "later"; editor.dispatchEvent(new window.Event("input")); toggle.click();
  await taskBrowser.openPath("instruction.md");
  pending[2].resolve({ preview: parsed("stale") }); await tick();
  assert.equal(taskBrowser.currentFile().path, "instruction.md");
  assert.equal(root.querySelector(".task-scoring-preview"), null);
});

test("localhost Task browser reveals previewable and metadata-only files, hides in resources/remote mode, and reports errors", async () => {
  const revealed = [];
  let fail = false;
  const root = document.createElement("div");
  root.innerHTML = `
    <div data-harbor-file-tree></div>
    <header class="harbor-editor-head"><div><strong data-harbor-editor-path></strong><span data-harbor-editor-meta></span></div></header>
    <textarea data-harbor-editor readonly></textarea>
  `;
  const taskBrowser = createTaskBrowser({
    root,
    editable: false,
    canReveal: () => true,
    readFile: async (_ref, path) => ({ path, content: "# Hello", revision: "r1" }),
    revealFile: async (ref, path) => {
      revealed.push({ ref, path });
      if (fail) throw new Error("file manager unavailable");
      return { revealed: true };
    },
  });
  const taskDetail = detail();
  taskDetail.tree.push({ path: "environment/data/raw.bin", kind: "file", size: 8, previewable: false, editable: false });
  await taskBrowser.setTaskDetail(taskDetail, { taskRef: { dataset_id: "ds", task: "t1" } });

  const revealBtn = root.querySelector(".harbor-editor-actions [data-file-reveal]");
  assert.ok(revealBtn);
  assert.equal(revealBtn.hidden, false);
  revealBtn.click(); await tick();
  assert.deepEqual(revealed.at(-1), { ref: { dataset_id: "ds", task: "t1" }, path: "instruction.md" });

  await taskBrowser.openPath("environment/data/raw.bin");
  assert.equal(revealBtn.hidden, false);
  fail = true;
  revealBtn.click(); await tick();
  assert.deepEqual(revealed.at(-1), { ref: { dataset_id: "ds", task: "t1" }, path: "environment/data/raw.bin" });
  assert.match(root.querySelector("[data-task-reveal-error]").textContent, /file manager unavailable/);

  taskBrowser.showResources("files");
  assert.equal(revealBtn.hidden, true);
  assert.equal(root.querySelector("[data-task-reveal-error]").hidden, true);

  const remoteRoot = document.createElement("div");
  remoteRoot.innerHTML = '<header class="harbor-editor-head"><div><strong data-harbor-editor-path></strong></div></header><textarea data-harbor-editor readonly></textarea>';
  const remoteBrowser = createTaskBrowser({
    root: remoteRoot,
    editable: false,
    canReveal: () => false,
    readFile: async () => ({ path: "instruction.md", content: "hi" }),
  });
  await remoteBrowser.setTaskDetail(detail(), { taskRef: { dataset_id: "ds", task: "t1" } });
  assert.equal(remoteRoot.querySelector("[data-file-reveal]"), null);
});

test("scoring preview renders inline per-item comment threads, step selector, focus highlight, and CRUD sync", async () => {
  const previousFetch = globalThis.fetch;
  const calls = [];
  const root = document.createElement("div");
  root.innerHTML = '<header class="harbor-editor-head"></header><button data-harbor-save></button><textarea data-harbor-editor></textarea>';
  document.body.append(root);
  const itemKey = JSON.stringify(["", "rubric", "fidelity"]);
  const stepOneKey = JSON.stringify(["one", "rubric", "fidelity"]);
  const synced = [];
  let store = {
    [itemKey]: [
      { id: "c1", body: "Initial check", author_id: "alice", updated_at_ms: 1000, revision: "r1" },
    ],
  };
  globalThis.fetch = async (url, options = {}) => {
    const path = String(url);
    const method = options.method || "GET";
    const body = options.body ? JSON.parse(String(options.body)) : null;
    calls.push({ path, method, body });
    if (method === "POST" && path.endsWith("/scoring-comments")) {
      const created = { id: "c2", body: body.body, author_id: "admin", updated_at_ms: 2000, revision: "r2" };
      store[body.item_key] = [...(store[body.item_key] || []), created];
      return { ok: true, status: 201, statusText: "Created", text: async () => JSON.stringify({ item_key: body.item_key, comment: created, comments: store[body.item_key] }) };
    }
    throw new Error(`unexpected fetch: ${method} ${path}`);
  };
  try {
    const taskBrowser = createTaskBrowser({
      root,
      editable: false,
      readFile: async () => ({
        content: "saved yaml",
        preview: { kind: "judge", items: [{ id: "fidelity", question: "Matches evidence?" }], config: {} },
      }),
      onScoringCommentsChange: (taskRef, key, comments) => synced.push({ taskRef, key, comments }),
    });
    const taskDetail = {
      dataset_id: "office",
      task: {
        directory: "office-one",
        scoring_items: [
          { key: itemKey, step: "", type: "rubric", id: "fidelity", path: "tests/judge.yaml" },
          { key: stepOneKey, step: "one", type: "rubric", id: "fidelity", path: "tests/judge.yaml" },
        ],
        scoring_comments: store,
      },
      default_file_path: "tests/judge.yaml",
      tree: [{ path: "tests/judge.yaml", kind: "file", previewable: true, editable: false }],
    };
    await taskBrowser.setTaskDetail(taskDetail, {
      taskRef: { dataset_id: "office", task: "office-one" },
      focusItemKey: itemKey,
    });
    const focused = root.querySelector(".task-scoring-preview-item.is-focused");
    assert.ok(focused);
    assert.match(focused.textContent, /Initial check/);
    const stepSelect = root.querySelector("[data-scoring-comment-step]");
    assert.ok(stepSelect);

    assert.equal(focused.querySelector("[data-comment-composer]"), null);
    focused.querySelector("[data-comment-composer-open]").click();
    const textarea = focused.querySelector("[data-comment-composer] textarea");
    textarea.value = "Inline follow-up";
    textarea.dispatchEvent(new window.Event("input", { bubbles: true }));
    focused.querySelector("[data-comment-composer]").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
    await tick();
    await tick();

    assert.equal(calls.length, 1);
    assert.equal(calls[0].body.item_key, itemKey);
    assert.equal(calls[0].body.body, "Inline follow-up");
    assert.equal(synced.length, 1);
    assert.equal(synced[0].comments.length, 2);

    // Syncing external updates from the flattened table modal updates the inline thread.
    taskBrowser.syncScoringComments({ dataset_id: "office", task: "office-one" }, itemKey, [
      ...store[itemKey],
      { id: "c3", body: "From modal", author_id: "alice", updated_at_ms: 3000, revision: "r3" },
    ]);
    assert.match(root.querySelector(".task-scoring-preview-item").textContent, /From modal/);
  } finally {
    globalThis.fetch = previousFetch;
    root.remove();
  }
});
