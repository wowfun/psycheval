import assert from "node:assert/strict";
import test from "node:test";
import childProcess from "node:child_process";
import { EventEmitter } from "node:events";
import { syncBuiltinESMExports } from "node:module";
import { stopFixture } from "../e2e/fixture-process.mjs";

test("Windows fixture termination tolerates an exit notification after taskkill fails", { skip: process.platform !== "win32" }, async () => {
  const fixture = Object.assign(new EventEmitter(), { pid: 42, exitCode: null, signalCode: null });
  const original = childProcess.execFile;
  childProcess.execFile = (_file, _args, _options, callback) => {
    callback(new Error("taskkill raced an exiting child"));
    setTimeout(() => { fixture.exitCode = 0; fixture.emit("exit", 0); }, 10);
  };
  syncBuiltinESMExports();
  try {
    await stopFixture(fixture);
    assert.equal(fixture.exitCode, 0);
    assert.equal(fixture.listenerCount("exit"), 0);
  } finally { childProcess.execFile = original; syncBuiltinESMExports(); }
});

test("Windows fixture termination still fails when exit never arrives", { skip: process.platform !== "win32" }, async t => {
  const fixture = Object.assign(new EventEmitter(), { pid: 42, exitCode: null, signalCode: null });
  const failure = new Error("termination denied");
  const original = childProcess.execFile;
  childProcess.execFile = (_file, _args, _options, callback) => callback(failure);
  syncBuiltinESMExports();
  t.mock.timers.enable({ apis: ["setTimeout"] });
  try {
    const stopping = stopFixture(fixture);
    await Promise.resolve(); await Promise.resolve();
    t.mock.timers.tick(3000);
    await assert.rejects(stopping, error => error === failure);
    assert.equal(fixture.listenerCount("exit"), 0);
  } finally {
    childProcess.execFile = original; syncBuiltinESMExports(); t.mock.timers.reset();
  }
});
