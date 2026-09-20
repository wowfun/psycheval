import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";
import { response, target, pageOf, deferred, tick } from "./support/report-library.js";

test("target picker retains selected objects across pages and ignores stale searches and disposed selections", async () => {
  const pages = new Map([[1, deferred()], [2, deferred()]]);
  const browser = installBrowserDom('<div id="picker"></div>', { fetch: path => pages.get(Number(new URL(path, "http://localhost").searchParams.get("page"))).promise });
  try {
    const { createReportTargetPicker } = await import("../../src/psycheval/assets/web/modules/report-target-picker.js");
    const { bindingId } = await import("../../src/psycheval/assets/web/modules/report-library-store.js");
    const selected = new Map();
    const picker = createReportTargetPicker(document.querySelector("#picker"), {
      kind: "session", selected: () => selected,
      onChange(item, checked) { if (checked) selected.set(bindingId(item), item); else selected.delete(bindingId(item)); },
    });
    const initial = picker.load();
    pages.get(1).resolve(response(pageOf([target("session", "first")], 1, 100)));
    await initial;
    document.querySelector("[data-target-key]").click();
    const next = picker.load(2);
    pages.get(2).resolve(response(pageOf([target("session", "second")], 2, 100)));
    await next;
    assert.equal(document.querySelector("[data-target-selected]").textContent, "session first ×");
    document.querySelector("[data-target-key]").click();
    assert.equal(selected.size, 2);
    pages.set(1, deferred());
    const stale = picker.load(1);
    const search = document.querySelector("[data-target-search]");
    search.value = "new query";
    search.dispatchEvent(new window.Event("input"));
    pages.get(1).resolve(response(pageOf([target("session", "stale")])));
    await stale;
    assert.equal(document.querySelector('[data-target-key="stale"]'), null);
    picker.destroy();
    await tick();
    assert.equal(selected.size, 2);
  } finally { browser.cleanup(); }
});
