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

function workspaceViewColumns() {
  const editableAttrs = (view, field) => workspaceSnapshotMode()
    ? `data-view-navigate="${esc(view.name)}" tabindex="0"`
    : `data-view-navigate="${esc(view.name)}" data-view-edit-field="${esc(field)}" tabindex="0"`;
  const columns = [
    { key: "name", label: t("view_name", "Name"), value: view => view.name, html: view => `<strong>${esc(view.name)}</strong>`, cellAttrs: view => editableAttrs(view, "name") },
    { key: "tags", label: t("tags", "Tags"), filterable: true, filterValues: view => view.filters.tags, value: view => view.filters.tags.join(", ") || "-", html: view => renderWorkspaceViewValueList(view.filters.tags), cellAttrs: view => editableAttrs(view, "tags") },
    { key: "models", label: t("model", "Models"), filterable: true, filterValues: view => view.filters.models, value: view => view.filters.models.join(", ") || "-", html: view => renderWorkspaceViewValueList(view.filters.models), cellAttrs: view => editableAttrs(view, "models") },
    { key: "group_by", label: t("summary_group_by", "Group by"), filterable: true, value: view => view.group_by, filterLabel: workspaceViewGroupByLabel, html: view => esc(workspaceViewGroupByLabel(view.group_by)), cellAttrs: view => editableAttrs(view, "group_by") },
    { key: "other_conditions", label: t("view_other_conditions", "Other conditions"), value: view => workspaceViewOtherConditionsLabel(view), html: view => `<span class="workspace-view-config-preview">${esc(workspaceViewOtherConditionsLabel(view))}</span>`, cellAttrs: view => editableAttrs(view, "other_conditions") },
    { key: "notes", label: t("view_notes", "Notes"), value: view => view.notes || "-", html: view => `<span>${esc(String(view.notes || "").replace(/\s+/g, " ").trim() || "-")}</span>`, className: "workspace-view-notes-cell", cellTitle: view => view.notes || "", cellAttrs: view => `${editableAttrs(view, "notes")} aria-label="${esc(view.notes || t("view_notes_empty", "No notes"))}"` },
  ];
  if (workspaceSnapshotMode()) return columns;
  return [
    selectionColumn({
      selectionKey: view => view?.name || "",
      selectionSet: () => state.workspaceViewSelection,
      rowInputAttr: name => `data-view-select="${esc(name)}"`,
      headerInputAttr: "data-view-select-visible",
      rowAriaLabel: name => workspaceViewMessage("select_view", "Select {name}", { name }),
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

function workspaceViewMessage(key, fallback, values = {}) {
  let message = String(t(key, fallback));
  Object.entries(values).forEach(([name, value]) => {
    message = message.replaceAll(`{${name}}`, String(value));
  });
  return message;
}

function renderWorkspaceViewControls() {
  if (!serveMode()) return "";
  const compositeApplied = state.workspaceAppliedViewNames.size > 0;
  return `<div class="workspace-view-controls" data-workspace-view-control>
    <button type="button" class="step-toggle-button leaderboard-summary-save" data-view-save ${compositeApplied ? `disabled title="${esc(t("clear_conditions_before_saving_view", "Clear applied views before saving a new view."))}"` : ""}>${esc(t("save_view", "Save view"))}</button>
  </div>`;
}

function bindWorkspaceViewControls(target) {
  if (!workspaceDisplayMode() || !target?.querySelectorAll) return;
  bindDataTableControls(target, "workspace-views", renderWorkspaceViewRail);
  target.querySelectorAll("[data-view-save]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      openWorkspaceViewSaveDialog(button);
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
      const name = String(input.dataset.viewSelect || "");
      if (input.checked) state.workspaceViewSelection.add(name);
      else state.workspaceViewSelection.delete(name);
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
      event.preventDefault();
      navigateToWorkspaceView(cell.dataset.viewNavigate);
    });
    cell.addEventListener("dblclick", event => {
      event.preventDefault();
      event.stopPropagation();
      clearTimeout(navigationTimer);
      navigationTimer = null;
      beginWorkspaceViewInlineEdit(cell);
    });
  });
  target.querySelectorAll("[data-view-table-toggle]").forEach(button => {
    button.addEventListener("click", () => toggleWorkspaceViewTable(button.dataset.viewTableToggle));
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
  if (state.workspaceAppliedViewNames.size) {
    setServeStatus(t("clear_conditions_before_saving_view", "Clear applied views before saving a new view."), true);
    return;
  }
  const dialog = document.querySelector?.("[data-view-save-dialog]");
  if (!dialog) return;
  bindWorkspaceViewDialog();
  state.workspaceViewSave.opener = opener || null;
  dialog.hidden = false;
  document.body?.classList?.add("view-save-open");
  const nameInput = dialog.querySelector?.("[data-view-name-input]");
  if (nameInput) {
    nameInput.value = workspaceViewDefaultName();
    focusSoon(nameInput);
  }
  const notesInput = dialog.querySelector?.("[data-view-notes-input]");
  if (notesInput) notesInput.value = "";
  renderWorkspaceViewCurrentConfiguration(dialog);
}

function workspaceViewDefaultName(filters = currentWorkspaceViewFilters(), groupBy = state.leaderboardSummaryGroupBy) {
  const suffix = ` - ${["agent", "model", "overall"].includes(groupBy) ? groupBy : "agent"}`;
  const prefix = listValue(filters?.tags).length ? listValue(filters.tags).join(",") : "All";
  const maximumPrefixLength = Math.max(0, 120 - suffix.length);
  const truncated = prefix.length > maximumPrefixLength ? prefix.slice(0, maximumPrefixLength).replace(/[,\s]+$/g, "") : prefix;
  return `${truncated || "All"}${suffix}`.slice(-120);
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
  state.workspaceViewSelection = new Set(
    Array.from(state.workspaceViewSelection).filter(name => names.has(name))
  );
  state.workspaceAppliedViewNames = new Set(
    Array.from(state.workspaceAppliedViewNames).filter(name => names.has(name))
  );
  state.catalogQuery.views = workspaceViews()
    .filter(view => state.workspaceAppliedViewNames.has(view.name))
    .map(view => view.name);
}

function renderWorkspaceViewRail() {
  const target = $("workspace-views");
  if (!target) return;
  const allViews = workspaceViews();
  const views = workspaceViewRows();
  const visible = allViews.length >= 1;
  target.hidden = !visible;
  document.body?.classList?.toggle("workspace-views-open", visible);
  if (!visible) {
    target.innerHTML = "";
    return;
  }
  target.innerHTML = `<div class="workspace-views-head"><div><h2>${esc(t("saved_views", "Saved views"))}</h2><p>${esc(t("summary_scale_note", "Each metric has its own scale. Compare bars only within a metric."))}</p></div></div>
    ${renderWorkspaceViewIndex(views, allViews)}
    <div class="workspace-view-list">${views.map(renderWorkspaceViewCard).join("")}</div>`;
  bindWorkspaceViewControls(target);
}

function renderWorkspaceViewIndex(views = workspaceViewRows(), allViews = workspaceViews()) {
  const selectedCount = allViews.filter(view => state.workspaceViewSelection.has(view.name)).length;
  return `<section class="workspace-view-index" aria-label="${esc(t("saved_views", "Saved views"))}">
    ${serveMode() ? `<div class="workspace-view-index-toolbar">
      <span data-view-selection-count aria-live="polite">${esc(workspaceViewMessage("views_selected_count", "{count} selected", { count: selectedCount }))}</span>
      <div class="workspace-view-index-actions">
        <button type="button" class="step-toggle-button" data-view-apply-selected ${selectedCount ? "" : "disabled"}>${esc(t("apply", "Apply"))}</button>
        <button type="button" class="step-toggle-button" data-view-export-selected ${selectedCount ? "" : "disabled"}>${esc(t("export_excel", "Export Excel"))}</button>
        <button type="button" class="step-toggle-button workspace-view-delete" data-view-delete-selected ${selectedCount ? "" : "disabled"}>${esc(t("delete_views", "Delete"))}</button>
      </div>
    </div>` : ""}
    ${renderDataTable({
      tableId: "workspace-views",
      columns: workspaceViewColumns(),
      rows: views,
      filterOptionsRows: allViews,
      tableClass: "workspace-view-index-table",
      shellClass: "workspace-view-index-shell",
      rowClass: view => `${state.workspaceViewSelection.has(view.name) ? "selected " : ""}${state.workspaceAppliedViewNames.has(view.name) ? "applied" : ""}`,
      rowAttrs: view => `data-view-index-row="${esc(view.name)}"`,
    })}
  </section>`;
}

function renderWorkspaceViewIndexRow(view) {
  const selected = state.workspaceViewSelection.has(view.name);
  const applied = state.workspaceAppliedViewNames.has(view.name);
  const notes = String(view.notes || "");
  const notesPreview = notes.replace(/\s+/g, " ").trim() || "-";
  const cellAttrs = field => `data-view-navigate="${esc(view.name)}" data-view-edit-field="${field}" tabindex="0"`;
  return `<tr class="${selected ? "selected " : ""}${applied ? "applied" : ""}" data-view-index-row="${esc(view.name)}">
    <td class="workspace-view-select-column"><input type="checkbox" data-view-select="${esc(view.name)}" aria-label="${esc(workspaceViewMessage("select_view", "Select {name}", { name: view.name }))}" ${selected ? "checked" : ""}></td>
    <td ${cellAttrs("name")}><strong>${esc(view.name)}</strong></td>
    <td ${cellAttrs("configuration")}><span class="workspace-view-config-preview">${esc(workspaceViewConfigurationLabel(view))}</span></td>
    <td ${cellAttrs("notes")} class="workspace-view-notes-cell" title="${esc(notes)}" aria-label="${esc(notes || t("view_notes_empty", "No notes"))}"><span>${esc(notesPreview)}</span></td>
  </tr>`;
}

function syncWorkspaceViewIndexActions(target = $("workspace-views")) {
  const count = workspaceViews().filter(view => state.workspaceViewSelection.has(view.name)).length;
  target?.querySelectorAll?.("[data-view-apply-selected],[data-view-export-selected],[data-view-delete-selected]").forEach(button => {
    button.disabled = count < 1;
  });
  const label = target?.querySelector?.("[data-view-selection-count]");
  if (label) label.textContent = workspaceViewMessage("views_selected_count", "{count} selected", { count });
}

function renderWorkspaceViewCard(view) {
  const summary = workspaceViewSummaryForName(view.name) || { matched_count: 0, groups: [] };
  const matchedCount = Number(summary.matched_count || 0);
  const filters = workspaceViewFilters(view.filters);
  const applied = state.workspaceAppliedViewNames.has(view.name);
  return `<article class="workspace-view-card leaderboard-summary${applied ? " applied" : ""}" data-workspace-view="${esc(view.name)}" tabindex="-1">
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
    filters.tags.length ? `${t("tags", "Tags")}: ${filters.tags.join(", ")}` : "",
    filters.agents.length ? `${t("agent", "Agent")}: ${filters.agents.join(", ")}` : "",
    filters.models.length ? `${t("model", "Model")}: ${filters.models.join(", ")}` : "",
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
    ? Boolean(otherConditions.trim() || listValue(filters.tags).length || listValue(filters.models).length)
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
    const listKeys = otherConditions !== null ? ["tags", "models"] : ["tags", "agents", "models", "results"];
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

function workspaceViewConfigurationEditValue(view, field, value) {
  if (field === "other_conditions") return workspaceViewConfigurationYaml(view, { otherConditionsYaml: value });
  const next = {
    ...view,
    filters: workspaceViewFilters(view?.filters),
  };
  if (field === "tags" || field === "models") next.filters[field] = workspaceViewCommaValues(value);
  if (field === "group_by") next.group_by = ["overall", "agent", "model"].includes(value) ? value : view.group_by;
  return workspaceViewConfigurationYaml(next);
}

function navigateToWorkspaceView(name) {
  const card = Array.from($("workspace-views")?.querySelectorAll?.("[data-workspace-view]") || [])
    .find(item => item.dataset?.workspaceView === String(name || ""));
  if (!card) return;
  card.scrollIntoView?.({ behavior: "smooth", block: "start" });
  card.focus?.({ preventScroll: true });
  card.classList?.add("navigated");
  setTimeout(() => card.classList?.remove("navigated"), 1200);
}

function beginWorkspaceViewInlineEdit(cell) {
  const name = String(cell?.dataset?.viewNavigate || "");
  const field = String(cell?.dataset?.viewEditField || "");
  const view = workspaceViewForName(name);
  if (!view || !["name", "tags", "models", "group_by", "other_conditions", "notes"].includes(field) || cell.querySelector?.("[data-view-inline-editor]")) return;
  const value = field === "name"
    ? view.name
    : field === "tags" || field === "models"
      ? view.filters[field].join(", ")
    : field === "group_by"
      ? view.group_by
    : field === "other_conditions"
      ? workspaceViewOtherConditionsYaml(view)
      : view.notes;
  const control = field === "group_by"
    ? `<select data-view-edit-control aria-label="${esc(t("summary_group_by", "Group by"))}">${["overall", "agent", "model"].map(option => `<option value="${option}" ${value === option ? "selected" : ""}>${esc(workspaceViewGroupByLabel(option))}</option>`).join("")}</select>`
    : field === "notes" || field === "other_conditions"
      ? `<textarea data-view-edit-control rows="${field === "other_conditions" ? 8 : 6}" aria-label="${esc(t(field === "other_conditions" ? "view_other_conditions" : "view_notes", field === "other_conditions" ? "Other conditions" : "Notes"))}">${esc(value)}</textarea>`
      : `<input data-view-edit-control type="text" value="${esc(value)}" aria-label="${esc(t(field === "name" ? "view_name" : field === "tags" ? "tags" : "model", field === "name" ? "View name" : field === "tags" ? "Tags" : "Models"))}">`;
  cell.innerHTML = `<div class="workspace-view-inline-editor" data-view-inline-editor>
    ${control}
    <div class="workspace-view-inline-status" data-view-edit-status aria-live="polite"></div>
    <div class="workspace-view-inline-actions">
      <button type="button" class="step-toggle-button" data-view-edit-save>${esc(t("save", "Save"))}</button>
      <button type="button" class="step-toggle-button" data-view-edit-cancel>${esc(t("cancel", "Cancel"))}</button>
    </div>
  </div>`;
  const input = cell.querySelector?.("[data-view-edit-control]");
  const save = () => saveWorkspaceViewInlineEdit(cell, name, field, input?.value || "");
  cell.querySelector?.("[data-view-edit-save]")?.addEventListener("click", event => {
    event.preventDefault();
    event.stopPropagation();
    save();
  });
  cell.querySelector?.("[data-view-edit-cancel]")?.addEventListener("click", event => {
    event.preventDefault();
    event.stopPropagation();
    renderWorkspaceViewRail();
  });
  input?.addEventListener?.("click", event => event.stopPropagation());
  input?.addEventListener?.("dblclick", event => event.stopPropagation());
  input?.addEventListener?.("keydown", event => {
    if (event.key === "Escape") {
      event.preventDefault();
      renderWorkspaceViewRail();
      return;
    }
    const shouldSave = ["name", "tags", "models", "group_by"].includes(field)
      ? event.key === "Enter"
      : event.key === "Enter" && (event.ctrlKey || event.metaKey);
    if (!shouldSave) return;
    event.preventDefault();
    save();
  });
  input?.focus?.();
  if (field === "name") input?.select?.();
}

async function saveWorkspaceViewInlineEdit(cell, name, field, value) {
  const status = cell?.querySelector?.("[data-view-edit-status]");
  const buttons = cell?.querySelectorAll?.("[data-view-edit-save],[data-view-edit-cancel]") || [];
  buttons.forEach(button => { button.disabled = true; });
  if (status) status.textContent = "";
  const appliedBefore = state.workspaceAppliedViewNames.has(name);
  try {
    const view = workspaceViewForName(name);
    const configurationField = ["tags", "models", "group_by", "other_conditions"].includes(field);
    const wireField = configurationField ? "configuration" : field;
    const wireValue = configurationField ? workspaceViewConfigurationEditValue(view, field, value) : value;
    const response = await serveApi("/api/views/update", {
      method: "POST",
      body: { name, field: wireField, value: wireValue },
    });
    const updatedName = String(response?.view?.name || name);
    if (updatedName !== name) replaceWorkspaceViewStateName(name, updatedName);
    state.workspaceViews = listValue(response?.views);
    state.workspaceViewSummaries = [];
    state.workspaceViewsLoaded = true;
    state.workspaceViewsRefreshVersion += 1;
    renderWorkspaceViewRail();
    await refreshWorkspaceViews();
    if (appliedBefore) await reloadAppliedWorkspaceViews();
    setServeStatus(t("view_updated", "View updated"));
  } catch (error) {
    buttons.forEach(button => { button.disabled = false; });
    if (status) status.textContent = error.message || String(error);
    setServeStatus(error.message || String(error), true);
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
  const names = selectedWorkspaceViewNames();
  if (!names.length) return;
  const prompt = workspaceViewMessage(
    "view_delete_confirm",
    "Permanently delete {count} selected views?",
    { count: names.length },
  );
  if (typeof window.confirm === "function" && !window.confirm(prompt)) return;
  const appliedChanged = names.some(name => state.workspaceAppliedViewNames.has(name));
  try {
    const response = await serveApi("/api/views/delete", {
      method: "POST",
      body: { names },
    });
    names.forEach(name => {
      state.workspaceViewSelection.delete(name);
      state.workspaceAppliedViewNames.delete(name);
      state.workspaceViewTableOpen.delete(name);
    });
    state.workspaceViews = listValue(response?.views);
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

function selectedWorkspaceViewNames() {
  return workspaceViews()
    .filter(view => state.workspaceViewSelection.has(view.name))
    .map(view => view.name);
}

function exportSelectedWorkspaceViews() {
  const names = selectedWorkspaceViewNames();
  if (!serveMode() || !names.length) return;
  return serveDownload("summary_xlsx", {
    kind: "summary_xlsx",
    summary: { scope: "saved_views", views: names }
  }, "peval-saved-views.xlsx");
}

function appliedWorkspaceViewNames() {
  return workspaceViews()
    .filter(view => state.workspaceAppliedViewNames.has(view.name))
    .map(view => view.name);
}

async function applySelectedWorkspaceViews() {
  const names = selectedWorkspaceViewNames();
  if (!names.length || !serveMode()) return;
  closeOpenSubmenus();
  state.rowSelection.clear();
  state.sourceSelection.clear();
  state.selectedSourceKey = null;
  state.selectedArtifactRevision = null;
  state.selectedTrial = null;
  state.selectedStep = null;
  state.workspaceAppliedViewNames = new Set(names);
  state.search.query = "";
  state.search.scope = "all";
  state.search.normalSourceMode = "all";
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
    state: "all",
    page: 1,
    page_size: 100,
    search: "",
    sort: "last_turn_end",
    direction: "desc",
    tags: [],
    agents: [],
    models: [],
    results: [],
    views: names,
  }, { force: true });
}

async function reloadAppliedWorkspaceViews() {
  const names = appliedWorkspaceViewNames();
  state.catalogQuery.views = names;
  if (!names.length) return;
  await loadCatalogPage({ page: 1, views: names }, { force: true });
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
    views: [],
  }, { force: true });
}

async function applyWorkspaceView(name) {
  const view = workspaceViewForName(name);
  if (!view) return;
  state.workspaceViewSelection = new Set([view.name]);
  return applySelectedWorkspaceViews();
}

async function cancelWorkspaceViewApplication() {
  return clearWorkspaceViewConditions();
}
