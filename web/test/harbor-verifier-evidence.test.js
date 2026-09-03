import assert from "node:assert/strict";
import test from "node:test";

import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","sources":[]}</script>
`);
const selected = await import("../../src/psycheval/assets/web/modules/analysis-selected.js");

test.after(() => browser.cleanup());

test("WorkBuddy evidence renders score consistency and safe artifact controls", () => {
  const html = selected.renderHarborEvidence({
    harbor_provenance: { result_id: "result-1" },
    verifier_evidence: {
      source_key: "source-key",
      status: "present",
      score: 0.7,
      score_source: "reward",
      harbor_reward: 0.6,
      reward_consistency: "drifted",
      tests: { passed: 3, total: 4, status: "passed" },
      llm_judge: { status: "completed", score: 0.5 },
      artifacts: [
        {
          id: "artifact-id",
          name: "report<unsafe>",
          preview: { kind: "text" },
          download_available: true,
        },
        {
          id: "image-id",
          name: "chart",
          preview: { kind: "image" },
          download_available: true,
        },
      ],
    },
  });

  assert.match(html, /WorkBuddy verifier/);
  assert.match(html, /drifted/);
  assert.match(html, /3 \/ 4/);
  assert.match(html, /report&lt;unsafe&gt;/);
  assert.match(
    html,
    /href="\/api\/harbor\/verifier-artifacts\/source-key\/artifact-id"/,
  );
  assert.doesNotMatch(html, /<pre>/);
  assert.match(
    html,
    /\/api\/harbor\/verifier-artifacts\/source-key\/artifact-id\?download=true/,
  );
  assert.match(
    html,
    /src="\/api\/harbor\/verifier-artifacts\/source-key\/image-id"/,
  );
});

test("guest score summary renders without artifact controls", () => {
  const html = selected.renderHarborEvidence({
    harbor_provenance: { result_id: "result-1" },
    verifier_evidence: {
      status: "present",
      score: 1,
      score_source: "reward",
      reward_consistency: "matched",
    },
  });
  assert.match(html, /WorkBuddy verifier/);
  assert.doesNotMatch(html, /verifier-artifacts/);
});
