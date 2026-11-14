import { esc, fmtNum, t } from "./shared.js";
import { relativePosition } from "./summary-chart.js";

function renderSummarySegments(label, items, selected, attribute) {
  return `<div class="leaderboard-summary-control"><div class="leaderboard-summary-segments" role="group" aria-label="${esc(label)}">${items.map(item => `<button type="button" class="leaderboard-summary-segment${selected === item.key ? " active" : ""}" ${attribute}="${esc(item.key)}" aria-pressed="${selected === item.key}">${esc(item.label)}</button>`).join("")}</div></div>`;
}

function renderSummaryHeader({ id, title, scope = "", actions }) {
  return `<div class="panel-head leaderboard-summary-head"><div><h2 id="${esc(id)}-title">${esc(title)}</h2>${scope ? `<p>${esc(scope)}</p>` : ""}</div><div class="leaderboard-summary-actions">${actions}</div></div>`;
}

function renderSummaryDisclosure({ id, open, summary, table, attribute = "data-summary-table-toggle" }) {
  return `<div class="leaderboard-summary-table-disclosure"><button type="button" class="leaderboard-summary-table-toggle" ${attribute} aria-expanded="${open}" aria-controls="${esc(id)}"><span><strong>${esc(t(open ? "summary_hide_table" : "summary_show_table", open ? "Hide summary table" : "Show summary table"))}</strong><small>${esc(summary)}</small></span><i aria-hidden="true">${open ? "−" : "+"}</i></button><div id="${esc(id)}" class="summary-table-region" ${open ? "" : "hidden"}>${open ? table : ""}</div></div>`;
}

function renderSummaryExportMenu({ id, kinds, disabledReason = () => "" }) {
  const hints = [...new Set(kinds.map(item => disabledReason(item.key)).filter(Boolean))];
  return `<details class="export-menu leaderboard-summary-export"><summary class="export-menu-button" aria-label="${esc(t("export_options", "Export options"))}">${esc(t("export", "Export"))}</summary><div class="export-menu-panel">${kinds.map(item => `<button type="button" data-summary-export="${esc(item.key)}" ${disabledReason(item.key) ? "disabled" : ""} aria-describedby="${esc(id)}-export-help">${esc(item.label)}</button>`).join("")}<small id="${esc(id)}-export-help" ${hints.length ? "" : "hidden"}>${hints.map(esc).join(" ")}</small></div></details>`;
}

function summaryBarData(definition, items, format) {
  let minimum = 0, maximum = 0;
  for (const item of items) { minimum = Math.min(minimum, item.value ?? 0); maximum = Math.max(maximum, item.value ?? 0); }
  const position = value => maximum === minimum ? 0 : relativePosition(value, minimum, maximum);
  const zero = position(0);
  return { definition, values: items.map(item => ({ ...item, formatted: format(item.value),
    count: item.row?.count || 0, zero, start: position(Math.min(0, item.value ?? 0)),
    width: item.value !== null ? Math.abs(position(item.value) - zero) : 0,
  })) };
}

function renderSummaryBarChart({ definition, values }, statistic = "") {
  return `<section class="leaderboard-summary-chart" data-summary-chart="${esc(definition.key)}"><div class="leaderboard-summary-chart-card-head"><h4>${esc(definition.label)}</h4><span>${esc(statistic)}</span></div><div class="leaderboard-summary-bar-list">${values.map(item => `<div class="leaderboard-summary-bar" role="img" aria-label="${esc(`${item.group.label}; ${definition.label}; ${statistic} ${item.formatted}; n=${item.count}${item.valueHint ? `; ${item.valueHint}` : ""}`)}" title="${esc(item.hint || "")}"><span class="leaderboard-summary-bar-label" title="${esc(item.group.label)}">${esc(item.group.label)}</span><span class="leaderboard-summary-bar-track"><b style="left:${item.zero}%"></b><i style="left:${item.start}%;width:${Number(item.width.toFixed(2))}%"></i></span><span class="leaderboard-summary-bar-value"><strong>${esc(item.formatted)}</strong><small>n=${fmtNum(item.count)}</small></span>${item.valueHint ? `<small class="summary-bar-note">${esc(item.valueHint)}</small>` : ""}</div>`).join("")}</div></section>`;
}

export { renderSummarySegments, renderSummaryHeader, renderSummaryDisclosure, renderSummaryExportMenu, summaryBarData, renderSummaryBarChart };
