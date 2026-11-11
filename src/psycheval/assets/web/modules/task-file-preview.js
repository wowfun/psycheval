import { t } from "./shared.js";
import { createJsonView } from "./json-view.js";
import { scoringText } from "./task-table.js";

function createScoringPreview(preview) {
  if (!preview) return null;
  const root = document.createElement("div");
  root.className = "task-scoring-preview";
  function text(parent, tag, value) {
    const node = document.createElement(tag); node.textContent = scoringText(value); parent.append(node); return node;
  }
  function details(parent, label, value) {
    const node = document.createElement("details");
    text(node, "summary", label); node.append(createJsonView(JSON.stringify(value))); parent.append(node);
  }
  const fields = [["question", "task_scoring_question", "Question"], ["pass_criteria", "task_scoring_pass", "Pass criteria"],
    ["fail_criteria", "task_scoring_fail", "Fail criteria"], ["scope_limits", "task_scoring_scope", "Scope limits"], ["artifact_refs", "task_scoring_artifacts", "Artifact refs"]];
  for (const item of preview.items || []) {
    const article = document.createElement("section"); article.className = "task-scoring-preview-item";
    text(article, "h3", item.id);
    if (preview.kind === "grader") {
      text(article, "p", `${item.dimension} · ${t("task_scoring_weight", "Weight")}: ${item.weight}`);
    } else {
      const list = document.createElement("dl");
      for (const [key, label, fallback] of fields) {
        const value = item[key];
        if (value == null || Array.isArray(value) && !value.length) continue;
        text(list, "dt", t(label, fallback));
        const description = document.createElement("dd");
        if (Array.isArray(value)) { const ul = document.createElement("ul"); value.forEach(value => text(ul, "li", value)); description.append(ul); }
        else text(description, "p", value);
        list.append(description);
      }
      article.append(list);
      const extra = Object.fromEntries(Object.entries(item).filter(([key]) => key !== "id" && !fields.some(([field]) => key === field)));
      if (Object.keys(extra).length) details(article, t("task_scoring_metadata", "Additional metadata"), extra);
    }
    root.append(article);
  }
  const config = { ...(preview.config || {}) };
  if (preview.kind === "judge") {
    if (config.artifacts) details(root, t("task_scoring_artifacts", "Artifact refs"), config.artifacts);
    delete config.artifacts;
    const { rubrics: _rubrics, ...judge } = config.llm_judge || {};
    config.llm_judge = judge;
  }
  details(root, t("task_scoring_configuration", "Scoring configuration"), config);
  return root;
}

export { createScoringPreview };
