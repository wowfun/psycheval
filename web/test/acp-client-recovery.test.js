import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const calls = [];
const response = payload => new Response(JSON.stringify(payload), { status: 200 });
const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"role":"admin","initial_page":"home","workspace_id":"ownership-test","csp_nonce":"test-nonce"}</script>
  <button data-acp-open>Copilot</button>
  <div data-acp-backdrop hidden></div>
  <aside data-acp-drawer hidden>
    <button data-acp-close>Close</button>
    <select data-acp-agent></select><button data-acp-connect>Connect</button>
    <a data-acp-configure hidden></a>
    <p data-acp-notice hidden></p>
    <div data-acp-placeholder></div><div data-acp-chat></div>
    <select data-acp-prompt-asset></select><button data-acp-use-prompt>Use</button>
  </aside>
`, {
  fetch: async path => {
    calls.push(String(path));
    if (String(path) === "/api/acp/agents") {
      return response({ cwd: "/workspace", agents: [{ id: "opencode", title: "OpenCode" }] });
    }
    if (String(path) === "/api/prompts") return response([]);
    throw new Error(`unexpected request: ${path}`);
  },
});

window.localStorage.setItem(
  "peval:ownership-test:acp-client",
  JSON.stringify({
    agent_id: "opencode",
    sessions: { opencode: "missing-session" },
    contexts: [
      {
        id: "source:source-7:4",
        label: "source-7 · Step 4",
        value: { kind: "source", source_key: "source-7", step_id: "4" },
      },
      {
        id: "source:source-7:4",
        label: "duplicate",
        value: { kind: "source", source_key: "source-7", step_id: "4" },
      },
      { id: "", label: "invalid", value: { kind: "source" } },
    ],
  }),
);

class StaleSessionSocket extends window.EventTarget {
  static instances = [];
  static loadRequests = 0;
  static newRequests = 0;

  constructor() {
    super();
    this.readyState = 0;
    StaleSessionSocket.instances.push(this);
    queueMicrotask(() => {
      this.readyState = 1;
      this.dispatchEvent(new window.Event("open"));
    });
  }

  send(raw) {
    const messages = JSON.parse(raw);
    for (const message of Array.isArray(messages) ? messages : [messages]) {
      if (message.method === "initialize") {
        this.#result(message.id, {
          protocolVersion: 1,
          agentInfo: { name: "synthetic", version: "1" },
          agentCapabilities: {
            loadSession: true,
            promptCapabilities: {},
            sessionCapabilities: { load: {} },
          },
          authMethods: [],
        });
      } else if (message.method === "session/load") {
        StaleSessionSocket.loadRequests += 1;
        this.#message({
          jsonrpc: "2.0",
          id: message.id,
          error: { code: -32603, message: "saved session is missing" },
        });
      } else if (message.method === "session/new") {
        StaleSessionSocket.newRequests += 1;
        this.#result(message.id, {
          sessionId: "fresh-session",
          modes: { currentModeId: "", availableModes: [] },
        });
      }
    }
  }

  close() {
    if (this.readyState === 3) return;
    this.readyState = 3;
    queueMicrotask(() => this.dispatchEvent(new window.Event("close")));
  }

  #result(id, result) {
    this.#message({ jsonrpc: "2.0", id, result });
  }

  #message(value) {
    queueMicrotask(() => {
      if (this.readyState !== 1) return;
      this.dispatchEvent(
        new window.MessageEvent("message", { data: JSON.stringify(value) }),
      );
    });
  }
}

const previousWebSocket = globalThis.WebSocket;
globalThis.WebSocket = StaleSessionSocket;
window.WebSocket = StaleSessionSocket;

const acp = await import("../../src/psycheval/assets/web/modules/acp-client.js");

test.after(async () => {
  await acp.disconnectAcpAgent();
  browser.cleanup();
  if (previousWebSocket === undefined) delete globalThis.WebSocket;
  else globalThis.WebSocket = previousWebSocket;
});

test("the host restores only bounded context references and never eager-loads content", async () => {
  await acp.initializeAcp();

  assert.deepEqual(calls, ["/api/acp/agents", "/api/prompts"]);
  assert.deepEqual(acp.acpState.contexts, [
    {
      id: "source:source-7:4",
      label: "source-7 · Step 4",
      value: { kind: "source", source_key: "source-7", step_id: "4" },
    },
  ]);
  const saved = JSON.parse(window.localStorage.getItem("peval:ownership-test:acp-client"));
  assert.deepEqual(saved.contexts, acp.acpState.contexts);
  assert.equal(calls.some(path => path.includes("/sessions")), false);
});

test("a structured stale-session rejection retries once with a fresh session", async () => {
  assert.equal(await acp.connectAcpAgent(), true);
  assert.equal(StaleSessionSocket.loadRequests, 1);
  assert.equal(StaleSessionSocket.newRequests, 1);
  const saved = JSON.parse(
    window.localStorage.getItem("peval:ownership-test:acp-client"),
  );
  assert.equal(saved.sessions.opencode, "fresh-session");
  assert.ok(acp.acpState.mounted);
});
