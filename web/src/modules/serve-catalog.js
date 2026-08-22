import { WORKSPACE_SNAPSHOT, adminMode, applySessionSearch, esc, hasMetricValue, isAnalysisArtifactPath, listValue, lower, normalizeServeSourceMode, render, renderComparison, renderComparisonPanels, selectedIndex, selectedKey, serveMode, state, synthesizedReportRow, t, workspaceSnapshotMode } from "./runtime.js";
import { applyDataTableControls, currentLeaderboardColumnLayout, filterValues, leaderboardColumns, renderLeaderboardColumnControls, renderLeaderboardExportControls, tableControls } from "./data-tables.js";
import { downloadBlob, firstUserStepSelection } from "./export.js";
import { renderServeSourceStateControls, serveSourceModeStatusText } from "./source-state-controls.js";
import { emptyServeReport, hideServeNotice, reloadExpiredAdminSession, serveApi, setServeStatus } from "./serve-effects.js";
import { refreshWorkspaceReports, renderAttachWorkspaceReportAction } from "./workspace-reports.js";
import { browserWorkspaceViewDefinitions, clearWorkspaceViewConditions, refreshWorkspaceViews, workspaceViewQueryPayload, workspaceViewRows, workspaceViews } from "./workspace-views.js";

function reportRows() {
  if (serveMode() && (state.catalogRows.length || state.catalogPage.generation)) return listValue(state.catalogRows);
  const trajectories = listValue(state.view?.trajectory);
  const metas = listValue(state.view?.trajectory_meta);
  return metas
    .map((meta, index) => synthesizedReportRow(trajectories[index] || {}, meta, index))
    .filter(row => row.trial_key);
}

function normalizeCatalogRow(row) {
  const sourceKey = String(row?.source_key || "");
  return {
    ...row,
    artifact_trial_key: row?.trial_key || null,
    trial_key: sourceKey,
    source_key: sourceKey,
    step_outline: catalogStepOutline(row?.step_outline),
    session_id: row?.trial_session_id || row?.session_id || "-",
    finished_at_ms: row?.last_turn_finished_at_ms,
    source_active: row?.active !== false,
    status: row?.status || row?.last_status || "unknown"
  };
}

function catalogStepOutline(value) {
  return listValue(value).flatMap(item => {
    if (!item || item.step_id === null || item.step_id === undefined) return [];
    const rawSource = lower(item.source);
    const source = rawSource === "assistant" ? "agent" : ["system", "user", "agent"].includes(rawSource) ? rawSource : "unknown";
    const outline = { step_id: item.step_id, source };
    if (hasMetricValue(item.duration_ms)) outline.duration_ms = Number(item.duration_ms);
    return [outline];
  });
}

function leaderboardRows() {
  if (serveMode()) return reportRows();
  return applyDataTableControls("leaderboard", applySessionSearch(reportRows()), leaderboardColumns(), reportRows());
}

function rowAnalysisCount(row) {
  if (row?.analysis_count !== null && row?.analysis_count !== undefined) {
    const value = Number(row.analysis_count);
    return Number.isFinite(value) ? Math.max(0, Math.min(2, Math.trunc(value))) : 0;
  }
  const analysis = (state.view?.annotations?.analysis || [])
    .find(item => item?.trial_key === row?.trial_key);
  if (!analysis) return 0;
  let harbor = false;
  let workspace = false;
  listValue(analysis.markdown_reports).forEach(report => {
    if (!String(report?.markdown || "").trim()) return;
    if (report?.source === "harbor_trial") harbor = true;
    else workspace = true;
  });
  if (String(analysis.md_report || "").trim()) workspace = true;
  const relativePaths = analysis.relative_paths;
  if (relativePaths && typeof relativePaths === "object"
      && [relativePaths.md, relativePaths.json].some(isAnalysisArtifactPath)) {
    workspace = true;
  }
  if (isAnalysisArtifactPath(analysis.relative_path)) workspace = true;
  return Number(harbor) + Number(workspace);
}

function trialIndexFor(trialKey) {
  if (serveMode() && state.selectedSourceKey && trialKey === state.selectedSourceKey) return 0;
  const metas = state.view?.trajectory_meta || [];
  return metas.findIndex(meta => meta.trial_key === trialKey);
}

function trajectoryFor(trialKey) {
  const index = trialIndexFor(trialKey);
  if (serveMode() && index < 0) return { steps: [] };
  return (state.view?.trajectory || [])[index >= 0 ? index : selectedIndex()] || { steps: [] };
}

function metaFor(trialKey) {
  const metas = state.view?.trajectory_meta || [];
  const index = trialIndexFor(trialKey);
  if (serveMode() && index < 0) return { steps: [] };
  return metas[index >= 0 ? index : selectedIndex()] || { steps: [] };
}

function sourceForTrialKey(trialKey) {
  if (workspaceSnapshotMode()) {
    const sourceKey = Object.entries(WORKSPACE_SNAPSHOT?.source_trial_keys || {})
      .find(([_key, reportTrialKey]) => String(reportTrialKey) === String(trialKey))?.[0];
    return listValue(state.serveSources).find(source => source?.source_key === sourceKey) || null;
  }
  if (!serveMode()) return null;
  const direct = listValue(state.serveSources).find(source => source?.source_key === trialKey);
  if (direct) return direct;
  if (state.selectedSourceKey) {
    return listValue(state.serveSources).find(source => source?.source_key === state.selectedSourceKey) || null;
  }
  return null;
}

function sourceKeyForTrialKey(trialKey) {
  if (workspaceSnapshotMode()) return sourceForTrialKey(trialKey)?.source_key || null;
  if (serveMode() && listValue(state.serveSources).some(source => source?.source_key === trialKey)) return trialKey;
  return sourceForTrialKey(trialKey)?.source_key || state.selectedSourceKey || null;
}

function trialKeyForServeSource(sourceKey, view = state.view) {
  if (!sourceKey || sourceKey !== state.selectedSourceKey) return null;
  return listValue(view?.trajectory_meta)[0]?.trial_key || null;
}

function sourceForTrialIndex(index) {
  if (workspaceSnapshotMode()) return index >= 0 ? listValue(state.serveSources)[index] || null : null;
  if (!serveMode() || index < 0) return null;
  return listValue(state.serveSources).find(source => source?.source_key === state.selectedSourceKey) || null;
}

function syncSelectionWithVisibleRows(rows) {
  if (serveMode()) {
    if (!rows.length || !state.selectedSourceKey) state.selectedStep = null;
    return;
  }
  const allRows = reportRows();
  if (!allRows.length) return;
  const key = selectedKey();
  if (rows.length && !rows.some(row => row.trial_key === key)) {
    state.selectedTrial = rows[0].trial_key;
    state.selectedStep = null;
  }
}

function visibleSelectedSourceKeys(rows = leaderboardRows()) {
  return Array.from(new Set(
    listValue(rows)
      .map(row => String(row?.source_key || row?.trial_key || ""))
      .filter(key => key && state.rowSelection.has(key)),
  ));
}

function filterOptions(column, rows) {
  if (!serveMode()) {
    const values = rows.flatMap(row => filterValues(row, column));
    return Array.from(new Set(values)).sort((left, right) => left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" }));
  }
  const facetKey = ({ source_category: "categories", source_tags: "tags", agent: "agents", model: "models", task_name: "tasks", job_name: "jobs", model_provider: "providers", status: "results" })[column.key];
  if (!facetKey) {
    const values = rows.flatMap(row => filterValues(row, column));
    return Array.from(new Set(values)).sort((left, right) => left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" }));
  }
  return listValue(state.catalogPage?.facets?.[facetKey]).map(item => String(item?.value || "")).filter(Boolean);
}

function renderLeaderboardPanelControls(rows) {
  if (workspaceSnapshotMode()) {
    return `<div class="leaderboard-actions"><div class="leaderboard-action-row">${renderLeaderboardColumnControls(rows)}</div></div>`;
  }
  if (!serveMode()) return "";
  const selectedCount = state.rowSelection.size;
  return `<div class="leaderboard-actions">
    <div class="leaderboard-action-row">${renderServeSourceStateControls(rows)}${renderAttachWorkspaceReportAction(rows)}${renderLeaderboardColumnControls(rows)}${renderLeaderboardExportControls()}</div>
    <div class="catalog-page-controls" data-catalog-page-controls>
      <button type="button" class="action-button icon-only" data-catalog-prev aria-label="${esc(t("previous", "Previous"))}" ${state.catalogPage.page <= 1 ? "disabled" : ""}>‹</button>
      <span>${esc(catalogPageLabel())}</span>
      <button type="button" class="action-button icon-only" data-catalog-next aria-label="${esc(t("next", "Next"))}" ${catalogPageEnd() >= state.catalogPage.total ? "disabled" : ""}>›</button>
      <span>${esc(String(t("selected_count", "{count} selected")).replace("{count}", String(selectedCount)))}</span>
      <button type="button" class="action-button" data-catalog-clear-conditions ${leaderboardConditionsAreDefault() ? "disabled" : ""}>${esc(t("clear_conditions", "Clear conditions"))}</button>
    </div>
  </div>`;
}

function renderLeaderboardSearchControls() {
  if (!serveMode()) return "";
  const query = state.search?.query || "";
  return `<div class="leaderboard-search" data-leaderboard-search>
    <input type="search" data-leaderboard-search-input value="${esc(query)}" placeholder="${esc(t("search_sessions", "Search sessions"))}" aria-label="${esc(t("search_sessions", "Search sessions"))}">
  </div>`;
}

function catalogPageEnd() {
  return Math.min(Number(state.catalogPage.total || 0), Number(state.catalogPage.page || 1) * Number(state.catalogPage.page_size || 100));
}

function catalogPageLabel() {
  const total = Number(state.catalogPage.total || 0);
  if (!total) return "0 / 0";
  const start = (Number(state.catalogPage.page || 1) - 1) * Number(state.catalogPage.page_size || 100) + 1;
  return `${start}-${catalogPageEnd()} / ${total}`;
}

function bindLeaderboardCatalogControls(target) {
  if (!serveMode() || !target) return;
  target.querySelector("[data-catalog-prev]")?.addEventListener("click", event => {
    event.stopPropagation();
    loadCatalogPage({ page: Math.max(1, Number(state.catalogQuery.page || 1) - 1) });
  });
  target.querySelector("[data-catalog-next]")?.addEventListener("click", event => {
    event.stopPropagation();
    loadCatalogPage({ page: Number(state.catalogQuery.page || 1) + 1 });
  });
  target.querySelector("[data-catalog-clear-conditions]")?.addEventListener("click", event => {
    event.stopPropagation();
    clearWorkspaceViewConditions();
  });
}

function leaderboardConditionsAreDefault() {
  const query = state.catalogQuery || {};
  const filters = tableControls("leaderboard").filters || {};
  return state.workspaceViewSelection.size < 1
    && !listValue(query.views).length
    && normalizeServeSourceMode(query.state) === "active"
    && !String(query.search || "")
    && !listValue(query.categories).length
    && !listValue(query.tags).length
    && !listValue(query.agents).length
    && !listValue(query.models).length
    && !listValue(query.tasks).length
    && !listValue(query.jobs).length
    && !listValue(query.providers).length
    && !listValue(query.results).length
    && catalogSortKey(query.sort) === "last_turn_end"
    && String(query.direction || "desc") === "desc"
    && !Object.values(filters).some(value => listValue(value).length)
    && state.leaderboardSummaryGroupBy === "agent"
    && state.leaderboardSummaryStatistic === "mean"
    && !state.leaderboardSummaryTableOpen;
}

function requestCatalogSort(key) {
  const query = state.catalogQuery;
  if (query.sort !== key) {
    query.sort = key;
    query.direction = "asc";
  } else if (query.direction === "asc") {
    query.direction = "desc";
  } else {
    query.sort = "last_turn_end";
    query.direction = "desc";
  }
  tableControls("leaderboard").sort = query.sort === "last_turn_end" ? "finished_at_ms" : key;
  tableControls("leaderboard").direction = query.direction;
  loadCatalogPage({ page: 1 });
}

function requestCatalogFacets() {
  const filters = tableControls("leaderboard").filters || {};
  return loadCatalogPage({
    page: 1,
    categories: listValue(filters.source_category),
    tags: listValue(filters.source_tags),
    agents: listValue(filters.agent),
    models: listValue(filters.model),
    tasks: listValue(filters.task_name),
    jobs: listValue(filters.job_name),
    providers: listValue(filters.model_provider),
    results: listValue(filters.status)
  }, { force: true });
}

async function refreshSourceCategoryOptions() {
  if (!serveMode()) return [];
  const query = "state=all&page=1&page_size=1&search=&sort=last_turn_end&direction=desc&surface=leaderboard";
  try {
    const page = await serveApi(`/api/catalog?${query}`);
    if (page?.checking && !page?.generation) return listValue(state.sourceCategoryOptions);
    const seen = new Set();
    state.sourceCategoryOptions = listValue(page?.facets?.categories)
      .map(item => String(item?.value || "").trim())
      .filter(value => value && !seen.has(value) && seen.add(value));
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  }
  return listValue(state.sourceCategoryOptions);
}

function catalogQueryString(surface = "leaderboard") {
  const query = state.catalogQuery;
  const params = new URLSearchParams({
    state: query.state || "active",
    page: String(query.page || 1),
    page_size: String(query.page_size || 100),
    search: query.search || "",
    sort: catalogSortKey(query.sort),
    direction: query.direction || "desc",
    surface
  });
  listValue(query.categories).forEach(value => params.append("category", value));
  listValue(query.tags).forEach(value => params.append("tag", value));
  listValue(query.agents).forEach(value => params.append("agent", value));
  listValue(query.models).forEach(value => params.append("model", value));
  listValue(query.tasks).forEach(value => params.append("task", value));
  listValue(query.jobs).forEach(value => params.append("job", value));
  listValue(query.providers).forEach(value => params.append("provider", value));
  listValue(query.results).forEach(value => params.append("result", value));
  listValue(query.views).forEach(value => params.append("view", value));
  return params.toString();
}

function catalogSortKey(key) {
  return ({
    finished_at_ms: "last_turn_end",
    session_id: "session",
    status: "result",
    task_name: "task",
    job_name: "job",
    model_provider: "provider",
  })[key] || key || "last_turn_end";
}

async function loadCatalogPage(changes = {}, options = {}) {
  if (!serveMode()) return;
  if (state.catalogLoading) {
    if (options.force) {
      return new Promise(resolve => {
        setTimeout(() => resolve(loadCatalogPage(changes, options)), 50);
      });
    }
    return;
  }
  state.catalogQuery = { ...state.catalogQuery, ...changes };
  state.catalogQuery.state = normalizeServeSourceMode(state.catalogQuery.state);
  state.catalogLoading = true;
  try {
    const wasChecking = Boolean(state.catalogPage?.checking);
    const previousGeneration = Number(state.catalogPage?.generation || 0);
    const applied = workspaceViewQueryPayload();
    state.catalogQuery.views = applied.views;
    const page = applied.browser_views.length
      ? await serveApi("/api/catalog/query", {
        method: "POST",
        body: {
          state: state.catalogQuery.state || "active",
          page: Number(state.catalogQuery.page || 1),
          page_size: Number(state.catalogQuery.page_size || 100),
          search: state.catalogQuery.search || "",
          sort: catalogSortKey(state.catalogQuery.sort),
          direction: state.catalogQuery.direction || "desc",
          categories: listValue(state.catalogQuery.categories),
          tags: listValue(state.catalogQuery.tags),
          agents: listValue(state.catalogQuery.agents),
          models: listValue(state.catalogQuery.models),
          tasks: listValue(state.catalogQuery.tasks),
          jobs: listValue(state.catalogQuery.jobs),
          providers: listValue(state.catalogQuery.providers),
          results: listValue(state.catalogQuery.results),
          ...applied,
        },
      })
      : await serveApi(`/api/catalog?${catalogQueryString(options.surface || "leaderboard")}`);
    state.catalogPage = page;
    state.serveSourceMode = normalizeServeSourceMode(state.catalogQuery.state);
    state.serveSources = listValue(page.items);
    state.catalogRows = listValue(page.items).filter(row => row?.readable !== false).map(normalizeCatalogRow);
    state.serveLoading = Boolean(page.checking && !page.generation);
    if (page.generation && page.generation !== previousGeneration) await resolveCatalogSelections();
    renderComparison();
    setWorkspaceWriteControlsDisabled(Boolean(page.checking));
    if (page.checking) {
      setServeStatus(t("serve_scanning_runs", "Checking runs"));
      setTimeout(() => loadCatalogPage({}, { force: true }), 200);
    } else {
      setServeStatus(serveSourceModeStatusText());
      if (wasChecking) await refreshSourceCategoryOptions();
    }
    await ensureCatalogDetail(previousGeneration !== Number(page.generation || 0));
    if (typeof refreshWorkspaceViews === "function" && (
      !state.workspaceViewsLoaded
      || (workspaceViews().length >= 1 && Number(state.workspaceViewSummaryGeneration) !== Number(page.generation || 0))
    )) refreshWorkspaceViews();
  } catch (error) {
    if (error?.status === 409 && state.workspaceAppliedViewNames.size) {
      const appliedCount = state.workspaceAppliedViewNames.size;
      await refreshWorkspaceViews();
      if (state.workspaceAppliedViewNames.size < appliedCount) {
        setTimeout(() => {
          if (state.workspaceAppliedViewNames.size) loadCatalogPage({ page: 1 }, { force: true });
          else clearWorkspaceViewConditions();
        }, 0);
      }
    }
    setServeStatus(error.message || String(error), true);
  } finally {
    state.catalogLoading = false;
  }
}

async function resolveCatalogSelections() {
  const selected = Array.from(new Set([...state.rowSelection, state.selectedSourceKey].filter(Boolean)));
  if (!selected.length) return;
  const payload = await serveApi("/api/catalog/resolve", { method: "POST", body: { source_keys: selected } });
  const present = new Set(listValue(payload?.source_keys));
  Array.from(state.rowSelection).forEach(key => { if (!present.has(key)) state.rowSelection.delete(key); });
  if (state.selectedSourceKey && !present.has(state.selectedSourceKey)) {
    state.selectedSourceKey = null;
    state.selectedArtifactRevision = null;
    state.selectedTrial = null;
  }
}

async function ensureCatalogDetail(generationChanged = false) {
  let sourceKey = state.selectedSourceKey;
  const selectedRow = state.catalogRows.find(row => row.source_key === sourceKey);
  if (!sourceKey) {
    const failed = state.catalogRows.find(row => lower(row.status) !== "passed");
    sourceKey = (failed || state.catalogRows[0])?.source_key || null;
  }
  if (!sourceKey) {
    state.view = emptyServeReport();
    state.selectedTrial = null;
    render(state.view);
    return;
  }
  if (!generationChanged && sourceKey === state.selectedSourceKey && state.view?.trajectory_meta?.length) return;
  if (generationChanged && selectedRow && selectedRow.artifact_revision === state.selectedArtifactRevision) return;
  await loadServeSourceReport(sourceKey);
}

async function loadServeWorkspace() {
  if (!serveMode()) return;
  await Promise.all([
    loadCatalogPage(),
    refreshWorkspaceReports(),
    refreshSourceCategoryOptions(),
  ]);
}

function catalogRowForSourceKey(sourceKey) {
  return listValue(state.catalogRows).find(row => row?.source_key === sourceKey) || null;
}

function loadedServeDetailIsCurrent(sourceKey) {
  const row = catalogRowForSourceKey(sourceKey);
  return sourceKey === state.selectedSourceKey
    && listValue(state.view?.trajectory_meta).length > 0
    && (!row?.artifact_revision || row.artifact_revision === state.selectedArtifactRevision);
}

function detailStepSelection(report, trialKey, selection = {}) {
  if (selection.stepId !== null && selection.stepId !== undefined) {
    const step = listValue(report?.trajectory?.[0]?.steps).find(item => String(item?.step_id) === String(selection.stepId));
    return step ? { trialKey, stepId: String(step.step_id) } : null;
  }
  return selection.firstUserStep ? firstUserStepSelection(trialKey, report) : null;
}

function applyServeDetailSelection(sourceKey, report, artifactRevision, selection = {}) {
  const trialKey = listValue(report?.trajectory_meta)[0]?.trial_key || null;
  state.selectedSourceKey = sourceKey;
  state.selectedArtifactRevision = artifactRevision || null;
  state.selectedTrial = trialKey;
  state.selectedStep = trialKey ? detailStepSelection(report, trialKey, selection) : null;
  render(report || emptyServeReport());
}

function selectServeDetail(sourceKey, selection = {}) {
  if (!sourceKey) return Promise.resolve();
  if (loadedServeDetailIsCurrent(sourceKey)) {
    applyServeDetailSelection(sourceKey, state.view, state.selectedArtifactRevision, selection);
    return Promise.resolve();
  }
  return loadServeSourceReport(sourceKey, selection);
}

function selectServeSource(sourceKey) {
  return selectServeDetail(sourceKey);
}

async function loadServeSourceReport(sourceKey, selection = {}) {
  if (!sourceKey) return;
  try {
    const envelope = await serveApi(`/api/report?source_key=${encodeURIComponent(sourceKey)}`);
    applyServeDetailSelection(sourceKey, envelope.report || emptyServeReport(), envelope.artifact_revision, selection);
    setServeStatus(serveSourceModeStatusText());
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  }
}

function applyLeaderboardSearchMode() {
  if (!serveMode()) return renderComparisonPanels();
  clearTimeout(state.catalogSearchTimer);
  state.catalogSearchTimer = setTimeout(() => {
    loadCatalogPage({ page: 1, search: String(state.search?.query || "") });
  }, 150);
}

async function switchServeSourceMode(mode) {
  const nextMode = normalizeServeSourceMode(mode);
  if (nextMode === "all") return;
  state.catalogQuery.state = nextMode;
  state.catalogQuery.page = 1;
  state.serveSourceMode = nextMode;
  state.selectedSourceKey = null;
  state.selectedArtifactRevision = null;
  state.rowSelection.clear();
  await loadCatalogPage();
}

function applyServeMutationPayload(payload, options = {}) {
  hideServeNotice();
  if (payload?.operation_id) {
    return pollCatalogOperation(payload.operation_id, options);
  }
  return loadCatalogPage({}, { force: true });
}

async function applyServeSourceStateMutationPayload(payload, options = {}) {
  return applyServeMutationPayload(payload, options);
}

async function pollCatalogOperation(operationId, options = {}) {
  try {
    const operation = await serveApi(`/api/operations/${encodeURIComponent(operationId)}`);
    setServeStatus(`${operation.operation_type}: ${operation.completed}/${operation.total}`);
    setWorkspaceWriteControlsDisabled(operation.state === "queued" || operation.state === "running");
    if (operation.state === "queued" || operation.state === "running") {
      setTimeout(() => pollCatalogOperation(operationId, options), 200);
      return;
    }
    setWorkspaceWriteControlsDisabled(false);
    const selectedKeys = listValue(options.sourceKeys);
    const successfulIndexes = new Set(listValue(operation.successes).map(item => Number(item.index)));
    selectedKeys.forEach((key, index) => {
      if (successfulIndexes.has(index)) state.rowSelection.delete(key);
    });
    await loadCatalogPage({}, { force: true });
    await refreshSourceCategoryOptions();
    const failures = listValue(operation.failures);
    if (failures.length) setServeStatus(`${failures.length} operation item(s) failed: ${failures[0]?.error || "error"}`, true);
  } catch (error) {
    setWorkspaceWriteControlsDisabled(false);
    setServeStatus(error.message || String(error), true);
  }
}

function setWorkspaceWriteControlsDisabled(disabled) {
  state.workspaceWriteBusy = Boolean(disabled);
  document.querySelectorAll("[data-refresh-all],[data-refresh-sources],[data-source-add-form] button[type=submit],[data-harbor-add-mount],[data-harbor-remove-mounts],[data-source-state-action],[data-source-delete-action]").forEach(control => {
    if (disabled) {
      if (!Object.prototype.hasOwnProperty.call(control.dataset, "busyPreviousDisabled")) {
        control.dataset.busyPreviousDisabled = control.disabled ? "true" : "false";
      }
      control.disabled = true;
      control.setAttribute("aria-busy", "true");
      return;
    }
    if (Object.prototype.hasOwnProperty.call(control.dataset, "busyPreviousDisabled")) {
      control.disabled = control.dataset.busyPreviousDisabled === "true";
      delete control.dataset.busyPreviousDisabled;
    }
    control.removeAttribute("aria-busy");
  });
}

async function refreshServeSourcesFromServer() {
  if (!adminMode()) return;
  try {
    const payload = await serveApi("/api/sources/reload", { method: "POST", body: {} });
    await applyServeMutationPayload(payload);
    if (!payload?.operation_id) await refreshSourceCategoryOptions();
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  }
}

async function refreshServeReportFromServer() {
  return refreshServeSourcesFromServer();
}

function exportCurrentScope(kind) {
  if (!serveMode()) return;
  if (kind === "xlsx") {
    const applied = workspaceViewQueryPayload();
    serveDownload("xlsx", {
      kind: "xlsx",
      query: { ...state.catalogQuery, ...applied, page: undefined, page_size: undefined }
    });
    return;
  }
  if (kind === "workspace_html") {
    const viewControls = tableControls("workspace-views");
    const visibleViews = typeof workspaceViewRows === "function" ? workspaceViewRows() : [];
    const applied = workspaceViewQueryPayload();
    serveDownload("workspace_html", {
      kind: "workspace_html",
      browser_views: browserWorkspaceViewDefinitions(),
      query: {
        state: state.catalogQuery.state || "active",
        search: state.catalogQuery.search || "",
        sort: state.catalogQuery.sort || "last_turn_end",
        direction: state.catalogQuery.direction || "desc",
        categories: listValue(state.catalogQuery.categories),
        tags: listValue(state.catalogQuery.tags),
        agents: listValue(state.catalogQuery.agents),
        models: listValue(state.catalogQuery.models),
        tasks: listValue(state.catalogQuery.tasks),
        jobs: listValue(state.catalogQuery.jobs),
        providers: listValue(state.catalogQuery.providers),
        results: listValue(state.catalogQuery.results),
        ...applied,
      },
      selected_source_keys: Array.from(state.rowSelection),
      presentation: {
        summary_group_by: state.leaderboardSummaryGroupBy,
        summary_statistic: state.leaderboardSummaryStatistic,
        summary_table_open: Boolean(state.leaderboardSummaryTableOpen),
        selected_source_key: state.selectedSourceKey || null,
        selected_step_id: state.selectedStep?.stepId ?? null,
        leaderboard_columns: currentLeaderboardColumnLayout(),
        visible_view_names: visibleViews.map(view => view.name),
        workspace_view_filters: {
          categories: listValue(viewControls.filters?.categories),
          tags: listValue(viewControls.filters?.tags),
          models: listValue(viewControls.filters?.models),
          tasks: listValue(viewControls.filters?.tasks),
          jobs: listValue(viewControls.filters?.jobs),
          providers: listValue(viewControls.filters?.providers),
          group_by: listValue(viewControls.filters?.group_by),
        },
        open_view_tables: visibleViews
          .filter(view => state.workspaceViewTableOpen.has(view.id))
          .map(view => view.name),
      },
    }, "peval-workspace-snapshot.html");
    return;
  }
  const keys = state.rowSelection.size
    ? Array.from(state.rowSelection)
    : state.catalogRows.map(row => row.source_key).filter(Boolean);
  if (keys.length > 100) {
    setServeStatus(t("serve_export_cell_limit", "JSON export is limited to 100 cells"), true);
    return;
  }
  serveDownload(kind, { kind, source_keys: keys });
}

function exportLeaderboardSummary() {
  if (!serveMode()) return;
  const sourceKeys = leaderboardRows().map(row => row?.source_key).filter(Boolean);
  if (!sourceKeys.length) return;
  const applied = workspaceViewQueryPayload();
  return serveDownload("summary_xlsx", {
    kind: "summary_xlsx",
    summary: {
      scope: "leaderboard",
      source_keys: sourceKeys,
      query: { ...state.catalogQuery, ...applied, page: undefined, page_size: undefined },
      group_by: state.leaderboardSummaryGroupBy,
      statistic: state.leaderboardSummaryStatistic
    }
  }, "peval-leaderboard-summary.xlsx");
}

async function serveDownload(kind, body, requestedFilename = "") {
  try {
    const response = await fetch("/api/exports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin"
    });
    if (!response.ok) {
      reloadExpiredAdminSession(response);
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload?.error || response.statusText);
    }
    const blob = await response.blob();
    const filename = requestedFilename || (kind === "xlsx" ? "peval-leaderboard.xlsx" : kind === "workspace_html" ? "peval-workspace-snapshot.html" : "peval-report-v19.json");
    downloadBlob(filename, blob.type || "application/octet-stream", blob);
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  }
}
export {
  applyLeaderboardSearchMode,
  applyServeDetailSelection,
  applyServeMutationPayload,
  applyServeSourceStateMutationPayload,
  bindLeaderboardCatalogControls,
  catalogPageEnd,
  catalogPageLabel,
  catalogQueryString,
  catalogRowForSourceKey,
  catalogSortKey,
  catalogStepOutline,
  detailStepSelection,
  ensureCatalogDetail,
  exportCurrentScope,
  exportLeaderboardSummary,
  filterOptions,
  leaderboardConditionsAreDefault,
  leaderboardRows,
  loadServeWorkspace,
  loadCatalogPage,
  loadServeSourceReport,
  loadedServeDetailIsCurrent,
  metaFor,
  normalizeCatalogRow,
  pollCatalogOperation,
  refreshServeReportFromServer,
  refreshServeSourcesFromServer,
  renderLeaderboardPanelControls,
  renderLeaderboardSearchControls,
  reportRows,
  requestCatalogFacets,
  requestCatalogSort,
  refreshSourceCategoryOptions,
  resolveCatalogSelections,
  rowAnalysisCount,
  selectServeDetail,
  selectServeSource,
  serveDownload,
  setWorkspaceWriteControlsDisabled,
  sourceForTrialIndex,
  sourceForTrialKey,
  sourceKeyForTrialKey,
  switchServeSourceMode,
  syncSelectionWithVisibleRows,
  trajectoryFor,
  trialIndexFor,
  trialKeyForServeSource,
  visibleSelectedSourceKeys,
};
