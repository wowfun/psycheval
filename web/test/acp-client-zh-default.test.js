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
    <select data-acp-prompt-asset></select><button data-acp-use-prompt>Use</button>
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

test("a fresh Chinese workspace selects the Chinese evaluation preset", async () => {
  await acp.initializeAcp();
  const select = document.querySelector("[data-acp-prompt-asset]");
  assert.equal(select.value, "evaluation-review-zh-cn");
  assert.deepEqual(
    [...select.options].map(option => option.textContent),
    ["Custom prompt", "Evaluation review", "评测复盘", "失败诊断"],
  );
  assert.equal(
    JSON.parse(window.localStorage.getItem("peval:zh-default:acp-client"))
      .prompt_asset_explicit,
    false,
  );
});
