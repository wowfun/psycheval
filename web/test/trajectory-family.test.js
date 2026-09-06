import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"guest","sources":[]}</script>
  <section id="leaderboard-region"></section><section id="report-notes"></section>
  <section id="comparison"></section><section id="trace"></section><aside id="detail-sidebar" hidden></aside>
`);
const runtime = await import("../../src/psycheval/assets/web/modules/runtime.js");
const family = await import("../../src/psycheval/assets/web/modules/trajectory-family.js");
const catalog = await import("../../src/psycheval/assets/web/modules/serve-catalog.js");
test.after(() => browser.cleanup());

test("empty initial detail has no child selection", () => {
  runtime.state.selectedTrajectory = null;
  assert.equal(family.selectedTrajectoryDetail(null, null).trajectory, null);
  assert.equal(family.renderTrajectoryNavigation(null, null), "");
  assert.equal(family.renderTrajectoryNavigation({ trajectory_id: "only", steps: [] }, {}), "");
});

test("child selection changes detail evidence and metrics without changing root metrics", () => {
  const child = { trajectory_id: "child", agent: { name: "child-agent" }, steps: [{ step_id: 1, source: "agent", message: "Child answer" }], final_metrics: { total_prompt_tokens: 7 } };
  const root = { trajectory_id: "root", agent: { name: "root-agent" }, steps: [{ step_id: 1, source: "user", message: "Root prompt" }], final_metrics: { total_prompt_tokens: 101 }, subagent_trajectories: [child] };
  const meta = { trial_key: "trial", status: "passed", steps: [{ step_id: 1 }], subagent_meta: { child: { steps: [{ step_id: 1 }], total_events: 3, duration_ms: 41 } } };
  runtime.state.selectedTrial = "trial";
  runtime.state.selectedSourceKey = null;
  runtime.state.selectedTrajectory = { trialKey: "trial", trajectoryId: "child" };
  runtime.state.detailSidebar.open = true;
  runtime.render({ trajectory: [root], trajectory_meta: [meta], annotations: {} });
  assert.equal(family.selectedTrajectoryDetail(root, meta).trajectory, child);
  assert.equal(catalog.trajectoryFor("trial").final_metrics.total_prompt_tokens, 101);
  assert.match(document.querySelector("#trace").textContent, /child-agent/);
  assert.match(document.querySelector("#detail-sidebar").textContent, /Child answer/);
  assert.doesNotMatch(document.querySelector("#detail-sidebar").textContent, /Root prompt/);
  const rootNode = document.querySelector('#trace [data-trajectory-node][data-trajectory-id="root"]');
  assert.match(rootNode.textContent, /Main session/);
  assert.equal(document.querySelector('#trace .trajectory-tree > li > ul [data-trajectory-id="child"]').getAttribute("aria-current"), "true");
  rootNode.click();
  assert.match(document.querySelector("#detail-sidebar").textContent, /Root prompt/);
  assert.equal(document.activeElement.dataset.trajectoryId, "root");
  assert.equal(runtime.state.selectedStep, null);
  runtime.state.selectedTrajectory = { trialKey: "trial", trajectoryId: "removed-child" };
  assert.equal(family.selectedTrajectoryDetail(root, meta).trajectory, root);
});

test("trajectory tree nests grandchildren under their direct parent and escapes labels", () => {
  const grandchild = { trajectory_id: "grandchild", extra: { claude: { agent_id: "<script>grandchild</script>" } } };
  const child = { trajectory_id: "child", subagent_trajectories: [grandchild] };
  const root = { trajectory_id: "root", subagent_trajectories: [child, { trajectory_id: "sibling" }] };
  const target = document.createElement("div");
  target.innerHTML = family.renderTrajectoryNavigation(root, { trial_key: "other-trial" });
  assert.equal(target.querySelectorAll("[data-trajectory-node]").length, 4);
  assert.equal(target.querySelectorAll("script").length, 0);
  assert.match(target.querySelector('.trajectory-tree > li > ul > li > ul [data-trajectory-id="grandchild"]').textContent, /<script>grandchild<\/script>/);
  assert.equal(target.querySelector('[aria-current="true"]').dataset.trajectoryId, "root");
});

test("each row copies its own last Agent message without changing selection", async () => {
  const originalClipboard = Object.getOwnPropertyDescriptor(navigator, "clipboard");
  const copied = [];
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async text => copied.push(text) } });
  const grandchild = { trajectory_id: "grand", steps: [{ source: "agent", message: "Grandchild answer" }] };
  const child = { trajectory_id: "child", steps: [
    { source: "agent", message: "Earlier answer" },
    { source: "agent", message: [{ type: "text", text: "Child **answer**" }, { type: "image", source: { path: "private.png" } }, { type: "text", text: "Second block" }], reasoning_content: "Private reasoning", observation: { results: [{ content: "Tool output" }] } },
    { source: "user", message: "Later user message" },
  ], subagent_trajectories: [grandchild] };
  const root = { trajectory_id: "root", steps: [{ source: "agent", message: "  Root <answer>\n```text\nverbatim\n```\n" }], subagent_trajectories: [child] };
  const target = document.createElement("div");
  const meta = { trial_key: "copy-trial" };
  target.innerHTML = family.renderTrajectoryNavigation(root, meta);
  family.bindTrajectoryNavigation(target, root, meta);
  const selection = { trialKey: "unrelated-trial", trajectoryId: "unchanged" };
  runtime.state.selectedTrajectory = selection;
  try {
    for (const id of ["root", "child", "grand"]) {
      const button = target.querySelector(`[data-trajectory-copy="${id}"]`);
      button.click();
      button.click();
      await new Promise(resolve => setImmediate(resolve));
      assert.equal(button.textContent, "Copied");
      assert.equal(button.disabled, false);
      assert.equal(button.hasAttribute("aria-busy"), false);
      assert.equal(runtime.state.selectedTrajectory, selection);
    }
    assert.deepEqual(copied, ["  Root <answer>\n```text\nverbatim\n```\n", "Child **answer**\nSecond block", "Grandchild answer"]);
  } finally {
    if (originalClipboard) Object.defineProperty(navigator, "clipboard", originalClipboard);
    else delete navigator.clipboard;
  }
});

test("copy is disabled for a missing or empty final Agent message", () => {
  for (const steps of [[], [{ source: "user", message: "User only" }], [
    { source: "agent", message: "Earlier answer" },
    { source: "agent", message: " \n", reasoning_content: "Only reasoning" },
  ], [{ source: "agent", message: [{ type: "image", source: { path: "image.png" } }] }]]) {
    const target = document.createElement("div");
    target.innerHTML = family.renderTrajectoryNavigation({ trajectory_id: "root", steps, subagent_trajectories: [{ trajectory_id: "child" }] }, {});
    assert.equal(target.querySelector('[data-trajectory-copy="root"]').disabled, true);
    assert.equal(target.querySelector('[data-trajectory-copy="root"]').title, "No Agent message to copy");
  }
});

test("clipboard failures are visible and can be retried", async () => {
  const originalClipboard = Object.getOwnPropertyDescriptor(navigator, "clipboard");
  let reject = true;
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async () => {
    if (reject) throw new Error("Permission denied");
  } } });
  const root = { trajectory_id: "root", steps: [{ source: "agent", message: "Answer" }], subagent_trajectories: [{ trajectory_id: "child" }] };
  const target = document.createElement("div");
  target.innerHTML = family.renderTrajectoryNavigation(root, {});
  family.bindTrajectoryNavigation(target, root, {});
  try {
    const button = target.querySelector('[data-trajectory-copy="root"]');
    button.click();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(button.textContent, "Copy failed");
    assert.equal(button.disabled, false);
    reject = false;
    button.click();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(button.textContent, "Copied");
  } finally {
    if (originalClipboard) Object.defineProperty(navigator, "clipboard", originalClipboard);
    else delete navigator.clipboard;
  }
});

test("copy falls back when Clipboard API is unavailable and restores focus", async () => {
  const originalClipboard = Object.getOwnPropertyDescriptor(navigator, "clipboard");
  const originalCommand = Object.getOwnPropertyDescriptor(document, "execCommand");
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: undefined });
  let copied;
  Object.defineProperty(document, "execCommand", { configurable: true, value: command => {
    assert.equal(command, "copy");
    copied = document.querySelector("textarea").value;
    return true;
  } });
  const root = { trajectory_id: "root", steps: [{ source: "agent", message: "Fallback answer" }], subagent_trajectories: [{ trajectory_id: "child" }] };
  const target = document.createElement("div");
  target.innerHTML = family.renderTrajectoryNavigation(root, {});
  document.body.append(target);
  family.bindTrajectoryNavigation(target, root, {});
  try {
    const button = target.querySelector('[data-trajectory-copy="root"]');
    button.focus();
    button.click();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(copied, "Fallback answer");
    assert.equal(button.textContent, "Copied");
    assert.equal(document.querySelector("textarea"), null);
    assert.equal(document.activeElement, button);
  } finally {
    target.remove();
    if (originalClipboard) Object.defineProperty(navigator, "clipboard", originalClipboard);
    else delete navigator.clipboard;
    if (originalCommand) Object.defineProperty(document, "execCommand", originalCommand);
    else delete document.execCommand;
  }
});
