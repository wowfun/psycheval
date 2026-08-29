import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;

test.beforeAll(async () => {
  fixture = await startFixture({ PEVAL_E2E_LOCALE: "zh-CN" });
});

test.afterAll(async () => {
  await stopFixture(fixture);
});

test("Chinese workspace supplies complete visible ACP chat labels", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Copilot" }).click();

  const drawer = page.locator("[data-acp-drawer]");
  await expect(drawer.getByRole("button", { name: "连接" })).toBeVisible();
  await expect(drawer.getByText("连接 Agent 并新建会话后开始协作。", { exact: true })).toBeVisible();
  await expect(drawer.getByText("预设", { exact: true })).toBeVisible();
  await expect(drawer.getByRole("button", { name: "使用", exact: true })).toBeVisible();

  await drawer.getByRole("button", { name: "连接" }).click();
  const chat = drawer.locator("[data-acp-chat]");
  await expect(chat.locator("textarea")).toHaveAttribute("placeholder", "询问这次评测…");
  await expect(chat.getByText("开始对话", { exact: true })).toBeVisible();
  await expect(chat.getByText("消息、工具活动和计划会显示在这里。", { exact: true })).toBeVisible();
  await expect(chat.getByRole("button", { name: "新建会话" })).toBeVisible();
  await expect(chat.getByRole("button", { name: "添加上下文" })).toBeVisible();
});
