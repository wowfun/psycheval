import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.beforeAll(async () => {
  fixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PEVAL_E2E_TABLES: "1", PYTHONPATH: process.cwd() });
});
test.afterAll(async () => { await stopFixture(fixture); });

test("Home editable cells activate the row on click and edit on double click", async ({ page }) => {
  await page.goto(fixture.origin);
  await expect(page.locator("[data-notes-edit]")).toBeVisible();
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
  const workbench = page.locator("[data-harbor-workbench]");
  await expect(workbench).toHaveAttribute("aria-busy", "false");
  const first = page.locator('[data-task-row-key="dataset:editable|task:first"]');
  await first.locator('[data-table-column-key="task"]').click();
  await expect(first).toHaveClass(/selected-row/);
  await expect(workbench).toHaveAttribute("aria-busy", "false");
  const row = page.locator('[data-task-row-key="dataset:editable|task:second"]');
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
  await expect(page.locator("[data-notes-edit]")).toBeVisible();
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

for (const width of [1440, 390]) test(`filter actions stay fixed while options scroll at ${width}px`, async ({ page }, testInfo) => {
  const longFixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PEVAL_E2E_LONG_TABLE: "1" });
  try {
    await page.setViewportSize({ width, height: 900 });
    // Expand only facet choices; real fixture Jobs still exercise apply and clear.
    await page.route('**/api/catalog?*', async route => {
      const response = await route.fetch();
      const payload = await response.json();
      payload.facets.jobs = [
        ...Array.from({ length: 40 }, (_, i) => ({ value: `000-long-filter-job-${String(i).padStart(2, '0')}`, count: 1 })),
        ...payload.facets.jobs,
      ];
      await route.fulfill({ response, json: payload });
    });
    await page.goto(longFixture.origin);
    const menu = page.locator('#leaderboard [data-filter-menu="job_name"]');
    // Center the column in the horizontally scrollable narrow table before opening.
    if (width < 700) await menu.locator('summary').evaluate(node => node.scrollIntoView({ block: 'nearest', inline: 'center' }));
    await menu.locator('summary').click();
    const options = menu.locator('.filter-options');
    const inputs = options.locator('input');
    const clear = menu.locator('[data-filter-clear]');
    const apply = menu.locator('[data-filter-apply]');
    const before = await clear.boundingBox();
    const listBox = await options.boundingBox();
    await page.mouse.move(listBox.x + listBox.width / 2, listBox.y + 10);
    await page.mouse.wheel(0, 10000);
    await expect.poll(() => options.evaluate(node => node.scrollTop)).toBeGreaterThan(0);
    const last = inputs.last();
    const chosen = await last.inputValue();
    expect(chosen).not.toMatch(/^000-long-filter-job-/);
    await expect(last).toBeInViewport();
    const after = await clear.boundingBox();
    expect(after.y).toBeCloseTo(before.y, 1);
    await expect(clear).toBeInViewport();
    await expect(apply).toBeInViewport();
    await last.check();
    await inputs.first().focus();
    await page.keyboard.press('Shift+Tab');
    await expect(apply).toBeFocused();
    await page.keyboard.press('Shift+Tab');
    await expect(clear).toBeFocused();
    await page.keyboard.press('Space');
    await expect(options.locator('input:checked')).toHaveCount(0);
    await inputs.first().focus();
    for (let i = 1; i < await inputs.count(); i++) await page.keyboard.press('Tab');
    await expect(last).toBeFocused();
    await expect(last).toBeInViewport();
    expect((await clear.boundingBox()).y).toBeCloseTo(before.y, 1);
    await page.screenshot({ path: testInfo.outputPath(`filter-actions-${width}.png`) });
    await page.keyboard.press('Space');
    const filtered = page.waitForRequest(request => request.url().includes('/api/catalog?') && new URL(request.url()).searchParams.get('job') === chosen);
    await apply.click();
    await filtered;
    await expect(page.locator('#leaderboard tbody [data-table-column-key="job_name"]').first()).toHaveText(chosen);
    await menu.locator('summary').click();
    await clear.click();
    const restored = page.waitForRequest(request => request.url().includes('/api/catalog?') && !new URL(request.url()).searchParams.has('job'));
    await apply.click();
    await restored;
    await menu.locator('summary').click();
    await expect(options.locator('input:checked')).toHaveCount(0);
  } finally { await stopFixture(longFixture); }
});
