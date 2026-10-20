import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const dom = installBrowserDom('<script id="peval-i18n" type="application/json">{}</script>');
const { createJsonView } = await import("../../src/psycheval/assets/web/modules/json-view.js");
test.after(() => dom.cleanup());
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

test("objects and arrays start fully expanded and preserve individual fold choices", async () => {
  const view = createJsonView('{"checks":[{"id":"answer","passed":true}],"judge":{"status":"complete"}}');
  assert.equal(view.querySelector("[data-json-root]").open, true);
  const checks = view.querySelector('[data-json-key="checks"]');
  assert.equal(checks.open, true);
  const item = checks.querySelector('[data-json-key="0"]');
  assert.equal(item.open, true);
  assert.equal(view.querySelectorAll("details:not([open])").length, 0);
  assert.equal(item.querySelector('[data-json-key="passed"]').textContent, '"passed": true');
  item.querySelector("summary").click(); await tick();
  assert.equal(item.open, false);
  checks.querySelector("summary").click(); await tick();
  assert.equal(checks.open, false);
  checks.querySelector("summary").click(); await tick();
  assert.equal(checks.open, true);
  assert.equal(item.open, false);
});

test("large collections render only the requested batches", () => {
  const view = createJsonView(JSON.stringify(Array.from({ length: 205 }, (_, i) => i)));
  assert.equal(view.querySelectorAll(".json-leaf").length, 100);
  view.querySelector(".json-more").click();
  assert.equal(view.querySelectorAll(".json-leaf").length, 200);
  view.querySelector(".json-more").click();
  assert.equal(view.querySelectorAll(".json-leaf").length, 205);
  assert.equal(view.querySelector(".json-more"), null);
  assert.equal(view.querySelector('[data-json-key="204"]').textContent, "[204]: 204");
});

test("additional batches also start fully expanded", () => {
  const view = createJsonView(JSON.stringify(Array.from({ length: 101 }, () => ({ nested: ["line one\nline two"] }))));
  assert.equal(view.querySelectorAll("details:not([open])").length, 0);
  view.querySelector(".json-more").click();
  const last = view.querySelector('[data-json-root] > .json-children > [data-json-key="100"]');
  assert.equal(last.open, true);
  assert.equal(last.querySelectorAll("details:not([open])").length, 0);
  assert.equal(last.querySelector(".json-string-text").textContent, "line one\nline two");
});

test("long strings start expanded and fold independently with faithful multiline text", async () => {
  const content = "First line\n" + "Retained evidence ".repeat(100);
  const view = createJsonView(JSON.stringify({ content }));
  const branch = view.querySelector('[data-json-key="content"]');
  assert.equal(branch.open, true);
  assert.equal(branch.querySelector(".json-string-text").textContent, content);
  branch.querySelector("summary").click(); await tick();
  assert.equal(branch.open, false);
  branch.querySelector("summary").click(); await tick();
  assert.equal(branch.open, true);
  assert.equal(branch.querySelector(".json-string-text").textContent, content);
});

test("keys and strings remain inert text including prototype names", () => {
  const key = '<img src=x onerror="unsafe()">';
  const view = createJsonView(JSON.stringify({ [key]: "<script>unsafe()</script>", __proto__: null, constructor: { safe: true } }));
  assert.equal(view.querySelector("img,script"), null);
  assert.ok(view.textContent.includes(JSON.stringify(key)));
  const branch = view.querySelector('[data-json-key="constructor"]');
  assert.equal(branch.open, true);
  assert.ok(branch.textContent.includes('"safe": true'));
  const prototype = createJsonView('{"__proto__":{"polluted":true}}');
  assert.equal({}.polluted, undefined);
  assert.ok(prototype.querySelector('[data-json-key="__proto__"]'));
});

test("numeric literals retain precision, notation, and negative zero", () => {
  const view = createJsonView('{"large":9007199254740993,"fraction":1.2300,"exponent":1e400,"negativeZero":-0}');
  assert.deepEqual([...view.querySelectorAll(".json-number")].map(node => node.textContent), ["9007199254740993", "1.2300", "1e400", "-0"]);
});

test("numeric previews remain available when the reviver has no source context", () => {
  const parse = JSON.parse;
  JSON.parse = (content, reviver) => parse(content, reviver ? (key, value) => reviver(key, value) : undefined);
  try {
    const view = createJsonView('{"value":12.5,"zero":-0}');
    assert.deepEqual([...view.querySelectorAll(".json-number")].map(node => node.textContent), ["12.5", "-0"]);
  } finally { JSON.parse = parse; }
});

test("nested large collections bound DOM work on initial display and each batch", () => {
  const view = createJsonView(JSON.stringify(Array.from({ length: 100 }, () => Array.from({ length: 100 }, (_, i) => i))));
  const count = () => view.querySelectorAll(".json-branch,.json-leaf").length;
  assert.ok(count() <= 1000);
  const before = count();
  view.querySelector(".json-more").click();
  assert.ok(count() > before && count() <= before + 1000);
});

test("deep trees defer descendants until the user opens the branch", async () => {
  let value = { answer: 42 };
  for (let i = 0; i < 50; i += 1) value = { nested: value };
  const view = createJsonView(JSON.stringify(value));
  const branch = view.querySelector("details:not([open])");
  assert.ok(branch);
  assert.equal(branch.querySelector(".json-children").childElementCount, 0);
  branch.querySelector("summary").click(); await tick();
  assert.ok(branch.querySelector(".json-children").childElementCount > 0);
  const count = view.querySelectorAll("details").length;
  branch.querySelector("summary").click(); await tick();
  branch.querySelector("summary").click(); await tick();
  assert.equal(view.querySelectorAll("details").length, count);
});

test("root scalars and empty collections retain their types", () => {
  for (const content of ["null", "false", "0", '"hello"', "[]", "{}"]) {
    const view = createJsonView(content);
    assert.equal(view.textContent, content);
    assert.equal(view.querySelector("details"), null);
  }
  assert.throws(() => createJsonView("{broken"), SyntaxError);
});
