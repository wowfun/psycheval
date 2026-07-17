import assert from "node:assert/strict";
import test from "node:test";

import { createReportApp } from "../src/app/report-app.js";
import { createModeRuntime } from "../src/app/mode-runtime.js";

test("report app owns an idempotent start and destroy lifecycle", async () => {
  const calls = [];
  const app = createReportApp({
    platform: {
      document: {},
      window: globalThis,
      destroy: () => calls.push("platform:destroy"),
    },
    bootstrap: {
      report: {},
      renderOptions: { mode: "report" },
      workspaceSnapshot: null,
    },
    modeRuntime: {
      kind: "report",
      start: () => calls.push("mode:start"),
      destroy: () => calls.push("mode:destroy"),
    },
  });

  await app.start();
  await app.start();
  app.destroy();
  app.destroy();

  assert.deepEqual(calls, ["mode:start", "mode:destroy", "platform:destroy"]);
});

test("mode runtime selects one explicit browser mode", () => {
  const calls = [];
  const runtime = createModeRuntime({
    report: { rows: [] },
    renderOptions: { mode: "workspace_snapshot" },
    workspaceSnapshot: {},
  }, {
    renderReport: report => calls.push(["render", report]),
    renderWorkspaceViewRail: () => calls.push(["rail"]),
  });

  runtime.start();

  assert.equal(runtime.kind, "workspace_snapshot");
  assert.deepEqual(calls, [["render", { rows: [] }], ["rail"]]);
});
