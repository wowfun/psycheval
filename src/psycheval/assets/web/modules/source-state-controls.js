import { adminMode, currentServeSourceMode, esc, listValue, normalizeServeSourceMode, readableServeSourcesFrom, t } from "./runtime.js";
import { serveApi, setServeStatus } from "./serve-effects.js";
import { applyServeSourceStateMutationPayload, leaderboardRows, switchServeSourceMode, visibleSelectedSourceKeys } from "./serve-catalog.js";

function renderServeSourceStateControls(rows = leaderboardRows()) {
  const mode = currentServeSourceMode();
  const allMode = mode === "all";
  const archived = mode === "archived";
  const toggleDisabled = allMode ? "disabled" : "";
  const selectedCount = visibleSelectedSourceKeys(rows).length;
  const actionLabel = archived
    ? t("activate_selected", "Activate selected")
    : t("archive_selected", "Archive selected");
  const action = adminMode()
    ? `<button class="action-button primary" type="button" data-source-state-action ${selectedCount && !allMode ? "" : "disabled"}>${esc(allMode ? t("mixed_state_action_disabled", "Mixed view") : actionLabel)}</button>`
    : "";
  const selected = new Set(visibleSelectedSourceKeys(rows));
  const includesLinkedHarbor = rows.some(row => selected.has(row?.source_key || row?.trial_key) && row?.kind === "harbor-trial");
  const deleteAction = adminMode()
    ? `<button class="action-button danger" type="button" data-source-delete-action ${selectedCount && !includesLinkedHarbor ? "" : "disabled"} ${includesLinkedHarbor ? `title="${esc(t("serve_linked_harbor_delete_disabled", "Linked Harbor Trials cannot be deleted; archive them instead."))}"` : ""}>${esc(t("delete_selected", "Delete selected"))}</button>`
    : "";
  return `<div class="source-state-controls" data-source-state-controls>
    <label class="source-state-toggle">
      <input type="checkbox" data-source-state-toggle ${archived || allMode ? "checked" : ""} ${toggleDisabled}>
      <span>${esc(t("show_archived", "Show archived"))}</span>
    </label>
    ${action}${deleteAction}
  </div>`;
}

function bindServeSourceStateControls(target) {
  if (!target) return;
  target.querySelectorAll("[data-source-state-toggle]").forEach(input => {
    input.addEventListener("click", event => event.stopPropagation());
    input.addEventListener("change", event => {
      event.stopPropagation();
      switchServeSourceMode(input.checked ? "archived" : "active");
    });
  });
  target.querySelectorAll("[data-source-state-action]").forEach(button => {
    button.addEventListener("click", event => {
      event.stopPropagation();
      mutateVisibleServeSourceState();
    });
  });
  target.querySelectorAll("[data-source-delete-action]").forEach(button => {
    button.addEventListener("click", event => {
      event.stopPropagation();
      deleteVisibleServeSources();
    });
  });
}

async function mutateVisibleServeSourceState() {
  if (!adminMode()) return;
  const sourceKeys = visibleSelectedSourceKeys();
  if (!sourceKeys.length) return;
  const mode = currentServeSourceMode();
  if (mode === "all") {
    setServeStatus(t("mixed_state_action_disabled", "Mixed view"), true);
    return;
  }
  const targetMode = mode === "archived" ? "active" : "archived";
  try {
    const payload = await serveApi("/api/sources/state", {
      method: "POST",
      body: {
        source_keys: sourceKeys,
        active: targetMode === "active",
        report_source_state: mode
      }
    });
    await applyServeSourceStateMutationPayload(payload, { sourceKeys, targetMode });
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  }
}
async function deleteVisibleServeSources() {
  if (!adminMode()) return;
  const sourceKeys = visibleSelectedSourceKeys();
  if (!sourceKeys.length) return;
  if (!window.confirm(t("serve_delete_selected_confirm", "Permanently delete the selected sources? This cannot be undone."))) return;
  try {
    const payload = await serveApi("/api/sources/delete", {
      method: "POST",
      body: { source_keys: sourceKeys },
    });
    await applyServeSourceStateMutationPayload(payload, { sourceKeys, targetMode: currentServeSourceMode() });
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  }
}

function firstReadableSourceKeyFrom(sourceKeys, sources, mode) {
  const requested = new Set(listValue(sourceKeys).map(key => String(key || "")).filter(Boolean));
  return readableServeSourcesFrom(sources, mode).find(source => requested.has(source.source_key))?.source_key || null;
}

function serveSourceModeStatusText(mode = currentServeSourceMode()) {
  if (normalizeServeSourceMode(mode) === "all") {
    return t("serve_all_sessions", "All sessions");
  }
  return normalizeServeSourceMode(mode) === "archived"
    ? t("serve_archived_snapshots", "Archived snapshots")
    : t("serve_active_snapshots", "Active snapshots");
}
export {
  bindServeSourceStateControls,
  firstReadableSourceKeyFrom,
  deleteVisibleServeSources,
  mutateVisibleServeSourceState,
  renderServeSourceStateControls,
  serveSourceModeStatusText,
};
