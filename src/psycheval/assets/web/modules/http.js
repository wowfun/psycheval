// @ts-check

import { invalidateWorkspace } from "../app/workspace-runtime.js";
import { adminMode, authenticationEnabled, t } from "./shared.js";

const responseEtags = new Map();

function reloadExpiredAdminSession(response) {
  if (response?.status !== 403 || !adminMode() || !authenticationEnabled()) return false;
  if (window.location.pathname === "/config") window.location.assign("/");
  else window.location.reload();
  return true;
}

async function serveApi(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const etagKey = options.etagKey || path;
  if (options.ifMatch !== undefined) {
    const revision = options.ifMatch === true ? responseEtags.get(etagKey) : options.ifMatch;
    if (!revision) throw new Error(t("serve_revision_missing", "Refresh this resource before saving"));
    headers["If-Match"] = String(revision).startsWith('"') ? String(revision) : `"${String(revision)}"`;
  }
  let body = options.body;
  if (body !== undefined && typeof body !== "string") {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }
  const method = String(options.method || "GET").toUpperCase();
  const response = await fetch(path, {
    method,
    headers,
    body,
    credentials: "same-origin",
    signal: options.signal,
  });
  const responseEtag = response.headers?.get?.("ETag");
  if (response.ok && responseEtag) responseEtags.set(etagKey, responseEtag);
  const text = await response.text();
  if (!response.ok) reloadExpiredAdminSession(response);
  let payload = {};
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (cause) {
      const message = response.ok
        ? t("serve_invalid_json_response", "Server returned an invalid JSON response")
        : response.statusText || `HTTP ${response.status}`;
      const error = /** @type {Error & {status: number, problem?: unknown}} */ (
        new Error(message, { cause })
      );
      error.status = response.status;
      throw error;
    }
  }
  if (!response.ok) {
    const error = /** @type {Error & {status: number, problem?: unknown}} */ (
      new Error(payload?.detail || payload?.title || response.statusText)
    );
    error.status = response.status;
    error.problem = payload;
    throw error;
  }
  for (const change of requestInvalidations(path, method, options.body)) {
    invalidateWorkspace(change);
  }
  return payload;
}

function serveEtag(key) {
  return responseEtags.get(key) || null;
}

function requestInvalidations(path, method, body) {
  if (["GET", "HEAD", "OPTIONS"].includes(method)) return [];
  const changes = new Set();
  if (path !== "/api/source-key-resolutions" && /^\/api\/(?:sources|source-|analysis)/.test(path)) {
    changes.add("catalog");
  }
  if (/^\/api\/reports(?:\/|$)/.test(path)) changes.add("reports");
  if (
    /^\/api\/harbor\/(?:dataset-unregistration-operations|mounts|mount-deletion-operations)(?:\/|$)/.test(path)
    || /^\/api\/harbor\/datasets(?:\/[^/]+)?$/.test(path)
  ) changes.add("dataset-registry");
  else if (/^\/api\/harbor\//.test(path)) changes.add("tasks");
  if (/^\/api\/prompts(?:\/|$)/.test(path)) changes.add("prompt-assets");
  if (path === "/api/config") {
    const keys = new Set(Object.keys(body && typeof body === "object" ? body : {}));
    if (keys.has("datasets") || keys.has("mounts")) changes.add("dataset-registry");
    if (keys.has("acp_agents")) changes.add("assistant-config");
  }
  return changes;
}

export { reloadExpiredAdminSession, requestInvalidations, serveApi, serveEtag };
