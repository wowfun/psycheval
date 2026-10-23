import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { radarAxes, radarPoints, radarSelection, radarColor, relativePosition } from "../../src/psycheval/assets/web/modules/summary-chart.js";
const definitions = JSON.parse(readFileSync(new URL("./support/metrics.json", import.meta.url), "utf8"));
const axesFor = (groups, keys, statistic) => radarAxes(groups, keys.map(key => definitions.find(item => item.key === key)), statistic);
import { encodeWorkspaceLocation, decodeWorkspaceLocation } from "../../src/psycheval/assets/web/app/workspace-location.js";

const group = (key, values) => ({ key, metrics: Object.entries(values).map(([key, value]) => ({ key, count: value === null ? 0 : 1, mean: value })) });

test("finite extreme values do not overflow chart scales", () => {
  assert.equal(relativePosition(0, -1e308, 1e308), 50);
  assert.equal(relativePosition(1e308, -1e308, 1e308), 100);
  assert.equal(relativePosition(-1e308, -1e308, 1e308), 0);
});
const mean = row => row?.mean;

test("radar compares against all query groups and reverses durations, including zero and negative values", () => {
  const groups = [group("a", { score: -2, duration_ms: 0 }), group("b", { score: 0, duration_ms: 10 }), group("c", { score: 6, duration_ms: 20 })];
  const axes = axesFor(groups, ["score", "duration_ms"], mean);
  assert.deepEqual(radarPoints(groups[1], axes, mean).map(point => point.normalized), [25, 50]);
  const selected = radarSelection(groups, ["a", "b"]);
  assert.deepEqual(radarPoints(selected[1], axes, mean).map(point => point.normalized), [25, 50]);
  assert.equal(radarPoints(groups[0], axes, mean)[1].normalized, 100);
});

test("missing values use the origin without becoming measurements; equal values use 50", () => {
  const groups = [group("a", { score: 0, ttft_ms: null }), group("b", { score: 0, ttft_ms: null })];
  const axes = axesFor(groups, ["score", "ttft_ms"], mean);
  const points = radarPoints(groups[0], axes, mean);
  assert.equal(points[0].normalized, 50);
  assert.equal(points[0].equal, true);
  assert.equal(points[1].coordinate, 0);
  assert.equal(points[1].value, null);
  assert.equal(points[1].normalized, null);
  assert.equal(axes[1].min, null);
  const measuredOrigin = radarPoints(group("c", { score: -1 }), axesFor([group("c", { score: -1 }), group("d", { score: 1 })], ["score"], mean), mean)[0];
  assert.equal(measuredOrigin.coordinate, 0);
  assert.equal(measuredOrigin.value, -1);
});

test("automatic selection uses the first five; explicit empty and nullable group keys keep their identity", () => {
  const groups = [group(null, {}), ...Array.from({ length: 6 }, (_, index) => group(String(index), {}))];
  assert.equal(radarSelection(groups, null).length, 5);
  assert.deepEqual(radarSelection(groups, []), []);
  assert.deepEqual(radarSelection(groups, [null]), [groups[0]]);
  assert.notEqual(radarColor(null), radarColor("null"));
  assert.equal(radarColor("a"), radarColor("a"));
});

test("radar configuration shares canonical axes and explicit nullable keys, and rejects invalid selections", () => {
  const summary = { chart_type: "radar", metrics: ["tps", "score", "duration_ms"], radar_groups: ["中文", null, "a"] };
  const href = encodeWorkspaceLocation("home", { state: { summary } });
  const decoded = decodeWorkspaceLocation("home", new URL(href, "http://localhost"));
  assert.deepEqual(decoded.state.summary.metrics, ["tps", "score", "duration_ms"]);
  assert.deepEqual(new Set(decoded.state.summary.radar_groups), new Set(summary.radar_groups));
  assert.equal(encodeWorkspaceLocation("home", decoded), href);
  for (const invalid of [{ chart_type: "wrong" }, { metrics: ["score", "score", "tps"] }, { radar_groups: Array.from({ length: 6 }, (_, index) => String(index)) }, { radar_groups: [false] }]) {
    assert.throws(() => encodeWorkspaceLocation("home", { state: { summary: invalid } }));
  }
  const defaults = decodeWorkspaceLocation("home", new URL("http://localhost"));
  assert.equal(defaults.state.summary.metrics, null);
  assert.doesNotThrow(() => encodeWorkspaceLocation("home", { state: { summary: { metrics: [] } } }));
});
