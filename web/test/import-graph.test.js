import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const WEB_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../../src/psycheval/assets/web");
const STATIC_IMPORT = /^import(?:[\s\S]*?from\s*)?["']([^"']+)["'];/gm;

function staticGraph(entry) {
  const seen = new Set();
  const visit = path => {
    const resolved = resolve(path);
    if (seen.has(resolved)) return;
    seen.add(resolved);
    const source = readFileSync(resolved, "utf8");
    for (const match of source.matchAll(STATIC_IMPORT)) {
      if (match[1].startsWith(".")) visit(resolve(dirname(resolved), match[1]));
    }
  };
  visit(resolve(WEB_ROOT, entry));
  return new Set([...seen].map(path => relative(WEB_ROOT, path)));
}

test("the static entry graph contains only the Workspace kernel", () => {
  assert.deepEqual([...staticGraph("main.js")].sort(), [
    "app/browser-platform.js",
    "app/render-options.js",
    "app/workspace-app.js",
    "app/workspace-runtime.js",
    "main.js",
  ]);
});

test("non-Home pages cannot pull Home runtime or sibling page implementations", () => {
  for (const page of ["datasets", "reports", "config"]) {
    const graph = staticGraph(`pages/${page}-page.js`);
    assert.equal(graph.has("modules/runtime.js"), false, page);
    assert.equal(graph.has("modules/home-controls.js"), false, page);
    assert.equal(graph.has("modules/workspace-reports.js"), false, page);
    assert.equal(
      [...graph].some(path => path.startsWith("pages/") && path !== `pages/${page}-page.js`),
      false,
      page,
    );
  }
});

test("lightweight shared seams do not import the Home runtime", () => {
  for (const module of [
    "modules/shared.js",
    "modules/http.js",
    "modules/data-tables.js",
    "modules/report-store.js",
  ]) {
    assert.equal(staticGraph(module).has("modules/runtime.js"), false, module);
  }
});
