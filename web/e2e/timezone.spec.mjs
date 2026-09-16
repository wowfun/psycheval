import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.use({ timezoneId: "America/Los_Angeles" });
test.beforeAll(async () => {
  fixture = await startFixture({ TZ: "Asia/Shanghai", PEVAL_E2E_VERIFICATION: "1", PEVAL_E2E_TABLES: "1", PYTHONPATH: process.cwd() });
});
test.afterAll(async () => { await stopFixture(fixture); });

async function chooseTimezone(page, timezone) {
  await page.locator("[data-timezone-mode]").selectOption(timezone ? "specific" : "local");
  if (timezone) await page.locator("[data-timezone-name]").fill(timezone);
  await page.locator("[data-timezone-save]").click();
  await expect(page.locator("[data-timezone-status]")).toContainText("Display timezone saved");
}

test("server timezone updates loaded time surfaces without reloading data or drafts and persists", async ({ page }) => {
  await page.goto(fixture.origin);
  expect(await page.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone)).toBe("America/Los_Angeles");
  const config = await (await page.request.get(`${fixture.origin}/api/config`)).json();
  expect(config).toMatchObject({ timezone: null, effective_timezone: "Asia/Shanghai" });
  await expect(page.locator("#leaderboard time").first()).toContainText("+08:00");
  await page.locator('#leaderboard tbody tr').filter({ hasText: 'office-one' }).click();
  await expect(page.locator("#detail-sidebar")).toBeVisible();
  await page.locator('#detail-sidebar [data-sidebar-close]').click();
  // Keep production-rendered timeline tooltip mounted to exercise immediate hint updates.
  const before = await page.evaluate(async () => {
    const { state } = await import("/assets/peval/modules/runtime.js");
    const { loadCatalogPage } = await import("/assets/peval/modules/serve-catalog.js");
    await loadCatalogPage({ page: 2, page_size: 1, search: "e2e", sort: "finished_at_ms", direction: "asc" }, { force: true });
    const { timelineTooltipHtml } = await import("/assets/peval/modules/timeline-chart.js");
    const { timelineDetailColumns } = await import("/assets/peval/modules/timeline-table.js");
    const { xlsxTableRows } = await import("/assets/peval/modules/export.js");
    const tooltip = document.createElement("div");
    tooltip.id = "timezone-tooltip";
    tooltip.innerHTML = timelineTooltipHtml({ wall_start_ms: 1000, wall_end_ms: 1200, duration_ms: 200 });
    document.body.append(tooltip);
    const columns = timelineDetailColumns({ active_total_ms: 200 });
    return { query: JSON.stringify(state.catalogQuery), exported: xlsxTableRows([{ wall_start_ms: 1000, wall_end_ms: 1200 }], columns) };
  });
  await page.locator('.workspace-nav-link[data-workspace-route="config"]').click();
  await page.route("**/api/session-inspections", route => route.fulfill({ json: {
    adapter: "psychevo", db: "fixture.db", sessions: [{ session_id: "timezone-session", name: "Timezone session", updated_at_ms: 1000 }],
  } }));
  const source = page.locator('[data-source-add-form][data-source-kind="db"]');
  await source.locator('[name="db"]').fill("fixture.db");
  await source.locator("[data-session-inspect]").click();
  await expect(source.locator("time")).toContainText("+08:00");
  const prompt = page.locator("[data-prompt-content]");
  await expect(prompt).toBeEnabled();
  await prompt.fill("unsaved timezone regression draft");
  const times = await page.locator("time[data-display-time]").count();
  expect(times).toBeGreaterThan(4);
  const otherDocument = await page.context().newPage();
  await otherDocument.goto(fixture.origin);
  await expect(otherDocument.locator("#leaderboard time").first()).toContainText("+08:00");
  let catalogReads = 0;
  page.on("request", request => { if (/\/api\/(catalog|details)/.test(request.url())) catalogReads++; });
  await chooseTimezone(page, "asia/kolkata");
  await expect(page.locator("[data-timezone-name]")).toHaveValue("Asia/Kolkata");
  await expect(prompt).toHaveValue("unsaved timezone regression draft");
  await expect(page.locator("[data-timezone-effective]")).toContainText("Asia/Kolkata");
  const after = await page.evaluate(async () => {
    const { state } = await import("/assets/peval/modules/runtime.js");
    const { timelineDetailColumns } = await import("/assets/peval/modules/timeline-table.js");
    const { xlsxTableRows } = await import("/assets/peval/modules/export.js");
    return {
      query: JSON.stringify(state.catalogQuery),
      exported: xlsxTableRows([{ wall_start_ms: 1000, wall_end_ms: 1200 }], timelineDetailColumns({ active_total_ms: 200 })),
      times: [...document.querySelectorAll("time[data-display-time]")].map(node => [node.textContent, node.title]),
    };
  });
  expect(after.query).toBe(before.query);
  expect(after.exported).toEqual(before.exported);
  expect(after.times).toHaveLength(times);
  for (const [text, title] of after.times) {
    expect(text).toContain("+05:30");
    expect(title).toContain("+05:30");
  }
  expect(catalogReads).toBe(0);
  await expect(otherDocument.locator("#leaderboard time").first()).toContainText("+08:00");
  await otherDocument.reload();
  await expect(otherDocument.locator("#leaderboard time").first()).toContainText("+05:30");
  await otherDocument.close();
  await expect(source.locator("time")).toContainText("+05:30");
  await page.screenshot({ path: ".local/timezone-settings.png" });
  await page.reload();
  await expect(page.locator("[data-timezone-name]")).toHaveValue("Asia/Kolkata");
  await chooseTimezone(page, "utc");
  await expect(page.locator("[data-timezone-name]")).toHaveValue("UTC");
  await chooseTimezone(page, null);
  await expect(page.locator("[data-timezone-effective]")).toContainText("Asia/Shanghai");
  await page.reload();
  await expect(page.locator("[data-timezone-mode]")).toHaveValue("local");
});

test("conflicting timezone save retains draft and error until explicit retry", async ({ page }) => {
  await page.goto(`${fixture.origin}/config`);
  await expect(page.locator("[data-timezone-mode]")).toBeEnabled();
  const config = await page.request.get(`${fixture.origin}/api/config`);
  const update = await page.request.patch(`${fixture.origin}/api/config`, {
    headers: { "If-Match": config.headers().etag, Origin: fixture.origin }, data: { timezone: "UTC" },
  });
  expect(update.ok()).toBeTruthy();
  await page.locator("[data-timezone-mode]").selectOption("specific");
  await page.locator("[data-timezone-name]").fill("America/New_York");
  await page.locator("[data-timezone-save]").click();
  await expect(page.locator("[data-timezone-status]")).toContainText(/changed|conflict/i);
  await expect(page.locator("[data-timezone-name]")).toHaveValue("America/New_York");
  await expect(page.locator("[data-timezone-status]")).not.toContainText("Display timezone saved");
  await page.locator("[data-timezone-save]").click();
  await expect(page.locator("[data-timezone-status]")).toContainText("Display timezone saved");
  await chooseTimezone(page, null);
});
