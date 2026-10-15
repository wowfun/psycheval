import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";
import { reportPageHtml, response, target, report, pageOf, deferred, tick } from "./support/report-library.js";

let handler;
const browser = installBrowserDom(reportPageHtml, { fetch: (...args) => handler(...args) });
const manager = await import("../../src/psycheval/assets/web/modules/report-manager-page.js");
const { reportLibraryStore: store, acceptReport, editBinding, draftChanged } = await import("../../src/psycheval/assets/web/modules/report-library-store.js");
test.after(() => browser.cleanup());

test("a pending linked report cannot replace a newer manually opened report", async () => {
  const pending = deferred();
  const newest = report("new-selection");
  acceptReport(newest);
  handler = () => pending.promise;
  const old = manager.openReportRef("package:old-link", { tab: "preview" });
  manager.openReportPreview(newest.report_ref);
  pending.resolve(response(report("old-link")));
  await old;
  assert.equal(store.activeRef, newest.report_ref);
  assert.equal(store.locationTarget.report, newest.report_ref);
});

test("a linked report survives an unrelated overlapping list refresh", async () => {
  const linked = report("outside-page"), pending = deferred();
  manager.restoreReportLocation({ ...manager.captureReportLocation(), object: { report: linked.report_ref } });
  handler = path => String(path).includes("?") ? Promise.resolve(response(pageOf([]))) : pending.promise;
  const opening = manager.openReportRef(linked.report_ref);
  await manager.loadReportManagerPage();
  pending.resolve(response(linked));
  await opening;
  assert.equal(store.activeRef, linked.report_ref);
  assert.equal(store.locationTarget.report, linked.report_ref);
  assert.equal(document.querySelector("#report-library-detail").hidden, false);
});

test("failed deletion releases a list read's busy state and keeps its draft", async () => {
  const selected = report("failed-delete"), deletion = deferred(), list = deferred();
  acceptReport(selected);
  manager.openReportPreview(selected.report_ref);
  editBinding(selected.report_ref, target("dataset", "draft"), true);
  handler = (path, options = {}) => options.method === "DELETE" ? deletion.promise : list.promise;
  const deleting = manager.deleteReport();
  const reading = manager.loadReportManagerPage();
  deletion.resolve(response({ detail: "fixture deletion failed" }, 503));
  await deleting;
  list.resolve(response(pageOf([selected])));
  await reading;
  assert.equal(store.loading, false);
  assert.equal(document.querySelector("[data-report-inventory]").getAttribute("aria-busy"), "false");
  assert.equal(store.activeRef, selected.report_ref);
  assert.ok(draftChanged(store.drafts.get(selected.report_ref)));
});

test("older page responses cannot replace the newest page", async () => {
  const pages = new Map([[1, deferred()], [2, deferred()]]);
  handler = path => pages.get(Number(new URL(path, "http://localhost").searchParams.get("page"))).promise;
  const first = manager.loadReportManagerPage({ page: 1 });
  const second = manager.loadReportManagerPage({ page: 2 });
  pages.get(2).resolve(response(pageOf([report("newest")], 2, 100)));
  await second;
  pages.get(1).resolve(response(pageOf([report("stale")], 1, 100)));
  await first;
  assert.equal(store.page, 2);
  assert.equal(store.items[0].report_ref, "package:newest");
});

test("late save and refresh responses preserve another selection and edits made during save", async () => {
  const oldRead = deferred();
  const write = deferred();
  let reads = 0;
  let persisted = report("editable");
  const other = report("other");
  acceptReport(persisted); acceptReport(other);
  store.activeRef = persisted.report_ref;
  const firstTarget = target("dataset", "first");
  const newerTarget = target("job", "second");
  editBinding(persisted.report_ref, firstTarget, true);
  handler = (path, options = {}) => {
    if (options.method === "PUT") return write.promise;
    if (++reads === 1) return oldRead.promise;
    return Promise.resolve(response(pageOf([persisted, other])));
  };
  const reading = manager.loadReportManagerPage();
  const saving = manager.saveBindings();
  editBinding(persisted.report_ref, newerTarget, true);
  store.activeRef = other.report_ref;
  persisted = report("editable", [firstTarget]);
  write.resolve(response(persisted));
  await saving;
  oldRead.resolve(response(pageOf([report("editable")])));
  await reading;
  assert.equal(store.activeRef, other.report_ref);
  const draft = store.drafts.get(persisted.report_ref);
  assert.equal(draft.values.size, 2);
  assert.ok(draftChanged(draft));
  assert.deepEqual(draft.baseline, [firstTarget]);
  assert.equal(store.items.length, 2);
});

test("a missing active report closes details while retaining its draft for reappearance", async () => {
  const selected = report("missing");
  acceptReport(selected);
  manager.openReportPreview(selected.report_ref);
  editBinding(selected.report_ref, target("dataset", "draft"), true);
  handler = path => Promise.resolve(path.includes("?")
    ? response(pageOf([])) : response({ detail: "Report no longer exists" }, 404));
  await manager.loadReportManagerPage();
  assert.equal(manager.activeReportSnapshot().report_ref, null);
  assert.equal(document.querySelector("#report-library-detail").hidden, true);
  assert.equal(document.body.classList.contains("workspace-sidebar-right-open"), false);
  assert.equal(store.reports.has(selected.report_ref), false);
  assert.equal(store.drafts.get(selected.report_ref).values.size, 1);
  handler = () => Promise.resolve(response(pageOf([selected])));
  await manager.loadReportManagerPage();
  manager.openReportPreview(selected.report_ref);
  assert.equal(document.querySelector("#report-library-detail").hidden, false);
  assert.match(document.querySelector("#report-library-detail iframe").src, /package%3Amissing/);
  assert.equal(store.drafts.get(selected.report_ref).values.size, 1);
});

test("a temporary metadata failure retains the selected report and its draft", async () => {
  const selected = report("retryable");
  acceptReport(selected);
  manager.openReportPreview(selected.report_ref);
  editBinding(selected.report_ref, target("job", "draft"), true);
  handler = path => Promise.resolve(path.includes("?")
    ? response(pageOf([])) : response({ detail: "Metadata temporarily unavailable" }, 503));
  await manager.loadReportManagerPage();
  assert.equal(store.activeRef, selected.report_ref);
  assert.equal(document.querySelector("#report-library-detail").hidden, false);
  assert.equal(store.drafts.get(selected.report_ref).values.size, 1);
});

test("a late metadata 404 cannot close a newer report selection", async () => {
  const missing = report("late-missing");
  const current = report("current");
  acceptReport(missing); acceptReport(current);
  manager.openReportPreview(missing.report_ref);
  const metadata = deferred();
  handler = path => path.includes("?")
    ? Promise.resolve(response(pageOf([current]))) : metadata.promise;
  const loading = manager.loadReportManagerPage();
  await tick();
  manager.openReportPreview(current.report_ref);
  metadata.resolve(response({ detail: "Report no longer exists" }, 404));
  await loading;
  assert.equal(store.activeRef, current.report_ref);
  assert.equal(document.querySelector("#report-library-detail").hidden, false);
  assert.match(document.querySelector("#report-library-detail iframe").src, /package%3Acurrent/);
});
