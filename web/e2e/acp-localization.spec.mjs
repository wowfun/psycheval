import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;

test.beforeAll(async () => {
  fixture = await startFixture({ PEVAL_E2E_LOCALE: "zh-CN" });
});

test.afterAll(async () => {
  await stopFixture(fixture);
});

test("Chinese workspace supplies complete visible ACP chat labels", async ({
  context,
  page,
}) => {
  await context.grantPermissions(["clipboard-write"]);
  await page.goto(fixture.origin);
  await page.getByRole("button", { name: "Copilot" }).click();

  const drawer = page.locator("[data-acp-drawer]");
  await expect(drawer.getByRole("button", { name: "连接" })).toBeVisible();
  await expect(drawer.getByText("连接 Agent 并新建会话后开始协作。", { exact: true })).toBeVisible();
  await expect(drawer.getByText("预设", { exact: true })).toBeVisible();
  await expect(drawer.getByRole("button", { name: "使用", exact: true })).toBeVisible();
  const presets = drawer.locator("[data-acp-prompt-asset]");
  await expect(presets.locator("option")).toHaveCount(9);
  await expect(presets).toHaveValue("evaluation-review-zh-cn");

  await drawer.getByRole("button", { name: "连接" }).click();
  const chat = drawer.locator("[data-acp-chat]");
  await expect(chat.locator("textarea")).toHaveAttribute("placeholder", "询问这次评测…");
  await expect(chat.getByText("开始对话", { exact: true })).toBeVisible();
  await expect(chat.getByText("消息、工具活动和计划会显示在这里。", { exact: true })).toBeVisible();
  await expect(chat.getByRole("button", { name: "新建会话" })).toBeVisible();
  await expect(chat.getByRole("combobox", { name: "模式" })).toBeVisible();
  const addContext = chat.getByRole("button", { name: "添加上下文" });
  await expect(addContext).toBeEnabled();
  await expect.poll(() => page.evaluate(async () =>
    (await import("/assets/peval/modules/acp-client.js")).currentContext()?.value?.kind,
  )).toBe("source");
  await addContext.click();
  await expect(presets).toHaveValue("evaluation-review-zh-cn");
  await expect(chat.locator("textarea")).toHaveValue("");
  await drawer.getByRole("button", { name: "使用", exact: true }).click();
  await expect(chat.locator("textarea")).toHaveValue(/审阅附带的评测证据/);
  await chat.locator("textarea").fill("检查复制标签");
  await chat.locator(".paui-send").click();
  await expect(chat).toContainText("Synthetic response");
  await expect(chat.getByRole("button", { name: "复制" })).toHaveCount(2);
  await chat.getByRole("button", { name: "复制" }).first().click();
  await expect(chat.getByRole("button", { name: "已复制" })).toBeVisible();

  await chat.locator("textarea").fill("Show structured tools");
  await chat.locator(".paui-send").click();
  await expect(chat.locator(".paui-tool")).toHaveCount(3);
  for (const tool of await chat.locator(".paui-tool").all()) {
    await tool.locator("summary").click();
  }
  const read = chat.locator('[data-tool-block="read"]');
  await expect(read.getByRole("button", { name: "复制" })).toBeVisible();
  await read.getByRole("button", { name: "... 其余 2 行" }).click();
  await expect(read.getByRole("button", { name: "收起" })).toBeVisible();

  await chat.getByRole("button", { name: "会话", exact: true }).click();
  const dialog = chat.getByRole("dialog", { name: "会话" });
  await expect(
    dialog.getByRole("button", { name: "关闭会话" }),
  ).toHaveCount(0);
  const catalogSession = dialog
    .locator(".paui-session")
    .filter({ hasText: "Earlier session" });
  await expect(catalogSession).toContainText("现在");
  await catalogSession.hover();
  const actions = catalogSession.getByRole("button", {
    name: "Earlier session 的操作",
  });
  await expect(actions).toBeVisible();
  const actionBox = await actions.boundingBox();
  expect(actionBox?.width).toBeGreaterThanOrEqual(32);
  expect(actionBox?.height).toBeGreaterThanOrEqual(32);
  await actions.click();
  await expect(
    dialog.getByRole("menuitem", { name: "删除会话" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(actions).toBeFocused();
});

test("a saved preset remains selected when source context is attached", async ({
  page,
}) => {
  await page.goto(fixture.origin);
  const workspaceId = await page.locator("#peval-render-options").evaluate(node =>
    JSON.parse(node.textContent || "{}").workspace_id,
  );
  await page.evaluate(id => {
    window.localStorage.setItem(
      `peval:${id}:acp-client`,
      JSON.stringify({ prompt_asset_id: "report-review" }),
    );
  }, workspaceId);
  await page.reload();
  await page.getByRole("button", { name: "Copilot" }).click();

  const drawer = page.locator("[data-acp-drawer]");
  const presets = drawer.locator("[data-acp-prompt-asset]");
  await expect(presets).toHaveValue("report-review");
  await drawer.getByRole("button", { name: "连接" }).click();
  const addContext = drawer
    .locator("[data-acp-chat]")
    .getByRole("button", { name: "添加上下文" });
  await expect(addContext).toBeEnabled();
  await expect.poll(() => page.evaluate(async () =>
    (await import("/assets/peval/modules/acp-client.js")).currentContext()?.value?.kind,
  )).toBe("source");
  await addContext.click();
  await expect(presets).toHaveValue("report-review");
});
