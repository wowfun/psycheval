// @ts-check
import { fmtDate } from "./date-time.js";

import { RENDER_OPTIONS } from "../app/render-options.js";

const $ = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>"]/g, character => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
})[character]);
const lower = value => String(value || "").toLowerCase();

function scriptJson(id, fallback) {
  const node = $(id);
  if (!node) return fallback;
  try {
    return JSON.parse(node.textContent || JSON.stringify(fallback));
  } catch {
    return fallback;
  }
}

const I18N = scriptJson("peval-i18n", {});
function t(key, fallback) {
  return Object.prototype.hasOwnProperty.call(I18N, key) ? I18N[key] : (fallback ?? key);
}
/** @param {string} key @param {string} fallback @param {Record<string, unknown>} [values] */
function formatMessage(key, fallback, values = {}) {
  let text = String(t(key, fallback));
  for (const [name, value] of Object.entries(values)) {
    text = text.replaceAll(`{${name}}`, String(value));
  }
  return text;
}
function browserStorage() {
  try { return window.localStorage; } catch { return null; }
}
function statusLabel(value) {
  const raw = String(value || "-");
  return t(`status.${lower(raw)}`, raw);
}
function modelDisplayName(value) {
  if (typeof value !== "string" || !value.trimStart().startsWith("[")) return value;
  try {
    const parts = JSON.parse(value);
    return Array.isArray(parts) && parts.length === 2 && parts.every(part => typeof part === "string" && part.length > 0) ? parts[1] : value;
  } catch {
    return value;
  }
}
const fmtNum = value => value === null || value === undefined ? "-" : Number(value).toLocaleString();
function fmtMs(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  const seconds = Math.max(0, Number(value) / 1000);
  return seconds >= 60 ? `${Math.floor(seconds / 60)}m${(seconds % 60).toFixed(1)}s` : `${seconds.toFixed(1)}s`;
}
function fmtTtft(value) {
  if (!hasMetricValue(value)) return "-";
  const milliseconds = Math.max(0, Number(value));
  return milliseconds < 1000 ? `${Math.round(milliseconds)} ms` : `${(milliseconds / 1000).toFixed(2)}s`;
}
function fmtTps(value) { return hasMetricValue(value) ? `${Number(value).toFixed(1)} tok/s` : "-"; }
function fmtCost(value) { return hasMetricValue(value) ? `$${Number(value).toFixed(4)}` : "-"; }
function fmtPct(value) { return hasMetricValue(value) ? `${(Number(value) * 100).toFixed(1)}%` : "-"; }
function fmtScore(value) { return hasMetricValue(value) ? Number(value).toLocaleString() : "-"; }
function hasMetricValue(value) {
  return value !== null && value !== undefined && value !== "" && !Number.isNaN(Number(value));
}
function adminMode() { return RENDER_OPTIONS?.role !== "guest"; }
function authenticationEnabled() { return Boolean(RENDER_OPTIONS?.authentication_enabled); }
function listValue(value) { return Array.isArray(value) ? value : []; }

export {
  $,
  I18N,
  RENDER_OPTIONS,
  adminMode,
  authenticationEnabled,
  browserStorage,
  esc,
  fmtCost,
  fmtDate,
  fmtMs,
  fmtNum,
  fmtPct,
  fmtScore,
  fmtTps,
  fmtTtft,
  formatMessage,
  hasMetricValue,
  listValue,
  lower,
  modelDisplayName,
  scriptJson,
  statusLabel,
  t,
};
