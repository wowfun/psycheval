import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"guest","sources":[]}</script>
  <section id="leaderboard-region"></section>
  <section id="report-notes"></section>
  <section id="comparison"></section>
  <section id="trace"></section>
  <aside id="detail-sidebar" hidden></aside>
`);

const runtime = await import("../../src/psycheval/assets/web/modules/runtime.js");
const sidebarModule = await import("../../src/psycheval/assets/web/modules/detail-sidebar.js");
const catalog = await import("../../src/psycheval/assets/web/modules/serve-catalog.js");

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
    const payload = String(path) === "/api/harbor/datasets/dataset/tasks/task"
      ? {
          dataset_id: "dataset",
          task: { directory: "task" },
          default_file_path: "instruction.md",
          tree: [
            { path: "instruction.md", kind: "file", size: 4, previewable: true, editable: true },
            { path: "steps/collect/instruction.md", kind: "file", size: 16, previewable: true, editable: true },
          ],
        }
      : { path: "steps/collect/instruction.md", content: "Collect evidence.", revision: "file-r1" };
    return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify(payload) };
  };
  runtime.state.selectedTrial = "trial-one";
  runtime.state.selectedStep = null;
  runtime.state.detailSidebar = { open: true, tab: "task", pendingOpener: null, pendingOpenerSelector: null };
  runtime.state.workspaceViewsLoaded = true;

  runtime.render(harborReport());
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
  assert.equal(
    calls.filter(path => path === "/api/harbor/datasets/dataset/tasks/task").length,
    1,
  );
  assert.equal(
    calls.filter(path => path.endsWith("/files/steps%2Fcollect%2Finstruction.md")).length,
    1,
  );
  assert.equal(steps.querySelectorAll(".step").length, 2);
  assert.equal(task.compareDocumentPosition(steps) & window.Node.DOCUMENT_POSITION_FOLLOWING, window.Node.DOCUMENT_POSITION_FOLLOWING);
  assert.equal(document.querySelector("#trace #step-list"), null);
  globalThis.fetch = previousFetch;
});

test("a WorkBuddy Trial opens its default Task instruction through the shared read-only browser", async () => {
  const previousFetch = globalThis.fetch;
  const calls = [];
  const base = "/api/harbor/datasets/office/tasks/office-task";
  globalThis.fetch = async path => {
    calls.push(String(path));
    assert.ok([base, `${base}/files/instruction.md`].includes(String(path)));
    const payload = String(path) === base
      ? {
          dataset_id: "office",
          format: "workbuddy.v1",
          read_only: true,
          task: { directory: "office-task" },
          default_file_path: "instruction.md",
          tree: [{ path: "instruction.md", kind: "file", size: 17, previewable: true, editable: false }],
        }
      : { path: "instruction.md", content: "Office task text.", revision: "office-r1" };
    return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify(payload) };
  };
  try {
    const report = harborReport();
    report.trajectory_meta[0].task_metadata = {
      status: "resolved",
      name: "workbuddy/office-task",
      task_ref: { dataset_id: "office", task: "office-task" },
    };
    delete report.trajectory_meta[0].harbor_step;
    runtime.state.view = report;
    runtime.state.selectedTrial = "trial-one";
    runtime.state.selectedStep = null;
    runtime.state.detailSidebar.open = true;
    runtime.state.detailSidebar.tab = "task";
    runtime.renderComparisonPanels();
    await new Promise(resolve => setTimeout(resolve, 0));

    const task = document.querySelector("[data-detail-sidebar-task]");
    assert.match(task.textContent, /workbuddy\/office-task/);
    assert.equal(task.querySelectorAll(".harbor-file-row.kind-file").length, 1);
    assert.equal(task.querySelector("[data-harbor-editor]").value, "Office task text.");
    assert.equal(task.querySelector("[data-harbor-editor]").readOnly, true);
    assert.deepEqual(calls, [base, `${base}/files/instruction.md`]);
  } finally {
    globalThis.fetch = previousFetch;
  }
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

test("a Harbor trial with no configured Task keeps Steps and omits the Task browser", async () => {
  let fetched = false;
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    fetched = true;
    throw new Error("must not fetch");
  };
  try {
    const report = harborReport();
    report.trajectory_meta[0].task_metadata = {
      status: "not_configured",
      live: true,
    };
    runtime.state.view = report;
    runtime.state.selectedTrial = "trial-one";
    runtime.state.selectedStep = null;
    runtime.state.detailSidebar.open = true;
    runtime.state.detailSidebar.tab = "task";

    runtime.renderComparisonPanels();
    await new Promise(resolve => setTimeout(resolve, 0));

    const sidebar = document.querySelector("#detail-sidebar");
    assert.equal(sidebar.hidden, false);
    assert.equal(sidebar.querySelector("[data-detail-sidebar-task]"), null);
    assert.equal(sidebar.querySelectorAll("[data-detail-sidebar-steps] .step").length, 2);
    assert.equal(fetched, false);
  } finally {
    globalThis.fetch = previousFetch;
  }
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
    runtime.state.detailSidebar.tab = "task";

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

test("guest verification is independent of Task resolution and child Agent navigation", async () => {
  const previousFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async path => {
    calls.push(String(path));
    assert.match(String(path), /^\/api\/verification-files\/root-source/);
    const value = String(path).endsWith("/reward") ? { content: "0" } : { tree: [
      { id: "reward", path: "verifier/reward.txt", kind: "file", size: 1, preview_kind: "text", previewable: true },
    ] };
    return { ok: true, text: async () => JSON.stringify(value) };
  };
  try {
    sidebarModule.closeDetailSidebar({ render: false, restoreFocus: false });
    runtime.state.detailSidebar = { open: false };
    const report = harborReport();
    const meta = report.trajectory_meta[0];
    meta.score = 0; meta.status = "completed";
    meta.task_metadata = { status: "not_configured" };
    const root = report.trajectory[0];
    root.trajectory_id = "root";
    root.subagent_trajectories = [{ trajectory_id: "child", steps: [], final_metrics: {} }];
    runtime.state.selectedSourceKey = "root-source";
    runtime.state.selectedTrajectory = { trialKey: "trial-one", trajectoryId: "child" };
    sidebarModule.openDetailSidebar({ trialKey: "trial-one" });
    runtime.render(report);
    await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(runtime.state.detailSidebar.tab, "verification");
    const sidebar = document.querySelector("#detail-sidebar");
    assert.equal(sidebar.querySelector('[data-trial-panel="verification"]').hidden, false);
    assert.match(sidebar.querySelector(".verification-summary").textContent, /completed.*Score0/);
    assert.equal(sidebar.querySelector(".verification-metrics dd").textContent, "0");
    assert.deepEqual(calls, ["/api/verification-files/root-source", "/api/verification-files/root-source/reward"]);
    sidebar.querySelector('[data-trial-tab="task"]').click();
    sidebarModule.openDetailSidebar({ trialKey: "trial-two" });
    assert.equal(runtime.state.detailSidebar.tab, "task");
    sidebarModule.openDetailSidebar({ trialKey: "trial-one", stepId: 2 });
    assert.equal(runtime.state.detailSidebar.tab, "trajectory");
    assert.deepEqual(runtime.state.selectedStep, { trialKey: "trial-one", stepId: "2" });
  } finally {
    sidebarModule.closeDetailSidebar({ render: false, restoreFocus: false });
    runtime.state.selectedTrajectory = null;
    globalThis.fetch = previousFetch;
  }
});

test("rapid Trial loads and a cached reselection invalidate older source responses", async () => {
  const previousFetch = globalThis.fetch;
  const pending = new Map();
  globalThis.fetch = path => new Promise(resolve => pending.set(String(path), resolve));
  const complete = (source, name) => {
    const report = harborReport(); report.trajectory_meta[0].trial_key = name;
    pending.get(`/api/sources/${source}`)({ ok: true, text: async () => JSON.stringify({ report }) });
  };
  try {
    runtime.state.detailSidebar.open = false;
    const old = catalog.loadServeSourceReport("older");
    const latest = catalog.loadServeSourceReport("latest");
    complete("latest", "latest-trial"); await latest;
    complete("older", "older-trial"); await old;
    assert.equal(runtime.state.selectedSourceKey, "latest");
    assert.equal(runtime.state.selectedTrial, "latest-trial");
    const pendingOther = catalog.loadServeSourceReport("other");
    await catalog.selectServeDetail("latest");
    complete("other", "other-trial"); await pendingOther;
    assert.equal(runtime.state.selectedSourceKey, "latest");
    assert.equal(runtime.state.selectedTrial, "latest-trial");
  } finally { globalThis.fetch = previousFetch; }
});

test("an unreadable full source keeps the catalog score and retained files accessible", async () => {
  const previousFetch = globalThis.fetch;
  let detailCalls = 0;
  globalThis.fetch = async path => {
    if (String(path).startsWith("/api/sources/")) {
      detailCalls += 1;
      return { ok: false, status: 404, text: async () => JSON.stringify({ detail: "Live Dataset was deleted" }) };
    }
    const payload = String(path).endsWith("/reward") ? { content: "0.676" } : { tree: [
      { id: "reward", path: "verifier/reward.txt", kind: "file", size: 5, preview_kind: "text", previewable: true },
    ] };
    return { ok: true, text: async () => JSON.stringify(payload) };
  };
  try {
    runtime.state.catalogRows = [{ source_key: "retained", trial_key: "retained", artifact_trial_key: "retained-trial", adapter: "harbor", score: 0.676, status: "completed" }];
    runtime.state.detailSidebar.tab = "verification";
    await catalog.selectServeDetail("retained", { openSidebar: true });
    await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(runtime.state.selectedTrial, "retained-trial");
    assert.match(document.querySelector(".verification-summary").textContent, /0.676/);
    assert.equal(document.querySelector(".verification-metrics dd").textContent, "0.676");
    assert.match(document.querySelector('[data-trial-panel="trajectory"]').textContent, /Trajectory unavailable/);
    await catalog.selectServeDetail("retained", { openSidebar: true });
    assert.equal(detailCalls, 2, "unavailable source detail can be retried");
  } finally {
    runtime.state.catalogRows = [];
    sidebarModule.closeDetailSidebar({ render: false, restoreFocus: false });
    globalThis.fetch = previousFetch;
  }
});

test("temporary source errors do not fabricate missing trajectory evidence", async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: false, status: 500, text: async () => JSON.stringify({ detail: "Temporary failure" }) });
  try {
    runtime.state.selectedSourceKey = "prior";
    runtime.state.catalogRows = [{ source_key: "broken", trial_key: "broken", adapter: "harbor", score: 1 }];
    await catalog.selectServeDetail("broken", { openSidebar: true });
    assert.equal(runtime.state.selectedSourceKey, "prior");
    assert.notEqual(runtime.state.selectedTrial, "broken");
  } finally { runtime.state.catalogRows = []; globalThis.fetch = previousFetch; }
});
