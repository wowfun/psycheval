import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;

test.beforeAll(async () => {
  fixture = await startFixture();
});

test.afterAll(async () => {
  await stopFixture(fixture);
});

test("disconnected drawer keeps controls, placeholder, and presets in separate rows", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Copilot" }).click();
  const drawer = page.locator("[data-acp-drawer]");
  const geometry = await drawer.evaluate(element => {
    const box = selector => element.querySelector(selector).getBoundingClientRect();
    const drawerBox = element.getBoundingClientRect();
    const controls = box(".acp-controls");
    const chat = box(".acp-chat-frame");
    const placeholder = box(".acp-chat-placeholder");
    const presets = box(".acp-prompt-assets");
    return {
      controlsBottom: controls.bottom,
      chatTop: chat.top,
      chatBottom: chat.bottom,
      placeholderTop: placeholder.top,
      placeholderBottom: placeholder.bottom,
      presetsTop: presets.top,
      presetsBottom: presets.bottom,
      presetsHeight: presets.height,
      drawerBottom: drawerBox.bottom,
    };
  });
  expect(geometry.chatTop).toBeGreaterThanOrEqual(geometry.controlsBottom);
  expect(geometry.placeholderTop).toBeGreaterThanOrEqual(geometry.chatTop);
  expect(geometry.placeholderBottom).toBeLessThanOrEqual(geometry.chatBottom);
  expect(geometry.presetsTop).toBeGreaterThanOrEqual(geometry.chatBottom);
  expect(geometry.presetsBottom).toBeLessThanOrEqual(geometry.drawerBottom + 1);
  expect(geometry.presetsHeight).toBeLessThanOrEqual(96);
});

test("vendored ACP chat runs under the workspace CSP and keeps drawer state", async ({
  page,
}) => {
  const consoleErrors = [];
  const pageErrors = [];
  const requests = [];
  const webSockets = [];
  await page.addInitScript(() => {
    window.__cspViolations = [];
    document.addEventListener("securitypolicyviolation", (event) => {
      window.__cspViolations.push({
        directive: event.effectiveDirective,
        blocked: event.blockedURI,
      });
    });
  });
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => requests.push(request.url()));
  page.on("websocket", (socket) => webSockets.push(socket.url()));

  const response = await page.goto("/");
  const csp = response.headers()["content-security-policy"];
  expect(csp).toContain("script-src 'self' 'nonce-");
  expect(csp).not.toContain("'unsafe-eval'");

  const sourceRow = page.locator("tr[data-source-key]").first();
  await expect(sourceRow).toBeVisible();
  const sourceKey = await sourceRow.getAttribute("data-source-key");
  await sourceRow.click();
  await page.getByRole("button", { name: "Copilot" }).click();
  const drawer = page.locator("[data-acp-drawer]");
  await expect(drawer.locator(".acp-drawer-head")).toHaveCount(0);
  await expect(
    drawer.getByRole("heading", { name: "Psycheval Copilot" }),
  ).toHaveCount(0);
  const controlsGeometry = await drawer
    .locator(".acp-controls")
    .evaluate((element) => ({
      drawerTop: element.closest("[data-acp-drawer]").getBoundingClientRect()
        .top,
      controlsTop: element.getBoundingClientRect().top,
    }));
  expect(controlsGeometry.controlsTop).toBeCloseTo(
    controlsGeometry.drawerTop,
    0,
  );
  await expect(drawer.locator(".acp-context-bar")).toHaveCount(0);
  await page.getByRole("button", { name: "Connect" }).click();
  await expect(page.locator("[data-acp-protocol]")).toHaveCount(0);
  await expect(page.locator("[data-acp-chat] textarea")).toBeEnabled();
  expect(webSockets).toEqual([
    "ws://127.0.0.1:4178/api/acp/agents/synthetic/ws",
    "ws://127.0.0.1:4178/api/acp/agents/synthetic/ws",
  ]);

  const chat = page.locator("[data-acp-chat]");
  const composer = chat.locator("textarea");
  const addContext = chat.getByRole("button", { name: "Add context" });
  await expect(addContext).toBeEnabled();
  await addContext.click();
  await expect(
    chat.locator('[data-pretty-aui-slot="composer-context-item"]'),
  ).toHaveCount(1);
  await expect(chat.locator('[data-pretty-aui-slot="composer-context"]')).toContainText(
    sourceKey,
  );
  const secondSourceRow = page.locator("tr[data-source-key]").nth(1);
  await expect(secondSourceRow).toBeVisible();
  const secondSourceKey = await secondSourceRow.getAttribute("data-source-key");
  await secondSourceRow.click();
  await addContext.click();
  await addContext.click();
  await expect(
    chat.locator('[data-pretty-aui-slot="composer-context-item"]'),
  ).toHaveCount(2);
  await expect(chat.locator('[data-pretty-aui-slot="composer-context"]')).toContainText(
    secondSourceKey,
  );
  const contextInputOrder = await chat.evaluate(element => {
    const selection = element.shadowRoot.querySelector(
      '[data-pretty-aui-slot="composer-context"]',
    );
    const input = element.shadowRoot.querySelector("textarea");
    return Boolean(
      selection.compareDocumentPosition(input) & Node.DOCUMENT_POSITION_FOLLOWING,
    );
  });
  expect(contextInputOrder).toBe(true);
  await composer.fill("Review this evaluation.");
  await chat.locator(".paui-send").click();
  await expect(page.locator("[data-acp-chat]")).toContainText(
    "Synthetic response: the evaluation evidence is ready for review.",
  );
  await expect(chat).toContainText("Explain the failure cluster");
  await expect(chat.locator('[data-kind="context"]')).toHaveCount(2);

  await composer.fill("Review it one more time.");
  await chat.locator(".paui-send").click();
  await expect(chat.locator('[data-kind="context"]')).toHaveCount(4);
  const contexts = chat.locator('[data-kind="context"]');
  for (let index = 0; index < 4; index += 1) {
    const context = contexts.nth(index);
    await expect(context.locator("details")).not.toHaveAttribute("open", "");
    await context.locator("summary").click();
    await expect(context).toContainText("peval://source/");
    await expect(context).toContainText('"reference"');
    await expect(context).toContainText(/e2e-trial/);
  }

  const firstTurnOrder = await chat
    .locator(".paui-turn")
    .first()
    .evaluate((turn) => {
      const user = turn.querySelector('[data-role="user"]');
      const context = turn.querySelector('[data-kind="context"]');
      const assistant = turn.querySelector('[data-kind="assistant"]');
      if (!user || !context || !assistant)
        throw new Error("incomplete turn timeline");
      return {
        userBeforeContext: Boolean(
          user.compareDocumentPosition(context) &
          Node.DOCUMENT_POSITION_FOLLOWING,
        ),
        contextBeforeAssistant: Boolean(
          context.compareDocumentPosition(assistant) &
          Node.DOCUMENT_POSITION_FOLLOWING,
        ),
      };
    });
  expect(firstTurnOrder).toEqual({
    userBeforeContext: true,
    contextBeforeAssistant: true,
  });

  await chat.evaluate((element) => {
    element.dataset.navigationIdentity = "preserved";
  });
  for (const route of ["datasets", "reports", "config", "home"]) {
    await page
      .locator(`.workspace-nav-link[data-workspace-route="${route}"]`)
      .click();
    await expect(drawer).toBeVisible();
    await expect(chat).toHaveAttribute("data-navigation-identity", "preserved");
    await expect(chat).toContainText("Synthetic response");
    await expect(composer).toBeEnabled();
    await expect(
      chat.locator('[data-pretty-aui-slot="composer-context-item"]'),
    ).toHaveCount(2);
  }

  const transcript = chat.locator(".paui-body");
  const scrollGeometry = await transcript.evaluate((element) => {
    element.scrollTop = 0;
    return {
      clientHeight: element.clientHeight,
      overflowY: getComputedStyle(element).overflowY,
      scrollHeight: element.scrollHeight,
    };
  });
  expect(scrollGeometry.overflowY).toBe("auto");
  expect(scrollGeometry.scrollHeight).toBeGreaterThan(
    scrollGeometry.clientHeight,
  );
  const transcriptBox = await transcript.boundingBox();
  if (!transcriptBox) throw new Error("missing transcript geometry");
  await page.mouse.move(transcriptBox.x + 2, transcriptBox.y + 80);
  await page.mouse.wheel(0, 500);
  await expect
    .poll(() => transcript.evaluate((element) => element.scrollTop))
    .toBeGreaterThan(0);
  await expect(composer).toBeInViewport();
  for (let index = 0; index < 4; index += 1) {
    await contexts.nth(index).locator("summary").click();
  }

  await transcript.evaluate(element => {
    element.scrollTop = element.scrollHeight;
  });
  await expect
    .poll(() =>
      transcript.evaluate(
        element => element.scrollHeight - element.clientHeight - element.scrollTop,
      ),
    )
    .toBeLessThanOrEqual(1);
  const bottomGap = await chat.evaluate(element => {
    const transcript = element.shadowRoot.querySelector(".paui-body");
    const activities = element.shadowRoot.querySelectorAll(
      '[data-pretty-aui-slot="activity"]',
    );
    const last = activities.item(activities.length - 1);
    return transcript.getBoundingClientRect().bottom - last.getBoundingClientRect().bottom;
  });
  expect(bottomGap).toBeLessThanOrEqual(48);
  await transcript.evaluate(element => {
    element.scrollTop = Math.max(0, element.scrollHeight - element.clientHeight - 160);
    element.dispatchEvent(new Event("scroll"));
  });
  const toBottom = chat.locator(".paui-to-bottom");
  await expect(toBottom).toBeVisible();
  const buttonOffset = await chat.evaluate(element => {
    const transcript = element.shadowRoot.querySelector(".paui-body");
    const button = element.shadowRoot.querySelector(".paui-to-bottom");
    return transcript.getBoundingClientRect().bottom - button.getBoundingClientRect().bottom;
  });
  expect(buttonOffset).toBeLessThanOrEqual(24);

  await drawer.getByRole("button", { name: "Close", exact: true }).click();
  await expect(page.locator("[data-acp-drawer]")).toBeHidden();
  await page.getByRole("button", { name: "Copilot" }).click();
  await expect(page.locator("[data-acp-chat]")).toContainText(
    "Synthetic response",
  );
  await expect(page.locator("[data-acp-drawer]")).toHaveScreenshot(
    "acp-drawer.png",
    { animations: "disabled" },
  );
  await chat
    .locator('[data-pretty-aui-slot="composer-context-item"]')
    .first()
    .getByRole("button")
    .click();
  await expect(
    chat.locator('[data-pretty-aui-slot="composer-context-item"]'),
  ).toHaveCount(1);

  expect(
    requests.some((url) => /\/api\/acp\/agents\/[^/]+\/sessions/.test(url)),
  ).toBe(false);
  expect(
    requests.filter((url) => url.endsWith("/api/acp/context-resolutions")),
  ).toHaveLength(4);
  expect(await page.evaluate(() => window.__cspViolations)).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
});

test("session list uses the fixed-height chat viewport and scrolls independently", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Copilot" }).click();
  await page.getByRole("button", { name: "Connect" }).click();
  const chat = page.locator("[data-acp-chat]");
  await expect(chat.locator("textarea")).toBeEnabled();

  const newChat = chat.getByRole("button", { name: "New session" });
  for (let index = 0; index < 4; index += 1) {
    await newChat.click();
    await expect(newChat).toBeEnabled();
  }
  await chat.getByRole("button", { name: "Session", exact: true }).click();
  const list = chat.locator(".paui-session-list");
  await expect(list).toBeVisible();
  const compactGeometry = await list.evaluate((element) => {
    const listBox = element.getBoundingClientRect();
    const rowBoxes = [...element.querySelectorAll(".paui-session")].map(
      (row) => row.getBoundingClientRect(),
    );
    return {
      lastBottom: rowBoxes.at(-1).bottom - listBox.top,
      maxRowHeight: Math.max(...rowBoxes.map((row) => row.height)),
    };
  });
  expect(compactGeometry.maxRowHeight).toBeLessThanOrEqual(56);
  expect(compactGeometry.lastBottom).toBeLessThanOrEqual(300);

  await chat.getByRole("button", { name: "Close", exact: true }).click();
  for (let index = 0; index < 8; index += 1) {
    await newChat.click();
    await expect(newChat).toBeEnabled();
  }
  await chat.getByRole("button", { name: "Session", exact: true }).click();
  await expect(list).toBeVisible();
  const geometry = await chat.evaluate((element) => {
    const shadow = element.shadowRoot;
    const root = shadow.querySelector(".pretty-aui");
    const backdrop = shadow.querySelector(".paui-drawer-backdrop");
    const drawer = shadow.querySelector(".paui-drawer");
    const list = shadow.querySelector(".paui-session-list");
    const rootBox = root.getBoundingClientRect();
    const backdropBox = backdrop.getBoundingClientRect();
    const drawerBox = drawer.getBoundingClientRect();
    const listBox = list.getBoundingClientRect();
    return {
      backdropBottom: backdropBox.bottom,
      backdropHeight: backdropBox.height,
      drawerBottom: drawerBox.bottom,
      listBottom: listBox.bottom,
      listClientHeight: list.clientHeight,
      listOverflowY: getComputedStyle(list).overflowY,
      listScrollHeight: list.scrollHeight,
      rootBottom: rootBox.bottom,
      rootHeight: rootBox.height,
    };
  });
  expect(
    Math.abs(geometry.backdropHeight - geometry.rootHeight),
  ).toBeLessThanOrEqual(2);
  expect(geometry.backdropBottom).toBeLessThanOrEqual(geometry.rootBottom + 1);
  expect(geometry.drawerBottom).toBeLessThanOrEqual(geometry.rootBottom + 1);
  expect(geometry.listBottom).toBeLessThanOrEqual(geometry.drawerBottom + 1);
  expect(geometry.listClientHeight).toBeGreaterThan(200);
  expect(geometry.listOverflowY).toBe("auto");
  expect(geometry.listScrollHeight).toBeGreaterThan(geometry.listClientHeight);

  await list.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });
  await expect
    .poll(() => list.evaluate((element) => element.scrollTop))
    .toBeGreaterThan(0);
});
