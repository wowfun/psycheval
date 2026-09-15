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
    await page.route("**/api/jobs/abc/logs", route => route.fulfill({ json: { entries: [], truncated: false } }));
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
    await expect(page.locator("[data-job-harness]")).toHaveValue("fixture");
    await expect(page.locator("[data-variant]")).toHaveCount(2);
    await page.locator('[data-select-task="fixture/one"]').check();
    await expect(page.locator("[data-job-preview-output]")).toBeHidden();
    const directStart = page.waitForRequest(request => request.url() === `${fixture.origin}/api/jobs` && request.method() === "POST");
    await page.locator("[data-job-start]").click();
    expect((await directStart).postDataJSON()).not.toHaveProperty("preview_id");
    await expect(page.locator("[data-job-detail]")).toContainText("fixture run finished", { timeout: 20_000 });
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
    await expect(page.locator("[data-job-start]")).toBeEnabled();
    await page.getByRole("link", { name: "Home", exact: true }).click();
    await page.getByRole("link", { name: "Configure run", exact: true }).click();
    await expect(page.locator("[data-variant-model]")).toHaveValue("changed-model");
    await expect(page.locator('[data-select-task="fixture/one"]')).toBeChecked();
    const started = page.waitForRequest(request => request.url() === `${fixture.origin}/api/jobs` && request.method() === "POST");
    await page.locator("[data-job-start]").click();
    const body = (await started).postDataJSON();
    expect(body).not.toHaveProperty("preview_id");
    expect(body.request.variants[0].model).toBe("changed-model");
    await expect(page.locator("[data-job-detail]")).toContainText("fixture run finished", { timeout: 20_000 });
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
    expect((await page.request.put(`${fixture.origin}/api/jobs/preferred-harness`, { data: { harness: "fixture" } })).status()).toBe(403);
    expect((await (await page.request.get(`${fixture.origin}/api/jobs/options`)).json()).preferred_harness).toBeNull();
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
    await page.route("**/api/jobs/abc/logs", route => route.fulfill({ json: { entries: [{ format: "text", text: "A log line\n".repeat(100) }], truncated: false } }));
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

test("Jobs shows arbitrary NDJSON from stdout and stderr before the worker finishes", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_JOBS: "1", PYTHONPATH: process.cwd(), UV_NO_SYNC: "1" });
  try {
    await page.goto(`${fixture.origin}/jobs`);
    const request = { harness: "fixture", tasks: ["fixture/one"], variants: [{ id: "a", label: "A", agent: "fixture", model: "a", options: {} }], settings: { ndjson: true, delay: 60 } };
    const response = await page.request.post(`${fixture.origin}/api/jobs`, { data: { request, request_id: "browser-ndjson" } });
    expect(response.ok()).toBe(true);
    const run = await response.json();
    await page.locator("[data-jobs-refresh]").click();
    await page.locator(`[data-select-run="${run.id}"]`).click();
    const log = page.locator(".job-log");
    await expect(log).toContainText("first event");
    await expect(log).toContainText("中文");
    await expect(log).toContainText("warning from downstream", { timeout: 10_000 });
    await expect(log).toContainText("error from downstream");
    await expect(log).toContainText("plain diagnostic");
    await expect(log.locator('[data-log-format="json"]')).toHaveCount(2);
    expect((await (await page.request.get(`${fixture.origin}/api/jobs/${run.id}`)).json()).state).toBe("running");
    await page.request.post(`${fixture.origin}/api/jobs/${run.id}/stop`, { data: {} });
    await expect.poll(async () => (await (await page.request.get(`${fixture.origin}/api/jobs/${run.id}`)).json()).state).toBe("cancelled");
    await page.locator("[data-jobs-refresh]").click();
    await expect(log).toContainText("error from downstream");
    await expect(log.locator('[data-log-format="json"]')).toHaveCount(2);
  } finally { await stopFixture(fixture); }
});

test("Jobs log refresh follows the bottom and preserves reading, focus and literal JSON", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_JOBS: "1", PYTHONPATH: process.cwd(), UV_NO_SYNC: "1" });
  try {
    let version = 0;
    const entries = Array.from({ length: 25 }, (_, i) => ({ format: "json", text: JSON.stringify({ arbitrary: i, html: '<svg onload="unsafe()">', huge: "900719925474099312345" }, null, 2) }));
    await page.route("**/api/jobs", route => route.fulfill({ json: { items: [{ id: "abc", state: "running", harness: "fixture" }] } }));
    await page.route("**/api/jobs/abc", route => route.fulfill({ json: { id: "abc", state: "running", trials_completed: version, request: {}, results: [] } }));
    await page.route("**/api/jobs/abc/logs", route => route.fulfill({ json: { entries, truncated: true } }));
    await page.goto(`${fixture.origin}/jobs`);
    await page.locator('[data-select-run="abc"]').click();
    const log = page.locator(".job-log");
    const bottomGap = () => log.evaluate(node => node.scrollHeight - node.clientHeight - node.scrollTop);
    await expect(log.locator(".job-log-entry")).toHaveCount(25);
    await expect.poll(bottomGap).toBeLessThan(2);
    await expect(log.locator("svg")).toHaveCount(0);
    await expect(log).toContainText('900719925474099312345');
    await expect(page.locator("[data-job-log-truncated]")).toBeVisible();
    const original = await log.elementHandle();
    await log.evaluate(node => { node.scrollTop = 80; node.dispatchEvent(new Event("scroll")); });
    await expect(page.locator("[data-job-log-latest]")).toBeVisible();
    await page.locator("[data-filter-variant]").focus();
    entries.push({ format: "json", text: '["new event"]' });
    version++;
    await expect(log.locator(".job-log-entry")).toHaveCount(26);
    expect(await original.evaluate(node => node.isConnected)).toBe(true);
    expect(await log.evaluate(node => node.scrollTop)).toBe(80);
    await expect(page.locator("[data-filter-variant]")).toBeFocused();
    const logSummary = page.locator("[data-job-log-section] > summary");
    await logSummary.click();
    entries.push({ format: "json", text: "false" });
    version++;
    await expect(log.locator(".job-log-entry")).toHaveCount(27);
    await expect(page.locator("[data-job-log-section]")).not.toHaveAttribute("open");
    await logSummary.click();
    await expect.poll(() => log.evaluate(node => node.scrollTop)).toBe(80);
    await page.locator("[data-job-log-latest]").click();
    await expect.poll(bottomGap).toBeLessThan(2);
    await expect(log).toBeFocused();
    await expect(page.locator("[data-job-log-latest]")).toBeHidden();
    entries.push({ format: "text", text: "last diagnostic" });
    await expect(log).toContainText("last diagnostic");
    await expect.poll(bottomGap).toBeLessThan(2);
    await expect(log.locator(".job-log-entry")).toHaveCount(28);
  } finally { await stopFixture(fixture); }
});

test("Jobs discards delayed log responses after selecting another run", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_JOBS: "1", PYTHONPATH: process.cwd(), UV_NO_SYNC: "1" });
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  try {
    const items = ["abc", "def"].map(id => ({ id, state: "completed", harness: "fixture", request: {}, results: [] }));
    await page.route("**/api/jobs", route => route.fulfill({ json: { items } }));
    for (const item of items) {
      await page.route(`**/api/jobs/${item.id}`, route => route.fulfill({ json: item }));
      await page.route(`**/api/jobs/${item.id}/logs`, async route => {
        if (item.id === "abc") await pending;
        await route.fulfill({ json: { entries: [{ format: "json", text: JSON.stringify({ run: item.id }) }], truncated: false } });
      });
    }
    await page.goto(`${fixture.origin}/jobs`);
    const sent = page.waitForRequest("**/api/jobs/abc/logs");
    await page.locator('[data-select-run="abc"]').click();
    await sent;
    await page.locator('[data-select-run="def"]').click();
    await expect(page.locator(".job-log")).toContainText("def");
    const received = page.waitForResponse("**/api/jobs/abc/logs");
    release();
    await received;
    await expect(page.locator(".job-log")).not.toContainText("abc");
    await expect(page.locator(".job-log-entry")).toHaveCount(1);
  } finally { release(); await stopFixture(fixture); }
});

test("Jobs serializes harness loading and recovers from an external preference conflict", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_JOBS: "1", PYTHONPATH: process.cwd(), UV_NO_SYNC: "1" });
  function gate() {
    let release;
    const pending = new Promise(resolve => { release = resolve; });
    return { pending, release };
  }
  const initial = gate(), save = gate(), catalog = gate();
  let writes = 0;
  try {
    await page.route("**/api/jobs/tasks/harbor", async route => { await initial.pending; await route.continue(); });
    await page.route("**/api/jobs/tasks/fixture", async route => { await catalog.pending; await route.continue(); });
    await page.route("**/api/jobs/preferred-harness", async route => { writes++; await save.pending; await route.continue(); });
    const initialLoad = page.waitForRequest("**/api/jobs/tasks/harbor");
    await page.goto(`${fixture.origin}/jobs`);
    await initialLoad;
    const select = page.locator("[data-job-harness]");
    await expect(select).toBeDisabled();
    await expect(page.locator("[data-job-start]")).toBeDisabled();
    initial.release();
    await expect(select).toBeEnabled();
    const saving = page.waitForRequest("**/api/jobs/preferred-harness");
    await select.selectOption("fixture");
    await saving;
    await expect(select).toBeDisabled();
    await expect(page.locator("[data-job-preview]")).toBeDisabled();
    await expect(page.locator("[data-job-start]")).toBeDisabled();
    const options = await (await page.request.get(`${fixture.origin}/api/jobs/options`)).json();
    const external = await page.request.put(`${fixture.origin}/api/jobs/defaults/harbor`, { data: { defaults: {}, revision: options.revision } });
    expect(external.ok()).toBe(true);
    const refreshed = page.waitForRequest("**/api/jobs/tasks/fixture");
    save.release();
    await refreshed;
    await expect(select).toBeDisabled();
    catalog.release();
    await expect(page.locator("[data-jobs-notice]")).toContainText("Options refreshed");
    await expect(select).toBeEnabled();
    expect(writes).toBe(1);
    await page.getByText("Save selected defaults", { exact: true }).click();
    await page.locator("[data-job-save-defaults]").click();
    await expect(page.locator("[data-jobs-notice]")).toContainText("Defaults saved");
    await select.selectOption("harbor");
    await expect(select).toBeEnabled();
    expect((await (await page.request.get(`${fixture.origin}/api/jobs/options`)).json()).preferred_harness).toBe("harbor");
    expect(writes).toBe(2);
  } finally {
    initial.release(); save.release(); catalog.release();
    await stopFixture(fixture);
  }
});
