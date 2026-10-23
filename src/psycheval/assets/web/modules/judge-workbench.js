import { adminMode, t } from "./shared.js";
import { bindCopyButton } from "./clipboard.js";
import { closeModalSurface, openModalSurface } from "./modal-surfaces.js";

const label = (key, fallback) => t(`judge_${key}`, fallback);
const json = value => JSON.stringify(value, null, 2);
function button(text, action, primary = false) {
  const node = document.createElement("button"); node.type = "button";
  node.className = `action-button${primary ? " primary" : ""}`; node.textContent = text;
  if (action) node.addEventListener("click", action);
  return node;
}
function pre(value) { const node = document.createElement("pre"); node.textContent = typeof value === "string" ? value : json(value); return node; }
function option(text, value) { const node = document.createElement("option"); node.textContent = text; node.value = value; return node; }
function details(title, content) {
  const node = document.createElement("details"); const summary = document.createElement("summary");
  summary.textContent = title; node.append(summary, pre(content)); return node;
}
function download(value) {
  const url = URL.createObjectURL(new Blob([json(value)], { type: "application/json" }));
  const link = document.createElement("a"); link.href = url; link.download = "judge-prompt.json";
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function createJudgeWorkbench({ request }) {
  let sourceKey = null, generation = 0, modal = null, active = null, refresh = null;
  const drafts = new Map();
  const base = () => `/api/judge/${encodeURIComponent(sourceKey)}`;
  function close() { if (modal) closeModalSurface(modal); refresh = null; generation += 1; }
  function surface(title) {
    close(); modal?.remove();
    const root = document.createElement("div"); root.className = "action-form-overlay judge-overlay"; root.hidden = true;
    root.setAttribute("role", "dialog"); root.setAttribute("aria-modal", "true"); root.setAttribute("aria-label", title);
    const pane = document.createElement("section"); pane.className = "action-form judge-dialog";
    const head = document.createElement("header"); head.className = "judge-heading";
    const heading = document.createElement("h3"); heading.textContent = title;
    head.append(heading, button(t("close", "Close"), close));
    const status = document.createElement("p"); status.className = "judge-status"; status.setAttribute("aria-live", "polite");
    const body = document.createElement("div"); body.className = "judge-body";
    pane.append(head, status, body); root.append(pane); document.body.append(root); modal = root;
    root.addEventListener("keydown", event => { if (event.key === "Escape") { event.stopPropagation(); close(); } });
    root.addEventListener("click", event => { if (event.target === root) close(); });
    openModalSurface(root, { focusTarget: head.querySelector("button") });
    const version = generation;
    return { root, body, status, current: () => version === generation && !root.hidden };
  }
  function messages(root, values, truncated = false) {
    for (const message of values || []) {
      const section = document.createElement("section"); section.className = "judge-message";
      const heading = document.createElement("header"); const role = document.createElement("strong"); role.textContent = message.role;
      const copy = button(t("copy", "Copy")); bindCopyButton(copy, () => message.content, message.role); copy.disabled = truncated;
      heading.append(role, copy); section.append(heading, pre(message.content)); root.append(section);
    }
  }
  function renderResult(result, run) {
    result.replaceChildren();
    if (!run) return;
    const heading = document.createElement("h4"); heading.textContent = `${label(run.state, run.state)} · ${run.profile}`; result.append(heading);
    const old = new Map(run.baseline.map(item => [item.id, item]));
    const outcomes = new Map(run.checks.map(item => [item.id, item]));
    for (const id of run.selected_ids) {
      const row = document.createElement("section"); row.className = "judge-result";
      const outcome = outcomes.get(id), baseline = old.get(id);
      const title = document.createElement("strong"); title.textContent = `${id} · ${baseline?.status || label("no_baseline", "No baseline")} → ${outcome ? outcome.passed ? "pass" : "fail" : label("unassessed", "Unassessed")}`;
      row.append(title, pre(`${label("original_reason", "Original reason")}: ${baseline?.reason || "—"}\n\n${label("current_reason", "Current reason")}: ${outcome?.reason || run.errors?.[id] || run.reason || "—"}`));
      const diagnostic = Object.values(run.diagnostics).find(item => item.id === id);
      const promptView = document.createElement("details"), summary = document.createElement("summary");
      summary.textContent = label("actual_prompt", "Actual prompt"); promptView.append(summary);
      if (diagnostic?.messages) {
        promptView.append(button(t("download", "Download"), () => download({ ...diagnostic, settings: run.settings })));
        messages(promptView, diagnostic.messages);
      }
      else promptView.append(pre(label("not_requested", "Not requested")));
      row.append(promptView); result.append(row);
    }
  }
  async function prompt(id) {
    const view = surface(`${label("actual_prompt", "Actual prompt")} · ${id}`);
    const endpoint = `${base()}/prompt/${encodeURIComponent(id)}`;
    view.status.textContent = t("loading", "Loading…");
    try {
      const data = await request(endpoint);
      if (!view.current()) return;
      view.status.textContent = `${label("original", "Original evaluation")} · ${label(data.status, data.status)} · ${label("redacted", "Redacted snapshot")}`;
      if (data.truncated) view.status.textContent += ` · ${label("truncated", "Preview truncated; download the complete snapshot")}`;
      if (!data.messages) view.body.append(pre(data.result?.reason || label("no_snapshot", "No retained request messages. Viewing does not generate a prompt.")));
      const actions = document.createElement("div"); actions.className = "judge-actions";
      const copy = button(label("copy_messages", "Copy messages JSON")); bindCopyButton(copy, () => json(data.messages), "messages"); copy.disabled = !data.messages || data.truncated;
      const download = document.createElement("a"); download.className = "action-button"; download.textContent = t("download", "Download"); download.href = `${endpoint}?download=true`;
      actions.append(copy, download);
      if (adminMode()) actions.append(button(label("draft", "Create draft"), () => draft([id])));
      view.body.append(actions); messages(view.body, data.messages, data.truncated);
      view.body.append(details(label("attempts", "Request attempts and responses"), data.attempts));
      if (data.settings != null) view.body.append(details(label("settings", "Recorded settings"), data.settings));
    } catch (error) { if (view.current()) view.status.textContent = error.message; }
  }
  function field(container, title, value, change, multiline = true) {
    const row = document.createElement("label"); row.textContent = title;
    const input = document.createElement(multiline ? "textarea" : "input"); input.value = value || "";
    if (multiline) input.rows = 3;
    input.addEventListener("input", () => change(input.value)); row.append(input); container.append(row); return input;
  }
  function arrayField(container, title, values, change) {
    const block = document.createElement("section"); block.className = "judge-criteria";
    const heading = document.createElement("strong"); heading.textContent = title; block.append(heading);
    const rows = document.createElement("div"); block.append(rows);
    function draw() {
      rows.replaceChildren();
      values.forEach((value, index) => {
        const row = document.createElement("div"); row.className = "judge-criterion";
        field(row, `${title} ${index + 1}`, value, text => { values[index] = text; change(); });
        row.append(button(label("remove", "Remove"), () => { values.splice(index, 1); change(); draw(); })); rows.append(row);
      });
    }
    block.append(button(label("add_criterion", "Add criterion"), () => { values.push(""); change(); draw(); }));
    draw(); container.append(block);
  }
  async function draft(ids) {
    if (!adminMode()) return;
    const view = surface(label("try_rubrics", "Try rubrics")); const key = sourceKey;
    view.status.textContent = t("loading", "Loading…");
    try {
      const [original, configuration] = await Promise.all([request(base()), request("/api/config")]);
      if (!view.current()) return;
      if (!original.supported) throw new Error(label("unsupported", "This source is not a generic YAML Judge."));
      let state = drafts.get(key);
      if (!state) {
        state = { config: structuredClone(original.config), instruction: original.context?.instruction || "", task: "", yaml: "", profile: configuration.judge?.default_profile || "", ids: [], preview: null, result: null, phase: "", pending: false, error: "" };
        drafts.set(key, state);
      }
      const selection = ids || (state.ids.length ? state.ids : original.config.llm_judge.rubrics.map(item => item.id));
      if (!state.pending && json(selection) !== json(state.ids)) { state.ids = [...selection]; state.preview = null; }
      const endpoint = `/api/judge/${encodeURIComponent(key)}`;
      const form = document.createElement("div"); form.className = "judge-editor";
      const preview = document.createElement("section"); preview.className = "judge-preview";
      const result = document.createElement("section"); result.className = "judge-latest";
      const actions = document.createElement("div"); actions.className = "judge-actions";
      const changed = () => { state.preview = null; state.error = ""; draw(); };
      const profileLabel = document.createElement("label"); profileLabel.textContent = label("profile", "Judge profile");
      const select = document.createElement("select"); select.setAttribute("aria-label", label("profile", "Judge profile"));
      select.append(option(label("choose_profile", "Choose a profile"), ""));
      for (const [id, item] of Object.entries(configuration.judge?.profiles || {})) select.append(option(`${item.title || id} · ${item.model}`, id));
      select.value = state.profile; select.onchange = () => { state.profile = select.value; changed(); }; profileLabel.append(select); form.append(profileLabel);
      const configLink = document.createElement("a"); configLink.href = "/config"; configLink.dataset.workspaceRoute = "config"; configLink.onclick = close; configLink.textContent = label("manage_profiles", "Manage Judge profiles"); form.append(configLink);
      for (const id of state.ids) {
        const rubric = state.config.llm_judge.rubrics.find(item => item.id === id);
        if (!rubric) continue;
        const block = document.createElement("fieldset"); const legend = document.createElement("legend"); legend.textContent = id; block.append(legend);
        block.append(button(label("actual_prompt", "Actual prompt"), () => prompt(id)));
        field(block, label("question", "Question"), rubric.question, value => { rubric.question = value; changed(); });
        field(block, label("artifact_refs", "Artifact references (comma separated)"), rubric.artifact_refs.join(", "), value => { rubric.artifact_refs = value.split(",").map(item => item.trim()).filter(Boolean); changed(); }, false);
        for (const [name, text] of [["pass_criteria", label("pass_criteria", "Pass criteria")], ["fail_criteria", label("fail_criteria", "Fail criteria")], ["scope_limits", label("scope_limits", "Scope limits")]]) {
          rubric[name] ||= []; arrayField(block, text, rubric[name], changed);
        }
        form.append(block);
      }
      const context = document.createElement("details"); context.open = !original.context;
      const summary = document.createElement("summary"); summary.textContent = label("context", "Instruction override"); context.append(summary);
      field(context, label("instruction", "Instruction"), state.instruction, value => { state.instruction = value; changed(); });
      field(context, label("current_task", "Explicit current Task directory (optional)"), state.task, value => { state.task = value; changed(); }, false);
      form.append(context);
      const yamlSection = document.createElement("details"); const yamlSummary = document.createElement("summary"); yamlSummary.textContent = label("import_yaml", "Import YAML override"); yamlSection.append(yamlSummary);
      const yamlInput = field(yamlSection, label("yaml_override", "Optional YAML overrides the fields above"), state.yaml, value => { state.yaml = value; changed(); });
      const upload = document.createElement("input"); upload.type = "file"; upload.accept = ".yaml,.yml,.json"; upload.setAttribute("aria-label", label("import_yaml", "Import YAML override"));
      upload.onchange = async () => { const file = upload.files?.[0]; if (file && file.size <= 1024 * 1024) { state.yaml = await file.text(); yamlInput.value = state.yaml; changed(); } };
      yamlSection.append(upload); form.append(yamlSection);
      function payload() {
        return {
          rubric_ids: [...state.ids], profile: state.profile || null,
          judge_config: state.yaml || JSON.stringify(state.config), task: state.task || null,
          instruction_text: state.instruction !== (original.context?.instruction || "") ? state.instruction : null,
        };
      }
      const previewButton = button(label("preview", "Preview prompt"), previewDraft);
      const runButton = button(label("run", "Run selected rubrics"), execute, true);
      const cancelButton = button(t("cancel", "Cancel"), () => {
        if (active?.key !== key) return;
        active.controller.abort(); state.phase = "cancelled"; state.result = null; state.error = ""; draw();
      });
      actions.append(previewButton, runButton, cancelButton);
      function draw() {
        if (!view.current()) return;
        const busyElsewhere = active && active.key !== key;
        view.status.textContent = state.error || [label("session_notice", "Drafts and latest results stay in this page until refresh."), state.phase ? label(state.phase, state.phase) : "", busyElsewhere ? label("busy_elsewhere", "Another Trial is running.") : ""].filter(Boolean).join(" · ");
        form.querySelectorAll("input,textarea,select,button").forEach(node => { node.disabled = state.pending; });
        previewButton.disabled = state.pending;
        runButton.disabled = state.pending || !!active || !!state.needsPreview;
        cancelButton.hidden = active?.key !== key || active.controller.signal.aborted;
        preview.replaceChildren();
        if (state.preview) {
          const section = document.createElement("details"), title = document.createElement("summary");
          title.textContent = label("unsent", "Unsent preview — no model call"); section.open = true; section.append(title);
          section.append(details(label("settings", "Recorded settings"), state.preview.settings));
          for (const [id, values] of Object.entries(state.preview.messages)) {
            const heading = document.createElement("h4"); heading.textContent = id; section.append(heading); messages(section, values);
          }
          preview.append(section);
        }
        renderResult(result, state.result);
      }

      async function previewDraft() {
        if (state.pending) return;
        state.pending = true; state.error = ""; state.preview = null; draw();
        try {
          state.preview = await request(`${endpoint}/preview`, { method: "POST", body: payload() });
          state.needsPreview = false;
          if (state.phase === "failed") state.phase = "";
        }
        catch (error) { state.error = error.message; }
        finally { state.pending = false; refresh?.(); }
      }
      async function execute() {
        if (active || state.pending || state.needsPreview) return;
        const controller = new AbortController();
        active = { key, controller }; state.pending = true; state.phase = "running"; state.result = null; state.error = "";
        const body = { ...payload(), expected_fingerprint: state.preview?.fingerprint || null };
        draw();
        try {
          const value = await request(`${endpoint}/run`, { method: "POST", body, signal: controller.signal });
          if (!controller.signal.aborted) { state.result = value; state.phase = value.state; state.preview = null; }
        } catch (error) {
          if (controller.signal.aborted) state.phase = "cancelled";
          else {
            state.phase = "failed"; state.error = error.message;
            if (error.status === 409) { state.preview = null; state.needsPreview = true; }
          }
        } finally {
          state.pending = false; active = null; refresh?.();
        }
      }
      view.body.append(actions, result, preview, form);
      refresh = draw; draw();
    } catch (error) { if (view.current()) view.status.textContent = error.message; }
  }
  return { prompt, draft, setSource(key) { if (sourceKey !== key) close(); sourceKey = key; } };
}

export { createJudgeWorkbench };
