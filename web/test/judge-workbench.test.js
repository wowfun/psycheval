import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const dom = installBrowserDom('<script id="peval-i18n" type="application/json">{}</script>');
const { createJudgeWorkbench } = await import("../../src/psycheval/assets/web/modules/judge-workbench.js");
const { interpretVerificationFile, renderVerificationDocument } = await import("../../src/psycheval/assets/web/modules/verification-formats.js");
test.after(() => dom.cleanup());
const tick = () => new Promise(resolve => setTimeout(resolve, 0));
const click = text => [...document.querySelectorAll('.judge-overlay:not([hidden]) .judge-dialog button')].find(node => node.textContent === text).click();
const config = { version: 1, artifacts: [], llm_judge: { rubrics: [{ id: "quality", question: "Original", artifact_refs: [], pass_criteria: ["line one\nline two"], fail_criteria: [], scope_limits: [] }] } };

test("actual prompt is a standalone read and source changes discard stale responses", async () => {
  const calls = []; let resolve;
  const workbench = createJudgeWorkbench({ request: url => { calls.push(url); return new Promise(done => { resolve = done; }); } });
  workbench.setSource("first"); const pending = workbench.prompt("quality");
  workbench.setSource("second"); resolve({ status: "recorded", messages: [{ role: "user", content: "stale" }] });
  await pending;
  assert.deepEqual(calls, ["/api/judge/first/prompt/quality"]);
  assert.equal(document.querySelector('.judge-overlay').hidden, true);
  assert.ok(!document.querySelector('.judge-body').textContent.includes("stale"));
});

test("legacy prompt snapshots omit unknown settings", async () => {
  const workbench = createJudgeWorkbench({ request: async () => ({ status: "recorded", messages: [{ role: "user", content: "Retained prompt" }], attempts: [], settings: null }) });
  workbench.setSource("legacy"); await workbench.prompt("quality");
  const body = document.querySelector('.judge-overlay:not([hidden]) .judge-body');
  assert.ok(!body.textContent.includes("null"));
  assert.ok(![...body.querySelectorAll('summary')].some(node => node.textContent === "Recorded settings"));
  click("Close");
});

const original = { supported: true, config, context: { instruction: "Instruction" } };
const configuration = { judge: { default_profile: "fixture", profiles: { fixture: { model: "test" } } } };
const result = reason => ({ state: "complete", profile: "fixture", selected_ids: ["quality"], baseline: [{ id: "quality", status: "fail", reason: "Original reason" }], checks: [{ id: "quality", passed: true, reason }], errors: {}, diagnostics: { "rubric-0001.json": { id: "quality", messages: [{ role: "user", content: "Actual request" }] } } });
const question = () => document.querySelector('.judge-overlay:not([hidden]) fieldset textarea');
const latest = () => document.querySelector('.judge-overlay:not([hidden]) .judge-latest');

test("editing invalidates preview and run submits the draft with an optional fingerprint", async () => {
  const calls = [], previews = [];
  const workbench = createJudgeWorkbench({ request: async (url, options) => {
    calls.push({ url, options });
    if (url === "/api/config") return configuration;
    if (url.endsWith("/preview")) { previews.push(options.body); return { fingerprint: `fingerprint-${previews.length}`, messages: { quality: [{ role: "user", content: options.body.judge_config }] } }; }
    if (url.endsWith("/run")) return result("Latest reason");
    return original;
  } });
  workbench.setSource("trial"); await workbench.draft(["quality"]);
  click("Preview prompt"); await tick();
  assert.deepEqual(JSON.parse(previews[0].judge_config).llm_judge.rubrics[0].pass_criteria, ["line one\nline two"]);
  question().value = "Revised"; question().dispatchEvent(new window.Event("input"));
  assert.equal(document.querySelector('.judge-preview').textContent, "");
  click("Preview prompt"); await tick();
  click("Close"); await workbench.draft();
  assert.match(document.querySelector('.judge-overlay:not([hidden]) .judge-preview').textContent, /Revised/);
  click("Run selected rubrics"); await tick();
  assert.equal(previews.length, 2);
  assert.equal(calls.find(item => item.url.endsWith("/run")).options.body.expected_fingerprint, "fingerprint-2");
  assert.equal(JSON.parse(calls.find(item => item.url.endsWith("/run")).options.body.judge_config).llm_judge.rubrics[0].question, "Revised");
  assert.match(latest().querySelector('[data-judge-result="baseline"]').textContent, /Baseline resultFailedOriginal reason/);
  assert.match(latest().querySelector('[data-judge-result="current"]').textContent, /Current resultPassedLatest reason/);
  assert.match(latest().textContent, /Actual request/);
  workbench.setSource("another"); workbench.setSource("trial"); await workbench.draft();
  assert.equal(question().value, "Revised");
  assert.match(latest().textContent, /Latest reason/);
  click("Close");
});

test("result columns pair verdicts and literal reasons by rubric, including missing and unassessed results", async () => {
  const reason = "First line\n<script>literal evidence</script>\n" + "长理由WithoutSpaces".repeat(40);
  const run = {
    ...result(reason), state: "incomplete", selected_ids: ["quality", "new", "unassessed", "timeout"], reason: "Deadline reached",
    baseline: [{ id: "unassessed", status: "pass", reason: "Retained success" }, { id: "quality", status: "fail", reason: "Retained failure\nDetails" }],
    checks: [{ id: "new", passed: false, reason: "New failure" }, { id: "quality", passed: true, reason }], errors: { unassessed: "Provider unavailable" },
  };
  const workbench = createJudgeWorkbench({ request: async url => url === "/api/config" ? configuration : url.endsWith("/run") ? run : original });
  workbench.setSource("comparison"); await workbench.draft(["quality"]);
  click("Run selected rubrics"); await tick();
  const rows = [...latest().querySelectorAll(".judge-result")];
  assert.deepEqual(rows.map(row => row.querySelector(".judge-result-title").textContent), run.selected_ids);
  const columns = rows.map(row => [...row.querySelectorAll(".judge-result-column")]);
  for (const pair of columns) assert.deepEqual(pair.map(node => node.dataset.judgeResult), ["baseline", "current"]);
  assert.equal(columns[0][0].querySelector("pre").textContent, "Retained failure\nDetails");
  assert.equal(columns[0][1].querySelector("pre").textContent, reason);
  assert.equal(columns[0][1].querySelector("script"), null);
  assert.equal(columns[0][0].querySelector(".judge-result-verdict").dataset.status, "fail");
  assert.equal(columns[0][1].querySelector(".judge-result-verdict").dataset.status, "pass");
  assert.match(columns[1][0].textContent, /No baseline/);
  assert.equal(columns[1][0].querySelector("pre").textContent, "—");
  assert.match(columns[1][1].textContent, /FailedNew failure/);
  assert.match(columns[2][0].textContent, /PassedRetained success/);
  assert.match(columns[2][1].textContent, /UnassessedProvider unavailable/);
  assert.match(columns[3][1].textContent, /UnassessedDeadline reached/);
  assert.equal(rows[0].lastElementChild.tagName, "DETAILS");
  click("Close");
});

test("one run survives closing and navigation; late responses stay with their Trial and replace the last attempt", async () => {
  const runs = [];
  const request = async (url, options) => {
    if (url === "/api/config") return configuration;
    if (url.endsWith("/run")) return new Promise(resolve => runs.push({ url, options, resolve }));
    return original;
  };
  const workbench = createJudgeWorkbench({ request });
  workbench.setSource("first"); await workbench.draft(["quality"]);
  click("Run selected rubrics"); await tick(); click("Close");
  assert.equal(runs[0].options.signal.aborted, false);
  workbench.setSource(null); workbench.setSource("second"); await workbench.draft(["quality"]);
  assert.match(document.querySelector('.judge-overlay:not([hidden]) .judge-status').textContent, /Another Trial is running/);
  click("Run selected rubrics"); assert.equal(runs.length, 1);
  runs[0].resolve(result("First result")); await tick();
  assert.equal(latest().textContent, "");
  workbench.setSource("first"); await workbench.draft();
  assert.match(latest().textContent, /First result/);
  click("Run selected rubrics"); await tick();
  assert.equal(latest().textContent, "");
  runs[1].resolve(result("Replacement result")); await tick();
  assert.match(latest().textContent, /Replacement result/);
  assert.doesNotMatch(latest().textContent, /First result/);
  click("Close");
  const refreshed = createJudgeWorkbench({ request });
  refreshed.setSource("first"); await refreshed.draft(["quality"]);
  assert.equal(latest().textContent, ""); click("Close");
});

test("explicit cancel aborts the request and never accepts a late partial response", async () => {
  let finish, signal;
  const workbench = createJudgeWorkbench({ request: async (url, options) => {
    if (url === "/api/config") return configuration;
    if (url.endsWith("/run")) { signal = options.signal; return new Promise(resolve => { finish = resolve; }); }
    return original;
  } });
  workbench.setSource("trial"); await workbench.draft(["quality"]);
  click("Run selected rubrics"); await tick(); click("Cancel");
  assert.equal(signal.aborted, true);
  finish(result("Must be discarded")); await tick();
  assert.equal(latest().textContent, "");
  assert.match(document.querySelector('.judge-overlay:not([hidden]) .judge-status').textContent, /cancelled/);
  click("Close"); await workbench.draft();
  assert.match(document.querySelector('.judge-overlay:not([hidden]) .judge-status').textContent, /cancelled/);
  click("Close");
});

test("fingerprint conflicts require a fresh preview and do not retry", async () => {
  let runs = 0, previews = 0;
  const workbench = createJudgeWorkbench({ request: async (url) => {
    if (url === "/api/config") return configuration;
    if (url.endsWith("/preview")) { previews++; return { fingerprint: "old", messages: {} }; }
    if (url.endsWith("/run")) { runs++; throw Object.assign(new Error("Inputs changed; preview again"), { status: 409 }); }
    return original;
  } });
  workbench.setSource("trial"); await workbench.draft(["quality"]);
  click("Preview prompt"); await tick(); click("Run selected rubrics"); await tick();
  assert.match(document.querySelector('.judge-overlay:not([hidden]) .judge-status').textContent, /preview again/);
  assert.equal(document.querySelector('.judge-overlay:not([hidden]) .judge-preview').textContent, "");
  assert.equal(runs, 1); assert.equal(previews, 1); click("Close");
});

test("rubric actions use metadata IDs and guest views omit execution", () => {
  const model = interpretVerificationFile("score.json", JSON.stringify({ verdicts: [{ item_id: "prefix:quality", judge_name: "llm_judge", status: "pass", metadata: { rubric: { id: "quality" } } }] }));
  const calls = [];
  const view = renderVerificationDocument(model, null, { onPrompt: id => calls.push(id) });
  [...view.querySelectorAll('button')].find(node => node.textContent === "Actual prompt").click();
  assert.deepEqual(calls, ["quality"]);
  assert.ok(!view.textContent.includes("Try rubric"));
});

test("rubric selection sits before the heading and survives result filtering", () => {
  const model = interpretVerificationFile("score.json", JSON.stringify({ verdicts: [{ item_id: "llm:quality", judge_name: "llm_judge", status: "pass", metadata: { rubric: { id: "quality" } } }] }));
  const calls = [];
  const view = renderVerificationDocument(model, null, { onPrompt() {}, onTry: ids => calls.push(ids) });
  document.body.append(view);
  const heading = view.querySelector('.verification-verdict summary');
  const checkbox = heading.querySelector('input[type="checkbox"]');
  assert.equal(checkbox.nextSibling.textContent, "llm:quality");
  assert.equal(checkbox.getAttribute('aria-label'), "Select quality");
  assert.equal(view.querySelector('.verification-verdict .judge-actions').querySelector('input'), null);
  assert.equal(view.querySelector('.verification-verdict .judge-actions').textContent, "Actual promptTry rubric");
  checkbox.click();
  const search = view.querySelector('input[type="search"]');
  search.value = "quality"; search.dispatchEvent(new window.Event("input"));
  assert.equal(view.querySelector('summary input').checked, true);
  [...view.querySelectorAll('button')].find(node => node.textContent === "Try selected").click();
  assert.deepEqual(calls, [["quality"]]);
  view.remove();
});
