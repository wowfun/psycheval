// @ts-check

const LOCAL_SRC = "/assets/echarts/6.0.0/echarts.min.js";
/** @type {Promise<void> | null} */
let loading = null;

function ensureEcharts() {
  if (globalThis.echarts) return Promise.resolve();
  if (loading) return loading;
  loading = loadScript(LOCAL_SRC).catch(error => {
    loading = null;
    throw error;
  });
  return loading;
}

/** @param {string} src */
function loadScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.addEventListener("load", () => resolve(), { once: true });
    script.addEventListener("error", () => {
      script.remove();
      reject(new Error(`Failed to load ${src}`));
    }, { once: true });
    document.head.append(script);
  });
}

export { ensureEcharts };
