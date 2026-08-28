// @ts-check

/** @type {import("./workspace-app.js").WorkspaceApp | null} */
let workspaceApp = null;
let snapshotProvider = null;
const invalidationListeners = new Set();

/** @param {import("./workspace-app.js").WorkspaceApp} app */
function setWorkspaceApp(app) {
  workspaceApp = app;
}

/** @param {import("./workspace-app.js").InvalidationDomain | Iterable<import("./workspace-app.js").InvalidationDomain>} changes */
function invalidateWorkspace(changes) {
  workspaceApp?.invalidate(changes);
  const domains = typeof changes === "string" ? [changes] : [...changes];
  for (const listener of invalidationListeners) listener(new Set(domains));
}

function snapshotWorkspace() {
  return snapshotProvider?.() || { context: { page: "home" }, dirty: false };
}

function setWorkspaceSnapshotProvider(provider) {
  snapshotProvider = provider;
}

function subscribeWorkspaceInvalidation(listener) {
  invalidationListeners.add(listener);
  return () => invalidationListeners.delete(listener);
}

export {
  invalidateWorkspace,
  setWorkspaceApp,
  setWorkspaceSnapshotProvider,
  snapshotWorkspace,
  subscribeWorkspaceInvalidation,
};
