import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

test("shared header stays aligned across routes with different page heights", async ({ page }, testInfo) => {
  const fixture = await startFixture({ PYTHONPATH: process.cwd() });
  try {
    await page.goto(fixture.origin);
    await page.evaluate(() => document.fonts.ready);
    for (const width of [1440, 1920, 390]) {
      await page.setViewportSize({ width, height: 900 });
      let reference;
      for (const route of ["home", "datasets", "jobs", "reports", "config", "home"]) {
        const link = page.locator(`.workspace-nav [data-workspace-route="${route}"]`);
        await link.click();
        await expect(link).toHaveAttribute("aria-current", "page");
        await expect(page.locator(`[data-workspace-page="${route}"]`)).toBeVisible();
        const boxes = await Promise.all([".workspace-header", ".workspace-brand", ".workspace-nav"].map(selector => page.locator(selector).boundingBox()));
        if (!reference) reference = boxes;
        boxes.forEach((box, index) => {
          for (const key of ["x", "y", "width", "height"]) expect(box[key], `${route} ${index}.${key} at ${width}`).toBeCloseTo(reference[index][key], 0);
        });
      }
      await page.screenshot({ path: testInfo.outputPath(`header-${width}.png`) });
    }
  } finally {
    await stopFixture(fixture);
  }
});
