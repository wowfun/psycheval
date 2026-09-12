import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const dom = installBrowserDom('<script id="peval-i18n" type="application/json">{}</script>');
const { interpretVerificationFile, renderVerificationDocument, renderVerificationSummary } = await import("../../src/psycheval/assets/web/modules/verification-formats.js");
const { createVerificationBrowser } = await import("../../src/psycheval/assets/web/modules/verification-browser.js");
test.after(() => dom.cleanup());
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test("reward formats preserve zero, multiple dimensions, and recorded nested weights", () => {
  assert.deepEqual(interpretVerificationFile("reward.txt", "0").metrics, [["reward", 0]]);
  assert.deepEqual(interpretVerificationFile("reward.json", "0").metrics, [["reward", 0]]);
  assert.deepEqual(interpretVerificationFile("reward.json", '{"a":-2,"b":3}').metrics, [["a", -2], ["b", 3]]);
  const detail = { overall: { kind: "group", score: 0.5, aggregation: "weighted_sum", components: [{ name: "rule", weight: 0.8, detail: {
    kind: "programmatic", score: 0.5, criteria: [{ name: "answer", value: 0.5, weight: 1, reasoning: "partial evidence" }],
  } }] } };
  const model = interpretVerificationFile("reward-details.json", JSON.stringify(detail));
  assert.equal(model.rows.length, 3);
  assert.match(model.rows[1].name, /weight 0.8/);
  assert.match(model.rows[2].reason, /partial evidence/);
  assert.equal(interpretVerificationFile("reward-details.json", '{"x":{"kind":"llm","score":1,"criteria":[null]}}'), null);
});

test("score and judge previews show explicit reasons and formula without inventing missing values", () => {
  const payload = { reward: 0.676, tests_passed: 359, tests_total: 579, verdicts: [{ item_id: "rubric", status: "fail", score: 0, reason: "<script>bad()</script>", evidence_ids: ["workbook"] }],
    metadata: { score_merge: { method: "weighted_sum", rule_weight: 0.8, rule_score: 0.62, llm_weight: 0.2, llm_score: 0.9, overall: 0.676 } } };
  const model = interpretVerificationFile("verifier/score.json", JSON.stringify(payload));
  assert.ok(model.metrics.some(pair => pair[1] === "0.8 × 0.62 + 0.2 × 0.9 = 0.676"));
  assert.equal(model.rows[0].score, 0);
  const calls = [];
  const view = renderVerificationDocument(model, id => calls.push(id));
  assert.equal(view.querySelector("script"), null);
  assert.match(view.textContent, /<script>bad/);
  view.querySelector("details button").click();
  assert.deepEqual(calls, ["workbook"]);
  delete payload.metadata.score_merge.rule_score;
  assert.ok(!interpretVerificationFile("score.json", JSON.stringify(payload)).metrics.some(pair => pair[0] === "Recorded formula"));
  const judge = interpretVerificationFile("llm_judge.json", '{"rubrics":[{"id":"quality","verdict":"fail","score":0}]}');
  assert.equal(judge.rows[0].reason, "");
  for (const content of ["{bad", '{"unknown":123}', '"hello"']) assert.equal(interpretVerificationFile("score.json", content), null);
  assert.equal(interpretVerificationFile("score.json", JSON.stringify(payload), true), null);
});

test("JUnit preserves failure, error and skip separately and paginates filtered cases", () => {
  const cases = Array.from({ length: 55 }, (_, index) => `<testcase classname="suite" name="case-${index}" time="0.1">${index === 52 ? '<failure message="assertion">trace</failure>' : index === 53 ? '<error message="setup"/>' : index === 54 ? '<skipped message="optional"/>' : ""}</testcase>`).join("");
  const model = interpretVerificationFile("results.xml", `<testsuites><testsuite>${cases}</testsuite></testsuites>`);
  assert.deepEqual(model.metrics.map(pair => pair[1]), [52, 1, 1, 1]);
  const view = renderVerificationDocument(model);
  assert.equal(view.querySelectorAll("details").length, 50);
  assert.equal(view.querySelector("details").dataset.status, "fail");
  view.querySelector('.verification-pager button[aria-label="Next"]').click();
  assert.equal(view.querySelectorAll("details").length, 5);
  view.querySelector("select").value = "skipped";
  view.querySelector("select").dispatchEvent(new window.Event("change"));
  assert.equal(view.querySelectorAll("details").length, 1);
  assert.match(view.querySelector("details").textContent, /case-54/);
  assert.equal(interpretVerificationFile("results.xml", '<!DOCTYPE test [<!ENTITY x "secret">]><testsuite/>'), null);
});

function entry(path, id = path) { return { path, id, kind: "file", size: 10, preview_kind: "text", previewable: true, downloadable: true }; }

test("large multidimensional rewards paginate instead of rendering every metric", () => {
  const data = Object.fromEntries(Array.from({ length: 10000 }, (_, i) => [`score-${i}`, i]));
  const model = interpretVerificationFile("reward.json", JSON.stringify(data));
  const view = renderVerificationDocument(model);
  assert.equal(model.rows.length, 10000);
  assert.equal(view.querySelectorAll("details").length, 50);
});

test("empty verification trees are retried without a revision change", async () => {
  let ready = false;
  const browser = createVerificationBrowser({ request: async url => url.endsWith("/file") ? { content: "1" } : { tree: ready ? [entry("verifier/reward.txt", "file")] : [] } });
  browser.setSource("trial");
  await browser.load({ adapter: "harbor", status: "running" });
  ready = true;
  await browser.load({ adapter: "harbor", status: "running" });
  assert.match(browser.element.textContent, /reward.txt/);
});

test("file browser loads lazily, remembers preview state, and resolves retained evidence", async () => {
  const calls = [];
  const files = [entry("verifier/score.json", "score"), entry("verifier/artifact_manifest.json", "manifest"), entry("verifier/artifact_text/report.md", "text"), entry("verifier/raw_artifacts/report.xlsx", "xlsx")];
  const browser = createVerificationBrowser({ request: async path => {
    calls.push(path);
    if (path === "/api/verification-files/trial") return { tree: files };
    if (path.endsWith("/score")) return { content: '{"reward":0,"verdicts":[{"item_id":"check","status":"fail","reason":"Details","evidence_ids":["report"]}]}' };
    if (path.endsWith("/manifest")) return { content: '{"artifacts":[{"id":"report","text_path":"artifact_text/report.md","verifier_raw_path":"raw_artifacts/report.xlsx"}]}' };
    return { content: "Retained report" };
  } });
  browser.setSource("trial"); assert.equal(calls.length, 0);
  await browser.load({ verifier_evidence: { score_source: "reward" } });
  assert.match(browser.element.textContent, /Details/);
  browser.element.querySelector("[data-verification-raw]").click();
  const root = document.createElement("div"); browser.attach(root);
  await browser.load({}); assert.equal(calls.length, 2);
  assert.ok(root.querySelector(".verification-raw"));
  browser.element.querySelector("[data-verification-raw]").click();
  browser.element.querySelector("details button").click(); await tick();
  assert.equal(browser.element.querySelector(".file-markdown").textContent, "Retained report");
  assert.equal(browser.element.querySelector('[href*="download=true"]'), null);
  browser.element.querySelector("[data-verification-raw]").click();
  assert.equal(browser.element.querySelector(".verification-raw").textContent, "Retained report");
});

test("obsolete file and Trial responses cannot overwrite a new selection", async () => {
  const pending = new Map();
  const browser = createVerificationBrowser({ request: path => new Promise(resolve => pending.set(path, resolve)) });
  browser.setSource("old"); const old = browser.load({});
  browser.setSource("new"); const current = browser.load({});
  pending.get("/api/verification-files/new")({ tree: [entry("verifier/reward.txt", "a"), entry("verifier/log.txt", "b")] });
  await tick();
  const last = browser.open(entry("verifier/log.txt", "b"));
  pending.get("/api/verification-files/new/b")({ content: "Newest" }); await last;
  pending.get("/api/verification-files/new/a")({ content: "Wrong file" }); await current;
  pending.get("/api/verification-files/old")({ tree: [] }); await old;
  assert.equal(browser.element.querySelector(".verification-raw").textContent, "Newest");
});

test("the canonical summary separates execution, missing evidence and valid zero", () => {
  for (const [status, evidence, expected] of [
    ["running", "missing", "Not generated yet"], ["completed", "missing", "missing"], ["completed", "malformed", "malformed"],
  ]) assert.match(renderVerificationSummary({ status, score: 0, verifier_evidence: { status: evidence } }), new RegExp(expected));
  const text = renderVerificationSummary({ status: "completed", score: 0, score_message: "Canonical source", verifier_evidence: { score: 1, status: "present", tests: { passed: 2, total: 4 } } });
  assert.match(text, /Run status/);
  assert.match(text, /<dd>0<\/dd>/);
  assert.match(text, /2 \/ 4/);
  assert.doesNotMatch(text, /<dd>1<\/dd>|failed/);
});

test("default file follows canonical score authority instead of a stray score file", async () => {
  for (const [score_message, expected] of [["Harbor verifier reward", "reward"], ["WorkBuddy verifier score.json: reward", "score"]]) {
    const calls = [];
    const browser = createVerificationBrowser({ request: async path => {
      calls.push(path);
      return path.endsWith("/trial") ? { tree: [entry("verifier/score.json", "score"), entry("verifier/reward.json", "reward")] } : { content: '{"reward":0}' };
    } });
    browser.setSource("trial"); await browser.load({ score_message });
    assert.equal(calls.at(-1), `/api/verification-files/trial/${expected}`);
  }
});

test("raw fallback distinguishes malformed and truncated text and keeps binary files as metadata", async () => {
  let payload;
  const browser = createVerificationBrowser({ request: async () => payload });
  browser.setSource("trial");
  payload = { content: "{broken", truncated: false };
  await browser.open(entry("verifier/score.json"));
  assert.equal(browser.element.querySelector(".verification-raw").textContent, "{broken");
  assert.match(browser.element.querySelector(".verification-notice").textContent, /Invalid structured data/);
  payload = { content: '{"reward":0}', truncated: true };
  await browser.open(entry("verifier/score.json"));
  assert.equal(browser.element.querySelector(".verification-metrics"), null);
  assert.match(browser.element.querySelector(".verification-notice").textContent, /truncated/);
  await browser.open({ ...entry("artifacts/report.xlsx"), previewable: false, preview_kind: null });
  assert.equal(browser.element.querySelector('[href*="download=true"]'), null);
  assert.equal(browser.element.querySelector(".verification-raw"), null);
  browser.setSource("binary-only");
  payload = { tree: [{ ...entry("artifacts/only.xlsx"), previewable: false, preview_kind: null }] };
  await browser.load({});
  assert.equal(browser.element.querySelector('[href*="download=true"]'), null);
  assert.doesNotMatch(browser.element.querySelector(".verification-notice").textContent, /No retained/);
});

test("Verification Markdown renders tables safely and leaves truncated Markdown raw", async () => {
  const content = '# Workbook\n\n| Column | Value |\n| --- | --- |\n| **Total** | `12` |\n\n<script>unsafe()</script>';
  let truncated = false;
  const browser = createVerificationBrowser({ request: async () => ({ content, truncated }) });
  browser.setSource("trial");
  await browser.open(entry("verifier/report.MARKDOWN"));
  assert.equal(browser.element.querySelector(".file-markdown h4").textContent, "Workbook");
  assert.equal(browser.element.querySelectorAll(".file-markdown table td").length, 2);
  assert.equal(browser.element.querySelector("script"), null);
  assert.equal(browser.element.querySelector('[href*="download=true"]'), null);
  browser.element.querySelector("[data-verification-raw]").click();
  assert.equal(browser.element.querySelector(".verification-raw").textContent, content);
  browser.element.querySelector("[data-verification-raw]").click();
  assert.ok(browser.element.querySelector(".file-markdown table"));
  truncated = true;
  await browser.open(entry("verifier/long.md"));
  assert.equal(browser.element.querySelector(".file-markdown"), null);
  assert.equal(browser.element.querySelector("[data-verification-raw]"), null);
});
