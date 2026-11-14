# Evaluation Lifecycle

Psycheval evaluates observable Agent behavior from reproducible Task inputs and
retained evidence.

## Vocabulary and lifecycle

- A **Task** is one instruction, environment, and verifier contract.
- A **Dataset** is a collection of Tasks.
- A **Trial** is one Agent attempt at one Task.
- A **Job** schedules one or more Trials for an Agent and Dataset.
- A **trajectory** is the ordered structured record of actions and observations.
- A **report** is a derived view over trajectories or Trials.

A Job resolves its Agent, Dataset, trial count, and execution configuration.
Each attempt creates its own Trial paths, trajectory, verifier output, reward,
exception state, and artifacts. Aggregation must preserve Trial failures rather
than replacing them with a Job-level average.

For WorkBuddy Trials, `verifier/score.json` is the canonical per-attempt score;
the Harbor reward remains separately visible and is classified as matched,
drifted, malformed, or missing. The official Dataset aggregate is owned by the
external WorkBuddy metrics implementation: attempts are averaged within a Task,
then all expected Tasks are averaged with missing or build-error Tasks scoring
zero.

Trial lifecycle status remains distinct from this score: a successfully
completed Agent/verifier lifecycle may retain status `success` when the
canonical WorkBuddy score is zero.

## Evidence semantics

A tool observation supports a call only when it is successful and has the same
`tool_call_id`. Required arguments belong to that call. Evidence from different
calls or alternative branches cannot be combined, and final prose cannot
replace a missing call, observation, or artifact.

ATIF establishes internal evidence consistency. Its provenance depends on the
Agent adapter or independent runtime telemetry; a synthetic ATIF fixture is not
proof that an Agent performed the recorded action.

The generic verifier evaluates ordered required calls, forbidden tool-name
patterns, final-answer terms, and safe artifact-root-relative paths.

Tool-name matching for `tool_names` and `forbidden_tool_names` ignores letter
case and literal `-` / `_` separators in both recorded names and patterns.
For example, `webfetch` matches `WebFetch`, `web-fetch`, and `web_fetch`.
Glob operators and character classes retain their syntax; exact names do not
become substring matches. A positive character class containing only literal `-`
and `_` is an ignored separator; ranges still consume a character. `?` consumes
one remaining character, so `web?fetch`
matches `webXfetch` but not `webfetch`. Required calls, forbidden calls and observation queries
use the same matcher. Argument values, URLs, observations and retained evidence
keep their existing semantics and original text. Dataset patterns use lowercase
names without separators or redundant spelling aliases.

Public Python seams are `build_scoring_plan(config)`, `evaluate(...)`, and
`aggregate(checks, *, plan)` in `psycheval.harbor.verifier`; the module CLI is
`python -m psycheval.harbor.verifier`. The [Harbor contract](harbor.md#script-checks-and-weighted-scoring)
owns custom script checks, fixed scoring items, and weighted partial credit.
Its optional [YAML Judge](harbor.md#yaml-llm-judge) adds text-quality scoring
without changing deterministic continuation gates. Incomplete model assessments
retain the rule score and their failure reason rather than a partial LLM score.

Workspace reconciliation reads only bounded verifier JSON plus regular-file
metadata for manifest-referenced artifacts from a Trial's effective data
directory; it does not buffer artifact bodies. Verifier JSON and safe artifact
metadata contribute to the evidence revision and therefore invalidate the
rebuildable source projection when they change. It projects explicit
score/verdict fields and, for administrators, opaque artifact identifiers; it
never projects raw verifier payloads, host paths, environment maps, process
output, or LLM responses into that summary. Catalog and export projections retain this safe summary for guests.

Manifest artifact downloads use `verifier_raw_path` under `raw_artifacts/`,
falling back to `text_path` when no raw path is present. Text previews and that
fallback accept `text_path` under `artifact_text/` or WorkBuddy's
`judge_evidence/`. Paths remain relative to the verifier directory, subject to
the same containment, regular-file, link, byte-budget, and preview-type checks.
Manifest extraction statuses remain visible, including upstream rejection;
an admitted path must resolve to a regular file and does not certify its content.
Explicit `missing` or `error` records without either path remain visible as
metadata-only artifacts, with no preview or download. Their free-form reasons
remain in the retained manifest, outside the safe summary. Other pathless records
are invalid; an unavailable status never bypasses validation of a supplied path.

Guests and administrators can inspect retained verification files on demand: `verifier/`,
`artifacts/`, `result.json`, and `exception.txt` within the selected Trial's
effective result directory (the selected Harbor Step for multi-step sources).
This read-only interface includes raw output, free-form verdict reasons, copying,
and bounded download access. HTTP retains `?download=true`; the bundled browser
exposes no per-file download button. Preview capability is a renderer capability,
not an authorization boundary: an unrenderable retained artifact can be downloaded.
Both roles are readers of the same shared workspace evidence. Known environment
credentials, recognizable secret literals and explicit JSON credential fields are
redacted in textual responses, including downloads, without modifying source
files. This HTTP filtering does not apply to an administrator-configured Agent
reading referenced paths directly; see the [workspace trust contract](workspace.md).
Binary artifacts containing recognized credentials are refused; ZIP-based
artifacts are checked within the same expanded-byte budget. Malformed or
unsupported compressed members produce a controlled file read error. The
credential filter does not promise to detect arbitrary private data or encoded secrets:
publishers must place only reader-shareable evidence in retained directories.
Malformed text is scanned as non-overlapping string tokens; escaped or
unterminated strings must not cause repeated scans of the remaining content.
Markdown uses the [shared file preview](workspace.md), with truncated content
remaining raw text. The interface grants no mutation capability. Lookup resolves only the
registered Mount, Job, and Trial; it requires neither Dataset registration nor
live Task resolution. It does not reconcile other Trials or compute Task digests.
File lists contain relative metadata and opaque identifiers; listing never reads
file bodies. A selected preview reads at most 2 MiB of text and marks truncation;
truncated or unrecognized documents are displayed as literal text. Structured
previews show recorded scores, weights, reasons, and test statuses without
recomputing the canonical score. Downloads retain the bounded artifact download
limit. Links and reparse points are rejected, active document content is never
executed, and binary responses use a sandbox Content Security Policy. Artifact
references resolve only to files inside the retained result directories.

## Deterministic and live validation

### Family-scoped tool evidence

The grader-wide `trajectory_scope` is `family` by default; `root` selects only
the current execution root. Each Harbor Step evaluates its own family. Required
calls, forbidden tools and observation queries share this selection. Final
answers and artifacts remain owned by the root. Copied context is not execution.
Tool identity includes trajectory identity.

Ambiguous call IDs produce failed tool checks; invalid causal graphs and exhausted
matching capacity fail the ordered checks. These results carry an
`evidence_incomplete` reason, not verifier errors.
Observation queries return no trusted matches for ambiguous evidence. Invalid
grader configuration remains an error. Check diagnostics retain accepted patterns,
observed tools and qualified witnesses without inventing execution order.
Ordered matching discards a later state when an earlier state on its proven
causal chain already satisfies at least the same rule dimensions; unordered
sibling states remain independent.

Tool evidence completeness is `complete`, `partial` or `unknown`, independently
of message display truncation. Missing declarations are unknown. Known complete
matches can satisfy required calls. Absence of forbidden tools requires complete
evidence throughout the scope; otherwise the check fails with
`evidence_incomplete`. Child capture is a grading dependency under family scope.
Import never automatically regrades evidence. Historical scores remain retained.
Standalone OpenCode exports cannot prove that every descendant was discovered;
family absence checks therefore remain incomplete without capture evidence.
Third-party ATIF without completeness declarations is also unknown. An explicit
`trajectory_scope: root` selects root-only evidence, but still requires a complete
root stream. Claude links prove dispatch when a parent tool result explicitly
references an embedded child; they do not by themselves prove a terminal join.
Repeated child links without per-call execution boundaries remain unordered.

Ordered matching uses canonical within-session order and proven activation
dispatch/join edges across sessions. Background dispatch is not a join. Parallel
siblings are unordered. Matching retains feasible witnesses instead of choosing
an arbitrary topological order. Arguments and observations belong to one call.


Direct verifier tests use explicit trajectory, source, and artifact fixtures.
Small synthetic Harbor Tasks test orchestration, resume, paths, artifacts, and
reward plumbing. Neither is an Agent-quality result.

Live evaluation is opt-in because providers, credentials, network access,
browser infrastructure, and upstream content can vary. Reports must distinguish
an Agent contract failure from harness, provider, network, browser, or upstream
failure. A live success is evidence for that run, not a deterministic guarantee.
