import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

test("Workspace navigation closes the global ACP drawer", async () => {
  const browser = installBrowserDom(`
    <script type="application/json" id="peval-i18n">{}</script>
    <script type="application/json" id="peval-render-options">{"role":"admin"}</script>
    <button data-acp-open aria-expanded="false">ACP</button>
    <div data-acp-backdrop hidden></div>
    <aside data-acp-drawer hidden><textarea data-acp-prompt></textarea></aside>
  `, {
    fetch: async path => {
      if (String(path) === "/api/acp/agents") {
        return new Response('{"agents":[]}', { status: 200 });
      }
      if (String(path) === "/api/prompts") return new Response("[]", { status: 200 });
      throw new Error(`unexpected request: ${path}`);
    },
  });
  try {
    const shell = await import("../../src/psycheval/assets/web/modules/global-shell.js");
    const { openAcpDrawer } = await import("../../src/psycheval/assets/web/modules/acp-client.js");
    shell.initializeGlobalShell();
    await new Promise(resolve => setTimeout(resolve, 0));
    await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(openAcpDrawer(), true);
    assert.equal(document.querySelector("[data-acp-drawer]").hidden, false);

    window.dispatchEvent(new window.CustomEvent("peval:workspace-navigate"));

    assert.equal(document.querySelector("[data-acp-drawer]").hidden, true);
    assert.equal(document.querySelector("[data-acp-backdrop]").hidden, true);
    assert.equal(document.body.classList.contains("acp-drawer-open"), false);
  } finally {
    browser.cleanup();
  }
});
