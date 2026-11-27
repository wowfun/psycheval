import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom, pointerClick } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"annotator","user_id":"alice","authentication_enabled":true}</script>
  <button id="opener" type="button">Open comments</button>
`);

const shared = await import("../../src/psycheval/assets/web/modules/shared.js");
const commentsUi = await import("../../src/psycheval/assets/web/modules/comments-ui.js");

const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test.after(() => browser.cleanup());

test("canModifyComment enforces guest read-only, annotator own-only, and admin full access", () => {
  const aliceComment = { id: "c1", author_id: "alice", body: "mine" };
  const bobComment = { id: "c2", author_id: "bob", body: "theirs" };
  const adminComment = { id: "c3", author_id: "admin", body: "admin note" };
  const minimalComment = { id: "c4", body: "manual entry without author" };

  shared.RENDER_OPTIONS.role = "guest";
  shared.RENDER_OPTIONS.user_id = null;
  assert.equal(commentsUi.canModifyComment(aliceComment), false);
  assert.equal(commentsUi.canModifyComment(minimalComment), false);

  shared.RENDER_OPTIONS.role = "annotator";
  shared.RENDER_OPTIONS.user_id = "alice";
  assert.equal(commentsUi.canModifyComment(aliceComment), true);
  assert.equal(commentsUi.canModifyComment(bobComment), false);
  assert.equal(commentsUi.canModifyComment(adminComment), false);
  assert.equal(commentsUi.canModifyComment(minimalComment), false);

  // Even an annotator whose user_id is "admin" (any case) cannot mutate admin comments.
  shared.RENDER_OPTIONS.user_id = "admin";
  assert.equal(commentsUi.canModifyComment(adminComment), false);
  shared.RENDER_OPTIONS.user_id = "Admin";
  assert.equal(commentsUi.canModifyComment({ id: "c5", author_id: "Admin", body: "spoof" }), false);

  shared.RENDER_OPTIONS.role = "admin";
  shared.RENDER_OPTIONS.user_id = "admin";
  assert.equal(commentsUi.canModifyComment(aliceComment), true);
  assert.equal(commentsUi.canModifyComment(bobComment), true);
  assert.equal(commentsUi.canModifyComment(adminComment), true);
  assert.equal(commentsUi.canModifyComment(minimalComment), true);

  shared.RENDER_OPTIONS.role = "annotator";
  shared.RENDER_OPTIONS.user_id = "alice";
});

test("renderCommentCellPreview and thread hide omitted optional fields for minimal comments", () => {
  const html = commentsUi.renderCommentCellPreview(
    [{ id: "c1", author_id: "alice", body: "<b>Check</b> & verify" }],
    { buttonAttrs: 'data-scoring-comments-open="k1"', canAdd: true },
  );
  assert.match(html, /data-scoring-comments-open="k1"/);
  assert.match(html, /&lt;b&gt;Check&lt;\/b&gt; &amp; verify/);
  assert.doesNotMatch(html, /<b>/);

  const minimalList = [{ id: "m1", body: "Minimal body only" }];
  assert.equal(commentsUi.commentPreviewText(minimalList), "Minimal body only");
  assert.equal(commentsUi.commentFullTooltip(minimalList), "Minimal body only");

  const emptyGuest = commentsUi.renderCommentCellPreview([], {
    buttonAttrs: 'data-scoring-comments-open="k1"',
    canAdd: false,
  });
  assert.equal(emptyGuest, '<span class="muted">-</span>');

  const emptyAnnotator = commentsUi.renderCommentCellPreview([], {
    buttonAttrs: 'data-scoring-comments-open="k1"',
    canAdd: true,
  });
  assert.match(emptyAnnotator, /data-scoring-comments-open="k1"/);
  assert.match(emptyAnnotator, /aria-label="Comments: Add comment"/);

  const host = document.createElement("div");
  document.body.append(host);
  try {
    shared.RENDER_OPTIONS.role = "guest";
    shared.RENDER_OPTIONS.user_id = null;
    const thread = commentsUi.createCommentThread({
      comments: [
        { id: "m1", body: "Body only" },
        { id: "m2", body: "Author only", author_id: "alice" },
        { id: "m3", body: "Timestamp only", updated_at_ms: 1_700_000_000_000 },
      ],
    });
    host.append(thread.element);

    const card1 = host.querySelector('[data-comment-id="m1"]');
    assert.equal(card1.querySelector(".comment-item-head"), null);
    assert.equal(card1.querySelector(".comment-author"), null);
    assert.equal(card1.querySelector(".comment-timestamp"), null);
    assert.equal(card1.querySelector(".comment-body").textContent, "Body only");

    const card2 = host.querySelector('[data-comment-id="m2"]');
    assert.equal(card2.querySelector(".comment-author").textContent, "alice");
    assert.equal(card2.querySelector(".comment-timestamp"), null);

    const card3 = host.querySelector('[data-comment-id="m3"]');
    assert.equal(card3.querySelector(".comment-author"), null);
    assert.ok(card3.querySelector(".comment-timestamp time"));

    // Admin still gets Edit/Delete header actions for body-only comments without empty meta nodes.
    shared.RENDER_OPTIONS.role = "admin";
    shared.RENDER_OPTIONS.user_id = "admin";
    thread.setComments([{ id: "m1", body: "Body only" }]);
    const adminCard = host.querySelector('[data-comment-id="m1"]');
    assert.equal(adminCard.querySelector(".comment-item-meta"), null);
    assert.ok(adminCard.querySelector('[data-comment-edit="m1"]'));
    assert.ok(adminCard.querySelector('[data-comment-delete="m1"]'));
  } finally {
    shared.RENDER_OPTIONS.role = "annotator";
    shared.RENDER_OPTIONS.user_id = "alice";
    host.remove();
  }
});

test("createCommentThread supports create, validation, inline edit, Escape cancel, delete, and draft retention on failure", async () => {
  const previousConfirm = window.confirm;
  window.confirm = () => true;
  const host = document.createElement("div");
  document.body.append(host);
  let items = [
    { id: "c1", body: "Alice original", author_id: "alice", updated_at_ms: 1000, revision: "r1" },
    { id: "c2", body: "Bob remark", author_id: "bob", updated_at_ms: 1500, revision: "r2" },
  ];
  let failCreate = false;
  let failUpdate = false;
  const thread = commentsUi.createCommentThread({
    comments: items,
    onCreate: async body => {
      if (failCreate) throw new Error("network down");
      const next = { id: "c3", body, author_id: "alice", updated_at_ms: 2000, revision: "r3" };
      items = [...items, next];
      return items;
    },
    onUpdate: async (comment, body) => {
      if (failUpdate) {
        const conflict = /** @type {Error & {status?: number}} */ (new Error("raw english conflict"));
        conflict.status = 412;
        throw conflict;
      }
      items = items.map(item => item.id === comment.id ? { ...item, body, revision: "r1b" } : item);
      return items;
    },
    onDelete: async comment => {
      items = items.filter(item => item.id !== comment.id);
      return items;
    },
  });
  host.append(thread.element);

  try {
    // Only Alice's own comment has Edit/Delete controls; Bob's does not.
    assert.ok(host.querySelector('[data-comment-edit="c1"]'));
    assert.ok(host.querySelector('[data-comment-delete="c1"]'));
    assert.equal(host.querySelector('[data-comment-edit="c2"]'), null);
    assert.equal(host.querySelector('[data-comment-delete="c2"]'), null);

    // Composer input is hidden by default until "Add comment" is clicked.
    assert.equal(host.querySelector("[data-comment-composer]"), null);
    const openComposerBtn = host.querySelector("[data-comment-composer-open]");
    assert.ok(openComposerBtn);
    openComposerBtn.click();
    assert.ok(host.querySelector("[data-comment-composer] textarea"));

    // Escape or Cancel collapses the composer and restores focus to the Add comment button.
    host.querySelector("[data-comment-composer] textarea").dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    assert.equal(host.querySelector("[data-comment-composer]"), null);
    assert.equal(document.activeElement, host.querySelector("[data-comment-composer-open]"));

    host.querySelector("[data-comment-composer-open]").click();
    // Blank submission shows inline validation error while keeping composer open.
    host.querySelector("[data-comment-composer]").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
    await tick();
    assert.ok(host.querySelector(".comment-error"));
    assert.ok(host.querySelector("[data-comment-composer] textarea"));

    // Failed create preserves draft text, surfaces error, and restores focus to textarea.
    failCreate = true;
    const composer = host.querySelector("[data-comment-composer] textarea");
    composer.value = "Draft to retain";
    composer.dispatchEvent(new window.Event("input", { bubbles: true }));
    host.querySelector("[data-comment-composer]").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
    await tick();
    assert.equal(host.querySelector("[data-comment-composer] textarea").value, "Draft to retain");
    assert.match(host.querySelector(".comment-error").textContent, /network down/);
    assert.equal(document.activeElement, host.querySelector("[data-comment-composer] textarea"));

    // Successful create appends item, clears draft, collapses composer, and restores focus to Add button.
    failCreate = false;
    host.querySelector("[data-comment-composer]").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
    await tick();
    assert.equal(host.querySelector("[data-comment-composer]"), null);
    assert.ok(host.querySelector("[data-comment-composer-open]"));
    assert.equal(document.activeElement, host.querySelector("[data-comment-composer-open]"));
    assert.equal(host.querySelectorAll("[data-comment-id]").length, 3);

    // Inline edit supports Escape cancel without saving (restoring focus), 412 localized conflict, and save.
    host.querySelector('[data-comment-edit="c1"]').click();
    const editInput = host.querySelector('[data-comment-edit-input="c1"]');
    assert.equal(editInput.value, "Alice original");
    editInput.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    assert.equal(host.querySelector('[data-comment-edit-input="c1"]'), null);
    assert.equal(document.activeElement, host.querySelector('[data-comment-edit="c1"]'));

    host.querySelector('[data-comment-edit="c1"]').click();
    const editInput2 = host.querySelector('[data-comment-edit-input="c1"]');
    editInput2.value = "Alice edited";
    editInput2.dispatchEvent(new window.Event("input", { bubbles: true }));
    failUpdate = true;
    host.querySelector(".comment-edit-form").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
    await tick();
    assert.match(host.querySelector(".comment-error").textContent, /Comment changed elsewhere; reload/);
    assert.equal(document.activeElement, host.querySelector('[data-comment-edit-input="c1"]'));

    failUpdate = false;
    host.querySelector(".comment-edit-form").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
    await tick();
    assert.match(host.querySelector('[data-comment-id="c1"]').textContent, /Alice edited/);
    assert.equal(document.activeElement, host.querySelector('[data-comment-edit="c1"]'));

    // Delete removes item and restores focus to Add comment button.
    host.querySelector('[data-comment-delete="c1"]').click();
    await tick();
    assert.equal(host.querySelector('[data-comment-id="c1"]'), null);
    assert.equal(document.activeElement, host.querySelector("[data-comment-composer-open]"));
  } finally {
    window.confirm = previousConfirm;
    host.remove();
  }
});

test("openCommentsModal opens dialog, closes on Escape/backdrop, and restores opener focus", () => {
  const opener = document.getElementById("opener");
  opener.focus();
  const modal = commentsUi.openCommentsModal({
    title: "Comments",
    subtitle: "task / item",
    opener,
    comments: [],
    onCreate: async () => [],
  });
  const dialog = document.querySelector("[data-comments-modal]");
  assert.ok(dialog);
  assert.equal(document.body.classList.contains("comments-modal-open"), true);
  pointerClick(dialog);
  assert.equal(document.querySelector("[data-comments-modal]"), null);
  assert.equal(document.body.classList.contains("comments-modal-open"), false);
  assert.equal(document.activeElement, opener);
  modal.close();
});
