import { esc, t } from "./shared.js";

import { radarColors } from "./summary-chart.js";

function summaryPieData(metric) {
  const maximum = metric.values.reduce((max, item) => Math.max(max, Number.isFinite(item.value) ? item.value : 0), 0);
  const total = maximum ? metric.values.reduce((sum, item) => sum + (Number.isFinite(item.value) && item.value > 0 ? item.value / maximum : 0), 0) : 0;
  const colors = radarColors(metric.values.length);
  let angle = -Math.PI / 2;
  return { definition: metric.definition, empty: !total, values: metric.values.map((item, index) => {
    const share = total && Number.isFinite(item.value) && item.value > 0 ? item.value / maximum / total : 0;
    const start = angle; angle += share * Math.PI * 2;
    return { ...item, color: item.color || colors[index], share, start, end: angle,
      percentage: item.value == null ? "" : `${(share * 100).toLocaleString(undefined, { maximumFractionDigits: 1 })}%` };
  }) };
}

function renderSummaryPieChart(metric) {
  const pie = summaryPieData(metric);
  const sectors = pie.values.filter(item => item.share > 0).map(item => {
    const title = esc(`${item.group.label}: ${item.formatted} · ${item.percentage}`);
    if (item.share >= 1) return `<circle cx="100" cy="100" r="88" fill="${item.color}"><title>${title}</title></circle>`;
    const point = angle => `${100 + Math.cos(angle) * 88} ${100 + Math.sin(angle) * 88}`;
    return `<path d="M 100 100 L ${point(item.start)} A 88 88 0 ${item.share > .5 ? 1 : 0} 1 ${point(item.end)} Z" fill="${item.color}"><title>${title}</title></path>`;
  }).join("");
  return `<section class="leaderboard-summary-chart" data-summary-chart="${esc(pie.definition.key)}"><div class="leaderboard-summary-chart-card-head"><h4>${esc(pie.definition.label)}</h4></div><div class="summary-pie"><svg viewBox="0 0 200 200" role="img" aria-label="${esc(`${pie.definition.label}: ${t("summary_pie", "Pie chart")}`)}">${sectors || '<circle cx="100" cy="100" r="88" fill="none" stroke="var(--rule)" stroke-width="1" />'}</svg>${pie.empty ? `<p>${esc(t("summary_pie_empty", "No positive values to plot"))}</p>` : ""}<ul>${pie.values.map(item => `<li data-pie-group="${esc(JSON.stringify(item.group.key))}"><i style="background:${item.color}" aria-hidden="true"></i><span>${esc(item.group.label)}</span><strong>${esc(item.formatted)}${item.percentage ? ` · ${esc(item.percentage)}` : ""}</strong>${item.valueHint ? `<small>${esc(item.valueHint)}</small>` : ""}</li>`).join("")}</ul></div></section>`;
}

export { summaryPieData, renderSummaryPieChart };
