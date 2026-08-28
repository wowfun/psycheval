import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const detailCss = readFileSync(
  new URL("../../src/psycheval/assets/css/26-detail-sidebar.css", import.meta.url),
  "utf8",
);
const sidebarCss = readFileSync(
  new URL("../../src/psycheval/assets/css/25-sidebar.css", import.meta.url),
  "utf8",
);
const viewsCss = readFileSync(
  new URL("../../src/psycheval/assets/css/30-workspace-views.css", import.meta.url),
  "utf8",
);
const reportsCss = readFileSync(
  new URL("../../src/psycheval/assets/css/28-workspace-reports.css", import.meta.url),
  "utf8",
);

test("the Task browser uses wide columns, narrow container stacking, and the mobile drawer", () => {
  assert.match(detailCss, /\.detail-sidebar-task-browser\s*\{[^}]*grid-template-columns:minmax\(150px,36%\) minmax\(0,1fr\)/s);
  assert.match(detailCss, /@container detail-task-browser \(max-width:520px\)[\s\S]*grid-template-columns:1fr/);
  assert.match(detailCss, /@media\(max-width:720px\)[\s\S]*\.detail-sidebar\s*\{[^}]*bottom:0[^}]*width:100%/s);
  assert.match(detailCss, /@media\(max-width:720px\)[\s\S]*\.detail-sidebar>\.sidebar-resize\s*\{\s*display:none/s);
  assert.match(reportsCss, /@media\(max-width:700px\)[\s\S]*\.report-reader>\.sidebar-resize\s*\{\s*display:none/s);
  assert.match(viewsCss, /@media \(max-width:1180px\)[\s\S]*\.workspace-views>\.sidebar-resize\s*\{\s*display:none/s);
});

test("shared handles stay fully exposed while sidebar panels own clipping", () => {
  assert.match(sidebarCss, /\.sidebar-resize\s*\{[^}]*width:14px/s);
  assert.match(sidebarCss, /\[data-sidebar-side="left"\]>\.sidebar-resize\s*\{\s*right:-7px/s);
  assert.match(sidebarCss, /\[data-sidebar-side="right"\]>\.sidebar-resize\s*\{\s*left:-7px/s);
  assert.match(detailCss, /\.detail-sidebar\s*\{[^}]*overflow:visible/s);
  assert.match(detailCss, /\.detail-sidebar-panel\s*\{[^}]*overflow:hidden/s);
  assert.match(viewsCss, /\.workspace-views\s*\{[^}]*overflow:visible/s);
  assert.match(viewsCss, /\.workspace-views-panel\s*\{[^}]*overflow:auto/s);
  assert.match(detailCss, /\.detail-sidebar-body\.has-task\s*\{[^}]*grid-template-rows:minmax\(260px,min\(360px,48dvh\)\) minmax\(0,1fr\)/s);
});
