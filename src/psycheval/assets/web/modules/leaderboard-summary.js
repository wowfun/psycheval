import { metricDefinitions, selectedMetricDefinitions, formatMetric } from "./metric-presentation.js";
import { renderSummaryMetricControl, bindSummaryMetricControl } from "./summary-metrics.js";
import { $, esc, fmtMs, fmtNum, fmtPct, hasMetricValue, listValue, state, t } from "./runtime.js";
import { tableCellContent, tableValueAttributes } from "./data-tables.js";
import { exportLeaderboardSummary, loadLeaderboardSummary } from "./serve-catalog.js";
import { bindWorkspaceViewControls, renderWorkspaceViewControls } from "./workspace-views.js";
import { workspaceLocationChanged } from "../app/workspace-runtime.js";
import { radarContext, renderLeaderboardRadar, bindLeaderboardRadar, disposeLeaderboardRadar } from "./leaderboard-radar.js";
import { radarSelection, relativePosition } from "./summary-chart.js";
import { downloadSummaryImage } from "./leaderboard-summary-export.js";
import { beginFeedback } from "./action-feedback.js";

let imageExportBusy = false;

function renderLeaderboardSummary() {
  disposeLeaderboardRadar();
  const target = $("leaderboard-summary");
  if (!target) return;
  const summary = state.leaderboardSummary?.summary || null;
  const matchedCount = Number(summary?.matched_count ?? state.catalogPage?.total ?? 0);
  const initialChecking = Boolean(
    state.leaderboardSummary?.checking
    && !Number(state.leaderboardSummary?.generation || 0),
  );
  const heading = `
    <div class="panel-head leaderboard-summary-head">
      <div>
        <h2 id="leaderboard-summary-title">${esc(t("leaderboard_summary", "Leaderboard Summary"))}</h2>
        ${initialChecking ? "" : `<p>${esc(leaderboardSummaryScopeText(matchedCount))}</p>`}
      </div>
      ${renderLeaderboardSummaryActions()}
    </div>`;
  if (state.leaderboardSummaryLoading || state.leaderboardSummary?.checking) {
    target.innerHTML = `
      ${heading}
      <p class="leaderboard-summary-empty" aria-live="polite">${esc(t("leaderboard_summary_loading", "Calculating the complete-query summary…"))}</p>
    `;
    bindLeaderboardSummaryControls(target);
    return;
  }
  if (state.leaderboardSummaryError) {
    const detail = String(state.leaderboardSummaryError);
    target.innerHTML = `
      ${heading}
      <p class="leaderboard-summary-empty" role="alert">${esc(t("leaderboard_summary_error", "The complete-query summary is unavailable."))} ${esc(detail)}</p>
    `;
    bindLeaderboardSummaryControls(target);
    return;
  }
  if (!summary || matchedCount < 1) {
    target.innerHTML = `
      ${heading}
      <p class="leaderboard-summary-empty">${esc(t("leaderboard_summary_empty", "No Trials match the current conditions."))}</p>
    `;
    bindLeaderboardSummaryControls(target);
    return;
  }

  const groups = leaderboardSummaryGroups();
  const radar = leaderboardRadarContext(groups);
  target.innerHTML = `
    ${heading}
    ${visibleLeaderboardSummaryDefinitions(groups).length ? renderLeaderboardSummaryTableDisclosure(groups) : `<p class="leaderboard-summary-empty">${esc(t("metric_select", "Select at least one available metric with data."))}</p>`}
    ${state.leaderboardSummaryGroupBy === "overall" ? "" : renderLeaderboardSummaryCharts(groups, radar)}
  `;
  bindLeaderboardSummaryControls(target, radar);
}

function leaderboardSummaryGroups() {
  const definitions = new Map(leaderboardSummaryDefinitions().map(item => [item.key, item]));
  return listValue(state.leaderboardSummary?.summary?.groups).map(group => ({
    ...group,
    metrics: (group.metrics || []).map(row => ({ ...definitions.get(row.key), ...row })),
    label: state.leaderboardSummaryGroupBy === "overall" && group?.key === "overall"
      ? t("summary_overall", "Overall")
      : String(group?.label ?? "-"),
  }));
}

function leaderboardSummaryScopeText(count) {
  return t(
    "leaderboard_summary_scope",
    "{count} matching Trials across all pages.",
  ).replace("{count}", fmtNum(count));
}

function renderLeaderboardSummaryActions() {
  const workspaceControls = renderWorkspaceViewControls();
  const exportControl = `<details class="export-menu leaderboard-summary-export">
    <summary class="export-menu-button" aria-label="${esc(t("export_options", "Export options"))}">${esc(t("export", "Export"))}</summary>
    <div class="export-menu-panel">
      <button type="button" data-summary-export="xlsx" aria-describedby="summary-export-help">${esc(t("export_excel", "Export Excel"))}</button>
      <button type="button" data-summary-export="bar" aria-describedby="summary-export-help">${esc(t("summary_export_bar", "Bar chart (.png)"))}</button>
      <button type="button" data-summary-export="radar" aria-describedby="summary-export-help">${esc(t("summary_export_radar", "Radar chart (.png)"))}</button>
      <small id="summary-export-help" hidden></small>
    </div>
  </details>`;
  return `<div class="leaderboard-summary-actions">${renderLeaderboardSummaryGroupControl()}${workspaceControls}${renderSummaryMetricControl(state)}${exportControl}</div>`;
}

function renderLeaderboardSummaryGroupControl() {
  return `<div class="leaderboard-summary-control leaderboard-summary-group-control">
    <span>${esc(t("summary_group_by", "Group by"))}</span>
    <div class="leaderboard-summary-segments" role="group" aria-label="${esc(t("summary_group_by", "Group by"))}">
      ${leaderboardSummaryGroupButton("overall", t("summary_overall", "Overall"))}
      ${leaderboardSummaryGroupButton("agent", t("agent", "Agent"))}
      ${leaderboardSummaryGroupButton("model", t("model", "Model"))}
      ${leaderboardSummaryGroupButton("category", t("category", "Category"))}
      ${leaderboardSummaryGroupButton("task", t("task", "Task"))}
      ${leaderboardSummaryGroupButton("job", t("job", "Job"))}
      ${leaderboardSummaryGroupButton("provider", t("provider", "Provider"))}
    </div>
  </div>`;
}

function leaderboardSummaryGroupButton(value, label) {
  const active = state.leaderboardSummaryGroupBy === value;
  return `<button type="button" class="leaderboard-summary-segment${active ? " active" : ""}" data-summary-group-by="${esc(value)}" aria-pressed="${active}">${esc(label)}</button>`;
}

function leaderboardSummaryDefinitions() { return metricDefinitions(state); }

function visibleLeaderboardSummaryDefinitions(groups, savedView = false) {
  return (savedView ? leaderboardSummaryDefinitions().filter(item => item.saved_view) : selectedMetricDefinitions(state)).filter(definition => listValue(groups).some(group => (
    listValue(group?.metrics).some(metric => (
      metric?.key === definition.key && Number(metric?.count || 0) > 0
    ))
  )));
}

function renderLeaderboardSummaryTableDisclosure(groups) {
  const open = Boolean(state.leaderboardSummaryTableOpen);
  const unit = leaderboardSummaryGroupUnit(state.leaderboardSummaryGroupBy);
  const summary = `${visibleLeaderboardSummaryDefinitions(groups).length} ${t("summary_metrics", "metrics")} · ${groups.length} ${unit}`;
  return `<div class="leaderboard-summary-table-disclosure">
    <button type="button" class="leaderboard-summary-table-toggle" data-summary-table-toggle aria-expanded="${open}" aria-controls="leaderboard-summary-table-region">
      <span><strong>${esc(t(open ? "summary_hide_table" : "summary_show_table", open ? "Hide summary table" : "Show summary table"))}</strong><small>${esc(summary)}</small></span>
      <i aria-hidden="true">${open ? "−" : "+"}</i>
    </button>
    ${open ? `<div id="leaderboard-summary-table-region">${renderLeaderboardSummaryTable(groups)}</div>` : ""}
  </div>`;
}

function renderLeaderboardSummaryTable(groups) {
  const groupHeading = leaderboardSummaryGroupHeading(state.leaderboardSummaryGroupBy);
  const statistics = leaderboardSummaryStatistics();
  return `<div class="table-shell leaderboard-summary-shell"><div class="table-wrap"><table class="data-table leaderboard-summary-table">
    <thead><tr>
      <th ${tableValueAttributes("identity", t("summary_metric", "Metric"))}>${tableCellContent(esc(t("summary_metric", "Metric")))}</th>
      <th ${tableValueAttributes("identity", groupHeading)}>${tableCellContent(esc(groupHeading))}</th>
      <th ${tableValueAttributes("number", t("summary_count", "Count"), "num")}>${tableCellContent(esc(t("summary_count", "Count")))}</th>
      ${statistics.map(statistic => `<th ${tableValueAttributes("number", statistic.label, `num${state.leaderboardSummaryStatistic === statistic.key ? " summary-selected-stat" : ""}`)} data-summary-stat-heading="${esc(statistic.key)}">${tableCellContent(esc(statistic.label))}</th>`).join("")}
    </tr></thead>
    <tbody>${visibleLeaderboardSummaryDefinitions(groups).map(definition => renderLeaderboardSummaryMetricGroup(definition, groups, statistics)).join("")}</tbody>
  </table></div></div>`;
}

function renderLeaderboardSummaryMetricGroup(definition, groups, statistics) {
  return groups.map((group, index) => {
    const row = group.metrics.find(metric => metric.key === definition.key);
    return `<tr data-summary-metric="${esc(definition.key)}"${index === 0 ? " data-summary-group-start" : ""}>
      ${index === 0 ? `<th ${tableValueAttributes("identity", definition.label, "summary-metric-cell")} scope="rowgroup" rowspan="${groups.length}">${tableCellContent(esc(definition.label))}</th>` : ""}
      <th ${tableValueAttributes("identity", group.label, "summary-group-cell")} scope="row">${tableCellContent(`<strong>${esc(group.label)}</strong><span>n=${fmtNum(group.count)}</span>`)}</th>
      <td ${tableValueAttributes("number", fmtNum(row?.count), "num")}>${tableCellContent(fmtNum(row?.count))}</td>
      ${statistics.map(statistic => { const value = leaderboardSummaryValue(row, statistic.value(row)); return `<td ${tableValueAttributes("number", value, `num${state.leaderboardSummaryStatistic === statistic.key ? " summary-selected-stat" : ""}`)} data-summary-stat="${esc(statistic.key)}">${tableCellContent(esc(value))}</td>`; }).join("")}
    </tr>`;
  }).join("");
}

function leaderboardSummaryStatistics() {
  return [
    { key: "mean", label: t("summary_mean", "Mean"), value: row => row?.mean },
    { key: "min", label: t("metric_min", "Min"), value: row => row?.distribution?.min },
    { key: "q1", label: t("summary_q1", "Q1"), value: row => row?.distribution?.q1 },
    { key: "p50", label: t("summary_p50", "P50"), value: row => row?.distribution?.p50 },
    { key: "q3", label: t("summary_q3", "Q3"), value: row => row?.distribution?.q3 },
    { key: "p95", label: t("summary_p95", "P95"), value: row => row?.distribution?.p95 },
    { key: "max", label: t("metric_max", "Max"), value: row => row?.distribution?.max },
  ];
}

function leaderboardRadarContext(groups) {
  return state.leaderboardSummaryChartType === "radar"
    ? radarContext(groups, selectedMetricDefinitions(state), selectedLeaderboardSummaryStatistic(), leaderboardSummaryValue) : null;
}

function renderLeaderboardSummaryCharts(groups, radar = leaderboardRadarContext(groups)) {
  const statistic = selectedLeaderboardSummaryStatistic();
  const groupHeading = leaderboardSummaryGroupHeading(state.leaderboardSummaryGroupBy);
  const isRadar = state.leaderboardSummaryChartType === "radar";
  return `<section class="leaderboard-summary-chart-panel" aria-labelledby="leaderboard-summary-chart-title">
    <div class="leaderboard-summary-chart-head">
      <div>
        <h3 id="leaderboard-summary-chart-title">${esc(statistic.label)} · ${esc(groupHeading)}</h3>
        <p>${esc(isRadar ? t("summary_radar_scale", "Relative to all groups in the current query · farther out is better. × = no data (offset near the origin for readability).") : t("summary_scale_note", "Each metric has its own scale. Compare bars only within a metric."))}</p>
      </div>
      <div class="summary-chart-controls">${renderLeaderboardSummaryChartTypeControl()}${renderLeaderboardSummaryStatisticControl()}</div>
    </div>
    ${isRadar ? renderLeaderboardRadar(radar) : `<div class="leaderboard-summary-chart-grid">
      ${visibleLeaderboardSummaryDefinitions(groups).map(definition => renderLeaderboardSummaryChart(definition, groups, statistic)).join("")}
    </div>`}
  </section>`;
}

function renderLeaderboardSummaryChartTypeControl() {
  return `<div class="leaderboard-summary-control"><span>${esc(t("summary_chart_type", "Chart"))}</span><div class="leaderboard-summary-segments" role="group" aria-label="${esc(t("summary_chart_type", "Chart"))}">${["bar", "radar"].map(type => `<button type="button" class="leaderboard-summary-segment${state.leaderboardSummaryChartType === type ? " active" : ""}" data-summary-chart-type="${type}" aria-pressed="${state.leaderboardSummaryChartType === type}">${esc(type === "bar" ? t("summary_bar", "Bar chart") : t("summary_radar", "Radar chart"))}</button>`).join("")}</div></div>`;
}

function summaryPresentationChanged(selector) {
  workspaceLocationChanged("home");
  const target = $("leaderboard-summary");
  const panel = target?.querySelector(".leaderboard-summary-chart-panel");
  if (!panel) { renderLeaderboardSummary(); return; }
  const groups = leaderboardSummaryGroups();
  const radar = leaderboardRadarContext(groups);
  disposeLeaderboardRadar();
  panel.outerHTML = renderLeaderboardSummaryCharts(groups, radar);
  bindLeaderboardSummaryChartControls(target, radar);
  updateSummaryExportControls(target);
  target.querySelectorAll("[data-summary-stat-heading],[data-summary-stat]").forEach(cell => {
    cell.classList.toggle("summary-selected-stat", (cell.dataset.summaryStatHeading || cell.dataset.summaryStat) === state.leaderboardSummaryStatistic);
  });
  target.querySelector(selector)?.focus({ preventScroll: true });
}

function renderLeaderboardSummaryStatisticControl() {
  return `<div class="leaderboard-summary-control leaderboard-summary-stat-control">
    <span>${esc(t("summary_statistic", "Statistic"))}</span>
    <div class="leaderboard-summary-segments" role="group" aria-label="${esc(t("summary_chart_statistic", "Chart statistic"))}">
      ${leaderboardSummaryStatistics().map(statistic => {
        const active = state.leaderboardSummaryStatistic === statistic.key;
        return `<button type="button" class="leaderboard-summary-segment${active ? " active" : ""}" data-summary-statistic="${esc(statistic.key)}" aria-pressed="${active}">${esc(statistic.label)}</button>`;
      }).join("")}
    </div>
  </div>`;
}

function selectedLeaderboardSummaryStatistic() {
  return leaderboardSummaryStatistics().find(statistic => statistic.key === state.leaderboardSummaryStatistic)
    || leaderboardSummaryStatistics()[0];
}

function leaderboardSummaryChartData(definition, groups, statistic) {
  const values = groups.map(group => {
    const row = group.metrics.find(metric => metric.key === definition.key);
    return { group, row, value: summaryNumber(statistic.value(row)) };
  });
  const minimum = Math.min(0, ...values.map(item => item.value ?? 0));
  const maximum = Math.max(0, ...values.map(item => item.value ?? 0));
  const position = value => maximum === minimum ? 0 : relativePosition(value, minimum, maximum);
  const zero = position(0);
  return { definition, values: values.map(item => ({
    ...item,
    formatted: formatMetric(definition, item.value),
    count: item.row?.count || 0,
    zero,
    start: position(Math.min(0, item.value ?? 0)),
    width: item.value !== null ? Math.abs(position(item.value) - zero) : 0,
  })) };
}

function renderLeaderboardSummaryChart(definition, groups, statistic) {
  const { values } = leaderboardSummaryChartData(definition, groups, statistic);
  return `<section class="leaderboard-summary-chart" data-summary-chart="${esc(definition.key)}">
    <div class="leaderboard-summary-chart-card-head"><h4>${esc(definition.label)}</h4><span>${esc(statistic.label)}</span></div>
    <div class="leaderboard-summary-bar-list">${values.map(item => {
      const { formatted, width } = item;
      const ariaLabel = `${item.group.label}; ${definition.label}; ${statistic.label} ${formatted}; n=${item.row?.count || 0}`;
      return `<div class="leaderboard-summary-bar" role="img" aria-label="${esc(ariaLabel)}">
        <span class="leaderboard-summary-bar-label" title="${esc(item.group.label)}">${esc(item.group.label)}</span>
        <span class="leaderboard-summary-bar-track"><b style="left:${item.zero}%"></b><i style="left:${item.start}%;width:${Number(width.toFixed(2))}%"></i></span>
        <span class="leaderboard-summary-bar-value"><strong>${esc(formatted)}</strong><small>n=${fmtNum(item.row?.count || 0)}</small></span>
      </div>`;
    }).join("")}</div>
  </section>`;
}

function bindLeaderboardSummaryChartControls(target, radar) {
  target.querySelectorAll("[data-summary-chart-type]").forEach(button => button.addEventListener("click", () => {
    state.leaderboardSummaryChartType = button.dataset.summaryChartType;
    summaryPresentationChanged(`[data-summary-chart-type='${button.dataset.summaryChartType}']`);
  }));
  if (radar) bindLeaderboardRadar(target, radar, summaryPresentationChanged);
  target.querySelectorAll("[data-summary-statistic]").forEach(button => {
    button.addEventListener("click", () => setLeaderboardSummaryStatistic(button.dataset.summaryStatistic));
  });
}

function bindLeaderboardSummaryControls(target, radar = null) {
  if (!target?.querySelectorAll) return;
  bindLeaderboardSummaryChartControls(target, radar);
  bindSummaryMetricControl(target, state, () => { workspaceLocationChanged("home"); renderLeaderboardSummary(); });
  target.querySelectorAll("[data-summary-group-by]").forEach(button => {
    button.addEventListener("click", () => setLeaderboardSummaryGroupBy(button.dataset.summaryGroupBy));
  });
  target.querySelectorAll("[data-summary-table-toggle]").forEach(button => {
    button.addEventListener("click", toggleLeaderboardSummaryTable);
  });
  updateSummaryExportControls(target);
  target.querySelector(".leaderboard-summary-export")?.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.open = false;
    event.currentTarget.querySelector("summary").focus();
  });
  target.querySelectorAll("[data-summary-export]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      const kind = button.dataset.summaryExport;
      if (imageExportBusy || summaryExportDisabledReason(kind)) return;
      const menu = button.closest("details");
      menu.open = false;
      menu.querySelector("summary").focus({ preventScroll: true });
      if (kind === "xlsx") exportLeaderboardSummary();
      else exportLeaderboardImage(kind);
    });
  });
  bindWorkspaceViewControls(target);
}

function summaryExportDisabledReason(kind) {
  if (!visibleLeaderboardSummaryDefinitions(leaderboardSummaryGroups()).length) return t("metric_select", "Select at least one available metric with data.");
  if (kind === "radar" && selectedMetricDefinitions(state).filter(item => ["higher", "lower"].includes(item.direction)).length < 3) return t("metric_radar_min", "Select at least three metrics with a direction.");
  if (kind === "xlsx") return Number(state.catalogPage?.total || 0) ? "" : t("leaderboard_summary_empty", "No Trials match the current conditions.");
  const summary = state.leaderboardSummary?.summary;
  if (state.leaderboardSummaryLoading || state.leaderboardSummary?.checking || state.leaderboardSummaryError || !summary?.matched_count || !summary.groups?.length) {
    return t("summary_export_not_ready", "Chart export requires a completed, nonempty summary.");
  }
  if (state.leaderboardSummaryGroupBy === "overall") return t("summary_export_group_required", "Select a grouping to export charts.");
  if (kind === "radar" && !radarSelection(summary.groups, state.leaderboardSummaryRadarGroups).length) return t("summary_radar_select", "Select up to five groups to compare.");
  if (kind === "bar" && !visibleLeaderboardSummaryDefinitions(summary.groups).length) return t("summary_no_data", "No data");
  return "";
}

function updateSummaryExportControls(target) {
  const hints = new Set();
  target?.querySelectorAll("[data-summary-export]").forEach(button => {
    const reason = summaryExportDisabledReason(button.dataset.summaryExport);
    button.disabled = imageExportBusy || Boolean(reason);
    button.title = reason;
    if (reason) hints.add(reason);
  });
  const help = target?.querySelector("#summary-export-help");
  if (help) { help.textContent = [...hints].join(" "); help.hidden = !hints.size; }
}

function leaderboardSummaryImageSnapshot() {
  const groups = structuredClone(leaderboardSummaryGroups());
  const statistic = selectedLeaderboardSummaryStatistic();
  return {
    title: t("leaderboard_summary", "Leaderboard Summary"),
    subtitle: `${statistic.label} · ${leaderboardSummaryGroupHeading()}`,
    scope: leaderboardSummaryScopeText(state.leaderboardSummary.summary.matched_count),
    bars: visibleLeaderboardSummaryDefinitions(groups).map(definition => leaderboardSummaryChartData(definition, groups, statistic)),
    radar: radarContext(groups, selectedMetricDefinitions(state), statistic, leaderboardSummaryValue),
  };
}

async function exportLeaderboardImage(kind) {
  const feedback = beginFeedback("#leaderboard-summary .leaderboard-summary-head", { key: "home:summary-image", page: "home" });
  imageExportBusy = true;
  updateSummaryExportControls($("leaderboard-summary"));
  feedback.pending(t("summary_export_generating", "Generating image…"));
  try {
    const snapshot = leaderboardSummaryImageSnapshot();
    await downloadSummaryImage(kind, snapshot);
    feedback.clear();
  } catch (error) {
    feedback.error(`${t("summary_export_failed", "Could not export the chart.")} ${error.message || error}`);
  } finally {
    imageExportBusy = false;
    updateSummaryExportControls($("leaderboard-summary"));
  }
}

async function setLeaderboardSummaryGroupBy(value) {
  if (!["overall", "agent", "model", "category", "task", "job", "provider"].includes(value)) return;
  state.leaderboardSummaryGroupBy = value;
  state.leaderboardSummaryRadarGroups = null;
  workspaceLocationChanged("home");
  const request = loadLeaderboardSummary();
  renderLeaderboardSummary();
  await request;
  renderLeaderboardSummary();
}

function leaderboardSummaryGroupHeading(groupBy = state.leaderboardSummaryGroupBy) {
  if (groupBy === "overall") return t("summary_scope", "Scope");
  if (groupBy === "model") return t("model", "Model");
  if (groupBy === "category") return t("category", "Category");
  if (groupBy === "task") return t("task", "Task");
  if (groupBy === "job") return t("job", "Job");
  if (groupBy === "provider") return t("provider", "Provider");
  return t("agent", "Agent");
}

function leaderboardSummaryGroupUnit(groupBy = state.leaderboardSummaryGroupBy) {
  if (groupBy === "overall") return t("summary_scopes", "scope");
  if (groupBy === "model") return t("summary_models", "models");
  if (groupBy === "category") return t("summary_categories", "categories");
  if (groupBy === "task") return t("summary_tasks", "tasks");
  if (groupBy === "job") return t("summary_jobs", "jobs");
  if (groupBy === "provider") return t("summary_providers", "providers");
  return t("summary_agents", "agents");
}

function toggleLeaderboardSummaryTable() {
  state.leaderboardSummaryTableOpen = !state.leaderboardSummaryTableOpen;
  workspaceLocationChanged("home");
  renderLeaderboardSummary();
}

function setLeaderboardSummaryStatistic(value) {
  if (!leaderboardSummaryStatistics().some(statistic => statistic.key === value)) return;
  state.leaderboardSummaryStatistic = value;
  summaryPresentationChanged(`[data-summary-statistic='${value}']`);
}

function leaderboardSummaryValue(row, value) {
  return formatMetric(row?.unit !== undefined ? row : leaderboardSummaryDefinitions().find(item => item.key === row?.key) || row, value);
}

function summaryNumber(value) {
  if (!hasMetricValue(value)) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}
export {
  bindLeaderboardSummaryControls,
  leaderboardSummaryDefinitions,
  leaderboardSummaryChartData,
  leaderboardSummaryImageSnapshot,
  leaderboardSummaryGroupButton,
  leaderboardSummaryGroupHeading,
  leaderboardSummaryGroupUnit,
  leaderboardSummaryStatistics,
  leaderboardSummaryValue,
  renderLeaderboardSummary,
  renderLeaderboardSummaryActions,
  renderLeaderboardSummaryChart,
  renderLeaderboardSummaryCharts,
  renderLeaderboardSummaryGroupControl,
  renderLeaderboardSummaryMetricGroup,
  renderLeaderboardSummaryStatisticControl,
  renderLeaderboardSummaryTable,
  renderLeaderboardSummaryTableDisclosure,
  selectedLeaderboardSummaryStatistic,
  setLeaderboardSummaryGroupBy,
  setLeaderboardSummaryStatistic,
  leaderboardSummaryScopeText,
  summaryNumber,
  toggleLeaderboardSummaryTable,
  visibleLeaderboardSummaryDefinitions,
};
