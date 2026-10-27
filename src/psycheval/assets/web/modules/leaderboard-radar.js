import { esc, fmtNum, state, t } from "./runtime.js";
import { RADAR_GROUP_LIMIT } from "../app/workspace-view-contract.js";
import { radarAxes, radarPoints, radarSelection, radarColors } from "./summary-chart.js";

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

function radarContext(groups, definitions, statistic, format) {
  const axes = radarAxes(groups, definitions, statistic.value);
  const selected = radarSelection(groups, state.leaderboardSummaryRadarGroups);
  const colors = radarColors(selected.length);
  const series = selected.map((group, index) => ({ group, points: radarPoints(group, axes, statistic.value), color: colors[index] }));
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
  const { groups, definitions, axes, selected, series } = context;
  const chosen = new Set(selected.map(group => group.key));
  const unavailable = state.leaderboardSummaryRadarGroups?.filter(key => !groups.some(group => group.key === key)) || [];
  return `  <div class="summary-radar-layout">
    <div class="summary-radar-plot">
      ${selected.length && axes.length >= 3 ? `<div data-summary-radar role="img" aria-label="${esc(t("summary_radar", "Radar chart"))}"></div>` : `<p class="leaderboard-summary-empty">${esc((axes.length < 3 ? t("metric_radar_min", "Select at least three metrics with a direction.") : t("summary_radar_select", "Select up to five groups to compare.")))}</p>`}
      <p data-radar-fallback hidden role="alert">${esc(t("summary_radar_unavailable", "Radar chart is unavailable. Switch to the bar chart or use the summary table."))}</p>
      <div class="summary-radar-detail" data-radar-detail aria-live="polite">${series.length ? groupDetails(series[0], context) : ""}</div>
    </div>
    <div class="summary-radar-comparisons">
      <div class="summary-radar-group-head"><strong>${esc(t("summary_radar_groups", "Comparison groups"))} <span data-radar-count>${selected.length}/${RADAR_GROUP_LIMIT}</span></strong><button type="button" class="action-button compact" data-radar-reset>${esc(t("summary_radar_first", "First five"))}</button></div>
      <label class="summary-radar-search">${esc(t("search", "Search"))}<input type="search" data-radar-search autocomplete="off" value="${esc(state.leaderboardSummaryRadarSearch || "")}"></label>
      ${unavailable.length ? `<p class="summary-radar-warning" role="status">${esc(t("summary_radar_removed", "Some selected groups are outside the current results:"))} ${esc(unavailable.map(key => key ?? "-").join(", "))}</p>` : ""}
      <div class="summary-radar-group-list">${groups.map((group, index) => {
        const item = series.find(item => item.group === group);
        const points = item?.points || radarPoints(group, axes, context.statistic.value);
        const missing = points.filter(point => point.value === null).map(point => radarMetricLabel(context, point.key));
        const note = originNote(points);
        const checked = chosen.has(group.key);
        return `<label class="summary-radar-group" data-radar-group-row="${index}" style="--radar-color:${item?.color || "var(--rule)"}"><input type="checkbox" data-radar-group="${index}" ${checked ? "checked" : ""} ${!checked && selected.length >= RADAR_GROUP_LIMIT ? "disabled" : ""}><span><strong>${esc(group.label)}</strong><small>n=${fmtNum(group.count)}</small>${note ? `<small>${esc(note)}</small>` : ""}${missing.length ? `<small class="summary-radar-warning">× ${esc(t("summary_no_data", "No data"))}: ${esc(missing.join(", "))}</small>` : ""}</span></label>`;
      }).join("")}</div>
      <p data-radar-search-empty hidden>${esc(t("summary_radar_no_groups", "No matching groups."))}</p>
    </div>
  </div>`;
}

function radarOption(context, width, height, palette = null) {
  const { axes, series } = context;
  const root = palette ? null : document.querySelector("[data-summary-radar]");
  const style = root ? window.getComputedStyle(root) : null;
  const ink = palette?.ink || style?.getPropertyValue("--ink").trim() || "#292c36";
  const rule = palette?.rule || style?.getPropertyValue("--rule").trim() || "#dadce2";
  const radius = palette?.radius ?? Math.min(width, height) * 0.29;
  const center = palette?.center || [width / 2, height / 2];
  // Match the pinned ECharts 6.1.0 layout below: centered, 90° start, counterclockwise.
  const markers = series.flatMap((item, seriesIndex) => item.points.map((point, index) => {
    const angle = Math.PI / 2 + index * 2 * Math.PI / axes.length;
    const distance = point.value === null ? 12 + seriesIndex * 10 : radius * point.coordinate / 100;
    const x = center[0] + distance * Math.cos(angle);
    const y = center[1] - distance * Math.sin(angle);
    return point.value === null
      ? { type: "group", x, y, silent: true, children: [{ type: "line", shape: { x1: -4, y1: -4, x2: 4, y2: 4 }, style: { stroke: item.color, lineWidth: 2 } }, { type: "line", shape: { x1: -4, y1: 4, x2: 4, y2: -4 }, style: { stroke: item.color, lineWidth: 2 } }] }
      : { type: "circle", shape: { cx: x, cy: y, r: 3 }, silent: true, style: { fill: item.color, stroke: "#fff", lineWidth: 1 } };
  }));
  return {
    animation: false,
    tooltip: { trigger: "item", confine: true, formatter: params => groupDetails(series[params.seriesIndex], context) },
    radar: { center, radius, startAngle: 90, splitNumber: 4,
      indicator: axes.map(axis => ({ name: `${radarMetricLabel(context, axis.key)}\n${axis.direction > 0 ? "↑" : "↓"}`, min: 0, max: 100 })),
      axisName: { show: !palette?.hideAxisNames, color: ink, fontSize: 11, width: Math.max(75, Math.min(140, width * 0.23)), overflow: "break" },
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

function bindLeaderboardRadar(target, context, change) {
  const search = target.querySelector("[data-radar-search]");
  const searchRows = [...target.querySelectorAll("[data-radar-group-row]")].map(row => ({ row, label: context.groups[Number(row.dataset.radarGroupRow)].label.toLocaleLowerCase() }));
  const filterGroups = () => {
    let visible = 0;
    const query = search.value.trim().toLocaleLowerCase();
    searchRows.forEach(({ row, label }) => {
      row.hidden = !label.includes(query);
      if (!row.hidden) visible += 1;
    });
    target.querySelector("[data-radar-search-empty]").hidden = visible > 0;
  };
  search?.addEventListener("input", () => { state.leaderboardSummaryRadarSearch = search.value; filterGroups(); });
  if (search) filterGroups();
  target.querySelectorAll("[data-radar-group]").forEach(input => {
    const group = context.groups[Number(input.dataset.radarGroup)];
    input.addEventListener("change", () => {
      const keys = context.selected.map(item => item.key);
      state.leaderboardSummaryRadarGroups = input.checked ? [...keys, group.key] : keys.filter(key => key !== group.key);
      change("[data-radar-group='" + input.dataset.radarGroup + "']");
    });
  });
  target.querySelector("[data-radar-reset]")?.addEventListener("click", () => {
    state.leaderboardSummaryRadarGroups = null;
    change("[data-radar-reset]");
  });
  const node = target.querySelector("[data-summary-radar]");
  if (!node) return;
  try {
    if (!window.echarts) throw new Error("ECharts unavailable");
    const instance = window.echarts.init(node, null, { renderer: "canvas" });
    chart = instance;
    let renderedWidth = 0, renderedHeight = 0;
    const update = () => {
      if (chart !== instance || !node.isConnected) return;
      const width = node.clientWidth, height = node.clientHeight;
      if (!width || !height || width === renderedWidth && height === renderedHeight) return;
      renderedWidth = width; renderedHeight = height;
      instance.resize();
      instance.setOption(radarOption(context, width, height), true);
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
    target.querySelectorAll("[data-radar-group-row]").forEach(row => {
      const group = context.groups[Number(row.dataset.radarGroupRow)];
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
