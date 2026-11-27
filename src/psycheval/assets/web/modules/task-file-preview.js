import { listValue, t } from "./shared.js";
import { createJsonView } from "./json-view.js";
import { scoringText } from "./task-table.js";
import { createCommentThread } from "./comments-ui.js";

function createScoringPreview(preview, commentOptions = null) {
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

  const steps = listValue(commentOptions?.steps);
  const activeStep = commentOptions?.activeStep ?? steps[0] ?? "";
  if (steps.length > 1) {
    const bar = document.createElement("div");
    bar.className = "task-scoring-step-bar";
    const label = document.createElement("label");
    label.textContent = `${t("comment_step", "Step")}: `;
    const select = document.createElement("select");
    select.dataset.scoringCommentStep = "";
    select.setAttribute("aria-label", t("comment_step", "Step"));
    for (const step of steps) {
      const option = document.createElement("option");
      option.value = step;
      option.textContent = step || "—";
      option.selected = step === activeStep;
      select.append(option);
    }
    select.addEventListener("change", () => commentOptions?.onStepChange?.(select.value));
    label.append(select);
    bar.append(label);
    root.append(bar);
  }

  const itemKind = preview.kind === "grader" ? "rule" : "rubric";
  const fields = [["question", "task_scoring_question", "Question"], ["pass_criteria", "task_scoring_pass", "Pass criteria"],
    ["fail_criteria", "task_scoring_fail", "Fail criteria"], ["scope_limits", "task_scoring_scope", "Scope limits"], ["artifact_refs", "task_scoring_artifacts", "Artifact refs"]];
  let focusedArticle = null;
  for (const item of preview.items || []) {
    const article = document.createElement("section");
    article.className = "task-scoring-preview-item";
    const itemKey = JSON.stringify([activeStep, itemKind, item.id]);
    article.dataset.scoringItemKey = itemKey;
    if (commentOptions?.focusItemKey && commentOptions.focusItemKey === itemKey) {
      article.classList.add("is-focused");
      focusedArticle = article;
    }
    text(article, "h3", item.id);
    if (preview.kind === "grader") {
      if (item.description) text(article, "p", item.description);
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
    if (commentOptions && commentOptions.commentsByKey !== undefined) {
      const itemComments = listValue(commentOptions.commentsByKey?.[itemKey]);
      const thread = createCommentThread({
        title: t("comments", "Comments"),
        comments: itemComments,
        compact: true,
        canCreate: Boolean(commentOptions.canCreate && !commentOptions.isDraft),
        onCreate: commentOptions.onCreate ? body => commentOptions.onCreate(itemKey, body) : undefined,
        onUpdate: commentOptions.onUpdate ? (comment, body) => commentOptions.onUpdate(itemKey, comment, body) : undefined,
        onDelete: commentOptions.onDelete ? comment => commentOptions.onDelete(itemKey, comment) : undefined,
      });
      article.append(thread.element);
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
  if (focusedArticle) {
    requestAnimationFrame(() => focusedArticle.scrollIntoView?.({ block: "nearest" }));
  }
  return root;
}

export { createScoringPreview };
