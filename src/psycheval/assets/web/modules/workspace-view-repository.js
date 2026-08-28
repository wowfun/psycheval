const BROWSER_VIEW_VERSION = 1;
const BROWSER_VIEW_LIMIT = 100;
const VIEW_NAME_LIMIT = 120;
const VIEW_NOTES_BYTE_LIMIT = 1024 * 1024;
const VIEW_GROUPS = new Set(["overall", "agent", "model", "category", "task", "job", "provider"]);
const FILTER_KEYS = new Set([
  "state", "search", "categories", "tags", "agents", "models", "results",
  "tasks", "jobs", "providers",
]);
const LIST_FILTER_KEYS = [
  "categories", "tags", "agents", "models", "results", "tasks", "jobs", "providers",
];
const VIEW_KEYS = new Set(["name", "filters", "group_by", "notes"]);

function browserViewStorageKey(workspaceId) {
  return `peval.saved-views.v${BROWSER_VIEW_VERSION}.${String(workspaceId || "default")}`;
}

function repositoryError(message, cause = null) {
  const error = new Error(message);
  if (cause) error.cause = cause;
  return error;
}

function normalizeName(value) {
  if (typeof value !== "string") throw repositoryError("View name must be a string.");
  const name = value.trim();
  if (!name) throw repositoryError("View name is required.");
  if (name.length > VIEW_NAME_LIMIT) throw repositoryError(`View name exceeds ${VIEW_NAME_LIMIT} characters.`);
  if (name === "." || name === ".." || /[\\/]/.test(name)) throw repositoryError("View name must be one filename stem.");
  if (Array.from(name).some(character => {
    const code = character.codePointAt(0);
    return code < 32 || code === 127;
  })) throw repositoryError("View name must not contain control characters.");
  return name;
}

function normalizeStringList(value, key) {
  if (!Array.isArray(value) || value.some(item => typeof item !== "string")) {
    throw repositoryError(`View filters ${key} must be a string array.`);
  }
  const seen = new Set();
  return value.filter(item => {
    if (seen.has(item)) return false;
    seen.add(item);
    return true;
  });
}

function normalizeFilters(value) {
  const filters = value === undefined || value === null ? {} : value;
  if (!filters || typeof filters !== "object" || Array.isArray(filters)) {
    throw repositoryError("View filters must be an object.");
  }
  if (Object.keys(filters).some(key => !FILTER_KEYS.has(key))) {
    throw repositoryError("View filters contain unsupported fields.");
  }
  const state = filters.state === undefined ? "active" : filters.state;
  const search = filters.search === undefined ? "" : filters.search;
  if (typeof state !== "string" || typeof search !== "string") {
    throw repositoryError("View filters state and search must be strings.");
  }
  if (!["active", "archived", "all"].includes(state)) {
    throw repositoryError("View filters state must be active, archived, or all.");
  }
  const normalized = {};
  if (state !== "active") normalized.state = state;
  if (search) normalized.search = search;
  LIST_FILTER_KEYS.forEach(key => {
    const items = normalizeStringList(filters[key] || [], key);
    if (items.length) normalized[key] = items;
  });
  return normalized;
}

function utf8ByteLength(value) {
  let bytes = 0;
  for (const character of value) {
    const code = character.codePointAt(0);
    if (code <= 0x7f) bytes += 1;
    else if (code <= 0x7ff) bytes += 2;
    else if (code <= 0xffff) bytes += 3;
    else bytes += 4;
  }
  return bytes;
}

function normalizeBrowserView(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw repositoryError("Browser view must be an object.");
  }
  if (Object.keys(value).some(key => !VIEW_KEYS.has(key))) {
    throw repositoryError("Browser view contains unsupported fields.");
  }
  const notes = value.notes === undefined ? "" : value.notes;
  if (typeof notes !== "string") throw repositoryError("View notes must be a string.");
  if (utf8ByteLength(notes) > VIEW_NOTES_BYTE_LIMIT) {
    throw repositoryError(`View notes exceed ${VIEW_NOTES_BYTE_LIMIT} byte limit.`);
  }
  const groupBy = String(value.group_by || "").trim().toLowerCase();
  if (!VIEW_GROUPS.has(groupBy)) {
    throw repositoryError("group_by must be overall, agent, model, category, task, job, or provider.");
  }
  return {
    name: normalizeName(value.name),
    filters: normalizeFilters(value.filters),
    group_by: groupBy,
    notes,
  };
}

function normalizeBrowserViews(value, { enforceLimit = true } = {}) {
  if (!Array.isArray(value)) throw repositoryError("Browser Saved Views must be an array.");
  if (enforceLimit && value.length > BROWSER_VIEW_LIMIT) {
    throw repositoryError(`Browser Saved Views may contain at most ${BROWSER_VIEW_LIMIT} views.`);
  }
  const views = value.map(normalizeBrowserView);
  const names = new Set();
  views.forEach(view => {
    if (names.has(view.name)) throw repositoryError(`Duplicate browser view: ${view.name}`);
    names.add(view.name);
  });
  return views;
}

function identified(origin, view) {
  const normalized = normalizeBrowserView(view);
  return { ...normalized, id: `${origin}:${normalized.name}`, origin };
}

function viewSort(left, right) {
  return left.name.localeCompare(right.name, undefined, { numeric: true, sensitivity: "base" });
}

function createWorkspaceViewRepository({ workspaceId, storage, request }) {
  if (typeof request !== "function") throw repositoryError("Saved View request adapter is required.");
  const storageKey = browserViewStorageKey(workspaceId);
  let serverViews = [];
  let browserViews = [];
  let serverLoaded = false;
  let browserLoaded = false;

  function readBrowserViews() {
    if (!storage || typeof storage.getItem !== "function") {
      throw repositoryError("Browser Saved Views storage is unavailable.");
    }
    let text;
    try {
      text = storage.getItem(storageKey);
    } catch (error) {
      throw repositoryError(`Browser Saved Views could not be read: ${error?.message || error}`, error);
    }
    if (text === null || text === "") return [];
    try {
      const payload = JSON.parse(text);
      if (!payload || typeof payload !== "object" || Array.isArray(payload) || payload.version !== BROWSER_VIEW_VERSION || !Object.prototype.hasOwnProperty.call(payload, "views")) {
        throw new Error("unsupported or malformed storage payload");
      }
      return normalizeBrowserViews(payload.views);
    } catch (error) {
      throw repositoryError(`Browser Saved Views could not be read: ${error?.message || error}`, error);
    }
  }

  function persist(next) {
    if (!storage || typeof storage.setItem !== "function") {
      throw repositoryError("Browser Saved Views storage is unavailable.");
    }
    const normalized = normalizeBrowserViews(next);
    try {
      storage.setItem(storageKey, JSON.stringify({ version: BROWSER_VIEW_VERSION, views: normalized }));
    } catch (error) {
      throw repositoryError(`Browser Saved Views could not be saved: ${error?.message || error}`, error);
    }
    browserViews = normalized;
  }

  function visibleViews() {
    const serverNames = new Set(serverViews.map(view => view.name));
    return [
      ...serverViews.map(view => identified("server", view)),
      ...browserViews.filter(view => !serverNames.has(view.name)).map(view => identified("browser", view)),
    ].sort(viewSort);
  }

  function findVisible(id) {
    return visibleViews().find(view => view.id === String(id || "")) || null;
  }

  async function refresh() {
    const response = await request("/api/views");
    const nextServer = normalizeBrowserViews(Array.isArray(response) ? response : [], { enforceLimit: false });
    serverViews = nextServer;
    serverLoaded = true;
    browserLoaded = false;
    browserViews = readBrowserViews();
    browserLoaded = true;
    return visibleViews();
  }

  async function save(definition, { location = "browser", overwrite = false } = {}) {
    const view = normalizeBrowserView(definition);
    if (location === "workspace") {
      const response = await request(`/api/views/${encodeURIComponent(view.name)}`, {
        method: "PUT",
        body: { filters: view.filters, group_by: view.group_by, notes: view.notes, overwrite: Boolean(overwrite) },
      });
      serverViews = normalizeBrowserViews([
        ...serverViews.filter(item => item.name !== response.name),
        response,
      ], { enforceLimit: false });
      serverLoaded = true;
      return identified("server", response);
    }
    if (location !== "browser") throw repositoryError("Saved View location must be workspace or browser.");
    if (!serverLoaded) throw repositoryError("Load workspace Saved Views before saving to this browser.");
    if (!browserLoaded) throw repositoryError("Browser Saved Views storage must be read successfully before saving.");
    if (serverViews.some(item => item.name === view.name)) {
      throw repositoryError(`A workspace Saved View already uses the name ${view.name}.`);
    }
    const index = browserViews.findIndex(item => item.name === view.name);
    if (index >= 0 && !overwrite) throw repositoryError(`Browser Saved View already exists: ${view.name}`);
    const next = [...browserViews];
    if (index >= 0) next[index] = view;
    else next.push(view);
    persist(next);
    return identified("browser", view);
  }

  async function update(id, change) {
    const current = findVisible(id);
    if (!current) throw repositoryError(`Saved View is not available: ${id}`);
    if (!change || !["name", "notes", "configuration"].includes(change.field)) {
      throw repositoryError("Saved View update must change name, notes, or configuration.");
    }
    if (current.origin === "server") {
      const response = await request(`/api/views/${encodeURIComponent(current.name)}`, {
        method: "PATCH",
        body: { field: change.field, value: change.value },
      });
      serverViews = normalizeBrowserViews([
        ...serverViews.filter(item => item.name !== current.name && item.name !== response.name),
        response,
      ], { enforceLimit: false });
      return identified("server", response);
    }
    let next = { name: current.name, filters: current.filters, group_by: current.group_by, notes: current.notes };
    if (change.field === "name") next.name = change.value;
    if (change.field === "notes") next.notes = change.value;
    if (change.field === "configuration") {
      if (!change.value || typeof change.value !== "object") throw repositoryError("Browser Saved View configuration must be an object.");
      next = { ...next, filters: change.value.filters, group_by: change.value.group_by };
    }
    next = normalizeBrowserView(next);
    if (serverViews.some(item => item.name === next.name)) {
      throw repositoryError(`A workspace Saved View already uses the name ${next.name}.`);
    }
    if (browserViews.some(item => item.name === next.name && item.name !== current.name) && !change.overwrite) {
      throw repositoryError(`Browser Saved View already exists: ${next.name}`);
    }
    persist([
      ...browserViews.filter(item => item.name !== current.name && item.name !== next.name),
      next,
    ]);
    return identified("browser", next);
  }

  async function remove(ids) {
    const unique = Array.from(new Set((Array.isArray(ids) ? ids : []).map(String)));
    const resolved = unique.map(id => {
      const view = findVisible(id);
      if (!view) throw repositoryError(`Saved View is not available: ${id}`);
      return view;
    });
    const serverNames = resolved.filter(view => view.origin === "server").map(view => view.name);
    const browserNames = new Set(resolved.filter(view => view.origin === "browser").map(view => view.name));
    if (serverNames.length) {
      let operation = await request("/api/view-deletion-operations", {
        method: "POST",
        body: { names: serverNames },
      });
      while (["queued", "running"].includes(operation?.state)) {
        await new Promise(resolve => setTimeout(resolve, 250));
        operation = await request(`/api/operations/${encodeURIComponent(operation.id)}`);
      }
      const failures = Array.isArray(operation?.failures) ? operation.failures : [];
      if (operation?.state === "failed" || failures.length) {
        throw repositoryError(failures[0]?.error || "Workspace Saved View deletion failed.");
      }
      serverViews = normalizeBrowserViews(serverViews.filter(view => !serverNames.includes(view.name)), { enforceLimit: false });
    }
    if (browserNames.size) persist(browserViews.filter(view => !browserNames.has(view.name)));
    return { server: serverNames, browser: Array.from(browserNames), views: visibleViews() };
  }

  function queryPayload(ids) {
    const server = [];
    const browser = [];
    const seen = new Set();
    (Array.isArray(ids) ? ids : []).forEach(rawId => {
      const id = String(rawId);
      if (seen.has(id)) return;
      seen.add(id);
      const view = findVisible(id);
      if (!view) throw repositoryError(`Saved View is not available: ${id}`);
      if (view.origin === "server") server.push(view.name);
      else browser.push({ name: view.name, filters: view.filters, group_by: view.group_by, notes: view.notes });
    });
    return { views: server, browser_views: browser };
  }

  return {
    refresh,
    list: visibleViews,
    save,
    update,
    delete: remove,
    queryPayload,
    ready: () => serverLoaded,
    browserReady: () => browserLoaded,
  };
}

export {
  BROWSER_VIEW_LIMIT,
  BROWSER_VIEW_VERSION,
  browserViewStorageKey,
  createWorkspaceViewRepository,
  normalizeBrowserView,
};
