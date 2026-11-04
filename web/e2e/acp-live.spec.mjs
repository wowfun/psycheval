import { expect, test } from "@playwright/test";
import { mkdtemp, readFile, realpath, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, relative, isAbsolute } from "node:path";
import { randomUUID } from "node:crypto";
import { startFixture, stopFixture } from "./fixture-process.mjs";

const live = process.env.PEVAL_LIVE_OPENCODE === "1";
let fixture;
let external;
const marker = `PEVAL_READ_${randomUUID()}`;
test.skip(!live, "set PEVAL_LIVE_OPENCODE=1 for the local OpenCode ACP check");

test.beforeAll(async () => {
  external = await mkdtemp(join(tmpdir(), "peval-live-evidence-"));
  fixture = await startFixture({
    PEVAL_E2E_ACP_COMMAND: process.env.PEVAL_OPENCODE || "opencode",
    PEVAL_E2E_ACP_ARGS: JSON.stringify(["acp"]),
    PEVAL_E2E_ACP_TITLE: "OpenCode",
    PEVAL_E2E_REFERENCE_ROOT: external,
    PEVAL_E2E_REFERENCE_MARKER: marker,
  });
});

test.afterAll(async () => {
  await stopFixture(fixture);
  if (external) {
    const resolved = await realpath(external);
    const within = relative(await realpath(tmpdir()), resolved);
    if (!within || within.startsWith("..") || isAbsolute(within)) throw new Error("Unexpected live fixture cleanup path");
    await rm(resolved, { recursive: true, force: true });
  }
});

test("OpenCode plan reads external evidence through editable references and permission approval", async ({ page }, testInfo) => {
  test.setTimeout(240_000);
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(fixture.origin);
  const catalog = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
  const source = catalog.items.find(row => row.source_ref?.startsWith("harbor/live/"));
  expect(source).toBeDefined();
  await page.locator(`tr[data-source-key="${source.source_key}"]`).first().click({timeout: 10_000});
  await page.getByRole("button", { name: "Copilot", exact: true }).click();
  await page.getByRole("button", { name: "Connect", exact: true }).click();
  const chat = page.locator("[data-acp-chat]");
  const composer = chat.locator("textarea");
  await expect(composer).toBeEnabled({ timeout: 45_000 });
  await expect(chat.getByRole("combobox", { name: "Mode", exact: true })).toContainText(/plan/i);
  const model = chat.locator(".paui-model > button");
  await expect(model).toBeVisible();
  const capabilities = await page.evaluate(async () => {
    const {acpState} = await import("/assets/peval/modules/acp-client.js");
    const s = acpState.mounted.controller.getSnapshot();
    const models = s.configOptions.find(o => o.category === "model" || o.id === "model");
    return {protocol:s.protocolVersion, options:s.configOptions.map(o => ({category:o.category, id:o.id, selected:o.currentValue})),
      selectedModel: models?.options?.find(o => o.value === models.currentValue)};
  });
  await testInfo.attach("negotiated-controls", {body:JSON.stringify(capabilities), contentType:"application/json"});
  const choice = capabilities.selectedModel;
  const provider = choice?.value.match(/^([^/]+)\/.+/)?.[1];
  const qualified = provider && choice.name.startsWith(`${provider}/`);
  const shortName = qualified ? choice.name.slice(provider.length + 1) : choice?.name;
  if (qualified) await expect(model.locator("span").first()).toHaveText(shortName);
  await model.click();
  const models = chat.getByRole("menuitem", {name: /model/i});
  await expect(models).toBeVisible();
  await models.click();
  await expect(chat.getByRole("menu")).toBeVisible();
  await expect(chat.locator(".paui-model__choices button").first()).toBeVisible();
  if (qualified) {
    await expect(chat.getByText(choice.group ?? provider, {exact:true}).and(chat.locator(".paui-model__group"))).toBeVisible();
    await expect(chat.locator('.paui-model__choices button:is([aria-selected="true"],[aria-checked="true"]) span').first()).toHaveText(shortName);
  }
  await page.keyboard.press("Escape");
  await expect(models).toBeFocused();
  const effort = chat.getByRole("menuitem", {name: /effort/i});
  if (await effort.count()) {
    await effort.click();
    await expect(chat.getByRole("menu", {name:/effort/i})).toBeVisible();
    await page.keyboard.press("Escape");
  }
  await page.keyboard.press("Escape");
  await chat.getByRole("button", { name: "References", exact:true }).click();
  await page.locator(".acp-reference-picker").getByRole("button", { name: "Insert references" }).click();
  const reference = await composer.inputValue();
  expect(reference).toContain(external.replaceAll("\\", "/"));
  expect(reference).not.toContain("\\");
  expect(reference.length).toBeLessThan(3000);
  const trajectory = await readFile(join(external, "job/live-trial/agent/trajectory.json"));
  expect(trajectory.byteLength).toBeGreaterThan(2 * 1024 * 1024);
  await composer.fill(`${reference}\n\nRemain in plan mode. Use your file read tool to read verification-marker.txt in the referenced evidence_path directory. Read only that synthetic file; do not use shell, Skills, subagents, or write files. Reply with its exact content. The trajectory is large and need not be loaded for this check.`);
  await chat.locator(".paui-send").click();
  const allow = chat.getByRole("button", { name: /allow once/i });
  await expect(allow).toBeVisible({ timeout: 120_000 });
  await testInfo.attach("permission", { body: await chat.locator(".pretty-aui").innerText(), contentType: "text/plain" });
  await allow.click();
  await expect(chat.locator('.paui-message[data-role="assistant"] .paui-message__content').last()).toContainText(marker, { timeout: 120_000 });
  await expect(composer).toHaveValue("");
  await expect(chat.locator('[data-kind="context"]')).toHaveCount(0);
  expect(errors).toEqual([]);
  await testInfo.attach("live-session", { body: await chat.locator(".pretty-aui").innerText(), contentType: "text/plain" });
  const summary = chat.getByRole("button", {name:/Completed in/});
  await expect(summary).toHaveAttribute("aria-expanded", "false");
  await expect(chat.locator(".paui-message time")).toHaveCount(2);
  await summary.click();
  await expect(chat.locator(".paui-tool").first()).toBeVisible();
  await testInfo.attach("live-completed", {body: await page.screenshot(), contentType: "image/png"});
  await chat.getByRole("button", {name:"Session", exact:true}).click();
  const currentRow = chat.locator('.paui-session[data-active="true"]');
  await currentRow.hover();
  await expect(currentRow.locator(".paui-session__actions button")).toHaveCount(3);
  await expect(currentRow.getByRole("button", {name:"Pin session"})).toHaveCSS("opacity", "1");
  await expect(chat.getByRole("tooltip")).toBeVisible();
  await testInfo.attach("live-session-list", {body:await chat.screenshot(), contentType:"image/png"});
  await page.reload();
  await expect(chat.locator('.paui-message[data-role="assistant"]').last()).toContainText(marker, {timeout:45_000});
  await expect(chat.locator(".paui-message time")).toHaveCount(0);
});
