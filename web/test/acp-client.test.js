import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const calls = [];
const contextRequests = [];
const modelUpdates = [];
const prompts = [];
const backgroundErrorPrefix = "background session failed ";
const oversizedBackgroundError = `${backgroundErrorPrefix}${"😀".repeat(
  8 * 1024,
)}tail`;
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
    return response({
      items: body.contexts.map(context => {
        const source = context.kind === "source";
        return {
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
        };
      }),
    });
  }
  throw new Error(`unexpected request: ${value}`);
};

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"role":"admin","initial_page":"home","workspace_id":"workspace-test","csp_nonce":"test-nonce"}</script>
  <button data-acp-open aria-expanded="false" disabled>Copilot</button>
  <main class="workspace"></main>
  <div data-acp-backdrop hidden></div>
  <aside data-acp-drawer hidden>
    <button data-acp-close>Close</button>
    <select data-acp-agent></select><button data-acp-connect>Connect</button>
    <a href="/config#acp-agents-title" data-acp-configure hidden>Configure</a>
    <div data-acp-placeholder>Connect first</div><div data-acp-chat></div>
    <select data-acp-prompt-asset></select><button data-acp-use-prompt>Use</button>
  </aside>
`, { fetch: fetchStub });

window.localStorage.setItem(
  "peval:workspace-test:acp-client",
  JSON.stringify({ models: { another: "another-model" } }),
);

class SyntheticAcpSocket extends window.EventTarget {
  static instances = [];
  static newRequests = 0;

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
      const sessionId = `session-${++SyntheticAcpSocket.newRequests}`;
      this.#result(message.id, {
        sessionId,
        configOptions: [modelConfig("balanced")],
      });
      return;
    }
    if (message.method === "session/set_config_option") {
      modelUpdates.push({
        sessionId: message.params.sessionId,
        id: message.params.configId,
        value: message.params.value,
      });
      this.#result(message.id, {
        configOptions: [modelConfig(message.params.value)],
      });
      return;
    }
    if (message.method === "session/list") {
      this.#result(message.id, { sessions: [] });
      return;
    }
    if (message.method === "session/prompt") {
      prompts.push(message.params.prompt);
      if (JSON.stringify(message.params.prompt).includes("fail in background")) {
        setTimeout(() => {
          this.#message({
            jsonrpc: "2.0",
            id: message.id,
            error: { code: -32603, message: oversizedBackgroundError },
          });
        }, 30);
        return;
      }
      this.#message({
        jsonrpc: "2.0",
        method: "session/update",
        params: {
          sessionId: message.params.sessionId,
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

function modelConfig(currentValue) {
  return {
    id: "model",
    name: "Model",
    category: "model",
    type: "select",
    currentValue,
    options: [
      { value: "fast", name: "Fast" },
      { value: "balanced", name: "Balanced" },
    ],
  };
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
  const workspaceRefreshes = [];
  workspaceRuntime.setWorkspaceApp({
    invalidate(changes) {
      workspaceRefreshes.push(["invalidate", changes]);
    },
    async navigate(page, options) {
      workspaceRefreshes.push(["navigate", page, options]);
    },
  });
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
  const workspace = document.querySelector(".workspace");
  Object.defineProperties(workspace, {
    offsetWidth: { configurable: true, value: 800 },
    clientWidth: { configurable: true, value: 785 },
  });
  acp.openAcpDrawer(opener);
  assert.equal(
    document.documentElement.style.getPropertyValue(
      "--acp-scrollbar-compensation",
    ),
    "15px",
  );

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
  const modelSelect = host.shadowRoot.querySelector(
    '[role="combobox"][aria-label="Model"]',
  );
  assert.match(modelSelect.textContent, /Balanced/);
  modelSelect.click();
  await waitFor(() =>
    [...host.shadowRoot.querySelectorAll('[role="option"]')]
      .some(option => option.textContent.includes("Fast")),
  );
  const fastOption = [...host.shadowRoot.querySelectorAll('[role="option"]')]
    .find(option => option.textContent.includes("Fast"));
  assert.ok(fastOption);
  fastOption.click();
  await waitFor(() => modelUpdates.length === 1);
  const newSession = [...host.shadowRoot.querySelectorAll("button")].find(button =>
    button.textContent.includes("New session"),
  );
  assert.ok(newSession);
  newSession.click();
  await waitFor(() => SyntheticAcpSocket.newRequests === 2);
  await waitFor(() => modelUpdates.length === 2);
  assert.deepEqual(modelUpdates, [
    { sessionId: "session-1", id: "model", value: "fast" },
    { sessionId: "session-2", id: "model", value: "fast" },
  ]);
  assert.match(
    host.shadowRoot.querySelector('[role="combobox"][aria-label="Model"]')
      .textContent,
    /Fast/,
  );
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
  await waitFor(() => acp.acpState.contexts.length === 2);
  await waitFor(() => addContext.disabled === false);
  addContext.click();
  await waitFor(
    () =>
      host.shadowRoot.querySelectorAll(
        '[data-pretty-aui-slot="composer-context-item"]',
      ).length === 2,
  );
  await waitFor(
    () => host.shadowRoot.querySelectorAll('[data-kind="notice"]').length === 3,
  );
  assert.deepEqual(
    [...host.shadowRoot.querySelectorAll('[data-kind="notice"]')].map(
      row => row.textContent,
    ),
    [
      "Current evaluation context attached",
      "Current evaluation context attached",
      "Evaluation context is already attached",
    ],
  );
  assert.equal(
    host.shadowRoot.querySelector('[data-kind="notice"] button'),
    null,
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
      contexts: [
        { kind: "source", source_key: "source-7", step_id: "4" },
        {
          kind: "dataset_task",
          dataset_id: "bench-v1.0",
          task: "trend-digest-01",
        },
      ],
      embedded_context: true,
    },
  ]);
  assert.equal(prompts[0][0].type, "resource");
  assert.equal(prompts[0][1].type, "resource");
  assert.deepEqual(prompts[0][0]._meta["pretty-aui/context"], {
    version: 1,
    id: "source:source-7:4",
    label: "source-7 · Step 4",
  });
  const envelope = prompts[0][2].text.match(
    /^\n\n<pretty-aui-user-message-v1-([a-f0-9]{32})>\n$/,
  );
  assert.ok(envelope);
  assert.equal(prompts[0][3].text, "Trace the first mistake.");
  assert.equal(
    prompts[0][4].text,
    `\n</pretty-aui-user-message-v1-${envelope[1]}>`,
  );
  await waitFor(() => host.shadowRoot.textContent.includes("Synthetic response."));
  await waitFor(() => workspaceRefreshes.length === 2);
  assert.deepEqual(workspaceRefreshes, [
    ["invalidate", "catalog"],
    ["navigate", "datasets", { focus: false, history: false }],
  ]);
  host.shadowRoot
    .querySelector('[aria-label="Remove context: source-7 · Step 4"]')
    .click();
  await waitFor(
    () =>
      host.shadowRoot.querySelectorAll(
        '[data-pretty-aui-slot="composer-context-item"]',
      ).length === 1,
  );
  await waitFor(
    () => host.shadowRoot.querySelectorAll('[data-kind="notice"]').length === 4,
  );
  assert.deepEqual(
    [...host.shadowRoot.querySelectorAll('[data-kind="notice"]')].map(
      row => row.textContent,
    ),
    [
      "Current evaluation context attached",
      "Current evaluation context attached",
      "Evaluation context is already attached",
      "Evaluation context removed",
    ],
  );
  assert.doesNotMatch(
    host.shadowRoot
      .querySelector('[data-pretty-aui-slot="composer-context"]')
      .textContent,
    /source-7/,
  );
  assert.equal(
    JSON.parse(window.localStorage.getItem("peval:workspace-test:acp-client")).sessions.opencode,
    "session-2",
  );
  assert.deepEqual(
    JSON.parse(window.localStorage.getItem("peval:workspace-test:acp-client")).models,
    { another: "another-model", opencode: "fast" },
  );
  assert.equal(window.localStorage.getItem("peval:other-workspace:acp-client"), null);
  assert.deepEqual(
    JSON.parse(window.localStorage.getItem("peval:workspace-test:acp-client"))
      .contexts.map(context => context.value.kind),
    ["dataset_task"],
  );
  assert.equal(calls.some(path => path.includes("/sessions")), false);

  const controller = acp.acpState.mounted.controller;
  await controller.openSession("session-1");
  await waitFor(
    () =>
      host.shadowRoot.querySelectorAll('[data-kind="notice"]').length === 1 &&
      host.shadowRoot.querySelector('[data-kind="notice"]')?.textContent ===
        "Local agent connected",
  );
  assert.deepEqual(
    [...host.shadowRoot.querySelectorAll('[data-kind="notice"]')].map(
      row => row.textContent,
    ),
    ["Local agent connected"],
  );
  await controller.openSession("session-2");
  const failedTurn = controller.send("fail in background");
  await waitFor(() => prompts.length === 2);
  await controller.newSession();
  await assert.rejects(failedTurn.done, /background session failed/);
  assert.equal(controller.getSnapshot().sessionId, "session-3");
  assert.equal(
    host.shadowRoot.textContent.includes("background session failed"),
    false,
  );
  await controller.openSession("session-2");
  await waitFor(
    () =>
      host.shadowRoot.querySelector(
        '[data-kind="notice"][data-level="error"]',
      )?.textContent?.startsWith("background session failed"),
  );
  const errorNotice = host.shadowRoot.querySelector(
    '[data-kind="notice"][data-level="error"]',
  );
  assert.equal(new TextEncoder().encode(errorNotice.textContent).length <= 16 * 1024, true);
  assert.equal(errorNotice.textContent.endsWith("…"), true);
  assert.equal(
    oversizedBackgroundError.startsWith(errorNotice.textContent.slice(0, -1)),
    true,
  );

  acp.closeAcpDrawer();
  assert.equal(document.querySelector("[data-acp-drawer]").hidden, true);
  assert.equal(
    document.documentElement.style.getPropertyValue(
      "--acp-scrollbar-compensation",
    ),
    "",
  );
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

test("a failed post-turn workspace refresh is reported without an unhandled rejection", async () => {
  const errors = [];
  const unhandled = [];
  const previousConsoleError = console.error;
  const captureUnhandled = error => unhandled.push(error);
  console.error = (...values) => errors.push(values);
  process.on("unhandledRejection", captureUnhandled);
  workspaceRuntime.setWorkspaceApp({
    invalidate() {},
    async navigate() {
      throw new Error("injected workspace refresh failure");
    },
  });
  workspaceRuntime.setWorkspaceSnapshotProvider(() => ({
    context: { page: "home", source_key: "source-7", step_id: "4" },
    dirty: false,
  }));

  try {
    const controller = acp.acpState.mounted.controller;
    await controller.newSession();
    const host = document.querySelector("[data-acp-chat]");
    host.shadowRoot.querySelector('[aria-label="Add context"]').click();
    await waitFor(() =>
      acp.acpState.contexts.some(context => context.value?.kind === "source"),
    );
    const turn = controller.send("refresh failure");
    await turn.done;
    await waitFor(() => errors.length === 1);
    await new Promise(resolve => setImmediate(resolve));

    assert.equal(unhandled.length, 0);
    assert.match(String(errors[0][0]), /workspace refresh.*failed/i);
    assert.match(String(errors[0][1]), /injected workspace refresh failure/);
  } finally {
    process.off("unhandledRejection", captureUnhandled);
    console.error = previousConsoleError;
  }
});

async function waitFor(predicate) {
  const deadline = Date.now() + 2000;
  while (!predicate() && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  assert.equal(predicate(), true, "timed out waiting for ACP UI state");
}
