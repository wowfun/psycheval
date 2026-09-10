import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom, submitActionForm } from "./support/browser.js";

const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test("changing progress preserves the mounted status node", async () => {
  const browser = installBrowserDom('<div id="feedback"></div>');
  try {
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    const feedback = beginFeedback("#feedback");
    feedback.pending("1/10");
    const node = document.querySelector("#feedback .action-feedback");
    node.tabIndex = -1; node.focus();
    feedback.pending("2/10");
    assert.equal(document.querySelector("#feedback .action-feedback"), node);
    assert.equal(document.activeElement, node);
    assert.equal(node.querySelector("p").textContent, "2/10");
  } finally { browser.cleanup(); }
});

for (const visible of [false, true]) test(`success expiry releases feedback and empty notification host (visible=${visible})`, async () => {
  const browser = installBrowserDom('<div id="feedback"></div><div id="content"></div>');
  try {
    if (visible) browser.dom.window.HTMLElement.prototype.getBoundingClientRect = () => ({ top: 10, bottom: 50, left: 10, right: 100 });
    const timers = new Map(); let serial = 0, lookups = 0;
    window.setTimeout = callback => { timers.set(++serial, callback); return serial; };
    window.clearTimeout = id => timers.delete(id);
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    const feedback = beginFeedback(() => { lookups++; return document.querySelector("#feedback"); });
    feedback.success();
    const message = document.querySelector("#feedback .action-feedback");
    message.dispatchEvent(new window.Event("mouseenter"));
    assert.equal(timers.size, 0);
    message.dispatchEvent(new window.Event("mouseleave"));
    assert.equal(timers.size, 1);
    [...timers.values()][0]();
    assert.equal(document.querySelector(".action-feedback"), null);
    assert.equal(document.querySelector(".action-notifications"), null);
    const before = lookups;
    document.querySelector("#content").textContent = "Later render";
    await new Promise(resolve => setTimeout(resolve, 30));
    assert.equal(lookups, before);
    feedback.error("Late response");
    assert.equal(document.querySelector(".action-feedback"), null);
  } finally { browser.cleanup(); }
});

for (const stop of ["dispose", "pagehide", "replace"]) test(`operation observation stops on ${stop}`, async () => {
  let reads = 0;
  const browser = installBrowserDom('<div id="feedback"></div>', { fetch: async () => {
    reads++;
    return new Response(JSON.stringify({ state: "running", completed: 0, total: 1 }));
  } });
  try {
    const timers = new Map(); let serial = 0, busy = false;
    window.setTimeout = callback => { timers.set(++serial, callback); return serial; };
    window.clearTimeout = id => timers.delete(id);
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    const { watchOperation } = await import("../../src/psycheval/assets/web/modules/operation-feedback.js");
    const feedback = beginFeedback("#feedback");
    await watchOperation("one", { feedback, onBusy: value => { busy = value; } });
    const oldPoll = [...timers.values()][0];
    if (stop === "dispose") feedback.dispose();
    else if (stop === "pagehide") window.dispatchEvent(new window.Event("pagehide"));
    else await watchOperation("one", { feedback: beginFeedback("#feedback", { key: "other" }) });
    assert.equal(busy, false);
    assert.equal(timers.size, stop === "replace" ? 1 : 0);
    const before = reads;
    await oldPoll();
    assert.equal(reads, before);
    window.dispatchEvent(new window.Event("pagehide"));
  } finally { browser.cleanup(); }
});

test("post-save refresh keeps retry available after repeated read failures and clears on success", async () => {
  const browser = installBrowserDom('<div id="feedback"></div>');
  try {
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    const { offerRefresh } = await import("../../src/psycheval/assets/web/modules/operation-feedback.js");
    let calls = 0;
    offerRefresh(beginFeedback("#feedback"), new Error("Initial read failed"), async () => {
      calls++;
      if (calls < 3) throw new Error(`Read failure ${calls}`);
    });
    for (let attempt = 1; attempt <= 3; attempt++) {
      const retry = [...document.querySelectorAll("#feedback button")].find(button => button.textContent === "Refresh");
      retry.click(); retry.click();
      await tick();
      assert.equal(calls, attempt);
      if (attempt < 3) assert.match(document.querySelector("#feedback").textContent, new RegExp(`Read failure ${attempt}`));
    }
    assert.equal(document.querySelector("#feedback .action-feedback"), null);
  } finally { browser.cleanup(); }
});

test("cleared feedback releases targets, hides empty status, and cannot be revived", async () => {
  const browser = installBrowserDom('<div data-global-shell-status hidden></div><div id="content"></div>');
  try {
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    let lookups = 0;
    const target = () => { lookups++; return document.querySelector("[data-global-shell-status]"); };
    const first = beginFeedback(target, { key: "shell" });
    const second = beginFeedback(target, { key: "another" });
    first.error("First"); second.error("Second");
    first.clear();
    assert.equal(target().hidden, false);
    second.clear();
    assert.equal(target().hidden, true);
    await tick();
    const before = lookups;
    document.querySelector("#content").textContent = "Unrelated render";
    await tick();
    assert.equal(lookups, before);
    first.error("Late error");
    assert.equal(document.querySelector(".action-feedback"), null);
  } finally { browser.cleanup(); }
});

test("attached feedback and identical progress avoid repeated target lookup and DOM replacement", async () => {
  const browser = installBrowserDom('<div id="feedback"></div><div id="content"></div>');
  try {
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    const feedback = beginFeedback("#feedback");
    feedback.pending("1/10");
    const node = document.querySelector("#feedback .action-feedback");
    feedback.pending("1/10");
    assert.equal(document.querySelector("#feedback .action-feedback"), node);
    const query = document.querySelector.bind(document);
    let lookups = 0;
    document.querySelector = selector => { if (selector === "#feedback") lookups++; return query(selector); };
    query("#content").textContent = "Other update";
    await tick();
    assert.equal(lookups, 0);
  } finally { browser.cleanup(); }
});

test("a failed operation without item diagnostics still identifies the failed operation", async () => {
  const browser = installBrowserDom('<div id="operation"></div>', { fetch: async () => new Response(JSON.stringify({
    state: "failed", kind: "source-import", failures: [],
  })) });
  try {
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    const { watchOperation } = await import("../../src/psycheval/assets/web/modules/operation-feedback.js");
    await watchOperation("failure-id", { feedback: beginFeedback("#operation") });
    assert.match(document.querySelector("#operation").textContent, /0 succeeded, 1 failed/);
    assert.match(document.querySelector("#operation details").textContent, /Operation failed: source-import \(failure-id\)/);
  } finally { browser.cleanup(); }
});

test("notification positioning coalesces repeated DOM updates into one frame", async () => {
  const browser = installBrowserDom('<main class="workspace"><div id="feedback"></div><div id="content"></div></main>');
  try {
    let reads = 0, lookups = 0;
    document.querySelector(".workspace").getBoundingClientRect = () => { reads++; return { right: 800, width: 800 }; };
    const frames = [];
    window.requestAnimationFrame = callback => frames.push(callback);
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    beginFeedback(() => { lookups++; return document.querySelector("#feedback"); }).error("Offscreen error", { details: ["Diagnostics"] });
    const details = document.querySelector("#feedback details");
    details.open = true; details.tabIndex = -1; details.focus();
    await tick();
    const before = reads, previousLookups = lookups;
    for (let index = 0; index < 3; index++) {
      document.querySelector("#content").textContent = String(index);
      await tick();
    }
    assert.equal(reads, before);
    assert.equal(lookups, previousLookups);
    assert.equal(frames.length, 1);
    frames[0]();
    assert.equal(reads, before + 1);
    assert.equal(lookups, previousLookups + 1);
    assert.equal(document.querySelector("#feedback details"), details);
    assert.equal(details.open, true);
    assert.equal(document.activeElement, details);
  } finally { browser.cleanup(); }
});

test("disposing an in-flight operation aborts its read and ignores a late response", async () => {
  let release, signal, completed = 0, busy = false;
  const browser = installBrowserDom('<div id="feedback"></div>', { fetch: (_path, options) => {
    signal = options.signal;
    return new Promise(resolve => { release = resolve; });
  } });
  try {
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    const { watchOperation } = await import("../../src/psycheval/assets/web/modules/operation-feedback.js");
    const feedback = beginFeedback("#feedback");
    const observed = watchOperation("late", {
      feedback, onBusy: value => { busy = value; }, onComplete: async () => { completed++; },
    });
    feedback.dispose();
    assert.equal(signal.aborted, true);
    assert.equal(busy, false);
    release(new Response(JSON.stringify({ state: "succeeded" })));
    await observed;
    assert.equal(completed, 0);
    assert.equal(document.querySelector(".action-feedback"), null);
  } finally { browser.cleanup(); }
});

for (const committed of [false, true]) test(`refresh retry holds the busy gate and prevents overlap (committed=${committed})`, async () => {
  const browser = installBrowserDom('<div id="operation"></div>', { fetch: async () => new Response(JSON.stringify({
    state: committed ? "failed" : "succeeded", failures: committed ? [{ index: 0, error: "Index offline" }] : [],
  })) });
  try {
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    const { watchOperation } = await import("../../src/psycheval/assets/web/modules/operation-feedback.js");
    let busy = false, refreshes = 0, release;
    await watchOperation("retry", {
      committed, feedback: beginFeedback("#operation"), onBusy: value => { busy = value; },
      onComplete: async () => {
        refreshes++;
        if (refreshes === 1) { if (!committed) throw new Error("Read offline"); return; }
        await new Promise(resolve => { release = resolve; });
      },
    });
    assert.equal(busy, false);
    const retry = [...document.querySelectorAll("#operation button")].find(button => button.textContent === "Refresh");
    retry.click(); retry.click();
    assert.equal(busy, true);
    assert.equal(refreshes, 2);
    release(); await tick();
    assert.equal(busy, false);
    if (committed) {
      assert.match(document.querySelector("#operation").textContent, /0: Index offline/);
      assert.doesNotMatch(document.querySelector("#operation").textContent, /Completed/);
    } else assert.match(document.querySelector("#operation").textContent, /Completed/);
  } finally { browser.cleanup(); }
});

test("operation progress has no empty phase prefix", async () => {
  let requests = 0;
  const browser = installBrowserDom('<div id="operation"></div>', { fetch: async () => new Response(JSON.stringify({
    state: ++requests === 1 ? "running" : "succeeded", completed: 0, total: 1,
  })) });
  try {
    const callbacks = [];
    window.setTimeout = callback => callbacks.push(callback);
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    const { watchOperation } = await import("../../src/psycheval/assets/web/modules/operation-feedback.js");
    await watchOperation("progress", { feedback: beginFeedback("#operation") });
    assert.equal(document.querySelector("#operation p").textContent, "0/1");
    await callbacks[0]();
  } finally { browser.cleanup(); }
});

test("feedback survives rendering and independent refreshes; stale actions cannot replace a result", async () => {
  const browser = installBrowserDom('<main><div id="operation"></div><div id="load"></div></main>');
  try {
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    const old = beginFeedback("#operation", { key: "save" });
    old.pending();
    const current = beginFeedback("#operation", { key: "save" });
    current.error("Save failed <script>unsafe</script>");
    old.success("Old response");
    beginFeedback("#load").clear();
    document.querySelector("main").innerHTML = '<div id="operation"></div><div id="load"></div>';
    await new Promise(resolve => window.requestAnimationFrame(resolve));
    assert.match(document.querySelector("#operation").textContent, /Save failed/);
    assert.doesNotMatch(document.querySelector("#operation").textContent, /Old response/);
    assert.equal(document.querySelector("#operation script"), null);
    assert.equal(document.querySelectorAll(".action-toast").length, 1);
    current.dispose();
    assert.equal(document.querySelectorAll(".action-feedback").length, 0);
  } finally { browser.cleanup(); }
});

test("visible local feedback is not duplicated into a notification", async () => {
  const browser = installBrowserDom('<div id="region"></div>');
  try {
    browser.dom.window.HTMLElement.prototype.getBoundingClientRect = () => ({ top: 100, bottom: 160, left: 30, right: 330 });
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    beginFeedback("#region").error("Local error");
    assert.equal(document.querySelectorAll("#region .action-feedback").length, 1);
    assert.equal(document.querySelectorAll(".action-toast").length, 0);
  } finally { browser.cleanup(); }
});

test("action forms retain failed input, map structured field errors, and prevent duplicate submissions", async () => {
  const browser = installBrowserDom('<button id="opener">Register</button>');
  try {
    const { openActionForm } = await import("../../src/psycheval/assets/web/modules/action-form.js");
    let reject, calls = 0;
    const opener = document.querySelector("#opener");
    opener.focus();
    openActionForm({
      title: "Register Dataset", fields: [{ name: "path", label: "Dataset path" }],
      submit: () => { calls++; return new Promise((_resolve, failure) => { reject = failure; }); },
    });
    const form = submitActionForm({ path: '"D:\\含 空格\\datasets"' });
    form.dispatchEvent(new window.Event("submit", { cancelable: true }));
    assert.equal(calls, 1);
    assert.equal(form.getAttribute("aria-busy"), "true");
    assert.equal(form.elements.namedItem("path").readOnly, true);
    reject(Object.assign(new Error("Invalid Dataset path"), { problem: { errors: [{ pointer: "/path", detail: "Directory does not exist" }] } }));
    await tick();
    const input = form.elements.namedItem("path");
    assert.equal(input.value, '"D:\\含 空格\\datasets"');
    assert.equal(input.readOnly, false);
    assert.equal(input.getAttribute("aria-invalid"), "true");
    assert.equal(document.getElementById(input.getAttribute("aria-describedby")).textContent, "Directory does not exist");
    assert.match(form.textContent, /Invalid Dataset path/);
    assert.equal(document.querySelector(".action-toast"), null);
    assert.equal(form.querySelector('[type="submit"]').disabled, false);
    form.querySelector('[data-action-form-cancel]').click();
    assert.equal(document.querySelector(".action-form-overlay"), null);
    assert.equal(document.activeElement, opener);
  } finally { browser.cleanup(); }
});

test("destructive secondary actions are not implicit submissions", async () => {
  const browser = installBrowserDom('<button id="opener">Rename</button>');
  try {
    const { openActionForm } = await import("../../src/psycheval/assets/web/modules/action-form.js");
    let saved = 0, removed = 0;
    const root = openActionForm({ title: "Rename", fields: [{ name: "name", label: "Name", value: "draft" }],
      submit: async () => { saved++; return false; },
      secondaryAction: { label: "Delete", run: async () => { removed++; return false; } },
    });
    const form = root.querySelector("form");
    assert.equal(form.querySelector('[type="submit"]').textContent, "Save");
    form.requestSubmit(); await tick();
    assert.equal(saved, 1); assert.equal(removed, 0);
    root.querySelector('[data-secondary-action]').click(); await tick();
    assert.equal(removed, 1);
  } finally { browser.cleanup(); }
});

test("a nested modal preserves the suspended input draft and restores focus", async () => {
  const browser = installBrowserDom('<button id="opener">Open</button>');
  try {
    const { openActionForm } = await import("../../src/psycheval/assets/web/modules/action-form.js");
    const first = openActionForm({ title: "First", fields: [{ name: "draft", label: "Draft" }], submit: async () => {} });
    const input = first.querySelector("input"); input.value = "unsaved"; input.focus();
    const second = openActionForm({ title: "Second", fields: [], submit: async () => {} });
    assert.equal(first.isConnected, true); assert.equal(first.hidden, true);
    second.querySelector('[data-action-form-cancel]').click();
    assert.equal(first.hidden, false); assert.equal(input.value, "unsaved");
    assert.equal(document.activeElement, input);
  } finally { browser.cleanup(); }
});

test("input dialogs constrain keyboard focus and retain derived defaults until edited", async () => {
  const browser = installBrowserDom('<button id="opener">New Task</button>');
  try {
    const { openActionForm } = await import("../../src/psycheval/assets/web/modules/action-form.js");
    const root = openActionForm({ title: "New Task", fields: [
      { name: "directory", label: "Directory" },
      { name: "package", label: "Package", defaultFrom: "directory", prefix: "local/" },
    ], submit: async () => {} });
    const directory = root.querySelector('[name="directory"]');
    const pkg = root.querySelector('[name="package"]');
    directory.value = "hello";
    directory.dispatchEvent(new window.Event("input"));
    assert.equal(pkg.value, "local/hello");
    pkg.value = "custom/package";
    pkg.dispatchEvent(new window.Event("input"));
    directory.value = "world";
    directory.dispatchEvent(new window.Event("input"));
    assert.equal(pkg.value, "custom/package");
    const submit = root.querySelector('[type="submit"]');
    submit.focus();
    submit.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true }));
    assert.equal(document.activeElement, directory);
    directory.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    assert.equal(document.querySelector(".action-form-overlay"), null);
  } finally { browser.cleanup(); }
});

test("an unavailable operation can be queried again without replaying its write", async () => {
  const requests = [];
  const browser = installBrowserDom('<div id="operation"></div>', { fetch: async (path, options) => {
    requests.push({ path, method: options.method });
    if (requests.length === 1) throw new Error("Disconnected");
    return new Response(JSON.stringify({ state: "succeeded", completed: 1, total: 1, successes: [{}], failures: [] }));
  } });
  try {
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    const { watchOperation } = await import("../../src/psycheval/assets/web/modules/operation-feedback.js");
    let completed = 0;
    await watchOperation("same-operation", { feedback: beginFeedback("#operation"), onComplete: async () => { completed++; } });
    assert.match(document.querySelector("#operation").textContent, /temporarily unavailable/);
    const retry = [...document.querySelectorAll("#operation button")].find(button => button.textContent === "Check again");
    retry.click(); retry.click();
    await tick();
    assert.equal(completed, 1);
    assert.deepEqual(requests, [
      { path: "/api/operations/same-operation", method: "GET" },
      { path: "/api/operations/same-operation", method: "GET" },
    ]);
    assert.match(document.querySelector("#operation").textContent, /Completed/);
  } finally { browser.cleanup(); }
});


for (const observer of [true, false]) test(`refresh error context appears exactly once (observer=${observer})`, async () => {
  const browser = installBrowserDom('<div id="feedback"></div>', { fetch: async () => new Response(JSON.stringify({ state: "succeeded" })) });
  try {
    const { beginFeedback } = await import("../../src/psycheval/assets/web/modules/action-feedback.js");
    const { watchOperation, offerRefresh } = await import("../../src/psycheval/assets/web/modules/operation-feedback.js");
    const message = "Saved, but workspace refresh failed";
    const feedback = beginFeedback("#feedback");
    if (observer) await watchOperation("saved", { feedback, committed: true, onComplete: async () => { throw new Error(message); } });
    else offerRefresh(feedback, new Error(message), async () => {});
    assert.equal(document.querySelector("#feedback p").textContent, message);
    feedback.dispose();
  } finally { browser.cleanup(); }
});
