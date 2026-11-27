import { esc, t } from "./shared.js";
import { columnVisibleForLayout, moveColumn, normalizeColumnLayout, saveColumnLayout } from "./table-columns.js";

function createColumnControl({ id, state, context, onRender, conditionText = () => "", searchText = column => `${column.label} ${column.key}`.toLocaleLowerCase(), options = {}, headerAction = null, rowActions = null }) {
  function render(rows) {
    const { columns, layout, presence } = context(rows);
    const draft = state.draft
      ? normalizeColumnLayout(columns.map(column => column.key), state.draft, options)
      : layout;
    const ordered = draft.order.map(key => columns.find(column => column.key === key) || { key, label: key, defaultVisible: false, unavailable: true });
    const checked = column => columnVisibleForLayout(column, draft, presence);
    const visibleCount = ordered.filter(checked).length;
    const rowsHtml = ordered.map((column, index) => {
      const isChecked = checked(column);
      const condition = conditionText(column);
      const actions = typeof rowActions === "function" ? (rowActions(column) || []) : [];
      const actionsHtml = actions.length
        ? `<div class="column-control-row-actions">${actions.map(action => `<button type="button" class="${action.danger ? "danger" : ""}" data-column-action="${esc(action.key)}" data-column-action-target="${esc(column.key)}" ${action.disabled ? "disabled" : ""} title="${esc(action.title || action.label)}">${esc(action.label)}</button>`).join("")}</div>`
        : "";
      return `<li class="column-control-row${isChecked ? "" : " hidden-column"}" data-column-row="${esc(column.key)}" data-column-match="${esc(searchText(column))}" ${searchText(column).includes((state.search || "").toLocaleLowerCase()) ? "" : "hidden"}>
        <span class="column-control-index">${String(index + 1).padStart(2, "0")}</span>
        <label><input type="checkbox" data-column-visible="${esc(column.key)}" ${column.description ? `aria-describedby="${id}-column-hint-${index}"` : ""} ${isChecked ? "checked" : ""}><span>${esc(column.label)}</span></label>
        <span class="column-control-state">${column.unavailable ? esc(t("metric_unavailable", "Currently unavailable")) : presence[column.key] ? "" : esc(t("no_data", "No data"))}${condition ? `<small>${esc(condition)}</small>` : ""}</span>
        <span class="column-control-moves"><button type="button" data-column-move="${esc(column.key)}" data-column-direction="-1" aria-label="${esc(`${t("move_earlier", "Move earlier")}: ${column.label}`)}" ${index === 0 ? "disabled" : ""}>↑</button><button type="button" data-column-move="${esc(column.key)}" data-column-direction="1" aria-label="${esc(`${t("move_later", "Move later")}: ${column.label}`)}" ${index === ordered.length - 1 ? "disabled" : ""}>↓</button></span>
        ${column.description ? `<small class="column-description" id="${id}-column-hint-${index}">${esc(column.description)}</small>` : ""}
        ${actionsHtml}
      </li>`;
    }).join("");
    const headerButtons = headerAction
      ? `<div class="column-control-head-actions"><button type="button" data-column-header-action ${headerAction.disabled ? "disabled" : ""}>${esc(headerAction.label)}</button><button type="button" data-column-reset>${esc(t("reset_auto", "Reset to auto"))}</button></div>`
      : `<button type="button" data-column-reset>${esc(t("reset_auto", "Reset to auto"))}</button>`;
    return `<details class="column-control" ${state.draft ? "open" : ""}>
      <summary class="action-button column-control-button">${esc(t("columns", "Columns"))} ${visibleCount}/${ordered.length}</summary>
      <div class="column-control-panel">
        <div class="column-control-head"><strong>${esc(t("columns", "Columns"))}</strong>${headerButtons}</div>
        <label>${esc(t("search", "Search"))}<input type="search" data-column-search value="${esc(state.search || "")}"></label>
        <ol class="column-control-list">${rowsHtml}</ol>
        <div class="column-control-foot"><span aria-live="polite">${esc(`${visibleCount} / ${ordered.length}`)}</span><button type="button" class="action-button primary" data-column-apply>${esc(t("apply", "Apply"))}</button></div>
      </div>
    </details>`;
  }
  function restoreFocus(findControl) {
    const root = onRender();
    let control = findControl(root);
    if (control?.disabled) {
      const row = control.closest("[data-column-row]");
      row?.setAttribute("tabindex", "-1");
      control = row;
    }
    control?.focus();
  }
  function bind(target) {
    const details = target?.querySelector?.(".column-control");
    if (!details) return;
    details.querySelector("[data-column-search]").addEventListener("input", event => {
      state.search = event.target.value;
      details.querySelectorAll("[data-column-match]").forEach(row => { row.hidden = !row.dataset.columnMatch.includes(event.target.value.toLocaleLowerCase()); });
    });
    details.addEventListener("toggle", () => {
      if (!details.isConnected) return;
      if (details.open && !state.draft) {
        state.draft = structuredClone(context().layout);
      } else if (!details.open) {
        const hadDraft = Boolean(state.draft);
        state.draft = null;
        if (hadDraft) onRender();
      }
    });
    details.addEventListener("keydown", event => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      state.draft = null;
      details.open = false;
      restoreFocus(root => root?.querySelector?.(".column-control > summary"));
    });
    details.querySelectorAll("[data-column-visible]").forEach(input => {
      input.addEventListener("change", () => {
        const columnKey = input.dataset.columnVisible;
        const draft = state.draft || structuredClone(context().layout);
        draft.visibility[columnKey] = input.checked ? "show" : "hide";
        state.draft = draft;
        restoreFocus(root => Array.from(
          root?.querySelectorAll?.("[data-column-visible]") || []
        ).find(control => control.dataset.columnVisible === columnKey));
      });
    });
    details.querySelectorAll("[data-column-move]").forEach(button => {
      button.addEventListener("click", () => {
        const columnKey = button.dataset.columnMove;
        const direction = button.dataset.columnDirection;
        const draft = state.draft || structuredClone(context().layout);
        draft.order = moveColumn(draft.order, columnKey, Number(direction));
        state.draft = draft;
        restoreFocus(root => Array.from(
          root?.querySelectorAll?.("[data-column-move]") || []
        ).find(control => control.dataset.columnMove === columnKey && control.dataset.columnDirection === direction));
      });
    });
    details.querySelector("[data-column-reset]")?.addEventListener("click", () => {
      state.draft = normalizeColumnLayout(context().columns.map(column => column.key), null, options);
      restoreFocus(root => root?.querySelector?.("[data-column-reset]"));
    });
    if (headerAction?.onClick) {
      details.querySelector("[data-column-header-action]")?.addEventListener("click", event => {
        event.stopPropagation();
        state.draft = null;
        details.open = false;
        headerAction.onClick(details.querySelector("summary"));
      });
    }
    if (typeof rowActions === "function") {
      details.querySelectorAll("[data-column-action]").forEach(button => {
        button.addEventListener("click", event => {
          event.stopPropagation();
          const targetKey = button.dataset.columnActionTarget;
          const actionKey = button.dataset.columnAction;
          const column = context().columns.find(item => item.key === targetKey);
          const action = column ? (rowActions(column) || []).find(item => item.key === actionKey) : null;
          if (!action?.onClick) return;
          state.draft = null;
          details.open = false;
          action.onClick(column, details.querySelector("summary"));
        });
      });
    }
    details.querySelector("[data-column-apply]")?.addEventListener("click", () => {
      state.layout = normalizeColumnLayout(context().columns.map(column => column.key), state.draft, options);
      saveColumnLayout(state.layout, options);
      state.draft = null;
      restoreFocus(root => root?.querySelector?.(".column-control > summary"));
    });
  }

  return { render, bind };
}
export { createColumnControl };
