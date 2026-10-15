import assert from "node:assert/strict";
import test from "node:test";

import { createBrowserPlatform } from "../../src/psycheval/assets/web/app/browser-platform.js";
import { createWorkspaceApp } from "../../src/psycheval/assets/web/app/workspace-app.js";
import { installBrowserDom } from "./support/browser.js";
import { decodeWorkspaceLocation } from "../../src/psycheval/assets/web/app/workspace-location.js";

function locationAdapter(page, restored) {
  let location = decodeWorkspaceLocation(page, new URL(`http://localhost${page === "home" ? "/" : "/reports"}`));
  return {
    activate() {}, snapshot: () => ({}), destroy() {},
    captureLocation: () => location,
    restoreLocation(value) { location = value; restored?.push(value); },
    update(value) { location = { ...location, ...value }; },
  };
}

test("conditions replace history; object opening and closing push; hidden pages cannot publish", async () => {
  const browser = installBrowserDom(workspaceShell());
  const home = locationAdapter("home"), reports = locationAdapter("reports");
  const app = createWorkspaceApp({ platform: createBrowserPlatform(window), initialPage: "home", pageLoaders: { home: () => home, reports: () => reports } });
  try {
    await app.start();
    const original = window.history.length;
    const initial = home.captureLocation();
    home.update({ state: { ...initial.state, query: { ...initial.state.query, search: "中文", page: 2 } } });
    app.locationChanged("home");
    assert.equal(window.history.length, original);
    assert.equal(decodeWorkspaceLocation("home", window.location).state.query.search, "中文");
    home.update({ object: { source: "stable-source" } }); app.locationChanged("home", "object");
    assert.equal(window.history.length, original + 1);
    home.update({ object: { source: "stable-source", step: "2", tab: "trajectory" } }); app.locationChanged("home");
    assert.equal(window.history.length, original + 1);
    home.update({ object: {} }); app.locationChanged("home", "object");
    assert.equal(window.history.length, original + 2);
    await app.navigate("reports");
    const href = window.location.href;
    home.update({ object: { source: "background" } }); app.locationChanged("home", "object");
    assert.equal(window.location.href, href);
    assert.equal(app.shareLink("reports"), href);
  } finally { app.destroy(); browser.cleanup(); }
});

test("history restores query before activation and preserves unsaved page DOM", async () => {
  const browser = installBrowserDom(workspaceShell());
  const calls = [], home = locationAdapter("home"), reports = locationAdapter("reports");
  home.activate = () => { calls.push(home.captureLocation().state.query.search); };
  const app = createWorkspaceApp({ platform: createBrowserPlatform(window), initialPage: "home", pageLoaders: { home: () => home, reports: () => reports } });
  try {
    await app.start();
    document.querySelector("[data-report-draft]").checked = true;
    await app.navigate("home", { search: "?source=outside-page", hash: "#view=" + btoa('{"v":1,"query":{"search":"old conditions"}}').replace(/=+$/, ""), restore: true });
    const shared = window.location.href;
    await app.navigate("reports");
    window.history.replaceState({}, "", shared); window.dispatchEvent(new window.PopStateEvent("popstate"));
    await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(home.captureLocation().object.source, "outside-page");
    assert.equal(calls.at(-1), "old conditions");
    assert.equal(document.querySelector("[data-report-draft]").checked, true);
  } finally { app.destroy(); browser.cleanup(); }
});

test("obsolete location restoration is cancelled and background refresh does not interrupt it", async () => {
  const browser = installBrowserDom(workspaceShell());
  let release, signal;
  const home = locationAdapter("home"), reports = locationAdapter("reports");
  const app = createWorkspaceApp({ platform: createBrowserPlatform(window), initialPage: "home", pageLoaders: { home: () => home, reports: () => reports } });
  try {
    await app.start();
    home.restoreLocation = async (value, cancellation) => {
      signal = cancellation;
      await new Promise(resolve => { release = resolve; });
      if (!signal.aborted) home.update(value);
    };
    const old = app.navigate("home", { search: "?source=obsolete", restore: true });
    await new Promise(resolve => setTimeout(resolve, 0));
    await app.navigate("home", { history: false });
    assert.equal(signal.aborted, false);
    await app.navigate("reports");
    assert.equal(signal.aborted, true);
    release(); await old;
    assert.equal(window.location.pathname, "/reports");
    assert.equal(window.location.search, "");
  } finally { app.destroy(); browser.cleanup(); }
});

function workspaceShell() {
  return `
    <div class="workspace" data-workspace-root>
      <nav>
        <a href="/" data-workspace-route="home" aria-current="page">Home</a>
        <a href="/datasets" data-workspace-route="datasets">Datasets</a>
        <a href="/reports" data-workspace-route="reports">Reports</a>
      </nav>
      <main data-workspace-page="home" tabindex="-1"><input value="kept"></main>
      <main data-workspace-page="datasets" tabindex="-1" hidden><textarea data-dataset-draft></textarea></main>
      <main data-workspace-page="reports" tabindex="-1" hidden><input id="report-target" type="checkbox" data-report-draft></main>
    </div>
  `;
}

test("an explicit object change during activation retains its history entry", async () => {
  const browser = installBrowserDom(workspaceShell());
  const home = locationAdapter("home");
  let release;
  const app = createWorkspaceApp({ platform: createBrowserPlatform(window), initialPage: "home", pageLoaders: { home: () => home } });
  try {
    await app.start();
    home.activate = () => new Promise(resolve => { release = resolve; });
    const restoring = app.navigate("home", { restore: true, history: false });
    await new Promise(resolve => setTimeout(resolve, 0));
    const before = window.history.length;
    home.update({ object: { source: "clicked-during-activation" } });
    app.locationChanged("home", "object");
    release(); await restoring;
    assert.equal(window.history.length, before + 1);
    assert.equal(new URL(window.location.href).searchParams.get("source"), "clicked-during-activation");
  } finally { app.destroy(); browser.cleanup(); }
});

test("a refresh during restoration reapplies even the same domain after the old read", async () => {
  const browser = installBrowserDom(workspaceShell());
  const home = locationAdapter("home");
  let release, activations = 0;
  const app = createWorkspaceApp({ platform: createBrowserPlatform(window), initialPage: "home", pageLoaders: { home: () => home } });
  try {
    await app.start();
    home.activate = async changes => {
      assert.equal(changes.has("catalog"), true);
      if (++activations === 1) await new Promise(resolve => { release = resolve; });
    };
    app.invalidate("catalog");
    const restoring = app.navigate("home", { restore: true });
    await new Promise(resolve => setTimeout(resolve, 0));
    app.invalidate("catalog");
    await app.navigate("home", { history: false });
    release(); await restoring;
    assert.equal(activations, 2);
  } finally { app.destroy(); browser.cleanup(); }
});

test("invalid links and capture limits display localized errors without rejecting start", async () => {
  const browser = installBrowserDom(workspaceShell() + `<script id="peval-i18n" type="application/json">{
    "shared_link_invalid":"工作台链接无效或版本不受支持",
    "shared_link_too_large":"工作台链接超过 64 KiB 限制",
    "shared_link_loading":"工作台定位仍在加载"
  }</script>`);
  const home = locationAdapter("home");
  const app = createWorkspaceApp({ platform: createBrowserPlatform(window), initialPage: "home", pageLoaders: { home: () => home } });
  try {
    window.history.replaceState({}, "", "/#view=broken");
    await app.start();
    assert.match(document.querySelector("[data-workspace-load-error]").textContent, /工作台链接无效/);
    await app.navigate("home", { restore: true, replace: true });
    home.update({ state: { query: { search: "a".repeat(65536) } } });
    const href = window.location.href;
    await app.navigate("home", { history: false });
    assert.equal(window.location.href, href);
    assert.match(document.querySelector("[data-workspace-page=home]").dataset.workspaceStaleMessage, /工作台链接超过/);
    assert.throws(() => app.shareLink("home"), /工作台链接超过/);
  } finally { app.destroy(); browser.cleanup(); }
});

function pageLoaders(calls) {
  return Object.fromEntries(["home", "datasets", "reports"].map(page => [
    page,
    async ({ root }) => {
      calls.push(`load:${page}`);
      return {
        async activate(changes, hash) {
          calls.push(`activate:${page}:${[...changes].sort().join(",")}:${hash}`);
          root.dataset.activated = "true";
        },
        snapshot() {
          return { context: { page }, dirty: page === "datasets" };
        },
        destroy() {
          calls.push(`destroy:${page}`);
        },
      };
    },
  ]));
}

test("operation refresh failures reach their caller and retain invalidation for a read retry", async () => {
  const browser = installBrowserDom(workspaceShell());
  const { refreshWorkspace, setWorkspaceApp, setWorkspaceSnapshotProvider } = await import(
    "../../src/psycheval/assets/web/app/workspace-runtime.js"
  );
  let fail = true, refreshes = 0;
  const app = createWorkspaceApp({
    platform: createBrowserPlatform(window), initialPage: "home",
    publishSnapshot: setWorkspaceSnapshotProvider,
    pageLoaders: {
      home: () => ({
        activate(changes) {
          if (!changes.has("catalog")) return;
          refreshes++;
          if (fail) throw new Error("Catalog refresh unavailable");
        },
        snapshot: () => ({ context: { page: "home" } }),
        destroy() {},
      }),
    },
  });
  setWorkspaceApp(app);
  try {
    await app.start();
    const root = document.querySelector('[data-workspace-page="home"]');
    await assert.rejects(refreshWorkspace("catalog"), /Catalog refresh unavailable/);
    assert.equal(root.dataset.workspaceStale, "true");
    fail = false;
    await app.navigate("home", { focus: false, history: false });
    assert.equal(refreshes, 2);
    assert.equal(root.hasAttribute("data-workspace-stale"), false);
  } finally {
    app.destroy(); setWorkspaceApp(null); setWorkspaceSnapshotProvider(null); browser.cleanup();
  }
});

for (const phase of ["load", "activate"]) for (const superseded of ["navigation", "destroy"]) {
  test(`a ${phase} failure after ${superseded} cannot publish a stale error`, async () => {
    const browser = installBrowserDom(workspaceShell());
    let rejectPending, started;
    const ready = new Promise(resolve => { started = resolve; });
    const pending = new Promise((_, reject) => { rejectPending = reject; });
    const adapter = { activate() {}, snapshot: () => ({}), destroy() {} };
    const app = createWorkspaceApp({
      platform: createBrowserPlatform(window), initialPage: "home",
      pageLoaders: {
        home: () => adapter, reports: () => adapter,
        datasets: () => {
          if (phase === "load") { started(); return pending; }
          return { ...adapter, activate() { started(); return pending; } };
        },
      },
    });
    try {
      await app.start();
      const stale = app.navigate("datasets", { focus: false, throwOnError: true });
      const settled = stale.then(() => null, error => error);
      await ready;
      if (superseded === "destroy") app.destroy();
      else await app.navigate("reports", { focus: false });
      rejectPending(new Error("Obsolete request failed"));
      assert.equal(await settled, null);
      assert.equal(document.querySelector("[data-workspace-stale]"), null);
      assert.equal(document.querySelector("[data-workspace-load-error]"), null);
    } finally { app.destroy(); browser.cleanup(); }
  });
}

test("a current loader failure is propagated and a later navigation can retry it", async () => {
  const browser = installBrowserDom(workspaceShell());
  let attempts = 0;
  const adapter = { activate() {}, snapshot: () => ({}), destroy() {} };
  const app = createWorkspaceApp({
    platform: createBrowserPlatform(window), initialPage: "home",
    pageLoaders: {
      home: () => adapter,
      datasets: () => {
        if (++attempts === 1) return Promise.reject(new Error("Module unavailable"));
        return adapter;
      },
    },
  });
  try {
    await app.start();
    await assert.rejects(app.navigate("datasets", { throwOnError: true }), /Module unavailable/);
    assert.match(document.querySelector("[data-workspace-load-error]").textContent, /Module unavailable/);
    await app.navigate("datasets", { focus: false });
    assert.equal(attempts, 2);
    assert.equal(document.querySelector("[data-workspace-load-error]"), null);
  } finally { app.destroy(); browser.cleanup(); }
});

test("workspace navigation preserves page DOM and consumes targeted invalidations", async () => {
  const browser = installBrowserDom(workspaceShell());
  const calls = [];
  try {
    const root = document.querySelector("[data-workspace-root]");
    const input = document.querySelector("input");
    const navigations = [];
    window.addEventListener("peval:workspace-navigate", event => navigations.push(event.detail));
    let snapshot = () => ({ context: {}, dirty: false });
    const app = createWorkspaceApp({
      platform: createBrowserPlatform(window),
      initialPage: "home",
      pageLoaders: pageLoaders(calls),
      publishSnapshot: provider => { snapshot = provider; },
    });

    await app.start();
    await app.navigate("datasets", { focus: false });
    document.querySelector("[data-dataset-draft]").value = "unsaved task file";
    await app.navigate("home", { focus: false });

    assert.equal(document.querySelector("[data-workspace-root]"), root);
    assert.equal(document.querySelector("input"), input);
    assert.equal(input.value, "kept");
    assert.equal(document.querySelector("[data-dataset-draft]").value, "unsaved task file");
    assert.deepEqual(calls.filter(call => call.startsWith("load:")), [
      "load:home",
      "load:datasets",
    ]);

    app.invalidate("tasks");
    await app.navigate("datasets", { focus: false });
    await app.navigate("home", { focus: false });
    await app.navigate("datasets", { focus: false });

    assert.equal(calls.filter(call => call === "load:datasets").length, 1);
    assert.equal(calls.filter(call => call === "activate:datasets:tasks:").length, 1);
    assert.equal(document.body.classList.contains("serve-page-datasets"), true);
    assert.equal(document.querySelector('[data-workspace-page="home"]').hidden, true);
    assert.equal(document.querySelector('[data-workspace-page="datasets"]').hidden, false);
    assert.equal(
      document.querySelector('[data-workspace-route="datasets"]').getAttribute("aria-current"),
      "page",
    );
    assert.deepEqual(snapshot(), { context: { page: "datasets" }, dirty: true });
    assert.deepEqual(navigations[0], { from: "home", to: "datasets" });

    app.destroy();
    app.destroy();
    assert.equal(calls.filter(call => call === "destroy:home").length, 1);
    assert.equal(calls.filter(call => call === "destroy:datasets").length, 1);
  } finally {
    browser.cleanup();
  }
});

test("a stale page load cannot steal activation and destroy cleans pending adapters", async () => {
  const browser = installBrowserDom(workspaceShell());
  let resolveDatasets;
  const calls = [];
  const adapter = page => ({
    activate: () => calls.push(`activate:${page}`),
    snapshot: () => ({ context: { page }, dirty: false }),
    destroy: () => calls.push(`destroy:${page}`),
  });
  try {
    const app = createWorkspaceApp({
      platform: createBrowserPlatform(window),
      initialPage: "home",
      pageLoaders: {
        home: async () => adapter("home"),
        reports: async () => adapter("reports"),
        datasets: () => new Promise(resolve => { resolveDatasets = resolve; }),
      },
    });
    await app.start();
    const stale = app.navigate("datasets", { focus: false });
    await app.navigate("reports", { focus: false });
    resolveDatasets(adapter("datasets"));
    await stale;

    assert.equal(document.querySelector('[data-workspace-page="reports"]').hidden, false);
    assert.equal(calls.includes("activate:datasets"), false);
    document.querySelector("[data-report-draft]").checked = true;
    await app.navigate("home", { focus: false });
    await app.navigate("reports", { focus: false });
    assert.equal(document.querySelector("[data-report-draft]").checked, true);
    await app.navigate("reports", { hash: "#report-target" });
    assert.equal(document.activeElement?.id, "report-target");

    app.destroy();
    assert.equal(calls.filter(call => call === "destroy:datasets").length, 1);
  } finally {
    browser.cleanup();
  }
});

test("workspace router intercepts ordinary links and follows popstate", async () => {
  const browser = installBrowserDom(workspaceShell());
  try {
    const app = createWorkspaceApp({
      platform: createBrowserPlatform(window),
      initialPage: "home",
      pageLoaders: pageLoaders([]),
    });
    await app.start();

    const datasets = document.querySelector('[data-workspace-route="datasets"]');
    const click = new window.MouseEvent("click", { bubbles: true, cancelable: true });
    datasets.dispatchEvent(click);
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(click.defaultPrevented, true);
    assert.equal(window.location.pathname, "/datasets");

    const home = document.querySelector('[data-workspace-route="home"]');
    const modifiedClick = new window.MouseEvent("click", {
      bubbles: true,
      cancelable: true,
      ctrlKey: true,
    });
    home.dispatchEvent(modifiedClick);
    assert.equal(modifiedClick.defaultPrevented, false);

    const popped = new Promise(resolve => window.addEventListener("popstate", resolve, { once: true }));
    window.history.back();
    await popped;
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(document.querySelector('[data-workspace-page="home"]').hidden, false);
    app.destroy();
  } finally {
    browser.cleanup();
  }
});

test("a page loader can recover after failure without leaving a stale error banner", async () => {
  const browser = installBrowserDom(`
    <script type="application/json" id="peval-i18n">{"serve_page_load_failed":"无法加载此页面。","serve_reload":"重新加载"}</script>
    ${workspaceShell()}
  `);
  let attempts = 0;
  try {
    const app = createWorkspaceApp({
      platform: createBrowserPlatform(window),
      initialPage: "home",
      pageLoaders: {
        home: async () => {
          attempts += 1;
          if (attempts === 1) throw new Error("temporary module failure");
          return {
            activate() {},
            snapshot: () => ({ context: { page: "home" }, dirty: false }),
            destroy() {},
          };
        },
      },
    });

    await app.start();
    assert.match(
      document.querySelector("[data-workspace-load-error]")?.textContent || "",
      /无法加载此页面。 temporary module failure/,
    );
    assert.equal(document.querySelector("[data-workspace-load-error] button")?.textContent, "重新加载");

    await app.navigate("home", { focus: false });
    assert.equal(attempts, 2);
    assert.equal(document.querySelector("[data-workspace-load-error]"), null);
    app.destroy();
  } finally {
    browser.cleanup();
  }
});
