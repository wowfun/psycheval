from __future__ import annotations

from reports_html_support import *

class PevalPyReportHtmlInteractionTests(unittest.TestCase):
    @unittest.skip("superseded by shell-first catalog startup coverage")
    def test_serve_startup_loading_status_recovers_after_ready_payload(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
function makeNode() {
  return {
    textContent: "",
    innerHTML: "",
    listeners: {},
    classList: {
      values: new Set(),
      toggle(name, force) {
        const active = force === undefined ? !this.values.has(name) : Boolean(force);
        if (active) this.values.add(name);
        else this.values.delete(name);
        return active;
      },
      contains(name) { return this.values.has(name); }
    },
    addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    setAttribute() {}
  };
}
const countNode = makeNode();
const statusNode = makeNode();
const listNode = makeNode();
const nodes = {
  "peval-py-data": { textContent: "{}" },
  "peval-py-token-estimates": { textContent: "{}" },
  "peval-py-i18n": { textContent: JSON.stringify({
    serve_loading_sources: "Loading sources",
    serve_scanning_runs: "Scanning runs; sessions will appear when discovery finishes.",
    serve_latest_snapshots: "Latest snapshots",
    serve_active_snapshots: "Active snapshots",
    serve_source_count: "source",
    serve_sources_count: "sources",
    serve_no_sources: "No sources loaded"
  }) },
  "peval-py-render-options": { textContent: JSON.stringify({ mode: "serve", loading: true, sources: [] }) }
};
const context = {
  document: {
    body: { classList: { add() {}, remove() {}, toggle() {} } },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector(selector) {
      if (selector === "[data-source-count]") return countNode;
      if (selector === "[data-source-status]") return statusNode;
      if (selector === "[data-source-list]") return listNode;
      return null;
    },
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
  requestAnimationFrame(callback) { callback(); },
  countNode,
  statusNode,
  listNode,
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(() => {
  renderServeSources();
  const loading = {
    count: countNode.textContent,
    status: statusNode.textContent,
    statusLoading: statusNode.classList.contains("loading"),
    statusDanger: statusNode.classList.contains("danger"),
    list: listNode.innerHTML,
  };
  render = view => {
    state.view = view;
    renderServeSources();
  };
  applyServeMutationPayload({
    loading: false,
    sources: [{
      source_key: "source-1",
      label: "source one",
      artifact_dir: "runs/a",
      active: true,
      last_status: "ok",
      snapshot: true,
      refreshable: false
    }],
    report: { schema_version: 19, includes: ["core"], trajectory: [], trajectory_meta: [] },
    report_source_key: "source-1",
    report_source_state: "active"
  });
  const ready = {
    count: countNode.textContent,
    status: statusNode.textContent,
    statusLoading: statusNode.classList.contains("loading"),
    statusDanger: statusNode.classList.contains("danger"),
    list: listNode.innerHTML,
  };
  return JSON.stringify({ loading, ready });
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

        self.assertEqual(result["loading"]["count"], "Loading sources")
        self.assertEqual(
            result["loading"]["status"],
            "Scanning runs; sessions will appear when discovery finishes.",
        )
        self.assertTrue(result["loading"]["statusLoading"])
        self.assertFalse(result["loading"]["statusDanger"])
        self.assertIn("source-row empty loading", result["loading"]["list"])
        self.assertNotIn("No sources loaded", result["loading"]["list"])
        self.assertEqual(result["ready"]["count"], "1 source")
        self.assertEqual(result["ready"]["status"], "Active snapshots")
        self.assertFalse(result["ready"]["statusLoading"])
        self.assertFalse(result["ready"]["statusDanger"])
        self.assertIn("source one", result["ready"]["list"])

    def test_inline_source_edit_click_does_not_trigger_trial_selection_rerender(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = f"""
const vm = require("vm");
const asset = {json.dumps(asset)};
const listeners = {{ click: [], dblclick: [] }};
const probe = {{ renderCount: 0, replaced: false, focused: false, selected: false }};
const input = {{
  className: "",
  value: "",
  setAttribute() {{}},
  addEventListener() {{}},
  focus() {{ probe.focused = true; }},
  select() {{ probe.selected = true; }}
}};
const cell = {{
  dataset: {{
    sourceKey: "source-1",
    sourceInlineEdit: "alias",
    value: "",
    trialKey: "trial-1"
  }},
  innerHTML: "<span>-</span>",
  addEventListener(type, handler) {{
    if (listeners[type]) listeners[type].push(handler);
  }},
  querySelector(selector) {{
    return probe.replaced && selector === "input" ? input : null;
  }},
  replaceChildren(node) {{
    probe.replaced = node === input;
  }},
  getAttribute(name) {{
    return name === "data-trial-key" ? "trial-1" : null;
  }}
}};
const target = {{
  querySelector() {{ return null; }},
  querySelectorAll(selector) {{
    if (selector === "[data-source-inline-edit]") return [cell];
    if (selector === "[data-trial-key]") return [cell];
    return [];
  }}
}};
const nodes = {{
  "peval-py-data": {{ textContent: "{{}}" }},
  "peval-py-i18n": {{ textContent: "{{}}" }},
  "peval-py-token-estimates": {{ textContent: "{{}}" }},
  "peval-py-render-options": {{ textContent: JSON.stringify({{
    mode: "serve",
    sources: [{{ source_key: "source-1", trial_key: "trial-1", active: true, artifact_dir: "runs/a", last_status: "ok" }}]
  }}) }},
}};
const context = {{
  document: {{
    body: {{ classList: {{ add() {{}}, remove() {{}}, toggle() {{}} }} }},
    addEventListener() {{}},
    createElement() {{ return input; }},
    getElementById(id) {{ return nodes[id] || null; }},
    querySelector() {{ return null; }},
    querySelectorAll() {{ return []; }},
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
  target,
  listeners,
  probe,
}};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(() => {{
  state.view = {{
    trajectory: [{{ session_id: "session-1", final_metrics: {{}} }}],
    trajectory_meta: [{{ trial_key: "trial-1", status: "passed", steps: [] }}]
  }};
  state.serveSources = [{{ source_key: "source-1", trial_key: "trial-1", active: true, artifact_dir: "runs/a", last_status: "ok" }}];
  renderComparisonPanels = () => {{ probe.renderCount += 1; }};
  bindInlineSourceEditors(target);
  bindTrialSelection(target);
  const clickEvent = {{ preventDefault() {{}}, stopPropagation() {{ this.stopped = true; }} }};
  listeners.click.forEach(handler => handler(clickEvent));
  const afterClick = {{ renderCount: probe.renderCount, replaced: probe.replaced, stopped: Boolean(clickEvent.stopped) }};
  const dblclickEvent = {{ preventDefault() {{ this.defaultPrevented = true; }}, stopPropagation() {{ this.stopped = true; }} }};
  listeners.dblclick.forEach(handler => handler(dblclickEvent));
  return JSON.stringify({{ afterClick, afterDoubleClick: {{ renderCount: probe.renderCount, replaced: probe.replaced, focused: probe.focused, selected: probe.selected, stopped: Boolean(dblclickEvent.stopped), defaultPrevented: Boolean(dblclickEvent.defaultPrevented) }} }});
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

        self.assertEqual(result["afterClick"]["renderCount"], 0)
        self.assertFalse(result["afterClick"]["replaced"])
        self.assertTrue(result["afterClick"]["stopped"])
        self.assertEqual(result["afterDoubleClick"]["renderCount"], 0)
        self.assertTrue(result["afterDoubleClick"]["replaced"])
        self.assertTrue(result["afterDoubleClick"]["focused"])
        self.assertTrue(result["afterDoubleClick"]["selected"])

    def test_leaderboard_row_click_opens_first_user_step_when_present(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
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

    def test_path_picker_fills_path_textarea_and_preserves_input_on_cancel_or_error(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
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
    getElementById: () => null,
    querySelector(selector) {{
      if (selector === "[data-source-status]") return statusNode;
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

        self.assertEqual(result["afterSuccess"]["value"], "/tmp/one.jsonl\n/tmp/two.json")
        self.assertEqual(result["afterSuccess"]["status"], "Path selection updated")
        self.assertEqual(result["afterCancel"]["value"], "keep cancel")
        self.assertEqual(result["afterError"]["value"], "keep error")
        self.assertEqual(result["afterError"]["status"], "native file picker unavailable")
        self.assertEqual([call["path"] for call in result["fetchCalls"]], ["/api/path-picker"] * 3)
        self.assertTrue(
            all(json.loads(call["body"]) == {"multiple": True} for call in result["fetchCalls"])
        )

    def test_inline_source_tags_editor_can_toggle_existing_tags(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = f"""
const vm = require("vm");
const asset = {json.dumps(asset)};
const probe = {{ renderCount: 0, focused: false, selected: false }};
class Element {{
  constructor(tagName = "div") {{
    this.tagName = String(tagName).toUpperCase();
    this.children = [];
    this.dataset = {{}};
    this.attributes = {{}};
    this.listeners = {{}};
    this.className = "";
    this.value = "";
    this.textContent = "";
    this.innerHTML = "";
    this.type = "";
    this.classList = {{
      values: new Set(),
      toggle: (name, force) => {{
        const active = force === undefined ? !this.classList.values.has(name) : Boolean(force);
        if (active) this.classList.values.add(name);
        else this.classList.values.delete(name);
        return active;
      }},
      contains: name => this.classList.values.has(name)
    }};
  }}
  appendChild(node) {{
    this.children.push(node);
    node.parentNode = this;
    return node;
  }}
  replaceChildren(...nodes) {{
    this.children = nodes;
    nodes.forEach(node => {{ node.parentNode = this; }});
  }}
  addEventListener(type, handler) {{
    (this.listeners[type] ||= []).push(handler);
  }}
  dispatch(type) {{
    const event = {{
      defaultPrevented: false,
      stopped: false,
      preventDefault() {{ this.defaultPrevented = true; }},
      stopPropagation() {{ this.stopped = true; }}
    }};
    (this.listeners[type] || []).forEach(handler => handler(event));
    return event;
  }}
  setAttribute(name, value) {{
    this.attributes[name] = String(value);
  }}
  getAttribute(name) {{
    return this.attributes[name] || null;
  }}
  querySelector(selector) {{
    return this.querySelectorAll(selector)[0] || null;
  }}
  querySelectorAll(selector) {{
    const matches = node => {{
      if (selector === "input") return node.tagName === "INPUT";
      if (selector === "[data-source-tag-option]") return Object.prototype.hasOwnProperty.call(node.dataset, "sourceTagOption");
      return false;
    }};
    const found = [];
    const visit = node => {{
      if (matches(node)) found.push(node);
      node.children.forEach(visit);
    }};
    this.children.forEach(visit);
    return found;
  }}
  focus() {{ probe.focused = true; }}
  select() {{ probe.selected = true; }}
}}
const cell = new Element("span");
cell.dataset = {{
  sourceKey: "source-1",
  sourceInlineEdit: "tags",
  value: "green, custom",
  trialKey: "trial-1"
}};
const nodes = {{
  "peval-py-data": {{ textContent: "{{}}" }},
  "peval-py-i18n": {{ textContent: "{{}}" }},
  "peval-py-token-estimates": {{ textContent: "{{}}" }},
  "peval-py-render-options": {{ textContent: JSON.stringify({{
    mode: "serve",
    sources: [
      {{ source_key: "source-1", trial_key: "trial-1", active: true, artifact_dir: "runs/a", last_status: "ok", source_tags: ["green", "blue"] }},
      {{ source_key: "source-2", trial_key: "trial-2", active: false, artifact_dir: "runs/b", last_status: "ok", source_tags: ["red"] }}
    ]
  }}) }},
}};
const context = {{
  document: {{
    body: {{ classList: {{ add() {{}}, remove() {{}}, toggle() {{}} }} }},
    addEventListener() {{}},
    createElement(tagName) {{ return new Element(tagName); }},
    getElementById(id) {{ return nodes[id] || null; }},
    querySelector() {{ return null; }},
    querySelectorAll() {{ return []; }},
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
  probe,
  cell,
}};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(() => {{
  state.view = {{
    trajectory: [{{ session_id: "session-1", final_metrics: {{}} }}],
    trajectory_meta: [{{ trial_key: "trial-1", status: "passed", steps: [], source_tags: ["blue", "yellow"] }}]
  }};
  state.serveReportCache = {{
    archived: {{ trajectory_meta: [{{ trial_key: "trial-2", source_tags: ["purple"] }}] }}
  }};
  renderComparisonPanels = () => {{ probe.renderCount += 1; }};
  beginInlineSourceEdit(cell);
  const editor = cell.children[0];
  const input = editor.querySelector("input");
  const options = editor.querySelectorAll("[data-source-tag-option]");
  const labels = options.map(option => option.textContent);
  const before = {{
    value: input.value,
    labels,
    greenSelected: options.find(option => option.textContent === "green").classList.contains("selected"),
    blueSelected: options.find(option => option.textContent === "blue").classList.contains("selected")
  }};
  const blueClick = options.find(option => option.textContent === "blue").dispatch("click");
  const afterBlue = {{
    value: input.value,
    blueSelected: options.find(option => option.textContent === "blue").classList.contains("selected"),
    stopped: blueClick.stopped,
    defaultPrevented: blueClick.defaultPrevented
  }};
  const greenClick = options.find(option => option.textContent === "green").dispatch("click");
  input.value = input.value + ", manual";
  input.listeners.input.forEach(handler => handler({{}}));
  const redClick = options.find(option => option.textContent === "red").dispatch("click");
  return JSON.stringify({{
    before,
    afterBlue,
    afterGreenAndRed: {{
      value: input.value,
      greenSelected: options.find(option => option.textContent === "green").classList.contains("selected"),
      redSelected: options.find(option => option.textContent === "red").classList.contains("selected"),
      greenStopped: greenClick.stopped,
      redStopped: redClick.stopped
    }},
    renderCount: probe.renderCount,
    focused: probe.focused,
    selected: probe.selected
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

        self.assertEqual(result["before"]["value"], "green, custom")
        self.assertEqual(result["before"]["labels"], ["green", "blue", "red", "yellow", "purple"])
        self.assertTrue(result["before"]["greenSelected"])
        self.assertFalse(result["before"]["blueSelected"])
        self.assertEqual(result["afterBlue"]["value"], "green, custom, blue")
        self.assertTrue(result["afterBlue"]["blueSelected"])
        self.assertTrue(result["afterBlue"]["stopped"])
        self.assertTrue(result["afterBlue"]["defaultPrevented"])
        self.assertEqual(result["afterGreenAndRed"]["value"], "custom, blue, manual, red")
        self.assertFalse(result["afterGreenAndRed"]["greenSelected"])
        self.assertTrue(result["afterGreenAndRed"]["redSelected"])
        self.assertTrue(result["afterGreenAndRed"]["greenStopped"])
        self.assertTrue(result["afterGreenAndRed"]["redStopped"])
        self.assertEqual(result["renderCount"], 0)
        self.assertTrue(result["focused"])
        self.assertTrue(result["selected"])

    @unittest.skip("superseded by server-side catalog query coverage")
    def test_leaderboard_search_and_tag_filters_use_serve_source_rows(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
        sources = [
            {
                "source_key": "source-active",
                "active": True,
                "artifact_dir": "runs/a",
                "last_status": "ok",
                "trial_key": "trial:active",
                "source_tags": ["green"],
            },
            {
                "source_key": "source-archived",
                "active": False,
                "artifact_dir": "runs/b",
                "last_status": "ok",
                "trial_key": "trial:archived",
                "source_tags": ["red", "blue"],
            },
        ]
        report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                {
                    "trajectory_id": "trial:active",
                    "session_id": "active",
                    "steps": [{"step_id": 1, "source": "user", "message": "needle in message"}],
                    "final_metrics": {},
                },
                {
                    "trajectory_id": "trial:archived",
                    "session_id": "archived",
                    "steps": [
                        {
                            "step_id": 1,
                            "source": "agent",
                            "reasoning_content": "hidden thought",
                            "tool_calls": [{"function_name": "lookup", "arguments": {"q": "blue"}}],
                            "observation": {"content": "observed target"},
                        }
                    ],
                    "final_metrics": {},
                },
            ],
            "trajectory_meta": [
                {"trial_key": "trial:active", "status": "passed", "steps": [], "source_tags": ["green"]},
                {"trial_key": "trial:archived", "status": "passed", "steps": [], "source_tags": ["red", "blue"]},
            ],
        }
        script = f"""
const vm = require("vm");
const asset = {json.dumps(asset)};
const report = {json.dumps(report)};
const sources = {json.dumps(sources)};
const nodes = {{
  "peval-py-data": {{ textContent: "{{}}" }},
  "peval-py-i18n": {{ textContent: "{{}}" }},
  "peval-py-token-estimates": {{ textContent: "{{}}" }},
  "peval-py-render-options": {{ textContent: JSON.stringify({{ mode: "serve", sources }}) }},
}};
const context = {{
  document: {{
    body: {{ classList: {{ add() {{}}, remove() {{}}, toggle() {{}} }} }},
    addEventListener() {{}},
    getElementById(id) {{ return nodes[id] || null; }},
    querySelector() {{ return null; }},
    querySelectorAll() {{ return []; }},
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
  sources,
}};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(() => {{
  state.view = report;
  state.serveSources = sources;
  state.serveSourceMode = "all";
  const searchMarkup = renderLeaderboardSearchControls();
  const scopeListeners = {{}};
  const scopeControl = {{
    value: "visible",
    addEventListener(type, handler) {{ scopeListeners[type] = handler; }}
  }};
  const searchTarget = {{
    querySelector(selector) {{
      return selector === "[data-leaderboard-search-scope]" ? scopeControl : null;
    }}
  }};
  let applyCount = 0;
  applyLeaderboardSearchMode = () => {{ applyCount += 1; }};
  bindLeaderboardSearchControls(searchTarget);
  scopeControl.value = "all";
  scopeListeners.change({{ stopPropagation() {{}} }});
  state.search.query = "needle";
  const messageRows = leaderboardRows().map(row => [row.trial_key, row.source_key, row.source_tags]);
  state.search.query = "observed target";
  const observationRows = leaderboardRows().map(row => row.trial_key);
  state.search.query = "";
  setFilterValue("leaderboard", "source_tags", "blue", true);
  const tagRows = leaderboardRows().map(row => row.trial_key);
  return JSON.stringify({{
    messageRows,
    observationRows,
    tagRows,
    applyCount,
    selectedScope: state.search.scope,
    hasScopeSelect: searchMarkup.includes("data-leaderboard-search-scope"),
    hasVisibleOption: searchMarkup.includes('<option value="visible"'),
    hasAllOption: searchMarkup.includes('<option value="all"'),
    hasScopeRadios: searchMarkup.includes('type="radio"')
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

        self.assertEqual(
            result["messageRows"],
            [["trial:active", "source-active", ["green"]]],
        )
        self.assertEqual(result["observationRows"], ["trial:archived"])
        self.assertEqual(result["tagRows"], ["trial:archived"])
        self.assertEqual(result["applyCount"], 1)
        self.assertEqual(result["selectedScope"], "all")
        self.assertTrue(result["hasScopeSelect"])
        self.assertTrue(result["hasVisibleOption"])
        self.assertTrue(result["hasAllOption"])
        self.assertFalse(result["hasScopeRadios"])

    def test_markdown_renderer_renders_analysis_md_headings_tables_and_escapes(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
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
        self.assertIn('<h4 class="markdown-heading markdown-heading-1">Cached Review</h4>', rendered)
        self.assertIn('<h5 class="markdown-heading markdown-heading-2">Slow step</h5>', rendered)
        self.assertIn("<strong>strong</strong>", rendered)
        self.assertIn("<em>emphasis</em>", rendered)
        self.assertIn("<code>inline_code</code>", rendered)
        self.assertIn('<div class="markdown-table-wrap"><table class="markdown-table">', rendered)
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
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
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
                }
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
                }
            ],
        }
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
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

    @unittest.skip("superseded by server-side catalog export coverage")
    def test_html_runtime_rows_and_export_subset_avoid_persisted_comparison(self) -> None:
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
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
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
  const analysisedValues = rows.map(row => rowAnalysised(row));
  const analysisedColumn = leaderboardColumns().find(column => column.key === "analysised");
  const analysisedFilterable = Boolean(analysisedColumn?.filterable);
  const analysisedOptions = filterOptions(analysisedColumn, reportRows());
  setFilterValue("leaderboard", "analysised", "True", true);
  const trueFilteredKeys = leaderboardRows().map(row => row.trial_key);
  clearFilter("leaderboard", "analysised");
  setFilterValue("leaderboard", "analysised", "False", true);
  const falseFilteredKeys = leaderboardRows().map(row => row.trial_key);
  clearFilter("leaderboard", "analysised");
  const xlsxBytes = xlsxBytesForRows(rows);
  const xlsxText = Buffer.from(xlsxBytes).toString("utf8");
  let downloaded = null;
  downloadBlob = (filename, mime, blob) => {{
    downloaded = {{ filename, mime, type: blob.type, size: blob.size }};
  }};
  exportCurrentScope("xlsx");
  state.view = legacyReport;
  const legacyRows = reportRows();
  JSON.stringify({{
    rowCount: rows.length,
    firstAdapter: rows[0].adapter,
    firstErrorRate: rowToolErrorRate(rows[0]),
    analysisedValues,
    analysisedFilterable,
    analysisedOptions,
    trueFilteredKeys,
    falseFilteredKeys,
    pathChecks: [
      isAnalysisArtifactPath("runs/default/agent/session/cell/analysis.md"),
      isAnalysisArtifactPath("runs/default/agent/session/cell/analysis.json"),
      isAnalysisArtifactPath("runs/default/agent/session/cell/notes.md")
    ],
    xlsxZipMagic: [xlsxBytes[0], xlsxBytes[1], xlsxBytes[2], xlsxBytes[3]],
    xlsxHasHeader: xlsxText.includes("Analysised"),
    xlsxHasTrue: xlsxText.includes("<t>True</t>"),
    xlsxHasFalse: xlsxText.includes("<t>False</t>"),
    downloaded,
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
        self.assertEqual(result["analysisedValues"], ["True", "False"])
        self.assertTrue(result["analysisedFilterable"])
        self.assertEqual(result["analysisedOptions"], ["False", "True"])
        self.assertEqual(result["trueFilteredKeys"], ["trial:one"])
        self.assertEqual(result["falseFilteredKeys"], ["trial:two"])
        self.assertEqual(result["pathChecks"], [True, True, False])
        self.assertEqual(result["xlsxZipMagic"], [80, 75, 3, 4])
        self.assertTrue(result["xlsxHasHeader"])
        self.assertTrue(result["xlsxHasTrue"])
        self.assertTrue(result["xlsxHasFalse"])
        self.assertEqual(result["downloaded"]["filename"], "peval-leaderboard-visible.xlsx")
        self.assertEqual(
            result["downloaded"]["mime"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertEqual(
            result["downloaded"]["type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertGreater(result["downloaded"]["size"], 0)
        self.assertFalse(result["subsetHasComparison"])
        self.assertEqual(result["subsetIncludes"], ["core"])
        self.assertEqual(result["subsetNotes"], ["keep"])
        self.assertEqual(result["subsetAnalysisKeys"], ["trial:one", "trial:two"])
        self.assertEqual(result["legacyRowCount"], 0)

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
                    "duration_ms": 2000,
                    "steps": [
                        {"step_id": 1, "duration_ms": 100},
                        {"step_id": 2, "duration_ms": 1000, "duration_source": "measured"},
                        {"step_id": 3, "duration_ms": 2000, "duration_source": "boundary_estimate"},
                        {"step_id": 4, "duration_ms": 500},
                    ],
                    "warnings": [],
                },
                {
                    "trial_key": "trial:beta",
                    "status": "failed",
                    "duration_ms": 3000,
                    "steps": [
                        {"step_id": 1, "duration_ms": 3000, "duration_source": "measured"},
                    ],
                    "warnings": [],
                },
                {
                    "trial_key": "trial:gamma",
                    "status": "passed",
                    "duration_ms": 6000,
                    "steps": [
                        {"step_id": 1, "duration_ms": 500, "duration_source": "measured"},
                        {"step_id": 2, "duration_ms": None, "duration_source": "measured"},
                    ],
                    "warnings": [],
                },
            ],
        }
        single_report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [{"trajectory_id": "trial:single", "session_id": "single", "steps": []}],
            "trajectory_meta": [{"trial_key": "trial:single", "status": "passed", "steps": []}],
        }
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const report = __REPORT__;
const singleReport = __SINGLE_REPORT__;
const nodes = {
  "peval-py-i18n": { textContent: "{}" },
  "peval-py-token-estimates": { textContent: "{}" },
  "peval-py-render-options": { textContent: JSON.stringify({ mode: "report" }) },
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
    overallGroups: overallGroups.map(group => ({ label: group.label, rows: group.rows.length })),
    overallMetricRows: countToken(overallHtml, 'data-summary-metric='),
    overallChartCount: countToken(overallHtml, 'data-summary-chart='),
    modelHtml,
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
""".replace("__ASSET__", json.dumps(asset)).replace("__REPORT__", json.dumps(report)).replace("__SINGLE_REPORT__", json.dumps(single_report))
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
        self.assertEqual(result["model"]["mean"], 750)
        self.assertEqual(result["toolCalls"]["mean"], 1)
        self.assertEqual(result["toolRate"]["count"], 1)
        self.assertEqual(result["toolRate"]["mean"], 0)
        self.assertEqual(result["selectedDurationMean"], 4000)
        self.assertEqual(
            [(group["label"], group["rows"]) for group in result["agentGroups"]],
            [("agent-a", 1), ("agent-c", 1)],
        )
        self.assertEqual(result["agentGroups"][0]["duration"]["mean"], 2000)
        self.assertEqual(result["agentGroups"][0]["model"]["mean"], 1000)
        self.assertEqual(result["agentGroups"][1]["model"]["mean"], 500)
        self.assertEqual(result["agentGroups"][1]["toolRate"]["count"], 0)

        self.assertEqual(
            result["defaultState"],
            {"groupBy": "agent", "tableOpen": False, "statistic": "mean"},
        )
        self.assertIn("Leaderboard Summary", result["defaultHtml"])
        self.assertIn("Show summary table", result["defaultHtml"])
        self.assertIn('aria-expanded="false"', result["defaultHtml"])
        self.assertNotIn('<table class="data-table leaderboard-summary-table"', result["defaultHtml"])
        self.assertEqual(result["defaultChartCount"], 6)
        self.assertIn('data-summary-statistic="mean" aria-pressed="true"', result["defaultHtml"])

        self.assertIn("Hide summary table", result["openHtml"])
        self.assertIn('aria-expanded="true"', result["openHtml"])
        self.assertEqual(result["openMetricRows"], 12)
        self.assertIn("<th>Metric</th>", result["openHtml"])
        self.assertIn("<th>Agent</th>", result["openHtml"])
        self.assertIn('class="num">Count</th>', result["openHtml"])
        self.assertNotIn("Missing", result["openHtml"])
        self.assertNotIn("Total", result["openHtml"])
        self.assertEqual(
            [item["key"] for item in result["statisticStates"]],
            ["mean", "min", "q1", "p50", "q3", "p95", "max"],
        )
        self.assertTrue(all(item["state"] == item["key"] for item in result["statisticStates"]))
        self.assertTrue(all(item["pressed"] for item in result["statisticStates"]))
        self.assertTrue(all(item["highlighted"] for item in result["statisticStates"]))
        self.assertTrue(all(item["tableOpen"] for item in result["statisticStates"]))
        self.assertIn('data-summary-stat-heading="p95"', result["p95Html"])

        self.assertEqual(len(result["modelGroups"]), 1)
        self.assertEqual(result["modelGroups"][0]["label"], "model-a")
        self.assertEqual(result["modelGroups"][0]["rows"], 2)
        self.assertEqual(result["modelGroups"][0]["duration"]["mean"], 4000)
        self.assertEqual(result["modelGroups"][0]["duration"]["distribution"]["p95"], 5800)
        self.assertGreaterEqual(result["modelP95Occurrences"], 2)
        self.assertEqual(result["modelMetricRows"], 6)
        self.assertEqual(result["modelChartCount"], 6)
        self.assertIn("<th>Model</th>", result["modelHtml"])
        self.assertIn("Active Duration; P95 5.8s; n=2", result["modelHtml"])
        self.assertIn('<table class="data-table leaderboard-summary-table"', result["modelHtml"])

        self.assertEqual(result["overallGroups"], [{"label": "Overall", "rows": 2}])
        self.assertEqual(result["overallMetricRows"], 6)
        self.assertEqual(result["overallChartCount"], 0)
        self.assertIn("<th>Scope</th>", result["overallHtml"])
        self.assertIn('<table class="data-table leaderboard-summary-table"', result["overallHtml"])
        self.assertNotIn("leaderboard-summary-chart-panel", result["overallHtml"])
        self.assertIn("No visible rows to summarize.", result["emptyHtml"])
        self.assertIn('id="leaderboard-summary"', result["multiHtml"])
        self.assertIn('id="leaderboard"', result["singleHtml"])
        self.assertIn('id="trajectory-overview"', result["singleHtml"])
        self.assertNotIn('id="leaderboard-summary"', result["singleHtml"])
        self.assertEqual(result["singleRows"], ["trial:single"])
        self.assertEqual(result["singleFilteredRows"], [])
        self.assertEqual(result["comparisonCalls"], [{"trace": False}, {"trace": False}])

    @unittest.skip("full embedded serve reports were replaced by catalog detail loading")
    def test_serve_source_selection_uses_full_report_uniquified_trials(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        sources = [
            {
                "source_key": "source-a",
                "active": True,
                "artifact_dir": "runs/default/a/session_t001",
                "last_status": "ok",
                "trial_key": "session:t001",
            },
            {
                "source_key": "source-b",
                "active": True,
                "artifact_dir": "runs/default/b/session_t001",
                "last_status": "ok",
                "trial_key": "session:t001",
            },
            {
                "source_key": "source-c",
                "active": True,
                "artifact_dir": "runs/default/c/session_t001",
                "last_status": "ok",
                "trial_key": "session:t001",
            },
        ]
        report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                {
                    "trajectory_id": "trial:a",
                    "session_id": "a",
                    "steps": [],
                    "final_metrics": {"extra": {"total_turns": 1, "total_tool_calls": 0}},
                },
                {
                    "trajectory_id": "trial:b",
                    "session_id": "b",
                    "steps": [],
                    "final_metrics": {"extra": {"total_turns": 1, "total_tool_calls": 0}},
                },
                {
                    "trajectory_id": "trial:c",
                    "session_id": "c",
                    "steps": [],
                    "final_metrics": {"extra": {"total_turns": 1, "total_tool_calls": 0}},
                },
            ],
            "trajectory_meta": [
                {"trial_key": "session:t001", "status": "passed", "duration_ms": 100, "steps": [], "warnings": []},
                {"trial_key": "session:t001:2", "status": "passed", "duration_ms": 200, "steps": [], "warnings": []},
                {"trial_key": "session:t001:3", "status": "failed", "duration_ms": 300, "steps": [], "warnings": []},
            ],
        }
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const report = __REPORT__;
const sources = __SOURCES__;
const nodes = {};
function makeNode(id) {
  const node = {
    id,
    textContent: "",
    hidden: false,
    dataset: {},
    style: {},
    classList: { add() {}, remove() {}, toggle() {} },
    addEventListener() {},
    removeEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    closest() { return null; },
    _innerHTML: "",
  };
  Object.defineProperty(node, "innerHTML", {
    get() { return this._innerHTML; },
    set(value) {
      this._innerHTML = String(value || "");
      for (const match of this._innerHTML.matchAll(/id="([^"]+)"/g)) {
        if (!nodes[match[1]]) nodes[match[1]] = makeNode(match[1]);
      }
    },
  });
  return node;
}
[
  "peval-py-data",
  "peval-py-i18n",
  "peval-py-token-estimates",
  "peval-py-render-options",
  "report-notes",
  "comparison",
  "trace",
  "step-drawer",
].forEach(id => nodes[id] = makeNode(id));
nodes["peval-py-data"].textContent = "{}";
nodes["peval-py-i18n"].textContent = "{}";
nodes["peval-py-token-estimates"].textContent = "{}";
nodes["peval-py-render-options"].textContent = JSON.stringify({ mode: "serve", sources: [] });
const context = {
  nodes,
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
  requestAnimationFrame(callback) { callback(); },
  fetch() { throw new Error("source selection must not fetch a single-source report"); },
  report,
  sources,
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`
  applyServeMutationPayload({ sources, report, report_source_key: "source-b" });
  const afterMutation = {
    selectedTrial: state.selectedTrial,
    selectedSourceKey: state.selectedSourceKey,
    reportRows: reportRows().length,
    hasLeaderboard: nodes.leaderboard.innerHTML.includes("Leaderboard"),
    hasSummary: nodes["leaderboard-summary"].innerHTML.includes("Leaderboard Summary"),
    mappedSecond: sourceKeyForTrialKey("session:t001:2"),
  };
  state.rowSelection.add("session:t001:2");
  selectServeSource("source-c");
  const afterSourceSelect = {
    selectedTrial: state.selectedTrial,
    selectedSourceKey: state.selectedSourceKey,
    reportRows: reportRows().length,
    rowSelectionKept: state.rowSelection.has("session:t001:2"),
    hasLeaderboard: nodes.leaderboard.innerHTML.includes("Leaderboard"),
    hasSummary: nodes["leaderboard-summary"].innerHTML.includes("Leaderboard Summary"),
    hasOverview: nodes["trajectory-overview"].innerHTML.includes("Trajectory Overview"),
  };
  loadServeSourceReport("source-a");
  const afterLegacyLoadName = {
    selectedTrial: state.selectedTrial,
    selectedSourceKey: state.selectedSourceKey,
    reportRows: reportRows().length,
  };
  JSON.stringify({ afterMutation, afterSourceSelect, afterLegacyLoadName });
`, context);
console.log(result);
""".replace("__ASSET__", json.dumps(asset)).replace("__REPORT__", json.dumps(report)).replace("__SOURCES__", json.dumps(sources))
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

        self.assertEqual(result["afterMutation"]["selectedTrial"], "session:t001:2")
        self.assertEqual(result["afterMutation"]["selectedSourceKey"], "source-b")
        self.assertEqual(result["afterMutation"]["reportRows"], 3)
        self.assertTrue(result["afterMutation"]["hasLeaderboard"])
        self.assertTrue(result["afterMutation"]["hasSummary"])
        self.assertEqual(result["afterMutation"]["mappedSecond"], "source-b")
        self.assertEqual(result["afterSourceSelect"]["selectedTrial"], "session:t001:3")
        self.assertEqual(result["afterSourceSelect"]["selectedSourceKey"], "source-c")
        self.assertEqual(result["afterSourceSelect"]["reportRows"], 3)
        self.assertTrue(result["afterSourceSelect"]["rowSelectionKept"])
        self.assertTrue(result["afterSourceSelect"]["hasLeaderboard"])
        self.assertTrue(result["afterSourceSelect"]["hasSummary"])
        self.assertTrue(result["afterSourceSelect"]["hasOverview"])
        self.assertEqual(result["afterLegacyLoadName"]["selectedTrial"], "session:t001")
        self.assertEqual(result["afterLegacyLoadName"]["selectedSourceKey"], "source-a")
        self.assertEqual(result["afterLegacyLoadName"]["reportRows"], 3)

    @unittest.skip("superseded by server-paginated state and operation coverage")
    def test_serve_archived_mode_lazy_loads_and_batches_visible_selection(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        sources = [
            {"source_key": "source-a", "active": True, "artifact_dir": "runs/a", "last_status": "ok", "trial_key": "trial:active-a"},
            {"source_key": "source-b", "active": True, "artifact_dir": "runs/b", "last_status": "ok", "trial_key": "trial:active-b"},
            {"source_key": "source-c", "active": True, "artifact_dir": "runs/c", "last_status": "ok", "trial_key": "trial:active-c"},
            {"source_key": "source-d", "active": False, "artifact_dir": "runs/d", "last_status": "ok", "trial_key": "trial:archived-d"},
        ]
        sources_after_archive = [
            {**sources[0], "active": False},
            sources[1],
            sources[2],
            sources[3],
        ]
        active_report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                {"trajectory_id": "trial:active-a", "session_id": "active-a", "steps": [], "final_metrics": {"extra": {"total_turns": 1}}},
                {"trajectory_id": "trial:active-b", "session_id": "active-b", "steps": [], "final_metrics": {"extra": {"total_turns": 2}}},
                {"trajectory_id": "trial:active-c", "session_id": "active-c", "steps": [], "final_metrics": {"extra": {"total_turns": 3}}},
            ],
            "trajectory_meta": [
                {"trial_key": "trial:active-a", "status": "passed", "duration_ms": 1000, "steps": [], "warnings": []},
                {"trial_key": "trial:active-b", "status": "failed", "duration_ms": 2000, "steps": [], "warnings": []},
                {"trial_key": "trial:active-c", "status": "passed", "duration_ms": 3000, "steps": [], "warnings": []},
            ],
        }
        active_after_archive = {
            **active_report,
            "trajectory": active_report["trajectory"][1:],
            "trajectory_meta": active_report["trajectory_meta"][1:],
        }
        archived_report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                {"trajectory_id": "trial:archived-d", "session_id": "archived-d", "steps": [], "final_metrics": {"extra": {"total_turns": 4}}},
            ],
            "trajectory_meta": [
                {"trial_key": "trial:archived-d", "status": "passed", "duration_ms": 4000, "steps": [], "warnings": []},
            ],
        }
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const activeReport = __ACTIVE_REPORT__;
const archivedReport = __ARCHIVED_REPORT__;
const sources = __SOURCES__;
const sourcesAfterArchive = __SOURCES_AFTER_ARCHIVE__;
const activeAfterArchive = __ACTIVE_AFTER_ARCHIVE__;
const nodes = {};
function makeNode(id) {
  const node = {
    id,
    textContent: "",
    hidden: false,
    dataset: {},
    classList: { add() {}, remove() {}, toggle() {} },
    addEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    closest() { return null; },
    _innerHTML: "",
  };
  Object.defineProperty(node, "innerHTML", {
    get() { return this._innerHTML; },
    set(value) {
      this._innerHTML = String(value || "");
      for (const match of this._innerHTML.matchAll(/id="([^"]+)"/g)) {
        if (!nodes[match[1]]) nodes[match[1]] = makeNode(match[1]);
      }
    },
  });
  return node;
}
[
  "peval-py-i18n",
  "peval-py-token-estimates",
  "peval-py-render-options",
  "report-notes",
  "comparison",
  "trace",
  "step-drawer",
].forEach(id => nodes[id] = makeNode(id));
nodes["peval-py-i18n"].textContent = "{}";
nodes["peval-py-token-estimates"].textContent = "{}";
nodes["peval-py-render-options"].textContent = JSON.stringify({ mode: "serve", sources });
const fetchCalls = [];
function response(payload) {
  return { ok: true, statusText: "OK", text: async () => JSON.stringify(payload) };
}
const context = {
  nodes,
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
  requestAnimationFrame(callback) { callback(); },
  fetch: async (path, options = {}) => {
    const body = options.body ? JSON.parse(options.body) : null;
    fetchCalls.push({ path, body });
    if (String(path).includes("source_state=archived")) return response(archivedReport);
    if (String(path) === "/api/sources/state") {
      return response({
        sources: sourcesAfterArchive,
        report: activeAfterArchive,
        report_source_key: "source-b",
        report_source_state: "active",
      });
    }
    throw new Error(`unexpected fetch ${path}`);
  },
  activeReport,
  archivedReport,
  sources,
  sourcesAfterArchive,
  activeAfterArchive,
  fetchCalls,
};
vm.createContext(context);
vm.runInContext(asset, context);
const promise = vm.runInContext(`(async () => {
  applyServeMutationPayload({ sources, report: activeReport, report_source_key: "source-a", report_source_state: "active" });
  const actionRowStart = nodes.leaderboard.innerHTML.indexOf('class="leaderboard-action-row"');
  const searchStart = nodes.leaderboard.innerHTML.indexOf('class="leaderboard-search"');
  const actionRowMarkup = nodes.leaderboard.innerHTML.slice(actionRowStart, searchStart);
  const initial = {
    mode: state.serveSourceMode,
    leaderboardControls: (nodes.leaderboard.innerHTML.match(/data-source-state-controls/g) || []).length,
    overviewControls: (nodes["trajectory-overview"].innerHTML.match(/data-source-state-controls/g) || []).length,
    actionLabel: nodes.leaderboard.innerHTML.includes("Archive selected"),
    archivedToggleEnabled: !nodes.leaderboard.innerHTML.includes("data-source-state-toggle  disabled"),
    overviewCheckboxes: (nodes["trajectory-overview"].innerHTML.match(/data-row-select/g) || []).length,
    unifiedActionRow: actionRowStart >= 0
      && searchStart > actionRowStart
      && actionRowMarkup.includes("data-source-state-controls")
      && actionRowMarkup.includes("data-source-state-action")
      && actionRowMarkup.includes("data-report-attach")
      && actionRowMarkup.includes("leaderboard-export"),
  };
  await switchServeSourceMode("archived");
  const afterArchived = {
    mode: state.serveSourceMode,
    reportRows: reportRows().length,
    selectedSourceKey: state.selectedSourceKey,
    checkedInLeaderboard: nodes.leaderboard.innerHTML.includes("data-source-state-toggle checked"),
    checkedInOverview: nodes["trajectory-overview"].innerHTML.includes("data-source-state-toggle checked"),
    actionLabel: nodes.leaderboard.innerHTML.includes("Activate selected"),
    archivedFetches: fetchCalls.filter(call => String(call.path).includes("source_state=archived")).length,
    hasSummary: nodes.comparison.innerHTML.includes('id="leaderboard-summary"'),
  };
  await switchServeSourceMode("active");
  await switchServeSourceMode("archived");
  const cachedFetches = fetchCalls.filter(call => String(call.path).includes("source_state=archived")).length;
  await switchServeSourceMode("active");
  setFilterValue("leaderboard", "status", "passed", true);
  state.rowSelection.add("trial:active-a");
  state.rowSelection.add("trial:active-b");
  renderComparisonPanels({ trace: false });
  const activeSingleSelection = {
    actionEnabled: nodes.leaderboard.innerHTML.includes("data-source-state-action >Archive selected"),
    overviewChecked: nodes["trajectory-overview"].innerHTML.includes('data-row-select="trial:active-a" checked'),
  };
  await mutateVisibleServeSourceState();
  const statePost = fetchCalls.find(call => call.path === "/api/sources/state");
  const afterArchive = {
    mode: state.serveSourceMode,
    reportRows: reportRows().length,
    selectedSourceKey: state.selectedSourceKey,
    rowSelectionSize: state.rowSelection.size,
    statePayload: statePost.body,
  };
  const callsBeforeUnavailable = fetchCalls.length;
  state.serveSources = [sources[0], sources[1], sources[2]];
  state.serveReportCache = { active: activeReport };
  state.serveSourceMode = "active";
  render(activeReport);
  const zeroTargetDisabled = nodes.leaderboard.innerHTML.includes("data-source-state-toggle  disabled");
  await switchServeSourceMode("archived");
  const unavailable = {
    mode: state.serveSourceMode,
    fetchUnchanged: fetchCalls.length === callsBeforeUnavailable,
    zeroTargetDisabled,
  };
  return JSON.stringify({ initial, afterArchived, cachedFetches, activeSingleSelection, afterArchive, unavailable });
})()`, context);
promise.then(result => console.log(result)).catch(error => { console.error(error && error.stack || error); process.exit(1); });
""".replace("__ASSET__", json.dumps(asset)).replace("__ACTIVE_REPORT__", json.dumps(active_report)).replace("__ARCHIVED_REPORT__", json.dumps(archived_report)).replace("__SOURCES__", json.dumps(sources)).replace("__SOURCES_AFTER_ARCHIVE__", json.dumps(sources_after_archive)).replace("__ACTIVE_AFTER_ARCHIVE__", json.dumps(active_after_archive))
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

        self.assertEqual(result["initial"]["mode"], "active")
        self.assertEqual(result["initial"]["leaderboardControls"], 1)
        self.assertEqual(result["initial"]["overviewControls"], 1)
        self.assertTrue(result["initial"]["actionLabel"])
        self.assertTrue(result["initial"]["archivedToggleEnabled"])
        self.assertEqual(result["initial"]["overviewCheckboxes"], 3)
        self.assertTrue(result["initial"]["unifiedActionRow"])
        self.assertEqual(result["afterArchived"]["mode"], "archived")
        self.assertEqual(result["afterArchived"]["reportRows"], 1)
        self.assertEqual(result["afterArchived"]["selectedSourceKey"], "source-d")
        self.assertTrue(result["afterArchived"]["checkedInLeaderboard"])
        self.assertTrue(result["afterArchived"]["checkedInOverview"])
        self.assertTrue(result["afterArchived"]["actionLabel"])
        self.assertEqual(result["afterArchived"]["archivedFetches"], 1)
        self.assertFalse(result["afterArchived"]["hasSummary"])
        self.assertEqual(result["cachedFetches"], 1)
        self.assertTrue(result["activeSingleSelection"]["actionEnabled"])
        self.assertTrue(result["activeSingleSelection"]["overviewChecked"])
        self.assertEqual(result["afterArchive"]["mode"], "active")
        self.assertEqual(result["afterArchive"]["reportRows"], 2)
        self.assertEqual(result["afterArchive"]["selectedSourceKey"], "source-b")
        self.assertEqual(result["afterArchive"]["rowSelectionSize"], 0)
        self.assertEqual(result["afterArchive"]["statePayload"]["source_keys"], ["source-a"])
        self.assertFalse(result["afterArchive"]["statePayload"]["active"])
        self.assertEqual(result["afterArchive"]["statePayload"]["report_source_state"], "active")
        self.assertEqual(result["unavailable"]["mode"], "active")
        self.assertTrue(result["unavailable"]["fetchUnchanged"])
        self.assertTrue(result["unavailable"]["zeroTargetDisabled"])

    def test_sqlite_db_form_manages_adapter_defaults_in_place(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        asset = asset.rsplit("\nrender(data());", 1)[0]
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
  "peval-py-data": { textContent: "{}" },
  "peval-py-token-estimates": { textContent: "{}" },
  "peval-py-i18n": { textContent: "{}" },
  "peval-py-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [], adapter_defaults: { hermes: "/old/hermes.db" } }) }
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
            ["node"], input=script, text=True, capture_output=True, timeout=10, check=False
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
        self.assertEqual(result["afterSave"]["defaults"], {"hermes": "/resolved/new.db"})
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
            {"adapter": "auto", "path": "", "saveDisabled": True, "clearDisabled": True},
        )

    @unittest.skip("superseded by cross-page catalog selection and operation coverage")
    def test_source_manager_selection_batches_state_and_delete_actions(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        sources = [
            {"source_key": "source-a", "active": True, "artifact_dir": "runs/a", "last_status": "ok", "trial_key": "trial:active-a", "refreshable": True, "source_tags": ["priority", "release"]},
            {"source_key": "source-b", "active": False, "artifact_dir": "runs/b", "last_status": "ok", "trial_key": "trial:archived-b", "refreshable": False, "snapshot": True},
        ]
        sources_after_archive = [
            {**sources[0], "active": False},
            sources[1],
        ]
        sources_after_delete = [
            sources_after_archive[0],
        ]
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const sources = __SOURCES__;
const sourcesAfterArchive = __SOURCES_AFTER_ARCHIVE__;
const sourcesAfterDelete = __SOURCES_AFTER_DELETE__;
function makeNode(id) {
  const node = {
    id,
    textContent: "",
    hidden: false,
    disabled: false,
    dataset: {},
    classList: { add() {}, remove() {}, toggle() {} },
    addEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    closest() { return null; },
    _innerHTML: "",
  };
  Object.defineProperty(node, "innerHTML", {
    get() { return this._innerHTML; },
    set(value) { this._innerHTML = String(value || ""); },
  });
  return node;
}
const nodes = {
  list: makeNode("source-list"),
  stateButton: makeNode("state-button"),
  deleteButton: makeNode("delete-button"),
  status: makeNode("source-status"),
  count: makeNode("source-count"),
};
const fetchCalls = [];
const confirmMessages = [];
function response(payload) {
  return { ok: true, statusText: "OK", text: async () => JSON.stringify(payload) };
}
const context = {
  document: {
    body: { classList: { add() {}, remove() {}, toggle() {} } },
    addEventListener() {},
    getElementById(id) {
      if (id === "peval-py-i18n") return { textContent: "{}" };
      if (id === "peval-py-token-estimates") return { textContent: "{}" };
      if (id === "peval-py-render-options") return { textContent: JSON.stringify({ mode: "serve", sources }) };
      return null;
    },
    querySelector(selector) {
      if (selector === "[data-source-list]") return nodes.list;
      if (selector === "[data-source-bulk-state]") return nodes.stateButton;
      if (selector === "[data-source-bulk-delete]") return nodes.deleteButton;
      if (selector === "[data-source-status]") return nodes.status;
      if (selector === "[data-source-count]") return nodes.count;
      return null;
    },
    querySelectorAll() { return []; },
  },
  window: {
    addEventListener() {},
    confirm(message) {
      confirmMessages.push(message);
      return true;
    },
  },
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
  fetch: async (path, options = {}) => {
    const body = options.body ? JSON.parse(options.body) : null;
    fetchCalls.push({ path, body });
    if (path === "/api/sources/state") {
      return response({ sources: sourcesAfterArchive, report_source_state: "active" });
    }
    if (String(path) === "/api/sources/source-b/delete") {
      return response({ sources: sourcesAfterDelete, report_source_state: "active" });
    }
    throw new Error(`unexpected fetch ${path}`);
  },
  nodes,
  sources,
  sourcesAfterArchive,
  sourcesAfterDelete,
  fetchCalls,
  confirmMessages,
};
vm.createContext(context);
vm.runInContext(asset, context);
const promise = vm.runInContext(`(async () => {
  state.serveSources = sources;
  renderServeSources();
  const initial = {
    rowCheckboxes: (nodes.list.innerHTML.match(/data-source-row-select/g) || []).length,
    headerCheckbox: nodes.list.innerHTML.includes("data-source-select-visible"),
    perRowDeleteRemoved: !nodes.list.innerHTML.includes('data-source-action="delete"'),
    perRowRefreshRemoved: !nodes.list.innerHTML.includes('data-source-action="refresh"'),
    inlineAlias: nodes.list.innerHTML.includes('data-source-inline-edit="alias"'),
    aliasButtonRemoved: !nodes.list.innerHTML.includes("data-source-alias-save"),
    tagChips: (nodes.list.innerHTML.match(/source-tag-chip/g) || []).length,
    tagsReadOnly: !nodes.list.innerHTML.includes('data-source-inline-edit="tags"'),
    emptyTags: sourceColumns().find(column => column.key === "source_tags").html(sources[1]).includes('<span class="muted">-</span>'),
    bulkDisabled: nodes.stateButton.disabled && nodes.deleteButton.disabled,
  };
  state.sourceSelection.add("source-a");
  renderServeSources();
  const selectedActive = {
    label: nodes.stateButton.textContent,
    action: nodes.stateButton.dataset.sourceBulkState,
    disabled: nodes.stateButton.disabled,
  };
  await mutateSelectedServeSourceState();
  const statePost = fetchCalls.find(call => call.path === "/api/sources/state");
  const afterState = {
    payload: statePost.body,
    selectionSize: state.sourceSelection.size,
    sourceAActive: state.serveSources.find(source => source.source_key === "source-a").active,
  };
  state.sourceSelection.add("source-b");
  renderServeSources();
  const selectedArchived = {
    label: nodes.stateButton.textContent,
    action: nodes.stateButton.dataset.sourceBulkState,
  };
  await deleteSelectedServeSources();
  const deletePost = fetchCalls.find(call => String(call.path).endsWith("/source-b/delete"));
  const afterDelete = {
    confirmMessages,
    deletePath: deletePost.path,
    remainingKeys: state.serveSources.map(source => source.source_key),
    selectionSize: state.sourceSelection.size,
  };
  return JSON.stringify({ initial, selectedActive, afterState, selectedArchived, afterDelete });
})()`, context);
promise.then(result => console.log(result)).catch(error => { console.error(error && error.stack || error); process.exit(1); });
""".replace("__ASSET__", json.dumps(asset)).replace("__SOURCES__", json.dumps(sources)).replace("__SOURCES_AFTER_ARCHIVE__", json.dumps(sources_after_archive)).replace("__SOURCES_AFTER_DELETE__", json.dumps(sources_after_delete))
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

        self.assertEqual(result["initial"]["rowCheckboxes"], 2)
        self.assertTrue(result["initial"]["headerCheckbox"])
        self.assertTrue(result["initial"]["perRowDeleteRemoved"])
        self.assertTrue(result["initial"]["perRowRefreshRemoved"])
        self.assertTrue(result["initial"]["inlineAlias"])
        self.assertTrue(result["initial"]["aliasButtonRemoved"])
        self.assertEqual(result["initial"]["tagChips"], 2)
        self.assertTrue(result["initial"]["tagsReadOnly"])
        self.assertTrue(result["initial"]["emptyTags"])
        self.assertTrue(result["initial"]["bulkDisabled"])
        self.assertEqual(result["selectedActive"]["label"], "Archive selected")
        self.assertEqual(result["selectedActive"]["action"], "archived")
        self.assertFalse(result["selectedActive"]["disabled"])
        self.assertEqual(result["afterState"]["payload"]["source_keys"], ["source-a"])
        self.assertFalse(result["afterState"]["payload"]["active"])
        self.assertEqual(result["afterState"]["payload"]["report_source_state"], "active")
        self.assertEqual(result["afterState"]["selectionSize"], 0)
        self.assertFalse(result["afterState"]["sourceAActive"])
        self.assertEqual(result["selectedArchived"]["label"], "Activate selected")
        self.assertEqual(result["selectedArchived"]["action"], "active")
        self.assertEqual(
            result["afterDelete"]["confirmMessages"],
            ["Delete selected sources from peval-py state?"],
        )
        self.assertEqual(result["afterDelete"]["deletePath"], "/api/sources/source-b/delete")
        self.assertEqual(result["afterDelete"]["remainingKeys"], ["source-a"])
        self.assertEqual(result["afterDelete"]["selectionSize"], 0)

    @unittest.skip("superseded by catalog generation detail invalidation coverage")
    def test_serve_source_state_auto_switches_when_current_mode_becomes_empty(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        sources = [
            {"source_key": "source-a", "active": True, "artifact_dir": "runs/a", "last_status": "ok", "trial_key": "trial:active-a"},
            {"source_key": "source-d", "active": False, "artifact_dir": "runs/d", "last_status": "ok", "trial_key": "trial:archived-d"},
        ]
        active_single = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                {"trajectory_id": "trial:active-a", "session_id": "active-a", "steps": [], "final_metrics": {"extra": {"total_turns": 1}}},
            ],
            "trajectory_meta": [
                {"trial_key": "trial:active-a", "status": "passed", "duration_ms": 1000, "steps": [], "warnings": []},
            ],
            "annotations": {"notes": []},
        }
        archived_single = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                {"trajectory_id": "trial:archived-d", "session_id": "archived-d", "steps": [], "final_metrics": {"extra": {"total_turns": 2}}},
            ],
            "trajectory_meta": [
                {"trial_key": "trial:archived-d", "status": "passed", "duration_ms": 2000, "steps": [], "warnings": []},
            ],
            "annotations": {"notes": [{"trial_key": "trial:archived-d", "source": "cell", "label": "notes.md", "markdown": "Archived note."}]},
        }
        active_after_activate = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                active_single["trajectory"][0],
                archived_single["trajectory"][0],
            ],
            "trajectory_meta": [
                active_single["trajectory_meta"][0],
                archived_single["trajectory_meta"][0],
            ],
            "annotations": {"notes": archived_single["annotations"]["notes"]},
        }
        archived_after_archive = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [
                active_single["trajectory"][0],
                archived_single["trajectory"][0],
            ],
            "trajectory_meta": [
                active_single["trajectory_meta"][0],
                archived_single["trajectory_meta"][0],
            ],
            "annotations": {"notes": archived_single["annotations"]["notes"]},
        }
        empty_active = {"schema_version": 19, "includes": ["core"], "trajectory": [], "trajectory_meta": [], "annotations": {"notes": []}}
        empty_archived = {"schema_version": 19, "includes": ["core"], "trajectory": [], "trajectory_meta": [], "annotations": {"notes": []}}
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const scenarios = __SCENARIOS__;

function makeNodeFactory(nodes) {
  return function makeNode(id) {
    const node = {
      id,
      textContent: "",
      hidden: false,
      dataset: {},
      classList: { add() {}, remove() {}, toggle() {} },
      addEventListener() {},
      querySelector() { return null; },
      querySelectorAll() { return []; },
      closest() { return null; },
      _innerHTML: "",
    };
    Object.defineProperty(node, "innerHTML", {
      get() { return this._innerHTML; },
      set(value) {
        this._innerHTML = String(value || "");
        for (const match of this._innerHTML.matchAll(/id="([^"]+)"/g)) {
          if (!nodes[match[1]]) nodes[match[1]] = makeNode(match[1]);
        }
      },
    });
    return node;
  };
}

function response(payload) {
  return { ok: true, statusText: "OK", text: async () => JSON.stringify(payload) };
}

function createContext(scenario) {
  const nodes = {};
  const makeNode = makeNodeFactory(nodes);
  [
    "peval-py-i18n",
    "peval-py-token-estimates",
    "peval-py-render-options",
    "report-notes",
    "comparison",
    "trace",
    "step-drawer",
  ].forEach(id => nodes[id] = makeNode(id));
  nodes["peval-py-i18n"].textContent = "{}";
  nodes["peval-py-token-estimates"].textContent = "{}";
  nodes["peval-py-render-options"].textContent = JSON.stringify({ mode: "serve", sources: scenario.sources });
  const fetchCalls = [];
  const context = {
    nodes,
    scenario,
    fetchCalls,
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
    requestAnimationFrame(callback) { callback(); },
    fetch: async (path, options = {}) => {
      const body = options.body ? JSON.parse(options.body) : null;
      fetchCalls.push({ path, body });
      if (String(path) === "/api/sources/state") return response(scenario.statePayload);
      if (String(path).includes(`source_state=${scenario.targetMode}`)) return response(scenario.targetReport);
      throw new Error(`unexpected fetch ${path}`);
    },
  };
  vm.createContext(context);
  vm.runInContext(asset, context);
  return context;
}

async function runScenario(scenario) {
  const context = createContext(scenario);
  const result = await vm.runInContext(`(async () => {
    applyServeMutationPayload({
      sources: scenario.sources,
      report: scenario.initialReport,
      report_source_key: scenario.initialSourceKey,
      report_source_state: scenario.initialMode,
    });
    const nullEditorResult = (() => {
      try {
        return renderNotesEditor(undefined);
      } catch (error) {
        return error.message;
      }
    })();
    state.rowSelection.add(scenario.selectedTrial);
    state.notesEditor = { trialKey: scenario.selectedTrial, markdown: "draft", error: "", saving: false };
    renderComparisonPanels({ trace: false });
    await mutateVisibleServeSourceState();
    return JSON.stringify({
      nullEditorResult,
      mode: state.serveSourceMode,
      reportRows: reportRows().length,
      selectedSourceKey: state.selectedSourceKey,
      selectedTrial: state.selectedTrial,
      rowSelectionSize: state.rowSelection.size,
      hasLeaderboard: nodes.leaderboard.innerHTML.includes("Leaderboard"),
      hasOverview: nodes["trajectory-overview"].innerHTML.includes("Trajectory Overview"),
      comparisonLength: nodes.comparison.innerHTML.length,
      traceLength: nodes.trace.innerHTML.length,
      targetFetches: fetchCalls.filter(call => String(call.path).includes("source_state=" + scenario.targetMode)).length,
      statePayload: fetchCalls.find(call => call.path === "/api/sources/state").body,
    });
  })()`, context);
  return JSON.parse(result);
}

Promise.all(scenarios.map(runScenario))
  .then(result => console.log(JSON.stringify(result)))
  .catch(error => { console.error(error && error.stack || error); process.exit(1); });
""".replace("__ASSET__", json.dumps(asset)).replace("__SCENARIOS__", json.dumps([
            {
                "name": "activate-last-archived",
                "sources": sources,
                "initialMode": "archived",
                "targetMode": "active",
                "initialSourceKey": "source-d",
                "selectedTrial": "trial:archived-d",
                "initialReport": archived_single,
                "targetReport": active_after_activate,
                "statePayload": {
                    "sources": [sources[0], {**sources[1], "active": True}],
                    "report": empty_archived,
                    "report_source_key": None,
                    "report_source_state": "archived",
                },
            },
            {
                "name": "archive-last-active",
                "sources": sources,
                "initialMode": "active",
                "targetMode": "archived",
                "initialSourceKey": "source-a",
                "selectedTrial": "trial:active-a",
                "initialReport": active_single,
                "targetReport": archived_after_archive,
                "statePayload": {
                    "sources": [{**sources[0], "active": False}, sources[1]],
                    "report": empty_active,
                    "report_source_key": None,
                    "report_source_state": "active",
                },
            },
        ]))
        node = subprocess.run(
            ["node"],
            input=script,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(node.returncode, 0, node.stderr)
        activate, archive = json.loads(node.stdout)

        self.assertEqual(activate["nullEditorResult"], "")
        self.assertEqual(activate["mode"], "active")
        self.assertEqual(activate["reportRows"], 2)
        self.assertEqual(activate["selectedSourceKey"], "source-d")
        self.assertEqual(activate["selectedTrial"], "trial:archived-d")
        self.assertEqual(activate["rowSelectionSize"], 0)
        self.assertTrue(activate["hasLeaderboard"])
        self.assertTrue(activate["hasOverview"])
        self.assertGreater(activate["comparisonLength"], 0)
        self.assertGreater(activate["traceLength"], 0)
        self.assertEqual(activate["targetFetches"], 1)
        self.assertEqual(activate["statePayload"]["source_keys"], ["source-d"])
        self.assertTrue(activate["statePayload"]["active"])
        self.assertEqual(activate["statePayload"]["report_source_state"], "archived")

        self.assertEqual(archive["nullEditorResult"], "")
        self.assertEqual(archive["mode"], "archived")
        self.assertEqual(archive["reportRows"], 2)
        self.assertEqual(archive["selectedSourceKey"], "source-a")
        self.assertEqual(archive["selectedTrial"], "trial:active-a")
        self.assertEqual(archive["rowSelectionSize"], 0)
        self.assertTrue(archive["hasLeaderboard"])
        self.assertTrue(archive["hasOverview"])
        self.assertGreater(archive["comparisonLength"], 0)
        self.assertGreater(archive["traceLength"], 0)
        self.assertEqual(archive["targetFetches"], 1)
        self.assertEqual(archive["statePayload"]["source_keys"], ["source-a"])
        self.assertFalse(archive["statePayload"]["active"])
        self.assertEqual(archive["statePayload"]["report_source_state"], "active")

    def test_comparison_panel_rerenders_preserve_scroll_positions(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
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

    def test_comparison_panel_scroll_progress_syncs_in_both_directions(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
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


    def test_workspace_report_cells_render_zero_one_many_and_isolate_clicks(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const listeners = { control: [], preview: [] };
const probe = { opened: null, menuClosed: false };
const control = {
  addEventListener(type, handler) { if (type === "click") listeners.control.push(handler); }
};
const details = { removeAttribute(name) { if (name === "open") probe.menuClosed = true; } };
const preview = {
  dataset: { reportPreview: "20260710-130000-000000" },
  addEventListener(type, handler) { if (type === "click") listeners.preview.push(handler); },
  closest(selector) { return selector === "details" ? details : null; }
};
const target = {
  querySelectorAll(selector) {
    if (selector === "[data-workspace-report-control]") return [control];
    if (selector === "[data-report-preview]") return [preview];
    if (selector === "[data-report-attach]") return [];
    return [];
  }
};
const nodes = {
  "peval-py-data": { textContent: "{}" },
  "peval-py-token-estimates": { textContent: "{}" },
  "peval-py-i18n": { textContent: "{}" },
  "peval-py-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [], reports: [] }) }
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
  target, listeners, probe
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
  const event = { preventDefault() { this.prevented = true; }, stopPropagation() { this.stopped = true; } };
  listeners.control.forEach(handler => handler(event));
  listeners.preview.forEach(handler => handler(event));
  return JSON.stringify({ zero, one, many, columnKeys, event, probe, selectedTrial: state.selectedTrial });
})()`, context);
console.log(result);
""".replace("__ASSET__", json.dumps(asset))
        node = subprocess.run(
            ["node"], input=script, text=True, capture_output=True, timeout=10, check=False
        )
        self.assertEqual(node.returncode, 0, node.stderr)
        result = json.loads(node.stdout)

        self.assertIn("&mdash;", result["zero"])
        self.assertIn("one.md", result["one"])
        self.assertIn("2 reports", result["many"])
        self.assertLess(result["many"].index("newer.md"), result["many"].index("older.html"))
        alias_index = result["columnKeys"].index("source_alias")
        self.assertEqual(result["columnKeys"][alias_index + 1], "workspace_reports")
        self.assertTrue(result["event"]["stopped"])
        self.assertTrue(result["event"]["prevented"])
        self.assertEqual(result["probe"]["opened"], "20260710-130000-000000")
        self.assertTrue(result["probe"]["menuClosed"])
        self.assertEqual(result["selectedTrial"], "trial-before")

    def test_workspace_report_attach_cancel_preserves_selection_and_success_opens_reader(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const nodes = {
  "peval-py-data": { textContent: "{}" },
  "peval-py-token-estimates": { textContent: "{}" },
  "peval-py-i18n": { textContent: "{}" },
  "peval-py-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [], reports: [] }) }
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
            ["node"], input=script, text=True, capture_output=True, timeout=10, check=False
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
        self.assertEqual(result["afterSuccess"]["reportIds"], ["20260710-140000-000000"])
        self.assertFalse(result["afterSuccess"]["disabled"])

    @unittest.skip("superseded by shell-first workspace report catalog loading")
    def test_workspace_report_empty_catalog_payload_and_reader_step_mutual_exclusion(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
function classList() {
  return {
    values: new Set(),
    add(name) { this.values.add(name); },
    remove(name) { this.values.delete(name); },
    toggle(name, force) {
      const active = force === undefined ? !this.values.has(name) : Boolean(force);
      if (active) this.values.add(name); else this.values.delete(name);
      return active;
    },
    contains(name) { return this.values.has(name); }
  };
}
const closeButton = { listeners: {}, focusCount: 0, addEventListener(type, handler) { this.listeners[type] = handler; }, focus() { this.focusCount += 1; } };
const reader = {
  hidden: true,
  innerHTML: "",
  querySelectorAll(selector) { return selector === "[data-report-reader-close]" ? [closeButton] : []; },
  querySelector(selector) { return selector === "[data-report-reader-close]" ? closeButton : null; }
};
const nodes = {
  "peval-py-data": { textContent: "{}" },
  "peval-py-token-estimates": { textContent: "{}" },
  "peval-py-i18n": { textContent: "{}" },
  "peval-py-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [], reports: [] }) },
  "workspace-report-reader": reader
};
const bodyClasses = classList();
const context = {
  document: {
    activeElement: null,
    body: { classList: bodyClasses },
    addEventListener() {},
    getElementById(id) { return nodes[id] || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; }
  },
  window: { addEventListener() {} },
  requestAnimationFrame(callback) { callback(); },
  console, JSON, Number, String, Object, Math, Date, Set, Array, RegExp,
  reader, bodyClasses, closeButton
};
vm.createContext(context);
vm.runInContext(asset, context);
const result = vm.runInContext(`(() => {
  const report = { report_id: "20260710-150000-000000", filename: "reader.html", format: "html", source_keys: ["cell-a"] };
  state.workspaceReports = [report];
  let comparisonRenders = 0;
  let sourcesAtCatalog = null;
  renderComparisonPanels = () => { comparisonRenders += 1; };
  renderServeSources = () => {};
  pruneSourceSelection = () => {};
  setServeStatus = () => {};
  const applyCatalog = applyWorkspaceReportCatalog;
  applyWorkspaceReportCatalog = reports => {
    sourcesAtCatalog = state.serveSources.map(source => source.source_key);
    applyCatalog(reports);
  };
  applyServeMutationPayload({
    reports: [],
    sources: [{ source_key: "cell-ready", artifact_dir: "runs/default/a/s/c", last_status: "ok" }]
  });
  const emptyPayload = { reportCount: workspaceReports().length, comparisonRenders, sourcesAtCatalog };
  state.workspaceReports = [report];
  renderStepDrawer = () => setStepDrawerOpen(Boolean(state.selectedStep));
  state.selectedStep = { trialKey: "trial-a", stepId: "1" };
  setStepDrawerOpen(true);
  openWorkspaceReportReader(report.report_id);
  const readerOpen = {
    readerHidden: reader.hidden,
    reportClass: bodyClasses.contains("report-reader-open"),
    stepClass: bodyClasses.contains("step-drawer-open"),
    selectedStep: state.selectedStep,
    sandbox: reader.innerHTML.includes('sandbox="allow-scripts"'),
    sameOrigin: reader.innerHTML.includes("allow-same-origin"),
    openInNewTab: reader.innerHTML.includes('data-report-reader-open-tab')
      && reader.innerHTML.includes('target="_blank"')
      && reader.innerHTML.includes('rel="noopener"')
      && reader.innerHTML.includes("/api/reports/" + report.report_id + "/open"),
    resizable: reader.innerHTML.includes('data-report-reader-resize')
      && reader.innerHTML.includes('aria-orientation="vertical"')
  };
  state.selectedStep = { trialKey: "trial-a", stepId: "2" };
  setStepDrawerOpen(true);
  const stepOpen = {
    readerHidden: reader.hidden,
    reportClass: bodyClasses.contains("report-reader-open"),
    stepClass: bodyClasses.contains("step-drawer-open"),
    openReportId: state.reportReader.openId
  };
  return JSON.stringify({ emptyPayload, readerOpen, stepOpen, closeFocusCount: closeButton.focusCount });
})()`, context);
console.log(result);
""".replace("__ASSET__", json.dumps(asset))
        node = subprocess.run(
            ["node"], input=script, text=True, capture_output=True, timeout=10, check=False
        )
        self.assertEqual(node.returncode, 0, node.stderr)
        result = json.loads(node.stdout)

        self.assertEqual(
            result["emptyPayload"],
            {
                "reportCount": 0,
                "comparisonRenders": 1,
                "sourcesAtCatalog": ["cell-ready"],
            },
        )
        self.assertFalse(result["readerOpen"]["readerHidden"])
        self.assertTrue(result["readerOpen"]["reportClass"])
        self.assertFalse(result["readerOpen"]["stepClass"])
        self.assertIsNone(result["readerOpen"]["selectedStep"])
        self.assertTrue(result["readerOpen"]["sandbox"])
        self.assertFalse(result["readerOpen"]["sameOrigin"])
        self.assertTrue(result["readerOpen"]["openInNewTab"])
        self.assertTrue(result["readerOpen"]["resizable"])
        self.assertTrue(result["stepOpen"]["readerHidden"])
        self.assertFalse(result["stepOpen"]["reportClass"])
        self.assertTrue(result["stepOpen"]["stepClass"])
        self.assertIsNone(result["stepOpen"]["openReportId"])
        self.assertGreaterEqual(result["closeFocusCount"], 1)

    def test_workspace_report_reader_resizes_with_pointer_and_keyboard(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        asset = asset.rsplit("\nrender(data());", 1)[0]
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
  "peval-py-data": { textContent: "{}" },
  "peval-py-token-estimates": { textContent: "{}" },
  "peval-py-i18n": { textContent: "{}" },
  "peval-py-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [], reports: [] }) },
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
            ["node"], input=script, text=True, capture_output=True, timeout=10, check=False
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
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const bindingTarget = { innerHTML: "" };
const manager = { hidden: true };
const nodes = {
  "peval-py-data": { textContent: "{}" },
  "peval-py-token-estimates": { textContent: "{}" },
  "peval-py-i18n": { textContent: "{}" },
  "peval-py-render-options": { textContent: JSON.stringify({ mode: "serve", sources: [], reports: [] }) }
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
            ["node"], input=script, text=True, capture_output=True, timeout=10, check=False
        )
        self.assertEqual(node.returncode, 0, node.stderr)
        result = json.loads(node.stdout)

        self.assertEqual(result["initial"]["readable"], ["cell-active", "cell-archived", "cell-empty"])
        self.assertTrue(result["initial"]["saveDisabled"])
        self.assertEqual(result["initial"]["tagChips"], 3)
        self.assertTrue(result["initial"]["emptyTags"])
        self.assertEqual(result["searchMatches"], ["cell-archived"])
        self.assertTrue(result["changed"]["dirty"])
        self.assertFalse(result["changed"]["saveDisabled"])
        self.assertEqual(result["afterSave"]["sourceKeys"], ["cell-active", "cell-archived"])
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

    def test_html_submenu_outside_click_closer_only_targets_menus(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is required to execute report.js interaction helpers")
        asset = load_asset_text("report.js")
        self.assertIn("\nrender(data());", asset)
        asset = asset.rsplit("\nrender(data());", 1)[0]
        script = """
const vm = require("vm");
const asset = __ASSET__;
const exportMenu = { id: "export", open: true };
const filterMenu = { id: "filter", open: true };
const reportMenu = { id: "report", open: true };
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
    if (selector !== ".export-menu[open],.filter-control[open],.report-cell-menu[open]") {
      throw new Error(`unexpected selector: ${selector}`);
    }
    return [exportMenu, filterMenu, reportMenu].filter(details => details.open);
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
  reportMenu,
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
  reportMenu.open = true;
  clickHandler({ target: { closest: selector => selector === SUBMENU_DETAILS_SELECTOR ? exportMenu : null } });
  const insideExport = { exportOpen: exportMenu.open, filterOpen: filterMenu.open, reportOpen: reportMenu.open, timelineOpen: timelineSection.open };
  filterMenu.open = true;
  exportMenu.open = true;
  reportMenu.open = true;
  clickHandler({ target: { closest: () => null } });
  const outside = { exportOpen: exportMenu.open, filterOpen: filterMenu.open, reportOpen: reportMenu.open, timelineOpen: timelineSection.open };
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
            {"exportOpen": True, "filterOpen": False, "reportOpen": False, "timelineOpen": True},
        )
        self.assertEqual(
            result["outside"],
            {"exportOpen": False, "filterOpen": False, "reportOpen": False, "timelineOpen": True},
        )
        self.assertTrue(result["clickHandlerCapture"])
