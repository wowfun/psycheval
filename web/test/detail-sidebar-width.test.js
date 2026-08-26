import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","workspace_id":"workspace-one","sources":[]}</script>
  <section id="trace"></section>
  <aside id="workspace-report-reader" hidden></aside>
  <aside id="detail-sidebar" hidden></aside>
`);

Object.defineProperty(document.documentElement, "clientWidth", { configurable: true, value: 1200 });
Object.defineProperty(window, "innerWidth", { configurable: true, writable: true, value: 1200 });

const runtime = await import("../../src/psycheval/assets/web/modules/runtime.js");
const sidebarModule = await import("../../src/psycheval/assets/web/modules/detail-sidebar.js");

test.after(() => browser.cleanup());

function pointerEvent(type, values) {
  const event = new window.Event(type, { bubbles: true, cancelable: true });
  Object.entries(values).forEach(([key, value]) => {
    Object.defineProperty(event, key, { configurable: true, value });
  });
  return event;
}

function renderOpenSidebar() {
  runtime.state.view = {
    trajectory: [{ steps: [], final_metrics: {} }],
    trajectory_meta: [{ trial_key: "trial-one", status: "passed", steps: [] }],
    annotations: {},
  };
  runtime.state.selectedTrial = "trial-one";
  runtime.state.detailSidebar.open = true;
  sidebarModule.renderDetailSidebar();
  return document.querySelector("[data-detail-sidebar-resize]");
}

test("the detail sidebar resizes from its left edge with pointer and keyboard input", () => {
  const handle = renderOpenSidebar();
  let capturedPointer = null;
  let releasedPointer = null;
  handle.setPointerCapture = pointerId => { capturedPointer = pointerId; };
  handle.releasePointerCapture = pointerId => { releasedPointer = pointerId; };
  assert.equal(handle.getAttribute("role"), "separator");
  assert.equal(handle.getAttribute("aria-valuemin"), "360");
  assert.equal(handle.getAttribute("aria-valuemax"), "840");

  handle.dispatchEvent(pointerEvent("pointerdown", { button: 0, pointerId: 7, clientX: 580 }));
  document.dispatchEvent(pointerEvent("pointermove", { pointerId: 7, clientX: 300 }));
  document.dispatchEvent(pointerEvent("pointerup", { pointerId: 7, clientX: 300 }));

  assert.equal(capturedPointer, 7);
  assert.equal(releasedPointer, 7);
  assert.equal(document.documentElement.style.getPropertyValue("--detail-sidebar-width"), "840px");
  assert.equal(window.localStorage.getItem("peval.detail-sidebar-width.v1.workspace-one"), "840");

  handle.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
  assert.equal(document.documentElement.style.getPropertyValue("--detail-sidebar-width"), "816px");
  handle.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowLeft", shiftKey: true, bubbles: true }));
  assert.equal(document.documentElement.style.getPropertyValue("--detail-sidebar-width"), "840px");
});

test("invalid or differently scoped Workspace widths fall back to the current default", () => {
  window.localStorage.setItem("peval.detail-sidebar-width.v1.workspace-one", "broken");
  window.localStorage.setItem("peval.detail-sidebar-width.v1.workspace-two", "720");
  runtime.state.detailSidebar.preferredWidth = null;

  renderOpenSidebar();

  assert.equal(document.documentElement.style.getPropertyValue("--detail-sidebar-width"), "620px");
  assert.equal(window.localStorage.getItem("peval.detail-sidebar-width.v1.workspace-two"), "720");
});

test("viewport clamping preserves the Workspace width preference", () => {
  window.localStorage.setItem("peval.detail-sidebar-width.v1.workspace-one", "760");
  runtime.state.detailSidebar.preferredWidth = null;
  renderOpenSidebar();
  Object.defineProperty(document.documentElement, "clientWidth", { configurable: true, value: 700 });
  window.innerWidth = 700;

  window.dispatchEvent(new window.Event("resize"));

  assert.equal(document.documentElement.style.getPropertyValue("--detail-sidebar-width"), "360px");
  assert.equal(window.localStorage.getItem("peval.detail-sidebar-width.v1.workspace-one"), "760");
});
