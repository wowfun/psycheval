import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const response = (payload, status = 200) => new Response(JSON.stringify(payload), {
  status,
  headers: { "Content-Type": status >= 400 ? "application/problem+json" : "application/json" },
});

test("Reports page retries initialization after a transient first activation failure", async () => {
  let attempts = 0;
  let reportRequests = 0;
  const browser = installBrowserDom(`
    <script type="application/json" id="peval-i18n">{}</script>
    <script type="application/json" id="peval-render-options">{"role":"guest"}</script>
    <section data-workspace-page="reports">
      <div data-report-manager>
        <button data-report-manager-reload>Reload</button>
        <p data-report-manager-status hidden></p>
        <input type="search" data-evaluation-report-search>
        <div data-evaluation-report-inventory></div>
        <span data-evaluation-report-count></span>
        <div data-evaluation-report-pagination></div>
        <div data-report-inventory></div>
        <span data-report-count></span>
        <label data-report-page-search-control hidden><input type="search" data-report-page-search></label>
        <div data-report-bindings></div>
      </div>
    </section>
    <aside id="workspace-report-reader" hidden></aside>
  `, {
    fetch: async path => {
      const value = String(path);
      if (value === "/api/reports") {
        reportRequests += 1;
        return response([{
          report_id: "report-1",
          report_ref: "package:report-1",
          filename: "imported.md",
          format: "markdown",
          source_keys: [],
        }]);
      }
      assert.match(value, /^\/api\/evaluation-reports\?/);
      attempts += 1;
      if (attempts === 1) return response({ detail: "temporary failure" }, 503);
      return response({
        page: 1,
        page_size: 100,
        total: 1,
        items: [{
          report_ref: "analysis:recovered",
          title: "Recovered evaluation",
          filename: "analysis.md",
          source_keys: ["source-1"],
          primary_source_key: "source-1",
          source_label: "Recovered source",
        }],
      });
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
    assert.match(document.querySelector("[data-evaluation-report-inventory]").textContent, /Recovered evaluation/);
    assert.ok(document.querySelector('[data-report-page-preview="package:report-1"]'));
    document.querySelector('[data-evaluation-report-select="analysis:recovered"]').click();
    assert.deepEqual(adapter.snapshot().context, {
      page: "reports",
      report_ref: "analysis:recovered",
      report_name: "Recovered evaluation",
    });

    const reportsBeforeInvalidation = reportRequests;
    await adapter.activate(new Set(["catalog"]));
    assert.equal(attempts, 3);
    assert.equal(reportRequests, reportsBeforeInvalidation);

    await adapter.activate(new Set(["reports"]));
    assert.equal(attempts, 3);
    assert.equal(reportRequests, reportsBeforeInvalidation + 1);
  } finally {
    browser.cleanup();
  }
});
