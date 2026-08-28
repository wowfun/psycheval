// @ts-check

function readRenderOptions() {
  const node = document.getElementById("peval-render-options");
  if (!node) return {};
  try {
    const value = JSON.parse(node.textContent || "{}");
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

const RENDER_OPTIONS = readRenderOptions();

export { RENDER_OPTIONS, readRenderOptions };
