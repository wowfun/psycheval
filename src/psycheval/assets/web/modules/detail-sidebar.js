import { $, RENDER_OPTIONS, esc, listValue, renderComparisonPanels, state, t } from "./runtime.js";
import { stepTimingStats } from "./analysis-metrics.js";
import { bindBlockCopyControls, bindStepToggle, renderStep, renderStepsHeader } from "./steps.js";
import { sourceKeyForTrialKey } from "./serve-catalog.js";
import { createVerificationBrowser } from "./verification-browser.js";
import { renderVerificationSummary } from "./verification-formats.js";
import { createTaskBrowser } from "./harbor-task-browser.js";
import { serveApi } from "./serve-effects.js";
import { createSidebarController } from "./sidebar.js";
import { selectedTrajectoryDetail, renderTrajectoryNavigation, bindTrajectoryNavigation } from "./trajectory-family.js";

let detailSidebarController = null;

function detailSidebarSurface() {
  if (!detailSidebarController) {
    detailSidebarController = createSidebarController({
      id: "trial-detail",
      side: "right",
      root: () => $("detail-sidebar"),
      bodyClass: "detail-sidebar-open",
      cssVariable: "--detail-sidebar-width",
      workspaceId: RENDER_OPTIONS?.workspace_id || "default",
      minWidth: 360,
      minWorkspaceWidth: 360,
      defaultWidth: width => Math.min(760, Math.max(620, width * 0.44)),
      resizeLabel: t("detail_sidebar_resize", "Resize detail sidebar"),
      onRequestClose: options => closeDetailSidebar({
        restoreFocus: options.restoreFocus,
        render: options.reason === "dismiss",
      }),
      onResize: () => state.timelineChart?.resize?.(),
    });
  }
  return detailSidebarController;
}

function detailSidebarState() {
  if (!state.detailSidebar) {
    state.detailSidebar = { open: false, pendingOpener: null, pendingOpenerSelector: null };
  }
  state.detailSidebar.tab ||= "verification";
  return state.detailSidebar;
}

function openDetailSidebar(options = {}) {
  const sidebar = detailSidebarState();
  sidebar.open = true;
  sidebar.pendingOpener = options.opener || document.activeElement || null;
  sidebar.pendingOpenerSelector = options.openerSelector || null;
  if (options.trialKey) state.selectedTrial = options.trialKey;
  if (options.stepId !== null && options.stepId !== undefined) {
    sidebar.tab = "trajectory";
    state.selectedStep = { trialKey: state.selectedTrial, stepId: String(options.stepId) };
  } else {
    state.selectedStep = null;
  }
}

function closeDetailSidebar(options = {}) {
  const sidebar = detailSidebarState();
  const target = $("detail-sidebar");
  const surface = detailSidebarSurface();
  if (!sidebar.open && (!target || target.hidden)) return false;
  sidebar.open = false;
  sidebar.pendingOpener = null;
  sidebar.pendingOpenerSelector = null;
  state.selectedStep = null;
  sidebar.taskBrowser?.clear();
  sidebar.verificationBrowser?.clear();
  surface.close({ restoreFocus: options.restoreFocus });
  if (options.render !== false) renderComparisonPanels();
  return true;
}

function renderDetailSidebar() {
  const target = $("detail-sidebar");
  if (!target) return;
  const sidebar = detailSidebarState();
  const metas = listValue(state.view?.trajectory_meta);
  const index = metas.findIndex(meta => meta?.trial_key === state.selectedTrial);
  const rootMeta = index >= 0 ? metas[index] : null;
  const root = index >= 0 ? listValue(state.view?.trajectory)[index] : null;
  const detail = selectedTrajectoryDetail(root, rootMeta);
  const trial = rootMeta ? detail.meta : null;
  const trajectory = detail.trajectory;
  const childIds = new Set((trajectory?.subagent_trajectories || []).map(child => child.trajectory_id));
  if (!sidebar.open || !trial) {
    if (!trial) {
      sidebar.open = false;
      state.selectedStep = null;
    }
    detailSidebarSurface().close({ restoreFocus: false });
    sidebar.taskBrowser?.clear();
    sidebar.verificationBrowser?.clear();
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
  const task = renderDetailSidebarTask(rootMeta);
  const tabs = [["verification", t("verification", "Verification")], ["task", t("task", "Task")], ["trajectory", t("trajectory", "Trajectory")]];
  target.innerHTML = `
    <div class="detail-sidebar-panel" role="complementary" aria-labelledby="detail-sidebar-title">
      <div class="detail-sidebar-head">
        <div><p class="eyebrow">${esc(t("selected_trial_details", "Selected trial details"))}</p><h2 id="detail-sidebar-title">${esc(rootMeta.trial_key || "-")}</h2></div>
        <button class="action-button compact" type="button" data-sidebar-close aria-label="${esc(t("close", "Close"))}">${esc(t("close", "Close"))}</button>
        ${renderVerificationSummary(rootMeta)}
      </div>
      <div class="detail-sidebar-tabs" role="tablist" aria-label="${esc(t("selected_trial_details", "Trial details"))}">
        ${tabs.map(([id, text]) => `<button type="button" role="tab" id="trial-tab-${id}" aria-controls="trial-panel-${id}" aria-selected="${sidebar.tab === id}" tabindex="${sidebar.tab === id ? 0 : -1}" data-trial-tab="${id}">${esc(text)}</button>`).join("")}
      </div>
      <div class="detail-sidebar-body">
        <section id="trial-panel-verification" role="tabpanel" aria-labelledby="trial-tab-verification" data-trial-panel="verification" ${sidebar.tab !== "verification" ? "hidden" : ""}>
          <div data-verification-browser></div>
        </section>
        <section id="trial-panel-task" role="tabpanel" aria-labelledby="trial-tab-task" data-trial-panel="task" ${sidebar.tab !== "task" ? "hidden" : ""}>${task || `<p class="copy">${esc(t("task_files_unavailable", "Task files unavailable"))}</p>`}</section>
        <section id="trial-panel-trajectory" role="tabpanel" aria-labelledby="trial-tab-trajectory" data-trial-panel="trajectory" class="detail-sidebar-steps" data-detail-sidebar-steps ${sidebar.tab !== "trajectory" ? "hidden" : ""}>
          ${renderTrajectoryNavigation(root, rootMeta)}
          ${trial.detail_unavailable ? `<p class="copy">${esc(t("verification_trajectory_unavailable", "Trajectory unavailable; retained verification files remain accessible."))}</p>` : renderStepsHeader(trajectory, { headingId: "detail-sidebar-steps-title" })}
          <div class="detail-sidebar-step-list" data-detail-sidebar-step-list>${steps.map(step => renderStep(step, trial, timingStats, { open: String(step?.step_id) === selectedStepId, childIds })).join("")}</div>
        </section>
      </div>
    </div>
  `;
  detailSidebarSurface().open({
    ...((sidebar.pendingOpener || sidebar.pendingOpenerSelector) ? {
      opener: sidebar.pendingOpener,
      openerSelector: sidebar.pendingOpenerSelector,
    } : {}),
  });
  sidebar.pendingOpener = null;
  sidebar.pendingOpenerSelector = null;
  bindStepToggle(target, "[data-detail-sidebar-step-list]");
  bindBlockCopyControls(target);
  bindTrajectoryNavigation(target, root, rootMeta);
  if (!sidebar.verificationBrowser) sidebar.verificationBrowser = createVerificationBrowser();
  const sourceKey = sourceKeyForTrialKey(rootMeta.trial_key) || rootMeta.verifier_evidence?.source_key;
  sidebar.verificationBrowser.setSource(sourceKey, rootMeta.verifier_evidence?.revision || rootMeta.evidence_revision || state.catalogPage?.generation);
  sidebar.verificationBrowser.attach(target.querySelector("[data-verification-browser]"));
  const activate = id => {
    sidebar.tab = id;
    target.querySelectorAll("[data-trial-tab]").forEach(button => {
      button.setAttribute("aria-selected", String(button.dataset.trialTab === id));
      button.tabIndex = button.dataset.trialTab === id ? 0 : -1;
    });
    target.querySelectorAll("[data-trial-panel]").forEach(panel => { panel.hidden = panel.dataset.trialPanel !== id; });
    if (id === "verification") void sidebar.verificationBrowser.load(rootMeta);
    if (id === "task") bindDetailSidebarTaskBrowser(target, rootMeta);
    if (id === "trajectory") focusSelectedStep(target, selectedStepId);
  };
  const buttons = [...target.querySelectorAll("[data-trial-tab]")];
  buttons.forEach((button, index) => {
    button.addEventListener("click", () => activate(button.dataset.trialTab));
    button.addEventListener("keydown", event => {
      const next = event.key === "ArrowRight" ? (index + 1) % buttons.length : event.key === "ArrowLeft" ? (index + buttons.length - 1) % buttons.length : event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1 : null;
      if (next === null) return;
      event.preventDefault(); buttons[next].focus(); activate(buttons[next].dataset.trialTab);
    });
  });
  activate(sidebar.tab);
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

export {
  closeDetailSidebar,
  detailSidebarState,
  openDetailSidebar,
  renderDetailSidebar,
  renderDetailSidebarTask,
};
