import { listValue, t } from "./shared.js";
import { bindFilePreviewToggle, createFileMarkdown, createFileRead, formatBytes, renderFileTree, selectFile, showFileText } from "./file-browser.js";

function createTaskBrowser(options = {}) {
  const fileRead = createFileRead();
  const collapsed = new Set();
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
    draftText: "",
    raw: false,
    dirty: false,
    busy: false,
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
      if (!canEditFile()) return;
      browser.draftText = editor.value;
      setDirty(editor.value !== browser.savedText);
      syncControls();
    });
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "action-button compact";
    toggle.dataset.filePreviewToggle = "";
    toggle.hidden = true;
    (node(".harbor-editor-actions") || node(".harbor-editor-head") || editor.parentElement).append(toggle);
    const preview = document.createElement("div");
    preview.className = "harbor-markdown";
    preview.dataset.harborMarkdown = "";
    preview.hidden = true;
    editor.before(preview);
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
    fileRead.invalidate();
    browser.detail = detail && typeof detail === "object" ? detail : null;
    browser.taskRef = normalizeTaskRef(selection.taskRef) || detailTaskRef(browser.detail);
    browser.contextKey = selection.contextKey || taskContextKey(browser.taskRef, selection);
    browser.filePath = null;
    browser.fileRevision = null;
    browser.savedText = "";
    browser.draftText = "";
    browser.raw = false;
    setDirty(false);
    browser.previewStatus = "empty";
    browser.previewMessage = "";
    render();

    const tree = listValue(browser.detail?.tree);
    const item = selectFile(tree, {
      preferredPath: selection.preferredPath,
      preservedPath: selection.preserveCurrent ? previousPath : null,
      defaultPath: browser.detail?.default_file_path,
      strictPreferred: selection.strictPreferred,
    });
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
    const isCurrent = fileRead.begin();
    browser.filePath = item.path;
    browser.fileRevision = null;
    browser.savedText = "";
    browser.draftText = "";
    browser.raw = false;
    setDirty(false);
    if (!item.previewable || typeof browser.readFile !== "function" || !browser.taskRef) {
      showUnavailable(item.path, item.previewable
        ? t("task_file_unavailable", "Task file unavailable")
        : t("harbor_metadata_only", "metadata only"), item);
      return null;
    }
    browser.previewStatus = "loading";
    browser.previewMessage = t("loading", "Loading…");
    render();
    try {
      const payload = await browser.readFile(browser.taskRef, item.path);
      if (!isCurrent() || browser.filePath !== item.path) return null;
      browser.fileRevision = payload?.revision || null;
      browser.savedText = String(payload?.content ?? "");
      browser.draftText = browser.savedText;
      setDirty(false);
      browser.previewStatus = "ready";
      browser.previewMessage = "";
      render();
      const editor = node("[data-harbor-editor]");
      if (editor) {
        showFileText(editor, browser.savedText);
        if (options.focus && !editor.hidden) editor.focus();
      }
      return payload;
    } catch (error) {
      if (!isCurrent() || browser.filePath !== item.path) return null;
      showUnavailable(item.path, error?.message || String(error), item);
      browser.onError?.(error);
      return null;
    }
  }

  function showUnavailable(path, message, item = null) {
    fileRead.invalidate();
    browser.filePath = path || null;
    browser.fileRevision = null;
    browser.savedText = "";
    browser.draftText = "";
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
    fileRead.invalidate();
    browser.taskRequestId += 1;
    browser.taskRequestPromise = null;
    browser.detail = null;
    collapsed.clear();
    browser.taskRef = null;
    browser.contextKey = null;
    browser.filePath = null;
    browser.fileRevision = null;
    browser.savedText = "";
    browser.draftText = "";
    browser.raw = false;
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
    renderFileTree(node("[data-harbor-file-tree]"), listValue(browser.detail?.tree), {
      selectedPath: browser.filePath,
      onOpen: item => openItem(item, { focus: true }),
      onContextMenu: browser.onContextMenu,
      collapsed,
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
      ? `${formatBytes(item.size)} · ${item.previewable ? t("harbor_text", "text") : t("harbor_metadata_only", "metadata only")}`
      : "";
    if (!editor) return;
    editor.readOnly = !canEditFile();
    editor.disabled = browser.previewStatus === "empty";
    if (browser.previewStatus === "ready") showFileText(editor, browser.draftText);
    else if (browser.previewStatus === "loading") showFileText(editor, browser.previewMessage);
    else if (browser.previewStatus === "unavailable") showFileText(editor, browser.previewMessage);
    else editor.value = "";
    const preview = node("[data-harbor-markdown]");
    const toggle = node("[data-file-preview-toggle]");
    const markdown = browser.previewStatus === "ready" ? createFileMarkdown(browser.filePath, browser.draftText) : null;
    editor.hidden = Boolean(markdown) && !browser.raw;
    if (preview) {
      preview.hidden = !editor.hidden;
      preview.replaceChildren(...(markdown ? [markdown] : []));
    }
    if (toggle) {
      toggle.hidden = !markdown;
      bindFilePreviewToggle(toggle, browser.raw, raw => { browser.raw = raw; renderPreview(); });
    }
  }

  function canEditFile() {
    return browser.editable && browser.previewStatus === "ready"
      && listValue(browser.detail?.tree).some(item => item.path === browser.filePath && item.editable);
  }

  function syncControls() {
    const save = node("[data-harbor-save]");
    if (save) save.disabled = !canEditFile() || browser.busy || !browser.dirty;
    const path = node("[data-harbor-editor-path]");
    if (path && browser.filePath) path.textContent = `${browser.filePath}${browser.dirty ? " •" : ""}`;
  }

  function setBusy(value) {
    browser.busy = Boolean(value);
    syncControls();
  }

  function setEditable(value) {
    const next = Boolean(value);
    if (browser.editable === next) return;
    browser.editable = next;
    render();
  }

  function setContextMenu(handler) {
    const next = typeof handler === "function" ? handler : null;
    if (browser.onContextMenu === next) return;
    browser.onContextMenu = next;
    render();
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
    rebindTask(taskRef) {
      fileRead.invalidate();
      browser.taskRef = normalizeTaskRef(taskRef);
      browser.contextKey = taskContextKey(browser.taskRef);
    },
    acceptRevision(path, revision) {
      if (browser.filePath === path) browser.fileRevision = revision;
    },
    acceptSave(path, content) {
      if (browser.filePath !== path) return;
      browser.savedText = content;
      setDirty(node("[data-harbor-editor]")?.value !== content);
    },
    attach,
    clear,
    currentFile,
    isDirty: () => browser.dirty,
    loadTask,
    openPath,
    replaceDetail,
    setBusy,
    setContextMenu,
    setEditable,
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

export { createTaskBrowser, formatBytes };
