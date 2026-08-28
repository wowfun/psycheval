// @ts-check

import { RENDER_OPTIONS, t } from "./shared.js";

const adapterDefaults = { ...(RENDER_OPTIONS.adapter_defaults || {}) };

function formPayload(form) {
  const formData = new FormData(form);
  const body = {};
  for (const [key, value] of formData.entries()) {
    const text = String(value || "").trim();
    if (text) body[key] = text;
  }
  return body;
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
    if (Array.from(control.options || []).some(option => option.value === value)) control.value = value;
    return;
  }
  const radio = Array.from(form.querySelectorAll('[name="adapter"]'))
    .find(input => input.value === value);
  if (radio) radio.checked = true;
}

function defaultDbForAdapter(form) {
  const select = form?.querySelector?.('[name="adapter"]');
  const value = selectedAdapterValue(form);
  if (!select || !value) return "";
  const selected = Array.from(select.options || []).find(option => option.value === value);
  return selected?.dataset?.defaultDb || adapterDefaults[value] || "";
}

function applyDefaultDbToForm(form, options = {}) {
  const field = form?.querySelector?.('[name="db"]');
  if (!field) return "";
  const defaultDb = defaultDbForAdapter(form);
  if (defaultDb && (options.force || !String(field.value || "").trim())) field.value = defaultDb;
  return defaultDb;
}

function syncAdapterDefaultDbControls(form) {
  if (!form) return;
  const adapter = selectedAdapterValue(form);
  const path = String(form.querySelector?.('[name="db"]')?.value || "").trim();
  const save = form.querySelector?.("[data-adapter-default-db-save]");
  const clear = form.querySelector?.("[data-adapter-default-db-clear]");
  if (!save || !clear) return;
  const hasAdapter = Boolean(adapter);
  const hasDefault = Boolean(adapter && adapterDefaults[adapter]);
  save.disabled = !hasAdapter || !path;
  clear.disabled = !hasAdapter || !hasDefault;
  const title = hasAdapter ? "" : t("serve_select_adapter_for_default_db", "Select a specific adapter to manage its default DB");
  save.title = title || (!path ? t("serve_enter_db_for_default", "Enter a DB path to save as default") : "");
  clear.title = title;
}

function updateAdapterDefaults(values) {
  Object.keys(adapterDefaults).forEach(key => delete adapterDefaults[key]);
  Object.assign(adapterDefaults, values || {});
}

function showServeNotice(text, error = false) {
  const notice = document.querySelector("[data-config-page-status]");
  if (!notice) return;
  notice.textContent = text;
  notice.classList.toggle("danger", Boolean(error));
  notice.classList.toggle("loading", false);
  notice.removeAttribute("hidden");
}

export {
  applyDefaultDbToForm,
  formPayload,
  selectedAdapterValue,
  setAdapterChoice,
  showServeNotice,
  syncAdapterDefaultDbControls,
  updateAdapterDefaults,
};
