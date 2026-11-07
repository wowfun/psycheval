import {expect,test} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {startFixture,stopFixture} from './fixture-process.mjs';
import {encodeWorkspaceLocation} from '../../src/psycheval/assets/web/app/workspace-location.js';

for(const locale of ['en','zh-CN']) test(`metric provenance explains mixed and missing values in ${locale}`,async({page},testInfo)=>{
  const fixture=await startFixture({PEVAL_E2E_PROVENANCE:'1',PEVAL_E2E_LOCALE:locale});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  try {
    await page.goto(encodeWorkspaceLocation('home',{state:{summary:{group_by:'overall',metrics:['tool_success_rate','tps','tokens']}}},fixture.origin));
    await page.locator('[data-summary-table-toggle]').click();
    const mixed=page.locator('[data-summary-stat="mean"]').first();
    await expect(mixed).toHaveAttribute('title',/successes\/known/);
    await expect(mixed).toHaveAttribute('title',/\(calls-errors\)\/calls/);
    await expect(mixed).not.toHaveAttribute('aria-label',/successes|Contract|契约/);
    for(const width of [1440,390]) {
      await page.setViewportSize({width,height:900});
      await page.locator('.summary-metric-control > summary').click();
      const missing=page.locator('[data-metric-row="tps"]');
      const input=missing.locator('input');
      await expect(input).toHaveAccessibleDescription(/retry|重试/);
      await expect(input).toHaveAccessibleDescription(/native|原生/i);
      await input.focus();
      await expect(input).toBeFocused();
      const labelBox=await missing.locator('label span').boundingBox();
      expect(labelBox.width).toBeGreaterThan(50);
      expect(labelBox.height).toBeLessThan(45);
      const box=await page.locator('.summary-metric-control .column-control-panel').boundingBox();
      expect(box.x).toBeGreaterThanOrEqual(0);expect(box.x+box.width).toBeLessThanOrEqual(width);
      await page.screenshot({path:testInfo.outputPath(`provenance-${locale}-${width}.png`)});
      await page.keyboard.press('Escape');
    }
    const titles=await page.locator('tbody [data-table-column-key="tool_success_rate"]').evaluateAll(nodes=>nodes.map(node=>node.title));
    expect(titles.join('\n')).toMatch(/successes\/known/);
    expect(errors).toEqual([]);
  } finally {await stopFixture(fixture);}
});

test('JSON download uses the server schema filename and retains provenance',async({page},testInfo)=>{
  const fixture=await startFixture({PEVAL_E2E_PROVENANCE:'1'});
  try {
    await page.goto(fixture.origin);
    await expect(page.locator('#leaderboard tbody tr')).toHaveCount(2);
    await page.locator('#leaderboard .export-menu > summary').click();
    const pending=page.waitForEvent('download');
    await page.locator('#leaderboard [data-export-kind="json"]').click();
    const download=await pending;
    const path=testInfo.outputPath(download.suggestedFilename());
    await download.saveAs(path);
    const report=JSON.parse(await readFile(path,'utf8'));
    expect(download.suggestedFilename()).toBe(`peval-report-v${report.schema_version}.json`);
    expect(report.schema_version).toBe(21);
    expect(report.trajectory_meta).toHaveLength(2);
    expect(report.trajectory_meta.every(meta=>Object.keys(meta.metric_provenance).length===12)).toBe(true);
  } finally {await stopFixture(fixture);}
});
