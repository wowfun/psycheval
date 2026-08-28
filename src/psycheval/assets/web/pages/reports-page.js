// @ts-check

import {
  initializeReportManagerPage,
  loadReportManagerPage,
} from "../modules/report-manager-page.js";
import { reportBindingsChanged, reportStore } from "../modules/report-store.js";

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
      if (changes.has("catalog") || changes.has("reports")) {
        await loadReportManagerPage();
      }
    },
    snapshot() {
      return {
        context: {
          page: "reports",
          report_id: reportStore.manager.selectedId || null,
          report_name: reportStore.reports.find(
            report => report.report_id === reportStore.manager.selectedId,
          )?.filename || null,
        },
        dirty: reportBindingsChanged(),
      };
    },
    destroy() {},
  };
}

export { createReportsPage };
