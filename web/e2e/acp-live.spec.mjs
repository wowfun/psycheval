import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

const live = process.env.PEVAL_LIVE_OPENCODE === "1";
let fixture;

test.skip(!live, "set PEVAL_LIVE_OPENCODE=1 for the local OpenCode ACP check");

test.beforeAll(async () => {
  fixture = await startFixture({
    PEVAL_E2E_ACP_COMMAND:
      process.env.PEVAL_OPENCODE || "/home/kevin/.opencode/bin/opencode",
    PEVAL_E2E_ACP_ARGS: JSON.stringify(["acp", "--pure"]),
    PEVAL_E2E_ACP_TITLE: "OpenCode",
  });
});

test.afterAll(async () => {
  await stopFixture(fixture);
});

test("local OpenCode completes a prompt through the Psycheval gateway", async ({
  page,
}) => {
  test.setTimeout(210_000);
  const errors = [];
  await page.addInitScript(() => {
    window.__cspViolations = [];
    document.addEventListener("securitypolicyviolation", event => {
      window.__cspViolations.push(event.effectiveDirective);
    });
  });
  page.on("console", message => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", error => errors.push(error.message));

  await page.goto("/");
  await page.getByRole("button", { name: "Copilot" }).click();
  await page.getByRole("button", { name: "Connect" }).click();
  await expect(page.locator("[data-acp-protocol]")).toHaveCount(0);
  const composer = page.locator("[data-acp-chat] textarea");
  await expect(composer).toBeEnabled({ timeout: 30_000 });
  await composer.fill(
    "Reply with exactly PSYCHEVAL_PRETTY_AUI_LIVE_OK and nothing else. Do not use tools.",
  );
  await page.locator("[data-acp-chat] .paui-send").click();
  await expect(page.locator("[data-acp-chat]")).toContainText(
    "PSYCHEVAL_PRETTY_AUI_LIVE_OK",
    { timeout: 180_000 },
  );
  expect(await page.evaluate(() => window.__cspViolations)).toEqual([]);
  expect(errors).toEqual([]);
});
