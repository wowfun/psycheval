import assert from "node:assert/strict";
import test from "node:test";
import echartsPackage from "echarts/package.json" with { type: "json" };

import { installBrowserDom } from "./support/browser.js";

test("ECharts stays on the workspace asset and retries after a load failure", async () => {
  const browser = installBrowserDom("");
  try {
    assert.equal(echartsPackage.version, "6.1.0");
    const { ensureEcharts } = await import("../../src/psycheval/assets/web/app/echarts.js");
    const first = ensureEcharts();
    const firstScript = document.head.querySelector("script");
    assert.equal(firstScript.getAttribute("src"), "/assets/echarts/6.1.0/echarts.min.js");
    firstScript.dispatchEvent(new window.Event("error"));
    await assert.rejects(first, /Failed to load \/assets\/echarts/);
    assert.equal(document.querySelector('script[src^="https://"]'), null);

    const second = ensureEcharts();
    const secondScript = document.head.querySelector("script");
    assert.notEqual(secondScript, firstScript);
    assert.equal(secondScript.getAttribute("src"), "/assets/echarts/6.1.0/echarts.min.js");
    secondScript.dispatchEvent(new window.Event("load"));
    await second;
  } finally {
    browser.cleanup();
  }
});
