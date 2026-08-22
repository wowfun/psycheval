import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-data">{}</script>
  <script type="application/json" id="peval-token-estimates">{}</script>
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","sources":[]}</script>
  <div class="workspace-main-scroll" data-workspace-main-scroll>
    <section id="leaderboard-region"></section>
    <section id="comparison"></section>
    <section id="trace">
      <details class="step" data-step="1">
        <summary><span>Inline Step</span></summary>
      </details>
    </section>
  </div>
  <aside id="step-drawer"></aside>
`);

const runtime = await import("../src/modules/runtime.js");
const controls = await import("../src/modules/serve-controls.js");

test.after(() => browser.cleanup());

test("opening an inline Step keeps the Step drawer and analysis scroll state", () => {
  runtime.state.view = {
    trajectory: [{
      session_id: "session-one",
      steps: [{ step_id: 1, source: "user", message: "Inspect this step" }],
      final_metrics: {},
    }],
    trajectory_meta: [{
      trial_key: "trial-one",
      status: "passed",
      steps: [{ step_id: 1, tool_calls: [], observations: [] }],
    }],
    annotations: {},
  };
  runtime.state.selectedTrial = "trial-one";
  runtime.state.selectedStep = { trialKey: "trial-one", stepId: "1" };
  document.body.classList.add("step-drawer-open");
  controls.bindGlobalControls();

  const scroller = document.querySelector("[data-workspace-main-scroll]");
  const inlineStep = document.querySelector("#trace .step");
  scroller.scrollTop = 120;
  inlineStep.querySelector("summary").click();

  assert.deepEqual(runtime.state.selectedStep, { trialKey: "trial-one", stepId: "1" });
  assert.equal(inlineStep.isConnected, true);
  assert.equal(inlineStep.open, true);
  assert.equal(document.body.classList.contains("step-drawer-open"), true);
  assert.equal(scroller.scrollTop, 120);
});
