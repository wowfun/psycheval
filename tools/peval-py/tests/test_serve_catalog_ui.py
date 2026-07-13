from __future__ import annotations

import json
import shutil
import subprocess
import unittest

from peval_py.html.assets import load_asset_text


class ServeCatalogUiTests(unittest.TestCase):
    def test_catalog_rows_default_detail_and_cross_page_selection(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required for report.js catalog state coverage")
        asset = load_asset_text("report.js").rsplit("\nrender(data());", 1)[0]
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


if __name__ == "__main__":
    unittest.main()
