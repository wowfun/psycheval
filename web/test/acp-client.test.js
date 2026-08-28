import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const calls = [];
const SESSION_ONE = "session/1";
const SESSION_ONE_TOKEN = "c2Vzc2lvbi8x";
const SESSION_TWO_TOKEN = "c2Vzc2lvbi0y";
let eventRequest = 0;
let resolveIdlePoll;
let resolveRecoveredPoll;
let resolvePermissionPoll;
const jsonResponse = (payload, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  statusText: status === 200 ? "OK" : "Service Unavailable",
  text: async () => JSON.stringify(payload),
});
const fetchStub = async (path, options = {}) => {
  const value = String(path);
  calls.push({ path: value, body: options.body ? JSON.parse(options.body) : null });
  let payload = {};
  if (value === "/api/acp/agents") {
    payload = { agents: [{ id: "opencode", title: "OpenCode", connected: true, protocol_version: 1 }] };
  } else if (value === "/api/prompts") {
    payload = [{ id: "failure-diagnosis", title: "Failure diagnosis", content: "# Failure diagnosis\n\nTrace the first mistake." }];
  } else if (value.startsWith("/api/acp/agents/opencode/sessions?")) {
    payload = { sessions: [
      { agent_id: "opencode", session_id: SESSION_ONE, title: "Investigation", active_prompt: false, closed: false, loaded: true, revision: 0 },
      { agent_id: "opencode", session_id: "session-2", title: "Needs resume", active_prompt: false, closed: false, loaded: false, revision: 0 },
    ] };
  } else if (value === `/api/acp/agents/opencode/sessions/${SESSION_TWO_TOKEN}` && options.method === "PUT") {
    return jsonResponse({ detail: "resume failed" }, 502);
  } else if (value.includes("/events?")) {
    eventRequest += 1;
    if (eventRequest === 2) {
      return new Promise(resolve => { resolveIdlePoll = resolve; });
    }
    if (eventRequest === 3) return jsonResponse({ error: "temporary outage" }, 503);
    if (eventRequest === 4) {
      return new Promise(resolve => { resolveRecoveredPoll = resolve; });
    }
    if (eventRequest === 5) {
      return new Promise(resolve => { resolvePermissionPoll = resolve; });
    }
    if (eventRequest > 5) return new Promise(() => {});
    payload = {
      next_cursor: 3,
      reset: false,
      session: { agent_id: "opencode", session_id: SESSION_ONE, title: "Investigation", active_prompt: false, closed: false, loaded: true, revision: 3 },
      events: [
        { sequence: 1, type: "message", text: "**Failure cluster** found." },
        { sequence: 2, type: "tool", title: "Read trajectory", status: "completed", raw_input: { source: "source-7" } },
        { sequence: 3, type: "permission", request_id: "91", options: [{ optionId: "allow_once", name: "Allow once" }] },
      ],
    };
  } else if (value === `/api/acp/agents/opencode/sessions/${SESSION_ONE_TOKEN}/permission-responses`) {
    payload = {};
  }
  return jsonResponse(payload);
};

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin","initial_page":"home","workspace_id":"workspace-test","sources":[]}</script>
  <button data-acp-open>Copilot</button>
  <div data-acp-backdrop hidden></div>
  <aside data-acp-drawer hidden>
    <button data-acp-close>Close</button>
    <select data-acp-agent></select><button data-acp-connect>Connect</button><a href="/config#acp-agents-title" data-acp-configure hidden>Configure agents</a><span data-acp-protocol></span>
    <select data-acp-session></select><button data-acp-new-session>New</button><button data-acp-session-close>×</button>
    <div data-acp-context-chip><span data-acp-context-label></span></div><button data-acp-context-capture>Attach</button>
    <p data-acp-notice hidden></p><div data-acp-events></div><div data-acp-session-options hidden></div>
    <form data-acp-composer><select data-acp-prompt-asset></select><button data-acp-use-prompt type="button">Use</button><textarea data-acp-prompt></textarea><span data-acp-usage></span><button data-acp-stop type="button">Stop</button><button data-acp-send>Send</button></form>
  </aside>
  <aside id="workspace-report-reader" hidden></aside>
  <main id="comparison"></main><section id="trace"></section><aside id="detail-sidebar"></aside>
`, { fetch: fetchStub });

const runtime = await import("../../src/psycheval/assets/web/modules/runtime.js");
const acp = await import("../../src/psycheval/assets/web/modules/acp-client.js");
const workspaceRuntime = await import("../../src/psycheval/assets/web/app/workspace-runtime.js");
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test.after(() => browser.cleanup());

test("ACP drawer preserves explicit context, renders protocol events, and restores focus", async () => {
  runtime.state.selectedSourceKey = "source-7";
  runtime.state.selectedStep = { trialKey: "trial-7", stepId: "4" };
  workspaceRuntime.setWorkspaceSnapshotProvider(
    () => ({
      context: { page: "home", source_key: "source-7", step_id: "4" },
      dirty: false,
    }),
  );
  const opener = document.querySelector("[data-acp-open]");
  await acp.initializeAcp();
  assert.equal(document.querySelector("[data-acp-connect]").hidden, false);
  assert.equal(document.querySelector("[data-acp-configure]").hidden, true);
  opener.focus();
  acp.openAcpDrawer(opener);
  document.querySelector("[data-acp-context-capture]").click();
  await tick();
  await tick();

  assert.equal(document.body.classList.contains("acp-drawer-open"), true);
  assert.equal(document.querySelector("[data-acp-protocol]").textContent, "ACP v1");
  assert.match(document.querySelector("[data-acp-context-label]").textContent, /source-7.*4/);
  assert.match(document.querySelector("[data-acp-events]").textContent, /Failure cluster/);
  assert.match(document.querySelector("[data-acp-events]").textContent, /Read trajectory/);
  document.querySelector("[data-acp-use-prompt]").click();
  assert.match(document.querySelector("[data-acp-prompt]").value, /Trace the first mistake/);
  assert.ok(document.querySelector("[data-acp-permission='91'][data-option-id='allow_once']"));

  document.querySelector("[data-acp-permission='91'][data-option-id='allow_once']").click();
  await tick();
  assert.deepEqual(calls.find(call => call.path === `/api/acp/agents/opencode/sessions/${SESSION_ONE_TOKEN}/permission-responses`).body, {
    request_id: "91", option_id: "allow_once", cancelled: false,
  });

  const eventList = document.querySelector("[data-acp-events]");
  const renderedEvent = eventList.firstElementChild;
  const openDetails = eventList.querySelector("details");
  const renderedSessionOption = document.querySelector("[data-acp-session]").firstElementChild;
  openDetails.open = true;
  eventList.scrollTop = 17;
  resolveIdlePoll(jsonResponse({
    next_cursor: 3,
    reset: false,
    session: { agent_id: "opencode", session_id: SESSION_ONE, title: "Investigation", active_prompt: false, closed: false, loaded: true, revision: 3 },
    events: [],
  }));
  await tick();
  assert.equal(eventList.firstElementChild, renderedEvent, "an idle poll preserves rendered event nodes");
  assert.equal(document.querySelector("[data-acp-session]").firstElementChild, renderedSessionOption, "an idle poll preserves session controls");
  assert.equal(openDetails.open, true);
  assert.equal(eventList.scrollTop, 17);
  await new Promise(resolve => setTimeout(resolve, 600));
  assert.ok(eventRequest >= 4, "polling retries after a temporary HTTP failure");
  resolveRecoveredPoll(jsonResponse({
    next_cursor: 0,
    reset: true,
    session: { agent_id: "opencode", session_id: SESSION_ONE, title: "Investigation", active_prompt: false, closed: false, loaded: true, revision: 0 },
    events: [],
  }));
  await tick();
  assert.equal(acp.acpState.revision, 0, "a server reset can return to revision zero");

  resolvePermissionPoll(jsonResponse({
    next_cursor: 4,
    reset: true,
    session: { agent_id: "opencode", session_id: SESSION_ONE, title: "Investigation", active_prompt: false, closed: false, loaded: true, revision: 4 },
    events: [
      { sequence: 3, type: "permission", request_id: "91", options: [{ optionId: "allow_once", name: "Allow once" }] },
      { sequence: 4, type: "permission_result", request_id: "91", option_id: "allow_once", cancelled: false },
    ],
  }));
  await tick();
  const answeredPermissionButtons = Array.from(document.querySelectorAll("[data-acp-permission='91']"));
  assert.ok(answeredPermissionButtons.length > 0);
  assert.ok(answeredPermissionButtons.every(button => button.disabled));
  assert.match(document.querySelector(".acp-event-permission").textContent, /Allow once/);

  const sessionSelect = document.querySelector("[data-acp-session]");
  sessionSelect.value = "session-2";
  sessionSelect.dispatchEvent(new window.Event("change", { bubbles: true }));
  await tick();
  await tick();
  assert.ok(
    calls.some(call => call.path.startsWith(`/api/acp/agents/opencode/sessions/${SESSION_TWO_TOKEN}/events?`)),
    "polling resumes even when loading the selected session fails",
  );

  acp.closeAcpDrawer();
  assert.equal(document.querySelector("[data-acp-drawer]").hidden, true);
  assert.equal(document.activeElement, opener);
});
