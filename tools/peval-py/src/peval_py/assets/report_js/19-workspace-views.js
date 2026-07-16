function workspaceViews() {
  return listValue(state.workspaceViews)
    .filter(view => view && typeof view.name === "string" && view.name.trim())
    .map(view => ({
      ...view,
      name: String(view.name),
      filters: workspaceViewFilters(view.filters),
      group_by: ["overall", "agent", "model"].includes(view.group_by) ? view.group_by : "agent",
      notes: typeof view.notes === "string" ? view.notes : "",
    }))
    .sort((left, right) => left.name.localeCompare(right.name, undefined, { numeric: true, sensitivity: "base" }));
}

function workspaceViewFilters(value) {
  const filters = value && typeof value === "object" ? value : {};
  return {
    state: normalizeServeSourceMode(filters.state),
    search: typeof filters.search === "string" ? filters.search : "",
    tags: listValue(filters.tags).map(String),
    agents: listValue(filters.agents).map(String),
    models: listValue(filters.models).map(String),
    results: listValue(filters.results).map(String),
  };
}

function workspaceViewForName(name) {
  return workspaceViews().find(view => view.name === String(name || "")) || null;
}

function workspaceViewSummaryForName(name) {
  return listValue(state.workspaceViewSummaries).find(view => view?.name === name) || null;
}

function workspaceViewMessage(key, fallback, values = {}) {
  let message = String(t(key, fallback));
  Object.entries(values).forEach(([name, value]) => {
    message = message.replaceAll(`{${name}}`, String(value));
  });
  return message;
}

function renderWorkspaceViewControls() {
  if (!serveMode()) return "";
  return `<div class="workspace-view-controls" data-workspace-view-control>
    <button type="button" class="step-toggle-button leaderboard-summary-save" data-view-save>${esc(t("save_view", "Save view"))}</button>
  </div>`;
}

function bindWorkspaceViewControls(target) {
  if (!serveMode() || !target?.querySelectorAll) return;
  target.querySelectorAll("[data-view-save]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      openWorkspaceViewSaveDialog(button);
    });
  });
  target.querySelectorAll("[data-view-apply]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      applyWorkspaceView(button.dataset.viewApply);
    });
  });
  target.querySelectorAll("[data-view-table-toggle]").forEach(button => {
    button.addEventListener("click", () => toggleWorkspaceViewTable(button.dataset.viewTableToggle));
  });
  target.querySelectorAll("[data-view-cancel-application]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      cancelWorkspaceViewApplication();
    });
  });
}

function bindWorkspaceViewDialog() {
  if (!serveMode()) return;
  const dialog = document.querySelector?.("[data-view-save-dialog]");
  if (!dialog || dialog.dataset?.bound === "true") return;
  if (dialog.dataset) dialog.dataset.bound = "true";
  dialog.querySelectorAll?.("[data-view-save-cancel]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      closeWorkspaceViewSaveDialog();
    });
  });
  dialog.querySelector?.("[data-view-save-form]")?.addEventListener("submit", event => {
    event.preventDefault();
    saveWorkspaceView(dialog);
  });
  dialog.addEventListener?.("click", event => {
    if (event.target === dialog) closeWorkspaceViewSaveDialog();
  });
}

function openWorkspaceViewSaveDialog(opener) {
  const dialog = document.querySelector?.("[data-view-save-dialog]");
  if (!dialog) return;
  bindWorkspaceViewDialog();
  state.workspaceViewSave.opener = opener || null;
  dialog.hidden = false;
  document.body?.classList?.add("view-save-open");
  const nameInput = dialog.querySelector?.("[data-view-name-input]");
  if (nameInput) {
    nameInput.value = "";
    focusSoon(nameInput);
  }
  const notesInput = dialog.querySelector?.("[data-view-notes-input]");
  if (notesInput) notesInput.value = "";
  renderWorkspaceViewCurrentConfiguration(dialog);
}

function closeWorkspaceViewSaveDialog(options = {}) {
  const dialog = document.querySelector?.("[data-view-save-dialog]");
  if (!dialog || dialog.hidden) return false;
  dialog.hidden = true;
  document.body?.classList?.remove("view-save-open");
  const opener = state.workspaceViewSave.opener;
  state.workspaceViewSave.opener = null;
  if (options.restoreFocus !== false) focusSoon(opener);
  return true;
}

function currentWorkspaceViewFilters() {
  const query = state.catalogQuery || {};
  return workspaceViewFilters({
    state: query.state,
    search: query.search,
    tags: query.tags,
    agents: query.agents,
    models: query.models,
    results: query.results,
  });
}

function renderWorkspaceViewCurrentConfiguration(dialog) {
  const target = dialog?.querySelector?.("[data-view-current-configuration]");
  if (!target) return;
  const filters = currentWorkspaceViewFilters();
  const fields = [];
  if (filters.state !== "active") fields.push([t("source", "Source"), workspaceViewStateLabel(filters.state)]);
  if (filters.search) fields.push([t("search_sessions", "Search sessions"), filters.search]);
  if (filters.tags.length) fields.push([t("tags", "Tags"), filters.tags.join(", ")]);
  if (filters.agents.length) fields.push([t("agent", "Agent"), filters.agents.join(", ")]);
  if (filters.models.length) fields.push([t("model", "Model"), filters.models.join(", ")]);
  if (filters.results.length) fields.push([t("result", "Result"), filters.results.map(statusLabel).join(", ")]);
  fields.push([t("summary_group_by", "Group by"), workspaceViewGroupByLabel(state.leaderboardSummaryGroupBy)]);
  target.innerHTML = fields.map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join("");
}

function workspaceViewStateLabel(stateValue) {
  if (stateValue === "archived") return t("serve_archived", "archived");
  if (stateValue === "all") return t("serve_all_sessions", "All sessions");
  return t("serve_active", "active");
}

function workspaceViewFilterConfig(filters = currentWorkspaceViewFilters()) {
  const compact = {};
  if (filters.state !== "active") compact.state = filters.state;
  if (filters.search) compact.search = filters.search;
  if (filters.tags.length) compact.tags = [...filters.tags];
  if (filters.agents.length) compact.agents = [...filters.agents];
  if (filters.models.length) compact.models = [...filters.models];
  if (filters.results.length) compact.results = [...filters.results];
  return compact;
}

async function saveWorkspaceView(dialog) {
  const name = String(dialog.querySelector?.("[data-view-name-input]")?.value || "").trim();
  const notes = String(dialog.querySelector?.("[data-view-notes-input]")?.value || "");
  const payload = {
    name,
    filters: workspaceViewFilterConfig(),
    group_by: state.leaderboardSummaryGroupBy,
    notes,
    overwrite: false,
  };
  try {
    let response;
    try {
      response = await serveApi("/api/views", { method: "POST", body: payload });
    } catch (error) {
      if (!String(error?.message || error).includes("already exists")) throw error;
      const prompt = workspaceViewMessage("view_overwrite_confirm", "Replace the saved view {name}?", { name });
      if (typeof window.confirm === "function" && !window.confirm(prompt)) return;
      response = await serveApi("/api/views", { method: "POST", body: { ...payload, overwrite: true } });
    }
    state.workspaceViews = listValue(response?.views);
    state.workspaceViewSummaries = [];
    state.workspaceViewsLoaded = true;
    state.workspaceViewsRefreshVersion += 1;
    renderWorkspaceViewRail();
    closeWorkspaceViewSaveDialog();
    await refreshWorkspaceViews();
    setServeStatus(t("view_saved", "View saved"));
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  }
}

async function refreshWorkspaceViews() {
  if (!serveMode()) return;
  state.workspaceViewsRefreshQueued = true;
  if (state.workspaceViewsRefreshPromise) return state.workspaceViewsRefreshPromise;
  state.workspaceViewsLoading = true;
  state.workspaceViewsRefreshPromise = (async () => {
    while (state.workspaceViewsRefreshQueued) {
      state.workspaceViewsRefreshQueued = false;
      const revision = state.workspaceViewsRefreshVersion;
      try {
        const catalog = await serveApi("/api/views");
        if (revision !== state.workspaceViewsRefreshVersion) {
          state.workspaceViewsRefreshQueued = true;
          continue;
        }
        const views = listValue(catalog?.views);
        let summaries = [];
        let generation = Number(state.catalogPage?.generation || 0);
        if (views.length) {
          const summaryPayload = await serveApi("/api/views/summary");
          if (revision !== state.workspaceViewsRefreshVersion) {
            state.workspaceViewsRefreshQueued = true;
            continue;
          }
          summaries = listValue(summaryPayload?.views);
          generation = Number(summaryPayload?.generation || 0);
        }
        state.workspaceViews = views;
        state.workspaceViewSummaries = summaries;
        state.workspaceViewsLoaded = true;
        state.workspaceViewSummaryGeneration = generation;
        pruneWorkspaceViewState();
        renderWorkspaceViewRail();
        if ($("leaderboard-summary")) renderLeaderboardSummary(leaderboardRows());
      } catch (error) {
        if (revision === state.workspaceViewsRefreshVersion) setServeStatus(error.message || String(error), true);
      }
    }
  })().finally(() => {
    state.workspaceViewsLoading = false;
    state.workspaceViewsRefreshPromise = null;
    if (state.workspaceViewsRefreshQueued) return refreshWorkspaceViews();
  });
  return state.workspaceViewsRefreshPromise;
}

function pruneWorkspaceViewState() {
  const names = new Set(workspaceViews().map(view => view.name));
  state.workspaceViewTableOpen = new Set(
    Array.from(state.workspaceViewTableOpen).filter(name => names.has(name))
  );
  if (state.workspaceAppliedViewName && !names.has(state.workspaceAppliedViewName)) {
    state.workspaceAppliedViewName = null;
  }
}

function renderWorkspaceViewRail() {
  const target = $("workspace-views");
  if (!target) return;
  const views = workspaceViews();
  const visible = views.length >= 1;
  target.hidden = !visible;
  document.body?.classList?.toggle("workspace-views-open", visible);
  if (!visible) {
    target.innerHTML = "";
    return;
  }
  target.innerHTML = `<div class="workspace-views-head"><div><h2>${esc(t("saved_views", "Saved views"))}</h2><p>${esc(t("summary_scale_note", "Each metric has its own scale. Compare bars only within a metric."))}</p></div>
    <button type="button" class="step-toggle-button workspace-view-cancel" data-view-cancel-application ${state.workspaceAppliedViewName ? "" : "disabled"}>${esc(t("cancel_view_application", "Cancel application"))}</button></div>
    <div class="workspace-view-list">${views.map(renderWorkspaceViewCard).join("")}</div>`;
  bindWorkspaceViewControls(target);
}

function renderWorkspaceViewCard(view) {
  const summary = workspaceViewSummaryForName(view.name) || { matched_count: 0, groups: [] };
  const matchedCount = Number(summary.matched_count || 0);
  const filters = workspaceViewFilters(view.filters);
  const applied = state.workspaceAppliedViewName === view.name;
  return `<article class="workspace-view-card leaderboard-summary${applied ? " applied" : ""}" data-workspace-view="${esc(view.name)}">
    <header class="workspace-view-card-head panel-head leaderboard-summary-head">
      <div><h3>${esc(view.name)}</h3><p>${esc(workspaceViewMessage("saved_view_matches", "{count} matching sessions", { count: fmtNum(matchedCount) }))}</p></div>
      <button type="button" class="step-toggle-button" data-view-apply="${esc(view.name)}" ${applied ? "disabled" : ""}>${esc(t("apply", "Apply"))}</button>
    </header>
    ${renderWorkspaceViewFilters(filters, view.group_by)}
    ${view.notes ? `<div class="note-body workspace-view-notes">${renderMarkdown(view.notes)}</div>` : ""}
    ${matchedCount ? `${renderWorkspaceViewTableDisclosure(view, summary)}${renderWorkspaceViewCharts(summary, view.group_by)}` : `<p class="workspace-view-empty">${esc(t("saved_view_empty", "No matching sessions."))}</p>`}
  </article>`;
}

function renderWorkspaceViewFilters(filters, groupBy) {
  const selected = [
    filters.state !== "active" ? `${t("source", "Source")}: ${workspaceViewStateLabel(filters.state)}` : "",
    filters.search ? `${t("search", "Search")}: ${filters.search}` : "",
    filters.tags.length ? `${t("tags", "Tags")}: ${filters.tags.join(", ")}` : "",
    filters.agents.length ? `${t("agent", "Agent")}: ${filters.agents.join(", ")}` : "",
    filters.models.length ? `${t("model", "Model")}: ${filters.models.join(", ")}` : "",
    filters.results.length ? `${t("result", "Result")}: ${filters.results.join(", ")}` : "",
    `${t("summary_group_by", "Group by")}: ${workspaceViewGroupByLabel(groupBy)}`,
  ].filter(Boolean);
  return `<p class="workspace-view-filters">${esc(selected.join(" · ") || t("summary_overall", "Overall"))}</p>`;
}

function workspaceViewGroupByLabel(groupBy) {
  if (groupBy === "model") return t("model", "Model");
  if (groupBy === "agent") return t("agent", "Agent");
  return t("summary_overall", "Overall");
}

function workspaceViewGroupLabel(group) {
  return group?.key === "overall" ? t("summary_overall", "Overall") : String(group?.label || "-");
}

function renderWorkspaceViewTableDisclosure(view, summary) {
  const open = state.workspaceViewTableOpen.has(view.name);
  const groups = listValue(summary.groups);
  const unit = view.group_by === "overall"
    ? t("summary_scopes", "scope")
    : view.group_by === "model"
      ? t("summary_models", "models")
      : t("summary_agents", "agents");
  const description = `${leaderboardSummaryDefinitions().length} ${t("summary_metrics", "metrics")} · ${groups.length} ${unit}`;
  const regionId = `workspace-view-table-${encodeURIComponent(view.name)}`;
  return `<div class="leaderboard-summary-table-disclosure workspace-view-table-disclosure">
    <button type="button" class="leaderboard-summary-table-toggle" data-view-table-toggle="${esc(view.name)}" aria-expanded="${open}" aria-controls="${esc(regionId)}">
      <span><strong>${esc(t(open ? "summary_hide_table" : "summary_show_table", open ? "Hide summary table" : "Show summary table"))}</strong><small>${esc(description)}</small></span>
      <i aria-hidden="true">${open ? "−" : "+"}</i>
    </button>
    ${open ? `<div id="${esc(regionId)}">${renderWorkspaceViewTable(summary, view.group_by)}</div>` : ""}
  </div>`;
}

function renderWorkspaceViewTable(summary, groupBy) {
  const groups = listValue(summary.groups);
  const statistics = leaderboardSummaryStatistics();
  const groupHeading = groupBy === "model" ? t("model", "Model") : groupBy === "agent" ? t("agent", "Agent") : t("summary_scope", "Scope");
  return `<div class="table-shell leaderboard-summary-shell workspace-view-table-shell"><div class="table-wrap"><table class="data-table leaderboard-summary-table workspace-view-table">
    <thead><tr><th>${esc(t("summary_metric", "Metric"))}</th><th>${esc(groupHeading)}</th><th class="num">${esc(t("summary_count", "Count"))}</th>${statistics.map(statistic => `<th class="num">${esc(statistic.label)}</th>`).join("")}</tr></thead>
    <tbody>${leaderboardSummaryDefinitions().map(definition => groups.map((group, index) => {
      const metric = listValue(group.metrics).find(item => item?.key === definition.key);
      return `<tr${index === 0 ? " data-summary-group-start" : ""}>${index === 0 ? `<th class="summary-metric-cell" scope="rowgroup" rowspan="${groups.length}">${esc(definition.label)}</th>` : ""}<th class="summary-group-cell" scope="row"><strong>${esc(workspaceViewGroupLabel(group))}</strong><span>n=${fmtNum(group.count)}</span></th><td class="num">${fmtNum(metric?.count)}</td>${statistics.map(statistic => `<td class="num">${esc(leaderboardSummaryValue(metric, statistic.value(metric)))}</td>`).join("")}</tr>`;
    }).join("")).join("")}</tbody>
  </table></div></div>`;
}

function toggleWorkspaceViewTable(name) {
  const view = workspaceViewForName(name);
  if (!view) return;
  if (state.workspaceViewTableOpen.has(view.name)) state.workspaceViewTableOpen.delete(view.name);
  else state.workspaceViewTableOpen.add(view.name);
  renderWorkspaceViewRail();
}

function renderWorkspaceViewCharts(summary, groupBy) {
  const groups = listValue(summary.groups);
  const statistic = leaderboardSummaryStatistics()[0];
  const groupLabel = groupBy === "model" ? t("model", "Model") : groupBy === "agent" ? t("agent", "Agent") : t("summary_scope", "Scope");
  return `<section class="workspace-view-charts" aria-label="${esc(`${statistic.label} · ${groupLabel}`)}">
    <div class="workspace-view-chart-head"><strong>${esc(`${statistic.label} · ${groupLabel}`)}</strong></div>
    <div class="workspace-view-chart-grid">${leaderboardSummaryDefinitions().map(definition => renderWorkspaceViewChart(definition, groups, statistic)).join("")}</div>
  </section>`;
}

function renderWorkspaceViewChart(definition, groups, statistic) {
  const values = groups.map(group => {
    const metric = listValue(group.metrics).find(item => item?.key === definition.key);
    return { group, metric, value: statistic.value(metric) };
  });
  const maximum = Math.max(0, ...values.map(item => summaryNumber(item.value) ?? 0));
  return `<section class="workspace-view-chart" data-view-chart="${esc(definition.key)}"><h4>${esc(definition.label)}</h4><div class="leaderboard-summary-bar-list">${values.map(item => {
    const numeric = summaryNumber(item.value);
    const formatted = leaderboardSummaryValue(item.metric, numeric);
    const width = maximum > 0 && numeric !== null ? Math.max(2, (numeric / maximum) * 100) : 0;
    return `<div class="leaderboard-summary-bar" role="img" aria-label="${esc(`${workspaceViewGroupLabel(item.group)}; ${definition.label}; ${statistic.label} ${formatted}; n=${item.metric?.count || 0}`)}"><span class="leaderboard-summary-bar-label" title="${esc(workspaceViewGroupLabel(item.group))}">${esc(workspaceViewGroupLabel(item.group))}</span><span class="leaderboard-summary-bar-track"><i style="width:${Number(width.toFixed(2))}%"></i></span><span class="leaderboard-summary-bar-value"><strong>${esc(formatted)}</strong><small>n=${fmtNum(item.metric?.count || 0)}</small></span></div>`;
  }).join("")}</div></section>`;
}

async function applyWorkspaceView(name) {
  const view = workspaceViewForName(name);
  if (!view || !serveMode()) return;
  const filters = workspaceViewFilters(view.filters);
  closeOpenSubmenus();
  state.rowSelection.clear();
  state.sourceSelection.clear();
  state.selectedSourceKey = null;
  state.selectedArtifactRevision = null;
  state.selectedTrial = null;
  state.selectedStep = null;
  state.leaderboardSummaryGroupBy = view.group_by;
  state.leaderboardSummaryTableOpen = false;
  state.leaderboardSummaryStatistic = "mean";
  state.workspaceAppliedViewName = view.name;
  state.workspaceViewTableOpen.clear();
  state.search.query = filters.search;
  state.search.scope = "all";
  state.search.normalSourceMode = filters.state;
  const controls = tableControls("leaderboard");
  controls.sort = "finished_at_ms";
  controls.direction = "desc";
  controls.filters = {
    source_tags: [...filters.tags],
    agent: [...filters.agents],
    model: [...filters.models],
    status: [...filters.results],
  };
  renderWorkspaceViewRail();
  await loadCatalogPage({
    state: filters.state,
    page: 1,
    page_size: 100,
    search: filters.search,
    sort: "last_turn_end",
    direction: "desc",
    tags: filters.tags,
    agents: filters.agents,
    models: filters.models,
    results: filters.results,
  }, { force: true });
}

async function cancelWorkspaceViewApplication() {
  if (!serveMode() || !state.workspaceAppliedViewName) return;
  state.workspaceAppliedViewName = null;
  state.workspaceViewTableOpen.clear();
  state.rowSelection.clear();
  state.sourceSelection.clear();
  state.selectedSourceKey = null;
  state.selectedArtifactRevision = null;
  state.selectedTrial = null;
  state.selectedStep = null;
  state.leaderboardSummaryGroupBy = "agent";
  state.leaderboardSummaryTableOpen = false;
  state.leaderboardSummaryStatistic = "mean";
  state.search.query = "";
  state.search.scope = "visible";
  state.search.normalSourceMode = "active";
  const controls = tableControls("leaderboard");
  controls.sort = "finished_at_ms";
  controls.direction = "desc";
  controls.filters = {
    source_tags: [],
    agent: [],
    model: [],
    status: [],
  };
  renderWorkspaceViewRail();
  await loadCatalogPage({
    state: "active",
    page: 1,
    page_size: 100,
    search: "",
    sort: "last_turn_end",
    direction: "desc",
    tags: [],
    agents: [],
    models: [],
    results: [],
  }, { force: true });
}
