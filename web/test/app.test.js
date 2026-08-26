import assert from "node:assert/strict";
import test from "node:test";

import {
  createWorkspaceApp,
  startWorkspacePage,
} from "../../src/psycheval/assets/web/app/workspace-app.js";

test("workspace app owns an idempotent start and destroy lifecycle", async () => {
  const calls = [];
  const app = createWorkspaceApp({
    platform: {
      destroy: () => calls.push("platform:destroy"),
    },
    startPage: () => calls.push("page:start"),
  });

  await app.start();
  await app.start();
  app.destroy();
  app.destroy();

  assert.deepEqual(calls, ["page:start", "platform:destroy"]);
});

test("workspace startup dispatches only the selected Live page", async () => {
  for (const page of ["home", "datasets", "reports", "config"]) {
    const calls = [];
    const controllers = {
      renderHome: () => calls.push("render:home"),
      loadHome: () => calls.push("load:home"),
      bindGlobalControls: () => calls.push("bind:global"),
      startDatasets: () => calls.push("start:datasets"),
      startReports: () => calls.push("start:reports"),
      startConfig: () => calls.push("start:config"),
    };

    await startWorkspacePage(page, controllers);

    assert.deepEqual(
      calls,
      page === "home" ? ["render:home", "load:home"] : ["bind:global", `start:${page}`],
    );
  }
});
