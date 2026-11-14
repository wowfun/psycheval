import { test, expect } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

test("Dataset columns persist, refresh preserves drafts, and shared menus and pies fit both viewports", async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  const fixture = await startFixture({ PEVAL_E2E_TASK_SCORING: "1" });
  const errors = []; page.on("pageerror", error => errors.push(error.message));
  try {
    await page.goto(`${fixture.origin}/datasets`);
    const registry = page.locator("[data-dataset-collections]");
    await expect(registry.locator("tbody tr")).toHaveCount(2);
    await registry.locator(".column-control > summary").click();
    await registry.locator('[data-column-visible="note"]').check();
    for (let index = 0; index < 4; index++) await registry.locator('[data-column-move="note"][data-column-direction="-1"]').click();
    await registry.locator("[data-column-apply]").click();
    const columns = () => registry.locator("th[data-table-column]").evaluateAll(nodes => nodes.map(node => node.dataset.tableColumn));
    expect((await columns()).slice(0, 2)).toEqual(["id", "note"]);
    await page.reload();
    await expect(registry.locator('th[data-table-column="note"]')).toBeVisible();
    expect((await columns()).slice(0, 2)).toEqual(["id", "note"]);
    const note = registry.locator('[data-dataset-row="native"] td[data-table-column-key="note"]');
    await note.dblclick(); await note.locator("textarea").fill("Unsaved note");
    await registry.locator("[data-harbor-refresh]").click();
    await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/collections/datasets/status`)).json()).checking).toBe(false);
    await expect(note.locator("textarea")).toHaveValue("Unsaved note");
    await note.locator("textarea").press("Escape");
    await registry.locator(".column-control > summary").click();
    await registry.locator("[data-column-reset]").click();
    await registry.locator("[data-column-apply]").click();
    await expect(registry.locator('th[data-table-column="note"]')).toHaveCount(0);

    const actions = page.locator(".harbor-workbench-tools .toolbar-actions-menu");
    await actions.locator("summary").click();
    await expect(actions.locator("hr")).toHaveCount(1);
    expect(await actions.locator("button").first().evaluate(node => ({ radius: getComputedStyle(node).borderRadius, shadow: getComputedStyle(node).boxShadow }))).toEqual({ radius: "6px", shadow: "none" });
    await actions.locator("button").first().press("Escape");
    await expect(actions).not.toHaveAttribute("open");
    const view = page.locator(".harbor-workbench-tools .toolbar-view-menu");
    await view.locator("summary").click();
    await expect(view.locator(".toolbar-menu-check input[type=checkbox]")).toHaveCount(2);
    await view.locator("[data-task-flatten]").check();
    await expect(view).toHaveAttribute("open", "");
    await view.locator("[data-task-flatten]").press("Escape");

    const summary = page.locator("[data-task-summary]");
    await summary.locator('[data-task-summary-chart="pie"]').click();
    const chart = summary.locator(".leaderboard-summary-chart-panel");
    await chart.screenshot({ path: testInfo.outputPath("task-pies-desktop.png") });
    await page.setViewportSize({ width: 390, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await chart.screenshot({ path: testInfo.outputPath("task-pies-mobile.png") });
    await actions.locator("summary").click();
    const trigger = await actions.locator("summary").boundingBox();
    const panel = await actions.locator(".toolbar-menu-panel").boundingBox();
    expect(Math.min(Math.abs(panel.y - trigger.y - trigger.height - 6), Math.abs(trigger.y - panel.y - panel.height - 6))).toBeLessThan(2);
    expect(panel.y).toBeGreaterThanOrEqual(8);
    expect(panel.y + panel.height).toBeLessThanOrEqual(844);
    await actions.locator("button").first().press("Escape");
    expect(errors).toEqual([]);
  } finally { await stopFixture(fixture); }
});
