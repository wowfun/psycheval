import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.beforeAll(async () => {
  fixture = await startFixture({ PEVAL_E2E_TIMELINE: "1", PEVAL_E2E_OBSERVED_TIMING: "1", PEVAL_E2E_NATIVE_TIMING: "1", PYTHONPATH: process.cwd() });
});
test.afterAll(async () => { await stopFixture(fixture); });

test("native model and tool timings reach metrics, source hints, colored nodes and step navigation", async ({ page }, testInfo) => {
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
  const row = catalog.items.find(item => item.trial_key === "e2e-trial");
  expect(row.model_duration_ms).toBe(1100);
  await page.goto(fixture.origin);
  const nodes = page.locator(`.trajectory-row[data-source-key="${row.source_key}"]`);
  await expect(nodes.locator('[data-step-id="3"]')).toHaveAttribute("title", /Model call.*response-body end/);
  expect(await nodes.locator('[data-step-id="3"]').evaluate(node => getComputedStyle(node).backgroundColor)).not.toEqual(await nodes.locator('[data-step-id="4"]').evaluate(node => getComputedStyle(node).backgroundColor));
  await nodes.locator('[data-step-id="4"]').click();
  await expect(page.locator('#detail-sidebar details[data-step="4"]')).toHaveAttribute("open", "");
  await page.locator('#detail-sidebar [data-sidebar-close]').click();
  const timeline = page.locator(".timeline-diagnostics");
  await expect(timeline).toContainText("Tool call: read_file");
  await expect(timeline).toContainText("0.000s");
  await expect(timeline).not.toContainText("≈");
  await expect(timeline).toContainText("Partial coverage");
  await expect(timeline.locator('span[title*="response-body end"]').first()).toBeVisible();
  await expect(timeline.locator('span[title*="tool-called to terminal"]').first()).toBeVisible();
  await timeline.screenshot({ path: testInfo.outputPath("native-timing-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(timeline.locator("[data-timeline-chart] canvas")).toBeVisible();
  await timeline.screenshot({ path: testInfo.outputPath("native-timing-mobile.png") });
  expect(errors).toEqual([]);
});
