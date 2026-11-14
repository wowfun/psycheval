import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";
import { decodeWorkspaceLocation } from "../../src/psycheval/assets/web/app/workspace-location.js";

for (const locale of ["en", "zh-CN"]) test(`toolbar menus and transient feedback (${locale})`, async ({ page }, testInfo) => {
  const fixture = await startFixture({ PEVAL_E2E_LOCALE: locale });
  try {
    await page.goto(fixture.origin);
    await expect(page.locator("#leaderboard tbody tr")).toHaveCount(2);
    await expect(page.locator("[data-workspace-copy-link]")).toHaveCount(0);
    const view = page.locator(".toolbar-view-menu");
    const actions = page.locator(".toolbar-actions-menu");
    await view.locator("summary").click();
    await expect(view.locator('[data-metric-scope][value="family"]')).toBeChecked();
    await expect(view.locator("[data-view-save]")).toBeEnabled();
    await view.locator('[data-metric-scope][value="root"]').check();
    await expect.poll(() => decodeWorkspaceLocation("home", new URL(page.url())).state.query.metric_scope).toBe("root");
    await expect(view.locator("summary")).toBeFocused();
    await view.locator("summary").click();
    await view.locator("[data-source-state-toggle]").check();
    await expect.poll(() => decodeWorkspaceLocation("home", new URL(page.url())).state.query.state).toBe("archived");
    await view.locator("summary").click();
    await view.locator("[data-source-state-toggle]").uncheck();
    await expect(page.locator("#leaderboard tbody tr")).toHaveCount(2);
    await actions.locator("summary").click();
    await expect(actions.locator("[data-source-state-action]")).toBeDisabled();
    await expect(actions.locator("[data-source-delete-action]")).toBeDisabled();
    await expect(actions.locator("[data-report-attach]")).toBeDisabled();
    await actions.locator("summary").press("Escape");
    await expect(actions.locator("summary")).toBeFocused();
    await page.locator('#leaderboard label:has([data-table-select-visible])').click();
    await expect(page.locator('#leaderboard [data-table-select-visible]')).toBeChecked();
    await actions.locator("summary").click();
    await expect(actions.locator("[data-source-state-action]")).toBeEnabled();
    await expect(actions.locator("[data-report-attach]")).toBeEnabled();
    for (const width of [1440, 850, 390]) {
      await page.setViewportSize({ width, height: 900 });
      for (const [name, menu] of [["view", view], ["actions", actions]]) {
        if (await menu.getAttribute("open") === null) await menu.locator("summary").click();
        await expect(menu.locator(".toolbar-menu-panel")).toBeVisible();
        const box = await menu.locator(".toolbar-menu-panel").boundingBox();
        expect(box.x).toBeGreaterThanOrEqual(0);
        expect(box.x + box.width).toBeLessThanOrEqual(width);
        await page.screenshot({ path: testInfo.outputPath(`${name}-${locale}-${width}.png`) });
        await menu.locator("summary").press("Escape");
      }
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.clock.install();
    await page.locator("[data-catalog-refresh]").click();
    const success = page.locator('[data-leaderboard-status] [data-action-feedback="home:rescan"]');
    await expect(success).toHaveText(locale === "en" ? "Completed" : "已完成");
    await expect(success.locator("button")).toHaveCount(0);
    await page.locator("#leaderboard-title").hover();
    await page.clock.fastForward(5001);
    await expect(success).toHaveCount(0);
    await page.route("**/api/source-discovery-operations", route => route.fulfill({ status: 500, contentType: "application/problem+json", body: JSON.stringify({ detail: "Controlled refresh failure" }) }));
    await page.locator("[data-catalog-refresh]").click();
    const failure = page.locator('#leaderboard [data-action-feedback="home:rescan"]');
    await expect(failure).toContainText("Controlled refresh failure");
    await expect(failure.locator("button")).toHaveCount(0);
    await page.clock.fastForward(10001);
    await expect(failure).toHaveCount(0);
  } finally { await stopFixture(fixture); }
});
