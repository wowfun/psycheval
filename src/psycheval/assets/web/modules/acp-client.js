// @ts-check

import {
  createWebSocketConnector,
  mountChat,
} from "../vendor/pretty-aui/pretty-aui.js";
import {
  snapshotWorkspace,
  subscribeWorkspaceInvalidation,
} from "../app/workspace-runtime.js";
import { serveApi } from "./http.js";
import { RENDER_OPTIONS, adminMode, esc, listValue, t } from "./shared.js";

const acpState = {
  initialized: false,
  unsubscribeInvalidation: null,
  agents: [],
  cwd: "",
  agentId: "",
  mounted: null,
  contexts: [],
  prompts: [],
  promptAssetId: "",
  opener: null,
  connecting: false,
  mountGeneration: 0,
};

const contextListeners = new Set();
const contextProvider = {
  getSelection: () =>
    acpState.contexts.map(context => ({ id: context.id, label: context.label })),
  subscribe(listener) {
    contextListeners.add(listener);
    return () => contextListeners.delete(listener);
  },
  add: captureContext,
  remove: removeContext,
  resolve: resolveCapturedContexts,
};

function drawer() {
  return /** @type {HTMLElement | null} */ (
    document.querySelector("[data-acp-drawer]")
  );
}

function storageKey() {
  return `peval:${RENDER_OPTIONS?.workspace_id || "default"}:acp-client`;
}

async function initializeAcp() {
  if (acpState.initialized || !adminMode() || !drawer()) return;
  acpState.initialized = true;
  restoreUiState();
  bindControls();
  document.querySelectorAll("[data-acp-open]").forEach(button => {
    /** @type {HTMLButtonElement} */ (button).disabled = false;
  });
  acpState.unsubscribeInvalidation = subscribeWorkspaceInvalidation(changes => {
    if (changes.has("assistant-config")) void refreshAcpConfiguration();
    else if (changes.has("prompt-assets")) void refreshPromptCatalog();
  });
  try {
    await loadCatalogs();
    const saved = readSavedUi();
    if (saved.open && acpState.agents.length) {
      openAcpDrawer(document.querySelector("[data-acp-open]"));
    }
    if (saved.auto_connect && acpState.agentId) await connectAcpAgent();
  } catch (error) {
    showNotice(errorMessage(error), true);
  }
}

async function loadCatalogs() {
  const [agentPayload, promptPayload] = await Promise.all([
    serveApi("/api/acp/agents"),
    serveApi("/api/prompts"),
  ]);
  applyAgentCatalog(agentPayload);
  applyPromptCatalog(promptPayload);
  renderControls();
}

function applyAgentCatalog(agentPayload) {
  acpState.cwd = typeof agentPayload?.cwd === "string" ? agentPayload.cwd : "";
  acpState.agents = listValue(agentPayload?.agents);
  if (!acpState.agents.some(agent => agent.id === acpState.agentId)) {
    acpState.agentId = acpState.agents[0]?.id || "";
  }
}

function applyPromptCatalog(promptPayload) {
  acpState.prompts = listValue(promptPayload);
  if (!acpState.prompts.some(prompt => prompt.id === acpState.promptAssetId)) {
    acpState.promptAssetId = acpState.prompts[0]?.id || "";
  }
}

async function refreshPromptCatalog() {
  if (!acpState.initialized) return;
  try {
    applyPromptCatalog(await serveApi("/api/prompts"));
    renderPromptAssets();
  } catch (error) {
    showNotice(errorMessage(error), true);
  }
}

async function refreshAcpConfiguration() {
  if (!acpState.initialized) return;
  await disconnectAcpAgent({ persist: false });
  try {
    await loadCatalogs();
    persistUiState({ auto_connect: false });
  } catch (error) {
    showNotice(errorMessage(error), true);
  }
}

function bindControls() {
  document.querySelectorAll("[data-acp-open]").forEach(button => {
    button.addEventListener("click", () => openAcpDrawer(button));
  });
  document.querySelectorAll("[data-acp-close]").forEach(button => {
    button.addEventListener("click", () => closeAcpDrawer());
  });
  document.querySelector("[data-acp-backdrop]")?.addEventListener("click", () => {
    closeAcpDrawer();
  });
  document.querySelector("[data-acp-agent]")?.addEventListener("change", event => {
    const target = /** @type {HTMLSelectElement} */ (event.target);
    acpState.agentId = String(target.value || "");
    persistUiState({ agent_id: acpState.agentId, auto_connect: false });
    renderControls();
  });
  document.querySelector("[data-acp-connect]")?.addEventListener("click", () => {
    if (acpState.mounted) void disconnectAcpAgent();
    else void connectAcpAgent();
  });
  document.querySelector("[data-acp-prompt-asset]")?.addEventListener("change", event => {
    const target = /** @type {HTMLSelectElement} */ (event.target);
    acpState.promptAssetId = String(target.value || "");
    persistUiState({ prompt_asset_id: acpState.promptAssetId });
    renderPromptAssets();
  });
  document
    .querySelector("[data-acp-use-prompt]")
    ?.addEventListener("click", usePromptAsset);
}

function openAcpDrawer(opener = null) {
  const panel = drawer();
  if (!panel || !adminMode()) return false;
  acpState.opener = opener || document.activeElement;
  panel.hidden = false;
  const backdrop = /** @type {HTMLElement | null} */ (
    document.querySelector("[data-acp-backdrop]")
  );
  if (backdrop) backdrop.hidden = false;
  document.body.classList.add("acp-drawer-open");
  document.querySelector("[data-acp-open]")?.setAttribute("aria-expanded", "true");
  persistUiState({ open: true });
  if (acpState.mounted) acpState.mounted.focusComposer();
  else /** @type {HTMLElement | null} */ (document.querySelector("[data-acp-connect]"))?.focus();
  return true;
}

function closeAcpDrawer(options = {}) {
  const panel = drawer();
  if (!panel || panel.hidden) return false;
  panel.hidden = true;
  const backdrop = /** @type {HTMLElement | null} */ (
    document.querySelector("[data-acp-backdrop]")
  );
  if (backdrop) backdrop.hidden = true;
  document.body.classList.remove("acp-drawer-open");
  document.querySelector("[data-acp-open]")?.setAttribute("aria-expanded", "false");
  persistUiState({ open: false });
  if (options.restoreFocus !== false) acpState.opener?.focus?.();
  acpState.opener = null;
  return true;
}

async function connectAcpAgent(options = {}) {
  if (
    acpState.connecting ||
    acpState.mounted ||
    !selectedAgent() ||
    !acpState.cwd
  ) {
    return false;
  }
  const host = document.querySelector("[data-acp-chat]");
  if (!host) return false;
  const agentId = acpState.agentId;
  const savedSessionId = options.fresh ? "" : savedSession(agentId);
  const generation = ++acpState.mountGeneration;
  acpState.connecting = true;
  showNotice(t("acp_connecting", "Starting local agent…"));
  renderControls();

  const mounted = mountChat(host, {
    options: {
      connector: createWebSocketConnector(websocketUrl(agentId), {
        cookies: "include",
      }),
      protocol: "auto",
      session: { cwd: acpState.cwd },
      initialSession: savedSessionId
        ? { type: "open", sessionId: savedSessionId }
        : { type: "new" },
      context: contextProvider,
      allowAuthentication: false,
      clientInfo: {
        name: "psycheval",
        title: "Psycheval",
        version: "0.1.0",
      },
      onEvent: event => handleChatEvent(event, agentId, generation),
    },
    surface: "sidebar",
    colorScheme: "system",
    labels: prettyLabels(),
    ...(RENDER_OPTIONS.csp_nonce
      ? { styleNonce: String(RENDER_OPTIONS.csp_nonce) }
      : {}),
  });
  acpState.mounted = mounted;
  renderControls();
  try {
    await mounted.ready;
    if (generation !== acpState.mountGeneration || acpState.mounted !== mounted) {
      return false;
    }
    acpState.connecting = false;
    persistUiState({ auto_connect: true });
    showNotice(t("acp_connected", "Local agent connected"));
    renderControls();
    if (!drawer()?.hidden) mounted.focusComposer();
    return true;
  } catch (error) {
    if (generation !== acpState.mountGeneration || acpState.mounted !== mounted) {
      return false;
    }
    await releaseMounted(mounted);
    if (
      savedSessionId &&
      error?.code === "SESSION_REJECTED" &&
      error?.phase === "session/open"
    ) {
      forgetSavedSession(agentId);
      return connectAcpAgent({ fresh: true });
    }
    acpState.connecting = false;
    persistUiState({ auto_connect: false });
    showNotice(errorMessage(error), true);
    renderControls();
    return false;
  }
}

async function disconnectAcpAgent(options = {}) {
  const mounted = acpState.mounted;
  ++acpState.mountGeneration;
  acpState.mounted = null;
  acpState.connecting = false;
  if (mounted) await mounted.unmount();
  if (options.persist !== false) persistUiState({ auto_connect: false });
  if (mounted) showNotice(t("acp_disconnected", "Local agent disconnected"));
  renderControls();
  return Boolean(mounted);
}

async function releaseMounted(mounted) {
  if (acpState.mounted === mounted) acpState.mounted = null;
  acpState.connecting = false;
  await mounted.unmount();
}

function handleChatEvent(event, agentId, generation) {
  if (generation !== acpState.mountGeneration) return;
  if (event.type === "session_changed") {
    saveSession(agentId, event.sessionId);
    return;
  }
  if (event.type === "error") showNotice(event.error?.message || t("error", "Error"), true);
}

async function resolveCapturedContexts(request) {
  const contextsById = new Map(
    acpState.contexts.map(context => [context.id, context]),
  );
  const payloads = await Promise.all(
    request.selection.map(async selection => {
      const context = contextsById.get(selection.id);
      if (!context) throw new Error(`Selected context is unavailable: ${selection.label}`);
      return serveApi("/api/acp/context-resolutions", {
        method: "POST",
        body: {
          context: context.value,
          embedded_context: Boolean(request.capabilities?.embeddedContext),
        },
        signal: request.signal,
      });
    }),
  );
  return payloads.flatMap(payload => listValue(payload?.items));
}

function captureContext() {
  const next = currentContext();
  if (!next) {
    showNotice(t("acp_context_unavailable", "Select an evaluation item first"), true);
    return;
  }
  if (acpState.contexts.some(context => context.id === next.id)) {
    showNotice(t("acp_context_already_attached", "Evaluation context is already attached"));
    return;
  }
  if (acpState.contexts.length >= 64) {
    showNotice(t("acp_context_limit", "Context is limited to 64 items"), true);
    return;
  }
  acpState.contexts = [...acpState.contexts, next];
  persistUiState({ contexts: acpState.contexts });
  const suggestedPromptId = {
    source: "failure-diagnosis",
    dataset_task: "task-audit",
    report: "report-review",
  }[next.value?.kind];
  if (suggestedPromptId && acpState.prompts.some(prompt => prompt.id === suggestedPromptId)) {
    acpState.promptAssetId = suggestedPromptId;
  }
  showNotice(t("acp_context_attached", "Current evaluation context attached"));
  notifyContextSelection();
  renderPromptAssets();
}

function removeContext(id) {
  const next = acpState.contexts.filter(context => context.id !== id);
  if (next.length === acpState.contexts.length) return;
  acpState.contexts = next;
  persistUiState({ contexts: next });
  notifyContextSelection();
  showNotice(t("acp_context_removed", "Evaluation context removed"));
}

function notifyContextSelection() {
  for (const listener of contextListeners) listener();
}

function usePromptAsset() {
  const prompt = acpState.prompts.find(item => item.id === acpState.promptAssetId);
  if (!prompt || !acpState.mounted) return;
  acpState.mounted.setDraft(String(prompt.content || ""), { focus: true });
}

function currentContext() {
  const context = snapshotWorkspace().context || {};
  if (context.page === "home" && context.source_key) {
    const stepId = context.step_id;
    return {
      id: `source:${context.source_key}:${stepId || ""}`,
      label: stepId
        ? `${context.source_key} · ${t("step", "Step")} ${stepId}`
        : context.source_key,
      value: {
        kind: "source",
        source_key: context.source_key,
        ...(stepId ? { step_id: stepId } : {}),
      },
    };
  }
  if (context.page === "datasets" && context.dataset_id && context.task) {
    return {
      id: `dataset:${context.dataset_id}:${context.task}`,
      label: `${context.dataset_id} / ${context.task}`,
      value: {
        kind: "dataset_task",
        dataset_id: context.dataset_id,
        task: context.task,
      },
    };
  }
  if (context.page === "reports" && context.report_id) {
    return {
      id: `report:${context.report_id}`,
      label: context.report_name || context.report_id,
      value: { kind: "report", report_id: context.report_id },
    };
  }
  return null;
}

function websocketUrl(agentId) {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${window.location.host}/api/acp/agents/${encodeURIComponent(agentId)}/ws`;
}

function prettyLabels() {
  return {
    accept: t("acp_continue", "Continue"),
    addContext: t("acp_add_context", "Add context"),
    agentName: agent => agent ? `${agent} Agent` : t("agent", "Agent"),
    agentOngoing: t("acp_agent_ongoing", "Ongoing"),
    agentCompleted: t("acp_agent_completed", "Completed"),
    agentFailed: t("acp_agent_failed", "Failed"),
    agentCancelled: t("acp_agent_cancelled", "Cancelled"),
    agentBackground: t("acp_agent_background", "Started in background"),
    agentObserved: duration => formatLabel("acp_agent_observed", "Observed {duration}", { duration }),
    assistantName: t("acp_assistant", "Psycheval Copilot"),
    authRequired: t("acp_auth_required", "Authentication required"),
    binaryChange: t("acp_binary_change", "Binary or structural change"),
    cancel: t("cancel", "Cancel"),
    changedFiles: t("acp_changed_files", "Changed files"),
    close: t("close", "Close"),
    closeSession: t("acp_close_session", "Close session"),
    commands: t("acp_commands", "Commands"),
    composerPlaceholder: t("acp_prompt_placeholder", "Ask about this evaluation…"),
    contextInjection: t("acp_context_injection", "Context injection"),
    contextSelection: t("acp_context_selection", "Context for next prompt"),
    contextTruncated: total => formatLabel(
      "acp_context_truncated",
      "Context display truncated ({count} characters total).",
      { count: total.toLocaleString() },
    ),
    decline: t("acp_decline", "Decline"),
    deleteSession: t("acp_delete_session", "Delete session"),
    emptyDescription: t("acp_empty_description", "Messages, tool activity, and plans will appear here."),
    emptyTitle: t("acp_empty_title", "Start a conversation"),
    error: t("error", "Error"),
    finish: t("acp_finish", "I've finished"),
    historyGap: t("acp_history_gap", "Earlier messages are unavailable for this session."),
    historyGapTitle: t("acp_history_gap_title", "Partial history"),
    loadMore: t("acp_load_more", "Load more"),
    newChat: t("acp_new_session", "New session"),
    noSessions: t("acp_no_session", "No session yet"),
    openLink: t("acp_open_link", "Open link"),
    openChildSession: t("acp_open_child_session", "Open child session"),
    permission: t("acp_permission", "Permission"),
    pendingInteractions: count => formatLabel(
      "acp_pending_interactions",
      "{count} pending interactions",
      { count },
    ),
    plan: t("acp_plan", "Plan"),
    retry: t("acp_retry", "Retry"),
    removeContext: label => `${t("acp_remove_context", "Remove context")}: ${label}`,
    resource: t("acp_resource", "Resource"),
    scrollToLatest: t("acp_scroll_latest", "Scroll to latest message"),
    send: t("acp_send", "Send"),
    sessionPhase: phase => t(`acp_phase_${phase}`, phase),
    sessionUntitled: t("acp_untitled_session", "Untitled session"),
    sessions: t("acp_session", "Session"),
    stop: t("acp_stop", "Stop"),
    thinking: t("acp_thinking", "Thinking"),
    terminalOutputInActivity: t("acp_terminal_output", "Terminal output is shown in the activity stream."),
    tool: t("acp_tool", "Tool"),
    toolInput: t("acp_tool_input", "Input"),
    toolOutput: t("acp_tool_output", "Output"),
    toolResult: t("acp_tool_result", "tool result"),
    unsupportedContent: type => formatLabel(
      "acp_unsupported_content",
      "Unsupported agent content: {type}",
      { type },
    ),
    unsafeResourceLink: t("acp_unsafe_resource_link", "unsafe resource link"),
    usage: (used, size) => `${formatUsage(used)} / ${formatUsage(size)}`,
    you: t("you", "You"),
    confirmDeleteSession: title => formatLabel(
      "acp_confirm_delete_session",
      "Delete “{title}”?",
      { title },
    ),
    backToSession: title => formatLabel(
      "acp_back_to_session",
      "Back to {title}",
      { title },
    ),
  };
}

function formatLabel(key, fallback, values) {
  let value = String(t(key, fallback));
  for (const [name, replacement] of Object.entries(values)) {
    value = value.replaceAll(`{${name}}`, String(replacement));
  }
  return value;
}

function formatUsage(value) {
  return value < 1_000_000_000_000
    ? value.toLocaleString()
    : value.toExponential(2);
}

function renderControls() {
  const select = /** @type {HTMLSelectElement | null} */ (
    document.querySelector("[data-acp-agent]")
  );
  if (select) {
    select.innerHTML = acpState.agents.length
      ? acpState.agents
          .map(
            agent =>
              `<option value="${esc(agent.id)}" ${agent.id === acpState.agentId ? "selected" : ""}>${esc(agent.title)}</option>`,
          )
          .join("")
      : `<option value="">${esc(t("acp_no_agents", "No agents configured"))}</option>`;
    select.disabled = !acpState.agents.length || acpState.connecting || Boolean(acpState.mounted);
  }
  const connect = /** @type {HTMLButtonElement | null} */ (
    document.querySelector("[data-acp-connect]")
  );
  if (connect) {
    connect.textContent = acpState.mounted
      ? t("acp_disconnect", "Disconnect")
      : t("acp_connect", "Connect");
    connect.disabled = !selectedAgent() || acpState.connecting;
    connect.hidden = !acpState.agents.length;
  }
  const configure = /** @type {HTMLElement | null} */ (
    document.querySelector("[data-acp-configure]")
  );
  if (configure) configure.hidden = Boolean(acpState.agents.length);
  const placeholder = /** @type {HTMLElement | null} */ (
    document.querySelector("[data-acp-placeholder]")
  );
  if (placeholder) placeholder.hidden = Boolean(acpState.mounted);
  renderPromptAssets();
}

function renderPromptAssets() {
  const select = /** @type {HTMLSelectElement | null} */ (
    document.querySelector("[data-acp-prompt-asset]")
  );
  if (select) {
    select.innerHTML = `<option value="">${esc(t("acp_prompt_custom", "Custom prompt"))}</option>${acpState.prompts
      .map(
        prompt =>
          `<option value="${esc(prompt.id)}" ${prompt.id === acpState.promptAssetId ? "selected" : ""}>${esc(prompt.title)}</option>`,
      )
      .join("")}`;
  }
  const use = /** @type {HTMLButtonElement | null} */ (
    document.querySelector("[data-acp-use-prompt]")
  );
  if (use) {
    use.disabled =
      !acpState.mounted ||
      !acpState.prompts.some(prompt => prompt.id === acpState.promptAssetId);
  }
}

function selectedAgent() {
  return acpState.agents.find(agent => agent.id === acpState.agentId) || null;
}

function showNotice(message, error = false) {
  const node = /** @type {HTMLElement | null} */ (
    document.querySelector("[data-acp-notice]")
  );
  if (!node) return;
  node.textContent = message;
  node.classList.toggle("danger", error);
  node.hidden = !message;
}

function errorMessage(error) {
  return error?.message || String(error || t("error", "Error"));
}

function readSavedUi() {
  try {
    const value = JSON.parse(window.localStorage.getItem(storageKey()) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

function restoreUiState() {
  const saved = readSavedUi();
  acpState.agentId = typeof saved.agent_id === "string" ? saved.agent_id : "";
  acpState.promptAssetId =
    typeof saved.prompt_asset_id === "string" ? saved.prompt_asset_id : "";
  acpState.contexts = restoredContexts(saved.contexts);
  persistUiState({ contexts: acpState.contexts });
}

function restoredContexts(value) {
  const contexts = [];
  const ids = new Set();
  for (const context of listValue(value)) {
    if (
      !context ||
      typeof context !== "object" ||
      typeof context.id !== "string" ||
      !context.id ||
      context.id.length > 16 * 1024 ||
      ids.has(context.id) ||
      typeof context.label !== "string" ||
      !context.label ||
      context.label.length > 16 * 1024 ||
      !context.value ||
      typeof context.value !== "object" ||
      Array.isArray(context.value)
    ) {
      continue;
    }
    ids.add(context.id);
    contexts.push({ id: context.id, label: context.label, value: context.value });
    if (contexts.length === 64) break;
  }
  return contexts;
}

function persistUiState(extra = {}) {
  try {
    window.localStorage.setItem(
      storageKey(),
      JSON.stringify({
        ...readSavedUi(),
        agent_id: acpState.agentId,
        prompt_asset_id: acpState.promptAssetId,
        contexts: acpState.contexts,
        ...extra,
      }),
    );
  } catch {
    // Workspace-local UI preference persistence is best effort.
  }
}

function savedSession(agentId) {
  const sessions = readSavedUi().sessions;
  return sessions && typeof sessions[agentId] === "string" ? sessions[agentId] : "";
}

function saveSession(agentId, sessionId) {
  const saved = readSavedUi();
  const sessions = { ...(saved.sessions || {}) };
  if (sessionId) sessions[agentId] = sessionId;
  else delete sessions[agentId];
  persistUiState({ sessions });
}

function forgetSavedSession(agentId) {
  saveSession(agentId, undefined);
}

export {
  acpState,
  closeAcpDrawer,
  connectAcpAgent,
  currentContext,
  disconnectAcpAgent,
  initializeAcp,
  openAcpDrawer,
};
