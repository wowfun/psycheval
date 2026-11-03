// @ts-check
import { openModalSurface, closeModalSurface } from "./modal-surfaces.js";
import { esc, t } from "./shared.js";

let pickerSequence = 0;

function candidateLabel(item) {
  const labels = {
    source: ["acp_reference_source", "Source"],
    task: ["acp_reference_task", "Current Task and Dataset"],
    report: ["acp_reference_report", "Report (read-only)"],
    canonical_report: ["acp_reference_canonical_report", "Canonical report"],
    associations: ["acp_reference_associations", "Associated sources"],
    truncated: ["acp_reference_truncated", "More associated sources"],
  };
  const label = labels[item.label_key];
  return label ? t(...label) : item.label;
}

/** Returns selected plain text; neither persists selection nor edits the composer. */
function chooseReferences(items, signal) {
  if (signal.aborted) return Promise.resolve(undefined);
  return new Promise(resolve => {
    const root = document.createElement("div");
    root.className = "action-form-overlay acp-reference-picker";
    root.hidden = true;
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-label", t("acp_references", "Workbench references"));
    const prefix = `acp-reference-${++pickerSequence}`;
    root.innerHTML = `<form class="action-form">
      <h3>${esc(t("acp_references", "Workbench references"))}</h3>
      ${items.map((item, index) => `<div class="acp-reference-choice"><label><input type="checkbox" value="${index}" aria-describedby="${prefix}-${index}" ${item.selected && item.text ? "checked" : ""} ${item.text ? "" : "disabled"}> <span>${esc(candidateLabel(item))}</span></label>
        ${item.reason ? `<small id="${prefix}-${index}">${esc(item.id === "truncated" ? t("acp_reference_truncated_hint", "Only the first 64 associated sources are shown; select a source directly for further references.") : item.reason)}</small>` : `<pre id="${prefix}-${index}">${esc(item.text)}</pre>`}</div>`).join("")}
      ${items.some(item => item.text) ? "" : `<p role="status">${esc(t("acp_references_unavailable", "No references are available for this object."))}</p>`}
      <div class="source-form-actions"><button type="button" data-reference-cancel>${esc(t("cancel", "Cancel"))}</button><button type="submit">${esc(t("acp_insert_references", "Insert references"))}</button></div>
    </form>`;
    const owner = document.querySelector("[data-acp-drawer]") || document.body;
    owner.append(root);
    let result;
    const finish = () => { signal.removeEventListener("abort", abort); root.remove(); resolve(result); };
    const abort = () => { if (!closeModalSurface(root)) finish(); };
    signal.addEventListener("abort", abort, { once: true });
    root.addEventListener("keydown", event => {
      if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); closeModalSurface(root); }
    });
    root.querySelector("[data-reference-cancel]").addEventListener("click", abort);
    const submit = /** @type {HTMLButtonElement} */ (root.querySelector('button[type="submit"]'));
    const updateSelection = () => { submit.disabled = !root.querySelector("input:checked:not(:disabled)"); };
    root.addEventListener("change", updateSelection);
    updateSelection();
    root.querySelector("form").addEventListener("submit", event => {
      event.preventDefault();
      const selected = [...root.querySelectorAll("input:checked")].map(input => items[Number(/** @type {HTMLInputElement} */ (input).value)].text);
      if (!selected.length) return;
      result = selected.join("\n\n");
      closeModalSurface(root);
    });
    const active = document.activeElement;
    openModalSurface(root, {
      opener: active?.shadowRoot?.activeElement || active,
      focusTarget: root.querySelector("input:not(:disabled),button"),
      onClose: finish,
    });
  });
}

export { chooseReferences };
