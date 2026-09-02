// @ts-check

import { ensureEcharts } from "../app/echarts.js";
import { RENDER_OPTIONS, render, state } from "../modules/runtime.js";
import {
  loadCatalogPage,
  loadServeWorkspace,
  selectServeDetail,
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
    async activate(changes, hash) {
      if (!initialized) {
        await ensureEcharts();
        render(EMPTY_REPORT);
        await loadServeWorkspace();
        initialized = true;
        await selectSourceFromHash(hash);
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
      await selectSourceFromHash(hash);
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

async function selectSourceFromHash(hash) {
  const sourceKey = sourceKeyFromHash(hash);
  if (sourceKey) await selectServeDetail(sourceKey);
}

function sourceKeyFromHash(hash) {
  const prefix = "#source=";
  if (!String(hash || "").startsWith(prefix)) return null;
  let sourceKey;
  try {
    sourceKey = decodeURIComponent(String(hash).slice(prefix.length));
  } catch {
    return null;
  }
  return sourceKey || null;
}

export { createHomePage, sourceKeyFromHash };
