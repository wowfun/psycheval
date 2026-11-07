import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.beforeAll(async () => {
  fixture = await startFixture({ PEVAL_E2E_TABLES: "1", PEVAL_E2E_COLLECTIONS: "1", PYTHONPATH: process.cwd() });
});
test.afterAll(async () => { await stopFixture(fixture); });

test("Jobs mount management preserves concurrent associations, rename focus and selection", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${fixture.origin}/jobs`);
  await expect(page.locator("[data-jobs-list] tbody tr")).toHaveCount(2);
  await page.locator("[data-jobs-mounts]").click();
  const panel = page.locator(".registry-manager-panel");
  await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/catalog-status`)).json()).checking).toBe(false);
  const configResponse = await page.request.get(`${fixture.origin}/api/config`);
  const config = await configResponse.json();
  const mount = config.mounts.find(row => row.id === "collections");
  const pathCell = panel.locator('[data-table-row-key="collections"] [data-table-column-key="path"]');
  await pathCell.dblclick();
  const input = pathCell.locator("input");
  const draft = `${mount.path}/.`;
  await input.fill(draft);

  // Another editor changes an unrelated field while this draft stays open.
  const concurrent = await page.request.patch(`${fixture.origin}/api/harbor/mounts/collections`, {
    headers: { "If-Match": configResponse.headers().etag, Origin: fixture.origin },
    data: { new_id: "collections", path: mount.path, dataset_ids: ["editable"] },
  });
  expect(concurrent.status(), await concurrent.text()).toBe(202);
  const operation = await concurrent.json();
  await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/operations/${operation.id}`)).json()).state).toBe("succeeded");
  await input.press("Enter");
  await expect(pathCell.locator(".table-cell-editor-status")).toContainText("Current saved content");
  await expect(pathCell.locator("details pre")).toContainText("editable");
  await expect(input).toHaveValue(draft);
  await page.screenshot({ path: testInfo.outputPath("registry-conflict.png") });
  const retried = page.waitForRequest(request => request.method() === "PATCH" && request.url().endsWith("/api/harbor/mounts/collections"));
  await input.press("Enter");
  expect((await retried).postDataJSON()).toEqual({ new_id: "collections", path: draft, dataset_ids: ["editable"] });
  await expect(pathCell.locator("input")).toHaveCount(0);
  await expect(panel.locator('[data-table-column-key="datasets"]')).toContainText("editable");
  await expect(page.locator('[data-jobs-collection] [data-action-feedback="jobs:registry"]')).toContainText("Completed");

  const select = panel.locator('[data-table-row-select="collections"]');
  await select.focus(); await select.press("Space");
  const idCell = panel.locator('[data-table-row-key="collections"] [data-table-column-key="id"]');
  await idCell.dblclick();
  await idCell.locator("input").fill("renamed");
  await idCell.locator("input").press("Enter");
  const renamed = panel.locator('[data-table-row-key="renamed"]');
  await expect(renamed).toBeVisible();
  await expect(renamed.locator('[data-table-row-select="renamed"]')).toBeChecked();
  await expect(renamed.locator('[data-table-column-key="id"]')).toBeFocused();
  await expect(page.locator('[data-jobs-collection] [data-action-feedback="jobs:registry"]')).toContainText("Completed");
  await expect(renamed.locator('[data-table-column-key="id"]')).toBeFocused();
  await page.screenshot({ path: testInfo.outputPath("registry-renamed.png") });
  page.once("dialog", dialog => dialog.accept());
  await panel.locator("[data-harbor-remove-mounts]").click();
  await expect(panel.locator("[data-table-row-select]")).toHaveCount(0);
  const finalConfig = await (await page.request.get(`${fixture.origin}/api/config`)).json();
  expect(finalConfig.mounts).toEqual([]);
});
