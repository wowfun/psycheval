import { test, expect } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

test("partial trajectory keeps the execution error and exposes cleanup paths", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PEVAL_E2E_PARTIAL: "1", PEVAL_E2E_LOCALE: "zh-CN", PYTHONPATH: process.cwd() });
  try {
    await page.goto(fixture.origin);
    const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
    const trial = catalog.items.find(row => row.task_name === "workbuddy/office-one");
    expect(trial.status).toBe("errored");
    await page.locator(`.trajectory-row[data-source-key="${trial.source_key}"]`).click();
    const sidebar = page.locator("#detail-sidebar");
    await sidebar.getByRole("tab", { name: "轨迹", exact: true }).click();
    const trajectory = sidebar.locator('[data-trial-panel="trajectory"]');
    await expect(trajectory.getByRole("note")).toContainText("不完整轨迹");
    await expect(trajectory).toContainText("process_pipes: TimeoutError");
    await expect(trajectory).toContainText("retained-runtime");
    await expect(trajectory.locator(".step")).toHaveCount(1);
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await trajectory.evaluate(node => node.scrollWidth > node.clientWidth)).toBe(false);
      await page.screenshot({ path: `.local/partial-trajectory-${width}.png` });
    }
    await page.reload();
    await expect(page.locator('#detail-sidebar [role="note"]')).toContainText("不完整轨迹");
  } finally { await stopFixture(fixture); }
});
