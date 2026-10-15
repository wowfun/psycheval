import assert from "node:assert/strict";
import test from "node:test";
import { encodeWorkspaceLocation, decodeWorkspaceLocation, MAX_LOCATION_BYTES } from "../../src/psycheval/assets/web/app/workspace-location.js";
import { normalizeBrowserView } from "../../src/psycheval/assets/web/modules/workspace-view-repository.js";

test("Saved View names use the server's Unicode character count through storage and links", () => {
  const name = "🙂".repeat(120);
  const view = normalizeBrowserView({ name, filters: {}, group_by: "agent", notes: "" });
  const href = encodeWorkspaceLocation("home", { state: { views: [{ name: view.name, filters: view.filters }] } });
  assert.equal(decodeWorkspaceLocation("home", new URL(href, "http://localhost")).state.views[0].name, name);
  assert.throws(() => normalizeBrowserView({ name: name + "🙂", filters: {}, group_by: "agent", notes: "" }));
});

test("locations round trip identities, Unicode, duplicate predicates and display state deterministically", () => {
  const value = { object: { source: "stable-key", trajectory: "child/中文", step: "2", tab: "trajectory" }, state: {
    query: { search: "中文 + &", page: 3, models: ["mimo", "mimo", "model/中文"], sort: "reward", direction: "asc" },
    views: [{ name: "当地条件", filters: { results: ["failed"] } }], summary: { group_by: "model", statistic: "p95", table_open: true },
  } };
  const href = encodeWorkspaceLocation("home", value, "http://localhost");
  const decoded = decodeWorkspaceLocation("home", new URL(href));
  assert.deepEqual(decoded.object, value.object);
  assert.deepEqual(decoded.state.query.models, ["mimo", "model/中文"]);
  assert.equal(decoded.state.query.search, "中文 + &");
  assert.equal(decoded.state.query.page, 3);
  assert.deepEqual(decoded.state.summary, value.state.summary);
  assert.equal(encodeWorkspaceLocation("home", decoded, "http://localhost"), href);
});
test("defaults are omitted and both report origins retain their opaque references", () => {
  assert.equal(encodeWorkspaceLocation("home"), "/");
  for (const report of ["analysis:" + "a".repeat(64), "package:20261012-120000-000001"]) {
    const href = encodeWorkspaceLocation("reports", { object: { report, tab: "associations" }, state: { query: { state: "archived", kinds: ["dataset"], page: 2 } } });
    const decoded = decodeWorkspaceLocation("reports", new URL(href, "http://localhost"));
    assert.equal(decoded.object.report, report);
    assert.equal(decoded.state.query.state, "archived");
    assert.equal(decoded.state.query.page, 2);
  }
});
test("invalid and oversized states cannot silently widen a shared query", () => {
  for (const state of [{ query: { page: -1 } }, { query: { models: "wrong" } }, { query: { models: [" "] } }, { summary: { statistic: "invalid" } }, { extra: true }]) {
    assert.throws(() => encodeWorkspaceLocation("home", { state }));
  }
  for (const hash of ["#view=broken", "#anything", "#source=old", "#view=" + btoa('{"v":2}'), "#view=" + btoa('{"v":1,"views":[{}]}')]) {
    assert.throws(() => decodeWorkspaceLocation("home", new URL("http://localhost/" + hash)));
  }
  assert.throws(() => encodeWorkspaceLocation("home", { object: { source: "a", report: "b" } }));
  assert.throws(() => decodeWorkspaceLocation("home", new URL("http://localhost/?source=a&source=b")));
  assert.throws(() => encodeWorkspaceLocation("home", { state: { query: { search: "a".repeat(MAX_LOCATION_BYTES) } } }));
});

test("shared snapshots enforce the View count limit without truncation", () => {
  const views = Array.from({ length: 100 }, (_, index) => ({ name: `view ${index}`, filters: { search: `condition ${index}` } }));
  const href = encodeWorkspaceLocation("home", { state: { views } });
  assert.equal(decodeWorkspaceLocation("home", new URL(href, "http://localhost")).state.views.length, 100);
  assert.throws(() => encodeWorkspaceLocation("home", { state: { views: [...views, views[0]] } }));
  const payload = btoa(JSON.stringify({ v: 1, views: [...views, views[0]] })).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
  assert.throws(() => decodeWorkspaceLocation("home", new URL("http://localhost/#view=" + payload)));
});

test("the complete URL byte boundary is enforced, including origin and object identity", () => {
  const origin = "http://localhost:8765";
  const value = length => ({ object: { source: "a".repeat(length) } });
  const prefix = encodeWorkspaceLocation("home", value(1), origin).length - 1;
  const boundary = encodeWorkspaceLocation("home", value(MAX_LOCATION_BYTES - prefix), origin);
  assert.equal(new TextEncoder().encode(boundary).length, MAX_LOCATION_BYTES);
  assert.equal(decodeWorkspaceLocation("home", new URL(boundary)).object.source.length, MAX_LOCATION_BYTES - prefix);
  assert.throws(() => encodeWorkspaceLocation("home", value(MAX_LOCATION_BYTES - prefix + 1), origin), /64 KiB/);
  assert.throws(() => decodeWorkspaceLocation("home", new URL(boundary + "a")));
});

test("default arrays are isolated and duplicate view conditions preserve their actual predicates", () => {
  const first = decodeWorkspaceLocation("home", new URL("http://localhost/"));
  first.state.query.models.push("local mutation");
  assert.deepEqual(decodeWorkspaceLocation("home", new URL("http://localhost/")).state.query.models, []);
  const views = [{ name: "中文", filters: { models: ["b", "a", "a"] } }, { name: "中文", filters: { results: ["failed"] } }];
  const encode = values => encodeWorkspaceLocation("home", { state: { views: values } });
  assert.equal(encode(views), encode([...views].reverse()));
  assert.equal(decodeWorkspaceLocation("home", new URL(encode(views), "http://localhost")).state.views.length, 2);
  assert.throws(() => encodeWorkspaceLocation("home", { state: { query: { page_size: 101 } } }));
  const many = Array.from({ length: 1001 }, (_, index) => `model${index}`);
  assert.equal(decodeWorkspaceLocation("home", new URL(encodeWorkspaceLocation("home", { state: { query: { models: many } } }), "http://localhost")).state.query.models.length, many.length);
});
