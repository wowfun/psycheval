// @ts-check

import { RENDER_OPTIONS, t } from "./shared.js";
import { createSidebarController } from "./sidebar.js";

const adapters = new Map();
let activeAdapter = null;
let reportController = null;

function reportSidebarController() {
  if (!reportController) {
    reportController = createSidebarController({
      id: "report-reader",
      side: "left",
      root: () => document.getElementById("workspace-report-reader"),
      bodyClass: "report-reader-open",
      cssVariable: "--report-reader-width",
      workspaceId: RENDER_OPTIONS?.workspace_id || "default",
      minWidth: 360,
      minWorkspaceWidth: 360,
      defaultWidth: width => Math.min(720, width * 0.44),
      resizeLabel: t("report_resize", "Resize report reader"),
      onRequestClose: options => activeAdapter?.requestClose(options) ?? false,
      onResize: width => activeAdapter?.resize(width),
    });
  }
  return reportController;
}

function createReportSidebarAdapter(options) {
  const { ownerId, onRequestClose, onResize = () => {} } = options;
  if (!ownerId || typeof onRequestClose !== "function") {
    throw new Error("Report sidebar owner and close callback are required.");
  }
  if (adapters.has(ownerId)) throw new Error(`Report sidebar owner already exists: ${ownerId}`);
  let destroyed = false;

  function requestClose(closeOptions = {}) {
    if (destroyed || activeAdapter !== adapter) return false;
    const result = onRequestClose(closeOptions);
    if (result !== false && activeAdapter === adapter) activeAdapter = null;
    return result;
  }

  function open(openOptions = {}) {
    if (destroyed) return false;
    const { render, ...controllerOptions } = openOptions;
    if (activeAdapter && activeAdapter !== adapter) {
      const replaced = activeAdapter.requestClose({ reason: "replaced", restoreFocus: false });
      if (!replaced) return false;
    }
    if (typeof render === "function") render();
    activeAdapter = adapter;
    const opened = reportSidebarController().open(controllerOptions);
    if (!opened && activeAdapter === adapter) activeAdapter = null;
    return opened;
  }

  function close(closeOptions = {}) {
    if (activeAdapter !== adapter) return false;
    const closed = reportSidebarController().close(closeOptions);
    activeAdapter = null;
    return closed;
  }

  function sync() {
    return activeAdapter === adapter ? reportSidebarController().sync() : 0;
  }

  function destroy() {
    if (destroyed) return;
    if (activeAdapter === adapter) {
      requestClose({ reason: "destroy", restoreFocus: false });
      if (activeAdapter === adapter) close({ restoreFocus: false });
    }
    destroyed = true;
    adapters.delete(ownerId);
    if (!adapters.size && reportController) {
      reportController.destroy();
      reportController = null;
      activeAdapter = null;
    }
  }

  const adapter = {
    close,
    destroy,
    open,
    requestClose,
    resize: onResize,
    sync,
  };
  adapters.set(ownerId, adapter);
  return { close, destroy, open, sync };
}

export { createReportSidebarAdapter };
