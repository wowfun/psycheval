// @ts-check

import {
  activeReportSnapshot,
  initializeReportManagerPage,
  loadEvaluationReports,
  loadImportedReports,
} from "../modules/report-manager-page.js";
import { reportBindingsChanged } from "../modules/report-store.js";

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
      const requests = [];
      if (changes.has("catalog")) requests.push(loadEvaluationReports());
      if (changes.has("reports")) requests.push(loadImportedReports());
      await Promise.all(requests);
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
