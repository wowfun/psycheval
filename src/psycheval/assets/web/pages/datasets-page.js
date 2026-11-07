// @ts-check

import {
  initializeHarborWorkbench,
  isHarborDirty,
  refreshHarborInventory,
  resumeTaskSidebar,
  workbenchState,
} from "../modules/harbor-workbench.js";

/** @param {import("../app/workspace-app.js").PageLoaderContext} _context */
function createDatasetsPage(_context) {
  let initialized = false;
  return {
    async activate(changes) {
      if (!initialized) {
        const loaded = await initializeHarborWorkbench();
        if (loaded === null) throw new Error("Dataset inventory is stale");
        initialized = true;
        return;
      }
      if (changes.has("dataset-registry") || changes.has("tasks") || changes.has("reports") || changes.has("collections")) {
        const loaded = await refreshHarborInventory({
          skipGuard: true,
          skipTaskReload: isHarborDirty(),
        });
        if (loaded === null) throw new Error("Dataset inventory is stale");
      }
      resumeTaskSidebar();
    },
    snapshot() {
      return {
        context: {
          page: "datasets",
          dataset_id: workbenchState.datasetId || null,
          task: workbenchState.taskName || null,
          file: null,
        },
        dirty: isHarborDirty(),
      };
    },
    destroy() {},
  };
}

export { createDatasetsPage };
