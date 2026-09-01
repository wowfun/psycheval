import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const response = payload => new Response(JSON.stringify(payload), { status: 200 });
const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"role":"admin","workspace_id":"zh-saved"}</script>
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
      ]),
});
document.documentElement.lang = "zh-CN";
window.localStorage.setItem(
  "peval:zh-saved:acp-client",
  JSON.stringify({ prompt_asset_id: "evaluation-review" }),
);

const acp = await import("../../src/psycheval/assets/web/modules/acp-client.js");

test.after(() => browser.cleanup());

test("a valid saved prompt selection wins over the Chinese locale default", async () => {
  await acp.initializeAcp();
  assert.equal(
    document.querySelector("[data-acp-prompt-asset]").value,
    "evaluation-review",
  );
  assert.equal(
    JSON.parse(window.localStorage.getItem("peval:zh-saved:acp-client"))
      .prompt_asset_explicit,
    true,
  );
});
