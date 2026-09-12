import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.beforeAll(async () => {
  fixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PEVAL_E2E_TABLES: "1", PYTHONPATH: process.cwd() });
});
test.afterAll(async () => { await stopFixture(fixture); });

test("Home editable cells activate the row on click and edit on double click", async ({ page }) => {
  await page.goto(fixture.origin);
  const row = page.locator('#leaderboard tbody tr').filter({ hasText: 'office-one' });
  const sourceKey = await row.getAttribute('data-source-key');
  const cell = page.locator(`#leaderboard [data-source-key="${sourceKey}"] [data-table-column-key="task_name"]`);
  await cell.click();
  await expect(page.locator('#detail-sidebar')).toBeVisible();
  await page.locator('#detail-sidebar [data-sidebar-close]').click();
  await cell.dblclick({ delay: 150 });
  await expect(cell.locator('[data-table-cell-editor]')).toBeVisible();
  await expect(page.locator('#detail-sidebar')).toBeHidden();
  await cell.locator('input').press('Escape');
  await cell.focus();
  await cell.press('Enter');
  await expect(cell.locator('[data-table-cell-editor]')).toBeVisible();
  await cell.locator('input').press('Escape');
});

test("Dataset Task cells keep single-click selection and double-click editing separate", async ({ page }) => {
  await page.goto(`${fixture.origin}/datasets`);
  const first = page.locator('[data-harbor-row-key="dataset:editable|task:first"]');
  await first.locator('[data-table-column-key="task"]').click();
  await expect(first).toHaveClass(/selected-row/);
  const row = page.locator('[data-harbor-row-key="dataset:editable|task:second"]');
  const cell = row.locator('[data-table-column-key="task"]');
  await cell.dblclick({ delay: 150 });
  await expect(cell.locator('[data-table-cell-editor]')).toBeVisible();
  await expect(first).toHaveClass(/selected-row/);
  await cell.locator('input').press('Escape');
  await cell.click();
  await expect(row).toHaveClass(/selected-row/);
});

test("Dataset is the first data column and filters and sorts the complete catalog", async ({ page }) => {
  await page.goto(fixture.origin);
  const table = page.locator('#leaderboard table');
  await expect(table.locator('thead th').nth(1)).toContainText('Dataset');
  await expect(table.locator('tbody [data-table-column-key="dataset_id"]').filter({ hasText: 'office' })).toHaveCount(1);
  const sorted = page.waitForRequest(request => request.url().includes('/api/catalog?') && new URL(request.url()).searchParams.get('sort') === 'dataset');
  await table.locator('[data-table-sort="dataset_id"]').click();
  expect(new URL((await sorted).url()).searchParams.get('direction')).toBe('asc');
  const menu = table.locator('[data-filter-menu="dataset_id"]');
  await menu.locator('summary').click();
  await menu.locator('input[value="office"]').check();
  const filtered = page.waitForRequest(request => request.url().includes('/api/catalog?') && new URL(request.url()).searchParams.get('dataset') === 'office');
  await menu.locator('[data-filter-apply]').click();
  await filtered;
  await expect(table.locator('tbody tr')).toHaveCount(1);
  await expect(table.locator('tbody [data-table-column-key="dataset_id"]')).toHaveText('office');
  await page.locator('#leaderboard .export-menu > summary').click();
  const exported = page.waitForResponse(response => response.url().endsWith('/api/exports'));
  const downloaded = page.waitForEvent('download');
  await page.locator('#leaderboard [data-export-kind="xlsx"]').click();
  const response = await exported;
  expect(response.request().postDataJSON().query.sort).toBe('dataset');
  expect(response.request().postDataJSON().query.datasets).toEqual(['office']);
  expect(response.status()).toBe(200);
  expect((await downloaded).suggestedFilename()).toBe('peval-leaderboard.xlsx');
});
