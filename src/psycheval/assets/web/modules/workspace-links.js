import { workspaceShareLink } from "../app/workspace-runtime.js";
import { bindCopyButton } from "./clipboard.js";
import { esc, t } from "./shared.js";

function workspaceLinkButton() {
  return `<button type="button" class="action-button compact" data-workspace-copy-link>${esc(t("copy_link", "Copy link"))}</button>`;
}
function bindWorkspaceLinkButtons(root, page) {
  root?.querySelectorAll("[data-workspace-copy-link]").forEach(button => {
    if (button.dataset.linkBound) return;
    button.dataset.linkBound = "true";
    bindCopyButton(button, () => workspaceShareLink(page), t("copy_link", "Copy link"));
  });
}
export { workspaceLinkButton, bindWorkspaceLinkButtons };
