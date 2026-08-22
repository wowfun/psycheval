import assert from "node:assert/strict";
import test from "node:test";
import { pathToFileURL } from "node:url";

import { REPORT_BUNDLE_PATH } from "../scripts/report-bundle.mjs";
import { installBrowserDom } from "./support/browser.js";

function reportShell(mode, workspaceSnapshot = null, renderOptions = {}) {
  const options = { mode, sources: [], ...renderOptions };
  const datasetPage = options.serve_page === "datasets" ? `
    <section data-harbor-workbench>
      <button data-harbor-reload>Reload</button>
      <input data-harbor-search type="search">
      <span data-harbor-overview-count></span>
      <div data-harbor-overview></div>
      <h2 data-harbor-selected-title></h2>
      <span data-harbor-selected-meta></span>
      <p data-harbor-workbench-status hidden></p>
      <div data-harbor-file-tree></div>
      <strong data-harbor-editor-path></strong>
      <span data-harbor-editor-meta></span>
      <textarea data-harbor-editor disabled></textarea>
      <div data-harbor-diagnostics></div>
    </section>` : "";
  return `
    <main>
      <section id="report-notes"></section>
      <section id="comparison"></section>
      <section id="trace"></section>
    </main>
    <aside id="workspace-views" hidden></aside>
    <aside id="step-drawer" hidden></aside>
    <strong data-source-count></strong>
    <span data-source-status></span>
    ${datasetPage}
    <script type="application/json" id="peval-data">{"trajectory":[],"trajectory_meta":[],"annotations":{}}</script>
    <script type="application/json" id="peval-token-estimates">{}</script>
    <script type="application/json" id="peval-i18n">{}</script>
    ${workspaceSnapshot === null ? "" : `<script type="application/json" id="peval-workspace-snapshot">${JSON.stringify(workspaceSnapshot)}</script>`}
    <script type="application/json" id="peval-render-options">${JSON.stringify(options)}</script>
  `;
}

test("committed ESM bundle starts static and workspace snapshot modes offline", async () => {
  let fetched = false;
  for (const [mode, snapshot] of [
    ["report", null],
    ["workspace_snapshot", { views: [], view_summaries: [], presentation: {} }],
  ]) {
    const browser = installBrowserDom(reportShell(mode, snapshot), {
      fetch: async () => {
        fetched = true;
        throw new Error(`${mode} must not fetch`);
      },
    });
    try {
      await import(`${pathToFileURL(REPORT_BUNDLE_PATH).href}?${mode}-smoke=${Date.now()}`);
      assert.equal(document.querySelector("#comparison").textContent, "");
    } finally {
      browser.cleanup();
    }
  }
  assert.equal(fetched, false);
});

test("committed ESM bundle starts the serve catalog and detail flow", async () => {
  const requests = [];
  const browser = installBrowserDom(reportShell("serve"), {
    fetch: async input => {
      const url = String(input);
      requests.push(url);
      if (url.startsWith("/api/catalog?")) {
        return new Response(JSON.stringify({
          generation: 1,
          total: 1,
          page: 1,
          page_size: 100,
          checking: false,
          facets: {},
          items: [{
            source_key: "source-one",
            trial_session_id: "session-one",
            artifact_revision: "revision-one",
            readable: true,
            active: true,
            status: "passed",
          }],
        }));
      }
      if (url.startsWith("/api/report?")) {
        return new Response(JSON.stringify({
          artifact_revision: "revision-one",
          report: { trajectory: [], trajectory_meta: [], annotations: {} },
        }));
      }
      if (url === "/api/views") {
        return new Response(JSON.stringify({ views: [] }));
      }
      if (url === "/api/reports") {
        return new Response(JSON.stringify({ reports: [] }));
      }
      throw new Error(`unexpected request: ${url}`);
    },
  });
  try {
    await import(`${pathToFileURL(REPORT_BUNDLE_PATH).href}?serve-smoke=${Date.now()}`);
    await new Promise(resolve => setImmediate(resolve));
    await new Promise(resolve => setImmediate(resolve));
    assert.ok(requests.some(url => url.startsWith("/api/catalog?")));
    assert.ok(requests.some(url => url.startsWith("/api/report?source_key=source-one")));
    assert.ok(requests.includes("/api/views"));
    assert.ok(requests.includes("/api/reports"));
  } finally {
    browser.cleanup();
  }
});

test("committed ESM bundle starts Datasets without requesting the Leaderboard catalog", async () => {
  const requests = [];
  const browser = installBrowserDom(reportShell("serve", null, {
    serve_page: "datasets",
    role: "guest",
  }), {
    fetch: async input => {
      const url = String(input);
      requests.push(url);
      if (url === "/api/harbor/datasets") {
        return new Response(JSON.stringify({ datasets: [] }));
      }
      throw new Error(`unexpected request: ${url}`);
    },
  });
  try {
    await import(`${pathToFileURL(REPORT_BUNDLE_PATH).href}?datasets-smoke=${Date.now()}`);
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(requests, ["/api/harbor/datasets"]);
    assert.equal(document.querySelectorAll("[data-harbor-overview-row]").length, 0);
  } finally {
    browser.cleanup();
  }
});
