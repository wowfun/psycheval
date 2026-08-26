// @ts-check

/**
 * Own the Live Workspace lifecycle.
 *
 * @param {{ platform: { destroy: () => void }, startPage: () => void | Promise<void> }} dependencies
 */
function createWorkspaceApp({ platform, startPage }) {
  let started = false;
  let destroyed = false;
  return {
    start() {
      if (started || destroyed) return undefined;
      started = true;
      return startPage();
    },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      platform.destroy();
    },
  };
}

/**
 * Dispatch one of the four Live Workspace pages.
 *
 * @param {string} page
 * @param {{
 *   renderHome: () => void,
 *   loadHome: () => void | Promise<void>,
 *   bindGlobalControls: () => void,
 *   startDatasets: () => void | Promise<void>,
 *   startReports: () => void | Promise<void>,
 *   startConfig: () => void | Promise<void>,
 * }} controllers
 */
function startWorkspacePage(page, controllers) {
  if (page === "home") {
    controllers.renderHome();
    return controllers.loadHome();
  }
  controllers.bindGlobalControls();
  if (page === "datasets") return controllers.startDatasets();
  if (page === "reports") return controllers.startReports();
  if (page === "config") return controllers.startConfig();
  return undefined;
}

export { createWorkspaceApp, startWorkspacePage };
