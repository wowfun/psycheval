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
  await chat.getByRole("button", { name: "Add to message", exact: true }).click();
  await chat.getByRole("menuitem", { name: "Workbench references" }).click();
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
  await testInfo.attach("live-completed", {body: await page.screenshot(), contentType: "image/png"});
});
