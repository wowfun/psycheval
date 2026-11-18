import { esc, fmtNum, t } from "./shared.js";
import { radarAxes, radarPoints, comparisonGroups, radarColors, wrappedLines } from "./summary-chart.js";

let chart = null;
let observer = null;
let resizeFrame = null;

function disposeLeaderboardRadar() {
  observer?.disconnect();
  observer = null;
  if (resizeFrame !== null) cancelAnimationFrame(resizeFrame);
  resizeFrame = null;
  chart?.dispose();
  chart = null;
}

function radarContext(groups, definitions, statistic, format, selectedKeys = null) {
  const axes = radarAxes(groups, definitions, statistic.value);
  const selected = comparisonGroups(groups, selectedKeys);
  const radarColorsForGroups = radarColors(groups.length);
  const colors = new Map(groups.map((group, index) => [group.key, radarColorsForGroups[index]]));
  const series = selected.map(group => ({ group, points: radarPoints(group, axes, statistic.value), color: colors.get(group.key) }));
  return { groups, definitions, statistic, format, axes, selected, series };
}

function pointText(point, context) {
  if (point.value === null) return `${t("summary_no_data", "No data")} · n=0`;
  const relative = point.equal ? t("summary_radar_equal", "No group difference") : `${fmtNum(point.normalized)} / 100`;
  return `${context.format(point.row, point.value)} · n=${fmtNum(point.count)} · ${relative}`;
}

function originNote(points) {
  return points.some(point => point.value !== null) && points.every(point => point.coordinate === 0)
    ? t("summary_radar_at_origin", "Measured relative values are all 0; the outline is at the origin.")
    : "";
}

function groupDetails(item, context) {
  const note = originNote(item.points);
  return `<strong>${esc(item.group.label)} · ${esc(context.statistic.label)}</strong>${note ? `<p class="summary-radar-warning">${esc(note)}</p>` : ""}<dl>${item.points.map(point => `<div><dt>${esc(radarMetricLabel(context, point.key))}</dt><dd>${esc(pointText(point, context))}</dd></div>`).join("")}</dl>`;
}

function radarMetricLabel(context, key) {
  const labelFor = id => context.definitions.find(definition => definition.key === id)?.label || id;
  const label = labelFor(key);
  return context.axes.some(axis => axis.key !== key && labelFor(axis.key) === label) ? `${label} (${key})` : label;
}

function renderLeaderboardRadar(context) {
  const { axes, selected, series } = context;
  return `<div class="summary-radar-plot">
    ${selected.length && axes.length >= 3 ? `<div data-summary-radar role="img" aria-label="${esc(t("summary_radar", "Radar chart"))}"></div>` : `<p class="leaderboard-summary-empty">${esc(axes.length < 3 ? t("metric_radar_min", "Select at least three metrics with a direction.") : t("summary_group_select", "Select at least one comparison group."))}</p>`}
    <p data-radar-fallback hidden role="alert">${esc(t("summary_radar_unavailable", "Radar chart is unavailable. Switch to the bar chart or use the summary table."))}</p>
    <div class="summary-radar-legend" aria-label="${esc(t("summary_comparison_groups", "Comparison groups"))}">${series.map((item, index) => `<button type="button" data-radar-legend="${index}" style="--radar-color:${item.color}"><i aria-hidden="true"></i>${esc(item.group.label)}</button>`).join("")}</div>
    <div class="summary-radar-detail" data-radar-detail aria-live="polite">${series.length ? groupDetails(series[0], context) : ""}</div>
  </div>`;
}

function radarOption(context, width, height, palette = null, measureText = null) {
  const { axes, series } = context;
  const root = palette ? null : document.querySelector("[data-summary-radar]");
  const style = root ? window.getComputedStyle(root) : null;
  const ink = palette?.ink || style?.getPropertyValue("--ink").trim() || "#292c36";
  const rule = palette?.rule || style?.getPropertyValue("--rule").trim() || "#dadce2";
  const labelWidth = Math.min(140, width * 0.21);
  const radius = palette?.radius ?? Math.max(1, Math.min(width / 2 - labelWidth - 19, height * 0.29));
  const center = palette?.center || [width / 2, height / 2];
  // Match the pinned ECharts 6.1.0 layout below: centered, 90° start, counterclockwise.
  const markers = series.flatMap((item, seriesIndex) => item.points.map((point, index) => {
    const angle = Math.PI / 2 + index * 2 * Math.PI / axes.length;
    const distance = point.value === null ? 12 + 20 * seriesIndex / Math.max(1, series.length - 1) : radius * point.coordinate / 100;
    const x = center[0] + distance * Math.cos(angle);
    const y = center[1] - distance * Math.sin(angle);
    return point.value === null
      ? { type: "group", x, y, silent: true, children: [{ type: "line", shape: { x1: -4, y1: -4, x2: 4, y2: 4 }, style: { stroke: item.color, lineWidth: 2 } }, { type: "line", shape: { x1: -4, y1: 4, x2: 4, y2: -4 }, style: { stroke: item.color, lineWidth: 2 } }] }
      : { type: "circle", shape: { cx: x, cy: y, r: 3 }, silent: true, style: { fill: item.color, stroke: "#fff", lineWidth: 1 } };
  }));
  return {
    animation: false,
    tooltip: {
      trigger: "item",
      confine: true,
      enterable: true,
      className: "summary-radar-tooltip",
      extraCssText: "white-space:normal;",
      formatter: params => groupDetails(series[params.seriesIndex], context),
    },
    radar: { center, radius, startAngle: 90, splitNumber: 4,
      indicator: axes.map(axis => {
        const label = radarMetricLabel(context, axis.key);
        const lines = measureText ? wrappedLines(measureText, label, labelWidth) : [label];
        return { name: `${lines.join("\n")}\n${axis.direction > 0 ? "↑" : "↓"}`, min: 0, max: 100 };
      }),
      axisName: { show: !palette?.hideAxisNames, color: ink, fontSize: 11, fontFamily: "sans-serif" },
      splitArea: { show: false }, axisLine: { lineStyle: { color: rule } }, splitLine: { lineStyle: { color: rule } },
    },
    graphic: markers,
    series: series.map(item => ({ type: "radar", name: item.group.label, symbol: "none",
      lineStyle: { color: item.color, width: 2, type: "solid" },
      itemStyle: { color: item.color }, areaStyle: { color: item.color, opacity: 0.06 },
      emphasis: { focus: "series", lineStyle: { color: item.color, width: 3 }, areaStyle: { color: item.color, opacity: 0.15 } },
      data: [{ name: item.group.label, value: item.points.map(point => point.coordinate) }],
    })),
  };
}

function bindLeaderboardRadar(target, context) {
  const node = target.querySelector("[data-summary-radar]");
  if (!node) return;
  try {
    if (!window.echarts) throw new Error("ECharts unavailable");
    const instance = window.echarts.init(node, null, { renderer: "canvas" });
    chart = instance;
    const textContext = document.createElement("canvas").getContext("2d");
    textContext.font = "11px sans-serif";
    let renderedWidth = 0, renderedHeight = 0;
    const update = () => {
      if (chart !== instance || !node.isConnected) return;
      const width = node.clientWidth, height = node.clientHeight;
      if (!width || !height || width === renderedWidth && height === renderedHeight) return;
      renderedWidth = width; renderedHeight = height;
      instance.resize();
      instance.setOption(radarOption(context, width, height, null, text => textContext.measureText(text).width), true);
    };
    update();
    if (typeof ResizeObserver === "function") {
      observer = new ResizeObserver(() => {
        if (chart !== instance || resizeFrame !== null) return;
        resizeFrame = requestAnimationFrame(() => { resizeFrame = null; update(); });
      });
      observer.observe(node);
    }
    const highlight = group => {
      if (chart !== instance || !context.selected.some(item => item.key === group.key)) return;
      const index = context.series.findIndex(item => item.group.key === group.key);
      instance.dispatchAction({ type: "downplay" });
      instance.dispatchAction({ type: "highlight", seriesIndex: index });
      target.querySelector("[data-radar-detail]").innerHTML = groupDetails(context.series[index], context);
    };
    target.querySelectorAll("[data-radar-legend]").forEach(row => {
      const group = context.selected[Number(row.dataset.radarLegend)];
      row.addEventListener("pointerenter", () => highlight(group));
      row.addEventListener("focusin", () => highlight(group));
      const downplay = () => { if (chart === instance) instance.dispatchAction({ type: "downplay" }); };
      row.addEventListener("pointerleave", downplay);
      row.addEventListener("focusout", downplay);
    });
    chart.on("mouseover", params => {
      if (context.series[params.seriesIndex]) highlight(context.series[params.seriesIndex].group);
    });
  } catch {
    disposeLeaderboardRadar();
    node.hidden = true;
    target.querySelector("[data-radar-fallback]").hidden = false;
  }
}

export { radarContext, renderLeaderboardRadar, bindLeaderboardRadar, disposeLeaderboardRadar, radarOption, radarMetricLabel, originNote };
