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
        : path === "/api/jobs" ? { items: [run] } : String(path).endsWith("/logs") ? { entries: [{ format: "json", text: payload }], truncated: false } : run;
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
    assert.equal(root.querySelector(".job-log-entry").textContent, payload);
    const log = root.querySelector(".job-log");
    const entry = log.firstElementChild;
    await controller.activate(new Set(), "");
    assert.equal(root.querySelector(".job-log"), log);
    assert.equal(log.firstElementChild, entry);
  } finally { controller.destroy(); root.remove(); globalThis.fetch = previous; }
});

test("Jobs ignores a run-list refresh that finishes after leaving the page", async () => {
  const previous = globalThis.fetch;
  const root = document.createElement("section"); document.body.append(root);
  const run = { id: "one", harness: "fixture", state: "completed", request: {}, results: [] };
  let resolveListing = null, delayListing = false, detailReads = 0;
  globalThis.fetch = async path => {
    let value;
    if (path === "/api/jobs/options") value = { harnesses: [{ id: "fixture" }] };
    else if (path === "/api/jobs/tasks/fixture") value = { datasets: [] };
    else if (path === "/api/jobs") {
      if (delayListing) await new Promise(resolve => { resolveListing = resolve; });
      value = { items: [run] };
    } else if (String(path).endsWith("/logs")) value = { entries: [{ format: "json", text: "null" }], truncated: false };
    else { detailReads++; value = run; }
    return new Response(JSON.stringify(value));
  };
  const controller = createJobsPage({ root, app: /** @type {any} */ ({}) });
  try {
    await controller.activate(new Set(), "");
    root.querySelector("[data-select-run]").click();
    for (let i = 0; i < 20 && !root.querySelector(".job-log-entry"); i++) await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(root.querySelector(".job-log-entry").textContent, "null");
    delayListing = true;
    const pending = controller.activate(new Set(), "");
    window.dispatchEvent(new CustomEvent("peval:workspace-navigate", { detail: { to: "home" } }));
    resolveListing();
    await pending;
    assert.equal(detailReads, 1);
  } finally { controller.destroy(); root.remove(); globalThis.fetch = previous; }
});

test("Jobs restores an available preferred harness and falls back without saving on load", async () => {
  const previous = globalThis.fetch;
  try {
    for (const [preferred, expected] of [["second", "second"], ["missing", "first"], ["unavailable", "first"]]) {
      const root = document.createElement("section"); document.body.append(root);
      const requests = [];
      globalThis.fetch = async (path, options) => {
        requests.push([path, options?.method || "GET"]);
        const value = path === "/api/jobs/options" ? {
          preferred_harness: preferred,
          harnesses: [{ id: "unavailable", available: false }, { id: "first" }, { id: "second" }],
        } : String(path).startsWith("/api/jobs/tasks/") ? { datasets: [] } : { items: [] };
        return new Response(JSON.stringify(value));
      };
      const controller = createJobsPage({ root, app: /** @type {any} */ ({}) });
      try {
        await controller.activate(new Set(), "");
        assert.equal(root.querySelector("[data-job-harness]").value, expected);
        assert.equal(root.querySelector("[data-job-start]").disabled, false);
        assert.deepEqual(requests, [["/api/jobs/options", "GET"], [`/api/jobs/tasks/${expected}`, "GET"], ["/api/jobs", "GET"]]);
      } finally { controller.destroy(); root.remove(); }
    }
  } finally { globalThis.fetch = previous; }
});

async function until(predicate) {
  for (let i = 0; i < 100; i++) {
    if (predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 0));
  }
  assert.ok(predicate(), "Jobs interaction did not settle");
}

test("Jobs refreshes conflicting preference revisions without overwriting the draft or retrying writes", async () => {
  const previous = globalThis.fetch;
  try {
    for (const operation of ["preferred", "defaults"]) {
      const root = document.createElement("section"); document.body.append(root);
      let optionReads = 0;
      const writes = [];
      const options = revision => ({ revision, harnesses: ["first", "second"].map(id => ({ id, defaults: { variants: [{ id: "a", label: "A", agent: "fixture", model: "original", options: {} }] } })) });
      globalThis.fetch = async (path, init) => {
        let value;
        if (path === "/api/jobs/options") value = options(++optionReads === 1 ? "old" : "current");
        else if (String(path).startsWith("/api/jobs/tasks/")) value = { datasets: [] };
        else if (init?.method === "PUT") {
          const payload = JSON.parse(init.body);
          writes.push({ path, payload });
          if (payload.revision !== "current") return new Response(JSON.stringify({ detail: "configuration changed" }), { status: 409 });
          value = options("saved");
        } else value = { items: [] };
        return new Response(JSON.stringify(value));
      };
      const controller = createJobsPage({ root, app: /** @type {any} */ ({}) });
      try {
        await controller.activate(new Set(), "");
        const select = root.querySelector("[data-job-harness]");
        const save = root.querySelector("[data-job-save-defaults]");
        const model = root.querySelector("[data-variant-model]");
        model.value = "user draft";
        model.dispatchEvent(new Event("input", { bubbles: true }));
        if (operation === "preferred") {
          select.value = "second";
          select.dispatchEvent(new Event("change", { bubbles: true }));
        } else save.click();
        await until(() => writes.length > 0 && !select.disabled);
        assert.equal(optionReads, 2);
        assert.equal(writes.length, 1, "a conflict must not silently repeat the write");
        if (operation === "defaults") {
          assert.equal(model.value, "user draft");
          save.click();
        } else {
          select.value = "first";
          select.dispatchEvent(new Event("change", { bubbles: true }));
        }
        await until(() => writes.length === 2 && !select.disabled);
        assert.equal(writes[1].payload.revision, "current");
        if (operation === "defaults") assert.equal(writes[1].payload.defaults.variants[0].model, "user draft");
      } finally { controller.destroy(); root.remove(); }
    }
  } finally { globalThis.fetch = previous; }
});

test("Jobs locks harness selection while loading and recovers after catalog errors", async () => {
  const previous = globalThis.fetch;
  const root = document.createElement("section"); document.body.append(root);
  let release, catalogStarted = false;
  const pending = new Promise(resolve => { release = resolve; });
  globalThis.fetch = async (path, init) => {
    let value;
    if (path === "/api/jobs/options" || init?.method === "PUT") value = { revision: "r", harnesses: [{ id: "first" }, { id: "second" }] };
    else if (path === "/api/jobs/tasks/first") {
      catalogStarted = true;
      await pending;
      value = { datasets: [] };
    } else if (path === "/api/jobs/tasks/second") return new Response(JSON.stringify({ detail: "catalog unavailable" }), { status: 422 });
    else value = { items: [] };
    return new Response(JSON.stringify(value));
  };
  const controller = createJobsPage({ root, app: /** @type {any} */ ({}) });
  const activating = controller.activate(new Set(), "");
  try {
    await until(() => catalogStarted);
    const select = root.querySelector("[data-job-harness]");
    assert.equal(select.disabled, true);
    select.value = "second";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    assert.equal(select.value, "first");
    release(); await activating;
    assert.equal(select.disabled, false);
    select.value = "second";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    await until(() => !select.disabled);
    assert.match(root.querySelector("[data-jobs-notice]").textContent, /catalog unavailable/);
    assert.equal(root.querySelector("[data-job-start]").disabled, true);
    select.value = "first";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    await until(() => !select.disabled);
    assert.equal(root.querySelector("[data-job-start]").disabled, false);
  } finally { release(); await activating; controller.destroy(); root.remove(); globalThis.fetch = previous; }
});
