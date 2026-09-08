import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.beforeAll(async () => {
  fixture = await startFixture({ PEVAL_E2E_CLAUDE: "1", PYTHONPATH: process.cwd() });
});
test.afterAll(async () => { await stopFixture(fixture); });

test("Connect waits for the Agent catalog before accepting clicks", async ({ page }) => {
  let release;
  const ready = new Promise(resolve => { release = resolve; });
  await page.route("**/api/acp/agents", async route => {
    await ready;
    await route.continue();
  });
  try {
    await page.goto(fixture.origin);
    await page.getByRole("button", { name: "Copilot" }).click();
    const connect = page.getByRole("button", { name: "Connect", exact: true });
    await expect(connect).toBeDisabled();
    release();
    await connect.click();
    await expect(page.locator("[data-acp-chat] textarea")).toBeEnabled();
  } finally {
    release();
  }
});

test("Configuration controls wait for their event handlers", async ({ page }) => {
  let release;
  const ready = new Promise(resolve => { release = resolve; });
  await page.route("**/pages/config-page.js*", async route => {
    await ready;
    await route.continue();
  });
  try {
    await page.goto(new URL("/config", fixture.origin).href);
    const configuration = page.locator("[data-config-page]");
    await expect(configuration).toHaveAttribute("inert", "");
    const form = configuration.locator('[data-source-add-form][data-source-kind="path"]');
    const input = form.locator('[name="path"]');
    await input.evaluate(element => element.focus());
    await expect(input).not.toBeFocused();
    release();
    await expect(configuration).not.toHaveAttribute("inert", "");
    await input.fill(".claude");
    const inspected = page.waitForResponse(response => response.url().endsWith("/api/session-inspections"));
    await form.locator("[data-session-inspect]").click();
    expect((await inspected).ok()).toBe(true);
    await expect(form.locator("[data-table-row-select]")).toHaveCount(2);
  } finally {
    release();
  }
});
