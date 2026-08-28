import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","workspace_id":"workspace-one","sources":[]}</script>
  <button id="left-opener">Left opener</button>
  <button id="views-opener">Views opener</button>
  <button id="trial-opener">Trial opener</button>
  <button id="neutral">Neutral</button>
  <aside id="left-sidebar" hidden></aside>
  <aside id="views-sidebar" hidden></aside>
  <aside id="trial-sidebar" hidden></aside>
  <aside id="workspace-report-reader" hidden></aside>
`);

let viewport = 1200;
Object.defineProperty(document.documentElement, "clientWidth", {
  configurable: true,
  get: () => viewport,
});
Object.defineProperty(window, "innerWidth", {
  configurable: true,
  get: () => viewport,
});

const sidebar = await import("../../src/psycheval/assets/web/modules/sidebar.js");
const reportSidebar = await import("../../src/psycheval/assets/web/modules/report-sidebar.js");
const homeControls = await import("../../src/psycheval/assets/web/modules/home-controls.js");
const controllers = [];

test.after(() => browser.cleanup());
test.afterEach(() => {
  controllers.splice(0).reverse().forEach(controller => controller.destroy());
  window.localStorage.clear();
  document.documentElement.removeAttribute("style");
  document.body.className = "";
  viewport = 1200;
  for (const root of document.querySelectorAll("aside")) {
    root.hidden = true;
    root.innerHTML = "";
    root.className = "";
    root.removeAttribute("data-sidebar-id");
    root.removeAttribute("data-sidebar-side");
  }
});

function pointerEvent(type, values) {
  const event = new window.Event(type, { bubbles: true, cancelable: true });
  Object.entries(values).forEach(([key, value]) => {
    Object.defineProperty(event, key, { configurable: true, value });
  });
  return event;
}

function drag(handle, pointerId, clientX) {
  handle.dispatchEvent(pointerEvent("pointerdown", { button: 0, pointerId, clientX }));
  document.dispatchEvent(pointerEvent("pointermove", { pointerId, clientX }));
  document.dispatchEvent(pointerEvent("pointerup", { pointerId, clientX }));
}

function createController({
  id,
  side,
  root,
  workspaceId = "workspace-one",
  defaultWidth = () => 600,
  closeCalls = [],
}) {
  let controller;
  controller = sidebar.createSidebarController({
    id,
    side,
    root,
    bodyClass: `${id}-open`,
    cssVariable: `--${id}-width`,
    workspaceId,
    minWidth: 360,
    minWorkspaceWidth: 360,
    defaultWidth,
    resizeLabel: `Resize ${id}`,
    onRequestClose: options => {
      closeCalls.push(options);
      return controller.close(options);
    },
  });
  controllers.push(controller);
  return controller;
}

test("pointer and keyboard resizing are direction-aware and always clean up capture", () => {
  const left = createController({ id: "pointer-left", side: "left", root: "#left-sidebar" });
  const right = createController({ id: "pointer-right", side: "right", root: "#trial-sidebar" });
  left.open();
  right.open();
  const leftHandle = document.querySelector("#left-sidebar [data-sidebar-resize]");
  const rightHandle = document.querySelector("#trial-sidebar [data-sidebar-resize]");
  let captured = null;
  let released = null;
  leftHandle.setPointerCapture = pointerId => { captured = pointerId; };
  leftHandle.releasePointerCapture = pointerId => { released = pointerId; };

  leftHandle.dispatchEvent(pointerEvent("pointerdown", { button: 2, pointerId: 3, clientX: 700 }));
  assert.equal(document.body.classList.contains("sidebar-resizing"), false);
  assert.equal(document.documentElement.style.getPropertyValue("--pointer-left-width"), "600px");

  leftHandle.dispatchEvent(pointerEvent("pointerdown", { button: 0, pointerId: 7, clientX: 600 }));
  document.dispatchEvent(pointerEvent("pointermove", { pointerId: 8, clientX: 400 }));
  assert.equal(document.documentElement.style.getPropertyValue("--pointer-left-width"), "600px");
  document.dispatchEvent(pointerEvent("pointermove", { pointerId: 7, clientX: 500 }));
  assert.equal(document.documentElement.style.getPropertyValue("--pointer-left-width"), "500px");
  document.dispatchEvent(pointerEvent("pointercancel", { pointerId: 7, clientX: 500 }));
  document.dispatchEvent(pointerEvent("pointermove", { pointerId: 7, clientX: 450 }));
  assert.equal(captured, 7);
  assert.equal(released, 7);
  assert.equal(document.body.classList.contains("sidebar-resizing"), false);
  assert.equal(document.documentElement.style.getPropertyValue("--pointer-left-width"), "500px");

  rightHandle.dispatchEvent(pointerEvent("pointerdown", { button: 0, pointerId: 9, clientX: 500 }));
  document.dispatchEvent(pointerEvent("pointermove", { pointerId: 9, clientX: 520 }));
  document.dispatchEvent(pointerEvent("pointerup", { pointerId: 9, clientX: 520 }));
  assert.equal(document.documentElement.style.getPropertyValue("--pointer-right-width"), "680px");

  leftHandle.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
  assert.equal(document.documentElement.style.getPropertyValue("--pointer-left-width"), "524px");
  leftHandle.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowLeft", shiftKey: true, bubbles: true }));
  assert.equal(document.documentElement.style.getPropertyValue("--pointer-left-width"), "452px");
  rightHandle.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
  assert.equal(document.documentElement.style.getPropertyValue("--pointer-right-width"), "704px");
  rightHandle.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowRight", shiftKey: true, bubbles: true }));
  assert.equal(document.documentElement.style.getPropertyValue("--pointer-right-width"), "632px");
});

test("storage is isolated by Workspace and sidebar while viewport clamping remains temporary", () => {
  window.localStorage.setItem(sidebar.sidebarStorageKey("workspace-one", "stored"), "760");
  window.localStorage.setItem(sidebar.sidebarStorageKey("workspace-two", "stored"), "720");
  window.localStorage.setItem(sidebar.sidebarStorageKey("workspace-one", "invalid"), "broken");
  const stored = createController({ id: "stored", side: "left", root: "#left-sidebar" });
  const invalid = createController({
    id: "invalid",
    side: "right",
    root: "#views-sidebar",
    defaultWidth: width => Math.min(760, Math.max(620, width * 0.44)),
  });
  stored.open();
  invalid.open();

  assert.equal(document.documentElement.style.getPropertyValue("--stored-width"), "760px");
  assert.equal(document.documentElement.style.getPropertyValue("--invalid-width"), "620px");
  assert.equal(window.localStorage.getItem(sidebar.sidebarStorageKey("workspace-two", "stored")), "720");
  const invalidHandle = document.querySelector("#views-sidebar [data-sidebar-resize]");
  drag(invalidHandle, 11, 1_190);
  assert.equal(invalidHandle.getAttribute("aria-valuenow"), "360");
  drag(invalidHandle, 12, 0);
  assert.equal(invalidHandle.getAttribute("aria-valuenow"), "840");
  viewport = 700;
  window.dispatchEvent(new window.Event("resize"));
  assert.equal(document.documentElement.style.getPropertyValue("--stored-width"), "360px");
  assert.equal(window.localStorage.getItem(sidebar.sidebarStorageKey("workspace-one", "stored")), "760");
  viewport = 1200;
  window.dispatchEvent(new window.Event("resize"));
  assert.equal(document.documentElement.style.getPropertyValue("--stored-width"), "760px");

  drag(document.querySelector("#left-sidebar [data-sidebar-resize]"), 13, 540);
  drag(invalidHandle, 14, 590);
  const trial = createController({ id: "trial-independent", side: "right", root: "#trial-sidebar" });
  trial.open();
  drag(document.querySelector("#trial-sidebar [data-sidebar-resize]"), 15, 520);
  assert.equal(window.localStorage.getItem(sidebar.sidebarStorageKey("workspace-one", "stored")), "540");
  assert.equal(window.localStorage.getItem(sidebar.sidebarStorageKey("workspace-one", "invalid")), "610");
  assert.equal(window.localStorage.getItem(sidebar.sidebarStorageKey("workspace-one", "trial-independent")), "680");
});

test("same-side replacement, Escape ordering, focus fallback, and navigation share one lifecycle", async () => {
  const reportClose = [];
  const viewsClose = [];
  const trialClose = [];
  window.localStorage.setItem(sidebar.sidebarStorageKey("workspace-one", "report-reader"), "500");
  window.localStorage.setItem(sidebar.sidebarStorageKey("workspace-one", "workspace-views"), "620");
  window.localStorage.setItem(sidebar.sidebarStorageKey("workspace-one", "trial-detail"), "700");
  const report = createController({ id: "report-reader", side: "left", root: "#left-sidebar", closeCalls: reportClose });
  const views = createController({ id: "workspace-views", side: "right", root: "#views-sidebar", closeCalls: viewsClose });
  const trial = createController({ id: "trial-detail", side: "right", root: "#trial-sidebar", closeCalls: trialClose });
  homeControls.bindHomeControls();

  assert.equal(window.localStorage.getItem(sidebar.sidebarStorageKey("workspace-one", "report-reader")), "500");
  assert.equal(window.localStorage.getItem(sidebar.sidebarStorageKey("workspace-one", "workspace-views")), "620");
  assert.equal(window.localStorage.getItem(sidebar.sidebarStorageKey("workspace-one", "trial-detail")), "700");

  views.open({ opener: document.querySelector("#views-opener") });
  report.open({ opener: document.querySelector("#left-opener") });
  assert.equal(document.querySelector("#views-sidebar").hidden, false);
  assert.equal(document.querySelector("#left-sidebar").hidden, false);
  trial.open({
    opener: document.querySelector("#trial-opener"),
    openerSelector: "#trial-opener",
  });
  assert.equal(document.querySelector("#views-sidebar").hidden, true);
  assert.equal(document.querySelector("#left-sidebar").hidden, false);
  assert.equal(document.querySelector("#trial-sidebar").hidden, false);
  assert.equal(viewsClose.at(-1).reason, "replaced");
  assert.equal(viewsClose.at(-1).restoreFocus, false);

  report.open();
  document.querySelector("#trial-opener").remove();
  const replacementTrialOpener = document.createElement("button");
  replacementTrialOpener.id = "trial-opener";
  document.body.append(replacementTrialOpener);
  document.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  await new Promise(resolve => window.requestAnimationFrame(resolve));
  assert.equal(document.querySelector("#trial-sidebar").hidden, true);
  assert.equal(document.querySelector("#left-sidebar").hidden, false);
  assert.equal(document.activeElement, replacementTrialOpener);

  views.open({
    opener: document.querySelector("#views-opener"),
    openerSelector: "#views-opener",
  });
  await new Promise(resolve => window.requestAnimationFrame(resolve));
  document.querySelector("#neutral").focus();
  window.dispatchEvent(new window.CustomEvent("peval:workspace-navigate"));
  assert.equal(document.querySelector("#left-sidebar").hidden, true);
  assert.equal(document.querySelector("#views-sidebar").hidden, true);
  assert.equal(document.activeElement, document.querySelector("#neutral"));
  assert.equal(reportClose.at(-1).reason, "navigate");
  assert.equal(viewsClose.at(-1).reason, "navigate");
  assert.equal(trialClose.at(-1).reason, "dismiss");
});

test("sync remounts the delegated handle after business rendering replaces the root", () => {
  const controller = createController({ id: "rerendered", side: "right", root: "#trial-sidebar" });
  controller.open();
  document.querySelector("#trial-sidebar").innerHTML = '<button data-sidebar-close type="button">Close</button>';
  controller.sync();

  const handle = document.querySelector("#trial-sidebar [data-sidebar-resize]");
  assert.ok(handle);
  assert.equal(handle.getAttribute("aria-valuenow"), "600");
  document.querySelector("#trial-sidebar [data-sidebar-close]").click();
  assert.equal(document.querySelector("#trial-sidebar").hidden, true);
});

test("destroy requests business cleanup before detaching the controller", () => {
  const closeCalls = [];
  const controller = createController({
    id: "destroyed",
    side: "right",
    root: "#trial-sidebar",
    closeCalls,
  });
  controller.open();

  controller.destroy();

  assert.equal(document.querySelector("#trial-sidebar").hidden, true);
  assert.equal(closeCalls.length, 1);
  assert.equal(closeCalls[0].reason, "destroy");
  assert.equal(closeCalls[0].restoreFocus, false);
});

test("Report owners hand off one physical sidebar after cleaning the previous owner", () => {
  const closeCalls = [];
  let home;
  let reportsPage;
  home = reportSidebar.createReportSidebarAdapter({
    ownerId: "test-home-report",
    onRequestClose: options => {
      closeCalls.push({ owner: "home", ...options });
      return home.close(options);
    },
  });
  reportsPage = reportSidebar.createReportSidebarAdapter({
    ownerId: "test-reports-page",
    onRequestClose: options => {
      closeCalls.push({ owner: "reports", ...options });
      return reportsPage.close(options);
    },
  });
  try {
    home.open({
      render: () => { document.querySelector("#workspace-report-reader").innerHTML = "<p>Home</p>"; },
    });
    reportsPage.open({
      render: () => { document.querySelector("#workspace-report-reader").innerHTML = "<p>Reports</p>"; },
    });

    const root = document.querySelector("#workspace-report-reader");
    assert.equal(root.querySelector("p").textContent, "Reports");
    assert.equal(root.querySelectorAll("[data-sidebar-resize]").length, 1);
    assert.equal(home.close(), false);
    assert.equal(root.querySelector("p").textContent, "Reports");
    assert.equal(closeCalls.length, 1);
    assert.equal(closeCalls[0].owner, "home");
    assert.equal(closeCalls[0].reason, "replaced");
  } finally {
    reportsPage.destroy();
    home.destroy();
  }
});
