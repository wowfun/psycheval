// @ts-check

/** @typedef {import("./report-app.js").BrowserBootstrap} BrowserBootstrap */

/**
 * @param {BrowserBootstrap} bootstrap
 * @param {{ renderReport: (report: Record<string, unknown>) => void, renderWorkspaceViewRail: () => void }} effects
 */
function createModeRuntime(bootstrap, effects) {
  const rawMode = String(bootstrap.renderOptions.mode || "report");
  const kind = rawMode === "serve"
    ? "serve"
    : rawMode === "workspace_snapshot"
      ? "workspace_snapshot"
      : "report";
  return {
    kind,
    start() {
      effects.renderReport(bootstrap.report);
      if (kind === "workspace_snapshot") effects.renderWorkspaceViewRail();
    },
    destroy() {},
  };
}

export { createModeRuntime };
