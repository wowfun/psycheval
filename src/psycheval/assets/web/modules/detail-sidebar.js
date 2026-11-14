import { $, RENDER_OPTIONS, esc, homeDetail, listValue, renderComparisonPanels, state, t } from "./runtime.js";
import { stepTimingStats } from "./analysis-metrics.js";
import { renderIncompleteTrajectory, renderSelectedWarnings, renderTrialInfo } from "./analysis-selected.js";
import { bindBlockCopyControls, bindStepToggle, renderStep, renderStepsHeader } from "./steps.js";
import { cancelTrialDetailRequest, sourceKeyForTrialKey } from "./serve-catalog.js";
import { createVerificationBrowser } from "./verification-browser.js";
import { renderVerificationSummary } from "./verification-formats.js";
import { createTaskBrowser } from "./harbor-task-browser.js";
import { serveApi } from "./serve-effects.js";
import { createSidebarController } from "./sidebar.js";
import { selectedTrajectoryDetail, renderTrajectoryNavigation, bindTrajectoryNavigation } from "./trajectory-family.js";
import { bindServeSourceStateControls } from "./source-state-controls.js";
import { createRecentState } from "./recent-state.js";

let detailSidebarController = null;
let timingRequest = 0;
let timingPanel = null;
let renderedDetail = null;
const timingDisclosures = createRecentState();

function disposeTimingPanel() {
  timingRequest += 1;
  timingPanel?.dispose();
  timingPanel = null;
}
function loadTimingPanel(target, trajectory, trial, rootMeta, depth) {
  if (timingPanel) return;
  const request = ++timingRequest;
  target.innerHTML = `<p class="copy">${esc(t("loading", "Loading…"))}</p>`;
  void import("./timeline-shell.js").then(({ mountTimingPanel, timingIdentity }) => {
    if (request !== timingRequest || !target.isConnected || !state.detailSidebar.open || state.detailSidebar.tab !== "timing") return;
    const { key } = timingIdentity(trajectory, trial);
    timingPanel = mountTimingPanel(target, trajectory, trial, { rootMeta: depth ? null : rootMeta, isRoot: !depth, disclosure: timingDisclosures.get(key) });
  }).catch(error => {
    if (request !== timingRequest || !target.isConnected) return;
    target.innerHTML = `<p class="copy danger" role="alert">${esc(error.message || String(error))}</p>`;
  });
}

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
        locationKind: options.reason === "dismiss" ? "object" : "replace",
      }),
    });
  }
  homeDetail.register("source", { cancel: cancelTrialDetailRequest, close: closeDetailSidebar });
  return detailSidebarController;
}

function requestDetailSidebarLocation(target) {
  detailSidebarSurface();
  homeDetail.activate(target);
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
  sidebar.tab = options.tab || (options.stepId !== null && options.stepId !== undefined ? "trajectory" : "verification");
  sidebar.open = true;
  sidebar.pendingOpener = options.opener || document.activeElement || null;
  sidebar.pendingOpenerSelector = options.openerSelector || null;
  if (options.trialKey) state.selectedTrial = options.trialKey;
  if (options.stepId !== null && options.stepId !== undefined) {
    state.selectedStep = { trialKey: state.selectedTrial, stepId: String(options.stepId) };
  } else {
    state.selectedStep = null;
  }
  const source = sourceKeyForTrialKey(state.selectedTrial);
  if (source) {
    requestDetailSidebarLocation({
      source,
      ...(state.selectedTrajectory?.trajectoryId ? { trajectory: state.selectedTrajectory.trajectoryId } : {}),
      ...(state.selectedStep?.stepId ? { step: state.selectedStep.stepId } : {}),
      tab: options.tab || sidebar.tab,
    });
  }
}

function closeDetailSidebar(options = {}) {
  const sidebar = detailSidebarState();
  const target = $("detail-sidebar");
  const surface = detailSidebarSurface();
  if (!sidebar.open && (!target || target.hidden)) return false;
  cancelTrialDetailRequest();
  disposeTimingPanel();
  sidebar.open = false;
  sidebar.pendingOpener = null;
  sidebar.pendingOpenerSelector = null;
  state.selectedStep = null;
  homeDetail.clear("source", options.locationKind || "object");
  sidebar.taskBrowser?.clear();
  sidebar.verificationBrowser?.clear();
  surface.close({ restoreFocus: options.restoreFocus });
  if (options.render !== false) renderComparisonPanels();
  return true;
}

function detailRenderState() {
  return [state.view, state.selectedSourceKey, state.selectedTrial, state.selectedTrajectory?.trialKey,
    state.selectedTrajectory?.trajectoryId, state.selectedStep?.trialKey, state.selectedStep?.stepId,
    state.detailSidebar, state.detailSidebar?.open, state.detailSidebar?.tab, state.catalogQuery.metric_scope];
}

function renderDetailSidebar({ ifChanged = false } = {}) {
  const target = $("detail-sidebar");
  const current = detailRenderState();
  if (ifChanged && renderedDetail && target?.firstElementChild === renderedDetail.node
    && current.every((value, index) => value === renderedDetail.state[index])
    && !state.detailSidebar?.pendingOpener && !state.detailSidebar?.pendingOpenerSelector) return;
  renderedDetail = null;
  disposeTimingPanel();
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
  const hasVerification = rootMeta.adapter === "harbor";
  const tabs = [];
  if (hasVerification) tabs.push(["verification", t("verification", "Verification")]);
  if (task) tabs.push(["task", t("task", "Task")]);
  tabs.push(["trajectory", t("trajectory", "Trajectory")], ["info", t("trial_info", "Info")], ["timing", t("trial_timing", "Timing")]);
  const tabChanged = !tabs.some(([id]) => id === sidebar.tab);
  if (tabChanged) sidebar.tab = tabs[0][0];
  if (!task) sidebar.taskBrowser?.clear();
  if (!hasVerification) sidebar.verificationBrowser?.clear();
  target.innerHTML = `
    <div class="detail-sidebar-panel" role="complementary" aria-labelledby="detail-sidebar-title">
      <div class="detail-sidebar-head">
        <div><p class="eyebrow">${esc(t("selected_trial_details", "Selected trial details"))}</p><h2 id="detail-sidebar-title">${esc(rootMeta.trial_key || "-")}</h2></div>
        <div class="detail-sidebar-actions">

          <button class="action-button compact" type="button" data-sidebar-close aria-label="${esc(t("close", "Close"))}">${esc(t("close", "Close"))}</button>
        </div>
        ${renderVerificationSummary(rootMeta)}
      </div>
      <div class="detail-sidebar-tabs" role="tablist" aria-label="${esc(t("selected_trial_details", "Trial details"))}">
        ${tabs.map(([id, text]) => `<button type="button" role="tab" id="trial-tab-${id}" aria-controls="trial-panel-${id}" aria-selected="${sidebar.tab === id}" tabindex="${sidebar.tab === id ? 0 : -1}" data-trial-tab="${id}">${esc(text)}</button>`).join("")}
      </div>
      <div class="detail-sidebar-navigation" data-trial-navigation>${renderTrajectoryNavigation(root, rootMeta)}</div>
      <div class="detail-sidebar-body">
        ${hasVerification ? `<section id="trial-panel-verification" role="tabpanel" aria-labelledby="trial-tab-verification" data-trial-panel="verification" ${sidebar.tab !== "verification" ? "hidden" : ""}>
          <div data-verification-browser></div>
        </section>` : ""}
        ${task ? `<section id="trial-panel-task" role="tabpanel" aria-labelledby="trial-tab-task" data-trial-panel="task" ${sidebar.tab !== "task" ? "hidden" : ""}>${task}</section>` : ""}
        <section id="trial-panel-trajectory" role="tabpanel" aria-labelledby="trial-tab-trajectory" data-trial-panel="trajectory" class="detail-sidebar-steps" data-detail-sidebar-steps ${sidebar.tab !== "trajectory" ? "hidden" : ""}>
          ${trial.detail_unavailable ? `<p class="copy">${esc(t("verification_trajectory_unavailable", "Trajectory unavailable; retained verification files remain accessible."))}</p>` : renderStepsHeader(trajectory, { headingId: "detail-sidebar-steps-title" })}
          <div class="detail-sidebar-step-list" data-detail-sidebar-step-list>${renderIncompleteTrajectory(trajectory)}${renderSelectedWarnings(trial)}${steps.map(step => renderStep(step, trial, timingStats, { open: String(step?.step_id) === selectedStepId, childIds })).join("")}</div>
        </section>
        <section id="trial-panel-info" role="tabpanel" aria-labelledby="trial-tab-info" data-trial-panel="info" class="trial-info" hidden>${renderTrialInfo(trajectory, rootMeta, detail.depth, trial)}</section>
        <section id="trial-panel-timing" role="tabpanel" aria-labelledby="trial-tab-timing" data-trial-panel="timing" hidden></section>
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
  bindServeSourceStateControls(target);
  bindTrajectoryNavigation(target, root, rootMeta);
  if (hasVerification) {
    if (!sidebar.verificationBrowser) sidebar.verificationBrowser = createVerificationBrowser();
    const sourceKey = sourceKeyForTrialKey(rootMeta.trial_key) || rootMeta.verifier_evidence?.source_key;
    sidebar.verificationBrowser.setSource(sourceKey, rootMeta.verifier_evidence?.revision || rootMeta.evidence_revision || state.catalogPage?.generation);
    sidebar.verificationBrowser.attach(target.querySelector("[data-verification-browser]"));
  }
  target.querySelectorAll("[data-detail-sidebar-step-list] .step > summary").forEach(summary => {
    summary.addEventListener("click", event => {
      if (event.target.closest("button,a,input,select")) return;
      const row = summary.parentElement;
      state.selectedStep = row.open ? null : { trialKey: state.selectedTrial, stepId: String(row.dataset.step) };
      homeDetail.position({ step: state.selectedStep?.stepId });
    });
  });
  const activate = (id, notify = true) => {
    if (id !== "timing") disposeTimingPanel();
    sidebar.tab = id;
    target.querySelectorAll("[data-trial-tab]").forEach(button => {
      button.setAttribute("aria-selected", String(button.dataset.trialTab === id));
      button.tabIndex = button.dataset.trialTab === id ? 0 : -1;
    });
    target.querySelectorAll("[data-trial-panel]").forEach(panel => { panel.hidden = panel.dataset.trialPanel !== id; });
    const tablist = target.querySelector("[role=tablist]");
    const activeTab = target.querySelector('[role=tab][aria-selected=true]');
    const visible = tablist.getBoundingClientRect(), active = activeTab.getBoundingClientRect();
    if (active.right > visible.right) tablist.scrollLeft += active.right - visible.right;
    else if (active.left < visible.left) tablist.scrollLeft -= visible.left - active.left;
    target.querySelector("[data-trial-navigation]").hidden = !["trajectory", "info", "timing"].includes(id) || !target.querySelector(".trajectory-navigation");
    if (id === "timing") loadTimingPanel(target.querySelector("[data-trial-panel=timing]"), trajectory, trial, rootMeta, detail.depth);
    if (id === "verification") void sidebar.verificationBrowser.load(rootMeta);
    if (id === "task") bindDetailSidebarTaskBrowser(target, rootMeta);
    if (id === "trajectory") focusSelectedStep(target, selectedStepId);
    if (notify) homeDetail.position({ tab: id });
    renderedDetail = { node: target.firstElementChild, state: detailRenderState() };
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
  activate(sidebar.tab, tabChanged);
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
  requestDetailSidebarLocation,
  closeDetailSidebar,
  detailSidebarState,
  openDetailSidebar,
  renderDetailSidebar,
  renderDetailSidebarTask,
};
