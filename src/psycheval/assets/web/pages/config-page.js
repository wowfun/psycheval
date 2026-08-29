// @ts-check

import {
  harborConfigState,
  initializeConfiguration,
  promptConfigState,
  refreshHarborConfig,
} from "../modules/configuration.js";

/** @param {import("../app/workspace-app.js").PageLoaderContext} _context */
function createConfigPage(_context) {
  let initialized = false;
  return {
    async activate(changes) {
      if (!initialized) {
        const loaded = await initializeConfiguration();
        if (!loaded) throw new Error("Configuration is stale");
        initialized = true;
        return;
      }
      if (
        changes.has("dataset-registry") ||
        changes.has("assistant-config") ||
        changes.has("prompt-assets")
      ) {
        const loaded = await refreshHarborConfig();
        if (!loaded) throw new Error("Configuration is stale");
      }
    },
    snapshot() {
      return {
        context: {
          page: "config",
          prompt_id: promptConfigState.selectedId || null,
          dataset_count: harborConfigState.snapshot?.datasets?.length || 0,
        },
        dirty: Boolean(promptConfigState.dirty),
      };
    },
    destroy() {},
  };
}

export { createConfigPage };
