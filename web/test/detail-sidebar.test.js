import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"guest","sources":[]}</script>
  <section id="leaderboard-region"></section>
  <section id="comparison"></section>
  <section id="trace"></section>
  <aside id="detail-sidebar" hidden></aside>
`);

const runtime = await import("../../src/psycheval/assets/web/modules/runtime.js");
const sidebarModule = await import("../../src/psycheval/assets/web/modules/detail-sidebar.js");

test.after(() => browser.cleanup());

function harborReport() {
  return {
    trajectory: [{
      session_id: "session-one",
      agent: { name: "agent", model_name: "model" },
      steps: [
        { step_id: 1, source: "user", message: "Inspect this step" },
        { step_id: 2, source: "agent", message: "Finished" },
      ],
      final_metrics: {},
    }],
    trajectory_meta: [{
      trial_key: "trial-one",
      adapter: "harbor",
      task_name: "org/task",
      status: "passed",
      steps: [{ step_id: 1 }, { step_id: 2 }],
      task_metadata: {
        status: "resolved",
        name: "org/task",
        description: "Task description",
        task_ref: { dataset_id: "dataset", task: "task" },
      },
      harbor_step: { name: "collect" },
    }],
    annotations: {},
  };
}

test("the selected Harbor trial renders the shared read-only browser at its current step", async () => {
  const previousFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async path => {
    calls.push(String(path));
    const payload = String(path).startsWith("/api/harbor/task?")
      ? {
          dataset_id: "dataset",
          task: { directory: "task" },
          default_file_path: "instruction.md",
          tree: [
            { path: "instruction.md", kind: "file", size: 4, editable: true },
            { path: "steps/collect/instruction.md", kind: "file", size: 16, editable: true },
          ],
        }
      : { path: "steps/collect/instruction.md", content: "Collect evidence.", revision: "file-r1" };
    return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify(payload) };
  };
  runtime.state.view = harborReport();
  runtime.state.selectedTrial = "trial-one";
  runtime.state.selectedStep = null;
  runtime.state.detailSidebar = { open: true, opener: null, preferredWidth: null };

  runtime.renderComparisonPanels();
  await new Promise(resolve => setTimeout(resolve, 0));
  await new Promise(resolve => setTimeout(resolve, 0));

  const sidebar = document.querySelector("#detail-sidebar");
  const task = sidebar.querySelector("[data-detail-sidebar-task]");
  const steps = sidebar.querySelector("[data-detail-sidebar-steps]");
  assert.equal(sidebar.hidden, false);
  assert.match(task.textContent, /org\/task/);
  assert.doesNotMatch(task.textContent, /Task description/);
  assert.equal(task.querySelectorAll(".harbor-file-row.kind-file").length, 2);
  assert.equal(task.querySelector("[data-harbor-editor]").value, "Collect evidence.");
  assert.equal(task.querySelector("[data-harbor-editor]").readOnly, true);
  assert.equal(task.querySelector("[data-harbor-save]"), null);
  assert.ok(calls.some(path => path.includes("path=steps%2Fcollect%2Finstruction.md")));
  assert.equal(steps.querySelectorAll(".step").length, 2);
  assert.equal(task.compareDocumentPosition(steps) & window.Node.DOCUMENT_POSITION_FOLLOWING, window.Node.DOCUMENT_POSITION_FOLLOWING);
  assert.equal(document.querySelector("#trace #step-list"), null);
  globalThis.fetch = previousFetch;
});

test("closing the sidebar preserves the selected Trial and non-Harbor rows show only Steps", () => {
  runtime.state.view = {
    trajectory: [{ session_id: "plain", steps: [], final_metrics: {} }],
    trajectory_meta: [{ trial_key: "plain-trial", adapter: "atif", status: "passed", steps: [] }],
    annotations: {},
  };
  runtime.state.selectedTrial = "plain-trial";
  runtime.state.selectedStep = null;
  runtime.state.detailSidebar.open = true;

  runtime.renderComparisonPanels();

  assert.equal(document.querySelector("#detail-sidebar [data-detail-sidebar-task]"), null);
  assert.match(document.querySelector("#detail-sidebar [data-detail-sidebar-steps]").textContent, /Steps \(0\)/);
  sidebarModule.closeDetailSidebar({ render: false, restoreFocus: false });
  assert.equal(runtime.state.selectedTrial, "plain-trial");
  assert.equal(runtime.state.selectedStep, null);
  assert.equal(runtime.state.detailSidebar.open, false);
});

test("a resolved Harbor identity without a safe Task ref stays unavailable without fetching", async () => {
  let fetched = false;
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    fetched = true;
    throw new Error("must not fetch");
  };
  try {
    const report = harborReport();
    delete report.trajectory_meta[0].task_metadata.task_ref;
    runtime.state.view = report;
    runtime.state.selectedTrial = "trial-one";
    runtime.state.selectedStep = null;
    runtime.state.detailSidebar.open = true;

    runtime.renderComparisonPanels();
    await new Promise(resolve => setTimeout(resolve, 0));

    const task = document.querySelector("[data-detail-sidebar-task]");
    assert.match(task.textContent, /org\/task/);
    assert.match(task.querySelector("[data-harbor-editor]").value, /unavailable/i);
    assert.equal(fetched, false);
  } finally {
    globalThis.fetch = previousFetch;
  }
});
