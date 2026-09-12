import test from "node:test";
import assert from "node:assert/strict";
import { installBrowserDom } from "./support/browser.js";
const dom = installBrowserDom('<script id="peval-i18n" type="application/json">{}</script>');
const { createJobsPage, parseEntries, flattenEntries, summarizeVariants } = await import("../../src/psycheval/assets/web/pages/jobs-page.js");
test.after(() => dom.cleanup());

test("variant summaries retain parameter identities and distinguish zero from unscored", () => {
  const groups = summarizeVariants([
    { variant_id: "low", score: 0 }, { variant_id: "low", score: 1 },
    { variant_id: "high", score: null }, { variant_id: "high", score: "0.7" },
  ]);
  assert.equal(groups.length, 2);
  assert.equal(groups[0].mean, 0.5);
  assert.equal(groups[0].scored, 2);
  assert.equal(groups[1].mean, null);
});

test("Jobs typed settings preserve zero, false, arrays and nested environment references", () => {
  const value = { n: 0, enabled: false, empty: [], kwargs: { temperature: 0, stop: ["a", "b"] }, env: { API_KEY: "${API_KEY}" } };
  assert.deepEqual(parseEntries(flattenEntries(value)), value);
});
test("Jobs settings reject duplicate, conflicting and prototype keys", () => {
  const entry = key => ({ key, type: "number", value: "0" });
  assert.throws(() => parseEntries([entry("a"), entry("a")]), /Duplicate/);
  assert.throws(() => parseEntries([entry("a"), entry("a.b")]), /Conflicting/);
  assert.throws(() => parseEntries([entry("__proto__.bad")]), /Invalid/);
  assert.throws(() => parseEntries([{ key: "n", type: "boolean", value: "1" }]), /boolean/);
});

test("Jobs DOM treats plugin labels, progress and results as literal text", async () => {
  const payload = '\"><svg onload="unsafe()">';
  const root = document.createElement("section"); document.body.append(root);
  const previous = globalThis.fetch;
  const run = { id: "one", harness: payload, state: "completed", submitted_at: payload, trials_completed: payload, trials_total: payload, results: [{ id: "trial", task: payload, state: payload, score: 0 }], request: {} };
  globalThis.fetch = async path => {
    const value = path === "/api/jobs/options" ? { harnesses: [{ id: "fixture", label: payload, defaults: { variants: [{ id: "a", label: payload, agent: payload, model: payload, options: {} }] } }] }
      : path === "/api/jobs/tasks/fixture" ? { datasets: [{ id: "d", label: payload, tasks: [{ id: "t", label: payload }] }] }
        : path === "/api/jobs" ? { items: [run] } : String(path).endsWith("/logs") ? { text: payload } : run;
    return new Response(JSON.stringify(value));
  };
  const controller = createJobsPage({ root, app: /** @type {any} */ ({}) });
  try {
    await controller.activate(new Set(), "");
    root.querySelector("[data-select-run]").click();
    for (let i = 0; i < 20 && root.querySelector("[data-job-detail]").hidden; i++) await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(root.querySelector("[data-job-detail]").hidden, false);
    assert.equal(root.querySelectorAll("svg, img, [onload], [onerror]").length, 0);
    assert.match(root.querySelector(".job-progress").textContent, /svg onload/);
    assert.equal(root.querySelector("[data-variant-agent]").value, payload);
  } finally { controller.destroy(); root.remove(); globalThis.fetch = previous; }
});
