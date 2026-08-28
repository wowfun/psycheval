import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const response = (payload, status = 200) => new Response(JSON.stringify(payload), {
  status,
  headers: { "Content-Type": status >= 400 ? "application/problem+json" : "application/json" },
});

test("Reports page retries initialization after a transient first activation failure", async () => {
  let attempts = 0;
  const browser = installBrowserDom(`
    <script type="application/json" id="peval-i18n">{}</script>
    <script type="application/json" id="peval-render-options">{"role":"guest"}</script>
    <section data-workspace-page="reports">
      <div data-report-manager>
        <button data-report-manager-reload>Reload</button>
        <p data-report-manager-status hidden></p>
        <div data-report-inventory></div>
        <span data-report-count></span>
        <label data-report-page-search-control hidden><input type="search" data-report-page-search></label>
        <div data-report-bindings></div>
      </div>
    </section>
  `, {
    fetch: async path => {
      assert.equal(String(path), "/api/reports");
      attempts += 1;
      if (attempts === 1) {
        return response({ detail: "temporary failure" }, 503);
      }
      return response([{
        report_id: "report-1",
        filename: "recovered.md",
        format: "markdown",
        source_keys: [],
      }]);
    },
  });
  try {
    const { createReportsPage } = await import(
      "../../src/psycheval/assets/web/pages/reports-page.js"
    );
    const adapter = createReportsPage({});

    await assert.rejects(adapter.activate(new Set()), /temporary failure/);
    await adapter.activate(new Set());

    assert.equal(attempts, 2);
    assert.match(document.querySelector("[data-report-inventory]").textContent, /recovered\.md/);
  } finally {
    browser.cleanup();
  }
});
