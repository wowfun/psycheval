import { RENDER_OPTIONS, SUBMENU_DETAILS_SELECTOR, adapterDefaults, adminMode, closeOpenSubmenus, renderComparisonPanels, selectedKey, serveMode, state, t } from "./runtime.js";
import { addSelectedDbSessions, choosePathSourceFiles, inspectDbSessions, submitServeSourceForm } from "./configuration.js";
import { selectedAdapterValue, serveApi, setServeStatus, showServeNotice } from "./serve-effects.js";
import { refreshServeReportFromServer, refreshServeSourcesFromServer } from "./serve-catalog.js";
import { bindWorkspaceReportGlobalControls, closeWorkspaceReportReader, workspaceReportBindingsChanged } from "./workspace-reports.js";
import { bindWorkspaceViewDialog, closeWorkspaceViewSaveDialog } from "./workspace-views.js";
import { beginNotesEdit, cancelNotesEdit, saveSelectedNotes } from "./analysis-notes.js";
import { closeModalSurface, openModalSurface } from "./modal-surfaces.js";
import { bindHarborWorkbench, confirmDiscard, isHarborDirty } from "./harbor-workbench.js";
import { closeAcpDrawer, initializeAcp } from "./acp-client.js";

function bindGlobalControls() {
  if (state.boundGlobalControls) return;
  document.addEventListener("keydown", event => {
    if (event.defaultPrevented) return;
    if (event.key === "Escape" && closeAcpDrawer()) {
      return;
    }
    if (event.key === "Escape" && closeAdminLogin()) {
      return;
    }
    if (event.key === "Escape" && closeWorkspaceViewSaveDialog()) {
      return;
    }
    if (event.key === "Escape" && closeWorkspaceReportReader()) {
      return;
    }
    if (event.key !== "Escape" || !state.selectedStep) return;
    state.selectedStep = null;
    renderComparisonPanels();
  });
  document.addEventListener("click", event => {
    closeOpenSubmenus(event.target?.closest?.(SUBMENU_DETAILS_SELECTOR) || null);
  }, true);
  document.addEventListener("click", event => {
    const link = event.target?.closest?.(".workspace-nav-link[href]");
    if (!link) return;
    if (isHarborDirty() && !confirmDiscard()) {
      event.preventDefault();
      return;
    }
    if (workspaceReportBindingsChanged() && !window.confirm(t("report_discard_bindings", "Discard unsaved report binding changes?"))) {
      event.preventDefault();
    }
  });
  document.addEventListener("click", event => {
    if (!state.selectedStep) return;
    const target = event.target;
    if (target?.closest?.("#step-drawer") || target?.closest?.("#workspace-report-reader") || target?.closest?.("[data-report-manager]") || target?.closest?.("[data-workspace-report-control]") || target?.closest?.("[data-config-page]") || target?.closest?.("[data-harbor-workbench]") || target?.closest?.("[data-step]") || target?.closest?.("[data-step-action]") || target?.closest?.("[data-step-id]") || target?.closest?.("[data-timeline-step-id]") || target?.closest?.("[data-timeline-chart]")) return;
    state.selectedStep = null;
    renderComparisonPanels();
  });
  document.addEventListener("click", event => {
    if (!adminMode()) return;
    const editButton = event.target?.closest?.("[data-notes-edit]");
    if (editButton) {
      event.preventDefault();
      beginNotesEdit(editButton.dataset.trialKey || selectedKey());
      return;
    }
    const cancelButton = event.target?.closest?.("[data-notes-cancel]");
    if (cancelButton) {
      event.preventDefault();
      cancelNotesEdit();
      return;
    }
    const saveButton = event.target?.closest?.("[data-notes-save]");
    if (saveButton) {
      event.preventDefault();
      saveSelectedNotes(saveButton);
    }
  });
  window.addEventListener("resize", () => {
    if (state.timelineChart) state.timelineChart.resize();
  });
  if (serveMode()) {
    bindServeSourceControls();
    bindWorkspaceViewDialog();
  }
  state.boundGlobalControls = true;
}
function bindServeSourceControls() {
  initializeAcp();
  bindAuthenticationControls();
  bindWorkspaceReportGlobalControls();
  bindHarborWorkbench();
  document.querySelectorAll("[data-refresh-all]").forEach(button => {
    button.addEventListener("click", () => refreshServeReportFromServer({ refresh: true }));
  });
  document.querySelectorAll("[data-refresh-sources]").forEach(button => {
    button.addEventListener("click", () => refreshServeSourcesFromServer());
  });
  document.querySelectorAll("[data-locale-select]").forEach(select => {
    select.addEventListener("change", event => {
      changeServeLocale(event.target.value);
    });
  });
  document.querySelectorAll("[data-source-add-form]").forEach(form => {
    form.addEventListener("submit", event => {
      event.preventDefault();
      submitServeSourceForm(form);
    });
  });
  document.querySelectorAll("[data-path-picker]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      choosePathSourceFiles(button);
    });
  });
  document.querySelectorAll("[data-db-inspect]").forEach(button => {
    button.addEventListener("click", event => {
      event.preventDefault();
      inspectDbSessions(button.closest("[data-source-add-form]"));
    });
  });
  document.querySelectorAll("[data-db-session-picker]").forEach(picker => {
    picker.addEventListener("click", event => {
      const button = event.target?.closest?.("[data-db-add-selected]");
      if (!button) return;
      event.preventDefault();
      addSelectedDbSessions(button.closest("[data-source-add-form]"));
    });
  });
  bindAdapterDefaultDbControls();
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
  dialog?.addEventListener?.("click", event => {
    if (event.target === dialog) closeAdminLogin();
  });
  dialog?.querySelector?.("[data-admin-login-form]")?.addEventListener("submit", submitAdminLogin);
  document.querySelectorAll("[data-admin-logout]").forEach(button => {
    button.addEventListener("click", async event => {
      event.preventDefault();
      button.disabled = true;
      try {
        await serveApi("/api/auth/logout", { method: "POST", body: {} });
        if (RENDER_OPTIONS?.serve_page === "config") window.location.assign("/");
        else window.location.reload();
      } catch (error) {
        button.disabled = false;
        setServeStatus(error.message || String(error), true);
      }
    });
  });
}
function openAdminLogin(opener = null) {
  const dialog = document.querySelector("[data-admin-login-dialog]");
  if (!dialog) return false;
  const status = dialog.querySelector("[data-admin-login-status]");
  if (status) {
    status.hidden = true;
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
    await serveApi("/api/auth/login", { method: "POST", body: { password } });
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
async function changeServeLocale(locale) {
  if (!adminMode()) return;
  try {
    await serveApi("/api/config/locale", {
      method: "POST",
      body: { locale }
    });
    window.location.reload();
  } catch (error) {
    setServeStatus(error.message || String(error), true);
  }
}
function bindAdapterDefaultDbControls() {
  document.querySelectorAll("[data-source-add-form][data-source-kind=\"db\"]").forEach(form => {
    const select = form.querySelector("[name=\"adapter\"]");
    const field = dbFieldFor(form);
    const saveButton = form.querySelector("[data-adapter-default-db-save]");
    const clearButton = form.querySelector("[data-adapter-default-db-clear]");
    if (!select || !field || !saveButton || !clearButton) return;
    select.addEventListener("change", () => {
      applyDefaultDbToForm(form, { force: true });
      syncAdapterDefaultDbControls(form);
    });
    field.addEventListener("input", () => syncAdapterDefaultDbControls(form));
    saveButton.addEventListener("click", event => {
      event.preventDefault();
      saveAdapterDefaultDb(form, String(field.value || "").trim());
    });
    clearButton.addEventListener("click", event => {
      event.preventDefault();
      saveAdapterDefaultDb(form, "");
    });
    applyDefaultDbToForm(form);
    syncAdapterDefaultDbControls(form);
  });
}
function syncAdapterDefaultDbControls(form) {
  const adapter = selectedAdapterValue(form);
  const field = dbFieldFor(form);
  const saveButton = form?.querySelector?.("[data-adapter-default-db-save]");
  const clearButton = form?.querySelector?.("[data-adapter-default-db-clear]");
  if (!field || !saveButton || !clearButton) return;
  const path = String(field.value || "").trim();
  const hasAdapter = Boolean(adapter);
  const hasDefault = Boolean(adapter && adapterDefaults()[adapter]);
  saveButton.disabled = !hasAdapter || !path;
  clearButton.disabled = !hasAdapter || !hasDefault;
  const adapterTitle = hasAdapter ? "" : t("serve_select_adapter_for_default_db", "Select a specific adapter to manage its default DB");
  saveButton.title = adapterTitle || (!path ? t("serve_enter_db_for_default", "Enter a DB path to save as default") : "");
  clearButton.title = adapterTitle;
}
function syncAllAdapterDefaultDbControls() {
  document.querySelectorAll("[data-source-add-form][data-source-kind=\"db\"]").forEach(syncAdapterDefaultDbControls);
}
async function saveAdapterDefaultDb(form, defaultDbPath) {
  if (!adminMode()) return false;
  const adapter = selectedAdapterValue(form);
  if (!adapter) {
    const message = t("serve_select_adapter_for_default_db", "Select a specific adapter to manage its default DB");
    setServeStatus(message, true);
    showServeNotice(message, true);
    syncAdapterDefaultDbControls(form);
    return false;
  }
  try {
    const payload = await serveApi("/api/config/adapter-default-db", {
      method: "POST",
      body: {
        adapter,
        default_db_path: String(defaultDbPath || "").trim()
      }
    });
    state.adapterDefaults = payload?.adapter_defaults && typeof payload.adapter_defaults === "object"
      ? { ...payload.adapter_defaults }
      : { ...adapterDefaults(), [adapter]: payload?.default_db_path || "" };
    if (!payload?.default_db_path) delete state.adapterDefaults[adapter];
    updateAdapterDefaultOptions();
    applyUpdatedAdapterDefaultToDbForms(adapter);
    syncAllAdapterDefaultDbControls();
    const message = payload?.default_db_path
      ? t("serve_adapter_default_db_saved", "Adapter default DB saved")
      : t("serve_adapter_default_db_cleared", "Adapter default DB cleared");
    setServeStatus(message);
    showServeNotice(message);
    return true;
  } catch (error) {
    setServeStatus(error.message || String(error), true);
    showServeNotice(error.message || String(error), true);
    syncAllAdapterDefaultDbControls();
    return false;
  }
}
function updateAdapterDefaultOptions() {
  document.querySelectorAll("select[name=\"adapter\"] option").forEach(option => {
    const defaultDb = adapterDefaults()[option.value] || "";
    if (defaultDb) {
      option.dataset.defaultDb = defaultDb;
    } else {
      delete option.dataset.defaultDb;
    }
  });
}
function applyUpdatedAdapterDefaultToDbForms(adapter) {
  document.querySelectorAll("[data-source-add-form][data-source-kind=\"db\"]").forEach(form => {
    const selected = selectedAdapterValue(form);
    applyDefaultDbToForm(form, { force: Boolean(selected && selected === adapter) });
    syncAdapterDefaultDbControls(form);
  });
}
function dbFieldFor(form) {
  return form?.querySelector?.("[name=\"db\"]") || null;
}
function defaultDbForAdapter(form) {
  const select = form?.querySelector?.("[name=\"adapter\"]");
  const value = selectedAdapterValue(form);
  if (!select || !value) return "";
  const selected = Array.from(select.options || []).find(option => option.value === value);
  return selected?.dataset?.defaultDb || adapterDefaults()[value] || "";
}
function applyDefaultDbToForm(form, options = {}) {
  const field = dbFieldFor(form);
  if (!field) return "";
  const defaultDb = defaultDbForAdapter(form);
  if (defaultDb && (options.force || !String(field.value || "").trim())) {
    field.value = defaultDb;
  }
  return defaultDb;
}
export {
  applyDefaultDbToForm,
  applyUpdatedAdapterDefaultToDbForms,
  bindAdapterDefaultDbControls,
  bindAuthenticationControls,
  bindGlobalControls,
  bindServeSourceControls,
  changeServeLocale,
  closeAdminLogin,
  dbFieldFor,
  defaultDbForAdapter,
  openAdminLogin,
  saveAdapterDefaultDb,
  syncAdapterDefaultDbControls,
  syncAllAdapterDefaultDbControls,
  updateAdapterDefaultOptions,
};
