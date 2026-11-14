import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";
const browser = installBrowserDom('<script type="application/json" id="peval-i18n">{}</script><script type="application/json" id="peval-render-options">{"mode":"serve","role":"guest"}</script>');
const { renderTrialInfo } = await import("../../src/psycheval/assets/web/modules/analysis-selected.js");
const { state } = await import("../../src/psycheval/assets/web/modules/runtime.js");
test.after(() => browser.cleanup());

test("Info omits empty fields and groups while retaining measured zero", () => {
  state.view = { annotations:{} };
  assert.equal(renderTrialInfo(null, { harbor_provenance:{ regrade:{}, task_version:"  " } }), "");
  const target = document.createElement("div");
  target.innerHTML = renderTrialInfo({ final_metrics:{ total_prompt_tokens:0, extra:{ accounting:{ pricing_source:"" } } } }, { trial_key:"root" });
  assert.deepEqual([...target.querySelectorAll("dt")].map(node => node.textContent), ["Input"]);
  assert.equal(target.querySelector("dd").textContent, "0");
  assert.equal(target.querySelector(".selected-notes"), null);
});

test("child usage follows its session while provenance, notes and structured findings stay with the Trial", () => {
  state.view = { annotations:{ notes:[{trial_key:"root", markdown:"Root note"}], analysis:[{
    trial_key:"root", findings:["Recorded finding"], md_report:"Duplicated Markdown report",
    analysis_metrics:{auto:{tooling:{distinct_tools:4,tool_success_rate:1},cost:{cost_per_1k_tokens:0},latency:{step_duration_ms:{p50:100}}}},
  }] } };
  const meta = {trial_key:"root", status:"passed", score:1, data_ref:{relative_path:"source<path>"}, harbor_provenance:{task_version:"v3"}, task_metadata:{description:"Live metadata"}};
  const root = renderTrialInfo({final_metrics:{total_prompt_tokens:101}}, meta);
  const target = document.createElement("div");
  target.innerHTML = root;
  const usage = target.querySelector(".trial-info-section");
  assert.match(usage.textContent, /Usage breakdown.*Distinct tools.*4.*Cost \/ 1k tokens.*0/s);
  assert.equal(target.querySelectorAll(":scope > .info-grid").length, 0);
  assert.match(root, /Distinct tools|Unit/);
  assert.match(root, /Cost \/ 1k tokens/);
  assert.doesNotMatch(root, /Tool success rate|Duplicated Markdown report|Step duration|Live metadata/);
  const child = renderTrialInfo({final_metrics:{total_prompt_tokens:7}}, meta, 1);
  assert.match(child, />7<|Root note|Recorded finding/);
  assert.match(child, /Root note/);
  assert.match(child, /Recorded finding/);
  assert.match(child, /source&lt;path&gt;/);
  assert.match(child, /v3/);
  assert.doesNotMatch(child, /101|Distinct tools|Cost \/ 1k tokens/);
});

test("Info retains native session evidence and recorded variant without duplicating the session tree", () => {
  state.view = { annotations:{} };
  const meta = { trial_key:"root", variant_label:"baseline", total_events:12 };
  const target = document.createElement("div");
  target.innerHTML = renderTrialInfo({session_id:"native-root", trajectory_id:"root", steps:[]}, meta);
  assert.match(target.textContent, /Session.*native-root.*Source events.*12/s);
  assert.match(target.textContent, /Recorded provenance.*Variant.*baseline/s);
  target.innerHTML = renderTrialInfo({session_id:"native-child", trajectory_id:"child", steps:[]}, meta, 1, {total_events:0});
  assert.match(target.textContent, /Session.*native-child.*Source events.*0/s);
  assert.doesNotMatch(target.textContent, /native-root|12/);
  target.innerHTML = renderTrialInfo({session_id:"child", trajectory_id:"child", steps:[]}, meta, 1, {});
  assert.doesNotMatch(target.textContent, /Session|Source events/);
});
