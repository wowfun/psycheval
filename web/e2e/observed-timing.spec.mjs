import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.beforeAll(async () => { fixture = await startFixture({ PEVAL_E2E_TIMELINE: "1", PEVAL_E2E_OBSERVED_TIMING: "1", PYTHONPATH: process.cwd() }); });
test.afterAll(async () => { await stopFixture(fixture); });

test("observed durations shade nodes, show provenance and preserve step navigation", async ({ page }, testInfo) => {
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
  const row = catalog.items.find(item => item.trial_key === "e2e-trial");
  expect(row.model_duration_ms).toBeNull();
  await page.goto(fixture.origin);
  const nodes = page.locator(`.trajectory-row[data-source-key="${row.source_key}"]`);
  await expect(nodes.locator('[data-step-id="3"]')).toHaveClass(/duration-heat-1\b/);
  await expect(nodes.locator('[data-step-id="4"]')).toHaveClass(/duration-heat-10\b/);
  expect(await nodes.locator('[data-step-id="3"]').evaluate(node => getComputedStyle(node).backgroundColor)).not.toEqual(await nodes.locator('[data-step-id="4"]').evaluate(node => getComputedStyle(node).backgroundColor));
  await expect(nodes.locator('[data-step-id="5"]')).not.toHaveClass(/duration-heat-/);
  await expect(nodes.locator('[data-step-id="4"]')).toHaveAttribute("title", /Observed output/);
  await nodes.locator('[data-step-id="4"]').click();
  await expect(page.locator('#detail-sidebar details[data-step="4"]')).toHaveAttribute("open", "");
  await page.locator('#detail-sidebar [data-sidebar-close]').click();
  const timeline = page.locator(".timeline-diagnostics");
  const stageLabels = timeline.locator(".timeline-stage-label");
  await expect(stageLabels).toHaveCount(5);
  const labels = await stageLabels.allTextContents();
  expect([...labels].sort()).toEqual(["Model", "Model", "Model", "Tool call: cached_read", "Tool call: read_file"]);
  await expect(timeline).toContainText("Partial coverage");
  await expect(timeline).toContainText("≈0.000s");
  await expect(timeline.locator('span[title*="may include waiting"]')).toBeVisible();
  await expect(timeline.locator("[data-timeline-chart] canvas")).toBeVisible();
  const axisLabels = await page.evaluate(async () => {
    const { state } = await import("/assets/peval/modules/runtime.js");
    return state.timelineChart.getOption().yAxis[0].data;
  });
  expect(axisLabels.map(label => label.replace(/^#[\d.]+ /, ""))).toEqual(labels);
  await nodes.screenshot({ path: testInfo.outputPath("duration-nodes-desktop.png") });
  await timeline.screenshot({ path: testInfo.outputPath("observed-timing-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(timeline.locator("[data-timeline-chart] canvas")).toBeVisible();
  await nodes.screenshot({ path: testInfo.outputPath("duration-nodes-mobile.png") });
  await timeline.screenshot({ path: testInfo.outputPath("observed-timing-mobile.png") });
  expect(errors).toEqual([]);
});
