from __future__ import annotations

from tests.peval.reports_html_support import (
    json,
    load_asset_text,
    re,
    shutil,
    subprocess,
    unittest,
)


class PevalReportHtmlReportInteractionTests(unittest.TestCase):
    def test_markdown_renderer_renders_analysis_md_headings_tables_and_escapes(
        self,
    ) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        markdown = (
            "# Cached Review\n\n"
            "## Slow step\n\n"
            "This is **strong** and _emphasis_ with `inline_code`.\n\n"
            "| Check | Result | Count |\n"
            "| :--- | :---: | ---: |\n"
            "| <script>alert(1)</script> | **pass** | 3 |\n"
            "| Pipe \\| ok | _warn_ | 12 |\n\n"
            "Not | a table\n\n"
            "```\n"
            "| raw | code |\n"
            "```"
        )
        script = f"""
const vm = require("vm");
const asset = {json.dumps(asset)};
const markdown = {json.dumps(markdown)};
const context = {{
  document: {{
    body: {{ classList: {{ toggle() {{}} }} }},
    addEventListener() {{}},
    getElementById: () => null,
    querySelector: () => null,
    querySelectorAll: () => [],
  }},
  window: {{ addEventListener() {{}} }},
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
  markdown,
}};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`
  state.view = {{
    annotations: {{
      analysis: [{{ trial_key: "trial:md", status: "cached", md_report: markdown }}]
    }}
  }};
  JSON.stringify({{
    markdown: renderMarkdown(markdown),
    analysis: renderSelectedAnalysis("trial:md")
  }});
`, context);
console.log(result);
"""
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
        rendered = result["analysis"]
        self.assertIn(
            '<h4 class="markdown-heading markdown-heading-1">Cached Review</h4>',
            rendered,
        )
        self.assertIn(
            '<h5 class="markdown-heading markdown-heading-2">Slow step</h5>', rendered
        )
        self.assertIn("<strong>strong</strong>", rendered)
        self.assertIn("<em>emphasis</em>", rendered)
        self.assertIn("<code>inline_code</code>", rendered)
        self.assertIn(
            '<div class="markdown-table-wrap"><table class="markdown-table">', rendered
        )
        self.assertIn('<th class="align-left">Check</th>', rendered)
        self.assertIn('<th class="align-center">Result</th>', rendered)
        self.assertIn('<th class="align-right">Count</th>', rendered)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertIn("<strong>pass</strong>", rendered)
        self.assertIn("Pipe | ok", rendered)
        self.assertIn("<em>warn</em>", rendered)
        self.assertIn("<p>Not | a table</p>", rendered)
        self.assertIn('<pre class="note-code">| raw | code |</pre>', rendered)
        self.assertNotIn("<script>alert(1)</script>", rendered)

    def test_html_timeline_click_opens_drawer_for_single_session_report(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                {
                    "trajectory_id": "trial:single",
                    "session_id": "single",
                    "agent": {"name": "hermes", "model_name": "test-model"},
                    "steps": [
                        {"step_id": 1, "source": "user", "message": "run it"},
                        {
                            "step_id": 2,
                            "source": "agent",
                            "message": "reading",
                            "tool_calls": [
                                {
                                    "tool_call_id": "call-read",
                                    "function_name": "read",
                                    "arguments": {"file_path": "README.md"},
                                }
                            ],
                        },
                    ],
                    "final_metrics": {},
                }
            ],
            "trajectory_meta": [
                {
                    "trial_key": "trial:single",
                    "status": "passed",
                    "started_at_ms": 1_000,
                    "finished_at_ms": 1_200,
                    "duration_ms": 100,
                    "steps": [
                        {
                            "step_id": 1,
                            "timestamp_ms": 1_000,
                            "elapsed_ms": 0,
                            "duration_ms": None,
                            "tool_calls": [],
                            "observations": [],
                        },
                        {
                            "step_id": 2,
                            "timestamp_ms": 1_100,
                            "elapsed_ms": 100,
                            "duration_ms": 100,
                            "tool_calls": [
                                {
                                    "tool_call_id": "call-read",
                                    "title": "read",
                                    "timestamp_ms": 1_120,
                                    "execution_duration_ms": 50,
                                }
                            ],
                            "observations": [],
                        },
                    ],
                    "warnings": [],
                }
            ],
        }
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = f"""
const vm = require("vm");
const asset = {json.dumps(asset)};
const report = {json.dumps(report)};
const context = {{
  document: {{
    body: {{ classList: {{ toggle() {{}} }} }},
    addEventListener() {{}},
    getElementById: () => null,
    querySelector: () => null,
  }},
  window: {{ addEventListener() {{}} }},
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
  report,
  rendered: [],
}};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`
  state.view = report;
  state.selectedTrial = report.trajectory_meta[0].trial_key;
  renderLeaderboard = () => rendered.push("leaderboard");
  renderTrajectoryOverview = () => rendered.push("overview");
  renderTrace = () => rendered.push("trace");
  renderStepDrawer = () => rendered.push(state.selectedStep ? "drawer-open" : "drawer-closed");
  openTimelineStep({{ kind: "stage", trial_key: "trial:single", step_id: 2 }});
  const stageStep = state.selectedStep;
  openTimelineStep({{ kind: "marker", trial_key: "trial:single", step_id: 1 }});
  JSON.stringify({{ selectedTrial: state.selectedTrial, selectedStep: state.selectedStep, stageStep, rendered }});
`, context);
console.log(result);
"""
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

        self.assertEqual(result["selectedTrial"], "trial:single")
        self.assertEqual(
            result["stageStep"],
            {"trialKey": "trial:single", "stepId": "2"},
        )
        self.assertEqual(
            result["selectedStep"],
            {"trialKey": "trial:single", "stepId": "1"},
        )
        self.assertIn("drawer-open", result["rendered"])

    def test_html_trajectory_overview_nodes_render_duration_heat(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                {
                    "trajectory_id": "trial:overview",
                    "session_id": "overview",
                    "agent": {"name": "psychevo"},
                    "steps": [
                        {"step_id": 1, "source": "user", "message": "start"},
                        {"step_id": 2, "source": "agent", "message": "fast"},
                        {"step_id": 3, "source": "agent", "message": "slow"},
                    ],
                    "final_metrics": {},
                },
                {
                    "trajectory_id": "trial:overview-2",
                    "session_id": "overview-2",
                    "agent": {"name": "psychevo"},
                    "steps": [
                        {"step_id": 1, "source": "user", "message": "start"},
                    ],
                    "final_metrics": {},
                },
            ],
            "trajectory_meta": [
                {
                    "trial_key": "trial:overview",
                    "status": "passed",
                    "steps": [
                        {"step_id": 1, "duration_ms": 0},
                        {"step_id": 2, "duration_ms": 120},
                        {"step_id": 3, "duration_ms": 240},
                    ],
                    "warnings": [],
                },
                {
                    "trial_key": "trial:overview-2",
                    "status": "passed",
                    "steps": [
                        {"step_id": 1, "duration_ms": 0},
                    ],
                    "warnings": [],
                },
            ],
        }
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = f"""
const vm = require("vm");
const asset = {json.dumps(asset)};
const report = {json.dumps(report)};
const context = {{
  document: {{
    body: {{ classList: {{ toggle() {{}} }} }},
    addEventListener() {{}},
    getElementById: () => null,
    querySelector: () => null,
  }},
  window: {{ addEventListener() {{}} }},
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
  report,
}};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`
  state.view = report;
  state.selectedTrial = "trial:overview";
  state.selectedStep = {{ trialKey: "trial:overview", stepId: "3" }};
  renderTrajectoryOverviewRow(reportRows()[0]);
`, context);
console.log(result);
"""
        node = subprocess.run(
            ["node"],
            input=script,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(node.returncode, 0, node.stderr)
        row_html = node.stdout
        buttons = {
            match.group("id"): match.group("tag")
            for match in re.finditer(
                r'(?P<tag><button class="[^"]*"[^>]*data-step-id="(?P<id>[^"]+)"[^>]*>)',
                row_html,
            )
        }

        self.assertIn("1", buttons)
        self.assertIn("2", buttons)
        self.assertIn("3", buttons)
        self.assertNotIn("duration-heat-", buttons["1"])
        self.assertNotIn("--time-pct", buttons["1"])
        self.assertIn("step 0.0s", buttons["1"])
        self.assertIn("duration-heat-5", buttons["2"])
        self.assertNotIn("--time-pct", buttons["2"])
        self.assertIn("duration-heat-10", buttons["3"])
        self.assertIn("selected-node", buttons["3"])
        self.assertNotIn("--time-pct", buttons["3"])
        self.assertIn("step 0.2s; 100% of slowest step", buttons["3"])

    def test_html_runtime_rows_and_report_subset_avoid_persisted_comparison(
        self,
    ) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                {
                    "trajectory_id": "trial:one",
                    "session_id": "one",
                    "agent": {"name": "agent-a", "model_name": "model-a"},
                    "steps": [],
                    "final_metrics": {
                        "total_prompt_tokens": 80,
                        "total_completion_tokens": 40,
                        "total_cost_usd": 0.03,
                        "extra": {
                            "total_turns": 2,
                            "total_tool_calls": 4,
                            "total_tool_errors": 1,
                        },
                    },
                },
                {
                    "trajectory_id": "trial:two",
                    "session_id": "two",
                    "agent": {"name": "agent-b", "model_name": "model-b"},
                    "steps": [],
                    "final_metrics": {
                        "extra": {
                            "total_turns": 1,
                            "total_tool_calls": 0,
                            "total_tool_errors": 0,
                        },
                    },
                },
            ],
            "trajectory_meta": [
                {
                    "trial_key": "trial:one",
                    "adapter": "psychevo",
                    "status": "passed",
                    "finished_at_ms": 300,
                    "duration_ms": 100,
                    "wall_duration_ms": 300,
                    "warnings": ["warn"],
                    "steps": [],
                },
                {
                    "trial_key": "trial:two",
                    "adapter": "opencode",
                    "status": "failed",
                    "finished_at_ms": 500,
                    "duration_ms": 50,
                    "wall_duration_ms": 500,
                    "warnings": [],
                    "steps": [],
                },
            ],
            "annotations": {
                "report_notes": [],
                "notes": [{"trial_key": "trial:one", "markdown": "keep"}],
                "analysis": [
                    {
                        "trial_key": "trial:one",
                        "status": "cached",
                        "markdown_reports": [
                            {
                                "source": "harbor_trial",
                                "markdown": "Harbor",
                                "relative_path": "artifacts/logs/analysis.md",
                            },
                            {
                                "source": "workspace_overlay",
                                "markdown": "Workspace",
                                "relative_path": "harbor/mount/job/trial/analysis.md",
                            },
                        ],
                        "relative_paths": {
                            "json": "runs/default/agent-a/one/trial_one/analysis.json",
                            "md": "runs/default/agent-a/one/trial_one/analysis.md",
                        },
                    },
                    {"trial_key": "trial:two", "status": "computed"},
                ],
            },
        }
        legacy_report = {
            "schema_version": 19,
            "includes": ["core", "comparison"],
            "trajectory": [],
            "trajectory_meta": [],
            "comparison": {
                "leaderboard": {
                    "entries": [{"trial_key": "trial:single", "adapter": "legacy"}]
                }
            },
        }
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = f"""
const vm = require("vm");
const asset = {json.dumps(asset)};
const report = {json.dumps(report)};
const legacyReport = {json.dumps(legacy_report)};
class BlobStub {{
  constructor(parts, options = {{}}) {{
    this.parts = parts;
    this.type = options.type || "";
    this.size = parts.reduce((total, part) => total + (part.length || part.byteLength || String(part).length), 0);
  }}
}}
const context = {{
  document: {{
    body: {{ classList: {{ toggle() {{}} }} }},
    addEventListener() {{}},
    getElementById: () => null,
    querySelector: () => null,
  }},
  window: {{ addEventListener() {{}} }},
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
  TextEncoder,
  Uint8Array,
  DataView,
  Buffer,
  Blob: BlobStub,
  report,
  legacyReport,
}};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`
  state.view = report;
  const rows = reportRows();
  const subset = reportSubset(rows);
  const analysisCounts = rows.map(row => rowAnalysisCount(row));
  const analysisColumn = leaderboardColumns().find(column => column.key === "analysis_count");
  const analysisFilterable = Boolean(analysisColumn?.filterable);
  const analysisOptions = filterOptions(analysisColumn, reportRows());
  setFilterValue("leaderboard", "analysis_count", "2", true);
  const twoAnalysisKeys = leaderboardRows().map(row => row.trial_key);
  clearFilter("leaderboard", "analysis_count");
  setFilterValue("leaderboard", "analysis_count", "0", true);
  const zeroAnalysisKeys = leaderboardRows().map(row => row.trial_key);
  clearFilter("leaderboard", "analysis_count");
  const xlsxBytes = xlsxBytesForRows(rows, leaderboardColumns());
  const xlsxText = Buffer.from(xlsxBytes).toString("utf8");
  state.view = legacyReport;
  const legacyRows = reportRows();
  JSON.stringify({{
    rowCount: rows.length,
    firstAdapter: rows[0].adapter,
    firstErrorRate: rowToolErrorRate(rows[0]),
    analysisCounts,
    analysisFilterable,
    analysisOptions,
    twoAnalysisKeys,
    zeroAnalysisKeys,
    pathChecks: [
      isAnalysisArtifactPath("runs/default/agent/session/cell/analysis.md"),
      isAnalysisArtifactPath("runs/default/agent/session/cell/analysis.json"),
      isAnalysisArtifactPath("runs/default/agent/session/cell/notes.md")
    ],
    xlsxZipMagic: [xlsxBytes[0], xlsxBytes[1], xlsxBytes[2], xlsxBytes[3]],
    xlsxHasHeader: xlsxText.includes("#Analysis"),
    subsetHasComparison: Object.prototype.hasOwnProperty.call(subset, "comparison"),
    subsetIncludes: subset.includes,
    subsetNotes: subset.annotations.notes.map(note => note.markdown),
    subsetAnalysisKeys: subset.annotations.analysis.map(item => item.trial_key),
    legacyRowCount: legacyRows.length
  }});
`, context);
console.log(result);
"""
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
        self.assertEqual(result["rowCount"], 2)
        self.assertEqual(result["firstAdapter"], "psychevo")
        self.assertAlmostEqual(result["firstErrorRate"], 0.25)
        self.assertEqual(result["analysisCounts"], [2, 0])
        self.assertTrue(result["analysisFilterable"])
        self.assertEqual(result["analysisOptions"], ["0", "2"])
        self.assertEqual(result["twoAnalysisKeys"], ["trial:one"])
        self.assertEqual(result["zeroAnalysisKeys"], ["trial:two"])
        self.assertEqual(result["pathChecks"], [True, True, False])
        self.assertEqual(result["xlsxZipMagic"], [80, 75, 3, 4])
        self.assertTrue(result["xlsxHasHeader"])
        self.assertFalse(result["subsetHasComparison"])
        self.assertEqual(result["subsetIncludes"], ["core"])
        self.assertEqual(result["subsetNotes"], ["keep"])
        self.assertEqual(result["subsetAnalysisKeys"], ["trial:one", "trial:two"])
        self.assertEqual(result["legacyRowCount"], 0)

    def test_data_table_filters_stage_multiple_values_until_apply(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
function control(dataset = {}) {
  return {
    dataset,
    checked: false,
    disabled: false,
    open: false,
    value: "",
    listeners: {},
    addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
    dispatch(type, event = {}) {
      const payload = {
        key: event.key,
        defaultPrevented: false,
        stopped: false,
        preventDefault() { this.defaultPrevented = true; },
        stopPropagation() { this.stopped = true; },
      };
      (this.listeners[type] || []).forEach(handler => handler(payload));
      return payload;
    },
  };
}
const passed = control({ filterKey: "status" });
passed.value = "passed";
passed.checked = true;
const failed = control({ filterKey: "status" });
failed.value = "failed";
const clear = control({ filterClear: "status" });
const apply = control({ filterApply: "status" });
const menu = control({ filterMenu: "status" });
menu.open = true;
menu.querySelectorAll = selector => selector === "[data-filter-key]" ? [passed, failed] : [];
menu.querySelector = selector => selector === "[data-filter-apply]" ? apply : null;
const root = {
  querySelectorAll(selector) {
    if (selector === "[data-filter-key]") return [passed, failed];
    if (selector === "[data-filter-clear]") return [clear];
    if (selector === "[data-filter-apply]") return [apply];
    if (selector === "[data-filter-menu]") return [menu];
    return [];
  },
};
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-i18n": { textContent: JSON.stringify({ apply: "Apply" }) },
  "peval-token-estimates": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "report" }) },
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
  root,
  menu,
  passed,
  failed,
  clear,
  apply,
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(() => {
  tableControls("leaderboard").filters.status = ["passed"];
  const column = { key: "status", label: "Result", filterable: true, value: row => row.status };
  tableControls("preview").filters.status = ["passed", "missing"];
  const markup = renderFilterControl("preview", column, [{ status: "passed" }]);
  let renderCount = 0;
  bindDataTableControls(root, {
    tableId: "leaderboard",
    onChange: () => { renderCount += 1; },
  });

  failed.checked = true;
  failed.dispatch("change");
  const staged = {
    committed: activeFilterValues("leaderboard", "status"),
    renderCount,
    menuOpen: menu.open,
  };

  clear.dispatch("click");
  const clearedDraft = {
    checked: [passed.checked, failed.checked],
    committed: activeFilterValues("leaderboard", "status"),
    renderCount,
  };

  menu.open = false;
  menu.dispatch("toggle");
  const discarded = { checked: [passed.checked, failed.checked] };

  menu.open = true;
  menu.dispatch("toggle");
  failed.checked = true;
  apply.dispatch("click");
  const applied = {
    committed: activeFilterValues("leaderboard", "status"),
    renderCount,
    menuOpen: menu.open,
  };

  menu.open = true;
  failed.checked = false;
  const escape = menu.dispatch("keydown", { key: "Escape" });
  return JSON.stringify({
    markup,
    staged,
    clearedDraft,
    discarded,
    applied,
    escaped: {
      checked: [passed.checked, failed.checked],
      menuOpen: menu.open,
      defaultPrevented: escape.defaultPrevented,
      stopped: escape.stopped,
    },
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

        self.assertIn('data-filter-apply="status"', result["markup"])
        self.assertIn('value="missing" checked', result["markup"])
        self.assertRegex(
            result["markup"],
            r'<div class="filter-menu-head"><strong>Result</strong><div class="filter-menu-actions">'
            r'<button class="action-button compact filter-clear"[^>]*data-filter-clear="status"[^>]*>Clear</button>'
            r'<button class="action-button compact primary filter-apply"[^>]*data-filter-apply="status"[^>]*>Apply</button>'
            r'</div></div><div class="filter-options">',
        )
        self.assertEqual(result["staged"]["committed"], ["passed"])
        self.assertEqual(result["staged"]["renderCount"], 0)
        self.assertTrue(result["staged"]["menuOpen"])
        self.assertEqual(result["clearedDraft"]["checked"], [False, False])
        self.assertEqual(result["clearedDraft"]["committed"], ["passed"])
        self.assertEqual(result["clearedDraft"]["renderCount"], 0)
        self.assertEqual(result["discarded"]["checked"], [True, False])
        self.assertEqual(result["applied"]["committed"], ["passed", "failed"])
        self.assertEqual(result["applied"]["renderCount"], 1)
        self.assertFalse(result["applied"]["menuOpen"])
        self.assertEqual(result["escaped"]["checked"], [True, True])
        self.assertFalse(result["escaped"]["menuOpen"])
        self.assertTrue(result["escaped"]["defaultPrevented"])
        self.assertTrue(result["escaped"]["stopped"])

    def test_serve_data_table_filter_apply_requests_all_values_once(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
function control(dataset = {}) {
  return {
    dataset,
    checked: false,
    disabled: false,
    open: false,
    value: "",
    listeners: {},
    addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
    dispatch(type) {
      const event = { stopPropagation() {}, preventDefault() {} };
      (this.listeners[type] || []).forEach(handler => handler(event));
    },
  };
}
const alpha = control({ filterKey: "source_tags" });
alpha.value = "alpha";
alpha.checked = true;
const beta = control({ filterKey: "source_tags" });
beta.value = "beta";
beta.checked = true;
const apply = control({ filterApply: "source_tags" });
const menu = control({ filterMenu: "source_tags" });
menu.open = true;
menu.querySelectorAll = selector => selector === "[data-filter-key]" ? [alpha, beta] : [];
menu.querySelector = selector => selector === "[data-filter-apply]" ? apply : null;
const root = {
  querySelectorAll(selector) {
    if (selector === "[data-filter-key]") return [alpha, beta];
    if (selector === "[data-filter-apply]") return [apply];
    if (selector === "[data-filter-menu]") return [menu];
    return [];
  },
};
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-i18n": { textContent: "{}" },
  "peval-token-estimates": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "serve" }) },
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
  Promise,
  root,
  menu,
  apply,
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(async () => {
  let resolveRequest;
  const pending = new Promise(resolve => { resolveRequest = resolve; });
  const calls = [];
  loadCatalogPage = (changes, options) => {
    calls.push({ changes, options });
    return pending;
  };
  bindDataTableControls(root, { tableId: "leaderboard", onChange: () => {} });
  apply.dispatch("click");
  const during = {
    calls,
    committed: activeFilterValues("leaderboard", "source_tags"),
    menuOpen: menu.open,
    applyDisabled: apply.disabled,
  };
  resolveRequest();
  await pending;
  await Promise.resolve();
  return JSON.stringify({ during, applyDisabledAfter: apply.disabled });
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

        self.assertEqual(
            result["during"]["calls"],
            [
                {
                    "changes": {
                        "page": 1,
                        "categories": [],
                        "tags": ["alpha", "beta"],
                        "agents": [],
                        "models": [],
                        "tasks": [],
                        "jobs": [],
                        "providers": [],
                        "results": [],
                    },
                    "options": {"force": True},
                }
            ],
        )
        self.assertEqual(result["during"]["committed"], ["alpha", "beta"])
        self.assertFalse(result["during"]["menuOpen"])
        self.assertTrue(result["during"]["applyDisabled"])
        self.assertFalse(result["applyDisabledAfter"])

    def test_leaderboard_summary_uses_filtered_visible_rows(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                {
                    "trajectory_id": "trial:alpha",
                    "session_id": "alpha",
                    "agent": {"name": "agent-a", "model_name": "model-a"},
                    "steps": [
                        {"step_id": 1, "source": "user"},
                        {"step_id": 2, "source": "agent"},
                        {"step_id": 3, "source": "assistant"},
                        {"step_id": 4, "source": "tool"},
                    ],
                    "final_metrics": {
                        "total_prompt_tokens": 60,
                        "total_completion_tokens": 40,
                        "extra": {
                            "total_turns": 2,
                            "total_tool_calls": 2,
                            "total_tool_errors": 0,
                        },
                    },
                },
                {
                    "trajectory_id": "trial:beta",
                    "session_id": "beta",
                    "agent": {"name": "agent-b", "model_name": "model-b"},
                    "steps": [
                        {"step_id": 1, "source": "assistant"},
                    ],
                    "final_metrics": {
                        "total_prompt_tokens": 150,
                        "total_completion_tokens": 50,
                        "extra": {
                            "total_turns": 4,
                            "total_tool_calls": 4,
                            "total_tool_errors": 2,
                        },
                    },
                },
                {
                    "trajectory_id": "trial:gamma",
                    "session_id": "gamma",
                    "agent": {"name": "agent-c", "model_name": "model-a"},
                    "steps": [
                        {"step_id": 1, "source": "assistant"},
                        {"step_id": 2, "source": "agent"},
                    ],
                    "final_metrics": {
                        "total_prompt_tokens": 220,
                        "total_completion_tokens": 80,
                        "extra": {
                            "total_turns": 6,
                            "total_tool_calls": 0,
                            "total_tool_errors": 0,
                        },
                    },
                },
            ],
            "trajectory_meta": [
                {
                    "trial_key": "trial:alpha",
                    "status": "passed",
                    "source_category": "frontend",
                    "duration_ms": 2000,
                    "steps": [
                        {"step_id": 1, "duration_ms": 100},
                        {
                            "step_id": 2,
                            "duration_ms": 1000,
                            "duration_source": "measured",
                        },
                        {
                            "step_id": 3,
                            "duration_ms": 2000,
                            "duration_source": "boundary_estimate",
                        },
                        {"step_id": 4, "duration_ms": 500},
                    ],
                    "warnings": [],
                },
                {
                    "trial_key": "trial:beta",
                    "status": "failed",
                    "source_category": "backend",
                    "duration_ms": 3000,
                    "steps": [
                        {
                            "step_id": 1,
                            "duration_ms": 3000,
                            "duration_source": "measured",
                        },
                    ],
                    "warnings": [],
                },
                {
                    "trial_key": "trial:gamma",
                    "status": "passed",
                    "duration_ms": 6000,
                    "steps": [
                        {
                            "step_id": 1,
                            "duration_ms": 500,
                            "duration_source": "measured",
                        },
                        {
                            "step_id": 2,
                            "duration_ms": None,
                            "duration_source": "measured",
                        },
                    ],
                    "warnings": [],
                },
            ],
        }
        single_report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                {"trajectory_id": "trial:single", "session_id": "single", "steps": []}
            ],
            "trajectory_meta": [
                {"trial_key": "trial:single", "status": "passed", "steps": []}
            ],
        }
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = (
            """
const vm = require("vm");
const asset = __ASSET__;
const report = __REPORT__;
const singleReport = __SINGLE_REPORT__;
const nodes = {
  "peval-i18n": { textContent: "{}" },
  "peval-token-estimates": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "report" }) },
  "leaderboard-summary": { innerHTML: "" },
  "comparison": { innerHTML: "" },
};
const context = {
  nodes,
  document: {
    body: { classList: { toggle() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector: () => null,
    querySelectorAll: () => [],
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
  report,
  singleReport,
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`
  function byKey(rows) {
    return Object.fromEntries(rows.map(row => [row.key, row]));
  }
  function metricFor(group, key) {
    return group.metrics.find(metric => metric.key === key);
  }
  function countToken(html, token) {
    return html.split(token).length - 1;
  }
  state.view = report;
  state.selectedTrial = "trial:alpha";
  state.rowSelection.add("trial:beta");
  setFilterValue("leaderboard", "status", "passed", true);
  const rows = leaderboardRows();
  renderLeaderboardSummary(rows);
  const summary = byKey(leaderboardSummaryRows(rows));
  const selectionProof = byKey(leaderboardSummaryRows(leaderboardRows()));
  const agentGroups = leaderboardSummaryGroups(rows);
  const defaultHtml = nodes["leaderboard-summary"].innerHTML;
  const defaultState = {
    groupBy: state.leaderboardSummaryGroupBy,
    tableOpen: state.leaderboardSummaryTableOpen,
    statistic: state.leaderboardSummaryStatistic,
  };

  toggleLeaderboardSummaryTable();
  const openHtml = nodes["leaderboard-summary"].innerHTML;
  const statisticStates = leaderboardSummaryStatistics().map(statistic => {
    setLeaderboardSummaryStatistic(statistic.key);
    return {
      key: statistic.key,
      state: state.leaderboardSummaryStatistic,
      pressed: nodes["leaderboard-summary"].innerHTML.includes('data-summary-statistic="' + statistic.key + '" aria-pressed="true"'),
      highlighted: nodes["leaderboard-summary"].innerHTML.includes('data-summary-stat-heading="' + statistic.key + '"'),
      tableOpen: state.leaderboardSummaryTableOpen,
    };
  });
  const p95Html = (() => {
    setLeaderboardSummaryStatistic("p95");
    return nodes["leaderboard-summary"].innerHTML;
  })();

  setLeaderboardSummaryGroupBy("model");
  const modelGroups = leaderboardSummaryGroups(leaderboardRows());
  const modelHtml = nodes["leaderboard-summary"].innerHTML;
  setLeaderboardSummaryGroupBy("category");
  const categoryGroups = leaderboardSummaryGroups(leaderboardRows());
  const categoryHtml = nodes["leaderboard-summary"].innerHTML;
  setLeaderboardSummaryGroupBy("overall");
  const overallGroups = leaderboardSummaryGroups(leaderboardRows());
  const overallHtml = nodes["leaderboard-summary"].innerHTML;

  renderLeaderboardSummary([]);
  const emptyHtml = nodes["leaderboard-summary"].innerHTML;

  const originalRenderComparisonPanels = renderComparisonPanels;
  const comparisonCalls = [];
  renderComparisonPanels = options => comparisonCalls.push(options);
  nodes.comparison.innerHTML = "";
  renderComparison();
  const multiHtml = nodes.comparison.innerHTML;
  state.view = singleReport;
  nodes.comparison.innerHTML = "sentinel";
  renderComparison();
  const singleHtml = nodes.comparison.innerHTML;
  const singleRows = reportRows();
  clearFilter("leaderboard", "status");
  setFilterValue("leaderboard", "status", "failed", true);
  const singleFilteredRows = leaderboardRows();
  renderComparisonPanels = originalRenderComparisonPanels;

  JSON.stringify({
    visibleKeys: rows.map(row => row.trial_key),
    duration: summary.duration_ms,
    tokens: summary.tokens,
    model: summary.model_duration_ms,
    toolCalls: summary.total_tool_calls,
    toolRate: summary.tool_error_rate,
    selectedDurationMean: selectionProof.duration_ms.mean,
    agentGroups: agentGroups.map(group => ({
      label: group.label,
      rows: group.rows.length,
      duration: metricFor(group, "duration_ms"),
      model: metricFor(group, "model_duration_ms"),
      toolRate: metricFor(group, "tool_error_rate"),
    })),
    defaultState,
    defaultHtml,
    openHtml,
    openMetricRows: countToken(openHtml, 'data-summary-metric='),
    defaultChartCount: countToken(defaultHtml, 'data-summary-chart='),
    statisticStates,
    p95Html,
    modelGroups: modelGroups.map(group => ({
      label: group.label,
      rows: group.rows.length,
      duration: metricFor(group, "duration_ms"),
    })),
    modelP95Occurrences: countToken(modelHtml, "5.8s"),
    modelMetricRows: countToken(modelHtml, 'data-summary-metric='),
    modelChartCount: countToken(modelHtml, 'data-summary-chart='),
    categoryGroups: categoryGroups.map(group => ({
      label: group.label,
      rows: group.rows.length,
      duration: metricFor(group, "duration_ms"),
    })),
    categoryMetricRows: countToken(categoryHtml, 'data-summary-metric='),
    categoryChartCount: countToken(categoryHtml, 'data-summary-chart='),
    overallGroups: overallGroups.map(group => ({ label: group.label, rows: group.rows.length })),
    overallMetricRows: countToken(overallHtml, 'data-summary-metric='),
    overallChartCount: countToken(overallHtml, 'data-summary-chart='),
    modelHtml,
    categoryHtml,
    overallHtml,
    emptyHtml,
    multiHtml,
    singleHtml,
    singleRows: singleRows.map(row => row.trial_key),
    singleFilteredRows: singleFilteredRows.map(row => row.trial_key),
    comparisonCalls,
  });
`, context);
console.log(result);
""".replace("__ASSET__", json.dumps(asset))
            .replace("__REPORT__", json.dumps(report))
            .replace("__SINGLE_REPORT__", json.dumps(single_report))
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

        self.assertEqual(result["visibleKeys"], ["trial:alpha", "trial:gamma"])
        self.assertEqual(result["duration"]["count"], 2)
        self.assertEqual(result["duration"]["mean"], 4000)
        self.assertEqual(result["tokens"]["mean"], 200)
        self.assertEqual(result["model"]["count"], 2)
        self.assertEqual(result["model"]["mean"], 1750)
        self.assertEqual(result["toolCalls"]["mean"], 1)
        self.assertEqual(result["toolRate"]["count"], 1)
        self.assertEqual(result["toolRate"]["mean"], 0)
        self.assertEqual(result["selectedDurationMean"], 4000)
        self.assertEqual(
            [(group["label"], group["rows"]) for group in result["agentGroups"]],
            [("agent-a", 1), ("agent-c", 1)],
        )
        self.assertEqual(result["agentGroups"][0]["duration"]["mean"], 2000)
        self.assertEqual(result["agentGroups"][0]["model"]["mean"], 3000)
        self.assertEqual(result["agentGroups"][1]["model"]["mean"], 500)
        self.assertEqual(result["agentGroups"][1]["toolRate"]["count"], 0)

        self.assertEqual(
            result["defaultState"],
            {"groupBy": "agent", "tableOpen": False, "statistic": "mean"},
        )
        self.assertIn("Leaderboard Summary", result["defaultHtml"])
        self.assertIn("Show summary table", result["defaultHtml"])
        self.assertIn('aria-expanded="false"', result["defaultHtml"])
        self.assertNotIn(
            '<table class="data-table leaderboard-summary-table"', result["defaultHtml"]
        )
        self.assertEqual(result["defaultChartCount"], 7)
        self.assertIn(
            'data-summary-statistic="mean" aria-pressed="true"', result["defaultHtml"]
        )
        self.assertIn('data-summary-group-by="category"', result["defaultHtml"])

        self.assertIn("Hide summary table", result["openHtml"])
        self.assertIn('aria-expanded="true"', result["openHtml"])
        self.assertEqual(result["openMetricRows"], 14)
        self.assertIn('data-value-type="identity" title="Metric"', result["openHtml"])
        self.assertIn('data-value-type="identity" title="Agent"', result["openHtml"])
        self.assertIn('data-value-type="number" title="Count"', result["openHtml"])
        self.assertNotIn("Missing", result["openHtml"])
        self.assertNotIn("Total", result["openHtml"])
        self.assertEqual(
            [item["key"] for item in result["statisticStates"]],
            ["mean", "min", "q1", "p50", "q3", "p95", "max"],
        )
        self.assertTrue(
            all(item["state"] == item["key"] for item in result["statisticStates"])
        )
        self.assertTrue(all(item["pressed"] for item in result["statisticStates"]))
        self.assertTrue(all(item["highlighted"] for item in result["statisticStates"]))
        self.assertTrue(all(item["tableOpen"] for item in result["statisticStates"]))
        self.assertIn('data-summary-stat-heading="p95"', result["p95Html"])

        self.assertEqual(len(result["modelGroups"]), 1)
        self.assertEqual(result["modelGroups"][0]["label"], "model-a")
        self.assertEqual(result["modelGroups"][0]["rows"], 2)
        self.assertEqual(result["modelGroups"][0]["duration"]["mean"], 4000)
        self.assertEqual(
            result["modelGroups"][0]["duration"]["distribution"]["p95"], 5800
        )
        self.assertGreaterEqual(result["modelP95Occurrences"], 2)
        self.assertEqual(result["modelMetricRows"], 7)
        self.assertEqual(result["modelChartCount"], 7)
        self.assertIn('data-value-type="identity" title="Model"', result["modelHtml"])
        self.assertIn("Active Duration; P95 5.8s; n=2", result["modelHtml"])
        self.assertIn(
            '<table class="data-table leaderboard-summary-table"', result["modelHtml"]
        )

        self.assertEqual(
            [(group["label"], group["rows"]) for group in result["categoryGroups"]],
            [("-", 1), ("frontend", 1)],
        )
        self.assertEqual(result["categoryGroups"][0]["duration"]["mean"], 6000)
        self.assertEqual(result["categoryGroups"][1]["duration"]["mean"], 2000)
        self.assertEqual(result["categoryMetricRows"], 14)
        self.assertEqual(result["categoryChartCount"], 7)
        self.assertIn(
            'data-value-type="identity" title="Category"', result["categoryHtml"]
        )
        self.assertIn("2 categories", result["categoryHtml"])
        self.assertIn(
            'id="leaderboard-summary-chart-title">P95 · Category</h3>',
            result["categoryHtml"],
        )

        self.assertEqual(result["overallGroups"], [{"label": "Overall", "rows": 2}])
        self.assertEqual(result["overallMetricRows"], 7)
        self.assertEqual(result["overallChartCount"], 0)
        self.assertIn('data-value-type="identity" title="Scope"', result["overallHtml"])
        self.assertIn(
            '<table class="data-table leaderboard-summary-table"', result["overallHtml"]
        )
        self.assertNotIn("leaderboard-summary-chart-panel", result["overallHtml"])
        self.assertIn("No visible rows to summarize.", result["emptyHtml"])
        self.assertIn('id="leaderboard-summary"', result["multiHtml"])
        self.assertIn('id="leaderboard"', result["singleHtml"])
        self.assertIn('id="trajectory-overview"', result["singleHtml"])
        self.assertNotIn('id="leaderboard-summary"', result["singleHtml"])
        self.assertEqual(result["singleRows"], ["trial:single"])
        self.assertEqual(result["singleFilteredRows"], [])
        self.assertEqual(
            result["comparisonCalls"], [{"trace": False}, {"trace": False}]
        )
