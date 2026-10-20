// @ts-check
import { RADAR_GROUP_LIMIT } from "../app/workspace-view-contract.js";

const RADAR_DIRECTIONS = Object.freeze({
  score: 1, duration_ms: -1, ttft_ms: -1, tps: 1,
  cache_hit_rate: 1, model_duration_ms: -1, tool_success_rate: 1,
});
const measured = value => typeof value === "number" && Number.isFinite(value) ? value : null;

/** @param {any[]} groups @param {string[]} keys @param {(row: any) => any} statistic */
function radarAxes(groups, keys, statistic) {
  return Object.keys(RADAR_DIRECTIONS).filter(key => keys.includes(key)).map(key => {
    const values = groups.flatMap(group => {
      const value = radarValue(group, key, statistic).value;
      return value === null ? [] : [value];
    });
    return { key, direction: RADAR_DIRECTIONS[key], min: values.length ? Math.min(...values) : null, max: values.length ? Math.max(...values) : null };
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
      normalized = axis.max === axis.min ? 50 : 100 * (metric.value - axis.min) / (axis.max - axis.min);
      if (axis.direction < 0) normalized = 100 - normalized;
    }
    return { ...metric, key: axis.key, normalized, coordinate: normalized ?? 0, equal: axis.min !== null && axis.min === axis.max };
  });
}

/** @param {any[]} groups @param {(string | null)[] | null} keys */
function radarSelection(groups, keys) {
  return keys === null ? groups.slice(0, RADAR_GROUP_LIMIT) : groups.filter(group => keys.includes(group.key));
}

/** @param {string | null} key */
function radarHue(key) {
  const identity = JSON.stringify(key);
  let hash = 0;
  for (const char of identity) hash = (Math.imul(hash, 31) + char.charCodeAt(0)) >>> 0;
  hash = Math.imul(hash ^ (hash >>> 16), 0x45d9f3b) >>> 0;
  hash = (hash ^ (hash >>> 16)) >>> 0;
  return hash % 360;
}

/** @param {string | null} key */
function radarColor(key) { return `hsl(${radarHue(key)} 58% 43%)`; }

/** @param {(string | null)[]} keys */
function radarColors(keys) {
  const hues = [];
  return keys.map(key => {
    const preferred = radarHue(key);
    for (let offset = 0; offset < 360; offset += 1) {
      const hue = (preferred + offset) % 360;
      if (hues.every(used => Math.min(Math.abs(used - hue), 360 - Math.abs(used - hue)) >= 40)) {
        hues.push(hue);
        return `hsl(${hue} 58% 43%)`;
      }
    }
    throw new RangeError("Too many radar colors; compare at most five groups.");
  });
}

export { RADAR_DIRECTIONS, radarAxes, radarPoints, radarSelection, radarColor, radarColors };
