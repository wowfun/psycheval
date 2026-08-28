import { createBrowserPlatform } from "./app/browser-platform.js";
import { RENDER_OPTIONS } from "./app/render-options.js";
import { createWorkspaceApp } from "./app/workspace-app.js";
import { setWorkspaceApp, setWorkspaceSnapshotProvider } from "./app/workspace-runtime.js";

"peval-entrypoint";

const pageLoaders = {
  home: context => import("./pages/home-page.js").then(module => module.createHomePage(context)),
  datasets: context => import("./pages/datasets-page.js").then(module => module.createDatasetsPage(context)),
  reports: context => import("./pages/reports-page.js").then(module => module.createReportsPage(context)),
  config: context => import("./pages/config-page.js").then(module => module.createConfigPage(context)),
};

const app = createWorkspaceApp({
  platform: createBrowserPlatform(window),
  initialPage: String(RENDER_OPTIONS.initial_page || "home"),
  pageLoaders,
  publishSnapshot: setWorkspaceSnapshotProvider,
});
setWorkspaceApp(app);
void import("./modules/global-shell.js")
  .then(module => module.initializeGlobalShell())
  .catch(error => globalThis.console?.error("Workspace shell failed to initialize", error));
void app.start();
