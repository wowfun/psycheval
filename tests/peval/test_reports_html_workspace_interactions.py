from __future__ import annotations

from tests.peval.reports_html_support import (
    json,
    load_asset_text,
    shutil,
    subprocess,
    unittest,
)


class PevalReportHtmlWorkspaceInteractionTests(unittest.TestCase):
    def test_sqlite_db_form_manages_adapter_defaults_in_place(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
function interactiveControl(value = "") {
  return {
    value,
    disabled: false,
    title: "",
    listeners: {},
    addEventListener(type, handler) { this.listeners[type] = handler; }
  };
}
const options = [
  { value: "auto", dataset: {} },
  { value: "hermes", dataset: { defaultDb: "/old/hermes.db" } },
  { value: "opencode", dataset: {} }
];
const select = interactiveControl("auto");
select.tagName = "SELECT";
select.options = options;
const field = interactiveControl("");
const saveButton = interactiveControl();
const clearButton = interactiveControl();
const picker = { hidden: true, innerHTML: "" };
const form = {
  dataset: { sourceKind: "db" },
  reset() { select.value = "auto"; field.value = ""; },
  querySelector(selector) {
    if (selector === '[name="adapter"]') return select;
    if (selector === '[name="db"]') return field;
    if (selector === "[data-adapter-default-db-save]") return saveButton;
    if (selector === "[data-adapter-default-db-clear]") return clearButton;
    if (selector === "[data-db-session-picker]") return picker;
    return null;
  },
  querySelectorAll() { return []; }
};
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-token-estimates": { textContent: "{}" },
  "peval-i18n": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [], adapter_defaults: { hermes: "/old/hermes.db" } }) }
};
const calls = [];
const context = {
  document: {
    body: { classList: { add() {}, remove() {}, toggle() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector() { return null; },
    querySelectorAll(selector) {
      if (selector === '[data-source-add-form][data-source-kind="db"]') return [form];
      if (selector === 'select[name="adapter"] option') return options;
      return [];
    }
  },
  window: { addEventListener() {} },
  console, JSON, Number, String, Object, Math, Date, Set, Array, RegExp,
  form, select, field, saveButton, clearButton, options, picker, calls
};
vm.createContext(context);
vm.runInContext(asset, context);
vm.runInContext(`(async () => {
  selectedAdapterValue = () => select.value === "auto" ? undefined : select.value;
  formPayload = () => ({ db: field.value, adapter: selectedAdapterValue(form) });
  setServeStatus = () => {};
  showServeNotice = () => {};
  renderDbSessionPicker = () => {};
  applyServeMutationPayload = () => {};
  showImportResultsSummary = () => {};
  serveApi = async (path, options = {}) => {
    calls.push({ path, body: options.body || null });
    if (path === "/api/config/adapter-default-db") {
      if (options.body.default_db_path) {
        return { adapter: options.body.adapter, default_db_path: "/resolved/new.db", adapter_defaults: { hermes: "/resolved/new.db" } };
      }
      return { adapter: options.body.adapter, default_db_path: null, adapter_defaults: {} };
    }
    if (path === "/api/db-sessions") return { adapter: "opencode", db: options.body.db, sessions: [] };
    if (path === "/api/sources") return { sources: [], import_results: [] };
    throw new Error("unexpected path " + path);
  };
  bindAdapterDefaultDbControls();
  const initial = {
    saveDisabled: saveButton.disabled,
    clearDisabled: clearButton.disabled,
    saveBound: typeof saveButton.listeners.click === "function",
    clearBound: typeof clearButton.listeners.click === "function"
  };
  select.value = "hermes";
  select.listeners.change();
  const selected = { path: field.value, saveDisabled: saveButton.disabled, clearDisabled: clearButton.disabled };
  field.value = "/new/hermes.db";
  field.listeners.input();
  await saveAdapterDefaultDb(form, field.value);
  const saveCall = calls.find(call => call.path === "/api/config/adapter-default-db");
  const afterSave = { path: field.value, defaults: { ...state.adapterDefaults }, saveCall };
  await saveAdapterDefaultDb(form, "");
  const defaultCalls = calls.filter(call => call.path === "/api/config/adapter-default-db");
  const afterClear = {
    path: field.value,
    defaults: { ...state.adapterDefaults },
    clearDisabled: clearButton.disabled,
    clearCall: defaultCalls[1]
  };
  select.value = "auto";
  field.value = "/tmp/opencode.db";
  syncAdapterDefaultDbControls(form);
  await inspectDbSessions(form);
  const afterInspect = { adapter: select.value, path: field.value, saveDisabled: saveButton.disabled, clearDisabled: clearButton.disabled };
  await submitServeSourceForm(form);
  const afterReset = { adapter: select.value, path: field.value, saveDisabled: saveButton.disabled, clearDisabled: clearButton.disabled };
  console.log(JSON.stringify({ initial, selected, afterSave, afterClear, afterInspect, afterReset }));
})().catch(error => { console.error(error && error.stack || error); process.exitCode = 1; });`, context);
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
            result["initial"],
            {
                "saveDisabled": True,
                "clearDisabled": True,
                "saveBound": True,
                "clearBound": True,
            },
        )
        self.assertEqual(
            result["selected"],
            {"path": "/old/hermes.db", "saveDisabled": False, "clearDisabled": False},
        )
        self.assertEqual(
            result["afterSave"]["saveCall"],
            {
                "path": "/api/config/adapter-default-db",
                "body": {"adapter": "hermes", "default_db_path": "/new/hermes.db"},
            },
        )
        self.assertEqual(result["afterSave"]["path"], "/resolved/new.db")
        self.assertEqual(
            result["afterSave"]["defaults"], {"hermes": "/resolved/new.db"}
        )
        self.assertEqual(
            result["afterClear"]["clearCall"],
            {
                "path": "/api/config/adapter-default-db",
                "body": {"adapter": "hermes", "default_db_path": ""},
            },
        )
        self.assertEqual(result["afterClear"]["path"], "/resolved/new.db")
        self.assertEqual(result["afterClear"]["defaults"], {})
        self.assertTrue(result["afterClear"]["clearDisabled"])
        self.assertEqual(
            result["afterInspect"],
            {
                "adapter": "opencode",
                "path": "/tmp/opencode.db",
                "saveDisabled": False,
                "clearDisabled": True,
            },
        )
        self.assertEqual(
            result["afterReset"],
            {
                "adapter": "auto",
                "path": "",
                "saveDisabled": True,
                "clearDisabled": True,
            },
        )

    def test_comparison_panel_rerenders_preserve_scroll_positions(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const context = {
  leaderboardWrap: { scrollTop: 96, scrollLeft: 42, addEventListener() {} },
  overviewList: { scrollTop: 128, scrollLeft: 7, addEventListener() {} },
  document: {
    body: { classList: { toggle() {} } },
    addEventListener() {},
    getElementById: () => null,
    querySelector(selector) {
      if (selector === "#leaderboard .table-wrap") return context.leaderboardWrap;
      if (selector === "#trajectory-overview .trajectory-overview-list") return context.overviewList;
      return null;
    },
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
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`
  const calls = [];
  leaderboardRows = () => [{ trial_key: "trial:one" }];
  syncSelectionWithVisibleRows = rows => calls.push(["sync", rows.length]);
  renderLeaderboard = rows => {
    calls.push(["leaderboard", rows.length]);
    globalThis.leaderboardWrap = { scrollTop: 0, scrollLeft: 0, addEventListener() {} };
  };
  renderLeaderboardSummary = rows => calls.push(["summary", rows.length]);
  renderTrajectoryOverview = rows => {
    calls.push(["overview", rows.length]);
    globalThis.overviewList = { scrollTop: 0, scrollLeft: 0, addEventListener() {} };
  };
  renderTrace = () => calls.push(["trace"]);
  renderStepDrawer = () => calls.push(["drawer"]);
  renderComparisonPanels();
  JSON.stringify({
    leaderboardTop: leaderboardWrap.scrollTop,
    leaderboardLeft: leaderboardWrap.scrollLeft,
    overviewTop: overviewList.scrollTop,
    overviewLeft: overviewList.scrollLeft,
    calls
  });
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

        self.assertEqual(result["leaderboardTop"], 96)
        self.assertEqual(result["leaderboardLeft"], 42)
        self.assertEqual(result["overviewTop"], 128)
        self.assertEqual(result["overviewLeft"], 0)
        self.assertEqual(
            result["calls"],
            [["sync", 1], ["leaderboard", 1], ["overview", 1], ["trace"], ["drawer"]],
        )

    def test_serve_detail_selection_preserves_comparison_scroll_positions(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const report = {
  schema_version: 19,
  includes: ["core"],
  annotations: {},
  trajectory: [{ trajectory_id: "trial:late", session_id: "late", steps: [], final_metrics: {} }],
  trajectory_meta: [{ trial_key: "trial:late", status: "passed", steps: [] }]
};
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-i18n": { textContent: "{}" },
  "peval-token-estimates": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [] }) },
  "report-notes": { innerHTML: "" },
};
const comparison = {};
Object.defineProperty(comparison, "innerHTML", {
  get() { return this.value || ""; },
  set(value) {
    this.value = value;
    context.leaderboardWrap = { scrollTop: 0, scrollLeft: 0, addEventListener() {} };
    context.overviewList = { scrollTop: 0, scrollLeft: 0, addEventListener() {} };
  }
});
nodes.comparison = comparison;
const context = {
  leaderboardWrap: { scrollTop: 240, scrollLeft: 44, addEventListener() {} },
  overviewList: { scrollTop: 320, scrollLeft: 0, addEventListener() {} },
  document: {
    body: { classList: { toggle() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector(selector) {
      if (selector === "#leaderboard .table-wrap") return context.leaderboardWrap;
      if (selector === "#trajectory-overview .trajectory-overview-list") return context.overviewList;
      return null;
    },
    querySelectorAll() { return []; },
  },
  window: { addEventListener() {} },
  report,
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
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(() => {
  syncSelectedSourceFromView = () => {};
  renderServeSources = () => {};
  bindGlobalControls = () => {};
  scheduleServeStartupPoll = () => {};
  leaderboardRows = () => [{ trial_key: "trial:late", source_key: "source-late" }];
  syncSelectionWithVisibleRows = () => {};
  renderLeaderboard = () => {};
  renderTrajectoryOverview = () => {};
  renderTrace = () => {};
  renderStepDrawer = () => {};
  applyServeDetailSelection("source-late", report, "revision-2");
  return JSON.stringify({
    leaderboardTop: leaderboardWrap.scrollTop,
    leaderboardLeft: leaderboardWrap.scrollLeft,
    overviewTop: overviewList.scrollTop
  });
})()`, context);
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

        self.assertEqual(result["leaderboardTop"], 240)
        self.assertEqual(result["leaderboardLeft"], 44)
        self.assertEqual(result["overviewTop"], 320)

    def test_comparison_panel_scroll_progress_syncs_in_both_directions(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const writes = { leaderboard: [], overview: [] };
function makeNode(name, scrollTop, scrollLeft, scrollHeight, clientHeight) {
  const node = {
    handlers: [],
    scrollHeight,
    clientHeight,
    addEventListener(type, handler) {
      if (type === "scroll") this.handlers.push(handler);
    },
    triggerScroll() {
      this.handlers.forEach(handler => handler({ target: this }));
    }
  };
  let top = scrollTop;
  let left = scrollLeft;
  Object.defineProperty(node, "scrollTop", {
    get() { return top; },
    set(value) {
      top = value;
      writes[name].push({ field: "top", value });
      if (name === "overview" && context.triggerOverviewNested) {
        context.triggerOverviewNested = false;
        node.triggerScroll();
      }
      if (name === "leaderboard" && context.triggerLeaderboardNested) {
        context.triggerLeaderboardNested = false;
        node.triggerScroll();
      }
    }
  });
  Object.defineProperty(node, "scrollLeft", {
    get() { return left; },
    set(value) {
      left = value;
      writes[name].push({ field: "left", value });
    }
  });
  return node;
}
const context = {
  leaderboardWrap: makeNode("leaderboard", 250, 77, 1200, 200),
  overviewList: makeNode("overview", 0, 11, 2200, 200),
  triggerOverviewNested: false,
  triggerLeaderboardNested: false,
  rafCalls: 0,
  writes,
  document: {
    body: { classList: { toggle() {} } },
    addEventListener() {},
    getElementById: () => null,
    querySelector(selector) {
      if (selector === "#leaderboard .table-wrap") return context.leaderboardWrap;
      if (selector === "#trajectory-overview .trajectory-overview-list") return context.overviewList;
      return null;
    },
  },
  requestAnimationFrame(callback) {
    context.rafCalls += 1;
    callback();
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
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`
  bindComparisonScrollSync();
  const listenerCounts = {
    leaderboard: leaderboardWrap.handlers.length,
    overview: overviewList.handlers.length
  };

  globalThis.triggerOverviewNested = true;
  leaderboardWrap.triggerScroll();
  const afterLeaderboardScroll = {
    leaderboardTop: leaderboardWrap.scrollTop,
    leaderboardLeft: leaderboardWrap.scrollLeft,
    overviewTop: overviewList.scrollTop,
    overviewLeft: overviewList.scrollLeft,
    leaderboardWrites: writes.leaderboard.slice(),
    overviewWrites: writes.overview.slice(),
    syncingReleased: state.comparisonScrollSyncing === false
  };

  writes.leaderboard.length = 0;
  writes.overview.length = 0;
  overviewList.scrollTop = 1500;
  writes.overview.length = 0;
  globalThis.triggerLeaderboardNested = true;
  overviewList.triggerScroll();
  const afterOverviewScroll = {
    leaderboardTop: leaderboardWrap.scrollTop,
    leaderboardLeft: leaderboardWrap.scrollLeft,
    overviewTop: overviewList.scrollTop,
    overviewLeft: overviewList.scrollLeft,
    leaderboardWrites: writes.leaderboard.slice(),
    overviewWrites: writes.overview.slice(),
    syncingReleased: state.comparisonScrollSyncing === false
  };

  JSON.stringify({ listenerCounts, afterLeaderboardScroll, afterOverviewScroll, rafCalls });
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

        self.assertEqual(result["listenerCounts"], {"leaderboard": 1, "overview": 1})
        self.assertEqual(result["afterLeaderboardScroll"]["leaderboardTop"], 250)
        self.assertEqual(result["afterLeaderboardScroll"]["leaderboardLeft"], 77)
        self.assertEqual(result["afterLeaderboardScroll"]["overviewTop"], 500)
        self.assertEqual(result["afterLeaderboardScroll"]["overviewLeft"], 11)
        self.assertEqual(result["afterLeaderboardScroll"]["leaderboardWrites"], [])
        self.assertEqual(
            result["afterLeaderboardScroll"]["overviewWrites"],
            [{"field": "top", "value": 500}],
        )
        self.assertTrue(result["afterLeaderboardScroll"]["syncingReleased"])
        self.assertEqual(result["afterOverviewScroll"]["leaderboardTop"], 750)
        self.assertEqual(result["afterOverviewScroll"]["leaderboardLeft"], 77)
        self.assertEqual(result["afterOverviewScroll"]["overviewTop"], 1500)
        self.assertEqual(result["afterOverviewScroll"]["overviewLeft"], 11)
        self.assertEqual(
            result["afterOverviewScroll"]["leaderboardWrites"],
            [{"field": "top", "value": 750}],
        )
        self.assertEqual(result["afterOverviewScroll"]["overviewWrites"], [])
        self.assertTrue(result["afterOverviewScroll"]["syncingReleased"])
        self.assertGreaterEqual(result["rafCalls"], 4)

    def test_workspace_report_cells_render_zero_one_many_and_isolate_clicks(
        self,
    ) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const listeners = { control: [], select: [] };
const probe = { opened: null };
const control = {
  addEventListener(type, handler) { if (type === "click") listeners.control.push(handler); }
};
const select = {
  value: "20260710-130000-000000",
  addEventListener(type, handler) { if (type === "change") listeners.select.push(handler); },
};
const target = {
  querySelectorAll(selector) {
    if (selector === "[data-workspace-report-control]") return [control];
    if (selector === "[data-report-preview]") return [];
    if (selector === "[data-report-preview-select]") return [select];
    if (selector === "[data-report-attach]") return [];
    return [];
  }
};
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-token-estimates": { textContent: "{}" },
  "peval-i18n": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [], reports: [] }) }
};
const context = {
  document: {
    body: { classList: { add() {}, remove() {}, toggle() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; }
  },
  window: { addEventListener() {} },
  console, JSON, Number, String, Object, Math, Date, Set, Array, RegExp,
  target, listeners, probe, select
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(() => {
  state.selectedTrial = "trial-before";
  state.workspaceReports = [
    { report_id: "20260710-120000-000000", filename: "one.md", format: "markdown", source_keys: ["cell-a"] },
    { report_id: "20260710-125000-000000", filename: "older.html", format: "html", source_keys: ["cell-b"] },
    { report_id: "20260710-130000-000000", filename: "newer.md", format: "markdown", source_keys: ["cell-b"] }
  ];
  openWorkspaceReportReader = reportId => { probe.opened = reportId; };
  const zero = renderWorkspaceReportCell({ source_key: "cell-none" });
  const one = renderWorkspaceReportCell({ source_key: "cell-a" });
  const many = renderWorkspaceReportCell({ source_key: "cell-b" });
  const columnKeys = leaderboardColumns().map(column => column.key);
  bindWorkspaceReportLeaderboardControls(target);
  const clickEvent = { preventDefault() { this.prevented = true; }, stopPropagation() { this.stopped = true; } };
  const changeEvent = { stopPropagation() { this.stopped = true; } };
  listeners.control.forEach(handler => handler(clickEvent));
  listeners.select.forEach(handler => handler(changeEvent));
  return JSON.stringify({ zero, one, many, columnKeys, clickEvent, changeEvent, probe, selectValue: select.value, selectedTrial: state.selectedTrial });
})()`, context);
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

        self.assertIn("&mdash;", result["zero"])
        self.assertIn("one.md", result["one"])
        self.assertIn("2 reports", result["many"])
        self.assertLess(
            result["many"].index("newer.md"), result["many"].index("older.html")
        )
        alias_index = result["columnKeys"].index("task_name")
        self.assertEqual(result["columnKeys"][alias_index + 1], "workspace_reports")
        self.assertTrue(result["clickEvent"]["stopped"])
        self.assertTrue(result["changeEvent"]["stopped"])
        self.assertEqual(result["probe"]["opened"], "20260710-130000-000000")
        self.assertEqual(result["selectValue"], "")
        self.assertEqual(result["selectedTrial"], "trial-before")

    def test_workspace_report_attach_cancel_preserves_selection_and_success_opens_reader(
        self,
    ) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-token-estimates": { textContent: "{}" },
  "peval-i18n": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [], reports: [] }) }
};
const context = {
  document: {
    body: { classList: { add() {}, remove() {}, toggle() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; }
  },
  window: { addEventListener() {} },
  console, JSON, Number, String, Object, Math, Date, Set, Array, RegExp
};
vm.createContext(context);
vm.runInContext(asset, context);
vm.runInContext(`(async () => {
  const probe = { calls: [], renders: 0, opened: null, statuses: [] };
  const button = { disabled: false };
  visibleSelectedSourceKeys = () => ["cell-a"];
  renderComparisonPanels = () => { probe.renders += 1; };
  openWorkspaceReportReader = reportId => { probe.opened = reportId; };
  setServeStatus = (message, error = false) => probe.statuses.push({ message, error });
  state.rowSelection.add("trial-a");
  serveApi = async (path, options) => {
    probe.calls.push({ path, body: options?.body || null });
    return { paths: [] };
  };
  await attachWorkspaceReport(button);
  const afterCancel = {
    selected: Array.from(state.rowSelection),
    renders: probe.renders,
    opened: probe.opened,
    calls: probe.calls.slice(),
    disabled: button.disabled
  };
  probe.calls = [];
  serveApi = async (path, options) => {
    probe.calls.push({ path, body: options?.body || null });
    if (path === "/api/path-picker") return { paths: ["/tmp/report.md"] };
    return {
      report_id: "20260710-140000-000000",
      reports: [{ report_id: "20260710-140000-000000", filename: "report.md", format: "markdown", source_keys: ["cell-a"] }]
    };
  };
  await attachWorkspaceReport(button);
  const afterSuccess = {
    selected: Array.from(state.rowSelection),
    renders: probe.renders,
    opened: probe.opened,
    calls: probe.calls,
    reportIds: workspaceReports().map(report => report.report_id),
    disabled: button.disabled
  };
  console.log(JSON.stringify({ afterCancel, afterSuccess }));
})().catch(error => { console.error(error); process.exitCode = 1; });`, context);
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

        self.assertEqual(result["afterCancel"]["selected"], ["trial-a"])
        self.assertEqual(result["afterCancel"]["renders"], 0)
        self.assertIsNone(result["afterCancel"]["opened"])
        self.assertEqual(
            result["afterCancel"]["calls"],
            [{"path": "/api/path-picker", "body": {"multiple": False}}],
        )
        self.assertFalse(result["afterCancel"]["disabled"])
        self.assertEqual(result["afterSuccess"]["selected"], [])
        self.assertEqual(result["afterSuccess"]["renders"], 1)
        self.assertEqual(result["afterSuccess"]["opened"], "20260710-140000-000000")
        self.assertEqual(
            result["afterSuccess"]["calls"],
            [
                {"path": "/api/path-picker", "body": {"multiple": False}},
                {
                    "path": "/api/reports",
                    "body": {"path": "/tmp/report.md", "source_keys": ["cell-a"]},
                },
            ],
        )
        self.assertEqual(
            result["afterSuccess"]["reportIds"], ["20260710-140000-000000"]
        )
        self.assertFalse(result["afterSuccess"]["disabled"])

    def test_workspace_report_reader_resizes_with_pointer_and_keyboard(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
function classList() {
  return {
    values: new Set(),
    add(name) { this.values.add(name); },
    remove(name) { this.values.delete(name); },
    contains(name) { return this.values.has(name); }
  };
}
const bodyClasses = classList();
const documentListeners = {};
const style = {
  values: {},
  setProperty(name, value) { this.values[name] = value; }
};
const closeButton = {
  listeners: {},
  addEventListener(type, handler) { this.listeners[type] = handler; },
  focus() {}
};
const resizeHandle = {
  attributes: {},
  listeners: {},
  captured: null,
  released: null,
  addEventListener(type, handler) { this.listeners[type] = handler; },
  setAttribute(name, value) { this.attributes[name] = value; },
  setPointerCapture(pointerId) { this.captured = pointerId; },
  releasePointerCapture(pointerId) { this.released = pointerId; }
};
const reader = {
  hidden: true,
  innerHTML: "",
  getBoundingClientRect() {
    return { width: Number.parseInt(style.values["--report-reader-width"] || "480", 10) };
  },
  querySelectorAll(selector) {
    return selector === "[data-report-reader-close]" ? [closeButton] : [];
  },
  querySelector(selector) {
    if (selector === "[data-report-reader-close]") return closeButton;
    if (selector === "[data-report-reader-resize]") return resizeHandle;
    return null;
  }
};
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-token-estimates": { textContent: "{}" },
  "peval-i18n": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [], reports: [] }) },
  "workspace-report-reader": reader
};
const context = {
  document: {
    activeElement: null,
    body: { classList: bodyClasses },
    documentElement: { clientWidth: 1200, style },
    addEventListener(type, handler) { documentListeners[type] = handler; },
    removeEventListener(type, handler) { if (documentListeners[type] === handler) delete documentListeners[type]; },
    getElementById(id) { return nodes[id] || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; }
  },
  window: { innerWidth: 1200, addEventListener() {} },
  requestAnimationFrame(callback) { callback(); },
  console, JSON, Number, String, Object, Math, Date, Set, Array, RegExp,
  reader, resizeHandle, bodyClasses, documentListeners, style
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(() => {
  const report = { report_id: "20260710-170000-000000", filename: "resize.md", format: "markdown", source_keys: [] };
  state.workspaceReports = [report];
  renderStepDrawer = () => {};
  openWorkspaceReportReader(report.report_id);
  resizeHandle.listeners.pointerdown({ button: 0, pointerId: 7, clientX: 480, preventDefault() {} });
  documentListeners.pointermove({ pointerId: 7, clientX: 700 });
  const duringDrag = bodyClasses.contains("report-reader-resizing");
  resizeHandle.listeners.keydown({ key: "ArrowRight", shiftKey: true, preventDefault() {} });
  documentListeners.pointerup({ pointerId: 7 });
  return JSON.stringify({
    width: style.values["--report-reader-width"],
    stateWidth: state.reportReader.width,
    duringDrag,
    draggingAfterRelease: bodyClasses.contains("report-reader-resizing"),
    captured: resizeHandle.captured,
    released: resizeHandle.released,
    aria: resizeHandle.attributes
  });
})()`, context);
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

        self.assertEqual(result["width"], "772px")
        self.assertEqual(result["stateWidth"], 772)
        self.assertTrue(result["duringDrag"])
        self.assertFalse(result["draggingAfterRelease"])
        self.assertEqual(result["captured"], 7)
        self.assertEqual(result["released"], 7)
        self.assertEqual(
            result["aria"],
            {"aria-valuemin": "360", "aria-valuemax": "840", "aria-valuenow": "772"},
        )

    def test_workspace_report_manager_search_rebind_and_delete(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const bindingTarget = { innerHTML: "" };
const manager = { hidden: true };
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-token-estimates": { textContent: "{}" },
  "peval-i18n": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [], reports: [] }) }
};
const context = {
  document: {
    body: { classList: { add() {}, remove() {}, toggle() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector(selector) {
      if (selector === "[data-report-bindings]") return bindingTarget;
      if (selector === "[data-report-manager]") return manager;
      return null;
    },
    querySelectorAll() { return []; }
  },
  window: { addEventListener() {}, confirm() { return true; } },
  console, JSON, Number, String, Object, Math, Date, Set, Array, RegExp,
  bindingTarget
};
vm.createContext(context);
vm.runInContext(asset, context);
vm.runInContext(`(async () => {
  const report = { report_id: "20260710-160000-000000", filename: "manager.md", format: "markdown", source_keys: [] };
  state.workspaceReports = [report];
  state.reportManager.selectedId = report.report_id;
  syncWorkspaceReportDraft();
  state.serveSources = [
    { source_key: "cell-active", label: "Active session", trial_session_id: "active", active: true, artifact_dir: "runs/a", last_status: "ok", source_tags: ["priority", "release"] },
    { source_key: "cell-archived", label: "Archived session", trial_session_id: "archived", active: false, artifact_dir: "runs/b", last_status: "ok", source_tags: ["review"] },
    { source_key: "cell-empty", label: "Empty tags", trial_session_id: "empty", active: true, artifact_dir: "runs/empty", last_status: "ok" },
    { source_key: "cell-missing", label: "Missing session", active: true, artifact_dir: "runs/c", last_status: "missing" }
  ];
  renderWorkspaceReportBindings();
  const initial = {
    readable: readableWorkspaceReportSources().map(source => source.source_key),
    saveDisabled: bindingTarget.innerHTML.includes("data-report-bindings-save disabled"),
    tagChips: (bindingTarget.innerHTML.match(/source-tag-chip/g) || []).length,
    emptyTags: bindingTarget.innerHTML.includes('class="report-binding-tags"><span class="muted">-</span>')
  };
  state.reportManager.search = "review";
  const searchMatches = filteredWorkspaceReportSources().map(source => source.source_key);
  state.reportManager.search = "";
  state.reportManager.draftBindings.add("cell-active");
  state.reportManager.draftBindings.add("cell-archived");
  state.reportManager.dirty = workspaceReportBindingsChanged();
  renderWorkspaceReportBindings();
  const changed = {
    dirty: state.reportManager.dirty,
    saveDisabled: bindingTarget.innerHTML.includes("data-report-bindings-save disabled")
  };
  const calls = [];
  renderComparisonPanels = () => {};
  setWorkspaceReportManagerStatus = () => {};
  serveApi = async (path, options) => {
    calls.push({ path, body: options?.body || null });
    if (path.endsWith("/delete")) return { reports: [] };
    return { reports: [{ ...report, source_keys: ["cell-active", "cell-archived"] }] };
  };
  await saveWorkspaceReportBindings();
  const afterSave = {
    sourceKeys: workspaceReportForId(report.report_id).source_keys,
    dirty: state.reportManager.dirty
  };
  await deleteWorkspaceReport(report.report_id);
  console.log(JSON.stringify({ initial, searchMatches, changed, afterSave, calls, remaining: workspaceReports().length }));
})().catch(error => { console.error(error); process.exitCode = 1; });`, context);
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
            result["initial"]["readable"],
            ["cell-active", "cell-archived", "cell-empty"],
        )
        self.assertTrue(result["initial"]["saveDisabled"])
        self.assertEqual(result["initial"]["tagChips"], 3)
        self.assertTrue(result["initial"]["emptyTags"])
        self.assertEqual(result["searchMatches"], ["cell-archived"])
        self.assertTrue(result["changed"]["dirty"])
        self.assertFalse(result["changed"]["saveDisabled"])
        self.assertEqual(
            result["afterSave"]["sourceKeys"], ["cell-active", "cell-archived"]
        )
        self.assertFalse(result["afterSave"]["dirty"])
        self.assertEqual(
            result["calls"],
            [
                {
                    "path": "/api/reports/20260710-160000-000000/bindings",
                    "body": {"source_keys": ["cell-active", "cell-archived"]},
                },
                {
                    "path": "/api/reports/20260710-160000-000000/delete",
                    "body": {},
                },
            ],
        )
        self.assertEqual(result["remaining"], 0)
