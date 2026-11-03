import { expect, test } from "@playwright/test";
import { startFixture, stopFixture } from "./fixture-process.mjs";
const png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg==";
let fixture;
test.beforeAll(async () => { fixture = await startFixture({PEVAL_E2E_IMAGES: "1"}); });
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
    await chat.getByRole("button", {name:"添加到消息",exact:true}).click();
    await chat.getByRole("menuitem", {name:"工作台引用",exact:true}).click();
    await expect(page.locator(".acp-reference-picker").getByRole("checkbox", {name:"来源",exact:true})).toBeChecked();
    await page.locator(".acp-reference-picker").getByRole("button", {name:"取消",exact:true}).click();
    await expect(chat.locator("textarea")).toHaveValue("保留此草稿");
  } finally { await stopFixture(localized); }
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
    await chat.getByRole("button", {name:"Add to message",exact:true}).click();
    await chat.getByRole("menuitem", {name:"Workbench references",exact:true}).click();
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

test("the single menu supports nested keyboard navigation and focus restoration", async ({page}) => {
  await page.goto(fixture.origin);
  await page.getByRole("button", {name:"Copilot",exact:true}).click();
  await page.getByRole("button", {name:"Connect",exact:true}).click();
  const chat = page.locator("[data-acp-chat]");
  const trigger = chat.getByRole("button", {name:"Add to message",exact:true});
  await trigger.click();
  await chat.getByRole("menuitem", {name:/^Prompt templates/}).focus();
  await page.keyboard.press("ArrowRight");
  await expect(chat.getByRole("menuitem", {name:/^English/})).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(chat.getByRole("menuitem", {name:/^Prompt templates/})).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await expect(chat.getByRole("menu")).toHaveCount(0);
});
