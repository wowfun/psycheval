import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";
const png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg==";
let fixture;
test.beforeAll(async () => { fixture = await startFixture({PEVAL_E2E_IMAGES: "1", PEVAL_E2E_PAGED_SESSIONS:"1"}); });
test.afterAll(async () => { await stopFixture(fixture); });

test("image bytes, preview lifetime, mixed paste and page drop stay within the composer", async ({page}, testInfo) => {
  const sent = [];
  page.on("websocket", socket => socket.on("framesent", frame => {
    try { const message = JSON.parse(String(frame.payload)); if (message.method === "session/prompt") sent.push(message.params.prompt); } catch {}
  }));
  await page.addInitScript(() => {
    window.__previewURLs = new Set();
    const create = URL.createObjectURL.bind(URL);
    const revoke = URL.revokeObjectURL.bind(URL);
    URL.createObjectURL = value => { const url = create(value); window.__previewURLs.add(url); return url; };
    URL.revokeObjectURL = url => { window.__previewURLs.delete(url); revoke(url); };
  });
  await page.goto(fixture.origin);
  await page.getByRole("button", {name: "Copilot", exact: true}).click();
  await page.getByRole("button", {name: "Connect", exact: true}).click();
  const chat = page.locator("[data-acp-chat]");
  const composer = chat.locator("textarea");
  await expect(composer).toBeEnabled();
  await chat.locator('input[type="file"]').setInputFiles({name: "pixel.png", mimeType: "image/png", buffer: Buffer.from(png, "base64")});
  await expect(chat.getByRole("img", {name: "pixel.png"})).toBeVisible();
  await expect(chat).toContainText("MiB");
  const draft = () => page.evaluate(async () => (await import("/assets/peval/modules/acp-client.js")).acpState.mounted.controller.getSnapshot().draft);
  expect((await draft()).images[0].data).toBe(png);
  const previewURLs = await page.evaluate(() => [...window.__previewURLs]);
  await composer.fill("Typing preserves the decoded preview");
  await expect(composer).toHaveValue("Typing preserves the decoded preview");
  expect(await page.evaluate(() => [...window.__previewURLs])).toEqual(previewURLs);
  await composer.fill("");
  const firstSession = await page.evaluate(async () => (await import("/assets/peval/modules/acp-client.js")).acpState.mounted.controller.getSnapshot().sessionId);
  await chat.getByRole("button", {name: "New session"}).click();
  await expect.poll(() => page.evaluate(() => window.__previewURLs.size)).toBe(0);
  await page.evaluate(async id => (await import("/assets/peval/modules/acp-client.js")).acpState.mounted.controller.openSession(id), firstSession);
  await expect(chat.getByRole("img", {name: "pixel.png"})).toBeVisible();
  const paste = await composer.evaluate((node, data) => {
    const transfer = new DataTransfer();
    transfer.items.add(new File([Uint8Array.from(atob(data), c => c.charCodeAt(0))], "paste.png", {type:"image/png"}));
    transfer.setData("text/plain", "text wins");
    const event = new ClipboardEvent("paste", {bubbles:true, cancelable:true, clipboardData:transfer});
    node.dispatchEvent(event);
    return event.defaultPrevented;
  }, png);
  expect(paste).toBe(false);
  expect((await draft()).images).toHaveLength(1);
  for (const type of ["drop", "paste"]) {
    await composer.evaluate((node, {data, type}) => {
      const transfer = new DataTransfer();
      transfer.items.add(new File([Uint8Array.from(atob(data), c => c.charCodeAt(0))], `${type}.png`, {type:"image/png"}));
      node.dispatchEvent(type === "drop"
        ? new DragEvent("drop", {bubbles:true,cancelable:true,dataTransfer:transfer})
        : new ClipboardEvent("paste", {bubbles:true,cancelable:true,clipboardData:transfer}));
    }, {data:png, type});
    await expect(chat.getByRole("img", {name:`${type}.png`})).toBeVisible();
    expect((await draft()).images).toHaveLength(2);
    await chat.getByRole("button", {name:`Remove image: ${type}.png`,exact:true}).click();
    await expect(chat.getByRole("img", {name:`${type}.png`})).toHaveCount(0);
  }
  const prevented = await page.evaluate(() => {
    const transfer = new DataTransfer(); transfer.items.add(new File(["unsupported"], "file.txt", {type: "text/plain"}));
    const event = new DragEvent("drop", {bubbles:true,cancelable:true,dataTransfer:transfer});
    document.body.dispatchEvent(event); return event.defaultPrevented;
  });
  expect(prevented).toBe(true);
  await testInfo.attach("composer", {body: await page.screenshot(), contentType:"image/png"});
  await chat.locator(".paui-send").click();
  await expect.poll(() => sent.length).toBe(1);
  expect(sent[0]).toEqual([{type:"image",mimeType:"image/png",data:png}]);
  await expect.poll(() => page.evaluate(() => window.__previewURLs.size)).toBe(0);
  await expect(composer).toHaveValue("");
});

test("Chinese image validation uses localized labels and preserves the draft", async ({page}) => {
  const localized = await startFixture({PEVAL_E2E_IMAGES:"1",PEVAL_E2E_LOCALE:"zh-CN"});
  try {
    await page.goto(localized.origin);
    await page.locator("tr[data-source-key]").first().click();
    await page.getByRole("button", {name:"Copilot",exact:true}).click();
    await page.getByRole("button", {name:"连接",exact:true}).click();
    const chat = page.locator("[data-acp-chat]");
    await chat.locator("textarea").fill("保留此草稿");
    await chat.locator('input[type="file"]').setInputFiles({name:"mismatch.jpg",mimeType:"image/jpeg",buffer:Buffer.from(png,"base64")});
    await expect(chat.getByRole("alert")).toContainText("图片文件签名与 MIME 必须匹配");
    await expect(chat.locator("textarea")).toHaveValue("保留此草稿");
    await expect(chat.locator(".paui-composer-images img")).toHaveCount(0);
    await chat.getByRole("button", {name:"引用",exact:true}).click();
    await expect(page.locator(".acp-reference-picker").getByRole("checkbox", {name:"来源",exact:true})).toBeChecked();
    await page.locator(".acp-reference-picker").getByRole("button", {name:"取消",exact:true}).click();
    await expect(chat.locator("textarea")).toHaveValue("保留此草稿");
  } finally { await stopFixture(localized); }
});

test("Home reveals References when search selects the first available source in the background", async ({page}) => {
  const sourcePage = await (await page.request.get(`${fixture.origin}/api/catalog`)).json();
  const source = sourcePage.items[0];
  await page.route("**/api/catalog?*", route => route.fulfill({json: {
    ...sourcePage,
    ...(!new URL(route.request().url()).searchParams.get("search")
      ? {items: [], total: 0}
      : {items: [source], total: 1}),
  }}));
  await page.goto(fixture.origin);
  await page.getByRole("button", {name:"Copilot",exact:true}).click();
  await page.getByRole("button", {name:"Connect",exact:true}).click();
  const chat = page.locator("[data-acp-chat]");
  const composer = chat.locator("textarea");
  await composer.fill("Review this.");
  const references = chat.getByRole("button", {name:"References",exact:true});
  await expect(references).toHaveCount(0);
  await page.locator("[data-leaderboard-search-input]").fill("e2e");
  await expect(references).toBeVisible();
  const request = page.waitForRequest("**/api/acp/reference-candidates");
  await references.click();
  expect((await request).postDataJSON().reference.source_key).toBe(source.source_key);
  await page.locator(".acp-reference-picker").getByRole("button", {name:"Insert references"}).click();
  await expect(composer).toHaveValue(/Review this\.\n\nsource_ref:/);
});

test("reference preview selection preserves checks and a cancelled suspended picker stays closed", async ({page}) => {
  await page.goto(fixture.origin);
  await page.locator("tr[data-source-key]").first().click();
  await page.getByRole("button", {name:"Copilot",exact:true}).click();
  await page.getByRole("button", {name:"Connect",exact:true}).click();
  const chat = page.locator("[data-acp-chat]");
  const composer = chat.locator("textarea");
  await composer.fill("Keep this draft.");
  const openPicker = async () => {
    await chat.getByRole("button", {name:"References",exact:true}).click();
    await expect(page.locator(".acp-reference-picker")).toBeVisible();
  };
  await openPicker();
  const picker = page.locator(".acp-reference-picker");
  const checkbox = picker.getByRole("checkbox", {name:"Source",exact:true});
  const preview = picker.locator("pre").first();
  const box = await preview.boundingBox();
  await page.mouse.move(box.x + 4, box.y + 10);
  await page.mouse.down();
  await page.mouse.move(box.x + Math.min(160, box.width - 6), box.y + 10, {steps:8});
  await page.mouse.up();
  expect(await page.evaluate(() => window.getSelection().toString())).not.toBe("");
  await expect(checkbox).toBeChecked();
  await picker.getByRole("button", {name:"Insert references",exact:true}).click();
  await expect(composer).toHaveValue(/Keep this draft\.\n\nsource_ref:/);
  const draft = await composer.inputValue();
  await openPicker();
  const oldSession = await page.evaluate(async () => {
    const {acpState} = await import("/assets/peval/modules/acp-client.js");
    const {openModalSurface} = await import("/assets/peval/modules/modal-surfaces.js");
    const root = document.createElement("div");
    root.id = "synthetic-newer-modal"; root.hidden = true; root.setAttribute("aria-modal", "true");
    document.body.append(root); openModalSurface(root);
    const controller = acpState.mounted.controller;
    const id = controller.getSnapshot().sessionId;
    await controller.newSession();
    return id;
  });
  await expect(picker).toHaveCount(0);
  await page.evaluate(async id => {
    const {closeModalSurface} = await import("/assets/peval/modules/modal-surfaces.js");
    const root = document.querySelector("#synthetic-newer-modal");
    closeModalSurface(root); root.remove();
    const {acpState} = await import("/assets/peval/modules/acp-client.js");
    await acpState.mounted.controller.openSession(id);
  }, oldSession);
  await expect(picker).toHaveCount(0);
  await expect(composer).toHaveValue(draft);
});

test("Retry in the chat restores the host Disconnect action", async ({page}) => {
  await page.addInitScript(() => {
    const NativeSocket = window.WebSocket;
    window.__acpSockets = [];
    window.WebSocket = class extends NativeSocket {
      constructor(...args) { super(...args); window.__acpSockets.push(this); }
    };
  });
  await page.goto(fixture.origin);
  await page.getByRole("button", {name:"Copilot",exact:true}).click();
  const button = page.locator("[data-acp-connect]");
  await button.click();
  const chat = page.locator("[data-acp-chat]");
  await expect(chat.locator("textarea")).toBeEnabled();
  await page.evaluate(() => window.__acpSockets.at(-1).close());
  await expect(button).toHaveText("Reconnect");
  await chat.getByRole("button", {name:"Retry",exact:true}).click();
  await expect(button).toHaveText("Disconnect");
  await expect(button).toBeEnabled();
  await expect(chat.locator("textarea")).toBeEnabled();
  await button.click();
  await expect(button).toHaveText("Connect");
});

test("flat template groups support keyboard navigation and focus restoration", async ({page}) => {
  await page.goto(fixture.origin);
  await page.getByRole("button", {name:"Copilot",exact:true}).click();
  await page.getByRole("button", {name:"Connect",exact:true}).click();
  const chat = page.locator("[data-acp-chat]");
  const add = chat.getByRole("button", {name:"Add to message",exact:true});
  const mode = chat.getByRole("combobox", {name:"Mode",exact:true});
  await expect(mode).toBeVisible();
  await expect(add).toBeEnabled();
  for (const width of [1280,390]) {
    await page.setViewportSize({width,height:850});
    await add.focus();
    await page.keyboard.press("Tab");
    await expect(mode).toBeFocused();
    const addBox = await add.boundingBox(), modeBox = await mode.boundingBox();
    expect(addBox.x + addBox.width).toBeLessThanOrEqual(modeBox.x + 1);
    await add.click();
    const geometry = await chat.evaluate(host => {
      const panel = host.shadowRoot.querySelector(".paui-composer-menu__panel");
      const card = host.shadowRoot.querySelector(".paui-composer");
      const a = panel.getBoundingClientRect(), b = card.getBoundingClientRect();
      return {left: a.left-b.left, right:a.right-b.right, above:a.bottom<=b.top,
        sameColor:getComputedStyle(panel).backgroundColor===getComputedStyle(card).backgroundColor};
    });
    expect(Math.abs(geometry.left)).toBeLessThanOrEqual(1);
    expect(Math.abs(geometry.right)).toBeLessThanOrEqual(1);
    expect(geometry.above && geometry.sameColor).toBe(true);
    await page.keyboard.press("Escape");
  }
  const trigger = chat.getByRole("button", {name:"Prompts",exact:true});
  await trigger.click();
  const english = chat.getByRole("group", {name:"English",exact:true});
  const first = english.getByRole("menuitem").first();
  await expect(first).toBeFocused();
  await expect(first).toHaveCSS("outline-style", "none");
  await expect(first).not.toHaveCSS("box-shadow", "none");
  const preview = first.locator("small");
  const text = await preview.textContent();
  expect(text.trim().length).toBeGreaterThan(40);
  await expect(first).toHaveAttribute("title", text);
  await expect(first).toHaveAccessibleName("Evaluation review");
  await expect(first).toHaveAccessibleDescription(text);
  await expect(preview).toHaveCSS("text-overflow", "ellipsis");
  expect(await preview.evaluate(node => node.scrollWidth > node.clientWidth)).toBe(true);
  const menu = chat.getByRole("menu", {name:"Prompts"});
  expect(await menu.evaluate(node => getComputedStyle(node, "::-webkit-scrollbar").width)).toBe("8px");
  await page.keyboard.press("ArrowDown");
  await expect(english.getByRole("menuitem").nth(1)).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await expect(chat.getByRole("menu")).toHaveCount(0);
});

test("session organization is shared across browser contexts without writes on history open", async ({browser, page}) => {
  const other = await browser.newContext({hasTouch:true, viewport:{width:390,height:844}});
  const peer = await other.newPage();
  const alias = "Shared investigation of the oldest scored evaluation in the workspace";
  const connect = async view => {
    await view.goto(fixture.origin);
    await view.getByRole("button",{name:"Copilot",exact:true}).click();
    await view.getByRole("button",{name:"Connect",exact:true}).click();
    const chat = view.locator("[data-acp-chat]");
    await expect(chat.locator("textarea")).toBeEnabled();
    return chat;
  };
  const list = chat => chat.getByRole("button",{name:"Session",exact:true}).click();
  const action = async (chat, title, name) => {
    const row = chat.locator(".paui-session").filter({has:chat.page().locator(".paui-session__title",{hasText:title})});
    await row.hover();
    if (name !== "Rename session") {
      const actions = row.locator(".paui-session__actions button");
      await expect(actions.nth(0)).toHaveAccessibleName(`Actions for ${title}`);
      await expect(actions.nth(1)).toHaveAccessibleName(/^(Archive|Restore) session$/);
      await expect(actions.nth(2)).toHaveAccessibleName(/^(Pin|Unpin) session$/);
      await expect(chat.getByRole("tooltip")).toContainText(title);
      if (name === "Pin session") {
        const [rowBox, tipBox] = await Promise.all([row.boundingBox(), chat.getByRole("tooltip").boundingBox()]);
        expect(tipBox.x + tipBox.width).toBeLessThanOrEqual(rowBox.x);
        expect(Math.abs(tipBox.y - rowBox.y)).toBeLessThanOrEqual(2);
        const label = row.locator(".paui-session__title");
        expect(await label.evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
        await expect.poll(() => label.evaluate(el =>
          el.firstElementChild.getBoundingClientRect().right - el.getBoundingClientRect().right
        )).toBeLessThanOrEqual(1);
      }
      await row.getByRole("button",{name,exact:true}).click();
      return;
    }
    await row.click({button:"right"});
    await chat.getByRole("menuitem",{name,exact:true}).click();
  };
  try {
    await page.emulateMedia({colorScheme:"dark"});
    const first = await connect(page);
    const cursors = [];
    peer.on("websocket", socket => socket.on("framesent", frame => {
      const data = JSON.parse(String(frame.payload));
      if (data.method === "session/list") cursors.push(data.params.cursor);
    }));
    const second = await connect(peer);
    const writes = [];
    page.on("request", request => {if (request.url().endsWith("/organization") && request.method() === "PATCH") writes.push(request);});
    await list(first);
    await expect(first.locator(".pretty-aui")).toHaveCSS("color-scheme","light");
    await first.locator(".paui-drawer > header strong").hover();
    await expect(first.getByRole("button",{name:"Archived",exact:true})).toHaveCSS("background-color","rgba(0, 0, 0, 0)");
    const group = first.locator(".paui-session-group").first();
    await group.click();
    await expect(group).toHaveAttribute("aria-expanded","false");
    await expect(first.locator(".paui-session")).toHaveCount(0);
    await group.click();
    const titles = first.locator(".paui-session__title");
    await first.getByRole("button",{name:/load more/i}).click();
    await expect(titles).toContainText(["Previous page"]);
    const order = await titles.allTextContents();
    await first.getByRole("button",{name:"Previous page",exact:true}).click();
    await list(first);
    await expect(titles).toHaveText(order);
    await expect(first.locator(".paui-session").filter({hasText:"Previous page"})).not.toContainText("Idle");
    expect(writes).toHaveLength(0);
    await action(first, "Previous page", "Rename session");
    const rename = first.getByRole("textbox",{name:"Rename session"});
    await expect(rename).toBeFocused();
    await expect(rename).toHaveCSS("outline-style","none");
    await rename.fill(alias);
    await rename.press("Enter");
    await expect(first.locator(".paui-header")).toContainText(alias);
    await expect(first.getByRole("button", {name:`Actions for ${alias}`,exact:true})).toBeFocused();
    await action(first, alias, "Pin session");
    await expect(first.locator(".paui-session").first()).toContainText(alias);
    await action(first, alias, "Archive session");
    await expect(titles).not.toContainText([alias]);
    await list(second);
    await second.getByRole("button", {name:"Archived", exact:true}).click();
    await expect(second.locator(".paui-session__title")).toHaveText([alias]);
    expect(cursors).not.toContain("older");
    const archivedRow = second.locator(".paui-session");
    await expect(archivedRow.locator(".paui-session__quick").first()).toBeHidden();
    const touchMenu = archivedRow.getByRole("button",{name:`Actions for ${alias}`});
    await expect(touchMenu).toHaveCSS("opacity","1");
    await touchMenu.tap();
    await second.getByRole("menuitem",{name:"Restore session",exact:true}).tap();
    await second.getByRole("dialog").getByRole("button",{name:"Session",exact:true}).click();
    await expect(second.locator(".paui-session__title").first()).toHaveText(alias);
  } finally { await other.close(); }
});
