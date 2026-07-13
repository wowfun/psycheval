from __future__ import annotations

import http.client
import os
import threading
import time

from peval_py_test_support import *

from cli_inputs_support import write_trial_cell_artifacts
from peval_py.inputs import parse_adapter_assignments
from peval_py.serve import (
    DEFAULT_PORT_END,
    DEFAULT_PORT_START,
    ECHARTS_ASSET_PATH,
    HttpError,
    LocalHTTPServer,
    ServeRuntime,
    bind_server,
    cached_echarts_asset,
    echarts_cache_path,
    load_serve_inputs,
    make_handler,
    source_path_values,
    workspace_relative_path,
)
from peval_py.state import (
    REFRESH_LOG_LIMIT,
    UPLOAD_LIMIT_BYTES,
    discover_complete_trial_cell_dirs,
    loaded_trial_cell_import_session,
    open_workspace_state,
    resolve_workspace_root,
)




def peval_py_workspace(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "peval-py.toml").write_text("", encoding="utf-8")
    return root


def write_cached_analysis(
    root: Path,
    *,
    agent_id: str,
    session_id: str,
    summary: str,
    eval_slug: str = "default",
    cell_key: str = "session_t001",
) -> Path:
    path = root / "runs" / eval_slug / agent_id / session_id / cell_key / "analysis.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"summary": summary, "checks": {}}),
        encoding="utf-8",
    )
    return path


def write_cached_markdown(
    root: Path,
    *,
    agent_id: str,
    session_id: str,
    markdown: str,
    eval_slug: str = "default",
    cell_key: str = "session_t001",
) -> Path:
    path = root / "runs" / eval_slug / agent_id / session_id / cell_key / "analysis.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def write_cached_note(
    root: Path,
    *,
    agent_id: str,
    session_id: str,
    markdown: str,
    eval_slug: str = "default",
    cell_key: str = "session_t001",
) -> Path:
    path = root / "runs" / eval_slug / agent_id / session_id / cell_key / "notes.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def serve_args(**overrides):
    values = {
        "path": None,
        "db": None,
        "input_table": None,
        "session_id": None,
        "adapter": None,
        "note": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def sample_report(config: ToolConfig) -> dict:
    result = convert_records(
        read_jsonl(str(FIXTURES / "common_session.jsonl")),
        config,
    )
    return build_report(result, config, "common_session.jsonl")


def request_json(
    port: int,
    method: str,
    path: str,
    payload: dict,
    *,
    origin: str,
) -> tuple[int, dict[str, str], dict]:
    body = json.dumps(payload)
    headers = {
        "Content-Type": "application/json",
        "Origin": origin,
    }
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read().decode("utf-8")
    result = json.loads(raw)
    response_headers = {key.lower(): value for key, value in response.getheaders()}
    conn.close()
    if response.status in {200, 202} and isinstance(result, dict) and (
        result.get("operation_id") or result.get("generation")
    ):
        original_status = response.status
        if result.get("operation_id"):
            result = wait_for_catalog_operation(port, str(result["operation_id"]))
        result = hydrate_legacy_catalog_response(port, result, payload)
        if original_status == 202:
            return 200, response_headers, result
    return response.status, response_headers, result


def raw_get_json(port: int, path: str) -> tuple[int, dict]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    response = conn.getresponse()
    raw = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(raw)


def wait_for_catalog_operation(port: int, operation_id: str) -> dict:
    for _attempt in range(500):
        status, operation = raw_get_json(port, f"/api/operations/{operation_id}")
        if status != 200:
            return operation
        if operation.get("state") not in {"queued", "running"}:
            return operation
        time.sleep(0.01)
    raise AssertionError(f"catalog operation did not finish: {operation_id}")


def hydrate_legacy_catalog_response(
    port: int,
    result: dict,
    request_payload: dict,
) -> dict:
    sources: list[dict] = []
    page_number = 1
    while True:
        status, page = raw_get_json(
            port,
            f"/api/catalog?state=all&surface=sources&page={page_number}&page_size=100",
        )
        if status != 200:
            break
        sources.extend(page.get("items") or [])
        if len(sources) >= int(page.get("total") or 0):
            break
        page_number += 1
    hydrated = {**result, "sources": sources, "loading": False}
    report_state = str(request_payload.get("report_source_state") or "active")
    report_sources = [
        source
        for source in sources
        if source.get("readable") is not False
        and (
            report_state == "all"
            or (report_state == "archived" and source.get("active") is False)
            or (report_state == "active" and source.get("active") is not False)
        )
    ]
    hydrated["report"] = legacy_catalog_report(port, report_sources)
    hydrated["report_source_key"] = report_sources[0]["source_key"] if report_sources else None
    hydrated["report_source_state"] = report_state
    status, reports = raw_get_json(port, "/api/reports")
    hydrated["reports"] = reports.get("reports", []) if status == 200 else []
    if result.get("operation_id") and result.get("operation_type") == "source-import":
        entries: list[dict] = []
        for item in sorted(
            [*(result.get("successes") or []), *(result.get("failures") or [])],
            key=lambda entry: int(entry.get("index") or 0),
        ):
            source = item.get("item") if isinstance(item.get("item"), dict) else {}
            entry = {
                "path": item.get("path") or source.get("path"),
                "status": item.get("status"),
            }
            if item.get("source_keys") is not None:
                entry["source_keys"] = item.get("source_keys")
            if item.get("error"):
                entry["error"] = item["error"]
            entries.append(entry)
        hydrated["import_results"] = entries
    elif isinstance(result.get("result"), dict):
        if result["result"].get("import_results") is not None:
            hydrated["import_results"] = result["result"]["import_results"]
    return hydrated


def legacy_catalog_report(port: int, sources: list[dict]) -> dict:
    combined = {
        "schema_version": 19,
        "includes": ["core"],
        "trajectory": [],
        "trajectory_meta": [],
        "annotations": {"notes": [], "analysis": [], "report_notes": []},
    }
    for source in sources:
        status, envelope = raw_get_json(
            port,
            f"/api/report?source_key={source['source_key']}",
        )
        if status != 200:
            continue
        report = envelope.get("report") or {}
        combined["trajectory"].extend(report.get("trajectory") or [])
        combined["trajectory_meta"].extend(report.get("trajectory_meta") or [])
        annotations = report.get("annotations") or {}
        for key in ("notes", "analysis", "report_notes"):
            combined["annotations"][key].extend(annotations.get(key) or [])
    return combined


def request_bytes(port: int, path: str) -> tuple[int, dict[str, str], bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    response = conn.getresponse()
    body = response.read()
    response_headers = {key.lower(): value for key, value in response.getheaders()}
    conn.close()
    return response.status, response_headers, body


def request_text(port: int, path: str) -> tuple[int, dict[str, str], str]:
    status, headers, body = request_bytes(port, path)
    return status, headers, body.decode("utf-8")


def report_js_comparison_state(
    report: dict,
    *,
    sources: list[dict] | None = None,
    mode: str = "serve",
) -> dict:
    if not shutil.which("node"):
        raise unittest.SkipTest("node is required to execute report.js")
    asset = load_asset_text("report.js")
    script = """
const vm = require("vm");
const asset = __ASSET__;
const report = __REPORT__;
const renderOptions = __RENDER_OPTIONS__;
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
nodes["peval-py-data"].textContent = JSON.stringify(report);
nodes["peval-py-i18n"].textContent = "{}";
nodes["peval-py-token-estimates"].textContent = "{}";
nodes["peval-py-render-options"].textContent = JSON.stringify(renderOptions);
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
  requestAnimationFrame(callback) { callback(); },
};
vm.createContext(context);
vm.runInContext(asset, context);
console.log(JSON.stringify({
  reportRows: vm.runInContext("reportRows().length", context),
  selectedTrial: vm.runInContext("selectedKey()", context),
  selectedSourceKey: vm.runInContext("state.selectedSourceKey", context),
  comparisonLength: nodes.comparison.innerHTML.length,
  hasLeaderboard: Boolean(nodes.leaderboard?.innerHTML.includes("Leaderboard")),
  hasSummary: Boolean(nodes["leaderboard-summary"]?.innerHTML.includes("Leaderboard Summary")),
  hasOverview: Boolean(nodes["trajectory-overview"]?.innerHTML.includes("Trajectory Overview")),
  traceLength: nodes.trace.innerHTML.length,
}));
""".replace("__ASSET__", json.dumps(asset)).replace(
        "__REPORT__",
        json.dumps(report),
    ).replace(
        "__RENDER_OPTIONS__",
        json.dumps({"mode": mode, "sources": sources or []}),
    )
    result = subprocess.run(
        ["node"],
        input=script,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


if __name__ == "__main__":
    unittest.main()
