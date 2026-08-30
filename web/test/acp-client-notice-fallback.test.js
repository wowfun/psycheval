import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const response = payload =>
  new Response(JSON.stringify(payload), { status: 200 });
const browser = installBrowserDom(
  `
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"role":"admin","initial_page":"home","workspace_id":"notice-fallback-test"}</script>
  <button data-acp-open>Copilot</button>
  <div data-acp-backdrop hidden></div>
  <aside data-acp-drawer hidden>
    <button data-acp-close>Close</button>
    <select data-acp-agent></select><button data-acp-connect>Connect</button>
    <a data-acp-configure hidden></a>
    <div class="acp-chat-placeholder" data-acp-placeholder>Connect first</div>
    <div data-acp-chat></div>
    <select data-acp-prompt-asset></select><button data-acp-use-prompt>Use</button>
  </aside>
`,
  {
    fetch: async path => {
      if (String(path) === "/api/acp/agents") {
        return response({
          cwd: "/workspace",
          agents: [{ id: "broken", title: "Broken Agent" }],
        });
      }
      if (String(path) === "/api/prompts") return response([]);
      throw new Error(`unexpected request: ${path}`);
    },
  },
);

class FailingAcpSocket extends window.EventTarget {
  constructor() {
    super();
    this.readyState = 0;
    queueMicrotask(() => {
      this.readyState = 1;
      this.dispatchEvent(new window.Event("open"));
    });
  }

  send() {
    queueMicrotask(() => this.close());
  }

  close() {
    if (this.readyState === 3) return;
    this.readyState = 3;
    queueMicrotask(() => this.dispatchEvent(new window.Event("close")));
  }
}

const previousWebSocket = globalThis.WebSocket;
globalThis.WebSocket = FailingAcpSocket;
window.WebSocket = FailingAcpSocket;

const acp = await import("../../src/psycheval/assets/web/modules/acp-client.js");

test.after(async () => {
  await acp.disconnectAcpAgent();
  browser.cleanup();
  if (previousWebSocket === undefined) delete globalThis.WebSocket;
  else globalThis.WebSocket = previousWebSocket;
});

test("an unmounted connection failure uses only the chat placeholder", async () => {
  await acp.initializeAcp();

  assert.equal(await acp.connectAcpAgent(), false);
  const placeholder = document.querySelector("[data-acp-placeholder]");
  assert.equal(acp.acpState.mounted, null);
  assert.equal(document.querySelector("[data-acp-notice]"), null);
  assert.equal(placeholder.getAttribute("role"), "alert");
  assert.equal(placeholder.classList.contains("danger"), true);
  assert.notEqual(placeholder.textContent, "Connect first");

  const retry = acp.connectAcpAgent();
  assert.equal(placeholder.getAttribute("role"), null);
  assert.equal(placeholder.classList.contains("danger"), false);
  assert.equal(
    placeholder.textContent,
    "Connect an agent and open a session to begin.",
  );
  assert.equal(await retry, false);
});
