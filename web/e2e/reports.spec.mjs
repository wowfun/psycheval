import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

async function reportFiles(page, origin) {
  const config = await (await page.request.get(`${origin}/api/config`)).json();
  const root = config.datasets.find(item => item.id === "empty-library").path.replace(/[\\/]library-dataset$/, "");
  return { markdown: `${root}/library.md`, html: `${root}/library.html` };
}
async function importFromPage(page, path) {
  await page.route("**/api/path-selections", route => route.fulfill({ json: { paths: [path] } }));
  const imported = page.waitForResponse(response => response.request().method() === "POST" && new URL(response.url()).pathname === "/api/reports");
  await page.locator("[data-report-import]").click();
  const response = await imported;
  expect(response.status()).toBe(201);
  const report = await response.json();
  await expect(page.locator("#report-library-detail iframe")).toHaveAttribute("src", `/api/report-library/${encodeURIComponent(report.report_ref)}/preview`);
  await expect(page.locator("#report-library-detail iframe")).toHaveAttribute("sandbox", "allow-scripts");
  await page.unroute("**/api/path-selections");
  return report;
}
async function associations(page) {
  await page.locator('[data-report-tab="associations"]').click();
  await expect(page.locator("[data-binding-kind]")).toBeVisible();
}
async function chooseKind(page, kind) {
  await page.locator("[data-binding-kind]").selectOption(kind);
  await expect(page.locator("[data-binding-picker] [data-target-status]")).toHaveText("");
}
async function save(page) {
  const saved = page.waitForResponse(response => response.request().method() === "PUT" && response.url().endsWith("/bindings"));
  await expect(page.locator("[data-report-save]")).toHaveText("Save associations");
  await page.locator("[data-report-save]").click();
  const response = await saved;
  expect(response.status()).toBe(200);
  await expect(page.locator("[data-report-save]")).toBeDisabled();
  const report = await response.json();
  await expect(page.locator(`[data-action-feedback="reports:save:${report.report_ref}"]`).first()).toContainText("Report associations saved");
  return report;
}

test("externally deleted reports close on refresh without losing another selection", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_REPORTS: "1", PYTHONPATH: process.cwd() });
  let release;
  try {
    const files = await reportFiles(page, fixture.origin);
    const headers = { Origin: fixture.origin };
    const imported = await (await page.request.post(`${fixture.origin}/api/reports`, { headers, data: { path: files.html } })).json();
    const second = await (await page.request.post(`${fixture.origin}/api/reports`, { headers, data: { path: files.markdown } })).json();
    await page.goto(`${fixture.origin}/reports`);
    const detail = page.locator("#report-library-detail");
    await page.locator(`[data-report-select="${imported.report_ref}"]`).click();
    await associations(page);
    await chooseKind(page, "dataset");
    await page.locator('[data-binding-picker] [data-target-key="empty-library"]').check();
    const deleted = await page.request.delete(`${fixture.origin}/api/report-library/${encodeURIComponent(imported.report_ref)}`, { headers });
    expect(deleted.status()).toBe(204);
    const metadataPath = `/api/report-library/${encodeURIComponent(imported.report_ref)}`;
    await page.route(`**${metadataPath}`, async route => {
      const response = await route.fetch();
      await new Promise(resolve => { release = resolve; });
      await route.fulfill({ response });
    });
    await page.locator("[data-report-manager-reload]").click();
    await expect.poll(() => Boolean(release)).toBe(true);
    // Switching selection while the old metadata request is pending must survive its 404.
    await detail.locator("[data-sidebar-close]").click();
    await page.locator('[data-report-select^="analysis:"]').click();
    release();
    await expect(page.locator("[data-report-inventory]")).toHaveAttribute("aria-busy", "false");
    await expect(detail).toBeVisible();
    await expect(detail.locator("iframe")).toHaveAttribute("src", /analysis%3A/);
    await page.unroute(`**${metadataPath}`);
    // Deleting the currently selected report must clear its detail and keep its draft.
    await detail.locator("[data-sidebar-close]").click();
    await page.locator(`[data-report-select="${second.report_ref}"]`).click();
    await associations(page);
    await chooseKind(page, "dataset");
    await page.locator('[data-binding-picker] [data-target-key="empty-library"]').check();
    expect((await page.request.delete(`${fixture.origin}/api/report-library/${encodeURIComponent(second.report_ref)}`, { headers })).status()).toBe(204);
    await page.locator("[data-report-manager-reload]").click();
    await expect(detail).toBeHidden();
    await expect(detail.locator("iframe")).toHaveCount(0);
    await expect(page.locator("body")).not.toHaveClass(/workspace-sidebar-right-open|report-library-detail-open/);
    expect(await page.evaluate(async ref => {
      const { reportLibraryStore } = await import("/assets/peval/modules/report-library-store.js");
      return { active: reportLibraryStore.activeRef, draft: reportLibraryStore.drafts.get(ref).values.size };
    }, second.report_ref)).toEqual({ active: null, draft: 1 });
  } finally { release?.(); await stopFixture(fixture); }
});

test("report details close on Escape and navigation before Home has loaded", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_REPORTS: "1", PYTHONPATH: process.cwd() });
  try {
    const files = await reportFiles(page, fixture.origin);
    await page.request.post(`${fixture.origin}/api/reports`, { headers: { Origin: fixture.origin }, data: { path: files.html } });
    await page.goto(`${fixture.origin}/reports`);
    const opener = page.locator("[data-report-select]").last();
    const detail = page.locator("#report-library-detail");
    await page.locator("[data-report-row]").last().locator("td").nth(2).click();
    await expect(detail).toBeVisible();
    const handle = detail.locator("[data-sidebar-resize]");
    const width = Number(await handle.getAttribute("aria-valuenow"));
    await handle.focus();
    await page.keyboard.press("ArrowLeft");
    await expect(handle).toHaveAttribute("aria-valuenow", String(width + 24));
    await page.keyboard.press("Escape");
    await expect(detail).toBeHidden();
    await expect(opener).toBeFocused();
    await expect(page.locator("body")).not.toHaveClass(/report-library-detail-open|workspace-sidebar-right-open/);
    await page.keyboard.press("Enter");
    await expect(detail).toBeVisible();
    await page.locator('[data-workspace-route="datasets"]').first().click();
    await expect(detail).toBeHidden();
    await expect(page.locator("body")).not.toHaveClass(/report-library-detail-open|workspace-sidebar-right-open/);
    await page.locator('[data-workspace-route="reports"]').first().click();
    await expect(detail).toBeHidden();
    await opener.click();
    await expect(detail).toBeVisible();
    await page.locator("[data-acp-open]").click();
    await expect(page.locator("body")).toHaveClass(/acp-drawer-open/);
    await page.keyboard.press("Escape");
    await expect(page.locator("body")).not.toHaveClass(/acp-drawer-open/);
    await expect(detail).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(detail).toBeHidden();
  } finally { await stopFixture(fixture); }
});

test("report filter menus open exclusively and dismiss without clearing selections", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_REPORTS: "1", PYTHONPATH: process.cwd() });
  try {
    await page.goto(`${fixture.origin}/reports`);
    const menus = page.locator(".report-filter");
    await expect(menus).toHaveCount(3);
    await expect(page.locator(".report-library-grid th")).toHaveText(["Report", "Format", "Associations", "Updated"]);
    await expect(page.locator("[data-report-toolbar]")).not.toContainText("Source type");
    await menus.nth(0).locator("summary").click();
    await page.locator('[data-report-kind="session"]').check();
    await expect(menus.nth(0)).toHaveAttribute("open", "");
    for (const kind of ["dataset", "job"]) {
      const menu = page.locator(`[data-report-filter="${kind}"]`);
      await menu.locator("summary").click();
      await expect(page.locator(".report-filter[open]")).toHaveCount(1);
      await expect(menu.locator("[data-target-key]")).toHaveCount(1);
      await menu.locator("[data-target-search]").click();
      await page.keyboard.press("Escape");
      await expect(page.locator(".report-filter[open]")).toHaveCount(0);
      await expect(menu.locator("summary")).toBeFocused();
    }
    await menus.nth(0).locator("summary").click();
    await expect(page.locator('[data-report-kind="session"]')).toBeChecked();
    await page.locator("[data-report-search]").click();
    await expect(page.locator(".report-filter[open]")).toHaveCount(0);
    await menus.nth(0).locator("summary").focus();
    await page.keyboard.press("Enter");
    await expect(page.locator('[data-report-kind="session"]')).toBeChecked();
    await page.keyboard.press("Escape");
    await expect(menus.nth(0).locator("summary")).toBeFocused();
  } finally { await stopFixture(fixture); }
});

test("Chinese report filter search stays above its input and panels fit the viewport", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_REPORTS: "1", PEVAL_E2E_LOCALE: "zh-CN", PYTHONPATH: process.cwd() });
  try {
    await page.goto(`${fixture.origin}/reports`);
    for (const width of [1440, 768, 390]) {
      await page.setViewportSize({ width, height: 900 });
      for (const kind of ["dataset", "job"]) {
        const menu = page.locator(`[data-report-filter="${kind}"]`);
        await menu.locator("summary").click();
        await expect(menu.locator("[data-target-key]")).toHaveCount(1);
        const dimensions = await menu.locator(".report-binding-search").evaluate(label => {
          const text = label.querySelector("span").getBoundingClientRect();
          const input = label.querySelector("input").getBoundingClientRect();
          const panel = label.parentElement.getBoundingClientRect();
          const range = document.createRange();
          range.selectNodeContents(label.querySelector("span"));
          return { labelBottom: text.bottom, inputTop: input.top, lines: range.getClientRects().length, left: panel.left, right: panel.right, viewport: window.innerWidth };
        });
        expect(dimensions.labelBottom).toBeLessThanOrEqual(dimensions.inputTop);
        expect(dimensions.lines).toBe(1);
        expect(dimensions.left).toBeGreaterThanOrEqual(8);
        expect(dimensions.right).toBeLessThanOrEqual(dimensions.viewport - 8);
        await menu.locator("summary").click();
      }
    }
  } finally { await stopFixture(fixture); }
});

test("report import clears feedback on cancellation and reports retryable failures", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_REPORTS: "1", PYTHONPATH: process.cwd() });
  let releasePicker;
  try {
    await page.goto(`${fixture.origin}/reports`);
    let attempts = 0;
    await page.route("**/api/path-selections", async route => {
      if (++attempts === 1) {
        await new Promise(resolve => { releasePicker = resolve; });
        await route.fulfill({ json: { paths: [] } });
      } else if (attempts === 2) {
        await route.fulfill({ status: 503, json: { detail: "Native file picker unavailable" } });
      } else await route.fulfill({ json: { paths: [] } });
    });
    const button = page.locator("[data-report-import]");
    const feedback = page.locator('[data-report-manager-status] [data-action-feedback="reports:import"]');
    await button.click();
    await expect(button).toBeDisabled();
    await expect(feedback).toContainText("Choose a file in the server's file picker");
    releasePicker();
    await expect(button).toBeEnabled();
    await expect(page.locator('[data-action-feedback="reports:import"]')).toHaveCount(0);
    await expect(page.locator("[data-report-manager-status]")).toBeHidden();
    await expect(page.locator("[data-report-row]")).toHaveCount(1);
    await button.click();
    await expect(feedback).toContainText("Native file picker unavailable");
    await expect(button).toBeEnabled();
    await button.click();
    await expect(button).toBeEnabled();
    await expect(page.locator('[data-action-feedback="reports:import"]')).toHaveCount(0);
    await expect(page.locator("[data-report-manager-status]")).toBeHidden();
  } finally { releasePicker?.(); await stopFixture(fixture); }
});

test("standalone import, mixed associations, target pagination, report drafts and Home refresh", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_REPORTS: "1", PYTHONPATH: process.cwd() });
  try {
    await page.setViewportSize({ width: 1500, height: 1000 });
    const files = await reportFiles(page, fixture.origin);
    await page.goto(`${fixture.origin}/reports`);
    const markdown = await importFromPage(page, files.markdown);
    expect(markdown.bindings).toEqual([]);
    await expect(page.locator("body")).toHaveClass(/workspace-sidebar-right-open/);
    await expect(page.frameLocator("#report-library-detail iframe").locator("h1")).toHaveText("Independent report");
    await associations(page);
    const picker = page.locator("[data-binding-picker]");
    await picker.locator("[data-target-key]").first().check();
    await picker.locator("[data-target-next]").click();
    await expect(picker.locator("[data-target-page]")).toContainText("2 /");
    await picker.locator("[data-target-key]").first().check();
    await expect(picker.locator("[data-target-selected] button")).toHaveCount(2);
    await chooseKind(page, "dataset");
    await picker.locator('[data-target-key="empty-library"]').check();
    await chooseKind(page, "job");
    await picker.locator(`[data-target-key="managed:${"a".repeat(32)}"]`).check();
    const saved = await save(page);
    expect(saved.bindings.map(item => item.kind).sort()).toEqual(["dataset", "job", "session", "session"]);

    await page.locator("#report-library-detail [data-sidebar-close]").click();
    const html = await importFromPage(page, files.html);
    await associations(page);
    await chooseKind(page, "dataset");
    await picker.locator('[data-target-key="empty-library"]').check();
    await save(page);
    const home = await (await page.request.get(`${fixture.origin}/api/reports`)).json();
    expect(home.find(item => item.report_ref === html.report_ref).source_keys).toEqual([]);
    expect(home.find(item => item.report_ref === markdown.report_ref).source_keys).toHaveLength(2);

    // Make a draft, then switch reports and pages without losing it.
    await page.locator("[data-binding-remove]").click();
    await page.locator("#report-library-detail [data-sidebar-close]").click();
    await page.locator(`[data-report-select="${markdown.report_ref}"]`).click();
    await page.evaluate(async () => {
      const { reportLibraryStore } = await import("/assets/peval/modules/report-library-store.js");
      reportLibraryStore.pageSize = 1;
      const { loadReportManagerPage } = await import("/assets/peval/modules/report-manager-page.js");
      await loadReportManagerPage({ page: 2 });
    });
    await page.locator("[data-report-manager-reload]").click();
    await expect(page.locator("[data-report-pagination]")).toContainText("2 / 3");
    await page.evaluate(async ref => {
      const { openReportPreview } = await import("/assets/peval/modules/report-manager-page.js");
      openReportPreview(ref);
    }, html.report_ref);
    await associations(page);
    await expect(page.locator("[data-binding-remove]")).toHaveCount(0);
    await expect(page.locator("[data-report-save]")).toBeEnabled();

    // A mutation from Home invalidates the report library without erasing its draft.
    await page.locator('[data-workspace-route="home"]').first().click();
    await page.evaluate(async path => {
      const { serveApi } = await import("/assets/peval/modules/http.js");
      await serveApi("/api/reports", { method: "POST", body: { path, bindings: [] } });
    }, files.markdown);
    await page.locator('[data-workspace-route="reports"]').first().click();
    await expect(page.locator("[data-report-pagination]")).toContainText("/ 4");
    await page.evaluate(async ref => (await import("/assets/peval/modules/report-manager-page.js")).openReportPreview(ref), html.report_ref);
    await associations(page);
    await expect(page.locator("[data-report-save]")).toBeEnabled();
    await save(page);
    await page.reload();
    await page.locator(`[data-report-select="${html.report_ref}"]`).click();
    await associations(page);
    await expect(page.locator("[data-binding-remove]")).toHaveCount(0);
  } finally { await stopFixture(fixture); }
});

test("canonical sources stay immutable; guest filters and reads reports without mutation controls", async ({ page, browser }) => {
  const fixture = await startFixture({ PEVAL_E2E_REPORTS: "1", PEVAL_E2E_PASSWORD: "report-fixture", PYTHONPATH: process.cwd() });
  let guest;
  try {
    const headers = { Origin: fixture.origin };
    await page.request.post(`${fixture.origin}/api/session`, { headers, data: { password: "report-fixture" } });
    const files = await reportFiles(page, fixture.origin);
    await page.request.post(`${fixture.origin}/api/reports`, { headers, data: { path: files.html } });
    await page.goto(`${fixture.origin}/reports`);
    await page.locator('[data-report-select^="analysis:"]').click();
    await associations(page);
    await expect(page.locator("[data-association-summary]")).toContainText("Original source");
    await expect(page.locator('[data-binding-kind] option[value="session"]')).toHaveCount(0);
    await expect(page.locator("[data-report-delete]")).toHaveCount(1);
    await page.locator('[data-binding-picker] [data-target-key="empty-library"]').check();
    const canonical = await save(page);
    const preview = await page.request.get(`${fixture.origin}/api/report-library/${encodeURIComponent(canonical.report_ref)}/preview`);
    expect(await preview.text()).toContain("Canonical report");

    guest = await browser.newContext();
    const guestPage = await guest.newPage();
    await guestPage.goto(`${fixture.origin}/reports`);
    await expect(guestPage.locator("[data-report-row]")).toHaveCount(2);
    await expect(guestPage.locator("[data-report-import]")).toHaveCount(0);
    await guestPage.locator('[data-report-filter="dataset"] summary').click();
    await guestPage.locator('[data-filter-picker="dataset"] [data-target-key="empty-library"]').check();
    await expect(guestPage.locator("[data-report-row]")).toHaveCount(1);
    await guestPage.locator('[data-report-filter="dataset"] summary').click();
    await guestPage.locator("[data-report-select]").click();
    await guestPage.locator('[data-report-tab="associations"]').click();
    await expect(guestPage.locator("[data-report-save],[data-report-delete],[data-report-archive],[data-binding-picker]")).toHaveCount(0);
    const rejected = await guest.request.put(`${fixture.origin}/api/report-library/${encodeURIComponent(canonical.report_ref)}/bindings`, { headers, data: { bindings: [] } });
    expect(rejected.status()).toBe(403);
    const statePath = `${fixture.origin}/api/report-library/${encodeURIComponent(canonical.report_ref)}/state`;
    expect((await page.request.put(statePath, { headers, data: { archived: true } })).status()).toBe(200);
    await guestPage.locator("[data-report-state]").selectOption("archived");
    await expect(guestPage.locator("[data-report-row]")).toHaveCount(1);
    await guestPage.locator("[data-report-select]").click();
    await expect(guestPage.locator("#report-library-detail iframe")).toBeVisible();
    await expect(guestPage.locator("[data-report-archive],[data-report-delete]")).toHaveCount(0);
    expect((await guest.request.put(statePath, { headers, data: { archived: false } })).status()).toBe(403);
    expect((await guest.request.delete(statePath.replace(/\/state$/, ""), { headers })).status()).toBe(403);
  } finally { await guest?.close(); await stopFixture(fixture); }
});

for (const origin of ["evaluation", "imported"]) {
  test(`${origin} report archives, restores, and deletes with Home refresh and retained evidence`, async ({ page }) => {
    const fixture = await startFixture({ PEVAL_E2E_REPORTS: "1", PYTHONPATH: process.cwd() });
    try {
      const headers = { Origin: fixture.origin };
      await page.goto(`${fixture.origin}/reports`);
      const canonical = (await (await page.request.get(`${fixture.origin}/api/report-library`)).json()).items.find(item => item.origin === "evaluation");
      const files = await reportFiles(page, fixture.origin);
      const selected = origin === "imported" ? await importFromPage(page, files.markdown) : canonical;
      const ref = selected.report_ref;
      const resource = `${fixture.origin}/api/report-library/${encodeURIComponent(ref)}`;
      const row = page.locator(`[data-report-select="${ref}"]`);
      const homeReport = page.locator(`[data-workspace-page="home"] [data-report-preview="${selected.report_id}"]`);
      if (origin === "imported") {
        expect((await page.request.put(`${resource}/bindings`, { headers, data: { bindings: [{ kind: "session", key: canonical.source_keys[0] }] } })).status()).toBe(200);
        await page.locator('[data-workspace-route="home"]').first().click();
        await expect(homeReport).toBeVisible();
        await page.locator('[data-workspace-route="reports"]').first().click();
      }
      await row.click();
      const archived = page.waitForResponse(response => response.request().method() === "PUT" && response.url() === `${resource}/state`);
      await page.locator("[data-report-archive]").click();
      expect((await archived).status()).toBe(200);
      await expect(row).toHaveCount(0);
      await expect(page.locator("#report-library-detail")).toBeHidden();
      await page.reload();
      await expect(row).toHaveCount(0);
      await page.locator("[data-report-state]").selectOption("archived");
      await row.click();
      await expect(page.locator("[data-report-archive]")).toHaveText("Restore report");
      expect((await page.request.get(`${resource}/preview`)).status()).toBe(200);
      if (origin === "imported") {
        await page.locator('[data-workspace-route="home"]').first().click();
        await expect(homeReport).toHaveCount(0);
        await page.locator('[data-workspace-route="reports"]').first().click();
        await row.click();
      }
      const restored = page.waitForResponse(response => response.request().method() === "PUT" && response.url() === `${resource}/state`);
      await page.locator("[data-report-archive]").click();
      expect((await restored).status()).toBe(200);
      await expect(row).toHaveCount(0);
      await page.locator("[data-report-state]").selectOption("active");
      if (origin === "imported") {
        await page.locator('[data-workspace-route="home"]').first().click();
        await expect(homeReport).toBeVisible();
        await page.locator('[data-workspace-route="reports"]').first().click();
      }
      const sourceReportContainsCanonical = async () => page.evaluate(async key => {
        const { selectServeDetail } = await import("/assets/peval/modules/serve-catalog.js");
        const { state } = await import("/assets/peval/modules/runtime.js");
        await selectServeDetail(key, { openSidebar: true });
        return { selected: state.selectedSourceKey, contains: JSON.stringify(state.view).includes("Canonical report") };
      }, canonical.source_keys[0]);
      if (origin === "evaluation") {
        await page.locator('[data-workspace-route="home"]').first().click();
        expect((await sourceReportContainsCanonical()).contains).toBe(true);
        await page.locator('[data-workspace-route="reports"]').first().click();
      }
      await row.click();
      page.once("dialog", dialog => dialog.dismiss());
      await page.locator("[data-report-delete]").click();
      await expect(row).toBeVisible();
      page.once("dialog", dialog => { expect(dialog.message()).toContain("evidence"); return dialog.accept(); });
      const deleted = page.waitForResponse(response => response.request().method() === "DELETE" && response.url() === resource);
      await page.locator("[data-report-delete]").click();
      expect((await deleted).status()).toBe(204);
      await expect(row).toHaveCount(0);
      await expect(page.locator("#report-library-detail")).toBeHidden();
      expect((await page.request.get(`${resource}/preview`)).status()).toBe(404);
      const targets = await (await page.request.get(`${fixture.origin}/api/report-library/targets?kind=session`)).json();
      expect(targets.items.some(item => item.key === canonical.source_keys[0])).toBe(true);
      if (origin === "evaluation") {
        await page.locator('[data-workspace-route="home"]').first().click();
        expect(await sourceReportContainsCanonical()).toEqual({ selected: canonical.source_keys[0], contains: false });
      }
      if (origin === "imported") {
        const reimported = await page.request.post(`${fixture.origin}/api/reports`, { headers, data: { path: files.markdown } });
        expect(reimported.status()).toBe(201);
        expect((await reimported.json()).archived).toBe(false);
      }
    } finally { await stopFixture(fixture); }
  });
}

test("failed saves retry; late saves and list responses preserve newer edits and selection", async ({ page }) => {
  const fixture = await startFixture({ PEVAL_E2E_REPORTS: "1", PYTHONPATH: process.cwd() });
  let releaseSave;
  let releaseRead;
  try {
    const files = await reportFiles(page, fixture.origin);
    const imported = [];
    for (const path of [files.markdown, files.html]) {
      imported.push(await (await page.request.post(`${fixture.origin}/api/reports`, { headers: { Origin: fixture.origin }, data: { path } })).json());
    }
    const [markdown, html] = imported;
    await page.goto(`${fixture.origin}/reports`);
    await page.locator(`[data-report-select="${markdown.report_ref}"]`).click();
    await associations(page);
    await chooseKind(page, "dataset");
    await page.locator('[data-binding-picker] [data-target-key="empty-library"]').check();
    let attempts = 0;
    let announceSave;
    const saveStarted = new Promise(resolve => { announceSave = resolve; });
    await page.route("**/api/report-library/*/bindings", async route => {
      if (++attempts === 1) {
        await route.fulfill({ status: 503, contentType: "application/problem+json", body: JSON.stringify({ detail: "Temporary save failure" }) });
        return;
      }
      const response = await route.fetch();
      const held = new Promise(resolve => { releaseSave = resolve; });
      announceSave();
      await held;
      await route.fulfill({ response });
    });
    await page.locator("[data-report-save]").click();
    await expect(page.locator('[data-action-feedback^="reports:save:"]').first()).toContainText("Temporary save failure");
    await expect(page.locator("[data-report-save]")).toBeEnabled();
    await page.locator("[data-report-save]").click();
    await saveStarted;
    await chooseKind(page, "job");
    await page.locator('[data-binding-picker] [data-target-key]').check();
    await page.locator("#report-library-detail [data-sidebar-close]").click();
    await page.locator(`[data-report-select="${html.report_ref}"]`).click();
    releaseSave();
    await expect.poll(() => page.evaluate(async ref => {
      const { reportLibraryStore } = await import("/assets/peval/modules/report-library-store.js");
      const draft = reportLibraryStore.drafts.get(ref);
      return { saving: draft.saving, count: draft.values.size, active: reportLibraryStore.activeRef };
    }, markdown.report_ref)).toEqual({ saving: false, count: 2, active: html.report_ref });
    await page.unroute("**/api/report-library/*/bindings");
    await page.locator("#report-library-detail [data-sidebar-close]").click();
    await page.locator(`[data-report-select="${markdown.report_ref}"]`).click();
    await associations(page);
    await expect(page.locator("[data-binding-remove]")).toHaveCount(2);
    await expect(page.locator("[data-report-save]")).toBeEnabled();
    await save(page);

    let announceRead;
    const readStarted = new Promise(resolve => { announceRead = resolve; });
    let reads = 0;
    await page.route("**/api/report-library?*", async route => {
      if (++reads > 1) { await route.continue(); return; }
      const response = await route.fetch();
      const held = new Promise(resolve => { releaseRead = resolve; });
      announceRead();
      await held;
      await route.fulfill({ response });
    });
    await page.locator("[data-report-manager-reload]").click();
    await readStarted;
    await page.locator("[data-report-search]").fill("library.html");
    await expect(page.locator("[data-report-row]")).toHaveCount(1);
    releaseRead();
    await expect(page.locator("[data-report-row]")).toHaveCount(1);
    await expect(page.locator("[data-report-select]")).toHaveText("library.html");
  } finally { releaseSave?.(); releaseRead?.(); await stopFixture(fixture); }
});
