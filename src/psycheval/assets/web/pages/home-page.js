// @ts-check

import { ensureEcharts } from "../app/echarts.js";
import { RENDER_OPTIONS, render, state } from "../modules/runtime.js";
import {
  loadCatalogPage,
  loadServeWorkspace,
  selectServeDetail,
} from "../modules/serve-catalog.js";
import { closeWorkspaceReportReader, openWorkspaceReportRef, refreshWorkspaceReports } from "../modules/workspace-reports.js";
import { captureHomeLocation, restoreHomeLocation } from "../modules/home-location.js";
import { setServeStatus } from "../modules/serve-effects.js";
import { notesDraftChanged } from "../modules/analysis-notes.js";
import { disposeLeaderboardRadar } from "../modules/leaderboard-radar.js";

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
  let pendingLocation = null;
  return {
    captureLocation: captureHomeLocation,
    restoreLocation(location, signal) {
      pendingLocation = location;
      restoreHomeLocation(location);
    },
    async activate(changes, _hash, signal) {
      if (pendingLocation) {
        const location = pendingLocation;
        pendingLocation = null;
        await ensureEcharts();
        if (signal.aborted) return;
        render(EMPTY_REPORT);
        const results = await Promise.all([loadCatalogPage({}, { force: true, signal, skipDetail: Boolean(location.object.source || location.object.report) }), refreshWorkspaceReports({ signal })]);
        if (signal.aborted) return;
        if (results.some(result => result === null)) throw new Error("Workspace data is stale");
        initialized = true;
        if (state.homeLocationTarget.source !== location.object.source || state.homeLocationTarget.report !== location.object.report) return;
        try {
          if (location.object.source) await selectServeDetail(location.object.source, {
            openSidebar: true, trajectoryId: location.object.trajectory, stepId: location.object.step,
            tab: location.object.tab, signal, throwOnError: true,
          });
          else if (location.object.report) await openWorkspaceReportRef(location.object.report, { signal });
        } catch (error) {
          if (!signal.aborted) setServeStatus(error.message || String(error), true);
        }
        return;
      }
      if (!initialized) {
        await ensureEcharts();
        if (signal.aborted) return;
        render(EMPTY_REPORT);
        await loadServeWorkspace({ signal });
        if (signal.aborted) return;
        initialized = true;
        return;
      }
      const requests = [];
      if (changes.has("catalog")) {
        state.serveReportCache = {};
        state.selectedArtifactRevision = null;
      }
      if (changes.has("catalog") || changes.has("dataset-registry")) {
        requests.push(loadCatalogPage({}, { force: true, signal }));
      }
      if (changes.has("reports")) requests.push(refreshWorkspaceReports({ signal }));
      if (changes.has("tasks")) {
        state.serveReportCache = {};
        state.selectedArtifactRevision = null;
      }
      const results = await Promise.all(requests);
      if (signal.aborted) return;
      if (results.some(result => result === null)) throw new Error("Workspace data is stale");
      if (changes.has("reports") && state.homeLocationTarget.report && !state.reportReader.openRef) {
        try { await openWorkspaceReportRef(state.homeLocationTarget.report, { locationKind: "replace", signal }); }
        catch (error) {
          if (error.status === 404) closeWorkspaceReportReader({ restoreFocus: false, locationKind: "replace" });
          else throw error;
        }
      }
    },
    snapshot() {
      return {
        context: {
          page: "home",
          source_key: state.selectedSourceKey || null,
          trial_key: state.selectedTrial || null,
          step_id: state.selectedStep?.stepId || null,
        },
        dirty: notesDraftChanged(),
      };
    },
    destroy() { disposeLeaderboardRadar(); },
  };
}

export { createHomePage };
