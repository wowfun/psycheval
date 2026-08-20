import assert from "node:assert/strict";
import test from "node:test";

import {
  layoutStorageKey,
  loadColumnLayout,
  moveColumn,
  normalizeColumnLayout,
  presenceForColumns,
  resolveColumns,
  saveColumnLayout,
} from "../src/modules/leaderboard-columns.js";

const columns = [
  { key: "session", value: row => row.session },
  { key: "ttft", value: row => row.ttft },
  { key: "cache", value: row => row.cache },
];

test("normalizes stale layouts and inserts new columns canonically", () => {
  const layout = normalizeColumnLayout(
    columns.map(column => column.key),
    {
      order: ["cache", "unknown", "cache", "session"],
      visibility: { cache: "hide", ttft: "show", unknown: "show", session: "maybe" },
    },
  );

  assert.deepEqual(layout, {
    version: 1,
    order: ["ttft", "cache", "session"],
    visibility: { cache: "hide", ttft: "show" },
  });
});

test("keeps canonical order among multiple columns missing from a saved layout", () => {
  const layout = normalizeColumnLayout(["a", "b", "c", "d"], {
    order: ["d", "b"],
  });

  assert.deepEqual(layout.order, ["a", "c", "d", "b"]);
});

test("auto-hides query-empty columns but manual show and hide win", () => {
  const presence = presenceForColumns(columns, [{ session: "s-1", ttft: null, cache: null }]);
  const automatic = resolveColumns(columns, normalizeColumnLayout(["session", "ttft", "cache"], null), presence);
  assert.deepEqual(automatic.map(column => column.key), ["session"]);

  const overridden = resolveColumns(
    columns,
    normalizeColumnLayout(["session", "ttft", "cache"], {
      visibility: { session: "hide", ttft: "show" },
    }),
    presence,
  );
  assert.deepEqual(overridden.map(column => column.key), ["ttft"]);

  const allHidden = resolveColumns(
    columns,
    normalizeColumnLayout(["session", "ttft", "cache"], {
      visibility: { session: "hide", ttft: "hide", cache: "hide" },
    }),
    presence,
  );
  assert.deepEqual(allHidden, []);

  const queryWide = presenceForColumns(columns, [{ session: "page-row" }], { session: 1, ttft: 2, cache: 0 });
  assert.deepEqual(queryWide, { session: true, ttft: true, cache: false });
});

test("moves columns and persists a workspace-scoped versioned layout", () => {
  assert.deepEqual(moveColumn(["session", "ttft", "cache"], "cache", -1), ["session", "cache", "ttft"]);
  const entries = new Map();
  const storage = {
    getItem: key => entries.get(key) ?? null,
    setItem: (key, value) => entries.set(key, value),
  };
  const layout = normalizeColumnLayout(["session", "ttft", "cache"], {
    order: ["cache", "session", "ttft"],
    visibility: { cache: "show" },
  });

  saveColumnLayout(layout, { workspaceId: "workspace-a", storage });

  assert.equal(entries.has(layoutStorageKey("workspace-a")), true);
  assert.deepEqual(
    loadColumnLayout(["session", "ttft", "cache"], { workspaceId: "workspace-a", storage }),
    layout,
  );
  assert.deepEqual(
    loadColumnLayout(["session", "ttft", "cache"], { workspaceId: "workspace-b", storage }),
    normalizeColumnLayout(["session", "ttft", "cache"], null),
  );
});
