const SUBMENU_DETAILS_SELECTOR = ".export-menu,.filter-control,.column-control,.toolbar-menu";
const OPEN_SUBMENU_DETAILS_SELECTOR = SUBMENU_DETAILS_SELECTOR.split(",").map(selector => `${selector}[open]`).join(",");
const boundDocuments = new WeakSet();
const boundMenus = new WeakSet();

function positionToolbarMenu(menu) {
  const panel = menu.querySelector(".toolbar-menu-panel");
  if (!panel) return;
  panel.style.removeProperty("top"); panel.style.removeProperty("max-height");
  if (!menu.open || innerWidth > 600) return;
  const rect = menu.querySelector("summary").getBoundingClientRect();
  const below = innerHeight - rect.bottom - 14, above = rect.top - 14;
  const upwards = below < 180 && above > below;
  panel.style.maxHeight = `${Math.max(40, upwards ? above : below)}px`;
  panel.style.top = `${Math.max(8, upwards ? rect.top - panel.getBoundingClientRect().height - 6 : rect.bottom + 6)}px`;
}

function closeOpenSubmenus(except = null) {
  document.querySelectorAll(OPEN_SUBMENU_DETAILS_SELECTOR).forEach(details => {
    if (details !== except) details.open = false;
  });
}

function bindToolbarMenus(root) {
  const doc = root.ownerDocument || root;
  if (!boundDocuments.has(doc)) {
    boundDocuments.add(doc);
    doc.addEventListener("click", event => closeOpenSubmenus(event.target.closest?.(SUBMENU_DETAILS_SELECTOR) || null), true);
    let frame = null;
    const reposition = () => {
      if (frame !== null) return;
      frame = requestAnimationFrame(() => { frame = null; doc.querySelectorAll(".toolbar-menu[open]").forEach(positionToolbarMenu); });
    };
    doc.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);
  }
  root.querySelectorAll(SUBMENU_DETAILS_SELECTOR).forEach(menu => {
    if (boundMenus.has(menu)) return;
    boundMenus.add(menu);
    if (menu.matches(".toolbar-menu")) menu.addEventListener("toggle", () => positionToolbarMenu(menu));
    if (menu.matches(".toolbar-menu,.export-menu")) menu.addEventListener("keydown", event => {
      if (event.key !== "Escape") return;
      event.preventDefault(); event.stopPropagation();
      menu.open = false; menu.querySelector("summary").focus({ preventScroll: true });
    });
    if (menu.matches(".toolbar-menu")) menu.addEventListener("click", event => {
      if (!event.target.closest(".toolbar-menu-panel button:not(:disabled)")) return;
      menu.open = false; menu.querySelector("summary").focus({ preventScroll: true });
    }, true);
  });
}

export { bindToolbarMenus, closeOpenSubmenus, SUBMENU_DETAILS_SELECTOR, OPEN_SUBMENU_DETAILS_SELECTOR };
