import { t } from "./shared.js";
import { beginFeedback } from "./action-feedback.js";
import { closeModalSurface, openModalSurface } from "./modal-surfaces.js";

/** Input stays mounted until the request is accepted or the user cancels. */
function openActionForm({ title, fields, submit, secondaryAction = null, opener = document.activeElement, submitLabel = t("save", "Save") }) {
  const root = document.createElement("div");
  root.className = "action-form-overlay";
  root.hidden = true;
  root.setAttribute("role", "dialog");
  root.setAttribute("aria-modal", "true");
  root.setAttribute("aria-label", title);
  const form = document.createElement("form");
  form.className = "action-form";
  const heading = document.createElement("h3");
  heading.textContent = title;
  form.append(heading);
  const inputs = {};
  for (const field of fields) {
    const label = document.createElement("label");
    label.textContent = field.label;
    const input = document.createElement(field.type === "textarea" ? "textarea" : "input");
    input.name = field.name;
    if (input.tagName === "INPUT") input.type = field.type || "text";
    input.value = field.value ?? "";
    input.required = field.required !== false;
    input.autocomplete = "off";
    if (field.min !== undefined) input.min = String(field.min);
    if (field.max !== undefined) input.max = String(field.max);
    if (field.step !== undefined) input.step = String(field.step);
    inputs[field.name] = input;
    label.append(input);
    form.append(label);
  }
  for (const field of fields) {
    if (!field.defaultFrom) continue;
    let edited = false;
    inputs[field.name].addEventListener("input", () => { edited = true; });
    inputs[field.defaultFrom].addEventListener("input", () => {
      if (!edited) inputs[field.name].value = `${field.prefix || ""}${inputs[field.defaultFrom].value.trim()}`;
    });
  }
  const status = document.createElement("div");
  status.className = "action-form-status";
  form.append(status);
  const actions = document.createElement("div");
  actions.className = "source-form-actions";
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.dataset.actionFormCancel = "true";
  cancel.className = "action-button";
  cancel.textContent = t("cancel", "Cancel");
  const save = document.createElement("button");
  save.type = "submit";
  save.className = "action-button primary";
  save.textContent = submitLabel;
  actions.append(cancel, save);
  if (secondaryAction) {
    const secondary = document.createElement("button");
    secondary.type = "button";
    secondary.className = "action-button danger";
    secondary.textContent = secondaryAction.label;
    secondary.dataset.secondaryAction = "true";
    secondary.addEventListener("click", () => submitAction(true));
    actions.prepend(secondary);
  }
  form.append(actions);
  root.append(form);
  document.body.append(root);
  let busy = false;
  let feedback = null;
  const close = () => {
    if (busy) return;
    closeModalSurface(root);
  };
  cancel.addEventListener("click", close);
  root.addEventListener("click", event => { if (event.target === root) close(); });
  root.addEventListener("keydown", event => {
    if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); close(); }
  });
  const submitAction = async secondary => {
    if (busy || (!secondary && !form.reportValidity())) return;
    for (const input of Object.values(inputs)) {
      input.removeAttribute("aria-invalid");
      input.removeAttribute("aria-describedby");
    }
    form.querySelectorAll(".action-field-error").forEach(node => node.remove());
    const values = Object.fromEntries(Object.entries(inputs).map(([name, input]) => [name, input.value]));
    busy = true;
    for (const input of Object.values(inputs)) input.readOnly = true;
    actions.querySelectorAll("button").forEach(button => { button.disabled = true; });
    form.setAttribute("aria-busy", "true");
    feedback?.dispose();
    feedback = beginFeedback(status);
    feedback.pending();
    try {
      const accepted = await (secondary ? secondaryAction.run(values) : submit(values));
      busy = false;
      if (accepted !== false) close();
      else feedback.clear();
    } catch (error) {
      feedback.error(error);
      for (const item of error.problem?.errors || []) {
        const name = String(item.pointer || "").replace(/^\//, "");
        const input = inputs[name];
        if (!input) continue;
        const message = document.createElement("p");
        message.className = "action-field-error danger";
        message.id = `action-error-${name}`;
        message.textContent = item.detail || item.message || error.message;
        input.setAttribute("aria-invalid", "true");
        input.setAttribute("aria-describedby", message.id);
        input.after(message);
      }
      form.querySelector('[aria-invalid="true"]')?.focus();
    } finally {
      busy = false;
      for (const input of Object.values(inputs)) input.readOnly = false;
      actions.querySelectorAll("button").forEach(button => { button.disabled = false; });
      form.removeAttribute("aria-busy");
    }
  };
  form.addEventListener("submit", event => {
    event.preventDefault();
    void submitAction(false);
  });
  openModalSurface(root, {
    opener, focusTarget: form.querySelector("input, textarea"),
    onClose: () => { feedback?.dispose(); root.remove(); },
  });
  return root;
}

export { openActionForm };
