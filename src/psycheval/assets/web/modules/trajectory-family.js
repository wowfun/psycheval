import { esc, renderComparisonPanels, state, t } from "./runtime.js";
import { bindCopyButton } from "./clipboard.js";

function trajectoryFamily(trajectory, meta, depth = 0, parent = null) {
  const entry = { trajectory, meta, depth, parent };
  return [entry, ...(trajectory?.subagent_trajectories || []).flatMap(child =>
    trajectoryFamily(child, meta?.subagent_meta?.[child.trajectory_id] || {}, depth + 1, entry)
  )];
}

function selectedTrajectoryDetail(trajectory, meta) {
  const entries = trajectoryFamily(trajectory, meta);
  const selected = state.selectedTrajectory;
  const entry = selected && meta?.trial_key && selected.trialKey === meta.trial_key
    ? entries.find(item => item.trajectory?.trajectory_id === selected.trajectoryId) || entries[0]
    : entries[0];
  return { ...entry, meta: { ...entry.meta, trial_key: meta?.trial_key } };
}

function trajectoryLabel({ trajectory, depth }) {
  if (!depth) return [t("main_session", "Main session"), trajectory.trajectory_id].filter(Boolean).join(" · ");
  return trajectory.extra?.claude?.agent_id || trajectory.trajectory_id;
}

function lastAgentMessage(trajectory) {
  const message = (trajectory?.steps || []).findLast(step => step?.source === "agent")?.message;
  if (typeof message === "string") return message;
  return Array.isArray(message)
    ? message.filter(block => block?.type === "text" && typeof block.text === "string").map(block => block.text).join("\n")
    : "";
}

function renderTrajectoryNavigation(trajectory, meta) {
  const entries = trajectoryFamily(trajectory, meta);
  if (entries.length < 2) return "";
  const selected = selectedTrajectoryDetail(trajectory, meta);
  const parent = selected.parent;
  const parentStep = parent?.trajectory?.steps?.find(step =>
    (step.observation?.results || []).some(result =>
      (result.subagent_trajectory_ref || []).some(ref => ref.trajectory_id === selected.trajectory.trajectory_id)));
  const back = parent ? `<button class="action-button" type="button" data-trajectory-id="${esc(parent.trajectory.trajectory_id)}" data-trajectory-step="${esc(parentStep?.step_id || "")}">${esc(t("parent_agent", "Parent agent"))}</button>` : "";
  const children = new Map();
  entries.forEach(entry => {
    const siblings = children.get(entry.parent) || [];
    siblings.push(entry);
    children.set(entry.parent, siblings);
  });
  const renderBranch = entry => {
    const label = trajectoryLabel(entry);
    const descendants = children.get(entry) || [];
    const canCopy = Boolean(lastAgentMessage(entry.trajectory).trim());
    const copyLabel = canCopy ? t("copy_last_agent_message", "Copy last Agent message") : t("no_agent_message_to_copy", "No Agent message to copy");
    return `<li><div class="trajectory-tree-row">
      <button type="button" data-trajectory-node data-trajectory-id="${esc(entry.trajectory.trajectory_id || "")}"${entry.trajectory === selected.trajectory ? ' aria-current="true"' : ""} title="${esc(label)}">${esc(label)}</button>
      <button type="button" data-trajectory-copy="${esc(entry.trajectory.trajectory_id || "")}" title="${esc(copyLabel)}" aria-label="${esc(`${copyLabel}: ${label}`)}" aria-live="polite"${canCopy ? "" : " disabled"}>${esc(t("copy", "Copy"))}</button>
      </div>${descendants.length ? `<ul>${descendants.map(renderBranch).join("")}</ul>` : ""}</li>`;
  };
  return `<nav class="trajectory-navigation" aria-label="${esc(t("trajectory", "Trajectory"))}">
    <ul class="trajectory-tree">${renderBranch(entries[0])}</ul>${back}</nav>`;
}

function bindTrajectoryNavigation(target, trajectory, meta) {
  const entries = trajectoryFamily(trajectory, meta);
  target?.querySelectorAll("[data-trajectory-copy]").forEach(button => {
    const entry = entries.find(item => item.trajectory?.trajectory_id === button.dataset.trajectoryCopy);
    if (entry) bindCopyButton(button, () => lastAgentMessage(entry.trajectory), trajectoryLabel(entry));
  });
  const select = (id, stepId = null, open = false) => {
    if (!entries.some(entry => entry.trajectory?.trajectory_id === id)) return;
    state.selectedTrajectory = { trialKey: meta.trial_key, trajectoryId: id };
    state.selectedStep = stepId ? { trialKey: meta.trial_key, stepId: String(stepId) } : null;
    if (open) state.detailSidebar.open = true;
    renderComparisonPanels();
  };
  target?.querySelectorAll("[data-trajectory-id]").forEach(button => {
    button.addEventListener("click", () => {
      const isTreeNode = button.hasAttribute("data-trajectory-node");
      const scrollTop = button.closest(".trajectory-navigation")?.scrollTop || 0;
      select(button.dataset.trajectoryId, button.dataset.trajectoryStep, !isTreeNode);
      if (isTreeNode) {
        const navigation = target.querySelector(".trajectory-navigation");
        if (navigation) navigation.scrollTop = scrollTop;
        Array.from(target.querySelectorAll("[data-trajectory-node]")).find(node => node.dataset.trajectoryId === button.dataset.trajectoryId)?.focus({ preventScroll: true });
      }
    });
  });
}

export { trajectoryFamily, selectedTrajectoryDetail, renderTrajectoryNavigation, bindTrajectoryNavigation };
