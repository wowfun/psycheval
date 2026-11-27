import { readFile } from "node:fs/promises";
import { test, expect } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

for (const locale of ["en", "zh-CN"]) {
  test(`Tasks custom columns (${locale}): create, persist to task.toml, reload, filter, summary, export, delete`, async ({ page }, testInfo) => {
    test.setTimeout(90_000);
    const fixture = await startFixture({
      PEVAL_E2E_TASK_SCORING: "1",
      PEVAL_E2E_LOCALE: locale,
      PYTHONPATH: process.cwd(),
    });
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    try {
      await page.goto(`${fixture.origin}/datasets`);
      const table = page.locator("[data-harbor-overview]");
      const rows = table.locator("tbody tr");
      const row = name => rows.filter({ has: page.locator('td[data-table-column-key="task"]', { hasText: new RegExp(`^${name}$`) }) });
      const cell = (name, key) => row(name).locator(`td[data-table-column-key="${key}"]`);
      const summary = page.locator("[data-task-summary]");
      const sidebar = page.locator('[data-sidebar-id="dataset-task"]');
      const columnsHost = page.locator("[data-task-columns-control]");

      await expect(rows).toHaveCount(3);

      // 1. Create an Enum column "qa_status" with empty default via Tasks Columns control.
      await columnsHost.locator(".column-control > summary").click();
      await columnsHost.locator("[data-column-header-action]").click();
      const modal = page.locator('[data-custom-column-form="create"]');
      await expect(modal).toBeVisible();
      await modal.locator('input[name="key"]').fill("qa_status");
      await modal.locator('select[name="type"]').selectOption("enum");
      await modal.locator('textarea[name="options"]').fill("OK\nPOK\nNOK");
      await modal.locator('button[type="submit"]').click();
      await expect(modal).toHaveCount(0);

      await expect(table.locator('th[data-table-column="meta:qa_status"]')).toBeVisible();
      await expect(cell("scored", "meta:qa_status")).toHaveText("");

      // 2. Inline-edit native Task cell -> persists to task.toml; WorkBuddy cell stays read-only.
      await cell("office-one", "meta:qa_status").dblclick();
      await expect(cell("office-one", "meta:qa_status").locator(".table-cell-editor-control")).toHaveCount(0);

      await cell("scored", "meta:qa_status").dblclick();
      const select = cell("scored", "meta:qa_status").locator("select.table-cell-editor-control");
      await expect(select).toBeVisible();
      await select.selectOption("OK");
      await select.press("Enter");
      await expect(cell("scored", "meta:qa_status")).toHaveText("OK");

      // Single-click custom column cell opens task.toml showing persisted [metadata].qa_status = "OK".
      await cell("scored", "meta:qa_status").click();
      await expect(sidebar.locator("[data-harbor-editor-path]")).toHaveText("task.toml");
      await expect(sidebar.locator("[data-harbor-editor]")).toHaveValue(/qa_status\s*=\s*"OK"/);
      await sidebar.locator("[data-sidebar-close]").click();

      // 3. Create a Number column "priority" with default value 2 -> batch-writes native tasks only.
      await columnsHost.locator(".column-control > summary").click();
      await columnsHost.locator("[data-column-header-action]").click();
      const numModal = page.locator('[data-custom-column-form="create"]');
      await numModal.locator('input[name="key"]').fill("priority");
      await numModal.locator('select[name="type"]').selectOption("number");
      await numModal.locator('input[name="default_value"]').fill("2");
      await expect(numModal.locator("[data-custom-readonly-hint]")).toBeVisible();
      await numModal.locator('button[type="submit"]').click();
      await expect(numModal).toHaveCount(0);
      await expect(cell("scored", "meta:priority")).toHaveText("2");
      await expect(cell("empty", "meta:priority")).toHaveText("2");
      await expect(cell("office-one", "meta:priority")).toHaveText("");

      // 4. Reload page -> values read from task.toml AND enum dropdown schema preserved.
      await page.reload();
      await expect(cell("scored", "meta:qa_status")).toHaveText("OK");
      await expect(cell("scored", "meta:priority")).toHaveText("2");
      await cell("empty", "meta:qa_status").dblclick();
      const reloadedSelect = cell("empty", "meta:qa_status").locator("select.table-cell-editor-control");
      await expect(reloadedSelect.locator("option")).toHaveText([locale === "en" ? "Unset" : "未设置", "OK", "POK", "NOK"]);
      await reloadedSelect.selectOption("POK");
      await reloadedSelect.press("Enter");
      await expect(cell("empty", "meta:qa_status")).toHaveText("POK");

      // 5. Filter by custom column, group in Task Summary, and export JSON + Excel.
      const qaFilter = table.locator('[data-filter-menu="meta:qa_status"]');
      await qaFilter.locator("summary").click();
      await qaFilter.locator('input[value="OK"]').check();
      await qaFilter.locator("[data-filter-apply]").click();
      await expect(rows).toHaveCount(1);
      await expect(cell("scored", "meta:qa_status")).toHaveText("OK");
      await qaFilter.locator("summary").click();
      await qaFilter.locator("[data-filter-clear]").click();
      await qaFilter.locator("[data-filter-apply]").click();
      await expect(rows).toHaveCount(3);

      await summary.locator('[data-task-summary-group="meta:qa_status"]').click();
      await summary.locator("[data-task-summary-toggle]").click();
      await expect(summary.locator('td[data-table-column-key="group"]')).toHaveText(["POK", "OK", locale === "en" ? "Unset" : "未设置"]);

      await page.locator("[data-task-scoring-actions] summary").click();
      const jsonDownload = page.waitForEvent("download");
      await page.locator('[data-task-export="json"]').click();
      const exported = JSON.parse(await readFile(await (await jsonDownload).path(), "utf8"));
      expect(exported.find(item => item.task === "scored")["meta:qa_status"]).toBe("OK");
      expect(exported.find(item => item.task === "scored")["meta:priority"]).toBe(2);

      await page.locator("[data-task-scoring-actions] summary").click();
      const xlsxDownload = page.waitForEvent("download");
      await page.locator('[data-task-export="xlsx"]').click();
      expect((await readFile(await (await xlsxDownload).path())).subarray(0, 2).toString()).toBe("PK");

      // 6. Responsive mobile check.
      await page.screenshot({ path: testInfo.outputPath(`custom-columns-${locale}-desktop.png`) });
      await page.setViewportSize({ width: 390, height: 844 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`custom-columns-${locale}-mobile.png`) });
      await page.setViewportSize({ width: 1440, height: 900 });

      // 7. Delete custom column "priority" from Columns control -> removes from task.toml.
      page.once("dialog", dialog => dialog.accept());
      await columnsHost.locator(".column-control > summary").click();
      await columnsHost.locator('[data-column-action="delete"][data-column-action-target="meta:priority"]').click();
      await expect(table.locator('th[data-table-column="meta:priority"]')).toHaveCount(0);
      await page.reload();
      await expect(table.locator('th[data-table-column="meta:priority"]')).toHaveCount(0);

      expect(errors).toEqual([]);
    } finally {
      await stopFixture(fixture);
    }
  });
}

test("Tasks custom columns (guest): auto-discovers persisted values read-only without edit or creation controls", async ({ page, browser }) => {
  test.setTimeout(90_000);
  const fixture = await startFixture({
    PEVAL_E2E_TASK_SCORING: "1",
    PEVAL_E2E_PASSWORD: "secret",
    PYTHONPATH: process.cwd(),
  });
  let guestContext;
  try {
    const headers = { Origin: fixture.origin };
    const login = await page.request.post(`${fixture.origin}/api/session`, {
      headers,
      data: { password: "secret" },
    });
    expect(login.ok()).toBeTruthy();

    // Wait for inventory, then persist two custom metadata keys as admin.
    await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/collections/datasets/status`)).json()).checking).toBe(false);
    const inv = await (await page.request.get(`${fixture.origin}/api/collections/datasets`)).json();
    const scored = inv.datasets.find(ds => ds.id === "native").tasks.find(t => t.directory === "scored");
    const patch1 = await page.request.patch(`${fixture.origin}/api/harbor/datasets/native/tasks/scored/metadata`, {
      headers: { ...headers, "If-Match": `"${scored.revision}"` },
      data: { key: "qa_status", value: "OK" },
    });
    expect(patch1.status()).toBe(202);
    const op1 = await patch1.json();
    await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/operations/${op1.id}`)).json()).state).toBe("succeeded");

    const patch2 = await page.request.patch(`${fixture.origin}/api/harbor/datasets/native/tasks/scored/metadata`, {
      headers: { ...headers, "If-Match": patch1.headers().etag },
      data: { key: "priority", value: 2 },
    });
    expect(patch2.status()).toBe(202);
    const op2 = await patch2.json();
    await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/operations/${op2.id}`)).json()).state).toBe("succeeded");
    await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/collections/datasets/status`)).json()).checking).toBe(false);

    // Open unauthenticated guest context.
    guestContext = await browser.newContext();
    const guest = await guestContext.newPage();
    const errors = [];
    guest.on("pageerror", error => errors.push(error.message));

    await guest.goto(`${fixture.origin}/datasets`);
    const table = guest.locator("[data-harbor-overview]");
    const rows = table.locator("tbody tr");
    const row = name => rows.filter({ has: guest.locator('td[data-table-column-key="task"]', { hasText: new RegExp(`^${name}$`) }) });
    const cell = (name, key) => row(name).locator(`td[data-table-column-key="${key}"]`);
    const columnsHost = guest.locator("[data-task-columns-control]");
    const summary = guest.locator("[data-task-summary]");

    await expect(rows).toHaveCount(3);
    await expect(cell("scored", "meta:qa_status")).toHaveText("OK");
    await expect(cell("scored", "meta:priority")).toHaveText("2");

    // Read-only: no create/edit/delete controls and no inline editor on dblclick.
    await expect(guest.locator("[data-harbor-add-column]")).toHaveCount(0);
    await columnsHost.locator(".column-control > summary").click();
    await expect(columnsHost.locator("[data-column-header-action]")).toHaveCount(0);
    await expect(columnsHost.locator("[data-column-action]")).toHaveCount(0);
    // Guest CAN toggle visibility in Columns control.
    await columnsHost.locator('[data-column-visible="meta:priority"]').uncheck();
    await columnsHost.locator("[data-column-apply]").click();
    await expect(table.locator('th[data-table-column="meta:priority"]')).toHaveCount(0);

    await cell("scored", "meta:qa_status").dblclick();
    await expect(cell("scored", "meta:qa_status").locator(".table-cell-editor-control")).toHaveCount(0);

    // Guest CAN group by custom column in Task Summary and export visible columns.
    await summary.locator('[data-task-summary-group="meta:qa_status"]').click();
    await summary.locator("[data-task-summary-toggle]").click();
    await expect(summary.locator('td[data-table-column-key="group"]')).toHaveText(["Unset", "OK"]);

    await guest.locator("[data-task-scoring-actions] summary").click();
    const download = guest.waitForEvent("download");
    await guest.locator('[data-task-export="json"]').click();
    const exported = JSON.parse(await readFile(await (await download).path(), "utf8"));
    expect(exported.find(item => item.task === "scored")["meta:qa_status"]).toBe("OK");
    expect(exported.find(item => item.task === "scored")).not.toHaveProperty("meta:priority");
    expect(errors).toEqual([]);
  } finally {
    await guestContext?.close();
    await stopFixture(fixture);
  }
});
