// @ts-check

import {
  activeReportSnapshot,
  initializeReportManagerPage,
  loadReportManagerPage,
} from "../modules/report-manager-page.js";
import { reportBindingsChanged } from "../modules/report-library-store.js";

/** @param {import("../app/workspace-app.js").PageLoaderContext} _context */
function createReportsPage(_context) {
  let initialized = false;
  return {
    async activate(changes) {
      if (!initialized) {
        await initializeReportManagerPage();
        initialized = true;
        return;
      }
      if (["catalog", "reports", "dataset-registry", "jobs"].some(domain => changes.has(domain))) {
        await loadReportManagerPage();
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
