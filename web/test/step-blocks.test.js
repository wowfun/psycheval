import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom('<script type="application/json" id="peval-i18n">{}</script>');
const steps = await import("../../src/psycheval/assets/web/modules/steps.js");
test.after(() => browser.cleanup());

test("every step block copies only its displayed body and keeps the step open", async () => {
  const clipboard = Object.getOwnPropertyDescriptor(navigator, "clipboard");
  const copied = [];
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async text => copied.push(text) } });
  const target = document.createElement("div");
  const argumentsValue = { command: "echo '<answer>'", multiline: "a\nb" };
  const result = { error: "Failure <details>", retry: false };
  const agent = {
    step_id: 2, source: "agent", message: "  **Agent message**\n```text\n<answer>\n```\n",
    reasoning_content: "Reasoning & rationale\nSecond line",
    tool_calls: [{ tool_call_id: "call-1", function_name: "Run", arguments: argumentsValue }],
    observation: { results: [
      { source_call_id: "call-1", content: result, subagent_trajectory_ref: [{ trajectory_id: "child" }] },
      { source_call_id: "call-2", content: 0 },
      { source_call_id: "call-3", content: false },
    ] },
  };
  const meta = { steps: [{ step_id: 2, observations: [{ source_call_id: "call-1", tool_error: true, status: "error" }] }] };
  const multimodal = [{ type: "text", text: "User caption" }, { type: "image", source: { path: "fixture.png" } }];
  target.innerHTML = [
    { step_id: 1, source: "system", message: "System instruction" },
    agent,
    { step_id: 3, source: "user", message: multimodal },
  ].map(step => steps.renderStep(step, meta, {}, { open: true })).join("");
  document.body.append(target);
  steps.bindBlockCopyControls(target);
  try {
    const cards = [...target.querySelectorAll(".block")];
    assert.equal(cards.length, 8);
    assert.equal(target.querySelectorAll("script").length, 0);
    assert.equal(target.querySelectorAll("h4.danger").length, 1);
    for (const card of cards) {
      const button = card.querySelector("[data-block-copy]");
      button.click();
      button.click();
      await new Promise(resolve => setImmediate(resolve));
      assert.equal(button.textContent, "Copied");
      assert.equal(card.closest(".step").open, true);
    }
    assert.deepEqual(copied, [
      "System instruction", agent.reasoning_content, agent.message,
      JSON.stringify(argumentsValue, null, 2), JSON.stringify(result, null, 2),
      "0", "false", JSON.stringify(multimodal, null, 2),
    ]);
  } finally {
    target.remove();
    if (clipboard) Object.defineProperty(navigator, "clipboard", clipboard);
    else delete navigator.clipboard;
  }
});

test("empty observation bodies keep a disabled Copy action", () => {
  for (const content of ["", " \n", null, undefined]) {
    const target = document.createElement("div");
    target.innerHTML = steps.renderObservationBlock({ source_call_id: "call", content }, {});
    const button = target.querySelector("[data-block-copy]");
    assert.equal(button.disabled, true);
    assert.equal(button.title, "No block content to copy");
  }
});


test("observation links resolve embedded identities even with external paths", () => {
  const target = document.createElement("div");
  target.innerHTML = steps.renderStep({ step_id: 1, source: "agent", message: "Result", observation: { results: [{
    content: "Done", subagent_trajectory_ref: [
      { trajectory_id: "child", trajectory_path: "child.json" },
      { trajectory_id: "external", trajectory_path: "external.json" },
      { trajectory_id: "missing" },
    ],
  }] } }, {}, {}, { childIds: new Set(["child"]) });
  assert.deepEqual([...target.querySelectorAll("[data-trajectory-id]")].map(node => node.dataset.trajectoryId), ["child"]);
});
