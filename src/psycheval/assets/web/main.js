import { createBrowserPlatform } from "./app/browser-platform.js";
import { createWorkspaceApp, startWorkspacePage } from "./app/workspace-app.js";
import { RENDER_OPTIONS, render } from "./modules/runtime.js";
import { loadServeWorkspace } from "./modules/serve-catalog.js";
import { bindGlobalControls } from "./modules/serve-controls.js";
import { initializeHarborWorkbench } from "./modules/harbor-workbench.js";
import { initializeWorkspaceReportPage } from "./modules/workspace-reports.js";
import { initializeConfiguration } from "./modules/configuration.js";

"peval-entrypoint";
const platform = createBrowserPlatform(globalThis);

function renderHome() {
    render({
      schema_version: 19,
      includes: ["core"],
      trajectory: [],
      trajectory_meta: [],
      annotations: { notes: [], analysis: [], report_notes: [] },
    });
}

const app = createWorkspaceApp({
  platform,
  startPage: () => startWorkspacePage(
    String(RENDER_OPTIONS.serve_page || "home"),
    {
      renderHome,
      loadHome: loadServeWorkspace,
      bindGlobalControls,
      startDatasets: initializeHarborWorkbench,
      startReports: initializeWorkspaceReportPage,
      startConfig: initializeConfiguration,
    },
  ),
});
app.start();
