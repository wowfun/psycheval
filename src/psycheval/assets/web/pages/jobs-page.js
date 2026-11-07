// @ts-check

import { noteColumn, reportsColumn, createCollectionSidebar } from "../modules/collection-ui.js";
import { createRegistryManager } from "../modules/registry-manager.js";
import { taskColumns, renderTaskTable } from "../modules/task-table.js";
import { createTaskBrowser } from "../modules/harbor-task-browser.js";
import { applyDataTableControls, bindDataTableControls, bindTableRowActivation, renderDataTable, selectionColumn } from "../modules/data-tables.js";
import { beginFeedback } from "../modules/action-feedback.js";
import { watchOperation } from "../modules/operation-feedback.js";
import { serveApi } from "../modules/http.js";
import { adminMode, t } from "../modules/shared.js";
import { invalidateWorkspace } from "../app/workspace-runtime.js";

const ACTIVE = new Set(["preparing", "running", "stopping"]);
const identity = () => Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, "0")).join("");
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function parseEntries(entries) {
  const result = {};
  for (const { key, type, value } of entries) {
    if (!key.trim() && !value.trim()) continue;
    const parts = key.trim().split(".");
    if (parts.some(part => !part || ["__proto__", "prototype", "constructor"].includes(part))) throw new Error(`Invalid key: ${key}`);
    let target = result;
    for (const part of parts.slice(0, -1)) {
      if (Object.hasOwn(target, part) && (target[part] === null || typeof target[part] !== "object" || Array.isArray(target[part]))) throw new Error(`Conflicting key: ${key}`);
      target = target[part] ??= {};
    }
    const leaf = parts.at(-1);
    if (Object.hasOwn(target, leaf)) throw new Error(`Duplicate key: ${key}`);
    let parsed = value;
    if (type !== "string") {
      parsed = JSON.parse(value);
      if (type === "number" && (typeof parsed !== "number" || !Number.isFinite(parsed))) throw new Error(`Invalid number: ${key}`);
      if (type === "boolean" && typeof parsed !== "boolean") throw new Error(`Invalid boolean: ${key}`);
    }
    target[leaf] = parsed;
  }
  return result;
}

function flattenEntries(value, prefix = "") {
  return Object.entries(value || {}).flatMap(([key, item]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (item && typeof item === "object" && !Array.isArray(item) && Object.keys(item).length) return flattenEntries(item, path);
    const type = typeof item === "string" ? "string" : typeof item === "number" ? "number" : typeof item === "boolean" ? "boolean" : "json";
    return [{ key: path, type, value: type === "string" ? item : JSON.stringify(item) }];
  });
}

function summarizeVariants(results) {
  const groups = new Map();
  for (const result of results) {
    const key = result.variant_id || "";
    const group = groups.get(key) || { id: key, label: result.variant_label || key, count: 0, scored: 0, total: 0 };
    group.count++;
    if (typeof result.score === "number" && Number.isFinite(result.score)) { group.scored++; group.total += result.score; }
    groups.set(key, group);
  }
  return [...groups.values()].map(group => ({ ...group, mean: group.scored ? group.total / group.scored : null }));
}

/** @param {import("../app/workspace-app.js").PageLoaderContext} context */
function createJobsPage({ root, app }) {
  let jobSidebar = null, taskSidebar = null, registryManager = null, taskBrowser = null;
  let selectedJob = null, selectedTaskKey = null, showArchived = false, jobsSearch = "", renderedJobs = null;
  const jobSelection = new Set();
  const q = selector => root.querySelector(selector) || jobSidebar?.root.querySelector(selector);
  const nodes = selector => /** @type {any[]} */ ([...root.querySelectorAll(selector), ...(jobSidebar?.root.querySelectorAll(selector) || [])]);
  let initialized = false, disposed = false, generation = 0, selectionGeneration = 0;
  let timer = null;
  let options = null, datasets = [], harness = "harbor", variants = [], selected = new Set();
  let preview = null, selectedRun = null, runs = [], requestId = identity();
  let renderedRun = null, renderedDetail = null;
  let renderedLog = null, logFollowing = true;
  let logPosition = [0, 0];
  let changed = false, busy = false, composerReady = false, harnessLoading = false;
  let variantFilter = "";
  let resultOffset = 0;
  const labels = { unfinished: t("jobs_unfinished_native_record", "Unfinished native record"), unknown: t("jobs_unknown", "Unknown"), preparing: t("jobs_preparing", "Preparing"), running: t("acp_phase_running", "Running"), stopping: t("jobs_stopping", "Stopping"), completed: t("status.completed", "Completed"), failed: t("jobs_failed", "Failed"), cancelled: t("acp_agent_cancelled", "Cancelled"), interrupted: t("jobs_interrupted", "Interrupted") };
  const stateLabel = value => labels[value] || value;

  function notify(text, error = false) {
    const node = q("[data-jobs-notice]");
    node.textContent = text;
    node.hidden = !text;
    node.classList.toggle("error", error);
  }
  function invalidated() {
    preview = null; changed = true; requestId = identity();
    updateComposer();
    q("[data-job-preview-output]").hidden = true;
  }
  function updateComposer() {
    q("[data-job-start]").disabled = busy || !composerReady || !adminMode();
    for (const node of nodes("[data-job-preview], [data-job-save-defaults]")) node.disabled = busy || !composerReady;
    q("[data-job-harness]").disabled = busy || harnessLoading;
  }
  function entryRow(entry = { key: "", type: "string", value: "" }) {
    return `<div class="job-kv-row"><input data-kv-key aria-label="${t("jobs_configuration_key", "Configuration key")}" value="${esc(entry.key)}" placeholder="kwargs.temperature"><select data-kv-type aria-label="${t("jobs_value_type", "Value type")}">${["string", "number", "boolean", "json"].map(type => `<option ${type === entry.type ? "selected" : ""}>${type}</option>`).join("")}</select><input data-kv-value aria-label="${t("jobs_configuration_value", "Configuration value")}" value="${esc(entry.value)}"><button type="button" class="action-button" data-remove-entry aria-label="${t("jobs_remove_setting", "Remove setting")}">×</button></div>`;
  }
  function editor(value, name) {
    return `<div class="job-kv" data-kv="${esc(name)}"><div data-kv-rows>${flattenEntries(value).map(entry => entryRow(entry)).join("")}</div><button type="button" class="action-button" data-add-entry>${t("jobs_add_setting", "Add setting")}</button></div>`;
  }
  function readEditor(node) {
    return parseEntries([...node.querySelectorAll(".job-kv-row")].map(row => ({ key: row.querySelector("[data-kv-key]").value, type: row.querySelector("[data-kv-type]").value, value: row.querySelector("[data-kv-value]").value })));
  }
  function readVariants() {
    return nodes("[data-variant]").map(node => ({
      id: node.dataset.variant, label: node.querySelector("[data-variant-label]").value,
      agent: node.querySelector("[data-variant-agent]").value, model: node.querySelector("[data-variant-model]").value,
      options: readEditor(node.querySelector("[data-kv]")),
    }));
  }
  function request() {
    const settings = readEditor(q('[data-kv="settings"]'));
    for (const input of nodes("[data-job-setting]")) {
      if (Object.hasOwn(settings, input.dataset.jobSetting)) throw new Error(t("jobs_edit_basic_fields_above", "Edit basic fields above"));
      const value = Number(input.value);
      if (!input.value.trim() || !Number.isFinite(value) || value <= 0 || (input.dataset.jobSetting !== "timeout_multiplier" && !Number.isInteger(value))) throw new Error(t("jobs_basic_settings_require_valid_positive_numbers", "Basic settings require valid positive numbers"));
      settings[input.dataset.jobSetting] = value;
    }
    return { harness, tasks: [...selected], variants: readVariants(), settings };
  }
  function renderVariants() {
    q("[data-job-variants]").innerHTML = variants.map(variant => `<section class="job-variant" data-variant="${esc(variant.id)}"><div class="job-variant-fields"><label>${t("jobs_variant", "Variant")}<input data-variant-label value="${esc(variant.label)}"></label><label>Agent<input data-variant-agent list="jobs-agents" value="${esc(variant.agent)}" placeholder="opencode"></label><label>Model<input data-variant-model list="jobs-models" value="${esc(variant.model)}" placeholder="provider/model"></label><button type="button" class="action-button" data-copy-variant>${t("jobs_duplicate", "Duplicate")}</button><button type="button" class="action-button" data-remove-variant ${variants.length === 1 ? "disabled" : ""}>${t("jobs_remove", "Remove")}</button></div><details><summary>${t("jobs_variant_settings", "Variant settings")}</summary>${editor(variant.options, variant.id)}</details></section>`).join("");
  }
  function taskRows() {
    return datasets.flatMap(dataset => dataset.tasks.map(task => ({
      key: task.id, datasetId: dataset.id, taskName: task.label, packageName: task.package_name,
      status: task.available === false ? "unavailable" : "registered", diagnostics: task.error || "",
      available: task.available !== false,
      taskRef: harness === "harbor" ? { dataset_id: dataset.id, task: task.id.slice(dataset.id.length + 1) } : null,
    })));
  }
  function renderTasks() {
    const columns = taskColumns({ selection: selectionColumn({ key: "__run_task_select",
      selectionKey: row => row.key, selectionSet: () => selected, selectable: row => row.available,
      rowAriaLabel: (_key, row) => `${t("select", "Select")}: ${row.taskName}`,
    }) });
    renderTaskTable({ root: q("[data-job-tasks]"), tableId: "job-task-selection", allRows: taskRows(), columns,
      search: q("[data-job-search]").value, selectedKey: selectedTaskKey,
      onChange: renderTasks, onSelectionChange: () => { invalidated(); renderTasks(); },
      onActivate: async (row, node) => {
        selectedTaskKey = row.key;
        taskSidebar.root.querySelector(".detail-sidebar-head h2").textContent = row.taskName;
        taskSidebar.open({ opener: node, openerSelector: `[data-task-row-token="${encodeURIComponent(row.key)}"]` });
        renderTasks();
        await taskBrowser.loadTask(row.taskRef);
      },
    });
    q("[data-job-task-count]").textContent = `${selected.size} ${t("jobs_tasks_selected", "Tasks selected")}`;
  }
  function filterTasks() { renderTasks(); }
  async function loadHarness(useDefaults = true) {
    composerReady = false; harnessLoading = true; updateComposer();
    const epoch = ++generation;
    try {
      const data = await serveApi(`/api/jobs/tasks/${encodeURIComponent(harness)}`);
      if (epoch !== generation || disposed) return;
      datasets = data.datasets;
      const description = options.harnesses.find(item => item.id === harness);
      if (!description) throw new Error(t("jobs_harness_is_unavailable_reload_the_page", "Harness is unavailable; reload the page"));
      if (useDefaults) {
        const defaults = { ...description.defaults, ...description.saved_defaults };
        variants = structuredClone(defaults.variants || [{ id: "a", label: "A", agent: "", model: "", options: {} }]);
        selected = new Set(defaults.tasks || []);
        const settings = { ...(description.defaults?.settings || {}), ...(description.saved_defaults?.settings || {}) };
        for (const input of nodes("[data-job-setting]")) {
          input.value = settings[input.dataset.jobSetting] ?? 1;
          delete settings[input.dataset.jobSetting];
        }
        q("[data-job-settings]").innerHTML = editor(settings, "settings");
        renderVariants();
      }
      q("#jobs-agents").innerHTML = (description.agents || []).map(value => `<option value="${esc(value)}"></option>`).join("");
      q("#jobs-models").innerHTML = (description.models || []).map(value => `<option value="${esc(value)}"></option>`).join("");
      renderTasks();
      composerReady = true;
    } finally {
      if (epoch === generation && !disposed) { harnessLoading = false; updateComposer(); }
    }
  }
  function renderRuns(force = false) {
    const target = q("[data-jobs-list]");
    if (!force && target.querySelector("[data-table-cell-editor]")) return;
    const signature = JSON.stringify([runs, selectedJob, showArchived, jobsSearch, [...jobSelection]]);
    if (!force && signature === renderedJobs) return;
    renderedJobs = signature;
    const columns = [
      ...(adminMode() ? [selectionColumn({ key: "__job_select", selectionKey: row => row.id, selectionSet: () => jobSelection,
        selectable: row => row.archived || row.can_archive })] : []),
      { key: "name", label: "Job", valueType: "identity", sortable: true, filterable: true, value: row => row.name },
      { key: "harness", label: "Harness", valueType: "identity", sortable: true, filterable: true, value: row => row.harness },
      { key: "status", label: t("report_state", "Status"), valueType: "status", sortable: true, filterable: true, value: row => row.state_error ? t("harbor_status_unavailable", "Unavailable") : stateLabel(row.state), cellTitle: row => row.state_error || stateLabel(row.state) },
      { key: "trials", label: "Trials", valueType: "number", sortable: true, value: row => row.trial_count,
        cellTitle: row => row.count_retained ? t("jobs_root_trial_count_retained_at_archival", "Root Trial count retained at archival") : t("jobs_discovered_root_trial_count", "Discovered root Trial count") },
      noteColumn("job", row => { const current = runs.find(item => item.id === row.id); if (current) Object.assign(current, { note: row.note, collection_revision: row.collection_revision }); }),
      reportsColumn("job"),
      ...(adminMode() ? [
        { key: "path", label: t("jobs_path", "Path"), valueType: "path", value: row => row.path },
        { key: "mounts", label: t("jobs_mounts", "Mounts"), valueType: "list", value: row => row.mount_ids },
        { key: "archived", label: t("jobs_archived", "Archived"), valueType: "status", value: row => row.archived ? t("acp_archived", "Archived") : t("report_state_active", "Active") },
        { key: "actions", label: t("jobs_manage", "Manage"), value: () => "", html: row => `<button class="action-button" data-job-archive="${esc(row.id)}" ${row.archived || row.can_archive ? "" : "disabled"} title="${esc(row.can_archive || row.archived ? "" : t("jobs_only_jobs_with_verified_terminal_state_can_be_archived", "Only Jobs with verified terminal state can be archived"))}">${row.archived ? t("jobs_restore", "Restore") : t("jobs_archive", "Archive")}</button>` },
      ] : []),
    ];
    const filtered = runs.filter(row => !jobsSearch || `${row.name} ${row.harness} ${row.note || ""}`.toLowerCase().includes(jobsSearch.toLowerCase()));
    const rows = applyDataTableControls("job-collections", filtered, columns, runs);
    target.innerHTML = renderDataTable({ tableId: "job-collections", columns, rows, rowKey: row => row.id, filterOptionsRows: runs,
      rowAttrs: row => `tabindex="0" data-select-job="${esc(row.id)}" data-job-row-token="${encodeURIComponent(row.id)}"`, rowClass: row => row.id === selectedJob ? "selected-row" : "",
      emptyText: t("jobs_no_jobs_start_a_run_or_mount_retained_results", "No Jobs. Start a run or mount retained results."),
    });
    bindDataTableControls(target, { tableId: "job-collections", columns, rows, rowKey: row => row.id, onChange: () => renderRuns(true), onSelectionChange: () => renderRuns(true) });
    target.querySelectorAll("[data-select-job]").forEach(node => bindTableRowActivation(node, () => guarded(() => selectCollection(node.dataset.selectJob, node))));
    for (const button of nodes("[data-jobs-archive-selected], [data-jobs-restore-selected]")) button.disabled = !runs.some(row => jobSelection.has(row.id) && (button.matches("[data-jobs-restore-selected]") ? row.archived : !row.archived && row.can_archive));
  }
  async function selectCollection(id, opener) {
    const row = runs.find(item => item.id === id);
    if (!row) return;
    if (selectedJob !== id) { resultOffset = 0; variantFilter = ""; }
    selectedJob = id;
    selectedRun = row.run_id;
    jobSidebar.open({ opener, openerSelector: `[data-job-row-token="${encodeURIComponent(id)}"]` });
    renderRuns();
    if (selectedRun) await selectRun(selectedRun);
    else {
      renderedRun = null; renderedDetail = null; renderedLog = null;
      const epoch = ++selectionGeneration;
      const detail = await serveApi(`/api/collections/jobs/${encodeURIComponent(id)}?offset=${resultOffset}`);
      if (disposed || epoch !== selectionGeneration || selectedJob !== id) return;
      const pane = q("[data-job-detail]"); pane.hidden = false;
      pane.innerHTML = `<header class="jobs-heading"><h3>${esc(detail.name)}</h3><span>${esc(stateLabel(detail.state))}</span></header><p>${esc(row.trial_count ?? "—")} Trials${row.archived ? ` · ${t("jobs_archived_restore_to_browse_trials", "Archived; restore to browse Trials")}` : ""}</p><div class="job-results">${detail.results.map(result => `<div class="job-result job-result-external"><strong>${esc(result.task || result.trial_name || "—")}</strong><span>${esc(result.score ?? "—")}</span><a href="/?source=${encodeURIComponent(result.source_key)}" data-workspace-route="home">${t("jobs_view_trial", "View Trial")}</a></div>`).join("")}</div>${detail.result_count > 50 ? `<div class="jobs-actions"><button class="action-button" data-job-page="previous" ${resultOffset === 0 ? "disabled" : ""}>${t("previous", "Previous")}</button><span>${Math.min(resultOffset + 1, detail.result_count)}–${Math.min(resultOffset + 50, detail.result_count)} / ${detail.result_count}</span><button class="action-button" data-job-page="next" ${resultOffset + 50 >= detail.result_count ? "disabled" : ""}>${t("next", "Next")}</button></div>` : ""}`;
    }
  }
  async function archiveJobs(rows, archived) {
    const operation = await serveApi("/api/collections/job-state-operations", { method: "POST", body: {
      archived, items: rows.map(row => ({ id: row.id, revision: row.collection_revision })),
    } });
    const feedback = beginFeedback(q("[data-jobs-collection]"), { page: "jobs", key: "jobs:archive" });
    await watchOperation(operation.id, { feedback,
      async onComplete(result) {
        const successful = new Set(result.successes.map(item => rows[item.index]?.id));
        if (successful.has(selectedJob)) { jobSidebar.close(); selectedJob = null; selectedRun = null; }
        for (const id of successful) jobSelection.delete(id);
        invalidateWorkspace(["catalog", "reports", "collections"]); await refreshRuns();
      },
    });
  }
  function updateLogFollowing() {
    const button = q("[data-job-log-latest]");
    if (button) button.hidden = logFollowing;
  }
  function restoreLogPosition() {
    const log = q(".job-log");
    if (!log?.clientHeight) return;
    log.scrollTop = logFollowing ? log.scrollHeight : logPosition[0];
    log.scrollLeft = logPosition[1];
  }
  function renderLog(logs, sameRun) {
    const log = q(".job-log");
    if (!sameRun) { renderedLog = null; logFollowing = true; logPosition = [0, 0]; }
    const signature = JSON.stringify(logs);
    if (signature === renderedLog) return;
    const fragment = document.createDocumentFragment();
    for (const entry of logs.entries) {
      const node = document.createElement("pre");
      node.className = "job-log-entry";
      node.dataset.logFormat = entry.format;
      node.textContent = entry.text;
      fragment.append(node);
    }
    if (!logs.entries.length) {
      const node = document.createElement("p");
      node.textContent = t("jobs_waiting_for_log", "Waiting for log");
      fragment.append(node);
    }
    log.replaceChildren(fragment);
    q("[data-job-log-truncated]").hidden = !logs.truncated;
    restoreLogPosition();
    renderedLog = signature;
    updateLogFollowing();
  }
  function onLogScroll(event) {
    const log = event.target;
    if (!log.matches?.(".job-log") || !log.clientHeight) return;
    logPosition = [log.scrollTop, log.scrollLeft];
    logFollowing = log.scrollHeight - log.clientHeight - log.scrollTop <= 24;
    updateLogFollowing();
  }
  function onLogToggle(event) {
    if (event.target.matches?.("[data-job-log-section]") && event.target.open) restoreLogPosition();
  }
  async function selectRun(id) {
    if (selectedRun !== id) { variantFilter = ""; resultOffset = 0; q("[data-job-detail]").hidden = true; }
    selectedRun = id;
    const epoch = ++selectionGeneration;
    renderRuns();
    const params = new URLSearchParams();
    if (resultOffset) params.set("offset", String(resultOffset));
    if (variantFilter) params.set("variant_id", variantFilter);
    const [detail, logs] = await Promise.all([serveApi(`/api/jobs/${id}${params.size ? `?${params}` : ""}`), serveApi(`/api/jobs/${id}/logs`)]);
    if (epoch !== selectionGeneration || selectedRun !== id || disposed) return;
    const pane = q("[data-job-detail]");
    const signature = JSON.stringify({ ...detail, heartbeat: undefined });
    const sameRun = renderedRun === id;
    const logSection = sameRun ? pane.querySelector("[data-job-log-section]") : null;
    const log = logSection?.querySelector(".job-log");
    if (log?.clientHeight) logPosition = [log.scrollTop, log.scrollLeft];
    if (sameRun && renderedDetail === signature) {
      renderLog(logs, true);
      return;
    }
    const expanded = sameRun ? [...pane.querySelectorAll("details")].map(node => node.open) : [];
    const focusedLog = logSection?.contains(document.activeElement) ? /** @type {HTMLElement} */ (document.activeElement) : null;
    const focusedFilter = sameRun && document.activeElement === pane.querySelector("[data-filter-variant]");
    renderedRun = id; renderedDetail = signature;
    pane.hidden = false;
    pane.innerHTML = `<header class="jobs-heading"><div><p class="eyebrow">${esc(stateLabel(detail.state))}</p><h3>${esc(detail.job_name || detail.id)}</h3></div>${adminMode() && ACTIVE.has(detail.state) ? `<button type="button" class="action-button" data-job-stop>${t("jobs_stop_run", "Stop run")}</button>` : ""}</header><p class="job-progress">${esc(detail.trials_completed ?? 0)} / ${esc(detail.trials_total ?? detail.prepared?.trial_count ?? "—")} Trials</p>${detail.error || detail.result_error ? `<p class="error">${esc(detail.error || detail.result_error)}</p>` : ""}<div class="job-results">${(detail.results || []).map(result => `<div class="job-result"><span>${esc(result.variant_label || result.variant_id || "")}</span><strong>${esc(result.task || result.id)}</strong><span>${esc(result.score ?? "—")}</span><small>${esc(result.score_source || stateLabel(result.state))}</small>${result.source_key ? `<a href="/?source=${encodeURIComponent(result.source_key)}" data-workspace-route="home">${t("jobs_view_trial", "View Trial")}</a>` : ""}</div>`).join("")}</div><details><summary>${t("jobs_run_configuration", "Run configuration")}</summary><pre>${esc(JSON.stringify(detail.request, null, 2))}</pre></details><details open data-job-log-section><summary>${t("jobs_run_log", "Run log")}</summary><button type="button" class="action-button" data-job-log-latest hidden>${t("jobs_back_to_latest", "Back to latest")}</button><p data-job-log-truncated hidden>${t("jobs_earlier_log_omitted_showing_the_last_128_kib_the_first_line_may_be_incomplete", "Earlier log omitted. Showing the last 128 KiB; the first line may be incomplete.")}</p><div class="job-log" tabindex="0" role="region" aria-label="${t("jobs_run_log", "Run log")}"></div></details>`;
    if (!ACTIVE.has(detail.state)) invalidateWorkspace("catalog");
    const results = pane.querySelector(".job-results");
    const groups = detail.variant_summary || summarizeVariants(detail.results || []);
    if (!groups.some(group => group.id === variantFilter)) variantFilter = "";
    results.insertAdjacentHTML("beforebegin", `<div class="job-variant-summary"><label>${t("jobs_filter_variant", "Filter variant")}<select data-filter-variant><option value="">${t("all", "All")}</option>${groups.map(group => `<option value="${esc(group.id)}" ${variantFilter === group.id ? "selected" : ""}>${esc(group.label)} · ${group.scored} / ${group.count} ${t("jobs_scored", "scored")} · ${t("jobs_mean", "mean")} ${group.mean === null ? "—" : Number(group.mean.toFixed(6))}</option>`).join("")}</select></label></div>`);
    [...results.children].forEach((node, index) => { node.dataset.resultVariant = detail.results[index].variant_id || ""; });
    filterResults();
    const count = detail.result_count ?? detail.results?.length ?? 0;
    if (count > 50 || resultOffset) results.insertAdjacentHTML("afterend", `<div class="jobs-actions"><button type="button" class="action-button" data-job-page="previous" ${resultOffset === 0 ? "disabled" : ""}>${t("previous", "Previous")}</button><span>${esc(Math.min(resultOffset + 1, count))}–${esc(Math.min(resultOffset + 50, count))} / ${esc(count)}</span><button type="button" class="action-button" data-job-page="next" ${resultOffset + 50 >= count ? "disabled" : ""}>${t("next", "Next")}</button></div>`);
    [...pane.querySelectorAll("details")].forEach((node, index) => { if (expanded[index] !== undefined) node.open = expanded[index]; });
    if (logSection) pane.querySelector("[data-job-log-section]").replaceWith(logSection);
    renderLog(logs, sameRun);
    restoreLogPosition();
    if (focusedLog) focusedLog.focus({ preventScroll: true });
    if (focusedFilter) pane.querySelector("[data-filter-variant]").focus({ preventScroll: true });
  }
  function filterResults() { for (const node of nodes("[data-result-variant]")) node.hidden = Boolean(variantFilter && node.dataset.resultVariant !== variantFilter); }
  async function refreshRuns() {
    const epoch = selectionGeneration;
    try {
      const data = await serveApi(`/api/collections/jobs?state=${showArchived ? "all" : "active"}`);
      if (disposed || epoch !== selectionGeneration) return;
      runs = data.items;
      const available = new Set(runs.map(row => row.id));
      for (const id of jobSelection) if (!available.has(id)) jobSelection.delete(id);
      if (selectedRun) selectedJob = runs.find(row => row.run_id === selectedRun)?.id || null;
      renderRuns();
      if (selectedRun && !jobSidebar.root.hidden) await selectRun(selectedRun);
    } finally { schedule(); }
  }
  function schedule() {
    clearTimeout(timer);
    if (!disposed && !root.hidden && runs.some(run => run.run_id && ACTIVE.has(run.state))) timer = setTimeout(() => { if (!root.hidden) void guarded(refreshRuns); }, 2000);
  }
  async function guarded(action) {
    try { await action(); } catch (error) { notify(error.message || String(error), true); }
  }
  async function savePreferences(path, body) {
    try {
      options = await serveApi(path, { method: "PUT", body: { ...body, revision: options.revision } });
    } catch (error) {
      if (error.status === 409) {
        options = await serveApi("/api/jobs/options");
        invalidated();
        error.message = t("jobs_configuration_changed_options_refreshed_this_change_was_not_saved_please_retry_the_action", "Configuration changed. Options refreshed; this change was not saved. Please retry the action.");
      }
      throw error;
    }
  }
  async function action(button) {
    if (button.matches("[data-job-log-latest]")) {
      logFollowing = true;
      const log = q(".job-log");
      log.scrollTop = log.scrollHeight;
      log.focus({ preventScroll: true });
      updateLogFollowing(); return;
    }
    if (button.matches("[data-job-page]")) { resultOffset = Math.max(0, resultOffset + (button.dataset.jobPage === "next" ? 50 : -50)); if (selectedJob) await selectCollection(selectedJob); else if (selectedRun) await selectRun(selectedRun); return; }
    if (button.matches("[data-add-entry]")) { button.closest("[data-kv]").querySelector("[data-kv-rows]").insertAdjacentHTML("beforeend", entryRow()); invalidated(); return; }
    if (button.matches("[data-remove-entry]")) { button.closest(".job-kv-row").remove(); invalidated(); return; }
    if (button.matches("[data-add-variant], [data-copy-variant], [data-remove-variant]")) {
      variants = readVariants();
      const id = button.closest("[data-variant]")?.dataset.variant;
      if (button.matches("[data-remove-variant]")) variants = variants.filter(item => item.id !== id);
      else { const source = variants.find(item => item.id === id) || variants.at(-1); variants.push({ ...structuredClone(source), id: identity(), label: String.fromCharCode(65 + variants.length) }); }
      renderVariants(); invalidated(); return;
    }
    if (button.matches("[data-jobs-mounts]")) { await registryManager.openMounts(button); return; }
    if (button.matches("[data-job-archive]")) { const row = runs.find(item => item.id === button.dataset.jobArchive); if (row) await archiveJobs([row], !row.archived); return; }
    if (button.matches("[data-jobs-archive-selected], [data-jobs-restore-selected]")) {
      const restoring = button.matches("[data-jobs-restore-selected]");
      await archiveJobs(runs.filter(item => jobSelection.has(item.id) && (restoring ? item.archived : !item.archived && item.can_archive)), !restoring);
      return;
    }
    if (busy) return;
    busy = true; button.disabled = true; updateComposer();
    try {
      if (button.matches("[data-job-preview]")) {
        const payload = request(); const epoch = generation;
        const result = await serveApi("/api/jobs/preview", { method: "POST", body: payload });
        if (epoch !== generation || JSON.stringify(payload) !== JSON.stringify(request())) return;
        preview = result;
        q("[data-job-preview-output]").hidden = false;
        q("[data-job-preview-count]").textContent = `${payload.tasks.length} Tasks × ${payload.variants.length} ${t("jobs_variants", "variants")} × ${payload.settings.n_attempts} = ${result.prepared.trial_count} Trials`;
        q("[data-job-preview-config]").textContent = JSON.stringify(result.prepared.config || result.prepared, null, 2);
        notify(t("jobs_configuration_validated_ready_to_start", "Configuration validated. Ready to start."));
      } else if (button.matches("[data-job-start]")) {
        const submittedId = requestId;
        const run = await serveApi("/api/jobs", { method: "POST", body: { request: request(), ...(preview ? { preview_id: preview.preview_id } : {}), request_id: submittedId } });
        selectedRun = run.id; variantFilter = "";
        if (requestId === submittedId) {
          changed = false; preview = null; requestId = identity();
          q("[data-job-preview-output]").hidden = true;
        }
        notify(t("jobs_job_started_it_continues_when_you_close_this_page", "Job started. It continues when you close this page."));
        selectedJob = null;
        jobSidebar.open({ opener: button });
        await refreshRuns();
      } else if (button.matches("[data-job-save-defaults]")) {
        const payload = request(), defaults = {};
        for (const checkbox of nodes("[data-default-section]:checked")) defaults[checkbox.dataset.defaultSection] = payload[checkbox.dataset.defaultSection];
        await savePreferences(`/api/jobs/defaults/${encodeURIComponent(harness)}`, { defaults });
        invalidated(); notify(t("jobs_defaults_saved", "Defaults saved."));
      } else if (button.matches("[data-job-stop]") && selectedRun) {
        await serveApi(`/api/jobs/${selectedRun}/stop`, { method: "POST", body: {} });
        await refreshRuns();
      } else if (button.matches("[data-jobs-refresh]")) await refreshRuns();
    } finally { busy = false; if (button.isConnected) button.disabled = false; updateComposer(); }
  }
  function build() {
    root.innerHTML = `<div class="jobs-page"><div class="serve-notice" data-jobs-notice role="status" hidden></div><section data-jobs-collection><header class="table-region-head"><div class="table-region-title-stack"><h2>Jobs</h2><input type="search" data-jobs-search placeholder="${t("jobs_search_jobs", "Search Jobs")}" aria-label="${t("jobs_search_jobs", "Search Jobs")}"></div><div class="table-region-actions"><button class="action-button" data-jobs-refresh>${t("serve_refresh", "Refresh")}</button>${adminMode() ? `<label><input type="checkbox" data-jobs-show-archived>${t("show_archived", "Show archived")}</label><button class="action-button" data-jobs-archive-selected disabled>${t("archive_selected", "Archive selected")}</button><button class="action-button" data-jobs-restore-selected disabled>${t("restore_selected", "Restore selected")}</button><button class="action-button" data-jobs-mounts>${t("serve_harbor_mounts", "Harbor mounts")}</button>` : ""}</div></header><div data-jobs-list></div></section><div class="jobs-layout"><section class="jobs-composer"><header class="jobs-heading"><h3>${t("jobs_new_run", "New run")}</h3><label>Harness<select data-job-harness></select></label></header><div class="jobs-selection"><div class="jobs-heading"><h4>${t("jobs_select_tasks", "Select Tasks")}</h4><span data-job-task-count></span></div><input type="search" data-job-search placeholder="${t("jobs_search_tasks", "Search Tasks")}" aria-label="${t("jobs_search_tasks", "Search Tasks")}"><div class="job-task-list" data-job-tasks></div></div><div class="jobs-heading"><h4>${t("jobs_agent_model_variants", "Agent / Model variants")}</h4><button class="action-button" type="button" data-add-variant>${t("jobs_add_variant", "Add variant")}</button></div><datalist id="jobs-agents"></datalist><datalist id="jobs-models"></datalist><div data-job-variants></div><div class="job-basics">${[["n_attempts", t("jobs_repeats", "Repeats"), "1"], ["n_concurrent_trials", t("jobs_concurrent_trials", "Concurrent Trials"), "1"], ["timeout_multiplier", t("jobs_timeout_multiplier", "Timeout multiplier"), "0.1"]].map(([key, label, min]) => `<label>${label}<input type="number" data-job-setting="${key}" aria-label="${label}" min="${min}" step="${min}"></label>`).join("")}</div><details class="job-advanced"><summary>${t("jobs_advanced_job_environment_verifier", "Advanced: Job, environment, verifier")}</summary><div data-job-settings></div></details><div class="jobs-actions"><button type="button" class="action-button" data-job-preview>${t("jobs_preview_configuration", "Preview configuration")}</button><button type="button" class="action-button primary" data-job-start disabled ${adminMode() ? "" : "hidden"}>${t("jobs_start_run", "Start run")}</button></div><div class="job-preview" data-job-preview-output hidden><strong data-job-preview-count></strong><details><summary>${t("jobs_effective_configuration", "Effective configuration")}</summary><pre data-job-preview-config></pre></details></div>${adminMode() ? `<details class="job-defaults"><summary>${t("jobs_save_selected_defaults", "Save selected defaults")}</summary><div class="jobs-actions">${[["variants", t("jobs_variants", "Variants"), true], ["settings", t("jobs_execution_settings", "Execution settings"), true], ["tasks", t("jobs_task_selection", "Task selection"), false]].map(([key, label, checked]) => `<label><input type="checkbox" data-default-section="${key}" ${checked ? "checked" : ""}>${label}</label>`).join("")}</div><button type="button" class="action-button" data-job-save-defaults>${t("jobs_save_defaults", "Save defaults")}</button></details>` : ""}</section></div><section class="job-detail" data-job-detail hidden></section></div>`;
    jobSidebar = createCollectionSidebar({ id: "jobs-detail", pageRoot: root, content: q("[data-job-detail]"), title: "Job" });
    const taskContent = document.createElement("div");
    taskContent.className = "harbor-workbench-grid harbor-task-browser";
    taskContent.innerHTML = `<section class="harbor-pane"><div class="harbor-file-tree" data-harbor-file-tree></div></section><section class="harbor-pane harbor-editor-pane"><header class="harbor-editor-head"><strong data-harbor-editor-path></strong><span data-harbor-editor-meta></span></header><textarea class="harbor-editor" data-harbor-editor readonly></textarea></section>`;
    taskSidebar = createCollectionSidebar({ id: "jobs-task", pageRoot: root, content: taskContent, title: t("jobs_task_details", "Task details") });
    taskBrowser = createTaskBrowser({ root: taskContent, editable: false,
      loadTask: ref => serveApi(`/api/harbor/datasets/${encodeURIComponent(ref.dataset_id)}/tasks/${encodeURIComponent(ref.task)}`),
      readFile: (ref, path) => serveApi(`/api/harbor/datasets/${encodeURIComponent(ref.dataset_id)}/tasks/${encodeURIComponent(ref.task)}/files/${encodeURIComponent(path)}`),
    });
    registryManager = createRegistryManager({ root: q("[data-jobs-collection]"), page: "jobs", onRefresh: refreshRuns });
    root.addEventListener("click", onClick);
    root.addEventListener("change", onChange);
    root.addEventListener("input", onInput);
    root.addEventListener("scroll", onLogScroll, true);
    root.addEventListener("toggle", onLogToggle, true);
    window.addEventListener("peval:workspace-navigate", onNavigate);
  }
  function onClick(event) { const button = event.target.closest("button"); if (button) void guarded(() => action(button)); }
  function onInput(event) { if (event.target.matches("[data-job-search]")) filterTasks(); else if (event.target.matches("[data-jobs-search]")) { jobsSearch = event.target.value; renderRuns(); } else if (event.target.closest(".jobs-composer") && !event.target.closest("[data-job-tasks]")) invalidated(); }
  function onChange(event) {
    const input = event.target;
    if (input.matches("[data-jobs-show-archived]")) { showArchived = input.checked; void guarded(refreshRuns); }
    if (input.matches("[data-filter-variant]")) { variantFilter = input.value; resultOffset = 0; filterResults(); void guarded(() => selectRun(selectedRun)); }
    if (input.matches("[data-job-harness]")) {
      if (busy || harnessLoading) { input.value = harness; return; }
      harness = input.value; busy = true; invalidated();
      void guarded(async () => {
        try {
          try {
            if (adminMode()) await savePreferences("/api/jobs/preferred-harness", { harness });
          } finally { await loadHarness(); }
        } finally { busy = false; updateComposer(); }
      });
    }
  }
  function onNavigate(event) { if (event.detail.to !== "jobs") { clearTimeout(timer); selectionGeneration++; } }
  return {
    async activate(changes, hash) {
      if (!initialized) {
        build(); options = await serveApi("/api/jobs/options");
        q("[data-job-harness]").innerHTML = options.harnesses.map(item => `<option value="${esc(item.id)}">${esc(item.label || item.id)}</option>`).join("");
        const available = options.harnesses.filter(item => item.available !== false);
        const preferred = available.find(item => item.id === options.preferred_harness) || available[0];
        if (preferred) q("[data-job-harness]").value = preferred.id;
        harness = q("[data-job-harness]").value;
        await loadHarness(); initialized = true;
      } else if (changes.has("tasks") || changes.has("dataset-registry")) { invalidated(); await loadHarness(false); }
      if (hash.startsWith("#task=")) {
        try { selected = new Set([decodeURIComponent(hash.slice(6))]); renderTasks(); invalidated(); }
        catch { notify(t("jobs_invalid_task_link", "Invalid Task link"), true); }
      }
      jobSidebar.resume(); taskSidebar.resume();
      await refreshRuns();
    },
    snapshot() { return { context: { page: "jobs", run_id: selectedRun }, dirty: changed }; },
    destroy() { jobSidebar?.destroy(); taskSidebar?.destroy(); registryManager?.destroy(); disposed = true; generation++; selectionGeneration++; clearTimeout(timer); root.removeEventListener("click", onClick); root.removeEventListener("change", onChange); root.removeEventListener("input", onInput); root.removeEventListener("scroll", onLogScroll, true); root.removeEventListener("toggle", onLogToggle, true); window.removeEventListener("peval:workspace-navigate", onNavigate); },
  };
}

export { createJobsPage, parseEntries, flattenEntries, summarizeVariants };
