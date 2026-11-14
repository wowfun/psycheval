import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","sources":[]}</script>
`);
const selected = await import("../../src/psycheval/assets/web/modules/analysis-selected.js");

test.after(() => browser.cleanup());

test("diagnostic trajectory notice and cleanup paths remain visible and escaped", () => {
  assert.match(selected.renderIncompleteTrajectory({ extra: { diagnostic_only: true } }), /Incomplete trajectory/);
  assert.equal(selected.renderIncompleteTrajectory({}), "");
  const html = selected.renderSelectedWarnings({ warnings: ["Windows cleanup warning; paths: C:/owned/<runtime>"] });
  assert.match(html, /C:\/owned\/&lt;runtime&gt;/);
});

test("Info keeps provenance but leaves verification results and artifacts to their reader", () => {
  const html = selected.renderTrialInfo({}, {
    trial_key: "trial", harbor_provenance: { result_id: "result<1>", task_digest: "sha256:recorded" },
    verifier_evidence: { score: 0.7, tests: { passed: 3, total: 4 }, artifacts: [{ name: "report<unsafe>", preview: { kind: "image" } }] },
    task_metadata: { description: "Live description" },
  });
  assert.match(html, /result&lt;1&gt;/);
  assert.match(html, /sha256:recorded/);
  assert.doesNotMatch(html, /WorkBuddy verifier|report&lt;unsafe&gt;|Live description|0\.7|3 \/ 4/);
});
