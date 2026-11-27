import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom('<script type="application/json" id="peval-i18n">{}</script><script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin","workspace_id":"ws-test"}</script>');
const custom = await import("../../src/psycheval/assets/web/modules/task-custom-columns.js");
test.after(() => browser.cleanup());

test("custom column key validation and canonical RFC 3986 encoding match backend rules", () => {
  for (const reserved of ["category", "difficulty", "source_case"]) {
    assert.throws(() => custom.validateCustomColumnKey(reserved), /reserved/i);
  }
  for (const invalid of ["", "   ", " lead", "trail ", "bad\nkey", "a".repeat(129)]) {
    assert.throws(() => custom.validateCustomColumnKey(invalid));
  }
  const cases = [
    ["qa_status", "meta:qa_status"],
    ["qa-v1.0_~", "meta:qa-v1.0_~"],
    ["qa status", "meta:qa%20status"],
    ["质检状态", "meta:%E8%B4%A8%E6%A3%80%E7%8A%B6%E6%80%81"],
    ["a!b(c)'d*", "meta:a%21b%28c%29%27d%2A"],
  ];
  for (const [raw, expected] of cases) {
    assert.equal(custom.encodeCustomColumnKey(raw), expected);
    assert.equal(custom.isCustomColumnKey(expected), true);
    assert.equal(custom.decodeCustomColumnKey(expected), raw);
  }
  for (const bad of ["qa_status", "meta:", "meta:category", "meta:%61", "meta:%ZZ"]) {
    assert.equal(custom.isCustomColumnKey(bad), false);
    assert.equal(custom.decodeCustomColumnKey(bad), null);
  }
});

test("type inference and discovery merge task.toml keys with browser schemas", () => {
  const rows = [
    { kind: "task", dataset: { id: "native", read_only: false }, task: { custom_metadata: { score_tier: 1, checked: true, tags_extra: ["a", "b"], complex: { nested: 1 } } } },
    { kind: "task", dataset: { id: "office", read_only: true }, task: { custom_metadata: { score_tier: 2, checked: false, note: "from-toml" } } },
  ];
  const inferred = new Map(custom.discoverCustomColumns(rows, []).map(col => [col.rawKey, col]));
  assert.equal(inferred.get("score_tier").type, "number");
  assert.equal(inferred.get("checked").type, "boolean");
  assert.equal(inferred.get("tags_extra").type, "list");
  assert.equal(inferred.get("complex").type, "readonly");
  assert.equal(inferred.get("note").type, "text");

  const discovered = custom.discoverCustomColumns(rows, [
    { key: "qa_status", type: "enum", options: ["OK", "POK", "NOK"] },
    { key: "note", type: "enum", options: ["from-toml", "other"] },
  ]);
  const byKey = new Map(discovered.map(col => [col.rawKey, col]));
  assert.equal(byKey.get("score_tier").type, "number");
  assert.equal(byKey.get("score_tier").hasWritableData, true);
  assert.equal(byKey.get("score_tier").hasReadOnlyData, true);
  assert.equal(byKey.get("qa_status").type, "enum");
  assert.equal(byKey.get("qa_status").hasData, false);
  assert.deepEqual(byKey.get("note").options, ["from-toml", "other"]);
});

test("discovery caps auto-discovered columns while preserving defined schemas and top populated keys", () => {
  const rows = [];
  for (let index = 0; index < 80; index += 1) {
    const key = `k_${String(index).padStart(3, "0")}`;
    rows.push({ kind: "task", dataset: { id: "native", read_only: false }, task: { custom_metadata: { [key]: "v" } } });
  }
  // Make k_079 populated across 3 rows so it beats single-row discovered keys.
  rows.push({ kind: "task", dataset: { id: "native", read_only: false }, task: { custom_metadata: { k_079: "v2" } } });
  rows.push({ kind: "task", dataset: { id: "native", read_only: false }, task: { custom_metadata: { k_079: "v3" } } });

  const discovered = custom.discoverCustomColumns(rows, [{ key: "explicit_empty", type: "text", options: [] }]);
  assert.equal(discovered.length, 65);
  assert.ok(discovered.some(col => col.rawKey === "explicit_empty"));
  assert.ok(discovered.some(col => col.rawKey === "k_079"));
  assert.ok(!discovered.some(col => col.rawKey === "k_078"));
});

test("parseCustomColumnInput validates all supported types, allows Cf chars, and reports value-specific errors", () => {
  assert.equal(custom.parseCustomColumnInput("text", "  "), null);
  assert.equal(custom.parseCustomColumnInput("text", "alice"), "alice");
  // Unicode Cf format characters (ZWJ emoji, soft hyphen, RTL mark) are allowed; Cc controls fail.
  for (const sample of ["👨‍👩‍👧‍👦", "soft\u00adhyphen", "rtl\u200ftext"]) {
    assert.equal(custom.validateCustomColumnKey(sample), sample);
    assert.equal(custom.parseCustomColumnInput("text", sample), sample);
    assert.deepEqual(custom.parseCustomColumnInput("list", sample), [sample]);
  }
  assert.throws(() => custom.parseCustomColumnInput("text", "bad\x00value"), /valid text without control characters/i);
  assert.throws(() => custom.parseCustomColumnInput("text", "x".repeat(16 * 1024 + 1)), /16 KiB/i);
  assert.throws(() => custom.parseCustomColumnInput("list", "x".repeat(257)), /256 UTF-8 bytes/i);
  assert.throws(
    () => custom.parseCustomColumnInput("list", Array.from({ length: 129 }, (_, i) => `item${i}`).join(",")),
    /128 list items/i,
  );
  assert.equal(custom.parseCustomColumnInput("number", "0"), 0);
  assert.equal(custom.parseCustomColumnInput("number", "-2.5"), -2.5);
  assert.equal(custom.parseCustomColumnInput("number", ""), null);
  assert.throws(() => custom.parseCustomColumnInput("number", "abc"));
  assert.equal(custom.parseCustomColumnInput("boolean", "true"), true);
  assert.equal(custom.parseCustomColumnInput("boolean", "false"), false);
  assert.equal(custom.parseCustomColumnInput("boolean", ""), null);
  assert.throws(() => custom.parseCustomColumnInput("boolean", "maybe"));
  assert.equal(custom.parseCustomColumnInput("enum", "OK", ["OK", "NOK"]), "OK");
  assert.equal(custom.parseCustomColumnInput("enum", "", ["OK", "NOK"]), null);
  assert.throws(() => custom.parseCustomColumnInput("enum", "BAD", ["OK", "NOK"]));
  assert.deepEqual(custom.parseCustomColumnInput("list", "不漏，不重, 不漏"), ["不漏", "不重"]);
  assert.equal(custom.parseCustomColumnInput("list", " , "), null);
});

test("schema persistence survives reload and ignores malformed entries", () => {
  const storage = window.localStorage;
  storage.clear();
  custom.saveCustomColumnSchemas([
    { key: "qa_status", type: "enum", options: ["OK", "POK", "NOK"] },
    { key: "priority", type: "number" },
    { key: "category", type: "text" },
  ], { workspaceId: "ws-1", storage });
  assert.deepEqual(custom.loadCustomColumnSchemas({ workspaceId: "ws-1", storage }), [
    { key: "qa_status", type: "enum", options: ["OK", "POK", "NOK"] },
    { key: "priority", type: "number", options: [] },
  ]);
  assert.deepEqual(custom.loadCustomColumnSchemas({ workspaceId: "ws-other", storage }), []);
});
