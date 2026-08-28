import { $, esc, fmtMs, fmtNum, fmtPct, hasMetricValue, listValue, state, t } from "./runtime.js";
import { tableCellContent, tableValueAttributes } from "./data-tables.js";
import { exportLeaderboardSummary, loadLeaderboardSummary } from "./serve-catalog.js";
import { bindWorkspaceViewControls, renderWorkspaceViewControls } from "./workspace-views.js";

function renderLeaderboardSummary() {
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

  const groups = listValue(summary.groups).map(group => ({
    ...group,
    label: state.leaderboardSummaryGroupBy === "overall" && group?.key === "overall"
      ? t("summary_overall", "Overall")
      : String(group?.label ?? "-"),
  }));
  target.innerHTML = `
    ${heading}
    ${renderLeaderboardSummaryTableDisclosure(groups)}
    ${state.leaderboardSummaryGroupBy === "overall" ? "" : renderLeaderboardSummaryCharts(groups)}
  `;
  bindLeaderboardSummaryControls(target);
}

function leaderboardSummaryScopeText(count) {
  return t(
    "leaderboard_summary_scope",
    "{count} matching Trials across all pages.",
  ).replace("{count}", fmtNum(count));
}

function renderLeaderboardSummaryActions() {
  const workspaceControls = renderWorkspaceViewControls();
  const exportControl = `<button type="button" class="action-button leaderboard-summary-export" data-summary-export-xlsx ${Number(state.catalogPage?.total || 0) ? "" : "disabled"}>${esc(t("export_excel", "Export Excel"))}</button>`;
  return `<div class="leaderboard-summary-actions">${renderLeaderboardSummaryGroupControl()}${workspaceControls}${exportControl}</div>`;
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

function leaderboardSummaryDefinitions() {
  return [
    { key: "score", label: t("reward", "Reward"), type: "number" },
    { key: "duration_ms", label: t("duration", "Active Duration"), type: "duration" },
    { key: "ttft_ms", label: t("avg_ttft", "Avg TTFT"), type: "duration" },
    { key: "tps", label: t("decode_tps", "Decode TPS"), type: "number" },
    { key: "tokens", label: t("tokens", "Tokens"), type: "number" },
    { key: "cache_hit_rate", label: t("cache_hit", "Cache Hit"), type: "percent" },
    { key: "turns", label: t("turns", "Turns"), type: "number" },
    { key: "model_duration_ms", label: t("model_call_duration", "Model call duration"), type: "duration" },
    { key: "total_tool_calls", label: t("tool_calls", "Tool Calls"), type: "number" },
    { key: "tool_error_rate", label: t("tool_error_rate", "Tool Error Rate"), type: "percent" },
  ];
}

function visibleLeaderboardSummaryDefinitions(groups) {
  return leaderboardSummaryDefinitions().filter(definition => listValue(groups).some(group => (
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

function renderLeaderboardSummaryCharts(groups) {
  const statistic = selectedLeaderboardSummaryStatistic();
  const groupHeading = leaderboardSummaryGroupHeading(state.leaderboardSummaryGroupBy);
  return `<section class="leaderboard-summary-chart-panel" aria-labelledby="leaderboard-summary-chart-title">
    <div class="leaderboard-summary-chart-head">
      <div>
        <h3 id="leaderboard-summary-chart-title">${esc(statistic.label)} · ${esc(groupHeading)}</h3>
        <p>${esc(t("summary_scale_note", "Each metric has its own scale. Compare bars only within a metric."))}</p>
      </div>
      ${renderLeaderboardSummaryStatisticControl()}
    </div>
    <div class="leaderboard-summary-chart-grid">
      ${visibleLeaderboardSummaryDefinitions(groups).map(definition => renderLeaderboardSummaryChart(definition, groups, statistic)).join("")}
    </div>
  </section>`;
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

function renderLeaderboardSummaryChart(definition, groups, statistic) {
  const values = groups.map(group => {
    const row = group.metrics.find(metric => metric.key === definition.key);
    return { group, row, value: statistic.value(row) };
  });
  const maximum = Math.max(0, ...values.map(item => summaryNumber(item.value) ?? 0));
  return `<section class="leaderboard-summary-chart" data-summary-chart="${esc(definition.key)}">
    <div class="leaderboard-summary-chart-card-head"><h4>${esc(definition.label)}</h4><span>${esc(statistic.label)}</span></div>
    <div class="leaderboard-summary-bar-list">${values.map(item => {
      const numericValue = summaryNumber(item.value);
      const formatted = leaderboardSummaryValue(item.row, numericValue);
      const width = maximum > 0 && numericValue !== null ? Math.max(2, (numericValue / maximum) * 100) : 0;
      const ariaLabel = `${item.group.label}; ${definition.label}; ${statistic.label} ${formatted}; n=${item.row?.count || 0}`;
      return `<div class="leaderboard-summary-bar" role="img" aria-label="${esc(ariaLabel)}">
        <span class="leaderboard-summary-bar-label" title="${esc(item.group.label)}">${esc(item.group.label)}</span>
        <span class="leaderboard-summary-bar-track"><i style="width:${Number(width.toFixed(2))}%"></i></span>
        <span class="leaderboard-summary-bar-value"><strong>${esc(formatted)}</strong><small>n=${fmtNum(item.row?.count || 0)}</small></span>
      </div>`;
    }).join("")}</div>
  </section>`;
}

function bindLeaderboardSummaryControls(target) {
  if (!target?.querySelectorAll) return;
  target.querySelectorAll("[data-summary-group-by]").forEach(button => {
    button.addEventListener("click", () => setLeaderboardSummaryGroupBy(button.dataset.summaryGroupBy));
  });
  target.querySelectorAll("[data-summary-table-toggle]").forEach(button => {
    button.addEventListener("click", toggleLeaderboardSummaryTable);
  });
  target.querySelectorAll("[data-summary-statistic]").forEach(button => {
    button.addEventListener("click", () => setLeaderboardSummaryStatistic(button.dataset.summaryStatistic));
  });
  target.querySelectorAll("[data-summary-export-xlsx]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      exportLeaderboardSummary();
    });
  });
  bindWorkspaceViewControls(target);
}

async function setLeaderboardSummaryGroupBy(value) {
  if (!["overall", "agent", "model", "category", "task", "job", "provider"].includes(value)) return;
  state.leaderboardSummaryGroupBy = value;
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
  renderLeaderboardSummary();
}

function setLeaderboardSummaryStatistic(value) {
  if (!leaderboardSummaryStatistics().some(statistic => statistic.key === value)) return;
  state.leaderboardSummaryStatistic = value;
  renderLeaderboardSummary();
}

function leaderboardSummaryValue(row, value) {
  if (!hasMetricValue(value)) return "-";
  if (row?.type === "duration") return fmtMs(value);
  if (row?.type === "percent") return fmtPct(value);
  return fmtNum(value);
}

function summaryNumber(value) {
  if (!hasMetricValue(value)) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}
export {
  bindLeaderboardSummaryControls,
  leaderboardSummaryDefinitions,
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
