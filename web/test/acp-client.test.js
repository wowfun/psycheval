import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const calls = [];
const contextRequests = [];
const modelUpdates = [];
const prompts = [];
let referenceGate;
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
      max_message_bytes: 16 * 1024 * 1024,
      agents: [{ id: "opencode", title: "OpenCode", connected: false, connections: 0 }],
    });
  }
  if (value === "/api/prompts") {
    return response([
      {
        id: "evaluation-review",
        title: "Evaluation review",
        content: "Review this evaluation.",
      },
      {
        id: "failure-diagnosis",
        title: "Failure diagnosis",
        content: "Trace the first mistake.",
      },
    ]);
  }
  if (value === "/api/acp/reference-candidates") {
    const body = JSON.parse(options.body);
    contextRequests.push(body);
    if (referenceGate) await referenceGate;
    return response({ items: [{ id: "source", label: "Source", selected: true, text: `source_ref: ${body.reference.source_key}\ntrajectory_id: ${body.reference.trajectory_id}\nstep_id: ${body.reference.step_id}` }] });
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
  </aside>
`, { fetch: fetchStub });

window.localStorage.setItem(
  "peval:workspace-test:acp-client",
  JSON.stringify({ models: { another: "another-model" }, contexts: [{ id: "old" }], prompt_asset_id: "old", prompt_asset_explicit: true }),
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
    if (message.method === "session/load") {
      this.#result(message.id, {configOptions: [modelConfig("balanced")]});
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
      const cancelled = JSON.stringify(message.params.prompt).includes("cancelled terminal");
      this.#result(message.id, { stopReason: cancelled ? "cancelled" : "end_turn" });
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

test("Psycheval appends references through the controller and cleans legacy preferences", async () => {
  const workspaceRefreshes = [];
  workspaceRuntime.setWorkspaceApp({ invalidate(changes) { workspaceRefreshes.push(changes); }, async navigate() {} });
  workspaceRuntime.setWorkspaceSnapshotProvider(() => ({ context: { page: "home", source_key: "source-7", trajectory_id: "child", step_id: "4" }, dirty: false }));
  await acp.initializeAcp();
  await acp.connectAcpAgent();
  const opener = document.querySelector("[data-acp-open]");
  acp.openAcpDrawer(opener);
  const controller = acp.acpState.mounted.controller;
  await controller.ready;
  const host = document.querySelector("[data-acp-chat]");
  await waitFor(() => host.shadowRoot.querySelector("textarea"));
  assert.equal(controller.getSnapshot().contextSelection.canAdd, false);
  assert.equal(host.shadowRoot.querySelectorAll('[aria-label="Add to message"]').length, 1);
  const saved = JSON.parse(window.localStorage.getItem("peval:workspace-test:acp-client"));
  for (const key of ["contexts", "prompt_asset_id", "prompt_asset_explicit"]) assert.equal(key in saved, false);
  assert.equal(saved.models.another, "another-model");
  controller.setDraft("Analyze this.");
  const reference = controller.getComposerActions().find(action => action.id === "workbench");
  const pending = controller.runComposerAction(reference);
  await waitFor(() => document.querySelector(".acp-reference-picker"));
  controller.setDraft("Analyze this. Preserve my later edit.");
  document.querySelector('.acp-reference-picker button[type="submit"]').click();
  assert.equal(await pending, true);
  const text = controller.getSnapshot().draft.text;
  assert.equal(text, "Analyze this. Preserve my later edit.\n\nsource_ref: source-7\ntrajectory_id: child\nstep_id: 4");
  assert.equal(document.querySelector("[data-acp-drawer]").hidden, false);
  await controller.sendDraft().done;
  assert.deepEqual(prompts[0], [{ type: "text", text }]);
  assert.equal(controller.getSnapshot().draft.text, "");
  await controller.send("No repeated references.").done;
  assert.deepEqual(prompts[1], [{ type: "text", text: "No repeated references." }]);
  assert.equal(contextRequests.length, 1);
  assert.ok(workspaceRefreshes.length >= 2);
  acp.closeAcpDrawer();
  assert.ok(acp.acpState.mounted);
});

test("prompt actions append without selecting or sending a default", async () => {
  const controller = acp.acpState.mounted.controller;
  controller.setDraft("existing");
  const promptsMenu = controller.getComposerActions().find(action => action.id === "prompts");
  assert.deepEqual(promptsMenu.children.map(group => group.label), ["English", "中文"]);
  await controller.runComposerAction(promptsMenu.children[0].children[0]);
  assert.equal(controller.getSnapshot().draft.text, "existing\n\nReview this evaluation.");
  assert.equal(prompts.length, 2);
});

test("cancelled terminal turns refresh catalog without hidden context resolution", async () => {
  const refreshes = [];
  workspaceRuntime.setWorkspaceApp({ invalidate(changes) { refreshes.push(changes); }, async navigate() {} });
  const controller = acp.acpState.mounted.controller;
  await controller.send("cancelled terminal").done;
  assert.ok(refreshes.length);
  assert.equal(contextRequests.length, 1);
});

test("background errors remain scoped and bounded", async () => {
  const controller = acp.acpState.mounted.controller;
  const first = controller.getSnapshot().sessionId;
  const turn = controller.send("fail in background");
  await controller.newSession();
  await assert.rejects(turn.done, /background session failed/);
  assert.equal(controller.getSnapshot().activities.some(item => item.type === "notice" && item.level === "error"), false);
  await controller.openSession(first);
  const notice = controller.getSnapshot().activities.find(item => item.type === "notice" && item.level === "error");
  assert.ok(notice);
  assert.ok(new TextEncoder().encode(notice.text).length <= 16 * 1024);
  await controller.newSession();
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
  assert.ok(predicate(), "timed out waiting for ACP UI state");
}

for (const during of ["fetch", "picker"]) test(`navigating during reference ${during} never appends stale text`, async () => {
  const controller = acp.acpState.mounted.controller;
  let context = {page: "home", source_key: "source-old"};
  workspaceRuntime.setWorkspaceSnapshotProvider(() => ({context, dirty:false}));
  controller.setDraft("keep navigation draft");
  let release;
  if (during === "fetch") referenceGate = new Promise(resolve => { release = resolve; });
  try {
    const action = controller.getComposerActions().find(item => item.id === "workbench");
    const pending = controller.runComposerAction(action);
    if (during === "picker") await waitFor(() => document.querySelector(".acp-reference-picker"));
    context = {page: "datasets", dataset_id: "new", task: "new"};
    if (during === "fetch") release();
    else document.querySelector('.acp-reference-picker button[type="submit"]').click();
    assert.equal(await pending, false);
    assert.equal(controller.getSnapshot().draft.text, "keep navigation draft");
    assert.equal(document.querySelector(".acp-reference-picker"), null);
  } finally { release?.(); referenceGate = undefined; }
});

test("session switch cancels a suspended picker without touching either draft", async () => {
  const {openModalSurface, closeModalSurface} = await import("../../src/psycheval/assets/web/modules/modal-surfaces.js");
  const controller = acp.acpState.mounted.controller;
  const oldSession = controller.getSnapshot().sessionId;
  controller.setDraft("old session draft");
  const pending = controller.runComposerAction(controller.getComposerActions().find(item => item.id === "workbench"));
  await waitFor(() => document.querySelector(".acp-reference-picker"));
  const newer = document.createElement("div");
  newer.setAttribute("aria-modal", "true"); newer.hidden = true; document.body.append(newer);
  openModalSurface(newer);
  try {
    await controller.newSession();
    controller.setDraft("new session draft");
    assert.equal(document.querySelector(".acp-reference-picker"), null);
    assert.equal(await pending, false);
    assert.equal(controller.getSnapshot().draft.text, "new session draft");
    await controller.openSession(oldSession);
    assert.equal(controller.getSnapshot().draft.text, "old session draft");
  } finally { closeModalSurface(newer); newer.remove(); }
});

test("vendored Retry updates the host connection button and releases its subscription", async () => {
  const mounted = acp.acpState.mounted;
  const controller = mounted.controller;
  const connect = document.querySelector("[data-acp-connect]");
  SyntheticAcpSocket.instances.at(-1).close();
  await waitFor(() => controller.getSnapshot().phase === "error");
  assert.equal(connect.textContent, "Reconnect");
  const chat = document.querySelector("[data-acp-chat]");
  const retry = () => [...chat.shadowRoot.querySelectorAll("button")].find(button => button.textContent === "Retry");
  await waitFor(retry);
  retry().click();
  await waitFor(() => controller.getSnapshot().phase === "idle");
  assert.equal(connect.textContent, "Disconnect");
  assert.equal(connect.disabled, false);
  assert.equal(acp.acpState.mounted, mounted);
  connect.click();
  await waitFor(() => acp.acpState.mounted === null);
  assert.equal(acp.acpState.unsubscribeController, null);
});
