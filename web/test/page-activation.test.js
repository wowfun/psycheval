import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";
import { reportPageHtml, response, report, pageOf, deferred } from "./support/report-library.js";

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
    const signal = new AbortController().signal;
    await assert.rejects(adapter.activate(new Set(), "", signal), /temporary failure/);
    await adapter.activate(new Set(), "", signal);
    assert.match(document.querySelector("[data-report-inventory]").textContent, /recovered/);
    document.querySelector("[data-report-select]").click();
    assert.deepEqual(adapter.snapshot().context, { page: "reports", report_ref: "analysis:recovered", report_name: "recovered.md" });
    assert.equal(document.querySelector("[data-report-import]"), null);
    document.querySelector('[data-report-tab="associations"]').click();
    assert.equal(document.querySelector("[data-binding-picker]"), null);
    for (const domain of ["catalog", "reports", "dataset-registry", "jobs"]) await adapter.activate(new Set([domain]), "", signal);
    assert.equal(attempts, 6);
  } finally { browser.cleanup(); }
});

test("a detail selected while restoring Reports supersedes the requested object", async () => {
  const rows = [report("requested"), report("clicked")];
  let pending;
  const details = [];
  const browser = installBrowserDom(reportPageHtml, { fetch: async path => {
    if (String(path).startsWith("/api/report-library?")) return pending ? pending.promise : response(pageOf(rows));
    details.push(String(path)); return response(rows[0]);
  } });
  try {
    const { createReportsPage } = await import("../../src/psycheval/assets/web/pages/reports-page.js");
    const manager = await import("../../src/psycheval/assets/web/modules/report-manager-page.js");
    const { decodeWorkspaceLocation } = await import("../../src/psycheval/assets/web/app/workspace-location.js");
    const adapter = createReportsPage({});
    const signal = new AbortController().signal;
    await adapter.activate(new Set(), "", signal);
    details.length = 0;
    adapter.restoreLocation(decodeWorkspaceLocation("reports", new URL("http://localhost/reports?report=package:requested")), signal);
    pending = deferred();
    const loading = adapter.activate(new Set(), "", signal);
    manager.openReportPreview("package:clicked");
    pending.resolve(response(pageOf(rows))); await loading;
    assert.equal(adapter.captureLocation().object.report, "package:clicked");
    assert.deepEqual(details, []);
  } finally { browser.cleanup(); }
});
