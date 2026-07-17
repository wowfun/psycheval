import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-py-data">{}</script>
  <script type="application/json" id="peval-py-token-estimates">{}</script>
  <script type="application/json" id="peval-py-i18n">{}</script>
  <script type="application/json" id="peval-py-render-options">{"mode":"serve","sources":[]}</script>
  <strong data-source-count></strong>
  <span data-source-status></span>
  <div data-source-manager hidden><section aria-modal="true"><button data-source-manager-close>Close</button><p data-source-manager-status hidden></p><ul data-source-list></ul></section></div>
  <div data-report-manager hidden><section aria-modal="true"><button data-report-manager-close>Close</button><p data-report-manager-status hidden></p><div data-report-inventory></div><span data-report-count></span><div data-report-bindings></div></section></div>
  <div data-view-save-dialog hidden><section aria-modal="true"><button data-view-save-cancel>Cancel</button></section></div>
  <button data-refresh-all>Refresh</button>
  <button data-source-bulk-state disabled>Archive</button>
  <button data-source-bulk-delete disabled>Delete</button>
`);

const runtime = await import("../src/modules/runtime.js");
const sourceManager = await import("../src/modules/source-manager.js");
const serveEffects = await import("../src/modules/serve-effects.js");
const catalog = await import("../src/modules/serve-catalog.js");
const modals = await import("../src/modules/modal-surfaces.js");
const reports = await import("../src/modules/workspace-reports.js");

test.after(() => browser.cleanup());

test("Source Manager renders its own page instead of the Leaderboard page", () => {
  runtime.state.serveSources = [];
  runtime.state.sourceManagerRows = [{
    source_key: "source-one",
    label: "runs/source-one",
    active: true,
    readable: true,
  }];
  runtime.state.sourceManagerStatus = { phase: "ready", message: "" };
  sourceManager.renderServeSources();

  assert.match(document.querySelector("[data-source-list]").textContent, /runs\/source-one/);
  assert.doesNotMatch(document.querySelector("[data-source-list]").textContent, /No sources loaded/);

  runtime.state.sourceManagerStatus = { phase: "loading", message: "Loading" };
  sourceManager.renderServeSources();
  assert.match(document.querySelector("[data-source-list]").textContent, /Loading/);

  runtime.state.sourceManagerRows = [];
  runtime.state.sourceManagerStatus = { phase: "error", message: "Catalog failed" };
  sourceManager.renderServeSources();
  assert.match(document.querySelector("[data-source-list]").textContent, /Catalog failed/);
});

test("Source Manager derives a cross-page batch state from every selected source", async () => {
  const requests = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => {
    requests.push({ path: String(path), body: JSON.parse(String(options.body || "{}")) });
    return {
      ok: true,
      statusText: "OK",
      text: async () => "{",
    };
  };

  try {
    runtime.state.sourceSelection.clear();
    runtime.state.sourceManagerStatus = { phase: "ready", message: "" };
    runtime.state.sourceManagerRows = [{
      source_key: "archived-on-page-one",
      label: "Archived on page one",
      active: false,
      readable: true,
    }];
    runtime.state.sourceSelection.add("archived-on-page-one");
    sourceManager.renderServeSources();
    assert.equal(
      document.querySelector("[data-source-bulk-state]").dataset.sourceBulkState,
      "active",
    );

    runtime.state.sourceManagerRows = [{
      source_key: "active-on-page-two",
      label: "Active on page two",
      active: true,
      readable: true,
    }];
    sourceManager.renderServeSources();

    const stateButton = document.querySelector("[data-source-bulk-state]");
    assert.equal(stateButton.textContent, "Activate selected");
    assert.equal(stateButton.dataset.sourceBulkState, "active");
    await serveEffects.mutateSelectedServeSourceState();
    assert.deepEqual(requests, [{
      path: "/api/sources/state",
      body: {
        source_keys: ["archived-on-page-one"],
        active: true,
        report_source_state: "active",
      },
    }]);
  } finally {
    globalThis.fetch = previousFetch;
    runtime.state.sourceSelection.clear();
    runtime.state.sourceManagerRows = [];
    runtime.state.sourceManagerStatus = { phase: "ready", message: "" };
    sourceManager.renderServeSources();
  }
});

test("workspace busy state disables and restores controls", () => {
  const refresh = document.querySelector("[data-refresh-all]");
  const bulk = document.querySelector("[data-source-bulk-state]");
  refresh.disabled = false;
  bulk.disabled = true;

  catalog.setWorkspaceWriteControlsDisabled(true);
  assert.equal(refresh.disabled, true);
  assert.equal(refresh.getAttribute("aria-busy"), "true");

  catalog.setWorkspaceWriteControlsDisabled(false);
  assert.equal(refresh.disabled, false);
  assert.equal(refresh.hasAttribute("aria-busy"), false);
  assert.equal(bulk.disabled, true);
});

test("modal surfaces are mutually exclusive and restore focus", () => {
  const opener = document.createElement("button");
  document.body.append(opener);
  opener.focus();
  const source = document.querySelector("[data-source-manager]");
  const report = document.querySelector("[data-report-manager]");

  modals.openModalSurface(source, {
    opener,
    bodyClass: "source-manager-open",
    focusTarget: source.querySelector("button"),
  });
  assert.equal(source.hidden, false);
  assert.equal(document.activeElement, source.querySelector("button"));

  modals.openModalSurface(report, {
    opener,
    bodyClass: "report-manager-open",
    focusTarget: report.querySelector("button"),
  });
  assert.equal(source.hidden, true);
  assert.equal(report.hidden, false);

  modals.closeModalSurface(report);
  assert.equal(document.activeElement, opener);
});

test("Reports Manager distinguishes loading from empty and clears old errors", () => {
  runtime.state.workspaceReports = [];
  runtime.state.reportManager.loading = true;
  runtime.state.reportManager.busy = false;
  reports.renderWorkspaceReportManager();
  assert.match(document.querySelector("[data-report-inventory]").textContent, /Loading/);
  assert.equal(document.querySelector("[data-report-manager]").getAttribute("aria-busy"), "true");

  runtime.state.reportManager.loading = false;
  reports.setWorkspaceReportManagerStatus("Old error", true);
  reports.setWorkspaceReportManagerStatus("");
  assert.equal(document.querySelector("[data-report-manager-status]").hidden, true);
});
