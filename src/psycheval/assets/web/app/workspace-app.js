// @ts-check

const PAGE_PATHS = Object.freeze({
  home: "/",
  datasets: "/datasets",
  reports: "/reports",
  config: "/config",
});

const INVALIDATION_PAGES = Object.freeze({
  catalog: ["home", "reports"],
  reports: ["home", "reports"],
  "dataset-registry": ["home", "datasets", "config"],
  tasks: ["home", "datasets"],
  "assistant-config": ["config"],
});

/** @typedef {keyof typeof PAGE_PATHS} WorkspacePage */
/** @typedef {keyof typeof INVALIDATION_PAGES} InvalidationDomain */
/**
 * @typedef {{
 *   activate: (changes: ReadonlySet<InvalidationDomain>, hash: string) => void | Promise<void>,
 *   snapshot: () => {context?: Record<string, unknown>, dirty?: boolean},
 *   destroy: () => void,
 * }} PageAdapter
 */
/**
 * @typedef {{
 *   root: HTMLElement,
 *   app: WorkspaceApp,
 * }} PageLoaderContext
 */
/** @typedef {(context: PageLoaderContext) => PageAdapter | Promise<PageAdapter>} PageLoader */
/**
 * @typedef {{
 *   document: Document,
 *   window: Window & typeof globalThis,
 *   destroy: () => void,
 * }} WorkspacePlatform
 */
/**
 * @typedef {{
 *   start: () => Promise<void>,
 *   navigate: (page: WorkspacePage, options?: NavigateOptions) => Promise<void>,
 *   invalidate: (changes: InvalidationDomain | Iterable<InvalidationDomain>) => void,
 *   destroy: () => void,
 * }} WorkspaceApp
 */
/**
 * @typedef {{
 *   focus?: boolean,
 *   hash?: string,
 *   replace?: boolean,
 *   history?: boolean,
 * }} NavigateOptions
 */

/**
 * Own persistent Live Workspace navigation and page lifecycles.
 *
 * @param {{
 *   platform: WorkspacePlatform,
 *   initialPage: string,
 *   pageLoaders: Partial<Record<WorkspacePage, PageLoader>>,
 *   publishSnapshot?: (provider: () => {context: Record<string, unknown>, dirty: boolean}) => void,
 * }} dependencies
 * @returns {WorkspaceApp}
 */
function createWorkspaceApp({ platform, initialPage, pageLoaders, publishSnapshot }) {
  const { document, window } = platform;
  const messages = scriptMessages(document);
  /** @type {Map<WorkspacePage, HTMLElement>} */
  const roots = new Map();
  for (const node of document.querySelectorAll("[data-workspace-page]")) {
    if (!(node instanceof window.HTMLElement)) continue;
    const page = asPage(node.dataset.workspacePage);
    if (page && !roots.has(page)) roots.set(page, node);
  }

  /** @type {Map<WorkspacePage, PageAdapter>} */
  const controllers = new Map();
  /** @type {Map<WorkspacePage, Promise<PageAdapter>>} */
  const loading = new Map();
  /** @type {Map<WorkspacePage, Set<InvalidationDomain>>} */
  const pending = new Map([...roots.keys()].map(page => [page, new Set()]));
  /** @type {Set<WorkspacePage>} */
  const activationNeeded = new Set(roots.keys());
  /** @type {Map<WorkspacePage, {windowY: number, elements: Map<Element, number>}>} */
  const scrollPositions = new Map();
  /** @type {WorkspacePage} */
  let activePage = availablePage(initialPage, roots) || firstPage(roots);
  let started = false;
  let destroyed = false;
  let generation = 0;
  const previousScrollRestoration = "scrollRestoration" in window.history
    ? window.history.scrollRestoration
    : null;

  /** @type {WorkspaceApp} */
  const app = {
    async start() {
      if (started || destroyed) return;
      started = true;
      document.addEventListener("click", onClick);
      window.addEventListener("popstate", onPopState);
      if ("scrollRestoration" in window.history) window.history.scrollRestoration = "manual";
      const locationPage = pageForPath(window.location.pathname);
      if (locationPage && roots.has(locationPage)) activePage = locationPage;
      window.history.replaceState(
        { ...(historyState(window.history.state)), workspacePage: activePage },
        "",
        `${PAGE_PATHS[activePage]}${window.location.search}${window.location.hash}`,
      );
      await app.navigate(activePage, {
        focus: false,
        hash: window.location.hash,
        history: false,
      });
    },

    async navigate(page, options = {}) {
      if (destroyed) return;
      const target = availablePage(page, roots);
      if (!target) return;
      const navigation = ++generation;
      const previous = activePage;
      if (started && previous && previous !== target) {
        rememberScroll(previous);
        closeTemporarySurfaces(previous);
        window.dispatchEvent(new window.CustomEvent("peval:workspace-navigate", {
          detail: { from: previous, to: target },
        }));
      }
      activePage = target;
      updateDocument(target);

      const hash = normalizeHash(options.hash ?? "");
      if (options.history !== false) {
        const href = `${PAGE_PATHS[target]}${hash}`;
        const state = { ...historyState(window.history.state), workspacePage: target };
        if (options.replace) window.history.replaceState(state, "", href);
        else window.history.pushState(state, "", href);
      }

      let controller;
      try {
        controller = await loadPage(target);
      } catch (error) {
        if (!destroyed && navigation === generation) showLoadFailure(target, error);
        return;
      }
      if (destroyed || navigation !== generation) return;

      const changes = new Set(pending.get(target));
      if (activationNeeded.has(target) || changes.size || previous !== target || hash) {
        try {
          await controller.activate(changes, hash);
        } catch (error) {
          markStale(target, error);
          return;
        }
        if (destroyed || navigation !== generation) return;
        activationNeeded.delete(target);
        for (const change of changes) pending.get(target)?.delete(change);
        clearStale(target);
      }
      clearLoadFailure(target);

      restoreScroll(target, hash);
      if (options.focus !== false || hash) focusPage(target, hash);
    },

    invalidate(changes) {
      const domains = typeof changes === "string" ? [changes] : changes;
      for (const domain of domains) {
        const pages = INVALIDATION_PAGES[domain];
        if (!pages) continue;
        for (const page of pages) {
          pending.get(/** @type {WorkspacePage} */ (page))?.add(domain);
        }
      }
    },

    destroy() {
      if (destroyed) return;
      destroyed = true;
      generation += 1;
      document.removeEventListener("click", onClick);
      window.removeEventListener("popstate", onPopState);
      for (const controller of controllers.values()) controller.destroy();
      controllers.clear();
      loading.clear();
      if (previousScrollRestoration && "scrollRestoration" in window.history) {
        window.history.scrollRestoration = previousScrollRestoration;
      }
      platform.destroy();
    },
  };

  publishSnapshot?.(snapshot);

  /** @param {MouseEvent} event */
  function onClick(event) {
    if (
      event.defaultPrevented
      || event.button !== 0
      || event.metaKey
      || event.ctrlKey
      || event.shiftKey
      || event.altKey
    ) return;
    const origin = event.target;
    if (!(origin instanceof window.Element)) return;
    const link = origin.closest("a[data-workspace-route]");
    if (!(link instanceof window.HTMLAnchorElement)) return;
    if (link.target && link.target !== "_self") return;
    if (link.hasAttribute("download")) return;
    const url = new window.URL(link.href, window.location.href);
    if (url.origin !== window.location.origin) return;
    const page = pageForPath(url.pathname);
    if (!page || !roots.has(page)) return;
    event.preventDefault();
    void app.navigate(page, { hash: url.hash }).catch(reportNavigationError);
  }

  function onPopState() {
    const page = pageForPath(window.location.pathname);
    if (!page || !roots.has(page)) return;
    void app.navigate(page, {
      focus: false,
      hash: window.location.hash,
      history: false,
    }).catch(reportNavigationError);
  }

  function snapshot() {
    const fallback = { context: { page: activePage }, dirty: false };
    const controller = controllers.get(activePage);
    if (!controller) return fallback;
    try {
      const value = controller.snapshot() || {};
      return {
        context: value.context || fallback.context,
        dirty: Boolean(value.dirty),
      };
    } catch {
      return fallback;
    }
  }

  /** @param {WorkspacePage} page */
  async function loadPage(page) {
    const existing = controllers.get(page);
    if (existing) return existing;
    const currentLoad = loading.get(page);
    if (currentLoad) return currentLoad;
    const loader = pageLoaders[page];
    const root = roots.get(page);
    if (!loader || !root) throw new Error(`Workspace page is unavailable: ${page}`);
    const promise = Promise.resolve(loader({ root, app })).then(controller => {
      if (!isPageAdapter(controller)) {
        throw new TypeError(`Workspace page adapter is invalid: ${page}`);
      }
      loading.delete(page);
      if (destroyed) {
        controller.destroy();
        return controller;
      }
      controllers.set(page, controller);
      return controller;
    }, error => {
      loading.delete(page);
      throw error;
    });
    loading.set(page, promise);
    return promise;
  }

  /** @param {WorkspacePage} page */
  function updateDocument(page) {
    for (const [candidate, root] of roots) root.hidden = candidate !== page;
    for (const link of document.querySelectorAll("[data-workspace-route]")) {
      const selected = link.getAttribute("data-workspace-route") === page;
      link.classList.toggle("active", selected);
      if (selected) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
    for (const name of [...document.body.classList]) {
      if (name.startsWith("serve-page-")) document.body.classList.remove(name);
    }
    document.body.classList.add(`serve-page-${page}`);
  }

  /** @param {WorkspacePage} page */
  function rememberScroll(page) {
    const root = roots.get(page);
    if (!root) return;
    const elements = new Map();
    for (const element of scrollElements(root)) elements.set(element, element.scrollTop);
    scrollPositions.set(page, { windowY: window.scrollY, elements });
  }

  /** @param {WorkspacePage} page */
  function closeTemporarySurfaces(page) {
    const root = roots.get(page);
    if (!root) return;
    root.querySelectorAll("details[open]").forEach(details => details.removeAttribute("open"));
    root.querySelectorAll("[data-route-transient]").forEach(surface => {
      surface.setAttribute("hidden", "");
    });
    root.querySelectorAll("[popover]").forEach(surface => {
      if ("hidePopover" in surface && typeof surface.hidePopover === "function") {
        surface.hidePopover();
      }
    });
  }

  /** @param {WorkspacePage} page @param {string} hash */
  function restoreScroll(page, hash) {
    if (hash) return;
    const saved = scrollPositions.get(page);
    if (!saved) return;
    window.requestAnimationFrame(() => {
      if (destroyed || activePage !== page) return;
      for (const [element, top] of saved.elements) element.scrollTop = top;
      if (typeof window.scrollTo === "function") window.scrollTo({ top: saved.windowY });
    });
  }

  /** @param {WorkspacePage} page @param {string} hash */
  function focusPage(page, hash) {
    const root = roots.get(page);
    if (!root) return;
    const target = hash ? document.getElementById(decodeHash(hash)) : null;
    const focusTarget = target instanceof window.HTMLElement ? target : root;
    if (!focusTarget.hasAttribute("tabindex")) focusTarget.setAttribute("tabindex", "-1");
    focusTarget.focus({ preventScroll: true });
    if (target && typeof target.scrollIntoView === "function") target.scrollIntoView();
  }

  /** @param {WorkspacePage} page @param {unknown} error */
  function showLoadFailure(page, error) {
    const root = roots.get(page);
    if (!root) return;
    let failure = root.querySelector("[data-workspace-load-error]");
    if (!failure) {
      failure = document.createElement("section");
      failure.setAttribute("data-workspace-load-error", "");
      failure.className = "workspace-page-error";
      root.prepend(failure);
    }
    failure.replaceChildren();
    const message = document.createElement("p");
    message.textContent = `${workspaceMessage(messages, "serve_page_load_failed", "This page could not be loaded.")} ${errorMessage(error)}`;
    const reload = document.createElement("button");
    reload.type = "button";
    reload.className = "action-button primary";
    reload.textContent = workspaceMessage(messages, "serve_reload", "Reload");
    reload.addEventListener("click", () => window.location.reload(), { once: true });
    failure.append(message, reload);
  }

  /** @param {WorkspacePage} page */
  function clearLoadFailure(page) {
    roots.get(page)?.querySelector("[data-workspace-load-error]")?.remove();
  }

  /** @param {WorkspacePage} page @param {unknown} error */
  function markStale(page, error) {
    const root = roots.get(page);
    if (!root) return;
    root.dataset.workspaceStale = "true";
    root.setAttribute("data-workspace-stale-message", errorMessage(error));
  }

  /** @param {WorkspacePage} page */
  function clearStale(page) {
    const root = roots.get(page);
    if (!root) return;
    delete root.dataset.workspaceStale;
    root.removeAttribute("data-workspace-stale-message");
  }

  return app;
}

/** @param {Element} root */
function scrollElements(root) {
  return [root, ...root.querySelectorAll(
    "[data-workspace-scroll], [data-workspace-main-scroll], .configuration-page",
  )];
}

/** @param {unknown} value @returns {value is PageAdapter} */
function isPageAdapter(value) {
  return Boolean(
    value
    && typeof value === "object"
    && "activate" in value
    && typeof value.activate === "function"
    && "snapshot" in value
    && typeof value.snapshot === "function"
    && "destroy" in value
    && typeof value.destroy === "function"
  );
}

/** @param {string} path @returns {WorkspacePage | null} */
function pageForPath(path) {
  const match = /** @type {[WorkspacePage, string] | undefined} */ (
    Object.entries(PAGE_PATHS).find(([, candidate]) => candidate === path)
  );
  return match?.[0] || null;
}

/** @param {unknown} value @returns {WorkspacePage | null} */
function asPage(value) {
  const page = String(value || "");
  return Object.hasOwn(PAGE_PATHS, page) ? /** @type {WorkspacePage} */ (page) : null;
}

/** @param {unknown} value @param {Map<WorkspacePage, HTMLElement>} roots */
function availablePage(value, roots) {
  const page = asPage(value);
  return page && roots.has(page) ? page : null;
}

/** @param {Map<WorkspacePage, HTMLElement>} roots @returns {WorkspacePage} */
function firstPage(roots) {
  const page = roots.keys().next().value;
  if (!page) throw new Error("Live Workspace has no page shells");
  return page;
}

/** @param {unknown} value */
function historyState(value) {
  return value && typeof value === "object" ? value : {};
}

/** @param {Document} document */
function scriptMessages(document) {
  try {
    const value = JSON.parse(document.getElementById("peval-i18n")?.textContent || "{}");
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

/** @param {Record<string, unknown>} messages @param {string} key @param {string} fallback */
function workspaceMessage(messages, key, fallback) {
  return Object.hasOwn(messages, key) ? String(messages[key]) : fallback;
}

/** @param {string} value */
function normalizeHash(value) {
  if (!value) return "";
  return value.startsWith("#") ? value : `#${value}`;
}

/** @param {string} hash */
function decodeHash(hash) {
  try {
    return decodeURIComponent(hash.slice(1));
  } catch {
    return hash.slice(1);
  }
}

/** @param {unknown} error */
function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

/** @param {unknown} error */
function reportNavigationError(error) {
  globalThis.console?.error("Workspace navigation failed", error);
}

export { INVALIDATION_PAGES, PAGE_PATHS, createWorkspaceApp };
