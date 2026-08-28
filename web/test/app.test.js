import assert from "node:assert/strict";
import test from "node:test";

import { createBrowserPlatform } from "../../src/psycheval/assets/web/app/browser-platform.js";
import { createWorkspaceApp } from "../../src/psycheval/assets/web/app/workspace-app.js";
import { installBrowserDom } from "./support/browser.js";

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

    window.history.back();
    await new Promise(resolve => setTimeout(resolve, 20));
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
