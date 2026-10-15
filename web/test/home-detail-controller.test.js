import assert from "node:assert/strict";
import test from "node:test";
import { createHomeDetailController } from "../../src/psycheval/assets/web/app/home-detail-controller.js";

test("detail transitions exclude the other reader and publish once with the complete position", () => {
  let location = {};
  const commits = [], cancelled = [];
  const details = createHomeDetailController({ read: () => location, write: value => { location = value; }, notify: kind => commits.push({ kind, location: { ...location } }) });
  for (const kind of ["source", "report"]) details.register(kind, { cancel: () => cancelled.push(kind), close: () => details.clear(kind, "replace") });
  details.activate({ source: "source", trajectory: "child", step: "2", tab: "trajectory" });
  assert.deepEqual(commits, [{ kind: "object", location }]);
  assert.deepEqual(cancelled, ["report"]);
  details.transaction(() => {
    details.position({ step: "3" });
    details.position({ tab: "verification" });
  });
  assert.equal(commits.length, 2);
  assert.deepEqual(commits[1], { kind: "replace", location: { source: "source", trajectory: "child", step: "3", tab: "verification" } });
  details.activate({ report: "package:report" });
  assert.deepEqual(commits.at(-1), { kind: "object", location: { report: "package:report" } });
  details.clear("report");
  assert.deepEqual(commits.at(-1), { kind: "object", location: {} });
});

test("unchanged positions do not encode again; removing a step retains its trajectory", () => {
  let location = { source: "s", trajectory: "child", step: "2", tab: "trajectory" }, commits = 0;
  const details = createHomeDetailController({ read: () => location, write: value => { location = value; }, notify: () => commits++ });
  details.position({ step: "2" }); assert.equal(commits, 0);
  details.position({ step: null });
  assert.deepEqual(location, { source: "s", trajectory: "child", tab: "trajectory" });
  assert.equal(commits, 1);
});

test("invalid detail identities fail before changing readers or history", () => {
  let location = { source: "source,中文", step: "2" };
  const initial = location;
  const effects = [];
  const details = createHomeDetailController({ read: () => location, write: value => { effects.push("write"); location = value; }, notify: () => effects.push("history") });
  details.register("source", { cancel: () => effects.push("cancel"), close: () => effects.push("close") });
  for (const invalid of [{ source: "s", report: "r" }, { step: "3" }, { source: { nested: "s" } }, { report: "r", tab: "task" }]) {
    assert.throws(() => details.activate(invalid), /Invalid or unsupported workspace link/);
    assert.equal(location, initial);
    assert.deepEqual(effects, []);
  }
  details.activate({ step: "2", source: "source,中文" });
  assert.deepEqual(effects, ["write"]);
});

test("late Trial position callbacks cannot alter a report location", () => {
  let location = { report: "package:report" };
  const commits = [];
  const details = createHomeDetailController({ read: () => location, write: value => { location = value; }, notify: kind => commits.push(kind) });
  details.position({ trajectory: "child", step: "3", tab: "trajectory" });
  assert.deepEqual(location, { report: "package:report" });
  assert.deepEqual(commits, []);
});
