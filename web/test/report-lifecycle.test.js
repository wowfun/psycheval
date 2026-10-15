import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";
import { reportPageHtml, response, target, report, pageOf, deferred } from "./support/report-library.js";

let reports;
let pendingArchive;
let pendingDelete;
let pendingList;
const writes = [];
const browser = installBrowserDom(reportPageHtml, { fetch: async (path, options = {}) => {
  const url = new URL(path, "http://localhost");
  if (options.method === "PUT" || options.method === "DELETE") writes.push({ path, options });
  if (url.pathname.endsWith("/state")) {
    if (pendingArchive) return pendingArchive.promise;
    const ref = decodeURIComponent(url.pathname.split("/")[3]);
    const index = reports.findIndex(item => item.report_ref === ref);
    reports[index] = { ...reports[index], ...JSON.parse(options.body) };
    return response(reports[index]);
  }
  if (options.method === "DELETE") return pendingDelete.promise;
  if (url.pathname === "/api/report-library/targets") return response(pageOf([]));
  if (url.pathname === "/api/report-library") {
    if (pendingList) { const pending = pendingList; pendingList = null; return pending.promise; }
    const state = url.searchParams.get("state");
    return response(pageOf(reports.filter(item => state === "all" || Boolean(item.archived) === (state === "archived"))));
  }
  const found = reports.find(item => item.report_ref === decodeURIComponent(url.pathname.split("/")[3]));
  return found ? response(found) : response({ detail: "Missing report" }, 404);
} });
const manager = await import("../../src/psycheval/assets/web/modules/report-manager-page.js");
const { reportLibraryStore: store, editBinding, draftChanged, acceptReport } = await import("../../src/psycheval/assets/web/modules/report-library-store.js");
const { RENDER_OPTIONS } = await import("../../src/psycheval/assets/web/app/render-options.js");
test.after(() => browser.cleanup());
test.beforeEach(async () => {
  RENDER_OPTIONS.role = "admin";
  window.confirm = () => true;
  reports = [report("imported"), report("canonical", [], "evaluation")];
  pendingArchive = pendingDelete = pendingList = null;
  writes.length = 0;
  store.reports.clear(); store.drafts.clear();
  store.activeRef = null; store.stateFilter = "active";
  await manager.initializeReportManagerPage();
});

test("both kinds expose management in preview and associations; guests only read", async () => {
  for (const item of reports) {
    manager.openReportPreview(item.report_ref);
    assert.ok(document.querySelector("[data-report-archive]"));
    assert.ok(document.querySelector("[data-report-delete]"));
    document.querySelector('[data-report-tab="associations"]').click();
    assert.equal(document.querySelectorAll("[data-report-delete]").length, 1);
  }
  RENDER_OPTIONS.role = "guest";
  manager.openReportPreview(reports[0].report_ref);
  assert.equal(document.querySelector("[data-report-archive],[data-report-delete]"), null);
  await manager.setArchived(); await manager.deleteReport();
  assert.equal(writes.length, 0);
});

test("archive and restore close filtered details while preserving unsaved associations", async () => {
  const ref = reports[1].report_ref;
  manager.openReportPreview(ref);
  editBinding(ref, target("dataset", "draft"), true);
  await manager.setArchived();
  assert.equal(store.activeRef, null);
  assert.equal(document.getElementById("report-library-detail").hidden, true);
  assert.ok(draftChanged(store.drafts.get(ref)));
  assert.equal(store.items.length, 1);
  store.stateFilter = "archived";
  await manager.loadReportManagerPage();
  assert.deepEqual(store.items.map(item => item.report_ref), [ref]);
  manager.openReportPreview(ref);
  assert.equal(document.querySelector("[data-report-archive]").textContent, "Restore report");
  await manager.setArchived();
  assert.equal(store.activeRef, null);
  assert.ok(draftChanged(store.drafts.get(ref)));
  assert.equal(store.items.length, 0);
});

test("archive completion adopts authoritative bindings when the local draft is clean", async () => {
  const first = reports[0];
  manager.openReportPreview(first.report_ref);
  pendingArchive = deferred();
  const archiving = manager.setArchived();
  const binding = target("dataset", "new-server-binding");
  const updated = { ...report(first.report_id, [binding]), archived: true };
  reports[0] = updated;
  pendingArchive.resolve(response(updated));
  await archiving;
  const draft = store.drafts.get(first.report_ref);
  assert.deepEqual(draft.baseline, [binding]);
  assert.deepEqual([...draft.values.values()], [binding]);
  assert.equal(draftChanged(draft), false);
  assert.equal(store.activeRef, null);
});

test("refresh during an archive preserves the baseline until the mutation settles", async () => {
  const first = reports[0];
  manager.openReportPreview(first.report_ref);
  const draft = store.drafts.get(first.report_ref);
  const baseline = [...draft.baseline];
  pendingArchive = deferred();
  const archiving = manager.setArchived();
  const binding = target("dataset", "server-change");
  acceptReport({ ...first, bindings: [binding] });
  assert.deepEqual(draft.baseline, baseline);
  reports[0] = { ...first, bindings: [binding], archived: true };
  pendingArchive.resolve(response(reports[0]));
  await archiving;
  assert.deepEqual(draft.baseline, [binding]);
});

test("pending archive blocks mutations; late results retain newer selection and ignore old lists", async () => {
  const first = reports[0];
  const other = reports[1];
  manager.openReportPreview(first.report_ref);
  editBinding(first.report_ref, target("dataset", "draft"), true);
  const oldList = deferred(); pendingList = oldList;
  const reading = manager.loadReportManagerPage();
  pendingArchive = deferred();
  const archiving = manager.setArchived();
  assert.equal(document.querySelector("[data-report-archive]").disabled, true);
  assert.equal(document.querySelector("[data-report-delete]").disabled, true);
  await manager.deleteReport(); await manager.saveBindings();
  assert.equal(writes.length, 1);
  manager.openReportPreview(other.report_ref);
  editBinding(first.report_ref, target("job", "newer"), true);
  reports[0] = { ...first, archived: true };
  pendingArchive.resolve(response(reports[0]));
  await archiving;
  oldList.resolve(response(pageOf([first, other])));
  await reading;
  assert.equal(store.activeRef, other.report_ref);
  assert.equal(store.reports.get(first.report_ref).archived, true);
  assert.equal(store.drafts.get(first.report_ref).values.size, 2);
  assert.deepEqual(store.items.map(item => item.report_ref), [other.report_ref]);
});

test("failed archive leaves the draft and allows retry", async () => {
  store.loading = true;
  manager.renderReportManagerPage();
  const ref = reports[0].report_ref;
  manager.openReportPreview(ref);
  editBinding(ref, target("dataset", "draft"), true);
  pendingArchive = deferred();
  const archiving = manager.setArchived();
  pendingArchive.resolve(response({ detail: "Archive failed" }, 503));
  await archiving;
  assert.equal(document.querySelector("[data-report-inventory]").getAttribute("aria-busy"), "false");
  assert.equal(store.activeRef, ref);
  assert.ok(draftChanged(store.drafts.get(ref)));
  assert.equal(document.querySelector("[data-report-archive]").disabled, false);
  pendingArchive = null;
  await manager.setArchived();
  assert.equal(store.activeRef, null);
});

test("delete cancellation and failure preserve drafts; success clears only the deleted report", async () => {
  const first = reports[0]; const other = reports[1];
  manager.openReportPreview(first.report_ref);
  editBinding(first.report_ref, target("dataset", "first"), true);
  editBinding(other.report_ref, target("dataset", "other"), true);
  window.confirm = () => false;
  await manager.deleteReport();
  assert.equal(writes.length, 0);
  window.confirm = message => { assert.match(message, /Permanently delete.*evidence.*kept/); return true; };
  pendingDelete = deferred();
  const failed = manager.deleteReport();
  await manager.setArchived(); await manager.saveBindings();
  assert.equal(writes.length, 1);
  pendingDelete.resolve(response({ detail: "Delete failed" }, 503));
  await failed;
  assert.ok(draftChanged(store.drafts.get(first.report_ref)));
  pendingDelete = deferred();
  const deleting = manager.deleteReport();
  manager.openReportPreview(other.report_ref);
  reports = [other];
  pendingDelete.resolve(new Response(null, { status: 204 }));
  await deleting;
  assert.equal(store.activeRef, other.report_ref);
  assert.equal(store.reports.has(first.report_ref), false);
  assert.equal(store.drafts.has(first.report_ref), false);
  assert.ok(draftChanged(store.drafts.get(other.report_ref)));
});

test("committed delete failure clears deleted content and reports the remaining cleanup", async () => {
  const canonical = reports[1];
  manager.openReportPreview(canonical.report_ref);
  pendingDelete = deferred();
  const deleting = manager.deleteReport();
  reports = [reports[0]];
  pendingDelete.resolve(response({ detail: "Projection failed", committed: true, metadata_cleared: true, catalog_reconciled: false }, 500));
  await deleting;
  assert.equal(store.activeRef, null);
  assert.equal(store.drafts.has(canonical.report_ref), false);
  assert.match(document.body.textContent, /was removed.*Projection failed/);
  assert.equal(store.items.length, 1);
});
