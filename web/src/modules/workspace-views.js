import { $, RENDER_OPTIONS, adminMode, closeOpenSubmenus, esc, fmtNum, listValue, normalizeServeSourceMode, serveMode, state, statusLabel, t, workspaceDisplayMode, workspaceSnapshotMode } from "./runtime.js";
import { applyDataTableControls, bindDataTableControls, renderDataTable, selectionColumn, setVisibleSelection, tableCellContent, tableControls, tableValueAttributes } from "./data-tables.js";
import { leaderboardSummaryDefinitions, leaderboardSummaryGroupHeading, leaderboardSummaryGroupUnit, leaderboardSummaryStatistics, leaderboardSummaryValue, renderLeaderboardSummary, summaryNumber } from "./leaderboard-summary.js";
import { serveApi, setServeStatus } from "./serve-effects.js";
import { leaderboardRows, loadCatalogPage, serveDownload } from "./serve-catalog.js";
import { closeModalSurface, focusSoon, openModalSurface } from "./modal-surfaces.js";
import { renderMarkdown } from "./markdown.js";
import { createWorkspaceViewRepository } from "./workspace-view-repository.js";

let liveWorkspaceViewRepository = null;

function browserStorageAdapter() {
  try {
    return globalThis.localStorage || globalThis.window?.localStorage;
  } catch (error) {
    return {
      getItem() { throw error; },
      setItem() { throw error; },
    };
  }
}

function workspaceViewRepository() {
  if (!serveMode()) return null;
  if (!liveWorkspaceViewRepository) {
    liveWorkspaceViewRepository = createWorkspaceViewRepository({
      workspaceId: RENDER_OPTIONS?.workspace_id || "default",
      storage: browserStorageAdapter(),
      request: serveApi,
    });
  }
  return liveWorkspaceViewRepository;
}

function workspaceViews() {
  return listValue(state.workspaceViews)
    .filter(view => view && typeof view.name === "string" && view.name.trim())
    .map(view => ({
      ...view,
      name: String(view.name),
      origin: view.origin === "browser" ? "browser" : "server",
      id: String(view.id || `${view.origin === "browser" ? "browser" : "server"}:${view.name}`),
      filters: workspaceViewFilters(view.filters),
      group_by: ["overall", "agent", "model", "category", "task", "job", "provider"].includes(view.group_by) ? view.group_by : "agent",
      notes: typeof view.notes === "string" ? view.notes : "",
    }))
    .sort((left, right) => left.name.localeCompare(right.name, undefined, { numeric: true, sensitivity: "base" }));
}

function workspaceViewFilters(value) {
  const filters = value && typeof value === "object" ? value : {};
  return {
    state: normalizeServeSourceMode(filters.state),
    search: typeof filters.search === "string" ? filters.search : "",
    categories: listValue(filters.categories).map(String),
    tags: listValue(filters.tags).map(String),
    agents: listValue(filters.agents).map(String),
    models: listValue(filters.models).map(String),
    tasks: listValue(filters.tasks).map(String),
    jobs: listValue(filters.jobs).map(String),
    providers: listValue(filters.providers).map(String),
    results: listValue(filters.results).map(String),
  };
}

function workspaceViewForName(name) {
  return workspaceViews().find(view => view.name === String(name || "")) || null;
}

function workspaceViewForId(id) {
  return workspaceViews().find(view => view.id === String(id || "")) || null;
}

function workspaceViewSummaryForName(name) {
  return listValue(state.workspaceViewSummaries).find(view => view?.name === name) || null;
}

function workspaceViewColumns() {
  const navigateAttrs = view => `data-view-navigate="${esc(view.id)}"${workspaceSnapshotMode() ? " tabindex=\"0\"" : ""}`;
  const edit = (field, options = {}) => workspaceSnapshotMode() ? undefined : view => (view.origin === "browser" || adminMode()) ? {
    value: view => workspaceViewEditValue(view, field),
    commit: (view, value) => commitWorkspaceViewCellEdit(view, field, value),
    ...options,
  } : undefined;
  const columns = [
    { key: "name", label: t("view_name", "Name"), valueType: "text", value: view => view.name, html: view => `<strong>${esc(view.name)}</strong>${view.origin === "browser" ? `<span class="workspace-view-local-badge">${esc(t("view_local", "Local"))}</span>` : ""}`, cellAttrs: navigateAttrs, edit: edit("name") },
    { key: "categories", label: t("category", "Category"), valueType: "scalar-list", filterable: true, filterValues: view => view.filters.categories, value: view => view.filters.categories.join(", ") || "-", html: view => renderWorkspaceViewValueList(view.filters.categories), cellAttrs: navigateAttrs, edit: edit("categories", { suggestions: workspaceViewCategorySuggestions }) },
    { key: "tags", label: t("tags", "Tags"), valueType: "list", filterable: true, filterValues: view => view.filters.tags, value: view => view.filters.tags.join(", ") || "-", html: view => renderWorkspaceViewValueList(view.filters.tags), cellAttrs: navigateAttrs, edit: edit("tags", { suggestions: workspaceViewTagSuggestions }) },
    { key: "models", label: t("model", "Models"), valueType: "list", filterable: true, filterValues: view => view.filters.models, value: view => view.filters.models.join(", ") || "-", html: view => renderWorkspaceViewValueList(view.filters.models), cellAttrs: navigateAttrs, edit: edit("models", { suggestions: workspaceViewModelSuggestions }) },
    { key: "tasks", label: t("task", "Task"), valueType: "list", filterable: true, filterValues: view => view.filters.tasks, value: view => view.filters.tasks.join(", ") || "-", html: view => renderWorkspaceViewValueList(view.filters.tasks), cellAttrs: navigateAttrs, edit: edit("tasks", { suggestions: workspaceViewTaskSuggestions }) },
    { key: "jobs", label: t("job", "Job"), valueType: "list", filterable: true, filterValues: view => view.filters.jobs, value: view => view.filters.jobs.join(", ") || "-", html: view => renderWorkspaceViewValueList(view.filters.jobs), cellAttrs: navigateAttrs, edit: edit("jobs", { suggestions: workspaceViewJobSuggestions }) },
    { key: "providers", label: t("provider", "Provider"), valueType: "list", filterable: true, filterValues: view => view.filters.providers, value: view => view.filters.providers.join(", ") || "-", html: view => renderWorkspaceViewValueList(view.filters.providers), cellAttrs: navigateAttrs, edit: edit("providers", { suggestions: workspaceViewProviderSuggestions }) },
    { key: "group_by", label: t("summary_group_by", "Group by"), valueType: "enum", filterable: true, value: view => view.group_by, filterLabel: workspaceViewGroupByLabel, html: view => esc(workspaceViewGroupByLabel(view.group_by)), cellAttrs: navigateAttrs, edit: edit("group_by", { options: () => ["overall", "agent", "model", "category", "task", "job", "provider"].map(value => ({ value, label: workspaceViewGroupByLabel(value) })) }) },
    { key: "other_conditions", label: t("view_other_conditions", "Other conditions"), valueType: "yaml", value: view => workspaceViewOtherConditionsLabel(view), fullText: workspaceViewOtherConditionsYaml, html: view => `<span class="workspace-view-config-preview">${esc(workspaceViewOtherConditionsLabel(view))}</span>`, cellAttrs: navigateAttrs, edit: edit("other_conditions") },
    { key: "notes", label: t("view_notes", "Notes"), valueType: "markdown", value: view => view.notes || "-", fullText: view => view.notes || "", html: view => `<span>${esc(String(view.notes || "").replace(/\s+/g, " ").trim() || "-")}</span>`, className: "workspace-view-notes-cell", cellAttrs: navigateAttrs, edit: edit("notes") },
  ];
  if (workspaceSnapshotMode()) return columns;
  return [
    selectionColumn({
      selectionKey: view => view?.id || "",
      selectionSet: () => state.workspaceViewSelection,
      rowInputAttr: id => `data-view-select="${esc(id)}"`,
      headerInputAttr: "data-view-select-visible",
      rowAriaLabel: id => workspaceViewMessage("select_view", "Select {name}", { name: workspaceViewForId(id)?.name || id }),
    }),
    ...columns,
  ];
}

function workspaceViewRows() {
  const views = workspaceViews();
  return applyDataTableControls("workspace-views", views, workspaceViewColumns(), views);
}

function renderWorkspaceViewValueList(values) {
  const items = listValue(values);
  return items.length
    ? `<span class="source-tag-list">${items.map(value => `<span class="source-tag-chip">${esc(value)}</span>`).join("")}</span>`
    : `<span class="muted">-</span>`;
}

function workspaceViewTagSuggestions() {
  return workspaceViews().flatMap(view => view.filters.tags);
}

function workspaceViewCategorySuggestions() {
  return workspaceViews().flatMap(view => view.filters.categories);
}

function workspaceViewModelSuggestions() {
  return workspaceViews().flatMap(view => view.filters.models);
}
function workspaceViewTaskSuggestions() {
  return workspaceViews().flatMap(view => view.filters.tasks);
}
function workspaceViewJobSuggestions() {
  return workspaceViews().flatMap(view => view.filters.jobs);
}
function workspaceViewProviderSuggestions() {
  return workspaceViews().flatMap(view => view.filters.providers);
}

function workspaceViewEditValue(view, field) {
  if (field === "name") return view.name;
  if (["categories", "tags", "models", "tasks", "jobs", "providers"].includes(field)) return view.filters[field];
  if (field === "group_by") return view.group_by;
  if (field === "other_conditions") return workspaceViewOtherConditionsYaml(view);
  return view.notes;
}

function workspaceViewMessage(key, fallback, values = {}) {
  let message = String(t(key, fallback));
  Object.entries(values).forEach(([name, value]) => {
    message = message.replaceAll(`{${name}}`, String(value));
  });
  return message;
}

function renderWorkspaceViewControls() {
  if (!workspaceDisplayMode()) return "";
  const compositeApplied = state.workspaceAppliedViewNames.size > 0;
  const reopen = state.workspaceViewsClosed && workspaceViews().length
    ? `<button type="button" class="action-button" data-workspace-views-open>${esc(t("saved_views", "Saved views"))}</button>`
    : "";
  const save = `<button type="button" class="action-button leaderboard-summary-save" data-view-save ${compositeApplied || !state.workspaceViewsLoaded ? `disabled title="${esc(compositeApplied ? t("clear_conditions_before_saving_view", "Clear applied views before saving a new view.") : t("view_directory_required", "Load Saved Views before saving."))}"` : ""}>${esc(t("save_view", "Save view"))}</button>`;
  return reopen || save ? `<div class="workspace-view-controls" data-workspace-view-control>${reopen}${save}</div>` : "";
}

function bindWorkspaceViewControls(target) {
  if (!workspaceDisplayMode() || !target?.querySelectorAll) return;
  const columns = workspaceViewColumns();
  const rows = workspaceViewRows();
  bindDataTableControls(target, {
    tableId: "workspace-views",
    columns,
    rows,
    rowKey: view => view.id,
    onChange: renderWorkspaceViewRail,
  });
  target.querySelectorAll("[data-view-save]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      openWorkspaceViewSaveDialog(button);
    });
  });
  target.querySelectorAll("[data-workspace-views-close]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      closeWorkspaceViewRail();
    });
  });
  target.querySelectorAll("[data-workspace-views-open]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      openWorkspaceViewRail();
    });
  });
  target.querySelectorAll("[data-view-apply-selected]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      applySelectedWorkspaceViews();
    });
  });
  target.querySelectorAll("[data-view-delete-selected]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      deleteSelectedWorkspaceViews();
    });
  });
  target.querySelectorAll("[data-view-export-selected]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      exportSelectedWorkspaceViews();
    });
  });
  target.querySelectorAll("[data-view-select]").forEach(input => {
    input.addEventListener("click", event => event.stopPropagation());
    input.addEventListener("change", () => {
      const id = String(input.dataset.viewSelect || "");
      if (input.checked) state.workspaceViewSelection.add(id);
      else state.workspaceViewSelection.delete(id);
      renderWorkspaceViewRail();
    });
  });
  target.querySelectorAll("[data-view-select-visible]").forEach(input => {
    input.indeterminate = input.hasAttribute?.("data-partial") || false;
    input.addEventListener("click", event => event.stopPropagation());
    input.addEventListener("change", event => {
      event.stopPropagation();
      setVisibleSelection(workspaceViewRows(), workspaceViewColumns()[0], input.checked);
      renderWorkspaceViewRail();
    });
  });
  target.querySelectorAll("[data-view-navigate]").forEach(cell => {
    let navigationTimer = null;
    cell.addEventListener("click", event => {
      if (event.target?.closest?.("input,textarea,button")) return;
      clearTimeout(navigationTimer);
      navigationTimer = setTimeout(() => {
        navigationTimer = null;
        navigateToWorkspaceView(cell.dataset.viewNavigate);
      }, 220);
    });
    cell.addEventListener("keydown", event => {
      if (event.key !== "Enter") return;
      if (!workspaceSnapshotMode()) return;
      event.preventDefault();
      navigateToWorkspaceView(cell.dataset.viewNavigate);
    });
    cell.addEventListener("dblclick", event => {
      event.preventDefault();
      event.stopPropagation();
      clearTimeout(navigationTimer);
      navigationTimer = null;
    });
  });
  target.querySelectorAll("[data-view-table-toggle]").forEach(button => {
    button.addEventListener("click", () => toggleWorkspaceViewTable(button.dataset.viewTableToggle));
  });
}

function bindWorkspaceViewDialog() {
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
  if (state.workspaceAppliedViewNames.size) {
    setServeStatus(t("clear_conditions_before_saving_view", "Clear applied views before saving a new view."), true);
    return;
  }
  const dialog = document.querySelector?.("[data-view-save-dialog]");
  if (!dialog) return;
  bindWorkspaceViewDialog();
  const nameInput = dialog.querySelector?.("[data-view-name-input]");
  openModalSurface(dialog, {
    opener,
    bodyClass: "view-save-open",
    focusTarget: nameInput,
  });
  if (nameInput) {
    nameInput.value = workspaceViewDefaultName();
  }
  const notesInput = dialog.querySelector?.("[data-view-notes-input]");
  if (notesInput) notesInput.value = "";
  const workspaceLocation = dialog.querySelector?.('[name="view_location"][value="workspace"]');
  const browserLocation = dialog.querySelector?.('[name="view_location"][value="browser"]');
  if (adminMode() && workspaceLocation) workspaceLocation.checked = true;
  else if (browserLocation) browserLocation.checked = true;
  renderWorkspaceViewCurrentConfiguration(dialog);
}

function workspaceViewDefaultName(filters = currentWorkspaceViewFilters(), groupBy = state.leaderboardSummaryGroupBy) {
  const suffix = ` - ${["agent", "model", "category", "task", "job", "provider", "overall"].includes(groupBy) ? groupBy : "agent"}`;
  const prefix = listValue(filters?.tags).length ? listValue(filters.tags).join(",") : "All";
  const maximumPrefixLength = Math.max(0, 120 - suffix.length);
  const truncated = prefix.length > maximumPrefixLength ? prefix.slice(0, maximumPrefixLength).replace(/[,\s]+$/g, "") : prefix;
  return `${truncated || "All"}${suffix}`.slice(-120);
}

function closeWorkspaceViewSaveDialog(options = {}) {
  const dialog = document.querySelector?.("[data-view-save-dialog]");
  return closeModalSurface(dialog, options);
}

function currentWorkspaceViewFilters() {
  const query = state.catalogQuery || {};
  return workspaceViewFilters({
    state: query.state,
    search: query.search,
    categories: query.categories,
    tags: query.tags,
    agents: query.agents,
    models: query.models,
    tasks: query.tasks,
    jobs: query.jobs,
    providers: query.providers,
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
  if (filters.categories.length) fields.push([t("category", "Category"), filters.categories.join(", ")]);
  if (filters.tags.length) fields.push([t("tags", "Tags"), filters.tags.join(", ")]);
  if (filters.agents.length) fields.push([t("agent", "Agent"), filters.agents.join(", ")]);
  if (filters.models.length) fields.push([t("model", "Model"), filters.models.join(", ")]);
  if (filters.tasks.length) fields.push([t("task", "Task"), filters.tasks.join(", ")]);
  if (filters.jobs.length) fields.push([t("job", "Job"), filters.jobs.join(", ")]);
  if (filters.providers.length) fields.push([t("provider", "Provider"), filters.providers.join(", ")]);
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
  if (filters.categories.length) compact.categories = [...filters.categories];
  if (filters.tags.length) compact.tags = [...filters.tags];
  if (filters.agents.length) compact.agents = [...filters.agents];
  if (filters.models.length) compact.models = [...filters.models];
  if (filters.tasks.length) compact.tasks = [...filters.tasks];
  if (filters.jobs.length) compact.jobs = [...filters.jobs];
  if (filters.providers.length) compact.providers = [...filters.providers];
  if (filters.results.length) compact.results = [...filters.results];
  return compact;
}

async function saveWorkspaceView(dialog) {
  const name = String(dialog.querySelector?.("[data-view-name-input]")?.value || "").trim();
  const notes = String(dialog.querySelector?.("[data-view-notes-input]")?.value || "");
  const requestedLocation = String(dialog.querySelector?.('[name="view_location"]:checked')?.value || "browser");
  const location = adminMode() && requestedLocation === "workspace" ? "workspace" : "browser";
  const payload = {
    name,
    filters: workspaceViewFilterConfig(),
    group_by: state.leaderboardSummaryGroupBy,
    notes,
  };
  try {
    const repository = workspaceViewRepository();
    if (!repository) return;
    try {
      await repository.save(payload, { location, overwrite: false });
    } catch (error) {
      if (!String(error?.message || error).includes("already exists")) throw error;
      const prompt = workspaceViewMessage("view_overwrite_confirm", "Replace the saved view {name}?", { name });
      if (typeof window.confirm === "function" && !window.confirm(prompt)) return;
      await repository.save(payload, { location, overwrite: true });
    }
    state.workspaceViews = repository.list();
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
      const appliedBefore = new Set(state.workspaceAppliedViewNames);
      try {
        const repository = workspaceViewRepository();
        const views = repository ? await repository.refresh() : workspaceViews();
        if (revision !== state.workspaceViewsRefreshVersion) {
          state.workspaceViewsRefreshQueued = true;
          continue;
        }
        let summaries = [];
        let generation = Number(state.catalogPage?.generation || 0);
        if (views.length) {
          const serverCount = views.filter(view => view.origin === "server").length;
          const browserIds = views.filter(view => view.origin === "browser").map(view => view.id);
          const [serverSummary, browserSummary] = await Promise.all([
            serverCount ? serveApi("/api/views/summary") : Promise.resolve({ views: [] }),
            browserIds.length ? serveApi("/api/views/summary", {
              method: "POST",
              body: { browser_views: repository.queryPayload(browserIds).browser_views },
            }) : Promise.resolve({ views: [] }),
          ]);
          if (revision !== state.workspaceViewsRefreshVersion) {
            state.workspaceViewsRefreshQueued = true;
            continue;
          }
          summaries = [...listValue(serverSummary?.views), ...listValue(browserSummary?.views)];
          generation = Number(serverSummary?.generation || browserSummary?.generation || 0);
        }
        state.workspaceViews = views;
        state.workspaceViewSummaries = summaries;
        state.workspaceViewsLoaded = true;
        state.workspaceViewSummaryGeneration = generation;
        pruneWorkspaceViewState();
        renderWorkspaceViewRail();
        if ($("leaderboard-summary")) renderLeaderboardSummary(leaderboardRows());
        if (Array.from(appliedBefore).some(id => !state.workspaceAppliedViewNames.has(id))) {
          if (state.workspaceAppliedViewNames.size) await reloadAppliedWorkspaceViews();
          else await clearWorkspaceViewConditions();
        }
      } catch (error) {
        if (revision === state.workspaceViewsRefreshVersion) {
          const repository = workspaceViewRepository();
          state.workspaceViews = repository?.list() || [];
          state.workspaceViewsLoaded = Boolean(repository?.ready());
          pruneWorkspaceViewState();
          renderWorkspaceViewRail();
          if (Array.from(appliedBefore).some(id => !state.workspaceAppliedViewNames.has(id))) {
            if (state.workspaceAppliedViewNames.size) await reloadAppliedWorkspaceViews();
            else await clearWorkspaceViewConditions();
          }
          setServeStatus(error.message || String(error), true);
        }
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
  const ids = new Set(workspaceViews().map(view => view.id));
  state.workspaceViewTableOpen = new Set(
    Array.from(state.workspaceViewTableOpen).filter(id => ids.has(id))
  );
  state.workspaceViewSelection = new Set(
    Array.from(state.workspaceViewSelection).filter(id => ids.has(id))
  );
  state.workspaceAppliedViewNames = new Set(
    Array.from(state.workspaceAppliedViewNames).filter(id => ids.has(id))
  );
  state.catalogQuery.views = workspaceViewQueryPayload(
    Array.from(state.workspaceAppliedViewNames)
  ).views;
}

function renderWorkspaceViewRail() {
  const target = $("workspace-views");
  if (!target) return;
  captureWorkspaceViewScrollState();
  const allViews = workspaceViews();
  const views = workspaceViewRows();
  if (!allViews.length) state.workspaceViewsClosed = false;
  const visible = allViews.length >= 1 && !state.workspaceViewsClosed;
  target.hidden = !visible;
  document.body?.classList?.toggle("workspace-views-open", visible);
  if (!visible) {
    target.innerHTML = "";
    return;
  }
  target.innerHTML = `<div class="workspace-views-head"><div><h2>${esc(t("saved_views", "Saved views"))}</h2><p>${esc(t("summary_scale_note", "Each metric has its own scale. Compare bars only within a metric."))}</p></div><button type="button" class="action-button compact" data-workspace-views-close>${esc(t("close", "Close"))}</button></div>
    ${renderWorkspaceViewIndex(views, allViews)}
    <div class="workspace-view-list" data-workspace-view-list>${views.map(renderWorkspaceViewCard).join("")}</div>`;
  bindWorkspaceViewControls(target);
  restoreWorkspaceViewScrollState();
}

function captureWorkspaceViewScrollState() {
  const scroll = state.workspaceViewScroll;
  const analysis = document.querySelector?.("[data-workspace-main-scroll]");
  const index = document.querySelector?.("#workspace-views .workspace-view-index-shell .table-wrap");
  const cards = document.querySelector?.("#workspace-views [data-workspace-view-list]");
  if (analysis && document.body?.classList?.contains("workspace-views-open")) scroll.analysisTop = analysis.scrollTop || 0;
  if (index) {
    scroll.indexTop = index.scrollTop || 0;
    scroll.indexLeft = index.scrollLeft || 0;
  }
  if (cards) scroll.cardsTop = cards.scrollTop || 0;
}

function restoreWorkspaceViewScrollState() {
  const scroll = state.workspaceViewScroll;
  const analysis = document.querySelector?.("[data-workspace-main-scroll]");
  const index = document.querySelector?.("#workspace-views .workspace-view-index-shell .table-wrap");
  const cards = document.querySelector?.("#workspace-views [data-workspace-view-list]");
  if (analysis) analysis.scrollTop = scroll.analysisTop || 0;
  if (index) {
    index.scrollTop = scroll.indexTop || 0;
    index.scrollLeft = scroll.indexLeft || 0;
  }
  if (cards) cards.scrollTop = scroll.cardsTop || 0;
}

function closeWorkspaceViewRail() {
  if (!workspaceViews().length) return;
  captureWorkspaceViewScrollState();
  state.workspaceViewsClosed = true;
  renderWorkspaceViewRail();
  renderLeaderboardSummary(leaderboardRows());
  focusSoon(document.querySelector?.("[data-workspace-views-open]"));
}

function openWorkspaceViewRail() {
  if (!workspaceViews().length) return;
  state.workspaceViewsClosed = false;
  renderWorkspaceViewRail();
  renderLeaderboardSummary(leaderboardRows());
  restoreWorkspaceViewScrollState();
  focusSoon(document.querySelector?.("[data-workspace-views-close]"));
}

function renderWorkspaceViewIndex(views = workspaceViewRows(), allViews = workspaceViews()) {
  const selected = allViews.filter(view => state.workspaceViewSelection.has(view.id));
  const selectedCount = selected.length;
  const localDeleteCount = selected.filter(view => view.origin === "browser").length;
  const deleteCount = adminMode() ? selectedCount : localDeleteCount;
  const deleteLabel = adminMode()
    ? t("delete_views", "Delete")
    : workspaceViewMessage("delete_local_views", "Delete local ({count})", { count: localDeleteCount });
  return `<section class="workspace-view-index" aria-label="${esc(t("saved_views", "Saved views"))}">
    ${serveMode() ? `<div class="workspace-view-index-toolbar">
      <span data-view-selection-count aria-live="polite">${esc(workspaceViewMessage("views_selected_count", "{count} selected", { count: selectedCount }))}</span>
      <div class="workspace-view-index-actions">
        <button type="button" class="action-button" data-view-apply-selected ${selectedCount ? "" : "disabled"}>${esc(t("apply", "Apply"))}</button>
        <button type="button" class="action-button" data-view-export-selected ${selectedCount ? "" : "disabled"}>${esc(t("export_excel", "Export Excel"))}</button>
        <button type="button" class="action-button danger" data-view-delete-selected ${deleteCount ? "" : "disabled"}>${esc(deleteLabel)}</button>
      </div>
    </div>` : ""}
    ${renderDataTable({
      tableId: "workspace-views",
      columns: workspaceViewColumns(),
      rows: views,
      rowKey: view => view.id,
      filterOptionsRows: allViews,
      tableClass: "workspace-view-index-table",
      shellClass: "workspace-view-index-shell",
      rowClass: view => `${state.workspaceViewSelection.has(view.id) ? "selected " : ""}${state.workspaceAppliedViewNames.has(view.id) ? "applied" : ""}`,
      rowAttrs: view => `data-view-index-row="${esc(view.id)}"`,
    })}
  </section>`;
}

function syncWorkspaceViewIndexActions(target = $("workspace-views")) {
  const selected = workspaceViews().filter(view => state.workspaceViewSelection.has(view.id));
  const count = selected.length;
  target?.querySelectorAll?.("[data-view-apply-selected],[data-view-export-selected]").forEach(button => { button.disabled = count < 1; });
  const deletable = adminMode() ? count : selected.filter(view => view.origin === "browser").length;
  const deleteButton = target?.querySelector?.("[data-view-delete-selected]");
  if (deleteButton) deleteButton.disabled = deletable < 1;
  const label = target?.querySelector?.("[data-view-selection-count]");
  if (label) label.textContent = workspaceViewMessage("views_selected_count", "{count} selected", { count });
}

function renderWorkspaceViewCard(view) {
  const summary = workspaceViewSummaryForName(view.name) || { matched_count: 0, groups: [] };
  const matchedCount = Number(summary.matched_count || 0);
  const filters = workspaceViewFilters(view.filters);
  const applied = state.workspaceAppliedViewNames.has(view.id);
  return `<article class="workspace-view-card leaderboard-summary${applied ? " applied" : ""}" data-workspace-view="${esc(view.id)}" tabindex="-1">
    <header class="workspace-view-card-head panel-head leaderboard-summary-head">
      <div><h3>${esc(view.name)}</h3><p>${esc(workspaceViewMessage("saved_view_matches", "{count} matching sessions", { count: fmtNum(matchedCount) }))}</p></div>
    </header>
    ${renderWorkspaceViewFilters(filters, view.group_by)}
    ${view.notes ? `<div class="note-body workspace-view-notes">${renderMarkdown(view.notes)}</div>` : ""}
    ${matchedCount ? `${renderWorkspaceViewTableDisclosure(view, summary)}${renderWorkspaceViewCharts(summary, view.group_by)}` : `<p class="workspace-view-empty">${esc(t("saved_view_empty", "No matching sessions."))}</p>`}
  </article>`;
}

function renderWorkspaceViewFilters(filters, groupBy) {
  return `<p class="workspace-view-filters">${esc(workspaceViewConfigurationLabel({ filters, group_by: groupBy }))}</p>`;
}

function workspaceViewConfigurationParts(view) {
  const filters = workspaceViewFilters(view?.filters);
  return [
    filters.state !== "active" ? `${t("source", "Source")}: ${workspaceViewStateLabel(filters.state)}` : "",
    filters.search ? `${t("search", "Search")}: ${filters.search}` : "",
    filters.categories.length ? `${t("category", "Category")}: ${filters.categories.join(", ")}` : "",
    filters.tags.length ? `${t("tags", "Tags")}: ${filters.tags.join(", ")}` : "",
    filters.agents.length ? `${t("agent", "Agent")}: ${filters.agents.join(", ")}` : "",
    filters.models.length ? `${t("model", "Model")}: ${filters.models.join(", ")}` : "",
    filters.tasks.length ? `${t("task", "Task")}: ${filters.tasks.join(", ")}` : "",
    filters.jobs.length ? `${t("job", "Job")}: ${filters.jobs.join(", ")}` : "",
    filters.providers.length ? `${t("provider", "Provider")}: ${filters.providers.join(", ")}` : "",
    filters.results.length ? `${t("result", "Result")}: ${filters.results.join(", ")}` : "",
    `${t("summary_group_by", "Group by")}: ${workspaceViewGroupByLabel(view?.group_by)}`,
  ].filter(Boolean);
}

function workspaceViewConfigurationLabel(view) {
  return workspaceViewConfigurationParts(view).join(" · ") || t("summary_overall", "Overall");
}

function workspaceViewOtherConditionsParts(view) {
  const filters = workspaceViewFilters(view?.filters);
  return [
    filters.state !== "active" ? `${t("source", "Source")}: ${workspaceViewStateLabel(filters.state)}` : "",
    filters.search ? `${t("search", "Search")}: ${filters.search}` : "",
    filters.agents.length ? `${t("agent", "Agent")}: ${filters.agents.join(", ")}` : "",
    filters.results.length ? `${t("result", "Result")}: ${filters.results.map(statusLabel).join(", ")}` : "",
  ].filter(Boolean);
}

function workspaceViewOtherConditionsLabel(view) {
  return workspaceViewOtherConditionsParts(view).join(" · ") || t("all", "All");
}

function workspaceViewOtherConditionsYaml(view) {
  const filters = workspaceViewFilterConfig(workspaceViewFilters(view?.filters));
  const lines = [];
  ["state", "search"].forEach(key => {
    if (filters[key]) lines.push(`${key}: ${JSON.stringify(filters[key])}`);
  });
  ["agents", "results"].forEach(key => {
    if (!listValue(filters[key]).length) return;
    lines.push(`${key}:`);
    filters[key].forEach(value => lines.push(`  - ${JSON.stringify(String(value))}`));
  });
  return lines.length ? `${lines.join("\n")}\n` : "";
}

function workspaceViewConfigurationYaml(view, options = {}) {
  const filters = workspaceViewFilterConfig(workspaceViewFilters(view?.filters));
  const lines = [];
  const otherConditions = Object.prototype.hasOwnProperty.call(options, "otherConditionsYaml")
    ? String(options.otherConditionsYaml || "").trimEnd()
    : null;
  const hasFilters = otherConditions !== null
    ? Boolean(otherConditions.trim() || listValue(filters.categories).length || listValue(filters.tags).length || listValue(filters.models).length || listValue(filters.tasks).length || listValue(filters.jobs).length || listValue(filters.providers).length)
    : Object.keys(filters).length > 0;
  if (hasFilters) {
    lines.push("filters:");
    if (otherConditions !== null) {
      otherConditions.split("\n").forEach(line => lines.push(`  ${line}`));
    } else {
      ["state", "search"].forEach(key => {
        if (filters[key]) lines.push(`  ${key}: ${JSON.stringify(filters[key])}`);
      });
    }
    const listKeys = otherConditions !== null
      ? ["categories", "tags", "models", "tasks", "jobs", "providers"]
      : ["categories", "tags", "agents", "models", "results", "tasks", "jobs", "providers"];
    listKeys.forEach(key => {
      if (!listValue(filters[key]).length) return;
      lines.push(`  ${key}:`);
      filters[key].forEach(value => lines.push(`    - ${JSON.stringify(String(value))}`));
    });
  }
  lines.push(`group_by: ${JSON.stringify(view?.group_by || "agent")}`);
  return `${lines.join("\n")}\n`;
}

function workspaceViewCommaValues(value) {
  const seen = new Set();
  return String(value || "").split(/[,，]/).map(item => item.trim()).filter(item => {
    if (!item || seen.has(item)) return false;
    seen.add(item);
    return true;
  });
}

function workspaceViewScalarValues(value) {
  const seen = new Set();
  const values = Array.isArray(value) ? value : [value];
  return values.map(item => String(item || "").trim()).filter(item => {
    if (!item || seen.has(item)) return false;
    seen.add(item);
    return true;
  });
}

function workspaceViewConfigurationEditValue(view, field, value) {
  if (field === "other_conditions") return workspaceViewConfigurationYaml(view, { otherConditionsYaml: value });
  const next = {
    ...view,
    filters: workspaceViewFilters(view?.filters),
  };
  if (field === "categories") next.filters.categories = workspaceViewScalarValues(value);
  if (["tags", "models", "tasks", "jobs", "providers"].includes(field)) next.filters[field] = Array.isArray(value) ? value : workspaceViewCommaValues(value);
  if (field === "group_by") next.group_by = ["overall", "agent", "model", "category", "task", "job", "provider"].includes(value) ? value : view.group_by;
  return workspaceViewConfigurationYaml(next);
}

function parseWorkspaceViewOtherConditions(value) {
  const filters = {};
  let listKey = null;
  String(value || "").split(/\r?\n/).forEach((rawLine, index) => {
    const line = rawLine.trim();
    if (!line) return;
    const listMatch = line.match(/^([a-z_]+):$/);
    if (listMatch) {
      listKey = listMatch[1];
      if (!["agents", "results"].includes(listKey)) throw new Error(`Unsupported condition on line ${index + 1}.`);
      filters[listKey] = [];
      return;
    }
    const itemMatch = line.match(/^-\s+(.+)$/);
    if (itemMatch && listKey) {
      let parsed;
      try { parsed = JSON.parse(itemMatch[1]); } catch { parsed = itemMatch[1]; }
      if (typeof parsed !== "string") throw new Error(`Condition value on line ${index + 1} must be text.`);
      filters[listKey].push(parsed);
      return;
    }
    const scalarMatch = line.match(/^(state|search):\s*(.*)$/);
    if (!scalarMatch) throw new Error(`Unsupported condition on line ${index + 1}.`);
    listKey = null;
    let parsed;
    try { parsed = JSON.parse(scalarMatch[2]); } catch { parsed = scalarMatch[2]; }
    if (typeof parsed !== "string") throw new Error(`Condition value on line ${index + 1} must be text.`);
    filters[scalarMatch[1]] = parsed;
  });
  return filters;
}

function workspaceViewEditedDefinition(view, field, value) {
  const next = {
    name: view.name,
    filters: workspaceViewFilters(view.filters),
    group_by: view.group_by,
    notes: view.notes,
  };
  if (field === "categories") next.filters.categories = workspaceViewScalarValues(value);
  if (["tags", "models", "tasks", "jobs", "providers"].includes(field)) {
    next.filters[field] = Array.isArray(value) ? value : workspaceViewCommaValues(value);
  }
  if (field === "group_by") next.group_by = value;
  if (field === "other_conditions") {
    const parsed = parseWorkspaceViewOtherConditions(value);
    next.filters.state = parsed.state || "active";
    next.filters.search = parsed.search || "";
    next.filters.agents = listValue(parsed.agents);
    next.filters.results = listValue(parsed.results);
  }
  return { ...next, filters: workspaceViewFilterConfig(next.filters) };
}

function navigateToWorkspaceView(id) {
  const card = Array.from($("workspace-views")?.querySelectorAll?.("[data-workspace-view]") || [])
    .find(item => item.dataset?.workspaceView === String(id || ""));
  if (!card) return;
  card.scrollIntoView?.({ behavior: "smooth", block: "start" });
  card.focus?.({ preventScroll: true });
  card.classList?.add("navigated");
  setTimeout(() => card.classList?.remove("navigated"), 1200);
}

async function commitWorkspaceViewCellEdit(view, field, value) {
  const id = String(view?.id || "");
  if (!id || (view.origin !== "browser" && !adminMode()) || !["name", "categories", "tags", "models", "tasks", "jobs", "providers", "group_by", "other_conditions", "notes"].includes(field)) throw new Error(t("view_edit_unavailable", "View editing is unavailable"));
  const appliedBefore = state.workspaceAppliedViewNames.has(id);
  try {
    const repository = workspaceViewRepository();
    if (!repository) throw new Error(t("view_edit_unavailable", "View editing is unavailable"));
    const currentView = workspaceViewForId(id) || view;
    const configurationField = ["categories", "tags", "models", "tasks", "jobs", "providers", "group_by", "other_conditions"].includes(field);
    const wireField = configurationField ? "configuration" : field;
    const definition = configurationField
      ? workspaceViewEditedDefinition(currentView, field, value)
      : null;
    const wireValue = configurationField
      ? (currentView.origin === "browser" ? definition : workspaceViewConfigurationYaml(definition))
      : value;
    let updated;
    try {
      updated = await repository.update(id, { field: wireField, value: wireValue });
    } catch (error) {
      if (currentView.origin !== "browser" || !String(error?.message || error).includes("already exists")) throw error;
      const nextName = field === "name" ? String(value || "").trim() : currentView.name;
      const prompt = workspaceViewMessage("view_overwrite_confirm", "Replace the saved view {name}?", { name: nextName });
      if (typeof window.confirm === "function" && !window.confirm(prompt)) throw error;
      updated = await repository.update(id, { field: wireField, value: wireValue, overwrite: true });
    }
    if (updated.id !== id) replaceWorkspaceViewStateName(id, updated.id);
    state.workspaceViews = repository.list();
    state.workspaceViewSummaries = [];
    state.workspaceViewsLoaded = true;
    state.workspaceViewsRefreshVersion += 1;
    renderWorkspaceViewRail();
    await refreshWorkspaceViews();
    if (appliedBefore) await reloadAppliedWorkspaceViews();
    setServeStatus(t("view_updated", "View updated"));
    return { rowKey: updated.id };
  } catch (error) {
    if (error?.status === 409) await refreshWorkspaceViews();
    setServeStatus(error.message || String(error), true);
    throw error;
  }
}

function replaceWorkspaceViewStateName(previousName, nextName) {
  [state.workspaceViewSelection, state.workspaceAppliedViewNames, state.workspaceViewTableOpen].forEach(values => {
    if (!values.has(previousName)) return;
    values.delete(previousName);
    values.add(nextName);
  });
}

async function deleteSelectedWorkspaceViews() {
  const selectedIds = selectedWorkspaceViewIds();
  const ids = adminMode()
    ? selectedIds
    : selectedIds.filter(id => workspaceViewForId(id)?.origin === "browser");
  if (!ids.length) return;
  const prompt = workspaceViewMessage(
    "view_delete_confirm",
    "Permanently delete {count} selected views?",
    { count: ids.length },
  );
  if (typeof window.confirm === "function" && !window.confirm(prompt)) return;
  const appliedChanged = ids.some(id => state.workspaceAppliedViewNames.has(id));
  try {
    const repository = workspaceViewRepository();
    if (!repository) return;
    await repository.delete(ids);
    ids.forEach(id => {
      state.workspaceViewSelection.delete(id);
      state.workspaceAppliedViewNames.delete(id);
      state.workspaceViewTableOpen.delete(id);
    });
    state.workspaceViews = repository.list();
    state.workspaceViewSummaries = [];
    state.workspaceViewsLoaded = true;
    state.workspaceViewsRefreshVersion += 1;
    renderWorkspaceViewRail();
    await refreshWorkspaceViews();
    if (appliedChanged) {
      if (state.workspaceAppliedViewNames.size) await reloadAppliedWorkspaceViews();
      else await clearWorkspaceViewConditions();
    }
    setServeStatus(t("views_deleted", "Views deleted"));
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  }
}

function workspaceViewGroupByLabel(groupBy) {
  if (groupBy === "model") return t("model", "Model");
  if (groupBy === "category") return t("category", "Category");
  if (groupBy === "task") return t("task", "Task");
  if (groupBy === "job") return t("job", "Job");
  if (groupBy === "provider") return t("provider", "Provider");
  if (groupBy === "agent") return t("agent", "Agent");
  return t("summary_overall", "Overall");
}

function workspaceViewGroupLabel(group, groupBy) {
  return groupBy === "overall" && group?.key === "overall"
    ? t("summary_overall", "Overall")
    : String(group?.label || "-");
}

function renderWorkspaceViewTableDisclosure(view, summary) {
  const open = state.workspaceViewTableOpen.has(view.id);
  const groups = listValue(summary.groups);
  const unit = leaderboardSummaryGroupUnit(view.group_by);
  const description = `${leaderboardSummaryDefinitions().length} ${t("summary_metrics", "metrics")} · ${groups.length} ${unit}`;
  const regionId = `workspace-view-table-${encodeURIComponent(view.id)}`;
  return `<div class="leaderboard-summary-table-disclosure workspace-view-table-disclosure">
    <button type="button" class="leaderboard-summary-table-toggle" data-view-table-toggle="${esc(view.id)}" aria-expanded="${open}" aria-controls="${esc(regionId)}">
      <span><strong>${esc(t(open ? "summary_hide_table" : "summary_show_table", open ? "Hide summary table" : "Show summary table"))}</strong><small>${esc(description)}</small></span>
      <i aria-hidden="true">${open ? "−" : "+"}</i>
    </button>
    ${open ? `<div id="${esc(regionId)}">${renderWorkspaceViewTable(summary, view.group_by)}</div>` : ""}
  </div>`;
}

function renderWorkspaceViewTable(summary, groupBy) {
  const groups = listValue(summary.groups);
  const statistics = leaderboardSummaryStatistics();
  const groupHeading = leaderboardSummaryGroupHeading(groupBy);
  return `<div class="table-shell leaderboard-summary-shell workspace-view-table-shell"><div class="table-wrap"><table class="data-table leaderboard-summary-table workspace-view-table">
    <thead><tr><th ${tableValueAttributes("identity", t("summary_metric", "Metric"))}>${tableCellContent(esc(t("summary_metric", "Metric")))}</th><th ${tableValueAttributes("identity", groupHeading)}>${tableCellContent(esc(groupHeading))}</th><th ${tableValueAttributes("number", t("summary_count", "Count"), "num")}>${tableCellContent(esc(t("summary_count", "Count")))}</th>${statistics.map(statistic => `<th ${tableValueAttributes("number", statistic.label, "num")}>${tableCellContent(esc(statistic.label))}</th>`).join("")}</tr></thead>
    <tbody>${leaderboardSummaryDefinitions().map(definition => groups.map((group, index) => {
      const metric = listValue(group.metrics).find(item => item?.key === definition.key);
      const groupLabel = workspaceViewGroupLabel(group, groupBy);
      return `<tr${index === 0 ? " data-summary-group-start" : ""}>${index === 0 ? `<th ${tableValueAttributes("identity", definition.label, "summary-metric-cell")} scope="rowgroup" rowspan="${groups.length}">${tableCellContent(esc(definition.label))}</th>` : ""}<th ${tableValueAttributes("identity", groupLabel, "summary-group-cell")} scope="row">${tableCellContent(`<strong>${esc(groupLabel)}</strong><span>n=${fmtNum(group.count)}</span>`)}</th><td ${tableValueAttributes("number", fmtNum(metric?.count), "num")}>${tableCellContent(fmtNum(metric?.count))}</td>${statistics.map(statistic => { const value = leaderboardSummaryValue(metric, statistic.value(metric)); return `<td ${tableValueAttributes("number", value, "num")}>${tableCellContent(esc(value))}</td>`; }).join("")}</tr>`;
    }).join("")).join("")}</tbody>
  </table></div></div>`;
}

function toggleWorkspaceViewTable(id) {
  const view = workspaceViewForId(id);
  if (!view) return;
  if (state.workspaceViewTableOpen.has(view.id)) state.workspaceViewTableOpen.delete(view.id);
  else state.workspaceViewTableOpen.add(view.id);
  renderWorkspaceViewRail();
}

function renderWorkspaceViewCharts(summary, groupBy) {
  const groups = listValue(summary.groups);
  const statistic = leaderboardSummaryStatistics()[0];
  const groupLabel = leaderboardSummaryGroupHeading(groupBy);
  return `<section class="workspace-view-charts" aria-label="${esc(`${statistic.label} · ${groupLabel}`)}">
    <div class="workspace-view-chart-head"><strong>${esc(`${statistic.label} · ${groupLabel}`)}</strong></div>
    <div class="workspace-view-chart-grid">${leaderboardSummaryDefinitions().map(definition => renderWorkspaceViewChart(definition, groups, statistic, groupBy)).join("")}</div>
  </section>`;
}

function renderWorkspaceViewChart(definition, groups, statistic, groupBy) {
  const values = groups.map(group => {
    const metric = listValue(group.metrics).find(item => item?.key === definition.key);
    return { group, metric, value: statistic.value(metric) };
  });
  const maximum = Math.max(0, ...values.map(item => summaryNumber(item.value) ?? 0));
  return `<section class="workspace-view-chart" data-view-chart="${esc(definition.key)}"><h4>${esc(definition.label)}</h4><div class="leaderboard-summary-bar-list">${values.map(item => {
    const numeric = summaryNumber(item.value);
    const formatted = leaderboardSummaryValue(item.metric, numeric);
    const width = maximum > 0 && numeric !== null ? Math.max(2, (numeric / maximum) * 100) : 0;
    const groupLabel = workspaceViewGroupLabel(item.group, groupBy);
    return `<div class="leaderboard-summary-bar" role="img" aria-label="${esc(`${groupLabel}; ${definition.label}; ${statistic.label} ${formatted}; n=${item.metric?.count || 0}`)}"><span class="leaderboard-summary-bar-label" title="${esc(groupLabel)}">${esc(groupLabel)}</span><span class="leaderboard-summary-bar-track"><i style="width:${Number(width.toFixed(2))}%"></i></span><span class="leaderboard-summary-bar-value"><strong>${esc(formatted)}</strong><small>n=${fmtNum(item.metric?.count || 0)}</small></span></div>`;
  }).join("")}</div></section>`;
}

function selectedWorkspaceViewIds() {
  return workspaceViews()
    .filter(view => state.workspaceViewSelection.has(view.id))
    .map(view => view.id);
}

function selectedWorkspaceViewNames() {
  return selectedWorkspaceViewIds().map(id => workspaceViewForId(id)?.name).filter(Boolean);
}

function workspaceViewQueryPayload(ids = Array.from(state.workspaceAppliedViewNames)) {
  const repository = workspaceViewRepository();
  if (repository?.ready()) return repository.queryPayload(ids);
  const selected = workspaceViews().filter(view => ids.includes(view.id));
  return {
    views: selected.length
      ? selected.filter(view => view.origin === "server").map(view => view.name)
      : listValue(state.catalogQuery?.views).map(String),
    browser_views: selected
      .filter(view => view.origin === "browser")
      .map(view => ({ name: view.name, filters: workspaceViewFilterConfig(view.filters), group_by: view.group_by, notes: view.notes })),
  };
}

function browserWorkspaceViewDefinitions() {
  return workspaceViews()
    .filter(view => view.origin === "browser")
    .map(view => ({ name: view.name, filters: workspaceViewFilterConfig(view.filters), group_by: view.group_by, notes: view.notes }));
}

function exportSelectedWorkspaceViews() {
  const ids = selectedWorkspaceViewIds();
  if (!serveMode() || !ids.length) return;
  const payload = workspaceViewQueryPayload(ids);
  return serveDownload("summary_xlsx", {
    kind: "summary_xlsx",
    summary: { scope: "saved_views", ...payload }
  }, "peval-saved-views.xlsx");
}

function appliedWorkspaceViewNames() {
  return workspaceViewQueryPayload(Array.from(state.workspaceAppliedViewNames)).views;
}

async function applySelectedWorkspaceViews() {
  const ids = selectedWorkspaceViewIds();
  if (!ids.length || !serveMode()) return;
  const payload = workspaceViewQueryPayload(ids);
  closeOpenSubmenus();
  state.rowSelection.clear();
  state.sourceSelection.clear();
  state.selectedSourceKey = null;
  state.selectedArtifactRevision = null;
  state.selectedTrial = null;
  state.selectedStep = null;
  state.workspaceAppliedViewNames = new Set(ids);
  state.search.query = "";
  state.search.scope = "all";
  state.search.normalSourceMode = "all";
  const controls = tableControls("leaderboard");
  controls.sort = "finished_at_ms";
  controls.direction = "desc";
  controls.filters = {
    source_category: [],
    source_tags: [],
    agent: [],
    model: [],
    task_name: [],
    job_name: [],
    model_provider: [],
    status: [],
  };
  renderWorkspaceViewRail();
  await loadCatalogPage({
    state: "all",
    page: 1,
    page_size: 100,
    search: "",
    sort: "last_turn_end",
    direction: "desc",
    categories: [],
    tags: [],
    agents: [],
    models: [],
    tasks: [],
    jobs: [],
    providers: [],
    results: [],
    views: payload.views,
  }, { force: true });
}

async function reloadAppliedWorkspaceViews() {
  const ids = Array.from(state.workspaceAppliedViewNames);
  const payload = workspaceViewQueryPayload(ids);
  state.catalogQuery.views = payload.views;
  if (!ids.length) return;
  await loadCatalogPage({ page: 1, views: payload.views }, { force: true });
}

async function clearWorkspaceViewConditions() {
  if (!serveMode()) return;
  closeOpenSubmenus();
  state.workspaceAppliedViewNames.clear();
  state.workspaceViewSelection.clear();
  state.workspaceViewTableOpen.clear();
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
    source_category: [],
    source_tags: [],
    agent: [],
    model: [],
    task_name: [],
    job_name: [],
    model_provider: [],
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
    categories: [],
    tags: [],
    agents: [],
    models: [],
    tasks: [],
    jobs: [],
    providers: [],
    results: [],
    views: [],
  }, { force: true });
}

async function applyWorkspaceView(name) {
  const view = workspaceViewForName(name);
  if (!view) return;
  state.workspaceViewSelection = new Set([view.id]);
  return applySelectedWorkspaceViews();
}

async function cancelWorkspaceViewApplication() {
  return clearWorkspaceViewConditions();
}
export {
  appliedWorkspaceViewNames,
  applySelectedWorkspaceViews,
  applyWorkspaceView,
  browserWorkspaceViewDefinitions,
  bindWorkspaceViewControls,
  bindWorkspaceViewDialog,
  cancelWorkspaceViewApplication,
  captureWorkspaceViewScrollState,
  clearWorkspaceViewConditions,
  closeWorkspaceViewSaveDialog,
  closeWorkspaceViewRail,
  commitWorkspaceViewCellEdit,
  currentWorkspaceViewFilters,
  deleteSelectedWorkspaceViews,
  exportSelectedWorkspaceViews,
  navigateToWorkspaceView,
  openWorkspaceViewSaveDialog,
  openWorkspaceViewRail,
  pruneWorkspaceViewState,
  refreshWorkspaceViews,
  reloadAppliedWorkspaceViews,
  renderWorkspaceViewCard,
  renderWorkspaceViewChart,
  renderWorkspaceViewCharts,
  renderWorkspaceViewControls,
  renderWorkspaceViewCurrentConfiguration,
  renderWorkspaceViewFilters,
  renderWorkspaceViewIndex,
  renderWorkspaceViewRail,
  renderWorkspaceViewTable,
  renderWorkspaceViewTableDisclosure,
  renderWorkspaceViewValueList,
  replaceWorkspaceViewStateName,
  restoreWorkspaceViewScrollState,
  saveWorkspaceView,
  selectedWorkspaceViewIds,
  selectedWorkspaceViewNames,
  syncWorkspaceViewIndexActions,
  toggleWorkspaceViewTable,
  workspaceViewColumns,
  workspaceViewCommaValues,
  workspaceViewConfigurationEditValue,
  workspaceViewConfigurationLabel,
  workspaceViewConfigurationParts,
  workspaceViewConfigurationYaml,
  workspaceViewDefaultName,
  workspaceViewEditValue,
  workspaceViewFilterConfig,
  workspaceViewFilters,
  workspaceViewForId,
  workspaceViewForName,
  workspaceViewGroupByLabel,
  workspaceViewGroupLabel,
  workspaceViewMessage,
  workspaceViewOtherConditionsLabel,
  workspaceViewOtherConditionsParts,
  workspaceViewOtherConditionsYaml,
  workspaceViewRows,
  workspaceViewQueryPayload,
  workspaceViewScalarValues,
  workspaceViewStateLabel,
  workspaceViewSummaryForName,
  workspaceViews,
};
