import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const requests = [];
const response = payload => new Response(JSON.stringify(payload), {
  status: 200,
  headers: { "Content-Type": "application/json" },
});
const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin","authentication_enabled":false}</script>
  <div data-report-manager>
    <button data-report-manager-reload>Reload</button>
    <p data-report-manager-status hidden></p>
    <div data-report-inventory></div>
    <span data-report-count></span>
    <label data-report-page-search-control hidden><input type="search" data-report-page-search></label>
    <div data-report-bindings></div>
  </div>
  <aside id="workspace-report-reader" hidden></aside>
`, {
  fetch: async (path, options = {}) => {
    requests.push({ path: String(path), options });
    if (String(path) === "/api/reports") {
      return response([{ report_id: "report-1", filename: "report.md", format: "markdown", source_keys: ["source-1"] }]);
    }
    if (String(path).startsWith("/api/catalog?")) {
      return response({
        page: 3,
        page_size: 100,
        total: 301,
        items: [{ source_key: "source-1", source_alias: "Run one", source_category: "baseline", active: true }],
      });
    }
    if (String(path) === "/api/sources/source-1" && options.method === "PATCH") return response({});
    if (String(path) === "/api/reports/report-1/bindings" && options.method === "PUT") {
      return response({ report_id: "report-1", filename: "report.md", format: "markdown", source_keys: [] });
    }
    throw new Error(`unexpected request: ${path}`);
  },
});

const managerPage = await import("../../src/psycheval/assets/web/modules/report-manager-page.js");
const { reportStore } = await import("../../src/psycheval/assets/web/modules/report-store.js");
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test.after(() => browser.cleanup());

test("Reports page edits Category without losing its binding draft or local state", async () => {
  await managerPage.initializeReportManagerPage();

  const checkbox = document.querySelector("[data-report-page-binding]");
  checkbox.click();
  assert.deepEqual([...reportStore.manager.draftBindings], []);
  reportStore.manager.search = "needle";
  reportStore.manager.page = 3;
  const list = document.querySelector('[data-table-id="report-bindings"]');
  list.scrollTop = 37;

  const category = document.querySelector('[data-table-column-key="source_category"]');
  category.dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true }));
  const editor = category.querySelector("input");
  editor.value = "candidate";
  editor.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  await tick();
  await tick();

  const patch = requests.find(request => request.path === "/api/sources/source-1");
  assert.equal(patch.options.method, "PATCH");
  assert.deepEqual(JSON.parse(patch.options.body), { category: "candidate" });
  assert.deepEqual([...reportStore.manager.draftBindings], []);
  assert.equal(reportStore.manager.search, "needle");
  assert.equal(reportStore.manager.page, 3);
  assert.equal(list.scrollTop, 37);
  assert.match(category.textContent, /candidate/);
  assert.equal(document.activeElement, category);
});

test("Reports search keeps the focused input node while debounced results load", async () => {
  reportStore.manager.search = "";
  managerPage.renderReportManagerPage();
  const search = document.querySelector("[data-report-page-search]");
  search.focus();
  search.value = "needle";
  search.setSelectionRange(6, 6);
  search.dispatchEvent(new window.Event("input", { bubbles: true }));

  await new Promise(resolve => setTimeout(resolve, 180));
  await tick();

  assert.equal(document.querySelector("[data-report-page-search]"), search);
  assert.equal(document.activeElement, search);
  assert.equal(search.value, "needle");
  assert.equal(search.selectionStart, 6);
});

test("Reports page persists an empty binding set through its owned API path", async () => {
  reportStore.manager.draftBindings = new Set();
  reportStore.manager.dirty = true;
  managerPage.renderReportManagerPage();
  document.querySelector("[data-report-page-save]").click();
  await tick();
  await tick();

  const save = requests.find(request => request.path === "/api/reports/report-1/bindings");
  assert.deepEqual(JSON.parse(save.options.body), { source_keys: [] });
  assert.deepEqual(reportStore.reports[0].source_keys, []);
  assert.equal(reportStore.manager.dirty, false);
});

test("Reports preview shares resize, focus, Escape, and navigation behavior", async () => {
  managerPage.renderReportManagerPage();
  const opener = document.querySelector("[data-report-page-preview]");
  assert.equal(managerPage.openReportPreview("report-1", { opener }), true);
  const preview = document.getElementById("workspace-report-reader");
  const resize = preview.querySelector("[data-sidebar-resize]");
  assert.ok(resize);
  assert.equal(resize.getAttribute("aria-label"), "Resize report reader");
  assert.equal(document.body.classList.contains("workspace-sidebar-left-open"), true);
  assert.match(document.documentElement.style.getPropertyValue("--workspace-left-sidebar-width"), /^\d+px$/);
  await new Promise(resolve => window.requestAnimationFrame(resolve));
  assert.equal(document.activeElement, preview.querySelector("[data-sidebar-close]"));
  document.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  await new Promise(resolve => window.requestAnimationFrame(resolve));
  assert.equal(preview.hidden, true);
  assert.equal(document.body.classList.contains("report-reader-open"), false);
  assert.equal(document.body.classList.contains("workspace-sidebar-left-open"), false);
  assert.equal(document.activeElement, opener);

  assert.equal(managerPage.openReportPreview("report-1", { opener }), true);
  const search = document.querySelector("[data-report-page-search]");
  search.focus();
  window.dispatchEvent(new window.CustomEvent("peval:workspace-navigate"));
  assert.equal(preview.hidden, true);
  assert.equal(document.body.classList.contains("report-reader-open"), false);
  assert.equal(document.activeElement, search);
});
