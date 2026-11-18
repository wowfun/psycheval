import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";
import { decodeWorkspaceLocation, encodeWorkspaceLocation } from "../../src/psycheval/assets/web/app/workspace-location.js";

test.describe("radar tooltip layout", () => {
  let fixture;
  test.beforeAll(async () => { fixture = await startFixture(); });
  test.afterAll(async () => { await stopFixture(fixture); });

  test("long tooltip content stays inside the chart and preserves Home scroll bounds", async ({ page }) => {
    const label = "LongModelName".repeat(22);
    const definitions = Array.from({ length: 32 }, (_, index) => ({
      key: `reward:metric-${index}`, label: `Metric ${index}`, type: "number", direction: "higher",
    }));
    await page.route(/\/api\/catalog(?:-summaries)?(?:\?|$)/, async route => {
      const response = await route.fetch();
      const envelope = await response.json();
      envelope.metric_descriptions = definitions;
      if (envelope.summary) {
        envelope.summary.groups = [0, 1].map(index => ({
          key: `model-${index}`, label: index === 1 ? label : "Baseline", count: 1,
          metrics: definitions.map(({ key }) => ({ key, count: 1, mean: index + 1 })),
        }));
      }
      await route.fulfill({ response, json: envelope });
    });
    await page.goto(encodeWorkspaceLocation("home", {
      state: { summary: { group_by: "model", chart_type: "radar", metrics: definitions.map(({ key }) => key) } },
    }, fixture.origin));
    const plot = page.locator("[data-summary-radar]");
    const tooltip = plot.locator(":scope > div").filter({ hasText: label });
    const overview = page.locator("#trajectory-overview");
    const pageOverflow = () => overview.evaluate(node => {
      const root = document.documentElement;
      const workspace = node.closest(".workspace");
      return {
        right: Math.max(0, root.scrollWidth - root.clientWidth),
        bottom: Math.max(0, root.scrollHeight - Math.max(root.clientHeight, Math.round(workspace.getBoundingClientRect().bottom + scrollY))),
      };
    });

    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await plot.locator("canvas").waitFor();
      await expect.poll(() => plot.evaluate(node => window.echarts.getInstanceByDom(node).getWidth())).toBeCloseTo((await plot.boundingBox()).width, 0);
      await plot.hover({ position: { x: (await plot.boundingBox()).width / 2 + 12, y: (await plot.boundingBox()).height / 2 + 8 } });
      await expect(tooltip).toBeVisible();
      expect(await pageOverflow()).toEqual({ right: 0, bottom: 0 });
      const chart = await plot.boundingBox(), hint = await tooltip.boundingBox();
      expect(hint.x).toBeGreaterThanOrEqual(chart.x - 1);
      expect(hint.x + hint.width).toBeLessThanOrEqual(chart.x + chart.width + 1);
      expect(hint.y).toBeGreaterThanOrEqual(chart.y - 1);
      expect(hint.y + hint.height).toBeLessThanOrEqual(chart.y + chart.height + 1);
      await overview.locator("h2").hover();
      await expect(tooltip).toBeHidden();
      expect(await pageOverflow()).toEqual({ right: 0, bottom: 0 });
    }
  });
});

test("radar selection, missing values, links, resize and chart cleanup", async ({ page, browser }, testInfo) => {
  const fixture = await startFixture();
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  let requests = 0;
  const summary = async route => {
    const response = await route.fetch();
    const envelope = await response.json();
    requests += 1;
    envelope.summary.matched_count = 7;
    envelope.summary.groups = Array.from({ length: 7 }, (_, index) => ({ key: `model-${index}`, label: `model-${index}`, count: 1,
      metrics: [
        { key: "score", type: "number", count: 1, mean: index / 6 },
        { key: "duration_ms", type: "duration", count: 1, mean: (7 - index) * 1000 },
        { key: "tps", type: "number", count: 1, mean: index * 20 },
        { key: "tool_success_rate", type: "percent", count: 1, mean: 1 },
      ],
    }));
    await route.fulfill({ response, json: envelope });
  };
  try {
    await page.route("**/api/catalog-summaries", summary);
    await page.goto(fixture.origin);
    await expect(page.locator("[data-summary-chart-type=bar]")).toHaveAttribute("aria-pressed", "true");
    await page.locator("[data-summary-chart-type=radar]").click();
    const plot = page.locator("[data-summary-radar]");
    await expect(plot.locator("canvas")).toHaveCount(1);
    const geometry = () => plot.evaluate(node => {
      const instance = window.echarts.getInstanceByDom(node);
      const option = instance.getOption();
      const coordinates = instance.getModel().getSeriesByIndex(0).coordinateSystem;
      const expected = option.series.flatMap(series => series.data[0].value.map((value, axis) => coordinates.dataToPoint(value, axis)));
      const elements = option.graphic.flatMap(component => component.elements);
      const circles = elements.filter(element => element.type === "circle");
      const missing = elements.filter(element => element.type === "group");
      return {
        measured: circles.length,
        maxError: Math.max(...circles.map(element => Math.min(...expected.map(point => Math.hypot(element.shape.cx - point[0], element.shape.cy - point[1]))))),
        missing: missing.length,
        distinctMissing: new Set(missing.map(element => `${element.x},${element.y}`)).size,
        colors: new Set(option.series.map(series => series.lineStyle.color)).size,
      };
    });
    const initialGeometry = await geometry();
    expect(initialGeometry.measured).toBeGreaterThan(0);
    expect(initialGeometry.missing).toBeGreaterThan(0);
    expect(initialGeometry.distinctMissing).toBe(initialGeometry.missing);
    expect(initialGeometry.maxError).toBeLessThan(0.5);
    expect(initialGeometry.colors).toBe(7);
    await expect(page.locator("[data-comparison-group]:checked")).toHaveCount(7);
    await expect(page.locator("[data-comparison-group]:disabled")).toHaveCount(0);
    await expect(page.locator("[data-radar-detail]")).toContainText("No data · n=0");
    await expect(page.locator("[data-radar-detail]")).toContainText("No group difference");
    const outline = () => plot.evaluate(node => {
      const instance = window.echarts.getInstanceByDom(node);
      const line = instance.getModel().getSeriesByIndex(1).getData().getItemGraphicEl(0).childAt(0);
      const area = instance.getModel().getSeriesByIndex(1).getData().getItemGraphicEl(0).childAt(1);
      return { stroke: line.style.stroke, fill: area.style.fill, opacity: line.style.opacity ?? 1, ignored: line.ignore, invisible: line.invisible, states: line.currentStates };
    });
    await page.locator("[data-radar-legend='1']").hover();
    await expect.poll(outline).toMatchObject({ stroke: expect.any(String), fill: expect.any(String), opacity: 1, ignored: false, invisible: false });
    await page.locator("#leaderboard-summary-title").hover();
    await expect.poll(outline).toMatchObject({ stroke: expect.any(String), fill: expect.any(String), opacity: 1, ignored: false, invisible: false });
    const requestCount = requests;
    const oldInstance = await plot.getAttribute("_echarts_instance_");
    await page.locator(".summary-group-control > summary").click();
    await page.locator("[data-comparison-group='0']").uncheck();
    await page.locator("[data-comparison-group='5']").check();
    await page.locator("[data-group-search]").fill("model-5");
    await expect(page.locator("[data-group-row]:visible")).toHaveCount(1);
    await page.locator("[data-comparison-group='5']").focus();
    await page.locator("[data-group-apply]").click();
    await page.locator("[data-radar-legend='4']").focus();
    await expect(page.locator("[data-radar-detail]")).toContainText("model-5");
    await page.locator(".summary-metric-control > summary").click();
    await page.locator("[data-metric-id=model_duration_ms]").check();
    await page.locator("[data-metric-apply]").click();
    await expect(page.locator("[data-group-search]")).toHaveValue("model-5");
    const href = page.url();
    const saved = decodeWorkspaceLocation("home", new URL(href)).state.summary;
    expect(saved.chart_type).toBe("radar");
    expect(saved.comparison_groups).toEqual(["model-1", "model-2", "model-3", "model-4", "model-5", "model-6"]);
    expect(saved.metrics).toContain("model_duration_ms");
    expect(requests).toBe(requestCount);
    expect(await page.evaluate(id => window.echarts.getInstanceById(id), oldInstance)).toBeUndefined();
    for (const width of [1440, 850, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await expect.poll(async () => plot.evaluate(node => Math.round(window.echarts.getInstanceByDom(node).getWidth()) === node.clientWidth)).toBe(true);
      await expect.poll(async () => (await geometry()).maxError).toBeLessThan(0.5);
      await expect.poll(() => plot.evaluate(node => {
        const instance = window.echarts.getInstanceByDom(node);
        const view = instance.getViewOfComponentModel(instance.getModel().getComponent("radar"));
        const labels = [];
        view.group.traverse(element => {
          if (element.type !== "text" || element.anid !== "name") return;
          const bounds = element.getBoundingRect().clone();
          bounds.applyTransform(element.getComputedTransform());
          labels.push(bounds.x >= -1 && bounds.y >= -1 && bounds.x + bounds.width <= node.clientWidth + 1 && bounds.y + bounds.height <= node.clientHeight + 1);
        });
        return labels.length > 0 && labels.every(Boolean);
      })).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`radar-${width}.png`), fullPage: true });
      const box = await plot.boundingBox();
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width + 1);
    }
    const fresh = await browser.newContext();
    try {
      const recipient = await fresh.newPage();
      await recipient.route("**/api/catalog-summaries", summary);
      await recipient.goto(href);
      await expect(recipient.locator("[data-summary-radar] canvas")).toHaveCount(1);
      await expect(recipient.locator("[data-comparison-group]:checked")).toHaveCount(6);
      await recipient.reload();
      await expect(recipient.locator("[data-metric-id=model_duration_ms]")).toBeChecked();
      await expect(recipient.locator("[data-catalog-clear-conditions]")).toBeDisabled();
      await recipient.locator("[data-leaderboard-search-input]").fill("e2e");
      await expect(recipient.locator("[data-catalog-clear-conditions]")).toBeEnabled();
      await recipient.locator("[data-catalog-clear-conditions]").click();
      await expect(recipient.locator("[data-leaderboard-search-input]")).toHaveValue("");
      await expect(recipient.locator("[data-summary-chart-type=radar]")).toHaveAttribute("aria-pressed", "true");
      expect(decodeWorkspaceLocation("home", new URL(recipient.url())).state.summary).toEqual(saved);
    } finally { await fresh.close(); }
    await page.locator("[data-summary-chart-type=bar]").click();
    await expect(plot).toHaveCount(0);
    await page.locator("[data-summary-chart-type=radar]").click();
    await expect(page.locator("[data-group-search]")).toHaveValue("model-5");
    await expect(page.locator("[data-comparison-group]:checked")).toHaveCount(6);
    expect(errors).toEqual([]);
  } finally { await stopFixture(fixture); }
});
