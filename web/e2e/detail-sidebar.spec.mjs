import { test, expect } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";
import { encodeWorkspaceLocation } from "../../src/psycheval/assets/web/app/workspace-location.js";

for (const role of ["guest", "admin"]) {
  test.describe(role, () => {
    let fixture;
    test.beforeAll(async () => { fixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PYTHONPATH: process.cwd(),
      ...(role === "guest" ? { PEVAL_E2E_PASSWORD: "fixture-secret" } : {}) });
    });
    test.afterAll(async () => { await stopFixture(fixture); });

    test("sees applicable Trial tabs across source switches and shared-link restoration", async ({ page }, testInfo) => {
      await page.goto(fixture.origin);
      const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
      const imported = catalog.items.find(row => row.adapter !== "harbor");
      const harbor = catalog.items.find(row => row.task_name === "workbuddy/office-one");
      const requests = [];
      page.on("request", request => {
        const path = new URL(request.url()).pathname;
        if (/^\/api\/verification-files\/|^\/api\/harbor\/datasets\/[^/]+\/tasks\//.test(path)) requests.push(path);
      });
      const sidebar = page.locator("#detail-sidebar");
      const tabs = sidebar.getByRole("tab");
      const trajectory = sidebar.locator('[data-trial-panel="trajectory"]');

      await page.locator(`.trajectory-row[data-source-key="${imported.source_key}"]`).click();
      await expect(tabs).toHaveText(["Trajectory"]);
      await expect(tabs).toHaveAttribute("aria-selected", "true");
      await expect(trajectory).toBeVisible();
      await expect(sidebar.locator('[data-trial-panel]')).toHaveCount(1);
      await tabs.focus();
      for (const key of ["ArrowLeft", "ArrowRight", "Home", "End"]) {
        await tabs.press(key);
        await expect(tabs).toBeFocused();
        await expect(trajectory).toBeVisible();
      }
      expect(requests).toEqual([]);

      await page.locator(`.trajectory-row[data-source-key="${harbor.source_key}"]`).click();
      await expect(tabs).toHaveText(["Verification", "Task", "Trajectory"]);
      await expect(sidebar.locator('[data-trial-panel="verification"]')).toBeVisible();
      await expect(sidebar.locator(".verification-metrics")).toContainText("0.676");
      await sidebar.getByRole("tab", { name: "Task", exact: true }).click();
      await expect(sidebar.locator("[data-harbor-editor]")).toHaveValue(/Create the requested artifact/);
      const historyLength = await page.evaluate(() => history.length);
      await page.locator(`.trajectory-row[data-source-key="${imported.source_key}"]`).click();
      await expect(tabs).toHaveText(["Trajectory"]);
      await expect(trajectory).toBeVisible();
      await expect.poll(() => new URL(page.url()).searchParams.get("tab")).toBe("trajectory");
      expect(await page.evaluate(() => history.length)).toBe(historyLength + 1);

      requests.length = 0;
      for (const tab of ["verification", "task"]) {
        const href = encodeWorkspaceLocation("home", { object: { source: imported.source_key, step: "2", tab } }, fixture.origin);
        const before = await page.evaluate(() => history.length);
        await page.goto(href);
        await expect(tabs).toHaveText(["Trajectory"]);
        await expect(tabs).toHaveAttribute("aria-selected", "true");
        await expect(trajectory).toBeVisible();
        await expect(sidebar.locator('.step[data-step="2"]')).toHaveAttribute("open", "");
        await expect(sidebar.locator('[data-trial-panel]')).toHaveCount(1);
        await expect.poll(() => new URL(page.url()).searchParams.get("tab")).toBe("trajectory");
        expect(await page.evaluate(() => history.length)).toBe(before + 1);
        const restored = page.url();
        await page.reload();
        await expect(trajectory).toBeVisible();
        await expect(tabs).toHaveText(["Trajectory"]);
        expect(page.url()).toBe(restored);
        expect(await page.evaluate(() => history.length)).toBe(before + 1);
      }
      expect(requests).toEqual([]);
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 900 });
        await expect(trajectory).toBeVisible();
        expect(await sidebar.evaluate(node => node.scrollWidth > node.clientWidth)).toBe(false);
        await page.screenshot({ path: testInfo.outputPath(`imported-trial-${width}.png`) });
      }
    });
  });
}
