import { renderLeaderboard } from "./data-tables.js";
import { renderLeaderboardSummary } from "./leaderboard-summary.js";
import { renderTrace, renderTrajectoryOverview } from "./trajectory-trace.js";
import { renderDetailSidebar } from "./detail-sidebar.js";
import { bindGlobalControls } from "./serve-controls.js";
import { leaderboardRows, metaFor, reportRows, sourceForTrialIndex, sourceForTrialKey, syncSelectionWithVisibleRows, trajectoryFor } from "./serve-catalog.js";
import { refreshWorkspaceViews } from "./workspace-views.js";
import { finalMetric, tokenTotal, trialWallDurationMs } from "./analysis-metrics.js";
import { renderMarkdown } from "./markdown.js";
import { inferenceRowMetrics } from "./inference-metrics.js";

const $ = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
const lower = value => String(value || "").toLowerCase();
function scriptJson(id, fallback) {
  const node = $(id);
  if (!node) return fallback;
  try {
    return JSON.parse(node.textContent || JSON.stringify(fallback));
  } catch {
    return fallback;
  }
}
const I18N = scriptJson("peval-i18n", {});
const RENDER_OPTIONS = scriptJson("peval-render-options", {});
function t(key, fallback) { return Object.prototype.hasOwnProperty.call(I18N, key) ? I18N[key] : (fallback ?? key); }
function statusLabel(value) {
  const raw = String(value || "-");
  return t(`status.${lower(raw)}`, raw);
}
const fmtNum = value => value === null || value === undefined ? "-" : Number(value).toLocaleString();
function fmtMs(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  const seconds = Math.max(0, Number(value) / 1000);
  return seconds >= 60 ? `${Math.floor(seconds / 60)}m${(seconds % 60).toFixed(1)}s` : `${seconds.toFixed(1)}s`;
}
function fmtTtft(value) {
  if (!hasMetricValue(value)) return "-";
  const milliseconds = Math.max(0, Number(value));
  return milliseconds < 1000 ? `${Math.round(milliseconds)} ms` : `${(milliseconds / 1000).toFixed(2)}s`;
}
function fmtTps(value) { return hasMetricValue(value) ? `${Number(value).toFixed(1)} tok/s` : "-"; }
function fmtDate(value) {
  if (value === null || value === undefined || String(value).trim() === "") return "-";
  const source = String(value).trim();
  const date = typeof value === "number" || /^-?\d+(?:\.\d+)?$/.test(source)
    ? new Date(Number(value))
    : /(?:Z|[+-]\d{2}:\d{2})$/i.test(source)
      ? new Date(source)
      : null;
  return date && !Number.isNaN(date.getTime()) ? date.toISOString() : source;
}
function fmtCost(value) { return hasMetricValue(value) ? `$${Number(value).toFixed(4)}` : "-"; }
function fmtPct(value) { return hasMetricValue(value) ? `${(Number(value) * 100).toFixed(1)}%` : "-"; }
function fmtScore(value) { return hasMetricValue(value) ? Number(value).toLocaleString() : "-"; }
function hasMetricValue(value) { return value !== null && value !== undefined && value !== "" && !Number.isNaN(Number(value)); }
function adminMode() { return RENDER_OPTIONS?.role !== "guest"; }
function authenticationEnabled() { return Boolean(RENDER_OPTIONS?.authentication_enabled); }
function initialAdapterDefaults() {
  return RENDER_OPTIONS?.adapter_defaults && typeof RENDER_OPTIONS.adapter_defaults === "object"
    ? { ...RENDER_OPTIONS.adapter_defaults }
    : {};
}
function adapterDefaults() {
  return state.adapterDefaults || {};
}
const state = { view: null, selectedTrial: null, selectedStep: null, detailSidebar: { open: false, opener: null, openerSelector: null, preferredWidth: null }, rowSelection: new Set(), tables: {}, timelineChart: null, boundGlobalControls: false, serveSources: [], sourceCategoryOptions: [], catalogRows: [], catalogPage: { generation: 0, total: 0, page: 1, page_size: 100, facets: {}, checking: Boolean(RENDER_OPTIONS?.loading) }, catalogQuery: { state: "active", page: 1, page_size: 100, search: "", sort: "last_turn_end", direction: "desc", categories: [], tags: [], agents: [], models: [], tasks: [], jobs: [], providers: [], results: [], views: [] }, catalogLoading: false, catalogSearchTimer: null, selectedArtifactRevision: null, workspaceReports: [], reportManager: { selectedId: null, search: "", page: 1, pageData: { page: 1, page_size: 100, total: 0 }, sourceRows: [], searchTimer: null, draftBindings: new Set(), dirty: false, loading: false, busy: false, opener: null }, reportReader: { openId: null, opener: null, width: null, objectUrl: null, previewObserver: null }, workspaceViews: [], workspaceViewSummaries: [], workspaceViewsLoaded: false, workspaceViewsLoading: false, workspaceViewsRefreshPromise: null, workspaceViewsRefreshQueued: false, workspaceViewsRefreshVersion: 0, workspaceViewSummaryGeneration: null, workspaceViewTableOpen: new Set(), workspaceViewSelection: new Set(), workspaceAppliedViewNames: new Set(), workspaceViewSave: { opener: null }, workspaceViewsClosed: false, workspaceViewScroll: { analysisTop: 0, indexTop: 0, indexLeft: 0, cardsTop: 0 }, selectedSourceKey: null, serveSourceMode: "active", serveReportCache: {}, adapterDefaults: initialAdapterDefaults(), notesEditor: null, search: { query: "", scope: "visible", normalSourceMode: "active" }, serveLoading: Boolean(RENDER_OPTIONS?.loading) };
state.leaderboardSummaryGroupBy = "agent";
state.leaderboardSummaryTableOpen = false;
state.leaderboardSummaryStatistic = "mean";
state.leaderboardSummary = null;
state.leaderboardSummaryLoading = false;
state.leaderboardSummaryError = null;
state.leaderboardSummaryScopeKey = null;
state.leaderboardSummaryRequestKey = null;
state.leaderboardSummaryRequestVersion = 0;
state.leaderboardSummaryRequestPromise = null;
state.leaderboardSummaryCache = new Map();
const SUBMENU_DETAILS_SELECTOR = ".export-menu,.filter-control,.column-control";
const OPEN_SUBMENU_DETAILS_SELECTOR = ".export-menu[open],.filter-control[open],.column-control[open]";
function closeOpenSubmenus(except = null) {
  document.querySelectorAll(OPEN_SUBMENU_DETAILS_SELECTOR).forEach(details => {
    if (details !== except) details.open = false;
  });
}
function listValue(value) {
  return Array.isArray(value) ? value : [];
}
function synthesizedReportRow(trajectory, meta, index = -1) {
  const metrics = trajectory?.final_metrics || {};
  const totalToolCalls = hasMetricValue(finalMetric(metrics, "total_tool_calls")) ? Number(finalMetric(metrics, "total_tool_calls")) : 0;
  const totalToolErrors = hasMetricValue(finalMetric(metrics, "total_tool_errors")) ? Number(finalMetric(metrics, "total_tool_errors")) : 0;
  const agent = trajectory?.agent || {};
  const source = sourceForTrialIndex(index);
  return {
    trial_key: meta?.trial_key,
    session_id: trajectory?.session_id || "-",
    source_alias: meta?.source_alias,
    display_alias: meta?.display_alias,
    source_category: sourceCategoryForMeta(meta, source),
    source_tags: sourceTagsFromValue(meta?.source_tags || source?.source_tags),
    task_keywords: sourceTagsFromValue(meta?.task_keywords || source?.task_keywords),
    display_tags: sourceTagsForMeta(meta, source),
    task_name: meta?.task_name || source?.task_name,
    job_name: meta?.job_name || source?.job_name,
    trial_name: meta?.trial_name || source?.trial_name,
    model_provider: meta?.model_provider || source?.model_provider,
    rewards: meta?.rewards || source?.rewards || {},
    harbor_provenance: meta?.harbor_provenance || source?.harbor_provenance || {},
    task_metadata: meta?.task_metadata || source?.task_metadata || {},
    source_key: source?.source_key || null,
    source_active: source?.active !== false,
    adapter: meta?.adapter,
    model: agent.model_name,
    status: meta?.status,
    finished_at_ms: meta?.finished_at_ms,
    duration_ms: meta?.duration_ms,
    wall_duration_ms: trialWallDurationMs(meta),
    turns: finalMetric(metrics, "total_turns"),
    total_tool_calls: totalToolCalls,
    total_tool_errors: totalToolErrors,
    tokens: tokenTotal(metrics),
    cost_usd: metrics.total_cost_usd,
    warnings: Array.isArray(meta?.warnings) ? meta.warnings.length : 0,
    ...(source?.analysis_count !== null && source?.analysis_count !== undefined
      ? { analysis_count: source.analysis_count }
      : {}),
    ...inferenceRowMetrics(metrics),
  };
}
function selectedKey() {
  return state.selectedTrial || state.view?.trajectory_meta?.[0]?.trial_key || null;
}
function selectedIndex() {
  const key = selectedKey();
  const metas = state.view?.trajectory_meta || [];
  const index = metas.findIndex(meta => meta.trial_key === key);
  return index >= 0 ? index : 0;
}
function finalMetricsFor(trialKey) { return trajectoryFor(trialKey)?.final_metrics || {}; }
function stepMeta(meta, stepId) { return (meta.steps || []).find(item => item.step_id === stepId) || {}; }
function render(view) {
  state.view = view;
  renderWorkspaceDescription();
  state.serveReportCache[currentServeSourceMode()] = view;
  if (!state.selectedTrial) {
    const firstFailed = reportRows().find(row => lower(row.status) !== "passed");
    state.selectedTrial = (firstFailed || reportRows()[0])?.trial_key || view.trajectory_meta?.[0]?.trial_key || null;
  }
  syncSelectedSourceFromView();
  bindGlobalControls();
  renderReportNotes(view.annotations?.report_notes || []);
  renderComparison();
  if (!state.workspaceViewsLoaded) refreshWorkspaceViews();
  renderTrace();
  renderDetailSidebar();
}
function renderWorkspaceDescription() {
  const node = document.querySelector("[data-workspace-description]");
  if (!node) return;
  const markdown = String(RENDER_OPTIONS?.workspace_description || "");
  const visible = Boolean(markdown.trim());
  node.hidden = !visible;
  node.innerHTML = visible ? renderMarkdown(markdown) : "";
}
function syncSelectedSourceFromView() {
  const trialKey = selectedKey();
  if (!trialKey) return;
  const source = sourceForTrialKey(trialKey);
  if (source?.source_key) state.selectedSourceKey = source.source_key;
}
function renderReportNotes(notes) {
  $("report-notes").innerHTML = notes.length ? `<div class="report-note-list">${notes.map(note => `<article class="report-note"><strong>${esc(note.label || t("report_note", "Report note"))}</strong><div class="note-body">${renderMarkdown(note.markdown || "")}</div></article>`).join("")}</div>` : "";
}
function renderComparison() {
  const scrollState = comparisonScrollState();
  const rows = reportRows();
  const leaderboardRegion = $("leaderboard-region");
  if (!rows.length) {
    if (leaderboardRegion) leaderboardRegion.innerHTML = "";
    $("comparison").innerHTML = `<section class="leaderboard-summary panel" aria-labelledby="leaderboard-summary-title" id="leaderboard-summary"></section>`;
    renderLeaderboardSummary();
    return;
  }
  if (leaderboardRegion) leaderboardRegion.innerHTML = `<section class="leaderboard panel" aria-labelledby="leaderboard-title" id="leaderboard"></section>`;
  $("comparison").innerHTML = `
    ${leaderboardRegion ? "" : `<section class="leaderboard panel" aria-labelledby="leaderboard-title" id="leaderboard"></section>`}
    <section class="leaderboard-summary panel" aria-labelledby="leaderboard-summary-title" id="leaderboard-summary"></section>
    <section class="trajectory-overview panel" aria-labelledby="trajectory-overview-title" id="trajectory-overview"></section>
  `;
  renderComparisonPanels({ trace: false }, scrollState);
}
function notesFor(trialKey) {
  return (state.view?.annotations?.notes || []).filter(note => note.trial_key === trialKey);
}
function cellNoteFor(trialKey) {
  return notesFor(trialKey).find(note => note.source === "cell" && note.label === "notes.md") || null;
}
function analysisFor(trialKey) {
  return (state.view?.annotations?.analysis || []).find(item => item.trial_key === trialKey) || null;
}
function analysisArtifactPathsFor(trialKey) {
  const analysis = analysisFor(trialKey);
  if (!analysis) return [];
  const paths = [];
  listValue(analysis.markdown_reports).forEach(report => {
    if (typeof report?.relative_path === "string") paths.push(report.relative_path);
  });
  const relativePaths = analysis.relative_paths || {};
  if (typeof relativePaths === "object") {
    ["md", "json"].forEach(key => {
      if (typeof relativePaths[key] === "string") paths.push(relativePaths[key]);
    });
  }
  if (typeof analysis.relative_path === "string") paths.push(analysis.relative_path);
  return paths;
}
function isAnalysisArtifactPath(path) {
  const normalized = String(path || "").replace(/\\/g, "/");
  return normalized === "analysis.md" || normalized === "analysis.json" || normalized.endsWith("/analysis.md") || normalized.endsWith("/analysis.json");
}
function normalizeServeSourceMode(mode) {
  if (mode === "all") return "all";
  return mode === "archived" ? "archived" : "active";
}
function currentServeSourceMode() {
  return normalizeServeSourceMode(state.serveSourceMode);
}
function serveSourcesForMode(mode = currentServeSourceMode()) {
  return serveSourcesForModeFrom(state.serveSources, mode);
}
function serveSourcesForModeFrom(sources, mode = currentServeSourceMode()) {
  const sourceMode = normalizeServeSourceMode(mode);
  if (sourceMode === "all") return Array.isArray(sources) ? sources : [];
  return (Array.isArray(sources) ? sources : []).filter(source => {
    const active = source?.active !== false;
    return sourceMode === "archived" ? !active : active;
  });
}
function activeServeSources() {
  return serveSourcesForMode("active");
}
function readableServeSources(mode = currentServeSourceMode()) {
  return readableServeSourcesFrom(state.serveSources, mode);
}
function readableServeSourcesFrom(sources, mode = currentServeSourceMode()) {
  return serveSourcesForModeFrom(sources, mode).filter(source => source?.source_key && source?.artifact_dir && source?.last_status !== "missing");
}
function trialIndexForView(trialKey, view = state.view) {
  const metas = listValue(view?.trajectory_meta);
  return metas.findIndex(meta => meta?.trial_key === trialKey);
}
function editableNotesSource(trialKey) {
  const source = sourceForTrialKey(trialKey);
  if (!source || source.refreshable === false || source.snapshot) return null;
  return source;
}
function notesPlainText(notes) {
  return notes.map(note => String(note.markdown || "").trim()).filter(Boolean).join("\\n\\n");
}
function noteSnippetFor(trialKey) {
  const text = notesPlainText(notesFor(trialKey)).replace(/\\s+/g, " ").trim();
  if (!text) return "-";
  return text.length > 96 ? `${text.slice(0, 96)}...` : text;
}
function renderNotesCell(trialKey) {
  const summary = noteSnippetFor(trialKey);
  return summary === "-" ? `<span class="muted">-</span>` : `<span class="note-snippet">${esc(summary)}</span>`;
}
function sourceAliasFor(row) {
  return String(row?.source_alias || "").trim();
}
function sourceIdentityFor(row) {
  return row?.session_id || row?.trial_key || "-";
}
function sourceDisplayFor(row) {
  return sourceAliasFor(row) || String(row?.task_name || "").trim() || sourceIdentityFor(row);
}
function sessionAliasValue(row) {
  return sourceAliasFor(row) || String(row?.task_name || "").trim() || "-";
}
function renderTaskAlias(row) {
  const alias = sourceAliasFor(row);
  const task = String(row?.task_name || "").trim();
  if (alias && task) return `<span class="task-alias"><strong>${esc(alias)}</strong><small>${esc(task)}</small></span>`;
  const value = alias || task;
  return value ? `<span class="task-alias"><strong>${esc(value)}</strong></span>` : `<span class="muted">-</span>`;
}
function sourceCategoryForMeta(meta, source = null) {
  return sourceCategoryFromValue(meta?.source_category || source?.source_category);
}
function sourceCategoryFromValue(value) {
  return String(value || "").trim();
}
function sourceCategoryFor(row) {
  return sourceCategoryFromValue(row?.source_category);
}
function sourceCategoryValue(row) {
  return sourceCategoryFor(row) || "-";
}
function sourceCategoryEditValue(row) {
  return sourceCategoryFor(row);
}
function renderReadOnlySourceCategory(row) {
  const category = sourceCategoryFor(row);
  return category
    ? `<span class="source-category-chip">${esc(category)}</span>`
    : `<span class="muted">-</span>`;
}
function sourceTagsForMeta(meta, source = null) {
  const display = listValue(meta?.display_tags).length ? meta.display_tags : source?.display_tags;
  if (listValue(display).length) return sourceTagsFromValue(display);
  return mergeSourceTags(
    meta?.task_keywords || source?.task_keywords,
    meta?.source_tags || source?.source_tags,
  );
}
function sourceTagsFromValue(value) {
  const tags = [];
  const seen = new Set();
  listValue(value).forEach(rawTag => {
    const tag = String(rawTag || "").trim();
    const identity = tag.toLowerCase();
    if (!tag || seen.has(identity)) return;
    seen.add(identity);
    tags.push(tag);
  });
  return tags;
}
function sourceTagsFor(row) {
  return listValue(row?.display_tags).length
    ? sourceTagsFromValue(row.display_tags)
    : mergeSourceTags(row?.task_keywords, row?.source_tags);
}
function mergeSourceTags(...groups) {
  return sourceTagsFromValue(groups.flatMap(group => listValue(group)));
}
function sourceTagsValue(row) {
  return sourceTagsFor(row).join(", ") || "-";
}
function sourceTagsEditValue(row) {
  return sourceTagsFromValue(row?.source_tags).join(", ");
}
function renderReadOnlySourceTags(row) {
  const keywords = sourceTagsFromValue(row?.task_keywords);
  const custom = sourceTagsFromValue(row?.source_tags).filter(tag => !keywords.some(keyword => keyword.toLowerCase() === tag.toLowerCase()));
  const tags = [...keywords, ...custom];
  return tags.length
    ? `<span class="source-tag-list">${keywords.map(tag => `<span class="source-tag-chip derived" title="${esc(t("task_keyword_read_only", "Task keyword (read-only)"))}">${esc(tag)}</span>`).join("")}${custom.map(tag => `<span class="source-tag-chip custom" title="${esc(t("custom_tag", "Custom tag"))}">${esc(tag)}</span>`).join("")}</span>`
    : `<span class="muted">-</span>`;
}
function searchQuery() {
  return String(state.search?.query || "").trim().toLowerCase();
}
function searchScope() {
  return state.search?.scope === "all" ? "all" : "visible";
}
function allSearchActive() {
  return searchScope() === "all" && Boolean(searchQuery());
}
function applySessionSearch(rows) {
  const query = searchQuery();
  if (!query) return rows;
  return rows.filter(row => sessionSearchText(row).includes(query));
}
function sessionSearchText(row) {
  const trajectory = trajectoryFor(row?.trial_key);
  const meta = metaFor(row?.trial_key);
  const parts = [
    row?.task_name, row?.job_name, row?.trial_name, row?.model_provider,
    row?.source_alias, row?.display_alias, row?.source_category,
    searchJson(row?.task_keywords), searchJson(row?.source_tags),
    searchJson(row?.harbor_provenance), searchJson(row?.rewards),
    searchJson(row?.task_metadata),
  ];
  listValue(trajectory?.steps).forEach(step => {
    parts.push(step?.message, step?.reasoning_content);
    parts.push(searchJson(step?.tool_calls), searchJson(step?.observation), searchJson(step?.observations));
  });
  listValue(meta?.steps).forEach(step => {
    parts.push(searchJson(step?.tool_calls), searchJson(step?.observations));
  });
  return parts.filter(value => value !== null && value !== undefined).join("\n").replace(/\s+/g, " ").toLowerCase();
}
function searchJson(value) {
  if (value === null || value === undefined) return "";
  try {
    return typeof value === "string" ? value : JSON.stringify(value);
  } catch {
    return String(value || "");
  }
}
function renderComparisonPanels(
  options = {},
  scrollState = options.preserveScroll === false ? null : comparisonScrollState()
) {
  const rows = leaderboardRows();
  syncSelectionWithVisibleRows(rows);
  renderLeaderboard(rows);
  if ($("leaderboard-summary")) renderLeaderboardSummary();
  renderTrajectoryOverview(rows);
  restoreComparisonScrollState(scrollState);
  bindComparisonScrollSync();
  if (options.trace !== false) renderTrace();
  renderDetailSidebar();
}
function comparisonScrollState() {
  return {
    leaderboard: scrollPosition("#leaderboard .table-wrap", true),
    trajectoryOverview: scrollPosition("#trajectory-overview .trajectory-overview-list", false)
  };
}
function scrollPosition(selector, includeHorizontal) {
  const node = document.querySelector(selector);
  if (!node) return null;
  const position = { top: node.scrollTop || 0 };
  if (includeHorizontal) position.left = node.scrollLeft || 0;
  return position;
}
function restoreComparisonScrollState(state) {
  if (!state) return;
  restoreScrollPosition("#leaderboard .table-wrap", state.leaderboard);
  restoreScrollPosition("#trajectory-overview .trajectory-overview-list", state.trajectoryOverview);
}
function restoreScrollPosition(selector, position) {
  if (!position) return;
  const node = document.querySelector(selector);
  if (!node) return;
  node.scrollTop = position.top || 0;
  if (Object.prototype.hasOwnProperty.call(position, "left")) {
    node.scrollLeft = position.left || 0;
  }
}
function bindComparisonScrollSync() {
  const leaderboard = document.querySelector("#leaderboard .table-wrap");
  const overview = document.querySelector("#trajectory-overview .trajectory-overview-list");
  if (!leaderboard || !overview) return;
  leaderboard.addEventListener("scroll", () => syncComparisonScroll(leaderboard, overview), { passive: true });
  overview.addEventListener("scroll", () => syncComparisonScroll(overview, leaderboard), { passive: true });
}
function syncComparisonScroll(source, target) {
  if (state.comparisonScrollSyncing) return;
  const sourceRange = scrollRange(source);
  const targetRange = scrollRange(target);
  if (sourceRange <= 0 || targetRange <= 0) return;
  const targetTop = scrollProgress(source, sourceRange) * targetRange;
  state.comparisonScrollSyncing = true;
  const apply = () => {
    target.scrollTop = targetTop;
    const release = () => {
      state.comparisonScrollSyncing = false;
    };
    if (typeof requestAnimationFrame === "function") requestAnimationFrame(release);
    else release();
  };
  if (typeof requestAnimationFrame === "function") requestAnimationFrame(apply);
  else apply();
}
function scrollRange(node) {
  return Math.max(0, (node.scrollHeight || 0) - (node.clientHeight || 0));
}
function scrollProgress(node, range = scrollRange(node)) {
  if (range <= 0) return 0;
  return Math.max(0, Math.min(1, (node.scrollTop || 0) / range));
}
export {
  $,
  I18N,
  OPEN_SUBMENU_DETAILS_SELECTOR,
  RENDER_OPTIONS,
  SUBMENU_DETAILS_SELECTOR,
  activeServeSources,
  adminMode,
  adapterDefaults,
  allSearchActive,
  analysisArtifactPathsFor,
  analysisFor,
  authenticationEnabled,
  applySessionSearch,
  bindComparisonScrollSync,
  cellNoteFor,
  closeOpenSubmenus,
  comparisonScrollState,
  currentServeSourceMode,
  editableNotesSource,
  esc,
  finalMetricsFor,
  fmtCost,
  fmtDate,
  fmtMs,
  fmtNum,
  fmtPct,
  fmtScore,
  fmtTps,
  fmtTtft,
  hasMetricValue,
  initialAdapterDefaults,
  isAnalysisArtifactPath,
  listValue,
  lower,
  normalizeServeSourceMode,
  noteSnippetFor,
  notesFor,
  notesPlainText,
  readableServeSources,
  readableServeSourcesFrom,
  render,
  renderComparison,
  renderComparisonPanels,
  renderNotesCell,
  renderReadOnlySourceCategory,
  renderReadOnlySourceTags,
  renderWorkspaceDescription,
  renderTaskAlias,
  renderReportNotes,
  restoreComparisonScrollState,
  restoreScrollPosition,
  scriptJson,
  scrollPosition,
  scrollProgress,
  scrollRange,
  searchJson,
  searchQuery,
  searchScope,
  selectedIndex,
  selectedKey,
  serveSourcesForMode,
  serveSourcesForModeFrom,
  sessionAliasValue,
  sessionSearchText,
  sourceAliasFor,
  sourceCategoryEditValue,
  sourceCategoryFor,
  sourceCategoryForMeta,
  sourceCategoryFromValue,
  sourceCategoryValue,
  sourceDisplayFor,
  sourceIdentityFor,
  mergeSourceTags,
  sourceTagsEditValue,
  sourceTagsFor,
  sourceTagsForMeta,
  sourceTagsFromValue,
  sourceTagsValue,
  state,
  statusLabel,
  stepMeta,
  syncComparisonScroll,
  syncSelectedSourceFromView,
  synthesizedReportRow,
  t,
  trialIndexForView,
};
