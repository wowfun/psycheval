import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";
import { reportPageHtml, response, report, pageOf } from "./support/report-library.js";

test("Reports initialization retries failures and every owning domain refreshes the unified query", async () => {
  let attempts = 0;
  const browser = installBrowserDom(reportPageHtml.replace('"role":"admin"', '"role":"guest"'), { fetch: async path => {
    assert.match(String(path), /^\/api\/report-library\?/);
    if (++attempts === 1) return response({ detail: "temporary failure" }, 503);
    return response(pageOf([report("recovered", [], "evaluation")]));
  } });
  try {
    const { createReportsPage } = await import("../../src/psycheval/assets/web/pages/reports-page.js");
    const adapter = createReportsPage({});
    await assert.rejects(adapter.activate(new Set()), /temporary failure/);
    await adapter.activate(new Set());
    assert.match(document.querySelector("[data-report-inventory]").textContent, /recovered/);
    document.querySelector("[data-report-select]").click();
    assert.deepEqual(adapter.snapshot().context, { page: "reports", report_ref: "analysis:recovered", report_name: "recovered.md" });
    assert.equal(document.querySelector("[data-report-import]"), null);
    document.querySelector('[data-report-tab="associations"]').click();
    assert.equal(document.querySelector("[data-binding-picker]"), null);
    for (const domain of ["catalog", "reports", "dataset-registry", "jobs"]) await adapter.activate(new Set([domain]));
    assert.equal(attempts, 6);
  } finally { browser.cleanup(); }
});
