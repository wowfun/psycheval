// @ts-check
import { normalizeLocationObject } from "./workspace-location.js";

/** Own Home's detail identity and exclusion without depending on either reader. */
function createHomeDetailController({ read, write, notify }) {
  const readers = new Map();
  let depth = 0;
  let pending = null;
  const kindOf = target => target.source ? "source" : target.report ? "report" : null;
  const equal = (a, b) => Object.keys(a).length === Object.keys(b).length && Object.keys(a).every(key => a[key] === b[key]);
  function publish(kind) {
    if (depth) { if (pending !== "object") pending = kind; }
    else notify(kind);
  }
  function transaction(action) {
    depth++;
    try { return action(); }
    finally {
      if (--depth === 0 && pending) {
        const kind = pending; pending = null; notify(kind);
      }
    }
  }
  function activate(value, historyKind = "object") {
    const target = normalizeLocationObject("home", Object.fromEntries(Object.entries(value).filter(([, value]) => value != null)));
    return transaction(() => {
      const previous = read();
      const kind = kindOf(target);
      write(target);
      for (const [other, reader] of readers) if (other !== kind) {
        reader.cancel();
        reader.close({ restoreFocus: false, render: false, locationKind: "replace" });
      }
      if (!equal(previous, target)) publish(kindOf(previous) === kind && previous[kind] === target[kind] ? "replace" : historyKind);
    });
  }
  return {
    register(kind, reader) { readers.set(kind, reader); },
    activate,
    transaction,
    position(changes) {
      const current = read();
      if (kindOf(current) === "source") activate({ ...current, ...changes }, "replace");
    },
    clear(kind, historyKind = "object") {
      if (kindOf(read()) !== kind) return;
      write({}); publish(historyKind);
    },
  };
}

export { createHomeDetailController };
