import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const calls = [];
const contextRequests = [];
const prompts = [];
const response = payload => new Response(JSON.stringify(payload), { status: 200 });
const fetchStub = async (path, options = {}) => {
  const value = String(path);
  calls.push(value);
  if (value === "/api/acp/agents") {
    return response({
      cwd: "/workspace/project",
      agents: [{ id: "opencode", title: "OpenCode", connected: false, connections: 0 }],
    });
  }
  if (value === "/api/prompts") {
    return response([
      {
        id: "failure-diagnosis",
        title: "Failure diagnosis",
        content: "Trace the first mistake.",
      },
    ]);
  }
  if (value === "/api/acp/context-resolutions") {
    const body = JSON.parse(options.body);
    contextRequests.push(body);
    const context = body.context;
    const source = context.kind === "source";
    return response({
      items: [
        {
          id: source
            ? `source:${context.source_key}:${context.step_id || ""}`
            : `dataset:${context.dataset_id}:${context.task}`,
          label: source
            ? `${context.source_key} · Step ${context.step_id}`
            : `${context.dataset_id} / ${context.task}`,
          content: [
            {
              type: "resource",
              resource: {
                uri: source
                  ? `peval://source/${context.source_key}`
                  : `peval://dataset/${context.dataset_id}/${context.task}`,
                mimeType: "application/json",
                text: JSON.stringify({ reference: context }),
              },
            },
          ],
        },
      ],
    });
  }
  throw new Error(`unexpected request: ${value}`);
};

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"role":"admin","initial_page":"home","workspace_id":"workspace-test","csp_nonce":"test-nonce"}</script>
  <button data-acp-open aria-expanded="false" disabled>Copilot</button>
  <div data-acp-backdrop hidden></div>
  <aside data-acp-drawer hidden>
    <button data-acp-close>Close</button>
    <select data-acp-agent></select><button data-acp-connect>Connect</button>
    <a href="/config#acp-agents-title" data-acp-configure hidden>Configure</a>
    <p data-acp-notice hidden></p>
    <div data-acp-placeholder>Connect first</div><div data-acp-chat></div>
    <select data-acp-prompt-asset></select><button data-acp-use-prompt>Use</button>
  </aside>
`, { fetch: fetchStub });

class SyntheticAcpSocket extends window.EventTarget {
  static instances = [];

  constructor(url) {
    super();
    this.url = String(url);
    this.readyState = 0;
    this.ordinal = SyntheticAcpSocket.instances.push(this);
    queueMicrotask(() => {
      if (this.readyState !== 0) return;
      this.readyState = 1;
      this.dispatchEvent(new window.Event("open"));
    });
  }

  send(raw) {
    const messages = JSON.parse(raw);
    for (const message of Array.isArray(messages) ? messages : [messages]) {
      this.#handle(message);
    }
  }

  close() {
    if (this.readyState === 3) return;
    this.readyState = 3;
    queueMicrotask(() => this.dispatchEvent(new window.Event("close")));
  }

  #handle(message) {
    if (message.method === "initialize") {
      this.#result(message.id, {
        protocolVersion: 1,
        agentInfo: { name: "synthetic", title: "Synthetic Agent", version: "1.0" },
        agentCapabilities: {
          loadSession: true,
          promptCapabilities: { embeddedContext: true },
          sessionCapabilities: { list: {}, close: {} },
        },
        authMethods: [],
      });
      return;
    }
    if (message.method === "session/new") {
      this.#result(message.id, {
        sessionId: "session-1",
        modes: { currentModeId: "", availableModes: [] },
      });
      return;
    }
    if (message.method === "session/list") {
      this.#result(message.id, { sessions: [] });
      return;
    }
    if (message.method === "session/prompt") {
      prompts.push(message.params.prompt);
      this.#message({
        jsonrpc: "2.0",
        method: "session/update",
        params: {
          sessionId: "session-1",
          update: {
            sessionUpdate: "agent_message_chunk",
            content: { type: "text", text: "Synthetic response." },
          },
        },
      });
      this.#result(message.id, { stopReason: "end_turn" });
    }
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
globalThis.WebSocket = SyntheticAcpSocket;
window.WebSocket = SyntheticAcpSocket;

const workspaceRuntime = await import("../../src/psycheval/assets/web/app/workspace-runtime.js");
const acp = await import("../../src/psycheval/assets/web/modules/acp-client.js");

test.after(async () => {
  await acp.disconnectAcpAgent();
  browser.cleanup();
  if (previousWebSocket === undefined) delete globalThis.WebSocket;
  else globalThis.WebSocket = previousWebSocket;
});

test("Psycheval composes the vendored controller through its gateway and context seam", async () => {
  let workspaceContext = {
    page: "home",
    source_key: "source-7",
    step_id: "4",
  };
  workspaceRuntime.setWorkspaceSnapshotProvider(() => ({
    context: workspaceContext,
    dirty: false,
  }));
  const opener = document.querySelector("[data-acp-open]");
  assert.equal(opener.disabled, true);
  await acp.initializeAcp();
  assert.equal(opener.disabled, false, "the launcher becomes interactive only after its handler is bound");
  opener.focus();
  acp.openAcpDrawer(opener);

  assert.equal(await acp.connectAcpAgent(), true);
  assert.equal(SyntheticAcpSocket.instances.length, 2, "v1 fallback gets a fresh gateway process");
  assert.equal(
    SyntheticAcpSocket.instances[1].url,
    "ws://127.0.0.1:8765/api/acp/agents/opencode/ws",
  );
  const host = document.querySelector("[data-acp-chat]");
  assert.ok(host.shadowRoot, "pretty-aui owns an open Shadow DOM");
  assert.equal(host.shadowRoot.querySelector("style").nonce, "test-nonce");
  const addContext = host.shadowRoot.querySelector(
    '[aria-label="Add context"]',
  );
  await waitFor(() => addContext.disabled === false);
  addContext.click();
  await waitFor(() => acp.acpState.contexts.length === 1);
  await waitFor(
    () =>
      host.shadowRoot.querySelectorAll(
        '[data-pretty-aui-slot="composer-context-item"]',
      ).length === 1,
  );
  workspaceContext = {
    page: "datasets",
    dataset_id: "bench-v1.0",
    task: "trend-digest-01",
  };
  addContext.click();
  addContext.click();
  await waitFor(
    () =>
      host.shadowRoot.querySelectorAll(
        '[data-pretty-aui-slot="composer-context-item"]',
      ).length === 2,
  );
  assert.match(host.shadowRoot.textContent, /source-7.*Step 4/);
  assert.match(host.shadowRoot.textContent, /bench-v1\.0 \/ trend-digest-01/);
  document.querySelector("[data-acp-use-prompt]").click();
  const textarea = host.shadowRoot.querySelector("textarea");
  assert.equal(textarea.value, "Trace the first mistake.");
  await waitFor(() => !host.shadowRoot.querySelector(".paui-send").disabled);
  host.shadowRoot.querySelector(".paui-send").click();

  await waitFor(() => prompts.length === 1);
  assert.deepEqual(contextRequests, [
    {
      context: { kind: "source", source_key: "source-7", step_id: "4" },
      embedded_context: true,
    },
    {
      context: {
        kind: "dataset_task",
        dataset_id: "bench-v1.0",
        task: "trend-digest-01",
      },
      embedded_context: true,
    },
  ]);
  assert.equal(prompts[0][0].type, "resource");
  assert.equal(prompts[0][1].type, "resource");
  assert.equal(prompts[0].at(-1).text, "Trace the first mistake.");
  await waitFor(() => host.shadowRoot.textContent.includes("Synthetic response."));
  host.shadowRoot
    .querySelector('[aria-label="Remove context: source-7 · Step 4"]')
    .click();
  await waitFor(
    () =>
      host.shadowRoot.querySelectorAll(
        '[data-pretty-aui-slot="composer-context-item"]',
      ).length === 1,
  );
  assert.doesNotMatch(
    host.shadowRoot
      .querySelector('[data-pretty-aui-slot="composer-context"]')
      .textContent,
    /source-7/,
  );
  assert.equal(
    JSON.parse(window.localStorage.getItem("peval:workspace-test:acp-client")).sessions.opencode,
    "session-1",
  );
  assert.deepEqual(
    JSON.parse(window.localStorage.getItem("peval:workspace-test:acp-client"))
      .contexts.map(context => context.value.kind),
    ["dataset_task"],
  );
  assert.equal(calls.some(path => path.includes("/sessions")), false);

  acp.closeAcpDrawer();
  assert.equal(document.querySelector("[data-acp-drawer]").hidden, true);
  assert.equal(document.activeElement, opener);
  assert.ok(acp.acpState.mounted, "closing the drawer keeps background sessions alive");
});

test("prompt asset invalidation refreshes presets without replacing live chat", async () => {
  const mounted = acp.acpState.mounted;
  const socketCount = SyntheticAcpSocket.instances.length;
  const promptRequests = calls.filter(path => path === "/api/prompts").length;

  workspaceRuntime.invalidateWorkspace("prompt-assets");

  await waitFor(
    () => calls.filter(path => path === "/api/prompts").length === promptRequests + 1,
  );
  assert.equal(acp.acpState.mounted, mounted);
  assert.equal(SyntheticAcpSocket.instances.length, socketCount);
  assert.ok(document.querySelector("[data-acp-chat]").shadowRoot);
});

async function waitFor(predicate) {
  const deadline = Date.now() + 2000;
  while (!predicate() && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  assert.equal(predicate(), true, "timed out waiting for ACP UI state");
}
