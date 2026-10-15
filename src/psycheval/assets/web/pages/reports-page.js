// @ts-check

import {
  activeReportSnapshot,
  initializeReportManagerPage,
  loadReportManagerPage,
  captureReportLocation,
  restoreReportLocation,
  openReportRef,
} from "../modules/report-manager-page.js";
import { reportBindingsChanged } from "../modules/report-library-store.js";

/** @param {import("../app/workspace-app.js").PageLoaderContext} _context */
function createReportsPage(_context) {
  let initialized = false;
  let pendingLocation = null;
  return {
    captureLocation: captureReportLocation,
    restoreLocation(location, signal) {
      pendingLocation = location;
      restoreReportLocation(location);
    },
    async activate(changes, _hash, signal) {
      if (pendingLocation) {
        const location = pendingLocation;
        pendingLocation = null;
        await initializeReportManagerPage({ signal });
        if (signal.aborted) return;
        initialized = true;
        const current = /** @type {{report?: string}} */ (captureReportLocation().object);
        if (current.report !== location.object.report) return;
        if (location.object.report) await openReportRef(location.object.report, { tab: location.object.tab || "preview", signal });
        return;
      }
      if (!initialized) {
        await initializeReportManagerPage({ signal });
        if (signal.aborted) return;
        initialized = true;
        return;
      }
      if (["catalog", "reports", "dataset-registry", "jobs"].some(domain => changes.has(domain))) {
        await loadReportManagerPage({ signal });
      }
    },
    snapshot() {
      const active = activeReportSnapshot();
      return {
        context: {
          page: "reports",
          report_ref: active.report_ref,
          report_name: active.report_name,
        },
        dirty: reportBindingsChanged(),
      };
    },
    destroy() {},
  };
}

export { createReportsPage };
