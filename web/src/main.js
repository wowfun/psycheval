import { createBrowserPlatform } from "./app/browser-platform.js";
import { createModeRuntime } from "./app/mode-runtime.js";
import { createReportApp } from "./app/report-app.js";
import { bootstrapData, render } from "./modules/runtime.js";
import { loadServeWorkspace, loadSourceManagerPage } from "./modules/serve-catalog.js";
import { bindGlobalControls } from "./modules/serve-controls.js";
import { initializeHarborWorkbench } from "./modules/harbor-workbench.js";
import { initializeWorkspaceReportPage } from "./modules/workspace-reports.js";
import { renderWorkspaceViewRail } from "./modules/workspace-views.js";

"peval-entrypoint";
const bootstrap = bootstrapData();
const platform = createBrowserPlatform(globalThis);

function startServePage(page, report) {
  if (page === "home") {
    render(report);
    return loadServeWorkspace();
  }
  bindGlobalControls();
  if (page === "datasets") return initializeHarborWorkbench();
  if (page === "reports") return initializeWorkspaceReportPage();
  if (page === "sources") return loadSourceManagerPage();
  return undefined;
}

const modeRuntime = createModeRuntime(bootstrap, {
  renderReport: render,
  renderWorkspaceViewRail,
  loadServeWorkspace,
  startServePage,
});
createReportApp({ platform, bootstrap, modeRuntime }).start();
