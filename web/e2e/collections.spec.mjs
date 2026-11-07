import { test, expect } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

for (const locale of ["en", "zh-CN"]) for (const role of ["admin", "guest"]) {
  test(`collections ${locale} ${role}: tables, notes, sidebars and responsive layout`, async ({ page }, testInfo) => {
    test.setTimeout(90_000);
    const fixture = await startFixture({ PEVAL_E2E_TABLES: "1", PEVAL_E2E_COLLECTIONS: "1",
      PEVAL_E2E_LOCALE: locale, ...(role === "guest" ? { PEVAL_E2E_PASSWORD: "secret" } : {}), PYTHONPATH: process.cwd() });
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    try {
      await page.setViewportSize({ width: 1440, height: 1000 });
      await page.goto(`${fixture.origin}/datasets`);
      const datasets = page.locator("[data-dataset-collections]");
      const tasks = page.locator("[data-harbor-overview]");
      const taskRows = tasks.locator("tbody tr");
      await expect(taskRows).toHaveCount(3);
      const editable = datasets.locator('[data-dataset-row="editable"]');
      await expect(editable.locator('[data-table-column-key="tasks"]')).toHaveText("2");
      if (role === "admin") {
        await editable.locator(".select-box").click();
        await expect(taskRows).toHaveCount(3);
        const note = editable.locator('[data-table-column-key="note"]');
        await note.dblclick();
        await note.locator("textarea").fill("# 中文备注\n\nSecond line");
        await note.getByRole("button", { name: locale === "en" ? "Save" : "保存", exact: true }).click();
        await expect(note.locator("textarea")).toHaveCount(0);
        const saved = await (await page.request.get(`${fixture.origin}/api/collections/datasets`)).json();
        expect(saved.datasets.find(row => row.id === "editable").note).toBe("# 中文备注\n\nSecond line");
        await note.focus(); await page.keyboard.press("Enter");
        await note.locator("textarea").fill("My conflicting draft");
        const remote = await page.request.put(`${fixture.origin}/api/collections/dataset/editable/note`, {
          data: { note: "Remote note", revision: saved.datasets.find(row => row.id === "editable").collection_revision },
        });
        expect(remote.ok()).toBe(true);
        await note.getByRole("button", { name: locale === "en" ? "Save" : "保存", exact: true }).click();
        await expect(note.locator(".table-cell-editor-status")).toContainText("Collection changed");
        await expect(note.locator("textarea")).toHaveValue("My conflicting draft");
        await note.getByRole("button", { name: locale === "en" ? "Cancel" : "取消", exact: true }).click();
      } else {
        await expect(datasets.locator('[data-table-column-key="path"], [data-table-column-key="mounts"], [data-table-row-select]')).toHaveCount(0);
        await expect(page.locator("[data-harbor-add-dataset]")).toHaveCount(0);
        await editable.locator('[data-table-column-key="note"]').dblclick();
        await expect(datasets.locator("textarea")).toHaveCount(0);
      }
      await editable.locator('[data-table-column-key="tasks"]').click();
      await expect(taskRows).toHaveCount(2);
      await datasets.locator("[data-dataset-clear]").click();
      await expect(taskRows).toHaveCount(3);
      const reports = editable.locator('[data-table-column-key="reports"] a');
      await reports.click();
      await expect(page).toHaveURL(/\/reports#view=/);
      const view = new URL(page.url()).hash.slice("#view=".length);
      expect(JSON.parse(Buffer.from(view, "base64url").toString()).query.datasets).toEqual(["editable"]);
      await expect(page.locator('[data-workspace-page="reports"]')).toBeVisible();
      await page.goBack();
      await expect(taskRows).toHaveCount(3);
      const first = taskRows.filter({ hasText: "org/first" });
      await first.locator('[data-table-column-key="status"]').click();
      const sidebar = page.locator('[data-sidebar-id="dataset-task"]');
      await expect(sidebar).toBeVisible();
      await expect(sidebar.locator("[data-harbor-editor]")).not.toHaveValue("");
      if (role === "admin") {
        const editor = sidebar.locator("[data-harbor-editor]");
        await sidebar.getByRole("button", { name: locale === "en" ? "Raw" : "原文", exact: true }).click();
        await editor.fill("Unsaved 中文 draft");
        page.once("dialog", dialog => dialog.dismiss());
        await taskRows.filter({ hasText: "org/second" }).locator('[data-table-column-key="status"]').click();
        await expect(editor).toHaveValue("Unsaved 中文 draft");
        await page.locator('nav [data-workspace-route="jobs"]').click();
        await page.locator('nav [data-workspace-route="datasets"]').click();
        await expect(sidebar).toBeVisible();
        await expect(editor).toHaveValue("Unsaved 中文 draft");
      } else {
        await expect(sidebar.locator("[data-harbor-editor]")).toHaveAttribute("readonly", "");
      }
      await expect(page.locator("[data-harbor-workbench-status]")).toBeHidden();
      await page.screenshot({ path: testInfo.outputPath(`datasets-${locale}-${role}-desktop.png`) });
      await page.setViewportSize({ width: 390, height: 844 });
      await expect(sidebar).toBeInViewport();
      const fileTree = sidebar.locator("[data-harbor-file-tree]");
      await expect(fileTree).toBeVisible();
      const filesBox = await fileTree.boundingBox();
      const editorBox = await sidebar.locator(".harbor-editor-head").boundingBox();
      expect(filesBox.y + filesBox.height).toBeLessThanOrEqual(editorBox.y + 1);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`datasets-${locale}-${role}-mobile.png`) });
      await sidebar.locator("[data-sidebar-close]").click();
      await expect(first).toBeFocused();
      await page.locator('nav [data-workspace-route="jobs"]').click();
      const jobs = page.locator("[data-jobs-list]");
      await expect(jobs.locator("tbody tr")).toHaveCount(2);
      if (role === "guest") {
        await expect(jobs.locator('[data-table-column-key="path"], [data-table-column-key="mounts"], [data-table-row-select]')).toHaveCount(0);
        await expect(page.locator("[data-jobs-mounts]")).toHaveCount(0);
      }
      const ended = jobs.locator("tbody tr").filter({ hasText: "ended" });
      await ended.locator('[data-table-column-key="trials"]').click();
      const jobDetail = page.locator('[data-sidebar-id="jobs-detail"]');
      await expect(jobDetail.locator(".job-result")).toHaveCount(1);
      await expect(jobDetail.locator("[data-job-stop]")).toHaveCount(0);
      const scoreBox = await jobDetail.locator(".job-result > span").boundingBox();
      const linkBox = await jobDetail.locator(".job-result > a").boundingBox();
      expect(Math.abs(scoreBox.y - linkBox.y)).toBeLessThan(2);
      await page.screenshot({ path: testInfo.outputPath(`jobs-${locale}-${role}-mobile.png`) });
      await page.setViewportSize({ width: 1440, height: 1000 });
      expect((await jobDetail.locator(".job-result > strong").boundingBox()).width).toBeGreaterThan(200);
      await jobDetail.locator("[data-sidebar-close]").click();
      // A checkbox edits the Run draft; opening Task details does not select it.
      const runTasks = page.locator("[data-job-tasks]");
      const check = runTasks.locator('[data-table-row-select="editable/first"]');
      await check.focus(); await page.keyboard.press("Space");
      await page.locator("[data-job-search]").fill("third");
      await expect(runTasks.locator("tbody tr")).toHaveCount(1);
      await runTasks.locator('[data-table-column-key="task"]').click();
      await expect(page.locator('[data-sidebar-id="jobs-task"]')).toBeVisible();
      await expect(runTasks.locator('[data-table-row-select="other/third"]')).not.toBeChecked();
      await page.locator('[data-sidebar-id="jobs-task"] [data-sidebar-close]').click();
      await page.locator("[data-job-search]").fill("");
      await expect(check).toBeChecked();
      if (role === "admin") {
        await page.locator("[data-jobs-mounts]").click();
        await expect(page.locator("[data-harbor-mount-config]")).toContainText("collections");
        await page.locator(".registry-manager-panel [data-close]").click();
        const before = (await (await page.request.get(`${fixture.origin}/api/catalog`)).json()).total;
        await ended.locator(".select-box").click();
        await page.locator("[data-jobs-archive-selected]").click();
        await expect(jobs.locator("tbody tr")).toHaveCount(1);
        expect((await (await page.request.get(`${fixture.origin}/api/catalog`)).json()).total).toBe(before - 1);
        await page.locator("[data-jobs-show-archived]").check();
        await expect(jobs.locator("tbody tr")).toHaveCount(2);
        await ended.locator(".select-box").click();
        await page.locator("[data-jobs-restore-selected]").click();
        await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/catalog`)).json()).total).toBe(before);
      }
      await page.screenshot({ path: testInfo.outputPath(`jobs-${locale}-${role}-desktop.png`) });
      expect(errors).toEqual([]);
    } finally { await stopFixture(fixture); }
  });
}
