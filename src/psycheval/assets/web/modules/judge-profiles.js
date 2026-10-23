import { t } from "./shared.js";
import { openActionForm } from "./action-form.js";

const label = (key, fallback) => t(`judge_${key}`, fallback);

function renderJudgeProfiles({ configuration, save }) {
  const root = document.querySelector("[data-judge-profiles]");
  if (!root) return;
  const value = configuration || { default_profile: null, profiles: {} };
  const button = (text, action) => {
    const node = document.createElement("button"); node.type = "button";
    node.className = "action-button"; node.textContent = text; node.onclick = action; return node;
  };
  function edit(id = null) {
    const profile = value.profiles[id] || {};
    const textField = (name, title, fallback = "", type = "text", required = false) => ({
      name, label: title, value: profile[name] ?? fallback, type, required,
    });
    const fields = [
      { name: "id", label: label("profile_id", "Profile ID"), value: id || "", required: true },
      textField("title", t("name", "Name")),
      textField("base_url", "Base URL", "", "url", true),
      textField("model", label("model", "Model"), "", "text", true),
      textField("api_key", label("credential_ref", "API key environment reference, e.g. ${JUDGE_API_KEY}")),
      textField("reasoning_effort", label("reasoning", "Reasoning effort (optional)")),
      textField("system_prompt", label("system_prompt", "System prompt override (optional)"), "", "textarea"),
      textField("user_prompt_template", label("user_template", "User prompt template (optional; include {context} once)"), "", "textarea"),
      ...[["concurrency", label("concurrency", "Concurrency"), 4],
        ["request_timeout", label("request_timeout", "Request timeout (seconds)"), 30],
        ["total_timeout", label("total_timeout", "Total timeout (seconds)"), 120],
        ["max_evidence_bytes", label("max_evidence", "Maximum evidence bytes"), 1048576]]
        .map(([name, title, fallback]) => ({ ...textField(name, title, fallback, "number", true), min: 1 })),
    ];
    openActionForm({ title: label(id ? "edit_profile" : "add_profile", id ? "Edit Judge profile" : "Add Judge profile"), fields,
      async submit(values) {
        const next = structuredClone(value), key = values.id.trim();
        if (key !== id && Object.hasOwn(next.profiles, key)) throw new Error(label("duplicate_profile", "This profile ID already exists."));
        if (id) delete next.profiles[id];
        const item = { ...values }; delete item.id;
        for (const key of ["concurrency", "request_timeout", "total_timeout", "max_evidence_bytes"]) item[key] = Number(item[key]);
        for (const key of ["system_prompt", "user_prompt_template", "reasoning_effort"]) item[key] = item[key] || null;
        next.profiles[key] = item;
        if (!next.default_profile || next.default_profile === id) next.default_profile = key;
        await save(next);
      },
      secondaryAction: id ? { label: label("remove", "Remove"), async run() {
        const next = structuredClone(value); delete next.profiles[id];
        if (next.default_profile === id) next.default_profile = Object.keys(next.profiles)[0] || null;
        await save(next);
      } } : null,
    });
  }
  root.replaceChildren();
  const head = document.createElement("header"); head.className = "configuration-section-head";
  const title = document.createElement("h2"); title.id = "judge-profiles-title"; title.textContent = label("profiles", "Judge profiles");
  head.append(title, button(label("add_profile", "Add Judge profile"), () => edit()));
  const note = document.createElement("p"); note.className = "copy";
  note.textContent = label("profiles_notice", "Profiles for rubric experiments. API keys are environment references; credentials resolve when a run starts.");
  root.append(head, note);
  for (const [id, item] of Object.entries(value.profiles)) {
    const row = document.createElement("div"); row.className = "judge-profile-row";
    const identity = document.createElement("strong"); identity.textContent = `${item.title || id}${id === value.default_profile ? ` · ${label("default", "Default")}` : ""}`;
    const description = document.createElement("code"); description.textContent = `${id} · ${item.model} · ${item.base_url}`;
    const info = document.createElement("div"); info.append(identity, description);
    row.append(info, button(label("edit", "Edit"), () => edit(id)));
    if (id !== value.default_profile) row.append(button(label("make_default", "Make default"), () => openActionForm({
      title: label("make_default", "Make default"), fields: [], submit: () => save({ ...value, default_profile: id }),
    })));
    root.append(row);
  }
}

export { renderJudgeProfiles };
