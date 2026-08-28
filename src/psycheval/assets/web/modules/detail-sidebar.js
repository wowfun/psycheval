import { $, RENDER_OPTIONS, esc, listValue, renderComparisonPanels, state, t } from "./runtime.js";
import { stepTimingStats } from "./analysis-metrics.js";
import { bindStepToggle, renderStep, renderStepsHeader } from "./steps.js";
import { closeWorkspaceReportReader } from "./workspace-reports.js";
import { createTaskBrowser } from "./harbor-task-browser.js";
import { serveApi } from "./serve-effects.js";

const DETAIL_SIDEBAR_MIN_WIDTH = 360;
const DETAIL_SIDEBAR_MIN_WORKSPACE_WIDTH = 360;
const DETAIL_SIDEBAR_KEYBOARD_STEP = 24;
const DETAIL_SIDEBAR_STORAGE_VERSION = 1;

function detailSidebarState() {
  if (!state.detailSidebar) {
    state.detailSidebar = { open: false, opener: null, openerSelector: null, preferredWidth: null };
  }
  return state.detailSidebar;
}

function openDetailSidebar(options = {}) {
  const sidebar = detailSidebarState();
  sidebar.open = true;
  sidebar.opener = options.opener || document.activeElement || null;
  sidebar.openerSelector = options.openerSelector || null;
  if (options.trialKey) state.selectedTrial = options.trialKey;
  if (options.stepId !== null && options.stepId !== undefined) {
    state.selectedStep = { trialKey: state.selectedTrial, stepId: String(options.stepId) };
  } else {
    state.selectedStep = null;
  }
}

function closeDetailSidebar(options = {}) {
  const sidebar = detailSidebarState();
  const target = $("detail-sidebar");
  if (!sidebar.open && (!target || target.hidden)) return false;
  const opener = sidebar.opener;
  const openerSelector = sidebar.openerSelector;
  sidebar.open = false;
  sidebar.opener = null;
  sidebar.openerSelector = null;
  state.selectedStep = null;
  sidebar.taskBrowser?.clear();
  setDetailSidebarOpen(false);
  if (options.render !== false) renderComparisonPanels();
  if (options.restoreFocus !== false) {
    requestAnimationFrame(() => {
      const current = opener?.isConnected ? opener : openerSelector ? document.querySelector(openerSelector) : null;
      current?.focus?.();
    });
  }
  return true;
}

function renderDetailSidebar() {
  const target = $("detail-sidebar");
  if (!target) return;
  const sidebar = detailSidebarState();
  const metas = listValue(state.view?.trajectory_meta);
  const index = metas.findIndex(meta => meta?.trial_key === state.selectedTrial);
  const trial = index >= 0 ? metas[index] : null;
  const trajectory = index >= 0 ? listValue(state.view?.trajectory)[index] : null;
  if (!sidebar.open || !trial) {
    if (!trial) {
      sidebar.open = false;
      state.selectedStep = null;
    }
    setDetailSidebarOpen(false);
    sidebar.taskBrowser?.clear();
    target.hidden = true;
    target.innerHTML = "";
    return;
  }
  const steps = listValue(trajectory?.steps);
  const selectedStepId = state.selectedStep?.trialKey === trial.trial_key
    ? String(state.selectedStep.stepId)
    : null;
  if (selectedStepId && !steps.some(step => String(step?.step_id) === selectedStepId)) {
    state.selectedStep = null;
  }
  const timingStats = stepTimingStats(trial);
  const task = renderDetailSidebarTask(trial);
  setDetailSidebarOpen(true);
  target.hidden = false;
  target.innerHTML = `
    <div class="detail-sidebar-resize" data-detail-sidebar-resize role="separator" aria-orientation="vertical" tabindex="0" aria-label="${esc(t("detail_sidebar_resize", "Resize detail sidebar"))}"></div>
    <div class="detail-sidebar-panel" role="complementary" aria-labelledby="detail-sidebar-title">
      <div class="detail-sidebar-head">
        <div><p class="eyebrow">${esc(t("selected_trial_details", "Selected trial details"))}</p><h2 id="detail-sidebar-title">${esc(trial.trial_key || "-")}</h2></div>
        <button class="action-button compact" type="button" data-detail-sidebar-close aria-label="${esc(t("close", "Close"))}">${esc(t("close", "Close"))}</button>
      </div>
      <div class="detail-sidebar-body${task ? " has-task" : ""}">
        ${task}
        <section class="detail-sidebar-steps" data-detail-sidebar-steps aria-labelledby="detail-sidebar-steps-title">
          ${renderStepsHeader(trajectory, { headingId: "detail-sidebar-steps-title" })}
          <div class="detail-sidebar-step-list" data-detail-sidebar-step-list>${steps.map(step => renderStep(step, trial, timingStats, { open: String(step?.step_id) === selectedStepId })).join("")}</div>
        </section>
      </div>
    </div>
  `;
  target.querySelector("[data-detail-sidebar-close]")?.addEventListener("click", event => {
    event.stopPropagation();
    closeDetailSidebar();
  });
  bindStepToggle(target, "[data-detail-sidebar-step-list]");
  bindDetailSidebarResize(target);
  bindDetailSidebarTaskBrowser(target, trial);
  focusSelectedStep(target, selectedStepId);
}

function renderDetailSidebarTask(trial) {
  if (trial?.adapter !== "harbor" || !trial?.task_name) return "";
  const metadata = trial.task_metadata && typeof trial.task_metadata === "object" ? trial.task_metadata : {};
  if (metadata.status === "not_configured") return "";
  return `<section class="detail-sidebar-task" data-detail-sidebar-task aria-labelledby="detail-sidebar-task-title">
    <div class="detail-sidebar-section-head"><div><p class="eyebrow">${esc(t("task", "Task"))}</p><h3 id="detail-sidebar-task-title">${esc(metadata.name || trial.task_name)}</h3></div><span class="chip">${esc(metadata.status || "-")}</span></div>
    <div class="harbor-task-browser detail-sidebar-task-browser" data-detail-sidebar-task-browser>
      <section class="harbor-files-pane" aria-label="${esc(t("harbor_files", "Files"))}">
        <div class="harbor-file-tree" data-harbor-file-tree></div>
      </section>
      <section class="harbor-editor-pane" aria-label="${esc(t("harbor_editor", "Preview"))}">
        <header class="harbor-editor-head"><div><strong data-harbor-editor-path>${esc(t("harbor_editor_empty", "Select a text file"))}</strong><span data-harbor-editor-meta></span></div></header>
        <textarea class="harbor-editor" data-harbor-editor spellcheck="false" readonly disabled></textarea>
      </section>
    </div>
  </section>`;
}

function bindDetailSidebarTaskBrowser(target, trial) {
  const root = target.querySelector("[data-detail-sidebar-task-browser]");
  const sidebar = detailSidebarState();
  if (!root) {
    sidebar.taskBrowser?.clear();
    return;
  }
  if (!sidebar.taskBrowser) {
    sidebar.taskBrowser = createTaskBrowser({
      root,
      editable: false,
      loadTask: taskRef => serveApi(`/api/harbor/datasets/${encodeURIComponent(taskRef.dataset_id)}/tasks/${encodeURIComponent(taskRef.task)}`),
      readFile: (taskRef, path) => serveApi(`/api/harbor/datasets/${encodeURIComponent(taskRef.dataset_id)}/tasks/${encodeURIComponent(taskRef.task)}/files/${encodeURIComponent(path)}`),
    });
  } else sidebar.taskBrowser.attach(root);
  const metadata = trial.task_metadata && typeof trial.task_metadata === "object" ? trial.task_metadata : {};
  const taskRef = metadata.task_ref && typeof metadata.task_ref === "object" ? metadata.task_ref : null;
  const stepName = String(trial?.harbor_step?.name || "").trim();
  const preferredPath = stepName ? `steps/${stepName}/instruction.md` : null;
  if (!taskRef) {
    sidebar.taskBrowser.clear(t("task_files_unavailable", "Task files unavailable"));
    return;
  }
  void sidebar.taskBrowser.loadTask(taskRef, {
    preferredPath,
    strictPreferred: Boolean(stepName),
    contextKey: `${trial.trial_key || ""}\u0000${taskRef.dataset_id || ""}\u0000${taskRef.task || ""}\u0000${preferredPath || ""}`,
  });
}

function focusSelectedStep(target, stepId) {
  if (!stepId) return;
  requestAnimationFrame(() => {
    const row = Array.from(target.querySelectorAll("[data-detail-sidebar-step-list] .step"))
      .find(item => String(item.dataset.step) === String(stepId));
    row?.scrollIntoView?.({ block: "nearest" });
    row?.querySelector("summary")?.focus?.({ preventScroll: true });
  });
}

function setDetailSidebarOpen(open) {
  if (open) closeWorkspaceReportReader({ restoreFocus: false });
  document.body.classList.toggle("detail-sidebar-open", Boolean(open));
}

function bindDetailSidebarResize(target = $("detail-sidebar")) {
  const handle = target?.querySelector?.("[data-detail-sidebar-resize]");
  if (!handle) return;
  restoreDetailSidebarWidth();
  applyDetailSidebarWidth(target);
  handle.addEventListener("pointerdown", event => {
    if (event.button !== undefined && event.button !== 0) return;
    event.preventDefault();
    const pointerId = event.pointerId;
    document.body.classList.add("detail-sidebar-resizing");
    handle.setPointerCapture?.(pointerId);
    const resize = moveEvent => {
      if (pointerId !== undefined && moveEvent.pointerId !== undefined && moveEvent.pointerId !== pointerId) return;
      setDetailSidebarWidth(detailSidebarViewportWidth() - Number(moveEvent.clientX || 0), target);
    };
    const finish = finishEvent => {
      if (pointerId !== undefined && finishEvent.pointerId !== undefined && finishEvent.pointerId !== pointerId) return;
      document.body.classList.remove("detail-sidebar-resizing");
      handle.releasePointerCapture?.(pointerId);
      document.removeEventListener("pointermove", resize);
      document.removeEventListener("pointerup", finish);
      document.removeEventListener("pointercancel", finish);
    };
    document.addEventListener("pointermove", resize);
    document.addEventListener("pointerup", finish);
    document.addEventListener("pointercancel", finish);
  });
  handle.addEventListener("keydown", event => {
    const direction = event.key === "ArrowLeft" ? 1 : event.key === "ArrowRight" ? -1 : 0;
    if (!direction) return;
    event.preventDefault();
    const amount = event.shiftKey ? DETAIL_SIDEBAR_KEYBOARD_STEP * 3 : DETAIL_SIDEBAR_KEYBOARD_STEP;
    setDetailSidebarWidth(currentDetailSidebarWidth(target) + direction * amount, target);
  });
  if (!state.detailSidebar.resizeBound) {
    window.addEventListener("resize", () => applyDetailSidebarWidth($("detail-sidebar")));
    state.detailSidebar.resizeBound = true;
  }
}

function detailSidebarStorageKey(workspaceId = null) {
  return `peval.detail-sidebar-width.v${DETAIL_SIDEBAR_STORAGE_VERSION}.${String(workspaceId || "default")}`;
}

function restoreDetailSidebarWidth() {
  if (state.detailSidebar.preferredWidth !== null) return;
  try {
    const value = Number(window.localStorage?.getItem(detailSidebarStorageKey(stateWorkspaceId())));
    if (Number.isFinite(value) && value > 0) state.detailSidebar.preferredWidth = value;
  } catch {
    // Browser storage is optional presentation state.
  }
}

function saveDetailSidebarWidth(width) {
  try {
    window.localStorage?.setItem(detailSidebarStorageKey(stateWorkspaceId()), String(Math.round(width)));
  } catch {
    // Browser storage is optional presentation state.
  }
}

function stateWorkspaceId() {
  return RENDER_OPTIONS?.workspace_id || "default";
}

function detailSidebarViewportWidth() {
  const documentWidth = Number(document.documentElement?.clientWidth || 0);
  const windowWidth = Number(window.innerWidth || 0);
  return documentWidth || windowWidth || 1180;
}

function detailSidebarMaximumWidth() {
  return Math.max(DETAIL_SIDEBAR_MIN_WIDTH, detailSidebarViewportWidth() - DETAIL_SIDEBAR_MIN_WORKSPACE_WIDTH);
}

function defaultDetailSidebarWidth() {
  const preferred = detailSidebarViewportWidth() * 0.44;
  return Math.min(760, Math.max(620, preferred));
}

function currentDetailSidebarWidth(target = $("detail-sidebar")) {
  const preferred = Number(state.detailSidebar.preferredWidth);
  if (Number.isFinite(preferred) && preferred > 0) {
    return clampDetailSidebarWidth(preferred);
  }
  const measured = Number(target?.getBoundingClientRect?.().width || 0);
  if (Number.isFinite(measured) && measured > 0) return clampDetailSidebarWidth(measured);
  return clampDetailSidebarWidth(defaultDetailSidebarWidth());
}

function clampDetailSidebarWidth(width) {
  const numeric = Number(width);
  const fallback = defaultDetailSidebarWidth();
  return Math.round(Math.min(detailSidebarMaximumWidth(), Math.max(DETAIL_SIDEBAR_MIN_WIDTH, Number.isFinite(numeric) ? numeric : fallback)));
}

function setDetailSidebarWidth(width, target = $("detail-sidebar")) {
  const next = clampDetailSidebarWidth(width);
  state.detailSidebar.preferredWidth = next;
  saveDetailSidebarWidth(next);
  applyDetailSidebarWidth(target, next);
  return next;
}

function applyDetailSidebarWidth(target = $("detail-sidebar"), width = currentDetailSidebarWidth(target)) {
  const effective = clampDetailSidebarWidth(width);
  document.documentElement?.style?.setProperty("--detail-sidebar-width", `${effective}px`);
  const handle = target?.querySelector?.("[data-detail-sidebar-resize]");
  if (handle) {
    handle.setAttribute("aria-valuemin", String(DETAIL_SIDEBAR_MIN_WIDTH));
    handle.setAttribute("aria-valuemax", String(detailSidebarMaximumWidth()));
    handle.setAttribute("aria-valuenow", String(effective));
  }
  state.timelineChart?.resize?.();
  return effective;
}

export {
  DETAIL_SIDEBAR_KEYBOARD_STEP,
  DETAIL_SIDEBAR_MIN_WIDTH,
  DETAIL_SIDEBAR_MIN_WORKSPACE_WIDTH,
  applyDetailSidebarWidth,
  bindDetailSidebarResize,
  currentDetailSidebarWidth,
  detailSidebarStorageKey,
  closeDetailSidebar,
  detailSidebarState,
  openDetailSidebar,
  renderDetailSidebar,
  renderDetailSidebarTask,
  setDetailSidebarWidth,
  setDetailSidebarOpen,
};
