import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom, pointerClick } from "./support/browser.js";
import { closeModalSurface, openModalSurface } from "../../src/psycheval/assets/web/modules/modal-surfaces.js";

test("a reference picker keeps its ancestor open and traps focus inside the child", () => {
  const browser = fixture();
  try {
    const { root } = browser;
    openModalSurface(root);
    const child = document.createElement("div");
    child.setAttribute("aria-modal", "true");
    child.hidden = true;
    child.innerHTML = '<button>First</button><button>Last</button>';
    root.append(child);
    const [first, last] = child.querySelectorAll("button");
    openModalSurface(child, {opener: root.querySelector("input"), focusTarget: first});
    assert.equal(root.hidden, false);
    last.focus();
    last.dispatchEvent(new window.KeyboardEvent("keydown", {key:"Tab", bubbles:true, cancelable:true}));
    assert.equal(document.activeElement, first);
    closeModalSurface(child);
    assert.equal(root.hidden, false);
    assert.equal(root.querySelector("input").value, "draft");
  } finally { browser.cleanup(); }
});

function pointer(target, type, options = {}) {
  target.dispatchEvent(new window.PointerEvent(type, {
    bubbles: true, cancelable: true, pointerId: 1, pointerType: "mouse", isPrimary: true, button: 0, ...options,
  }));
}

function fixture() {
  const browser = installBrowserDom('<button id="opener">Open</button><div id="modal" role="dialog" aria-modal="true" hidden><section><input value="draft"></section></div>');
  const root = document.querySelector("#modal");
  const pane = root.querySelector("section");
  const opener = document.querySelector("#opener");
  opener.focus();
  openModalSurface(root, { opener, focusTarget: root.querySelector("input") });
  return { ...browser, root, pane, opener };
}

for (const [start, end, closed] of [
  ["pane", "root", false], ["root", "pane", false], ["pane", "pane", false], ["root", "root", true],
]) test(`a gesture from ${start} to ${end} ${closed ? "dismisses" : "preserves"} the dialog`, () => {
  const browser = fixture();
  try {
    pointer(browser[start], "pointerdown");
    pointer(browser[end], "pointerup");
    // Cross-element gestures can produce a click targeted at their common overlay.
    pointer(browser.root, "click");
    assert.equal(browser.root.hidden, closed);
    assert.equal(browser.root.querySelector("input").value, "draft");
    if (closed) assert.equal(document.activeElement, browser.opener);
  } finally { browser.cleanup(); }
});

for (const kind of ["secondary button", "non-primary pointer", "cancelled", "mismatched release", "mismatched click", "no release", "prevented click"]) {
  test(`${kind} does not dismiss the dialog or poison the next click`, () => {
    const browser = fixture();
    try {
      const { root } = browser;
      const options = kind === "secondary button" ? { button: 2 } : kind === "non-primary pointer" ? { isPrimary: false } : {};
      pointer(root, "pointerdown", options);
      if (kind === "cancelled") pointer(root, "pointercancel");
      if (kind !== "no release") pointer(root, "pointerup", { ...options, ...(kind === "mismatched release" ? { pointerId: 2 } : {}) });
      const prevent = event => event.preventDefault();
      if (kind === "prevented click") root.addEventListener("click", prevent, { capture: true, once: true });
      pointer(root, "click", { ...options, ...(kind === "mismatched click" ? { pointerId: 2 } : {}) });
      assert.equal(root.hidden, false);
      pointerClick(root);
      assert.equal(root.hidden, true);
    } finally { browser.cleanup(); }
  });
}

test("reopening resets gestures and uses the latest close request once per click", () => {
  const browser = fixture();
  try {
    const { root } = browser;
    let previousRequests = 0, currentRequests = 0;
    openModalSurface(root, { onRequestClose: () => { previousRequests++; } });
    pointer(root, "pointerdown"); pointer(root, "pointerup");
    openModalSurface(root, { onRequestClose: () => { currentRequests++; } });
    pointer(root, "click");
    assert.equal(currentRequests, 0);
    pointerClick(root);
    pointer(root, "click");
    assert.equal(previousRequests, 0);
    assert.equal(currentRequests, 1);
    assert.equal(root.hidden, false);
  } finally { browser.cleanup(); }
});

for (const pointerType of ["touch", "pen"]) test(`${pointerType} capture cannot turn a release inside the pane into a backdrop click`, () => {
  const browser = fixture();
  try {
    const { root, pane } = browser;
    // Direct-manipulation pointers can keep targeting the pressed overlay after moving inside.
    document.elementFromPoint = () => pane;
    for (const type of ["pointerdown", "pointerup", "click"]) pointer(root, type, { pointerType });
    assert.equal(root.hidden, false);
    document.elementFromPoint = () => root;
    for (const type of ["pointerdown", "pointerup", "click"]) pointer(root, type, { pointerType });
    assert.equal(root.hidden, true);
  } finally { browser.cleanup(); }
});

for (const pointerType of ["touch", "pen"]) test(`${pointerType} releases without a valid backdrop gesture skip hit testing`, () => {
  const browser = fixture();
  try {
    const { root, pane } = browser;
    let hitTests = 0;
    document.elementFromPoint = () => { hitTests++; return root; };
    for (const kind of ["no press", "pane press", "cancelled", "mismatched pointer", "non-primary release", "secondary release", "hidden"]) {
      openModalSurface(root);
      const options = { pointerType };
      if (kind !== "no press") pointer(kind === "pane press" ? pane : root, "pointerdown", options);
      if (kind === "cancelled") pointer(root, "pointercancel", options);
      if (kind === "hidden") root.hidden = true;
      pointer(root, "pointerup", {
        ...options,
        ...(kind === "mismatched pointer" ? { pointerId: 2 } : {}),
        ...(kind === "non-primary release" ? { isPrimary: false } : {}),
        ...(kind === "secondary release" ? { button: 2 } : {}),
      });
      pointer(root, "click", options);
      assert.equal(hitTests, 0, kind);
      if (kind !== "hidden") assert.equal(root.hidden, false, kind);
    }
  } finally { browser.cleanup(); }
});

test("a second pointer cancels the pending primary gesture without poisoning the next click", () => {
  const browser = fixture();
  try {
    const { root } = browser;
    pointer(root, "pointerdown", { pointerType: "touch" });
    pointer(root, "pointerdown", { pointerType: "touch", pointerId: 2, isPrimary: false });
    pointer(root, "pointerup", { pointerType: "touch" });
    pointer(root, "click", { pointerType: "touch" });
    assert.equal(root.hidden, false);
    pointerClick(root);
    assert.equal(root.hidden, true);
  } finally { browser.cleanup(); }
});

test("closing clears the gesture and discards the old close request", () => {
  const browser = fixture();
  try {
    const { root } = browser;
    let requests = 0;
    openModalSurface(root, { onRequestClose: () => { requests++; } });
    pointer(root, "pointerdown"); pointer(root, "pointerup");
    closeModalSurface(root);
    pointer(root, "click");
    openModalSurface(root);
    pointer(root, "click");
    assert.equal(root.hidden, false);
    pointerClick(root);
    assert.equal(root.hidden, true);
    assert.equal(requests, 0);
  } finally { browser.cleanup(); }
});

test("suspending a dialog clears its pending gesture and preserves its close request and focus", () => {
  const browser = fixture();
  try {
    const { root } = browser;
    root.classList.add("action-form-overlay");
    const input = root.querySelector("input");
    let requests = 0;
    openModalSurface(root, { focusTarget: input, onRequestClose: () => { requests++; closeModalSurface(root); } });
    pointer(root, "pointerdown"); pointer(root, "pointerup");
    const nested = document.createElement("div");
    nested.hidden = true;
    nested.setAttribute("aria-modal", "true");
    document.body.append(nested);
    openModalSurface(nested);
    assert.equal(root.hidden, true);
    closeModalSurface(nested);
    assert.equal(root.hidden, false);
    assert.equal(document.activeElement, input);
    pointer(root, "click");
    assert.equal(root.hidden, false);
    assert.equal(input.value, "draft");
    pointerClick(root);
    assert.equal(requests, 1);
    assert.equal(root.hidden, true);
  } finally { browser.cleanup(); }
});
