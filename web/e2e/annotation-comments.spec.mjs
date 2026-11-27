import { test, expect } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

test("Annotator login, scoring-item comments, Trial review comments, ownership isolation, and Admin moderation", async ({ browser }) => {
  test.setTimeout(120_000);
  const fixture = await startFixture({
    PEVAL_E2E_PASSWORD: "admin-fixture-secret",
    PEVAL_E2E_ANNOTATOR_PASSWORD: "annotator-fixture-secret",
    PEVAL_E2E_TASK_SCORING: "1",
    PEVAL_E2E_VERIFICATION: "1",
    PEVAL_E2E_LOCALE: "en",
    PYTHONPATH: process.cwd(),
  });
  const errors = [];
  const contextA = await browser.newContext();
  const contextB = await browser.newContext();
  const page = await contextA.newPage();
  const otherPage = await contextB.newPage();
  page.on("pageerror", error => errors.push(error.message));
  otherPage.on("pageerror", error => errors.push(error.message));

  try {
    // 1. Guest sees Login button and cannot open /config.
    await page.goto(`${fixture.origin}/`);
    await expect(page.locator("[data-admin-login-open]")).toBeVisible();
    await expect(page.locator('a[href="/config"]')).toHaveCount(0);

    // 2. Log in as Annotator "alice" via dual-role dialog.
    await page.locator("[data-admin-login-open]").click();
    const dialog = page.locator("[data-admin-login-dialog]");
    await expect(dialog).toBeVisible();
    await dialog.locator('input[name="role"][value="annotator"]').check();
    await expect(dialog.locator('input[name="user_id"]')).toBeVisible();
    await dialog.locator('input[name="user_id"]').fill("alice");
    await dialog.locator('input[name="password"]').fill("annotator-fixture-secret");
    await Promise.all([
      page.waitForNavigation(),
      dialog.locator('button[type="submit"]').click(),
    ]);
    await expect(page.locator("[data-session-role-badge]")).toContainText("Annotator · alice");
    await expect(page.locator('a[href="/config"]')).toHaveCount(0);
    await expect(page.locator("[data-locale-select]")).toHaveCount(0);

    // 3. Datasets -> Tasks flattened scoring-item comments CRUD + inline judge.yaml sync.
    await page.goto(`${fixture.origin}/datasets`);
    await page.locator("[data-task-flatten]").check();
    const commentTrigger = page.locator("[data-scoring-comments-open]").first();
    await expect(commentTrigger).toBeVisible();
    await commentTrigger.click();
    const modal = page.locator("[data-comments-modal]");
    await expect(modal).toBeVisible();
    await expect(modal.locator("[data-comment-composer]")).toHaveCount(0);
    await modal.locator("[data-comment-composer-open]").click();
    await modal.locator("[data-comment-composer] textarea").fill("Rubric needs clearer boundary");
    await modal.locator("[data-comment-submit]").click();
    await expect(modal.locator("[data-comment-id]")).toContainText("Rubric needs clearer boundary");
    await modal.locator("[data-comments-modal-close]").click();

    // Open scoring file preview and verify inline comment appears.
    await page.locator("[data-harbor-overview-row]").first().click();
    const taskSidebar = page.locator('[data-sidebar-id="dataset-task"]');
    await expect(taskSidebar.locator(".task-scoring-preview")).toContainText("Rubric needs clearer boundary");

    // 4. Home -> Leaderboard Comments column CRUD + Trial Verification tab sync.
    await page.goto(`${fixture.origin}/`);
    const reviewTrigger = page.locator("#leaderboard [data-review-comments-open]").first();
    await expect(reviewTrigger).toBeVisible();
    await reviewTrigger.click();
    const lbModal = page.locator("[data-comments-modal]");
    await expect(lbModal).toBeVisible();
    await lbModal.locator("[data-comment-composer-open]").click();
    await lbModal.locator("[data-comment-composer] textarea").fill("Judge missed table discrepancy");
    await lbModal.locator("[data-comment-submit]").click();
    await expect(lbModal.locator("[data-comment-id]")).toContainText("Judge missed table discrepancy");
    await lbModal.locator("[data-comments-modal-close]").click();
    await expect(reviewTrigger).toContainText("Judge missed table discrepancy");

    // Open Trial sidebar -> Verification tab shows synced comments bar.
    await page.locator("#leaderboard tbody tr").first().click();
    const trialComments = page.locator("[data-trial-review-comments]");
    await expect(trialComments).toBeVisible();
    await expect(trialComments).toContainText("Judge missed table discrepancy");

    // 5. Second Annotator "bob" sees Alice's comment read-only (no edit/delete) and can add own comment.
    await otherPage.goto(`${fixture.origin}/`);
    await otherPage.locator("[data-admin-login-open]").click();
    const otherDialog = otherPage.locator("[data-admin-login-dialog]");
    await otherDialog.locator('input[name="role"][value="annotator"]').check();
    await otherDialog.locator('input[name="user_id"]').fill("bob");
    await otherDialog.locator('input[name="password"]').fill("annotator-fixture-secret");
    await Promise.all([
      otherPage.waitForNavigation(),
      otherDialog.locator('button[type="submit"]').click(),
    ]);
    await otherPage.locator("#leaderboard [data-review-comments-open]").first().click();
    const bobModal = otherPage.locator("[data-comments-modal]");
    await expect(bobModal).toContainText("Judge missed table discrepancy");
    await expect(bobModal.locator("[data-comment-edit]")).toHaveCount(0);
    await expect(bobModal.locator("[data-comment-delete]")).toHaveCount(0);
    await bobModal.locator("[data-comment-composer-open]").click();
    await bobModal.locator("[data-comment-composer] textarea").fill("Bob confirms finding");
    await bobModal.locator("[data-comment-submit]").click();
    await expect(bobModal.locator("[data-comment-edit]")).toHaveCount(1);

    // 6. Logout and log in as Admin -> can edit/delete every comment.
    await bobModal.locator("[data-comments-modal-close]").click();
    await Promise.all([
      otherPage.waitForNavigation(),
      otherPage.locator("[data-admin-logout]").click(),
    ]);
    await otherPage.locator("[data-admin-login-open]").click();
    const adminDialog = otherPage.locator("[data-admin-login-dialog]");
    await adminDialog.locator('input[name="role"][value="admin"]').check();
    await adminDialog.locator('input[name="password"]').fill("admin-fixture-secret");
    await Promise.all([
      otherPage.waitForNavigation(),
      adminDialog.locator('button[type="submit"]').click(),
    ]);
    await otherPage.locator("#leaderboard [data-review-comments-open]").first().click();
    const adminModal = otherPage.locator("[data-comments-modal]");
    await expect(adminModal.locator("[data-comment-edit]")).toHaveCount(2);
    await expect(adminModal.locator("[data-comment-delete]")).toHaveCount(2);

    expect(errors).toEqual([]);
  } finally {
    await contextA.close();
    await contextB.close();
    await stopFixture(fixture);
  }
});
