// @ts-check
import { SORT_KEYS as SORTS } from "./catalog-sort.js";
import { BROWSER_VIEW_LIMIT, VIEW_NAME_MAX_CHARS, VIEW_GROUPS as GROUPS } from "./workspace-view-contract.js";

const MAX_LOCATION_BYTES = 64 * 1024;
const FACETS = ["categories", "tags", "agents", "models", "tasks", "jobs", "providers", "datasets", "results"];
const HOME_QUERY = Object.freeze({ state: "active", search: "", page: 1, page_size: 100, sort: "last_turn_end", direction: "desc", ...Object.fromEntries(FACETS.map(key => [key, []])) });
const REPORT_QUERY = Object.freeze({ state: "active", search: "", page: 1, page_size: 50, kinds: [], datasets: [], jobs: [] });
const SUMMARY = Object.freeze({ group_by: "agent", statistic: "mean", table_open: false });
const STATS = new Set(["mean", "min", "q1", "p50", "q3", "p95", "max"]);

class WorkspaceLocationError extends Error {
  constructor(messageKey, message) { super(message); this.messageKey = messageKey; }
}
function invalid() { throw new WorkspaceLocationError("shared_link_invalid", "Invalid or unsupported workspace link"); }
function oversized() { throw new WorkspaceLocationError("shared_link_too_large", "Workspace link exceeds the 64 KiB limit"); }
function object(value, allowed) {
  if (!value || typeof value !== "object" || Array.isArray(value) || Object.keys(value).some(key => !allowed.includes(key))) invalid();
  return value;
}
function strings(value) {
  if (!Array.isArray(value) || value.some(item => typeof item !== "string" || !item.trim() || item.includes("\0"))) invalid();
  return [...new Set(value.map(item => item.trim()))].sort();
}
function queryState(page, value = {}) {
  const defaults = page === "home" ? HOME_QUERY : REPORT_QUERY;
  object(value, Object.keys(defaults));
  const result = /** @type {Record<string, any>} */ (Object.fromEntries(Object.entries(defaults).map(([key, item]) => [key, Array.isArray(item) ? [...item] : item])));
  for (const [key, item] of Object.entries(value)) {
    if (Array.isArray(defaults[key])) result[key] = strings(item);
    else if (typeof item !== typeof defaults[key]) invalid();
    else result[key] = item;
  }
  if (!["active", "archived", "all"].includes(result.state) || typeof result.search !== "string" || result.search.includes("\0")) invalid();
  if (!Number.isSafeInteger(result.page) || result.page < 1 || !Number.isSafeInteger(result.page_size) || result.page_size < 1 || result.page_size > 100) invalid();
  if (page === "home" && (!SORTS.has(result.sort) || !["asc", "desc"].includes(result.direction))) invalid();
  if (page === "reports" && result.kinds.some(key => !["session", "dataset", "job", "unassociated"].includes(key))) invalid();
  return result;
}
function summaryState(value = {}) {
  object(value, Object.keys(SUMMARY));
  const result = { ...SUMMARY, ...value };
  if (!GROUPS.has(result.group_by) || !STATS.has(result.statistic) || typeof result.table_open !== "boolean") invalid();
  return result;
}
function viewSnapshots(values = []) {
  if (!Array.isArray(values) || values.length > BROWSER_VIEW_LIMIT) invalid();
  return values.map(value => {
    object(value, ["name", "filters"]);
    if (typeof value.name !== "string" || !value.name || [...value.name].length > VIEW_NAME_MAX_CHARS) invalid();
    object(value.filters, ["state", "search", ...FACETS]);
    const full = queryState("home", value.filters);
    return { name: value.name, filters: Object.fromEntries(["state", "search", ...FACETS].map(key => [key, full[key]])) };
  }).map(view => ({ view, key: stable(view) }))
    .sort((a, b) => a.key < b.key ? -1 : a.key > b.key ? 1 : 0)
    .map(entry => entry.view);
}
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
function differences(value, defaults) {
  return Object.fromEntries(Object.entries(value).filter(([key, item]) => stable(item) !== stable(defaults[key])));
}
function normalizeLocationState(page, value = {}) {
  object(value, ["query", "views", "summary"]);
  if (page !== "home" && (value.views !== undefined || value.summary !== undefined)) invalid();
  return {
    query: queryState(page, value.query),
    ...(page === "home" ? { views: viewSnapshots(value.views), summary: summaryState(value.summary) } : {}),
  };
}
function encodePayload(page, value) {
  const state = normalizeLocationState(page, value);
  const query = differences(state.query, page === "home" ? HOME_QUERY : REPORT_QUERY);
  const payload = { v: 1 };
  if (Object.keys(query).length) payload.query = query;
  if (page === "home") {
    if (state.views.length) payload.views = state.views.map(view => ({ ...view, filters: differences(view.filters, HOME_QUERY) }));
    const summary = differences(state.summary, SUMMARY);
    if (Object.keys(summary).length) payload.summary = summary;
  }
  if (Object.keys(payload).length === 1) return "";
  const bytes = new TextEncoder().encode(stable(payload));
  if (bytes.length > MAX_LOCATION_BYTES) oversized();
  const chunks = [];
  for (let start = 0; start < bytes.length; start += 8192) chunks.push(String.fromCharCode(...bytes.subarray(start, start + 8192)));
  return "#view=" + btoa(chunks.join("")).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}
function normalizeLocationObject(page, value = {}) {
  object(value, ["source", "report", "trajectory", "step", "tab"]);
  const result = {};
  for (const [key, item] of Object.entries(value)) {
    if (typeof item !== "string" || !item || item.includes("\0")) invalid();
    result[key] = item;
  }
  if (result.source && result.report || page === "reports" && (result.source || result.trajectory || result.step)) invalid();
  if ((result.trajectory || result.step) && !result.source) invalid();
  const tabs = result.source ? ["trajectory", "task", "verification"] : result.report && page === "reports" ? ["preview", "associations"] : ["preview"];
  if (result.tab && (!result.source && !result.report || !tabs.includes(result.tab))) invalid();
  return result;
}
function encodeWorkspaceLocation(page, value = {}, origin = "") {
  const target = normalizeLocationObject(page, value.object);
  const params = new URLSearchParams(Object.entries(target).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0));
  const href = `${page === "reports" ? "/reports" : "/"}${params.size ? "?" + params : ""}${encodePayload(page, value.state || {})}`;
  if (new TextEncoder().encode(origin + href).length > MAX_LOCATION_BYTES) oversized();
  return origin + href;
}
function decodeWorkspaceLocation(page, location) {
  if (new TextEncoder().encode(location.href || `${location.search || ""}${location.hash || ""}`).length > MAX_LOCATION_BYTES) oversized();
  const params = new URLSearchParams(location.search || "");
  const target = {};
  for (const key of ["source", "report", "trajectory", "step", "tab"]) {
    if (params.getAll(key).length > 1) invalid();
    if (params.has(key)) target[key] = params.get(key);
  }
  let payload = {};
  if (location.hash) {
    if (!location.hash.startsWith("#view=")) invalid();
    const encoded = location.hash.slice(6);
    if (!/^[A-Za-z0-9_-]+$/.test(encoded)) invalid();
    try {
      const bytes = Uint8Array.from(atob(encoded.replaceAll("-", "+").replaceAll("_", "/")), char => char.charCodeAt(0));
      payload = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    } catch { invalid(); }
    object(payload, ["v", "query", "views", "summary"]);
    if (payload.v !== 1) invalid();
  }
  const { v: _version, ...state } = payload;
  return { object: normalizeLocationObject(page, target), state: normalizeLocationState(page, state) };
}

export { MAX_LOCATION_BYTES, HOME_QUERY, REPORT_QUERY, SUMMARY, normalizeLocationObject, normalizeLocationState, encodeWorkspaceLocation, decodeWorkspaceLocation };
