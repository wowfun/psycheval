import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.beforeAll(async () => {
  fixture = await startFixture({ PEVAL_E2E_TIMELINE: "1", PYTHONPATH: process.cwd() });
});
test.afterAll(async () => { await stopFixture(fixture); });

test("canonical tool timing reaches the catalog, waterfall and detail table", async ({ page }, testInfo) => {
  const externalRequests = [];
  await page.route("**/*", route => {
    const url = route.request().url();
    if (new URL(url).origin === fixture.origin) return route.continue();
    externalRequests.push(url);
    return route.abort();
  });
  const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
  const row = catalog.items.find(item => item.trial_key === "e2e-trial");
  expect(row.duration_ms).toBe(1420);
  expect(row.model_duration_ms).toBe(1000);
  await page.goto(fixture.origin);
  await page.locator(`#leaderboard tr[data-source-key="${row.source_key}"]`).click();
  await expect(page.locator("#detail-sidebar")).toBeVisible();
  await page.locator('#detail-sidebar [data-sidebar-close]').click();
  const timeline = page.locator(".timeline-diagnostics");
  await expect(timeline).toBeVisible();
  await expect(timeline.locator("tbody tr")).toHaveCount(3);
  await expect(timeline).toContainText("Tool call: read_file");
  await expect(timeline).toContainText("Tool call: cached_read");
  await expect(timeline).not.toContainText("Tool call: unknown_read");
  await expect(timeline.locator("[data-timeline-chart] canvas")).toBeVisible();
  const trace = await page.evaluate(async () => {
    const { selectedKey } = await import("/assets/peval/modules/runtime.js");
    const { metaFor, trajectoryFor } = await import("/assets/peval/modules/serve-catalog.js");
    const { timelineTrace } = await import("/assets/peval/modules/timeline-model.js");
    const key = selectedKey();
    return timelineTrace(trajectoryFor(key), metaFor(key));
  });
  expect(trace.model.active_total_ms).toBe(1420);
  expect(trace.stages.filter(stage => stage.kind === "tool").map(stage => stage.duration_ms).sort((a, b) => a - b)).toEqual([0, 420]);
  await timeline.scrollIntoViewIfNeeded();
  await timeline.screenshot({ path: testInfo.outputPath("timeline-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(timeline.locator("[data-timeline-chart] canvas")).toBeVisible();
  await expect.poll(() => timeline.locator("[data-timeline-chart]").evaluate(node => {
    const canvas = node.querySelector("canvas");
    return canvas?.clientWidth === node.clientWidth;
  })).toBe(true);
  await timeline.screenshot({ path: testInfo.outputPath("timeline-mobile.png") });
  for (const selector of [".timeline-waterfall-shell", ".timeline-table-shell .table-wrap"]) {
    const scrolled = await timeline.locator(selector).evaluate(node => {
      node.scrollLeft = node.scrollWidth - node.clientWidth;
      return node.scrollLeft > 0;
    });
    expect(scrolled).toBe(true);
  }
  await timeline.screenshot({ path: testInfo.outputPath("timeline-mobile-timing.png") });
  expect(externalRequests).toEqual([]);
});
