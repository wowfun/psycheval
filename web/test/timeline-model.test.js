import assert from "node:assert/strict";
import test from "node:test";
import { graphic } from "echarts";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom('<script type="application/json" id="peval-i18n">{}</script>');
const { timelineTrace } = await import("../../src/psycheval/assets/web/modules/timeline-model.js");
const { timelineBarRenderItem, timelineChartOption, timelineTooltipHtml } = await import("../../src/psycheval/assets/web/modules/timeline-chart.js");
const { timelineActivePctValue } = await import("../../src/psycheval/assets/web/modules/timeline-table.js");
const { renderTimelineDiagnostics } = await import("../../src/psycheval/assets/web/modules/timeline-shell.js");
test.after(() => browser.cleanup());

function fixture(intervals, markerTimes = []) {
  const tools = intervals.map(([start, duration], index) => ({
    tool_call_id: `call-${index}`,
    timestamp_ms: start,
    execution_duration_ms: duration,
  }));
  return {
    trajectory: { steps: [
      { step_id: 1, source: "agent", tool_calls: tools.map(tool => ({ tool_call_id: tool.tool_call_id, function_name: "web_search" })) },
      ...markerTimes.map((_time, index) => ({ step_id: index + 2, source: "user" })),
    ] },
    meta: { started_at_ms: 0, timestamp_semantics: "event_observed", steps: [
      { step_id: 1, timestamp_ms: 1000, tool_calls: tools },
      ...markerTimes.map((time, index) => ({ step_id: index + 2, timestamp_ms: time })),
    ] },
  };
}

for (const { name, intervals, expected, total } of [
  { name: "simultaneous calls", intervals: [[1000, 1250], [1000, 1067]], expected: [[0, 1250], [0, 1067]], total: 1250 },
  { name: "staggered overlap", intervals: [[1000, 1000], [1500, 1000]], expected: [[0, 1000], [500, 1500]], total: 1500 },
  { name: "transitive overlap", intervals: [[1000, 1000], [1500, 1000], [2400, 600]], expected: [[0, 1000], [500, 1500], [1400, 2000]], total: 2000 },
  { name: "nested intervals", intervals: [[1000, 2000], [1200, 100], [1600, 300]], expected: [[0, 2000], [200, 300], [600, 900]], total: 2000 },
  { name: "adjacent serial calls", intervals: [[1000, 100], [1100, 200]], expected: [[0, 100], [100, 300]], total: 300 },
  { name: "unsorted calls with gaps", intervals: [[3000, 200], [1000, 100], [3050, 100]], expected: [[100, 300], [0, 100], [150, 250]], total: 300 },
]) {
  test(`compressed waterfall preserves ${name} and cumulative shares`, () => {
    const { trajectory, meta } = fixture(intervals);
    const trace = timelineTrace(trajectory, meta);
    const activeTotal = intervals.reduce((sum, [, duration]) => sum + duration, 0);
    assert.equal(trace.model.display_total_ms, total);
    assert.equal(trace.model.active_total_ms, activeTotal);
    intervals.forEach(([start, duration], index) => {
      const stage = trace.stages.find(item => item.tool_call_id === `call-${index}`);
      assert.deepEqual([stage.display_start_ms, stage.display_end_ms], expected[index]);
      assert.equal(stage.display_end_ms - stage.display_start_ms, duration);
      assert.deepEqual([stage.wall_start_ms, stage.wall_end_ms], [start, start + duration]);
      assert.equal(timelineActivePctValue(stage, trace.model), duration / activeTotal * 100);
    });
    const chart = timelineChartOption(trace);
    assert.deepEqual(chart.series[0].data.map(item => item.value.slice(0, 3)), trace.stages.map((stage, index) => [stage.display_start_ms, stage.display_end_ms, index]));
    assert.ok(chart.xAxis.max >= total);
  });
}

test("markers share the interval mapping inside activity, in gaps, and at or beyond endpoints", () => {
  const { trajectory, meta } = fixture([[100, 100], [400, 100]], [0, 100, 150, 200, 250, 400, 450, 500, 600]);
  const trace = timelineTrace(trajectory, meta);
  const offsets = [0, 0, 50, 100, 100, 100, 150, 200, 200];
  assert.deepEqual(trace.markers.map(marker => marker.display_offset_ms), offsets);
  assert.deepEqual(timelineChartOption(trace).series[1].data.map(item => item.value[0]), offsets);
  assert.match(timelineTooltipHtml(trace.markers[2]), /Compressed time offset:<\/span> 0\.050s/);
});

test("zero-duration stages do not bridge gaps or extend the union", () => {
  const intervals = [[100, 100], [400, 100], [50, 0], [150, 0], [300, 0], [600, 0]];
  const { trajectory, meta } = fixture(intervals);
  const trace = timelineTrace(trajectory, meta);
  assert.equal(trace.stages.length, intervals.length);
  assert.equal(trace.model.display_total_ms, 200);
  assert.equal(trace.model.active_total_ms, 200);
  assert.deepEqual(trace.stages.filter(stage => stage.duration_ms === 0).map(stage => [stage.display_start_ms, stage.display_end_ms]), [[0, 0], [50, 50], [100, 100], [200, 200]]);
});

test("zero and unknown durations stay distinct without inventing intervals", () => {
  const { trajectory, meta } = fixture([[100, 0], [200, undefined]], [0, 300]);
  const trace = timelineTrace(trajectory, meta);
  assert.equal(trace.stages.length, 1);
  assert.deepEqual(trace.model, { active_total_ms: 0, display_total_ms: 0 });
  assert.equal(trace.partial, true);
  assert.deepEqual(trace.markers.map(marker => marker.display_offset_ms), [0, 0]);
  assert.ok(timelineChartOption(trace).xAxis.max >= 1);
  assert.equal(timelineActivePctValue(trace.stages[0], trace.model), null);
  meta.steps[0].tool_calls[0].execution_duration_ms = undefined;
  const unknown = timelineTrace(trajectory, meta);
  assert.deepEqual(unknown.model, { active_total_ms: null, display_total_ms: 0 });
  assert.equal(unknown.stages.length, 0);
  assert.deepEqual(unknown.markers.map(marker => marker.display_offset_ms), [0, 0]);
});

test("zero-duration bars remain visible at either edge of the chart", () => {
  const previous = window.echarts;
  window.echarts = { graphic };
  try {
    for (const offset of [0, 100]) {
      const values = [offset, offset, 0, 0, "#0891b2", "0.000s"];
      const item = timelineBarRenderItem({ coordSys: { x: 10, y: 0, width: 100, height: 40 } }, {
        value: index => values[index],
        coord: ([x]) => [x + 10, 20],
        size: () => [0, 30],
        style: style => style,
      });
      const shape = item.children[0].shape;
      assert.equal(shape.width, 2);
      assert.ok(shape.x >= 10 && shape.x + shape.width <= 110);
      assert.equal(item.children[1].style.text, "0.000s");
    }
  } finally { window.echarts = previous; }
});

test("input, model and tool stages share one union while retaining timing hints", () => {
  const { trajectory, meta } = fixture([[1500, 1000]], [1000]);
  meta.steps[0].duration_ms = 1000;
  meta.steps[0].duration_source = "acp_client_observed_output";
  meta.steps[1].duration_ms = 600;
  const trace = timelineTrace(trajectory, meta);
  assert.equal(trace.model.active_total_ms, 2600);
  assert.equal(trace.model.display_total_ms, 1500);
  assert.equal(trace.partial, false);
  const model = trace.stages.find(stage => stage.kind === "agent");
  const input = trace.stages.find(stage => stage.kind === "input");
  const tool = trace.stages.find(stage => stage.kind === "tool");
  assert.deepEqual([model.display_start_ms, input.display_start_ms, tool.display_start_ms], [0, 0, 500]);
  assert.equal(model.estimated, true);
  assert.match(timelineTooltipHtml(model), /≈1\.000s/);
  assert.match(timelineTooltipHtml(model), /Timing source/);
});

test("inherited starts retain parallel placement with explicit cumulative and compressed labels", () => {
  const { trajectory, meta } = fixture([[undefined, 1250], [undefined, 1067]]);
  const trace = timelineTrace(trajectory, meta);
  assert.deepEqual(trace.stages.map(stage => stage.display_start_ms), [0, 0]);
  const html = renderTimelineDiagnostics(trajectory, meta);
  assert.match(html, /Cumulative active duration: 2\.317s/);
  assert.match(html, /Gaps without recorded activity are compressed/);
  assert.match(html, /Partial coverage/);
  const tooltip = timelineTooltipHtml(trace.stages[1]);
  assert.match(tooltip, /Compressed time offset:<\/span> 0\.000s/);
  assert.match(tooltip, /Active Share:<\/span> 46\.1%/);
});
