import { createBrowserPlatform } from "./app/browser-platform.js";
import { createModeRuntime } from "./app/mode-runtime.js";
import { createReportApp } from "./app/report-app.js";
import { bootstrapData, render } from "./modules/runtime.js";
import { loadServeWorkspace } from "./modules/serve-catalog.js";
import { renderWorkspaceViewRail } from "./modules/workspace-views.js";

"peval-py-entrypoint";
const bootstrap = bootstrapData();
const platform = createBrowserPlatform(globalThis);
const modeRuntime = createModeRuntime(bootstrap, {
  renderReport: render,
  renderWorkspaceViewRail,
  loadServeWorkspace,
});
createReportApp({ platform, bootstrap, modeRuntime }).start();
