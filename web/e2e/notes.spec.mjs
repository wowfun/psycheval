import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

function notesCell(page, sourceKey) {
  return page.locator(`#leaderboard [data-source-key="${sourceKey}"] [data-table-column-key="notes"]`);
}

async function catalogRows(request, origin) {
  const response = await request.get(`${origin}/api/catalog`);
  expect(response.ok()).toBeTruthy();
  return (await response.json()).items;
}

test("saving, editing and clearing Trial notes refreshes the Leaderboard without changing its query", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PYTHONPATH: process.cwd() });
  try {
    const trial = (await catalogRows(page.request, fixture.origin)).find(row => row.kind === "harbor-trial");
    expect(trial.source_key).not.toBe(trial.trial_key);
    await page.goto(fixture.origin);
    await expect(page.locator("[data-notes-edit]")).toBeVisible();
    const query = { page: 1, page_size: 1, jobs: [trial.job_name], sort: "task", direction: "asc" };
    await page.evaluate(async query => {
      const { loadCatalogPage } = await import("/assets/peval/modules/serve-catalog.js");
      await loadCatalogPage(query, { force: true });
    }, query);
    await page.locator(`#leaderboard [data-source-key="${trial.source_key}"] [data-table-column-key="task_name"]`).click();
    await expect(page.locator("#detail-sidebar")).toBeVisible();
    await page.locator("#detail-sidebar [data-sidebar-close]").click();

    for (const note of ["中文备注\n\n**first**\tline", `Updated <script>alert("x")</script> ${"长".repeat(100)}`, ""]) {
      await page.locator("[data-notes-edit]").click();
      await page.locator("[data-notes-editor]").fill(note);
      const saved = page.waitForResponse(response => response.request().method() === "PATCH" && response.url().includes("/api/sources/"));
      await page.locator("[data-notes-save]").click();
      expect((await saved).status()).toBe(200);
      await expect(page.locator("[data-notes-editor]")).toHaveCount(0);
      if (note) {
        const folded = note.replace(/\s+/g, " ").trim();
        await expect(notesCell(page, trial.source_key)).toHaveText(folded.length > 96 ? `${folded.slice(0, 96)}...` : folded);
        await expect(notesCell(page, trial.source_key)).toHaveAttribute("title", note);
        await expect(notesCell(page, trial.source_key).locator("script")).toHaveCount(0);
      } else {
        // Auto visibility follows non-blank notes across the complete query.
        await expect(page.locator('#leaderboard [data-table-column-key="notes"]')).toHaveCount(0);
        await expect(page.locator(".selected-notes")).toContainText("No notes.");
      }
      const state = await page.evaluate(async () => {
        const { state } = await import("/assets/peval/modules/runtime.js");
        return { query: state.catalogQuery, sourceKey: state.selectedSourceKey };
      });
      expect(state.query).toMatchObject(query);
      expect(state.sourceKey).toBe(trial.source_key);
    }
  } finally { await stopFixture(fixture); }
});

test("catalog notes survive detail switches, pagination, reload and guest reads", async ({ page, browser }) => {
  const fixture = await startFixture({
    PEVAL_E2E_VERIFICATION: "1", PEVAL_E2E_CLAUDE: "1",
    PEVAL_E2E_PASSWORD: "notes-fixture-secret", PYTHONPATH: process.cwd(),
  });
  let guest;
  try {
    const headers = { Origin: fixture.origin };
    const login = await page.request.post(`${fixture.origin}/api/session`, { headers, data: { password: "notes-fixture-secret" } });
    expect(login.ok()).toBeTruthy();
    const imported = await page.request.post(`${fixture.origin}/api/source-import-operations`, {
      headers, data: { path: ".claude/root-session.jsonl", adapter: "claude" },
    });
    expect(imported.ok()).toBeTruthy();
    const operation = await imported.json();
    await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/operations/${operation.id}`)).json()).state).toBe("succeeded");
    const rows = await catalogRows(page.request, fixture.origin);
    const harbor = rows.find(row => row.kind === "harbor-trial");
    const local = rows.find(row => row.adapter === "claude" && row.refreshable);
    expect(local).toBeTruthy();
    const notes = new Map([[harbor.source_key, "Harbor 中文备注"], [local.source_key, "Local independent note"]]);
    for (const [sourceKey, note] of notes) {
      const response = await page.request.patch(`${fixture.origin}/api/sources/${encodeURIComponent(sourceKey)}`, { headers, data: { notes: note } });
      expect(response.ok()).toBeTruthy();
    }
    const expectNotes = async current => {
      for (const [key, note] of notes) await expect(notesCell(current, key)).toHaveText(note);
    };
    await page.goto(fixture.origin);
    await expectNotes(page);
    for (const sourceKey of notes.keys()) {
      await page.locator(`#leaderboard [data-source-key="${sourceKey}"] [data-table-column-key="task_name"]`).click();
      await expect(page.locator("#detail-sidebar")).toBeVisible();
      await page.locator("#detail-sidebar [data-sidebar-close]").click();
      await expectNotes(page);
    }
    for (let number = 1; number <= rows.length; number++) {
      await page.evaluate(async number => {
        const { loadCatalogPage } = await import("/assets/peval/modules/serve-catalog.js");
        await loadCatalogPage({ page: number, page_size: 1 }, { force: true });
      }, number);
      const row = page.locator("#leaderboard tbody tr");
      await expect(row).toHaveCount(1);
      const key = await row.getAttribute("data-source-key");
      await expect(notesCell(page, key)).toHaveText(notes.get(key) || "-");
    }
    const restoredKey = await page.locator("#leaderboard tbody tr").getAttribute("data-source-key");
    await page.reload();
    await expect(page.locator("#leaderboard tbody tr")).toHaveCount(1);
    await expect(notesCell(page, restoredKey)).toHaveText(notes.get(restoredKey) || "-");
    const restoredQuery = await page.evaluate(async () => {
      const { state } = await import("/assets/peval/modules/runtime.js");
      return state.catalogQuery;
    });
    expect(restoredQuery).toMatchObject({ page: rows.length, page_size: 1 });
    guest = await browser.newContext();
    const guestPage = await guest.newPage();
    await guestPage.goto(fixture.origin);
    await expectNotes(guestPage);
    await expect(guestPage.locator("[data-notes-edit]")).toHaveCount(0);
  } finally {
    if (guest) await guest.close();
    await stopFixture(fixture);
  }
});
