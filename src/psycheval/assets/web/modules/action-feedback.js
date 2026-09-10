import { t } from "./shared.js";
import { navigateWorkspace } from "../app/workspace-runtime.js";

const documents = new WeakMap();
const statusContainers = '[data-config-page-status], [data-harbor-workbench-status], [data-report-manager-status], [data-acp-agent-form-status], [data-admin-login-status], [data-global-shell-status]';

function feedbackStore() {
  const owner = document;
  let store = documents.get(document);
  if (store) return store;
  store = { entries: new Map(), host: null, serial: 0 };
  documents.set(document, store);
  let renderFrame = null;
  const render = () => {
    if (typeof document === "undefined" || document !== owner) { observer.disconnect(); return; }
    if (renderFrame !== null) return;
    renderFrame = window.requestAnimationFrame(() => {
      renderFrame = null;
      if (typeof document === "undefined" || document !== owner) return;
      for (const entry of store.entries.values()) renderInline(entry);
      positionNotifications(store);
    });
  };
  const observer = new window.MutationObserver(render);
  observer.observe(document.body, { childList: true, subtree: true });
  const pane = document.querySelector(".workspace");
  const resizeObserver = pane && window.ResizeObserver ? new window.ResizeObserver(render) : null;
  if (resizeObserver) resizeObserver.observe(pane);
  window.addEventListener("resize", render);
  window.addEventListener("peval:workspace-navigate", render);
  window.addEventListener("pagehide", () => {
    observer.disconnect(); resizeObserver?.disconnect();
    if (renderFrame !== null) window.cancelAnimationFrame(renderFrame);
    window.removeEventListener("resize", render);
    window.removeEventListener("peval:workspace-navigate", render);
    for (const entry of store.entries.values()) entry.dispose();
    documents.delete(owner);
  }, { once: true });
  return store;
}

function targetFor(entry) {
  return typeof entry.target === "function" ? entry.target()
    : typeof entry.target === "string" ? document.querySelector(entry.target) : entry.target;
}

function inView(node) {
  if (!node?.isConnected || node.closest('[hidden], [inert]')) return false;
  const rect = node.getBoundingClientRect();
  let top = Math.max(0, rect.top), bottom = Math.min(window.innerHeight, rect.bottom);
  let left = Math.max(0, rect.left), right = Math.min(window.innerWidth, rect.right);
  for (let parent = node.parentElement; parent; parent = parent.parentElement) {
    const style = window.getComputedStyle(parent);
    if (style.display === "none" || style.visibility === "hidden") return false;
    const bounds = parent.getBoundingClientRect();
    if (/(auto|scroll|hidden|clip)/.test(style.overflowY)) {
      top = Math.max(top, bounds.top); bottom = Math.min(bottom, bounds.bottom);
    }
    if (/(auto|scroll|hidden|clip)/.test(style.overflowX)) {
      left = Math.max(left, bounds.left); right = Math.min(right, bounds.right);
    }
  }
  return bottom > top && right > left;
}

function button(label, action) {
  const node = document.createElement("button");
  node.type = "button";
  node.className = "action-button";
  node.textContent = label;
  node.addEventListener("click", action);
  return node;
}

function renderInline(entry) {
  if (!entry.message) return;
  if (typeof entry.target !== "function" && entry.node?.isConnected) return;
  const target = targetFor(entry);
  if (!target?.isConnected) {
    removeInline(entry);
    return;
  }
  if (entry.node?.parentElement === target) return;
  removeInline(entry);
  if (target.matches(statusContainers)) target.hidden = false;
  target.append(entry.node);
}

function removeInline(entry) {
  const container = entry.node?.parentElement;
  entry.node?.remove();
  if (container?.matches(statusContainers) && !container.childElementCount && !container.textContent.trim()) container.hidden = true;
}

function makeContent(entry, toast = false) {
  const node = document.createElement("section");
  node.className = `action-feedback${entry.error ? " danger" : ""}${toast ? " action-toast" : ""}`;
  node.dataset.actionFeedback = entry.key;
  node.setAttribute("role", "status");
  node.setAttribute("aria-live", "polite");
  if (entry.label) {
    const title = document.createElement("strong");
    title.textContent = entry.label;
    node.append(title);
  }
  const message = document.createElement("p");
  message.textContent = entry.message;
  node.append(message);
  if (!toast && entry.details?.length) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = t("feedback_details", "Details");
    const list = document.createElement("ul");
    for (const item of entry.details) {
      const row = document.createElement("li");
      row.textContent = item;
      list.append(row);
    }
    details.append(summary, list);
    node.append(details);
  }
  if (!toast && entry.action) node.append(button(entry.action.label, entry.action.run));
  if (toast && entry.error) node.append(button(t("feedback_view", "View"), async () => {
    if (entry.page) await navigateWorkspace(entry.page);
    await entry.onView?.();
    renderInline(entry);
    const target = entry.node?.isConnected ? entry.node : targetFor(entry);
    target?.scrollIntoView?.({ block: "center" });
    target?.setAttribute("tabindex", "-1");
    target?.focus?.({ preventScroll: true });
    removeNotification(entry);
  }));
  if (!entry.pending) node.append(button(t("close", "Close"), () => {
    if (toast && entry.error) removeNotification(entry);
    else entry.dispose();
  }));
  return node;
}

function positionNotifications(store) {
  if (!store.host?.childElementCount) return;
  const bounds = document.querySelector(".workspace")?.getBoundingClientRect();
  const right = bounds?.right || window.innerWidth;
  store.host.style.right = `${Math.max(16, window.innerWidth - right + 16)}px`;
  store.host.style.maxWidth = `${Math.max(0, (bounds?.width || window.innerWidth) - 32)}px`;
}

function showNotification(entry, store) {
  removeNotification(entry);
  if (!entry.message || entry.pending || entry.notify === false || targetFor(entry)?.closest('[aria-modal="true"]:not([hidden])') || inView(entry.node)) return;
  if (!store.host?.isConnected) {
    store.host = document.createElement("aside");
    store.host.className = "action-notifications";
    store.host.setAttribute("aria-label", t("feedback_notifications", "Notifications"));
    document.body.append(store.host);
  }
  entry.toast = makeContent(entry, true);
  // Only one of the two projections announces this result.
  entry.node.setAttribute("aria-live", "off");
  store.host.prepend(entry.toast);
  positionNotifications(store);
}

function removeNotification(entry) {
  const host = entry.toast?.parentElement;
  entry.toast?.remove();
  entry.toast = null;
  entry.node?.setAttribute("aria-live", "polite");
  if (host && !host.childElementCount) host.remove();
}

function expireSuccess(entry) {
  if (entry.pending || entry.error || entry.notify === false) return;
  const owner = document, view = window;
  const nodes = [entry.node, entry.toast].filter(Boolean);
  let timer;
  const pause = () => view.clearTimeout(timer);
  const resume = () => {
    pause();
    if (!owner.hidden && !nodes.some(node => node.isConnected && node.matches(":hover, :focus-within"))) {
      timer = view.setTimeout(entry.dispose, 5000);
    }
  };
  for (const node of nodes) {
    node.addEventListener("mouseenter", pause);
    node.addEventListener("mouseleave", resume);
    node.addEventListener("focusin", pause);
    node.addEventListener("focusout", resume);
  }
  owner.addEventListener("visibilitychange", resume);
  entry.cleanup = () => {
    pause(); owner.removeEventListener("visibilitychange", resume);
    for (const node of nodes) {
      node.removeEventListener("mouseenter", pause);
      node.removeEventListener("mouseleave", resume);
      node.removeEventListener("focusin", pause);
      node.removeEventListener("focusout", resume);
    }
  };
  resume();
}

/** Start one action; later results from an older action with the same key are ignored. */
function beginFeedback(target, options = {}) {
  const owner = document;
  const store = feedbackStore();
  const key = options.key || (typeof target === "string" ? target : `feedback-${++store.serial}`);
  const previous = store.entries.get(key);
  previous?.dispose();
  const controller = new window.AbortController();
  const entry = { ...options, target, key, message: "", node: null, toast: null };
  entry.dispose = dispose;
  store.entries.set(key, entry);
  const update = (message, error = false, extra = {}) => {
    if (typeof document === "undefined" || document !== owner || store.entries.get(key) !== entry) return;
    if (!message) { dispose(); return; }
    if (extra.pending && entry.pending) {
      if (entry.message !== message) {
        entry.message = message;
        entry.node.querySelector("p").textContent = message;
      }
      return;
    }
    entry.cleanup?.();
    removeInline(entry);
    removeNotification(entry);
    Object.assign(entry, { message, error, pending: false, notify: true, details: [], action: null }, extra);
    entry.node = makeContent(entry);
    renderInline(entry);
    showNotification(entry, store);
    expireSuccess(entry);
  };
  return {
    signal: controller.signal,
    set(message = t("feedback_done", "Completed"), error = false) { update(message, error); },
    pending(message = t("saving", "Saving...")) { update(message, false, { pending: true }); },
    info(message) { update(message, false, { notify: false }); },
    success(message = t("feedback_done", "Completed")) { update(message); },
    error(error, extra = {}) { update(error?.message || String(error), true, {
      ...(error?.savedContent ? { details: [error.savedContent] } : {}), ...extra,
    }); },
    clear: dispose,
    dispose,
  };
  function dispose() {
    if (controller.signal.aborted) return;
    if (store.entries.get(key) === entry) store.entries.delete(key);
    controller.abort();
    entry.cleanup?.(); removeInline(entry); removeNotification(entry);
  }
}

/** Read-only refresh status is separate from action feedback. */
function pageFeedback(target) {
  return beginFeedback(target, { key: `${target}:load` });
}

function savedContentPreview(path, content) {
  const text = String(content ?? "");
  const limit = 8192;
  const preview = text.length > limit ? `${text.slice(0, limit)}\n… ${t("feedback_preview_truncated", "Preview truncated")}` : text;
  return `${t("feedback_saved_content", "Current saved content")} (${path}):\n${preview}`;
}

export { beginFeedback, inView, pageFeedback, savedContentPreview };
