import { currentServeSourceMode, data, listValue, normalizeServeSourceMode, readableServeSources, selectedKey, serveMode, sourceTagsFromValue, state, t } from "./runtime.js";
import { sourceBulkStateTarget } from "./source-manager.js";
import { applyLeaderboardSearchMode, applyServeMutationPayload, applyServeSourceStateMutationPayload, sourceRows, sourceSelectionKeys } from "./serve-catalog.js";

function formPayload(form) {
  const formData = new FormData(form);
  const body = {};
  for (const [key, value] of formData.entries()) {
    const text = String(value || "").trim();
    if (text) body[key] = text;
  }
  return body;
}
async function mutateSelectedServeSourceState() {
  const rows = sourceRows();
  const sourceKeys = sourceSelectionKeys(rows);
  if (!sourceKeys.length) return;
  const targetMode = sourceBulkStateTarget(rows);
  const reportMode = currentServeSourceMode() === "all"
    ? normalizeServeSourceMode(state.search?.normalSourceMode || "active")
    : currentServeSourceMode();
  try {
    const payload = await serveApi("/api/sources/state", {
      method: "POST",
      body: {
        source_keys: sourceKeys,
        active: targetMode === "active",
        report_source_state: reportMode === "all" ? "active" : reportMode
      }
    });
    state.sourceSelection.clear();
    await applyServeSourceStateMutationPayload(payload, { sourceKeys, targetMode });
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  }
}
function bindLeaderboardSearchControls(target) {
  if (!serveMode() || !target) return;
  const input = target.querySelector("[data-leaderboard-search-input]");
  if (input) {
    input.addEventListener("click", event => event.stopPropagation());
    input.addEventListener("input", event => {
      event.stopPropagation();
      state.search.query = String(input.value || "");
      applyLeaderboardSearchMode();
    });
  }
  const control = target.querySelector("[data-leaderboard-search-scope]");
  if (control) {
    control.addEventListener("click", event => event.stopPropagation());
    control.addEventListener("change", event => {
      event.stopPropagation();
      state.search.scope = control.value === "all" ? "all" : "visible";
      applyLeaderboardSearchMode();
    });
  }
}
function focusLeaderboardSearchInput() {
  const apply = () => {
    const input = document.querySelector("[data-leaderboard-search-input]");
    if (!input) return;
    input.focus();
    const end = String(input.value || "").length;
    if (typeof input.setSelectionRange === "function") input.setSelectionRange(end, end);
  };
  if (typeof requestAnimationFrame === "function") requestAnimationFrame(apply);
  else apply();
}
function existingSourceTagOptions() {
  const tags = [];
  const seen = new Set();
  const addTags = value => {
    sourceTagsFromValue(value).forEach(tag => {
      if (seen.has(tag)) return;
      seen.add(tag);
      tags.push(tag);
    });
  };
  listValue(state.serveSources).forEach(source => addTags(source?.source_tags));
  listValue(state.view?.trajectory_meta).forEach(meta => addTags(meta?.source_tags));
  Object.values(state.serveReportCache || {}).forEach(report => {
    listValue(report?.trajectory_meta).forEach(meta => addTags(meta?.source_tags));
  });
  return tags;
}
async function commitSourceCellEdit(row, field, value) {
  const sourceKey = row?.source_key;
  if (!serveMode() || !sourceKey || !["alias", "tags"].includes(field)) throw new Error(t("source_edit_unavailable", "Source editing is unavailable"));
  const action = field === "tags" ? "tags" : "alias";
  const body = {
    report_source_state: currentServeSourceMode(),
    [action === "tags" ? "tags" : "alias"]: action === "tags" ? listValue(value) : String(value || "").trim()
  };
  try {
    const payload = await serveApi(`/api/sources/${encodeURIComponent(sourceKey)}/${action}`, {
      method: "POST",
      body
    });
    applyServeMutationPayload(payload, { preserveTrial: row?.trial_key || selectedKey(), selectedSourceKey: sourceKey });
  } catch (error) {
    setServeStatus(error.message || String(error), true);
    throw error;
  }
}
function selectedAdapterValue(form) {
  return normalizeAdapterValue(new FormData(form).get("adapter"));
}
function normalizeAdapterValue(value) {
  const text = String(value || "").trim();
  return text && text.toLowerCase() !== "auto" ? text : undefined;
}
function setAdapterChoice(form, adapter) {
  const value = String(adapter || "").trim();
  if (!value) return;
  const control = form.querySelector('[name="adapter"]');
  if (!control) return;
  if (control.tagName === "SELECT") {
    if (Array.from(control.options || []).some(option => option.value === value)) {
      control.value = value;
    }
    return;
  }
  const radio = Array.from(form.querySelectorAll('[name="adapter"]')).find(input => input.value === value);
  if (radio) radio.checked = true;
}
function readableSourceKey(preferred = null, mode = currentServeSourceMode()) {
  if (preferred) {
    const match = readableServeSources(mode).find(source => source?.source_key === preferred);
    if (match) return match.source_key;
  }
  return readableServeSources(mode)[0]?.source_key || null;
}
function emptyServeReport() {
  return {
    schema_version: state.view?.schema_version || data()?.schema_version || 19,
    includes: ["core"],
    trajectory: [],
    trajectory_meta: []
  };
}
async function serveApi(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  let body = options.body;
  if (body !== undefined && typeof body !== "string") {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }
  const response = await fetch(path, {
    method: options.method || "GET",
    headers,
    body,
    credentials: "same-origin"
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(payload?.error || response.statusText);
  }
  return payload;
}
function clearServeReportCacheExcept(mode) {
  const keep = normalizeServeSourceMode(mode);
  state.serveReportCache = Object.fromEntries(
    Object.entries(state.serveReportCache || {}).filter(([key]) => normalizeServeSourceMode(key) === keep)
  );
}
function reportHasTrialKey(report, trialKey) {
  return Boolean(trialKey) && listValue(report?.trajectory_meta).some(meta => meta?.trial_key === trialKey);
}
function setServeStatus(text, error = false) {
  const node = document.querySelector("[data-source-status]");
  if (!node) return;
  node.textContent = text;
  node.classList.toggle("loading", false);
  node.classList.toggle("danger", Boolean(error));
}
function showServeNotice(text, error = false) {
  const notice = document.querySelector("[data-source-manager-status]");
  state.sourceManagerStatus = {
    phase: error ? "error" : "ready",
    message: String(text || ""),
  };
  if (!notice) return;
  notice.textContent = text;
  notice.classList.toggle("danger", Boolean(error));
  notice.classList.toggle("loading", false);
  notice.hidden = false;
}
function hideServeNotice() {
  state.sourceManagerStatus = { phase: "ready", message: "" };
  const notice = document.querySelector("[data-source-manager-status]");
  if (notice) notice.hidden = true;
}
export {
  bindLeaderboardSearchControls,
  clearServeReportCacheExcept,
  commitSourceCellEdit,
  emptyServeReport,
  existingSourceTagOptions,
  focusLeaderboardSearchInput,
  formPayload,
  hideServeNotice,
  mutateSelectedServeSourceState,
  normalizeAdapterValue,
  readableSourceKey,
  reportHasTrialKey,
  selectedAdapterValue,
  serveApi,
  setAdapterChoice,
  setServeStatus,
  showServeNotice,
};
