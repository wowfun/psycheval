import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { startFixture, stopFixture } from "./fixture-process.mjs";
import { expectSummaryImageSize } from "./summary-image-assertions.mjs";
import { encodeWorkspaceLocation, decodeWorkspaceLocation } from "../../src/psycheval/assets/web/app/workspace-location.js";

const raw = "自定义能耗/大小写 %." + "中文".repeat(10);
const id = "atif.extra:" + encodeURIComponent(raw);
const selected = [id, "score", "duration_ms"];
const python = process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python";

test("dynamic metrics retain selection, numeric exports and safe links across layouts and history", async ({ page }, testInfo) => {
  const fixture = await startFixture({ PEVAL_E2E_METRICS: "1" });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  let summaryRequests = 0;
  page.on("request", request => { if (request.url().endsWith("/api/catalog-summaries")) summaryRequests++; });
  try {
    await page.goto(encodeWorkspaceLocation("home", { state: { summary: { group_by: "model", metrics: selected } } }, fixture.origin));
    const chart = page.locator(`[data-summary-chart="${id}"]`);
    await expect(chart).toContainText("-3 Wh");
    await expect(chart).toContainText("0 Wh");
    const zeroes = await chart.locator(".leaderboard-summary-bar-track b").evaluateAll(nodes => nodes.map(node => node.style.left));
    expect(zeroes).toEqual(Array(5).fill("25%"));
    const metricMenu = page.locator(".summary-metric-control");
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await metricMenu.locator("summary").click();
      await page.locator("[data-metric-search]").fill("自定义");
      await expect(page.locator("[data-metric-row]:visible")).toHaveCount(1);
      const box = await metricMenu.locator(".column-control-panel").boundingBox();
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width);
      await page.screenshot({ path: testInfo.outputPath(`metrics-${width}.png`) });
      await page.keyboard.press("Escape");
      await expect(metricMenu).not.toHaveAttribute("open");
      await expect(metricMenu.locator("summary")).toBeFocused();
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.locator("#leaderboard .column-control > summary").click();
    await page.locator("[data-column-search]").fill("自定义");
    await expect(page.locator("[data-column-row]:visible")).toHaveCount(1);
    await page.locator(`[data-column-visible="${id}"]`).check();
    await page.locator("[data-column-apply]").click();
    const sorted = page.waitForRequest(request => request.url().includes("/api/catalog?") && new URL(request.url()).searchParams.get("sort") === `metric:${id}`);
    await page.locator(`[data-table-sort="${id}"]`).click();
    expect(new URL((await sorted).url()).searchParams.get("direction")).toBe("asc");
    await expect(page.locator(`tbody [data-table-column-key="${id}"]`).first()).toContainText("-3 Wh");
    const href = page.url(), count = summaryRequests;
    for (const kind of ["xlsx", "bar", "radar"]) {
      await page.locator(".leaderboard-summary-export > summary").click();
      const pending = page.waitForEvent("download");
      await page.locator(`[data-summary-export="${kind}"]`).click();
      const download = await pending;
      const path = testInfo.outputPath(download.suggestedFilename());
      await download.saveAs(path);
      if (kind === "xlsx") {
        const { stdout } = await promisify(execFile)(python, ["-X", "utf8", "-c", "import sys,zipfile,json; from xml.etree import ElementTree as E; z=zipfile.ZipFile(sys.argv[1]); print(json.dumps({'strings':z.read('xl/sharedStrings.xml').decode(),'values':[v.text for v in E.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//{*}v')]}))", path]);
        const workbook = JSON.parse(stdout);
        expect(workbook.strings).toContain("Wh");
        expect(workbook.strings).not.toContain("Tokens");
        expect(workbook.values).toContain("-3");
        expect(workbook.values).toContain("0");
      } else {
        const bytes = await readFile(path);
        const size = await page.evaluate(async data => {
          const bitmap = await createImageBitmap(new Blob([new Uint8Array(data)], { type: "image/png" }));
          const size = [bitmap.width, bitmap.height]; bitmap.close(); return size;
        }, [...bytes]);
        expectSummaryImageSize(size[0], size[1], kind);
      }
      expect(page.url()).toBe(href);
    }
    expect(summaryRequests).toBe(count);
    await page.reload();
    await expect(chart).toContainText("-3 Wh");
    expect(decodeWorkspaceLocation("home", new URL(page.url())).state.summary.metrics).toEqual(selected);
    await page.locator("[data-summary-statistic=p95]").click();
    await page.locator('a[data-workspace-route="jobs"]').first().click();
    await page.goBack();
    await expect(page.locator("[data-summary-statistic=p95]")).toHaveAttribute("aria-pressed", "true");
    const removed = encodeWorkspaceLocation("home", { state: { query: { sort: "metric:reward:removed", direction: "asc" }, summary: { group_by: "model", metrics: [id, "reward:removed"] } } }, fixture.origin);
    await page.goto(removed);
    await expect(chart).toBeVisible();
    await expect.poll(() => decodeWorkspaceLocation("home", new URL(page.url())).state.query.sort).toBe("last_turn_end");
    expect(decodeWorkspaceLocation("home", new URL(page.url())).state.summary.metrics).toContain("reward:removed");
    await expect(metricMenu).toContainText("Currently unavailable");
    await metricMenu.locator("summary").click();
    const beforeReorder = page.url();
    await page.locator(`[data-metric-row="${id}"] [data-metric-move="1"]`).click();
    expect(page.url()).toBe(beforeReorder);
    await page.locator("[data-metric-apply]").click();
    expect(decodeWorkspaceLocation("home", new URL(page.url())).state.summary.metrics).toEqual(["reward:removed", id]);
    await page.reload();
    await expect(chart).toBeVisible();
    expect(decodeWorkspaceLocation("home", new URL(page.url())).state.summary.metrics).toEqual(["reward:removed", id]);
    const nearLimit = encodeWorkspaceLocation("home", { state: { query: { search: "中".repeat(15000) }, summary: { metrics: selected } } }, fixture.origin);
    expect(new TextEncoder().encode(nearLimit).length).toBeGreaterThan(60000);
    const longQuery = page.waitForResponse(response => response.url().includes("/api/catalog?") || response.url().endsWith("/api/catalog-queries"));
    await page.goto(nearLimit);
    expect((await longQuery).status()).toBe(200);
    await expect(page.locator("[data-leaderboard-search-input]")).toHaveValue("中".repeat(15000));
    await expect(page.locator("#leaderboard-summary")).toContainText("No Trials match");
    expect(errors).toEqual([]);
  } finally { await stopFixture(fixture); }
});
