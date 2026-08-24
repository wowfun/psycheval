import { RENDER_OPTIONS, adminMode, esc, listValue, renderComparisonPanels, state, t } from "./runtime.js";
import { serveApi } from "./serve-effects.js";
import { closeWorkspaceReportReader } from "./workspace-reports.js";
import { workbenchState } from "./harbor-workbench.js";
import { renderMarkdown } from "./markdown.js";

const acpState = {
  initialized: false,
  agents: [],
  sessions: [],
  agentId: "",
  sessionId: "",
  revision: 0,
  events: [],
  context: null,
  contextCandidate: null,
  prompts: [],
  promptAssetId: "",
  polling: false,
  pollGeneration: 0,
  opener: null,
};

function drawer() { return document.querySelector("[data-acp-drawer]"); }
function storageKey() { return `peval:${RENDER_OPTIONS?.workspace_id || "default"}:acp-client`; }

async function initializeAcp() {
  if (acpState.initialized || !adminMode() || !drawer()) return;
  acpState.initialized = true;
  restoreUiState();
  bindControls();
  try {
    const [payload, promptPayload] = await Promise.all([
      serveApi("/api/acp/agents"),
      serveApi("/api/prompts"),
    ]);
    acpState.agents = listValue(payload?.agents);
    acpState.prompts = listValue(promptPayload?.prompts);
    if (!acpState.prompts.some(prompt => prompt.id === acpState.promptAssetId)) {
      acpState.promptAssetId = acpState.prompts[0]?.id || "";
    }
    if (!acpState.agents.some(agent => agent.id === acpState.agentId)) {
      acpState.agentId = acpState.agents[0]?.id || "";
    }
    renderAgentControls();
    renderPromptAssets();
    if (selectedAgent()?.connected) await refreshSessions(false);
    if (readSavedUi().open && acpState.agents.length) openAcpDrawer(document.querySelector("[data-acp-open]"));
  } catch (error) {
    showNotice(error.message || String(error), true);
  }
}

function bindControls() {
  document.querySelectorAll("[data-acp-open]").forEach(button => button.addEventListener("click", () => openAcpDrawer(button)));
  document.querySelectorAll("[data-acp-close]").forEach(button => button.addEventListener("click", () => closeAcpDrawer()));
  document.querySelector("[data-acp-backdrop]")?.addEventListener("click", () => closeAcpDrawer());
  document.querySelector("[data-acp-agent]")?.addEventListener("change", async event => {
    acpState.agentId = String(event.target.value || "");
    acpState.sessionId = "";
    acpState.revision = 0;
    acpState.events = [];
    stopPolling();
    renderAgentControls();
    if (selectedAgent()?.connected) await refreshSessions(false);
    persistUiState();
  });
  document.querySelector("[data-acp-connect]")?.addEventListener("click", toggleConnection);
  document.querySelector("[data-acp-new-session]")?.addEventListener("click", createSession);
  document.querySelector("[data-acp-session-close]")?.addEventListener("click", closeSession);
  document.querySelector("[data-acp-session]")?.addEventListener("change", event => selectSession(String(event.target.value || ""), { resume: true }));
  document.querySelector("[data-acp-context-capture]")?.addEventListener("click", captureContext);
  document.querySelector("[data-acp-prompt-asset]")?.addEventListener("change", event => {
    acpState.promptAssetId = String(event.target.value || "");
    renderPromptAssets();
  });
  document.querySelector("[data-acp-use-prompt]")?.addEventListener("click", usePromptAsset);
  document.querySelector("[data-acp-composer]")?.addEventListener("submit", sendPrompt);
  document.querySelector("[data-acp-stop]")?.addEventListener("click", cancelPrompt);
  document.querySelector("[data-acp-prompt]")?.addEventListener("keydown", event => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      document.querySelector("[data-acp-composer]")?.requestSubmit?.();
    }
  });
  document.querySelector("[data-acp-events]")?.addEventListener("click", handleEventAction);
  document.querySelector("[data-acp-session-options]")?.addEventListener("change", handleSessionOption);
}

function openAcpDrawer(opener = null) {
  const panel = drawer();
  if (!panel || !adminMode()) return false;
  acpState.contextCandidate = currentContext();
  closeWorkspaceReportReader({ restoreFocus: false });
  if (state.selectedStep) {
    state.selectedStep = null;
    renderComparisonPanels();
  }
  acpState.opener = opener || document.activeElement;
  panel.hidden = false;
  const backdrop = document.querySelector("[data-acp-backdrop]");
  if (backdrop) backdrop.hidden = false;
  document.body.classList.add("acp-drawer-open");
  document.querySelector("[data-acp-open]")?.setAttribute("aria-expanded", "true");
  persistUiState({ open: true });
  panel.querySelector("[data-acp-prompt]")?.focus?.();
  startPolling();
  return true;
}

function closeAcpDrawer(options = {}) {
  const panel = drawer();
  if (!panel || panel.hidden) return false;
  panel.hidden = true;
  const backdrop = document.querySelector("[data-acp-backdrop]");
  if (backdrop) backdrop.hidden = true;
  document.body.classList.remove("acp-drawer-open");
  document.querySelector("[data-acp-open]")?.setAttribute("aria-expanded", "false");
  stopPolling();
  persistUiState({ open: false });
  if (options.restoreFocus !== false) acpState.opener?.focus?.();
  acpState.opener = null;
  return true;
}

async function toggleConnection(event) {
  const button = event.currentTarget;
  const agent = selectedAgent();
  if (!agent) return;
  button.disabled = true;
  showNotice(agent.connected ? t("acp_disconnecting", "Disconnecting…") : t("acp_connecting", "Starting local agent…"));
  try {
    const payload = await serveApi(agent.connected ? "/api/acp/disconnect" : "/api/acp/connect", {
      method: "POST", body: { agent_id: agent.id }
    });
    replaceAgent(payload);
    if (payload.connected) await refreshSessions(true);
    else {
      acpState.sessions = [];
      selectSession("");
    }
    showNotice(payload.connected ? t("acp_connected", "Local agent connected") : t("acp_disconnected", "Local agent disconnected"));
  } catch (error) {
    showNotice(error.message || String(error), true);
  } finally {
    button.disabled = false;
    renderAgentControls();
  }
}

async function refreshSessions(refresh = true) {
  if (!acpState.agentId) return;
  const query = new URLSearchParams({ agent_id: acpState.agentId, refresh: refresh ? "1" : "0" });
  const payload = await serveApi(`/api/acp/sessions?${query}`);
  acpState.sessions = listValue(payload?.sessions);
  if (!acpState.sessions.some(session => session.session_id === acpState.sessionId)) {
    acpState.sessionId = acpState.sessions.find(session => !session.closed)?.session_id || "";
    acpState.revision = 0;
    acpState.events = [];
  }
  renderSessionControls();
  persistUiState();
  if (acpState.sessionId && selectedSession()?.loaded === false) {
    await resumeSession(acpState.sessionId);
  }
  startPolling();
}

async function createSession() {
  if (!selectedAgent()?.connected) return;
  setBusy(true);
  try {
    const session = await serveApi("/api/acp/sessions", {
      method: "POST", body: { agent_id: acpState.agentId }
    });
    upsertSession(session);
    selectSession(session.session_id);
    showNotice(t("acp_session_created", "Session ready"));
  } catch (error) {
    showNotice(error.message || String(error), true);
  } finally {
    setBusy(false);
  }
}

async function closeSession() {
  const session = selectedSession();
  if (!session || session.active_prompt) return;
  try {
    const updated = await serveApi("/api/acp/close", {
      method: "POST", body: ids()
    });
    upsertSession(updated);
    renderSessionControls();
  } catch (error) {
    showNotice(error.message || String(error), true);
  }
}

function selectSession(sessionId, options = {}) {
  stopPolling();
  acpState.sessionId = sessionId;
  acpState.revision = 0;
  acpState.events = [];
  renderSessionControls();
  renderEvents();
  persistUiState();
  if (options.resume && selectedSession()?.loaded === false) {
    resumeSession(sessionId);
  } else startPolling();
}

async function resumeSession(sessionId) {
  if (!sessionId) return;
  setBusy(true);
  try {
    const session = await serveApi("/api/acp/sessions", {
      method: "POST",
      body: { agent_id: acpState.agentId, resume_session_id: sessionId },
    });
    upsertSession(session);
    renderSessionControls();
  } catch (error) {
    showNotice(error.message || String(error), true);
  } finally {
    setBusy(false);
    startPolling();
  }
}

async function sendPrompt(event) {
  event.preventDefault();
  const textarea = document.querySelector("[data-acp-prompt]");
  const prompt = String(textarea?.value || "").trim();
  const session = selectedSession();
  if (!prompt || !session || session.active_prompt) return;
  try {
    const updated = await serveApi("/api/acp/prompt", {
      method: "POST",
      body: { ...ids(), prompt, ...(acpState.context ? { context: acpState.context.value } : {}) }
    });
    if (textarea) textarea.value = "";
    upsertSession(updated);
    renderSessionControls();
    startPolling();
  } catch (error) {
    showNotice(error.message || String(error), true);
  }
}

async function cancelPrompt() {
  try {
    const updated = await serveApi("/api/acp/cancel", { method: "POST", body: ids() });
    upsertSession(updated);
    renderSessionControls();
  } catch (error) {
    showNotice(error.message || String(error), true);
  }
}

function captureContext() {
  const next = acpState.contextCandidate || currentContext();
  if (!next) {
    showNotice(t("acp_context_unavailable", "Select an evaluation item first"), true);
    return;
  }
  acpState.context = next;
  const suggestedPromptId = { source: "failure-diagnosis", dataset_task: "task-audit", report: "report-review" }[next.value?.kind];
  if (suggestedPromptId && acpState.prompts.some(prompt => prompt.id === suggestedPromptId)) {
    acpState.promptAssetId = suggestedPromptId;
    renderPromptAssets();
  }
  renderContext();
  showNotice(t("acp_context_attached", "Current evaluation context attached"));
}

function renderPromptAssets() {
  const select = document.querySelector("[data-acp-prompt-asset]");
  if (select) {
    select.innerHTML = `<option value="">${esc(t("acp_prompt_custom", "Custom prompt"))}</option>${acpState.prompts.map(prompt => `<option value="${esc(prompt.id)}" ${prompt.id === acpState.promptAssetId ? "selected" : ""}>${esc(prompt.title)}</option>`).join("")}`;
  }
  const use = document.querySelector("[data-acp-use-prompt]");
  if (use) use.disabled = !acpState.prompts.some(prompt => prompt.id === acpState.promptAssetId);
}

function usePromptAsset() {
  const prompt = acpState.prompts.find(item => item.id === acpState.promptAssetId);
  const textarea = document.querySelector("[data-acp-prompt]");
  if (!prompt || !textarea) return;
  textarea.value = prompt.content || "";
  textarea.focus?.();
}

function currentContext() {
  const page = RENDER_OPTIONS?.serve_page;
  if (page === "home" && state.selectedSourceKey) {
    const stepId = state.selectedStep?.stepId;
    return {
      label: stepId ? `${state.selectedSourceKey} · ${t("step", "Step")} ${stepId}` : state.selectedSourceKey,
      value: { kind: "source", source_key: state.selectedSourceKey, ...(stepId ? { step_id: stepId } : {}) }
    };
  }
  if (page === "datasets" && workbenchState.datasetId && workbenchState.taskName) {
    return {
      label: `${workbenchState.datasetId} / ${workbenchState.taskName}`,
      value: { kind: "dataset_task", dataset_id: workbenchState.datasetId, task: workbenchState.taskName }
    };
  }
  if (page === "reports") {
    const reportId = state.reportReader.openId || state.reportManager.selectedId;
    const report = listValue(state.workspaceReports).find(item => item.report_id === reportId);
    if (reportId) return { label: report?.filename || reportId, value: { kind: "report", report_id: reportId } };
  }
  return null;
}

function startPolling() {
  if (acpState.polling || drawer()?.hidden || !acpState.agentId || !acpState.sessionId) return;
  acpState.polling = true;
  const generation = ++acpState.pollGeneration;
  pollEvents(generation);
}

function stopPolling() {
  acpState.polling = false;
  acpState.pollGeneration += 1;
}

async function pollEvents(generation) {
  let failures = 0;
  while (acpState.polling && generation === acpState.pollGeneration) {
    const query = new URLSearchParams({
      agent_id: acpState.agentId,
      session_id: acpState.sessionId,
      after: String(acpState.revision),
      wait: "20",
    });
    try {
      const payload = await serveApi(`/api/acp/events?${query}`);
      if (!acpState.polling || generation !== acpState.pollGeneration) return;
      const incoming = listValue(payload?.events);
      const nextEvents = payload?.reset ? incoming : mergeByRevision(acpState.events, incoming);
      const eventsChanged = JSON.stringify(nextEvents) !== JSON.stringify(acpState.events);
      const revision = Number(payload?.revision);
      if (Number.isFinite(revision)) acpState.revision = revision;
      const sessionChanged = payload?.session
        && JSON.stringify(payload.session) !== JSON.stringify(selectedSession());
      acpState.events = nextEvents;
      if (sessionChanged) upsertSession(payload.session);
      if (sessionChanged) renderSessionControls();
      if (eventsChanged) renderEvents();
      failures = 0;
    } catch (error) {
      if (generation !== acpState.pollGeneration) return;
      if (error?.status === 404) {
        stopPolling();
        acpState.sessionId = "";
        acpState.revision = 0;
        acpState.events = [];
        renderSessionControls();
        renderEvents();
        persistUiState();
        try {
          await refreshSessions(false);
        } catch (refreshError) {
          showNotice(refreshError.message || String(refreshError), true);
        }
        return;
      }
      showNotice(error.message || String(error), true);
      failures += 1;
      await new Promise(resolve => setTimeout(resolve, Math.min(250 * (2 ** (failures - 1)), 5000)));
    }
  }
}

function mergeByRevision(existing, incoming) {
  const values = new Map(existing.map(event => [Number(event.revision), event]));
  incoming.forEach(event => values.set(Number(event.revision), event));
  return Array.from(values.values()).sort((left, right) => Number(left.revision) - Number(right.revision));
}

function renderEvents() {
  const target = document.querySelector("[data-acp-events]");
  if (!target) return;
  if (!acpState.events.length) {
    target.innerHTML = `<div class="acp-empty">${esc(t("acp_empty_session", "This session is quiet. Send a prompt to start."))}</div>`;
    return;
  }
  target.innerHTML = collapseChunks(acpState.events).map(renderEvent).join("");
  target.querySelectorAll(".acp-message-body[data-markdown]").forEach(node => {
    node.innerHTML = renderMarkdown(node.dataset.markdown || "");
  });
  target.scrollTop = target.scrollHeight;
}

function collapseChunks(events) {
  const collapsed = [];
  events.forEach(event => {
    const previous = collapsed[collapsed.length - 1];
    if (previous && ["message", "thought"].includes(event.type) && previous.type === event.type) {
      previous.text = `${previous.text || ""}${event.text || ""}`;
      previous.revision = event.revision;
    } else collapsed.push({ ...event });
  });
  return collapsed;
}

function renderEvent(event) {
  const type = String(event.type || "unknown");
  const label = eventLabel(type);
  let body = "";
  if (["message", "user_message"].includes(type)) {
    body = `<div class="acp-message-body note-body" data-markdown="${esc(event.text || "")}"></div>`;
  } else if (type === "thought") {
    body = `<details><summary>${esc(t("acp_show_thought", "Agent reasoning"))}</summary><div class="acp-message-body note-body" data-markdown="${esc(event.text || "")}"></div></details>`;
  } else if (type === "tool") {
    body = `<div class="acp-tool-head"><strong>${esc(event.title || event.kind || t("tool_calls", "Tool call"))}</strong><span>${esc(event.status || "pending")}</span></div>${renderJsonDetails(event.raw_input || event.content || event.raw_output)}`;
  } else if (type === "permission") {
    const permissionResult = latestPermissionResult(event.request_id);
    const options = listValue(event.options);
    const selectedOption = options.find(option => String(option.optionId ?? option.id ?? "") === String(permissionResult?.option_id ?? ""));
    const requestIdAttributes = `data-acp-permission="${esc(event.request_id)}" data-acp-request-id-type="${esc(typeof event.request_id)}"`;
    const answered = permissionResult ? " disabled" : "";
    const resultSummary = permissionResult
      ? `<p class="acp-permission-result">${esc(permissionResult.cancelled ? t("cancel", "Cancel") : selectedOption?.name || selectedOption?.label || permissionResult.option_id || t("complete", "Complete"))}</p>`
      : "";
    body = `<strong>${esc(t("acp_permission_required", "Permission required"))}</strong>${renderJsonDetails(event.tool_call)}<div class="acp-permission-options">${options.map(option => `<button class="action-button compact" type="button" ${requestIdAttributes} data-option-id="${esc(option.optionId || option.id || "")}"${answered}>${esc(option.name || option.label || option.optionId || option.id || t("allow", "Allow"))}</button>`).join("")}<button class="action-button compact danger" type="button" ${requestIdAttributes} data-cancelled="true"${answered}>${esc(t("cancel", "Cancel"))}</button></div>${resultSummary}`;
  } else if (type === "plan") {
    body = `<ol class="acp-plan">${listValue(event.entries).map(entry => `<li data-status="${esc(entry.status || "pending")}"><span>${esc(entry.content || entry.title || "")}</span><small>${esc(entry.status || "pending")}</small></li>`).join("")}</ol>`;
  } else if (type === "error") {
    body = `<p class="danger">${esc(event.message || t("error", "Error"))}</p>`;
  } else if (["status", "session", "prompt_complete", "mode", "config", "usage", "permission_result"].includes(type)) {
    body = `<p>${esc(event.status || event.stop_reason || event.mode_id || t("acp_event_recorded", "Event recorded"))}</p>`;
  } else if (type === "commands") {
    body = `<div class="acp-command-list">${listValue(event.commands).map(command => `<code>/${esc(command.name || command.command || "")}</code>`).join("")}</div>`;
  } else {
    body = renderJsonDetails(event.payload || event.result || event);
  }
  return `<article class="acp-event acp-event-${esc(type)}"><span class="acp-event-node" aria-hidden="true"></span><header><span>${esc(label)}</span><code>#${esc(event.revision || "")}</code></header><div class="acp-event-body">${body}</div></article>`;
}

function latestPermissionResult(requestId) {
  return [...acpState.events].reverse().find(event => (
    event.type === "permission_result"
    && typeof event.request_id === typeof requestId
    && event.request_id === requestId
  ));
}

function renderJsonDetails(value) {
  if (value === null || value === undefined || value === "") return "";
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return `<details class="acp-payload"><summary>${esc(t("details", "Details"))}</summary><pre>${esc(text)}</pre></details>`;
}

function eventLabel(type) {
  return ({
    message: t("agent", "Agent"), user_message: t("you", "You"), thought: t("analysis", "Analysis"),
    tool: t("tool_calls", "Tool call"), permission: t("acp_permission", "Permission"), plan: t("acp_plan", "Plan"),
    error: t("error", "Error"), prompt_complete: t("complete", "Complete"), session: t("session", "Session"),
  })[type] || type.replaceAll("_", " ");
}

async function handleEventAction(event) {
  const button = event.target?.closest?.("[data-acp-permission]");
  if (!button) return;
  button.disabled = true;
  try {
    await serveApi("/api/acp/permission", {
      method: "POST",
      body: {
        ...ids(), request_id: button.dataset.acpRequestIdType === "string"
          ? String(button.dataset.acpPermission)
          : numericId(button.dataset.acpPermission),
        ...(button.dataset.optionId ? { option_id: button.dataset.optionId } : {}),
        cancelled: button.dataset.cancelled === "true",
      }
    });
  } catch (error) {
    button.disabled = false;
    showNotice(error.message || String(error), true);
  }
}

async function handleSessionOption(event) {
  const control = event.target;
  try {
    if (control.matches("[data-acp-mode]")) {
      const payload = await serveApi("/api/acp/session-mode", { method: "POST", body: { ...ids(), mode_id: control.value } });
      upsertSession(payload.session);
    } else if (control.matches("[data-acp-config]")) {
      const payload = await serveApi("/api/acp/session-config", { method: "POST", body: { ...ids(), option_id: control.dataset.acpConfig, value: control.value } });
      upsertSession(payload.session);
    }
  } catch (error) {
    showNotice(error.message || String(error), true);
  }
}

function renderAgentControls() {
  const select = document.querySelector("[data-acp-agent]");
  if (select) {
    select.innerHTML = acpState.agents.length ? acpState.agents.map(agent => `<option value="${esc(agent.id)}" ${agent.id === acpState.agentId ? "selected" : ""}>${esc(agent.title)}</option>`).join("") : `<option value="">${esc(t("acp_no_agents", "No agents configured"))}</option>`;
    select.disabled = !acpState.agents.length;
  }
  const agent = selectedAgent();
  const connect = document.querySelector("[data-acp-connect]");
  if (connect) {
    connect.hidden = !agent;
    connect.textContent = agent?.connected ? t("acp_disconnect", "Disconnect") : t("acp_connect", "Connect");
    connect.disabled = !agent;
  }
  const configure = document.querySelector("[data-acp-configure]");
  if (configure) configure.hidden = Boolean(agent);
  const protocol = document.querySelector("[data-acp-protocol]");
  if (protocol) {
    protocol.textContent = agent?.connected ? `ACP v${agent.protocol_version}` : "ACP · —";
    protocol.classList.toggle("connected", Boolean(agent?.connected));
  }
  renderSessionControls();
}

function renderSessionControls() {
  const select = document.querySelector("[data-acp-session]");
  if (select) {
    select.innerHTML = `<option value="">${esc(t("acp_no_session", "No session yet"))}</option>${acpState.sessions.map(session => `<option value="${esc(session.session_id)}" ${session.session_id === acpState.sessionId ? "selected" : ""}>${esc(session.title || shortId(session.session_id))}${session.closed ? ` · ${esc(t("closed", "closed"))}` : ""}</option>`).join("")}`;
    select.disabled = !selectedAgent()?.connected;
  }
  const session = selectedSession();
  const create = document.querySelector("[data-acp-new-session]");
  if (create) create.disabled = !selectedAgent()?.connected;
  const close = document.querySelector("[data-acp-session-close]");
  if (close) close.disabled = !session || session.closed || session.active_prompt;
  const prompt = document.querySelector("[data-acp-prompt]");
  const send = document.querySelector("[data-acp-send]");
  if (prompt) prompt.disabled = !session || session.closed;
  if (send) send.disabled = !session || session.closed || session.active_prompt;
  const stop = document.querySelector("[data-acp-stop]");
  if (stop) stop.hidden = !session?.active_prompt;
  const usage = document.querySelector("[data-acp-usage]");
  if (usage) usage.textContent = usageText(session?.usage);
  renderSessionOptions(session);
}

function renderSessionOptions(session) {
  const target = document.querySelector("[data-acp-session-options]");
  if (!target) return;
  const modes = listValue(session?.modes?.availableModes);
  const options = listValue(session?.config_options);
  target.hidden = !modes.length && !options.length;
  target.innerHTML = [
    modes.length ? `<label><span>${esc(t("acp_mode", "Mode"))}</span><select data-acp-mode>${modes.map(mode => `<option value="${esc(mode.id)}" ${mode.id === session.current_mode ? "selected" : ""}>${esc(mode.name || mode.id)}</option>`).join("")}</select></label>` : "",
    ...options.map(option => renderConfigOption(option)),
  ].join("");
}

function renderConfigOption(option) {
  const id = option.id || option.configId || "";
  const values = listValue(option.options);
  if (!id || !values.length) return "";
  return `<label><span>${esc(option.name || id)}</span><select data-acp-config="${esc(id)}">${values.map(value => `<option value="${esc(value.value ?? value.id ?? "")}" ${(value.value ?? value.id) === option.currentValue ? "selected" : ""}>${esc(value.name || value.label || value.value || value.id || "")}</option>`).join("")}</select></label>`;
}

function renderContext() {
  const label = document.querySelector("[data-acp-context-label]");
  if (label) label.textContent = acpState.context?.label || t("acp_context_none", "No evaluation context attached");
  document.querySelector("[data-acp-context-chip]")?.classList.toggle("attached", Boolean(acpState.context));
  const button = document.querySelector("[data-acp-context-capture]");
  if (button) button.textContent = acpState.context ? t("acp_replace_context", "Replace context") : t("acp_attach_context", "Attach current context");
}

function selectedAgent() { return acpState.agents.find(agent => agent.id === acpState.agentId) || null; }
function selectedSession() { return acpState.sessions.find(session => session.session_id === acpState.sessionId) || null; }
function ids() { return { agent_id: acpState.agentId, session_id: acpState.sessionId }; }
function replaceAgent(agent) { acpState.agents = acpState.agents.map(item => item.id === agent.id ? agent : item); }
function upsertSession(session) {
  if (!session?.session_id) return;
  const index = acpState.sessions.findIndex(item => item.session_id === session.session_id);
  if (index >= 0) acpState.sessions[index] = session;
  else acpState.sessions.push(session);
}
function shortId(value) { const text = String(value || ""); return text.length > 22 ? `${text.slice(0, 10)}…${text.slice(-8)}` : text; }
function numericId(value) { const number = Number(value); return Number.isSafeInteger(number) && String(number) === String(value) ? number : String(value); }
function usageText(usage) {
  if (!usage || typeof usage !== "object") return "";
  const used = usage.used ?? usage.tokens ?? usage.totalTokens;
  const size = usage.size ?? usage.contextWindow;
  return used === undefined ? "" : `${Number(used).toLocaleString()}${size ? ` / ${Number(size).toLocaleString()}` : ""} tok`;
}
function setBusy(busy) { document.querySelectorAll("[data-acp-new-session],[data-acp-session-close]").forEach(button => { button.disabled = busy; }); }
function showNotice(message, error = false) {
  const node = document.querySelector("[data-acp-notice]");
  if (!node) return;
  node.textContent = message;
  node.classList.toggle("danger", error);
  node.hidden = !message;
}
function readSavedUi() {
  try { return JSON.parse(window.localStorage.getItem(storageKey()) || "{}"); } catch { return {}; }
}
function restoreUiState() {
  const saved = readSavedUi();
  acpState.agentId = typeof saved.agent_id === "string" ? saved.agent_id : "";
  acpState.sessionId = typeof saved.session_id === "string" ? saved.session_id : "";
}
function persistUiState(extra = {}) {
  try {
    window.localStorage.setItem(storageKey(), JSON.stringify({ ...readSavedUi(), agent_id: acpState.agentId, session_id: acpState.sessionId, ...extra }));
  } catch { /* UI preference persistence is best effort. */ }
}

export { acpState, closeAcpDrawer, currentContext, initializeAcp, openAcpDrawer };
