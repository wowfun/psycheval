import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { startFixture, stopFixture } from "./fixture-process.mjs";

test("workspace tables keep an opaque header on one scroll owner and unclipped filter menus", async ({ page }, testInfo) => {
  const fixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PEVAL_E2E_TABLES: "1", PEVAL_E2E_TABLE_SCROLL: "1", PEVAL_E2E_LONG_TABLE: "1", PYTHONPATH: process.cwd() });
  const errors = []; page.on("pageerror", error => errors.push(error.message));
  try {
    for (const [path, selector] of [["", "#leaderboard"], ["/datasets", "[data-harbor-overview]"]]) {
      await page.goto(fixture.origin + path);
      const root = page.locator(selector), wrap = root.locator(".table-wrap").first();
      await expect(root.locator("tbody tr").nth(12)).toBeAttached();
      await wrap.scrollIntoViewIfNeeded();
      await wrap.evaluate(node => { node.scrollTop = 240; });
      const geometry = await wrap.evaluate(node => ({ top: node.getBoundingClientRect().top, head: node.querySelector("th").getBoundingClientRect().top, scroll: node.scrollTop }));
      expect(geometry.scroll).toBe(240);
      expect(Math.abs(geometry.head - geometry.top)).toBeLessThan(1);
      const box = await wrap.boundingBox(), header = await root.locator("thead").boundingBox();
      const clip = { x: Math.ceil(box.x) + 8, y: Math.floor(box.y), width: Math.floor(box.width) - 16, height: Math.floor(header.height) - 2 };
      const paint = color => root.locator("tbody tr,tbody td,tbody th").evaluateAll((nodes, color) => nodes.forEach(node => node.style.setProperty("background", color, "important")), color);
      await paint("#ff00ff"); const magenta = await page.screenshot({ clip });
      await paint("#00ff00"); const green = await page.screenshot({ clip });
      expect(magenta.equals(green), `${selector}: rows must never paint through the header's top edge`).toBe(true);
      await root.locator("tbody tr,tbody td,tbody th").evaluateAll(nodes => nodes.forEach(node => node.style.removeProperty("background")));
      if (!path) {
        expect(await root.locator(".toolbar-menu > summary").evaluateAll(nodes => nodes.every(node => ["none", "normal"].includes(getComputedStyle(node, "::after").content)))).toBe(true);
      }
    }
    const datasets = page.locator("[data-dataset-collections]");
    await expect(datasets.locator("[data-harbor-refresh]")).toHaveText("Refresh");
    await expect(page.locator(".harbor-workbench-tools [data-harbor-refresh]")).toHaveCount(0);
    const previousTable = await datasets.locator("table").elementHandle();
    const read = page.waitForResponse(response => response.url().endsWith("/api/collections/datasets") && response.request().method() === "GET");
    await datasets.locator("[data-harbor-refresh]").click(); await read;
    await expect.poll(() => previousTable.evaluate(node => node.isConnected)).toBe(false);
    const view = page.locator(".harbor-workbench-tools > .toolbar-menu").first();
    await view.locator("summary").click();
    await expect(view.locator("[data-task-flatten]")).toBeVisible();
    await expect(view.locator("[data-harbor-show-trash]")).toBeVisible();
    const actions = page.locator(".harbor-workbench-tools > .toolbar-menu").nth(1);
    await actions.locator("summary").click();
    await expect(view).not.toHaveAttribute("open", "");
    await expect(actions.locator("[data-harbor-sync-manifest]")).toBeVisible();
    await actions.locator("summary").press("Escape");
    await expect(actions).not.toHaveAttribute("open", "");
    const filter = datasets.locator('[data-filter-menu="id"]');
    await filter.locator("summary").click();
    const popup = filter.locator(".filter-menu");
    await expect(popup).toBeVisible();
    await expect.poll(() => popup.evaluate(node => node.matches(":popover-open"))).toBe(true);
    const panelBox = await popup.boundingBox(), tableBox = await datasets.locator(".table-wrap").boundingBox();
    expect(panelBox.y + panelBox.height).toBeGreaterThan(tableBox.y + tableBox.height);
    await filter.locator("input").first().focus(); await page.keyboard.press("Escape");
    await expect(filter.locator("summary")).toBeFocused();
    await page.screenshot({ path: testInfo.outputPath("dataset-tables.png") });
    expect(errors).toEqual([]);
  } finally { await stopFixture(fixture); }
});

test("filters without Popover support stay anchored and apply their draft", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_TABLES: "1", PEVAL_E2E_TABLE_SCROLL: "1", PYTHONPATH: process.cwd() });
  try {
    await page.addInitScript(() => {
      Object.defineProperty(HTMLElement.prototype, "showPopover", { configurable: true, value: undefined });
    });
    await page.goto(`${fixture.origin}/datasets`);
    const root = page.locator("[data-harbor-overview]"), wrap = root.locator(".table-wrap");
    await expect(root.locator("tbody tr").nth(25)).toBeAttached();
    await wrap.scrollIntoViewIfNeeded();
    const menu = root.locator('[data-filter-menu="dataset"]'), panel = menu.locator(".filter-menu");
    await menu.locator("summary").click();
    await expect(panel).toBeVisible();
    await expect(panel).not.toHaveAttribute("popover");
    expect(await panel.evaluate(node => getComputedStyle(node).position)).toBe("absolute");
    const offset = async () => (await panel.boundingBox()).y - (await menu.locator("summary").boundingBox()).y;
    const before = await offset();
    await wrap.evaluate(node => { node.scrollTop = 240; });
    expect(Math.abs(await offset() - before)).toBeLessThan(1);
    await panel.locator('[data-filter-key="dataset"][value="editable"]').check();
    await panel.locator('[data-filter-apply]').click();
    await expect(root.locator("tbody tr")).toHaveCount(26);
    await expect(root.locator('[data-filter-menu="dataset"]')).not.toHaveAttribute("open");
  } finally { await stopFixture(fixture); }
});

test("Task Summary groups metadata, exports chosen metrics and survives page navigation", async ({ page }, testInfo) => {
  const fixture = await startFixture({ PEVAL_E2E_TASK_SCORING: "1", PYTHONPATH: process.cwd() });
  const loaded = []; page.on("request", request => loaded.push(request.url()));
  try {
    await page.goto(`${fixture.origin}/datasets`);
    const summary = page.locator("[data-task-summary]");
    await expect(summary.locator("[data-summary-chart]")).toHaveCount(4);
    expect(loaded.some(url => /\/(runtime|leaderboard-summary|home-location)\.js/.test(url))).toBe(false);
    await summary.screenshot({ path: testInfo.outputPath("task-summary-default.png") });
    await page.setViewportSize({ width: 390, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await summary.screenshot({ path: testInfo.outputPath("task-summary-mobile.png") });
    await page.setViewportSize({ width: 1440, height: 900 });
    await summary.locator('[data-task-summary-group="category"]').click();
    await summary.locator('[data-task-summary-toggle]').click();
    await expect(summary.locator('td[data-table-column-key="group"]')).toHaveText(["Unset", "coding"]);
    await summary.locator('[data-task-summary-group="difficulty"]').click();
    await expect(summary.locator('td[data-table-column-key="group"]')).toHaveText(["Unset", "hard"]);
    await summary.locator('[data-task-summary-group="tags"]').click();
    await expect(summary.locator(".leaderboard-summary-head > div:first-child > p")).toContainText("counts may overlap");
    await summary.locator(".summary-metric-control > summary").click();
    await summary.locator('[data-metric-action="none"]').click();
    await summary.locator('[data-metric-id="rubric_count"]').check();
    await summary.locator('[data-metric-id="task_count"]').check();
    await summary.locator('[data-metric-apply]').click();
    await expect(summary.locator('[data-summary-chart]')).toHaveCount(2);
    await summary.locator(".summary-group-control > summary").click();
    await summary.locator('[data-group-action="none"]').click();
    await summary.locator('[data-comparison-group="0"]').check();
    await summary.locator('[data-group-apply]').click();
    await summary.locator(".export-menu > summary").click();
    const request = page.waitForRequest(request => request.url().endsWith("/api/harbor/task-exports"));
    const excel = page.waitForEvent("download"); await summary.locator('[data-summary-export="xlsx"]').click();
    const body = (await request).postDataJSON();
    expect(body.group_by).toBe("tags"); expect(body.comparison_groups).toHaveLength(1);
    expect(body.columns).toEqual(["group", "rubric_count", "task_count", "missing_rubric_count"]);
    expect((await excel).suggestedFilename()).toBe("peval-task-summary.xlsx");
    await summary.locator(".export-menu > summary").click();
    const png = page.waitForEvent("download"); await summary.locator('[data-summary-export="bar"]').click();
    const downloaded = await png;
    expect(downloaded.suggestedFilename()).toBe("peval-task-summary-bar.png");
    expect((await readFile(await downloaded.path())).subarray(1, 4).toString()).toBe("PNG");
    await page.locator('nav [data-workspace-route="jobs"]').click();
    await page.locator('nav [data-workspace-route="datasets"]').click();
    await expect(summary.locator('[data-task-summary-group="tags"]')).toHaveAttribute("aria-pressed", "true");
    await expect(summary.locator('[data-summary-chart]')).toHaveCount(2);
    await expect(summary.locator('tbody tr')).toHaveCount(1);
    await page.screenshot({ path: testInfo.outputPath("task-summary.png") });
  } finally { await stopFixture(fixture); }
});
