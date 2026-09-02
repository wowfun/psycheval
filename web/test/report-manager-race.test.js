import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}

const response = payload => new Response(JSON.stringify(payload), {
  status: 200,
  headers: { "Content-Type": "application/json" },
});

test("Reports page ignores an older load that finishes after the latest request", async () => {
  const pages = new Map([[1, deferred()], [2, deferred()]]);
  const browser = installBrowserDom(`
    <script type="application/json" id="peval-i18n">{}</script>
    <script type="application/json" id="peval-render-options">{"role":"admin"}</script>
    <div data-report-manager>
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
  `, {
    fetch: async path => {
      const url = String(path);
      if (url === "/api/reports") return response([]);
      const page = Number(new URL(url, "http://localhost").searchParams.get("page"));
      return pages.get(page).promise;
    },
  });
  try {
    const { loadImportedReports } = await import(
      "../../src/psycheval/assets/web/modules/report-manager-page.js"
    );
    const { reportStore } = await import(
      "../../src/psycheval/assets/web/modules/report-store.js"
    );

    const first = loadImportedReports({ page: 1 });
    const second = loadImportedReports({ page: 2 });
    pages.get(2).resolve(response({
      page: 2,
      page_size: 100,
      total: 200,
      items: [{ source_key: "newest", readable: true }],
    }));
    await second;
    pages.get(1).resolve(response({
      page: 1,
      page_size: 100,
      total: 200,
      items: [{ source_key: "stale", readable: true }],
    }));
    await first;

    assert.equal(reportStore.manager.pageData.page, 2);
    assert.deepEqual(reportStore.manager.sourceRows.map(row => row.source_key), ["newest"]);
  } finally {
    browser.cleanup();
  }
});
