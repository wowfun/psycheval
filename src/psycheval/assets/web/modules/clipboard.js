import { t } from "./shared.js";

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const focused = document.activeElement;
  const input = document.createElement("textarea");
  input.value = text;
  input.readOnly = true;
  input.style.cssText = "position:fixed;left:-9999px;top:0";
  document.body.append(input);
  try {
    input.select();
    if (!document.execCommand("copy")) throw new Error("Copy failed");
  } finally {
    input.remove();
    focused?.focus?.({ preventScroll: true });
  }
}

function bindCopyButton(button, getText, label) {
  button.addEventListener("click", async () => {
    if (button.getAttribute("aria-busy") === "true") return;
    button.setAttribute("aria-busy", "true");
    try {
      const text = getText();
      if (!text?.trim()) return;
      await copyText(text);
      button.textContent = t("copied", "Copied");
      button.removeAttribute("title");
    } catch (error) {
      button.textContent = t("copy_failed", "Copy failed");
      button.title = error.message || String(error);
    } finally {
      button.removeAttribute("aria-busy");
      button.setAttribute("aria-label", button.textContent === label ? label : `${button.textContent}: ${label}`);
    }
  });
}

export { bindCopyButton };
