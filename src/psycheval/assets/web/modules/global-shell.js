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
    if (closeAcpDrawer()) return;
    closeAdminLogin();
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
  dialog?.addEventListener("click", event => {
    if (event.target === dialog) closeAdminLogin();
  });
  dialog?.querySelector("[data-admin-login-form]")?.addEventListener("submit", submitAdminLogin);
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

function openAdminLogin(opener = null) {
  const dialog = document.querySelector("[data-admin-login-dialog]");
  if (!dialog) return false;
  const status = dialog.querySelector("[data-admin-login-status]");
  if (status) {
    status.setAttribute("hidden", "");
    status.textContent = "";
  }
  openModalSurface(dialog, {
    opener,
    bodyClass: "admin-login-open",
    focusTarget: dialog.querySelector('[name="password"]'),
  });
  return true;
}

function closeAdminLogin(options = {}) {
  return closeModalSurface(document.querySelector("[data-admin-login-dialog]"), options);
}

async function submitAdminLogin(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const password = String(new FormData(form).get("password") || "");
  const status = form.querySelector("[data-admin-login-status]");
  const submit = form.querySelector('[type="submit"]');
  if (submit) submit.disabled = true;
  try {
    await serveApi("/api/session", { method: "POST", body: { password } });
    window.location.reload();
  } catch (error) {
    if (status) {
      status.textContent = error.message || t("serve_login_failed", "Login failed");
      status.classList.add("danger");
      status.hidden = false;
    }
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
  const status = document.querySelector("[data-global-shell-status]");
  if (!status) return;
  status.textContent = message || "";
  status.toggleAttribute("hidden", !message);
}

export {
  bindAuthenticationControls,
  changeLocale,
  closeAdminLogin,
  initializeGlobalShell,
  openAdminLogin,
};
