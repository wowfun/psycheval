from __future__ import annotations

import json
import shutil
import subprocess
import unittest

from peval_py.html.assets import load_asset_text


class ServeCatalogUiTests(unittest.TestCase):
    def test_archived_toggle_queries_target_catalog_and_can_return_from_empty_state(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required for report.js archived-toggle coverage")
        asset = load_asset_text("report.js").rsplit('\n"peval-py-entrypoint";', 1)[0]
        script = r"""
const vm = require("vm");
const nodes = {
  "peval-py-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [] }) },
  "peval-py-i18n": { textContent: "{}" },
  "peval-py-token-estimates": { textContent: "{}" }
};
const context = {
  document: {
    body: { classList: { add() {}, remove() {}, toggle() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
  },
  window: { addEventListener() {} },
  console, JSON, Number, String, Object, Math, Date, Set, Array, RegExp, URLSearchParams,
  setTimeout(callback) { callback(); return 1; },
  clearTimeout() {},
};
vm.createContext(context);
vm.runInContext(__ASSET__, context);
const result = vm.runInContext(`(async () => {
  const active = normalizeCatalogRow({ source_key: "active-1", active: true, readable: true });
  state.serveSources = [active];
  state.catalogRows = [active];
  state.catalogPage = { generation: 1, page: 1, page_size: 100, total: 1, facets: {} };
  state.catalogQuery = { ...state.catalogQuery, state: "active", page: 1 };
  state.serveSourceMode = "active";
  const activeControls = renderServeSourceStateControls();
  const requests = [];
  const renders = [];
  serveApi = async path => {
    requests.push(path);
    const target = new URLSearchParams(path.split("?", 2)[1]).get("state");
    if (target === "archived") return { generation: 1, page: 1, page_size: 100, total: 0, facets: {}, items: [] };
    return { generation: 1, page: 1, page_size: 100, total: 1, facets: {}, items: [active] };
  };
  renderServeSources = () => renders.push("sources");
  renderComparison = () => renders.push("comparison");
  setWorkspaceWriteControlsDisabled = () => {};
  setServeStatus = () => {};
  ensureCatalogDetail = async () => renders.push("detail");
  await switchServeSourceMode("archived");
  const emptyArchived = { mode: state.serveSourceMode, total: state.catalogPage.total, rows: state.catalogRows.length };
  const archivedControls = renderServeSourceStateControls();
  await switchServeSourceMode("active");
  state.serveSourceMode = "all";
  const allControls = renderServeSourceStateControls();
  return JSON.stringify({ activeControls, archivedControls, allControls, requests, renders, emptyArchived, finalMode: state.serveSourceMode });
})()`, context);
Promise.resolve(result).then(value => console.log(value)).catch(error => { console.error(error && error.stack || error); process.exit(1); });
""".replace("__ASSET__", json.dumps(asset))
        node = subprocess.run(
            ["node"], input=script, text=True, capture_output=True, timeout=10, check=False
        )
        self.assertEqual(node.returncode, 0, node.stderr)
        result = json.loads(node.stdout)

        active_toggle = result["activeControls"].split("data-source-state-toggle", 1)[1].split(">", 1)[0]
        archived_toggle = result["archivedControls"].split("data-source-state-toggle", 1)[1].split(">", 1)[0]
        all_toggle = result["allControls"].split("data-source-state-toggle", 1)[1].split(">", 1)[0]
        self.assertNotIn("disabled", active_toggle)
        self.assertIn("checked", archived_toggle)
        self.assertNotIn("disabled", archived_toggle)
        self.assertIn("checked", all_toggle)
        self.assertIn("disabled", all_toggle)
        self.assertEqual(result["emptyArchived"], {"mode": "archived", "total": 0, "rows": 0})
        catalog_requests = [path for path in result["requests"] if path.startswith("/api/catalog?")]
        self.assertEqual(len(catalog_requests), 2)
        self.assertIn("state=archived", catalog_requests[0])
        self.assertIn("state=active", catalog_requests[1])
        self.assertEqual(result["renders"], ["sources", "comparison", "detail"] * 2)
        self.assertEqual(result["finalMode"], "all")

    def test_catalog_rows_default_detail_and_cross_page_selection(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required for report.js catalog state coverage")
        asset = load_asset_text("report.js").rsplit('\n"peval-py-entrypoint";', 1)[0]
        script = r"""
const vm = require("vm");
const nodes = {
  "peval-py-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [] }) },
  "peval-py-i18n": { textContent: "{}" },
  "peval-py-token-estimates": { textContent: "{}" }
};
const context = {
  document: {
    body: { classList: { add() {}, remove() {}, toggle() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
  },
  window: { addEventListener() {} },
  console,
  JSON,
  Number,
  String,
  Object,
  Math,
  Date,
  Set,
  Array,
  RegExp,
  URLSearchParams,
  setTimeout() { return 1; },
  clearTimeout() {},
};
vm.createContext(context);
vm.runInContext(__ASSET__, context);
const result = vm.runInContext(`(async () => {
  state.catalogPage = { generation: 7, page: 1, page_size: 100, total: 2, facets: {} };
  state.catalogRows = [
    normalizeCatalogRow({ source_key: "cell-latest", trial_key: "native-latest", trial_session_id: "latest", status: "passed", last_turn_finished_at_ms: 200, readable: true }),
    normalizeCatalogRow({ source_key: "cell-failed", trial_key: "native-failed", trial_session_id: "failed", status: "failed", last_turn_finished_at_ms: 100, readable: true })
  ];
  state.serveSources = state.catalogRows;
  state.view = { trajectory: [{ session_id: "failed", steps: [] }], trajectory_meta: [{ trial_key: "native-failed", steps: [] }] };
  state.rowSelection.add("cell-latest");
  state.sourceSelection.add("cell-latest");
  const loads = [];
  loadServeSourceReport = async key => { loads.push(key); state.selectedSourceKey = key; };
  await ensureCatalogDetail(false);
  state.catalogRows = [normalizeCatalogRow({ source_key: "cell-page-two", trial_key: "native-two", trial_session_id: "two", status: "passed", readable: true })];
  pruneSourceSelection();
  return JSON.stringify({
    defaultDetail: loads[0],
    selectedRows: Array.from(state.rowSelection),
    selectedSources: Array.from(state.sourceSelection),
    normalizedTrialKey: reportRows()[0].trial_key,
    total: state.catalogPage.total
  });
})()`, context);
Promise.resolve(result).then(value => console.log(value));
""".replace("__ASSET__", json.dumps(asset))
        node = subprocess.run(
            ["node"],
            input=script,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(node.returncode, 0, node.stderr)
        result = json.loads(node.stdout)
        self.assertEqual(result["defaultDetail"], "cell-failed")
        self.assertEqual(result["selectedRows"], ["cell-latest"])
        self.assertEqual(result["selectedSources"], ["cell-latest"])
        self.assertEqual(result["normalizedTrialKey"], "cell-page-two")
        self.assertEqual(result["total"], 2)

    def test_catalog_selection_resolves_source_keys_to_detail_trial_steps(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required for report.js catalog selection coverage")
        asset = load_asset_text("report.js").rsplit('\n"peval-py-entrypoint";', 1)[0]
        script = r"""
const vm = require("vm");
const reports = {
  "source-user": {
    trajectory: [{ session_id: "session-user", steps: [
      { step_id: 1, source: "agent", message: "before" },
      { step_id: 2, source: "User", message: "first user" }
    ], final_metrics: {} }],
    trajectory_meta: [{ trial_key: "trial-user", status: "passed", steps: [] }]
  },
  "source-node": {
    trajectory: [{ session_id: "session-node", steps: [
      { step_id: 4, source: "agent", message: "open this step" }
    ], final_metrics: {} }],
    trajectory_meta: [{ trial_key: "trial-node", status: "passed", steps: [] }]
  },
  "source-no-user": {
    trajectory: [{ session_id: "session-no-user", steps: [
      { step_id: 9, source: "agent", message: "no user message" }
    ], final_metrics: {} }],
    trajectory_meta: [{ trial_key: "trial-no-user", status: "passed", steps: [] }]
  }
};
const nodes = {
  "peval-py-data": { textContent: "{}" },
  "peval-py-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [] }) },
  "peval-py-i18n": { textContent: "{}" },
  "peval-py-token-estimates": { textContent: "{}" }
};
const calls = [];
const context = {
  document: {
    body: { classList: { toggle() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; }
  },
  window: { addEventListener() {} },
  fetch: async path => {
    const sourceKey = new URL(path, "http://localhost").searchParams.get("source_key");
    calls.push(sourceKey);
    return { ok: true, statusText: "OK", text: async () => JSON.stringify({ artifact_revision: `rev-${sourceKey}`, report: reports[sourceKey] }) };
  },
  console, JSON, Number, String, Object, Math, Date, Set, Array, RegExp, URL,
  reports, calls,
  requestAnimationFrame(callback) { callback(); }
};
vm.createContext(context);
vm.runInContext(__ASSET__, context);
const result = vm.runInContext(`(async () => {
  const rows = [
    normalizeCatalogRow({ source_key: "source-user", trial_key: "trial-user", trial_session_id: "session-user", readable: true, step_outline: [{ step_id: 1, source: "agent", duration_ms: 20, message: "do not render" }, { step_id: 2, source: "user", duration_ms: 30 }] }),
    normalizeCatalogRow({ source_key: "source-node", trial_key: "trial-node", trial_session_id: "session-node", readable: true, step_outline: [{ step_id: 4, source: "agent", duration_ms: 40 }] }),
    normalizeCatalogRow({ source_key: "source-no-user", trial_key: "trial-no-user", trial_session_id: "session-no-user", readable: true, step_outline: [{ step_id: 9, source: "agent", duration_ms: 50 }] })
  ];
  state.catalogRows = rows;
  state.serveSources = rows;
  render = view => { state.view = view; };
  const userRow = { dataset: { sourceKey: "source-user" }, listeners: {}, addEventListener(type, handler) { this.listeners[type] = handler; } };
  const noUserRow = { dataset: { sourceKey: "source-no-user" }, listeners: {}, addEventListener(type, handler) { this.listeners[type] = handler; } };
  let pending = null;
  const select = selectServeDetail;
  selectServeDetail = (...args) => pending = select(...args);
  bindTrialSelection({ querySelectorAll(selector) { return selector === "tr[data-source-key]" ? [userRow, noUserRow] : []; } });
  userRow.listeners.click({ stopPropagation() {} });
  await pending;
  const afterUser = { source: state.selectedSourceKey, trial: state.selectedTrial, step: state.selectedStep };
  noUserRow.listeners.click({ stopPropagation() {} });
  await pending;
  const afterNoUser = { source: state.selectedSourceKey, trial: state.selectedTrial, step: state.selectedStep };

  const node = { dataset: { sourceKey: "source-node", stepId: "4" }, listeners: {}, addEventListener(type, handler) { this.listeners[type] = handler; } };
  bindServeSourceStateControls = () => {};
  bindServeSelectionControls = () => {};
  bindTrajectoryControls({ querySelectorAll(selector) {
    if (selector === "[data-step-id]") return [node];
    return [];
  } });
  node.listeners.click({ stopPropagation() {} });
  await pending;
  const afterNode = { source: state.selectedSourceKey, trial: state.selectedTrial, step: state.selectedStep };
  const userOutline = renderTrajectoryOverviewRow(rows[0]);
  const nodeOutline = renderTrajectoryOverviewRow(rows[1]);
  return JSON.stringify({ calls, afterUser, afterNoUser, afterNode, userOutline, nodeOutline });
})()`, context);
Promise.resolve(result).then(value => console.log(value)).catch(error => { console.error(error && error.stack || error); process.exit(1); });
""".replace("__ASSET__", json.dumps(asset))
        node = subprocess.run(
            ["node"], input=script, text=True, capture_output=True, timeout=10, check=False
        )
        self.assertEqual(node.returncode, 0, node.stderr)
        result = json.loads(node.stdout)

        self.assertEqual(result["calls"], ["source-user", "source-no-user", "source-node"])
        self.assertEqual(
            result["afterUser"],
            {"source": "source-user", "trial": "trial-user", "step": {"trialKey": "trial-user", "stepId": "2"}},
        )
        self.assertEqual(
            result["afterNoUser"],
            {"source": "source-no-user", "trial": "trial-no-user", "step": None},
        )
        self.assertEqual(
            result["afterNode"],
            {"source": "source-node", "trial": "trial-node", "step": {"trialKey": "trial-node", "stepId": "4"}},
        )
        self.assertIn('data-source-key="source-user"', result["userOutline"])
        self.assertIn('data-step-id="2"', result["userOutline"])
        self.assertIn('data-source-key="source-node"', result["nodeOutline"])
        self.assertIn('data-step-id="4"', result["nodeOutline"])
        self.assertNotIn("do not render", result["userOutline"])


if __name__ == "__main__":
    unittest.main()
