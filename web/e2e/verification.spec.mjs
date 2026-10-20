import { test, expect } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

for (const role of ["guest", "admin"]) {
  test(`${role} inspects retained Trial scores, reasons, files and Task without mutations`, async ({ page, context }) => {
    const fixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PYTHONPATH: process.cwd(),
      ...(role === "guest" ? { PEVAL_E2E_PASSWORD: "fixture-secret" } : {}) });
    try {
      await context.grantPermissions(["clipboard-read", "clipboard-write"]);
      await page.goto(fixture.origin);
      const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
      const trial = catalog.items.find(row => row.task_name === "workbuddy/office-one");
      await page.locator(`.trajectory-row[data-source-key="${trial.source_key}"]`).click();
      const sidebar = page.locator("#detail-sidebar");
      const verification = sidebar.locator('[data-trial-panel="verification"]');
      await expect(verification).toBeVisible();
      await expect(sidebar.locator(".verification-summary")).toContainText("0.676");
      await expect(sidebar.locator(".verification-summary")).toContainText("359 / 579");
      await expect(verification.locator(".verification-metrics")).toContainText("0.8 × 0.62 + 0.2 × 0.9 = 0.676");
      await verification.locator('.harbor-file-row[title="verifier"]').click();
      await expect(verification.locator('.harbor-file-row[title="verifier/score.json"]')).toHaveCount(0);
      await verification.locator('.harbor-file-row[title="verifier"]').click();
      await expect(verification.locator('.harbor-file-row[title="verifier/score.json"]')).toHaveClass(/selected/);
      await verification.locator(".verification-verdict summary").click();
      await expect(verification.locator(".verification-verdict pre")).toContainText("Position totals do not match.");
      expect(await verification.locator("script").count()).toBe(0);
      await verification.getByRole("button", { name: "Raw", exact: true }).click();
      await expect(verification.locator(".verification-raw")).toContainText('"verdicts"');
      await verification.getByRole("button", { name: "Copy", exact: true }).click();
      await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain('"reward": 0.676');
      await verification.getByRole("button", { name: "Details", exact: true }).click();
      await verification.getByRole("button", { name: "workbook", exact: true }).click();
      await expect(verification.locator(".file-markdown h4")).toHaveText("Retained workbook");
      await expect(verification.locator(".file-markdown table")).toBeVisible();
      await expect(verification.getByRole("link", { name: /Download/ })).toHaveCount(0);
      await verification.getByRole("button", { name: "Raw", exact: true }).click();
      await expect(verification.locator(".verification-raw")).toContainText("# Retained workbook");
      await verification.getByRole("button", { name: "Preview", exact: true }).click();
      await verification.locator('[data-verification-search]').fill("results.xml");
      await verification.locator('.harbor-file-row[title="verifier/results.xml"]').click();
      await expect(verification.locator(".verification-verdict")).toHaveCount(50);
      await verification.getByLabel("Test status", { exact: true }).selectOption("skipped");
      await expect(verification.locator(".verification-verdict")).toHaveCount(1);
      await expect(verification.locator(".verification-verdict")).toContainText("case-578");
      await expect(verification.getByRole("link", { name: /Download/ })).toHaveCount(0);
      await sidebar.getByRole("tab", { name: "Task", exact: true }).click();
      await expect(sidebar.locator("[data-harbor-editor]")).toHaveValue(/Create the requested artifact/);
      await expect(sidebar.locator("[data-harbor-markdown] h4")).toHaveText("Task instructions");
      await expect(sidebar.locator("[data-harbor-editor]")).toBeHidden();
      await sidebar.locator("[data-file-preview-toggle]").click();
      await expect(sidebar.locator("[data-harbor-editor]")).toBeVisible();
      await expect(sidebar.locator("[data-harbor-editor]")).toHaveAttribute("readonly", "");
      await sidebar.locator("[data-file-preview-toggle]").click();
      await sidebar.getByRole("tab", { name: "Trajectory", exact: true }).click();
      await expect(sidebar.locator("[data-detail-sidebar-steps] .step")).toHaveCount(1);
      await sidebar.getByRole("tab", { name: "Verification", exact: true }).click();
      await expect(verification.getByLabel("Test status", { exact: true })).toHaveValue("skipped");
      await page.locator(`[data-source-key="${trial.source_key}"][data-step-id="1"]`).click();
      await expect(sidebar.locator('[data-trial-panel="trajectory"]')).toBeVisible();
      await expect(sidebar.locator('.step[data-step="1"]')).toHaveAttribute("open", "");
      await sidebar.getByRole("tab", { name: "Verification", exact: true }).click();
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 900 });
        await expect(verification).toBeVisible();
        const overflow = await verification.evaluate(node => node.scrollWidth > node.clientWidth);
        expect(overflow).toBe(false);
      }
      await page.screenshot({ path: `.local/verification-${role}.png` });
      await page.goto(`${fixture.origin}/datasets`);
      const datasets = page.locator("[data-harbor-workbench]");
      await datasets.locator('[data-harbor-row-key="dataset:office|task:office-one"]').click();
      await expect(datasets.locator(".file-markdown h4")).toHaveText("Task instructions");
      await expect(datasets.locator(".file-markdown table")).toBeVisible();
      await expect(datasets.locator('[href*="download=true"], [data-harbor-download]')).toHaveCount(0);
      await datasets.locator("[data-file-preview-toggle]").click();
      await expect(datasets.locator("[data-harbor-editor]")).toBeVisible();
      await expect(datasets.locator("[data-harbor-editor]")).toHaveValue(/# Task instructions/);
      await datasets.locator("[data-file-preview-toggle]").click();
      await expect(datasets.locator(".file-markdown")).toBeVisible();
      await page.screenshot({ path: `.local/dataset-markdown-${role}.png` });
    } finally { await stopFixture(fixture); }
  });
}

test("a retained Trial remains inspectable after its registered Task disappears", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PEVAL_E2E_MISSING_TASK: "1", PEVAL_E2E_PASSWORD: "fixture-secret", PYTHONPATH: process.cwd() });
  try {
    await page.goto(fixture.origin);
    const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
    const trial = catalog.items.find(row => row.task_name === "workbuddy/office-one");
    await page.locator(`.trajectory-row[data-source-key="${trial.source_key}"]`).click();
    const sidebar = page.locator("#detail-sidebar");
    await expect(sidebar.locator(".verification-summary")).toContainText("0.676");
    await expect(sidebar.locator(".verification-metrics")).toContainText("0.8 × 0.62 + 0.2 × 0.9 = 0.676");
    await sidebar.getByRole("tab", { name: "Trajectory", exact: true }).click();
    await expect(sidebar.locator('[data-trial-panel="trajectory"]')).toContainText("Trajectory unavailable");
    await sidebar.getByRole("tab", { name: "Verification", exact: true }).click();
    await expect(sidebar.locator(".verification-metrics")).toBeVisible();
  } finally { await stopFixture(fixture); }
});

test("raw verification files use the full preview height with one scroll area", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PYTHONPATH: process.cwd() });
  try {
    await page.goto(fixture.origin);
    const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
    const trial = catalog.items.find(row => row.task_name === "workbuddy/office-one");
    await page.locator(`.trajectory-row[data-source-key="${trial.source_key}"]`).click();
    const verification = page.locator('#detail-sidebar [data-trial-panel="verification"]');
    await verification.locator('.harbor-file-row[title="verifier/judge/rubric-0001.json"]').click();
    await expect(verification.locator(".json-view")).toBeVisible();
    await verification.getByRole("button", { name: "Raw", exact: true }).click();
    await expect(verification.locator(".verification-raw")).toContainText("Retained scoring context.");
    for (const viewport of [{ width: 1440, height: 900 }, { width: 1440, height: 650 }, { width: 390, height: 900 }]) {
      await page.setViewportSize(viewport);
      const content = verification.locator(".verification-content");
      const geometry = await content.evaluate(pane => {
        const raw = pane.querySelector(".verification-raw");
        const preview = pane.closest(".verification-preview");
        return {
          paneHeight: pane.clientHeight,
          paneScrollHeight: pane.scrollHeight,
          rawHeight: raw.clientHeight,
          rawScrollHeight: raw.scrollHeight,
          unusedHeight: preview.getBoundingClientRect().bottom - pane.getBoundingClientRect().bottom,
        };
      });
      expect(geometry.paneHeight).toBeGreaterThan(0);
      expect(geometry.rawHeight).toBeGreaterThan(geometry.paneHeight);
      expect(geometry.rawScrollHeight - geometry.rawHeight).toBeLessThanOrEqual(3);
      expect(geometry.paneScrollHeight).toBeGreaterThan(geometry.paneHeight);
      expect(Math.abs(geometry.unusedHeight)).toBeLessThanOrEqual(3);
      await content.hover();
      await page.mouse.wheel(0, geometry.paneScrollHeight);
      await expect.poll(() => content.evaluate(pane => Math.abs(pane.scrollHeight - pane.clientHeight - pane.scrollTop))).toBeLessThanOrEqual(3);
    }
  } finally { await stopFixture(fixture); }
});

test("JSON starts fully expanded, supports keyboard folding, and raw copy preserves the source", async ({ page, context }) => {
  const fixture = await startFixture({ PEVAL_E2E_VERIFICATION: "1", PYTHONPATH: process.cwd() });
  try {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await page.goto(fixture.origin);
    const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
    const trial = catalog.items.find(row => row.task_name === "workbuddy/office-one");
    await page.locator(`.trajectory-row[data-source-key="${trial.source_key}"]`).click();
    const verification = page.locator('#detail-sidebar [data-trial-panel="verification"]');
    await verification.locator('.harbor-file-row[title="verifier/judge/rubric-0001.json"]').click();
    const messages = verification.locator('.json-view [data-json-key="messages"]');
    await expect(verification.locator(".json-view details:not([open])")).toHaveCount(0);
    await expect(messages).toHaveAttribute("open", "");
    await messages.locator(":scope > summary").press("Enter");
    await expect(messages).not.toHaveAttribute("open", "");
    await messages.locator(":scope > summary").press("Enter");
    const content = messages.locator('[data-json-key="content"]');
    await expect(content.locator(".json-string-text")).toBeVisible();
    await content.locator(":scope > summary").press("Enter");
    await expect(content.locator(".json-string-text")).toBeHidden();
    await content.locator(":scope > summary").press("Enter");
    await expect(content.locator(".json-string-text")).toBeVisible();
    await content.locator(":scope > summary").press("Enter");
    await expect(content.locator(".json-string-text")).toBeHidden();
    await verification.getByRole("button", { name: "Raw", exact: true }).click();
    const original = await verification.locator(".verification-raw").textContent();
    await verification.getByRole("button", { name: "Copy", exact: true }).click();
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(original);
    await verification.getByRole("button", { name: "JSON", exact: true }).click();
    await expect(messages).toHaveAttribute("open", "");
    await expect(content).not.toHaveAttribute("open", "");
    await page.setViewportSize({ width: 390, height: 900 });
    expect(await verification.evaluate(node => node.scrollWidth > node.clientWidth)).toBe(false);
  } finally { await stopFixture(fixture); }
});
