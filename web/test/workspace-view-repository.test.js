import assert from "node:assert/strict";
import test from "node:test";

import {
  BROWSER_VIEW_LIMIT,
  browserViewStorageKey,
  createWorkspaceViewRepository,
} from "../src/modules/workspace-view-repository.js";

function memoryStorage(initial = {}) {
  const entries = new Map(Object.entries(initial));
  return {
    entries,
    getItem: key => entries.get(key) ?? null,
    setItem: (key, value) => entries.set(key, value),
  };
}

function view(name, overrides = {}) {
  return {
    name,
    filters: { state: "active", tags: ["keep"], ...overrides.filters },
    group_by: overrides.group_by || "agent",
    notes: overrides.notes || "",
  };
}

test("browser views are versioned, workspace-scoped, and survive repository recreation", async () => {
  const storage = memoryStorage();
  const request = async () => ({ views: [] });
  const first = createWorkspaceViewRepository({ workspaceId: "workspace-a", storage, request });
  await first.refresh();
  await first.save(view("Local"), { location: "browser" });

  assert.deepEqual(JSON.parse(storage.entries.get(browserViewStorageKey("workspace-a"))), {
    version: 1,
    views: [{ name: "Local", filters: { tags: ["keep"] }, group_by: "agent", notes: "" }],
  });
  const reopened = createWorkspaceViewRepository({ workspaceId: "workspace-a", storage, request });
  assert.deepEqual((await reopened.refresh()).map(item => item.id), ["browser:Local"]);
  const isolated = createWorkspaceViewRepository({ workspaceId: "workspace-b", storage, request });
  assert.deepEqual(await isolated.refresh(), []);
});

test("server views hide exact-name browser views without deleting them", async () => {
  const key = browserViewStorageKey("workspace-a");
  const storage = memoryStorage({
    [key]: JSON.stringify({ version: 1, views: [view("Shared"), view("Visible")] }),
  });
  let serverViews = [view("Shared", { notes: "server" })];
  const repository = createWorkspaceViewRepository({
    workspaceId: "workspace-a",
    storage,
    request: async () => ({ views: serverViews }),
  });

  assert.deepEqual((await repository.refresh()).map(item => item.id), ["server:Shared", "browser:Visible"]);
  assert.throws(
    () => repository.queryPayload(["browser:Shared"]),
    /not available/,
  );
  serverViews = [];
  assert.deepEqual((await repository.refresh()).map(item => item.id), ["browser:Shared", "browser:Visible"]);
  assert.equal(JSON.parse(storage.entries.get(key)).views.length, 2);
});

test("query payload keeps server names separate from normalized browser definitions", async () => {
  const storage = memoryStorage();
  const repository = createWorkspaceViewRepository({
    workspaceId: "workspace-a",
    storage,
    request: async () => ({ views: [view("Server")] }),
  });
  await repository.refresh();
  await repository.save(view("Browser", { filters: { state: "all", tags: ["a", "a"] }, notes: "memo" }), { location: "browser" });

  assert.deepEqual(repository.queryPayload(["server:Server", "browser:Browser"]), {
    views: ["Server"],
    browser_views: [{
      name: "Browser",
      filters: { state: "all", tags: ["a"] },
      group_by: "agent",
      notes: "memo",
    }],
  });
});

test("storage failures never leave a successful in-memory mutation", async () => {
  const storage = memoryStorage();
  storage.setItem = () => { throw new Error("quota exceeded"); };
  const repository = createWorkspaceViewRepository({
    workspaceId: "workspace-a",
    storage,
    request: async () => ({ views: [] }),
  });
  await repository.refresh();

  await assert.rejects(
    repository.save(view("Unsaved"), { location: "browser" }),
    /quota exceeded/,
  );
  assert.deepEqual(repository.list(), []);
});

test("browser limits and corrupt storage fail explicitly", async () => {
  const tooMany = Array.from({ length: BROWSER_VIEW_LIMIT + 1 }, (_, index) => view(`View ${index}`));
  const invalid = createWorkspaceViewRepository({
    workspaceId: "workspace-a",
    storage: memoryStorage({
      [browserViewStorageKey("workspace-a")]: JSON.stringify({ version: 1, views: tooMany }),
    }),
    request: async () => ({ views: [] }),
  });
  await assert.rejects(invalid.refresh(), /at most 100/);

  const corrupt = createWorkspaceViewRepository({
    workspaceId: "workspace-b",
    storage: memoryStorage({ [browserViewStorageKey("workspace-b")]: "not-json" }),
    request: async () => ({ views: [] }),
  });
  await assert.rejects(corrupt.refresh(), /could not be read/);
  await assert.rejects(
    corrupt.save(view("Must not overwrite"), { location: "browser" }),
    /must be read successfully/,
  );
});

test("delete commits server changes before browser changes", async () => {
  const calls = [];
  const storage = memoryStorage();
  const repository = createWorkspaceViewRepository({
    workspaceId: "workspace-a",
    storage,
    request: async (path, options = {}) => {
      calls.push([path, options.body]);
      if (path === "/api/views") return { views: [view("Server")] };
      if (path === "/api/views/delete") throw new Error("server failed");
      return {};
    },
  });
  await repository.refresh();
  await repository.save(view("Browser"), { location: "browser" });

  await assert.rejects(repository.delete(["server:Server", "browser:Browser"]), /server failed/);
  assert.deepEqual(repository.list().map(item => item.id), ["browser:Browser", "server:Server"]);
  assert.deepEqual(calls.at(-1), ["/api/views/delete", { names: ["Server"] }]);
});
