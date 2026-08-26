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
      { path: "instruction.md", kind: "file", size: 4, editable: true },
      { path: "steps/first", kind: "directory", size: null },
      { path: "steps/first/instruction.md", kind: "file", size: 5, editable: true },
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
