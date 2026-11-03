import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";
import { openModalSurface, closeModalSurface } from "../../src/psycheval/assets/web/modules/modal-surfaces.js";

const browser = installBrowserDom('<script id="peval-i18n" type="application/json">{"acp_reference_source":"来源"}</script><aside data-acp-drawer></aside>');
const { chooseReferences } = await import("../../src/psycheval/assets/web/modules/acp-references.js");
test.after(() => browser.cleanup());
const source = {id: "source", label: "Source", label_key: "source", text: "source_ref: runs/a\nevidence_path: /tmp/a", selected: true};

test("reference text is a description outside its localized checkbox label", async () => {
  const signal = new AbortController();
  const pending = chooseReferences([source], signal.signal);
  const root = document.querySelector(".acp-reference-picker");
  const preview = root.querySelector("pre");
  const checkbox = root.querySelector("input");
  try {
    assert.equal(preview.closest("label"), null);
    assert.equal(checkbox.getAttribute("aria-describedby"), preview.id);
    assert.equal(checkbox.labels[0].textContent.trim(), "来源");
    preview.click();
    assert.equal(checkbox.checked, true);
    root.querySelector('button[type="submit"]').click();
    assert.equal(await pending, source.text);
  } finally { signal.abort(); }
});

test("aborting a suspended picker settles its action and cannot revive it", async () => {
  const signal = new AbortController();
  const pending = chooseReferences([source], signal.signal);
  const root = document.querySelector(".acp-reference-picker");
  const newer = document.createElement("div");
  newer.setAttribute("aria-modal", "true");
  newer.hidden = true;
  document.body.append(newer);
  openModalSurface(newer);
  assert.equal(root.hidden, true);
  signal.abort();
  try {
    assert.equal(root.isConnected, false);
    assert.equal(await pending, undefined);
  } finally { closeModalSurface(newer); newer.remove(); root.remove(); }
  assert.equal(document.querySelector(".acp-reference-picker"), null);
});

test("insertion requires a usable checked reference and unavailable lists explain themselves", async () => {
  for (const items of [[source], [{id:"missing",label:"Missing",text:"",reason:"missing path"}], []]) {
    const signal = new AbortController();
    const pending = chooseReferences(items, signal.signal);
    const root = document.querySelector(".acp-reference-picker");
    try {
      const submit = root.querySelector('button[type="submit"]');
      const checkbox = root.querySelector("input");
      assert.equal(submit.disabled, !items.some(item => item.text));
      if (items[0] === source) {
        checkbox.click();
        assert.equal(submit.disabled, true);
        checkbox.click();
        assert.equal(submit.disabled, false);
      } else assert.ok(root.querySelector('[role="status"]')?.textContent);
    } finally { signal.abort(); }
    assert.equal(await pending, undefined);
  }
});
