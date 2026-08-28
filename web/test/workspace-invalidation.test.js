import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{}</script>
`);
const { requestInvalidations, serveApi, serveEtag } = await import("../../src/psycheval/assets/web/modules/http.js");

test.after(() => browser.cleanup());

test("successful mutations map to stable Workspace invalidation domains", () => {
  const domains = (path, method, body) => [...requestInvalidations(path, method, body)];
  assert.deepEqual(domains("/api/sources/source-1", "PATCH", {}), ["catalog"]);
  assert.deepEqual(domains("/api/reports/report-1/bindings", "PUT", {}), ["reports"]);
  assert.deepEqual(domains("/api/harbor/datasets", "POST", {}), ["dataset-registry"]);
  assert.deepEqual(
    domains("/api/harbor/datasets/demo/tasks/task/files/instructions.md", "PUT", {}),
    ["tasks"],
  );
  assert.deepEqual(
    domains("/api/config", "PATCH", { acp_agents: [] }),
    ["assistant-config"],
  );
  assert.deepEqual(domains("/api/reports", "GET", undefined), []);
  assert.deepEqual(domains("/api/source-key-resolutions", "POST", { items: [] }), []);
});

test("failed responses cannot replace a successful cached ETag", async () => {
  const previousFetch = globalThis.fetch;
  const requests = [];
  let responseIndex = 0;
  const responses = [
    new Response("{}", { status: 200, headers: { ETag: '"config-good"' } }),
    new Response('{"detail":"stale"}', {
      status: 412,
      headers: { "Content-Type": "application/problem+json", ETag: '"config-current"' },
    }),
    new Response("{}", { status: 200, headers: { ETag: '"config-next"' } }),
  ];
  globalThis.fetch = async (path, options = {}) => {
    requests.push({ path: String(path), options });
    return responses[responseIndex++];
  };
  try {
    await serveApi("/api/config");
    await assert.rejects(
      serveApi("/api/config", { method: "PATCH", body: {}, ifMatch: true }),
      error => error?.status === 412,
    );
    assert.equal(serveEtag("/api/config"), '"config-good"');
    await serveApi("/api/config", { method: "PATCH", body: {}, ifMatch: true });
    assert.equal(requests[2].options.headers["If-Match"], '"config-good"');
  } finally {
    globalThis.fetch = previousFetch;
  }
});
