import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.beforeAll(async () => {
  fixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PEVAL_E2E_TABLES: "1", PYTHONPATH: process.cwd() });
});
test.afterAll(async () => { await stopFixture(fixture); });

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
  await page.route("**/api/operations/rescan-test", async route => {
    observed.release();
    await completion.pending;
    await route.fulfill({ json: {
      id: "rescan-test", kind: "source-discovery", state: failed ? "failed" : "completed",
      successes: [], failures: failed ? [{ error: "Scan reconciliation failed" }] : [],
    } });
  });
  await page.goto(fixture.origin);
  await expect(page.locator("[data-catalog-page-controls]")).toContainText("/ 2");
  // Use the real query loader to retain a non-default page, filter, and sort.
  await page.evaluate(async () => {
    const { loadCatalogPage } = await import("/assets/peval/modules/serve-catalog.js");
    await loadCatalogPage({ page: 2, page_size: 1, datasets: ["office"], sort: "dataset_id", direction: "asc" }, { force: true });
  });
  await expect(page.locator("[data-catalog-page-controls]")).toContainText("2-2 / 2");
  await expect(page.locator("[data-catalog-next]")).toBeDisabled();
  await page.locator('.workspace-nav-link[data-workspace-route="config"]').click();
  await page.locator("[data-source-config-rescan]").click();
  await observed.pending;
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
        await expect(page.locator("[data-source-config-rescan]")).toBeEnabled();
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
    await page.locator('.workspace-nav-link[data-workspace-route="config"]').click();
    await expect(page.locator('[aria-labelledby="trajectory-ingestion-title"] .action-feedback')).toContainText("Scan reconciliation failed");
  } finally { scan.finish(); }
});

for (const failed of [false, true]) test(`rescan refresh failures retry the read without submitting another scan (failed=${failed})`, async ({ page }) => {
  const scan = await rescanScenario(page, { failed });
  try {
    await page.locator('.workspace-nav-link[data-workspace-route="home"]').click();
    await expect.poll(() => scan.reads).toBeGreaterThan(2);
    scan.rejectRefresh(true);
    scan.finish();
    const notification = page.locator(".action-toast").filter({ hasText: "Workspace data is stale" });
    await expect(notification).toBeVisible();
    await notification.getByRole("button", { name: "View", exact: true }).click();
    const feedback = page.locator('[aria-labelledby="trajectory-ingestion-title"] .action-feedback');
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
    await expect(notification).toHaveCount(0);
  } finally { scan.finish(); }
});
