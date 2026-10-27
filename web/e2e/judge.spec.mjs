import { test, expect } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

test("Chinese judge comparison translates known verdicts and preserves unknown retained statuses", async ({ page }, testInfo) => {
  const fixture = await startFixture({ PEVAL_E2E_JUDGE: "1", PEVAL_E2E_LOCALE: "zh-CN", PYTHONPATH: process.cwd() });
  try {
    await page.goto(fixture.origin);
    const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
    const trial = catalog.items.find(item => item.task_name === "judge-fixture");
    const statuses = ["pass", "fail", "error", "unassessed", "external-review"];
    await page.route(`**/api/judge/${trial.source_key}/run`, route => route.fulfill({ json: {
      state: "incomplete", profile: "fixture", selected_ids: [...statuses, "missing"],
      baseline: statuses.map(status => ({ id: status, status, reason: `原始理由：${status}` })),
      checks: [{ id: "pass", passed: true, reason: "证据充分" }, { id: "fail", passed: false, reason: "证据不足" }],
      errors: { error: "服务不可用" }, reason: "未完成评估", diagnostics: {},
    } }));
    await page.locator(`.trajectory-row[data-source-key="${trial.source_key}"] .trajectory-label`).click();
    await page.getByRole('button', { name: '试跑 Rubric', exact: true }).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('button', { name: '运行选中 Rubric', exact: true }).click();
    await expect(dialog.locator('[data-judge-result="baseline"] .judge-result-verdict')).toHaveText(["通过", "失败", "错误", "未评估", "external-review", "无基准结果"]);
    await expect(dialog.locator('[data-judge-result="current"] .judge-result-verdict')).toHaveText(["通过", "失败", "未评估", "未评估", "未评估", "未评估"]);
    await expect(dialog.getByRole('region', { name: '本次结果', exact: true }).nth(2)).toContainText('服务不可用');
    await expect(dialog.getByRole('region', { name: '基准结果', exact: true }).nth(2)).toContainText('原始理由：error');
    await dialog.screenshot({ path: testInfo.outputPath('verdicts-zh-CN.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    expect(await dialog.locator('.judge-body').evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true);
    await dialog.screenshot({ path: testInfo.outputPath('verdicts-zh-CN-mobile.png') });
  } finally { await stopFixture(fixture); }
});

test("session drafts, latest results, navigation, cancellation and profile settings", async ({ page }, testInfo) => {
  test.setTimeout(60_000);
  const fixture = await startFixture({ PEVAL_E2E_JUDGE: "1", PYTHONPATH: process.cwd() });
  try {
    await page.goto(fixture.origin);
    const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
    const trial = catalog.items.find(item => item.task_name === "judge-fixture");
    const other = catalog.items.find(item => item.task_name === "judge-other");
    const openTrial = async key => {
      await page.locator(`.trajectory-row[data-source-key="${key}"] .trajectory-label`).click();
      await expect(page.getByRole('button', { name: 'Try rubrics', exact: true })).toBeVisible();
    };
    await page.locator(`.trajectory-row[data-source-key="${trial.source_key}"]`).click();
    const verdict = page.locator('.verification-verdict').filter({ hasText: 'llm:fidelity' });
    const selected = verdict.locator('summary').getByRole('checkbox', { name: 'Select fidelity', exact: true });
    await selected.check();
    await expect(verdict).not.toHaveAttribute('open', '');
    await expect(verdict.locator('.judge-actions').getByRole('checkbox')).toHaveCount(0);
    await verdict.locator('summary').getByText('llm:fidelity', { exact: true }).click();
    await expect(selected).toBeChecked();
    await verdict.screenshot({ path: testInfo.outputPath('rubric-selection.png') });
    await verdict.getByRole('button', { name: 'Actual prompt', exact: true }).click();
    let dialog = page.getByRole('dialog');
    await expect(dialog).toContainText('Recorded request');
    await expect(dialog).toContainText('Faithful evidence.');
    await expect(dialog.locator('textarea')).toHaveCount(0);
    await dialog.screenshot({ path: testInfo.outputPath('recorded-prompt.png') });
    await dialog.getByRole('button', { name: 'Create draft', exact: true }).click();
    dialog = page.getByRole('dialog');
    await dialog.getByLabel('Question', { exact: true }).fill('Does the answer preserve the retained evidence?');
    await dialog.getByRole('button', { name: 'Preview prompt', exact: true }).click();
    await expect(dialog).toContainText('Unsent preview');
    await expect(dialog.locator('.judge-preview')).toContainText('Does the answer preserve the retained evidence?');
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    await page.route(`**/api/judge/${trial.source_key}/run`, async route => {
      const response = await route.fetch();
      await gate;
      await route.fulfill({ response });
    }, { times: 1 });
    await dialog.getByRole('button', { name: 'Run selected rubrics', exact: true }).click();
    await expect(dialog.locator('.judge-status')).toContainText('Running');
    await dialog.getByRole('button', { name: 'Close', exact: true }).click();
    await page.getByRole('button', { name: 'Try rubrics', exact: true }).click();
    await expect(page.getByRole('dialog').locator('.judge-status')).toContainText('Running');
    await page.getByRole('dialog').getByRole('button', { name: 'Close', exact: true }).click();
    await openTrial(other.source_key);
    await page.getByRole('button', { name: 'Try rubrics', exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText('Another Trial is running');
    await expect(page.getByRole('dialog').getByRole('button', { name: 'Run selected rubrics', exact: true })).toBeDisabled();
    release();
    await expect(page.getByRole('dialog').getByRole('button', { name: 'Run selected rubrics', exact: true })).toBeEnabled();
    await expect(page.getByRole('dialog').locator('.judge-result')).toHaveCount(0);
    await page.getByRole('dialog').getByRole('button', { name: 'Close', exact: true }).click();
    await openTrial(trial.source_key);
    await page.getByRole('button', { name: 'Try rubrics', exact: true }).click();
    await expect(page.getByRole('dialog').locator('[data-judge-result="baseline"] .judge-result-verdict')).toHaveText('Passed');
    await expect(page.getByRole('dialog').locator('[data-judge-result="current"] .judge-result-verdict')).toHaveText('Passed');
    const baseline = await page.getByRole('dialog').getByRole('region', { name: 'Baseline result', exact: true }).boundingBox();
    const current = await page.getByRole('dialog').getByRole('region', { name: 'Current result', exact: true }).boundingBox();
    expect(current.x).toBeGreaterThanOrEqual(baseline.x + baseline.width);
    expect(Math.abs(current.y - baseline.y)).toBeLessThan(1);
    await expect(page.getByRole('dialog').getByRole('button', { name: 'Cancel', exact: true })).toBeHidden();
    await expect(page.getByRole('dialog').getByLabel('Question', { exact: true })).toHaveValue('Does the answer preserve the retained evidence?');
    await page.getByRole('dialog').screenshot({ path: testInfo.outputPath('latest-result.png') });
    await page.getByRole('dialog').getByRole('button', { name: 'Close', exact: true }).click();
    await page.getByRole('link', { name: 'Configuration', exact: true }).click();
    await expect(page.locator('[data-judge-profiles]')).toContainText('fixture');
    await page.locator('[data-judge-profiles]').getByRole('button', { name: 'Edit', exact: true }).click();
    await page.getByRole('dialog').getByLabel('Name', { exact: true }).fill('Reviewed fixture');
    await page.getByRole('dialog').getByRole('button', { name: 'Save', exact: true }).click();
    await expect(page.locator('[data-judge-profiles]')).toContainText('Reviewed fixture');
    await page.getByRole('link', { name: 'Home', exact: true }).click();
    await openTrial(trial.source_key);
    await page.getByRole('button', { name: 'Try rubrics', exact: true }).click();
    await expect(page.getByRole('dialog').locator('[data-judge-result="baseline"] .judge-result-verdict')).toHaveText('Passed');
    await expect(page.getByRole('dialog').locator('[data-judge-result="current"] .judge-result-verdict')).toHaveText('Passed');
    await expect(page.getByRole('dialog').getByLabel('Question', { exact: true })).toHaveValue('Does the answer preserve the retained evidence?');
    await page.getByRole('dialog').getByRole('button', { name: 'Run selected rubrics', exact: true }).click();
    await expect(page.getByRole('dialog').locator('.judge-status')).toContainText('Complete');
    await expect(page.getByRole('dialog').locator('.judge-result')).toHaveCount(1);
    await page.getByRole('dialog').locator('.judge-result summary').click();
    await expect(page.getByRole('dialog').locator('.judge-result')).toContainText('Does the answer preserve the retained evidence?');
    const downloaded = page.waitForEvent('download');
    await page.getByRole('dialog').locator('.judge-result').getByRole('button', { name: 'Download', exact: true }).click();
    const download = await downloaded;
    expect(download.suggestedFilename()).toBe('judge-prompt.json');
    const { readFile } = await import('node:fs/promises');
    const exported = JSON.parse(await readFile(await download.path(), 'utf8'));
    expect(exported.id).toBe('fidelity');
    expect(exported.messages[0].content).toContain('Does the answer preserve the retained evidence?');
    await page.setViewportSize({ width: 390, height: 844 });
    const mobileBaseline = await page.getByRole('dialog').getByRole('region', { name: 'Baseline result', exact: true }).boundingBox();
    const mobileCurrent = await page.getByRole('dialog').getByRole('region', { name: 'Current result', exact: true }).boundingBox();
    expect(mobileCurrent.y).toBeGreaterThanOrEqual(mobileBaseline.y + mobileBaseline.height);
    expect(Math.abs(mobileCurrent.x - mobileBaseline.x)).toBeLessThan(1);
    expect(await page.locator('.judge-body').evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true);
    await page.getByRole('dialog').screenshot({ path: testInfo.outputPath('latest-result-mobile.png') });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const bounds = await page.locator('.judge-dialog').boundingBox();
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(390);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.reload();
    await openTrial(trial.source_key);
    await page.getByRole('button', { name: 'Try rubrics', exact: true }).click();
    await expect(page.getByRole('dialog').locator('.judge-result')).toHaveCount(0);
    await expect(page.getByRole('dialog').getByLabel('Question', { exact: true })).not.toHaveValue('Does the answer preserve the retained evidence?');
    let cancelRelease;
    const cancelGate = new Promise(resolve => { cancelRelease = resolve; });
    await page.route(`**/api/judge/${trial.source_key}/run`, async route => {
      await cancelGate;
      await route.abort();
    }, { times: 1 });
    await page.getByRole('dialog').getByRole('button', { name: 'Run selected rubrics', exact: true }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(page.getByRole('dialog').locator('.judge-status')).toContainText('Cancelled');
    cancelRelease();
    await expect(page.getByRole('dialog').locator('.judge-result')).toHaveCount(0);
  } finally { await stopFixture(fixture); }
});
