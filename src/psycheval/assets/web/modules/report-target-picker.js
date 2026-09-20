// @ts-check
import { serveApi } from "./http.js";
import { bindingId } from "./report-library-store.js";
import { esc, t } from "./shared.js";

function createReportTargetPicker(root, { kind, selected, onChange }) {
  let page = 1;
  let search = "";
  let generation = 0;
  let timer;
  let items = [];
  let disposed = false;
  root.innerHTML = `<label class="report-binding-search"><span>${esc(t("report_search_objects", "Search objects"))}</span><input type="search" data-target-search></label>
    <div data-target-selected></div><div data-target-status role="status"></div><div data-target-items class="report-target-items"></div>
    <div class="catalog-page-controls"><button type="button" class="action-button" data-target-prev aria-label="${esc(t("previous", "Previous"))}">‹</button><span data-target-page></span><button type="button" class="action-button" data-target-next aria-label="${esc(t("next", "Next"))}">›</button></div>`;
  const status = root.querySelector("[data-target-status]");
  const input = root.querySelector("[data-target-search]");
  input.addEventListener("input", () => {
    search = /** @type {HTMLInputElement} */ (input).value;
    generation += 1;
    clearTimeout(timer);
    timer = setTimeout(() => void load(1), 150);
  });
  root.addEventListener("change", change);
  root.addEventListener("click", click);
  function change(event) {
    const key = event.target.getAttribute("data-target-key");
    if (key === null) return;
    const item = items.find(item => item.key === key);
    if (item) onChange(item, event.target.checked);
    renderSelected();
  }
  function click(event) {
    const remove = event.target.closest("[data-target-remove]");
    if (remove) {
      const item = selected().get(remove.getAttribute("data-target-remove"));
      if (item) onChange(item, false);
      renderSelected();
    }
    if (event.target.closest("[data-target-prev]")) void load(page - 1);
    if (event.target.closest("[data-target-next]")) void load(page + 1);
  }
  function renderSelected() {
    root.querySelector("[data-target-selected]").innerHTML = [...selected().values()].filter(item => item.kind === kind).map(item => `<button type="button" class="action-button compact" data-target-remove="${esc(bindingId(item))}">${esc(item.label)} ×</button>`).join("");
    root.querySelectorAll("[data-target-key]").forEach(input => {
      /** @type {HTMLInputElement} */ (input).checked = selected().has(bindingId({ kind, key: input.getAttribute("data-target-key") }));
    });
  }
  async function load(nextPage = page) {
    page = Math.max(1, nextPage);
    const request = ++generation;
    status.textContent = t("loading", "Loading");
    const params = new URLSearchParams({ kind, page: String(page), page_size: "25", search });
    try {
      const result = await serveApi(`/api/report-library/targets?${params}`);
      if (disposed || request !== generation) return;
      page = result.page;
      items = result.items;
      root.querySelector("[data-target-items]").innerHTML = items.map(item => `<label class="report-target-option"><input type="checkbox" data-target-key="${esc(item.key)}"><span>${esc(item.label)}<small>${esc(item.key)}</small></span></label>`).join("");
      root.querySelector("[data-target-prev]").toggleAttribute("disabled", page <= 1);
      root.querySelector("[data-target-next]").toggleAttribute("disabled", page * result.page_size >= result.total);
      root.querySelector("[data-target-page]").textContent = `${page} / ${Math.max(1, Math.ceil(result.total / result.page_size))} · ${result.total}`;
      status.textContent = items.length ? "" : t("report_no_objects", "No matching objects");
      renderSelected();
    } catch (error) {
      if (!disposed && request === generation) status.textContent = error.message || String(error);
    }
  }
  return { load, renderSelected, destroy() { disposed = true; generation += 1; clearTimeout(timer); root.removeEventListener("change", change); root.removeEventListener("click", click); } };
}

export { createReportTargetPicker };
