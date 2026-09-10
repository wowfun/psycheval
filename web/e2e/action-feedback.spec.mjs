import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.beforeAll(async () => { fixture = await startFixture({ PYTHONPATH: process.cwd() }); });
test.afterAll(async () => { await stopFixture(fixture); });

test("Dataset forms retain failures and register a quoted native absolute path", async ({ page }) => {
  await page.goto(`${fixture.origin}/config`);
  await page.locator("[data-harbor-register-dataset]").click();
  let dialog = page.locator(".action-form-overlay");
  await dialog.locator('[name="path"]').fill('"  "');
  await dialog.locator('[type="submit"]').click();
  await expect(dialog.locator('[name="path"]')).toHaveAttribute("aria-invalid", "true");
  await expect(dialog.locator(".action-field-error")).toContainText("path must not be empty");
  await dialog.locator('[name="path"]').fill('"missing-dataset"');
  await dialog.locator('[type="submit"]').click();
  await expect(dialog.locator(".action-feedback")).toContainText("Dataset path not found");
  await expect(dialog.locator('[name="path"]')).toHaveValue('"missing-dataset"');
  await expect(dialog.locator(".action-feedback")).toBeInViewport();
  await expect(page.locator(".action-toast")).toHaveCount(0);
  await dialog.locator("[data-action-form-cancel]").click();
  await expect(page.locator("[data-harbor-register-dataset]")).toBeFocused();

  await page.locator("[data-harbor-add-dataset]").click();
  dialog = page.locator(".action-form-overlay");
  await dialog.locator('[name="dataset_id"]').fill("prepared");
  await dialog.locator('[name="path"]').fill('"existing-dataset"');
  await dialog.locator('[name="package_name"]').fill("local/prepared");
  await dialog.locator('[type="submit"]').click();
  await expect(dialog).toHaveCount(0);
  await expect(page.locator("[data-harbor-dataset-registry]")).toContainText("prepared");
  const config = await page.request.get(`${fixture.origin}/api/config`);
  const path = (await config.json()).datasets.find(dataset => dataset.id === "prepared").path;
  const removed = await page.request.post(`${fixture.origin}/api/harbor/dataset-unregistration-operations`, {
    headers: { "If-Match": config.headers().etag, Origin: fixture.origin }, data: { dataset_ids: ["prepared"] },
  });
  expect(removed.status()).toBe(202);
  const operation = await removed.json();
  await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/operations/${operation.id}`)).json()).state).toBe("succeeded");
  await page.locator("[data-harbor-config-reload]").click();
  await expect(page.locator("[data-harbor-dataset-registry]")).not.toContainText("prepared");
  await page.locator("[data-harbor-register-dataset]").click();
  dialog = page.locator(".action-form-overlay");
  await dialog.locator('[name="path"]').fill(`"  ${path}  "`);
  await dialog.locator('[type="submit"]').click();
  await expect(dialog).toHaveCount(0);
  await expect(page.locator("[data-harbor-dataset-registry]")).toContainText("existing-dataset");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator("[data-harbor-register-dataset]").click();
  dialog = page.locator(".action-form-overlay");
  await dialog.locator('[name="path"]').fill(`"${path}"`);
  await dialog.locator('[type="submit"]').click();
  await expect(dialog.locator(".action-feedback")).toContainText("already registered");
  await expect(dialog.locator(".action-feedback")).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: ".local/feedback-mobile.png" });
});

test("an off-page failure returns to its retained draft without taking focus", async ({ page }) => {
  let release, received;
  const ready = new Promise(resolve => { received = resolve; });
  const response = new Promise(resolve => { release = resolve; });
  await page.route("**/api/prompts/*", async route => {
    if (route.request().method() !== "PUT") return route.continue();
    received();
    await response;
    await route.fulfill({ status: 412, contentType: "application/problem+json", body: JSON.stringify({ detail: "Prompt changed elsewhere" }) });
  });
  try {
    await page.goto(`${fixture.origin}/config`);
    await page.locator("[data-prompt-content]").click();
    await page.locator("[data-prompt-content]").fill("My retained draft");
    await page.locator("[data-prompt-save]").click();
    await ready;
    await page.locator('[data-workspace-route="datasets"]').click();
    await expect(page.locator('[data-workspace-page="datasets"]')).toBeFocused();
    await page.getByRole("button", { name: "Copilot", exact: true }).click();
    const focusBefore = await page.evaluate(() => document.activeElement?.outerHTML);
    release();
    const notification = page.locator(".action-toast").filter({ hasText: "Prompt changed elsewhere" });
    await expect(notification).toBeVisible();
    await expect(notification).toBeInViewport();
    const noticeBounds = await notification.boundingBox();
    const drawerBounds = await page.locator("[data-acp-drawer]").boundingBox();
    expect(noticeBounds.x + noticeBounds.width).toBeLessThanOrEqual(drawerBounds.x);
    await page.screenshot({ path: ".local/feedback-desktop.png" });
    expect(await page.evaluate(() => document.activeElement?.outerHTML)).toBe(focusBefore);
    await notification.getByRole("button", { name: "View", exact: true }).click();
    await expect(page).toHaveURL(/\/config$/);
    await expect(page.locator("[data-prompt-content]")).toHaveValue("My retained draft");
    await expect(page.locator('[aria-labelledby="prompt-assets-title"] .action-feedback')).toContainText("Prompt changed elsewhere");
  } finally { release(); }
});

test("Task and file dialogs share validation and retain a failed file request", async ({ page }) => {
  const config = await page.request.get(`${fixture.origin}/api/config`);
  const created = await page.request.post(`${fixture.origin}/api/harbor/datasets`, {
    headers: { "If-Match": config.headers().etag, Origin: fixture.origin },
    data: { source: "new", id: "file-forms", path: "file-forms", package_name: "local/file-forms" },
  });
  expect(created.status()).toBe(202);
  const operation = await created.json();
  await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/operations/${operation.id}`)).json()).state).toBe("succeeded");
  await page.goto(`${fixture.origin}/datasets`);
  await page.locator("[data-harbor-create-task]").click();
  let dialog = page.locator(".action-form-overlay");
  await dialog.locator('[name="directory"]').fill("feedback-task");
  await expect(dialog.locator('[name="package_name"]')).toHaveValue("local/feedback-task");
  await dialog.locator('[type="submit"]').click();
  await expect(dialog).toHaveCount(0);
  await expect(page.locator("[data-harbor-selected-title]")).toContainText("feedback-task");
  await page.locator("[data-harbor-new-file]").click();
  dialog = page.locator(".action-form-overlay");
  await dialog.locator('[name="path"]').fill("../outside.txt");
  await dialog.locator('[type="submit"]').click();
  await expect(dialog.locator(".action-feedback.danger")).toBeVisible();
  await expect(dialog.locator('[name="path"]')).toHaveValue("../outside.txt");
  await dialog.locator('[name="path"]').fill("new.txt");
  await dialog.locator('[type="submit"]').click();
  await expect(dialog).toHaveCount(0);
  await expect(page.locator("[data-harbor-file-tree]")).toContainText("new.txt");
});


test("Enter in a rename dialog saves and never deletes", async ({ page }) => {
  await page.goto(`${fixture.origin}/config`);
  await page.evaluate(async () => {
    const { openActionForm } = await import("/assets/peval/modules/action-form.js");
    document.body.dataset.saved = "0";
    document.body.dataset.deleted = "0";
    openActionForm({ title: "Rename fixture", fields: [{ name: "name", label: "Name", value: "draft" }],
      submit: async () => { document.body.dataset.saved = "1"; return false; },
      secondaryAction: { label: "Delete fixture", run: async () => { document.body.dataset.deleted = "1"; return false; } },
    });
  });
  const dialog = page.getByRole("dialog", { name: "Rename fixture" });
  await dialog.getByLabel("Name").press("Enter");
  await expect(page.locator("body")).toHaveAttribute("data-saved", "1");
  await expect(page.locator("body")).toHaveAttribute("data-deleted", "0");
  await dialog.getByRole("button", { name: "Delete fixture" }).click();
  await expect(page.locator("body")).toHaveAttribute("data-deleted", "1");
});
