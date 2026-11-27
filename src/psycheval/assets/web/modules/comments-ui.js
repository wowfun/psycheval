// @ts-check
import { renderDateTime } from "./date-time.js";
import { closeModalSurface, openModalSurface } from "./modal-surfaces.js";
import {
  adminMode,
  annotatorMode,
  canAnnotate,
  currentUserId,
  esc,
  formatMessage,
  listValue,
  t,
} from "./shared.js";

const COMMENT_EXCERPT_LENGTH = 72;

/** @param {any} comment */
function canModifyComment(comment) {
  if (!comment || typeof comment !== "object") return false;
  if (adminMode()) return true;
  if (annotatorMode()) {
    const userId = currentUserId();
    const authorId = typeof comment.author_id === "string" ? comment.author_id.trim() : "";
    return Boolean(userId && userId.toLowerCase() !== "admin" && authorId && authorId === userId);
  }
  return false;
}

/** @param {any} error */
function formatCommentError(error) {
  if (error?.status === 412) {
    return t("comment_conflict", "Comment changed elsewhere; reload to see the latest version.");
  }
  return error?.message || String(error);
}

/**
 * Update a Task object's scoring_comments map, scoring_items[].comments, and count in place.
 * @param {any} task
 * @param {string} itemKey
 * @param {any[]} comments
 */
function applyScoringCommentsToTask(task, itemKey, comments) {
  if (!task || typeof task !== "object") return;
  const next = listValue(comments);
  const nextMap = { ...(task.scoring_comments && typeof task.scoring_comments === "object" ? task.scoring_comments : {}) };
  if (next.length) nextMap[itemKey] = next;
  else delete nextMap[itemKey];
  task.scoring_comments = nextMap;
  if (Array.isArray(task.scoring_items)) {
    let total = 0;
    task.scoring_items = task.scoring_items.map(item => {
      const updated = item?.key === itemKey ? { ...item, comments: next } : item;
      total += listValue(updated?.comments).length;
      return updated;
    });
    task.scoring_comment_count = total;
  }
}

/**
 * Create shared POST/PATCH/DELETE handlers for Task scoring-item comments.
 * @param {{dataset_id: string, task: string}} taskRef
 * @param {{serveApi: (path: string, options?: any) => Promise<any>, onUpdated?: (itemKey: string, comments: any[]) => void}} options
 */
function createScoringCommentActions(taskRef, { serveApi, onUpdated } = /** @type {any} */ ({})) {
  const base = `/api/harbor/datasets/${encodeURIComponent(taskRef.dataset_id)}/tasks/${encodeURIComponent(taskRef.task)}/scoring-comments`;
  return {
    async onCreate(itemKey, body) {
      const payload = await serveApi(base, { method: "POST", body: { item_key: itemKey, body } });
      const next = listValue(payload?.comments);
      onUpdated?.(itemKey, next);
      return next;
    },
    async onUpdate(itemKey, comment, body) {
      const payload = await serveApi(`${base}/${encodeURIComponent(comment.id)}`, {
        method: "PATCH",
        body: { item_key: itemKey, body },
        ifMatch: comment.revision,
      });
      const next = listValue(payload?.comments);
      onUpdated?.(itemKey, next);
      return next;
    },
    async onDelete(itemKey, comment) {
      const payload = await serveApi(
        `${base}/${encodeURIComponent(comment.id)}?item_key=${encodeURIComponent(itemKey)}`,
        { method: "DELETE", ifMatch: comment.revision },
      );
      const next = listValue(payload?.comments);
      onUpdated?.(itemKey, next);
      return next;
    },
  };
}

/** @param {string} value */
function commentStatusLabel(value) {
  if (value === "commented") return t("comment_status_commented", "Commented");
  if (value === "uncommented") return t("comment_status_uncommented", "Uncommented");
  return value;
}

/** @param {number} count */
function commentCountLabel(count) {
  if (count === 1) return t("comment_count_one", "1 comment");
  return formatMessage("comment_count", "{count} comments", { count });
}

/** @param {any[]} comments */
function commentPreviewText(comments) {
  const items = listValue(comments);
  if (!items.length) return "";
  const latest = items[items.length - 1];
  const author = String(latest?.author_id || "").trim();
  const body = String(latest?.body || "").replace(/\s+/g, " ").trim();
  const text = author ? `${author}: ${body}` : body;
  return text.length > COMMENT_EXCERPT_LENGTH ? `${text.slice(0, COMMENT_EXCERPT_LENGTH)}…` : text;
}

/** @param {any[]} comments */
function commentFullTooltip(comments) {
  return listValue(comments)
    .map(item => {
      const author = String(item?.author_id || "").trim();
      const body = String(item?.body || "").trim();
      if (!body) return "";
      return author ? `${author}: ${body}` : body;
    })
    .filter(Boolean)
    .join("\n\n");
}

/**
 * @param {any[]} comments
 * @param {{canAdd?: boolean, ariaLabel?: string, buttonAttrs?: string}} [options]
 */
function renderCommentCellPreview(comments, options = {}) {
  const items = listValue(comments);
  const canAdd = Boolean(options.canAdd ?? canAnnotate());
  const attrs = options.buttonAttrs ? ` ${options.buttonAttrs}` : "";
  const ariaLabel = options.ariaLabel || t("comments", "Comments");
  if (!items.length) {
    if (!canAdd) return `<span class="muted">-</span>`;
    const addLabel = t("comment_add", "Add comment");
    return `<button type="button" class="comment-cell-trigger is-empty"${attrs} aria-label="${esc(`${ariaLabel}: ${addLabel}`)}">+ ${esc(addLabel)}</button>`;
  }
  const preview = commentPreviewText(items);
  return `<button type="button" class="comment-cell-trigger"${attrs} aria-label="${esc(`${ariaLabel}: ${commentCountLabel(items.length)}`)}"><span class="comment-count-pill">${items.length}</span><span class="comment-cell-snippet">${esc(preview)}</span></button>`;
}

/**
 * @param {{
 *   title?: string,
 *   comments?: any[],
 *   canCreate?: boolean,
 *   compact?: boolean,
 *   emptyMessage?: string,
 *   onCreate?: (body: string) => Promise<any[]>,
 *   onUpdate?: (comment: any, body: string) => Promise<any[]>,
 *   onDelete?: (comment: any) => Promise<any[]>,
 * }} options
 */
function createCommentThread(options = {}) {
  const canCreate = Boolean(options.canCreate ?? canAnnotate());
  const root = document.createElement("section");
  root.className = `comment-thread${options.compact ? " is-compact" : ""}`;
  root.dataset.commentThread = "";

  let items = [...listValue(options.comments)];
  let editingId = null;
  let editDraft = "";
  let composerOpen = false;
  let draftBody = "";
  let busy = false;
  let errorMessage = "";

  function setError(message) {
    errorMessage = message ? String(message) : "";
  }

  function render() {
    root.replaceChildren();
    if (options.title) {
      const head = document.createElement("div");
      head.className = "comment-thread-head";
      const heading = document.createElement("h4");
      heading.textContent = options.title;
      const count = document.createElement("span");
      count.className = "comment-count-pill";
      count.textContent = String(items.length);
      head.append(heading, count);
      root.append(head);
    }

    if (errorMessage) {
      const alert = document.createElement("p");
      alert.className = "comment-error";
      alert.setAttribute("role", "alert");
      alert.textContent = errorMessage;
      root.append(alert);
    }

    const list = document.createElement("div");
    list.className = "comment-list";
    list.dataset.commentList = "";
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "comment-empty muted";
      empty.textContent = options.emptyMessage || t("comment_empty", "No comments yet.");
      list.append(empty);
    } else {
      for (const comment of items) {
        const card = document.createElement("article");
        card.className = "comment-item";
        card.dataset.commentId = String(comment.id || "");

        const meta = document.createElement("header");
        meta.className = "comment-item-head";
        const authorId = typeof comment.author_id === "string" ? comment.author_id.trim() : "";
        const hasTimestamp = typeof comment.updated_at_ms === "number" && Number.isFinite(comment.updated_at_ms);
        if (authorId || hasTimestamp) {
          const left = document.createElement("div");
          left.className = "comment-item-meta";
          if (authorId) {
            const author = document.createElement("span");
            author.className = "comment-author";
            author.textContent = authorId;
            left.append(author);
          }
          if (hasTimestamp) {
            const stamp = document.createElement("span");
            stamp.className = "comment-timestamp";
            stamp.innerHTML = renderDateTime(comment.updated_at_ms);
            left.append(stamp);
          }
          meta.append(left);
        }

        const editable = canModifyComment(comment);
        if (editable && editingId !== comment.id) {
          const actions = document.createElement("div");
          actions.className = "comment-item-actions";
          const editBtn = document.createElement("button");
          editBtn.type = "button";
          editBtn.className = "action-button compact";
          editBtn.dataset.commentEdit = String(comment.id);
          editBtn.textContent = t("edit", "Edit");
          editBtn.disabled = busy;
          editBtn.addEventListener("click", () => {
            if (busy) return;
            editingId = comment.id;
            editDraft = String(comment.body || "");
            setError("");
            render();
            const editInput = root.querySelector(`[data-comment-edit-input="${comment.id}"]`);
            if (editInput instanceof HTMLElement) editInput.focus();
          });

          const delBtn = document.createElement("button");
          delBtn.type = "button";
          delBtn.className = "action-button compact danger";
          delBtn.dataset.commentDelete = String(comment.id);
          delBtn.textContent = t("delete", "Delete");
          delBtn.disabled = busy;
          delBtn.addEventListener("click", async () => {
            if (busy || !options.onDelete) return;
            if (!window.confirm(t("comment_delete_confirm", "Delete this comment?"))) return;
            busy = true;
            setError("");
            render();
            try {
              const next = await options.onDelete(comment);
              items = [...listValue(next)];
              if (editingId === comment.id) editingId = null;
            } catch (error) {
              setError(formatCommentError(error));
            } finally {
              busy = false;
              render();
              const focusEl = root.querySelector("[data-comment-composer-open]")
                || root.querySelector("[data-comment-edit]")
                || root.querySelector("[data-comment-delete]");
              if (focusEl instanceof HTMLElement) focusEl.focus();
            }
          });
          actions.append(editBtn, delBtn);
          meta.append(actions);
        }
        if (meta.childElementCount > 0) card.append(meta);

        if (editingId === comment.id) {
          const editForm = document.createElement("form");
          editForm.className = "comment-edit-form";
          const textarea = document.createElement("textarea");
          textarea.rows = 3;
          textarea.value = editDraft;
          textarea.disabled = busy;
          textarea.dataset.commentEditInput = String(comment.id);
          textarea.setAttribute("aria-label", t("edit", "Edit"));
          textarea.addEventListener("input", () => { editDraft = textarea.value; });
          textarea.addEventListener("keydown", event => {
            if (event.key === "Escape") {
              event.preventDefault();
              event.stopPropagation();
              if (!busy) {
                editingId = null;
                setError("");
                render();
                const editBtn = root.querySelector(`[data-comment-edit="${comment.id}"]`);
                if (editBtn instanceof HTMLElement) editBtn.focus();
              }
            } else if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
              event.preventDefault();
              editForm.requestSubmit();
            }
          });
          const row = document.createElement("div");
          row.className = "comment-form-actions";
          const saveBtn = document.createElement("button");
          saveBtn.type = "submit";
          saveBtn.className = "action-button primary compact";
          saveBtn.dataset.commentEditSave = String(comment.id);
          saveBtn.textContent = t("save", "Save");
          saveBtn.disabled = busy;
          const cancelBtn = document.createElement("button");
          cancelBtn.type = "button";
          cancelBtn.className = "action-button compact";
          cancelBtn.dataset.commentEditCancel = String(comment.id);
          cancelBtn.textContent = t("cancel", "Cancel");
          cancelBtn.disabled = busy;
          cancelBtn.addEventListener("click", () => {
            if (busy) return;
            editingId = null;
            setError("");
            render();
            const editBtn = root.querySelector(`[data-comment-edit="${comment.id}"]`);
            if (editBtn instanceof HTMLElement) editBtn.focus();
          });
          row.append(saveBtn, cancelBtn);
          editForm.append(textarea, row);
          editForm.addEventListener("submit", async event => {
            event.preventDefault();
            if (busy || !options.onUpdate) return;
            const trimmed = editDraft.trim();
            if (!trimmed) {
              setError(t("comment_body_required", "Enter a comment before saving"));
              render();
              const editInput = root.querySelector(`[data-comment-edit-input="${comment.id}"]`);
              if (editInput instanceof HTMLElement) editInput.focus();
              return;
            }
            busy = true;
            setError("");
            render();
            let failed = false;
            try {
              const next = await options.onUpdate(comment, trimmed);
              items = [...listValue(next)];
              editingId = null;
              editDraft = "";
            } catch (error) {
              failed = true;
              setError(formatCommentError(error));
            } finally {
              busy = false;
              render();
              const focusEl = failed
                ? root.querySelector(`[data-comment-edit-input="${comment.id}"]`)
                : root.querySelector(`[data-comment-edit="${comment.id}"]`)
                  || root.querySelector("[data-comment-composer-open]");
              if (focusEl instanceof HTMLElement) focusEl.focus();
            }
          });
          card.append(editForm);
        } else {
          const body = document.createElement("p");
          body.className = "comment-body";
          body.textContent = String(comment.body || "");
          card.append(body);
        }
        list.append(card);
      }
    }
    root.append(list);

    if (canCreate && options.onCreate) {
      if (!composerOpen) {
        const actions = document.createElement("div");
        actions.className = "comment-form-actions";
        const openBtn = document.createElement("button");
        openBtn.type = "button";
        openBtn.className = "action-button compact";
        openBtn.dataset.commentComposerOpen = "";
        openBtn.textContent = t("comment_add", "Add comment");
        openBtn.disabled = busy;
        openBtn.addEventListener("click", () => {
          if (busy) return;
          composerOpen = true;
          setError("");
          render();
          const composerInput = root.querySelector("[data-comment-composer] textarea");
          if (composerInput instanceof HTMLElement) composerInput.focus();
        });
        actions.append(openBtn);
        root.append(actions);
      } else {
        const composer = document.createElement("form");
        composer.className = "comment-composer";
        composer.dataset.commentComposer = "";
        const textarea = document.createElement("textarea");
        textarea.rows = options.compact ? 2 : 3;
        textarea.name = "body";
        textarea.placeholder = t("comment_placeholder", "Write a comment…");
        textarea.setAttribute("aria-label", t("comment_add", "Add comment"));
        textarea.value = draftBody;
        textarea.disabled = busy;
        textarea.addEventListener("input", () => { draftBody = textarea.value; });
        const closeComposer = () => {
          if (busy) return;
          composerOpen = false;
          draftBody = "";
          setError("");
          render();
          const openBtn = root.querySelector("[data-comment-composer-open]");
          if (openBtn instanceof HTMLElement) openBtn.focus();
        };
        textarea.addEventListener("keydown", event => {
          if (event.key === "Escape") {
            event.preventDefault();
            event.stopPropagation();
            closeComposer();
          } else if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
            event.preventDefault();
            composer.requestSubmit();
          }
        });
        const actions = document.createElement("div");
        actions.className = "comment-form-actions";
        const submit = document.createElement("button");
        submit.type = "submit";
        submit.className = "action-button primary compact";
        submit.dataset.commentSubmit = "";
        submit.textContent = t("comment_add", "Add comment");
        submit.disabled = busy;
        const cancel = document.createElement("button");
        cancel.type = "button";
        cancel.className = "action-button compact";
        cancel.dataset.commentComposerCancel = "";
        cancel.textContent = t("cancel", "Cancel");
        cancel.disabled = busy;
        cancel.addEventListener("click", closeComposer);
        actions.append(submit, cancel);
        composer.append(textarea, actions);
        composer.addEventListener("submit", async event => {
          event.preventDefault();
          if (busy) return;
          const trimmed = draftBody.trim();
          if (!trimmed) {
            setError(t("comment_body_required", "Enter a comment before saving"));
            render();
            const composerInput = root.querySelector("[data-comment-composer] textarea");
            if (composerInput instanceof HTMLElement) composerInput.focus();
            return;
          }
          busy = true;
          setError("");
          render();
          let failed = false;
          try {
            const next = await options.onCreate(trimmed);
            items = [...listValue(next)];
            draftBody = "";
            composerOpen = false;
          } catch (error) {
            failed = true;
            setError(formatCommentError(error));
          } finally {
            busy = false;
            render();
            const focusEl = failed
              ? root.querySelector("[data-comment-composer] textarea")
              : root.querySelector("[data-comment-composer-open]");
            if (focusEl instanceof HTMLElement) focusEl.focus();
          }
        });
        root.append(composer);
      }
    }
  }

  render();
  return {
    element: root,
    setComments(next) {
      items = [...listValue(next)];
      render();
    },
    getComments() {
      return [...items];
    },
  };
}

/**
 * @param {{
 *   title: string,
 *   subtitle?: string,
 *   comments?: any[],
 *   canCreate?: boolean,
 *   opener?: Element | null,
 *   onCreate?: (body: string) => Promise<any[]>,
 *   onUpdate?: (comment: any, body: string) => Promise<any[]>,
 *   onDelete?: (comment: any) => Promise<any[]>,
 * }} options
 */
function openCommentsModal(options) {
  document.querySelectorAll("[data-comments-modal]").forEach(node => closeModalSurface(node, { restoreFocus: false }));
  const backdrop = document.createElement("div");
  backdrop.className = "auth-backdrop";
  backdrop.dataset.commentsModal = "";
  const dialog = document.createElement("section");
  dialog.className = "auth-dialog comment-modal";
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-labelledby", "comments-modal-title");

  const header = document.createElement("header");
  header.className = "configuration-page-head";
  const headText = document.createElement("div");
  const title = document.createElement("h2");
  title.id = "comments-modal-title";
  title.textContent = options.title || t("comments", "Comments");
  headText.append(title);
  if (options.subtitle) {
    const sub = document.createElement("p");
    sub.className = "copy";
    sub.textContent = options.subtitle;
    headText.append(sub);
  }
  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.className = "action-button compact";
  closeBtn.dataset.commentsModalClose = "";
  closeBtn.textContent = t("close", "Close");
  closeBtn.setAttribute("aria-label", t("close", "Close"));
  header.append(headText, closeBtn);

  const body = document.createElement("div");
  body.className = "comment-modal-body";
  const thread = createCommentThread({
    comments: options.comments,
    canCreate: options.canCreate,
    onCreate: options.onCreate,
    onUpdate: options.onUpdate,
    onDelete: options.onDelete,
  });
  body.append(thread.element);
  dialog.append(header, body);
  backdrop.append(dialog);
  document.body.append(backdrop);

  const close = () => {
    closeModalSurface(backdrop);
    backdrop.remove();
  };
  closeBtn.addEventListener("click", close);
  backdrop.addEventListener("keydown", event => {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close();
    }
  });
  const focusTarget = /** @type {HTMLElement | null} */ (
    backdrop.querySelector("[data-comment-composer] textarea")
    || backdrop.querySelector("[data-comment-composer-open]")
    || closeBtn
  );
  openModalSurface(backdrop, {
    opener: options.opener || document.activeElement,
    bodyClass: "comments-modal-open",
    focusTarget,
    onRequestClose: close,
  });
  return { root: backdrop, close, thread };
}

export {
  applyScoringCommentsToTask,
  canModifyComment,
  commentCountLabel,
  commentFullTooltip,
  commentPreviewText,
  commentStatusLabel,
  createCommentThread,
  createScoringCommentActions,
  openCommentsModal,
  renderCommentCellPreview,
};
