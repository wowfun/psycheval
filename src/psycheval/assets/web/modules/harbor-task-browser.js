import { listValue, t } from "./shared.js";

function createTaskBrowser(options = {}) {
  const browser = {
    root: options.root || null,
    editable: Boolean(options.editable),
    readFile: options.readFile,
    loadTask: options.loadTask,
    onContextMenu: options.onContextMenu || null,
    onDirtyChange: options.onDirtyChange || null,
    onError: options.onError || null,
    detail: null,
    taskRef: null,
    contextKey: null,
    filePath: null,
    fileRevision: null,
    savedText: "",
    dirty: false,
    busy: false,
    requestId: 0,
    taskRequestId: 0,
    taskRequestPromise: null,
    previewStatus: "empty",
    previewMessage: "",
  };

  function attach(root) {
    browser.root = root || null;
    bindEditor();
    render();
    return api;
  }

  function bindEditor() {
    const editor = node("[data-harbor-editor]");
    if (!editor || editor.dataset.taskBrowserBound === "true") return;
    editor.dataset.taskBrowserBound = "true";
    editor.addEventListener("input", () => {
      if (!browser.editable || browser.previewStatus !== "ready") return;
      setDirty(editor.value !== browser.savedText);
      syncControls();
    });
  }

  async function loadTask(taskRef, selection = {}) {
    const normalizedRef = normalizeTaskRef(taskRef);
    const contextKey = selection.contextKey || taskContextKey(normalizedRef, selection);
    if (browser.contextKey === contextKey && browser.detail) {
      render();
      return browser.detail;
    }
    if (browser.contextKey === contextKey && browser.taskRequestPromise) {
      render();
      return browser.taskRequestPromise;
    }
    resetState({ keepRoot: true });
    browser.taskRef = normalizedRef;
    browser.contextKey = contextKey;
    if (!normalizedRef || typeof browser.loadTask !== "function") {
      showUnavailable(selection.preferredPath, t("task_files_unavailable", "Task files unavailable"));
      return null;
    }
    const requestId = browser.taskRequestId + 1;
    browser.taskRequestId = requestId;
    browser.previewStatus = "loading";
    browser.previewMessage = t("loading", "Loading…");
    render();
    const operation = (async () => {
      try {
        const detail = await browser.loadTask(normalizedRef);
        if (requestId !== browser.taskRequestId || contextKey !== browser.contextKey) return null;
        await setTaskDetail(detail, { ...selection, taskRef: normalizedRef, contextKey });
        return detail;
      } catch (error) {
        if (requestId !== browser.taskRequestId || contextKey !== browser.contextKey) return null;
        showUnavailable(selection.preferredPath, error?.message || String(error));
        browser.onError?.(error);
        return null;
      }
    })();
    browser.taskRequestPromise = operation;
    try {
      return await operation;
    } finally {
      if (browser.taskRequestPromise === operation) {
        browser.taskRequestPromise = null;
      }
    }
  }

  async function setTaskDetail(detail, selection = {}) {
    const previousPath = browser.filePath;
    browser.requestId += 1;
    browser.detail = detail && typeof detail === "object" ? detail : null;
    browser.taskRef = normalizeTaskRef(selection.taskRef) || detailTaskRef(browser.detail);
    browser.contextKey = selection.contextKey || taskContextKey(browser.taskRef, selection);
    browser.filePath = null;
    browser.fileRevision = null;
    browser.savedText = "";
    setDirty(false);
    browser.previewStatus = "empty";
    browser.previewMessage = "";
    render();

    const tree = listValue(browser.detail?.tree);
    const preferredItem = selection.preferredPath
      ? tree.find(value => value?.kind === "file" && value?.path === selection.preferredPath) || null
      : null;
    const preservedItem = selection.preserveCurrent
      ? tree.find(value => value?.kind === "file" && value?.path === previousPath) || null
      : null;
    const defaultItem = tree.find(value => value?.kind === "file" && value?.path === browser.detail?.default_file_path) || null;
    const item = selection.strictPreferred
      ? preferredItem
      : preferredItem || preservedItem || defaultItem;
    if (!item) {
      const unavailablePath = selection.preferredPath || browser.detail?.default_file_path || null;
      const message = selection.strictPreferred
        ? t("task_step_instruction_unavailable", "Current step instruction unavailable")
        : t("task_default_file_unavailable", "Default Task instruction unavailable");
      showUnavailable(unavailablePath, message);
      return browser.detail;
    }
    await openItem(item, { skipDiscard: true, focus: Boolean(selection.focus) });
    return browser.detail;
  }

  async function openPath(path, options = {}) {
    const item = listValue(browser.detail?.tree).find(value => value?.path === path) || null;
    if (!item) {
      showUnavailable(path, t("task_file_unavailable", "Task file unavailable"));
      return null;
    }
    return openItem(item, options);
  }

  async function openItem(item, options = {}) {
    if (!item || item.kind !== "file") return null;
    if (!options.skipDiscard && browser.dirty && !window.confirm(t("harbor_discard_changes", "Discard unsaved file changes?"))) return null;
    const requestId = browser.requestId + 1;
    browser.requestId = requestId;
    browser.filePath = item.path;
    browser.fileRevision = null;
    browser.savedText = "";
    setDirty(false);
    if (!item.editable || typeof browser.readFile !== "function" || !browser.taskRef) {
      showUnavailable(item.path, item.editable
        ? t("task_file_unavailable", "Task file unavailable")
        : t("harbor_metadata_only", "metadata only"), item);
      return null;
    }
    browser.previewStatus = "loading";
    browser.previewMessage = t("loading", "Loading…");
    render();
    try {
      const payload = await browser.readFile(browser.taskRef, item.path);
      if (requestId !== browser.requestId || browser.filePath !== item.path) return null;
      browser.fileRevision = payload?.revision || null;
      browser.savedText = String(payload?.content ?? "");
      setDirty(false);
      browser.previewStatus = "ready";
      browser.previewMessage = "";
      render();
      const editor = node("[data-harbor-editor]");
      if (editor) {
        editor.value = browser.savedText;
        if (options.focus) editor.focus();
      }
      return payload;
    } catch (error) {
      if (requestId !== browser.requestId || browser.filePath !== item.path) return null;
      showUnavailable(item.path, error?.message || String(error), item);
      browser.onError?.(error);
      return null;
    }
  }

  function showUnavailable(path, message, item = null) {
    browser.requestId += 1;
    browser.filePath = path || null;
    browser.fileRevision = null;
    browser.savedText = "";
    setDirty(false);
    browser.previewStatus = "unavailable";
    browser.previewMessage = String(message || t("task_file_unavailable", "Task file unavailable"));
    render(item);
  }

  function replaceDetail(detail, options = {}) {
    return setTaskDetail(detail, {
      taskRef: options.taskRef || browser.taskRef,
      preferredPath: options.preferredPath,
      strictPreferred: options.strictPreferred,
      preserveCurrent: options.preserveCurrent !== false,
      contextKey: options.contextKey || browser.contextKey,
      focus: options.focus,
    });
  }

  function clear(message = null) {
    resetState({ keepRoot: true });
    if (message) {
      browser.previewStatus = "unavailable";
      browser.previewMessage = String(message);
    }
    render();
  }

  function resetState({ keepRoot = false } = {}) {
    browser.requestId += 1;
    browser.taskRequestId += 1;
    browser.taskRequestPromise = null;
    browser.detail = null;
    browser.taskRef = null;
    browser.contextKey = null;
    browser.filePath = null;
    browser.fileRevision = null;
    browser.savedText = "";
    browser.dirty = false;
    browser.previewStatus = "empty";
    browser.previewMessage = "";
    if (!keepRoot) browser.root = null;
  }

  function render(metadataItem = null) {
    renderTree();
    renderPreview(metadataItem);
    syncControls();
  }

  function renderTree() {
    const container = node("[data-harbor-file-tree]");
    if (!container) return;
    container.replaceChildren();
    const tree = listValue(browser.detail?.tree);
    if (!tree.length) {
      container.append(emptyNode(t("harbor_file_empty", "Select a Task to browse its files")));
      return;
    }
    tree.forEach(item => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `harbor-file-row kind-${item.kind}`;
      button.classList.toggle("selected", item.path === browser.filePath);
      button.style.setProperty("--depth", String(item.path.split("/").length - 1));
      button.append(
        textNode("span", item.kind === "directory" ? "▸" : "·"),
        textNode("span", item.path.split("/").at(-1)),
        textNode("small", item.kind === "file" ? formatBytes(item.size) : ""),
      );
      if (item.kind === "file") button.addEventListener("click", () => openItem(item, { focus: true }));
      if (browser.onContextMenu) {
        button.addEventListener("contextmenu", event => {
          event.preventDefault();
          browser.onContextMenu(item);
        });
      }
      container.append(button);
    });
  }

  function renderPreview(metadataItem = null) {
    const editor = node("[data-harbor-editor]");
    const path = node("[data-harbor-editor-path]");
    const meta = node("[data-harbor-editor-meta]");
    const item = metadataItem || listValue(browser.detail?.tree).find(value => value?.path === browser.filePath) || null;
    if (path) path.textContent = browser.filePath
      ? `${browser.filePath}${browser.dirty ? " •" : ""}`
      : t("harbor_editor_empty", "Select a text file");
    if (meta) meta.textContent = item
      ? `${formatBytes(item.size)} · ${item.editable ? t("harbor_text", "text") : t("harbor_metadata_only", "metadata only")}`
      : "";
    if (!editor) return;
    editor.readOnly = !browser.editable || browser.previewStatus !== "ready";
    editor.disabled = browser.previewStatus === "empty";
    if (browser.previewStatus === "ready") editor.value = browser.savedText;
    else if (browser.previewStatus === "loading") editor.value = browser.previewMessage;
    else if (browser.previewStatus === "unavailable") editor.value = browser.previewMessage;
    else editor.value = "";
  }

  function syncControls() {
    const save = node("[data-harbor-save]");
    if (save) save.disabled = !browser.editable || browser.busy || !browser.dirty || !browser.filePath;
    const path = node("[data-harbor-editor-path]");
    if (path && browser.filePath) path.textContent = `${browser.filePath}${browser.dirty ? " •" : ""}`;
  }

  function setBusy(value) {
    browser.busy = Boolean(value);
    syncControls();
  }

  function setDirty(value) {
    const next = Boolean(value);
    const changed = browser.dirty !== next;
    browser.dirty = next;
    if (changed) browser.onDirtyChange?.(next);
  }

  function currentFile() {
    const editor = node("[data-harbor-editor]");
    return {
      path: browser.filePath,
      revision: browser.fileRevision,
      content: editor ? editor.value : browser.savedText,
      savedText: browser.savedText,
      dirty: browser.dirty,
      status: browser.previewStatus,
    };
  }

  function node(selector) {
    return browser.root?.querySelector?.(selector) || null;
  }

  const api = {
    attach,
    clear,
    currentFile,
    isDirty: () => browser.dirty,
    loadTask,
    openPath,
    replaceDetail,
    setBusy,
    setTaskDetail,
    state: browser,
  };
  attach(browser.root);
  return api;
}

function normalizeTaskRef(value) {
  if (!value || typeof value !== "object") return null;
  const datasetId = String(value.dataset_id || "").trim();
  const task = String(value.task || "").trim();
  return datasetId && task ? { dataset_id: datasetId, task } : null;
}

function detailTaskRef(detail) {
  const datasetId = String(detail?.dataset_id || "").trim();
  const task = String(detail?.task?.directory || "").trim();
  return datasetId && task ? { dataset_id: datasetId, task } : null;
}

function taskContextKey(taskRef, selection = {}) {
  return [taskRef?.dataset_id || "", taskRef?.task || "", selection.preferredPath || "", selection.strictPreferred ? "strict" : "default"].join("\u0000");
}

function textNode(tag, value) {
  const result = document.createElement(tag);
  result.textContent = String(value ?? "");
  return result;
}

function emptyNode(value) {
  const result = textNode("p", value);
  result.className = "copy harbor-empty";
  return result;
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}

export { createTaskBrowser, formatBytes };
