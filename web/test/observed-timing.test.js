import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom('<script type="application/json" id="peval-i18n">{}</script>');
const { timelineTrace } = await import("../../src/psycheval/assets/web/modules/timeline-model.js");
const { renderTimelineDiagnostics } = await import("../../src/psycheval/assets/web/modules/timeline-shell.js");
const { timelineChartOption, timelineTooltipHtml } = await import("../../src/psycheval/assets/web/modules/timeline-chart.js");
const { renderTimelineDetailTable } = await import("../../src/psycheval/assets/web/modules/timeline-table.js");
const { renderTrace, renderTrajectoryNode, trajectoryOverviewTimingModel } = await import("../../src/psycheval/assets/web/modules/trajectory-trace.js");
const { state } = await import("../../src/psycheval/assets/web/modules/runtime.js");
const { catalogStepOutline } = await import("../../src/psycheval/assets/web/modules/serve-catalog.js");
const { renderStep } = await import("../../src/psycheval/assets/web/modules/steps.js");
const { timingSource, timestampFallbackAllowed } = await import("../../src/psycheval/assets/web/modules/timing-source.js");
test.after(() => browser.cleanup());

test("Trial success rate and success/total both preserve unknown or invalid counts", () => {
  const target = document.createElement("section"); target.id = "trace"; document.body.append(target);
  const previous = { view: state.view, selectedTrial: state.selectedTrial };
  try {
    for (const [calls, errors, ratio] of [[4, undefined, "-"], [undefined, 0, "-"], [4, 5, "-"], ["4", 0, "-"], [4, 1, "3/4"], [4, 4, "0/4"]]) {
      state.selectedTrial = "counts";
      state.view = { trajectory: [{ steps: [], final_metrics: { extra: { total_tool_calls: calls, total_tool_errors: errors } } }], trajectory_meta: [{ trial_key: "counts", steps: [] }] };
      renderTrace();
      const items = [...target.querySelectorAll(".info-grid > div")];
      const text = label => items.find(item => item.querySelector("span")?.textContent === label)?.querySelector("strong")?.textContent;
      assert.equal(text("Tool success / total"), ratio);
      if (ratio === "-") assert.equal(text("Tool Success Rate"), "-");
    }
  } finally { Object.assign(state, previous); target.remove(); }
});

test("shared classification keeps estimated badges consistent and never guesses unknown sources", () => {
  assert.equal(timestampFallbackAllowed("EVENT_OBSERVED"), false);
  assert.equal(timestampFallbackAllowed("order_only"), false);
  assert.equal(timestampFallbackAllowed(undefined), true);
  assert.equal(timingSource("acp_client_observed_future").observed, true);
  assert.equal(timingSource("unrecognized_estimate").estimated, undefined);
  assert.equal(timingSource("opencode_model_boundary_estimate").estimated, true);
  assert.equal(timingSource("hermes_message_boundary_estimate").estimated, true);
  for (const source of ["tool_activity_estimate", "step_boundary_estimate"]) {
    const html = renderStep({ step_id: 1, source: "agent", message: "fixture" }, {
      steps: [{ step_id: 1, duration_ms: 0, duration_source: source }],
    }, {});
    assert.match(html, /≈0\.0s/);
    assert.equal(timingSource(source).model_duration, false);
  }
});

const trajectory = { agent: { model_name: "fixture" }, steps: [
  { step_id: 1, source: "user", message: "task" },
  { step_id: 2, source: "agent", message: "answer", tool_calls: [{ tool_call_id: "a", function_name: "Read" }] },
  { step_id: 3, source: "agent", message: "done" },
] };

test("waterfall and detail table stage names are independent of timing source", () => {
  const labels = ["Model: fixture", "Tool call: Read"];
  for (const [modelSource, toolSource] of [
    ["acp_client_observed_output", "acp_client_observed_lifecycle"],
    ["acp_client_observed_output", "acp_client_observed_in_progress"],
    ["acp_client_observed_future", "acp_client_observed_future"],
    ["opencode_native_model_call", "opencode_native_tool_call"],
    [undefined, undefined],
  ]) {
    const trace = timelineTrace(trajectory, { timestamp_semantics: "event_observed", steps: [
      { step_id: 2, timestamp_ms: 1000, duration_ms: 100, duration_source: modelSource, tool_calls: [
        { tool_call_id: "a", timestamp_ms: 1100, execution_duration_ms: 300, execution_duration_source: toolSource },
      ] },
    ] });
    assert.deepEqual(trace.stages.map(stage => stage.stage), labels);
    assert.deepEqual(timelineChartOption(trace).yAxis.data, ["#2.1 Model: fixture", "#2.2 Tool call: Read"]);
    const table = document.createElement("div");
    table.innerHTML = renderTimelineDetailTable(trace.stages, trace.model);
    assert.deepEqual([...table.querySelectorAll(".timeline-stage-label")].map(node => node.textContent), labels);
    assert.deepEqual([...table.querySelectorAll(".timeline-stage-label")].map(node => node.title), trace.stages.map(stage => stage.timing_hint || stage.stage));
  }
});

test("observed timing keeps zero, distinguishes unknown, and does not infer model intervals", () => {
  const meta = { timestamp_semantics: "event_observed", started_at_ms: 1000, steps: [
    { step_id: 1, timestamp_ms: 1000 },
    { step_id: 2, timestamp_ms: 1100, duration_ms: 0, duration_source: "acp_client_observed_output", tool_calls: [
      { tool_call_id: "a", timestamp_ms: 1200, execution_duration_ms: 300, execution_duration_source: "acp_client_observed_lifecycle" },
    ] }, { step_id: 3, timestamp_ms: 1600 },
  ] };
  const trace = timelineTrace(trajectory, meta);
  assert.equal(trace.stages.length, 2);
  assert.equal(trace.stages[0].duration_ms, 0);
  assert.equal(trace.model.active_total_ms, 300);
  assert.equal(trace.partial, true);
  assert.equal(trace.stages[0].stage, "Model: fixture");
  assert.match(timelineTooltipHtml(trace.stages[1]), /may include waiting/);
  const html = renderTimelineDiagnostics(trajectory, meta);
  assert.match(html, /Partial coverage/);
  assert.match(html, /≈0\.000s/);
  assert.match(renderStep(trajectory.steps[1], meta, {}), /Observed output|may include waiting/);
  const unknown = renderTimelineDiagnostics(trajectory, { timestamp_semantics: "event_observed", steps: meta.steps.map(step => ({ step_id: step.step_id, timestamp_ms: step.timestamp_ms })) });
  assert.match(unknown, /timeline-total">Cumulative active duration: —/);
  assert.match(unknown, /No timed step/);
  assert.doesNotMatch(unknown, /0\.000s/);
});

test("catalog node shading uses varied durations and retains observed or estimated hints", () => {
  const steps = catalogStepOutline([
    { step_id: 1, source: "agent", duration_ms: 10, duration_source: "tool_activity_estimate" },
    { step_id: 2, source: "agent", duration_ms: 100, duration_source: "acp_client_observed_output" },
    { step_id: 3, source: "agent" },
  ]);
  const model = trajectoryOverviewTimingModel(steps);
  const nodes = steps.map((step, index) => renderTrajectoryNode(step, index, "fixture", model));
  assert.match(nodes[0], /duration-heat-1\b/);
  assert.match(nodes[0], /Estimated from tools/);
  assert.match(nodes[1], /duration-heat-10\b/);
  assert.match(nodes[1], /Observed output/);
  assert.doesNotMatch(nodes[2], /duration-heat-/);
});

test("native OpenCode model and tool calls retain independent boundaries and source hints", () => {
  const meta = { timestamp_semantics: "event_observed", started_at_ms: 1000, steps: [
    { step_id: 1, timestamp_ms: 1000 },
    { step_id: 2, timestamp_ms: 1100, duration_ms: 150, duration_source: "opencode_native_model_call", tool_calls: [
      { tool_call_id: "a", timestamp_ms: 1200, execution_duration_ms: 400, execution_duration_source: "opencode_native_tool_call" },
    ] }, { step_id: 3, timestamp_ms: 1700 },
  ] };
  const trace = timelineTrace(trajectory, meta);
  assert.deepEqual(trace.stages.map(stage => stage.duration_ms), [150, 400]);
  assert.ok(trace.stages.every(stage => !stage.estimated));
  assert.match(timelineTooltipHtml(trace.stages[0]), /response-body end/);
  assert.match(timelineTooltipHtml(trace.stages[1]), /tool-called to terminal/);
  assert.match(renderStep(trajectory.steps[1], meta, {}), /Model call|response-body end/);
  assert.equal(trace.partial, true);
});
