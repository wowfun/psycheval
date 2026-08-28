import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test("locale and logout failures restore controls and surface the server error", async () => {
  const calls = [];
  const browser = installBrowserDom(`
    <script type="application/json" id="peval-i18n">{}</script>
    <script type="application/json" id="peval-render-options">{"role":"admin","authentication_enabled":true}</script>
    <header class="workspace-header">
      <div class="workspace-utilities">
        <p data-global-shell-status role="status" hidden></p>
        <select data-locale-select>
          <option value="en" selected>English</option>
          <option value="zh-CN">中文</option>
        </select>
        <button data-admin-logout>Log out</button>
      </div>
    </header>
  `, {
    fetch: async (path, options = {}) => {
      calls.push({ path: String(path), options });
      if (String(path) === "/api/config" && options.method === "GET") {
        return new Response("{}", { status: 200, headers: { ETag: '"config-1"' } });
      }
      if (String(path) === "/api/config") {
        return new Response('{"detail":"configuration changed elsewhere"}', {
          status: 412,
          headers: { "Content-Type": "application/problem+json" },
        });
      }
      return new Response('{"detail":"logout unavailable"}', {
        status: 503,
        headers: { "Content-Type": "application/problem+json" },
      });
    },
  });
  try {
    const { initializeGlobalShell } = await import(
      "../../src/psycheval/assets/web/modules/global-shell.js"
    );
    initializeGlobalShell();

    const select = document.querySelector("[data-locale-select]");
    select.value = "zh-CN";
    select.dispatchEvent(new window.Event("change", { bubbles: true }));
    await tick();
    await tick();

    const status = document.querySelector("[data-global-shell-status]");
    assert.equal(select.value, "en");
    assert.equal(select.disabled, false);
    assert.equal(status.hidden, false);
    assert.match(status.textContent, /configuration changed elsewhere/);

    const logout = document.querySelector("[data-admin-logout]");
    logout.click();
    await tick();
    assert.equal(logout.disabled, false);
    assert.match(status.textContent, /logout unavailable/);
    assert.deepEqual(calls.map(call => call.path), [
      "/api/config",
      "/api/config",
      "/api/session",
    ]);
  } finally {
    browser.cleanup();
  }
});
