import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";
import { encodeWorkspaceLocation, decodeWorkspaceLocation } from "../../src/psycheval/assets/web/app/workspace-location.js";

async function copied(page, button) {
  await button.click();
  await expect(button).toHaveText("Copied");
  const href = await page.evaluate(() => navigator.clipboard.readText());
  expect(href).toBe(page.url());
  return href;
}
async function screenshots(page, testInfo, name, selector) {
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.locator(selector)).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath(`${name}-${width}.png`) });
    const box = await page.locator(selector).boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(width + 1);
    if (width === 390) expect((await page.locator(".workspace-header").boundingBox()).width).toBeGreaterThan(330);
    if (name === "home-report" && width === 1440) {
      const configure = await page.locator('#leaderboard a[data-workspace-route="jobs"]').boundingBox();
      const copy = await page.locator("#leaderboard [data-workspace-copy-link]").boundingBox();
      expect(configure.x + configure.width <= copy.x || copy.x + copy.width <= configure.x || configure.y + configure.height <= copy.y || copy.y + copy.height <= configure.y).toBe(true);
    }
  }
  await page.setViewportSize({ width: 1440, height: 900 });
}

test("Saved View conditions survive deletion in a fresh guest context; Trial location is independent of the list", async ({ page, context, browser }, testInfo) => {
  const fixture = await startFixture({ PEVAL_E2E_LINKS: "1", PEVAL_E2E_PASSWORD: "fixture-secret", PYTHONPATH: process.cwd() });
  const fresh = await browser.newContext({ permissions: ["clipboard-read", "clipboard-write"] });
  try {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    const headers = { Origin: fixture.origin };
    expect((await page.request.post(`${fixture.origin}/api/session`, { headers, data: { password: "fixture-secret" } })).status()).toBe(200);
    const viewPath = `${fixture.origin}/api/views/${encodeURIComponent("Original 中文")}`;
    expect((await page.request.put(viewPath, { headers, data: { filters: { state: "all", agents: ["link-target"] }, group_by: "agent" } })).status()).toBe(201);
    await page.goto(fixture.origin);
    const viewRow = page.locator("[data-view-index-row]").filter({ hasText: "Original 中文" });
    await expect(viewRow).toBeVisible();
    await page.locator("[data-leaderboard-search-input]").fill("link-target");
    await expect(page.locator(".trajectory-row")).toHaveCount(1);
    await page.locator("[data-view-save]").click();
    await page.locator("[data-view-name-input]").fill("Local 快照");
    await page.locator('[name="view_location"][value="browser"]').locator("..").click();
    await page.locator('[data-view-save-form] button[type="submit"]').click();
    const localRow = page.locator("[data-view-index-row]").filter({ hasText: "Local 快照" });
    await expect(localRow).toBeVisible();
    await localRow.locator('label').filter({ has: page.locator('input[type="checkbox"]') }).click();
    await viewRow.locator('label').filter({ has: page.locator('input[type="checkbox"]') }).click();
    await page.locator("[data-view-apply-selected]").click();
    await expect(page.locator(".trajectory-row")).toHaveCount(1);
    await page.locator("[data-summary-group-by=model]").click();
    await page.locator("[data-summary-statistic=p95]").click();
    await page.locator("[data-summary-table-toggle]").click();
    const href = await copied(page, page.locator("#leaderboard [data-workspace-copy-link]"));
    const state = decodeWorkspaceLocation("home", new URL(href)).state;
    expect(state.views.find(view => view.name === "Original 中文")).toMatchObject({ filters: { agents: ["link-target"] } });
    expect(state.views.find(view => view.name === "Local 快照")).toMatchObject({ filters: { search: "link-target" } });
    expect((await page.request.put(viewPath, { headers, data: { filters: { search: "does-not-match" }, group_by: "agent", overwrite: true } })).status()).toBe(200);
    const recipient = await fresh.newPage();
    const writes = [];
    recipient.on("request", request => { if (["PUT", "PATCH", "DELETE"].includes(request.method())) writes.push(request.url()); });
    await recipient.goto(href);
    await expect(recipient.locator(".trajectory-row")).toHaveCount(1);
    expect((await page.request.delete(viewPath, { headers })).status()).toBe(204);
    await recipient.reload();
    await expect(recipient.locator(".trajectory-row")).toHaveCount(1);
    await expect(recipient.locator("[data-shared-view-conditions]")).toContainText("Original 中文");
    await expect(recipient.locator("[data-summary-group-by=model]")).toHaveAttribute("aria-pressed", "true");
    await expect(recipient.locator("[data-summary-statistic=p95]")).toHaveAttribute("aria-pressed", "true");
    await expect(recipient.locator("[data-summary-table-toggle]")).toHaveAttribute("aria-expanded", "true");
    expect(await recipient.evaluate(() => Object.keys(localStorage).filter(key => /view/i.test(key)))).toEqual([]);
    expect((await (await recipient.request.get(`${fixture.origin}/api/session`)).json()).role).toBe("guest");
    await copied(recipient, recipient.locator("#leaderboard [data-workspace-copy-link]"));
    await screenshots(recipient, testInfo, "leaderboard", "#leaderboard [data-workspace-copy-link]");
    const catalog = await (await page.request.get(`${fixture.origin}/api/catalog?state=all`)).json();
    const target = catalog.items.find(row => row.agent_name === "psychevo");
    expect(target).toBeTruthy();
    const trialHref = encodeWorkspaceLocation("home", { object: { source: target.source_key, trajectory: "child-中文", step: "2", tab: "trajectory" }, state: { ...state, query: { ...state.query, page_size: 1 } } }, fixture.origin);
    await recipient.goto(trialHref);
    const sidebar = recipient.locator("#detail-sidebar");
    await expect(sidebar).toBeVisible();
    await expect(sidebar.locator('[data-trajectory-node][aria-current=true]')).toHaveAttribute("data-trajectory-id", "child-中文");
    await expect(sidebar.locator('.step[data-step="2"]')).toHaveAttribute("open", "");
    await expect(sidebar).toContainText("Child response");
    await expect(recipient.locator(`.trajectory-row[data-source-key="${target.source_key}"]`)).toHaveCount(0);
    await copied(recipient, sidebar.locator("[data-workspace-copy-link]"));
    await screenshots(recipient, testInfo, "trial", "#detail-sidebar [data-workspace-copy-link]");
    await recipient.reload();
    await expect(sidebar.locator('.step[data-step="2"]')).toHaveAttribute("open", "");
    const open = recipient.url();
    const historyLength = await recipient.evaluate(() => history.length);
    await sidebar.locator("[data-sidebar-close]").click();
    await expect(sidebar).toBeHidden();
    expect(new URL(recipient.url()).searchParams.has("source")).toBe(false);
    expect(await recipient.evaluate(() => history.length)).toBe(historyLength + 1);
    await recipient.goBack();
    await expect(sidebar).toBeVisible();
    expect(recipient.url()).toBe(open);
    await recipient.goForward();
    await expect(sidebar).toBeHidden();
    expect(writes).toEqual([]);
  } finally { try { await fresh.close(); } finally { await stopFixture(fixture); } }
});

test("archived reports restore through both readers, retain filters and unsaved association drafts", async ({ page, context, browser }, testInfo) => {
  const fixture = await startFixture({ PEVAL_E2E_REPORTS: "1", PEVAL_E2E_PASSWORD: "fixture-secret", PYTHONPATH: process.cwd() });
  const guest = await browser.newContext({ permissions: ["clipboard-read", "clipboard-write"] });
  try {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    const headers = { Origin: fixture.origin };
    await page.request.post(`${fixture.origin}/api/session`, { headers, data: { password: "fixture-secret" } });
    const config = await (await page.request.get(`${fixture.origin}/api/config`)).json();
    const root = config.datasets.find(item => item.id === "empty-library").path.replace(/[\\/]library-dataset$/, "");
    const report = await (await page.request.post(`${fixture.origin}/api/reports`, { headers, data: { path: `${root}/library.md` } })).json();
    const path = `${fixture.origin}/api/report-library/${encodeURIComponent(report.report_ref)}`;
    expect((await page.request.put(`${path}/state`, { headers, data: { archived: true } })).status()).toBe(200);
    const href = encodeWorkspaceLocation("reports", { object: { report: report.report_ref, tab: "associations" }, state: { query: { search: "not-in-list", kinds: ["dataset"] } } }, fixture.origin);
    await page.goto(href);
    const detail = page.locator("#report-library-detail");
    await expect(detail).toBeVisible();
    await expect(detail.locator('[data-report-tab="associations"]')).toHaveAttribute("aria-selected", "true");
    await expect(page.locator("[data-report-search]")).toHaveValue("not-in-list");
    await expect(page.locator('[data-report-kind="dataset"]')).toBeChecked();
    await expect(page.locator("[data-report-row]")).toHaveCount(0);
    const shared = await copied(page, detail.locator("[data-workspace-copy-link]"));
    await detail.locator("[data-binding-kind]").selectOption("dataset");
    await detail.locator('[data-target-key="empty-library"]').check();
    await page.locator('[data-workspace-route="home"]').first().click();
    await page.goBack();
    await expect(detail.locator("[data-association-summary]")).toContainText("empty-library");
    await detail.locator("[data-binding-kind]").selectOption("dataset");
    await expect(detail.locator('[data-target-key="empty-library"]')).toBeChecked();
    await expect(detail.locator("[data-report-save]")).toBeEnabled();
    const recipient = await guest.newPage();
    await recipient.goto(shared);
    await expect(recipient.locator("#report-library-detail")).toBeVisible();
    await expect(recipient.locator("[data-report-save]")).toHaveCount(0);
    await expect(recipient.locator('[data-report-tab="associations"]')).toHaveAttribute("aria-selected", "true");
    await screenshots(recipient, testInfo, "report-associations", "#report-library-detail [data-workspace-copy-link]");
    await recipient.reload();
    await expect(recipient.locator("#report-library-detail")).toBeVisible();
    const homeHref = encodeWorkspaceLocation("home", { object: { report: report.report_ref }, state: { query: { search: "no-trials" } } }, fixture.origin);
    await recipient.goto(homeHref);
    await expect(recipient.locator("[data-leaderboard-search-input]")).toHaveValue("no-trials");
    await expect(recipient.locator("#leaderboard [data-workspace-copy-link]")).toBeVisible();
    const reader = recipient.locator("#workspace-report-reader");
    await expect(reader).toBeVisible();
    await expect(reader.locator("iframe")).toHaveAttribute("src", `${new URL(path).pathname}/preview`);
    await copied(recipient, reader.locator("[data-workspace-copy-link]"));
    await screenshots(recipient, testInfo, "home-report", "#workspace-report-reader [data-workspace-copy-link]");
    await recipient.reload();
    await expect(reader).toBeVisible();
  } finally { try { await guest.close(); } finally { await stopFixture(fixture); } }
});

test("missing identities and invalid snapshots remain explicit and never select another object", async ({ page }) => {
  const fixture = await startFixture({ PYTHONPATH: process.cwd() });
  try {
    await page.goto(`${fixture.origin}/?source=missing-source`);
    await expect(page.getByRole("status").filter({ hasText: "unknown source" })).toBeVisible();
    expect(new URL(page.url()).searchParams.get("source")).toBe("missing-source");
    await expect(page.locator("#detail-sidebar")).toBeHidden();
    await expect(page.locator(".trajectory-row")).toHaveCount(2);
    const queries = [];
    page.on("request", request => { if (/\/api\/catalog(?:[?/-])/.test(request.url())) queries.push(request.url()); });
    const bad = `${fixture.origin}/#view=${Buffer.from('{"v":99}').toString("base64url")}`;
    await page.goto(bad);
    await expect(page.locator("[data-workspace-load-error]")).toContainText("Invalid or unsupported workspace link");
    expect(page.url()).toBe(bad);
    expect(queries).toEqual([]);
    await page.getByRole("button", { name: "Open default view" }).click();
    await expect(page.locator("[data-workspace-load-error]")).toHaveCount(0);
    await expect(page.locator(".trajectory-row")).toHaveCount(2);
  } finally { await stopFixture(fixture); }
});

test("Chinese link errors preserve the requested conditions and detail positions", async ({ page }, testInfo) => {
  const fixture = await startFixture({ PEVAL_E2E_LINKS: "1", PEVAL_E2E_LOCALE: "zh-CN", PYTHONPATH: process.cwd() });
  try {
    for (const [hash, message] of [
      [Buffer.from('{"v":99}').toString("base64url"), "工作台链接无效或版本不受支持"],
      ["a".repeat(65536), "工作台链接超过 64 KiB 限制"],
    ]) {
      const href = `${fixture.origin}/#view=${hash}`;
      await page.goto(href);
      await expect(page.locator("[data-workspace-load-error]")).toContainText(message);
      expect(page.url()).toBe(href);
    }
    await screenshots(page, testInfo, "link-error-zh", "[data-workspace-load-error]");
    await page.getByRole("button", { name: "打开默认视图" }).click();
    await expect(page.locator(".trajectory-row")).toHaveCount(2);
    const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
    const source = catalog.items.find(row => row.agent_name === "link-target").source_key;
    for (const [position, message] of [
      [{ trajectory: "missing-trajectory" }, "请求的轨迹不可用"],
      [{ step: "missing-step" }, "请求的步骤不可用"],
    ]) {
      const href = encodeWorkspaceLocation("home", { object: { source, ...position }, state: { query: { search: "link-target" } } }, fixture.origin);
      await page.goto(href);
      await expect(page.getByRole("status").filter({ hasText: message })).toBeVisible();
      expect(page.url()).toBe(href);
      await expect(page.locator("#detail-sidebar")).toBeHidden();
      await expect(page.locator("[data-leaderboard-search-input]")).toHaveValue("link-target");
    }
    await screenshots(page, testInfo, "detail-error-zh", "[data-leaderboard-search-input]");
  } finally { await stopFixture(fixture); }
});

test("a late Trial response and a pending search cannot overwrite a newer in-app navigation", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_LINKS: "1", PYTHONPATH: process.cwd() });
  let release;
  try {
    await page.goto(fixture.origin);
    await expect(page.locator(".trajectory-row")).toHaveCount(2);
    const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
    const old = catalog.items.find(row => row.agent_name === "psychevo");
    const newest = catalog.items.find(row => row.agent_name === "link-target");
    const oldPath = `/api/sources/${encodeURIComponent(old.source_key)}`;
    const ready = new Promise(resolve => {
      page.route(`**${oldPath}`, async route => {
        const response = await route.fetch();
        const wait = new Promise(done => { release = done; });
        resolve();
        await wait;
        try { await route.fulfill({ response }); } catch { /* The superseding navigation aborts this request. */ }
      });
    });
    const links = [
      encodeWorkspaceLocation("home", { object: { source: old.source_key, tab: "trajectory" } }, fixture.origin),
      encodeWorkspaceLocation("home", { object: { source: newest.source_key, step: "2", tab: "trajectory" }, state: { query: { search: "link-target" } } }, fixture.origin),
    ];
    await page.evaluate(hrefs => hrefs.forEach((href, index) => {
      const link = document.createElement("a");
      link.href = href; link.dataset.workspaceRoute = "home"; link.dataset.testRoute = String(index); link.textContent = `Trial ${index}`;
      document.body.append(link);
    }), links);
    await page.locator("[data-leaderboard-search-input]").fill("obsolete search");
    await page.locator('[data-test-route="0"]').click();
    await ready;
    await page.locator('[data-test-route="1"]').click();
    await expect(page.locator("#detail-sidebar")).toBeVisible();
    await expect(page.locator("[data-leaderboard-search-input]")).toHaveValue("link-target");
    release();
    await expect(page.locator('#detail-sidebar .step[data-step="2"]')).toHaveAttribute("open", "");
    expect(new URL(page.url()).searchParams.get("source")).toBe(newest.source_key);
    await expect(page.locator("#detail-sidebar [data-trajectory-id=child-中文]")).toHaveCount(0);
    await page.reload();
    await expect(page.locator("#detail-sidebar")).toBeVisible();
    await expect(page.locator("[data-leaderboard-search-input]")).toHaveValue("link-target");
  } finally { release?.(); await stopFixture(fixture); }
});

test("a Trial opened while a location loads retains selection and Back history", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_LINKS: "1", PYTHONPATH: process.cwd() });
  let release;
  try {
    await page.goto(fixture.origin);
    await expect(page.locator(".trajectory-row")).toHaveCount(2);
    const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
    const requested = catalog.items.find(row => row.agent_name === "psychevo");
    const clicked = catalog.items.find(row => row.agent_name === "link-target");
    const ready = new Promise(resolve => {
      page.route("**/api/reports", async route => {
        const response = await route.fetch();
        const wait = new Promise(done => { release = done; });
        resolve(); await wait; await route.fulfill({ response });
      }, { times: 1 });
    });
    const href = encodeWorkspaceLocation("home", { object: { source: requested.source_key } }, fixture.origin);
    await page.evaluate(href => {
      const link = document.createElement("a"); link.href = href;
      link.dataset.workspaceRoute = "home"; link.dataset.testRestore = ""; link.textContent = "Restore Trial";
      document.body.append(link);
    }, href);
    await page.locator("[data-test-restore]").click(); await ready;
    await page.locator(`.trajectory-row[data-source-key="${clicked.source_key}"]`).click();
    await expect(page.locator("#detail-sidebar")).toBeVisible();
    release();
    await expect.poll(() => new URL(page.url()).searchParams.get("source")).toBe(clicked.source_key);
    await page.goBack();
    await expect.poll(() => new URL(page.url()).searchParams.get("source")).toBe(requested.source_key);
    await expect(page.locator("#detail-sidebar")).toBeVisible();
  } finally { release?.(); await stopFixture(fixture); }
});
