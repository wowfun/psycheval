import { expect, test } from "@playwright/test";
import { appendFile } from "node:fs/promises";
import { join } from "node:path";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;
test.beforeAll(async () => {
  fixture = await startFixture({ PEVAL_E2E_CLAUDE: "1", PYTHONPATH: process.cwd() });
});
test.afterAll(async () => { await stopFixture(fixture); });

test("unified session input inspects IDs and reports mixed imports independently", async ({ page }, testInfo) => {
  const local = await startFixture({ PEVAL_E2E_CLAUDE: "1", PEVAL_E2E_LOCALE: "zh-CN", PYTHONPATH: process.cwd() });
  try {
    await page.goto(new URL("/config", local.origin).href);
    const form = page.locator('[data-source-add-form][data-source-kind="path"]');
    await expect(form.locator('[name="session_id"]')).toHaveCount(0);
    const input = form.locator('[name="path"]');
    await expect(input).toHaveAccessibleName("Session ID 或文件 / 目录路径（每行一个）");
    await input.fill("root-session");
    await form.locator('[name="adapter"]').selectOption("claude");
    const inspectResponse = page.waitForResponse(response => response.url().endsWith("/api/session-inspections"));
    await form.locator("[data-session-inspect]").click();
    const response = await inspectResponse;
    const inspected = await response.json();
    expect(response.ok(), JSON.stringify(inspected)).toBe(true);
    expect(inspected.sessions.map(session => session.session_id)).toEqual(["root-session"]);
    expect(inspected.selection_required).toBe(false);
    const picker = form.locator("[data-session-picker]");
    await picker.locator("label.select-box").last().click();
    const imported = page.waitForRequest(request => request.url().endsWith("/api/source-import-operations"));
    await picker.locator("[data-session-add-selected]").click();
    expect((await imported).postDataJSON()).toMatchObject({ path: inspected.path, adapter: "claude" });
    expect((await imported).postDataJSON()).not.toHaveProperty("session_ids");
    await expect(form.locator('button[type="submit"]')).toBeEnabled();

    await input.fill("newer\n.claude/root-session.jsonl\nmissing-session");
    await form.locator('[name="adapter"]').selectOption("claude");
    for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
      await page.setViewportSize(viewport);
      const inputBounds = await input.boundingBox();
      const actions = await form.locator(".source-form-actions").boundingBox();
      expect(actions.y).toBeGreaterThanOrEqual(inputBounds.y + inputBounds.height);
      for (const button of await form.locator(".source-form-actions button").all()) {
        const bounds = await button.boundingBox();
        expect(bounds.x).toBeGreaterThanOrEqual(0);
        expect(bounds.x + bounds.width).toBeLessThanOrEqual(viewport.width);
      }
    }
    await page.screenshot({ path: testInfo.outputPath("session-import-mobile.png"), fullPage: true });
    const operationResponse = page.waitForResponse(response => response.url().endsWith("/api/source-import-operations"));
    await form.locator('button[type="submit"]').click();
    const operation = await (await operationResponse).json();
    let completed;
    await expect.poll(async () => {
      completed = await (await page.request.get(new URL(`/api/operations/${operation.id}`, local.origin).href)).json();
      return completed.completed;
    }).toBe(3);
    expect(completed.successes.map(result => result.input)).toEqual(["newer", ".claude/root-session.jsonl"]);
    expect(completed.failures).toHaveLength(1);
    expect(completed.failures[0].error).toContain("missing-session");
    const { sources } = await (await page.request.get(new URL("/api/sources", local.origin).href)).json();
    expect(sources.filter(source => source.adapter === "claude").map(source => source.session_id).sort()).toEqual(["newer", "root-session"]);
    await expect(page.locator("[data-config-page-status]")).toContainText("missing-session");
    await expect(form.locator(".source-import-results code")).toHaveText(["newer", ".claude/root-session.jsonl", "missing-session"]);
  } finally {
    await stopFixture(local);
  }
});

test("Claude project selection imports one family and navigates children without extra sources", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto(new URL("/config", fixture.origin).href);
  const form = page.locator('[data-source-add-form][data-source-kind="path"]');
  await form.locator('[name="path"]').fill(".claude");
  const inspected = page.waitForResponse(response => response.url().endsWith("/api/session-inspections"));
  await form.locator("[data-session-inspect]").click();
  const project = (await (await inspected).json()).path;
  const picker = form.locator("[data-session-picker]");
  await expect(picker.locator("[data-table-row-select]")).toHaveCount(2);
  await expect(picker.getByRole("columnheader", { name: "Updated (UTC)" })).toBeVisible();
  await expect(picker.getByRole("row").filter({ hasText: "newer" })).toContainText("2026-01-01T00:00:50.000Z");
  await expect(picker.getByRole("row").filter({ hasText: "root-session" })).toContainText("2026-01-01T00:00:08.000Z");
  await expect(picker.locator("[data-session-diagnostics] li")).toHaveCount(3);
  await expect(picker.locator("[data-session-diagnostics]")).toContainText("bad.jsonl");
  await expect(picker.locator("[data-session-diagnostics]")).toContainText("duplicate-session");
  await picker.getByRole("row").filter({ hasText: "root-session" }).locator('label.select-box').click();
  await expect(picker.locator("[data-session-add-selected]")).toBeEnabled();
  await form.locator('[name="path"]').fill(".claude/");
  await expect(picker).toBeHidden();
  await form.locator("[data-session-inspect]").click();
  await expect(picker.locator("[data-session-add-selected]")).toBeDisabled();
  await picker.getByRole("row").filter({ hasText: "root-session" }).locator('label.select-box').click();
  await picker.locator("[data-session-add-selected]").click();
  let source;
  await expect.poll(async () => {
    const { sources } = await (await page.request.get(new URL("/api/sources", fixture.origin).href)).json();
    const claude = sources.filter(row => row.adapter === "claude");
    source = claude[0];
    return claude.length;
  }).toBe(1);
  await page.goto(fixture.origin);
  await page.locator(`.trajectory-row[data-source-key="${source.source_key}"]`).click();
  const trace = page.locator("#trace");
  const sidebar = page.locator("#detail-sidebar");
  await expect(trace.locator("[data-trajectory-node]")).toHaveCount(9);
  await expect(sidebar.locator("[data-trajectory-node]")).toHaveCount(9);
  await expect(sidebar.locator("[data-trajectory-copy]")).toHaveCount(9);
  for (const id of ["claude:root-session", "claude:root-session:agent:child-0", "claude:root-session:agent:grand-0"]) {
    await sidebar.locator(`[data-trajectory-copy="${id}"]`).click();
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe("Working");
    await expect(sidebar.locator(`[data-trajectory-copy="${id}"]`)).toHaveText("Copied");
    await expect(sidebar.locator("[data-trajectory-node][aria-current]")).toHaveAttribute("data-trajectory-id", "claude:root-session");
  }
  await page.evaluate(async () => {
    await navigator.clipboard.writeText("Before fallback");
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: undefined });
  });
  const rootCopy = sidebar.locator('[data-trajectory-copy="claude:root-session"]');
  await rootCopy.click();
  await expect(rootCopy).toHaveText("Copied");
  await expect(rootCopy).toBeFocused();
  await page.evaluate(() => { delete navigator.clipboard; });
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe("Working");
  await expect(sidebar.locator(".step")).toHaveCount(2);
  await sidebar.locator('.step[data-step="2"] summary').click();
  const agentStep = sidebar.locator('.step[data-step="2"]');
  for (const [selector, expected] of [
    [".message-block", "Working"],
    [".tool-block", JSON.stringify({ prompt: "Inspect fixture" }, null, 2)],
  ]) {
    const button = agentStep.locator(selector).first().locator("[data-block-copy]");
    await button.click();
    await expect(button).toHaveText("Copied");
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(expected);
    await expect(agentStep).toHaveAttribute("open", "");
    await expect(sidebar.locator("[data-trajectory-node][aria-current]")).toHaveAttribute("data-trajectory-id", "claude:root-session");
  }
  await expect(agentStep.locator(".observation-block [data-block-copy]").first()).toBeDisabled();
  await sidebar.locator('.observation-block [data-trajectory-id="claude:root-session:agent:child-0"]').click();
  await expect(trace.locator("[data-trajectory-node][aria-current]")).toHaveAttribute("data-trajectory-id", "claude:root-session:agent:child-0");
  await expect(sidebar.locator(".step")).toHaveCount(2);
  await trace.locator('[data-trajectory-node][data-trajectory-id="claude:root-session:agent:grand-0"]').click();
  await expect(sidebar.locator('[data-trajectory-node][aria-current]')).toHaveAttribute("data-trajectory-id", "claude:root-session:agent:grand-0");
  await expect(sidebar.locator("[data-trajectory-id]").filter({ hasText: "View subagent" })).toHaveCount(0);
  await trace.getByRole("button", { name: "Parent agent" }).click();
  await expect(trace.locator("[data-trajectory-node][aria-current]")).toHaveAttribute("data-trajectory-id", "claude:root-session:agent:child-0");
  await expect(sidebar.locator('.step[data-step="2"]')).toHaveAttribute("open", "");
  await appendFile(join(project, "root-session/subagents/agent-child-0.jsonl"), `${JSON.stringify({
    type: "user", sessionId: "root-session", agentId: "child-0", isSidechain: true,
    uuid: "child-refresh", timestamp: "2026-01-01T00:00:59.000Z",
    message: { role: "user", content: "Refreshed child evidence" },
  })}\n`);
  await trace.getByRole("button", { name: "Refresh source", exact: true }).click();
  await expect(sidebar.locator(".step")).toHaveCount(3);
  await expect(sidebar).toContainText("Refreshed child evidence");
  await expect(trace.locator("[data-trajectory-node][aria-current]")).toHaveAttribute("data-trajectory-id", "claude:root-session:agent:child-0");
  const detail = await (await page.request.get(new URL(`/api/sources/${source.source_key}`, fixture.origin).href)).json();
  expect(detail.report.trajectory).toHaveLength(1);
  expect(detail.report.trajectory[0].subagent_trajectories[0].steps).toHaveLength(3);
  expect(detail.report.trajectory[0].final_metrics.total_prompt_tokens).toBe(12);

  // A long root history must not consume the sidebar's navigation row.
  await appendFile(join(project, "root-session.jsonl"), Array.from({ length: 60 }, (_, index) => `${JSON.stringify({
    type: "user", sessionId: "root-session", uuid: `long-history-${index}`,
    timestamp: "2026-01-01T00:01:00.000Z", message: { role: "user", content: `History event ${index}` },
  })}\n`).join(""));
  await trace.getByRole("button", { name: "Refresh source", exact: true }).click();
  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await sidebar.locator('[data-trajectory-node][data-trajectory-id="claude:root-session"]').click();
    await expect(sidebar.locator(".step")).toHaveCount(62);
    const navigation = await sidebar.locator(".trajectory-navigation").boundingBox();
    const steps = await sidebar.locator("[data-detail-sidebar-steps]").boundingBox();
    const heading = await sidebar.locator("#detail-sidebar-title").boundingBox();
    expect(navigation.y + navigation.height).toBeLessThanOrEqual(steps.y);
    expect(navigation.x).toBeCloseTo(heading.x, 0);
    expect(steps.height).toBeGreaterThan(100);
    const copy = sidebar.locator('[data-trajectory-copy="claude:root-session"]');
    const childCopy = sidebar.locator('[data-trajectory-copy="claude:root-session:agent:child-0"]');
    const copyBounds = await copy.boundingBox();
    const childCopyBounds = await childCopy.boundingBox();
    const nodeBounds = await sidebar.locator('[data-trajectory-node][data-trajectory-id="claude:root-session"]').boundingBox();
    expect(copyBounds.x).toBeGreaterThanOrEqual(nodeBounds.x + nodeBounds.width);
    expect(copyBounds.x + copyBounds.width).toBeCloseTo(childCopyBounds.x + childCopyBounds.width, 0);
    expect(copyBounds.x + copyBounds.width).toBeLessThanOrEqual(navigation.x + navigation.width);
    await sidebar.locator('[data-trajectory-node][data-trajectory-id="claude:root-session:agent:child-0"]').click();
    await expect(sidebar.locator("[data-trajectory-node][aria-current]")).toHaveAttribute("data-trajectory-id", "claude:root-session:agent:child-0");
    await expect(sidebar.locator(".step")).toHaveCount(3);
    const refreshedStep = sidebar.locator('.step[data-step="3"]');
    await refreshedStep.locator("summary").click();
    const block = refreshedStep.locator(".message-block");
    const blockCopy = block.locator("[data-block-copy]");
    await blockCopy.click();
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe("Refreshed child evidence");
    await expect(refreshedStep).toHaveAttribute("open", "");
    const headerBounds = await block.locator("h4").boundingBox();
    const buttonBounds = await blockCopy.boundingBox();
    const bodyBounds = await block.locator("pre").boundingBox();
    expect(buttonBounds.x).toBeGreaterThanOrEqual(headerBounds.x + headerBounds.width);
    expect(buttonBounds.y + buttonBounds.height).toBeLessThanOrEqual(bodyBounds.y);
    expect(buttonBounds.x + buttonBounds.width).toBeLessThanOrEqual(viewport.width);
  }
});
