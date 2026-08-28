import assert from "node:assert/strict";
import test from "node:test";
import { pathToFileURL } from "node:url";

import { installBrowserDom } from "./support/browser.js";

const MAIN_ENTRY = new URL("../../src/psycheval/assets/web/main.js", import.meta.url);

function workspaceShell() {
  return `
    <section data-workspace-page="datasets" tabindex="-1">
      <main>
        <section id="report-notes"></section>
        <section id="comparison"></section>
        <section id="trace"></section>
      </main>
      <aside id="workspace-views" hidden></aside>
      <aside id="detail-sidebar" hidden></aside>
      <strong data-source-count></strong>
      <span data-source-status></span>
      <section data-harbor-workbench>
        <button data-harbor-reload>Reload</button>
        <input data-harbor-search type="search">
        <span data-harbor-overview-count></span>
        <div data-harbor-overview></div>
        <h2 data-harbor-selected-title></h2>
        <span data-harbor-selected-meta></span>
        <p data-harbor-workbench-status hidden></p>
        <div data-harbor-task-browser>
          <div data-harbor-file-tree></div>
          <strong data-harbor-editor-path></strong>
          <span data-harbor-editor-meta></span>
          <textarea data-harbor-editor disabled></textarea>
        </div>
        <div data-harbor-diagnostics></div>
      </section>
    </section>
    <script type="application/json" id="peval-i18n">{}</script>
    <script type="application/json" id="peval-render-options">
      {"initial_page":"datasets","role":"guest","sources":[]}
    </script>
    <button data-admin-login-open>Login</button>
    <div data-admin-login-dialog hidden>
      <button data-admin-login-close>Close</button>
      <form data-admin-login-form><input name="password" type="password"></form>
    </div>
  `;
}

test("the distributed ESM entrypoint starts a Live Workspace page", async () => {
  const requests = [];
  const browser = installBrowserDom(workspaceShell(), {
    fetch: async input => {
      const url = String(input);
      requests.push(url);
      if (url === "/api/harbor/datasets") {
        return new Response(JSON.stringify({ datasets: [] }));
      }
      throw new Error(`unexpected request: ${url}`);
    },
  });
  try {
    await import(`${pathToFileURL(MAIN_ENTRY.pathname).href}?smoke=${Date.now()}`);
    await new Promise(resolve => setImmediate(resolve));
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(requests, ["/api/harbor/datasets"]);
    assert.equal(document.querySelectorAll("[data-harbor-overview-row]").length, 0);
    document.querySelector("[data-admin-login-open]").click();
    assert.equal(document.querySelector("[data-admin-login-dialog]").hidden, false);
  } finally {
    browser.cleanup();
  }
});
