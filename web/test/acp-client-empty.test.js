import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const jsonResponse = payload => ({
  ok: true,
  status: 200,
  statusText: "OK",
  text: async () => JSON.stringify(payload),
});
const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin","serve_page":"home","workspace_id":"empty-agent-test","sources":[]}</script>
  <button data-acp-open>Copilot</button>
  <div data-acp-backdrop hidden></div>
  <aside data-acp-drawer hidden>
    <button data-acp-close>Close</button>
    <select data-acp-agent></select>
    <button data-acp-connect>Connect</button>
    <a href="/config#acp-agents-title" data-acp-configure hidden>Configure agents</a>
    <span data-acp-protocol></span>
    <select data-acp-session></select><button data-acp-new-session>New</button><button data-acp-session-close>×</button>
    <div data-acp-context-chip><span data-acp-context-label></span></div><button data-acp-context-capture>Attach</button>
    <p data-acp-notice hidden></p><div data-acp-events></div><div data-acp-session-options hidden></div>
    <form data-acp-composer><select data-acp-prompt-asset></select><button data-acp-use-prompt type="button">Use</button><textarea data-acp-prompt></textarea><span data-acp-usage></span><button data-acp-stop type="button">Stop</button><button data-acp-send>Send</button></form>
  </aside>
  <aside id="workspace-report-reader" hidden></aside>
  <main id="comparison"></main><section id="trace"></section><aside id="detail-sidebar"></aside>
`, {
  fetch: async path => jsonResponse(String(path) === "/api/acp/agents"
    ? { agents: [] }
    : { prompts: [] }),
});

const acp = await import("../../src/psycheval/assets/web/modules/acp-client.js");

test.after(() => browser.cleanup());

test("an empty ACP Agent list replaces Connect with the configuration link", async () => {
  await acp.initializeAcp();

  const connect = document.querySelector("[data-acp-connect]");
  const configure = document.querySelector("[data-acp-configure]");
  assert.equal(connect.hidden, true);
  assert.equal(configure.hidden, false);
  assert.equal(configure.getAttribute("href"), "/config#acp-agents-title");
});
