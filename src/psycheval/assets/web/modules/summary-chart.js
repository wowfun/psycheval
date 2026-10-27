// @ts-check
import { RADAR_GROUP_LIMIT } from "../app/workspace-view-contract.js";

const measured = value => typeof value === "number" && Number.isFinite(value) ? value : null;

function relativePosition(value, minimum, maximum) {
  if (maximum === minimum) return 50;
  const scale = Math.max(Math.abs(minimum), Math.abs(maximum));
  return 100 * ((value / scale - minimum / scale) / (maximum / scale - minimum / scale));
}

/** @param {any[]} groups @param {any[]} definitions @param {(row: any) => any} statistic */
function radarAxes(groups, definitions, statistic) {
  return definitions.filter(item => ["higher", "lower"].includes(item.direction)).map(definition => {
    const key = definition.key;
    const values = groups.flatMap(group => {
      const value = radarValue(group, key, statistic).value;
      return value === null ? [] : [value];
    });
    return { key, direction: definition.direction === "higher" ? 1 : -1, min: values.length ? Math.min(...values) : null, max: values.length ? Math.max(...values) : null };
  });
}

/** @param {any} group @param {string} key @param {(row: any) => any} statistic */
function radarValue(group, key, statistic) {
  const row = group.metrics?.find(item => item.key === key);
  const count = Number(row?.count || 0);
  return { row, count, value: count > 0 ? measured(statistic(row)) : null };
}

/** @param {any} group @param {ReturnType<typeof radarAxes>} axes @param {(row: any) => any} statistic */
function radarPoints(group, axes, statistic) {
  return axes.map(axis => {
    const metric = radarValue(group, axis.key, statistic);
    let normalized = null;
    if (metric.value !== null && axis.min !== null && axis.max !== null) {
      normalized = relativePosition(metric.value, axis.min, axis.max);
      if (axis.direction < 0) normalized = 100 - normalized;
    }
    return { ...metric, key: axis.key, normalized, coordinate: normalized ?? 0, equal: axis.min !== null && axis.min === axis.max };
  });
}

/** @param {any[]} groups @param {(string | null)[] | null} keys */
function radarSelection(groups, keys) {
  return keys === null ? groups.slice(0, RADAR_GROUP_LIMIT) : groups.filter(group => keys.includes(group.key));
}

// Five categorical slots, with dark enough strokes for the workspace's light
// surface and white PNGs. Color is reinforced by the comparison labels/details.
const RADAR_COLORS = Object.freeze(["#0072b2", "#c6344f", "#009e73", "#7b3294", "#ad7a00"]);

/** @param {number} count */
function radarColors(count) {
  if (!Number.isInteger(count) || count < 0 || count > RADAR_GROUP_LIMIT || RADAR_COLORS.length !== RADAR_GROUP_LIMIT) throw new RangeError("Radar colors require an integer count between zero and five.");
  return RADAR_COLORS.slice(0, count);
}

export { radarAxes, radarPoints, radarSelection, radarColors, relativePosition };
