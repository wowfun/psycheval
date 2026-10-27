import { readFile, writeFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";
import { expectSummaryImageSize } from "./summary-image-assertions.mjs";

test("summary menu downloads Excel and complete PNG charts with legend without changing presentation", async ({ page }, testInfo) => {
  const fixture = await startFixture({ PEVAL_E2E_LOCALE: "zh-CN" });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  let summaryRequests = 0;
  await page.route("**/api/catalog-summaries", async route => {
    const response = await route.fetch();
    const envelope = await response.json();
    summaryRequests += 1;
    envelope.summary.matched_count = 7;
    envelope.summary.groups = Array.from({ length: 7 }, (_, index) => ({
      key: `model-${index}`, label: index === 0 ? "中文模型与复杂任务评测的完整名称".repeat(5) : `model-${index}`, count: 1,
      metrics: [
        { key: "score", type: "number", count: 1, mean: index / 6, distribution: { p95: index / 6 } },
        { key: "duration_ms", type: "duration", count: 1, mean: (7 - index) * 1000, distribution: { p95: (7 - index) * 2000 } },
        { key: "tps", type: "number", count: index ? 1 : 0, mean: index ? index * 20 : null, distribution: { p95: index ? index * 25 : null } },
        { key: "tool_success_rate", type: "percent", count: 1, mean: 1, distribution: { p95: 1 } },
      ],
    }));
    await route.fulfill({ response, json: envelope });
  });
  const menu = page.locator(".leaderboard-summary-export");
  const exportButton = kind => menu.locator(`[data-summary-export=${kind}]`);
  async function download(kind) {
    await menu.locator("summary").click();
    const pending = page.waitForEvent("download");
    await exportButton(kind).click();
    const file = await pending;
    const name = kind === "xlsx" ? "peval-leaderboard-summary.xlsx" : `peval-leaderboard-summary-${kind}.png`;
    expect(file.suggestedFilename()).toBe(name);
    const path = testInfo.outputPath(name);
    await file.saveAs(path);
    await expect(menu).not.toHaveAttribute("open");
    const bytes = await readFile(path);
    if (kind === "xlsx") expect(bytes.subarray(0, 2).toString()).toBe("PK");
    else {
      expect(bytes.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
      expectSummaryImageSize(bytes.readUInt32BE(16), bytes.readUInt32BE(20), kind);
      const decoded = await page.evaluate(async data => {
        const bitmap = await createImageBitmap(new Blob([new Uint8Array(data)], { type: "image/png" }));
        const canvas = document.createElement("canvas"); canvas.width = bitmap.width; canvas.height = bitmap.height;
        const context = canvas.getContext("2d"); context.drawImage(bitmap, 0, 0);
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
        let ink = 0;
        for (let i = 0; i < pixels.length; i += 4) if (pixels[i] < 230 || pixels[i + 1] < 230 || pixels[i + 2] < 230) ink += 1;
        const result = { height: bitmap.height, corner: [...pixels.slice(0, 4)], ink };
        bitmap.close(); canvas.width = canvas.height = 0; return result;
      }, [...bytes]);
      expect(decoded.height).toBeGreaterThan(600);
      expect(decoded.corner).toEqual([255, 255, 255, 255]);
      expect(decoded.ink).toBeGreaterThan(10000);
    }
  }
  try {
    await page.goto(fixture.origin);
    await page.locator("[data-summary-group-by=model]").click();
    await expect(exportButton("bar")).toBeEnabled();
    await page.locator("[data-summary-statistic=p95]").click();
    await menu.locator("summary").focus();
    await page.keyboard.press("Enter");
    await expect(menu).toHaveAttribute("open", "");
    await page.keyboard.press("Escape");
    await expect(menu).not.toHaveAttribute("open");
    await expect(menu.locator("summary")).toBeFocused();
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await menu.locator("summary").click();
      const panel = menu.locator(".export-menu-panel");
      await panel.scrollIntoViewIfNeeded();
      const box = await panel.boundingBox();
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width);
      expect(await panel.evaluate(node => {
        const box = node.getBoundingClientRect();
        return node.contains(document.elementFromPoint(box.x + 10, box.bottom - 10));
      })).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`export-menu-${width}.png`), fullPage: true });
      await page.locator("#leaderboard-summary-title").click();
      await expect(menu).not.toHaveAttribute("open");
    }
    const href = page.url(), requestCount = summaryRequests;
    const response = page.waitForResponse(response => response.url().endsWith("/api/exports"));
    await download("xlsx");
    const excel = await response;
    expect(excel.status()).toBe(200);
    expect(excel.request().postDataJSON().summary).toMatchObject({ scope: "leaderboard", group_by: "model", statistic: "p95" });
    await download("bar");
    await download("radar");
    expect(page.url()).toBe(href);
    expect(summaryRequests).toBe(requestCount);
    await expect(page.locator("[data-summary-chart-type=bar]")).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator("[data-summary-radar]")).toHaveCount(0);
    await page.locator("[data-summary-chart-type=radar]").click();
    await expect(page.locator("[data-summary-radar] canvas")).toHaveCount(1);
    await page.locator("[data-radar-group='4']").uncheck();
    await page.locator("[data-radar-group='6']").check();
    await page.locator("[data-radar-search]").fill("model-6");
    const radarHref = page.url();
    const instance = await page.locator("[data-summary-radar]").getAttribute("_echarts_instance_");
    await download("bar");
    await download("radar");
    expect(page.url()).toBe(radarHref);
    expect(summaryRequests).toBe(requestCount);
    await expect(page.locator("[data-summary-radar]")).toHaveAttribute("_echarts_instance_", instance);
    await expect(page.locator("[data-radar-search]")).toHaveValue("model-6");
    await expect(page.locator("[data-radar-group]:checked")).toHaveCount(5);
    await expect(page.locator('#leaderboard .action-feedback').filter({ hasText: /活跃快照|已归档快照|全部 sessions/ })).toHaveCount(0);
    expect(errors).toEqual([]);
  } finally { await stopFixture(fixture); }
});

test("32 radar axes use real font bounds and stay attached to the exported chart", async ({ page }, testInfo) => {
  const fixture = await startFixture();
  try {
    await page.goto(fixture.origin);
    await page.locator("[data-summary-group-by=model]").click();
    await expect(page.locator('[data-summary-export="radar"]')).toBeEnabled();
    const result = await page.evaluate(async () => {
      const { state } = await import("/assets/peval/modules/runtime.js");
      const { leaderboardSummaryImageSnapshot } = await import("/assets/peval/modules/leaderboard-summary.js");
      const { summaryImageLayout, summaryImageBlob } = await import("/assets/peval/modules/leaderboard-summary-export.js");
      const definitions = Array.from({ length: 32 }, (_, index) => ({
        key: `reward:axis-${index}`, type: "number", direction: index % 2 ? "lower" : "higher",
        label: index === 0 ? "无空格的完整中文指标名称".repeat(3) : index === 16 ? "UnbrokenMetricIdentifier".repeat(3) : index === 8 ? "A long English metric label with multiple lines" : `Metric ${index}`,
        unit: index === 0 ? "毫秒每条记录" : index === 8 ? "USD" : index === 16 ? "tokens/s" : null,
      }));
      state.catalogPage = { total: 2, metric_descriptions: definitions };
      state.leaderboardSummaryMetrics = definitions.map(item => item.key);
      state.leaderboardSummaryRadarGroups = null;
      state.leaderboardSummary = { summary: { matched_count: 2, groups: [0, 1].map(index => ({
        key: `group-${index}`, label: `Group ${index}`, count: 1,
        metrics: definitions.map(item => ({ key: item.key, count: 1, mean: index })),
      })) } };
      await document.fonts.ready;
      const measure = document.createElement("canvas").getContext("2d");
      const snapshot = leaderboardSummaryImageSnapshot();
      const layout = summaryImageLayout("radar", snapshot, measure);
      const original = window.echarts.init;
      let geometry;
      window.echarts.init = (...args) => {
        const chart = original(...args);
        const render = chart.renderToCanvas.bind(chart);
        chart.renderToCanvas = options => {
          const radar = chart.getOption().radar[0];
          const coordinates = chart.getModel().getSeriesByIndex(0).coordinateSystem;
          geometry = { center: radar.center, radius: radar.radius, vertices: definitions.map((_, index) => coordinates.dataToPoint(100, index)) };
          return render(options);
        };
        return chart;
      };
      try {
        const blob = await summaryImageBlob("radar", snapshot);
        return { layout, geometry, names: definitions.map(item => item.label + (item.unit ? ` (${item.unit})` : "")), bytes: [...new Uint8Array(await blob.arrayBuffer())] };
      } finally { window.echarts.init = original; }
    });
    const { plot } = result.layout;
    expectSummaryImageSize(result.layout.width * 2, result.layout.height * 2, "radar");
    expect(plot.labels).toHaveLength(32);
    expect(result.geometry.center).toEqual(plot.center);
    expect(result.geometry.radius).toBe(plot.radius);
    plot.labels.forEach((label, index) => {
      expect(label.lines.join("")).toBe(`${result.names[index]} ${index % 2 ? "↓" : "↑"}`);
      expect(label.x).toBeGreaterThanOrEqual(0);
      expect(label.y).toBeGreaterThanOrEqual(0);
      expect(label.x + label.width).toBeLessThanOrEqual(plot.width);
      expect(label.y + label.height).toBeLessThanOrEqual(plot.height);
      const angle = Math.PI / 2 + index * 2 * Math.PI / 32;
      const vertex = result.geometry.vertices[index];
      expect(Math.hypot(vertex[0] - plot.center[0] - plot.radius * Math.cos(angle), vertex[1] - plot.center[1] + plot.radius * Math.sin(angle))).toBeLessThan(0.01);
      for (const other of plot.labels.slice(0, index)) {
        expect(label.x >= other.x + other.width || other.x >= label.x + label.width || label.y >= other.y + other.height || other.y >= label.y + label.height).toBe(true);
      }
    });
    const legend = result.layout.commands.filter(command => command.type === "text" && command.y >= plot.y + plot.height);
    expect(legend[0].lines).toEqual(["Comparison groups"]);
    expect(legend[0].y).toBe(plot.y + plot.height + 24);
    expect(legend.every(command => command.y >= plot.y + plot.height + 24)).toBe(true);
    await writeFile(testInfo.outputPath("radar-32-axes.png"), Buffer.from(result.bytes));
  } finally { await stopFixture(fixture); }
});
