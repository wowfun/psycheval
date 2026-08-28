// @ts-check

import { ensureEcharts } from "../app/echarts.js";
import { RENDER_OPTIONS, render, state } from "../modules/runtime.js";
import {
  loadCatalogPage,
  loadServeWorkspace,
} from "../modules/serve-catalog.js";
import { refreshWorkspaceReports } from "../modules/workspace-reports.js";

const EMPTY_REPORT = Object.freeze({
  schema_version: 19,
  includes: ["core"],
  trajectory: [],
  trajectory_meta: [],
  annotations: { notes: [], analysis: [], report_notes: [] },
});

/** @param {import("../app/workspace-app.js").PageLoaderContext} _context */
function createHomePage(_context) {
  let initialized = false;
  return {
    async activate(changes) {
      if (!initialized) {
        await ensureEcharts();
        render(EMPTY_REPORT);
        await loadServeWorkspace();
        initialized = true;
        return;
      }
      const requests = [];
      if (changes.has("catalog") || changes.has("dataset-registry")) {
        requests.push(loadCatalogPage());
      }
      if (changes.has("reports")) requests.push(refreshWorkspaceReports());
      if (changes.has("tasks")) {
        state.serveReportCache = {};
        state.selectedArtifactRevision = null;
      }
      const results = await Promise.all(requests);
      if (results.some(result => result === null)) throw new Error("Workspace data is stale");
    },
    snapshot() {
      return {
        context: {
          page: "home",
          source_key: state.selectedSourceKey || null,
          trial_key: state.selectedTrial || null,
          step_id: state.selectedStep?.stepId || null,
        },
        dirty: false,
      };
    },
    destroy() {},
  };
}

export { createHomePage };
