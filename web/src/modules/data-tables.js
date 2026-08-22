import { $, RENDER_OPTIONS, WORKSPACE_SNAPSHOT, adminMode, esc, fmtCost, fmtDate, fmtMs, fmtNum, fmtPct, fmtTps, fmtTtft, hasMetricValue, listValue, lower, noteSnippetFor, notesFor, notesPlainText, renderComparisonPanels, renderNotesCell, renderReadOnlySourceCategory, renderReadOnlySourceTags, renderTaskAlias, selectedKey, serveMode, sessionAliasValue, sourceCategoryEditValue, sourceCategoryFor, sourceCategoryValue, sourceIdentityFor, sourceTagsEditValue, sourceTagsFor, sourceTagsValue, state, statusLabel, t, workspaceDisplayMode, workspaceSnapshotMode } from "./runtime.js";
import { bindServeExportControls, bindTrialSelection } from "./export.js";
import { bindServeSourceStateControls } from "./source-state-controls.js";
import { bindLeaderboardSearchControls, commitSourceCellEdit, existingSourceCategoryOptions, existingSourceTagOptions } from "./serve-effects.js";
import { bindLeaderboardCatalogControls, catalogSortKey, filterOptions, leaderboardRows, renderLeaderboardPanelControls, renderLeaderboardSearchControls, reportRows, requestCatalogFacets, requestCatalogSort, rowAnalysisCount, trajectoryFor } from "./serve-catalog.js";
import { bindWorkspaceReportLeaderboardControls, workspaceReportLeaderboardColumn } from "./workspace-reports.js";
import { columnVisibleForLayout, loadColumnLayout, moveColumn, normalizeColumnLayout, presenceForColumns, resolveColumns, saveColumnLayout } from "./leaderboard-columns.js";

function selectionColumn(options = {}) {
  return {
    key: "__select",
    valueType: "selection",
    select: true,
    label: t("select_rows", "Select rows"),
    selectionKey: row => row?.trial_key || "",
    selectionSet: () => state.rowSelection,
    rowAriaLabel: key => `${t("select_row_for_export", "Select row for export")}: ${key}`,
    ...options,
  };
}
function leaderboardColumns() {
  const columns = [
    { key: "job_name", label: t("job", "Job"), valueType: "identity", filterable: true, sortable: true, value: row => row?.job_name || "-" },
    { key: "task_name", label: t("task_alias", "Task / Alias"), valueType: "text", filterable: true, filterValues: row => [row?.task_name].filter(Boolean), sortable: true, value: row => sessionAliasValue(row), html: row => renderTaskAlias(row), edit: adminMode() ? { value: row => String(row?.source_alias || ""), commit: (row, value) => commitSourceCellEdit(row, "alias", value) } : undefined },
    { key: "agent", label: t("agent", "Agent"), valueType: "identity", filterable: true, value: row => agentNameFor(row) },
    { key: "model", label: t("model", "Model"), valueType: "identity", filterable: true, value: row => row.model || "-" },
    { key: "model_provider", label: t("provider", "Provider"), valueType: "identity", defaultVisible: false, filterable: true, sortable: true, value: row => row?.model_provider || "-" },
    { key: "reward", label: t("reward", "Reward"), valueType: "number", numeric: true, sortable: true, metric: true, value: row => row?.score, presence: row => hasMetricValue(row?.score) ? row.score : Object.keys(row?.rewards || {}), format: (_value, row) => rewardValue(row) },
    { key: "status", label: t("result", "Result"), valueType: "status", filterable: true, value: row => row.status || "-", filterLabel: value => statusLabel(value), html: row => `<span class="stamp ${lower(row.status || "passed")}">${esc(statusLabel(row.status))}</span>` },
    { key: "finished_at_ms", label: t("last_turn_end", "Last Turn End"), valueType: "datetime", numeric: true, sortable: true, value: row => row.finished_at_ms, format: fmtDate },
    { key: "duration_ms", label: t("duration", "Active Duration"), valueType: "number", numeric: true, sortable: true, metric: true, value: row => row.duration_ms, format: fmtMs },
    { key: "ttft_ms", label: t("avg_ttft", "Avg TTFT"), valueType: "number", numeric: true, sortable: true, metric: true, value: row => row.ttft_ms, format: fmtTtft },
    { key: "tps", label: t("decode_tps", "Decode TPS"), valueType: "number", numeric: true, sortable: true, metric: true, value: row => row.tps, format: fmtTps },
    { key: "turns", label: t("turns", "Turns"), valueType: "number", numeric: true, sortable: true, metric: true, value: row => row.turns, format: fmtNum },
    { key: "total_tool_calls", label: t("tool_calls", "Tool Calls"), valueType: "number", numeric: true, sortable: true, metric: true, value: row => row.total_tool_calls, format: value => hasMetricValue(value) ? fmtNum(value) : "-" },
    { key: "tool_error_rate", label: t("tool_error_rate", "Tool Error Rate"), valueType: "number", numeric: true, sortable: true, metric: true, value: row => rowToolErrorRate(row), format: fmtPct },
    { key: "tokens", label: t("tokens", "Tokens"), valueType: "number", numeric: true, sortable: true, metric: true, value: row => row.tokens, format: fmtNum },
    { key: "cache_hit_rate", label: t("cache_hit", "Cache Hit"), valueType: "number", numeric: true, sortable: true, metric: true, value: row => row.cache_hit_rate, format: fmtPct },
    { key: "cost_usd", label: t("cost", "Cost"), valueType: "number", numeric: true, sortable: true, value: row => row.cost_usd, format: fmtCost },
    { key: "analysis_count", label: t("analysis_count", "#Analysis"), valueType: "number", numeric: true, filterable: true, value: row => rowAnalysisCount(row) },
    { key: "notes", label: t("notes", "Notes"), valueType: "markdown", value: row => noteSnippetFor(row.trial_key), html: row => renderNotesCell(row.trial_key), cellTitle: row => {
      const text = notesPlainText(notesFor(row.trial_key));
      return text && text !== noteSnippetFor(row.trial_key) ? text : "";
    } },
    { key: "session_id", label: t("session", "Session"), valueType: "identity", filterable: true, value: row => sourceIdentityFor(row), cellTitle: row => row.trial_key && row.trial_key !== sourceIdentityFor(row) ? row.trial_key : "" }
  ];
  if (!workspaceDisplayMode()) return columns;
  const serveColumns = columns.map(column => ["session_id", "analysis_count"].includes(column.key)
    ? { ...column, filterable: false }
    : column);
  return [
    { key: "source_category", label: t("category", "Category"), valueType: "text", filterable: true, filterValues: row => [sourceCategoryFor(row)].filter(Boolean), value: row => sourceCategoryValue(row), html: row => renderReadOnlySourceCategory(row), edit: adminMode() ? { value: row => sourceCategoryEditValue(row), suggestions: existingSourceCategoryOptions, commit: (row, value) => commitSourceCellEdit(row, "category", value) } : undefined },
    { key: "source_tags", label: t("tags", "Tags"), valueType: "list", filterable: true, filterValues: row => sourceTagsFor(row), value: row => sourceTagsValue(row), html: row => renderReadOnlySourceTags(row), edit: adminMode() ? { value: row => sourceTagsEditValue(row), suggestions: existingSourceTagOptions, commit: (row, value) => commitSourceCellEdit(row, "tags", value) } : undefined },
    ...serveColumns.slice(0, 2),
    workspaceReportLeaderboardColumn(),
    ...serveColumns.slice(2)
  ];
}
function rewardValue(row) {
  if (hasMetricValue(row?.score)) return fmtNum(row.score);
  const count = row?.rewards && typeof row.rewards === "object" ? Object.keys(row.rewards).length : 0;
  return count ? `${count} ${t("reward_dimensions_short", "dims")}` : "-";
}
function columnStorage() {
  if (!serveMode() || typeof window === "undefined") return null;
  try { return window.localStorage; } catch { return null; }
}
function cloneColumnLayout(layout) { return JSON.parse(JSON.stringify(layout)); }
function leaderboardColumnLayout(columns = leaderboardColumns()) {
  if (!state.leaderboardColumnLayout) {
    state.leaderboardColumnLayout = loadColumnLayout(columns.map(column => column.key), {
      workspaceId: RENDER_OPTIONS?.workspace_id,
      snapshotLayout: workspaceSnapshotMode() ? WORKSPACE_SNAPSHOT?.presentation?.leaderboard_columns : null,
      storage: columnStorage(),
    });
  }
  return normalizeColumnLayout(columns.map(column => column.key), state.leaderboardColumnLayout);
}
function currentLeaderboardColumnLayout() {
  return cloneColumnLayout(leaderboardColumnLayout());
}
function leaderboardColumnContext(rows = leaderboardRows()) {
  const columns = leaderboardColumns();
  const layout = leaderboardColumnLayout(columns);
  const serverPresence = serveMode() ? state.catalogPage?.column_presence : null;
  const presence = presenceForColumns(columns, rows, serverPresence);
  return { columns, layout, presence };
}
function displayLeaderboardColumns(rows = leaderboardRows()) {
  const { columns, layout, presence } = leaderboardColumnContext(rows);
  const displayed = resolveColumns(columns, layout, presence);
  return serveMode() ? [selectionColumn(), ...displayed] : displayed;
}
function renderLeaderboardColumnControls(rows = leaderboardRows()) {
  if (!workspaceDisplayMode()) return "";
  const { columns, layout, presence } = leaderboardColumnContext(rows);
  const draft = state.leaderboardColumnDraft
    ? normalizeColumnLayout(columns.map(column => column.key), state.leaderboardColumnDraft)
    : layout;
  const ordered = draft.order.map(key => columns.find(column => column.key === key)).filter(Boolean);
  const checked = column => columnVisibleForLayout(column, draft, presence);
  const visibleCount = ordered.filter(checked).length;
  const rowsHtml = ordered.map((column, index) => {
    const isChecked = checked(column);
    const activeSort = serveMode()
      ? catalogSortKey(state.catalogQuery?.sort) === catalogSortKey(column.key)
      : tableControls("leaderboard").sort === column.key;
    const filtered = activeFilterValues("leaderboard", column.key).length > 0;
    const condition = [activeSort ? (serveMode() ? state.catalogQuery?.direction : tableControls("leaderboard").direction) : "", filtered ? t("filtered", "Filtered") : ""].filter(Boolean).join(" · ");
    return `<li class="column-control-row${isChecked ? "" : " hidden-column"}" data-column-row="${esc(column.key)}">
      <span class="column-control-index">${String(index + 1).padStart(2, "0")}</span>
      <label><input type="checkbox" data-column-visible="${esc(column.key)}" ${isChecked ? "checked" : ""}><span>${esc(column.label)}</span></label>
      <span class="column-control-state">${presence[column.key] ? "" : esc(t("no_data", "No data"))}${condition ? `<small>${esc(condition)}</small>` : ""}</span>
      <span class="column-control-moves"><button type="button" data-column-move="${esc(column.key)}" data-column-direction="-1" aria-label="${esc(`${t("move_earlier", "Move earlier")}: ${column.label}`)}" ${index === 0 ? "disabled" : ""}>↑</button><button type="button" data-column-move="${esc(column.key)}" data-column-direction="1" aria-label="${esc(`${t("move_later", "Move later")}: ${column.label}`)}" ${index === ordered.length - 1 ? "disabled" : ""}>↓</button></span>
    </li>`;
  }).join("");
  return `<details class="column-control" ${state.leaderboardColumnDraft ? "open" : ""}>
    <summary class="action-button column-control-button">${esc(t("columns", "Columns"))} ${visibleCount}/${ordered.length}</summary>
    <div class="column-control-panel">
      <div class="column-control-head"><strong>${esc(t("columns", "Columns"))}</strong><button type="button" data-column-reset>${esc(t("reset_auto", "Reset to auto"))}</button></div>
      <ol class="column-control-list">${rowsHtml}</ol>
      <div class="column-control-foot"><span aria-live="polite">${esc(`${visibleCount} / ${ordered.length}`)}</span><button type="button" class="action-button primary" data-column-apply>${esc(t("apply", "Apply"))}</button></div>
    </div>
  </details>`;
}
function renderLeaderboardAndRestoreColumnFocus(findControl) {
  renderLeaderboard(leaderboardRows());
  const root = $("leaderboard");
  let control = findControl(root);
  if (control?.disabled) {
    const row = control.closest("[data-column-row]");
    row?.setAttribute("tabindex", "-1");
    control = row;
  }
  control?.focus();
}
function bindLeaderboardColumnControls(target) {
  const details = target?.querySelector?.(".column-control");
  if (!details) return;
  details.addEventListener("toggle", () => {
    if (details.open && !state.leaderboardColumnDraft) {
      state.leaderboardColumnDraft = cloneColumnLayout(leaderboardColumnLayout());
    } else if (!details.open) {
      state.leaderboardColumnDraft = null;
    }
  });
  details.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    state.leaderboardColumnDraft = null;
    details.open = false;
    details.querySelector("summary")?.focus();
  });
  details.querySelectorAll("[data-column-visible]").forEach(input => {
    input.addEventListener("change", () => {
      const columnKey = input.dataset.columnVisible;
      const draft = state.leaderboardColumnDraft || cloneColumnLayout(leaderboardColumnLayout());
      draft.visibility[columnKey] = input.checked ? "show" : "hide";
      state.leaderboardColumnDraft = draft;
      renderLeaderboardAndRestoreColumnFocus(root => Array.from(
        root?.querySelectorAll?.("[data-column-visible]") || []
      ).find(control => control.dataset.columnVisible === columnKey));
    });
  });
  details.querySelectorAll("[data-column-move]").forEach(button => {
    button.addEventListener("click", () => {
      const columnKey = button.dataset.columnMove;
      const direction = button.dataset.columnDirection;
      const draft = state.leaderboardColumnDraft || cloneColumnLayout(leaderboardColumnLayout());
      draft.order = moveColumn(draft.order, columnKey, Number(direction));
      state.leaderboardColumnDraft = draft;
      renderLeaderboardAndRestoreColumnFocus(root => Array.from(
        root?.querySelectorAll?.("[data-column-move]") || []
      ).find(control => control.dataset.columnMove === columnKey && control.dataset.columnDirection === direction));
    });
  });
  details.querySelector("[data-column-reset]")?.addEventListener("click", () => {
    state.leaderboardColumnDraft = normalizeColumnLayout(leaderboardColumns().map(column => column.key), null);
    renderLeaderboardAndRestoreColumnFocus(root => root?.querySelector?.("[data-column-reset]"));
  });
  details.querySelector("[data-column-apply]")?.addEventListener("click", () => {
    state.leaderboardColumnLayout = normalizeColumnLayout(leaderboardColumns().map(column => column.key), state.leaderboardColumnDraft);
    saveColumnLayout(state.leaderboardColumnLayout, { workspaceId: RENDER_OPTIONS?.workspace_id, storage: columnStorage() });
    state.leaderboardColumnDraft = null;
    renderLeaderboardAndRestoreColumnFocus(root => root?.querySelector?.(".column-control > summary"));
  });
}
function agentNameFor(row) {
  if (workspaceDisplayMode()) return row?.agent_name || row?.adapter || "-";
  const name = trajectoryFor(row?.trial_key)?.agent?.name;
  return name || row?.adapter || "-";
}
function rowToolErrorRate(row) {
  if (!hasMetricValue(row?.total_tool_calls) || Number(row.total_tool_calls) === 0) return null;
  return Number(row.total_tool_errors || 0) / Number(row.total_tool_calls);
}
function renderLeaderboard(rows = leaderboardRows()) {
  const target = $("leaderboard");
  if (!target) return;
  const columns = displayLeaderboardColumns(rows);
  target.innerHTML = `
    <div class="panel-head leaderboard-panel-head">
      <div class="leaderboard-title-stack">
        <h2 id="leaderboard-title">${esc(t("leaderboard", "Leaderboard"))}</h2>
        ${renderLeaderboardSearchControls()}
      </div>
      ${renderLeaderboardPanelControls(rows)}
    </div>
    ${renderDataTable({
      tableId: "leaderboard",
      columns,
      rows,
      rowKey: row => row.source_key || row.trial_key,
      filterOptionsRows: reportRows(),
      rowClass: row => `clickable-row ${(serveMode() ? row.source_key === state.selectedSourceKey : row.trial_key === selectedKey()) ? "selected-row" : ""}`,
      rowAttrs: row => serveMode()
        ? `data-source-key="${esc(row.source_key)}"`
        : `data-trial-key="${esc(row.trial_key)}"`,
      rowTitle: row => serveMode() ? (row.artifact_trial_key || row.trial_key) : row.trial_key,
    })}
`;
  bindLeaderboardControls();
}
function renderLeaderboardExportControls() {
  if (!serveMode()) return "";
  return `<div class="leaderboard-export" data-serve-only>
    <details class="export-menu">
      <summary class="export-menu-button" aria-label="${esc(t("export_options", "Export options"))}">${esc(t("export", "Export"))}</summary>
      <div class="export-menu-panel">
        <button type="button" data-export-kind="xlsx">${esc(t("export_xlsx_table", "Table (.xlsx)"))}</button>
        <button type="button" data-export-kind="json">${esc(t("export_json_report", "JSON report"))}</button>
        <button type="button" data-export-kind="workspace_html">${esc(t("export_workspace_snapshot", "Workspace snapshot (.html)"))}</button>
      </div>
    </details>
  </div>`;
}
function tableControls(tableId) {
  const controls = state.tables[tableId] || {};
  if (!Object.prototype.hasOwnProperty.call(controls, "sort")) controls.sort = null;
  controls.direction ||= "asc";
  controls.filters ||= {};
  state.tables[tableId] = controls;
  return controls;
}
function filterableColumns(columns) {
  return columns.filter(column => column.filterable);
}
function activeFilterValues(tableId, key) {
  const values = tableControls(tableId).filters?.[key];
  return Array.isArray(values) ? values : [];
}
function filterValue(row, column) {
  return filterValues(row, column)[0] || "-";
}
function filterValues(row, column) {
  if (column.filterValues) {
    return listValue(column.filterValues(row)).map(value => String(value || "").trim()).filter(Boolean);
  }
  const source = column.filterValue || column.value || (item => item?.[column.key]);
  const raw = source(row);
  const text = raw === null || raw === undefined || raw === "" ? "-" : String(raw);
  return [text];
}
function filterLabel(column, value) {
  return column.filterLabel ? column.filterLabel(value) : value;
}
function applyDataTableFilters(tableId, rows, columns) {
  const activeColumns = filterableColumns(columns);
  return rows.filter(row => columns.every(column => {
    if (!activeColumns.includes(column)) return true;
    const selected = activeFilterValues(tableId, column.key);
    if (!selected.length) return true;
    const values = filterValues(row, column);
    return values.some(value => selected.includes(value));
  }));
}
function setFilterValues(tableId, key, values) {
  const controls = tableControls(tableId);
  const selected = Array.from(new Set(listValue(values).map(value => String(value))));
  if (selected.length) controls.filters[key] = selected;
  else delete controls.filters[key];
}
function setFilterValue(tableId, key, value, checked) {
  const selected = new Set(activeFilterValues(tableId, key));
  if (checked) selected.add(value);
  else selected.delete(value);
  setFilterValues(tableId, key, Array.from(selected));
}
function clearFilter(tableId, key) {
  delete tableControls(tableId).filters[key];
}
function toggleDataTableSort(tableId, key) {
  const controls = tableControls(tableId);
  if (controls.sort !== key) {
    controls.sort = key;
    controls.direction = "asc";
    return;
  }
  if (controls.direction === "asc") {
    controls.direction = "desc";
    return;
  }
  controls.sort = null;
  controls.direction = "asc";
}
function selectedStepExists(selection) {
  if (!selection) return true;
  const { trialKey, stepId } = selection;
  const metas = state.view?.trajectory_meta || [];
  const index = metas.findIndex(meta => meta.trial_key === trialKey);
  if (index < 0) return false;
  const steps = (state.view?.trajectory || [])[index]?.steps || [];
  return steps.some(step => String(step.step_id) === String(stepId));
}
function selectedStepVisible(rows) {
  if (!state.selectedStep) return true;
  const { trialKey, stepId } = state.selectedStep;
  if (!rows.some(row => row.trial_key === trialKey)) return false;
  return selectedStepExists({ trialKey, stepId });
}
function compareTableValues(left, right, type, direction) {
  const leftMissing = left === null || left === undefined || left === "" || (type === "number" && Number.isNaN(Number(left)));
  const rightMissing = right === null || right === undefined || right === "" || (type === "number" && Number.isNaN(Number(right)));
  if (leftMissing || rightMissing) return leftMissing === rightMissing ? 0 : leftMissing ? 1 : -1;
  const delta = type === "number" ? Number(left) - Number(right) : String(left).localeCompare(String(right), undefined, { numeric: true, sensitivity: "base" });
  return direction === "desc" ? -delta : delta;
}
function applyDataTableControls(tableId, rows, columns, filterOptionsRows = rows) {
  const controls = tableControls(tableId);
  const filtered = applyDataTableFilters(tableId, rows, columns, filterOptionsRows);
  const sortColumn = columns.find(column => column.key === controls.sort && column.sortable);
  const out = [...filtered];
  if (sortColumn) out.sort((left, right) => compareTableValues(sortColumn.value(left), sortColumn.value(right), tableSortType(sortColumn), controls.direction));
  return out;
}
const TABLE_VALUE_TYPES = new Set(["selection", "number", "datetime", "status", "enum", "text", "list", "scalar-list", "identity", "path", "markdown", "yaml"]);
function tableValueType(column = {}) {
  const explicit = String(column.valueType || "").toLowerCase();
  if (TABLE_VALUE_TYPES.has(explicit)) return explicit;
  if (column.select || column.sourceSelect) return "selection";
  if (column.numeric || column.type === "number") return "number";
  return "text";
}
function tableSortType(column = {}) {
  const valueType = tableValueType(column);
  return valueType === "number" || valueType === "datetime" ? "number" : "text";
}
function tableText(row, column) {
  const raw = column.value(row);
  return column.format ? column.format(raw, row) : (raw ?? "-");
}
function tableFullText(row, column) {
  const text = column.fullText ? column.fullText(row) : tableText(row, column);
  if (Array.isArray(text)) return text.join(", ");
  return String(text ?? "");
}
function tableValueAttributes(valueType, fullText = "", className = "") {
  const type = tableValueType({ valueType });
  const label = String(fullText ?? "");
  const classes = [className, `table-value-${type}`].filter(Boolean).join(" ");
  return `class="${esc(classes)}" data-value-type="${esc(type)}"${label ? ` title="${esc(label)}" aria-label="${esc(label)}"` : ""}`;
}
function tableCellContent(html) {
  return `<div class="table-cell-content">${html}</div>`;
}
function renderDataTable({ tableId, columns, rows, rowKey = null, tableClass = "", shellClass = "", rowClass = "", rowAttrs = "", rowTitle = null, emptyText = null, filterOptionsRows = rows }) {
  const controls = tableControls(tableId);
  const headers = columns.map(column => renderTableHeader(tableId, column, controls, rows, filterOptionsRows)).join("");
  const rowOptions = { rowClass, rowAttrs, rowTitle, rowKey };
  const body = rows.length
    ? rows.map(row => renderTableRow(row, columns, rows, rowOptions)).join("")
    : `<tr><td class="table-empty" colspan="${columns.length}">${esc(emptyText || t("no_matching_rows", "No matching rows"))}</td></tr>`;
  const classes = ["data-table", tableClass].filter(Boolean).join(" ");
  const shellClasses = ["table-shell", shellClass].filter(Boolean).join(" ");
  return `<div class="${esc(shellClasses)}"><div class="table-wrap"><table class="${esc(classes)}" data-table-id="${esc(tableId)}"><thead><tr>${headers}</tr></thead><tbody>${body}</tbody></table></div></div>`;
}
function renderTableHeader(tableId, column, controls, rows = [], filterOptionsRows = rows) {
  if (column.select) return renderSelectionHeader(rows, column);
  const catalogSort = serveMode() && tableId === "leaderboard";
  const active = catalogSort
    ? catalogSortKey(state.catalogQuery?.sort) === catalogSortKey(column.key)
    : controls.sort === column.key;
  const direction = catalogSort ? state.catalogQuery?.direction : controls.direction;
  const mark = active ? (direction === "desc" ? "&#9660;" : "&#9650;") : "&#8597;";
  const label = column.sortable
    ? `<button class="sort-button ${active ? "active" : ""}" type="button" data-table-sort="${esc(column.key)}" aria-label="${esc(t("sort", "Sort"))} ${esc(column.label)}"><span class="sort-label">${esc(column.label)}</span><span class="sort-mark">${mark}</span></button>`
    : `<span class="static-head">${esc(column.label)}</span>`;
  const filter = column.filterable ? renderFilterControl(tableId, column, filterOptionsRows) : "";
  const contentClass = column.filterable ? "table-head-cell table-head-inline" : "table-head-cell";
  const valueType = tableValueType(column);
  const ariaSort = column.sortable ? ` aria-sort="${active ? (direction === "desc" ? "descending" : "ascending") : "none"}"` : "";
  return `<th class="${column.numeric ? "num " : ""}table-value-${esc(valueType)}" data-value-type="${esc(valueType)}"${ariaSort}><div class="${contentClass}">${label}${filter}</div></th>`;
}
function renderFilterControl(tableId, column, rows) {
  const selected = new Set(activeFilterValues(tableId, column.key));
  const options = Array.from(new Set([...filterOptions(column, rows), ...selected]))
    .sort((left, right) => left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" }));
  const count = selected.size;
  const countText = count ? `<span class="filter-count">${esc(`${count} ${t("selected_count", "selected")}`)}</span>` : "";
  const optionHtml = options.length
    ? options.map(value => `<label class="filter-option"><input type="checkbox" data-filter-key="${esc(column.key)}" value="${esc(value)}" ${selected.has(value) ? "checked" : ""}><span>${esc(filterLabel(column, value))}</span></label>`).join("")
    : `<p class="filter-empty">${esc(t("no_matching_rows", "No matching rows"))}</p>`;
  return `<details class="filter-control ${count ? "active" : ""}" data-filter-menu="${esc(column.key)}"><summary class="filter-button" aria-label="${esc(t("filter", "Filter"))} ${esc(column.label)}"><span class="filter-icon">&#9662;</span>${countText}</summary><div class="filter-menu"><div class="filter-menu-head"><strong>${esc(column.label)}</strong><div class="filter-menu-actions"><button class="action-button compact filter-clear" type="button" data-filter-clear="${esc(column.key)}" ${count ? "" : "disabled"}>${esc(t("clear", "Clear"))}</button><button class="action-button compact primary filter-apply" type="button" data-filter-apply="${esc(column.key)}" disabled>${esc(t("apply", "Apply"))}</button></div></div><div class="filter-options">${optionHtml}</div></div></details>`;
}
function selectionSetForColumn(column) {
  const value = typeof column?.selectionSet === "function" ? column.selectionSet() : column?.selectionSet;
  return value instanceof Set ? value : state.rowSelection;
}
function selectionKeyForRow(row, column) {
  if (typeof column?.selectable === "function" && !column.selectable(row)) return "";
  const value = typeof column?.selectionKey === "function" ? column.selectionKey(row) : row?.trial_key;
  return String(value || "");
}
function visibleSelectionState(rows, column) {
  const keys = rows.map(row => selectionKeyForRow(row, column)).filter(Boolean);
  const selected = selectionSetForColumn(column);
  const selectedCount = keys.filter(key => selected.has(key)).length;
  return {
    keys,
    checked: keys.length > 0 && selectedCount === keys.length,
    partial: selectedCount > 0 && selectedCount < keys.length,
  };
}
function setVisibleSelection(rows, column, checked) {
  const selected = selectionSetForColumn(column);
  visibleSelectionState(rows, column).keys.forEach(key => {
    if (checked) selected.add(key);
    else selected.delete(key);
  });
}
function renderSelectionHeader(rows, column = selectionColumn()) {
  const selection = visibleSelectionState(rows, column);
  return `<th class="select-col table-value-selection" data-value-type="selection"><label class="select-box"><input type="checkbox" data-table-select-visible="${esc(column.key)}" ${selection.checked ? "checked" : ""} ${selection.partial ? "data-partial=\"true\"" : ""} ${selection.keys.length ? "" : "disabled"} aria-label="${esc(column.headerAriaLabel || t("select_visible_rows", "Select visible rows"))}"><span></span></label></th>`;
}
function renderDataSelection(row, column = selectionColumn()) {
  const key = selectionKeyForRow(row, column);
  if (!key) return `<span class="select-box-placeholder" aria-hidden="true"></span>`;
  const checked = selectionSetForColumn(column).has(key);
  const ariaLabel = typeof column.rowAriaLabel === "function" ? column.rowAriaLabel(key, row) : `${t("select_row_for_export", "Select row for export")}: ${key}`;
  return `<label class="select-box"><input type="checkbox" data-table-row-select="${esc(key)}" data-table-selection-column="${esc(column.key)}" ${checked ? "checked" : ""} aria-label="${esc(ariaLabel)}"><span></span></label>`;
}
function renderRowSelection(row) {
  return renderDataSelection(row, selectionColumn());
}
function tableOptionValue(option, row, fallback = "") {
  return typeof option === "function" ? option(row) : (option || fallback);
}
function renderTableRow(row, columns, rows, options = {}) {
  const className = tableOptionValue(options.rowClass, row);
  const attrs = tableOptionValue(options.rowAttrs, row);
  const title = tableOptionValue(options.rowTitle, row);
  const titleAttr = title && !String(attrs).includes("title=") ? ` title="${esc(title)}"` : "";
  const rowKey = tableOptionValue(options.rowKey, row, row?.trial_key || row?.source_key || "");
  const keyAttr = rowKey ? ` data-table-row-key="${esc(rowKey)}"` : "";
  return `<tr class="${esc(className)}"${keyAttr}${attrs ? ` ${attrs}` : ""}${titleAttr}>${columns.map(column => renderDataCell(row, column, rows)).join("")}</tr>`;
}
function renderDataCell(row, column, rows) {
  if (column.select) return `<td class="select-col table-value-selection" data-value-type="selection">${column.html ? column.html(row) : renderDataSelection(row, column)}</td>`;
  const className = typeof column.className === "function" ? column.className(row) : column.className;
  const valueType = tableValueType(column);
  const edit = resolveTableCellEdit(column, row);
  const classes = [column.numeric ? "num" : "", `table-value-${valueType}`, edit ? "table-cell-editable" : "", column.metric ? metricCellShade(row, column, rows) : "", className || ""].filter(Boolean).join(" ");
  const html = column.html ? column.html(row) : esc(tableText(row, column));
  const fullText = tableFullText(row, column);
  const title = column.cellTitle ? (column.cellTitle(row) || fullText) : fullText;
  const attrs = typeof column.cellAttrs === "function" ? column.cellAttrs(row) : (column.cellAttrs || "");
  const editableAttrs = edit ? ` tabindex="0" aria-keyshortcuts="Enter"` : "";
  return `<td class="${classes}" data-table-column-key="${esc(column.key)}" data-value-type="${esc(valueType)}"${attrs ? ` ${attrs}` : ""}${title ? ` title="${esc(title)}" aria-label="${esc(title)}"` : ""}${editableAttrs}><div class="table-cell-content">${html}</div></td>`;
}
function metricCellShade(row, column, rows) {
  const value = column.value(row);
  if (!hasMetricValue(value)) return "metric-cell metric-missing";
  const values = rows.map(item => column.value(item)).filter(hasMetricValue).map(Number);
  if (!values.length) return "metric-cell metric-missing";
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return "metric-cell metric-shade-2";
  const bucket = Math.max(0, Math.min(4, Math.round(((Number(value) - min) / (max - min)) * 4)));
  return `metric-cell metric-shade-${bucket}`;
}
function bindDataTableControls(root, options = {}) {
  if (!root) return;
  const config = options || {};
  const { tableId, columns = [], rows = [], rowKey = null } = config;
  if (!tableId) return;
  const rerender = typeof config.onChange === "function" ? config.onChange : (() => {});
  bindDataTableSelection(root, {
    columns,
    rows,
    onChange: typeof config.onSelectionChange === "function" ? config.onSelectionChange : rerender,
  });
  root.querySelectorAll("[data-table-sort]").forEach(button => {
    button.addEventListener("click", event => {
      event.stopPropagation();
      if (serveMode() && tableId === "leaderboard") {
        requestCatalogSort(button.dataset.tableSort);
        return;
      }
      toggleDataTableSort(tableId, button.dataset.tableSort);
      rerender();
    });
  });
  root.querySelectorAll("[data-filter-key]").forEach(input => {
    input.addEventListener("change", event => {
      event.stopPropagation();
      const menu = dataTableFilterMenu(root, input.dataset.filterKey);
      syncDataTableFilterDraft(menu, tableId, input.dataset.filterKey);
    });
  });
  root.querySelectorAll("[data-filter-clear]").forEach(button => {
    button.addEventListener("click", event => {
      event.stopPropagation();
      const key = button.dataset.filterClear;
      const menu = dataTableFilterMenu(root, key);
      menu?.querySelectorAll?.("[data-filter-key]").forEach(input => { input.checked = false; });
      syncDataTableFilterDraft(menu, tableId, key);
    });
  });
  root.querySelectorAll("[data-filter-apply]").forEach(button => {
    button.addEventListener("click", event => {
      event.stopPropagation();
      const key = button.dataset.filterApply;
      const menu = dataTableFilterMenu(root, key);
      const values = dataTableFilterDraftValues(menu);
      setFilterValues(tableId, key, values);
      if (menu) menu.open = false;
      if (serveMode() && tableId === "leaderboard") {
        setDataTableFilterApplyDisabled(root, true);
        const request = requestCatalogFacets();
        if (request?.finally) request.finally(() => setDataTableFilterApplyDisabled(root, false));
        return;
      }
      rerender();
    });
  });
  root.querySelectorAll("[data-filter-menu]").forEach(menu => {
    menu.addEventListener("toggle", () => resetDataTableFilterDraft(menu, tableId));
    menu.addEventListener("keydown", event => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      menu.open = false;
      resetDataTableFilterDraft(menu, tableId);
    });
  });
  bindDataTableEditors(root, { tableId, columns, rows, rowKey, onChange: rerender });
}
function bindDataTableSelection(root, { columns = [], rows = [], onChange = null } = {}) {
  const selectionColumns = columns.filter(column => column?.select);
  if (!selectionColumns.length) return;
  const byKey = new Map(selectionColumns.map(column => [String(column.key), column]));
  root.querySelectorAll("[data-table-row-select]").forEach(input => {
    input.closest("label")?.addEventListener("click", event => event.stopPropagation());
    input.addEventListener("click", event => event.stopPropagation());
    input.addEventListener("change", event => {
      event.stopPropagation();
      const column = byKey.get(String(input.dataset.tableSelectionColumn || ""));
      const key = String(input.dataset.tableRowSelect || "");
      if (!column || !key) return;
      const selected = selectionSetForColumn(column);
      if (input.checked) selected.add(key);
      else selected.delete(key);
      syncDataTableSelection(root, { columns, rows });
      if (typeof onChange === "function") onChange();
    });
  });
  root.querySelectorAll("[data-table-select-visible]").forEach(input => {
    input.indeterminate = input.hasAttribute("data-partial");
    input.addEventListener("click", event => event.stopPropagation());
    input.addEventListener("change", event => {
      event.stopPropagation();
      const column = byKey.get(String(input.dataset.tableSelectVisible || ""));
      if (!column) return;
      setVisibleSelection(rows, column, input.checked);
      syncDataTableSelection(root, { columns, rows });
      if (typeof onChange === "function") onChange();
    });
  });
}
function syncDataTableSelection(root, { columns = [], rows = [] } = {}) {
  const selectionColumns = columns.filter(column => column?.select);
  const byKey = new Map(selectionColumns.map(column => [String(column.key), column]));
  root.querySelectorAll("[data-table-row-select]").forEach(input => {
    const column = byKey.get(String(input.dataset.tableSelectionColumn || ""));
    const key = String(input.dataset.tableRowSelect || "");
    if (column && key) input.checked = selectionSetForColumn(column).has(key);
  });
  root.querySelectorAll("[data-table-select-visible]").forEach(input => {
    const column = byKey.get(String(input.dataset.tableSelectVisible || ""));
    if (!column) return;
    const selection = visibleSelectionState(rows, column);
    input.checked = selection.checked;
    input.indeterminate = selection.partial;
    input.toggleAttribute("data-partial", selection.partial);
  });
}
function resolveTableCellEdit(column, row) {
  const source = typeof column?.edit === "function" ? column.edit(row) : column?.edit;
  if (!source || typeof source.commit !== "function" || tableValueType(column) === "selection") return null;
  const resolve = value => typeof value === "function" ? value(row) : value;
  return {
    ...source,
    value: resolve(source.value),
    options: resolve(source.options),
    suggestions: resolve(source.suggestions),
  };
}
function normalizeTableListValue(value) {
  const values = Array.isArray(value) ? value : String(value ?? "").split(/[,，]/);
  const out = [];
  const seen = new Set();
  values.forEach(item => {
    const normalized = String(item ?? "").trim();
    if (!normalized || seen.has(normalized)) return;
    seen.add(normalized);
    out.push(normalized);
  });
  return out;
}
function normalizeTableScalarListValue(value) {
  const values = Array.isArray(value) ? value : [value];
  const out = [];
  const seen = new Set();
  values.forEach(item => {
    const normalized = String(item ?? "").trim();
    if (!normalized || seen.has(normalized)) return;
    seen.add(normalized);
    out.push(normalized);
  });
  return out;
}
function normalizeTableEditValue(valueType, value) {
  if (valueType === "list") return normalizeTableListValue(value);
  if (valueType === "scalar-list") return normalizeTableScalarListValue(value);
  if (["text", "enum"].includes(valueType)) return String(value ?? "").trim();
  return String(value ?? "");
}
function tableRowKey(row, rowKey) {
  const value = typeof rowKey === "function" ? rowKey(row) : row?.[rowKey] ?? row?.trial_key ?? row?.source_key;
  return String(value ?? "");
}
function bindDataTableEditors(root, { tableId, columns, rows, rowKey, onChange }) {
  if (!columns.length || !rows.length) return;
  const columnByKey = new Map(columns.map(column => [String(column.key), column]));
  const rowByKey = new Map(rows.map(row => [tableRowKey(row, rowKey), row]));
  root.querySelectorAll(`[data-table-id="${tableId}"] [data-table-column-key]`).forEach(cell => {
    const column = columnByKey.get(cell.dataset.tableColumnKey);
    const row = rowByKey.get(cell.closest("[data-table-row-key]")?.dataset?.tableRowKey || "");
    if (!row || !resolveTableCellEdit(column, row)) return;
    cell.addEventListener("click", event => event.stopPropagation());
    cell.addEventListener("dblclick", event => {
      event.preventDefault();
      event.stopPropagation();
      beginTableCellEdit(cell, { tableId, column, row, onChange });
    });
    cell.addEventListener("keydown", event => {
      if (event.key !== "Enter" || event.currentTarget !== event.target) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      beginTableCellEdit(cell, { tableId, column, row, onChange });
    });
  });
}
function beginTableCellEdit(cell, { tableId, column, row, onChange = null }) {
  if (!cell || cell.querySelector("[data-table-cell-editor]")) return null;
  const edit = resolveTableCellEdit(column, row);
  if (!edit) return null;
  const valueType = tableValueType(column);
  const renderedRowKey = cell.closest("[data-table-row-key]")?.dataset?.tableRowKey || "";
  const original = cell.innerHTML;
  const originalTitle = cell.getAttribute("title");
  const originalAriaLabel = cell.getAttribute("aria-label");
  const editor = document.createElement("div");
  editor.className = `table-cell-editor table-cell-editor-${valueType}`;
  editor.dataset.tableCellEditor = valueType;
  editor.addEventListener("click", event => event.stopPropagation());
  editor.addEventListener("dblclick", event => event.stopPropagation());
  let input = null;
  const scalarListValues = valueType === "scalar-list"
    ? normalizeTableScalarListValue(edit.value)
    : null;
  if (valueType === "enum") input = tableEnumEditor(edit.options, edit.value);
  else if (["markdown", "yaml"].includes(valueType)) {
    input = document.createElement("textarea");
    input.rows = valueType === "yaml" ? 6 : 4;
    input.value = String(edit.value ?? "");
  } else {
    input = document.createElement("input");
    input.type = "text";
    input.value = valueType === "scalar-list"
      ? ""
      : Array.isArray(edit.value)
        ? edit.value.join(", ")
        : String(edit.value ?? "");
    if (valueType === "scalar-list") input.placeholder = t("add_value", "Add value");
  }
  input.classList.add("table-cell-editor-control");
  input.setAttribute("aria-label", column.label || column.key);
  editor.appendChild(input);
  if (valueType === "list") editor.appendChild(renderTableSuggestions(input, edit.suggestions, { multiple: true, allowCustom: edit.allowCustom }));
  else if (valueType === "scalar-list") {
    editor.appendChild(renderTableScalarListSuggestions(input, edit.suggestions, scalarListValues));
  }
  else if (valueType === "text" && normalizeTableListValue(edit.suggestions).length) {
    editor.appendChild(renderTableSuggestions(input, edit.suggestions));
  }
  const status = document.createElement("div");
  status.className = "table-cell-editor-status";
  status.setAttribute("aria-live", "polite");
  editor.appendChild(status);
  let finished = false;
  let pending = false;
  const focusCell = (rowKey = renderedRowKey) => focusTableCell(tableId, rowKey, column.key, cell);
  const cancel = () => {
    if (finished || pending) return;
    finished = true;
    cell.innerHTML = original;
    if (originalTitle === null) cell.removeAttribute("title");
    else cell.setAttribute("title", originalTitle);
    if (originalAriaLabel === null) cell.removeAttribute("aria-label");
    else cell.setAttribute("aria-label", originalAriaLabel);
    cell.focus();
  };
  const save = async () => {
    if (finished || pending) return;
    const editValue = valueType === "scalar-list"
      ? normalizeTableScalarListValue([...scalarListValues, input.value])
      : normalizeTableEditValue(valueType, input.value);
    if (edit.allowCustom === false) {
      const allowed = new Set(normalizeTableListValue(edit.suggestions));
      const values = Array.isArray(editValue) ? editValue : [editValue].filter(Boolean);
      const unknown = values.filter(value => !allowed.has(value));
      if (unknown.length) {
        status.textContent = `${t("choose_available_values", "Choose only available values")}: ${unknown.join(", ")}`;
        status.classList.add("danger");
        input.focus();
        return;
      }
    }
    pending = true;
    editor.classList.add("pending");
    editor.setAttribute("aria-busy", "true");
    input.disabled = true;
    editor.querySelectorAll("button").forEach(button => { button.disabled = true; });
    status.textContent = t("saving", "Saving...");
    try {
      const result = await edit.commit(row, editValue);
      finished = true;
      if (typeof onChange === "function") await onChange();
      focusCell(result?.rowKey || renderedRowKey);
    } catch (error) {
      pending = false;
      editor.classList.remove("pending");
      editor.removeAttribute("aria-busy");
      input.disabled = false;
      editor.querySelectorAll("button").forEach(button => { button.disabled = false; });
      status.textContent = error?.message || String(error);
      status.classList.add("danger");
      input.focus();
    }
  };
  if (["markdown", "yaml"].includes(valueType)) editor.appendChild(tableEditorActions(save, cancel));
  input.addEventListener("keydown", event => {
    event.stopPropagation();
    if (event.key === "Escape") {
      event.preventDefault();
      cancel();
      return;
    }
    if (["markdown", "yaml"].includes(valueType)) {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        save();
      }
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      save();
    }
  });
  if (!["markdown", "yaml"].includes(valueType)) {
    editor.addEventListener("focusout", () => {
      setTimeout(() => {
        if (!finished && !pending && !editor.contains(document.activeElement)) save();
      }, 0);
    });
  }
  cell.removeAttribute("title");
  cell.removeAttribute("aria-label");
  cell.replaceChildren(editor);
  input.focus();
  if (typeof input.select === "function" && valueType !== "enum") input.select();
  return { editor, input, save, cancel };
}
function tableEnumEditor(options, currentValue) {
  const select = document.createElement("select");
  listValue(options).forEach(option => {
    const item = typeof option === "object" ? option : { value: option, label: option };
    const node = document.createElement("option");
    node.value = String(item?.value ?? "");
    node.textContent = String(item?.label ?? item?.value ?? "");
    node.selected = node.value === String(currentValue ?? "");
    select.appendChild(node);
  });
  return select;
}
function renderTableSuggestions(input, suggestions, options = {}) {
  const multiple = Boolean(options.multiple);
  const strict = options.allowCustom === false;
  const candidates = normalizeTableListValue(suggestions);
  const known = new Set(candidates);
  const list = document.createElement("div");
  list.className = "table-cell-editor-suggestions";
  list.setAttribute("aria-label", t("suggestions", "Suggestions"));
  const sync = () => {
    const values = normalizeTableListValue(input.value);
    const selected = multiple
      ? new Set(values)
      : new Set([String(input.value || "").trim()].filter(Boolean));
    const active = multiple ? values.at(-1) || "" : String(input.value || "").trim();
    const query = strict && active && !known.has(active) ? active.toLocaleLowerCase() : "";
    list.querySelectorAll("button").forEach(button => {
      const active = selected.has(button.dataset.tableSuggestion);
      button.classList.toggle("selected", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
      button.hidden = Boolean(query) && !active
        && !button.dataset.tableSuggestion.toLocaleLowerCase().includes(query);
    });
  };
  candidates.forEach(suggestion => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "source-tag-chip table-cell-editor-suggestion";
    button.dataset.tableSuggestion = suggestion;
    button.textContent = suggestion;
    button.addEventListener("mousedown", event => event.preventDefault());
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      if (multiple) {
        const values = normalizeTableListValue(input.value);
        const active = values.at(-1) || "";
        const replacing = strict && active && !known.has(active);
        if (replacing) values.pop();
        const index = values.indexOf(suggestion);
        if (index >= 0 && !replacing) values.splice(index, 1);
        else if (index < 0) values.push(suggestion);
        input.value = normalizeTableListValue(values).join(", ");
      } else {
        input.value = suggestion;
      }
      sync();
      input.focus();
    });
    list.appendChild(button);
  });
  input.addEventListener("input", sync);
  sync();
  return list;
}
function renderTableScalarListSuggestions(input, suggestions, selectedValues) {
  const list = document.createElement("div");
  list.className = "table-cell-editor-suggestions";
  list.setAttribute("aria-label", t("suggestions", "Suggestions"));
  const candidates = normalizeTableScalarListValue([
    ...selectedValues,
    ...normalizeTableScalarListValue(suggestions),
  ]);
  const sync = () => {
    const selected = new Set(selectedValues);
    list.querySelectorAll("button").forEach(button => {
      const active = selected.has(button.dataset.tableSuggestion);
      button.classList.toggle("selected", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  };
  candidates.forEach(suggestion => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "source-tag-chip table-cell-editor-suggestion";
    button.dataset.tableSuggestion = suggestion;
    button.textContent = suggestion;
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      const index = selectedValues.indexOf(suggestion);
      if (index >= 0) selectedValues.splice(index, 1);
      else selectedValues.push(suggestion);
      sync();
      input.focus();
    });
    list.appendChild(button);
  });
  sync();
  return list;
}
function tableEditorActions(save, cancel) {
  const actions = document.createElement("div");
  actions.className = "table-cell-editor-actions";
  const saveButton = document.createElement("button");
  saveButton.type = "button";
  saveButton.className = "action-button compact primary";
  saveButton.textContent = t("save", "Save");
  saveButton.addEventListener("click", save);
  const cancelButton = document.createElement("button");
  cancelButton.type = "button";
  cancelButton.className = "action-button compact";
  cancelButton.textContent = t("cancel", "Cancel");
  cancelButton.addEventListener("click", cancel);
  actions.append(saveButton, cancelButton);
  return actions;
}
function focusTableCell(tableId, rowKey, columnKey, fallback = null) {
  const candidates = Array.from(document.querySelectorAll(`[data-table-id="${tableId}"] [data-table-column-key]`));
  const cell = candidates.find(node => node.dataset.tableColumnKey === String(columnKey) && node.closest("[data-table-row-key]")?.dataset?.tableRowKey === String(rowKey)) || fallback;
  if (cell?.isConnected !== false) cell?.focus?.();
}
function dataTableFilterMenu(root, key) {
  return Array.from(root?.querySelectorAll?.("[data-filter-menu]") || [])
    .find(menu => menu.dataset.filterMenu === key) || null;
}
function dataTableFilterDraftValues(menu) {
  return Array.from(menu?.querySelectorAll?.("[data-filter-key]") || [])
    .filter(input => input.checked)
    .map(input => input.value);
}
function sameDataTableFilterValues(left, right) {
  if (left.length !== right.length) return false;
  const expected = new Set(right);
  return left.every(value => expected.has(value));
}
function syncDataTableFilterDraft(menu, tableId, key) {
  if (!menu) return;
  const values = dataTableFilterDraftValues(menu);
  const clear = menu.querySelector?.("[data-filter-clear]");
  const apply = menu.querySelector?.("[data-filter-apply]");
  if (clear) clear.disabled = values.length === 0;
  if (apply) apply.disabled = sameDataTableFilterValues(values, activeFilterValues(tableId, key));
}
function resetDataTableFilterDraft(menu, tableId) {
  if (!menu) return;
  const key = menu.dataset.filterMenu;
  const selected = new Set(activeFilterValues(tableId, key));
  menu.querySelectorAll?.("[data-filter-key]").forEach(input => { input.checked = selected.has(input.value); });
  syncDataTableFilterDraft(menu, tableId, key);
}
function setDataTableFilterApplyDisabled(root, disabled) {
  root?.querySelectorAll?.("[data-filter-apply]").forEach(button => { button.disabled = disabled; });
}
function bindLeaderboardControls() {
  const target = $("leaderboard");
  if (!target) return;
  const rows = leaderboardRows();
  bindDataTableControls(target, {
    tableId: "leaderboard",
    columns: displayLeaderboardColumns(rows),
    rows,
    rowKey: row => row.source_key || row.trial_key,
    onChange: () => renderComparisonPanels(),
    onSelectionChange: () => renderComparisonPanels({ trace: false }),
  });
  bindServeSourceStateControls(target);
  bindServeExportControls(target);
  bindLeaderboardSearchControls(target);
  bindWorkspaceReportLeaderboardControls(target);
  bindTrialSelection(target);
  bindLeaderboardCatalogControls(target);
  bindLeaderboardColumnControls(target);
}
export {
  activeFilterValues,
  agentNameFor,
  applyDataTableControls,
  applyDataTableFilters,
  beginTableCellEdit,
  bindDataTableControls,
  bindDataTableSelection,
  bindDataTableEditors,
  bindLeaderboardControls,
  bindLeaderboardColumnControls,
  clearFilter,
  compareTableValues,
  currentLeaderboardColumnLayout,
  dataTableFilterDraftValues,
  dataTableFilterMenu,
  displayLeaderboardColumns,
  filterLabel,
  filterValue,
  filterValues,
  filterableColumns,
  leaderboardColumns,
  metricCellShade,
  normalizeTableEditValue,
  normalizeTableListValue,
  normalizeTableScalarListValue,
  renderDataCell,
  renderDataSelection,
  renderDataTable,
  renderFilterControl,
  renderLeaderboard,
  renderLeaderboardColumnControls,
  renderLeaderboardExportControls,
  renderRowSelection,
  renderSelectionHeader,
  renderTableHeader,
  renderTableRow,
  renderTableScalarListSuggestions,
  renderTableSuggestions,
  resetDataTableFilterDraft,
  resolveTableCellEdit,
  rowToolErrorRate,
  sameDataTableFilterValues,
  selectedStepExists,
  selectedStepVisible,
  selectionColumn,
  selectionKeyForRow,
  selectionSetForColumn,
  setDataTableFilterApplyDisabled,
  setFilterValue,
  setFilterValues,
  setVisibleSelection,
  syncDataTableSelection,
  syncDataTableFilterDraft,
  tableControls,
  tableCellContent,
  tableFullText,
  tableOptionValue,
  tableSortType,
  tableText,
  tableValueType,
  tableValueAttributes,
  toggleDataTableSort,
  visibleSelectionState,
};
