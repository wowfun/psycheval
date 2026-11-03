// @ts-check

import {
  createWebSocketConnector,
  mountChat,
} from "../vendor/pretty-aui/pretty-aui.js";
import {
  refreshWorkspace,
  snapshotWorkspace,
  subscribeWorkspaceInvalidation,
} from "../app/workspace-runtime.js";
import { chooseReferences } from "./acp-references.js";
import { serveApi } from "./http.js";
import { RENDER_OPTIONS, adminMode, esc, listValue, t } from "./shared.js";

const MAX_MODEL_PREFERENCE_LENGTH = 16 * 1024;
const MAX_NOTICE_LENGTH = 16 * 1024;

const acpState = {
  initialized: false,
  unsubscribeInvalidation: null,
  scrollbarObserver: null,
  agents: [],
  cwd: "",
  agentId: "",
  mounted: null,
  unsubscribeController: null,
  maxMessageBytes: undefined,
  prompts: [],
  opener: null,
  connecting: false,
  mountGeneration: 0,
};

function drawer() {
  return /** @type {HTMLElement | null} */ (
    document.querySelector("[data-acp-drawer]")
  );
}

function workspaceScrollbarWidth() {
  const workspace = /** @type {HTMLElement | null} */ (
    document.querySelector(".workspace")
  );
  if (!workspace) return 0;
  return Math.max(0, workspace.offsetWidth - workspace.clientWidth);
}

function syncScrollbarCompensation() {
  if (!document.body.classList.contains("acp-drawer-open")) return;
  document.documentElement.style.setProperty(
    "--acp-scrollbar-compensation",
    `${workspaceScrollbarWidth()}px`,
  );
}

function startScrollbarCompensation() {
  stopScrollbarCompensation();
  syncScrollbarCompensation();
  const workspace = document.querySelector(".workspace");
  if (!workspace || typeof window.ResizeObserver !== "function") return;
  acpState.scrollbarObserver = new window.ResizeObserver(
    syncScrollbarCompensation,
  );
  acpState.scrollbarObserver.observe(workspace);
}

function stopScrollbarCompensation() {
  acpState.scrollbarObserver?.disconnect();
  acpState.scrollbarObserver = null;
  document.documentElement.style.removeProperty(
    "--acp-scrollbar-compensation",
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
  acpState.maxMessageBytes = agentPayload?.max_message_bytes;
  acpState.cwd = typeof agentPayload?.cwd === "string" ? agentPayload.cwd : "";
  acpState.agents = listValue(agentPayload?.agents);
  if (!acpState.agents.some(agent => agent.id === acpState.agentId)) {
    acpState.agentId = acpState.agents[0]?.id || "";
  }
}

function applyPromptCatalog(promptPayload) {
  acpState.prompts = listValue(promptPayload);
}

async function refreshPromptCatalog() {
  if (!acpState.initialized) return;
  try {
    applyPromptCatalog(await serveApi("/api/prompts"));
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
    if (acpState.mounted?.controller.getSnapshot().phase === "error") void reconnectAcpAgent();
    else if (acpState.mounted) void disconnectAcpAgent();
    else void connectAcpAgent();
  });
  const preventFileNavigation = event => {
    if (event.dataTransfer?.types.includes("Files")) event.preventDefault();
  };
  document.addEventListener("dragover", preventFileNavigation);
  document.addEventListener("drop", preventFileNavigation);

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
  startScrollbarCompensation();
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
  stopScrollbarCompensation();
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
  clearPlaceholderError();
  acpState.connecting = true;
  renderControls();

  const mounted = mountChat(host, {
    options: {
      connector: createWebSocketConnector(websocketUrl(agentId), {
        cookies: "include",
        maxMessageBytes: acpState.maxMessageBytes,
      }),
      protocol: "auto",
      session: { cwd: acpState.cwd },
      initialSession: savedSessionId
        ? { type: "open", sessionId: savedSessionId }
        : { type: "new" },
      newSessionMode: "plan",
      modelPreference: {
        get: () => savedModel(agentId),
        set: value => saveModel(agentId, value),
      },
      composerActions,
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
    let phase = mounted.controller.getSnapshot().phase;
    acpState.unsubscribeController = mounted.controller.subscribe(() => {
      if (generation !== acpState.mountGeneration || acpState.mounted !== mounted) return;
      const next = mounted.controller.getSnapshot().phase;
      if (next === phase) return;
      phase = next;
      renderControls();
    });
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

async function reconnectAcpAgent() {
  const mounted = acpState.mounted;
  if (!mounted || acpState.connecting) return false;
  acpState.connecting = true;
  renderControls();
  try { await mounted.controller.reconnect(); return true; }
  catch (error) { showNotice(errorMessage(error), true); return false; }
  finally { acpState.connecting = false; renderControls(); }
}

async function disconnectAcpAgent(options = {}) {
  const mounted = acpState.mounted;
  ++acpState.mountGeneration;
  acpState.unsubscribeController?.();
  acpState.unsubscribeController = null;
  acpState.mounted = null;
  acpState.connecting = false;
  if (mounted) await mounted.unmount();
  if (options.persist !== false) persistUiState({ auto_connect: false });
  clearPlaceholderError();
  renderControls();
  return Boolean(mounted);
}

async function releaseMounted(mounted) {
  if (acpState.mounted === mounted) {
    acpState.unsubscribeController?.();
    acpState.unsubscribeController = null;
    acpState.mounted = null;
  }
  acpState.connecting = false;
  await mounted.unmount();
}

function handleChatEvent(event, agentId, generation) {
  if (generation !== acpState.mountGeneration) return;
  if (event.type === "session_changed") {
    saveSession(agentId, event.sessionId);
    return;
  }
  if (event.type === "turn_completed") {
    void refreshWorkspace("catalog").catch(error => {
      console.error("peval: workspace refresh after ACP turn failed", error);
    });
    return;
  }
  if (event.type === "error") {
    renderControls();
    showNotice(
      event.error?.message || t("error", "Error"),
      true,
      event.sessionId,
    );
  }
}

function currentReference() {
  const context = snapshotWorkspace().context || {};
  if ((context.page === "home" || context.page === "reports") && context.report_ref) {
    return { kind: "report", report_ref: context.report_ref };
  }
  if (context.page === "home" && context.source_key) {
    return { kind: "source", source_key: context.source_key,
      ...(context.trajectory_id ? { trajectory_id: context.trajectory_id } : {}),
      ...(context.step_id && context.trajectory_id ? { step_id: context.step_id } : {}),
    };
  }
  if (context.page === "datasets" && context.dataset_id && context.task) {
    return { kind: "dataset_task", dataset_id: context.dataset_id, task: context.task };
  }
  return null;
}

function composerActions() {
  const reference = currentReference();
  const languages = document.documentElement.lang.toLowerCase().startsWith("zh") ? ["zh", "en"] : ["en", "zh"];
  return [
    ...(reference ? [{ id: "workbench", label: t("acp_references", "Workbench references"), run: async ({ signal }) => {
      const identity = JSON.stringify(reference);
      const payload = await serveApi("/api/acp/reference-candidates", { method: "POST", body: { reference }, signal });
      if (identity !== JSON.stringify(currentReference()) || signal.aborted) return undefined;
      const text = await chooseReferences(listValue(payload?.items), signal);
      return identity === JSON.stringify(currentReference()) ? text : undefined;
    } }] : []),
    { id: "prompts", label: t("acp_prompts", "Prompt templates"), children: languages.map(language => ({
      id: `prompts:${language}`, label: language === "zh" ? "中文" : "English",
      children: acpState.prompts.filter(prompt => String(prompt.id).endsWith("-zh-cn") === (language === "zh")).map(prompt => ({
        id: `prompt:${prompt.id}`, label: prompt.title,
        run: () => String(prompt.content || ""),
      })),
    })) },
  ];
}

function websocketUrl(agentId) {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${window.location.host}/api/acp/agents/${encodeURIComponent(agentId)}/ws`;
}

function prettyLabels() {
  return {
    composerAdd: t("acp_composer_add", "Add to message"),
    addImages: t("acp_images", "Images"),
    imagesUnsupported: t("acp_images_unsupported", "This Agent does not accept images. Your draft is unchanged."),
    removeImage: name => `${t("acp_remove_image", "Remove image")}: ${name}`,
    recoverDraft: t("acp_recover_draft", "Append undelivered draft"),
    back: t("acp_back", "Back"),
    imageUnavailable: t("acp_image_unavailable", "Image unavailable"),
    imageUnavailableDetails: t("acp_image_unavailable_details", "Image preview released from local memory; Agent history is unchanged."),
    imageError: issue => ({
      count: t("acp_image_error_count", "A message allows at most four images."),
      budget: t("acp_image_error_budget", "Images exceed the remaining 8 MiB base64 budget."),
      type: t("acp_image_error_type", "Image signature and MIME must match PNG, JPEG, WebP or GIF."),
      dimensions: t("acp_image_error_dimensions", "Images must fit 8,000 pixels per edge and 16 million pixels total."),
      decode: t("acp_image_error_decode", "The image could not be read or decoded."),
    })[issue],
    imageBudget: (used, remaining) => `${(used / 1048576).toFixed(2)} / 8 MiB · ${(remaining / 1048576).toFixed(2)} MiB ${t("acp_remaining", "remaining")}`,
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
    commands: t("acp_commands", "Commands"),
    composerPlaceholder: t("acp_prompt_placeholder", "Ask about this evaluation…"),
    contextInjection: t("acp_context_injection", "Context injection"),
    contextSelection: t("acp_context_selection", "Context for next prompt"),
    contextTruncated: total => formatLabel(
      "acp_context_truncated",
      "Context display truncated ({count} characters total).",
      { count: total.toLocaleString() },
    ),
    copied: t("acp_copied", "Copied"),
    copy: t("acp_copy", "Copy"),
    decline: t("acp_decline", "Decline"),
    deleteSession: t("acp_delete_session", "Delete session"),
    emptyDescription: t("acp_empty_description", "Messages, tool activity, and plans will appear here."),
    emptyTitle: t("acp_empty_title", "Start a conversation"),
    error: t("error", "Error"),
    finish: t("acp_finish", "I've finished"),
    historyGap: t("acp_history_gap", "Earlier messages are unavailable for this session."),
    historyGapTitle: t("acp_history_gap_title", "Partial history"),
    loadMore: t("acp_load_more", "Load more"),
    mode: t("acp_mode", "Mode"),
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
    sessionAge: formatSessionAgeLabel,
    sessionActions: title => formatLabel(
      "acp_session_actions",
      "Actions for {title}",
      { title },
    ),
    sessionPhase: phase => t(`acp_phase_${phase}`, phase),
    sessionUntitled: t("acp_untitled_session", "Untitled session"),
    sessions: t("acp_session", "Session"),
    stop: t("acp_stop", "Stop"),
    thinking: t("acp_thinking", "Thinking"),
    terminalOutputInActivity: t("acp_terminal_output", "Terminal output is shown in the activity stream."),
    tool: t("acp_tool", "Tool"),
    toolCollapseLines: t("acp_tool_collapse_lines", "Show less"),
    toolExpandLines: hidden => formatLabel(
      "acp_tool_expand_lines",
      "... more {count} lines",
      { count: hidden.toLocaleString() },
    ),
    toolInput: t("acp_tool_input", "Input"),
    toolNoOutput: t("acp_tool_no_output", "No output"),
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

function formatSessionAgeLabel(value, unit) {
  if (unit === "now") return t("acp_session_age_now", "now");
  const labels = {
    minute: ["acp_session_age_minute", "{count}m"],
    hour: ["acp_session_age_hour", "{count}h"],
    day: ["acp_session_age_day", "{count}d"],
    month: ["acp_session_age_month", "{count}mo"],
    year: ["acp_session_age_year", "{count}y"],
  };
  const [key, fallback] = labels[unit] || ["acp_session_age_now", "now"];
  return formatLabel(key, fallback, { count: value.toLocaleString() });
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
    connect.textContent = acpState.mounted?.controller.getSnapshot().phase === "error"
      ? t("acp_reconnect", "Reconnect")
      : acpState.mounted
      ? t("acp_disconnect", "Disconnect")
      : t("acp_connect", "Connect");
    connect.disabled = !selectedAgent() || acpState.connecting || acpState.mounted?.controller.getSnapshot().phase === "connecting";
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
}

function selectedAgent() {
  return acpState.agents.find(agent => agent.id === acpState.agentId) || null;
}

function showNotice(message, error = false, sessionId = undefined) {
  const text = boundedNoticeText(message);
  if (!text) return false;
  const controller = acpState.mounted?.controller;
  if (controller) {
    try {
      return controller.appendNotice({
        text,
        level: error ? "error" : "info",
        ...(sessionId ? { sessionId } : {}),
      });
    } catch {
      return false;
    }
  }
  if (!error) return false;
  const placeholder = /** @type {HTMLElement | null} */ (
    document.querySelector("[data-acp-placeholder]")
  );
  if (!placeholder) return false;
  placeholder.textContent = text;
  placeholder.classList.add("danger");
  placeholder.setAttribute("role", "alert");
  placeholder.hidden = false;
  return true;
}

function boundedNoticeText(message) {
  const text = String(message || "");
  const encoder = new TextEncoder();
  if (encoder.encode(text).byteLength <= MAX_NOTICE_LENGTH) return text;
  const suffix = "…";
  const budget = MAX_NOTICE_LENGTH - encoder.encode(suffix).byteLength;
  let bytes = 0;
  let end = 0;
  for (const character of text) {
    const next = encoder.encode(character).byteLength;
    if (bytes + next > budget) break;
    bytes += next;
    end += character.length;
  }
  return `${text.slice(0, end)}${suffix}`;
}

function clearPlaceholderError() {
  const placeholder = /** @type {HTMLElement | null} */ (
    document.querySelector("[data-acp-placeholder]")
  );
  if (!placeholder) return;
  placeholder.textContent = t(
    "acp_empty",
    "Connect an agent and open a session to begin.",
  );
  placeholder.classList.remove("danger");
  placeholder.removeAttribute("role");
}

function errorMessage(error) {
  return error?.message || String(error || t("error", "Error"));
}

function readSavedUi(throwOnError = false) {
  try {
    const value = JSON.parse(window.localStorage.getItem(storageKey()) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch (error) {
    if (throwOnError) throw error;
    return {};
  }
}

function restoreUiState() {
  const saved = readSavedUi();
  acpState.agentId = typeof saved.agent_id === "string" ? saved.agent_id : "";
  persistUiState();
}

function persistUiState(extra = {}, throwOnError = false) {
  try {
    const saved = readSavedUi(throwOnError);
    delete saved.contexts;
    delete saved.prompt_asset_id;
    delete saved.prompt_asset_explicit;
    window.localStorage.setItem(
      storageKey(),
      JSON.stringify({
        ...saved,
        agent_id: acpState.agentId,
        ...extra,
      }),
    );
  } catch (error) {
    if (throwOnError) throw error;
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

// Let pretty-aui diagnose model-store failures while keeping the session usable.
function savedModel(agentId) {
  const models = readSavedUi(true).models;
  if (
    !models ||
    typeof models !== "object" ||
    Array.isArray(models) ||
    !Object.hasOwn(models, agentId)
  ) {
    return undefined;
  }
  return validModelPreference(models[agentId]) ? models[agentId] : undefined;
}

function saveModel(agentId, value) {
  if (!validModelPreference(value)) return;
  const saved = readSavedUi(true);
  const existing =
    saved.models && typeof saved.models === "object" && !Array.isArray(saved.models)
      ? saved.models
      : {};
  persistUiState({ models: { ...existing, [agentId]: value } }, true);
}

function validModelPreference(value) {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    new TextEncoder().encode(value).byteLength <= MAX_MODEL_PREFERENCE_LENGTH
  );
}

export {
  acpState,
  closeAcpDrawer,
  connectAcpAgent,
  currentReference,
  composerActions,
  disconnectAcpAgent,
  initializeAcp,
  openAcpDrawer,
};
