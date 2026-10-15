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
  assert.deepEqual(domains("/api/report-library/package:report-1/bindings", "PUT", {}), ["reports"]);
  assert.deepEqual(domains("/api/report-library/analysis%3Areport-1/state", "PUT", { archived: true }), ["reports"]);
  assert.deepEqual(domains("/api/report-library/package%3Areport-1", "DELETE", undefined), ["reports"]);
  assert.deepEqual(domains("/api/report-library/analysis%3Areport-1", "DELETE", undefined), ["reports"]);
  assert.deepEqual(domains("/api/harbor/datasets", "POST", {}), ["dataset-registry"]);
  assert.deepEqual(
    domains("/api/harbor/datasets/demo/tasks/task/files/instructions.md", "PUT", {}),
    ["tasks"],
  );
  assert.deepEqual(
    domains("/api/config", "PATCH", { acp_agents: [] }),
    ["assistant-config"],
  );
  assert.deepEqual(domains("/api/prompts/task-audit", "PUT", {}), ["prompt-assets"]);
  assert.deepEqual(domains("/api/reports", "GET", undefined), []);
  assert.deepEqual(domains("/api/source-key-resolutions", "POST", { items: [] }), []);
});

test("server declarations invalidate canonical detail on successful and committed failed deletions", async () => {
  const { subscribeWorkspaceInvalidation } = await import("../../src/psycheval/assets/web/app/workspace-runtime.js");
  const changes = [];
  const unsubscribe = subscribeWorkspaceInvalidation(domains => changes.push([...domains]));
  const previous = globalThis.fetch;
  try {
    for (const status of [204, 500]) {
      globalThis.fetch = async () => new Response(status === 500 ? '{"committed":true,"detail":"cleanup failed"}' : null, { status, headers: { "X-Peval-Invalidations": "reports,catalog" } });
      const request = serveApi("/api/report-library/opaque-identity", { method: "DELETE" });
      if (status === 500) await assert.rejects(request, /cleanup failed/); else await request;
    }
    assert.deepEqual(changes, [["reports"], ["catalog"], ["reports"], ["catalog"]]);
  } finally { unsubscribe(); globalThis.fetch = previous; }
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
