import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const css = readFileSync(
  new URL("../../src/psycheval/assets/css/26-detail-sidebar.css", import.meta.url),
  "utf8",
);

test("the Task browser uses wide columns, narrow container stacking, and the mobile drawer", () => {
  assert.match(css, /\.detail-sidebar-task-browser\s*\{[^}]*grid-template-columns:minmax\(150px,36%\) minmax\(0,1fr\)/s);
  assert.match(css, /@container detail-task-browser \(max-width:520px\)[\s\S]*grid-template-columns:1fr/);
  assert.match(css, /@media\(max-width:720px\)[\s\S]*\.detail-sidebar\s*\{[^}]*bottom:0[^}]*width:100%/s);
  assert.match(css, /@media\(max-width:720px\)[\s\S]*\.detail-sidebar-resize\s*\{\s*display:none/s);
});
