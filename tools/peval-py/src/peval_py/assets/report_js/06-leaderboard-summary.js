function renderLeaderboardSummary(rows = leaderboardRows()) {
  const target = $("leaderboard-summary");
  if (!target) return;
  const visibleRows = Array.isArray(rows) ? rows : [];
  if (!visibleRows.length) {
    target.innerHTML = `
      <div class="panel-head leaderboard-summary-head">
        <div><h2 id="leaderboard-summary-title">${esc(t("leaderboard_summary", "Leaderboard Summary"))}</h2></div>
        ${renderLeaderboardSummaryActions()}
      </div>
      <p class="leaderboard-summary-empty">${esc(t("leaderboard_summary_empty", "No visible rows to summarize."))}</p>
    `;
    bindLeaderboardSummaryControls(target);
    return;
  }

  const groups = leaderboardSummaryGroups(visibleRows, state.leaderboardSummaryGroupBy);
  target.innerHTML = `
    <div class="panel-head leaderboard-summary-head">
      <div>
        <h2 id="leaderboard-summary-title">${esc(t("leaderboard_summary", "Leaderboard Summary"))}</h2>
        <p>${esc(t("leaderboard_summary_hint", "Compare one statistic at a time; expand the table for the full distribution."))}</p>
      </div>
      ${renderLeaderboardSummaryActions()}
    </div>
    ${renderLeaderboardSummaryTableDisclosure(groups)}
    ${state.leaderboardSummaryGroupBy === "overall" ? "" : renderLeaderboardSummaryCharts(groups)}
  `;
  bindLeaderboardSummaryControls(target);
}

function renderLeaderboardSummaryActions() {
  const workspaceControls = typeof renderWorkspaceViewControls === "function"
    ? renderWorkspaceViewControls()
    : "";
  return `<div class="leaderboard-summary-actions">${renderLeaderboardSummaryGroupControl()}${workspaceControls}</div>`;
}

function renderLeaderboardSummaryGroupControl() {
  return `<div class="leaderboard-summary-control leaderboard-summary-group-control">
    <span>${esc(t("summary_group_by", "Group by"))}</span>
    <div class="leaderboard-summary-segments" role="group" aria-label="${esc(t("summary_group_by", "Group by"))}">
      ${leaderboardSummaryGroupButton("overall", t("summary_overall", "Overall"))}
      ${leaderboardSummaryGroupButton("agent", t("agent", "Agent"))}
      ${leaderboardSummaryGroupButton("model", t("model", "Model"))}
    </div>
  </div>`;
}

function leaderboardSummaryGroupButton(value, label) {
  const active = state.leaderboardSummaryGroupBy === value;
  return `<button type="button" class="leaderboard-summary-segment${active ? " active" : ""}" data-summary-group-by="${esc(value)}" aria-pressed="${active}">${esc(label)}</button>`;
}

function leaderboardSummaryGroups(rows = leaderboardRows(), groupBy = state.leaderboardSummaryGroupBy) {
  const visibleRows = Array.isArray(rows) ? rows : [];
  if (groupBy === "overall") {
    return [{ key: "overall", label: t("summary_overall", "Overall"), rows: visibleRows, metrics: leaderboardSummaryRows(visibleRows) }];
  }
  const grouped = new Map();
  visibleRows.forEach(row => {
    const rawLabel = groupBy === "model" ? row?.model : agentNameFor(row);
    const label = String(rawLabel || "-");
    if (!grouped.has(label)) grouped.set(label, []);
    grouped.get(label).push(row);
  });
  return Array.from(grouped, ([label, groupRows]) => ({
    key: label,
    label,
    rows: groupRows,
    metrics: leaderboardSummaryRows(groupRows),
  })).sort((left, right) => left.label.localeCompare(right.label, undefined, { numeric: true }));
}

function leaderboardSummaryRows(rows = leaderboardRows()) {
  const visibleRows = Array.isArray(rows) ? rows : [];
  return leaderboardSummaryDefinitions().map(definition => {
    const values = visibleRows
      .map(row => summaryNumber(definition.value(row)))
      .filter(value => value !== null);
    const total = values.reduce((sum, value) => sum + value, 0);
    return {
      key: definition.key,
      label: definition.label,
      type: definition.type,
      count: values.length,
      mean: values.length ? total / values.length : null,
      distribution: leaderboardSummaryDistribution(values),
    };
  });
}

function leaderboardSummaryDefinitions() {
  return [
    { key: "duration_ms", label: t("duration", "Active Duration"), type: "duration", value: row => row?.duration_ms },
    { key: "tokens", label: t("tokens", "Tokens"), type: "number", value: row => row?.tokens },
    { key: "turns", label: t("turns", "Turns"), type: "number", value: row => row?.turns },
    { key: "model_duration_ms", label: t("model_call_duration", "Model call duration"), type: "duration", value: row => measuredModelDurationForRow(row) },
    { key: "total_tool_calls", label: t("tool_calls", "Tool Calls"), type: "number", value: row => row?.total_tool_calls },
    { key: "tool_error_rate", label: t("tool_error_rate", "Tool Error Rate"), type: "percent", value: row => rowToolErrorRate(row) },
  ];
}

function measuredModelDurationForRow(row) {
  if (hasMetricValue(row?.model_duration_ms)) return Number(row.model_duration_ms);
  const metas = listValue(state.view?.trajectory_meta);
  const index = metas.findIndex(meta => meta?.trial_key === row?.trial_key);
  if (index < 0) return null;
  const trajectory = listValue(state.view?.trajectory)[index] || {};
  const trajectorySteps = listValue(trajectory.steps);
  const metaSteps = listValue(metas[index]?.steps);
  let total = 0;
  let count = 0;
  metaSteps.forEach((step, stepIndex) => {
    if (!step || typeof step !== "object") return;
    const source = lower(trajectorySteps[stepIndex]?.source);
    if (source !== "agent" && source !== "assistant") return;
    if (lower(step.duration_source).includes("estimate")) return;
    const duration = summaryNumber(step.duration_ms);
    if (duration === null) return;
    total += duration;
    count += 1;
  });
  return count ? total : null;
}

function renderLeaderboardSummaryTableDisclosure(groups) {
  const open = Boolean(state.leaderboardSummaryTableOpen);
  const unit = state.leaderboardSummaryGroupBy === "overall"
    ? t("summary_scopes", "scope")
    : state.leaderboardSummaryGroupBy === "model"
      ? t("summary_models", "models")
      : t("summary_agents", "agents");
  const summary = `${leaderboardSummaryDefinitions().length} ${t("summary_metrics", "metrics")} · ${groups.length} ${unit}`;
  return `<div class="leaderboard-summary-table-disclosure">
    <button type="button" class="leaderboard-summary-table-toggle" data-summary-table-toggle aria-expanded="${open}" aria-controls="leaderboard-summary-table-region">
      <span><strong>${esc(t(open ? "summary_hide_table" : "summary_show_table", open ? "Hide summary table" : "Show summary table"))}</strong><small>${esc(summary)}</small></span>
      <i aria-hidden="true">${open ? "−" : "+"}</i>
    </button>
    ${open ? `<div id="leaderboard-summary-table-region">${renderLeaderboardSummaryTable(groups)}</div>` : ""}
  </div>`;
}

function renderLeaderboardSummaryTable(groups) {
  const groupHeading = state.leaderboardSummaryGroupBy === "overall"
    ? t("summary_scope", "Scope")
    : state.leaderboardSummaryGroupBy === "model"
      ? t("model", "Model")
      : t("agent", "Agent");
  const statistics = leaderboardSummaryStatistics();
  return `<div class="table-shell leaderboard-summary-shell"><div class="table-wrap"><table class="data-table leaderboard-summary-table">
    <thead><tr>
      <th>${esc(t("summary_metric", "Metric"))}</th>
      <th>${esc(groupHeading)}</th>
      <th class="num">${esc(t("summary_count", "Count"))}</th>
      ${statistics.map(statistic => `<th class="num${state.leaderboardSummaryStatistic === statistic.key ? " summary-selected-stat" : ""}" data-summary-stat-heading="${esc(statistic.key)}">${esc(statistic.label)}</th>`).join("")}
    </tr></thead>
    <tbody>${leaderboardSummaryDefinitions().map(definition => renderLeaderboardSummaryMetricGroup(definition, groups, statistics)).join("")}</tbody>
  </table></div></div>`;
}

function renderLeaderboardSummaryMetricGroup(definition, groups, statistics) {
  return groups.map((group, index) => {
    const row = group.metrics.find(metric => metric.key === definition.key);
    return `<tr data-summary-metric="${esc(definition.key)}"${index === 0 ? " data-summary-group-start" : ""}>
      ${index === 0 ? `<th class="summary-metric-cell" scope="rowgroup" rowspan="${groups.length}">${esc(definition.label)}</th>` : ""}
      <th class="summary-group-cell" scope="row"><strong>${esc(group.label)}</strong><span>n=${fmtNum(group.rows.length)}</span></th>
      <td class="num">${fmtNum(row?.count)}</td>
      ${statistics.map(statistic => `<td class="num${state.leaderboardSummaryStatistic === statistic.key ? " summary-selected-stat" : ""}" data-summary-stat="${esc(statistic.key)}">${esc(leaderboardSummaryValue(row, statistic.value(row)))}</td>`).join("")}
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
  return `<section class="leaderboard-summary-chart-panel" aria-labelledby="leaderboard-summary-chart-title">
    <div class="leaderboard-summary-chart-head">
      <div>
        <h3 id="leaderboard-summary-chart-title">${esc(statistic.label)} · ${esc(state.leaderboardSummaryGroupBy === "model" ? t("model", "Model") : t("agent", "Agent"))}</h3>
        <p>${esc(t("summary_scale_note", "Each metric has its own scale. Compare bars only within a metric."))}</p>
      </div>
      ${renderLeaderboardSummaryStatisticControl()}
    </div>
    <div class="leaderboard-summary-chart-grid">
      ${leaderboardSummaryDefinitions().map(definition => renderLeaderboardSummaryChart(definition, groups, statistic)).join("")}
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
  if (typeof bindWorkspaceViewControls === "function") bindWorkspaceViewControls(target);
}

function setLeaderboardSummaryGroupBy(value) {
  if (!["overall", "agent", "model"].includes(value)) return;
  state.leaderboardSummaryGroupBy = value;
  renderLeaderboardSummary(leaderboardRows());
}

function toggleLeaderboardSummaryTable() {
  state.leaderboardSummaryTableOpen = !state.leaderboardSummaryTableOpen;
  renderLeaderboardSummary(leaderboardRows());
}

function setLeaderboardSummaryStatistic(value) {
  if (!leaderboardSummaryStatistics().some(statistic => statistic.key === value)) return;
  state.leaderboardSummaryStatistic = value;
  renderLeaderboardSummary(leaderboardRows());
}

function leaderboardSummaryDistribution(values) {
  if (!values.length) return null;
  const ordered = [...values].sort((left, right) => left - right);
  return {
    min: ordered[0],
    q1: leaderboardSummaryPercentile(ordered, 25),
    p50: leaderboardSummaryPercentile(ordered, 50),
    q3: leaderboardSummaryPercentile(ordered, 75),
    p95: leaderboardSummaryPercentile(ordered, 95),
    max: ordered[ordered.length - 1],
  };
}

function leaderboardSummaryPercentile(ordered, percentile) {
  if (ordered.length === 1) return ordered[0];
  const position = (ordered.length - 1) * (percentile / 100);
  const lowerIndex = Math.floor(position);
  const upperIndex = Math.ceil(position);
  if (lowerIndex === upperIndex) return ordered[lowerIndex];
  return ordered[lowerIndex] + (ordered[upperIndex] - ordered[lowerIndex]) * (position - lowerIndex);
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
