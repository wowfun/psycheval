import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

for (const width of [1440, 390]) test(`table filters have local choices and one open menu at ${width}px`, async ({ page }, testInfo) => {
  const fixture = await startFixture({ PEVAL_E2E_TABLES: "1", PEVAL_E2E_COLLECTIONS: "1", PYTHONPATH: process.cwd() });
  try {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`${fixture.origin}/jobs`);
    const jobs = page.locator("[data-jobs-list]");
    await expect(jobs.locator("tbody tr")).toHaveCount(2);
    const name = jobs.locator('[data-filter-menu="name"]');
    const harness = jobs.locator('[data-filter-menu="harness"]');
    const status = jobs.locator('[data-filter-menu="status"]');
    const open = async menu => {
      await menu.locator("summary").evaluate(node => node.scrollIntoView({ block: "nearest", inline: "center" }));
      await menu.locator("summary").click();
      await expect(menu).toHaveAttribute("open", "");
    };
    const choices = menu => menu.locator("[data-filter-key]").evaluateAll(inputs => inputs.map(input => input.value).sort());
    await open(name);
    await open(harness);
    await expect(page.locator("[data-filter-menu][open]")).toHaveCount(1);
    expect(await choices(name)).toEqual(["ended", "running"]);
    expect(await choices(harness)).toEqual(["harbor"]);
    const localStatuses = (await jobs.locator('tbody [data-table-column-key="status"]').allTextContents()).sort();
    await open(status);
    expect(await choices(status)).toEqual(localStatuses);
    await open(name);
    await name.locator('input[value="ended"]').check();
    await open(harness);
    await open(name);
    await expect(name.locator('input[value="ended"]')).not.toBeChecked();
    await name.locator('input[value="ended"]').check();
    await name.locator("[data-filter-apply]").click();
    await expect(jobs.locator("tbody tr")).toHaveCount(1);
    await open(name);
    expect(await choices(name)).toEqual(["ended", "running"]);
    await expect(name.locator('input[value="ended"]')).toBeChecked();
    await name.locator("[data-filter-clear]").click();
    await name.locator("[data-filter-apply]").click();
    await expect(jobs.locator("tbody tr")).toHaveCount(2);
    await open(name);
    const taskDataset = page.locator('[data-job-tasks] [data-filter-menu="dataset"]');
    await open(taskDataset);
    await expect(name).not.toHaveAttribute("open", "");
    await expect(page.locator("[data-filter-menu][open]")).toHaveCount(1);
    expect(await choices(taskDataset)).toEqual(["editable", "other"]);
    await taskDataset.locator("input").first().focus();
    await page.keyboard.press("Escape");
    await expect(taskDataset).not.toHaveAttribute("open", "");
    await expect(taskDataset.locator("summary")).toBeFocused();

    // Loading Home must not replace local choices with catalog facets on return.
    await page.locator('nav [data-workspace-route="home"]').click();
    const homeAgent = page.locator('#leaderboard [data-filter-menu="agent"]');
    const homeJob = page.locator('#leaderboard [data-filter-menu="job_name"]');
    await open(homeAgent);
    await expect(homeAgent.locator("input")).not.toHaveCount(0);
    await open(homeJob);
    await expect(homeJob.locator("input")).not.toHaveCount(0);
    await expect(page.locator("[data-filter-menu][open]")).toHaveCount(1);
    await page.locator('nav [data-workspace-route="jobs"]').click();
    await open(status);
    expect(await choices(status)).toEqual(localStatuses);
    await expect(page.locator("[data-filter-menu][open]")).toHaveCount(1);
    await page.screenshot({ path: testInfo.outputPath(`jobs-filter-${width}.png`) });
    await page.locator('nav [data-workspace-route="datasets"]').click();
    const datasetStatus = page.locator('[data-harbor-overview] [data-filter-menu="status"]');
    await open(datasetStatus);
    await expect(datasetStatus.locator("input")).not.toHaveCount(0);
    expect(await choices(datasetStatus)).not.toContain("Run completed");
    await expect(page.locator("[data-filter-menu][open]")).toHaveCount(1);
  } finally { await stopFixture(fixture); }
});
