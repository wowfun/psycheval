import { createColumnControl } from "./column-control.js";
import { validMetricId } from "../app/metric-contract.js";
import { metricDefinitions, formatMetric, metricSortKey, metricSearchText, metricProvenanceHint, hasPartialMetricCoverage } from "./metric-presentation.js";
import { renderDateTime } from "./date-time.js";
import { $, RENDER_OPTIONS, adminMode, canAnnotate, esc, fmtCost, fmtDate, fmtMs, fmtNum, fmtPct, fmtTps, fmtTtft, hasMetricValue, listValue, lower, modelDisplayName, statusLabel, t } from "./shared.js";
import { loadColumnLayout, normalizeColumnLayout, presenceForColumns, resolveColumns } from "./table-columns.js";
import { commentFullTooltip, commentPreviewText, commentStatusLabel, renderCommentCellPreview } from "./comments-ui.js";

import { configureDataTable, activeFilterValues, agentNameFor, bindDataTableControls, filterLabel, filterValues, renderDataSelection, renderDataTable, selectionColumn } from "./data-tables.js";

const requiredDependencies = ["state", "renderComparisonPanels", "renderReadOnlySourceCategory", "renderReadOnlySourceTags", "renderTaskAlias", "sessionAliasValue", "sourceCategoryEditValue", "sourceCategoryFor", "sourceCategoryValue", "sourceIdentityFor", "sourceTagsEditValue", "sourceTagsFor", "sourceTagsValue", "bindServeExportControls", "bindTrialSelection", "bindServeSourceStateControls", "bindLeaderboardSearchControls", "commitSourceCellEdit", "existingSourceCategoryOptions", "existingSourceTagOptions", "bindLeaderboardCatalogControls", "catalogSortKey", "filterOptions", "leaderboardRows", "openReviewCommentsModal", "renderLeaderboardPanelControls", "renderLeaderboardSearchControls", "reportRows", "requestCatalogFacets", "requestCatalogSort", "rowAnalysisCount", "bindWorkspaceReportLeaderboardControls", "workspaceReportLeaderboardColumn"];
let deps;

function configureLeaderboardDataTables(provided) {
  for (const key of Object.keys(provided)) {
    if (!requiredDependencies.includes(key)) throw new TypeError(`Unknown Leaderboard dependency: ${key}`);
  }
  for (const key of requiredDependencies) {
    if (key === "state" ? !provided.state || typeof provided.state !== "object" : typeof provided[key] !== "function") throw new TypeError(`Missing or invalid Leaderboard dependency: ${key}`);
  }
  deps = { ...provided };
  configureDataTable("leaderboard", {
    controls: () => deps.state.tables.leaderboard ||= {},
    isSorted: key => deps.catalogSortKey(metricSortKey(deps.state, deps.state.catalogQuery?.sort)) === deps.catalogSortKey(metricSortKey(deps.state, key)),
    direction: () => deps.state.catalogQuery?.direction,
    filterOptions: (column, rows) => deps.filterOptions(column, rows),
    onSort: key => deps.requestCatalogSort(key),
    onFilter: () => deps.requestCatalogFacets(),
  });
}

function leaderboardSelectionColumn() { return selectionColumn({ selectionSet: () => deps.state.rowSelection }); }

function metricColumn(key) {
  const definition = metricDefinitions(deps.state).find(item => item.key === key);
  if (!definition) return null;
  const valueFor = row => row.metric_values?.[key] ?? row[key];
  const showPartialCoverage = (value, row) => value != null && key !== "test_pass_rate"
    && hasPartialMetricCoverage(row.metric_provenance?.[key], row.family_coverage);
  const format = (value, row) => {
    if (key === "score" && value == null) return rewardValue(row);
    if (key === "test_pass_rate" && value != null) return `${fmtNum(row.metric_values?.tests_passed)} / ${fmtNum(row.metric_values?.tests_total)} (${fmtPct(value)})`;
    const suffix = showPartialCoverage(value, row) ? "*" : "";
    return formatMetric(definition, value) + suffix;
  };
  return {
    key: definition.column_key, label: definition.label, valueType: "number",
    description: definition.description || "",
    numeric: true, sortable: true, metric: true, defaultVisible: definition.column_default,
    value: valueFor,
    cellTitle: row => `${formatMetric(definition, row.metric_values?.[key] ?? row[key])}\n${metricProvenanceHint(row.metric_provenance?.[key], key, row.family_coverage)}`,
    ...(key === "score" ? { presence: row => row.metric_values?.score ?? row.score ?? Object.keys(row.rewards || {}) } : {}),
    format,
    html: row => {
      const value = valueFor(row);
      const hint = showPartialCoverage(value, row)
        ? `<span class="sr-only"> ${esc(t("coverage_partial", "partial coverage"))}</span>` : "";
      return esc(format(value, row)) + hint;
    },
  };
}
function leaderboardColumns() {
  const columns = [
    { key: "job_name", label: t("job", "Job"), valueType: "identity", filterable: true, sortable: true, value: row => row?.job_name || "-" },
    { key: "task_name", label: t("task_alias", "Task / Alias"), valueType: "text", filterable: true, filterValues: row => [row?.task_name].filter(Boolean), sortable: true, value: row => deps.sessionAliasValue(row), html: row => deps.renderTaskAlias(row), edit: adminMode() ? { value: row => String(row?.source_alias || ""), commit: (row, value) => deps.commitSourceCellEdit(row, "alias", value) } : undefined },
    { key: "agent", label: t("agent", "Agent"), valueType: "identity", filterable: true, value: row => agentNameFor(row) },
    { key: "model", label: t("model", "Model"), valueType: "identity", filterable: true, value: row => row.model || "-", format: modelDisplayName, filterLabel: modelDisplayName },
    { key: "model_provider", label: t("provider", "Provider"), valueType: "identity", defaultVisible: false, filterable: true, sortable: true, value: row => row?.model_provider || "-" },
    metricColumn("score"),
    { key: "status", label: t("result", "Result"), valueType: "status", filterable: true, value: row => row.status || "-", filterLabel: value => statusLabel(value), html: row => `<span class="stamp ${lower(row.status || "passed")}">${esc(statusLabel(row.status))}</span>` },
    {
      key: "review_comments",
      label: t("comments", "Comments"),
      valueType: "text",
      filterable: true,
      filterLabel: commentStatusLabel,
      filterValues: row => [(row?.review_comments_present || listValue(row?.review_comments).length > 0) ? "commented" : "uncommented"],
      value: row => commentPreviewText(row?.review_comments),
      cellTitle: row => commentFullTooltip(row?.review_comments),
      html: row => renderCommentCellPreview(row?.review_comments, {
        canAdd: canAnnotate(),
        ariaLabel: `${deps.sessionAliasValue(row) || row?.trial_key || ""} ${t("comments", "Comments")}`.trim(),
        buttonAttrs: `data-review-comments-open="${esc(row?.source_key || "")}"`,
      }),
    },
    { key: "finished_at_ms", label: t("last_turn_end", "Last Turn End"), valueType: "datetime", numeric: true, sortable: true, value: row => row.finished_at_ms, format: (value, row) => `${lastTurnEndHint(row) ? "≈ " : ""}${fmtDate(value)}`, html: renderLastTurnEnd, cellTitle: row => `${fmtDate(row.finished_at_ms)} · ${lastTurnEndHint(row)}\n${metricProvenanceHint(row.metric_provenance?.last_turn_finished_at_ms)}` },
    metricColumn("duration_ms"),
    metricColumn("ttft_ms"),
    metricColumn("tps"),
    metricColumn("agent_steps"),
    metricColumn("total_tool_calls"),
    metricColumn("tool_success_rate"),
    metricColumn("tokens"),
    metricColumn("cache_hit_rate"),
    metricColumn("cost_usd"),
    { key: "analysis_count", label: t("analysis_count", "#Analysis"), valueType: "number", numeric: true, filterable: true, value: row => deps.rowAnalysisCount(row) },
    { key: "notes", label: t("notes", "Notes"), valueType: "markdown", value: noteSnippetFor, html: renderNotesCell, cellTitle: row => {
      const text = notesText(row);
      return text && text !== noteSnippetFor(row) ? text : "";
    } },
    { key: "session_id", label: t("session", "Session"), valueType: "identity", filterable: true, value: row => deps.sourceIdentityFor(row), cellTitle: row => row.trial_key && row.trial_key !== deps.sourceIdentityFor(row) ? row.trial_key : "" }
  ];
  const availableColumns = columns.filter(Boolean);
  availableColumns.splice(availableColumns.findIndex(item => item.key === "analysis_count"), 0,
    ...metricDefinitions(deps.state).filter(item => !item.column_default).map(item => metricColumn(item.key)));
  const serveColumns = availableColumns.map(column => ["session_id", "analysis_count"].includes(column.key)
    ? { ...column, filterable: false }
    : column);
  return [
    { key: "dataset_id", label: t("dataset", "Dataset"), valueType: "identity", filterable: true, sortable: true, value: row => row?.dataset_id || "-" },
    { key: "source_category", label: t("category", "Category"), valueType: "text", filterable: true, filterValues: row => [deps.sourceCategoryFor(row)].filter(Boolean), value: row => deps.sourceCategoryValue(row), html: row => deps.renderReadOnlySourceCategory(row), edit: adminMode() ? { value: row => deps.sourceCategoryEditValue(row), suggestions: deps.existingSourceCategoryOptions, commit: (row, value) => deps.commitSourceCellEdit(row, "category", value) } : undefined },
    { key: "source_tags", label: t("tags", "Tags"), valueType: "list", filterable: true, filterValues: row => deps.sourceTagsFor(row), value: row => deps.sourceTagsValue(row), html: row => deps.renderReadOnlySourceTags(row), edit: adminMode() ? { value: row => deps.sourceTagsEditValue(row), suggestions: deps.existingSourceTagOptions, commit: (row, value) => deps.commitSourceCellEdit(row, "tags", value) } : undefined },
    ...serveColumns.slice(0, 2),
    deps.workspaceReportLeaderboardColumn(),
    ...serveColumns.slice(2)
  ];
}
function lastTurnEndHint(row) {
  if (!hasMetricValue(row?.finished_at_ms)) return "";
  if (row?.last_turn_finished_at_source === "harbor_agent_execution") return t("last_turn_end_from_agent_execution", "Approximate: Agent execution finished");
  if (row?.last_turn_finished_at_source === "harbor_trial") return t("last_turn_end_from_trial", "Approximate: Trial finished");
  return "";
}
function renderLastTurnEnd(row) {
  const time = renderDateTime(row.finished_at_ms);
  const hint = lastTurnEndHint(row);
  return hint ? `<span title="${esc(hint)}">≈ <span class="sr-only">${esc(hint)}: </span>${time}</span>` : time;
}
function notesText(row) {
  return String(row?.notes_markdown || "").trim();
}
function noteSnippetFor(row) {
  const text = notesText(row).replace(/\s+/g, " ");
  if (!text) return "-";
  return text.length > 96 ? `${text.slice(0, 96)}...` : text;
}
function renderNotesCell(row) {
  const summary = noteSnippetFor(row);
  return summary === "-" ? `<span class="muted">-</span>` : `<span class="note-snippet">${esc(summary)}</span>`;
}
function rewardValue(row) {
  if (hasMetricValue(row?.score)) return fmtNum(row.score);
  const count = row?.rewards && typeof row.rewards === "object" ? Object.keys(row.rewards).length : 0;
  return count ? `${count} ${t("reward_dimensions_short", "dims")}` : "-";
}
function columnStorage() {
  if (typeof window === "undefined") return null;
  try { return window.localStorage; } catch { return null; }
}
function cloneColumnLayout(layout) { return structuredClone(layout); }
function leaderboardColumnLayout(columns = leaderboardColumns()) {
  if (!deps.state.leaderboardColumnLayout) {
    deps.state.leaderboardColumnLayout = loadColumnLayout(columns.map(column => column.key), {
      workspaceId: RENDER_OPTIONS?.workspace_id,
      storage: columnStorage(),
      retainUnknown: key => key.includes(":") && validMetricId(key),
    });
  }
  return normalizeColumnLayout(columns.map(column => column.key), deps.state.leaderboardColumnLayout, columnOptions());
}
function currentLeaderboardColumnLayout() {
  return cloneColumnLayout(leaderboardColumnLayout());
}
function leaderboardColumnContext(rows = deps.leaderboardRows()) {
  const columns = leaderboardColumns();
  const layout = leaderboardColumnLayout(columns);
  const serverPresence = deps.state.catalogPage?.column_presence;
  const presence = presenceForColumns(
    columns,
    rows,
    serverPresence,
    key => activeFilterValues("leaderboard", key),
  );
  if (canAnnotate() && rows.length > 0) presence.review_comments = true;
  return { columns, layout, presence };
}
function displayLeaderboardColumns(rows = deps.leaderboardRows()) {
  const { columns, layout, presence } = leaderboardColumnContext(rows);
  const displayed = resolveColumns(columns, layout, presence);
  return [leaderboardSelectionColumn(), ...displayed];
}
const columnOptions = () => ({ workspaceId: RENDER_OPTIONS?.workspace_id, storage: columnStorage(), retainUnknown: key => key.includes(":") && validMetricId(key) });
const columnControl = createColumnControl({
  id: "leaderboard", state: {
    get draft() { return deps.state.leaderboardColumnDraft; }, set draft(value) { deps.state.leaderboardColumnDraft = value; },
    get search() { return deps.state.leaderboardColumnSearch; }, set search(value) { deps.state.leaderboardColumnSearch = value; },
    get layout() { return deps.state.leaderboardColumnLayout; }, set layout(value) { deps.state.leaderboardColumnLayout = value; },
  },
  context: rows => leaderboardColumnContext(rows),
  onRender: () => { renderLeaderboard(deps.leaderboardRows()); return $("leaderboard"); },
  searchText: column => metricSearchText(column.label, column.key),
  conditionText: column => {
    const sorted = deps.catalogSortKey(metricSortKey(deps.state, deps.state.catalogQuery?.sort)) === deps.catalogSortKey(metricSortKey(deps.state, column.key));
    return [sorted ? deps.state.catalogQuery?.direction : "", activeFilterValues("leaderboard", column.key).length ? t("filtered", "Filtered") : ""].filter(Boolean).join(" · ");
  },
  options: { get workspaceId() { return columnOptions().workspaceId; }, get storage() { return columnStorage(); }, retainUnknown: key => key.includes(":") && validMetricId(key) },
});
function renderLeaderboardColumnControls(rows = deps.leaderboardRows()) { return columnControl.render(rows); }
function bindLeaderboardColumnControls(target) { columnControl.bind(target); }
function renderLeaderboard(rows = deps.leaderboardRows()) {
  const target = $("leaderboard");
  if (!target) return;
  const activeMenu = target.contains(document.activeElement) ? document.activeElement.closest(".toolbar-menu") : null;
  const focusSelector = activeMenu ? `.${activeMenu.classList.contains("toolbar-view-menu") ? "toolbar-view-menu" : "toolbar-actions-menu"} > summary` : null;
  const columns = displayLeaderboardColumns(rows);
  target.innerHTML = `
    <div class="panel-head leaderboard-panel-head">
      <div class="leaderboard-title-stack">
        <div class="leaderboard-heading"><h2 id="leaderboard-title">${esc(t("leaderboard", "Leaderboard"))}</h2><div data-leaderboard-status></div></div>
        ${deps.renderLeaderboardSearchControls()}
      </div>
      ${deps.renderLeaderboardPanelControls(rows)}
    </div>
    ${renderDataTable({
      tableId: "leaderboard",
      columns,
      rows,
      rowKey: row => row.source_key || row.trial_key,
      rowClass: row => `clickable-row ${row.source_key === deps.state.selectedSourceKey ? "selected-row" : ""}`,
      rowAttrs: row => `data-source-key="${esc(row.source_key)}"`,
      rowTitle: row => row.artifact_trial_key || row.trial_key,
    })}
`;
  bindLeaderboardControls();
  if (focusSelector) target.querySelector(focusSelector)?.focus({ preventScroll: true });
}
function renderLeaderboardExportControls() {
  return `<div class="leaderboard-export">
    <details class="export-menu">
      <summary class="export-menu-button" aria-label="${esc(t("export_options", "Export options"))}">${esc(t("export", "Export"))}</summary>
      <div class="export-menu-panel">
        <button type="button" data-export-kind="xlsx">${esc(t("export_xlsx_table", "Table (.xlsx)"))}</button>
        <button type="button" data-export-kind="json">${esc(t("export_json_report", "JSON report"))}</button>
      </div>
    </details>
  </div>`;
}
function renderRowSelection(row) {
  return renderDataSelection(row, leaderboardSelectionColumn());
}
function bindLeaderboardControls() {
  const target = $("leaderboard");
  if (!target) return;
  const rows = deps.leaderboardRows();
  bindDataTableControls(target, {
    tableId: "leaderboard",
    columns: displayLeaderboardColumns(rows),
    rows,
    rowKey: row => row.source_key || row.trial_key,
    onChange: () => deps.renderComparisonPanels({ refreshDetail: false }),
    onSelectionChange: () => deps.renderComparisonPanels({ refreshDetail: false }),
  });
  deps.bindServeSourceStateControls(target);
  deps.bindServeExportControls(target);
  deps.bindLeaderboardSearchControls(target);
  deps.bindWorkspaceReportLeaderboardControls(target);
  deps.bindTrialSelection(target);
  deps.bindLeaderboardCatalogControls(target);
  bindLeaderboardColumnControls(target);
  const rowBySource = new Map(rows.map(row => [String(row?.source_key || ""), row]));
  target.querySelectorAll("[data-review-comments-open]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      const row = rowBySource.get(button.dataset.reviewCommentsOpen);
      if (row) deps.openReviewCommentsModal(row, button);
    });
  });
}
export { bindLeaderboardControls, bindLeaderboardColumnControls, configureLeaderboardDataTables, currentLeaderboardColumnLayout, displayLeaderboardColumns, leaderboardColumns, renderLeaderboard, renderLeaderboardColumnControls, renderLeaderboardExportControls, renderRowSelection, leaderboardSelectionColumn };
