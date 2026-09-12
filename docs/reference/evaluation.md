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
patterns, final-answer terms, and safe artifact-root-relative paths. Its public
Python seam is `psycheval.harbor.verifier.evaluate(...)` plus `aggregate(...)`;
the module CLI is `python -m psycheval.harbor.verifier`.

Workspace reconciliation reads only bounded verifier JSON plus regular-file
metadata for manifest-referenced artifacts from a Trial's effective data
directory; it does not buffer artifact bodies. Verifier JSON and safe artifact
metadata contribute to the evidence revision and therefore invalidate the
rebuildable source projection when they change. It projects explicit
score/verdict fields and, for administrators, opaque artifact identifiers; it
never projects raw verifier payloads, host paths, environment maps, process
output, or LLM responses into that summary. Catalog and export projections retain this safe summary for guests.

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
files. Binary artifacts containing recognized credentials are refused; ZIP-based
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

Direct verifier tests use explicit trajectory, source, and artifact fixtures.
Small synthetic Harbor Tasks test orchestration, resume, paths, artifacts, and
reward plumbing. Neither is an Agent-quality result.

Live evaluation is opt-in because providers, credentials, network access,
browser infrastructure, and upstream content can vary. Reports must distinguish
an Agent contract failure from harness, provider, network, browser, or upstream
failure. A live success is evidence for that run, not a deterministic guarantee.
