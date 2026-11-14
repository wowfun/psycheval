// @ts-check

const measured = value => typeof value === "number" && Number.isFinite(value) ? value : null;

function wrappedLines(measureText, text, width) {
  return String(text).split("\n").flatMap(paragraph => {
    const lines = [];
    let line = "";
    for (const character of paragraph) {
      while (line && measureText(line + character) > width) {
        const boundary = line.lastIndexOf(" ");
        const end = boundary < 0 ? line.length : boundary + 1;
        lines.push(line.slice(0, end));
        line = line.slice(end);
      }
      line += character;
    }
    lines.push(line);
    return lines;
  });
}

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
function comparisonGroups(groups, keys) {
  if (keys === null) return groups;
  const selected = new Set(keys);
  return groups.filter(group => selected.has(group.key));
}

// Stable slots in complete-summary order; selection never shifts colors.
const RADAR_COLORS = Object.freeze(["#0072b2", "#c6344f", "#009e73", "#7b3294", "#ad7a00"]);

/** @param {number} count */
function radarColors(count) {
  if (!Number.isInteger(count) || count < 0) throw new RangeError("Radar color count must be a nonnegative integer.");
  return Array.from({ length: count }, (_, index) => RADAR_COLORS[index] || `hsl(${((index - RADAR_COLORS.length) * 137.508 + 23) % 360} 65% 36%)`);
}

export { radarAxes, radarPoints, comparisonGroups, radarColors, relativePosition, wrappedLines };
