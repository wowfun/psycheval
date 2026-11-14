import { bindToolbarMenus } from "./toolbar-menu.js";
import { renderSummarySegments, renderSummaryHeader, renderSummaryDisclosure, renderSummaryExportMenu, summaryBarData, renderSummaryBarChart } from "./summary-ui.js";
import { metricDefinitions, selectedMetricDefinitions, formatMetric, metricProvenanceHint, metricSelectionHint, metricSearchText } from "./metric-presentation.js";
import { METRIC_SELECTION_LIMIT } from "../app/metric-contract.js";
import { renderSummaryMetricControl, bindSummaryMetricControl } from "./summary-metrics.js";
import { renderSummaryGroupControl, bindSummaryGroupControl } from "./summary-groups.js";
import { $, esc, fmtMs, fmtNum, fmtPct, hasMetricValue, listValue, state, t } from "./runtime.js";
import { renderTableShell, tableCellContent, tableValueAttributes } from "./data-tables.js";
import { exportLeaderboardSummary, loadLeaderboardSummary } from "./serve-catalog.js";
import { workspaceLocationChanged } from "../app/workspace-runtime.js";
import { radarContext, renderLeaderboardRadar, bindLeaderboardRadar, disposeLeaderboardRadar } from "./summary-radar.js";
import { comparisonGroups } from "./summary-chart.js";
import { downloadSummaryImage } from "./summary-image.js";
import { beginFeedback } from "./action-feedback.js";
import { preflightHomeChange } from "./home-location.js";
import { modelDisplayName } from "./shared.js";

let imageExportBusy = false;

const summaryControls = {
  id: "leaderboard-summary",
  get groupBy() { return state.leaderboardSummaryGroupBy; }, set groupBy(value) { state.leaderboardSummaryGroupBy = value; },
  get groups() { return state.leaderboardSummaryComparisonGroups; }, set groups(value) { state.leaderboardSummaryComparisonGroups = value; },
  get groupDraft() { return state.leaderboardGroupDraft; }, set groupDraft(value) { state.leaderboardGroupDraft = value; },
  get groupSearch() { return state.leaderboardSummaryGroupSearch; }, set groupSearch(value) { state.leaderboardSummaryGroupSearch = value; },
  get metrics() { return state.leaderboardSummaryMetrics; }, set metrics(value) { state.leaderboardSummaryMetrics = value; },
  get metricDraft() { return state.leaderboardMetricDraft; }, set metricDraft(value) { state.leaderboardMetricDraft = value; },
  get metricSearch() { return state.leaderboardMetricSearch; }, set metricSearch(value) { state.leaderboardMetricSearch = value; },
};
function metricControlOptions() {
  const definitions = metricDefinitions(state);
  return { definitions, defaults: definitions.filter(item => item.default).map(item => item.key), limit: METRIC_SELECTION_LIMIT, searchText: metricSearchText,
    hint: key => metricSelectionHint(state.leaderboardSummary?.summary?.groups || [], key),
    note: t("metric_timing_note", "Recorded durations may be incomplete or overlap. Other duration covers non-model Agent records; it is not idle time."),
    diagnostics: [...(state.catalogPage?.metric_diagnostics || state.leaderboardSummary?.metric_diagnostics || []), ...(state.catalogRows || []).flatMap(row => (row.metric_diagnostics || []).map(message => `${row.source_key}: ${message}`))],
    validate: keys => { try { preflightHomeChange({ summary: { metrics: keys } }); } catch { throw new Error(t("metric_link_limit", "The link is too large. Reduce selected metrics or view conditions.")); } },
  };
}
function validateSummaryGroups(keys) {
  try { preflightHomeChange({ summary: { comparison_groups: keys } }); }
  catch { throw new Error(t("summary_group_link_limit", "The link is too large. Select fewer groups or use Select all.")); }
}


function renderLeaderboardSummary() {
  disposeLeaderboardRadar();
  const target = $("leaderboard-summary");
  if (!target) return;
  const summary = state.leaderboardSummary?.summary || null;
  const allGroups = leaderboardSummaryGroups();
  const matchedCount = Number(summary?.matched_count ?? state.catalogPage?.total ?? 0);
  const initialChecking = Boolean(
    state.leaderboardSummary?.checking
    && !Number(state.leaderboardSummary?.generation || 0),
  );
  const heading = renderSummaryHeader({ id: "leaderboard-summary", title: t("leaderboard_summary", "Leaderboard Summary"),
    scope: initialChecking ? "" : leaderboardSummaryScopeText(matchedCount), actions: renderLeaderboardSummaryActions(allGroups) });
  if (state.leaderboardSummaryLoading || state.leaderboardSummary?.checking) {
    target.innerHTML = `
      ${heading}
      <p class="leaderboard-summary-empty" aria-live="polite">${esc(t("leaderboard_summary_loading", "Calculating the complete-query summary…"))}</p>
    `;
    bindLeaderboardSummaryControls(target, null, allGroups);
    return;
  }
  if (state.leaderboardSummaryError) {
    const detail = String(state.leaderboardSummaryError);
    target.innerHTML = `
      ${heading}
      <p class="leaderboard-summary-empty" role="alert">${esc(t("leaderboard_summary_error", "The complete-query summary is unavailable."))} ${esc(detail)}</p>
    `;
    bindLeaderboardSummaryControls(target, null, allGroups);
    return;
  }
  if (!summary || matchedCount < 1) {
    target.innerHTML = `
      ${heading}
      <p class="leaderboard-summary-empty">${esc(t("leaderboard_summary_empty", "No Trials match the current conditions."))}</p>
    `;
    bindLeaderboardSummaryControls(target, null, allGroups);
    return;
  }

  const groups = comparisonGroups(allGroups, state.leaderboardSummaryComparisonGroups);
  const radar = leaderboardRadarContext(allGroups);
  target.innerHTML = `
    ${heading}
    ${!groups.length ? `<p class="leaderboard-summary-empty">${esc(t("summary_group_select", "Select at least one comparison group."))}</p>` : visibleLeaderboardSummaryDefinitions(groups).length ? renderLeaderboardSummaryTableDisclosure(groups) : `<p class="leaderboard-summary-empty">${esc(t("metric_select", "Select at least one available metric with data."))}</p>`}
    ${state.leaderboardSummaryGroupBy === "overall" || !groups.length ? "" : renderLeaderboardSummaryCharts(groups, radar)}
  `;
  bindLeaderboardSummaryControls(target, radar, allGroups);
}

function leaderboardSummaryGroups() {
  const definitions = new Map(leaderboardSummaryDefinitions().map(item => [item.key, item]));
  return listValue(state.leaderboardSummary?.summary?.groups).map(group => ({
    ...group,
    metrics: (group.metrics || []).map(row => ({ ...definitions.get(row.key), ...row })),
    label: state.leaderboardSummaryGroupBy === "overall" && group?.key === "overall"
      ? t("summary_overall", "Overall")
      : state.leaderboardSummaryGroupBy === "model" ? modelDisplayName(String(group?.label ?? "-")) : String(group?.label ?? "-"),
  }));
}

function leaderboardSummaryScopeText(count) {
  return t(
    "leaderboard_summary_scope",
    "{count} matching Trials across all pages.",
  ).replace("{count}", fmtNum(count)) + ` · ${state.catalogQuery?.metric_scope === "root" ? t("scope_root", "Main session") : t("scope_family", "Main and sub-sessions")}`;
}

function renderLeaderboardSummaryActions(groups = leaderboardSummaryGroups()) {
  const exportControl = renderSummaryExportMenu({ id: "summary", kinds: [
    { key: "xlsx", label: t("export_excel", "Export Excel") },
    { key: "bar", label: t("summary_export_bar", "Bar chart (.png)") },
    { key: "radar", label: t("summary_export_radar", "Radar chart (.png)") },
  ] });
  return `${renderLeaderboardSummaryGroupControl()}${renderSummaryGroupControl(summaryControls, groups)}${renderSummaryMetricControl(summaryControls, metricControlOptions())}${exportControl}`;
}

function renderLeaderboardSummaryGroupControl() {
  const items = [["overall", "summary_overall", "Overall"], ["agent", "agent", "Agent"], ["model", "model", "Model"], ["category", "category", "Category"], ["task", "task", "Task"], ["job", "job", "Job"], ["provider", "provider", "Provider"]].map(([key, label, fallback]) => ({ key, label: t(label, fallback) }));
  return renderSummarySegments(t("summary_group_by", "Group by"), items, state.leaderboardSummaryGroupBy, "data-summary-group-by");
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
  return renderSummaryDisclosure({ id: "leaderboard-summary-table-region", open, summary, table: open ? renderLeaderboardSummaryTable(groups) : "" });
}

function renderLeaderboardSummaryTable(groups) {
  const groupHeading = leaderboardSummaryGroupHeading(state.leaderboardSummaryGroupBy);
  const statistics = leaderboardSummaryStatistics();
  return renderTableShell({ shellClass: "leaderboard-summary-shell", tableClass: "leaderboard-summary-table", head: `<tr>
      <th ${tableValueAttributes("identity", t("summary_metric", "Metric"))}>${tableCellContent(esc(t("summary_metric", "Metric")))}</th>
      <th ${tableValueAttributes("identity", groupHeading)}>${tableCellContent(esc(groupHeading))}</th>
      <th ${tableValueAttributes("number", t("summary_count", "Count"), "num")}>${tableCellContent(esc(t("summary_count", "Count")))}</th>
      ${statistics.map(statistic => `<th ${tableValueAttributes("number", statistic.label, `num${state.leaderboardSummaryStatistic === statistic.key ? " summary-selected-stat" : ""}`)} data-summary-stat-heading="${esc(statistic.key)}">${tableCellContent(esc(statistic.label))}</th>`).join("")}
    </tr>`, body: visibleLeaderboardSummaryDefinitions(groups).map(definition => renderLeaderboardSummaryMetricGroup(definition, groups, statistics)).join("") });
}

function renderLeaderboardSummaryMetricGroup(definition, groups, statistics) {
  return groups.map((group, index) => {
    const row = group.metrics.find(metric => metric.key === definition.key);
    return `<tr data-summary-metric="${esc(definition.key)}"${index === 0 ? " data-summary-group-start" : ""}>
      ${index === 0 ? `<th ${tableValueAttributes("identity", definition.label, "summary-metric-cell")} scope="rowgroup" rowspan="${groups.length}">${tableCellContent(esc(definition.label))}</th>` : ""}
      <th ${tableValueAttributes("identity", group.label, "summary-group-cell")} scope="row">${tableCellContent(`<strong>${esc(group.label)}</strong><span>n=${fmtNum(group.count)}</span>`)}</th>
      <td ${tableValueAttributes("number", fmtNum(row?.count), "num")}>${tableCellContent(fmtNum(row?.count))}</td>
      ${statistics.map(statistic => { const value = leaderboardSummaryValue(row, statistic.value(row)); return `<td ${tableValueAttributes("number", value, `num${state.leaderboardSummaryStatistic === statistic.key ? " summary-selected-stat" : ""}`, `${value}\n${metricProvenanceHint(row?.provenance, definition.key)}`)} data-summary-stat="${esc(statistic.key)}">${tableCellContent(esc(value))}</td>`; }).join("")}
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
    ? radarContext(groups, selectedMetricDefinitions(state), selectedLeaderboardSummaryStatistic(), leaderboardSummaryValue, state.leaderboardSummaryComparisonGroups) : null;
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
  const items = [{ key: "bar", label: t("summary_bar", "Bar chart") }, { key: "radar", label: t("summary_radar", "Radar chart") }];
  return renderSummarySegments(t("summary_chart_type", "Chart"), items, state.leaderboardSummaryChartType, "data-summary-chart-type");
}

function summaryPresentationChanged(selector) {
  workspaceLocationChanged("home");
  const target = $("leaderboard-summary");
  const panel = target?.querySelector(".leaderboard-summary-chart-panel");
  if (!panel) { renderLeaderboardSummary(); return; }
  const allGroups = leaderboardSummaryGroups();
  const groups = comparisonGroups(allGroups, state.leaderboardSummaryComparisonGroups);
  const radar = leaderboardRadarContext(allGroups);
  disposeLeaderboardRadar();
  panel.outerHTML = renderLeaderboardSummaryCharts(groups, radar);
  bindToolbarMenus(target);
  bindLeaderboardSummaryChartControls(target, radar);
  updateSummaryExportControls(target);
  target.querySelectorAll("[data-summary-stat-heading],[data-summary-stat]").forEach(cell => {
    cell.classList.toggle("summary-selected-stat", (cell.dataset.summaryStatHeading || cell.dataset.summaryStat) === state.leaderboardSummaryStatistic);
  });
  target.querySelector(selector)?.focus({ preventScroll: true });
}

function renderLeaderboardSummaryStatisticControl() {
  return renderSummarySegments(t("summary_chart_statistic", "Chart statistic"), leaderboardSummaryStatistics(), state.leaderboardSummaryStatistic, "data-summary-statistic");
}

function selectedLeaderboardSummaryStatistic() {
  return leaderboardSummaryStatistics().find(statistic => statistic.key === state.leaderboardSummaryStatistic)
    || leaderboardSummaryStatistics()[0];
}

function leaderboardSummaryChartData(definition, groups, statistic) {
  return summaryBarData(definition, groups.map(group => {
    const row = group.metrics.find(metric => metric.key === definition.key);
    return { group, row, value: summaryNumber(statistic.value(row)), hint: metricProvenanceHint(row?.provenance, definition.key) };
  }), value => formatMetric(definition, value));
}

function renderLeaderboardSummaryChart(definition, groups, statistic) {
  return renderSummaryBarChart(leaderboardSummaryChartData(definition, groups, statistic), statistic.label);
}

function bindLeaderboardSummaryChartControls(target, radar) {
  target.querySelectorAll("[data-summary-chart-type]").forEach(button => button.addEventListener("click", () => {
    state.leaderboardSummaryChartType = button.dataset.summaryChartType;
    summaryPresentationChanged(`[data-summary-chart-type='${button.dataset.summaryChartType}']`);
  }));
  if (radar) bindLeaderboardRadar(target, radar);
  target.querySelectorAll("[data-summary-statistic]").forEach(button => {
    button.addEventListener("click", () => setLeaderboardSummaryStatistic(button.dataset.summaryStatistic));
  });
}

function bindLeaderboardSummaryControls(target, radar = null, groups = leaderboardSummaryGroups()) {
  if (!target?.querySelectorAll) return;
  bindToolbarMenus(target);
  bindLeaderboardSummaryChartControls(target, radar);
  bindSummaryMetricControl(target, summaryControls, () => { workspaceLocationChanged("home"); renderLeaderboardSummary(); }, metricControlOptions());
  bindSummaryGroupControl(target, summaryControls, groups, () => { workspaceLocationChanged("home"); renderLeaderboardSummary(); }, validateSummaryGroups);
  target.querySelectorAll("[data-summary-group-by]").forEach(button => {
    button.addEventListener("click", () => setLeaderboardSummaryGroupBy(button.dataset.summaryGroupBy));
  });
  target.querySelectorAll("[data-summary-table-toggle]").forEach(button => {
    button.addEventListener("click", toggleLeaderboardSummaryTable);
  });
  updateSummaryExportControls(target);
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
}

function summaryExportDisabledReason(kind) {
  const selected = comparisonGroups(leaderboardSummaryGroups(), state.leaderboardSummaryComparisonGroups);
  if (!selected.length) return t("summary_group_select", "Select at least one comparison group.");
  if (!visibleLeaderboardSummaryDefinitions(selected).length) return t("metric_select", "Select at least one available metric with data.");
  if (kind === "radar" && selectedMetricDefinitions(state).filter(item => ["higher", "lower"].includes(item.direction)).length < 3) return t("metric_radar_min", "Select at least three metrics with a direction.");
  if (kind === "xlsx") return Number(state.catalogPage?.total || 0) ? "" : t("leaderboard_summary_empty", "No Trials match the current conditions.");
  const summary = state.leaderboardSummary?.summary;
  if (state.leaderboardSummaryLoading || state.leaderboardSummary?.checking || state.leaderboardSummaryError || !summary?.matched_count || !summary.groups?.length) {
    return t("summary_export_not_ready", "Chart export requires a completed, nonempty summary.");
  }
  if (state.leaderboardSummaryGroupBy === "overall") return t("summary_export_group_required", "Select a grouping to export charts.");
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
  const allGroups = structuredClone(leaderboardSummaryGroups());
  const groups = comparisonGroups(allGroups, state.leaderboardSummaryComparisonGroups);
  const statistic = selectedLeaderboardSummaryStatistic();
  return {
    title: t("leaderboard_summary", "Leaderboard Summary"),
    subtitle: `${statistic.label} · ${leaderboardSummaryGroupHeading()}`,
    scope: leaderboardSummaryScopeText(state.leaderboardSummary.summary.matched_count),
    bars: visibleLeaderboardSummaryDefinitions(groups).map(definition => leaderboardSummaryChartData(definition, groups, statistic)),
    radar: radarContext(allGroups, selectedMetricDefinitions(state), statistic, leaderboardSummaryValue, state.leaderboardSummaryComparisonGroups),
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
  state.leaderboardSummaryComparisonGroups = null;
  state.leaderboardGroupDraft = null;
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
