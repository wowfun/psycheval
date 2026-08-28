import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const calls = [];
const STALE_SESSION_TOKEN = "c3RhbGUtc2Vzc2lvbg";
const jsonResponse = (payload, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  statusText: status === 404 ? "Not Found" : "OK",
  text: async () => JSON.stringify(payload),
});
const fetchStub = async path => {
  const value = String(path);
  calls.push(value);
  if (value === "/api/acp/agents") {
    return jsonResponse({
      agents: [{ id: "opencode", title: "OpenCode", connected: false }],
    });
  }
  if (value === "/api/prompts") return jsonResponse([]);
  if (value.startsWith(`/api/acp/agents/opencode/sessions/${STALE_SESSION_TOKEN}/events?`)) {
    return jsonResponse({ detail: "unknown ACP session" }, 404);
  }
  if (value.startsWith("/api/acp/agents/opencode/sessions?")) {
    return jsonResponse({ sessions: [] });
  }
  return jsonResponse({});
};

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin","initial_page":"home","workspace_id":"recovery-test","sources":[]}</script>
  <button data-acp-open>Copilot</button>
  <div data-acp-backdrop hidden></div>
  <aside data-acp-drawer hidden>
    <button data-acp-close>Close</button>
    <select data-acp-agent></select><button data-acp-connect>Connect</button><span data-acp-protocol></span>
    <select data-acp-session></select><button data-acp-new-session>New</button><button data-acp-session-close>×</button>
    <div data-acp-context-chip><span data-acp-context-label></span></div><button data-acp-context-capture>Attach</button>
    <p data-acp-notice hidden></p><div data-acp-events></div><div data-acp-session-options hidden></div>
    <form data-acp-composer><select data-acp-prompt-asset></select><button data-acp-use-prompt type="button">Use</button><textarea data-acp-prompt></textarea><span data-acp-usage></span><button data-acp-stop type="button">Stop</button><button data-acp-send>Send</button></form>
  </aside>
  <aside id="workspace-report-reader" hidden></aside>
  <main id="comparison"></main><section id="trace"></section><aside id="detail-sidebar"></aside>
`, { fetch: fetchStub });

window.localStorage.setItem("peval:recovery-test:acp-client", JSON.stringify({
  open: true,
  agent_id: "opencode",
  session_id: "stale-session",
}));

const acp = await import("../../src/psycheval/assets/web/modules/acp-client.js");

test.after(() => browser.cleanup());

test("stale persisted ACP session recovers after one 404 poll", async () => {
  await acp.initializeAcp();
  const deadline = Date.now() + 1000;
  while (!calls.some(path => path.startsWith("/api/acp/agents/opencode/sessions?")) && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 10));
  }

  assert.equal(
    calls.filter(path => path.startsWith(`/api/acp/agents/opencode/sessions/${STALE_SESSION_TOKEN}/events?`)).length,
    1,
  );
  assert.equal(
    calls.filter(path => path.startsWith("/api/acp/agents/opencode/sessions?")).length,
    1,
  );
  assert.equal(acp.acpState.sessionId, "");
  assert.equal(JSON.parse(window.localStorage.getItem("peval:recovery-test:acp-client")).session_id, "");
});
