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
output, or LLM responses. An administrator preview or download opens only the
selected artifact. Its source lookup resolves the exact registered Mount, Job,
and Trial plus the recorded Task's lightweight Dataset association; it does not
reconcile unrelated Trials or compute Task-content digests. Preview is restricted
to the explicit text and raster-image suffix allowlists and is returned under a
sandbox Content Security Policy. The HTTP boundary independently constrains the
download filename to the public ASCII artifact-name form. Guests receive only the
safe score summary and no artifact identity.

## Deterministic and live validation

Direct verifier tests use explicit trajectory, source, and artifact fixtures.
Small synthetic Harbor Tasks test orchestration, resume, paths, artifacts, and
reward plumbing. Neither is an Agent-quality result.

Live evaluation is opt-in because providers, credentials, network access,
browser infrastructure, and upstream content can vary. Reports must distinguish
an Agent contract failure from harness, provider, network, browser, or upstream
failure. A live success is evidence for that run, not a deterministic guarantee.
