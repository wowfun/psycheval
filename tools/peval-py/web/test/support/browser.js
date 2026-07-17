import { JSDOM } from "jsdom";

const GLOBAL_NAMES = [
  "window",
  "document",
  "navigator",
  "FormData",
  "Blob",
  "File",
  "URL",
  "URLSearchParams",
  "HTMLElement",
  "Element",
  "Node",
  "requestAnimationFrame",
  "cancelAnimationFrame",
  "fetch",
];

function installBrowserDom(body, options = {}) {
  const dom = new JSDOM(`<!doctype html><html><body>${body}</body></html>`, {
    url: options.url || "http://127.0.0.1:8765/",
    pretendToBeVisual: true,
  });
  const previous = new Map(GLOBAL_NAMES.map(name => [name, globalThis[name]]));
  for (const name of GLOBAL_NAMES) {
    const value = name === "fetch" && options.fetch
      ? options.fetch
      : name === "requestAnimationFrame"
      ? callback => callback(0)
      : name === "cancelAnimationFrame"
        ? () => {}
        : dom.window[name];
    Object.defineProperty(globalThis, name, {
      configurable: true,
      writable: true,
      value,
    });
  }
  dom.window.confirm = options.confirm || (() => true);
  if (options.fetch) dom.window.fetch = options.fetch;
  return {
    dom,
    cleanup() {
      dom.window.close();
      for (const [name, value] of previous) {
        if (value === undefined) delete globalThis[name];
        else Object.defineProperty(globalThis, name, {
          configurable: true,
          writable: true,
          value,
        });
      }
    },
  };
}

export { installBrowserDom };
