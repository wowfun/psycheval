import { test, expect } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

test("mobile Jobs results keep scores and navigation readable with long Task names", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_JOBS: "1", PYTHONPATH: process.cwd(), UV_NO_SYNC: "1" });
  try {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.route("**/api/jobs", route => route.fulfill({ json: { items: [{ id: "abc", state: "completed", harness: "fixture" }] } }));
    await page.route("**/api/jobs/abc", route => route.fulfill({ json: {
      id: "abc", state: "completed", request: {},
      results: [{ id: "one", task: "workbuddy/research-factor-table-extract-L3-016", variant_label: "MiMo Pro", score: 0.2619, score_source: "reward", source_key: "one" }],
    } }));
    await page.route("**/api/jobs/abc/logs", route => route.fulfill({ json: { text: "" } }));
    await page.goto(`${fixture.origin}/jobs`);
    await page.locator('[data-select-run="abc"]').click();
    const result = page.locator(".job-result");
    await expect(result).toBeVisible();
    const sizes = await result.evaluate(node => {
      const task = node.querySelector("strong").getBoundingClientRect();
      const score = node.children[2].getBoundingClientRect();
      const link = node.querySelector("a").getBoundingClientRect();
      return { taskWidth: task.width, scoreHeight: score.height, linkHeight: link.height, overflow: node.scrollWidth > node.clientWidth };
    });
    expect(sizes.taskWidth).toBeGreaterThan(250);
    expect(sizes.scoreHeight).toBeLessThan(25);
    expect(sizes.linkHeight).toBeLessThan(25);
    expect(sizes.overflow).toBe(false);
  } finally { await stopFixture(fixture); }
});

test("Jobs configures A/B, saves typed defaults, retains results and cancels a running worker", async ({ page }) => {
  test.setTimeout(90_000);
  const fixture = await startFixture({ PEVAL_E2E_JOBS: "1", PYTHONPATH: process.cwd(), UV_NO_SYNC: "1" });
  try {
    await page.goto(`${fixture.origin}/jobs`);
    await page.locator("[data-job-harness]").selectOption("fixture");
    await page.locator('[data-select-task="fixture/one"]').check();
    await page.locator("[data-add-variant]").click();
    await page.locator("[data-variant-model]").nth(1).fill("model-b");
    await page.getByRole("button", { name: "Preview configuration", exact: true }).click();
    await expect(page.locator("[data-job-preview-count]")).toContainText("2 Trials");
    await page.screenshot({ path: ".local/jobs-desktop.png", fullPage: true });
    await page.getByRole("button", { name: "Start run", exact: true }).click();
    await expect(page.locator("[data-job-detail]")).toContainText("fixture run finished", { timeout: 20_000 });
    await expect(page.locator(".job-result")).toHaveCount(2);
    await expect(page.locator(".job-result").first()).toContainText("0");
    await page.locator("[data-filter-variant]").selectOption("a");
    await expect(page.locator(".job-result:visible")).toHaveCount(1);
    await expect(page.locator(".job-result:visible")).toContainText("0");
    await page.locator("[data-filter-variant]").selectOption("");
    await page.locator(".job-result a").first().click();
    await expect(page.locator("#detail-sidebar")).toBeVisible();
    await page.getByRole("link", { name: "Jobs", exact: true }).click();
    await expect(page.locator("[data-variant]")).toHaveCount(2);
    await page.getByText("Save selected defaults", { exact: true }).click();
    await page.getByRole("button", { name: "Save defaults", exact: true }).click();
    await expect(page.locator("[data-jobs-notice]")).toContainText("Defaults saved");
    await page.reload();
    await page.locator("[data-job-harness]").selectOption("fixture");
    await expect(page.locator("[data-variant]")).toHaveCount(2);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: ".local/jobs-mobile.png", fullPage: true });
    expect(await page.locator("[data-workspace-page=jobs]").evaluate(node => node.scrollWidth > node.clientWidth)).toBe(false);
    const payload = { harness: "fixture", tasks: ["fixture/one"], variants: [{ id: "a", label: "A", agent: "fixture", model: "a", options: {} }], settings: { delay: 60 } };
    const preview = await (await page.request.post(`${fixture.origin}/api/jobs/preview`, { data: payload })).json();
    const run = await (await page.request.post(`${fixture.origin}/api/jobs`, { data: { request: payload, preview_id: preview.preview_id, request_id: "browser-cancel" } })).json();
    await page.request.post(`${fixture.origin}/api/jobs/${run.id}/stop`, { data: {} });
    await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/jobs/${run.id}`)).json()).state).toBe("cancelled");
  } finally { await stopFixture(fixture); }
});

test("editing a variant invalidates an in-flight preview and source entry preserves selection", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_JOBS: "1", PYTHONPATH: process.cwd(), UV_NO_SYNC: "1" });
  try {
    await page.goto(`${fixture.origin}/jobs`);
    await page.locator("[data-job-harness]").selectOption("fixture");
    await page.locator('[data-select-task="fixture/one"]').check();
    let release;
    const pending = new Promise(resolve => { release = resolve; });
    await page.route("**/api/jobs/preview", async route => {
      const response = await route.fetch();
      await pending;
      await route.fulfill({ response });
    });
    const sent = page.waitForRequest("**/api/jobs/preview");
    await page.locator("[data-job-preview]").click();
    await sent;
    await page.locator("[data-variant-model]").fill("changed-model");
    release();
    await expect(page.locator("[data-job-preview]")).toBeEnabled();
    await expect(page.locator("[data-job-preview-output]")).toBeHidden();
    await expect(page.locator("[data-job-start]")).toBeDisabled();
    await page.getByRole("link", { name: "Home", exact: true }).click();
    await page.getByRole("link", { name: "Configure run", exact: true }).click();
    await expect(page.locator("[data-variant-model]")).toHaveValue("changed-model");
    await expect(page.locator('[data-select-task="fixture/one"]')).toBeChecked();
  } finally { await stopFixture(fixture); }
});

test("guests can read and preview Jobs but cannot launch or save defaults", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_JOBS: "1", PEVAL_E2E_PASSWORD: "secret", PYTHONPATH: process.cwd(), UV_NO_SYNC: "1" });
  try {
    await page.goto(`${fixture.origin}/jobs`);
    await page.locator("[data-job-harness]").selectOption("fixture");
    await page.locator('[data-select-task="fixture/one"]').check();
    await page.getByRole("button", { name: "Preview configuration" }).click();
    await expect(page.locator("[data-job-preview-count]")).toContainText("1 Trials");
    await expect(page.locator("[data-job-start]")).toBeHidden();
    expect((await page.request.post(`${fixture.origin}/api/jobs`, { data: {} })).status()).toBe(403);
    expect((await page.request.put(`${fixture.origin}/api/jobs/defaults/fixture`, { data: {} })).status()).toBe(403);
    await page.screenshot({ path: ".local/jobs-guest.png", fullPage: true });
  } finally { await stopFixture(fixture); }
});

test("Jobs tolerates malformed links and polling preserves the reading state", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_JOBS: "1", PYTHONPATH: process.cwd(), UV_NO_SYNC: "1" });
  try {
    await page.addInitScript(() => { Object.defineProperty(crypto, "randomUUID", { value: undefined }); });
    await page.goto(`${fixture.origin}/jobs#task=%`);
    await expect(page.locator("[data-jobs-notice]")).toContainText("Invalid Task link");
    await page.locator("[data-job-harness]").selectOption("fixture");
    await page.locator('[data-select-task="fixture/one"]').check();
    await page.locator('[data-job-setting="n_attempts"]').fill("");
    await page.locator("[data-job-preview]").click();
    await expect(page.locator("[data-jobs-notice]")).toContainText("valid positive numbers");
    let revision = 0;
    await page.route("**/api/jobs", route => route.fulfill({ json: { items: [{ id: "abc", state: "running", harness: "fixture" }] } }));
    await page.route("**/api/jobs/abc", route => route.fulfill({ json: { id: "abc", state: "running", trials_completed: revision++, request: {}, results: [] } }));
    await page.route("**/api/jobs/abc/logs", route => route.fulfill({ json: { text: "A log line\n".repeat(100) } }));
    await page.locator("[data-jobs-refresh]").click();
    await page.locator('[data-select-run="abc"]').click();
    const details = page.locator("[data-job-detail] details");
    await details.first().locator("summary").click();
    await details.last().locator("summary").click();
    await page.locator("[data-filter-variant]").focus();
    await expect.poll(() => revision).toBeGreaterThan(2);
    await expect(details.first()).toHaveAttribute("open", "");
    await expect(details.last()).not.toHaveAttribute("open");
    await expect(page.locator("[data-filter-variant]")).toBeFocused();
  } finally { await stopFixture(fixture); }
});
