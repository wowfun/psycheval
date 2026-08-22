from __future__ import annotations

from tests.peval.reports_html_support import (
    json,
    load_asset_text,
    shutil,
    subprocess,
    unittest,
)


class PevalReportHtmlSavedViewInteractionTests(unittest.TestCase):
    def test_saved_views_render_index_and_apply_selected_views_as_snapshot(
        self,
    ) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
function node() {
  return {
    hidden: true,
    innerHTML: "",
    classList: { toggle() {}, add() {}, remove() {} },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    addEventListener() {},
  };
}
const rail = node();
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-i18n": { textContent: "{}" },
  "peval-token-estimates": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "serve" }) },
  "workspace-views": rail,
};
const documentStub = {
  body: { classList: { toggle() {}, add() {}, remove() {} } },
  addEventListener() {},
  getElementById(id) { return nodes[id] || null; },
  querySelector() { return null; },
  querySelectorAll() { return []; },
};
const context = {
  document: documentStub,
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
  rail,
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(async () => {
  const metric = (key, type, mean) => ({ key, type, count: 2, mean, distribution: { min: mean, q1: mean, p50: mean, q3: mean, p95: mean, max: mean } });
  const metrics = () => [metric("duration_ms", "duration", 1200), metric("tokens", "number", 8), metric("turns", "number", 2), metric("model_duration_ms", "duration", 700), metric("total_tool_calls", "number", 3), metric("tool_error_rate", "percent", 0.25)];
  state.workspaceViews = [
    { name: "Agent slice", filters: { state: "active", search: "", categories: ["frontend"], tags: ["daily"], agents: ["alpha"], models: [], results: ["passed"] }, group_by: "agent", notes: "Context note." },
    { name: "Focused model", filters: { state: "archived", search: "error", categories: ["backend"], tags: [], agents: [], models: ["m1"], results: [] }, group_by: "category", notes: "" },
  ];
  state.workspaceViewSummaries = [
    { name: "Agent slice", matched_count: 2, groups: [{ key: "alpha", label: "alpha", count: 2, metrics: metrics() }] },
    { name: "Focused model", matched_count: 2, groups: [{ key: "backend", label: "backend", count: 2, metrics: metrics() }] },
  ];
  const viewColumns = workspaceViewColumns().map(column => ({
    key: column.key,
    valueType: column.valueType,
    filterable: Boolean(column.filterable),
    editable: Boolean(column.edit),
  }));
  const categoryConfiguration = workspaceViewConfigurationEditValue(state.workspaceViews[0], "categories", ["frontend", "Safety, Eval", "frontend"]);
  const categoryGroupConfiguration = workspaceViewConfigurationEditValue(state.workspaceViews[0], "group_by", "category");
  const controls = renderWorkspaceViewControls();
  renderWorkspaceViewRail();
  const collapsedRail = rail.innerHTML;
  state.workspaceViewSelection = new Set(["server:Focused model"]);
  renderWorkspaceViewRail();
  const partialSelectionRail = rail.innerHTML;
  setFilterValues("workspace-views", "categories", ["frontend"]);
  renderWorkspaceViewRail();
  const categoryRail = rail.innerHTML;
  const categoryRows = workspaceViewRows().map(view => view.name);
  clearFilter("workspace-views", "categories");
  setFilterValues("workspace-views", "tags", ["daily"]);
  renderWorkspaceViewRail();
  const dailyRail = rail.innerHTML;
  const visibleDaily = workspaceViewRows().map(view => view.name);
  setVisibleSelection(workspaceViewRows(), workspaceViewColumns()[0], true);
  const afterVisibleSelect = Array.from(state.workspaceViewSelection);
  setVisibleSelection(workspaceViewRows(), workspaceViewColumns()[0], false);
  const afterVisibleClear = Array.from(state.workspaceViewSelection);
  setFilterValues("workspace-views", "models", ["m1"]);
  renderWorkspaceViewRail();
  const zeroRail = rail.innerHTML;
  clearFilter("workspace-views", "tags");
  clearFilter("workspace-views", "models");
  setFilterValues("workspace-views", "group_by", ["agent", "category"]);
  const groupOrRows = workspaceViewRows().map(view => view.name);
  clearFilter("workspace-views", "group_by");
  state.workspaceViewSelection.clear();
  renderWorkspaceViewRail();
  toggleWorkspaceViewTable("server:Agent slice");
  const firstTableOpenRail = rail.innerHTML;
  toggleWorkspaceViewTable("server:Focused model");
  const bothTablesOpenRail = rail.innerHTML;
  state.workspaceViewSelection = new Set(["server:Agent slice", "server:Focused model"]);
  renderWorkspaceViewRail();
  const selectedRail = rail.innerHTML;
  const downloads = [];
  serveDownload = (kind, body, filename) => { downloads.push({ kind, body, filename }); };
  leaderboardRows = () => [{ source_key: "visible-2" }, { source_key: "visible-1" }];
  const probe = { calls: [] };
  loadCatalogPage = async (changes, options) => { probe.calls.push({ changes, options }); };
  state.leaderboardSummaryGroupBy = "model";
  state.leaderboardSummaryTableOpen = true;
  state.leaderboardSummaryStatistic = "p95";
  exportLeaderboardSummary();
  exportSelectedWorkspaceViews();
  state.catalogQuery = {
    state: "archived", page: 3, page_size: 25, search: "needle",
    sort: "session", direction: "asc", categories: ["frontend"], tags: ["daily"], agents: ["alpha"],
    models: ["m1"], results: ["failed"], views: ["Agent slice"],
  };
  state.rowSelection.add("chosen-source");
  state.selectedSourceKey = "visible-2";
  state.selectedStep = { trialKey: "trial-two", stepId: "7" };
  setFilterValues("workspace-views", "categories", ["frontend"]);
  setFilterValues("workspace-views", "tags", ["daily"]);
  exportCurrentScope("workspace_html");
  state.rowSelection.clear();
  clearFilter("workspace-views", "categories");
  clearFilter("workspace-views", "tags");
  state.rowSelection.add("old-row");
  state.selectedSourceKey = "old-source";
  state.selectedTrial = "old-trial";
  state.selectedStep = { stepId: "old" };
  await applySelectedWorkspaceViews();
  const applyQuery = probe.calls[0].changes;
  const appliedRail = rail.innerHTML;
  const afterApply = {
    applied: Array.from(state.workspaceAppliedViewNames),
    groupBy: state.leaderboardSummaryGroupBy,
    summaryTableOpen: state.leaderboardSummaryTableOpen,
    statistic: state.leaderboardSummaryStatistic,
  };
  state.workspaceViewSelection.delete("server:Agent slice");
  renderWorkspaceViewRail();
  const draftChangedRail = rail.innerHTML;
  state.rowSelection.add("kept-row");
  state.selectedSourceKey = "kept-source";
  state.selectedTrial = "kept-trial";
  state.selectedStep = { trialKey: "kept-trial", stepId: "2" };
  await clearWorkspaceViewConditions();
  const clearQuery = probe.calls[1].changes;
  const canceledRail = rail.innerHTML;
  RENDER_OPTIONS.mode = "report";
  const staticSummaryActions = renderLeaderboardSummaryActions();
  return JSON.stringify({
    controls,
    railHidden: rail.hidden,
    railHtml: rail.innerHTML,
    collapsedRail,
    partialSelectionRail,
    categoryRail,
    categoryRows,
    dailyRail,
    visibleDaily,
    afterVisibleSelect,
    afterVisibleClear,
    zeroRail,
    groupOrRows,
    viewColumns,
    categoryConfiguration,
    categoryGroupConfiguration,
    firstTableOpenRail,
    bothTablesOpenRail,
    selectedRail,
    downloads,
    applyQuery,
    clearQuery,
    appliedRail,
    draftChangedRail,
    canceledRail,
    staticSummaryActions,
    force: probe.calls.map(call => call.options.force),
    afterApply,
    appliedAfterClear: Array.from(state.workspaceAppliedViewNames),
    selectedAfterClear: Array.from(state.workspaceViewSelection),
    groupBy: state.leaderboardSummaryGroupBy,
    summaryTableOpen: state.leaderboardSummaryTableOpen,
    statistic: state.leaderboardSummaryStatistic,
    search: state.search,
    rowSelection: state.rowSelection.size,
    selectedSourceKey: state.selectedSourceKey,
    selectedTrial: state.selectedTrial,
    selectedStep: state.selectedStep,
    table: state.tables.leaderboard,
  });
})()`, context);
result.then(value => console.log(value)).catch(error => { console.error(error); process.exit(1); });
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

        self.assertIn("data-view-save", result["controls"])
        self.assertNotIn("workspace-view-menu", result["controls"])
        self.assertNotIn("data-view-apply-selected", result["controls"])
        self.assertFalse(result["railHidden"])
        self.assertIn("Agent slice", result["railHtml"])
        self.assertIn("Focused model", result["railHtml"])
        self.assertIn("Context note.", result["railHtml"])
        self.assertIn("Source: archived", result["railHtml"])
        self.assertIn("Category: backend", result["railHtml"])
        self.assertIn("Group by: Category", result["railHtml"])
        self.assertIn('data-view-chart="tokens"', result["railHtml"])
        self.assertIn("workspace-view-index-table", result["collapsedRail"])
        self.assertIn("Name", result["collapsedRail"])
        self.assertIn("Category", result["collapsedRail"])
        self.assertIn("Tags", result["collapsedRail"])
        self.assertIn("Models", result["collapsedRail"])
        self.assertIn("Group by", result["collapsedRail"])
        self.assertIn("Other conditions", result["collapsedRail"])
        self.assertIn("Notes", result["collapsedRail"])
        self.assertIn("data-table-select-visible", result["collapsedRail"])
        self.assertIn('title="Context note."', result["collapsedRail"])
        self.assertIn(
            'data-table-column-key="notes" data-value-type="markdown"',
            result["collapsedRail"],
        )
        self.assertIn("data-workspace-views-close", result["collapsedRail"])
        view_column_keys = [column["key"] for column in result["viewColumns"]]
        category_index = view_column_keys.index("categories")
        self.assertEqual(view_column_keys[category_index + 1], "tags")
        self.assertEqual(
            result["viewColumns"][category_index],
            {
                "key": "categories",
                "valueType": "scalar-list",
                "filterable": True,
                "editable": True,
            },
        )
        self.assertIn(
            'categories:\n    - "frontend"\n    - "Safety, Eval"',
            result["categoryConfiguration"],
        )
        self.assertIn('group_by: "category"', result["categoryGroupConfiguration"])
        self.assertEqual(result["collapsedRail"].count("data-table-row-select="), 2)
        self.assertIn('data-partial="true"', result["partialSelectionRail"])
        self.assertEqual(result["categoryRows"], ["Agent slice"])
        self.assertEqual(result["categoryRail"].count('data-workspace-view="'), 1)
        self.assertEqual(result["visibleDaily"], ["Agent slice"])
        self.assertEqual(result["dailyRail"].count('data-workspace-view="'), 1)
        self.assertEqual(
            result["afterVisibleSelect"],
            ["server:Focused model", "server:Agent slice"],
        )
        self.assertEqual(result["afterVisibleClear"], ["server:Focused model"])
        self.assertIn("workspace-view-index", result["zeroRail"])
        self.assertNotIn('data-workspace-view="', result["zeroRail"])
        self.assertEqual(result["groupOrRows"], ["Agent slice", "Focused model"])
        self.assertIn("data-view-apply-selected disabled", result["collapsedRail"])
        self.assertIn("data-view-export-selected disabled", result["collapsedRail"])
        self.assertIn("data-view-delete-selected disabled", result["collapsedRail"])
        self.assertNotIn("data-view-cancel-application", result["collapsedRail"])
        self.assertNotIn('data-view-apply="', result["collapsedRail"])
        self.assertEqual(result["collapsedRail"].count('aria-expanded="false"'), 2)
        self.assertEqual(result["firstTableOpenRail"].count('aria-expanded="true"'), 1)
        self.assertEqual(result["bothTablesOpenRail"].count('aria-expanded="true"'), 2)
        self.assertIn("7 metrics · 1 categories", result["bothTablesOpenRail"])
        self.assertIn(
            'data-value-type="identity" title="Category"', result["bothTablesOpenRail"]
        )
        self.assertIn("Mean · Category", result["bothTablesOpenRail"])
        self.assertIn(
            "backend; Active Duration; Mean 1.2s; n=2",
            result["bothTablesOpenRail"],
        )
        self.assertNotIn("data-view-apply-selected disabled", result["selectedRail"])
        self.assertNotIn("data-view-export-selected disabled", result["selectedRail"])
        self.assertNotIn("data-view-delete-selected disabled", result["selectedRail"])
        self.assertEqual(
            result["downloads"],
            [
                {
                    "kind": "summary_xlsx",
                    "body": {
                        "kind": "summary_xlsx",
                        "summary": {
                            "scope": "leaderboard",
                            "source_keys": ["visible-2", "visible-1"],
                            "query": {
                                "state": "active",
                                "search": "",
                                "sort": "last_turn_end",
                                "direction": "desc",
                                "categories": [],
                                "tags": [],
                                "agents": [],
                                "models": [],
                                "tasks": [],
                                "jobs": [],
                                "providers": [],
                                "results": [],
                                "views": [],
                                "browser_views": [],
                            },
                            "group_by": "model",
                            "statistic": "p95",
                        },
                    },
                    "filename": "peval-leaderboard-summary.xlsx",
                },
                {
                    "kind": "summary_xlsx",
                    "body": {
                        "kind": "summary_xlsx",
                        "summary": {
                            "scope": "saved_views",
                            "views": ["Agent slice", "Focused model"],
                            "browser_views": [],
                        },
                    },
                    "filename": "peval-saved-views.xlsx",
                },
                {
                    "kind": "workspace_html",
                    "body": {
                        "kind": "workspace_html",
                        "browser_views": [],
                        "query": {
                            "state": "archived",
                            "search": "needle",
                            "sort": "session",
                            "direction": "asc",
                            "categories": ["frontend"],
                            "tags": ["daily"],
                            "agents": ["alpha"],
                            "models": ["m1"],
                            "tasks": [],
                            "jobs": [],
                            "providers": [],
                            "results": ["failed"],
                            "views": ["Agent slice"],
                            "browser_views": [],
                        },
                        "selected_source_keys": ["chosen-source"],
                        "presentation": {
                            "summary_group_by": "model",
                            "summary_statistic": "p95",
                            "summary_table_open": True,
                            "selected_source_key": "visible-2",
                            "selected_step_id": "7",
                            "leaderboard_columns": {
                                "version": 1,
                                "order": [
                                    "source_category",
                                    "source_tags",
                                    "job_name",
                                    "task_name",
                                    "workspace_reports",
                                    "agent",
                                    "model",
                                    "model_provider",
                                    "reward",
                                    "status",
                                    "finished_at_ms",
                                    "duration_ms",
                                    "ttft_ms",
                                    "tps",
                                    "turns",
                                    "total_tool_calls",
                                    "tool_error_rate",
                                    "tokens",
                                    "cache_hit_rate",
                                    "cost_usd",
                                    "analysis_count",
                                    "notes",
                                    "session_id",
                                ],
                                "visibility": {},
                            },
                            "visible_view_names": ["Agent slice"],
                            "workspace_view_filters": {
                                "categories": ["frontend"],
                                "tags": ["daily"],
                                "models": [],
                                "tasks": [],
                                "jobs": [],
                                "providers": [],
                                "group_by": [],
                            },
                            "open_view_tables": ["Agent slice"],
                        },
                    },
                    "filename": "peval-workspace-snapshot.html",
                },
            ],
        )
        self.assertEqual(
            result["appliedRail"].count(
                "workspace-view-card leaderboard-summary applied"
            ),
            2,
        )
        self.assertEqual(
            result["draftChangedRail"].count(
                "workspace-view-card leaderboard-summary applied"
            ),
            2,
        )
        self.assertEqual(
            result["applyQuery"],
            {
                "state": "all",
                "page": 1,
                "page_size": 100,
                "search": "",
                "sort": "last_turn_end",
                "direction": "desc",
                "categories": [],
                "tags": [],
                "agents": [],
                "models": [],
                "tasks": [],
                "jobs": [],
                "providers": [],
                "results": [],
                "views": ["Agent slice", "Focused model"],
            },
        )
        self.assertEqual(
            result["afterApply"]["applied"],
            ["server:Agent slice", "server:Focused model"],
        )
        self.assertEqual(result["afterApply"]["groupBy"], "model")
        self.assertTrue(result["afterApply"]["summaryTableOpen"])
        self.assertEqual(result["afterApply"]["statistic"], "p95")
        self.assertEqual(result["force"], [True, True])
        self.assertEqual(
            result["clearQuery"],
            {
                "state": "active",
                "page": 1,
                "page_size": 100,
                "search": "",
                "sort": "last_turn_end",
                "direction": "desc",
                "categories": [],
                "tags": [],
                "agents": [],
                "models": [],
                "tasks": [],
                "jobs": [],
                "providers": [],
                "results": [],
                "views": [],
            },
        )
        self.assertEqual(result["groupBy"], "agent")
        self.assertFalse(result["summaryTableOpen"])
        self.assertEqual(result["statistic"], "mean")
        self.assertEqual(
            result["search"],
            {"query": "", "scope": "visible", "normalSourceMode": "active"},
        )
        self.assertEqual(result["appliedAfterClear"], [])
        self.assertNotIn("data-summary-export-xlsx", result["staticSummaryActions"])
        self.assertNotIn("data-view-save", result["staticSummaryActions"])
        self.assertEqual(result["selectedAfterClear"], [])
        self.assertEqual(result["rowSelection"], 1)
        self.assertEqual(result["selectedSourceKey"], "kept-source")
        self.assertEqual(result["selectedTrial"], "kept-trial")
        self.assertEqual(
            result["selectedStep"], {"trialKey": "kept-trial", "stepId": "2"}
        )
        self.assertEqual(
            result["table"],
            {
                "sort": "finished_at_ms",
                "direction": "desc",
                "filters": {
                    "source_category": [],
                    "source_tags": [],
                    "agent": [],
                    "model": [],
                    "task_name": [],
                    "job_name": [],
                    "model_provider": [],
                    "status": [],
                },
            },
        )

    def test_saved_view_snapshot_consumes_category_filters_and_grouping(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        snapshot = {
            "views": [
                {
                    "name": "Frontend",
                    "filters": {"categories": ["frontend"], "tags": ["daily"]},
                    "group_by": "category",
                    "notes": "",
                },
                {
                    "name": "Backend",
                    "filters": {"categories": ["backend"]},
                    "group_by": "agent",
                    "notes": "",
                },
            ],
            "view_summaries": [
                {
                    "name": "Frontend",
                    "matched_count": 1,
                    "groups": [
                        {
                            "key": "frontend",
                            "label": "frontend",
                            "count": 1,
                            "metrics": [],
                        }
                    ],
                }
            ],
            "presentation": {
                "summary_group_by": "category",
                "summary_statistic": "mean",
                "summary_table_open": False,
                "selected_source_key": None,
                "selected_step_id": None,
                "leaderboard_columns": {
                    "version": 1,
                    "order": [],
                    "visibility": {},
                },
                "workspace_view_filters": {
                    "categories": ["frontend"],
                    "tags": [],
                    "models": [],
                    "group_by": ["category"],
                },
                "open_view_tables": ["Frontend"],
            },
            "source_trial_keys": {},
        }
        script = """
const vm = require("vm");
const asset = __ASSET__;
const snapshot = __SNAPSHOT__;
const rail = {
  hidden: true,
  innerHTML: "",
  classList: { toggle() {}, add() {}, remove() {} },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  addEventListener() {},
};
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-i18n": { textContent: "{}" },
  "peval-token-estimates": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "workspace_snapshot" }) },
  "peval-workspace-snapshot": { textContent: JSON.stringify(snapshot) },
  "workspace-views": rail,
};
const context = {
  document: {
    body: { classList: { toggle() {}, add() {}, remove() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
  },
  window: { addEventListener() {} },
  console, JSON, Number, String, Object, Math, Date, Set, Array, RegExp,
  rail,
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(() => {
  const views = workspaceViews();
  const rows = workspaceViewRows();
  const columns = workspaceViewColumns();
  renderWorkspaceViewRail();
  return JSON.stringify({
    filters: state.tables["workspace-views"].filters,
    groups: views.map(view => ({ name: view.name, groupBy: view.group_by, categories: view.filters.categories })),
    rows: rows.map(view => view.name),
    columnKeys: columns.map(column => column.key),
    editable: columns.map(column => Boolean(column.edit)),
    railHidden: rail.hidden,
    railHtml: rail.innerHTML,
  });
})()`, context);
console.log(result);
""".replace("__ASSET__", json.dumps(asset)).replace(
            "__SNAPSHOT__", json.dumps(snapshot)
        )
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

        self.assertEqual(
            result["filters"],
            {
                "categories": ["frontend"],
                "tags": [],
                "models": [],
                "tasks": [],
                "jobs": [],
                "providers": [],
                "group_by": ["category"],
            },
        )
        self.assertEqual(
            result["groups"],
            [
                {
                    "name": "Backend",
                    "groupBy": "agent",
                    "categories": ["backend"],
                },
                {
                    "name": "Frontend",
                    "groupBy": "category",
                    "categories": ["frontend"],
                },
            ],
        )
        self.assertEqual(result["rows"], ["Frontend"])
        category_index = result["columnKeys"].index("categories")
        self.assertEqual(result["columnKeys"][category_index + 1], "tags")
        self.assertFalse(any(result["editable"]))
        self.assertFalse(result["railHidden"])
        self.assertIn("Category: frontend", result["railHtml"])
        self.assertIn("Group by: Category", result["railHtml"])
        self.assertIn(
            'data-view-table-toggle="server:Frontend" aria-expanded="true"',
            result["railHtml"],
        )
        self.assertNotIn("data-table-select-visible", result["railHtml"])
        self.assertNotIn("data-view-apply-selected", result["railHtml"])

    def test_saved_view_save_coalesces_stale_refresh_and_renders_singleton_rail(
        self,
    ) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const nameInput = { value: "Daily" };
const notesInput = { value: "Review this cohort." };
const workspaceLocation = { value: "workspace", checked: true };
const dialog = {
  hidden: false,
  querySelector(selector) {
    if (selector === "[data-view-name-input]") return nameInput;
    if (selector === "[data-view-notes-input]") return notesInput;
    if (selector === '[name="view_location"]:checked') return workspaceLocation;
    return null;
  },
};
const rail = {
  hidden: true,
  innerHTML: "",
  classList: { toggle() {}, add() {}, remove() {} },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  addEventListener() {},
};
let resolveStale;
const staleList = new Promise(resolve => { resolveStale = resolve; });
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-i18n": { textContent: "{}" },
  "peval-token-estimates": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "serve" }) },
  "workspace-views": rail,
};
const context = {
  document: {
    body: { classList: { toggle() {}, add() {}, remove() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector(selector) { return selector === "[data-view-save-dialog]" ? dialog : null; },
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
  Promise,
  localStorage: { getItem() { return null; }, setItem() {} },
  rail,
  dialog,
  staleList,
  resolveStale,
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(async () => {
  const view = { name: "Daily", filters: {}, group_by: "agent", notes: "Review this cohort." };
  const probe = { listCalls: 0, status: null };
  serveApi = async (path, options = {}) => {
    if (path === "/api/views" && options.method === "POST") return { views: [view] };
    if (path === "/api/views") {
      probe.listCalls += 1;
      return probe.listCalls === 1 ? staleList : { views: [view] };
    }
    if (path === "/api/views/summary") {
      return { generation: 7, views: [{ name: "Daily", matched_count: 1, groups: [] }] };
    }
    throw new Error("unexpected request: " + path);
  };
  setServeStatus = (message, error) => { probe.status = { message, error: Boolean(error) }; };
  const initialRefresh = refreshWorkspaceViews();
  await Promise.resolve();
  const saved = saveWorkspaceView(dialog);
  await Promise.resolve();
  resolveStale({ views: [] });
  await Promise.all([initialRefresh, saved]);
  return JSON.stringify({
    listCalls: probe.listCalls,
    names: state.workspaceViews.map(view => view.name),
    summaries: state.workspaceViewSummaries,
    railHidden: rail.hidden,
    railHtml: rail.innerHTML,
    status: probe.status,
  });
})()`, context);
result.then(value => console.log(value)).catch(error => { console.error(error); process.exit(1); });
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

        self.assertEqual(result["listCalls"], 2, result)
        self.assertEqual(result["names"], ["Daily"])
        self.assertEqual(
            result["summaries"], [{"name": "Daily", "matched_count": 1, "groups": []}]
        )
        self.assertFalse(result["railHidden"])
        self.assertIn("Daily", result["railHtml"])
        self.assertIn("1 matching sessions", result["railHtml"])
        self.assertIn(
            'data-view-table-toggle="server:Daily" aria-expanded="false"',
            result["railHtml"],
        )
        self.assertNotIn("workspace-view-menu", result["railHtml"])
        self.assertEqual(result["status"], {"message": "View saved", "error": False})

    def test_saved_view_dialog_confirms_then_retries_atomic_overwrite(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const nameInput = { value: "Daily" };
const notesInput = { value: "Original notes" };
const configuration = { innerHTML: "" };
const workspaceLocation = { value: "workspace", checked: true };
const browserLocation = { value: "browser", checked: false };
const dialog = {
  hidden: true,
  dataset: {},
  querySelector(selector) {
    if (selector === "[data-view-name-input]") return nameInput;
    if (selector === "[data-view-notes-input]") return notesInput;
    if (selector === "[data-view-current-configuration]") return configuration;
    if (selector === '[name="view_location"][value="workspace"]') return workspaceLocation;
    if (selector === '[name="view_location"][value="browser"]') return browserLocation;
    if (selector === '[name="view_location"]:checked') return workspaceLocation;
    return null;
  },
  querySelectorAll() { return []; },
  addEventListener() {},
};
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-i18n": { textContent: JSON.stringify({ view_overwrite_confirm: "Replace {name}?", view_saved: "Saved" }) },
  "peval-token-estimates": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "serve" }) },
};
const context = {
  document: {
    body: { classList: { add() {}, remove() {}, toggle() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector(selector) { return selector === "[data-view-save-dialog]" ? dialog : null; },
    querySelectorAll() { return []; },
  },
  window: { addEventListener() {}, confirm(message) { probe.confirm = message; return true; } },
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
  dialog,
  configuration,
  nameInput,
  notesInput,
};
const probe = { calls: [] };
context.probe = probe;
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(async () => {
  state.catalogQuery = { state: "active", search: "needle", categories: ["frontend"], tags: ["daily"], agents: ["alpha"], models: [], results: ["passed"] };
  state.leaderboardSummaryGroupBy = "category";
  openWorkspaceViewSaveDialog();
  const savedConfiguration = configuration.innerHTML;
  const defaultName = nameInput.value;
  const allDefaultName = workspaceViewDefaultName({ tags: [] }, "overall");
  const categoryDefaultName = workspaceViewDefaultName({ tags: [] }, "category");
  const longDefaultName = workspaceViewDefaultName({ tags: ["x".repeat(160)] }, "model");
  nameInput.value = "Daily";
  notesInput.value = "Original notes";
  serveApi = async (path, options) => {
    probe.calls.push({ path, body: options.body });
    if (probe.calls.length === 1) throw new Error("saved view already exists: Daily");
    return { views: [{ name: "Daily", filters: options.body.filters, group_by: options.body.group_by, notes: "Original notes" }] };
  };
  refreshWorkspaceViews = async (...args) => { probe.refreshArgs = args; };
  setServeStatus = (message, error) => { probe.status = { message, error: Boolean(error) }; };
  await saveWorkspaceView(dialog);
  return JSON.stringify({ calls: probe.calls, confirm: probe.confirm, refreshArgs: probe.refreshArgs, status: probe.status, hidden: dialog.hidden, views: state.workspaceViews, savedConfiguration, defaultName, allDefaultName, categoryDefaultName, longDefaultName });
})()`, context);
result.then(value => console.log(value)).catch(error => { console.error(error); process.exit(1); });
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

        self.assertIn("confirm", result, result)
        self.assertEqual(result["confirm"], "Replace Daily?")
        self.assertIn(
            "<dt>Search sessions</dt><dd>needle</dd>", result["savedConfiguration"]
        )
        self.assertIn(
            "<dt>Category</dt><dd>frontend</dd>", result["savedConfiguration"]
        )
        self.assertIn("<dt>Tags</dt><dd>daily</dd>", result["savedConfiguration"])
        self.assertIn("<dt>Agent</dt><dd>alpha</dd>", result["savedConfiguration"])
        self.assertIn("<dt>Result</dt><dd>passed</dd>", result["savedConfiguration"])
        self.assertIn(
            "<dt>Group by</dt><dd>Category</dd>", result["savedConfiguration"]
        )
        self.assertEqual(result["defaultName"], "daily - category")
        self.assertEqual(result["allDefaultName"], "All - overall")
        self.assertEqual(result["categoryDefaultName"], "All - category")
        self.assertEqual(len(result["longDefaultName"]), 120)
        self.assertTrue(result["longDefaultName"].endswith(" - model"))
        self.assertNotIn("<dt>Source</dt>", result["savedConfiguration"])
        self.assertNotIn("<dt>Model</dt>", result["savedConfiguration"])
        self.assertEqual(
            [call["path"] for call in result["calls"]], ["/api/views", "/api/views"]
        )
        self.assertFalse(result["calls"][0]["body"]["overwrite"])
        self.assertTrue(result["calls"][1]["body"]["overwrite"])
        self.assertEqual(result["calls"][1]["body"]["filters"]["search"], "needle")
        self.assertEqual(
            result["calls"][1]["body"]["filters"]["categories"], ["frontend"]
        )
        self.assertEqual(result["calls"][1]["body"]["filters"]["tags"], ["daily"])
        self.assertEqual(result["calls"][1]["body"]["group_by"], "category")
        self.assertEqual(
            result["calls"][1]["body"]["filters"],
            {
                "search": "needle",
                "categories": ["frontend"],
                "tags": ["daily"],
                "agents": ["alpha"],
                "results": ["passed"],
            },
        )
        self.assertEqual(result["refreshArgs"], [])
        self.assertEqual(result["status"], {"message": "Saved", "error": False})
        self.assertTrue(result["hidden"])
        self.assertEqual(result["views"][0]["name"], "Daily")

    def test_html_submenu_outside_click_closer_only_targets_menus(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const exportMenu = { id: "export", open: true };
const filterMenu = { id: "filter", open: true };
const timelineSection = { id: "timeline", open: true };
const handlers = [];
const documentStub = {
  body: { classList: { toggle() {} } },
  addEventListener(type, handler, options) {
    handlers.push({ type, handler, capture: options === true || options?.capture === true });
  },
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll(selector) {
    if (selector !== ".export-menu[open],.filter-control[open],.column-control[open]") {
      throw new Error(`unexpected selector: ${selector}`);
    }
    return [exportMenu, filterMenu].filter(details => details.open);
  },
};
const context = {
  document: documentStub,
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
  exportMenu,
  filterMenu,
  timelineSection,
  handlers,
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`
  bindGlobalControls();
  const clickHandler = handlers.find(item => item.type === "click" && item.capture).handler;
  filterMenu.open = true;
  exportMenu.open = true;
  clickHandler({ target: { closest: selector => selector === SUBMENU_DETAILS_SELECTOR ? exportMenu : null } });
  const insideExport = { exportOpen: exportMenu.open, filterOpen: filterMenu.open, timelineOpen: timelineSection.open };
  filterMenu.open = true;
  exportMenu.open = true;
  clickHandler({ target: { closest: () => null } });
  const outside = { exportOpen: exportMenu.open, filterOpen: filterMenu.open, timelineOpen: timelineSection.open };
  JSON.stringify({ insideExport, outside, clickHandlerCapture: Boolean(clickHandler) });
`, context);
console.log(result);
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

        self.assertEqual(
            result["insideExport"],
            {"exportOpen": True, "filterOpen": False, "timelineOpen": True},
        )
        self.assertEqual(
            result["outside"],
            {"exportOpen": False, "filterOpen": False, "timelineOpen": True},
        )
        self.assertTrue(result["clickHandlerCapture"])
