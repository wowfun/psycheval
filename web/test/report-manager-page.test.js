import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";
import { reportPageHtml, response, target, report, pageOf, tick, deferred } from "./support/report-library.js";

const requests = [];
let reports = [report("first", [target("session", "session-1")]), report("canonical", [], "evaluation")];
let failSave = false;
let deleting;
const browser = installBrowserDom(reportPageHtml, { fetch: async (path, options = {}) => {
  requests.push({ path: String(path), options });
  const url = new URL(path, "http://localhost");
  if (url.pathname === "/api/report-library/targets") return response(pageOf([target(url.searchParams.get("kind"), "one")]));
  if (url.pathname === "/api/path-selections") return response({ paths: ["C:/report.md"] });
  if (path === "/api/reports" && options.method === "POST") {
    const created = report("independent"); reports.push(created); return response(created, 201);
  }
  if (options.method === "DELETE") return deleting.promise;
  if (options.method === "PUT") {
    if (failSave) return response({ detail: "Save failed; try again" }, 503);
    const index = reports.findIndex(item => path.includes(encodeURIComponent(item.report_ref)));
    reports[index] = report(reports[index].report_id, JSON.parse(options.body).bindings.map(item => target(item.kind, item.key)));
    return response(reports[index]);
  }
  if (url.pathname === "/api/report-library") return response(pageOf(reports));
  throw new Error(`Unexpected request: ${path}`);
} });
const manager = await import("../../src/psycheval/assets/web/modules/report-manager-page.js");
const { reportLibraryStore: store, draftChanged } = await import("../../src/psycheval/assets/web/modules/report-library-store.js");
test.after(() => browser.cleanup());

test("unified table uses a right reader and retains independent drafts through selection and refresh", async () => {
  await manager.initializeReportManagerPage();
  assert.equal(document.querySelectorAll("[data-report-row]").length, 2);
  assert.deepEqual([...document.querySelectorAll(".report-library-grid th")].map(node => node.textContent), ["Report", "Format", "Associations", "Updated"]);
  assert.doesNotMatch(document.querySelector("[data-report-toolbar]").textContent, /Source type|Evaluation reports|Imported reports/);
  assert.equal(new URL(requests.at(-1).path, "http://localhost").searchParams.has("origin"), false);
  document.querySelector('[data-report-select="package:first"]').click();
  assert.ok(document.body.classList.contains("workspace-sidebar-right-open"));
  const frame = document.querySelector("#report-library-detail iframe");
  assert.equal(frame.getAttribute("sandbox"), "allow-scripts");
  assert.match(frame.getAttribute("src"), /package%3Afirst/);
  document.querySelector('[data-report-tab="associations"]').click();
  await tick();
  document.querySelector("[data-binding-remove]").click();
  assert.ok(draftChanged(store.drafts.get("package:first")));
  document.querySelector('[data-report-select="analysis:canonical"]').click();
  document.querySelector('[data-report-tab="associations"]').click();
  await tick();
  assert.equal(document.querySelector('[data-binding-kind] option[value="session"]'), null);
  assert.equal(document.querySelector("[data-report-delete]"), null);
  document.querySelector('[data-report-select="package:first"]').click();
  document.querySelector('[data-report-tab="associations"]').click();
  await manager.loadReportManagerPage();
  assert.equal(store.drafts.get("package:first").values.size, 0);
  assert.equal(document.querySelector("[data-report-save]").disabled, false);
  assert.equal(document.querySelector('[data-table-column-key="source_category"]'), null);
});

test("save failure retains draft and retry saves an empty association list", async () => {
  failSave = true;
  await manager.saveBindings();
  assert.ok(draftChanged(store.drafts.get("package:first")));
  assert.match(document.body.textContent, /Save failed; try again/);
  failSave = false;
  await manager.saveBindings();
  assert.equal(draftChanged(store.drafts.get("package:first")), false);
  const saved = requests.filter(item => item.options.method === "PUT").at(-1);
  assert.equal(saved.path, "/api/report-library/package%3Afirst/bindings");
  assert.deepEqual(JSON.parse(saved.options.body), { bindings: [] });
});

test("independent import requires no selected object and opens the saved report", async () => {
  document.querySelector("[data-report-import]").click();
  await tick(); await tick();
  const imported = requests.find(item => item.path === "/api/reports" && item.options.method === "POST");
  assert.deepEqual(JSON.parse(imported.options.body), { path: "C:/report.md", bindings: [] });
  assert.deepEqual(manager.activeReportSnapshot(), { report_ref: "package:independent", report_name: "independent.md" });
  assert.match(document.querySelector("#report-library-detail iframe").getAttribute("src"), /package%3Aindependent/);
});

test("pending deletion prevents a concurrent save and retry keeps the draft", async () => {
  document.querySelector('[data-report-tab="associations"]').click();
  await tick();
  document.querySelector("[data-target-key]").click();
  deleting = deferred();
  document.querySelector("[data-report-delete]").click();
  assert.equal(document.querySelector("[data-report-save]").disabled, true);
  assert.equal(document.querySelector("[data-report-delete]").disabled, true);
  const writes = requests.filter(item => item.options.method === "PUT").length;
  await manager.saveBindings();
  assert.equal(requests.filter(item => item.options.method === "PUT").length, writes);
  deleting.resolve(response({ detail: "Delete failed" }, 503));
  await tick(); await tick();
  assert.equal(document.querySelector("[data-report-delete]").disabled, false);
  assert.equal(document.querySelector("[data-report-save]").disabled, false);
  assert.ok(draftChanged(store.drafts.get("package:independent")));
});

test("unreadable associations keep the preview and draft but disable editing until recovery", async () => {
  document.querySelector('[data-report-select="analysis:canonical"]').click();
  document.querySelector('[data-report-tab="associations"]').click();
  await tick();
  document.querySelector("[data-target-key]").click();
  const canonical = reports.find(item => item.report_ref === "analysis:canonical");
  canonical.associations_available = false;
  await manager.loadReportManagerPage();
  assert.match(document.querySelector("[data-association-summary]").textContent, /Report associations could not be read/);
  assert.equal(document.querySelector("[data-binding-picker],[data-report-save],[data-binding-remove]"), null);
  assert.equal(store.drafts.get(canonical.report_ref).values.size, 1);
  document.querySelector('[data-report-tab="preview"]').click();
  assert.match(document.querySelector("#report-library-detail iframe").src, /analysis%3Acanonical\/preview$/);
  canonical.associations_available = true;
  await manager.loadReportManagerPage();
  document.querySelector('[data-report-tab="associations"]').click();
  assert.equal(document.querySelector("[data-report-save]").disabled, false);
  assert.equal(store.drafts.get(canonical.report_ref).values.size, 1);
});
