import { beginFeedback } from "./action-feedback.js";
// @ts-check

import { closeAcpDrawer, initializeAcp } from "./acp-client.js";
import { serveApi } from "./http.js";
import { closeModalSurface, openModalSurface } from "./modal-surfaces.js";
import { adminMode, t } from "./shared.js";

let bound = false;

function initializeGlobalShell() {
  if (bound) return;
  bound = true;
  document.addEventListener("keydown", event => {
    if (event.defaultPrevented || event.key !== "Escape") return;
    if (closeAcpDrawer() || closeAdminLogin()) event.preventDefault();
  });
  window.addEventListener("peval:workspace-navigate", () => {
    closeAdminLogin({ restoreFocus: false });
  });
  bindAuthenticationControls();
  document.querySelectorAll("[data-locale-select]").forEach(select => {
    const localeSelect = /** @type {HTMLSelectElement} */ (select);
    localeSelect.dataset.currentLocale = localeSelect.value;
    select.addEventListener("change", event => void changeLocale(
      /** @type {HTMLSelectElement} */ (event.target).value,
      /** @type {HTMLSelectElement} */ (event.target),
    ));
  });
  void initializeAcp();
}

function bindAuthenticationControls() {
  document.querySelectorAll("[data-admin-login-open]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      openAdminLogin(button);
    });
  });
  document.querySelectorAll("[data-admin-login-close]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      closeAdminLogin();
    });
  });
  const dialog = document.querySelector("[data-admin-login-dialog]");
  const form = dialog?.querySelector("[data-admin-login-form]");
  form?.addEventListener("submit", submitAdminLogin);
  form?.querySelectorAll('input[name="role"]').forEach(input => {
    input.addEventListener("change", () => syncLoginRoleFields(form));
  });
  if (form) syncLoginRoleFields(form);
  document.querySelectorAll("[data-admin-logout]").forEach(button => {
    button.addEventListener("click", async event => {
      event.preventDefault();
      button.setAttribute("disabled", "");
      try {
        await serveApi("/api/session", { method: "DELETE" });
        if (window.location.pathname === "/config") window.location.assign("/");
        else window.location.reload();
      } catch (error) {
        button.removeAttribute("disabled");
        setGlobalShellStatus(error.message || t("serve_logout_failed", "Log out failed"));
      }
    });
  });
}

function selectedLoginRole(form) {
  const checked = form?.querySelector?.('input[name="role"]:checked');
  if (checked) return String(checked.value || "admin");
  const hidden = form?.querySelector?.('input[name="role"]');
  return String(hidden?.value || form?.dataset?.defaultLoginRole || "admin");
}

function syncLoginRoleFields(form) {
  if (!form) return;
  const role = selectedLoginRole(form);
  const isAnnotator = role === "annotator";
  const userField = form.querySelector("[data-login-user-id-field]");
  const userInput = /** @type {HTMLInputElement | null} */ (form.querySelector('input[name="user_id"]'));
  if (userField) userField.hidden = !isAnnotator;
  if (userInput) {
    userInput.disabled = !isAnnotator;
    userInput.required = isAnnotator;
  }
  const passwordLabel = form.querySelector("[data-login-password-label]");
  if (passwordLabel) {
    passwordLabel.textContent = isAnnotator
      ? t("serve_annotator_password", "Annotator password")
      : t("serve_admin_password", "Administrator password");
  }
}

function openAdminLogin(opener = null) {
  const dialog = document.querySelector("[data-admin-login-dialog]");
  if (!dialog) return false;
  const form = dialog.querySelector("[data-admin-login-form]");
  if (form) syncLoginRoleFields(form);
  beginFeedback("[data-admin-login-status]", { key: "shell:login" }).clear();
  const status = dialog.querySelector("[data-admin-login-status]");
  if (status) {
    status.setAttribute("hidden", "");
    status.textContent = "";
  }
  const isAnnotator = selectedLoginRole(form) === "annotator";
  const focusTarget = isAnnotator
    ? dialog.querySelector('input[name="user_id"]:not([disabled])') || dialog.querySelector('[name="password"]')
    : dialog.querySelector('[name="password"]');
  openModalSurface(dialog, {
    opener,
    bodyClass: "admin-login-open",
    focusTarget,
    onRequestClose: closeAdminLogin,
  });
  return true;
}

function closeAdminLogin(options = {}) {
  return closeModalSurface(document.querySelector("[data-admin-login-dialog]"), options);
}

async function submitAdminLogin(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const role = selectedLoginRole(form);
  const formData = new FormData(form);
  const password = String(formData.get("password") || "");
  const userId = String(formData.get("user_id") || "").trim();
  const feedback = beginFeedback("[data-admin-login-status]", { key: "shell:login" });
  if (role === "annotator" && !userId) {
    feedback.error(t("serve_user_id_required", "Enter your User ID"));
    form.querySelector('[name="user_id"]')?.focus?.();
    return;
  }
  const submit = form.querySelector('[type="submit"]');
  if (submit) submit.disabled = true;
  try {
    const body = role === "annotator"
      ? { role, user_id: userId, password }
      : { role, password };
    await serveApi("/api/session", { method: "POST", body });
    window.location.reload();
  } catch (error) {
    feedback.error(error.message || t("serve_login_failed", "Login failed"));
    if (submit) submit.disabled = false;
    form.querySelector('[name="password"]')?.focus?.();
  }
}

async function changeLocale(locale, select = document.querySelector("[data-locale-select]")) {
  if (!adminMode()) return false;
  const control = /** @type {HTMLSelectElement | null} */ (select);
  const previous = control?.dataset.currentLocale || control?.value || "";
  if (control) control.disabled = true;
  setGlobalShellStatus("");
  try {
    await serveApi("/api/config");
    await serveApi("/api/config", {
      method: "PATCH",
      body: { locale },
      ifMatch: true,
      etagKey: "/api/config",
    });
    if (control) control.dataset.currentLocale = locale;
    window.location.reload();
    return true;
  } catch (error) {
    if (control) control.value = previous;
    setGlobalShellStatus(error.message || t("serve_locale_failed", "Locale change failed"));
    return false;
  } finally {
    if (control) control.disabled = false;
  }
}

function setGlobalShellStatus(message) {
  const feedback = beginFeedback("[data-global-shell-status]", { key: "shell:status" });
  if (message) feedback.error(message);
  else feedback.clear();
}

export {
  bindAuthenticationControls,
  changeLocale,
  closeAdminLogin,
  initializeGlobalShell,
  openAdminLogin,
};
