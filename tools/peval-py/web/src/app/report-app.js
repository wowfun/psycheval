// @ts-check

/**
 * @typedef {object} BrowserPlatform
 * @property {Document} document
 * @property {Window & typeof globalThis} window
 * @property {() => void} destroy
 */

/**
 * @typedef {object} BrowserBootstrap
 * @property {Record<string, unknown>} report
 * @property {Record<string, unknown>} renderOptions
 * @property {Record<string, unknown> | null} workspaceSnapshot
 */

/**
 * @typedef {object} ModeRuntime
 * @property {"report" | "serve" | "workspace_snapshot"} kind
 * @property {() => void | Promise<void>} start
 * @property {() => void} destroy
 */

/**
 * Create the browser application's lifecycle seam.
 *
 * @param {{ platform: BrowserPlatform, bootstrap: BrowserBootstrap, modeRuntime: ModeRuntime }} dependencies
 */
function createReportApp({ platform, bootstrap, modeRuntime }) {
  let started = false;
  let destroyed = false;
  return {
    bootstrap,
    mode: modeRuntime.kind,
    start() {
      if (started || destroyed) return undefined;
      started = true;
      return modeRuntime.start();
    },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      modeRuntime.destroy();
      platform.destroy();
    },
  };
}

export { createReportApp };
