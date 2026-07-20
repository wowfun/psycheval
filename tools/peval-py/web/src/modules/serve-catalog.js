import { WORKSPACE_SNAPSHOT, analysisArtifactPathsFor, applySessionSearch, esc, hasMetricValue, isAnalysisArtifactPath, listValue, lower, normalizeServeSourceMode, render, renderComparison, renderComparisonPanels, selectedIndex, selectedKey, serveMode, state, synthesizedReportRow, t, workspaceSnapshotMode } from "./runtime.js";
import { applyDataTableControls, filterValues, leaderboardColumns, renderLeaderboardExportControls, tableControls } from "./data-tables.js";
import { downloadBlob, firstUserStepSelection } from "./export.js";
import { renderServeSourceStateControls, serveSourceModeStatusText } from "./source-state-controls.js";
import { renderServeSources, sourceColumns, syncSourceManagerBulkActions } from "./source-manager.js";
import { emptyServeReport, hideServeNotice, serveApi, setServeStatus } from "./serve-effects.js";
import { closeWorkspaceReportManager, closeWorkspaceReportReader, refreshWorkspaceReports, renderAttachWorkspaceReportAction } from "./workspace-reports.js";
import { clearWorkspaceViewConditions, closeWorkspaceViewSaveDialog, refreshWorkspaceViews, workspaceViewRows, workspaceViews } from "./workspace-views.js";
import { renderStepDrawer } from "./trajectory-trace.js";
import { openModalSurface } from "./modal-surfaces.js";

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

function rowAnalysised(row) {
  if (serveMode() && Object.prototype.hasOwnProperty.call(row || {}, "analysised")) {
    return row.analysised ? "True" : "False";
  }
  return analysisArtifactPathsFor(row?.trial_key).some(isAnalysisArtifactPath) ? "True" : "False";
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

function pruneSourceSelection() {
  if (!serveMode()) return;
}

function sourceSelectionKeys() {
  return Array.from(state.sourceSelection);
}

function sourceRows() {
  return applyDataTableControls("sources", listValue(state.sourceManagerRows), sourceColumns());
}

function openServeSourceManager(opener = document.activeElement) {
  const manager = document.querySelector("[data-source-manager]");
  if (!manager) return;
  closeWorkspaceViewSaveDialog({ restoreFocus: false });
  closeWorkspaceReportManager({ restoreFocus: false });
  closeWorkspaceReportReader({ restoreFocus: false });
  state.selectedStep = null;
  renderStepDrawer();
  state.sourceManagerStatus = {
    phase: "loading",
    message: t("loading", "Loading"),
  };
  openModalSurface(manager, {
    opener,
    bodyClass: "source-manager-open",
    focusTarget: manager.querySelector("[data-source-manager-close]"),
  });
  renderServeSources();
  loadSourceManagerPage();
}

async function loadSourceManagerPage(pageNumber = Number(state.sourceManagerPage?.page || 1)) {
  if (typeof URLSearchParams !== "function" || typeof fetch !== "function") return;
  state.sourceManagerStatus = {
    phase: "loading",
    message: t("loading", "Loading"),
  };
  renderServeSources();
  try {
    const params = new URLSearchParams({
      state: "all",
      surface: "sources",
      page: String(Math.max(1, pageNumber)),
      page_size: "100",
      sort: "last_turn_end",
      direction: "desc"
    });
    const page = await serveApi(`/api/catalog?${params.toString()}`);
    state.sourceManagerPage = page;
    state.sourceManagerRows = listValue(page.items);
    state.sourceManagerStatus = { phase: "ready", message: "" };
    hideServeNotice();
    renderServeSources();
  } catch (error) {
    const message = error.message || String(error);
    state.sourceManagerStatus = { phase: "error", message };
    renderServeSources();
    setServeStatus(message, true);
  }
}

function sourceManagerPageEnd() {
  const page = Number(state.sourceManagerPage?.page || 1);
  const size = Number(state.sourceManagerPage?.page_size || 100);
  return Math.min(Number(state.sourceManagerPage?.total || 0), page * size);
}

function renderSourceManagerPagination() {
  const page = Number(state.sourceManagerPage?.page || 1);
  const size = Number(state.sourceManagerPage?.page_size || 100);
  const total = Number(state.sourceManagerPage?.total || state.sourceManagerRows.length || 0);
  const start = total ? (page - 1) * size + 1 : 0;
  return `<li class="catalog-page-controls source-manager-page-controls">
    <button type="button" class="action-button icon-only" data-source-page-prev aria-label="${esc(t("previous", "Previous"))}" ${page <= 1 ? "disabled" : ""}>‹</button>
    <span>${esc(`${start}-${sourceManagerPageEnd()} / ${total}`)}</span>
    <button type="button" class="action-button icon-only" data-source-page-next aria-label="${esc(t("next", "Next"))}" ${sourceManagerPageEnd() >= total ? "disabled" : ""}>›</button>
    <span>${esc(String(t("selected_count", "{count} selected")).replace("{count}", String(state.sourceSelection.size)))}</span>
    <button type="button" class="action-button" data-source-selection-clear ${state.sourceSelection.size ? "" : "disabled"}>${esc(t("clear", "Clear"))}</button>
  </li>`;
}

function bindSourceManagerPagination(root) {
  root?.querySelector?.("[data-source-page-prev]")?.addEventListener?.("click", () => loadSourceManagerPage(Number(state.sourceManagerPage.page || 1) - 1));
  root?.querySelector?.("[data-source-page-next]")?.addEventListener?.("click", () => loadSourceManagerPage(Number(state.sourceManagerPage.page || 1) + 1));
  root?.querySelector?.("[data-source-selection-clear]")?.addEventListener?.("click", () => {
    state.sourceSelection.clear();
    renderServeSources();
  });
}

function visibleSelectedSourceKeys() {
  return Array.from(state.rowSelection);
}

function filterOptions(column, rows) {
  if (!serveMode()) {
    const values = rows.flatMap(row => filterValues(row, column));
    return Array.from(new Set(values)).sort((left, right) => left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" }));
  }
  const facetKey = ({ source_tags: "tags", agent: "agents", model: "models", status: "results" })[column.key];
  if (!facetKey) {
    const values = rows.flatMap(row => filterValues(row, column));
    return Array.from(new Set(values)).sort((left, right) => left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" }));
  }
  return listValue(state.catalogPage?.facets?.[facetKey]).map(item => String(item?.value || "")).filter(Boolean);
}

function renderLeaderboardPanelControls(rows) {
  if (!serveMode()) return "";
  const selectedCount = state.rowSelection.size;
  return `<div class="leaderboard-actions">
    <div class="leaderboard-action-row">${renderServeSourceStateControls(rows)}${renderAttachWorkspaceReportAction(rows)}${renderLeaderboardExportControls()}</div>
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
    && !listValue(query.tags).length
    && !listValue(query.agents).length
    && !listValue(query.models).length
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
    tags: listValue(filters.source_tags),
    agents: listValue(filters.agent),
    models: listValue(filters.model),
    results: listValue(filters.status)
  }, { force: true });
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
  listValue(query.tags).forEach(value => params.append("tag", value));
  listValue(query.agents).forEach(value => params.append("agent", value));
  listValue(query.models).forEach(value => params.append("model", value));
  listValue(query.results).forEach(value => params.append("result", value));
  listValue(query.views).forEach(value => params.append("view", value));
  return params.toString();
}

function catalogSortKey(key) {
  return ({ finished_at_ms: "last_turn_end", session_id: "session", status: "result" })[key] || key || "last_turn_end";
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
    const previousGeneration = Number(state.catalogPage?.generation || 0);
    const page = await serveApi(`/api/catalog?${catalogQueryString(options.surface || "leaderboard")}`);
    state.catalogPage = page;
    state.serveSourceMode = normalizeServeSourceMode(state.catalogQuery.state);
    state.serveSources = listValue(page.items);
    state.catalogRows = listValue(page.items).filter(row => row?.readable !== false).map(normalizeCatalogRow);
    state.serveLoading = Boolean(page.checking && !page.generation);
    if (page.generation && page.generation !== previousGeneration) await resolveCatalogSelections();
    renderServeSources();
    renderComparison();
    setWorkspaceWriteControlsDisabled(Boolean(page.checking));
    if (page.checking) {
      setServeStatus(t("serve_scanning_runs", "Checking runs"));
      setTimeout(() => loadCatalogPage({}, { force: true }), 200);
    } else {
      setServeStatus(serveSourceModeStatusText());
    }
    await ensureCatalogDetail(previousGeneration !== Number(page.generation || 0));
    if (typeof refreshWorkspaceViews === "function" && (
      !state.workspaceViewsLoaded
      || (workspaceViews().length >= 1 && Number(state.workspaceViewSummaryGeneration) !== Number(page.generation || 0))
    )) refreshWorkspaceViews();
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  } finally {
    state.catalogLoading = false;
  }
}

async function resolveCatalogSelections() {
  const selected = Array.from(new Set([...state.rowSelection, ...state.sourceSelection, state.selectedSourceKey].filter(Boolean)));
  if (!selected.length) return;
  const payload = await serveApi("/api/catalog/resolve", { method: "POST", body: { source_keys: selected } });
  const present = new Set(listValue(payload?.source_keys));
  Array.from(state.rowSelection).forEach(key => { if (!present.has(key)) state.rowSelection.delete(key); });
  Array.from(state.sourceSelection).forEach(key => { if (!present.has(key)) state.sourceSelection.delete(key); });
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
  await loadCatalogPage();
}

function applyServeMutationPayload(payload) {
  hideServeNotice();
  if (payload?.operation_id) {
    pollCatalogOperation(payload.operation_id);
    return;
  }
  loadCatalogPage({}, { force: true }).then(() => {
    const manager = document.querySelector("[data-source-manager]");
    if (manager && !manager.hidden) loadSourceManagerPage();
  });
}

async function applyServeSourceStateMutationPayload(payload) {
  applyServeMutationPayload(payload);
}

async function pollCatalogOperation(operationId) {
  try {
    const operation = await serveApi(`/api/operations/${encodeURIComponent(operationId)}`);
    setServeStatus(`${operation.operation_type}: ${operation.completed}/${operation.total}`);
    setWorkspaceWriteControlsDisabled(operation.state === "queued" || operation.state === "running");
    if (operation.state === "queued" || operation.state === "running") {
      setTimeout(() => pollCatalogOperation(operationId), 200);
      return;
    }
    setWorkspaceWriteControlsDisabled(false);
    await loadCatalogPage({}, { force: true });
    const manager = document.querySelector("[data-source-manager]");
    if (manager && !manager.hidden) await loadSourceManagerPage();
    const failures = listValue(operation.failures);
    if (failures.length) setServeStatus(`${failures.length} operation item(s) failed: ${failures[0]?.error || "error"}`, true);
  } catch (error) {
    setWorkspaceWriteControlsDisabled(false);
    setServeStatus(error.message || String(error), true);
  }
}

function setWorkspaceWriteControlsDisabled(disabled) {
  state.workspaceWriteBusy = Boolean(disabled);
  document.querySelectorAll("[data-refresh-all],[data-refresh-sources],[data-source-bulk-state],[data-source-bulk-delete],[data-source-add-form] button[type=submit],[data-source-upload-form] button[type=submit],[data-source-state-action]").forEach(control => {
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
  if (!disabled) syncSourceManagerBulkActions();
}

async function refreshServeSourcesFromServer() {
  try {
    applyServeMutationPayload(await serveApi("/api/sources/reload", { method: "POST", body: {} }));
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  }
}

async function refreshServeReportFromServer() {
  return refreshServeSourcesFromServer();
}

async function deleteSelectedServeSources() {
  const sourceKeys = sourceSelectionKeys();
  if (!sourceKeys.length) return;
  if (!window.confirm(t("serve_delete_selected_confirm", "Delete selected sources from peval-py state?"))) return;
  try {
    state.sourceSelection.clear();
    applyServeMutationPayload(await serveApi("/api/sources/delete", {
      method: "POST",
      body: { source_keys: sourceKeys }
    }));
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  }
}

function exportCurrentScope(kind) {
  if (!serveMode()) return;
  if (kind === "xlsx") {
    serveDownload("xlsx", {
      kind: "xlsx",
      query: { ...state.catalogQuery, page: undefined, page_size: undefined }
    });
    return;
  }
  if (kind === "workspace_html") {
    const viewControls = tableControls("workspace-views");
    const visibleViews = typeof workspaceViewRows === "function" ? workspaceViewRows() : [];
    serveDownload("workspace_html", {
      kind: "workspace_html",
      query: {
        state: state.catalogQuery.state || "active",
        search: state.catalogQuery.search || "",
        sort: state.catalogQuery.sort || "last_turn_end",
        direction: state.catalogQuery.direction || "desc",
        tags: listValue(state.catalogQuery.tags),
        agents: listValue(state.catalogQuery.agents),
        models: listValue(state.catalogQuery.models),
        results: listValue(state.catalogQuery.results),
        views: listValue(state.catalogQuery.views),
      },
      selected_source_keys: Array.from(state.rowSelection),
      presentation: {
        summary_group_by: state.leaderboardSummaryGroupBy,
        summary_statistic: state.leaderboardSummaryStatistic,
        summary_table_open: Boolean(state.leaderboardSummaryTableOpen),
        selected_source_key: state.selectedSourceKey || null,
        selected_step_id: state.selectedStep?.stepId ?? null,
        visible_view_names: visibleViews.map(view => view.name),
        workspace_view_filters: {
          tags: listValue(viewControls.filters?.tags),
          models: listValue(viewControls.filters?.models),
          group_by: listValue(viewControls.filters?.group_by),
        },
        open_view_tables: visibleViews
          .map(view => view.name)
          .filter(name => state.workspaceViewTableOpen.has(name)),
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
  return serveDownload("summary_xlsx", {
    kind: "summary_xlsx",
    summary: {
      scope: "leaderboard",
      source_keys: sourceKeys,
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
  bindSourceManagerPagination,
  catalogPageEnd,
  catalogPageLabel,
  catalogQueryString,
  catalogRowForSourceKey,
  catalogSortKey,
  catalogStepOutline,
  deleteSelectedServeSources,
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
  loadSourceManagerPage,
  loadedServeDetailIsCurrent,
  metaFor,
  normalizeCatalogRow,
  openServeSourceManager,
  pollCatalogOperation,
  pruneSourceSelection,
  refreshServeReportFromServer,
  refreshServeSourcesFromServer,
  renderLeaderboardPanelControls,
  renderLeaderboardSearchControls,
  renderSourceManagerPagination,
  reportRows,
  requestCatalogFacets,
  requestCatalogSort,
  resolveCatalogSelections,
  rowAnalysised,
  selectServeDetail,
  selectServeSource,
  serveDownload,
  setWorkspaceWriteControlsDisabled,
  sourceForTrialIndex,
  sourceForTrialKey,
  sourceKeyForTrialKey,
  sourceManagerPageEnd,
  sourceRows,
  sourceSelectionKeys,
  switchServeSourceMode,
  syncSelectionWithVisibleRows,
  trajectoryFor,
  trialIndexFor,
  trialKeyForServeSource,
  visibleSelectedSourceKeys,
};
