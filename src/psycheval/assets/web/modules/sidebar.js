// @ts-check

const SIDEBAR_KEYBOARD_STEP = 24;
const SIDEBAR_STORAGE_VERSION = 1;

const controllers = new Map();
const activeBySide = new Map();
const openStack = [];
const resizeRegistries = new WeakMap();

function sidebarStorageKey(workspaceId, sidebarId) {
  return `peval.sidebar-width.v${SIDEBAR_STORAGE_VERSION}.${String(workspaceId || "default")}.${sidebarId}`;
}

function resolveElement(value, documentRef) {
  const resolved = typeof value === "function" ? value() : value;
  if (typeof resolved === "string") return documentRef.querySelector(resolved);
  return resolved || null;
}

function viewportWidth(documentRef, windowRef) {
  const documentWidth = Number(documentRef.documentElement?.clientWidth || 0);
  const windowWidth = Number(windowRef.innerWidth || 0);
  return documentWidth || windowWidth || 1180;
}

function moveToTop(controller) {
  const index = openStack.indexOf(controller);
  if (index >= 0) openStack.splice(index, 1);
  openStack.push(controller);
}

function removeFromStack(controller) {
  const index = openStack.indexOf(controller);
  if (index >= 0) openStack.splice(index, 1);
}

function registerResizeController(windowRef, controller) {
  let registry = resizeRegistries.get(windowRef);
  if (!registry) {
    const registered = new Set();
    const listener = () => registered.forEach(item => item.sync());
    registry = { registered, listener };
    resizeRegistries.set(windowRef, registry);
    windowRef.addEventListener("resize", listener);
  }
  registry.registered.add(controller);
}

function unregisterResizeController(windowRef, controller) {
  const registry = resizeRegistries.get(windowRef);
  if (!registry) return;
  registry.registered.delete(controller);
  if (registry.registered.size) return;
  windowRef.removeEventListener("resize", registry.listener);
  resizeRegistries.delete(windowRef);
}

function createSidebarController(options) {
  const {
    id,
    side,
    root,
    bodyClass,
    cssVariable,
    workspaceId = "default",
    minWidth = 360,
    minWorkspaceWidth = 360,
    defaultWidth,
    resizeLabel,
    onRequestClose,
    onResize = () => {},
    document: documentRef = document,
    window: windowRef = window,
  } = options;
  if (!id || !["left", "right"].includes(side)) {
    throw new Error("Sidebar id and side are required.");
  }
  if (!bodyClass || !cssVariable || typeof defaultWidth !== "function" || typeof onRequestClose !== "function") {
    throw new Error(`Sidebar ${id} is missing its interaction contract.`);
  }
  if (controllers.has(id)) throw new Error(`Sidebar controller already exists: ${id}`);

  const storageKey = sidebarStorageKey(workspaceId, id);
  let mountedRoot = null;
  let preferredWidth = null;
  let restored = false;
  let open = false;
  let opener = null;
  let openerSelector = null;
  let resizing = null;
  let destroyed = false;

  function getRoot() {
    return resolveElement(root, documentRef);
  }

  function maximumWidth() {
    return Math.max(minWidth, viewportWidth(documentRef, windowRef) - minWorkspaceWidth);
  }

  function fallbackWidth() {
    return Number(defaultWidth(viewportWidth(documentRef, windowRef)));
  }

  function clampWidth(width) {
    const numeric = Number(width);
    const fallback = fallbackWidth();
    return Math.round(Math.min(
      maximumWidth(),
      Math.max(minWidth, Number.isFinite(numeric) ? numeric : fallback),
    ));
  }

  function restoreWidth() {
    if (restored) return;
    restored = true;
    try {
      const stored = Number(windowRef.localStorage?.getItem(storageKey));
      if (Number.isFinite(stored) && stored > 0) preferredWidth = stored;
    } catch {
      // Browser storage is optional presentation state.
    }
  }

  function currentWidth() {
    restoreWidth();
    if (Number.isFinite(preferredWidth) && preferredWidth > 0) return clampWidth(preferredWidth);
    return clampWidth(fallbackWidth());
  }

  function saveWidth(width) {
    try {
      windowRef.localStorage?.setItem(storageKey, String(Math.round(width)));
    } catch {
      // Browser storage is optional presentation state.
    }
  }

  function applyWidth(width = currentWidth()) {
    const effective = clampWidth(width);
    documentRef.documentElement?.style?.setProperty(cssVariable, `${effective}px`);
    if (open && activeBySide.get(side) === controller) {
      documentRef.documentElement?.style?.setProperty(`--workspace-${side}-sidebar-width`, `${effective}px`);
    }
    const handle = getRoot()?.querySelector?.("[data-sidebar-resize]");
    if (handle) {
      handle.setAttribute("aria-valuemin", String(minWidth));
      handle.setAttribute("aria-valuemax", String(maximumWidth()));
      handle.setAttribute("aria-valuenow", String(effective));
    }
    onResize(effective);
    return effective;
  }

  function setWidth(width) {
    const next = clampWidth(width);
    preferredWidth = next;
    saveWidth(next);
    return applyWidth(next);
  }

  function ensureHandle(target) {
    let handle = target.querySelector?.("[data-sidebar-resize]");
    if (!handle) {
      handle = documentRef.createElement("div");
      handle.className = "sidebar-resize";
      handle.setAttribute("data-sidebar-resize", "");
      target.prepend(handle);
    }
    handle.setAttribute("role", "separator");
    handle.setAttribute("aria-orientation", "vertical");
    handle.setAttribute("tabindex", "0");
    handle.setAttribute("aria-label", String(resizeLabel || "Resize sidebar"));
    return handle;
  }

  function finishResize(event = null) {
    if (!resizing) return;
    if (event && resizing.pointerId !== undefined && event.pointerId !== undefined && event.pointerId !== resizing.pointerId) return;
    const { handle, pointerId, move, finish } = resizing;
    resizing = null;
    documentRef.body?.classList?.remove("sidebar-resizing");
    mountedRoot?.classList?.remove("resizing");
    try {
      handle.releasePointerCapture?.(pointerId);
    } catch {
      // Pointer capture may already be released by the browser.
    }
    documentRef.removeEventListener("pointermove", move);
    documentRef.removeEventListener("pointerup", finish);
    documentRef.removeEventListener("pointercancel", finish);
  }

  function startResize(event, handle) {
    if (event.button !== undefined && event.button !== 0) return;
    event.preventDefault();
    finishResize();
    const pointerId = event.pointerId;
    const move = moveEvent => {
      if (pointerId !== undefined && moveEvent.pointerId !== undefined && moveEvent.pointerId !== pointerId) return;
      const clientX = Number(moveEvent.clientX);
      if (!Number.isFinite(clientX)) return;
      setWidth(side === "left" ? clientX : viewportWidth(documentRef, windowRef) - clientX);
    };
    const finish = finishEvent => finishResize(finishEvent);
    resizing = { handle, pointerId, move, finish };
    documentRef.body?.classList?.add("sidebar-resizing");
    mountedRoot?.classList?.add("resizing");
    try {
      handle.setPointerCapture?.(pointerId);
    } catch {
      // Document listeners still provide a usable drag if capture is unavailable.
    }
    documentRef.addEventListener("pointermove", move);
    documentRef.addEventListener("pointerup", finish);
    documentRef.addEventListener("pointercancel", finish);
  }

  function onPointerDown(event) {
    const handle = event.target?.closest?.("[data-sidebar-resize]");
    if (!handle || !mountedRoot?.contains(handle)) return;
    startResize(event, handle);
  }

  function onKeyDown(event) {
    const handle = event.target?.closest?.("[data-sidebar-resize]");
    if (!handle || !mountedRoot?.contains(handle)) return;
    const direction = side === "left"
      ? event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0
      : event.key === "ArrowLeft" ? 1 : event.key === "ArrowRight" ? -1 : 0;
    if (!direction) return;
    event.preventDefault();
    const step = event.shiftKey ? SIDEBAR_KEYBOARD_STEP * 3 : SIDEBAR_KEYBOARD_STEP;
    setWidth(currentWidth() + direction * step);
  }

  function onClick(event) {
    const close = event.target?.closest?.("[data-sidebar-close]");
    if (!close || !mountedRoot?.contains(close)) return;
    event.preventDefault();
    requestClose({ reason: "dismiss", restoreFocus: true });
  }

  function mount() {
    const target = getRoot();
    if (!target) return null;
    if (mountedRoot !== target) {
      if (mountedRoot) {
        mountedRoot.removeEventListener("pointerdown", onPointerDown);
        mountedRoot.removeEventListener("keydown", onKeyDown);
        mountedRoot.removeEventListener("click", onClick);
      }
      mountedRoot = target;
      mountedRoot.addEventListener("pointerdown", onPointerDown);
      mountedRoot.addEventListener("keydown", onKeyDown);
      mountedRoot.addEventListener("click", onClick);
    }
    target.classList.add("resizable-sidebar");
    target.setAttribute("data-sidebar-id", id);
    target.setAttribute("data-sidebar-side", side);
    ensureHandle(target);
    return target;
  }

  function sync() {
    if (destroyed) return 0;
    const target = mount();
    return target ? applyWidth(currentWidth()) : 0;
  }

  function requestClose(closeOptions = {}) {
    const target = getRoot();
    if (!open && (!target || target.hidden)) return false;
    const result = onRequestClose(closeOptions);
    if (result === false) return false;
    if (open) close(closeOptions);
    return true;
  }

  function show(openOptions = {}) {
    if (destroyed) return false;
    const target = mount();
    if (!target) return false;
    const wasOpen = open;
    const current = activeBySide.get(side);
    if (current && current !== controller && !current.requestClose({ reason: "replaced", restoreFocus: false })) {
      return false;
    }
    if (Object.hasOwn(openOptions, "opener")) opener = openOptions.opener || null;
    if (Object.hasOwn(openOptions, "openerSelector")) openerSelector = openOptions.openerSelector || null;
    target.hidden = false;
    open = true;
    activeBySide.set(side, controller);
    if (!wasOpen) moveToTop(controller);
    documentRef.body?.classList?.add(bodyClass, `workspace-sidebar-${side}-open`);
    applyWidth(currentWidth());
    const focusTarget = resolveElement(openOptions.focusTarget, documentRef);
    if (focusTarget) windowRef.requestAnimationFrame?.(() => focusTarget?.focus?.());
    return true;
  }

  function close(closeOptions = {}) {
    const target = getRoot();
    if (!open && (!target || target.hidden)) return false;
    finishResize();
    if (target) target.hidden = true;
    open = false;
    documentRef.body?.classList?.remove(bodyClass);
    if (activeBySide.get(side) === controller) {
      activeBySide.delete(side);
      documentRef.body?.classList?.remove(`workspace-sidebar-${side}-open`);
      documentRef.documentElement?.style?.removeProperty(`--workspace-${side}-sidebar-width`);
    }
    removeFromStack(controller);
    const savedOpener = opener;
    const savedSelector = openerSelector;
    opener = null;
    openerSelector = null;
    if (closeOptions.restoreFocus !== false) {
      windowRef.requestAnimationFrame?.(() => {
        const current = savedOpener?.isConnected
          ? savedOpener
          : savedSelector ? documentRef.querySelector(savedSelector) : null;
        current?.focus?.();
      });
    }
    return true;
  }

  function destroy() {
    if (destroyed) return;
    requestClose({ reason: "destroy", restoreFocus: false });
    close({ restoreFocus: false });
    destroyed = true;
    finishResize();
    if (mountedRoot) {
      mountedRoot.removeEventListener("pointerdown", onPointerDown);
      mountedRoot.removeEventListener("keydown", onKeyDown);
      mountedRoot.removeEventListener("click", onClick);
    }
    unregisterResizeController(windowRef, controller);
    controllers.delete(id);
  }

  const controller = {
    close,
    destroy,
    open: show,
    requestClose,
    sync,
  };
  controllers.set(id, controller);
  registerResizeController(windowRef, controller);
  return { close, destroy, open: show, sync };
}

function closeTopmostSidebar(options = {}) {
  const controller = openStack.at(-1);
  return controller ? controller.requestClose({ reason: "dismiss", restoreFocus: true, ...options }) : false;
}

function closeAllSidebars(options = {}) {
  let closed = false;
  [...openStack].reverse().forEach(controller => {
    closed = controller.requestClose({ reason: "navigate", restoreFocus: false, ...options }) || closed;
  });
  return closed;
}

export {
  SIDEBAR_KEYBOARD_STEP,
  SIDEBAR_STORAGE_VERSION,
  closeAllSidebars,
  closeTopmostSidebar,
  createSidebarController,
  sidebarStorageKey,
};
