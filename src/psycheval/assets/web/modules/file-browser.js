import { t } from "./shared.js";
import { renderMarkdown } from "./markdown.js";

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}

function createFileRead() {
  let generation = 0;
  return {
    invalidate() { generation += 1; },
    begin() { const current = ++generation; return () => current === generation; },
  };
}

function selectFile(tree, { preferredPath, preservedPath, defaultPath, strictPreferred = false } = {}) {
  const find = path => tree.find(item => item.kind === "file" && item.path === path) || null;
  return strictPreferred ? find(preferredPath) : find(preferredPath) || find(preservedPath) || find(defaultPath);
}

function renderFileTree(container, tree, { selectedPath, onOpen, onContextMenu,
  collapsed = new Set(), search = "", emptyMessage = t("harbor_file_empty", "Select a Task to browse its files") } = {}) {
  if (!container) return;
  container.replaceChildren();
  const query = search.toLocaleLowerCase();
  const matches = new Set();
  if (query) for (const item of tree) {
    if (!item.path.toLocaleLowerCase().includes(query)) continue;
    const parts = item.path.split("/");
    while (parts.length) { matches.add(parts.join("/")); parts.pop(); }
  }
  const visible = query
    ? tree.filter(item => matches.has(item.path))
    : tree.filter(item => ![...collapsed].some(path => item.path.startsWith(`${path}/`)));
  if (!visible.length) {
    const empty = document.createElement("p");
    empty.className = "copy harbor-empty";
    empty.textContent = emptyMessage;
    container.append(empty);
  }
  for (const item of visible) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `harbor-file-row kind-${item.kind}`;
    button.classList.toggle("selected", item.path === selectedPath);
    button.title = item.path;
    button.style.setProperty("--depth", String(item.path.split("/").length - 1));
    for (const [tag, text] of [["span", item.kind === "directory" ? (collapsed.has(item.path) ? "▸" : "▾") : "·"],
      ["span", item.path.split("/").at(-1)], ["small", item.kind === "file" ? formatBytes(item.size) : ""]]) {
      const node = document.createElement(tag);
      node.textContent = text;
      button.append(node);
    }
    if (item.kind === "directory") {
      button.setAttribute("aria-expanded", String(Boolean(query) || !collapsed.has(item.path)));
      button.addEventListener("click", () => {
        if (collapsed.has(item.path)) collapsed.delete(item.path); else collapsed.add(item.path);
        renderFileTree(container, tree, { selectedPath, onOpen, onContextMenu, collapsed, search, emptyMessage });
      });
    } else button.addEventListener("click", () => onOpen?.(item));
    if (onContextMenu) button.addEventListener("contextmenu", event => {
      event.preventDefault();
      onContextMenu(item);
    });
    container.append(button);
  }
}

function showFileText(node, content) {
  if (!node) return;
  if (node instanceof HTMLTextAreaElement) node.value = content;
  else node.textContent = content;
}

function createFileMarkdown(path, content, truncated = false) {
  if (truncated || !/\.(md|markdown)$/i.test(path || "")) return null;
  const preview = document.createElement("div");
  preview.className = "note-body file-markdown";
  preview.innerHTML = renderMarkdown(content);
  return preview;
}

function bindFilePreviewToggle(button, raw, onChange, previewLabel = t("preview", "Preview")) {
  button.textContent = raw ? previewLabel : t("verification_raw", "Raw");
  button.setAttribute("aria-pressed", String(raw));
  button.onclick = () => onChange(!raw);
}

export { bindFilePreviewToggle, createFileMarkdown, createFileRead, formatBytes, renderFileTree, selectFile, showFileText };
