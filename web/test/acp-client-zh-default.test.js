import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const response = payload => new Response(JSON.stringify(payload), { status: 200 });
const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"role":"admin","workspace_id":"zh-default"}</script>
  <button data-acp-open disabled>Copilot</button>
  <div data-acp-backdrop hidden></div>
  <aside data-acp-drawer hidden>
    <button data-acp-close>Close</button>
    <select data-acp-agent></select><button data-acp-connect>Connect</button>
    <a data-acp-configure hidden></a><div data-acp-placeholder></div><div data-acp-chat></div>
  </aside>
`, {
  fetch: async path => response(String(path) === "/api/acp/agents"
    ? { agents: [] }
    : [
        { id: "evaluation-review", title: "Evaluation review", content: "English" },
        { id: "evaluation-review-zh-cn", title: "评测复盘", content: "中文" },
        { id: "failure-diagnosis-zh-cn", title: "失败诊断", content: "诊断" },
      ]),
});
document.documentElement.lang = "zh-CN";

const acp = await import("../../src/psycheval/assets/web/modules/acp-client.js");

test.after(() => browser.cleanup());

test("Chinese prompt groups are ordered without automatic insertion or saved selection", async () => {
  await acp.initializeAcp();
  const menu = acp.composerActions().find(action => action.id === "prompts");
  assert.deepEqual(menu.children.map(group => group.label), ["中文", "English"]);
  assert.ok(menu.children[0].children.some(action => action.label === "评测复盘"));
  const saved = JSON.parse(window.localStorage.getItem("peval:zh-default:acp-client"));
  assert.equal("prompt_asset_id" in saved, false);
  assert.equal("prompt_asset_explicit" in saved, false);
});
