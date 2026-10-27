import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.beforeAll(async () => {
  fixture = await startFixture({ PEVAL_E2E_TIMELINE: "1", PEVAL_E2E_TIMELINE_PARALLEL: "1", PYTHONPATH: process.cwd() });
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
  expect(trace.model.display_total_ms).toBe(1000);
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

test("parallel calls retain inherited and explicit starts on the compressed chart", async ({ page }, testInfo) => {
  const errors = [];
  const externalRequests = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route("**/*", route => {
    if (new URL(route.request().url()).origin === fixture.origin) return route.continue();
    externalRequests.push(route.request().url());
    return route.abort();
  });
  const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
  const row = catalog.items.find(item => item.trial_key === "e2e-trial-2");
  expect(row.duration_ms).toBe(4417);
  await page.goto(fixture.origin);
  await page.locator(`#leaderboard tr[data-source-key="${row.source_key}"]`).click();
  await expect(page.locator("#detail-sidebar")).toBeVisible();
  await page.locator('#detail-sidebar [data-sidebar-close]').click();
  const timeline = page.locator(".timeline-diagnostics");
  const chart = timeline.locator("[data-timeline-chart]");
  await expect(chart.locator("canvas")).toBeVisible();
  await expect(timeline.locator("tbody tr")).toHaveCount(6);
  await expect(timeline.locator(".timeline-total")).toHaveText("Cumulative active duration: 4.417s");
  await expect(timeline).toContainText("Gaps without recorded activity are compressed");
  await expect(timeline).toContainText("Partial coverage");

  for (const [viewport, screenshot] of [
    [{ width: 1440, height: 900 }, "parallel-timeline-desktop.png"],
    [{ width: 390, height: 844 }, "parallel-timeline-mobile.png"],
  ]) {
    await page.setViewportSize(viewport);
    await expect.poll(() => chart.evaluate(node => node.querySelector("canvas")?.clientWidth === node.clientWidth)).toBe(true);
    const rendered = await page.evaluate(async () => {
      const { state } = await import("/assets/peval/modules/runtime.js");
      const chart = state.timelineChart;
      const option = chart.getOption();
      return {
        max: option.xAxis[0].max,
        bars: option.series[0].data.map(item => ({
          id: item.trace_item.tool_call_id,
          start: item.value[0],
          end: item.value[1],
          wallStart: item.trace_item.wall_start_ms,
          wallEnd: item.trace_item.wall_end_ms,
          startPixel: chart.convertToPixel({ xAxisIndex: 0 }, item.value[0]),
          endPixel: chart.convertToPixel({ xAxisIndex: 0 }, item.value[1]),
          rowPixel: chart.convertToPixel({ yAxisIndex: 0 }, item.value[2]),
        })),
        markers: option.series[1].data.map(item => item.value[0]),
      };
    });
    expect(rendered.bars.map(bar => [bar.id, bar.start, bar.end])).toEqual([
      ["inherited-long", 0, 1250],
      ["inherited-short", 0, 1067],
      ["explicit-first", 1250, 2250],
      ["explicit-later", 1750, 2750],
      ["explicit-nested", 2000, 2100],
      ["explicit-zero", 2750, 2750],
    ]);
    expect(rendered.markers).toEqual([0, 500, 1250, 2750]);
    expect(rendered.max).toBeGreaterThanOrEqual(2750);
    expect(rendered.max).toBeLessThan(4417);
    const [long, short, first, later] = rendered.bars;
    expect(long.startPixel).toBe(short.startPixel);
    expect(long.rowPixel).not.toBe(short.rowPixel);
    expect(short.endPixel).toBeLessThan(long.endPixel);
    expect(later.startPixel).toBeGreaterThan(first.startPixel);
    expect(later.startPixel).toBeLessThan(first.endPixel);
    expect(later.endPixel).toBeGreaterThan(first.endPixel);
    expect(long.wallStart).toBe(Date.parse("2026-01-01T00:00:01Z"));
    expect(short.wallStart).toBe(long.wallStart);
    expect(later.wallStart).toBe(Date.parse("2026-01-01T00:00:04.500Z"));
    expect(later.wallEnd - later.wallStart).toBe(1000);
    await timeline.screenshot({ path: testInfo.outputPath(screenshot) });
  }

  await page.setViewportSize({ width: 1440, height: 900 });
  await chart.scrollIntoViewIfNeeded();
  const point = await page.evaluate(async () => {
    const { state } = await import("/assets/peval/modules/runtime.js");
    const item = state.timelineChart.getOption().series[0].data[1];
    return state.timelineChart.convertToPixel({ gridIndex: 0 }, [(item.value[0] + item.value[1]) / 2, item.value[2]]);
  });
  const bounds = await chart.boundingBox();
  await page.mouse.move(bounds.x + point[0], bounds.y + point[1]);
  await expect(chart.locator(".timeline-tooltip")).toContainText("Compressed time offset");
  await expect(chart.locator(".timeline-tooltip")).toContainText("24.2%");
  await page.mouse.click(bounds.x + point[0], bounds.y + point[1]);
  await expect(page.locator('#detail-sidebar details[data-step="2"]')).toHaveAttribute("open", "");
  await page.locator('#detail-sidebar [data-sidebar-close]').click();
  await timeline.locator('tbody tr[data-timeline-step-id="5"]').first().click();
  await expect(page.locator('#detail-sidebar details[data-step="5"]')).toHaveAttribute("open", "");
  expect(errors).toEqual([]);
  expect(externalRequests).toEqual([]);
});
