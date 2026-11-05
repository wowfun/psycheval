import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.beforeAll(async () => {
  fixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PEVAL_E2E_TABLES: "1", PYTHONPATH: process.cwd() });
});
test.afterAll(async () => { await stopFixture(fixture); });

test("cached rows stay available while counted progress uses only status reads", async ({ page }) => {
  await page.clock.install();
  const original = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
  let phase = "discovering", checking = true, statusReads = 0, catalogReads = 0;
  await page.route("**/api/catalog-status", route => {
    statusReads++;
    return route.fulfill({ json: {
      generation: original.generation, checking, phase,
      completed: phase === "discovering" ? 17 : 317,
      total: phase === "discovering" ? null : 1000,
    } });
  });
  await page.route("**/api/catalog?*", async route => {
    catalogReads++;
    const response = await route.fetch();
    return route.fulfill({ json: { ...await response.json(), checking } });
  });
  await page.goto(fixture.origin);
  const progress = page.locator("[data-catalog-progress]");
  await expect(progress).toContainText("17 found");
  await expect(page.locator("#leaderboard tbody tr").first()).toBeVisible();
  await expect(page.locator("[data-catalog-refresh]")).toBeDisabled();
  const initialCatalogReads = catalogReads;
  phase = "checking";
  await expect(progress).toContainText("317/1000");
  await page.locator("#leaderboard tbody tr").first().click();
  await expect(progress).toContainText("317/1000");
  expect(catalogReads).toBe(initialCatalogReads);
  await page.screenshot({ path: ".local/catalog-progress.png" });
  await page.locator('.workspace-nav-link[data-workspace-route="config"]').click();
  await expect(page.locator("[data-config-page]")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator("[data-source-config-rescan],[data-harbor-config-reload]")).toHaveCount(0);
  const pausedReads = statusReads;
  await page.clock.fastForward(750);
  expect(statusReads).toBe(pausedReads);
  phase = "committing";
  await page.locator('.workspace-nav-link[data-workspace-route="home"]').click();
  await expect(progress).toContainText("Publishing index");
  checking = false;
  await expect(progress).toBeHidden();
  await expect(page.locator("[data-catalog-refresh]")).toBeEnabled();
});

function gate() {
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  return { pending, release };
}

async function rescanScenario(page, { failed = false } = {}) {
  const original = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
  const row = original.items.find(item => item.dataset_id === "office");
  expect(row).toBeTruthy();
  const completion = gate(), observed = gate();
  let completed = false, writes = 0, catalogReads = 0, rejectRefresh = false;
  await page.route("**/api/catalog-status", route => route.fulfill({ json: {
    generation: original.generation + Number(completed), checking: writes > 0 && !completed,
    phase: "checking", completed: 1, total: 2, operation_id: "rescan-test",
  } }));
  let heldRead = null;
  const queries = [];
  await page.route("**/api/catalog?*", async route => {
    const query = new URL(route.request().url()).searchParams;
    if (query.get("state") === "all") {
      const response = await route.fetch();
      const payload = await response.json();
      payload.facets.categories = [{ value: completed ? "Rescanned category" : "Original category", count: 1 }];
      return route.fulfill({ json: payload });
    }
    queries.push(Object.fromEntries(query));
    catalogReads++;
    // Capture the old generation before holding a read so it can arrive after scan completion.
    const payload = {
      ...original, generation: original.generation + Number(completed), checking: false,
      effective_sort: query.get("sort") || "last_turn_end",
      total: completed ? 3 : 2, page: Number(query.get("page")), page_size: Number(query.get("page_size")),
      items: [{ ...row, task_name: completed ? "rescanned-office" : row.task_name }],
    };
    const held = heldRead;
    heldRead = null;
    if (held) { held.started.release(); await held.finish.pending; }
    if (completed && rejectRefresh) {
      return route.fulfill({ status: 503, json: { detail: "Catalog refresh unavailable" } });
    }
    await route.fulfill({ json: payload });
  });
  await page.route("**/api/catalog-summaries", async route => {
    const response = await route.fetch();
    const payload = await response.json();
    payload.generation = original.generation + Number(completed);
    payload.summary.matched_count = completed ? 3 : 2;
    await route.fulfill({ json: payload });
  });
  await page.route("**/api/source-discovery-operations", async route => {
    writes++;
    await route.fulfill({ status: 202, json: { id: "rescan-test", state: "running" } });
  });
  let firstOperationRead = true;
  await page.route("**/api/operations/rescan-test", async route => {
    observed.release();
    if (firstOperationRead) {
      firstOperationRead = false;
      return route.fulfill({ json: {
        id: "rescan-test", kind: "source-discovery", state: "running", completed: 0, total: 1,
        catalog_status: { generation: original.generation, checking: true, phase: "checking", completed: 1, total: 2, operation_id: "rescan-test" },
      } });
    }
    await completion.pending;
    await route.fulfill({ json: {
      id: "rescan-test", kind: "source-discovery", state: failed ? "failed" : "completed",
      catalog_status: { generation: original.generation + 1, checking: false, phase: "idle", completed: 2, total: 2, operation_id: "rescan-test" },
      successes: [], failures: failed ? [{ error: "Scan reconciliation failed" }] : [],
    } });
  });
  await page.goto(fixture.origin);
  await expect(page.locator("[data-catalog-page-controls]")).toContainText("/ 2");
  await expect(page.locator("[data-notes-edit]")).toBeVisible();
  // Use the real query loader to retain a non-default page, filter, and sort.
  await page.evaluate(async () => {
    const { loadCatalogPage } = await import("/assets/peval/modules/serve-catalog.js");
    await loadCatalogPage({ page: 2, page_size: 1, datasets: ["office"], sort: "dataset_id", direction: "asc" }, { force: true });
  });
  await expect(page.locator("[data-catalog-page-controls]")).toContainText("2-2 / 2");
  await expect(page.locator("[data-catalog-next]")).toBeDisabled();
  await page.locator("[data-catalog-refresh]").click();
  await observed.pending;
  await expect(page.locator("[data-catalog-progress]")).toContainText("1/2");
  await page.locator('.workspace-nav-link[data-workspace-route="config"]').click();
  await expect(page.locator("[data-config-page]")).toHaveAttribute("aria-busy", "false");
  return {
    finish() { completed = true; completion.release(); },
    rejectRefresh(value) { rejectRefresh = value; },
    holdNextRead() {
      heldRead = { started: gate(), finish: gate() };
      return heldRead;
    },
    get reads() { return catalogReads; },
    async expectUpdated() {
      await expect(page.locator("[data-catalog-page-controls]")).toContainText("2-2 / 3");
      await expect(page.locator("[data-catalog-next]")).toBeEnabled();
      await expect(page.locator("#leaderboard tbody")).toContainText("rescanned-office");
      await expect.poll(() => page.evaluate(async () => {
        const { state } = await import("/assets/peval/modules/runtime.js");
        return state.leaderboardSummary?.summary?.matched_count;
      })).toBe(3);
      await expect.poll(() => page.evaluate(async () => {
        const { state } = await import("/assets/peval/modules/runtime.js");
        return state.sourceCategoryOptions;
      })).toEqual(["Rescanned category"]);
      expect(queries.at(-1)).toMatchObject({ page: "2", page_size: "1", dataset: "office", sort: "dataset", direction: "asc" });
      expect(writes).toBe(1);
    },
  };
}

for (const timing of ["before returning", "after returning", "with a catalog request in flight"]) {
  test(`rescan updates the retained Leaderboard when it completes ${timing}`, async ({ page }) => {
    const scan = await rescanScenario(page);
    let held;
    try {
      if (timing === "before returning") {
        scan.finish();
        await expect(page.locator("[data-catalog-refresh]")).toBeEnabled();
        await page.locator('.workspace-nav-link[data-workspace-route="home"]').click();
      } else {
        if (timing.includes("in flight")) held = scan.holdNextRead();
        await page.locator('.workspace-nav-link[data-workspace-route="home"]').click();
        if (held) await held.started.pending;
        else await expect.poll(() => scan.reads).toBeGreaterThan(2);
        if (held) {
          await page.evaluate(async () => {
            const { subscribeWorkspaceInvalidation } = await import("/assets/peval/app/workspace-runtime.js");
            const unsubscribe = subscribeWorkspaceInvalidation(changes => {
              if (!changes.has("catalog")) return;
              document.body.dataset.rescanInvalidated = "true";
              unsubscribe();
            });
          });
        }
        scan.finish();
        if (held) {
          // Wait until the terminal response is consumed while the old read is still pending.
          await expect(page.locator("body")).toHaveAttribute("data-rescan-invalidated", "true");
          held.finish.release();
        }
      }
      await scan.expectUpdated();
      await page.locator('.workspace-nav-link[data-workspace-route="config"]').click();
      await page.locator('.workspace-nav-link[data-workspace-route="home"]').click();
      await scan.expectUpdated();
    } finally { scan.finish(); held?.finish.release(); }
  });
}

test("a failed scan retains its failure after the catalog refresh", async ({ page }) => {
  const scan = await rescanScenario(page, { failed: true });
  try {
    await page.locator('.workspace-nav-link[data-workspace-route="home"]').click();
    await expect.poll(() => scan.reads).toBeGreaterThan(2);
    scan.finish();
    await scan.expectUpdated();
    await expect(page.locator('#leaderboard .action-feedback')).toContainText("Scan reconciliation failed");
  } finally { scan.finish(); }
});

for (const failed of [false, true]) test(`rescan refresh failures retry the read without submitting another scan (failed=${failed})`, async ({ page }) => {
  const scan = await rescanScenario(page, { failed });
  try {
    await page.locator('.workspace-nav-link[data-workspace-route="home"]').click();
    await expect.poll(() => scan.reads).toBeGreaterThan(2);
    scan.rejectRefresh(true);
    scan.finish();
    const feedback = page.locator('#leaderboard [data-action-feedback="home:rescan"]');
    await expect(feedback).toContainText("Workspace data is stale");
    if (failed) await expect(feedback).toContainText("Scan reconciliation failed");
    scan.rejectRefresh(false);
    await feedback.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(feedback).not.toContainText("Workspace data is stale");
    if (failed) {
      await expect(feedback).toHaveClass(/danger/);
      await expect(feedback).toContainText("Scan reconciliation failed");
    }
    await page.locator('.workspace-nav-link[data-workspace-route="home"]').click();
    await scan.expectUpdated();
    await expect(page.locator(".action-toast").filter({ hasText: "Workspace data is stale" })).toHaveCount(0);
  } finally { scan.finish(); }
});
