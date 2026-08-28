// @ts-check

import { beginNotesEdit, cancelNotesEdit, saveSelectedNotes } from "./analysis-notes.js";
import { closeDetailSidebar } from "./detail-sidebar.js";
import { refreshServeReportFromServer, refreshServeSourcesFromServer } from "./serve-catalog.js";
import { SUBMENU_DETAILS_SELECTOR, closeOpenSubmenus, selectedKey, state } from "./runtime.js";
import { closeWorkspaceReportReader } from "./workspace-reports.js";
import { bindWorkspaceViewDialog, closeWorkspaceViewSaveDialog } from "./workspace-views.js";

let bound = false;

function bindHomeControls() {
  if (bound) return;
  bound = true;
  document.addEventListener("keydown", event => {
    if (event.defaultPrevented || event.key !== "Escape") return;
    if (closeWorkspaceViewSaveDialog()) return;
    if (closeWorkspaceReportReader()) return;
    closeDetailSidebar();
  });
  document.addEventListener("click", event => {
    closeOpenSubmenus(/** @type {Element | null} */ (event.target)?.closest?.(SUBMENU_DETAILS_SELECTOR) || null);
  }, true);
  document.addEventListener("click", event => {
    const target = /** @type {Element | null} */ (event.target);
    const edit = target?.closest?.("[data-notes-edit]");
    if (edit) {
      event.preventDefault();
      beginNotesEdit(edit.getAttribute("data-trial-key") || selectedKey());
      return;
    }
    const cancel = target?.closest?.("[data-notes-cancel]");
    if (cancel) {
      event.preventDefault();
      cancelNotesEdit();
      return;
    }
    const save = target?.closest?.("[data-notes-save]");
    if (save) {
      event.preventDefault();
      saveSelectedNotes(save);
    }
  });
  window.addEventListener("resize", () => state.timelineChart?.resize?.());
  document.querySelectorAll("[data-refresh-all]").forEach(button => {
    button.addEventListener("click", () => refreshServeReportFromServer());
  });
  document.querySelectorAll("[data-refresh-sources]").forEach(button => {
    button.addEventListener("click", () => refreshServeSourcesFromServer());
  });
  bindWorkspaceViewDialog();
}

export { bindHomeControls };
