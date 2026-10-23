import { esc, t } from "./shared.js";
import { METRIC_SELECTION_LIMIT } from "../app/metric-contract.js";
import { metricDefinitions, selectedMetricIds, metricSearchText } from "./metric-presentation.js";
import { preflightHomeChange } from "./home-location.js";

function renderSummaryMetricControl(state) {
  const definitions = metricDefinitions(state);
  const selected = state.leaderboardMetricDraft || selectedMetricIds(state);
  const keys = [...selected, ...definitions.map(item => item.key).filter(key => !selected.includes(key))];
  const search = state.leaderboardMetricSearch || "";
  const diagnostics = [...(state.catalogPage?.metric_diagnostics || state.leaderboardSummary?.metric_diagnostics || []), ...(state.catalogRows || []).flatMap(row => (row.metric_diagnostics || []).map(message => `${row.source_key}: ${message}`))];
  return `<details class="column-control summary-metric-control" ${state.leaderboardMetricDraft ? "open" : ""}>
    <summary class="action-button">${esc(t("metric_control", "Metrics"))} ${selected.length}</summary>
    <div class="column-control-panel">
      <label>${esc(t("search", "Search"))}<input type="search" data-metric-search value="${esc(search)}"></label>
      <div class="column-control-head">${[["all", t("select_all", "Select all")], ["none", t("clear", "Clear")], ["default", t("metric_reset", "Restore defaults")]].map(([action, label]) => `<button type="button" data-metric-action="${action}">${esc(label)}</button>`).join("")}</div>
      <ol class="column-control-list">${keys.map(key => {
        const definition = definitions.find(item => item.key === key);
        const label = definition?.label || key;
        const haystack = metricSearchText(label, key);
        return `<li class="column-control-row" data-metric-row="${esc(key)}" data-metric-match="${esc(haystack)}" ${haystack.includes(search.toLocaleLowerCase()) ? "" : "hidden"}>
          <label><input type="checkbox" data-metric-id="${esc(key)}" ${selected.includes(key) ? "checked" : ""}><span>${esc(label)}</span></label>
          <small>${definition ? esc(definition.unit || "") : esc(t("metric_unavailable", "Currently unavailable"))}</small>
          <span class="column-control-moves" ${selected.includes(key) ? "" : "hidden"}>${[-1, 1].map(direction => `<button type="button" data-metric-move="${direction}" aria-label="${esc(`${direction < 0 ? t("move_earlier", "Move earlier") : t("move_later", "Move later")}: ${label}`)}" ${(direction < 0 ? selected.indexOf(key) <= 0 : selected.indexOf(key) === selected.length - 1) ? "disabled" : ""}>${direction < 0 ? "↑" : "↓"}</button>`).join("")}</span>
        </li>`;
      }).join("")}</ol>
      <p data-metric-error role="alert"></p>
      <p class="copy">${esc(t("metric_timing_note", "Recorded durations may be incomplete or overlap. Other duration covers non-model Agent records; it is not idle time."))}</p>
      ${diagnostics.length ? `<p class="copy" role="status">${diagnostics.map(esc).join("<br>")}</p>` : ""}
      <div class="column-control-foot"><span data-metric-count>${selected.length}/${METRIC_SELECTION_LIMIT}</span><button class="action-button primary" type="button" data-metric-apply>${esc(t("apply", "Apply"))}</button></div>
    </div></details>`;
}

function bindSummaryMetricControl(target, state, render) {
  const details = target.querySelector(".summary-metric-control");
  if (!details) return;
  const error = message => { details.querySelector("[data-metric-error]").textContent = message; };
  const draft = () => state.leaderboardMetricDraft || [...selectedMetricIds(state)];
  const setDraft = keys => {
    if (keys.length > METRIC_SELECTION_LIMIT) { error(t("metric_limit", "Select at most 32 metrics; narrow the selection.")); return false; }
    state.leaderboardMetricDraft = keys;
    error("");
    details.querySelectorAll("[data-metric-id]").forEach(input => { input.checked = keys.includes(input.dataset.metricId); });
    const rows = [...details.querySelectorAll("[data-metric-row]")];
    const order = [...keys, ...rows.map(row => row.dataset.metricRow).filter(key => !keys.includes(key))];
    rows.sort((a, b) => order.indexOf(a.dataset.metricRow) - order.indexOf(b.dataset.metricRow)).forEach(row => {
      const index = keys.indexOf(row.dataset.metricRow);
      row.querySelector(".column-control-moves").hidden = index < 0;
      row.querySelectorAll("[data-metric-move]").forEach(button => {
        button.disabled = index < 0 || index + Number(button.dataset.metricMove) < 0 || index + Number(button.dataset.metricMove) >= keys.length;
      });
      row.parentElement.append(row);
    });
    details.querySelector("[data-metric-count]").textContent = `${keys.length}/${METRIC_SELECTION_LIMIT}`;
    return true;
  };
  details.addEventListener("toggle", () => {
    if (!details.isConnected) return;
    if (details.open) setDraft(state.leaderboardMetricDraft || [...selectedMetricIds(state)]);
    else { setDraft([...selectedMetricIds(state)]); state.leaderboardMetricDraft = null; }
  });
  details.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    event.preventDefault(); event.stopPropagation();
    state.leaderboardMetricDraft = null; details.open = false; details.querySelector("summary").focus();
  });
  details.querySelector("[data-metric-search]").addEventListener("input", event => {
    state.leaderboardMetricSearch = event.target.value;
    const query = event.target.value.toLocaleLowerCase();
    details.querySelectorAll("[data-metric-row]").forEach(row => { row.hidden = !row.dataset.metricMatch.includes(query); });
  });
  details.querySelectorAll("[data-metric-id]").forEach(input => input.addEventListener("change", () => {
    const keys = draft();
    if (!setDraft(input.checked ? [...keys, input.dataset.metricId] : keys.filter(key => key !== input.dataset.metricId))) input.checked = false;
  }));
  details.querySelectorAll("[data-metric-action]").forEach(button => button.addEventListener("click", () => {
    const action = button.dataset.metricAction;
    setDraft(action === "none" ? [] : metricDefinitions(state).filter(item => action === "all" || item.default).map(item => item.key));
  }));
  details.querySelectorAll("[data-metric-move]").forEach(button => button.addEventListener("click", () => {
    const keys = [...draft()];
    const index = keys.indexOf(button.closest("[data-metric-row]").dataset.metricRow);
    const next = index + Number(button.dataset.metricMove);
    if (index < 0 || next < 0 || next >= keys.length) return;
    [keys[index], keys[next]] = [keys[next], keys[index]];
    setDraft(keys);
    (button.disabled ? button.closest("[data-metric-row]").querySelector("input") : button).focus();
  }));
  details.querySelector("[data-metric-apply]").addEventListener("click", () => {
    const keys = [...draft()];
    try { preflightHomeChange({ summary: { metrics: keys } }); }
    catch { error(t("metric_link_limit", "The link is too large. Reduce selected metrics or view conditions.")); return; }
    state.leaderboardSummaryMetrics = keys;
    state.leaderboardMetricDraft = null;
    render();
    target.querySelector(".summary-metric-control > summary")?.focus();
  });
}
export { renderSummaryMetricControl, bindSummaryMetricControl };
