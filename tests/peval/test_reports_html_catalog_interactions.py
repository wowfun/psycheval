from __future__ import annotations

from tests.peval.reports_html_support import (
    json,
    load_asset_text,
    shutil,
    subprocess,
    unittest,
)


class PevalReportHtmlCatalogInteractionTests(unittest.TestCase):
    def test_leaderboard_row_click_opens_first_user_step_when_present(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                {
                    "trajectory_id": "trial:user",
                    "session_id": "with-user",
                    "steps": [
                        {"step_id": 1, "source": "agent", "message": "first"},
                        {"step_id": 2, "source": "User", "message": "open this"},
                        {"step_id": 3, "source": "user", "message": "not this"},
                    ],
                    "final_metrics": {},
                },
                {
                    "trajectory_id": "trial:no-user",
                    "session_id": "without-user",
                    "steps": [
                        {"step_id": 1, "source": "agent", "message": "only agent"},
                    ],
                    "final_metrics": {},
                },
            ],
            "trajectory_meta": [
                {"trial_key": "trial:user", "status": "passed", "steps": []},
                {"trial_key": "trial:no-user", "status": "passed", "steps": []},
            ],
        }
        script = f"""
const vm = require("vm");
const asset = {json.dumps(asset)};
const report = {json.dumps(report)};
const probe = {{ renderCount: 0 }};
function makeRow(trialKey) {{
  return {{
    listeners: {{}},
    addEventListener(type, handler) {{ this.listeners[type] = handler; }},
    getAttribute(name) {{ return name === "data-trial-key" ? trialKey : null; }}
  }};
}}
const userRow = makeRow("trial:user");
const noUserRow = makeRow("trial:no-user");
const root = {{
  querySelectorAll(selector) {{
    return selector === "tr[data-trial-key]" ? [userRow, noUserRow] : [];
  }}
}};
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
  requestAnimationFrame(callback) {{ callback(); }},
  report,
  probe,
  root,
  userRow,
  noUserRow,
}};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(() => {{
  state.view = report;
  renderComparisonPanels = () => {{ probe.renderCount += 1; }};
  bindTrialSelection(root);
  const userEvent = {{ stopped: false, stopPropagation() {{ this.stopped = true; }} }};
  userRow.listeners.click(userEvent);
  const afterUser = {{
    selectedTrial: state.selectedTrial,
    selectedStep: state.selectedStep,
    stopped: userEvent.stopped,
    renderCount: probe.renderCount
  }};
  const noUserEvent = {{ stopped: false, stopPropagation() {{ this.stopped = true; }} }};
  noUserRow.listeners.click(noUserEvent);
  return JSON.stringify({{
    afterUser,
    afterNoUser: {{
      selectedTrial: state.selectedTrial,
      selectedStep: state.selectedStep,
      stopped: noUserEvent.stopped,
      renderCount: probe.renderCount
    }}
  }});
}})()`, context);
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

        self.assertEqual(result["afterUser"]["selectedTrial"], "trial:user")
        self.assertEqual(
            result["afterUser"]["selectedStep"],
            {"trialKey": "trial:user", "stepId": "2"},
        )
        self.assertTrue(result["afterUser"]["stopped"])
        self.assertEqual(result["afterUser"]["renderCount"], 1)
        self.assertEqual(result["afterNoUser"]["selectedTrial"], "trial:no-user")
        self.assertIsNone(result["afterNoUser"]["selectedStep"])
        self.assertTrue(result["afterNoUser"]["stopped"])
        self.assertEqual(result["afterNoUser"]["renderCount"], 2)

    def test_serve_leaderboard_search_is_below_the_left_title(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js").rsplit('\n"peval-entrypoint";', 1)[0]
        script = r"""
const vm = require("vm");
const leaderboard = {
  innerHTML: "",
  querySelector() { return null; },
  querySelectorAll() { return []; }
};
const nodes = {
  "peval-data": { textContent: "{}" },
  "peval-i18n": { textContent: "{}" },
  "peval-token-estimates": { textContent: "{}" },
  "peval-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [] }) },
  leaderboard
};
const context = {
  document: {
    body: { classList: { toggle() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; }
  },
  window: { addEventListener() {} },
  console, JSON, Number, String, Object, Math, Date, Set, Array, RegExp, leaderboard
};
vm.createContext(context);
vm.runInContext(__ASSET__, context);
const result = vm.runInContext(`(() => {
  renderServeSourceStateControls = () => '<span data-source-state-controls></span>';
  renderAttachWorkspaceReportAction = () => '<button data-report-attach></button>';
  renderLeaderboardExportControls = () => '<span class="leaderboard-export"></span>';
  const row = normalizeCatalogRow({ source_key: "source-1", trial_key: "trial-1", trial_session_id: "session-1", readable: true });
  state.catalogRows = [row];
  renderLeaderboard([row]);
  const html = leaderboard.innerHTML;
  const titleStackStart = html.indexOf('class="leaderboard-title-stack"');
  const titleEnd = html.indexOf('</h2>', titleStackStart);
  const searchStart = html.indexOf('class="leaderboard-search"');
  const actionsStart = html.indexOf('class="leaderboard-actions"');
  const searchCount = (html.match(/class="leaderboard-search"/g) || []).length;
  return JSON.stringify({
    titleStackStart,
    titleEnd,
    searchStart,
    actionsStart,
    searchInsideTitleStack: titleStackStart >= 0 && titleEnd > titleStackStart && searchStart > titleEnd && searchStart < actionsStart,
    searchCount
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
        self.assertTrue(result["searchInsideTitleStack"])
        self.assertEqual(result["searchCount"], 1)

    def test_path_picker_fills_path_textarea_and_preserves_input_on_cancel_or_error(
        self,
    ) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn('\n"peval-entrypoint";', asset)
        asset = asset.rsplit('\n"peval-entrypoint";', 1)[0]
        script = f"""
const vm = require("vm");
const asset = {json.dumps(asset)};
const statusNode = {{
  textContent: "",
  classList: {{ toggle() {{}} }}
}};
const field = {{ value: "existing" }};
const form = {{
  querySelector(selector) {{ return selector === "[name=\\"path\\"]" ? field : null; }}
}};
const button = {{
  closest(selector) {{ return selector === "[data-source-add-form]" ? form : null; }}
}};
const responses = [
  {{ ok: true, payload: {{ paths: ["/tmp/one.jsonl", "/tmp/two.json"] }} }},
  {{ ok: true, payload: {{ paths: [] }} }},
  {{ ok: false, statusText: "Service Unavailable", payload: {{ error: "native file picker unavailable" }} }},
];
const fetchCalls = [];
function makeResponse(item) {{
  return {{
    ok: item.ok,
    statusText: item.statusText || "OK",
    text() {{ return Promise.resolve(JSON.stringify(item.payload)); }}
  }};
}}
const context = {{
  document: {{
    body: {{ classList: {{ toggle() {{}} }} }},
    addEventListener() {{}},
    getElementById(id) {{
      return id === "peval-render-options"
        ? {{ textContent: JSON.stringify({{ mode: "serve", role: "admin" }}) }}
        : null;
    }},
    querySelector(selector) {{
      if (selector === "[data-config-page-status]") return statusNode;
      return null;
    }},
    querySelectorAll: () => [],
  }},
  window: {{ addEventListener() {{}} }},
  fetch(path, options) {{
    fetchCalls.push({{ path, body: options.body, method: options.method }});
    return Promise.resolve(makeResponse(responses.shift()));
  }},
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
  requestAnimationFrame(callback) {{ callback(); }},
  statusNode,
  field,
  button,
  fetchCalls,
}};
vm.createContext(context);
vm.runInContext(asset, context);
const promise = vm.runInContext(`(async () => {{
  await choosePathSourceFiles(button);
  const afterSuccess = {{ value: field.value, status: statusNode.textContent }};
  field.value = "keep cancel";
  await choosePathSourceFiles(button);
  const afterCancel = {{ value: field.value, status: statusNode.textContent }};
  field.value = "keep error";
  await choosePathSourceFiles(button);
  return JSON.stringify({{
    afterSuccess,
    afterCancel,
    afterError: {{ value: field.value, status: statusNode.textContent }},
    fetchCalls
  }});
}})()`, context);
promise.then(result => console.log(result)).catch(error => {{ console.error(error && error.stack || error); process.exit(1); }});
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

        self.assertEqual(
            result["afterSuccess"]["value"], "/tmp/one.jsonl\n/tmp/two.json"
        )
        self.assertEqual(result["afterSuccess"]["status"], "Path selection updated")
        self.assertEqual(result["afterCancel"]["value"], "keep cancel")
        self.assertEqual(result["afterError"]["value"], "keep error")
        self.assertEqual(
            result["afterError"]["status"], "native file picker unavailable"
        )
        self.assertEqual(
            [call["path"] for call in result["fetchCalls"]], ["/api/path-picker"] * 3
        )
        self.assertTrue(
            all(
                json.loads(call["body"]) == {"multiple": True}
                for call in result["fetchCalls"]
            )
        )
