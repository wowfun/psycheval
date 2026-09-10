import { beginFeedback, pageFeedback } from "./action-feedback.js";
import { offerRefresh } from "./operation-feedback.js";
import { currentServeSourceMode, normalizeServeSourceMode, readableServeSources, selectedKey, sourceTagsFromValue, state } from "./runtime.js";
import { applyLeaderboardSearchMode, applyServeMutationPayload, refreshSourceCategoryOptions } from "./serve-catalog.js";
import { reloadExpiredAdminSession, serveApi, serveEtag } from "./http.js";
import { adminMode, listValue, t } from "./shared.js";

function formPayload(form) {
  const formData = new FormData(form);
  const body = {};
  for (const [key, value] of formData.entries()) {
    const text = String(value || "").trim();
    if (text) body[key] = text;
  }
  return body;
}
function bindLeaderboardSearchControls(target) {
  if (!target) return;
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
function existingSourceCategoryOptions() {
  const seen = new Set();
  return listValue(state.sourceCategoryOptions)
    .map(value => String(value || "").trim())
    .filter(value => value && !seen.has(value) && seen.add(value));
}
async function commitSourceCellEdit(row, field, value) {
  const sourceKey = row?.source_key;
  if (!adminMode() || !sourceKey || !["alias", "category", "tags"].includes(field)) throw new Error(t("source_edit_unavailable", "Source editing is unavailable"));
  const action = field;
  const body = action === "category"
    ? { category: String(value || "").trim() }
    : {
        [action]: action === "tags" ? listValue(value) : String(value || "").trim()
      };
  let committed = false;
  let updated;
  const refresh = async () => {
    const payload = await serveApi("/api/sources");
    updated = listValue(payload?.sources).find(source => source?.source_key === sourceKey);
    if (updated) Object.assign(row, updated);
    else if (action === "category") row.source_category = body.category || null;
    await applyServeMutationPayload(payload, { preserveTrial: row?.trial_key || selectedKey(), selectedSourceKey: sourceKey, throwOnError: true });
    if (action === "category") await refreshSourceCategoryOptions();
  };
  try {
    await serveApi(`/api/sources/${encodeURIComponent(sourceKey)}`, {
      method: "PATCH",
      body
    });
    committed = true;
    await refresh();
    return { rowKey: sourceKey, source: updated || row };
  } catch (error) {
    if (committed) {
      offerRefresh(beginFeedback("#comparison .leaderboard-action-row", { key: `home:source:${sourceKey}:refresh`, page: "home" }), error, refresh);
      return { rowKey: sourceKey, source: row };
    }
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
    schema_version: state.view?.schema_version || 19,
    includes: ["core"],
    trajectory: [],
    trajectory_meta: []
  };
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
  const feedback = pageFeedback("#comparison .leaderboard-action-row");
  if (error) feedback.error(text);
  else if (text) feedback.info(text);
  else feedback.clear();
}
export {
  bindLeaderboardSearchControls,
  clearServeReportCacheExcept,
  commitSourceCellEdit,
  emptyServeReport,
  existingSourceCategoryOptions,
  existingSourceTagOptions,
  focusLeaderboardSearchInput,
  formPayload,
  normalizeAdapterValue,
  readableSourceKey,
  reloadExpiredAdminSession,
  reportHasTrialKey,
  selectedAdapterValue,
  serveApi,
  serveEtag,
  setAdapterChoice,
  setServeStatus,
};
