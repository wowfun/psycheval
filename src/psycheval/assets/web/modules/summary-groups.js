import { esc, fmtNum, t } from "./shared.js";
import { comparisonGroups, radarColors } from "./summary-chart.js";
import { preflightHomeChange } from "./home-location.js";

function groupOptions(state, groups) {
  const known = new Set(groups.map(group => group.key));
  return [...groups, ...(state.leaderboardSummaryComparisonGroups || [])
    .filter(key => !known.has(key)).map(key => ({ key, label: key ?? "-", unavailable: true }))];
}

function renderSummaryGroupControl(state, groups) {
  if (state.leaderboardSummaryGroupBy === "overall") return "";
  const keys = state.leaderboardGroupDraft ? state.leaderboardGroupDraft.keys : state.leaderboardSummaryComparisonGroups;
  const chosen = new Set(comparisonGroups(groups, keys).map(group => group.key));
  const colors = radarColors(groups.length);
  const search = state.leaderboardSummaryGroupSearch || "";
  return `<details class="column-control summary-group-control" ${state.leaderboardGroupDraft ? "open" : ""}>
    <summary class="action-button">${esc(t("summary_comparison_groups", "Comparison groups"))} <span data-group-selection-count>${chosen.size}/${groups.length}</span></summary>
    <div class="column-control-panel">
      <label>${esc(t("search", "Search"))}<input type="search" data-group-search value="${esc(search)}"></label>
      <div class="column-control-head"><button type="button" data-group-action="all">${esc(t("select_all", "Select all"))}</button><button type="button" data-group-action="none">${esc(t("clear", "Clear"))}</button></div>
      <div class="column-control-list">${groupOptions(state, groups).map((group, index) => `<label class="summary-group-option" data-group-row="${index}" data-group-match="${esc(group.label.toLocaleLowerCase())}" ${group.label.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()) ? "" : "hidden"}>
        <input type="checkbox" data-comparison-group="${index}" ${keys === null || keys.includes(group.key) ? "checked" : ""}>
        <i aria-hidden="true" style="background:${colors[index] || "var(--muted)"}"></i><span>${esc(group.label)}<small>${group.unavailable ? esc(t("summary_group_unavailable", "Outside the current results")) : `n=${fmtNum(group.count)}`}</small></span>
      </label>`).join("")}</div>
      <p data-group-search-empty hidden>${esc(t("summary_radar_no_groups", "No matching groups."))}</p>
      <p data-group-error role="alert"></p>
      <div class="column-control-foot"><span data-group-selection-count>${chosen.size}/${groups.length}</span><button class="action-button primary" type="button" data-group-apply>${esc(t("apply", "Apply"))}</button></div>
    </div>
  </details>`;
}

function bindSummaryGroupControl(target, state, groups, change) {
  const details = target.querySelector(".summary-group-control");
  if (!details) return;
  const options = groupOptions(state, groups);
  const keys = () => state.leaderboardGroupDraft ? state.leaderboardGroupDraft.keys : state.leaderboardSummaryComparisonGroups;
  const setDraft = selected => {
    state.leaderboardGroupDraft = { keys: selected };
    details.querySelectorAll("[data-comparison-group]").forEach(input => {
      input.checked = selected === null || selected.includes(options[Number(input.dataset.comparisonGroup)].key);
    });
    const count = comparisonGroups(groups, selected).length;
    details.querySelectorAll("[data-group-selection-count]").forEach(node => { node.textContent = `${count}/${groups.length}`; });
    details.querySelector("[data-group-error]").textContent = "";
  };
  details.addEventListener("toggle", () => {
    if (!details.isConnected) return;
    if (details.open) {
      const selected = keys();
      setDraft(selected === null ? null : [...selected]);
    } else {
      setDraft(state.leaderboardSummaryComparisonGroups);
      state.leaderboardGroupDraft = null;
    }
  });
  details.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    event.preventDefault(); event.stopPropagation();
    details.open = false;
    details.querySelector("summary").focus();
  });
  const search = details.querySelector("[data-group-search]");
  const filter = () => {
    const query = search.value.trim().toLocaleLowerCase();
    const rows = [...details.querySelectorAll("[data-group-row]")];
    rows.forEach(row => { row.hidden = !row.dataset.groupMatch.includes(query); });
    details.querySelector("[data-group-search-empty]").hidden = rows.some(row => !row.hidden);
  };
  search.addEventListener("input", () => { state.leaderboardSummaryGroupSearch = search.value; filter(); });
  filter();
  details.querySelectorAll("[data-comparison-group]").forEach(input => input.addEventListener("change", () => {
    const key = options[Number(input.dataset.comparisonGroup)].key;
    const selected = keys() ?? groups.map(group => group.key);
    setDraft(input.checked ? [...selected, key] : selected.filter(item => item !== key));
  }));
  details.querySelectorAll("[data-group-action]").forEach(button => button.addEventListener("click", () => setDraft(button.dataset.groupAction === "all" ? null : [])));
  details.querySelector("[data-group-apply]").addEventListener("click", () => {
    const selected = keys();
    try { preflightHomeChange({ summary: { comparison_groups: selected } }); }
    catch { details.querySelector("[data-group-error]").textContent = t("summary_group_link_limit", "The link is too large. Select fewer groups or use Select all."); return; }
    state.leaderboardSummaryComparisonGroups = selected === null ? null : [...selected];
    state.leaderboardGroupDraft = null;
    change();
    target.querySelector(".summary-group-control > summary")?.focus({ preventScroll: true });
  });
}

export { renderSummaryGroupControl, bindSummaryGroupControl };
