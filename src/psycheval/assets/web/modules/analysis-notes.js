import { beginFeedback } from "./action-feedback.js";
import { adminMode, cellNoteFor, editableNotesSource, esc, notesFor, selectedKey, state, t } from "./runtime.js";
import { renderDetailSidebar } from "./detail-sidebar.js";
import { serveApi } from "./serve-effects.js";
import { applyServeMutationPayload } from "./serve-catalog.js";
import { renderManualNote } from "./markdown.js";

function renderSelectedNotes(trialKey) {
  const notes = notesFor(trialKey);
  const editor = renderNotesEditor(trialKey);
  const action = renderNotesAction(trialKey);
  const body = notes.length ? `<div class="note-list">${notes.map(renderManualNote).join("")}</div>` : "";
  if (!body && !editor && !action) return "";
  return `<section class="selected-extra selected-notes">
    <div class="selected-extra-head"><h3>${esc(t("notes", "Notes"))}</h3>${action}</div>
    ${editor}
    ${editor ? "" : body}
  </section>`;
}
function renderNotesAction(trialKey) {
  if (!adminMode()) return "";
  const source = editableNotesSource(trialKey);
  if (!source || state.notesEditor?.trialKey === trialKey) return "";
  const cellNote = cellNoteFor(trialKey);
  const label = cellNote ? t("edit_notes", "Edit notes") : t("add_notes", "Add notes");
  return `<button class="action-button notes-edit-button" type="button" data-notes-edit data-trial-key="${esc(trialKey)}">${esc(label)}</button>`;
}
function renderNotesEditor(trialKey) {
  if (!adminMode() || !trialKey || !state.notesEditor || state.notesEditor.trialKey !== trialKey) return "";
  const markdown = state.notesEditor.markdown ?? "";

  const disabled = state.notesEditor.saving ? " disabled" : "";
  return `<article class="notes-editor-panel" data-notes-editor-panel>
    <textarea data-notes-editor data-trial-key="${esc(trialKey)}" rows="8">${esc(markdown)}</textarea>
    ${state.notesEditor.error ? `<p class="copy danger" role="alert">${esc(state.notesEditor.error)}</p>` : ""}
    <div class="notes-editor-actions">
      <button class="action-button primary" type="button" data-notes-save data-trial-key="${esc(trialKey)}"${disabled}>${esc(t("save_notes", "Save notes"))}</button>
      <button class="action-button" type="button" data-notes-cancel${disabled}>${esc(t("cancel", "Cancel"))}</button>
    </div>
  </article>`;
}
function beginNotesEdit(trialKey) {
  if (!adminMode() || !trialKey || !editableNotesSource(trialKey)) return;
  const note = cellNoteFor(trialKey);
  const markdown = note?.markdown || "";
  state.notesEditor = { trialKey, markdown, baselineMarkdown: markdown, error: "", saving: false };
  renderDetailSidebar();
}
function cancelNotesEdit() {
  state.notesEditor = null;
  renderDetailSidebar();
}
function notesDraftChanged() {
  return Boolean(state.notesEditor && state.notesEditor.markdown !== (state.notesEditor.baselineMarkdown ?? ""));
}
async function saveSelectedNotes(button) {
  if (!adminMode()) return;
  const trialKey = button?.dataset?.trialKey || selectedKey();
  const source = editableNotesSource(trialKey);
  const panel = button?.closest?.("[data-notes-editor-panel]");
  const textarea = panel?.querySelector?.("[data-notes-editor]");
  if (!source?.source_key || !textarea) return;
  const markdown = textarea.value || "";
  const baselineMarkdown = state.notesEditor?.baselineMarkdown ?? cellNoteFor(trialKey)?.markdown ?? "";
  state.notesEditor = { trialKey, markdown, baselineMarkdown, error: "", saving: true };
  renderDetailSidebar();
  const pendingEditor = state.notesEditor;
  const feedback = beginFeedback(() => state.notesEditor?.trialKey === trialKey ? document.querySelector('[data-notes-editor-panel]') : null, {
    page: "home", key: `home:notes:${trialKey}`, label: trialKey,
  });
  feedback.pending();
  try {
    await serveApi(`/api/sources/${encodeURIComponent(source.source_key)}`, {
      method: "PATCH",
      body: { notes: markdown }
    });
    if (state.notesEditor === pendingEditor) state.notesEditor = null;
    feedback.dispose();
    applyServeMutationPayload({}, { preserveTrial: trialKey });
  } catch (error) {
    const message = `${t("notes_save_failed", "Save notes failed")}: ${error.message || String(error)}`;
    if (state.notesEditor === pendingEditor) state.notesEditor = { trialKey, markdown, baselineMarkdown, error: message, saving: false };
    feedback.dispose();
    renderDetailSidebar();
  }
}
export {
  notesDraftChanged,
  beginNotesEdit,
  cancelNotesEdit,
  renderNotesAction,
  renderNotesEditor,
  renderSelectedNotes,
  saveSelectedNotes,
};
