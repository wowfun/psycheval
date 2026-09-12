import { t } from "./shared.js";
import { serveApi } from "./serve-effects.js";
import { bindCopyButton } from "./clipboard.js";
import { bindFilePreviewToggle, createFileMarkdown, createFileRead, formatBytes, renderFileTree, selectFile, showFileText } from "./file-browser.js";
import { interpretVerificationFile, renderVerificationDocument } from "./verification-formats.js";

function createVerificationBrowser({ request = serveApi } = {}) {
  const element = document.createElement("div"); element.className = "verification-browser";
  element.innerHTML = `<section class="verification-files"><input type="search" data-verification-search><div class="harbor-file-tree" data-verification-tree></div></section>
    <section class="verification-preview"><header class="verification-file-head"><strong data-verification-path></strong><span data-verification-size></span><div data-verification-actions></div></header><p class="verification-notice" data-verification-notice hidden></p><div class="verification-content" data-verification-content></div></section>`;
  const node = selector => element.querySelector(selector);
  const search = node("[data-verification-search]");
  search.placeholder = t("verification_search_files", "Search files"); search.setAttribute("aria-label", search.placeholder);
  const fileRead = createFileRead(); const treeRead = createFileRead();
  const collapsed = new Set();
  let sourceKey = null, contextKey = null, tree = [], selected = null, payload = null, loaded = false, loading = null;
  function notice(text) { const target = node("[data-verification-notice]"); target.textContent = text; target.hidden = !text; }
  const contentNode = () => node("[data-verification-content]");
  const url = item => `/api/verification-files/${encodeURIComponent(sourceKey)}/${encodeURIComponent(item.id)}`;
  function renderTree() {
    renderFileTree(node("[data-verification-tree]"), tree, { selectedPath: selected?.path, onOpen: open,
      collapsed, search: search.value, emptyMessage: t("verification_no_files", "No retained verification files") });
  }
  search.addEventListener("input", renderTree);
  async function evidence(id) {
    const current = sourceKey; const currentSelection = selected;
    const manifest = tree.find(item => item.path === "verifier/artifact_manifest.json");
    if (!manifest) { notice(t("verification_evidence_missing", "Linked evidence is unavailable")); return; }
    try {
      const raw = await request(url(manifest));
      if (current !== sourceKey || currentSelection !== selected) return;
      const data = raw.truncated ? null : JSON.parse(raw.content);
      const artifact = data?.artifacts?.find(item => item?.id === id);
      const safe = path => typeof path === "string" && !/[\\:]/.test(path) && path.split("/").every(part => part && part !== "." && part !== "..");
      const linked = path => safe(path) ? tree.find(item => item.kind === "file" && item.path === `verifier/${path}`) : null;
      const retainedOriginal = linked(artifact?.verifier_raw_path);
      const item = linked(artifact?.text_path) || retainedOriginal;
      if (!item) notice(t("verification_evidence_missing", "Linked evidence is unavailable"));
      else await open(item);
    } catch (error) { if (current === sourceKey && currentSelection === selected) notice(error.message); }
  }
  function renderPreview() {
    const body = contentNode(); body.replaceChildren();
    const actions = node("[data-verification-actions]"); actions.replaceChildren();
    node("[data-verification-path]").textContent = selected?.path || "";
    node("[data-verification-size]").textContent = selected ? formatBytes(selected.size) : "";
    if (!selected) return;
    if (selected.preview_kind === "image") {
      const image = document.createElement("img"); image.alt = selected.path; image.src = url(selected);
      image.onerror = () => { if (body.contains(image)) notice(t("verification_preview_failed", "File preview unavailable")); };
      body.append(image); return;
    }
    if (!payload) return;
    const raw = document.createElement("pre"); raw.className = "verification-raw"; showFileText(raw, payload.content);
    const copy = document.createElement("button"); copy.className = "action-button compact"; copy.textContent = t("copy", "Copy");
    bindCopyButton(copy, () => payload?.content || "", selected.path); actions.append(copy);
    const model = interpretVerificationFile(selected.path, payload.content, payload.truncated);
    const markdown = createFileMarkdown(selected.path, payload.content, payload.truncated);
    if (payload.truncated) notice(t("verification_truncated", "Preview truncated at 2 MiB."));
    if (!model && !markdown) {
      if (!payload.truncated && selected.path.endsWith(".json")) {
        try { showFileText(raw, JSON.stringify(JSON.parse(payload.content), null, 2)); }
        catch { notice(t("verification_malformed_preview", "Invalid structured data; showing raw text.")); }
      }
      body.append(raw); return;
    }
    const formatted = markdown || renderVerificationDocument(model, evidence);
    body.append(formatted);
    const toggle = document.createElement("button"); toggle.className = "action-button compact";
    toggle.dataset.verificationRaw = "";
    const changeMode = showRaw => {
      body.replaceChildren(showRaw ? raw : formatted);
      bindFilePreviewToggle(toggle, showRaw, changeMode, markdown ? t("preview", "Preview") : t("verification_details", "Details"));
    };
    changeMode(false);
    actions.prepend(toggle);
  }
  async function open(item) {
    const isCurrent = fileRead.begin();
    selected = item; payload = null; notice(""); renderTree(); renderPreview();
    if (!item.previewable) { notice(t("harbor_metadata_only", "metadata only")); return; }
    if (item.preview_kind === "image") return;
    notice(t("loading", "Loading…"));
    try {
      const result = await request(url(item));
      if (!isCurrent()) return;
      payload = result; notice(""); renderPreview();
    } catch (error) { if (isCurrent()) notice(error.message); }
  }
  function setSource(key, revision = "") {
    const nextContext = `${key || ""}\0${revision || ""}`;
    if (nextContext === contextKey) return;
    contextKey = nextContext; sourceKey = key; loaded = false; loading = null;
    treeRead.invalidate(); fileRead.invalidate(); tree = []; selected = null; payload = null;
    collapsed.clear(); search.value = ""; notice(""); renderTree(); renderPreview();
  }
  async function load(meta) {
    if (!sourceKey) { notice(t("verification_no_files", "No retained verification files")); return; }
    if (loaded) return;
    if (loading) return loading;
    const isCurrent = treeRead.begin();
    notice(t("loading", "Loading…"));
    const operation = (async () => {
      try {
        const result = await request(`/api/verification-files/${encodeURIComponent(sourceKey)}`);
        if (!isCurrent()) return;
        tree = Array.isArray(result.tree) ? result.tree : []; loaded = tree.some(item => item.kind === "file"); notice(""); renderTree();
        const preferred = String(meta?.score_message || "").includes("score.json")
          ? ["verifier/score.json", "verifier/reward.json", "verifier/reward.txt"]
          : ["verifier/reward.json", "verifier/reward.txt", "result.json"];
        const path = preferred.find(path => tree.some(item => item.path === path && item.previewable))
          || tree.find(item => item.kind === "file" && item.previewable)?.path
          || tree.find(item => item.kind === "file")?.path;
        const selectedFile = selectFile(tree, { defaultPath: path });
        if (selectedFile) await open(selectedFile);
        else notice(meta?.adapter === "harbor" && meta.status === "running" ? t("verification_not_generated", "Not generated yet") : t("verification_no_files", "No retained verification files"));
      } catch (error) { if (isCurrent()) notice(error.message); }
    })();
    loading = operation;
    try { return await operation; }
    finally { if (loading === operation) loading = null; }
  }
  return { attach(root) { root?.replaceChildren(element); }, setSource, load,
    clear() { setSource(null); }, open, element };
}

export { createVerificationBrowser };
