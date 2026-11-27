import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test, expect } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

async function readRevealLog(logPath) {
  try {
    const text = await readFile(logPath, "utf8");
    return text.trim().split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line).path.replace(/\\/g, "/"));
  } catch {
    return [];
  }
}

for (const locale of ["en", "zh-CN"]) {
  test(`Localhost admin reveals Trial Verification and Task files in file manager (${locale})`, async ({ page }, testInfo) => {
    test.setTimeout(90_000);
    const scratch = await mkdtemp(join(tmpdir(), "peval-reveal-e2e-"));
    const revealLog = join(scratch, "reveals.jsonl");
    const fixture = await startFixture({
      PEVAL_E2E_VERIFICATION: "1",
      PEVAL_E2E_LOCALE: locale,
      PEVAL_E2E_REVEAL_LOG: revealLog,
      PYTHONPATH: process.cwd(),
    });
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    const expectedLabel = locale === "en" ? "Reveal in file manager" : "在文件管理器中显示";
    try {
      await page.goto(fixture.origin);
      const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
      const trial = catalog.items.find(row => row.task_name === "workbuddy/office-one");
      await page.locator(`.trajectory-row[data-source-key="${trial.source_key}"]`).click();

      // 1. Trial right sidebar -> Verification tab
      const sidebar = page.locator("#detail-sidebar");
      const verification = sidebar.locator('[data-trial-panel="verification"]');
      await expect(verification).toBeVisible();
      const verReveal = verification.locator("[data-file-reveal]");
      await expect(verReveal).toBeVisible();
      await expect(verReveal).toHaveText(expectedLabel);
      await verReveal.click();
      await expect.poll(async () => (await readRevealLog(revealLog)).length).toBe(1);
      expect((await readRevealLog(revealLog))[0]).toMatch(/\/verifier\/score\.json$/);
      await page.screenshot({ path: testInfo.outputPath(`reveal-trial-verification-${locale}-desktop.png`) });

      await page.setViewportSize({ width: 390, height: 900 });
      expect(await verification.evaluate(node => node.scrollWidth > node.clientWidth)).toBe(false);
      await page.setViewportSize({ width: 1440, height: 900 });

      // 2. Trial right sidebar -> Task tab
      await sidebar.locator('[data-trial-tab="task"]').click();
      const trialTask = sidebar.locator('[data-trial-panel="task"]');
      const trialTaskReveal = trialTask.locator("[data-file-reveal]");
      await expect(trialTaskReveal).toBeVisible();
      await expect(trialTaskReveal).toHaveText(expectedLabel);
      await trialTaskReveal.click();
      await expect.poll(async () => (await readRevealLog(revealLog)).length).toBe(2);
      expect((await readRevealLog(revealLog))[1]).toMatch(/\/office-one\/instruction\.md$/);

      // 3. Datasets -> Task right sidebar
      await page.goto(`${fixture.origin}/datasets`);
      const datasets = page.locator("[data-harbor-workbench]");
      const officeRow = datasets.locator("tbody tr").filter({
        has: page.locator('td[data-table-column-key="task"]', { hasText: /^office-one$/ }),
      });
      await officeRow.locator('td[data-table-column-key="task"]').click();
      const taskSidebar = page.locator('[data-sidebar-id="dataset-task"]');
      const taskReveal = taskSidebar.locator("[data-file-reveal]");
      await expect(taskReveal).toBeVisible();
      await expect(taskReveal).toHaveText(expectedLabel);
      await taskReveal.click();
      await expect.poll(async () => (await readRevealLog(revealLog)).length).toBe(3);
      expect((await readRevealLog(revealLog))[2]).toMatch(/\/office-one\/instruction\.md$/);
      await page.screenshot({ path: testInfo.outputPath(`reveal-datasets-task-${locale}-desktop.png`) });

      await page.setViewportSize({ width: 390, height: 844 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`reveal-datasets-task-${locale}-mobile.png`) });
      await page.setViewportSize({ width: 1440, height: 900 });

      // 4. Forwarded (proxied / non-direct-localhost) request is rejected with 403.
      const forwarded = await page.request.post(
        `${fixture.origin}/api/harbor/datasets/office/tasks/office-one/reveal`,
        {
          headers: { Origin: fixture.origin, "X-Forwarded-For": "203.0.113.42" },
          data: { path: "instruction.md" },
        },
      );
      expect(forwarded.status()).toBe(403);
      expect((await readRevealLog(revealLog)).length).toBe(3);
      expect(errors).toEqual([]);
    } finally {
      await stopFixture(fixture);
      await rm(scratch, { recursive: true, force: true });
    }
  });
}

test("Guest on localhost sees no reveal button and receives 403 from reveal APIs", async ({ page }) => {
  test.setTimeout(90_000);
  const scratch = await mkdtemp(join(tmpdir(), "peval-reveal-guest-"));
  const revealLog = join(scratch, "reveals.jsonl");
  const fixture = await startFixture({
    PEVAL_E2E_VERIFICATION: "1",
    PEVAL_E2E_PASSWORD: "fixture-secret",
    PEVAL_E2E_REVEAL_LOG: revealLog,
    PYTHONPATH: process.cwd(),
  });
  try {
    await page.goto(fixture.origin);
    const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
    const trial = catalog.items.find(row => row.task_name === "workbuddy/office-one");
    await page.locator(`.trajectory-row[data-source-key="${trial.source_key}"]`).click();

    const sidebar = page.locator("#detail-sidebar");
    await expect(sidebar.locator('[data-trial-panel="verification"]')).toBeVisible();
    await expect(sidebar.locator('[data-trial-panel="verification"] [data-file-reveal]')).toHaveCount(0);

    await sidebar.locator('[data-trial-tab="task"]').click();
    await expect(sidebar.locator('[data-trial-panel="task"] [data-harbor-editor-path]')).toHaveText("instruction.md");
    await expect(sidebar.locator('[data-trial-panel="task"] [data-file-reveal]')).toHaveCount(0);

    await page.goto(`${fixture.origin}/datasets`);
    const datasets = page.locator("[data-harbor-workbench]");
    const officeRow = datasets.locator("tbody tr").filter({
      has: page.locator('td[data-table-column-key="task"]', { hasText: /^office-one$/ }),
    });
    await officeRow.locator('td[data-table-column-key="task"]').click();
    const taskSidebar = page.locator('[data-sidebar-id="dataset-task"]');
    await expect(taskSidebar.locator("[data-harbor-editor-path]")).toHaveText("instruction.md");
    await expect(taskSidebar.locator("[data-file-reveal]")).toHaveCount(0);

    const tree = await (await page.request.get(`${fixture.origin}/api/verification-files/${encodeURIComponent(trial.source_key)}`)).json();
    const score = tree.tree.find(item => item.path === "verifier/score.json");
    const verResp = await page.request.post(
      `${fixture.origin}/api/verification-files/${encodeURIComponent(trial.source_key)}/${score.id}/reveal`,
      { headers: { Origin: fixture.origin }, data: {} },
    );
    expect(verResp.status()).toBe(403);

    const taskResp = await page.request.post(
      `${fixture.origin}/api/harbor/datasets/office/tasks/office-one/reveal`,
      { headers: { Origin: fixture.origin }, data: { path: "instruction.md" } },
    );
    expect(taskResp.status()).toBe(403);
    expect(await readRevealLog(revealLog)).toEqual([]);
  } finally {
    await stopFixture(fixture);
    await rm(scratch, { recursive: true, force: true });
  }
});
