import { adminMode, esc, RENDER_OPTIONS, t } from "./shared.js";
import { serveApi } from "./http.js";
import { createSidebarController } from "./sidebar.js";
import { encodeWorkspaceLocation } from "../app/workspace-location.js";

function noteColumn(kind, onSaved = () => {}) {
  return {
    key: "note", label: "Note", valueType: "markdown",
    value: row => row.note || "", fullText: row => row.note || "",
    edit: adminMode() ? row => row.collection_revision ? ({
      value: row.note,
      async commit(_current, note) {
        const saved = await serveApi(`/api/collections/${kind}/${encodeURIComponent(row.id)}/note`, {
          method: "PUT", body: { note, revision: row.collection_revision },
        });
        Object.assign(row, { note: saved.note, collection_revision: saved.revision });
        onSaved(row);
      },
    }) : null : null,
  };
}

function reportsColumn(kind) {
  return {
    key: "reports", label: "Reports", valueType: "number", sortable: true,
    value: row => row.report_count,
    html: row => {
      const href = encodeWorkspaceLocation("reports", { state: { query: {
        [kind === "dataset" ? "datasets" : "jobs"]: [kind === "dataset" ? row.id : row.report_ref],
      } } });
      return `<a href="${esc(href)}" data-workspace-route="reports">${esc(row.report_count ?? "—")}</a>`;
    },
  };
}

/** Page-owned content with the workspace's shared sidebar lifecycle and layout. */
function createCollectionSidebar({ id, pageRoot, content, title, onClose = () => {} }) {
  let region = pageRoot.querySelector(".workspace-side-region");
  if (!region) {
    const layout = document.createElement("div"), main = document.createElement("div");
    layout.className = "workspace-content";
    main.className = "workspace-main";
    main.append(...pageRoot.childNodes);
    region = document.createElement("div");
    region.className = "workspace-side-region";
    layout.append(main, region);
    pageRoot.append(layout);
  }
  const root = document.createElement("aside");
  root.className = "detail-sidebar collection-sidebar";
  root.hidden = true;
  root.setAttribute("aria-label", title);
  root.innerHTML = `<div class="collection-sidebar-panel"><header class="detail-sidebar-head"><h2>${esc(title)}</h2><button class="action-button" type="button" data-sidebar-close>${esc(t("close", "Close"))}</button></header><div class="collection-sidebar-body"></div></div>`;
  root.querySelector(".collection-sidebar-body").append(content);
  region.append(root);
  let wanted = false, lastOpen = {};
  const controller = createSidebarController({
    id, side: "right", root, bodyClass: "detail-sidebar-open", cssVariable: "--detail-sidebar-width",
    workspaceId: RENDER_OPTIONS?.workspace_id || "default",
    minWidth: 360, minWorkspaceWidth: 360,
    defaultWidth: width => Math.min(760, Math.max(620, width * 0.44)),
    resizeLabel: t("detail_sidebar_resize", "Resize detail sidebar"),
    onRequestClose(options) {
      if (options.reason !== "navigate") wanted = false;
      onClose(options);
      return true;
    },
  });
  return {
    root,
    open(options = {}) { wanted = true; lastOpen = options; return controller.open(options); },
    resume() { if (wanted) controller.open(lastOpen); },
    close(options = {}) { wanted = false; return controller.close(options); },
    destroy() { controller.destroy(); root.remove(); },
  };
}

export { noteColumn, reportsColumn, createCollectionSidebar };
