// @ts-check

import { serveApi } from "../modules/http.js";
import { adminMode } from "../modules/shared.js";
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
  const zh = document.documentElement.lang.startsWith("zh");
  const say = (cn, en) => zh ? cn : en;
  const q = selector => root.querySelector(selector);
  const nodes = selector => /** @type {any[]} */ ([...root.querySelectorAll(selector)]);
  let initialized = false, disposed = false, generation = 0, selectionGeneration = 0;
  let timer = null;
  let options = null, datasets = [], harness = "harbor", variants = [], selected = new Set();
  let preview = null, selectedRun = null, runs = [], requestId = identity();
  let renderedRun = null, renderedDetail = null;
  let changed = false, busy = false;
  let variantFilter = "";
  let resultOffset = 0;
  const labels = { preparing: say("准备中", "Preparing"), running: say("运行中", "Running"), stopping: say("停止中", "Stopping"), completed: say("运行完成", "Completed"), failed: say("运行失败", "Failed"), cancelled: say("已取消", "Cancelled"), interrupted: say("已中断", "Interrupted") };
  const stateLabel = value => labels[value] || value;

  function notify(text, error = false) {
    const node = q("[data-jobs-notice]");
    node.textContent = text;
    node.hidden = !text;
    node.classList.toggle("error", error);
  }
  function invalidated() {
    preview = null; changed = true; requestId = identity();
    q("[data-job-start]").disabled = true;
    q("[data-job-preview-output]").hidden = true;
  }
  function entryRow(entry = { key: "", type: "string", value: "" }) {
    return `<div class="job-kv-row"><input data-kv-key aria-label="${say("配置键", "Configuration key")}" value="${esc(entry.key)}" placeholder="kwargs.temperature"><select data-kv-type aria-label="${say("值类型", "Value type")}">${["string", "number", "boolean", "json"].map(type => `<option ${type === entry.type ? "selected" : ""}>${type}</option>`).join("")}</select><input data-kv-value aria-label="${say("配置值", "Configuration value")}" value="${esc(entry.value)}"><button type="button" class="action-button" data-remove-entry aria-label="${say("删除配置项", "Remove setting")}">×</button></div>`;
  }
  function editor(value, name) {
    return `<div class="job-kv" data-kv="${esc(name)}"><div data-kv-rows>${flattenEntries(value).map(entry => entryRow(entry)).join("")}</div><button type="button" class="action-button" data-add-entry>${say("添加键值", "Add setting")}</button></div>`;
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
      if (Object.hasOwn(settings, input.dataset.jobSetting)) throw new Error(say("基础字段请在上方编辑", "Edit basic fields above"));
      const value = Number(input.value);
      if (!input.value.trim() || !Number.isFinite(value) || value <= 0 || (input.dataset.jobSetting !== "timeout_multiplier" && !Number.isInteger(value))) throw new Error(say("基础配置必须是有效正数", "Basic settings require valid positive numbers"));
      settings[input.dataset.jobSetting] = value;
    }
    return { harness, tasks: [...selected], variants: readVariants(), settings };
  }
  function renderVariants() {
    q("[data-job-variants]").innerHTML = variants.map(variant => `<section class="job-variant" data-variant="${esc(variant.id)}"><div class="job-variant-fields"><label>${say("对比组", "Variant")}<input data-variant-label value="${esc(variant.label)}"></label><label>Agent<input data-variant-agent list="jobs-agents" value="${esc(variant.agent)}" placeholder="opencode"></label><label>Model<input data-variant-model list="jobs-models" value="${esc(variant.model)}" placeholder="provider/model"></label><button type="button" class="action-button" data-copy-variant>${say("复制", "Duplicate")}</button><button type="button" class="action-button" data-remove-variant ${variants.length === 1 ? "disabled" : ""}>${say("删除", "Remove")}</button></div><details><summary>${say("对比组高级配置", "Variant settings")}</summary>${editor(variant.options, variant.id)}</details></section>`).join("");
  }
  function renderTasks() {
    q("[data-job-tasks]").innerHTML = datasets.map(dataset => `<details open class="job-dataset"><summary><label><input type="checkbox" data-select-dataset="${esc(dataset.id)}" ${dataset.tasks.length && dataset.tasks.filter(task => task.available !== false).every(task => selected.has(task.id)) ? "checked" : ""}> ${esc(dataset.label)} <span class="job-count">${dataset.tasks.length}</span></label></summary>${dataset.error ? `<p class="error">${esc(dataset.error)}</p>` : ""}<div>${dataset.tasks.map(task => `<label class="job-task" data-task-label="${esc(task.label.toLowerCase())}"><input type="checkbox" data-select-task="${esc(task.id)}" ${selected.has(task.id) ? "checked" : ""} ${task.available === false ? "disabled" : ""}><span>${esc(task.label)}${task.error ? `<small>${esc(task.error)}</small>` : ""}</span></label>`).join("")}</div></details>`).join("") || `<p class="copy">${say("尚无已登记 Task，请先在数据集页登记来源。", "No registered Tasks. Register a source on the Datasets page.")}</p>`;
    filterTasks();
    q("[data-job-task-count]").textContent = `${selected.size} ${say("个 Task 已选", "Tasks selected")}`;
  }
  function filterTasks() {
    const search = q("[data-job-search]").value.toLowerCase();
    for (const node of nodes("[data-task-label]")) node.hidden = !node.dataset.taskLabel.includes(search);
  }
  async function loadHarness(useDefaults = true) {
    const epoch = ++generation;
    const data = await serveApi(`/api/jobs/tasks/${encodeURIComponent(harness)}`);
    if (epoch !== generation || disposed) return;
    datasets = data.datasets;
    const description = options.harnesses.find(item => item.id === harness);
    if (!description) throw new Error(say("Harness 已不可用，请重新加载页面", "Harness is unavailable; reload the page"));
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
  }
  function renderRuns() {
    q("[data-jobs-list]").innerHTML = runs.map(run => `<button type="button" class="job-list-item ${run.id === selectedRun ? "selected" : ""}" data-select-run="${esc(run.id)}"><strong>${esc(run.job_name || run.submitted_at)}</strong><span>${esc(run.harness)} · ${esc(stateLabel(run.state))}</span><small>${esc(run.trials_completed ?? 0)} / ${esc(run.trials_total ?? run.prepared?.trial_count ?? "—")} Trials</small></button>`).join("") || `<p class="copy">${say("还没有批次。配置 Task 和对比组后启动。", "No Jobs yet. Select Tasks and configure variants to start.")}</p>`;
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
    const log = pane.querySelector(".job-log");
    if (sameRun && renderedDetail === signature) {
      if (log) log.textContent = logs.text || say("等待日志", "Waiting for log");
      return;
    }
    const expanded = sameRun ? [...pane.querySelectorAll("details")].map(node => node.open) : [];
    const logScroll = sameRun && log ? [log.scrollTop, log.scrollLeft] : [0, 0];
    const focusedFilter = sameRun && document.activeElement === pane.querySelector("[data-filter-variant]");
    renderedRun = id; renderedDetail = signature;
    pane.hidden = false;
    pane.innerHTML = `<header class="jobs-heading"><div><p class="eyebrow">${esc(stateLabel(detail.state))}</p><h3>${esc(detail.job_name || detail.id)}</h3></div>${adminMode() && ACTIVE.has(detail.state) ? `<button type="button" class="action-button" data-job-stop>${say("停止运行", "Stop run")}</button>` : ""}</header><p class="job-progress">${esc(detail.trials_completed ?? 0)} / ${esc(detail.trials_total ?? detail.prepared?.trial_count ?? "—")} Trials</p>${detail.error || detail.result_error ? `<p class="error">${esc(detail.error || detail.result_error)}</p>` : ""}<div class="job-results">${(detail.results || []).map(result => `<div class="job-result"><span>${esc(result.variant_label || result.variant_id || "")}</span><strong>${esc(result.task || result.id)}</strong><span>${esc(result.score ?? "—")}</span><small>${esc(result.score_source || stateLabel(result.state))}</small>${result.source_key ? `<a href="/#source=${encodeURIComponent(result.source_key)}" data-workspace-route="home">${say("查看 Trial", "View Trial")}</a>` : ""}</div>`).join("")}</div><details><summary>${say("本次配置", "Run configuration")}</summary><pre>${esc(JSON.stringify(detail.request, null, 2))}</pre></details><details open><summary>${say("运行日志", "Run log")}</summary><pre class="job-log">${esc(logs.text || say("等待日志", "Waiting for log"))}</pre></details>`;
    if (!ACTIVE.has(detail.state)) invalidateWorkspace("catalog");
    const results = pane.querySelector(".job-results");
    const groups = detail.variant_summary || summarizeVariants(detail.results || []);
    if (!groups.some(group => group.id === variantFilter)) variantFilter = "";
    results.insertAdjacentHTML("beforebegin", `<div class="job-variant-summary"><label>${say("筛选对比组", "Filter variant")}<select data-filter-variant><option value="">${say("全部", "All")}</option>${groups.map(group => `<option value="${esc(group.id)}" ${variantFilter === group.id ? "selected" : ""}>${esc(group.label)} · ${group.scored} / ${group.count} ${say("已评分", "scored")} · ${say("均分", "mean")} ${group.mean === null ? "—" : Number(group.mean.toFixed(6))}</option>`).join("")}</select></label></div>`);
    [...results.children].forEach((node, index) => { node.dataset.resultVariant = detail.results[index].variant_id || ""; });
    filterResults();
    const count = detail.result_count ?? detail.results?.length ?? 0;
    if (count > 50 || resultOffset) results.insertAdjacentHTML("afterend", `<div class="jobs-actions"><button type="button" class="action-button" data-job-page="previous" ${resultOffset === 0 ? "disabled" : ""}>${say("上一页", "Previous")}</button><span>${esc(Math.min(resultOffset + 1, count))}–${esc(Math.min(resultOffset + 50, count))} / ${esc(count)}</span><button type="button" class="action-button" data-job-page="next" ${resultOffset + 50 >= count ? "disabled" : ""}>${say("下一页", "Next")}</button></div>`);
    [...pane.querySelectorAll("details")].forEach((node, index) => { if (expanded[index] !== undefined) node.open = expanded[index]; });
    const nextLog = pane.querySelector(".job-log");
    nextLog.scrollTop = logScroll[0]; nextLog.scrollLeft = logScroll[1];
    if (focusedFilter) pane.querySelector("[data-filter-variant]").focus({ preventScroll: true });
  }
  function filterResults() { for (const node of nodes("[data-result-variant]")) node.hidden = Boolean(variantFilter && node.dataset.resultVariant !== variantFilter); }
  async function refreshRuns() {
    try {
      const data = await serveApi("/api/jobs");
      if (disposed) return;
      runs = data.items;
      renderRuns();
      if (selectedRun) await selectRun(selectedRun);
    } finally { schedule(); }
  }
  function schedule() {
    clearTimeout(timer);
    if (!disposed && !root.hidden && runs.some(run => ACTIVE.has(run.state))) timer = setTimeout(() => { if (!root.hidden) void guarded(refreshRuns); }, 2000);
  }
  async function guarded(action) {
    try { await action(); } catch (error) { notify(error.message || String(error), true); }
  }
  async function action(button) {
    if (button.matches("[data-job-page]")) { resultOffset = Math.max(0, resultOffset + (button.dataset.jobPage === "next" ? 50 : -50)); await selectRun(selectedRun); return; }
    if (button.matches("[data-add-entry]")) { button.closest("[data-kv]").querySelector("[data-kv-rows]").insertAdjacentHTML("beforeend", entryRow()); invalidated(); return; }
    if (button.matches("[data-remove-entry]")) { button.closest(".job-kv-row").remove(); invalidated(); return; }
    if (button.matches("[data-add-variant], [data-copy-variant], [data-remove-variant]")) {
      variants = readVariants();
      const id = button.closest("[data-variant]")?.dataset.variant;
      if (button.matches("[data-remove-variant]")) variants = variants.filter(item => item.id !== id);
      else { const source = variants.find(item => item.id === id) || variants.at(-1); variants.push({ ...structuredClone(source), id: identity(), label: String.fromCharCode(65 + variants.length) }); }
      renderVariants(); invalidated(); return;
    }
    if (button.matches("[data-select-run]")) { await selectRun(button.dataset.selectRun); return; }
    if (busy) return;
    busy = true; button.disabled = true;
    try {
      if (button.matches("[data-job-preview]")) {
        const payload = request(); const epoch = generation;
        const result = await serveApi("/api/jobs/preview", { method: "POST", body: payload });
        if (epoch !== generation || JSON.stringify(payload) !== JSON.stringify(request())) return;
        preview = result;
        q("[data-job-preview-output]").hidden = false;
        q("[data-job-preview-count]").textContent = `${payload.tasks.length} Tasks × ${payload.variants.length} ${say("对比组", "variants")} × ${payload.settings.n_attempts} = ${result.prepared.trial_count} Trials`;
        q("[data-job-preview-config]").textContent = JSON.stringify(result.prepared.config || result.prepared, null, 2);
        q("[data-job-start]").disabled = !adminMode();
        notify(say("配置有效，可启动本批次。", "Configuration validated. Ready to start."));
      } else if (button.matches("[data-job-start]") && preview) {
        const run = await serveApi("/api/jobs", { method: "POST", body: { request: preview.request, preview_id: preview.preview_id, request_id: requestId } });
        selectedRun = run.id; variantFilter = ""; changed = false; preview = null;
        notify(say("批次已启动，关闭页面不会停止运行。", "Job started. It continues when you close this page."));
        await refreshRuns();
      } else if (button.matches("[data-job-save-defaults]")) {
        const payload = request(), defaults = {};
        for (const checkbox of nodes("[data-default-section]:checked")) defaults[checkbox.dataset.defaultSection] = payload[checkbox.dataset.defaultSection];
        options = await serveApi(`/api/jobs/defaults/${encodeURIComponent(harness)}`, { method: "PUT", body: { defaults, revision: options.revision } });
        invalidated(); notify(say("默认值已保存。", "Defaults saved."));
      } else if (button.matches("[data-job-stop]") && selectedRun) {
        await serveApi(`/api/jobs/${selectedRun}/stop`, { method: "POST", body: {} });
        await refreshRuns();
      } else if (button.matches("[data-jobs-refresh]")) await refreshRuns();
    } finally { busy = false; if (button.isConnected) button.disabled = button.matches("[data-job-start]") ? !preview || !adminMode() : false; }
  }
  function build() {
    root.innerHTML = `<div class="jobs-page"><header class="jobs-heading"><div><p class="eyebrow">${say("评测批次", "EVALUATION RUNS")}</p><h2>Jobs</h2></div><a class="action-button" href="/datasets" data-workspace-route="datasets">${say("管理数据集", "Manage Datasets")}</a></header><div class="serve-notice" data-jobs-notice role="status" hidden></div><div class="jobs-layout"><section class="jobs-composer"><header class="jobs-heading"><h3>${say("新建 Run", "New run")}</h3><label>Harness<select data-job-harness></select></label></header><div class="jobs-selection"><div class="jobs-heading"><h4>${say("选择 Task", "Select Tasks")}</h4><span data-job-task-count></span></div><input type="search" data-job-search placeholder="${say("搜索 Task", "Search Tasks")}" aria-label="${say("搜索 Task", "Search Tasks")}"><div class="job-task-list" data-job-tasks></div></div><div class="jobs-heading"><h4>${say("Agent / Model 对比组", "Agent / Model variants")}</h4><button class="action-button" type="button" data-add-variant>${say("添加对比组", "Add variant")}</button></div><datalist id="jobs-agents"></datalist><datalist id="jobs-models"></datalist><div data-job-variants></div><div class="job-basics">${[["n_attempts", say("重复次数", "Repeats"), "1"], ["n_concurrent_trials", say("并发 Trial", "Concurrent Trials"), "1"], ["timeout_multiplier", say("超时倍数", "Timeout multiplier"), "0.1"]].map(([key, label, min]) => `<label>${label}<input type="number" data-job-setting="${key}" aria-label="${label}" min="${min}" step="${min}"></label>`).join("")}</div><details class="job-advanced"><summary>${say("高级配置：批次、环境、验证器", "Advanced: Job, environment, verifier")}</summary><div data-job-settings></div></details><div class="jobs-actions"><button type="button" class="action-button" data-job-preview>${say("预览配置", "Preview configuration")}</button><button type="button" class="action-button primary" data-job-start disabled ${adminMode() ? "" : "hidden"}>${say("启动 Run", "Start run")}</button></div><div class="job-preview" data-job-preview-output hidden><strong data-job-preview-count></strong><details><summary>${say("最终配置", "Effective configuration")}</summary><pre data-job-preview-config></pre></details></div>${adminMode() ? `<details class="job-defaults"><summary>${say("保存选项作为默认值", "Save selected defaults")}</summary><div class="jobs-actions">${[["variants", say("对比组", "Variants"), true], ["settings", say("执行设置", "Execution settings"), true], ["tasks", say("Task 选择", "Task selection"), false]].map(([key, label, checked]) => `<label><input type="checkbox" data-default-section="${key}" ${checked ? "checked" : ""}>${label}</label>`).join("")}</div><button type="button" class="action-button" data-job-save-defaults>${say("保存默认值", "Save defaults")}</button></details>` : ""}</section><aside class="jobs-history"><header class="jobs-heading"><h3>${say("批次记录", "Run history")}</h3><button class="action-button" type="button" data-jobs-refresh>${say("刷新", "Refresh")}</button></header><div data-jobs-list></div></aside></div><section class="job-detail" data-job-detail hidden></section></div>`;
    root.addEventListener("click", onClick);
    root.addEventListener("change", onChange);
    root.addEventListener("input", onInput);
    window.addEventListener("peval:workspace-navigate", onNavigate);
  }
  function onClick(event) { const button = event.target.closest("button"); if (button) void guarded(() => action(button)); }
  function onInput(event) { if (event.target.matches("[data-job-search]")) filterTasks(); else if (event.target.closest(".jobs-composer")) invalidated(); }
  function onChange(event) {
    const input = event.target;
    if (input.matches("[data-filter-variant]")) { variantFilter = input.value; resultOffset = 0; filterResults(); void guarded(() => selectRun(selectedRun)); }
    if (input.matches("[data-job-harness]")) { harness = input.value; invalidated(); void guarded(() => loadHarness()); }
    if (input.matches("[data-select-task]")) { if (input.checked) selected.add(input.dataset.selectTask); else selected.delete(input.dataset.selectTask); invalidated(); renderTasks(); }
    if (input.matches("[data-select-dataset]")) { for (const task of datasets.find(item => item.id === input.dataset.selectDataset)?.tasks || []) { if (task.available !== false) { if (input.checked) selected.add(task.id); else selected.delete(task.id); } } invalidated(); renderTasks(); }
  }
  function onNavigate(event) { if (event.detail.to !== "jobs") { clearTimeout(timer); selectionGeneration++; } }
  return {
    async activate(changes, hash) {
      if (!initialized) {
        build(); options = await serveApi("/api/jobs/options");
        q("[data-job-harness]").innerHTML = options.harnesses.map(item => `<option value="${esc(item.id)}">${esc(item.label || item.id)}</option>`).join("");
        harness = q("[data-job-harness]").value;
        await loadHarness(); initialized = true;
      } else if (changes.has("tasks") || changes.has("dataset-registry")) { invalidated(); await loadHarness(false); }
      if (hash.startsWith("#task=")) {
        try { selected = new Set([decodeURIComponent(hash.slice(6))]); renderTasks(); invalidated(); }
        catch { notify(say("Task 链接格式无效", "Invalid Task link"), true); }
      }
      await refreshRuns();
    },
    snapshot() { return { context: { page: "jobs", run_id: selectedRun }, dirty: changed }; },
    destroy() { disposed = true; generation++; selectionGeneration++; clearTimeout(timer); root.removeEventListener("click", onClick); root.removeEventListener("change", onChange); root.removeEventListener("input", onInput); window.removeEventListener("peval:workspace-navigate", onNavigate); },
  };
}

export { createJobsPage, parseEntries, flattenEntries, summarizeVariants };
