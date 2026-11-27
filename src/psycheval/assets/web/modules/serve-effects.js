import { beginFeedback, pageFeedback } from "./action-feedback.js";
import { offerRefresh } from "./operation-feedback.js";
import { currentServeSourceMode, normalizeServeSourceMode, readableServeSources, renderComparisonPanels, selectedKey, sourceTagsFromValue, state } from "./runtime.js";
import { applyLeaderboardSearchMode, applyServeMutationPayload, refreshSourceCategoryOptions } from "./serve-catalog.js";
import { reloadExpiredAdminSession, serveApi, serveEtag } from "./http.js";
import { adminMode, canAnnotate, listValue, t } from "./shared.js";
import { openCommentsModal } from "./comments-ui.js";

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
      offerRefresh(beginFeedback("#leaderboard .leaderboard-action-row", { key: `home:source:${sourceKey}:refresh`, page: "home" }), error, refresh);
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
function applySourceCommentsUpdate(sourceKey, comments) {
  const next = listValue(comments);
  const rows = listValue(state.catalogRows);
  let delta = 0;
  for (const row of rows) {
    if (row?.source_key === sourceKey) {
      const had = Boolean(row.review_comments_present || listValue(row.review_comments).length);
      const has = next.length > 0;
      if (had !== has) delta = has ? 1 : -1;
      row.review_comments = next;
      row.review_comment_count = next.length;
      row.review_comments_present = has;
    }
  }
  if (state.catalogPage?.column_presence && delta !== 0) {
    const prev = Number(state.catalogPage.column_presence.review_comments || 0);
    state.catalogPage.column_presence.review_comments = Math.max(0, prev + delta);
  }
  if (state.catalogPage?.facets && delta !== 0) {
    const current = listValue(state.catalogPage.facets.review_comments);
    const counts = new Map(current.map(item => [String(item?.value || ""), Number(item?.count || 0)]));
    counts.set("commented", Math.max(0, (counts.get("commented") || 0) + delta));
    counts.set("uncommented", Math.max(0, (counts.get("uncommented") || 0) - delta));
    state.catalogPage.facets.review_comments = ["commented", "uncommented"]
      .filter(value => (counts.get(value) || 0) > 0)
      .map(value => ({ value, count: counts.get(value) }));
  }
  renderComparisonPanels({ refreshDetail: false });
  if (state.detailSidebar?.reviewCommentsSourceKey === sourceKey) {
    state.detailSidebar.reviewCommentsSync?.(next);
  }
}

async function createSourceComment(sourceKey, body) {
  const payload = await serveApi(`/api/source-comments/${encodeURIComponent(sourceKey)}`, {
    method: "POST",
    body: { body },
  });
  const next = listValue(payload?.comments);
  applySourceCommentsUpdate(sourceKey, next);
  return next;
}

async function updateSourceComment(sourceKey, comment, body) {
  const payload = await serveApi(
    `/api/source-comments/${encodeURIComponent(sourceKey)}/${encodeURIComponent(comment.id)}`,
    { method: "PATCH", body: { body }, ifMatch: comment.revision },
  );
  const next = listValue(payload?.comments);
  applySourceCommentsUpdate(sourceKey, next);
  return next;
}

async function deleteSourceComment(sourceKey, comment) {
  const payload = await serveApi(
    `/api/source-comments/${encodeURIComponent(sourceKey)}/${encodeURIComponent(comment.id)}`,
    { method: "DELETE", ifMatch: comment.revision },
  );
  const next = listValue(payload?.comments);
  applySourceCommentsUpdate(sourceKey, next);
  return next;
}

function openReviewCommentsModal(row, opener) {
  const sourceKey = String(row?.source_key || "");
  if (!sourceKey) return null;
  const label = row?.display_alias || row?.task_name || row?.trial_key || sourceKey;
  const subtitle = [row?.dataset_id, row?.job_name, row?.agent_name || row?.adapter].filter(Boolean).join(" · ");
  return openCommentsModal({
    title: `${label} · ${t("comments", "Comments")}`,
    subtitle,
    comments: listValue(row?.review_comments),
    canCreate: canAnnotate(),
    opener,
    onCreate: body => createSourceComment(sourceKey, body),
    onUpdate: (comment, body) => updateSourceComment(sourceKey, comment, body),
    onDelete: comment => deleteSourceComment(sourceKey, comment),
  });
}

function setServeStatus(text, error = false) {
  const feedback = pageFeedback("#leaderboard .leaderboard-action-row");
  if (error) feedback.error(text);
  else if (text) feedback.info(text);
  else feedback.clear();
}
export {
  applySourceCommentsUpdate,
  bindLeaderboardSearchControls,
  clearServeReportCacheExcept,
  commitSourceCellEdit,
  createSourceComment,
  deleteSourceComment,
  emptyServeReport,
  existingSourceCategoryOptions,
  existingSourceTagOptions,
  focusLeaderboardSearchInput,
  formPayload,
  normalizeAdapterValue,
  openReviewCommentsModal,
  readableSourceKey,
  reloadExpiredAdminSession,
  reportHasTrialKey,
  selectedAdapterValue,
  serveApi,
  serveEtag,
  setAdapterChoice,
  setServeStatus,
  updateSourceComment,
};
