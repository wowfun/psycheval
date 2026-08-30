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

  await page.goto(fixture.origin);
  const sourceRow = page.locator("tr[data-source-key]").first();
  await expect(sourceRow).toBeVisible();
  await sourceRow.click();
  await page.getByRole("button", { name: "Copilot" }).click();
  await page.getByRole("button", { name: "Connect" }).click();
  await expect(page.locator("[data-acp-protocol]")).toHaveCount(0);
  const chat = page.locator("[data-acp-chat]");
  const composer = chat.locator("textarea");
  await expect(composer).toBeEnabled({ timeout: 30_000 });
  await chat.getByRole("button", { name: "Add context" }).click();
  await expect(
    chat.locator('[data-pretty-aui-slot="composer-context-item"]'),
  ).toHaveCount(1);
  const prompt =
    "Reply with exactly PSYCHEVAL_PRETTY_AUI_CONTEXT_RESTORE_OK and nothing else. Do not use tools.";
  await composer.fill(prompt);
  await chat.locator(".paui-send").click();
  const liveAssistantContent = chat
    .locator('.paui-message[data-role="assistant"]')
    .locator(".paui-message__content");
  await expect(liveAssistantContent).toHaveText(
    "PSYCHEVAL_PRETTY_AUI_CONTEXT_RESTORE_OK",
    { timeout: 180_000 },
  );
  const liveUserContent = chat
    .locator('.paui-message[data-role="user"]')
    .locator(".paui-message__content");
  await expect(liveUserContent).toHaveText(prompt);

  await page.reload();
  await expect(chat.locator("textarea")).toBeEnabled({ timeout: 30_000 });
  const restoredUserContent = chat
    .locator('.paui-message[data-role="user"]')
    .locator(".paui-message__content");
  await expect(restoredUserContent).toHaveCount(1);
  await expect(restoredUserContent).toHaveText(prompt);
  const restoredAssistantContent = chat
    .locator('.paui-message[data-role="assistant"]')
    .locator(".paui-message__content");
  await expect(restoredAssistantContent).toHaveText(
    "PSYCHEVAL_PRETTY_AUI_CONTEXT_RESTORE_OK",
    { timeout: 30_000 },
  );
  await expect(chat).not.toContainText("pretty-aui-user-message-v1");
  await expect(chat.locator('[data-kind="context"]')).toHaveCount(1);

  const toolPrompt = [
    "Use the bash tool exactly once to run printf 'PSYCHEVAL_PRETTY_AUI_TOOL_OUTPUT\\n'.",
    "Then use the read tool exactly once to read /home/kevin/Projects/psycheval/package.json.",
    "After both tools finish, reply with exactly PSYCHEVAL_PRETTY_AUI_TOOL_CARDS_OK.",
  ].join(" ");
  await composer.fill(toolPrompt);
  await chat.locator(".paui-send").click();
  const allowOnce = chat.getByRole("button", { name: "Allow Once" });
  await expect(allowOnce).toBeVisible({ timeout: 60_000 });
  await allowOnce.click();
  await expect(restoredAssistantContent.last()).toHaveText(
    "PSYCHEVAL_PRETTY_AUI_TOOL_CARDS_OK",
    { timeout: 180_000 },
  );
  const terminal = chat.locator('[data-tool-block="terminal"]').last();
  const read = chat.locator('[data-tool-block="read"]').last();
  await expect(terminal).toHaveCount(1);
  await expect(read).toHaveCount(1);
  await terminal.locator("xpath=ancestor::details").locator("summary").click();
  await read.locator("xpath=ancestor::details").locator("summary").click();
  await expect(terminal).toContainText("PSYCHEVAL_PRETTY_AUI_TOOL_OUTPUT");
  await expect(read).toContainText('"name"');
  expect(await page.evaluate(() => window.__cspViolations)).toEqual([]);
  expect(errors).toEqual([]);
});
