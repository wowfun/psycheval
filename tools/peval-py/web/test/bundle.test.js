import assert from "node:assert/strict";
import test from "node:test";
import { pathToFileURL } from "node:url";

import { REPORT_BUNDLE_PATH } from "../scripts/report-bundle.mjs";
import { installBrowserDom } from "./support/browser.js";

function reportShell(mode, workspaceSnapshot = null) {
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
    <script type="application/json" id="peval-py-data">{"trajectory":[],"trajectory_meta":[],"annotations":{}}</script>
    <script type="application/json" id="peval-py-token-estimates">{}</script>
    <script type="application/json" id="peval-py-i18n">{}</script>
    ${workspaceSnapshot === null ? "" : `<script type="application/json" id="peval-py-workspace-snapshot">${JSON.stringify(workspaceSnapshot)}</script>`}
    <script type="application/json" id="peval-py-render-options">{"mode":"${mode}","sources":[]}</script>
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
  } finally {
    browser.cleanup();
  }
});
