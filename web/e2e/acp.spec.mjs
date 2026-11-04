import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";

let fixture;

test.beforeAll(async () => {
  fixture = await startFixture();
});

test.afterAll(async () => {
  await stopFixture(fixture);
});

test.afterEach(async ({ page }) => {
  if (!page.isClosed()) await page.close();
  await expect
    .poll(async () => {
      const response = await fetch(new URL("/api/acp/agents", fixture.origin));
      if (!response.ok) return -1;
      const payload = await response.json();
      return payload.agents.reduce(
        (total, agent) => total + agent.connections,
        0,
      );
    })
    .toBe(0);
});

test("fixture exposes its isolated browser origin", async () => {
  expect(fixture.origin).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
  const response = await fetch(new URL("/api/session", fixture.origin));
  expect(response.ok).toBe(true);
});

for (const width of [1440, 600]) {
  test(`Copilot configuration link keeps Agent settings usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.route("**/api/acp/agents", route => route.fulfill({ json: { agents: [] } }));
    await page.goto(fixture.origin);
    const launcher = page.getByRole("button", { name: "Copilot", exact: true });
    await launcher.click();
    const drawer = page.locator("[data-acp-drawer]");
    await drawer.getByRole("link", { name: "Configure agents" }).click();
    await expect(page.locator("#acp-agents-title")).toBeFocused();
    const add = page.locator("[data-acp-agent-form-open]");
    if (width === 600) {
      await expect(drawer).toBeHidden();
      await expect(launcher).toHaveAttribute("aria-expanded", "false");
    }
    await add.click();
    await page.locator("[data-acp-agent-form-cancel]").click();
    await expect(add).toBeFocused();
    if (width === 1440) {
      await expect(drawer.locator("[data-acp-close]")).toBeInViewport();
      await expect(launcher).toHaveAttribute("aria-expanded", "true");
      await drawer.locator("[data-acp-close]").click();
      await expect(launcher).toBeFocused();
    }
  });
}

test("every new Copilot session starts in plan mode", async ({ page }) => {
  await page.goto(fixture.origin);
  await page.getByRole("button", { name: "Copilot" }).click();
  await expect(page.locator("[data-acp-agent]")).toHaveValue("synthetic");
  await page.getByRole("button", { name: "Connect" }).click();
  const chat = page.locator("[data-acp-chat]");
  const mode = chat.getByRole("combobox", { name: "Mode" });
  await expect(mode).toContainText("Plan");

  await chat.getByRole("button", { name: "New session" }).click();
  await expect(mode).toContainText("Plan");
});

test("ACP v1 fallback never flashes a connection error", async ({ page }) => {
  const sockets = [];
  page.on("websocket", socket => sockets.push(socket.url()));
  await page.goto(fixture.origin);
  await page.getByRole("button", { name: "Copilot", exact: true }).click();
  await expect(page.locator("[data-acp-connect]")).toBeEnabled();
  const observed = await page.evaluate(async () => {
    const acp = await import("/assets/peval/modules/acp-client.js");
    const connecting = acp.connectAcpAgent();
    const mounted = acp.acpState.mounted;
    const states = [];
    const alerts = [];
    const record = () => {
      const snapshot = mounted.controller.getSnapshot();
      states.push({ phase: snapshot.phase, error: snapshot.error?.code });
    };
    const unsubscribe = mounted.controller.subscribe(record);
    const host = document.querySelector("[data-acp-chat]");
    const observer = new MutationObserver(() => {
      for (const alert of host.shadowRoot.querySelectorAll('[role="alert"]')) alerts.push(alert.textContent);
    });
    observer.observe(host.shadowRoot, { subtree: true, childList: true, characterData: true, attributes: true });
    record();
    try {
      const connected = await connecting;
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      return { connected, states, alerts };
    } finally {
      observer.disconnect();
      unsubscribe();
    }
  });
  expect(observed.connected).toBe(true);
  expect(observed.states.at(-1)).toEqual({ phase: "idle", error: undefined });
  expect(observed.states.filter(state => state.phase === "error" || state.error)).toEqual([]);
  expect(observed.alerts).toEqual([]);
  expect(sockets).toHaveLength(2);
});

test("an Agent without image support rejects selection and preserves the text draft", async ({page}) => {
  await page.goto(fixture.origin);
  await page.getByRole("button", {name:"Copilot",exact:true}).click();
  await page.getByRole("button", {name:"Connect",exact:true}).click();
  const chat = page.locator("[data-acp-chat]");
  await chat.locator("textarea").fill("Keep this draft");
  await chat.locator('input[type="file"]').setInputFiles({name:"image.png",mimeType:"image/png",buffer:Buffer.from("fixture")});
  await expect(chat.getByRole("alert")).toContainText("does not accept images");
  await expect(chat.locator("textarea")).toHaveValue("Keep this draft");
  await expect(chat.locator(".paui-composer-images img")).toHaveCount(0);
});

test("disconnected drawer keeps controls above the full-height placeholder", async ({
  page,
}) => {
  await page.goto(fixture.origin);
  const body = page.locator("body");
  await expect(body).toHaveCSS("overflow-y", "visible");
  await page.getByRole("button", { name: "Copilot" }).click();
  await expect(body).toHaveCSS("overflow-y", "hidden");
  const drawer = page.locator("[data-acp-drawer]");
  const geometry = await drawer.evaluate((element) => {
    const widthProbe = document.createElement("div");
    widthProbe.style.cssText =
      "position:fixed;right:var(--workspace-sidebar-gap);visibility:hidden;width:var(--detail-sidebar-width)";
    document.body.append(widthProbe);
    const box = (selector) =>
      element.querySelector(selector).getBoundingClientRect();
    const drawerBox = element.getBoundingClientRect();
    const controls = box(".acp-controls");
    const chat = box(".acp-chat-frame");
    const placeholder = box(".acp-chat-placeholder");
    const result = {
      controlsBottom: controls.bottom,
      chatTop: chat.top,
      chatBottom: chat.bottom,
      placeholderTop: placeholder.top,
      placeholderBottom: placeholder.bottom,
      drawerBottom: drawerBox.bottom,
      drawerLeft: drawerBox.left,
      regularRightSidebarLeft: widthProbe.getBoundingClientRect().left,
    };
    widthProbe.remove();
    return result;
  });
  expect(geometry.chatTop).toBeGreaterThanOrEqual(geometry.controlsBottom);
  expect(geometry.placeholderTop).toBeGreaterThanOrEqual(geometry.chatTop);
  expect(geometry.placeholderBottom).toBeLessThanOrEqual(geometry.chatBottom);
  expect(geometry.chatBottom).toBeCloseTo(geometry.drawerBottom, 0);
  expect(geometry.drawerLeft).toBeCloseTo(
    geometry.regularRightSidebarLeft,
    0,
  );
  await drawer.getByRole("button", { name: "Close", exact: true }).click();
  await expect(body).toHaveCSS("overflow-y", "visible");
});

test("drawer aligns with the active regular right-sidebar boundary", async ({
  page,
}) => {
  await page.goto(fixture.origin);
  await page.evaluate(() => {
    document.body.classList.add("workspace-sidebar-right-open");
    document.documentElement.style.setProperty(
      "--workspace-side-region-gap",
      "27px",
    );
    document.documentElement.style.setProperty(
      "--workspace-right-sidebar-width",
      "760px",
    );
  });

  await page.getByRole("button", { name: "Copilot" }).click();
  const drawer = page.locator("[data-acp-drawer]");
  for (const width of [760, 360]) {
    await page.evaluate((nextWidth) => {
      document.documentElement.style.setProperty(
        "--workspace-right-sidebar-width",
        `${nextWidth}px`,
      );
    }, width);
    const geometry = await drawer.evaluate((element) => ({
      drawerLeft: element.getBoundingClientRect().left,
      drawerOverflow: element.scrollWidth - element.clientWidth,
      contentGap: Number.parseFloat(
        getComputedStyle(document.documentElement).getPropertyValue(
          "--workspace-side-region-gap",
        ),
      ),
      regularRightSidebarLeft:
        innerWidth -
        Number.parseFloat(
          getComputedStyle(document.body).getPropertyValue(
            "--workspace-right-sidebar-width",
          ),
        ) -
        Number.parseFloat(
          getComputedStyle(document.body).getPropertyValue(
            "--workspace-sidebar-gap",
          ),
        ),
      workspaceContentRight: document
        .querySelector(".workspace-content")
        .getBoundingClientRect().right,
    }));

    expect(geometry.drawerLeft).toBe(geometry.regularRightSidebarLeft);
    expect(geometry.drawerOverflow).toBeLessThanOrEqual(0);
    expect(geometry.drawerLeft - geometry.workspaceContentRight).toBe(
      geometry.contentGap,
    );
  }

  await page.evaluate(() => {
    document.documentElement.style.setProperty(
      "--acp-scrollbar-compensation",
      "15px",
    );
  });
  const classicScrollbarGeometry = await drawer.evaluate((element) => {
    const style = getComputedStyle(document.documentElement);
    return {
      drawerLeft: element.getBoundingClientRect().left,
      expectedLeft:
        innerWidth -
        Number.parseFloat(
          getComputedStyle(document.body).getPropertyValue(
            "--workspace-right-sidebar-width",
          ),
        ) -
        Number.parseFloat(style.getPropertyValue("--workspace-sidebar-gap")) -
        Number.parseFloat(
          style.getPropertyValue("--acp-scrollbar-compensation"),
        ),
    };
  });
  expect(classicScrollbarGeometry.drawerLeft).toBe(
    classicScrollbarGeometry.expectedLeft,
  );

  await page.setViewportSize({ width: 1100, height: 900 });
  await page.evaluate(() => {
    document.documentElement.style.setProperty(
      "--acp-scrollbar-compensation",
      "0px",
    );
    document.documentElement.style.setProperty(
      "--workspace-right-sidebar-width",
      "620px",
    );
  });
  await expect
    .poll(() => drawer.evaluate((element) => element.getBoundingClientRect().width))
    .toBe(620);
});

test("vendored ACP chat runs under the workspace CSP and keeps drawer state", async ({
  context,
  page,
}) => {
  await page.clock.setFixedTime(new Date(2026, 7, 29, 17, 30));
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
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

  const response = await page.goto(fixture.origin);
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
  await expect(drawer.locator(".acp-notice, [data-acp-notice]")).toHaveCount(0);
  expect(webSockets).toEqual([
    `${fixture.origin.replace("http://", "ws://")}/api/acp/agents/synthetic/ws`,
    `${fixture.origin.replace("http://", "ws://")}/api/acp/agents/synthetic/ws`,
  ]);

  const chat = page.locator("[data-acp-chat]");
  const noticeRows = chat.locator(
    '[data-pretty-aui-slot="activity"][data-kind="notice"]',
  );
  await expect(noticeRows).toHaveCount(1);
  await expect(noticeRows.first()).toHaveAttribute("data-level", "info");
  await expect(noticeRows.first().getByRole("status")).toHaveText(
    "Local agent connected",
  );
  await expect(noticeRows.first().locator(".paui-host-notice")).toHaveCSS(
    "background-color",
    "rgba(0, 0, 0, 0)",
  );
  const composer = chat.locator("textarea");
  await composer.fill("Review this evaluation.");
  await chat.getByRole("button", { name: "References", exact:true }).click();
  const picker = page.locator(".acp-reference-picker");
  await expect(picker).toBeVisible();
  await expect(picker.locator('input[type="checkbox"]').first()).toBeChecked();
  await picker.getByRole("button", { name: "Insert references" }).click();
  await expect(composer).toHaveValue(/Review this evaluation\.\n\nsource_ref:/);
  const insertedText = await composer.inputValue();
  expect(insertedText).toContain("peval view tr");
  expect(insertedText).toContain("evidence_path:");
  await expect(chat.locator('[data-pretty-aui-slot="composer-context-item"]')).toHaveCount(0);
  await chat.locator(".paui-send").click();
  await expect(chat).toContainText("Synthetic response: the evaluation evidence is ready for review.");
  const steps = chat.getByRole("button", {name:/Completed in/});
  await steps.click();
  await expect(chat).toContainText("Explain the failure cluster");
  await steps.click();
  await expect(chat.locator('[data-kind="context"]')).toHaveCount(0);
  await composer.fill("Review it one more time.");
  await chat.locator(".paui-send").click();
  await expect(chat.locator('[data-kind="context"]')).toHaveCount(0);
  const actionRows = chat.locator('[data-pretty-aui-slot="message-actions"]');
  await expect(actionRows).toHaveCount(4);
  await expect(chat.getByRole("button", { name: "Copy" })).toHaveCount(4);
  const firstUserMessage = chat
    .locator(".paui-turn")
    .first()
    .locator('.paui-message[data-role="user"]');
  const firstUserTime = firstUserMessage.locator("time");
  await expect(firstUserTime).toHaveText(/^\d{2}:\d{2}$/);
  await expect(firstUserTime).toHaveCSS("opacity", "1");
  await page.mouse.move(0, 0);
  await firstUserMessage.getByRole("button", { name: "Copy" }).focus();
  await expect(firstUserTime).toHaveCSS("opacity", "1");

  const copy = firstUserMessage.getByRole("button", { name: "Copy" });
  await copy.click();
  await expect(
    firstUserMessage.getByRole("button", { name: "Copied" }),
  ).toBeVisible();
  await expect
    .poll(() => page.evaluate(async () => (await navigator.clipboard.readText()).replaceAll("\r\n", "\n")))
    .toBe(insertedText);
  await expect(
    firstUserMessage.getByRole("button", { name: "Copy" }),
  ).toBeVisible();
  await composer.fill("Draft survives page navigation.");

  await chat.evaluate((element) => {
    element.dataset.navigationIdentity = "preserved";
  });
  for (const route of ["datasets", "reports", "config", "home"]) {
    await page
      .locator(`.workspace-nav-link[data-workspace-route="${route}"]`)
      .click();
    await expect(page.locator(`[data-workspace-page="${route}"]`)).toBeFocused();
    await expect(drawer).toBeVisible();
    await expect(chat).toHaveAttribute("data-navigation-identity", "preserved");
    await expect(chat).toContainText("Synthetic response");
    await expect(composer).toBeEnabled();
    await expect(composer).toHaveValue("Draft survives page navigation.");
    await expect(
      chat.locator('[data-pretty-aui-slot="composer-context-item"]'),
    ).toHaveCount(0);
  }

  const workspace = page.locator(".workspace");
  await expect(workspace).toHaveCSS("overflow-y", "auto");
  const workspaceGeometry = await workspace.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));
  expect(workspaceGeometry.scrollHeight).toBeGreaterThan(
    workspaceGeometry.clientHeight,
  );
  await workspace.evaluate((element) => {
    element.scrollTop = 0;
  });
  await workspace.getByRole("heading", { name: "Leaderboard", exact: true }).hover();
  await page.mouse.wheel(0, 500);
  await expect
    .poll(() => workspace.evaluate((element) => element.scrollTop))
    .toBeGreaterThan(0);
  await workspace.evaluate((element) => {
    element.scrollTop = 0;
  });

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
  await transcript.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });
  await expect
    .poll(() =>
      transcript.evaluate(
        (element) =>
          element.scrollHeight - element.clientHeight - element.scrollTop,
      ),
    )
    .toBeLessThanOrEqual(1);
  const bottomGap = await chat.evaluate((element) => {
    const transcript = element.shadowRoot.querySelector(".paui-body");
    const activities = element.shadowRoot.querySelectorAll(
      '[data-pretty-aui-slot="activity"]',
    );
    const last = activities.item(activities.length - 1);
    return (
      transcript.getBoundingClientRect().bottom -
      last.getBoundingClientRect().bottom
    );
  });
  expect(bottomGap).toBeLessThanOrEqual(48);
  await transcript.evaluate((element) => {
    element.scrollTop = Math.max(
      0,
      element.scrollHeight - element.clientHeight - 160,
    );
    element.dispatchEvent(new Event("scroll"));
  });
  const toBottom = chat.locator(".paui-to-bottom");
  await expect(toBottom).toBeVisible();
  const buttonOffset = await chat.evaluate((element) => {
    const transcript = element.shadowRoot.querySelector(".paui-body");
    const button = element.shadowRoot.querySelector(".paui-to-bottom");
    return (
      transcript.getBoundingClientRect().bottom -
      button.getBoundingClientRect().bottom
    );
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
  expect(
    requests.some((url) => /\/api\/acp\/agents\/[^/]+\/sessions/.test(url)),
  ).toBe(false);
  expect(
    requests.filter((url) => url.endsWith("/api/acp/reference-candidates")),
  ).toHaveLength(1);
  expect(await page.evaluate(() => window.__cspViolations)).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
});

test("restored OpenCode-shaped history shows and copies only the user query", async ({
  context,
  page,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto(fixture.origin);
  await page.getByRole("button", { name: "Copilot" }).click();
  await page.getByRole("button", { name: "Connect" }).click();
  const chat = page.locator("[data-acp-chat]");
  await expect(chat.locator("textarea")).toBeEnabled();
  await expect
    .poll(() =>
      page.evaluate(() =>
        [...Array(localStorage.length).keys()]
          .map((index) => localStorage.key(index))
          .filter((key) => key?.endsWith(":acp-client"))
          .map((key) => JSON.parse(localStorage.getItem(key)))
          .some((value) => value.sessions?.synthetic),
      ),
    )
    .toBe(true);

  await page.reload();
  await expect(chat.locator("textarea")).toBeEnabled();
  const userMessage = chat.locator('.paui-message[data-role="user"]');
  const userContent = userMessage.locator(".paui-message__content");
  await expect(userMessage).toHaveCount(1);
  await expect(userContent).toHaveText("Only the restored browser query");
  await expect(userContent).not.toContainText('"score":0');
  await expect(userContent).not.toContainText("pretty-aui-user-message-v1");
  const restoredContext = chat.locator('[data-kind="context"]');
  await expect(restoredContext).toHaveCount(1);
  await expect(restoredContext.locator("summary")).toContainText(
    "[peval://source/e2e-restored]",
  );
  await restoredContext.locator("summary").click();
  await expect(restoredContext).toContainText('"score":0');
  await expect(restoredContext).not.toContainText("pretty-aui-user-message-v1");

  await userMessage.getByRole("button", { name: "Copy" }).click();
  await expect
    .poll(() => page.evaluate(() => navigator.clipboard.readText()))
    .toBe("Only the restored browser query");
});

test("running sessions show a decorative spinner after the title", async ({
  page,
}) => {
  await page.goto(fixture.origin);
  await page.getByRole("button", { name: "Copilot" }).click();
  await page.getByRole("button", { name: "Connect" }).click();
  const chat = page.locator("[data-acp-chat]");
  const composer = chat.locator("textarea");
  await expect(composer).toBeEnabled();

  await composer.fill("Hold the running session");
  await composer.press("Enter");
  await expect(
    chat.locator('.paui-presence[data-phase="running"]'),
  ).toBeVisible();
  await chat.getByRole("button", { name: "Session", exact: true }).click();
  const runningSpinner = chat.locator(".paui-session__spinner");
  await expect(runningSpinner).toHaveCount(1);
  await expect(runningSpinner).toHaveAttribute("aria-hidden", "true");
  await expect(chat.getByText("Earlier session", { exact: true })).toBeVisible({
    timeout: 1_000,
  });
  await chat.getByRole("button", { name: "Close", exact: true }).click();
  await expect(composer).toBeEnabled({ timeout: 5_000 });
});

test("structured Execute, Read, and Diff rows expose semantic cards and copies", async ({
  context,
  page,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(fixture.origin);
  await page.getByRole("button", { name: "Copilot" }).click();
  await page.getByRole("button", { name: "Connect" }).click();
  const chat = page.locator("[data-acp-chat]");
  const composer = chat.locator("textarea");
  await expect(composer).toBeEnabled();
  await composer.fill("Show structured tools");
  await composer.press("Enter");
  await expect(chat).toContainText("Synthetic response");

  await chat.getByRole("button",{name:/Completed in/}).last().click();
  const tools = chat.locator(".paui-tool");
  await expect(tools).toHaveCount(3);
  for (const tool of await tools.all()) await tool.locator("summary").click();

  const terminal = chat.locator('[data-tool-block="terminal"]');
  await expect(terminal).toContainText("/workspace");
  await expect(terminal).toContainText("alpha");
  await terminal.getByRole("button", { name: "Copy" }).click();
  await expect
    .poll(() => page.evaluate(async () => (await navigator.clipboard.readText()).replace(/\r\n/g, "\n")))
    .toBe("alpha\nbeta\n");
  await expect(terminal.locator(".paui-tool-terminal__output")).toHaveCSS(
    "overflow-x",
    "auto",
  );

  const read = chat.locator('[data-tool-block="read"]');
  await expect(read).not.toContainText("fixture line 5");
  await read.getByRole("button", { name: "... more 2 lines" }).click();
  await expect(read).toContainText("fixture line 5");
  await expect(
    read.getByRole("button", { name: "Show less" }),
  ).toHaveAttribute("aria-expanded", "true");
  await read.getByRole("button", { name: "Copy" }).click();
  await expect
    .poll(() => page.evaluate(async () => (await navigator.clipboard.readText()).replace(/\r\n/g, "\n")))
    .toBe(
      Array.from({ length: 10 }, (_, index) => `fixture line ${index + 1}`).join(
        "\n",
      ),
    );

  const diff = chat.locator('[data-tool-block="diff"]');
  await expect(diff.locator('[data-line-kind="add"]')).toHaveCount(4);
  await expect(diff.locator('[data-line-kind="delete"]')).toHaveCount(3);
  await diff.getByRole("button", { name: "... more 3 lines" }).click();
  await expect(diff.locator('[data-line-kind="add"]')).toHaveCount(5);
  await expect(diff.locator('[data-line-kind="delete"]')).toHaveCount(5);

  expect(
    await chat.evaluate((element) => {
      const root = element.shadowRoot.querySelector(".pretty-aui");
      return root.scrollWidth - root.clientWidth;
    }),
  ).toBeLessThanOrEqual(0);
});

test("session list uses the fixed-height chat viewport and scrolls independently", async ({
  page,
}) => {
  await page.goto(fixture.origin);
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
    const rowBoxes = [...element.querySelectorAll(".paui-session")].map((row) =>
      row.getBoundingClientRect(),
    );
    return {
      lastBottom: rowBoxes.at(-1).bottom - listBox.top,
      maxRowHeight: Math.max(...rowBoxes.map((row) => row.height)),
    };
  });
  expect(compactGeometry.maxRowHeight).toBeLessThanOrEqual(56);
  expect(compactGeometry.lastBottom).toBeLessThanOrEqual(300);

  await chat.getByRole("button", { name: "Close", exact: true }).click();
  await page.setViewportSize({ width: 1440, height: 600 });
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
