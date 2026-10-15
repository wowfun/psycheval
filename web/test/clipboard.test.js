import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

test("an unavailable link leaves its accessible name unchanged", async () => {
  const browser = installBrowserDom('<button aria-label="Copy link">Copy link</button>');
  try {
    const { bindCopyButton } = await import("../../src/psycheval/assets/web/modules/clipboard.js");
    const button = document.querySelector("button");
    bindCopyButton(button, () => "", "Copy link");
    button.click();
    await Promise.resolve();
    assert.equal(button.getAttribute("aria-label"), "Copy link");
    assert.equal(button.hasAttribute("aria-busy"), false);
  } finally { browser.cleanup(); }
});
