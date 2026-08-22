const COLUMN_LAYOUT_VERSION = 1;

function normalizeColumnLayout(columnKeys, value) {
  const canonical = Array.from(new Set(columnKeys.map(String)));
  const known = new Set(canonical);
  const rawOrder = Array.isArray(value?.order) ? value.order : [];
  const order = [];
  rawOrder.forEach(raw => {
    const key = String(raw || "");
    if (known.has(key) && !order.includes(key)) order.push(key);
  });
  const canonicalIndexes = new Map(canonical.map((key, index) => [key, index]));
  canonical.forEach(key => {
    if (order.includes(key)) return;
    const keyIndex = canonicalIndexes.get(key);
    const nextIndex = order.findIndex(candidate => canonicalIndexes.get(candidate) > keyIndex);
    if (nextIndex >= 0) order.splice(nextIndex, 0, key);
    else order.push(key);
  });
  const visibility = {};
  if (value?.visibility && typeof value.visibility === "object") {
    Object.entries(value.visibility).forEach(([key, mode]) => {
      if (known.has(key) && ["show", "hide"].includes(mode)) visibility[key] = mode;
    });
  }
  return { version: COLUMN_LAYOUT_VERSION, order, visibility };
}

function layoutStorageKey(workspaceId) {
  return `peval.leaderboard-columns.v${COLUMN_LAYOUT_VERSION}.${String(workspaceId || "default")}`;
}

function loadColumnLayout(columnKeys, { workspaceId, snapshotLayout, storage } = {}) {
  if (snapshotLayout) return normalizeColumnLayout(columnKeys, snapshotLayout);
  if (!storage) return normalizeColumnLayout(columnKeys, null);
  try {
    return normalizeColumnLayout(columnKeys, JSON.parse(storage.getItem(layoutStorageKey(workspaceId)) || "null"));
  } catch {
    return normalizeColumnLayout(columnKeys, null);
  }
}

function saveColumnLayout(layout, { workspaceId, storage } = {}) {
  if (!storage) return;
  try {
    storage.setItem(layoutStorageKey(workspaceId), JSON.stringify(layout));
  } catch {
    // Browser storage is optional presentation state.
  }
}

function semanticValuePresent(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim() !== "" && value.trim() !== "-";
  if (Array.isArray(value)) return value.length > 0;
  return true;
}

function presenceForColumns(columns, rows, serverPresence = null) {
  return Object.fromEntries(columns.map(column => {
    if (serverPresence && Object.prototype.hasOwnProperty.call(serverPresence, column.key)) {
      return [column.key, Number(serverPresence[column.key]) > 0];
    }
    const present = rows.some(row => semanticValuePresent(
      column.presence ? column.presence(row) : column.value ? column.value(row) : row?.[column.key]
    ));
    return [column.key, present];
  }));
}

function columnVisibleForLayout(column, layout, presence) {
  const mode = layout?.visibility?.[column.key];
  if (mode === "show") return true;
  if (mode === "hide") return false;
  return column.defaultVisible !== false && Boolean(presence[column.key]);
}

function resolveColumns(columns, layout, presence) {
  const byKey = new Map(columns.map(column => [column.key, column]));
  const ordered = layout.order.flatMap(key => byKey.has(key) ? [byKey.get(key)] : []);
  const visible = ordered.filter(column => columnVisibleForLayout(column, layout, presence));
  return visible;
}

function moveColumn(order, key, direction) {
  const next = [...order];
  const index = next.indexOf(key);
  const target = index + direction;
  if (index < 0 || target < 0 || target >= next.length) return next;
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

export {
  COLUMN_LAYOUT_VERSION,
  columnVisibleForLayout,
  layoutStorageKey,
  loadColumnLayout,
  moveColumn,
  normalizeColumnLayout,
  presenceForColumns,
  resolveColumns,
  saveColumnLayout,
  semanticValuePresent,
};
